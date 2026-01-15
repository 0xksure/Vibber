package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
	"github.com/go-chi/httprate"
	"github.com/joho/godotenv"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/handlers"
	customMiddleware "github.com/vibber/backend/internal/middleware"
	"github.com/vibber/backend/internal/repository"
)

func main() {
	// Load environment variables
	if err := godotenv.Load(); err != nil {
		log.Warn().Msg("No .env file found")
	}

	// Initialize logger
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	if os.Getenv("ENV") == "development" {
		log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})
	}

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to load configuration")
	}

	// Initialize database
	db, err := repository.NewPostgresDB(cfg.DatabaseURL)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to connect to database")
	}
	defer db.Close()

	// Initialize Redis
	redisClient, err := repository.NewRedisClient(cfg.RedisURL)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to connect to Redis")
	}
	defer redisClient.Close()

	// Initialize repositories
	repos := repository.NewRepositories(db)

	// Initialize handlers
	h := handlers.NewHandlers(repos, redisClient, cfg)

	// Setup router
	r := chi.NewRouter()

	// Global middleware
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))

	// CORS configuration
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{"http://localhost:3000", cfg.FrontendURL},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-Request-ID"},
		ExposedHeaders:   []string{"Link"},
		AllowCredentials: true,
		MaxAge:           300,
	}))

	// Rate limiting
	r.Use(httprate.LimitByIP(100, time.Minute))

	// Health check
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"healthy"}`))
	})

	// API routes
	r.Route("/api/v1", func(r chi.Router) {
		// Public routes
		r.Group(func(r chi.Router) {
			r.Post("/auth/login", h.Auth.Login)
			r.Post("/auth/register", h.Auth.Register)
			r.Get("/auth/oauth/{provider}", h.Auth.OAuthRedirect)
			r.Get("/auth/oauth/{provider}/callback", h.Auth.OAuthCallback)
		})

		// Protected routes
		r.Group(func(r chi.Router) {
			r.Use(customMiddleware.JWTAuth(cfg.JWTSecret))

			// Auth
			r.Post("/auth/refresh", h.Auth.RefreshToken)
			r.Post("/auth/logout", h.Auth.Logout)
			r.Get("/auth/me", h.Auth.Me)

			// Agents
			r.Route("/agents", func(r chi.Router) {
				r.Get("/", h.Agent.List)
				r.Post("/", h.Agent.Create)
				r.Route("/{agentID}", func(r chi.Router) {
					r.Get("/", h.Agent.Get)
					r.Put("/", h.Agent.Update)
					r.Delete("/", h.Agent.Delete)
					r.Post("/train", h.Agent.Train)
					r.Get("/status", h.Agent.Status)
					r.Put("/settings", h.Agent.UpdateSettings)
				})
			})

			// Integrations
			r.Route("/integrations", func(r chi.Router) {
				r.Get("/", h.Integration.List)
				r.Get("/{provider}/connect", h.Integration.Connect)
				r.Get("/{provider}/callback", h.Integration.Callback)
				r.Delete("/{integrationID}", h.Integration.Disconnect)
				r.Get("/{integrationID}/status", h.Integration.Status)
			})

			// Interactions
			r.Route("/interactions", func(r chi.Router) {
				r.Get("/", h.Interaction.List)
				r.Get("/{interactionID}", h.Interaction.Get)
				r.Post("/{interactionID}/feedback", h.Interaction.Feedback)
			})

			// Escalations
			r.Route("/escalations", func(r chi.Router) {
				r.Get("/", h.Escalation.List)
				r.Get("/{escalationID}", h.Escalation.Get)
				r.Post("/{escalationID}/resolve", h.Escalation.Resolve)
				r.Post("/{escalationID}/approve", h.Escalation.Approve)
				r.Post("/{escalationID}/reject", h.Escalation.Reject)
			})

			// Analytics
			r.Route("/analytics", func(r chi.Router) {
				r.Get("/overview", h.Analytics.Overview)
				r.Get("/trends", h.Analytics.Trends)
				r.Get("/performance", h.Analytics.Performance)
			})

			// Organizations (admin)
			r.Route("/organizations", func(r chi.Router) {
				r.Get("/", h.Organization.Get)
				r.Put("/", h.Organization.Update)
				r.Get("/members", h.Organization.ListMembers)
				r.Post("/members/invite", h.Organization.InviteMember)
			})

			// Credentials (organization OAuth app credentials)
			r.Route("/credentials", func(r chi.Router) {
				r.Get("/", h.Credentials.List)
				r.Post("/", h.Credentials.Create)
				r.Get("/{provider}", h.Credentials.Get)
				r.Put("/{provider}", h.Credentials.Update)
				r.Delete("/{provider}", h.Credentials.Delete)
				r.Post("/{provider}/verify", h.Credentials.Verify)
			})
		})

		// Webhook routes (validated by signature)
		r.Route("/webhooks", func(r chi.Router) {
			r.Post("/slack", h.Webhook.Slack)
			r.Post("/github", h.Webhook.GitHub)
			r.Post("/jira", h.Webhook.Jira)
		})

		// Internal API routes (for AI agent service-to-service communication)
		r.Route("/internal", func(r chi.Router) {
			// Authenticated by X-Service-Key header
			r.Get("/credentials", h.Credentials.GetForAgent)
		})
	})

	// Start server
	server := &http.Server{
		Addr:         fmt.Sprintf(":%s", cfg.Port),
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Graceful shutdown
	go func() {
		log.Info().Str("port", cfg.Port).Msg("Starting server")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("Server failed")
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Info().Msg("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Fatal().Err(err).Msg("Server forced to shutdown")
	}

	log.Info().Msg("Server exited gracefully")
}
