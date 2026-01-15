package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"golang.org/x/crypto/bcrypt"

	"github.com/vibber/backend/internal/config"
	"github.com/vibber/backend/internal/models"
	"github.com/vibber/backend/internal/repository"
	"github.com/vibber/backend/pkg/response"
)

type AuthHandler struct {
	repos *repository.Repositories
	redis *redis.Client
	cfg   *config.Config
}

func NewAuthHandler(repos *repository.Repositories, redis *redis.Client, cfg *config.Config) *AuthHandler {
	return &AuthHandler{
		repos: repos,
		redis: redis,
		cfg:   cfg,
	}
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	var req models.LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	user, err := h.repos.User.GetByEmail(r.Context(), req.Email)
	if err != nil {
		response.Error(w, http.StatusUnauthorized, "Invalid credentials")
		return
	}

	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(req.Password)); err != nil {
		response.Error(w, http.StatusUnauthorized, "Invalid credentials")
		return
	}

	// Generate tokens
	accessToken, err := h.generateAccessToken(user)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to generate token")
		return
	}

	refreshToken, err := h.generateRefreshToken(user)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to generate refresh token")
		return
	}

	// Update last login
	h.repos.User.UpdateLastLogin(r.Context(), user.ID)

	response.JSON(w, http.StatusOK, models.AuthResponse{
		User:         user,
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		ExpiresIn:    h.cfg.JWTExpiryMinutes * 60,
	})
}

func (h *AuthHandler) Register(w http.ResponseWriter, r *http.Request) {
	var req models.RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Check if user exists
	existing, _ := h.repos.User.GetByEmail(r.Context(), req.Email)
	if existing != nil {
		response.Error(w, http.StatusConflict, "Email already registered")
		return
	}

	// Hash password
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to process password")
		return
	}

	// Create organization
	org := &models.Organization{
		ID:   uuid.New(),
		Name: req.Organization,
		Slug: generateSlug(req.Organization),
		Plan: "starter",
	}

	if err := h.repos.Organization.Create(r.Context(), org); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to create organization")
		return
	}

	// Create user
	user := &models.User{
		ID:           uuid.New(),
		OrgID:        org.ID,
		Email:        req.Email,
		Name:         req.Name,
		PasswordHash: string(hashedPassword),
		Role:         "admin",
	}

	if err := h.repos.User.Create(r.Context(), user); err != nil {
		response.Error(w, http.StatusInternalServerError, "Failed to create user")
		return
	}

	// Generate tokens
	accessToken, _ := h.generateAccessToken(user)
	refreshToken, _ := h.generateRefreshToken(user)

	response.JSON(w, http.StatusCreated, models.AuthResponse{
		User:         user,
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		ExpiresIn:    h.cfg.JWTExpiryMinutes * 60,
	})
}

