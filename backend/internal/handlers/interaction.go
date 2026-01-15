package handlers

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"

	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/models"
	"github.com/vibber/backend/internal/repository"
	"github.com/vibber/backend/pkg/response"
)

type InteractionHandler struct {
	repos *repository.Repositories
	redis *redis.Client
	cfg   *config.Config
}

func NewInteractionHandler(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *InteractionHandler {
	return &InteractionHandler{
		repos: repos,
		redis: redis,
		cfg:   cfg,
	}
}

func (h *InteractionHandler) List(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)
	agentIDStr := r.URL.Query().Get("agent_id")
	pageStr := r.URL.Query().Get("page")
	pageSizeStr := r.URL.Query().Get("page_size")
	provider := r.URL.Query().Get("provider")
	status := r.URL.Query().Get("status")

	page := 1
	pageSize := 20

	if p, err := strconv.Atoi(pageStr); err == nil && p > 0 {
		page = p
	}
	if ps, err := strconv.Atoi(pageSizeStr); err == nil && ps > 0 && ps <= 100 {
		pageSize = ps
	}

	params := models.PaginationParams{
		Page:     page,
		PageSize: pageSize,
	}

	var allInteractions []*models.Interaction
	var totalCount int

	if agentIDStr != "" {
		agentID, err := uuid.Parse(agentIDStr)
		if err != nil {
			response.Error(w, http.StatusBadRequest, "Invalid agent ID")
			return
		}

		// Verify ownership
		agent, err := h.repos.Agent.GetByID(r.Context(), agentID)
		if err != nil || agent.UserID != userID {
			response.Error(w, http.StatusForbidden, "Access denied")
			return
		}

		interactions, total, err := h.repos.Interaction.ListByAgentID(r.Context(), agentID, params)
		if err != nil {
			response.Error(w, http.StatusInternalServerError, "Failed to fetch interactions")
			return
		}
		allInteractions = interactions
		totalCount = total
	} else {
		// Get interactions for all user's agents
		agents, _ := h.repos.Agent.ListByUserID(r.Context(), userID)
		for _, agent := range agents {
			interactions, _, _ := h.repos.Interaction.ListByAgentID(r.Context(), agent.ID, params)
			allInteractions = append(allInteractions, interactions...)
		}
		totalCount = len(allInteractions)
	}

	// Filter by provider if specified
	if provider != "" {
		filtered := make([]*models.Interaction, 0)
		for _, i := range allInteractions {
			if i.Provider == provider {
				filtered = append(filtered, i)
			}
		}
		allInteractions = filtered
		totalCount = len(filtered)
	}

	// Filter by status if specified
	if status != "" {
		filtered := make([]*models.Interaction, 0)
		for _, i := range allInteractions {
			if i.Status == status {
				filtered = append(filtered, i)
			}
		}
		allInteractions = filtered
		totalCount = len(filtered)
	}

	response.Paginated(w, allInteractions, page, pageSize, totalCount)
}

func (h *InteractionHandler) Get(w http.ResponseWriter, r *http.Request) {
	interactionID, err := uuid.Parse(chi.URLParam(r, "interactionID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid interaction ID")
		return
	}

	interaction, err := h.repos.Interaction.GetByID(r.Context(), interactionID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Interaction not found")
		return
	}

	// Verify ownership through agent
	userID := r.Context().Value("userID").(uuid.UUID)
	agent, _ := h.repos.Agent.GetByID(r.Context(), interaction.AgentID)
	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	// Get related escalation if exists
	var escalation interface{}
	if interaction.Escalated {
		// Would need a method to get escalation by interaction ID
	}

	response.JSON(w, http.StatusOK, map[string]interface{}{
		"interaction": interaction,
		"agent":       agent,
		"escalation":  escalation,
	})
}

func (h *InteractionHandler) Feedback(w http.ResponseWriter, r *http.Request) {
	interactionID, err := uuid.Parse(chi.URLParam(r, "interactionID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid interaction ID")
		return
	}

	interaction, err := h.repos.Interaction.GetByID(r.Context(), interactionID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Interaction not found")
		return
	}

	// Verify ownership through agent
	userID := r.Context().Value("userID").(uuid.UUID)
	agent, _ := h.repos.Agent.GetByID(r.Context(), interaction.AgentID)
	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	var req models.FeedbackRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Update interaction with feedback
	interaction.HumanFeedback = &req.Feedback
	if err := h.repos.Interaction.Update(r.Context(), interaction); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to update feedback")
		return
	}

	// If correction provided, create training sample
	if req.Correction != "" {
		sample := &models.TrainingSample{
			ID:         uuid.New(),
			AgentID:    agent.ID,
			Provider:   &interaction.Provider,
			SampleType: "correction",
			InputText:  interaction.InputData,
			OutputText: &req.Correction,
			IsPositive: true,
		}
		h.repos.Training.Create(r.Context(), sample)
	}

	// If rejected, also create negative sample
	if req.Feedback == "rejected" && interaction.OutputData != nil {
		sample := &models.TrainingSample{
			ID:         uuid.New(),
			AgentID:    agent.ID,
			Provider:   &interaction.Provider,
			SampleType: "negative",
			InputText:  interaction.InputData,
			OutputText: interaction.OutputData,
			IsPositive: false,
		}
		h.repos.Training.Create(r.Context(), sample)
	}

	response.JSON(w, http.StatusOK, map[string]string{"message": "Feedback recorded"})
}
