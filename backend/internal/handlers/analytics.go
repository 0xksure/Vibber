package handlers

import (
	"net/http"
	"strconv"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"

	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/repository"
	"github.com/vibber/backend/pkg/response"
)

type AnalyticsHandler struct {
	repos *repository.Repositories
	redis *redis.Client
	cfg   *config.Config
}

func NewAnalyticsHandler(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *AnalyticsHandler {
	return &AnalyticsHandler{
		repos: repos,
		redis: redis,
		cfg:   cfg,
	}
}

func (h *AnalyticsHandler) Overview(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)
	agentIDStr := r.URL.Query().Get("agent_id")

	if agentIDStr != "" {
		// Get metrics for specific agent
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

		metrics, err := h.repos.Interaction.GetOverviewMetrics(r.Context(), agentID)
		if err != nil {
			response.Error(w, http.StatusInternalServerError, "Failed to fetch metrics")
			return
		}

		response.JSON(w, http.StatusOK, metrics)
		return
	}

	// Aggregate metrics across all user's agents
	agents, _ := h.repos.Agent.ListByUserID(r.Context(), userID)

	aggregated := &struct {
		TotalInteractions  int                `json:"totalInteractions"`
		TodayInteractions  int                `json:"todayInteractions"`
		AutonomousRate     float64            `json:"autonomousRate"`
		PendingEscalations int                `json:"pendingEscalations"`
		AvgConfidenceScore float64            `json:"avgConfidenceScore"`
		AgentMetrics       []agentMetricsSummary `json:"agentMetrics"`
	}{
		AgentMetrics: make([]agentMetricsSummary, 0),
	}

	var totalConfidence float64
	var agentCount int

	for _, agent := range agents {
		metrics, _ := h.repos.Interaction.GetOverviewMetrics(r.Context(), agent.ID)
		if metrics != nil {
			aggregated.TotalInteractions += metrics.TotalInteractions
			aggregated.TodayInteractions += metrics.TodayInteractions
			aggregated.PendingEscalations += metrics.PendingEscalations
			totalConfidence += metrics.AvgConfidenceScore
			agentCount++

			aggregated.AgentMetrics = append(aggregated.AgentMetrics, agentMetricsSummary{
				AgentID:           agent.ID.String(),
				AgentName:         agent.Name,
				TotalInteractions: metrics.TotalInteractions,
				TodayInteractions: metrics.TodayInteractions,
				AutonomousRate:    metrics.AutonomousRate,
				ConfidenceScore:   metrics.AvgConfidenceScore,
			})
		}
	}

	if agentCount > 0 {
		aggregated.AvgConfidenceScore = totalConfidence / float64(agentCount)
	}

	// Calculate overall autonomous rate
	if aggregated.TotalInteractions > 0 {
		var totalEscalated int
		for _, m := range aggregated.AgentMetrics {
			totalEscalated += int(float64(m.TotalInteractions) * (100 - m.AutonomousRate) / 100)
		}
		aggregated.AutonomousRate = float64(aggregated.TotalInteractions-totalEscalated) / float64(aggregated.TotalInteractions) * 100
	}

	response.JSON(w, http.StatusOK, aggregated)
}

type agentMetricsSummary struct {
	AgentID           string  `json:"agentId"`
	AgentName         string  `json:"agentName"`
	TotalInteractions int     `json:"totalInteractions"`
	TodayInteractions int     `json:"todayInteractions"`
	AutonomousRate    float64 `json:"autonomousRate"`
	ConfidenceScore   float64 `json:"confidenceScore"`
}

func (h *AnalyticsHandler) Trends(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)
	agentIDStr := r.URL.Query().Get("agent_id")
	daysStr := r.URL.Query().Get("days")

	days := 30 // Default to 30 days
	if daysStr != "" {
		if d, err := strconv.Atoi(daysStr); err == nil && d > 0 && d <= 90 {
			days = d
		}
	}

	if agentIDStr != "" {
		// Get trends for specific agent
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

		trends, err := h.repos.Interaction.GetTrends(r.Context(), agentID, days)
		if err != nil {
			response.Error(w, http.StatusInternalServerError, "Failed to fetch trends")
			return
		}

		response.JSON(w, http.StatusOK, trends)
		return
	}

	// Aggregate trends across all agents
	agents, _ := h.repos.Agent.ListByUserID(r.Context(), userID)

	// This would aggregate daily data across all agents
	// For simplicity, returning first agent's trends or empty
	if len(agents) > 0 {
		trends, _ := h.repos.Interaction.GetTrends(r.Context(), agents[0].ID, days)
		response.JSON(w, http.StatusOK, trends)
		return
	}

	response.JSON(w, http.StatusOK, []interface{}{})
}

func (h *AnalyticsHandler) Performance(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)
	agentIDStr := r.URL.Query().Get("agent_id")

	type providerPerformance struct {
		Provider          string  `json:"provider"`
		TotalInteractions int     `json:"totalInteractions"`
		SuccessRate       float64 `json:"successRate"`
		AvgConfidence     float64 `json:"avgConfidence"`
		AvgResponseTime   float64 `json:"avgResponseTime"`
	}

	performance := make([]providerPerformance, 0)

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

		// Get performance by provider
		// This would query the database grouped by provider
		// For now, returning mock data structure
		integrations, _ := h.repos.Integration.ListByAgentID(r.Context(), agentID)
		for _, integration := range integrations {
			performance = append(performance, providerPerformance{
				Provider:          integration.Provider,
				TotalInteractions: 0,
				SuccessRate:       0,
				AvgConfidence:     0,
				AvgResponseTime:   0,
			})
		}
	}

	response.JSON(w, http.StatusOK, performance)
}
