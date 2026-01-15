package handlers

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"

	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/repository"
	"github.com/vibber/backend/pkg/response"
)

type IntegrationHandler struct {
	repos *repository.Repositories
	redis *redis.Client
	cfg   *config.Config
}

func NewIntegrationHandler(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *IntegrationHandler {
	return &IntegrationHandler{
		repos: repos,
		redis: redis,
		cfg:   cfg,
	}
}

func (h *IntegrationHandler) List(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)

	// Get user's agents
	agents, err := h.repos.Agent.ListByUserID(r.Context(), userID)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to fetch agents")
		return
	}

	// Collect integrations from all agents
	var allIntegrations []interface{}
	for _, agent := range agents {
		integrations, _ := h.repos.Integration.ListByAgentID(r.Context(), agent.ID)
		for _, i := range integrations {
			allIntegrations = append(allIntegrations, map[string]interface{}{
				"integration": i,
				"agentName":   agent.Name,
			})
		}
	}

	response.JSON(w, http.StatusOK, allIntegrations)
}

func (h *IntegrationHandler) Connect(w http.ResponseWriter, r *http.Request) {
	provider := chi.URLParam(r, "provider")
	agentID := r.URL.Query().Get("agent_id")

	if agentID == "" {
		response.Error(w, http.StatusBadRequest, "agent_id is required")
		return
	}

	var authURL string
	state := agentID // Use agent ID as state for callback

	switch provider {
	case "slack":
		authURL = h.getSlackAuthURL(state)
	case "github":
		authURL = h.getGitHubIntegrationAuthURL(state)
	case "jira":
		authURL = h.getJiraAuthURL(state)
	case "confluence":
		authURL = h.getConfluenceAuthURL(state)
	default:
		response.Error(w, http.StatusBadRequest, "Unsupported provider")
		return
	}

	http.Redirect(w, r, authURL, http.StatusTemporaryRedirect)
}

func (h *IntegrationHandler) Callback(w http.ResponseWriter, r *http.Request) {
	provider := chi.URLParam(r, "provider")
	code := r.URL.Query().Get("code")
	state := r.URL.Query().Get("state") // Contains agent ID

	if code == "" || state == "" {
		response.Error(w, http.StatusBadRequest, "Missing authorization code or state")
		return
	}

	agentID, err := uuid.Parse(state)
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid agent ID")
		return
	}

	// Exchange code for tokens based on provider
	switch provider {
	case "slack":
		err = h.handleSlackCallback(r.Context(), agentID, code)
	case "github":
		err = h.handleGitHubIntegrationCallback(r.Context(), agentID, code)
	case "jira":
		err = h.handleJiraCallback(r.Context(), agentID, code)
	case "confluence":
		err = h.handleConfluenceCallback(r.Context(), agentID, code)
	default:
		response.Error(w, http.StatusBadRequest, "Unsupported provider")
		return
	}

	if err != nil {
		// Redirect to frontend with error
		http.Redirect(w, r, h.cfg.FrontendURL+"/integrations?error="+err.Error(), http.StatusTemporaryRedirect)
		return
	}

	// Redirect to frontend on success
	http.Redirect(w, r, h.cfg.FrontendURL+"/integrations?success="+provider, http.StatusTemporaryRedirect)
}

func (h *IntegrationHandler) Disconnect(w http.ResponseWriter, r *http.Request) {
	integrationID, err := uuid.Parse(chi.URLParam(r, "integrationID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid integration ID")
		return
	}

	// Verify ownership through agent
	integration, err := h.repos.Integration.GetByID(r.Context(), integrationID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Integration not found")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)
	agent, _ := h.repos.Agent.GetByID(r.Context(), integration.AgentID)
	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	if err := h.repos.Integration.Delete(r.Context(), integrationID); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to disconnect integration")
		return
	}

	response.JSON(w, http.StatusOK, map[string]string{"message": "Integration disconnected"})
}

func (h *IntegrationHandler) Status(w http.ResponseWriter, r *http.Request) {
	integrationID, err := uuid.Parse(chi.URLParam(r, "integrationID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid integration ID")
		return
	}

	integration, err := h.repos.Integration.GetByID(r.Context(), integrationID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Integration not found")
		return
	}

	// Check if token is still valid
	status := "active"
	if integration.ExpiresAt != nil && integration.ExpiresAt.Before(time.Now()) {
		status = "expired"
	}

	response.JSON(w, http.StatusOK, map[string]interface{}{
		"status":    status,
		"provider":  integration.Provider,
		"scopes":    integration.Scopes,
		"expiresAt": integration.ExpiresAt,
	})
}

// OAuth URL generators
func (h *IntegrationHandler) getSlackAuthURL(state string) string {
	return "https://slack.com/oauth/v2/authorize?" +
		"client_id=" + h.cfg.SlackClientID +
		"&scope=channels:history,channels:read,chat:write,reactions:write,users:read" +
		"&redirect_uri=" + h.cfg.FrontendURL + "/api/v1/integrations/slack/callback" +
		"&state=" + state
}

func (h *IntegrationHandler) getGitHubIntegrationAuthURL(state string) string {
	return "https://github.com/login/oauth/authorize?" +
		"client_id=" + h.cfg.GitHubClientID +
		"&scope=repo,read:org" +
		"&redirect_uri=" + h.cfg.FrontendURL + "/api/v1/integrations/github/callback" +
		"&state=" + state
}

func (h *IntegrationHandler) getJiraAuthURL(state string) string {
	return "https://auth.atlassian.com/authorize?" +
		"audience=api.atlassian.com" +
		"&client_id=" + h.cfg.JiraClientID +
		"&scope=read:jira-work%20write:jira-work%20read:jira-user%20offline_access" +
		"&redirect_uri=" + h.cfg.FrontendURL + "/api/v1/integrations/jira/callback" +
		"&state=" + state +
		"&response_type=code" +
		"&prompt=consent"
}

func (h *IntegrationHandler) getConfluenceAuthURL(state string) string {
	return "https://auth.atlassian.com/authorize?" +
		"audience=api.atlassian.com" +
		"&client_id=" + h.cfg.JiraClientID + // Atlassian uses same app for Jira/Confluence
		"&scope=read:confluence-content.all%20write:confluence-content%20offline_access" +
		"&redirect_uri=" + h.cfg.FrontendURL + "/api/v1/integrations/confluence/callback" +
		"&state=" + state +
		"&response_type=code" +
		"&prompt=consent"
}

// Callback handlers - these would exchange codes for tokens
import (
	"context"
	"time"
)

func (h *IntegrationHandler) handleSlackCallback(ctx context.Context, agentID uuid.UUID, code string) error {
	// Exchange code for token using Slack API
	// Store integration in database
	return nil
}

func (h *IntegrationHandler) handleGitHubIntegrationCallback(ctx context.Context, agentID uuid.UUID, code string) error {
	// Exchange code for token using GitHub API
	// Store integration in database
	return nil
}

func (h *IntegrationHandler) handleJiraCallback(ctx context.Context, agentID uuid.UUID, code string) error {
	// Exchange code for token using Atlassian API
	// Store integration in database
	return nil
}

func (h *IntegrationHandler) handleConfluenceCallback(ctx context.Context, agentID uuid.UUID, code string) error {
	// Exchange code for token using Atlassian API
	// Store integration in database
	return nil
}
