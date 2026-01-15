package models

import (
	"time"

	"github.com/google/uuid"
)

// Organization represents a company/team using Vibber
type Organization struct {
	ID        uuid.UUID `json:"id" db:"id"`
	Name      string    `json:"name" db:"name"`
	Slug      string    `json:"slug" db:"slug"`
	Plan      string    `json:"plan" db:"plan"`
	CreatedAt time.Time `json:"createdAt" db:"created_at"`
	UpdatedAt time.Time `json:"updatedAt" db:"updated_at"`
}

// User represents a user in the system
type User struct {
	ID           uuid.UUID  `json:"id" db:"id"`
	OrgID        uuid.UUID  `json:"orgId" db:"org_id"`
	Email        string     `json:"email" db:"email"`
	Name         string     `json:"name" db:"name"`
	PasswordHash string     `json:"-" db:"password_hash"`
	AvatarURL    *string    `json:"avatarUrl" db:"avatar_url"`
	Role         string     `json:"role" db:"role"`
	Provider     *string    `json:"provider" db:"provider"`
	ProviderID   *string    `json:"-" db:"provider_id"`
	CreatedAt    time.Time  `json:"createdAt" db:"created_at"`
	UpdatedAt    time.Time  `json:"updatedAt" db:"updated_at"`
	LastLoginAt  *time.Time `json:"lastLoginAt" db:"last_login_at"`
}

// Agent represents an AI clone of a user
type Agent struct {
	ID                  uuid.UUID `json:"id" db:"id"`
	UserID              uuid.UUID `json:"userId" db:"user_id"`
	Name                string    `json:"name" db:"name"`
	Description         *string   `json:"description" db:"description"`
	AvatarURL           *string   `json:"avatarUrl" db:"avatar_url"`
	Status              string    `json:"status" db:"status"` // training, active, paused, error
	ConfidenceThreshold int       `json:"confidenceThreshold" db:"confidence_threshold"`
	AutoMode            bool      `json:"autoMode" db:"auto_mode"`
	WorkingHours        *string   `json:"workingHours" db:"working_hours"` // JSON string
	CreatedAt           time.Time `json:"createdAt" db:"created_at"`
	UpdatedAt           time.Time `json:"updatedAt" db:"updated_at"`
}

// AgentStatus represents the current status of an agent
type AgentStatus struct {
	Status             string    `json:"status"`
	IsActive           bool      `json:"isActive"`
	LastActivity       time.Time `json:"lastActivity"`
	TodayInteractions  int       `json:"todayInteractions"`
	PendingEscalations int       `json:"pendingEscalations"`
	ConfidenceScore    float64   `json:"confidenceScore"`
}

// Integration represents a connected service
type Integration struct {
	ID           uuid.UUID  `json:"id" db:"id"`
	AgentID      uuid.UUID  `json:"agentId" db:"agent_id"`
	Provider     string     `json:"provider" db:"provider"` // slack, github, jira, confluence, elastic
	AccessToken  string     `json:"-" db:"access_token"`
	RefreshToken *string    `json:"-" db:"refresh_token"`
	Scopes       []string   `json:"scopes" db:"scopes"`
	Status       string     `json:"status" db:"status"` // active, expired, error
	ExternalID   *string    `json:"externalId" db:"external_id"`
	Metadata     *string    `json:"metadata" db:"metadata"` // JSON string for provider-specific data
	CreatedAt    time.Time  `json:"createdAt" db:"created_at"`
	ExpiresAt    *time.Time `json:"expiresAt" db:"expires_at"`
}

// Interaction represents a single agent interaction
type Interaction struct {
	ID              uuid.UUID  `json:"id" db:"id"`
	AgentID         uuid.UUID  `json:"agentId" db:"agent_id"`
	IntegrationID   uuid.UUID  `json:"integrationId" db:"integration_id"`
	Provider        string     `json:"provider" db:"provider"`
	InteractionType string     `json:"interactionType" db:"interaction_type"` // message, pr_review, ticket_update, etc.
	InputData       string     `json:"inputData" db:"input_data"`             // JSON
	OutputData      *string    `json:"outputData" db:"output_data"`           // JSON
	ConfidenceScore *int       `json:"confidenceScore" db:"confidence_score"`
	Status          string     `json:"status" db:"status"` // pending, completed, escalated, failed
	Escalated       bool       `json:"escalated" db:"escalated"`
	HumanFeedback   *string    `json:"humanFeedback" db:"human_feedback"` // approved, rejected, corrected
	ProcessingTime  *int       `json:"processingTime" db:"processing_time"`
	CreatedAt       time.Time  `json:"createdAt" db:"created_at"`
	CompletedAt     *time.Time `json:"completedAt" db:"completed_at"`
}

