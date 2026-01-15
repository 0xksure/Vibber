package repository

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"

	"github.com/vibber/backend/internal/models"
)

// Repositories holds all repository instances
type Repositories struct {
	User         UserRepository
	Organization OrganizationRepository
	Agent        AgentRepository
	Integration  IntegrationRepository
	Interaction  InteractionRepository
	Escalation   EscalationRepository
	Training     TrainingRepository
}

// NewRepositories creates a new repositories instance
func NewRepositories(db *pgxpool.Pool) *Repositories {
	return &Repositories{
		User:         &userRepository{db: db},
		Organization: &organizationRepository{db: db},
		Agent:        &agentRepository{db: db},
		Integration:  &integrationRepository{db: db},
		Interaction:  &interactionRepository{db: db},
		Escalation:   &escalationRepository{db: db},
		Training:     &trainingRepository{db: db},
	}
}

// NewPostgresDB creates a new PostgreSQL connection pool
func NewPostgresDB(connString string) (*pgxpool.Pool, error) {
	config, err := pgxpool.ParseConfig(connString)
	if err != nil {
		return nil, err
	}

	config.MaxConns = 25
	config.MinConns = 5
	config.MaxConnLifetime = time.Hour
	config.MaxConnIdleTime = 30 * time.Minute

	pool, err := pgxpool.NewWithConfig(context.Background(), config)
	if err != nil {
		return nil, err
	}

	// Test connection
	if err := pool.Ping(context.Background()); err != nil {
		return nil, err
	}

	return pool, nil
}

// NewRedisClient creates a new Redis client
func NewRedisClient(connString string) (*redis.Client, error) {
	opt, err := redis.ParseURL(connString)
	if err != nil {
		return nil, err
	}

	client := redis.NewClient(opt)

	// Test connection
	if _, err := client.Ping(context.Background()).Result(); err != nil {
		return nil, err
	}

	return client, nil
}

// UserRepository interface
type UserRepository interface {
	Create(ctx context.Context, user *models.User) error
	GetByID(ctx context.Context, id uuid.UUID) (*models.User, error)
	GetByEmail(ctx context.Context, email string) (*models.User, error)
	Update(ctx context.Context, user *models.User) error
	UpdateLastLogin(ctx context.Context, id uuid.UUID) error
	ListByOrgID(ctx context.Context, orgID uuid.UUID) ([]*models.User, error)
}

// OrganizationRepository interface
type OrganizationRepository interface {
	Create(ctx context.Context, org *models.Organization) error
	GetByID(ctx context.Context, id uuid.UUID) (*models.Organization, error)
	GetBySlug(ctx context.Context, slug string) (*models.Organization, error)
	Update(ctx context.Context, org *models.Organization) error
}

// AgentRepository interface
type AgentRepository interface {
	Create(ctx context.Context, agent *models.Agent) error
	GetByID(ctx context.Context, id uuid.UUID) (*models.Agent, error)
	ListByUserID(ctx context.Context, userID uuid.UUID) ([]*models.Agent, error)
	Update(ctx context.Context, agent *models.Agent) error
	Delete(ctx context.Context, id uuid.UUID) error
}

// IntegrationRepository interface
type IntegrationRepository interface {
	Create(ctx context.Context, integration *models.Integration) error
	GetByID(ctx context.Context, id uuid.UUID) (*models.Integration, error)
	GetByAgentAndProvider(ctx context.Context, agentID uuid.UUID, provider string) (*models.Integration, error)
	ListByAgentID(ctx context.Context, agentID uuid.UUID) ([]*models.Integration, error)
	Update(ctx context.Context, integration *models.Integration) error
	Delete(ctx context.Context, id uuid.UUID) error
}

// InteractionRepository interface
type InteractionRepository interface {
	Create(ctx context.Context, interaction *models.Interaction) error
	GetByID(ctx context.Context, id uuid.UUID) (*models.Interaction, error)
	ListByAgentID(ctx context.Context, agentID uuid.UUID, params models.PaginationParams) ([]*models.Interaction, int, error)
	Update(ctx context.Context, interaction *models.Interaction) error
	CountToday(ctx context.Context, agentID uuid.UUID) (int, error)
	GetOverviewMetrics(ctx context.Context, agentID uuid.UUID) (*models.OverviewMetrics, error)
	GetTrends(ctx context.Context, agentID uuid.UUID, days int) ([]*models.TrendData, error)
}

