#!/bin/bash

# DigitalOcean Container Registry Setup Script
# This script helps you create a container registry and set up the necessary configuration

set -e

echo "🚀 DigitalOcean Container Registry Setup"
echo "========================================"

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl CLI is not installed. Please install it first:"
    echo "   macOS: brew install doctl"
    echo "   Ubuntu: snap install doctl"
    echo "   Or download from: https://github.com/digitalocean/doctl/releases"
    exit 1
fi

# Check if user is authenticated
if ! doctl account get &> /dev/null; then
    echo "❌ You are not authenticated with DigitalOcean."
    echo "   Please run: doctl auth init"
    exit 1
fi

echo "✅ doctl is installed and authenticated"

# Get registry name from user
read -p "Enter a name for your container registry (e.g., vibber-registry): " REGISTRY_NAME

if [ -z "$REGISTRY_NAME" ]; then
    echo "❌ Registry name cannot be empty"
    exit 1
fi

# Create the registry
echo "📦 Creating container registry: $REGISTRY_NAME"
if doctl registry create "$REGISTRY_NAME" --subscription-tier basic; then
    echo "✅ Registry created successfully!"
else
    echo "❌ Failed to create registry. It might already exist or there was an error."
    echo "   You can check existing registries with: doctl registry list"
fi

# Get the registry info
echo "📋 Registry Information:"
doctl registry get "$REGISTRY_NAME" || echo "Could not retrieve registry info"

echo ""
echo "🔑 Next Steps:"
echo "1. Get your DigitalOcean API token:"
echo "   - Go to https://cloud.digitalocean.com/account/api/tokens"
echo "   - Create a new token with read/write permissions"
echo ""
echo "2. Set GitHub repository secrets:"
echo "   - DIGITALOCEAN_ACCESS_TOKEN: [your API token]"
echo "   - DO_REGISTRY_NAME: $REGISTRY_NAME"
echo ""
echo "3. Your registry URL will be: registry.digitalocean.com/$REGISTRY_NAME"
echo ""
echo "✅ Setup complete! Your GitHub workflow should now work."