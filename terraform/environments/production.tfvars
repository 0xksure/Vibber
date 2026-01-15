# Production Environment Configuration

environment = "production"
region      = "nyc1"
app_region  = "nyc"

# App Platform - using basic-xs for cost efficiency
# Options: basic-xxs ($5), basic-xs ($10), basic-s ($20), professional-xs ($25)
app_instance_size = "basic-xs"

# Database - smallest production-ready sizes
db_size    = "db-s-1vcpu-2gb"
cache_size = "db-s-1vcpu-1gb"

# Domain
domain = "vibber.io"

# CORS
allowed_origins = [
  "https://app.vibber.io",
  "https://vibber.io",
  "https://www.vibber.io"
]