// Escalation represents an interaction that needs human attention
type Escalation struct {
	ID            uuid.UUID  `json:"id" db:"id"`
	InteractionID uuid.UUID  `json:"interactionId" db:"interaction_id"`
	AgentID       uuid.UUID  `json:"agentId" db:"agent_id"`
	Reason        string     `json:"reason" db:"reason"`
	Priority      string     `json:"priority" db:"priority"` // low, medium, high, urgent
	Status        string     `json:"status" db:"status"`     // pending, resolved, dismissed
	Context       *string    `json:"context" db:"context"`   // JSON with additional context
	Resolution    *string    `json:"resolution" db:"resolution"`
	ResolvedBy    *uuid.UUID `json:"resolvedBy" db:"resolved_by"`
	ResolvedAt    *time.Time `json:"resolvedAt" db:"resolved_at"`
	CreatedAt     time.Time  `json:"createdAt" db:"created_at"`
}

// TrainingSample represents a sample used to train an agent's personality
type TrainingSample struct {
	ID         uuid.UUID  `json:"id" db:"id"`
	AgentID    uuid.UUID  `json:"agentId" db:"agent_id"`
	Provider   *string    `json:"provider" db:"provider"`
	SampleType string     `json:"sampleType" db:"sample_type"` // message, response, style, domain
	InputText  string     `json:"inputText" db:"input_text"`
	OutputText *string    `json:"outputText" db:"output_text"`
	Embedding  []float32  `json:"-" db:"embedding"`
	IsPositive bool       `json:"isPositive" db:"is_positive"`
	CreatedAt  time.Time  `json:"createdAt" db:"created_at"`
}

// Analytics structures

type OverviewMetrics struct {
	TotalInteractions    int     `json:"totalInteractions"`
	TodayInteractions    int     `json:"todayInteractions"`
	AutonomousRate       float64 `json:"autonomousRate"`
	PendingEscalations   int     `json:"pendingEscalations"`
	AvgConfidenceScore   float64 `json:"avgConfidenceScore"`
	AvgProcessingTime    float64 `json:"avgProcessingTime"`
	InteractionsByType   map[string]int `json:"interactionsByType"`
	InteractionsByStatus map[string]int `json:"interactionsByStatus"`
}

type TrendData struct {
	Date         string  `json:"date"`
	Interactions int     `json:"interactions"`
	Escalations  int     `json:"escalations"`
	Confidence   float64 `json:"confidence"`
}

type PerformanceMetrics struct {
	Provider          string  `json:"provider"`
	TotalInteractions int     `json:"totalInteractions"`
	SuccessRate       float64 `json:"successRate"`
	AvgConfidence     float64 `json:"avgConfidence"`
	AvgResponseTime   float64 `json:"avgResponseTime"`
}

// OrganizationCredential stores OAuth app credentials per organization
// Organizations provide their own Slack, GitHub, Jira app credentials
type OrganizationCredential struct {
	ID            uuid.UUID  `json:"id" db:"id"`
	OrgID         uuid.UUID  `json:"orgId" db:"org_id"`
	Provider      string     `json:"provider" db:"provider"` // slack, github, jira, confluence, elastic
	ClientID      string     `json:"clientId" db:"client_id"`
	ClientSecret  string     `json:"-" db:"client_secret"` // Never expose in JSON
	WebhookSecret *string    `json:"-" db:"webhook_secret"`
	SigningSecret *string    `json:"-" db:"signing_secret"`
	Config        *string    `json:"config" db:"config"` // JSON for provider-specific config
	IsActive      bool       `json:"isActive" db:"is_active"`
	VerifiedAt    *time.Time `json:"verifiedAt" db:"verified_at"`
	CreatedBy     *uuid.UUID `json:"createdBy" db:"created_by"`
	CreatedAt     time.Time  `json:"createdAt" db:"created_at"`
	UpdatedAt     time.Time  `json:"updatedAt" db:"updated_at"`
}

// OrganizationCredentialConfig provider-specific configurations
type SlackCredentialConfig struct {
	WorkspaceID         string   `json:"workspaceId,omitempty"`
	AllowedChannels     []string `json:"allowedChannels,omitempty"`
	RestrictToWorkspace bool     `json:"restrictToWorkspace,omitempty"`
}

