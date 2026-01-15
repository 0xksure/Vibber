package middleware

import (
	"context"
	"net/http"
	"strings"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/vibber/backend/pkg/response"
)

// JWTAuth middleware validates JWT tokens
func JWTAuth(secret string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			authHeader := r.Header.Get("Authorization")
			if authHeader == "" {
				response.Error(w, http.StatusUnauthorized, "Missing authorization header")
				return
			}

			parts := strings.Split(authHeader, " ")
			if len(parts) != 2 || parts[0] != "Bearer" {
				response.Error(w, http.StatusUnauthorized, "Invalid authorization header format")
				return
			}

			tokenString := parts[1]

			token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
				if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
					return nil, jwt.ErrSignatureInvalid
				}
				return []byte(secret), nil
			})

			if err != nil || !token.Valid {
				response.Error(w, http.StatusUnauthorized, "Invalid or expired token")
				return
			}

			claims, ok := token.Claims.(jwt.MapClaims)
			if !ok {
				response.Error(w, http.StatusUnauthorized, "Invalid token claims")
				return
			}

			// Extract user information from claims
			userID, err := uuid.Parse(claims["sub"].(string))
			if err != nil {
				response.Error(w, http.StatusUnauthorized, "Invalid user ID in token")
				return
			}

			orgID, err := uuid.Parse(claims["orgId"].(string))
			if err != nil {
				response.Error(w, http.StatusUnauthorized, "Invalid organization ID in token")
				return
			}

			// Add user info to context
			ctx := context.WithValue(r.Context(), "userID", userID)
			ctx = context.WithValue(ctx, "orgID", orgID)
			ctx = context.WithValue(ctx, "userEmail", claims["email"].(string))
			ctx = context.WithValue(ctx, "userRole", claims["role"].(string))

			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// RequireRole middleware checks if user has required role
func RequireRole(roles ...string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			userRole := r.Context().Value("userRole").(string)

			for _, role := range roles {
				if userRole == role {
					next.ServeHTTP(w, r)
					return
				}
			}

			response.Error(w, http.StatusForbidden, "Insufficient permissions")
		})
	}
}
