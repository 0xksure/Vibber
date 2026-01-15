package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"

	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/models"
	"github.com/vibber/backend/internal/repository"
	"github.com/vibber/backend/pkg/response"
)

type CredentialsHandler struct {
	repos *repository.Repositories
	redis *redis.Client
	cfg   *config.Config
}

func NewCredentialsHandler(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *CredentialsHandler {
	return &CredentialsHandler{
		repos: repos,
		redis: redis,
		cfg:   cfg,
	}
}

// List returns all credentials for the organization (without secrets)
func (h *CredentialsHandler) List(w http.ResponseWriter, r *http.Request) {
	orgID := r.Context().Value("orgID").(uuid.UUID)

	credentials, err := h.repos.Credential.ListByOrgID(r.Context(), orgID)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to fetch credentials")
		return
	}

	// Convert to safe response format
	safeCredentials := make([]models.CredentialResponse, len(credentials))
	for i, cred := range credentials {
		safeCredentials[i] = models.CredentialResponse{
			ID:         cred.ID,
			Provider:   cred.Provider,
			ClientID:   cred.ClientID,
			HasSecret:  cred.ClientSecret != "",
			Config:     cred.Config,
			IsActive:   cred.IsActive,
			VerifiedAt: cred.VerifiedAt,
			CreatedAt:  cred.CreatedAt,
			UpdatedAt:  cred.UpdatedAt,
		}
	}

	response.JSON(w, http.StatusOK, safeCredentials)
}

// Create adds new credentials for a provider
func (h *CredentialsHandler) Create(w http.ResponseWriter, r *http.Request) {
	orgID := r.Context().Value("orgID").(uuid.UUID)
	userID := r.Context().Value("userID").(uuid.UUID)

	var req models.CreateCredentialRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Check if credentials already exist for this provider
	existing, _ := h.repos.Credential.GetByOrgAndProvider(r.Context(), orgID, req.Provider)
	if existing != nil {
		response.Error(w, http.StatusConflict, "Credentials already exist for this provider. Use PUT to update.")
		return
	}

	credential := &models.OrganizationCredential{
		ID:            uuid.New(),
		OrgID:         orgID,
		Provider:      req.Provider,
		ClientID:      req.ClientID,
		ClientSecret:  req.ClientSecret, // Should be encrypted at storage level
		WebhookSecret: req.WebhookSecret,
		SigningSecret: req.SigningSecret,
		Config:        req.Config,
		IsActive:      true,
		CreatedBy:     &userID,
	}

	if err := h.repos.Credential.Create(r.Context(), credential); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to create credentials")
		return
	}

	// Return safe response
	response.JSON(w, http.StatusCreated, models.CredentialResponse{
		ID:         credential.ID,
		Provider:   credential.Provider,
		ClientID:   credential.ClientID,
		HasSecret:  true,
		Config:     credential.Config,
		IsActive:   credential.IsActive,
		VerifiedAt: credential.VerifiedAt,
		CreatedAt:  credential.CreatedAt,
		UpdatedAt:  credential.UpdatedAt,
	})
}

// Get returns credentials for a specific provider (without secrets)
func (h *CredentialsHandler) Get(w http.ResponseWriter, r *http.Request) {
	orgID := r.Context().Value("orgID").(uuid.UUID)
	provider := chi.URLParam(r, "provider")

	credential, err := h.repos.Credential.GetByOrgAndProvider(r.Context(), orgID, provider)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Credentials not found")
		return
	}

	response.JSON(w, http.StatusOK, models.CredentialResponse{
		ID:         credential.ID,
		Provider:   credential.Provider,
		ClientID:   credential.ClientID,
		HasSecret:  credential.ClientSecret != "",
		Config:     credential.Config,
		IsActive:   credential.IsActive,
		VerifiedAt: credential.VerifiedAt,
		CreatedAt:  credential.CreatedAt,
		UpdatedAt:  credential.UpdatedAt,
	})
}

