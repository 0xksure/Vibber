# Vibber Infrastructure on DigitalOcean
# Terraform configuration for deploying the complete Vibber platform

terraform {
  required_version = ">= 1.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.34"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
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

# VPC for network isolation
resource "digitalocean_vpc" "vibber" {
  name     = "vibber-vpc-${var.environment}"
  region   = var.region
  ip_range = "10.10.0.0/16"
}

# Container Registry
resource "digitalocean_container_registry" "vibber" {
  name                   = "vibber"
  subscription_tier_slug = var.environment == "production" ? "professional" : "starter"
  region                 = var.region
}

# Kubernetes Cluster
resource "digitalocean_kubernetes_cluster" "vibber" {
  name    = "vibber-k8s-${var.environment}"
  region  = var.region
  version = var.kubernetes_version
  vpc_uuid = digitalocean_vpc.vibber.id

  node_pool {
    name       = "default-pool"
    size       = var.node_size
    node_count = var.node_count
    auto_scale = true
    min_nodes  = var.min_nodes
    max_nodes  = var.max_nodes

    labels = {
      environment = var.environment
      service     = "vibber"
    }

    tags = ["vibber", var.environment]
  }

  maintenance_policy {
    start_time = "04:00"
    day        = "sunday"
  }

  tags = ["vibber", var.environment]
}

# Managed PostgreSQL Database
resource "digitalocean_database_cluster" "postgres" {
  name       = "vibber-db-${var.environment}"
  engine     = "pg"
  version    = "16"
  size       = var.db_size
  region     = var.region
  node_count = var.environment == "production" ? 2 : 1

  private_network_uuid = digitalocean_vpc.vibber.id

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

# Firewall for database - only allow from K8s cluster
resource "digitalocean_database_firewall" "vibber" {
  cluster_id = digitalocean_database_cluster.postgres.id

  rule {
    type  = "k8s"
    value = digitalocean_kubernetes_cluster.vibber.id
  }
}

# Managed Redis Cache
resource "digitalocean_database_cluster" "redis" {
  name       = "vibber-cache-${var.environment}"
  engine     = "redis"
  version    = "7"
  size       = var.cache_size
  region     = var.region
  node_count = 1

  private_network_uuid = digitalocean_vpc.vibber.id

  tags = ["vibber", var.environment]
}

# Redis Firewall
resource "digitalocean_database_firewall" "redis" {
  cluster_id = digitalocean_database_cluster.redis.id

  rule {
    type  = "k8s"
    value = digitalocean_kubernetes_cluster.vibber.id
  }
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

# CDN for Spaces
resource "digitalocean_cdn" "vibber" {
  origin           = digitalocean_spaces_bucket.vibber.bucket_domain_name
  custom_domain    = var.cdn_domain
  certificate_name = var.cdn_certificate_name

  ttl = 3600
}

# Load Balancer for the cluster
resource "digitalocean_loadbalancer" "vibber" {
  name   = "vibber-lb-${var.environment}"
  region = var.region

  vpc_uuid = digitalocean_vpc.vibber.id

  forwarding_rule {
    entry_port     = 443
    entry_protocol = "https"

    target_port     = 30080
    target_protocol = "http"

    certificate_name = var.ssl_certificate_name
  }

  forwarding_rule {
    entry_port     = 80
    entry_protocol = "http"

    target_port     = 30080
    target_protocol = "http"
  }

  healthcheck {
    port     = 30080
    protocol = "http"
    path     = "/health"
  }

  redirect_http_to_https = true
  enable_proxy_protocol  = true

  droplet_tag = "vibber"
}

# Domain Records
resource "digitalocean_domain" "vibber" {
  count = var.manage_dns ? 1 : 0
  name  = var.domain
}

resource "digitalocean_record" "app" {
  count  = var.manage_dns ? 1 : 0
  domain = digitalocean_domain.vibber[0].id
  type   = "A"
  name   = "app"
  value  = digitalocean_loadbalancer.vibber.ip
  ttl    = 300
}

resource "digitalocean_record" "api" {
  count  = var.manage_dns ? 1 : 0
  domain = digitalocean_domain.vibber[0].id
  type   = "A"
  name   = "api"
  value  = digitalocean_loadbalancer.vibber.ip
  ttl    = 300
}

# Project to organize resources
resource "digitalocean_project" "vibber" {
  name        = "Vibber ${title(var.environment)}"
  description = "Vibber AI Agent Cloning Platform - ${var.environment}"
  purpose     = "Service or API"
  environment = var.environment == "production" ? "Production" : "Development"

  resources = [
    digitalocean_kubernetes_cluster.vibber.urn,
    digitalocean_database_cluster.postgres.urn,
    digitalocean_database_cluster.redis.urn,
    digitalocean_loadbalancer.vibber.urn,
    digitalocean_spaces_bucket.vibber.urn,
  ]
}

# Configure Kubernetes provider after cluster creation
provider "kubernetes" {
  host  = digitalocean_kubernetes_cluster.vibber.endpoint
  token = digitalocean_kubernetes_cluster.vibber.kube_config[0].token
  cluster_ca_certificate = base64decode(
    digitalocean_kubernetes_cluster.vibber.kube_config[0].cluster_ca_certificate
  )
}

provider "helm" {
  kubernetes {
    host  = digitalocean_kubernetes_cluster.vibber.endpoint
    token = digitalocean_kubernetes_cluster.vibber.kube_config[0].token
    cluster_ca_certificate = base64decode(
      digitalocean_kubernetes_cluster.vibber.kube_config[0].cluster_ca_certificate
    )
  }
}

# Install NGINX Ingress Controller
resource "helm_release" "nginx_ingress" {
  name             = "nginx-ingress"
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  namespace        = "ingress-nginx"
  create_namespace = true
  version          = "4.9.0"

  set {
    name  = "controller.service.type"
    value = "NodePort"
  }

  set {
    name  = "controller.service.nodePorts.http"
    value = "30080"
  }

  set {
    name  = "controller.service.nodePorts.https"
    value = "30443"
  }

  depends_on = [digitalocean_kubernetes_cluster.vibber]
}

# Install cert-manager for TLS certificates
resource "helm_release" "cert_manager" {
  name             = "cert-manager"
  repository       = "https://charts.jetstack.io"
  chart            = "cert-manager"
  namespace        = "cert-manager"
  create_namespace = true
  version          = "v1.14.0"

  set {
    name  = "installCRDs"
    value = "true"
  }

  depends_on = [digitalocean_kubernetes_cluster.vibber]
}

# Monitoring with Prometheus and Grafana
resource "helm_release" "prometheus_stack" {
  count            = var.enable_monitoring ? 1 : 0
  name             = "prometheus"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = "monitoring"
  create_namespace = true
  version          = "56.0.0"

  values = [
    <<-EOT
    grafana:
      adminPassword: ${var.grafana_admin_password}
      ingress:
        enabled: true
        hosts:
          - grafana.${var.domain}
    prometheus:
      prometheusSpec:
        retention: 15d
        storageSpec:
          volumeClaimTemplate:
            spec:
              accessModes: ["ReadWriteOnce"]
              resources:
                requests:
                  storage: 50Gi
    EOT
  ]

  depends_on = [helm_release.nginx_ingress]
}
