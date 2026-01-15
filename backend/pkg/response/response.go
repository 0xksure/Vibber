package response

import (
	"encoding/json"
	"net/http"
)

// JSON sends a JSON response
func JSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

// Error sends an error response
func Error(w http.ResponseWriter, status int, message string) {
	JSON(w, status, map[string]interface{}{
		"error":   true,
		"message": message,
		"status":  status,
	})
}

// Success sends a success response
func Success(w http.ResponseWriter, message string, data interface{}) {
	JSON(w, http.StatusOK, map[string]interface{}{
		"success": true,
		"message": message,
		"data":    data,
	})
}

// Paginated sends a paginated response
func Paginated(w http.ResponseWriter, data interface{}, page, pageSize, total int) {
	totalPages := (total + pageSize - 1) / pageSize

	JSON(w, http.StatusOK, map[string]interface{}{
		"data":       data,
		"page":       page,
		"pageSize":   pageSize,
		"totalItems": total,
		"totalPages": totalPages,
	})
}
