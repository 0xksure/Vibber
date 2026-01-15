# Vibber Terraform Outputs

# App Platform
output "app_url" {
  description = "Default URL for the App Platform app"
  value       = digitalocean_app.vibber.default_ingress
}

output "app_live_url" {
  description = "Live URL for the App Platform app"
  value       = digitalocean_app.vibber.live_url
}

output "app_id" {
  description = "App Platform app ID"
  value       = digitalocean_app.vibber.id
}

# Database
output "database_host" {
  description = "PostgreSQL database host"
  value       = digitalocean_database_cluster.postgres.host
  sensitive   = true
}

output "database_port" {
  description = "PostgreSQL database port"
  value       = digitalocean_database_cluster.postgres.port
}

output "database_name" {
  description = "PostgreSQL database name"
  value       = digitalocean_database_db.vibber.name
}

output "database_user" {
  description = "PostgreSQL database user"
  value       = digitalocean_database_user.vibber.name
}

output "database_uri" {
  description = "PostgreSQL connection URI"
  value       = digitalocean_database_cluster.postgres.uri
  sensitive   = true
}

# Redis
output "redis_host" {
  description = "Redis host"
  value       = digitalocean_database_cluster.redis.host
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = digitalocean_database_cluster.redis.port
}

output "redis_uri" {
  description = "Redis connection URI"
  value       = digitalocean_database_cluster.redis.uri
  sensitive   = true
}

# Storage
output "spaces_bucket_name" {
  description = "Spaces bucket name"
  value       = digitalocean_spaces_bucket.vibber.name
}

output "spaces_bucket_domain" {
  description = "Spaces bucket domain"
  value       = digitalocean_spaces_bucket.vibber.bucket_domain_name
}

# Container Registry
output "registry_endpoint" {
  description = "Container registry endpoint"
  value       = digitalocean_container_registry.vibber.endpoint
}

output "registry_server_url" {
  description = "Container registry server URL"
  value       = digitalocean_container_registry.vibber.server_url
}

# Project
output "project_id" {
  description = "DigitalOcean project ID"
  value       = digitalocean_project.vibber.id
}

# Summary
output "deployment_info" {
  description = "Deployment information summary"
  value = {
    environment = var.environment
    app_url     = digitalocean_app.vibber.live_url
    region      = var.app_region
    services = {
      frontend = "Running on App Platform"
      backend  = "Running on App Platform"
      ai_agent = "Running on App Platform"
    }
    databases = {
      postgres = digitalocean_database_cluster.postgres.name
      redis    = digitalocean_database_cluster.redis.name
    }
  }
}
