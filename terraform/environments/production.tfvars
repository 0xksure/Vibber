# Production Environment Configuration

environment = "production"
region      = "nyc1"

# Kubernetes
kubernetes_version = "1.29.1-do.0"
node_size          = "s-4vcpu-8gb"
node_count         = 3
min_nodes          = 3
max_nodes          = 15

# Database
db_size    = "db-s-2vcpu-4gb"
cache_size = "db-s-2vcpu-4gb"

# Domain
domain     = "vibber.io"
manage_dns = true

# CORS
allowed_origins = [
  "https://app.vibber.io",
  "https://vibber.io",
  "https://www.vibber.io"
]

# Monitoring
enable_monitoring = true
