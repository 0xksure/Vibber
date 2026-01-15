package config

import (
	"fmt"
	"os"
)

// Config holds all configuration for the application
type Config struct {
	// Server
	Port        string
	Env         string
	FrontendURL string

	// Database
	DatabaseURL string
	RedisURL    string

	// Security
	JWTSecret          string
	JWTExpiryMinutes   int
	RefreshExpiryHours int

	// OAuth Providers
	GoogleClientID     string
	GoogleClientSecret string
	GitHubClientID     string
	GitHubClientSecret string
	SlackClientID      string
	SlackClientSecret  string
	JiraClientID       string
	JiraClientSecret   string

	// Message Queue
	RabbitMQURL string

	// AI Services
	AgentServiceURL string
	OpenAIAPIKey    string
	AnthropicAPIKey string

	// External Services
	PineconeAPIKey string
	PineconeIndex  string
}

// Load loads configuration from environment variables
func Load() (*Config, error) {
	cfg := &Config{
		Port:               getEnv("PORT", "8080"),
		Env:                getEnv("ENV", "development"),
		FrontendURL:        getEnv("FRONTEND_URL", "http://localhost:3000"),
		DatabaseURL:        getEnv("DATABASE_URL", "postgres://postgres:postgres@localhost:5432/vibber?sslmode=disable"),
		RedisURL:           getEnv("REDIS_URL", "redis://localhost:6379"),
		JWTSecret:          getEnv("JWT_SECRET", ""),
		JWTExpiryMinutes:   15,
		RefreshExpiryHours: 168, // 7 days
		GoogleClientID:     getEnv("GOOGLE_CLIENT_ID", ""),
		GoogleClientSecret: getEnv("GOOGLE_CLIENT_SECRET", ""),
		GitHubClientID:     getEnv("GITHUB_CLIENT_ID", ""),
		GitHubClientSecret: getEnv("GITHUB_CLIENT_SECRET", ""),
		SlackClientID:      getEnv("SLACK_CLIENT_ID", ""),
		SlackClientSecret:  getEnv("SLACK_CLIENT_SECRET", ""),
		JiraClientID:       getEnv("JIRA_CLIENT_ID", ""),
		JiraClientSecret:   getEnv("JIRA_CLIENT_SECRET", ""),
		RabbitMQURL:        getEnv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
		AgentServiceURL:    getEnv("AGENT_SERVICE_URL", "http://localhost:8000"),
		OpenAIAPIKey:       getEnv("OPENAI_API_KEY", ""),
		AnthropicAPIKey:    getEnv("ANTHROPIC_API_KEY", ""),
		PineconeAPIKey:     getEnv("PINECONE_API_KEY", ""),
		PineconeIndex:      getEnv("PINECONE_INDEX", "vibber-agents"),
	}

	if err := cfg.validate(); err != nil {
		return nil, err
	}

	return cfg, nil
}

func (c *Config) validate() error {
	if c.JWTSecret == "" && c.Env == "production" {
		return fmt.Errorf("JWT_SECRET is required in production")
	}

	// Set a default JWT secret for development
	if c.JWTSecret == "" {
		c.JWTSecret = "dev-secret-change-in-production"
	}

	return nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