// Update modifies existing credentials
func (h *CredentialsHandler) Update(w http.ResponseWriter, r *http.Request) {
	orgID := r.Context().Value("orgID").(uuid.UUID)
	provider := chi.URLParam(r, "provider")

	credential, err := h.repos.Credential.GetByOrgAndProvider(r.Context(), orgID, provider)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Credentials not found")
		return
	}

	var req models.UpdateCredentialRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Update fields if provided
	if req.ClientID != nil {
		credential.ClientID = *req.ClientID
	}
	if req.ClientSecret != nil {
		credential.ClientSecret = *req.ClientSecret
	}
	if req.WebhookSecret != nil {
		credential.WebhookSecret = req.WebhookSecret
	}
	if req.SigningSecret != nil {
		credential.SigningSecret = req.SigningSecret
	}
	if req.Config != nil {
		credential.Config = req.Config
	}
	if req.IsActive != nil {
		credential.IsActive = *req.IsActive
	}

	// Reset verification status when credentials change
	if req.ClientID != nil || req.ClientSecret != nil {
		credential.VerifiedAt = nil
	}

	if err := h.repos.Credential.Update(r.Context(), credential); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to update credentials")
		return
	}

	response.JSON(w, http.StatusOK, models.CredentialResponse{
		ID:         credential.ID,
		Provider:   credential.Provider,
		ClientID:   credential.ClientID,
		HasSecret:  credential.ClientSecret != "",
		Config:     credential.Config,
		IsActive:   credential.IsActive,
		VerifiedAt: credential.VerifiedAt,
		CreatedAt:  credential.CreatedAt,
		UpdatedAt:  credential.UpdatedAt,
	})
}

// Delete removes credentials for a provider
func (h *CredentialsHandler) Delete(w http.ResponseWriter, r *http.Request) {
	orgID := r.Context().Value("orgID").(uuid.UUID)
	provider := chi.URLParam(r, "provider")

	credential, err := h.repos.Credential.GetByOrgAndProvider(r.Context(), orgID, provider)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Credentials not found")
		return
	}

	if err := h.repos.Credential.Delete(r.Context(), credential.ID); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to delete credentials")
		return
	}

	response.JSON(w, http.StatusOK, map[string]string{"message": "Credentials deleted"})
}

// Verify tests the credentials with the provider
func (h *CredentialsHandler) Verify(w http.ResponseWriter, r *http.Request) {
	orgID := r.Context().Value("orgID").(uuid.UUID)
	provider := chi.URLParam(r, "provider")

	credential, err := h.repos.Credential.GetByOrgAndProvider(r.Context(), orgID, provider)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Credentials not found")
		return
	}

	// Verify credentials with the provider's API
	verified, verifyErr := h.verifyWithProvider(credential)
	if verifyErr != nil {
		response.Error(w, http.StatusBadRequest, "Credential verification failed: "+verifyErr.Error())
		return
	}

	if verified {
		// Update verification timestamp
		if err := h.repos.Credential.MarkVerified(r.Context(), credential.ID); err != nil {
			response.Error(w, http.StatusInternalServerError, "Failed to update verification status")
			return
		}
	}

	response.JSON(w, http.StatusOK, map[string]interface{}{
		"verified": verified,
		"provider": provider,
	})
}

// GetForAgent returns full credentials for the AI agent (internal use)
// This endpoint should only be accessible from the AI agent service
func (h *CredentialsHandler) GetForAgent(w http.ResponseWriter, r *http.Request) {
	// Verify internal service authentication
	serviceKey := r.Header.Get("X-Service-Key")
	if serviceKey != h.cfg.InternalServiceKey {
		response.Error(w, http.StatusUnauthorized, "Invalid service key")
		return
	}

	orgIDStr := r.URL.Query().Get("org_id")
	provider := r.URL.Query().Get("provider")

	if orgIDStr == "" || provider == "" {
		response.Error(w, http.StatusBadRequest, "org_id and provider are required")
		return
	}

	orgID, err := uuid.Parse(orgIDStr)
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid org_id")
		return
	}

	credential, err := h.repos.Credential.GetByOrgAndProvider(r.Context(), orgID, provider)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Credentials not found")
		return
	}

	if !credential.IsActive {
		response.Error(w, http.StatusForbidden, "Credentials are not active")
		return
	}

	// Return full credentials for agent use
	response.JSON(w, http.StatusOK, models.CredentialForAgent{
		Provider:      credential.Provider,
		ClientID:      credential.ClientID,
		ClientSecret:  credential.ClientSecret,
		WebhookSecret: credential.WebhookSecret,
		SigningSecret: credential.SigningSecret,
		Config:        credential.Config,
	})
}

// verifyWithProvider tests credentials against the provider's API
func (h *CredentialsHandler) verifyWithProvider(cred *models.OrganizationCredential) (bool, error) {
	// Implementation would make API calls to verify credentials
	// For now, return true (actual implementation would depend on each provider)
	switch cred.Provider {
	case "slack":
		// Call Slack's auth.test API
		return true, nil
	case "github":
		// Call GitHub's /user API
		return true, nil
	case "jira":
		// Call Jira's /rest/api/3/myself API
		return true, nil
	default:
		return true, nil
	}
}
