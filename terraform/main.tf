# Vibber Infrastructure on DigitalOcean
# Terraform configuration using App Platform (simpler and cheaper than K8s)

terraform {
  required_version = ">= 1.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.34"
    }
  }

  backend "s3" {
    endpoint                    = "nyc3.digitaloceanspaces.com"
    key                         = "terraform/vibber/terraform.tfstate"
    bucket                      = "vibber-terraform-state"
    region                      = "us-east-1"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_requesting_account_id  = true
    skip_s3_checksum            = true
  }
}

provider "digitalocean" {
  token = var.do_token
}

# Container Registry for storing Docker images
resource "digitalocean_container_registry" "vibber" {
  name                   = "vibber"
  subscription_tier_slug = var.environment == "production" ? "professional" : "starter"
  region                 = var.region
}

# Connect registry to App Platform
resource "digitalocean_container_registry_docker_credentials" "vibber" {
  registry_name = digitalocean_container_registry.vibber.name
}

# Managed PostgreSQL Database (single node for cost savings)
resource "digitalocean_database_cluster" "postgres" {
  name       = "vibber-db-${var.environment}"
  engine     = "pg"
  version    = "16"
  size       = var.db_size
  region     = var.region
  node_count = 1

  maintenance_window {
    hour = 2
    day  = "sunday"
  }

  tags = ["vibber", var.environment]
}

# Database for Vibber
resource "digitalocean_database_db" "vibber" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "vibber"
}

# Database User
resource "digitalocean_database_user" "vibber" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "vibber_app"
}

# Managed Redis Cache
resource "digitalocean_database_cluster" "redis" {
  name       = "vibber-cache-${var.environment}"
  engine     = "redis"
  version    = "7"
  size       = var.cache_size
  region     = var.region
  node_count = 1

  tags = ["vibber", var.environment]
}

# Spaces bucket for file storage
resource "digitalocean_spaces_bucket" "vibber" {
  name   = "vibber-storage-${var.environment}"
  region = var.spaces_region
  acl    = "private"

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE"]
    allowed_origins = var.allowed_origins
    max_age_seconds = 3000
  }

  lifecycle_rule {
    enabled = true

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      days = 30
    }
  }
}

# App Platform App - Main Vibber Application
resource "digitalocean_app" "vibber" {
  spec {
    name   = "vibber-${var.environment}"
    region = var.app_region

    # Domain configuration
    domain {
      name = var.environment == "production" ? "app.${var.domain}" : "${var.environment}.${var.domain}"
      type = "PRIMARY"
    }

    # Frontend Service (single instance for cost savings)
    service {
      name               = "frontend"
      instance_count     = 1
      instance_size_slug = var.app_instance_size
      http_port          = 80

      image {
        registry_type = "DOCR"
        registry      = digitalocean_container_registry.vibber.name
        repository    = "frontend"
        tag           = "latest"
        deploy_on_push {
          enabled = true
        }
      }

      env {
        key   = "REACT_APP_API_URL"
        value = "https://api.${var.domain}"
      }

      env {
        key   = "REACT_APP_MIXPANEL_TOKEN"
        value = var.mixpanel_token
        type  = "SECRET"
      }

      health_check {
        http_path = "/"
      }

      routes {
        path = "/"
      }
    }

    # Backend API Service (single instance for cost savings)
    service {
      name               = "backend"
      instance_count     = 1
      instance_size_slug = var.app_instance_size
      http_port          = 8080

      image {
        registry_type = "DOCR"
        registry      = digitalocean_container_registry.vibber.name
        repository    = "backend"
        tag           = "latest"
        deploy_on_push {
          enabled = true
        }
      }

      env {
        key   = "ENV"
        value = var.environment
      }

      env {
        key   = "PORT"
        value = "8080"
      }

      env {
        key   = "DATABASE_URL"
        value = digitalocean_database_cluster.postgres.uri
        type  = "SECRET"
      }

      env {
        key   = "REDIS_URL"
        value = digitalocean_database_cluster.redis.uri
        type  = "SECRET"
      }

      env {
        key   = "JWT_SECRET"
        value = var.jwt_secret
        type  = "SECRET"
      }

      env {
        key   = "INTERNAL_SERVICE_KEY"
        value = var.internal_service_key
        type  = "SECRET"
      }

      env {
        key   = "FRONTEND_URL"
        value = "https://app.${var.domain}"
      }

      env {
        key   = "AGENT_SERVICE_URL"
        value = "$${AI_AGENT.PRIVATE_URL}"
      }

      env {
        key   = "ANTHROPIC_API_KEY"
        value = var.anthropic_api_key
        type  = "SECRET"
      }

      health_check {
        http_path = "/health"
      }

      routes {
        path                 = "/api"
        preserve_path_prefix = true
      }
    }

    # AI Agent Service (single instance for cost savings)
    service {
      name               = "ai-agent"
      instance_count     = 1
      instance_size_slug = var.app_instance_size
      http_port          = 8000

      image {
        registry_type = "DOCR"
        registry      = digitalocean_container_registry.vibber.name
        repository    = "ai-agent"
        tag           = "latest"
        deploy_on_push {
          enabled = true
        }
      }

      env {
        key   = "ENV"
        value = var.environment
      }

      env {
        key   = "DATABASE_URL"
        value = digitalocean_database_cluster.postgres.uri
        type  = "SECRET"
      }

      env {
        key   = "REDIS_URL"
        value = digitalocean_database_cluster.redis.uri
        type  = "SECRET"
      }

      env {
        key   = "ANTHROPIC_API_KEY"
        value = var.anthropic_api_key
        type  = "SECRET"
      }

      env {
        key   = "OPENAI_API_KEY"
        value = var.openai_api_key
        type  = "SECRET"
      }

      env {
        key   = "BACKEND_URL"
        value = "$${BACKEND.PRIVATE_URL}"
      }

      env {
        key   = "INTERNAL_SERVICE_KEY"
        value = var.internal_service_key
        type  = "SECRET"
      }

      health_check {
        http_path = "/health"
      }

      routes {
        path                 = "/agent"
        preserve_path_prefix = true
      }
    }

    # Database connection (trusted sources)
    database {
      name         = "vibber-db"
      engine       = "PG"
      cluster_name = digitalocean_database_cluster.postgres.name
      production   = var.environment == "production"
    }

    # Alert for deployment failures
    alert {
      rule = "DEPLOYMENT_FAILED"
    }

    alert {
      rule = "DOMAIN_FAILED"
    }
  }
}

# Firewall for database - only allow from App Platform
resource "digitalocean_database_firewall" "postgres" {
  cluster_id = digitalocean_database_cluster.postgres.id

  rule {
    type  = "app"
    value = digitalocean_app.vibber.id
  }
}

# Redis Firewall - only allow from App Platform
resource "digitalocean_database_firewall" "redis" {
  cluster_id = digitalocean_database_cluster.redis.id

  rule {
    type  = "app"
    value = digitalocean_app.vibber.id
  }
}

# Project to organize resources
resource "digitalocean_project" "vibber" {
  name        = "Vibber ${title(var.environment)}"
  description = "Vibber AI Agent Cloning Platform - ${var.environment}"
  purpose     = "Service or API"
  environment = var.environment == "production" ? "Production" : "Development"

  resources = [
    digitalocean_app.vibber.urn,
    digitalocean_database_cluster.postgres.urn,
    digitalocean_database_cluster.redis.urn,
    digitalocean_spaces_bucket.vibber.urn,
  ]
}
