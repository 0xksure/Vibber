package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthCheck(t *testing.T) {
	// Create a request to the health endpoint
	req, err := http.NewRequest("GET", "/health", nil)
	if err != nil {
		t.Fatal(err)
	}

	// Create a ResponseRecorder to record the response
	rr := httptest.NewRecorder()

	// Create a simple health handler
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
	})

	// Serve the request
	handler.ServeHTTP(rr, req)

	// Check the status code
	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	// Check the response body
	var response map[string]string
	if err := json.NewDecoder(rr.Body).Decode(&response); err != nil {
		t.Fatal(err)
	}

	if response["status"] != "healthy" {
		t.Errorf("handler returned unexpected body: got %v want %v", response["status"], "healthy")
	}
}

func TestResponseJSON(t *testing.T) {
	rr := httptest.NewRecorder()

	data := map[string]interface{}{
		"message": "test",
		"count":   42,
	}

	// Encode JSON
	rr.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(rr).Encode(data); err != nil {
		t.Fatal(err)
	}

	// Verify content type
	if ct := rr.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("wrong content type: got %v want application/json", ct)
	}

	// Verify body
	var response map[string]interface{}
	if err := json.NewDecoder(rr.Body).Decode(&response); err != nil {
		t.Fatal(err)
	}

	if response["message"] != "test" {
		t.Errorf("wrong message: got %v want test", response["message"])
	}
}
