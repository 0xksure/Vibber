# DigitalOcean Container Registry Setup Guide

## Step 1: Create a DigitalOcean Container Registry

1. Log in to your DigitalOcean account
2. Navigate to "Container Registry" in the left sidebar
3. Click "Create Registry"
4. Choose a name for your registry (e.g., `vibber-registry`)
5. Select a subscription plan (Basic plan should be sufficient for most use cases)
6. Click "Create Registry"

## Step 2: Get Your DigitalOcean Access Token

1. Go to API section in DigitalOcean dashboard
2. Click "Generate New Token"
3. Give it a name (e.g., "GitHub Actions")
4. Select "Read" and "Write" scopes
5. Copy the generated token (you won't see it again)

## Step 3: Set GitHub Repository Secrets

You need to set the following secrets in your GitHub repository (`0xksure/Vibber`):

### Required Secrets:

1. **DIGITALOCEAN_ACCESS_TOKEN**
   - Value: The access token you generated in Step 2
   - This allows GitHub Actions to authenticate with DigitalOcean

2. **DO_REGISTRY_NAME**
   - Value: The name of your container registry (e.g., `vibber-registry`)
   - This is used in the Docker image tagging

### How to set GitHub secrets:

1. Go to your GitHub repository: https://github.com/0xksure/Vibber
2. Click on "Settings" tab
3. In the left sidebar, click "Secrets and variables" → "Actions"
4. Click "New repository secret"
5. Add each secret with the name and value as specified above

## Step 4: Registry Authentication (Optional Manual Test)

To test your setup locally:

```bash
# Install doctl (DigitalOcean CLI)
# On macOS: brew install doctl
# On Ubuntu: snap install doctl

# Authenticate
doctl auth init

# Login to registry
doctl registry login

# Build and push (example)
docker build -t registry.digitalocean.com/your-registry-name/vibber-app:latest .
docker push registry.digitalocean.com/your-registry-name/vibber-app:latest
```

## Current Workflow Status

Your current GitHub workflow (`.github/workflows/deploy.yml`) is already configured to:
- Run tests on every push/PR
- Build and push Docker images to DigitalOcean Container Registry on main/master branch
- Tag images with both commit SHA and 'latest'

Once you complete the above steps, your workflow should work automatically!