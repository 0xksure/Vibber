package models

import (
	"testing"
	"time"

	"github.com/google/uuid"
)

func TestAgentModel(t *testing.T) {
	id := uuid.New()
	userID := uuid.New()
	description := "A test agent"

	agent := &Agent{
		ID:                  id,
		UserID:              userID,
		Name:                "Test Agent",
		Description:         &description,
		Status:              "active",
		ConfidenceThreshold: 80,
		AutoMode:            true,
	}

	if agent.ID != id {
		t.Errorf("Agent ID mismatch: got %v want %v", agent.ID, id)
	}

	if agent.Name != "Test Agent" {
		t.Errorf("Agent name mismatch: got %v want %v", agent.Name, "Test Agent")
	}

	if agent.ConfidenceThreshold != 80 {
		t.Errorf("Confidence threshold mismatch: got %v want %v", agent.ConfidenceThreshold, 80)
	}

	if !agent.AutoMode {
		t.Error("AutoMode should be true")
	}
}

func TestUserModel(t *testing.T) {
	id := uuid.New()
	orgID := uuid.New()

	user := &User{
		ID:           id,
		OrgID:        orgID,
		Email:        "test@example.com",
		Name:         "Test User",
		PasswordHash: "hashed_password",
		Role:         "admin",
	}

	if user.Email != "test@example.com" {
		t.Errorf("User email mismatch: got %v want %v", user.Email, "test@example.com")
	}

	if user.Role != "admin" {
		t.Errorf("User role mismatch: got %v want %v", user.Role, "admin")
	}
}

func TestOrganizationModel(t *testing.T) {
	id := uuid.New()

	org := &Organization{
		ID:   id,
		Name: "Test Org",
		Slug: "test-org",
		Plan: "starter",
	}

	if org.Name != "Test Org" {
		t.Errorf("Org name mismatch: got %v want %v", org.Name, "Test Org")
	}

	if org.Plan != "starter" {
		t.Errorf("Org plan mismatch: got %v want %v", org.Plan, "starter")
	}
}

func TestInteractionModel(t *testing.T) {
	id := uuid.New()
	agentID := uuid.New()
	integrationID := uuid.New()

	interaction := &Interaction{
		ID:              id,
		AgentID:         agentID,
		IntegrationID:   integrationID,
		Provider:        "slack",
		InteractionType: "message",
		Status:          "pending",
		InputData:       `{"text": "hello"}`,
		CreatedAt:       time.Now(),
	}

	if interaction.Provider != "slack" {
		t.Errorf("Provider mismatch: got %v want %v", interaction.Provider, "slack")
	}

	if interaction.Status != "pending" {
		t.Errorf("Status mismatch: got %v want %v", interaction.Status, "pending")
	}
}

func TestEscalationModel(t *testing.T) {
	id := uuid.New()
	interactionID := uuid.New()
	agentID := uuid.New()

	escalation := &Escalation{
		ID:            id,
		InteractionID: interactionID,
		AgentID:       agentID,
		Reason:        "Low confidence",
		Priority:      "high",
		Status:        "pending",
	}

	if escalation.Reason != "Low confidence" {
		t.Errorf("Reason mismatch: got %v want %v", escalation.Reason, "Low confidence")
	}

	if escalation.Priority != "high" {
		t.Errorf("Priority mismatch: got %v want %v", escalation.Priority, "high")
	}
}

func TestLoginRequest(t *testing.T) {
	req := LoginRequest{
		Email:    "test@example.com",
		Password: "password123",
	}

	if req.Email != "test@example.com" {
		t.Errorf("Email mismatch: got %v want %v", req.Email, "test@example.com")
	}
}

func TestRegisterRequest(t *testing.T) {
	req := RegisterRequest{
		Email:        "test@example.com",
		Password:     "password123",
		Name:         "Test User",
		Organization: "Test Org",
	}

	if req.Organization != "Test Org" {
		t.Errorf("Organization mismatch: got %v want %v", req.Organization, "Test Org")
	}
}

func TestAgentStatusModel(t *testing.T) {
	status := &AgentStatus{
		Status:             "active",
		IsActive:           true,
		LastActivity:       time.Now(),
		TodayInteractions:  10,
		PendingEscalations: 2,
		ConfidenceScore:    0.85,
	}

	if status.Status != "active" {
		t.Errorf("Status mismatch: got %v want %v", status.Status, "active")
	}

	if status.TodayInteractions != 10 {
		t.Errorf("TodayInteractions mismatch: got %v want %v", status.TodayInteractions, 10)
	}
}