// EscalationRepository interface
type EscalationRepository interface {
	Create(ctx context.Context, escalation *models.Escalation) error
	GetByID(ctx context.Context, id uuid.UUID) (*models.Escalation, error)
	ListPending(ctx context.Context, agentID uuid.UUID) ([]*models.Escalation, error)
	Update(ctx context.Context, escalation *models.Escalation) error
	CountPending(ctx context.Context, agentID uuid.UUID) (int, error)
}

// TrainingRepository interface
type TrainingRepository interface {
	Create(ctx context.Context, sample *models.TrainingSample) error
	ListByAgentID(ctx context.Context, agentID uuid.UUID) ([]*models.TrainingSample, error)
	Delete(ctx context.Context, id uuid.UUID) error
}

// Implementation stubs - these would be fully implemented in production

type userRepository struct {
	db *pgxpool.Pool
}

func (r *userRepository) Create(ctx context.Context, user *models.User) error {
	_, err := r.db.Exec(ctx, `
		INSERT INTO users (id, org_id, email, name, password_hash, avatar_url, role, provider, provider_id, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
	`, user.ID, user.OrgID, user.Email, user.Name, user.PasswordHash, user.AvatarURL, user.Role, user.Provider, user.ProviderID)
	return err
}

func (r *userRepository) GetByID(ctx context.Context, id uuid.UUID) (*models.User, error) {
	user := &models.User{}
	err := r.db.QueryRow(ctx, `
		SELECT id, org_id, email, name, password_hash, avatar_url, role, provider, provider_id, created_at, updated_at, last_login_at
		FROM users WHERE id = $1
	`, id).Scan(&user.ID, &user.OrgID, &user.Email, &user.Name, &user.PasswordHash, &user.AvatarURL, &user.Role, &user.Provider, &user.ProviderID, &user.CreatedAt, &user.UpdatedAt, &user.LastLoginAt)
	return user, err
}

func (r *userRepository) GetByEmail(ctx context.Context, email string) (*models.User, error) {
	user := &models.User{}
	err := r.db.QueryRow(ctx, `
		SELECT id, org_id, email, name, password_hash, avatar_url, role, provider, provider_id, created_at, updated_at, last_login_at
		FROM users WHERE email = $1
	`, email).Scan(&user.ID, &user.OrgID, &user.Email, &user.Name, &user.PasswordHash, &user.AvatarURL, &user.Role, &user.Provider, &user.ProviderID, &user.CreatedAt, &user.UpdatedAt, &user.LastLoginAt)
	return user, err
}

func (r *userRepository) Update(ctx context.Context, user *models.User) error {
	_, err := r.db.Exec(ctx, `
		UPDATE users SET name = $2, avatar_url = $3, role = $4, updated_at = NOW()
		WHERE id = $1
	`, user.ID, user.Name, user.AvatarURL, user.Role)
	return err
}

func (r *userRepository) UpdateLastLogin(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Exec(ctx, `UPDATE users SET last_login_at = NOW() WHERE id = $1`, id)
	return err
}

