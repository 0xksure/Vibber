package handlers

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"

	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/models"
	"github.com/vibber/backend/internal/repository"
	"github.com/vibber/backend/pkg/response"
)

type WebhookHandler struct {
	repos *repository.Repositories
	redis *redis.Client
	cfg   *config.Config
}

func NewWebhookHandler(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *WebhookHandler {
	return &WebhookHandler{
		repos: repos,
		redis: redis,
		cfg:   cfg,
	}
}

// Slack webhook handler
func (h *WebhookHandler) Slack(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Failed to read request body")
		return
	}
	r.Body = io.NopCloser(bytes.NewBuffer(body))

	// Verify Slack signature
	if !h.verifySlackSignature(r, body) {
		response.Error(w, http.StatusUnauthorized, "Invalid signature")
		return
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(body, &payload); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid JSON")
		return
	}

	// Handle URL verification challenge
	if payload["type"] == "url_verification" {
		response.JSON(w, http.StatusOK, map[string]string{
			"challenge": payload["challenge"].(string),
		})
		return
	}

	// Handle event callback
	if payload["type"] == "event_callback" {
		event := payload["event"].(map[string]interface{})
		eventType := event["type"].(string)

		switch eventType {
		case "message":
			h.handleSlackMessage(r.Context(), event)
		case "app_mention":
			h.handleSlackMention(r.Context(), event)
		}
	}

	w.WriteHeader(http.StatusOK)
}

// GitHub webhook handler
func (h *WebhookHandler) GitHub(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Failed to read request body")
		return
	}

	// Verify GitHub signature
	signature := r.Header.Get("X-Hub-Signature-256")
	if !h.verifyGitHubSignature(body, signature) {
		response.Error(w, http.StatusUnauthorized, "Invalid signature")
		return
	}

	eventType := r.Header.Get("X-GitHub-Event")

	var payload map[string]interface{}
	if err := json.Unmarshal(body, &payload); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid JSON")
		return
	}

	switch eventType {
	case "pull_request":
		h.handleGitHubPR(r.Context(), payload)
	case "pull_request_review":
		h.handleGitHubPRReview(r.Context(), payload)
	case "issue_comment":
		h.handleGitHubComment(r.Context(), payload)
	case "issues":
		h.handleGitHubIssue(r.Context(), payload)
	}

	w.WriteHeader(http.StatusOK)
}

// Jira webhook handler
func (h *WebhookHandler) Jira(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		response.Error(w, http.StatusBadRequest, "Failed to read request body")
		return
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(body, &payload); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid JSON")
		return
	}

	webhookEvent := payload["webhookEvent"].(string)

	switch webhookEvent {
	case "jira:issue_created":
		h.handleJiraIssueCreated(r.Context(), payload)
	case "jira:issue_updated":
		h.handleJiraIssueUpdated(r.Context(), payload)
	case "comment_created":
		h.handleJiraComment(r.Context(), payload)
	}

	w.WriteHeader(http.StatusOK)
}

// Signature verification helpers
func (h *WebhookHandler) verifySlackSignature(r *http.Request, body []byte) bool {
	timestamp := r.Header.Get("X-Slack-Request-Timestamp")
	signature := r.Header.Get("X-Slack-Signature")

	baseString := "v0:" + timestamp + ":" + string(body)
	mac := hmac.New(sha256.New, []byte(h.cfg.SlackClientSecret))
	mac.Write([]byte(baseString))
	expectedSignature := "v0=" + hex.EncodeToString(mac.Sum(nil))

	return hmac.Equal([]byte(signature), []byte(expectedSignature))
}

func (h *WebhookHandler) verifyGitHubSignature(body []byte, signature string) bool {
	if signature == "" {
		return false
	}

	mac := hmac.New(sha256.New, []byte(h.cfg.GitHubClientSecret))
	mac.Write(body)
	expectedSignature := "sha256=" + hex.EncodeToString(mac.Sum(nil))

	return hmac.Equal([]byte(signature), []byte(expectedSignature))
}

// Event handlers - these would queue events for the AI agent to process
import "context"

