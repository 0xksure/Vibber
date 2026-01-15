package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"

	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/repository"
	"github.com/vibber/backend/pkg/response"
)

type OrganizationHandler struct {
	repos *repository.Repositories
	redis *redis.Client
	cfg   *config.Config
}

func NewOrganizationHandler(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *OrganizationHandler {
	return &OrganizationHandler{
		repos: repos,
		redis: redis,
		cfg:   cfg,
	}
}

func (h *OrganizationHandler) Get(w http.ResponseWriter, r *http.Request) {
	orgID := r.Context().Value("orgID").(uuid.UUID)

	org, err := h.repos.Organization.GetByID(r.Context(), orgID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Organization not found")
		return
	}

	// Get member count
	members, _ := h.repos.User.ListByOrgID(r.Context(), orgID)

	response.JSON(w, http.StatusOK, map[string]interface{}{
		"organization": org,
		"memberCount":  len(members),
	})
}

func (h *OrganizationHandler) Update(w http.ResponseWriter, r *http.Request) {
	orgID := r.Context().Value("orgID").(uuid.UUID)
	userRole := r.Context().Value("userRole").(string)

	// Only admins can update organization
	if userRole != "admin" {
		response.Error(w, http.StatusForbidden, "Admin access required")
		return
	}

	org, err := h.repos.Organization.GetByID(r.Context(), orgID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Organization not found")
		return
	}

	var req struct {
		Name string `json:"name"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	if req.Name != "" {
		org.Name = req.Name
	}

	if err := h.repos.Organization.Update(r.Context(), org); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to update organization")
		return
	}

	response.JSON(w, http.StatusOK, org)
}

func (h *OrganizationHandler) ListMembers(w http.ResponseWriter, r *http.Request) {
	orgID := r.Context().Value("orgID").(uuid.UUID)

	members, err := h.repos.User.ListByOrgID(r.Context(), orgID)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to fetch members")
		return
	}

	response.JSON(w, http.StatusOK, members)
}

func (h *OrganizationHandler) InviteMember(w http.ResponseWriter, r *http.Request) {
	orgID := r.Context().Value("orgID").(uuid.UUID)
	userRole := r.Context().Value("userRole").(string)

	// Only admins can invite members
	if userRole != "admin" {
		response.Error(w, http.StatusForbidden, "Admin access required")
		return
	}

	var req struct {
		Email string `json:"email"`
		Role  string `json:"role"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Check if user already exists
	existing, _ := h.repos.User.GetByEmail(r.Context(), req.Email)
	if existing != nil {
		response.Error(w, http.StatusConflict, "User already exists")
		return
	}

	// In production, this would send an invitation email
	// For now, just return success
	response.JSON(w, http.StatusOK, map[string]interface{}{
		"message": "Invitation sent",
		"email":   req.Email,
		"orgId":   orgID,
	})
}