func (h *AuthHandler) RefreshToken(w http.ResponseWriter, r *http.Request) {
	var req struct {
		RefreshToken string `json:"refreshToken"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// Validate refresh token
	token, err := jwt.Parse(req.RefreshToken, func(token *jwt.Token) (interface{}, error) {
		return []byte(h.cfg.JWTSecret), nil
	})
	if err != nil || !token.Valid {
		response.Error(w, http.StatusUnauthorized, "Invalid refresh token")
		return
	}

	claims := token.Claims.(jwt.MapClaims)
	userID, _ := uuid.Parse(claims["sub"].(string))

	user, err := h.repos.User.GetByID(r.Context(), userID)
	if err != nil {
		response.Error(w, http.StatusUnauthorized, "User not found")
		return
	}

	// Generate new access token
	accessToken, _ := h.generateAccessToken(user)

	response.JSON(w, http.StatusOK, map[string]interface{}{
		"accessToken": accessToken,
		"expiresIn":   h.cfg.JWTExpiryMinutes * 60,
	})
}

func (h *AuthHandler) Logout(w http.ResponseWriter, r *http.Request) {
	// In a production system, you would blacklist the token in Redis
	response.JSON(w, http.StatusOK, map[string]string{"message": "Logged out successfully"})
}

func (h *AuthHandler) Me(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("userID").(uuid.UUID)

	user, err := h.repos.User.GetByID(r.Context(), userID)
	if err != nil {
		response.Error(w, http.StatusNotFound, "User not found")
		return
	}

	response.JSON(w, http.StatusOK, user)
}

func (h *AuthHandler) OAuthRedirect(w http.ResponseWriter, r *http.Request) {
	provider := chi.URLParam(r, "provider")

	var authURL string
	switch provider {
	case "google":
		authURL = h.getGoogleAuthURL()
	case "github":
		authURL = h.getGitHubAuthURL()
	default:
		response.Error(w, http.StatusBadRequest, "Unsupported provider")
		return
	}

	http.Redirect(w, r, authURL, http.StatusTemporaryRedirect)
}

func (h *AuthHandler) OAuthCallback(w http.ResponseWriter, r *http.Request) {
	provider := chi.URLParam(r, "provider")
	code := r.URL.Query().Get("code")

	if code == "" {
		response.Error(w, http.StatusBadRequest, "Missing authorization code")
		return
	}

	var user *models.User
	var err error

	switch provider {
	case "google":
		user, err = h.handleGoogleCallback(r.Context(), code)
	case "github":
		user, err = h.handleGitHubCallback(r.Context(), code)
	default:
		response.Error(w, http.StatusBadRequest, "Unsupported provider")
		return
	}

	if err != nil {
		response.Error(w, http.StatusInternalServerError, "OAuth authentication failed")
		return
	}

	// Generate tokens
	accessToken, _ := h.generateAccessToken(user)
	refreshToken, _ := h.generateRefreshToken(user)

	// Redirect to frontend with tokens
	redirectURL := h.cfg.FrontendURL + "/auth/callback?access_token=" + accessToken + "&refresh_token=" + refreshToken
	http.Redirect(w, r, redirectURL, http.StatusTemporaryRedirect)
}

func (h *AuthHandler) generateAccessToken(user *models.User) (string, error) {
	claims := jwt.MapClaims{
		"sub":   user.ID.String(),
		"email": user.Email,
		"name":  user.Name,
		"role":  user.Role,
		"orgId": user.OrgID.String(),
		"exp":   time.Now().Add(time.Duration(h.cfg.JWTExpiryMinutes) * time.Minute).Unix(),
		"iat":   time.Now().Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(h.cfg.JWTSecret))
}

func (h *AuthHandler) generateRefreshToken(user *models.User) (string, error) {
	claims := jwt.MapClaims{
		"sub":  user.ID.String(),
		"type": "refresh",
		"exp":  time.Now().Add(time.Duration(h.cfg.RefreshExpiryHours) * time.Hour).Unix(),
		"iat":  time.Now().Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(h.cfg.JWTSecret))
}

func (h *AuthHandler) getGoogleAuthURL() string {
	return "https://accounts.google.com/o/oauth2/v2/auth?client_id=" + h.cfg.GoogleClientID +
		"&redirect_uri=" + h.cfg.FrontendURL + "/api/v1/auth/oauth/google/callback" +
		"&response_type=code&scope=email%20profile"
}

func (h *AuthHandler) getGitHubAuthURL() string {
	return "https://github.com/login/oauth/authorize?client_id=" + h.cfg.GitHubClientID +
		"&redirect_uri=" + h.cfg.FrontendURL + "/api/v1/auth/oauth/github/callback" +
		"&scope=user:email"
}

func (h *AuthHandler) handleGoogleCallback(ctx context.Context, code string) (*models.User, error) {
	// Implementation would exchange code for tokens and get user info
	// This is a placeholder - actual implementation would use golang.org/x/oauth2
	return nil, nil
}

func (h *AuthHandler) handleGitHubCallback(ctx context.Context, code string) (*models.User, error) {
	// Implementation would exchange code for tokens and get user info
	// This is a placeholder - actual implementation would use golang.org/x/oauth2
	return nil, nil
}

func generateSlug(name string) string {
	// Simple slug generation - in production use a proper slugify library
	return name
}

import "context"
