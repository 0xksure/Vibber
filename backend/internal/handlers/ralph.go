package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"

	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/models"
	"github.com/vibber/backend/internal/repository"
	"github.com/vibber/backend/pkg/response"
)

// RalphHandler handles Ralph Wiggum iterative task execution
type RalphHandler struct {
	repos *repository.Repositories
	redis *redis.Client
	cfg   *config.Config
}

// NewRalphHandler creates a new Ralph handler
func NewRalphHandler(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *RalphHandler {
	return &RalphHandler{
		repos: repos,
		redis: redis,
		cfg:   cfg,
	}
}

// CreateTaskRequest represents a request to create a Ralph task
type CreateTaskRequest struct {
	Prompt           string  `json:"prompt"`
	Description      string  `json:"description,omitempty"`
	CompletionPromise *string `json:"completion_promise,omitempty"`
	MaxIterations    *int    `json:"max_iterations,omitempty"`
	WorkingDirectory *string `json:"working_directory,omitempty"`
	RunTests         *bool   `json:"run_tests,omitempty"`
	TestCommand      *string `json:"test_command,omitempty"`
	RunLint          *bool   `json:"run_lint,omitempty"`
	LintCommand      *string `json:"lint_command,omitempty"`
	RunTypecheck     *bool   `json:"run_typecheck,omitempty"`
	TypecheckCommand *string `json:"typecheck_command,omitempty"`
	Model            *string `json:"model,omitempty"`
}

// TaskResponse represents a Ralph task response
type TaskResponse struct {
	ID               string   `json:"id"`
	Status           string   `json:"status"`
	Message          string   `json:"message,omitempty"`
	PromptPreview    string   `json:"prompt_preview,omitempty"`
	CurrentIteration int      `json:"current_iteration"`
	MaxIterations    int      `json:"max_iterations"`
	DurationSeconds  float64  `json:"duration_seconds"`
	IsComplete       bool     `json:"is_complete"`
	Error            *string  `json:"error,omitempty"`
	FinalOutput      *string  `json:"final_output,omitempty"`
}

// CreateTask creates a new Ralph task for iterative execution
func (h *RalphHandler) CreateTask(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)

	// Get organization ID for the user
	user, err := h.repos.User.GetByID(r.Context(), userID)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to get user")
		return
	}

	var req CreateTaskRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	if len(req.Prompt) < 10 {
		response.Error(w, http.StatusBadRequest, "Prompt must be at least 10 characters")
		return
	}

	// Build request for AI service
	aiReq := map[string]interface{}{
		"prompt":      req.Prompt,
		"description": req.Description,
		"user_id":     userID.String(),
	}

	if user.OrganizationID != nil {
		aiReq["organization_id"] = user.OrganizationID.String()
	}

	if req.CompletionPromise != nil {
		aiReq["completion_promise"] = *req.CompletionPromise
	}
	if req.MaxIterations != nil {
		aiReq["max_iterations"] = *req.MaxIterations
	}
	if req.WorkingDirectory != nil {
		aiReq["working_directory"] = *req.WorkingDirectory
	}
	if req.RunTests != nil {
		aiReq["run_tests"] = *req.RunTests
	}
	if req.TestCommand != nil {
		aiReq["test_command"] = *req.TestCommand
	}
	if req.RunLint != nil {
		aiReq["run_lint"] = *req.RunLint
	}
	if req.LintCommand != nil {
		aiReq["lint_command"] = *req.LintCommand
	}
	if req.RunTypecheck != nil {
		aiReq["run_typecheck"] = *req.RunTypecheck
	}
	if req.TypecheckCommand != nil {
		aiReq["typecheck_command"] = *req.TypecheckCommand
	}
	if req.Model != nil {
		aiReq["model"] = *req.Model
	}

	// Forward to AI service
	result, err := h.forwardToAIService(r.Context(), "POST", "/api/v1/ralph/tasks", aiReq)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, fmt.Sprintf("Failed to create task: %v", err))
		return
	}

	// Store task reference in database for tracking
	taskID := result["id"].(string)
	h.storeTaskReference(r.Context(), userID, taskID, req.Prompt)

	response.JSON(w, http.StatusCreated, result)
}