type GitHubCredentialConfig struct {
	EnterpriseURL string   `json:"enterpriseUrl,omitempty"`
	AllowedOrgs   []string `json:"allowedOrgs,omitempty"`
	AllowedRepos  []string `json:"allowedRepos,omitempty"`
}

type JiraCredentialConfig struct {
	SiteURL      string   `json:"siteUrl"` // e.g., https://your-domain.atlassian.net
	IsCloud      bool     `json:"isCloud"`
	AllowedProjects []string `json:"allowedProjects,omitempty"`
}

// Request/Response structures

type LoginRequest struct {
	Email    string `json:"email" validate:"required,email"`
	Password string `json:"password" validate:"required,min=8"`
}

type RegisterRequest struct {
	Email        string `json:"email" validate:"required,email"`
	Password     string `json:"password" validate:"required,min=8"`
	Name         string `json:"name" validate:"required"`
	Organization string `json:"organization" validate:"required"`
}

type AuthResponse struct {
	User         *User  `json:"user"`
	AccessToken  string `json:"accessToken"`
	RefreshToken string `json:"refreshToken"`
	ExpiresIn    int    `json:"expiresIn"`
}

type CreateAgentRequest struct {
	Name                string `json:"name" validate:"required"`
	Description         string `json:"description"`
	ConfidenceThreshold int    `json:"confidenceThreshold"`
}

type UpdateAgentRequest struct {
	Name                *string `json:"name"`
	Description         *string `json:"description"`
	ConfidenceThreshold *int    `json:"confidenceThreshold"`
	AutoMode            *bool   `json:"autoMode"`
	WorkingHours        *string `json:"workingHours"`
}

type FeedbackRequest struct {
	Feedback   string `json:"feedback" validate:"required,oneof=approved rejected corrected"`
	Correction string `json:"correction,omitempty"`
	Notes      string `json:"notes,omitempty"`
}

type PaginationParams struct {
	Page     int    `json:"page"`
	PageSize int    `json:"pageSize"`
	SortBy   string `json:"sortBy"`
	SortDir  string `json:"sortDir"`
}

type PaginatedResponse struct {
	Data       interface{} `json:"data"`
	Page       int         `json:"page"`
	PageSize   int         `json:"pageSize"`
	TotalItems int         `json:"totalItems"`
	TotalPages int         `json:"totalPages"`
}

// Organization Credential Requests/Responses

type CreateCredentialRequest struct {
	Provider      string  `json:"provider" validate:"required,oneof=slack github jira confluence elastic"`
	ClientID      string  `json:"clientId" validate:"required"`
	ClientSecret  string  `json:"clientSecret" validate:"required"`
	WebhookSecret *string `json:"webhookSecret,omitempty"`
	SigningSecret *string `json:"signingSecret,omitempty"`
	Config        *string `json:"config,omitempty"` // JSON string
}

type UpdateCredentialRequest struct {
	ClientID      *string `json:"clientId,omitempty"`
	ClientSecret  *string `json:"clientSecret,omitempty"`
	WebhookSecret *string `json:"webhookSecret,omitempty"`
	SigningSecret *string `json:"signingSecret,omitempty"`
	Config        *string `json:"config,omitempty"`
	IsActive      *bool   `json:"isActive,omitempty"`
}

// CredentialResponse is a safe response that doesn't expose secrets
type CredentialResponse struct {
	ID         uuid.UUID  `json:"id"`
	Provider   string     `json:"provider"`
	ClientID   string     `json:"clientId"`
	HasSecret  bool       `json:"hasSecret"` // Indicates if secret is configured
	Config     *string    `json:"config"`
	IsActive   bool       `json:"isActive"`
	VerifiedAt *time.Time `json:"verifiedAt"`
	CreatedAt  time.Time  `json:"createdAt"`
	UpdatedAt  time.Time  `json:"updatedAt"`
}

// CredentialForAgent is passed to the AI agent with full credentials
type CredentialForAgent struct {
	Provider      string  `json:"provider"`
	ClientID      string  `json:"clientId"`
	ClientSecret  string  `json:"clientSecret"`
	WebhookSecret *string `json:"webhookSecret,omitempty"`
	SigningSecret *string `json:"signingSecret,omitempty"`
	Config        *string `json:"config,omitempty"`
}
