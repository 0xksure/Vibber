# Vibber Terraform Variables

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "region" {
  description = "DigitalOcean region for databases"
  type        = string
  default     = "nyc1"
}

variable "app_region" {
  description = "DigitalOcean App Platform region"
  type        = string
  default     = "nyc"
}

variable "spaces_region" {
  description = "DigitalOcean Spaces region"
  type        = string
  default     = "nyc3"
}

# App Platform Configuration
variable "app_instance_size" {
  description = "Instance size for App Platform services (basic-xxs is cheapest at $5/month)"
  type        = string
  default     = "basic-xxs"
}

# Database Configuration (cheapest options)
variable "db_size" {
  description = "Database droplet size (db-s-1vcpu-1gb is cheapest at ~$15/month)"
  type        = string
  default     = "db-s-1vcpu-1gb"
}

variable "cache_size" {
  description = "Redis cache droplet size (db-s-1vcpu-1gb is cheapest at ~$15/month)"
  type        = string
  default     = "db-s-1vcpu-1gb"
}

# Domain Configuration
variable "domain" {
  description = "Primary domain for Vibber"
  type        = string
  default     = "vibber.io"
}

variable "allowed_origins" {
  description = "Allowed origins for CORS on Spaces bucket"
  type        = list(string)
  default     = ["https://app.vibber.io", "https://vibber.io"]
}

# Application Configuration
variable "anthropic_api_key" {
  description = "Anthropic API key for AI agent"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openai_api_key" {
  description = "OpenAI API key for embeddings"
  type        = string
  sensitive   = true
  default     = ""
}

variable "mixpanel_token" {
  description = "Mixpanel token for analytics"
  type        = string
  sensitive   = true
  default     = ""
}

variable "jwt_secret" {
  description = "JWT secret for authentication"
  type        = string
  sensitive   = true
  default     = ""
}

variable "internal_service_key" {
  description = "Internal service key for agent-to-backend communication"
  type        = string
  sensitive   = true
  default     = ""
}

# OAuth Credentials (optional - can be set per-organization in the app)
variable "slack_client_id" {
  description = "Slack OAuth client ID"
  type        = string
  default     = ""
}

variable "slack_client_secret" {
  description = "Slack OAuth client secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "github_client_id" {
  description = "GitHub OAuth client ID"
  type        = string
  default     = ""
}

variable "github_client_secret" {
  description = "GitHub OAuth client secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "jira_client_id" {
  description = "Jira/Atlassian OAuth client ID"
  type        = string
  default     = ""
}

variable "jira_client_secret" {
  description = "Jira/Atlassian OAuth client secret"
  type        = string
  sensitive   = true
  default     = ""
}