// GetTask gets the status of a Ralph task
func (h *RalphHandler) GetTask(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")
	if taskID == "" {
		response.Error(w, http.StatusBadRequest, "Task ID required")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	// Verify ownership (check cache)
	if !h.verifyTaskOwnership(r.Context(), userID, taskID) {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	includeIterations := r.URL.Query().Get("include_iterations") == "true"
	endpoint := fmt.Sprintf("/api/v1/ralph/tasks/%s?include_iterations=%v", taskID, includeIterations)

	result, err := h.forwardToAIService(r.Context(), "GET", endpoint, nil)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, fmt.Sprintf("Failed to get task: %v", err))
		return
	}

	response.JSON(w, http.StatusOK, result)
}

// CancelTask cancels a running Ralph task
func (h *RalphHandler) CancelTask(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")
	if taskID == "" {
		response.Error(w, http.StatusBadRequest, "Task ID required")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	// Verify ownership
	if !h.verifyTaskOwnership(r.Context(), userID, taskID) {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	endpoint := fmt.Sprintf("/api/v1/ralph/tasks/%s/cancel", taskID)

	result, err := h.forwardToAIService(r.Context(), "POST", endpoint, nil)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, fmt.Sprintf("Failed to cancel task: %v", err))
		return
	}

	response.JSON(w, http.StatusOK, result)
}

// WaitForTask waits for a task to complete
func (h *RalphHandler) WaitForTask(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")
	if taskID == "" {
		response.Error(w, http.StatusBadRequest, "Task ID required")
		return
	}

	userID := r.Context().Value("userID").(uuid.UUID)

	// Verify ownership
	if !h.verifyTaskOwnership(r.Context(), userID, taskID) {
		response.Error(w, http.StatusForbidden, "Access denied")
		return
	}

	timeout := r.URL.Query().Get("timeout")
	if timeout == "" {
		timeout = "300"
	}

	endpoint := fmt.Sprintf("/api/v1/ralph/tasks/%s/wait?timeout=%s", taskID, timeout)

	result, err := h.forwardToAIService(r.Context(), "GET", endpoint, nil)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, fmt.Sprintf("Failed to wait for task: %v", err))
		return
	}

	response.JSON(w, http.StatusOK, result)
}

// ListTasks lists Ralph tasks for the current user
func (h *RalphHandler) ListTasks(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)

	// Get task IDs from cache
	taskIDs := h.getUserTaskIDs(r.Context(), userID)

	status := r.URL.Query().Get("status")
	limit := r.URL.Query().Get("limit")
	if limit == "" {
		limit = "20"
	}

	endpoint := fmt.Sprintf("/api/v1/ralph/tasks?limit=%s", limit)
	if status != "" {
		endpoint += fmt.Sprintf("&status=%s", status)
	}

	result, err := h.forwardToAIService(r.Context(), "GET", endpoint, nil)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, fmt.Sprintf("Failed to list tasks: %v", err))
		return
	}

	// Filter to only include user's tasks
	if tasks, ok := result["tasks"].([]interface{}); ok {
		filtered := make([]interface{}, 0)
		for _, task := range tasks {
			if taskMap, ok := task.(map[string]interface{}); ok {
				if id, ok := taskMap["id"].(string); ok {
					for _, userTaskID := range taskIDs {
						if id == userTaskID {
							filtered = append(filtered, task)
							break
						}
					}
				}
			}
		}
		result["tasks"] = filtered
		result["total"] = len(filtered)
	}

	response.JSON(w, http.StatusOK, result)
}

