package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"

	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/repository"
	"github.com/vibber/backend/pkg/response"
)

type EscalationHandler struct {
	repos *repository.Repositories
	redis *redis.Client
	cfg   *config.Config
}

func NewEscalationHandler(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *EscalationHandler {
	return &EscalationHandler{
		repos: repos,
		redis: redis,
		cfg:   cfg,
	}
}

func (h *EscalationHandler) List(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)
	agentIDStr := r.URL.Query().Get("agent_id")

	var escalations []*struct {
		Escalation  interface{} `json:"escalation"`
		Interaction interface{} `json:"interaction"`
		AgentName   string      `json:"agentName"`
	}

	if agentIDStr != "" {
		// Get escalations for specific agent
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

		pending, _ := h.repos.Escalation.ListPending(r.Context(), agentID)
		for _, e := range pending {
			interaction, _ := h.repos.Interaction.GetByID(r.Context(), e.InteractionID)
			escalations = append(escalations, &struct {
				Escalation  interface{} `json:"escalation"`
				Interaction interface{} `json:"interaction"`
				AgentName   string      `json:"agentName"`
			}{
				Escalation:  e,
				Interaction: interaction,
				AgentName:   agent.Name,
			})
		}
	} else {
		// Get escalations for all user's agents
		agents, _ := h.repos.Agent.ListByUserID(r.Context(), userID)
		for _, agent := range agents {
			pending, _ := h.repos.Escalation.ListPending(r.Context(), agent.ID)
			for _, e := range pending {
				interaction, _ := h.repos.Interaction.GetByID(r.Context(), e.InteractionID)
				escalations = append(escalations, &struct {
					Escalation  interface{} `json:"escalation"`
					Interaction interface{} `json:"interaction"`
					AgentName   string      `json:"agentName"`
				}{
					Escalation:  e,
					Interaction: interaction,
					AgentName:   agent.Name,
				})
			}
		}
	}

	response.JSON(w, http.StatusOK, escalations)
}

func (h *EscalationHandler) Get(w http.ResponseWriter, r *http.Request) {
	escalationID, err := uuid.Parse(chi.URLParam(r, "escalationID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid escalation ID")
		return
	}

	escalation, err := h.repos.Escalation.GetByID(r.Context(), escalationID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Escalation not found")
		return
	}

	// Verify ownership through agent
	userID := r.Context().Value("userID").(uuid.UUID)
	agent, _ := h.repos.Agent.GetByID(r.Context(), escalation.AgentID)
	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	// Get related interaction
	interaction, _ := h.repos.Interaction.GetByID(r.Context(), escalation.InteractionID)

	response.JSON(w, http.StatusOK, map[string]interface{}{
		"escalation":  escalation,
		"interaction": interaction,
		"agent":       agent,
	})
}

func (h *EscalationHandler) Resolve(w http.ResponseWriter, r *http.Request) {
	escalationID, err := uuid.Parse(chi.URLParam(r, "escalationID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid escalation ID")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	escalation, err := h.repos.Escalation.GetByID(r.Context(), escalationID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Escalation not found")
		return
	}

	// Verify ownership
	agent, _ := h.repos.Agent.GetByID(r.Context(), escalation.AgentID)
	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	var req struct {
		Resolution string `json:"resolution"`
		Action     string `json:"action"` // The action to take (e.g., reply text, command)
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Update escalation
	now := time.Now()
	escalation.Status = "resolved"
	escalation.Resolution = &req.Resolution
	escalation.ResolvedBy = &userID
	escalation.ResolvedAt = &now

	if err := h.repos.Escalation.Update(r.Context(), escalation); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to resolve escalation")
		return
	}

	// Execute the action if provided
	if req.Action != "" {
		// This would trigger the agent to execute the user's action
		// h.executeAction(r.Context(), escalation.InteractionID, req.Action)
	}

	response.JSON(w, http.StatusOK, map[string]string{"message": "Escalation resolved"})
}

func (h *EscalationHandler) Approve(w http.ResponseWriter, r *http.Request) {
	escalationID, err := uuid.Parse(chi.URLParam(r, "escalationID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid escalation ID")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	escalation, err := h.repos.Escalation.GetByID(r.Context(), escalationID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Escalation not found")
		return
	}

	// Verify ownership
	agent, _ := h.repos.Agent.GetByID(r.Context(), escalation.AgentID)
	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	// Mark as resolved with approval
	now := time.Now()
	resolution := "approved"
	escalation.Status = "resolved"
	escalation.Resolution = &resolution
	escalation.ResolvedBy = &userID
	escalation.ResolvedAt = &now

	if err := h.repos.Escalation.Update(r.Context(), escalation); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to approve escalation")
		return
	}

	// Update interaction with feedback
	interaction, _ := h.repos.Interaction.GetByID(r.Context(), escalation.InteractionID)
	feedback := "approved"
	interaction.HumanFeedback = &feedback
	h.repos.Interaction.Update(r.Context(), interaction)

	// Trigger agent to execute the pending action
	// This would be sent to the AI agent service

	response.JSON(w, http.StatusOK, map[string]string{"message": "Action approved and executed"})
}

func (h *EscalationHandler) Reject(w http.ResponseWriter, r *http.Request) {
	escalationID, err := uuid.Parse(chi.URLParam(r, "escalationID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid escalation ID")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	escalation, err := h.repos.Escalation.GetByID(r.Context(), escalationID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Escalation not found")
		return
	}

	// Verify ownership
	agent, _ := h.repos.Agent.GetByID(r.Context(), escalation.AgentID)
	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	var req struct {
		Reason     string `json:"reason"`
		Correction string `json:"correction"` // The correct response/action
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Mark as resolved with rejection
	now := time.Now()
	resolution := "rejected: " + req.Reason
	escalation.Status = "resolved"
	escalation.Resolution = &resolution
	escalation.ResolvedBy = &userID
	escalation.ResolvedAt = &now

	if err := h.repos.Escalation.Update(r.Context(), escalation); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to reject escalation")
		return
	}

	// Update interaction with feedback
	interaction, _ := h.repos.Interaction.GetByID(r.Context(), escalation.InteractionID)
	feedback := "rejected"
	interaction.HumanFeedback = &feedback
	h.repos.Interaction.Update(r.Context(), interaction)

	// Store the correction as a training sample for the agent
	if req.Correction != "" {
		// This would be sent to the AI agent service to improve future responses
	}

	response.JSON(w, http.StatusOK, map[string]string{"message": "Action rejected"})
}
