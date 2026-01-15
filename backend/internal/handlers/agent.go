package handlers

import (
	"bytes"
	"context"
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

type AgentHandler struct {
	repos *repository.Repositories
	redis *redis.Client
	cfg   *config.Config
}

func NewAgentHandler(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *AgentHandler {
	return &AgentHandler{
		repos: repos,
		redis: redis,
		cfg:   cfg,
	}
}

func (h *AgentHandler) List(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)

	agents, err := h.repos.Agent.ListByUserID(r.Context(), userID)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to fetch agents")
		return
	}

	response.JSON(w, http.StatusOK, agents)
}

func (h *AgentHandler) Create(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)

	var req models.CreateAgentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Default confidence threshold
	if req.ConfidenceThreshold == 0 {
		req.ConfidenceThreshold = 70
	}

	agent := &models.Agent{
		ID:                  uuid.New(),
		UserID:              userID,
		Name:                req.Name,
		Status:              "training",
		ConfidenceThreshold: req.ConfidenceThreshold,
		AutoMode:            false,
	}

	if req.Description != "" {
		agent.Description = &req.Description
	}

	if err := h.repos.Agent.Create(r.Context(), agent); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to create agent")
		return
	}

	response.JSON(w, http.StatusCreated, agent)
}

func (h *AgentHandler) Get(w http.ResponseWriter, r *http.Request) {
	agentID, err := uuid.Parse(chi.URLParam(r, "agentID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid agent ID")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	agent, err := h.repos.Agent.GetByID(r.Context(), agentID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Agent not found")
		return
	}

	// Verify ownership
	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	response.JSON(w, http.StatusOK, agent)
}

func (h *AgentHandler) Update(w http.ResponseWriter, r *http.Request) {
	agentID, err := uuid.Parse(chi.URLParam(r, "agentID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid agent ID")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	// Verify ownership
	agent, err := h.repos.Agent.GetByID(r.Context(), agentID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Agent not found")
		return
	}

	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	var req models.UpdateAgentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Update fields
	if req.Name != nil {
		agent.Name = *req.Name
	}
	if req.Description != nil {
		agent.Description = req.Description
	}
	if req.ConfidenceThreshold != nil {
		agent.ConfidenceThreshold = *req.ConfidenceThreshold
	}
	if req.AutoMode != nil {
		agent.AutoMode = *req.AutoMode
	}
	if req.WorkingHours != nil {
		agent.WorkingHours = req.WorkingHours
	}

	if err := h.repos.Agent.Update(r.Context(), agent); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to update agent")
		return
	}

	response.JSON(w, http.StatusOK, agent)
}

func (h *AgentHandler) Delete(w http.ResponseWriter, r *http.Request) {
	agentID, err := uuid.Parse(chi.URLParam(r, "agentID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid agent ID")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	// Verify ownership
	agent, err := h.repos.Agent.GetByID(r.Context(), agentID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Agent not found")
		return
	}

	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	if err := h.repos.Agent.Delete(r.Context(), agentID); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to delete agent")
		return
	}

	response.JSON(w, http.StatusOK, map[string]string{"message": "Agent deleted successfully"})
}

func (h *AgentHandler) Train(w http.ResponseWriter, r *http.Request) {
	agentID, err := uuid.Parse(chi.URLParam(r, "agentID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid agent ID")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	// Verify ownership
	agent, err := h.repos.Agent.GetByID(r.Context(), agentID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Agent not found")
		return
	}

	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	// Trigger training via AI service
	if err := h.triggerTraining(r.Context(), agent); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to start training")
		return
	}

	// Update status
	agent.Status = "training"
	h.repos.Agent.Update(r.Context(), agent)

	response.JSON(w, http.StatusAccepted, map[string]string{
		"message": "Training started",
		"status":  "training",
	})
}

func (h *AgentHandler) Status(w http.ResponseWriter, r *http.Request) {
	agentID, err := uuid.Parse(chi.URLParam(r, "agentID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid agent ID")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	// Verify ownership
	agent, err := h.repos.Agent.GetByID(r.Context(), agentID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Agent not found")
		return
	}

	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	// Get status from various sources
	status, err := h.getAgentStatus(r.Context(), agentID)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to get agent status")
		return
	}

	response.JSON(w, http.StatusOK, status)
}

func (h *AgentHandler) UpdateSettings(w http.ResponseWriter, r *http.Request) {
	agentID, err := uuid.Parse(chi.URLParam(r, "agentID"))
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid agent ID")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	// Verify ownership
	agent, err := h.repos.Agent.GetByID(r.Context(), agentID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "Agent not found")
		return
	}

	if agent.UserID != userID {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	var settings map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&settings); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Update settings in AI service
	if err := h.updateAgentSettings(r.Context(), agentID, settings); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to update settings")
		return
	}

	response.JSON(w, http.StatusOK, map[string]string{"message": "Settings updated"})
}

func (h *AgentHandler) triggerTraining(ctx context.Context, agent *models.Agent) error {
	payload, _ := json.Marshal(map[string]interface{}{
		"agent_id": agent.ID.String(),
		"user_id":  agent.UserID.String(),
	})

	req, err := http.NewRequestWithContext(ctx, "POST", h.cfg.AgentServiceURL+"/api/v1/train", bytes.NewBuffer(payload))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	return nil
}

func (h *AgentHandler) getAgentStatus(ctx context.Context, agentID uuid.UUID) (*models.AgentStatus, error) {
	// Get interaction counts
	todayCount, _ := h.repos.Interaction.CountToday(ctx, agentID)
	pendingEscalations, _ := h.repos.Escalation.CountPending(ctx, agentID)

	// Get agent
	agent, _ := h.repos.Agent.GetByID(ctx, agentID)

	return &models.AgentStatus{
		Status:             agent.Status,
		IsActive:           agent.Status == "active",
		TodayInteractions:  todayCount,
		PendingEscalations: pendingEscalations,
		ConfidenceScore:    85.5, // Would be calculated from recent interactions
	}, nil
}

func (h *AgentHandler) updateAgentSettings(ctx context.Context, agentID uuid.UUID, settings map[string]interface{}) error {
	settings["agent_id"] = agentID.String()
	payload, _ := json.Marshal(settings)

	req, err := http.NewRequestWithContext(ctx, "PUT", h.cfg.AgentServiceURL+"/api/v1/agents/"+agentID.String()+"/settings", bytes.NewBuffer(payload))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	return nil
}