// CreateTaskSync creates and runs a task synchronously
func (h *RalphHandler) CreateTaskSync(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)

	// Get organization ID for the user
	user, err := h.repos.User.GetByID(r.Context(), userID)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to get user")
		return
	}

	var req CreateTaskRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	if len(req.Prompt) < 10 {
		response.Error(w, http.StatusBadRequest, "Prompt must be at least 10 characters")
		return
	}

	timeout := r.URL.Query().Get("timeout")
	if timeout == "" {
		timeout = "600"
	}

	// Build request for AI service
	aiReq := map[string]interface{}{
		"prompt":      req.Prompt,
		"description": req.Description,
		"user_id":     userID.String(),
	}

	if user.OrganizationID != nil {
		aiReq["organization_id"] = user.OrganizationID.String()
	}

	if req.CompletionPromise != nil {
		aiReq["completion_promise"] = *req.CompletionPromise
	}
	if req.MaxIterations != nil {
		aiReq["max_iterations"] = *req.MaxIterations
	}
	if req.WorkingDirectory != nil {
		aiReq["working_directory"] = *req.WorkingDirectory
	}
	if req.RunTests != nil {
		aiReq["run_tests"] = *req.RunTests
	}
	if req.TestCommand != nil {
		aiReq["test_command"] = *req.TestCommand
	}
	if req.RunLint != nil {
		aiReq["run_lint"] = *req.RunLint
	}
	if req.LintCommand != nil {
		aiReq["lint_command"] = *req.LintCommand
	}
	if req.RunTypecheck != nil {
		aiReq["run_typecheck"] = *req.RunTypecheck
	}
	if req.TypecheckCommand != nil {
		aiReq["typecheck_command"] = *req.TypecheckCommand
	}
	if req.Model != nil {
		aiReq["model"] = *req.Model
	}

	endpoint := fmt.Sprintf("/api/v1/ralph/tasks/sync?timeout=%s", timeout)
	result, err := h.forwardToAIService(r.Context(), "POST", endpoint, aiReq)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, fmt.Sprintf("Failed to run task: %v", err))
		return
	}

	// Store task reference
	if taskID, ok := result["id"].(string); ok {
		h.storeTaskReference(r.Context(), userID, taskID, req.Prompt)
	}

	response.JSON(w, http.StatusOK, result)
}

// HealthCheck returns the health status of the Ralph service
func (h *RalphHandler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	result, err := h.forwardToAIService(r.Context(), "GET", "/api/v1/ralph/health", nil)
	if err != nil {
		response.JSON(w, http.StatusServiceUnavailable, map[string]string{
			"status":  "unhealthy",
			"service": "ralph-wiggum",
			"error":   err.Error(),
		})
		return
	}

	response.JSON(w, http.StatusOK, result)
}

// Helper methods

func (h *RalphHandler) forwardToAIService(ctx context.Context, method, endpoint string, body interface{}) (map[string]interface{}, error) {
	var reqBody io.Reader
	if body != nil {
		jsonBody, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request: %w", err)
		}
		reqBody = bytes.NewBuffer(jsonBody)
	}

	url := h.cfg.AgentServiceURL + endpoint
	req, err := http.NewRequestWithContext(ctx, method, url, reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Internal-Service", "vibber-backend")

	client := &http.Client{
		Timeout: 10 * time.Minute, // Long timeout for sync operations
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("AI service error (status %d): %s", resp.StatusCode, string(respBody))
	}

	var result map[string]interface{}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return result, nil
}

func (h *RalphHandler) storeTaskReference(ctx context.Context, userID uuid.UUID, taskID string, prompt string) {
	// Store in Redis for quick lookup
	key := fmt.Sprintf("ralph:task:%s:owner", taskID)
	h.redis.Set(ctx, key, userID.String(), 24*time.Hour)

	// Also store in user's task list
	listKey := fmt.Sprintf("ralph:user:%s:tasks", userID.String())
	h.redis.LPush(ctx, listKey, taskID)
	h.redis.LTrim(ctx, listKey, 0, 99) // Keep last 100 tasks
	h.redis.Expire(ctx, listKey, 7*24*time.Hour) // Expire after 7 days
}

func (h *RalphHandler) verifyTaskOwnership(ctx context.Context, userID uuid.UUID, taskID string) bool {
	key := fmt.Sprintf("ralph:task:%s:owner", taskID)
	owner, err := h.redis.Get(ctx, key).Result()
	if err != nil {
		return false
	}
	return owner == userID.String()
}

func (h *RalphHandler) getUserTaskIDs(ctx context.Context, userID uuid.UUID) []string {
	listKey := fmt.Sprintf("ralph:user:%s:tasks", userID.String())
	taskIDs, err := h.redis.LRange(ctx, listKey, 0, -1).Result()
	if err != nil {
		return []string{}
	}
	return taskIDs
}
