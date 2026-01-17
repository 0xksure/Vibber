package handlers

import (
	"github.com/redis/go-redis/v9"
	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/repository"
)

// Handlers holds all HTTP handlers
type Handlers struct {
	Auth         *AuthHandler
	Agent        *AgentHandler
	Integration  *IntegrationHandler
	Interaction  *InteractionHandler
	Escalation   *EscalationHandler
	Analytics    *AnalyticsHandler
	Organization *OrganizationHandler
	Webhook      *WebhookHandler
	Credentials  *CredentialsHandler
	Ralph        *RalphHandler
}

// NewHandlers creates a new handlers instance
func NewHandlers(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *Handlers {
	return &Handlers{
		Auth:         NewAuthHandler(repos, redis, cfg),
		Agent:        NewAgentHandler(repos, redis, cfg),
		Integration:  NewIntegrationHandler(repos, redis, cfg),
		Interaction:  NewInteractionHandler(repos, redis, cfg),
		Escalation:   NewEscalationHandler(repos, redis, cfg),
		Analytics:    NewAnalyticsHandler(repos, redis, cfg),
		Organization: NewOrganizationHandler(repos, redis, cfg),
		Webhook:      NewWebhookHandler(repos, redis, cfg),
		Credentials:  NewCredentialsHandler(repos, redis, cfg),
		Ralph:        NewRalphHandler(repos, redis, cfg),
	}
}