func (h *WebhookHandler) handleSlackMessage(ctx context.Context, event map[string]interface{}) {
	// Create interaction record
	interaction := &models.Interaction{
		ID:              uuid.New(),
		Provider:        "slack",
		InteractionType: "message",
		Status:          "pending",
	}

	inputData, _ := json.Marshal(event)
	interaction.InputData = string(inputData)

	// Queue for AI agent processing
	h.queueForProcessing(ctx, interaction)
}

func (h *WebhookHandler) handleSlackMention(ctx context.Context, event map[string]interface{}) {
	interaction := &models.Interaction{
		ID:              uuid.New(),
		Provider:        "slack",
		InteractionType: "mention",
		Status:          "pending",
	}

	inputData, _ := json.Marshal(event)
	interaction.InputData = string(inputData)

	h.queueForProcessing(ctx, interaction)
}

func (h *WebhookHandler) handleGitHubPR(ctx context.Context, payload map[string]interface{}) {
	action := payload["action"].(string)
	if action != "opened" && action != "synchronize" && action != "ready_for_review" {
		return
	}

	interaction := &models.Interaction{
		ID:              uuid.New(),
		Provider:        "github",
		InteractionType: "pull_request",
		Status:          "pending",
	}

	inputData, _ := json.Marshal(payload)
	interaction.InputData = string(inputData)

	h.queueForProcessing(ctx, interaction)
}

func (h *WebhookHandler) handleGitHubPRReview(ctx context.Context, payload map[string]interface{}) {
	interaction := &models.Interaction{
		ID:              uuid.New(),
		Provider:        "github",
		InteractionType: "pr_review",
		Status:          "pending",
	}

	inputData, _ := json.Marshal(payload)
	interaction.InputData = string(inputData)

	h.queueForProcessing(ctx, interaction)
}

func (h *WebhookHandler) handleGitHubComment(ctx context.Context, payload map[string]interface{}) {
	interaction := &models.Interaction{
		ID:              uuid.New(),
		Provider:        "github",
		InteractionType: "comment",
		Status:          "pending",
	}

	inputData, _ := json.Marshal(payload)
	interaction.InputData = string(inputData)

	h.queueForProcessing(ctx, interaction)
}

func (h *WebhookHandler) handleGitHubIssue(ctx context.Context, payload map[string]interface{}) {
	interaction := &models.Interaction{
		ID:              uuid.New(),
		Provider:        "github",
		InteractionType: "issue",
		Status:          "pending",
	}

	inputData, _ := json.Marshal(payload)
	interaction.InputData = string(inputData)

	h.queueForProcessing(ctx, interaction)
}

func (h *WebhookHandler) handleJiraIssueCreated(ctx context.Context, payload map[string]interface{}) {
	interaction := &models.Interaction{
		ID:              uuid.New(),
		Provider:        "jira",
		InteractionType: "issue_created",
		Status:          "pending",
	}

	inputData, _ := json.Marshal(payload)
	interaction.InputData = string(inputData)

	h.queueForProcessing(ctx, interaction)
}

func (h *WebhookHandler) handleJiraIssueUpdated(ctx context.Context, payload map[string]interface{}) {
	interaction := &models.Interaction{
		ID:              uuid.New(),
		Provider:        "jira",
		InteractionType: "issue_updated",
		Status:          "pending",
	}

	inputData, _ := json.Marshal(payload)
	interaction.InputData = string(inputData)

	h.queueForProcessing(ctx, interaction)
}

func (h *WebhookHandler) handleJiraComment(ctx context.Context, payload map[string]interface{}) {
	interaction := &models.Interaction{
		ID:              uuid.New(),
		Provider:        "jira",
		InteractionType: "comment",
		Status:          "pending",
	}

	inputData, _ := json.Marshal(payload)
	interaction.InputData = string(inputData)

	h.queueForProcessing(ctx, interaction)
}

func (h *WebhookHandler) queueForProcessing(ctx context.Context, interaction *models.Interaction) {
	// Publish to message queue for AI agent to process
	// In production, this would use RabbitMQ or similar
	message, _ := json.Marshal(interaction)
	h.redis.Publish(ctx, "agent:interactions", message)
}
