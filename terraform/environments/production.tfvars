# Production Environment Configuration - Cost Optimized

environment = "production"
region      = "nyc1"
app_region  = "nyc"

# App Platform - cheapest option ($5/service/month)
app_instance_size = "basic-xxs"

# Database - cheapest options (~$15/month each)
db_size    = "db-s-1vcpu-1gb"
cache_size = "db-s-1vcpu-1gb"

# Domain
domain = "vibber.io"

# CORS
allowed_origins = [
  "https://app.vibber.io",
  "https://vibber.io",
  "https://www.vibber.io"
]
