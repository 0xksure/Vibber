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
  description = "DigitalOcean region"
  type        = string
  default     = "nyc1"
}

variable "spaces_region" {
  description = "DigitalOcean Spaces region"
  type        = string
  default     = "nyc3"
}

# Kubernetes Configuration
variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.29.1-do.0"
}

variable "node_size" {
  description = "Droplet size for Kubernetes nodes"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "node_count" {
  description = "Initial number of nodes in the cluster"
  type        = number
  default     = 3
}

variable "min_nodes" {
  description = "Minimum number of nodes for autoscaling"
  type        = number
  default     = 2
}

variable "max_nodes" {
  description = "Maximum number of nodes for autoscaling"
  type        = number
  default     = 10
}

# Database Configuration
variable "db_size" {
  description = "Database droplet size"
  type        = string
  default     = "db-s-1vcpu-1gb"
}

variable "cache_size" {
  description = "Redis cache droplet size"
  type        = string
  default     = "db-s-1vcpu-1gb"
}

# Domain Configuration
variable "domain" {
  description = "Primary domain for Vibber"
  type        = string
  default     = "vibber.io"
}

variable "manage_dns" {
  description = "Whether Terraform should manage DNS records"
  type        = bool
  default     = false
}

variable "ssl_certificate_name" {
  description = "Name of the SSL certificate in DigitalOcean"
  type        = string
  default     = ""
}

variable "cdn_domain" {
  description = "Custom domain for CDN"
  type        = string
  default     = ""
}

variable "cdn_certificate_name" {
  description = "Certificate name for CDN custom domain"
  type        = string
  default     = ""
}

variable "allowed_origins" {
  description = "Allowed origins for CORS on Spaces bucket"
  type        = list(string)
  default     = ["https://app.vibber.io", "https://vibber.io"]
}

# Monitoring
variable "enable_monitoring" {
  description = "Enable Prometheus/Grafana monitoring stack"
  type        = bool
  default     = true
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
  default     = "admin"
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

# OAuth Credentials
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
