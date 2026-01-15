# Vibber Terraform Outputs

# Kubernetes Cluster
output "kubernetes_cluster_id" {
  description = "ID of the Kubernetes cluster"
  value       = digitalocean_kubernetes_cluster.vibber.id
}

output "kubernetes_cluster_name" {
  description = "Name of the Kubernetes cluster"
  value       = digitalocean_kubernetes_cluster.vibber.name
}

output "kubernetes_endpoint" {
  description = "Kubernetes API endpoint"
  value       = digitalocean_kubernetes_cluster.vibber.endpoint
  sensitive   = true
}

output "kubeconfig" {
  description = "Kubernetes configuration"
  value       = digitalocean_kubernetes_cluster.vibber.kube_config[0].raw_config
  sensitive   = true
}

# Database
output "database_host" {
  description = "PostgreSQL database host"
  value       = digitalocean_database_cluster.postgres.private_host
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

output "database_password" {
  description = "PostgreSQL database password"
  value       = digitalocean_database_user.vibber.password
  sensitive   = true
}

output "database_uri" {
  description = "PostgreSQL connection URI"
  value       = digitalocean_database_cluster.postgres.private_uri
  sensitive   = true
}

# Redis
output "redis_host" {
  description = "Redis host"
  value       = digitalocean_database_cluster.redis.private_host
}

output "redis_port" {
  description = "Redis port"
  value       = digitalocean_database_cluster.redis.port
}

output "redis_uri" {
  description = "Redis connection URI"
  value       = digitalocean_database_cluster.redis.private_uri
  sensitive   = true
}

# Container Registry
output "registry_endpoint" {
  description = "Container registry endpoint"
  value       = digitalocean_container_registry.vibber.endpoint
}

output "registry_name" {
  description = "Container registry name"
  value       = digitalocean_container_registry.vibber.name
}

# Load Balancer
output "load_balancer_ip" {
  description = "Load balancer IP address"
  value       = digitalocean_loadbalancer.vibber.ip
}

output "load_balancer_id" {
  description = "Load balancer ID"
  value       = digitalocean_loadbalancer.vibber.id
}

# Spaces
output "spaces_bucket_name" {
  description = "Spaces bucket name"
  value       = digitalocean_spaces_bucket.vibber.name
}

output "spaces_bucket_urn" {
  description = "Spaces bucket URN"
  value       = digitalocean_spaces_bucket.vibber.urn
}

output "spaces_endpoint" {
  description = "Spaces bucket endpoint"
  value       = digitalocean_spaces_bucket.vibber.bucket_domain_name
}

output "cdn_endpoint" {
  description = "CDN endpoint"
  value       = digitalocean_cdn.vibber.endpoint
}

# VPC
output "vpc_id" {
  description = "VPC ID"
  value       = digitalocean_vpc.vibber.id
}

output "vpc_urn" {
  description = "VPC URN"
  value       = digitalocean_vpc.vibber.urn
}

# URLs
output "app_url" {
  description = "Application URL"
  value       = "https://app.${var.domain}"
}

output "api_url" {
  description = "API URL"
  value       = "https://api.${var.domain}"
}

# Project
output "project_id" {
  description = "DigitalOcean project ID"
  value       = digitalocean_project.vibber.id
}