func (r *userRepository) ListByOrgID(ctx context.Context, orgID uuid.UUID) ([]*models.User, error) {
	rows, err := r.db.Query(ctx, `
		SELECT id, org_id, email, name, avatar_url, role, created_at, updated_at
		FROM users WHERE org_id = $1
	`, orgID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var users []*models.User
	for rows.Next() {
		user := &models.User{}
		if err := rows.Scan(&user.ID, &user.OrgID, &user.Email, &user.Name, &user.AvatarURL, &user.Role, &user.CreatedAt, &user.UpdatedAt); err != nil {
			return nil, err
		}
		users = append(users, user)
	}
	return users, nil
}

type organizationRepository struct {
	db *pgxpool.Pool
}

func (r *organizationRepository) Create(ctx context.Context, org *models.Organization) error {
	_, err := r.db.Exec(ctx, `
		INSERT INTO organizations (id, name, slug, plan, created_at, updated_at)
		VALUES ($1, $2, $3, $4, NOW(), NOW())
	`, org.ID, org.Name, org.Slug, org.Plan)
	return err
}

func (r *organizationRepository) GetByID(ctx context.Context, id uuid.UUID) (*models.Organization, error) {
	org := &models.Organization{}
	err := r.db.QueryRow(ctx, `
		SELECT id, name, slug, plan, created_at, updated_at FROM organizations WHERE id = $1
	`, id).Scan(&org.ID, &org.Name, &org.Slug, &org.Plan, &org.CreatedAt, &org.UpdatedAt)
	return org, err
}

func (r *organizationRepository) GetBySlug(ctx context.Context, slug string) (*models.Organization, error) {
	org := &models.Organization{}
	err := r.db.QueryRow(ctx, `
		SELECT id, name, slug, plan, created_at, updated_at FROM organizations WHERE slug = $1
	`, slug).Scan(&org.ID, &org.Name, &org.Slug, &org.Plan, &org.CreatedAt, &org.UpdatedAt)
	return org, err
}

func (r *organizationRepository) Update(ctx context.Context, org *models.Organization) error {
	_, err := r.db.Exec(ctx, `
		UPDATE organizations SET name = $2, plan = $3, updated_at = NOW() WHERE id = $1
	`, org.ID, org.Name, org.Plan)
	return err
}

type agentRepository struct {
	db *pgxpool.Pool
}

func (r *agentRepository) Create(ctx context.Context, agent *models.Agent) error {
	_, err := r.db.Exec(ctx, `
		INSERT INTO agents (id, user_id, name, description, avatar_url, status, confidence_threshold, auto_mode, working_hours, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
	`, agent.ID, agent.UserID, agent.Name, agent.Description, agent.AvatarURL, agent.Status, agent.ConfidenceThreshold, agent.AutoMode, agent.WorkingHours)
	return err
}

func (r *agentRepository) GetByID(ctx context.Context, id uuid.UUID) (*models.Agent, error) {
	agent := &models.Agent{}
	err := r.db.QueryRow(ctx, `
		SELECT id, user_id, name, description, avatar_url, status, confidence_threshold, auto_mode, working_hours, created_at, updated_at
		FROM agents WHERE id = $1
	`, id).Scan(&agent.ID, &agent.UserID, &agent.Name, &agent.Description, &agent.AvatarURL, &agent.Status, &agent.ConfidenceThreshold, &agent.AutoMode, &agent.WorkingHours, &agent.CreatedAt, &agent.UpdatedAt)
	return agent, err
}

func (r *agentRepository) ListByUserID(ctx context.Context, userID uuid.UUID) ([]*models.Agent, error) {
	rows, err := r.db.Query(ctx, `
		SELECT id, user_id, name, description, avatar_url, status, confidence_threshold, auto_mode, working_hours, created_at, updated_at
		FROM agents WHERE user_id = $1 ORDER BY created_at DESC
	`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var agents []*models.Agent
	for rows.Next() {
		agent := &models.Agent{}
		if err := rows.Scan(&agent.ID, &agent.UserID, &agent.Name, &agent.Description, &agent.AvatarURL, &agent.Status, &agent.ConfidenceThreshold, &agent.AutoMode, &agent.WorkingHours, &agent.CreatedAt, &agent.UpdatedAt); err != nil {
			return nil, err
		}
		agents = append(agents, agent)
	}
	return agents, nil
}

func (r *agentRepository) Update(ctx context.Context, agent *models.Agent) error {
	_, err := r.db.Exec(ctx, `
		UPDATE agents SET name = $2, description = $3, avatar_url = $4, status = $5, confidence_threshold = $6, auto_mode = $7, working_hours = $8, updated_at = NOW()
		WHERE id = $1
	`, agent.ID, agent.Name, agent.Description, agent.AvatarURL, agent.Status, agent.ConfidenceThreshold, agent.AutoMode, agent.WorkingHours)
	return err
}

func (r *agentRepository) Delete(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Exec(ctx, `DELETE FROM agents WHERE id = $1`, id)
	return err
}

type integrationRepository struct {
	db *pgxpool.Pool
}

func (r *integrationRepository) Create(ctx context.Context, i *models.Integration) error {
	_, err := r.db.Exec(ctx, `
		INSERT INTO integrations (id, agent_id, provider, access_token, refresh_token, scopes, status, external_id, metadata, created_at, expires_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), $10)
	`, i.ID, i.AgentID, i.Provider, i.AccessToken, i.RefreshToken, i.Scopes, i.Status, i.ExternalID, i.Metadata, i.ExpiresAt)
	return err
}

func (r *integrationRepository) GetByID(ctx context.Context, id uuid.UUID) (*models.Integration, error) {
	i := &models.Integration{}
	err := r.db.QueryRow(ctx, `
		SELECT id, agent_id, provider, access_token, refresh_token, scopes, status, external_id, metadata, created_at, expires_at
		FROM integrations WHERE id = $1
	`, id).Scan(&i.ID, &i.AgentID, &i.Provider, &i.AccessToken, &i.RefreshToken, &i.Scopes, &i.Status, &i.ExternalID, &i.Metadata, &i.CreatedAt, &i.ExpiresAt)
	return i, err
}

func (r *integrationRepository) GetByAgentAndProvider(ctx context.Context, agentID uuid.UUID, provider string) (*models.Integration, error) {
	i := &models.Integration{}
	err := r.db.QueryRow(ctx, `
		SELECT id, agent_id, provider, access_token, refresh_token, scopes, status, external_id, metadata, created_at, expires_at
		FROM integrations WHERE agent_id = $1 AND provider = $2
	`, agentID, provider).Scan(&i.ID, &i.AgentID, &i.Provider, &i.AccessToken, &i.RefreshToken, &i.Scopes, &i.Status, &i.ExternalID, &i.Metadata, &i.CreatedAt, &i.ExpiresAt)
	return i, err
}

func (r *integrationRepository) ListByAgentID(ctx context.Context, agentID uuid.UUID) ([]*models.Integration, error) {
	rows, err := r.db.Query(ctx, `
		SELECT id, agent_id, provider, scopes, status, external_id, metadata, created_at, expires_at
		FROM integrations WHERE agent_id = $1
	`, agentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var integrations []*models.Integration
	for rows.Next() {
		i := &models.Integration{}
		if err := rows.Scan(&i.ID, &i.AgentID, &i.Provider, &i.Scopes, &i.Status, &i.ExternalID, &i.Metadata, &i.CreatedAt, &i.ExpiresAt); err != nil {
			return nil, err
		}
		integrations = append(integrations, i)
	}
	return integrations, nil
}

func (r *integrationRepository) Update(ctx context.Context, i *models.Integration) error {
	_, err := r.db.Exec(ctx, `
		UPDATE integrations SET access_token = $2, refresh_token = $3, status = $4, expires_at = $5
		WHERE id = $1
	`, i.ID, i.AccessToken, i.RefreshToken, i.Status, i.ExpiresAt)
	return err
}

func (r *integrationRepository) Delete(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Exec(ctx, `DELETE FROM integrations WHERE id = $1`, id)
	return err
}

type interactionRepository struct {
	db *pgxpool.Pool
}

func (r *interactionRepository) Create(ctx context.Context, i *models.Interaction) error {
	_, err := r.db.Exec(ctx, `
		INSERT INTO interactions (id, agent_id, integration_id, provider, interaction_type, input_data, output_data, confidence_score, status, escalated, human_feedback, processing_time, created_at, completed_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), $13)
	`, i.ID, i.AgentID, i.IntegrationID, i.Provider, i.InteractionType, i.InputData, i.OutputData, i.ConfidenceScore, i.Status, i.Escalated, i.HumanFeedback, i.ProcessingTime, i.CompletedAt)
	return err
}

func (r *interactionRepository) GetByID(ctx context.Context, id uuid.UUID) (*models.Interaction, error) {
	i := &models.Interaction{}
	err := r.db.QueryRow(ctx, `
		SELECT id, agent_id, integration_id, provider, interaction_type, input_data, output_data, confidence_score, status, escalated, human_feedback, processing_time, created_at, completed_at
		FROM interactions WHERE id = $1
	`, id).Scan(&i.ID, &i.AgentID, &i.IntegrationID, &i.Provider, &i.InteractionType, &i.InputData, &i.OutputData, &i.ConfidenceScore, &i.Status, &i.Escalated, &i.HumanFeedback, &i.ProcessingTime, &i.CreatedAt, &i.CompletedAt)
	return i, err
}

func (r *interactionRepository) ListByAgentID(ctx context.Context, agentID uuid.UUID, params models.PaginationParams) ([]*models.Interaction, int, error) {
	offset := (params.Page - 1) * params.PageSize

	rows, err := r.db.Query(ctx, `
		SELECT id, agent_id, integration_id, provider, interaction_type, input_data, output_data, confidence_score, status, escalated, human_feedback, processing_time, created_at, completed_at
		FROM interactions WHERE agent_id = $1
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3
	`, agentID, params.PageSize, offset)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var interactions []*models.Interaction
	for rows.Next() {
		i := &models.Interaction{}
		if err := rows.Scan(&i.ID, &i.AgentID, &i.IntegrationID, &i.Provider, &i.InteractionType, &i.InputData, &i.OutputData, &i.ConfidenceScore, &i.Status, &i.Escalated, &i.HumanFeedback, &i.ProcessingTime, &i.CreatedAt, &i.CompletedAt); err != nil {
			return nil, 0, err
		}
		interactions = append(interactions, i)
	}

	var total int
	r.db.QueryRow(ctx, `SELECT COUNT(*) FROM interactions WHERE agent_id = $1`, agentID).Scan(&total)

	return interactions, total, nil
}

func (r *interactionRepository) Update(ctx context.Context, i *models.Interaction) error {
	_, err := r.db.Exec(ctx, `
		UPDATE interactions SET output_data = $2, confidence_score = $3, status = $4, escalated = $5, human_feedback = $6, processing_time = $7, completed_at = $8
		WHERE id = $1
	`, i.ID, i.OutputData, i.ConfidenceScore, i.Status, i.Escalated, i.HumanFeedback, i.ProcessingTime, i.CompletedAt)
	return err
}

func (r *interactionRepository) CountToday(ctx context.Context, agentID uuid.UUID) (int, error) {
	var count int
	err := r.db.QueryRow(ctx, `
		SELECT COUNT(*) FROM interactions WHERE agent_id = $1 AND created_at >= CURRENT_DATE
	`, agentID).Scan(&count)
	return count, err
}

func (r *interactionRepository) GetOverviewMetrics(ctx context.Context, agentID uuid.UUID) (*models.OverviewMetrics, error) {
	metrics := &models.OverviewMetrics{
		InteractionsByType:   make(map[string]int),
		InteractionsByStatus: make(map[string]int),
	}

	// Total and today counts
	r.db.QueryRow(ctx, `SELECT COUNT(*) FROM interactions WHERE agent_id = $1`, agentID).Scan(&metrics.TotalInteractions)
	r.db.QueryRow(ctx, `SELECT COUNT(*) FROM interactions WHERE agent_id = $1 AND created_at >= CURRENT_DATE`, agentID).Scan(&metrics.TodayInteractions)

	// Autonomous rate
	var escalatedCount int
	r.db.QueryRow(ctx, `SELECT COUNT(*) FROM interactions WHERE agent_id = $1 AND escalated = true`, agentID).Scan(&escalatedCount)
	if metrics.TotalInteractions > 0 {
		metrics.AutonomousRate = float64(metrics.TotalInteractions-escalatedCount) / float64(metrics.TotalInteractions) * 100
	}

	// Pending escalations
	r.db.QueryRow(ctx, `SELECT COUNT(*) FROM escalations WHERE agent_id = $1 AND status = 'pending'`, agentID).Scan(&metrics.PendingEscalations)

	// Average confidence
	r.db.QueryRow(ctx, `SELECT COALESCE(AVG(confidence_score), 0) FROM interactions WHERE agent_id = $1`, agentID).Scan(&metrics.AvgConfidenceScore)

	// Average processing time
	r.db.QueryRow(ctx, `SELECT COALESCE(AVG(processing_time), 0) FROM interactions WHERE agent_id = $1`, agentID).Scan(&metrics.AvgProcessingTime)

	return metrics, nil
}

func (r *interactionRepository) GetTrends(ctx context.Context, agentID uuid.UUID, days int) ([]*models.TrendData, error) {
	rows, err := r.db.Query(ctx, `
		SELECT
			DATE(created_at) as date,
			COUNT(*) as interactions,
			SUM(CASE WHEN escalated THEN 1 ELSE 0 END) as escalations,
			COALESCE(AVG(confidence_score), 0) as confidence
		FROM interactions
		WHERE agent_id = $1 AND created_at >= NOW() - INTERVAL '1 day' * $2
		GROUP BY DATE(created_at)
		ORDER BY date
	`, agentID, days)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var trends []*models.TrendData
	for rows.Next() {
		t := &models.TrendData{}
		if err := rows.Scan(&t.Date, &t.Interactions, &t.Escalations, &t.Confidence); err != nil {
			return nil, err
		}
		trends = append(trends, t)
	}
	return trends, nil
}

type escalationRepository struct {
	db *pgxpool.Pool
}

func (r *escalationRepository) Create(ctx context.Context, e *models.Escalation) error {
	_, err := r.db.Exec(ctx, `
		INSERT INTO escalations (id, interaction_id, agent_id, reason, priority, status, context, resolution, resolved_by, resolved_at, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
	`, e.ID, e.InteractionID, e.AgentID, e.Reason, e.Priority, e.Status, e.Context, e.Resolution, e.ResolvedBy, e.ResolvedAt)
	return err
}

func (r *escalationRepository) GetByID(ctx context.Context, id uuid.UUID) (*models.Escalation, error) {
	e := &models.Escalation{}
	err := r.db.QueryRow(ctx, `
		SELECT id, interaction_id, agent_id, reason, priority, status, context, resolution, resolved_by, resolved_at, created_at
		FROM escalations WHERE id = $1
	`, id).Scan(&e.ID, &e.InteractionID, &e.AgentID, &e.Reason, &e.Priority, &e.Status, &e.Context, &e.Resolution, &e.ResolvedBy, &e.ResolvedAt, &e.CreatedAt)
	return e, err
}

func (r *escalationRepository) ListPending(ctx context.Context, agentID uuid.UUID) ([]*models.Escalation, error) {
	rows, err := r.db.Query(ctx, `
		SELECT id, interaction_id, agent_id, reason, priority, status, context, resolution, resolved_by, resolved_at, created_at
		FROM escalations WHERE agent_id = $1 AND status = 'pending'
		ORDER BY
			CASE priority
				WHEN 'urgent' THEN 1
				WHEN 'high' THEN 2
				WHEN 'medium' THEN 3
				ELSE 4
			END,
			created_at DESC
	`, agentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var escalations []*models.Escalation
	for rows.Next() {
		e := &models.Escalation{}
		if err := rows.Scan(&e.ID, &e.InteractionID, &e.AgentID, &e.Reason, &e.Priority, &e.Status, &e.Context, &e.Resolution, &e.ResolvedBy, &e.ResolvedAt, &e.CreatedAt); err != nil {
			return nil, err
		}
		escalations = append(escalations, e)
	}
	return escalations, nil
}

func (r *escalationRepository) Update(ctx context.Context, e *models.Escalation) error {
	_, err := r.db.Exec(ctx, `
		UPDATE escalations SET status = $2, resolution = $3, resolved_by = $4, resolved_at = $5
		WHERE id = $1
	`, e.ID, e.Status, e.Resolution, e.ResolvedBy, e.ResolvedAt)
	return err
}

func (r *escalationRepository) CountPending(ctx context.Context, agentID uuid.UUID) (int, error) {
	var count int
	err := r.db.QueryRow(ctx, `
		SELECT COUNT(*) FROM escalations WHERE agent_id = $1 AND status = 'pending'
	`, agentID).Scan(&count)
	return count, err
}

type trainingRepository struct {
	db *pgxpool.Pool
}

func (r *trainingRepository) Create(ctx context.Context, s *models.TrainingSample) error {
	_, err := r.db.Exec(ctx, `
		INSERT INTO training_samples (id, agent_id, provider, sample_type, input_text, output_text, embedding, is_positive, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
	`, s.ID, s.AgentID, s.Provider, s.SampleType, s.InputText, s.OutputText, s.Embedding, s.IsPositive)
	return err
}

func (r *trainingRepository) ListByAgentID(ctx context.Context, agentID uuid.UUID) ([]*models.TrainingSample, error) {
	rows, err := r.db.Query(ctx, `
		SELECT id, agent_id, provider, sample_type, input_text, output_text, is_positive, created_at
		FROM training_samples WHERE agent_id = $1
	`, agentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var samples []*models.TrainingSample
	for rows.Next() {
		s := &models.TrainingSample{}
		if err := rows.Scan(&s.ID, &s.AgentID, &s.Provider, &s.SampleType, &s.InputText, &s.OutputText, &s.IsPositive, &s.CreatedAt); err != nil {
			return nil, err
		}
		samples = append(samples, s)
	}
	return samples, nil
}

func (r *trainingRepository) Delete(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Exec(ctx, `DELETE FROM training_samples WHERE id = $1`, id)
	return err
}
