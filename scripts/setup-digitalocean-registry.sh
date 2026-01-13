#!/bin/bash

# DigitalOcean Container Registry Setup Script
# This script helps you set up a DigitalOcean Container Registry and configure GitHub secrets

set -e

echo "🚀 DigitalOcean Container Registry Setup for Vibber Project"
echo "=========================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo -e "${RED}❌ doctl is not installed. Please install it first:${NC}"
    echo "  macOS: brew install doctl"
    echo "  Ubuntu: snap install doctl"
    echo "  Or download from: https://github.com/digitalocean/doctl/releases"
    exit 1
fi

echo -e "${GREEN}✅ doctl is installed${NC}"

# Check if user is authenticated
if ! doctl account get &> /dev/null; then
    echo -e "${YELLOW}⚠️  You need to authenticate with DigitalOcean first${NC}"
    echo "Run: doctl auth init"
    echo "Then re-run this script"
    exit 1
fi

echo -e "${GREEN}✅ DigitalOcean authentication verified${NC}"

# Registry configuration
REGISTRY_NAME="vibber-registry"
SUBSCRIPTION_TIER="basic"

echo -e "${BLUE}📦 Creating DigitalOcean Container Registry...${NC}"

# Create the registry
if doctl registry create $REGISTRY_NAME --subscription-tier $SUBSCRIPTION_TIER; then
    echo -e "${GREEN}✅ Registry '$REGISTRY_NAME' created successfully!${NC}"
else
    echo -e "${YELLOW}⚠️  Registry might already exist or there was an error${NC}"
    echo "Checking existing registries..."
    doctl registry list
fi

# Get registry info
echo -e "${BLUE}📋 Registry Information:${NC}"
doctl registry get $REGISTRY_NAME

# Generate access token instructions
echo ""
echo -e "${YELLOW}🔑 Next Steps - GitHub Secrets Setup:${NC}"
echo "========================================="
echo ""
echo "1. Create a DigitalOcean Personal Access Token:"
echo "   - Go to: https://cloud.digitalocean.com/account/api/tokens"
echo "   - Click 'Generate New Token'"
echo "   - Name: 'GitHub Actions Vibber'"
echo "   - Scopes: Read + Write"
echo "   - Copy the token (you won't see it again!)"
echo ""
echo "2. Set GitHub Repository Secrets:"
echo "   - Go to: https://github.com/0xksure/Vibber/settings/secrets/actions"
echo "   - Add these secrets:"
echo ""
echo -e "   ${GREEN}DIGITALOCEAN_ACCESS_TOKEN${NC}"
echo "   └── Value: [Your Personal Access Token from step 1]"
echo ""
echo -e "   ${GREEN}DO_REGISTRY_NAME${NC}"
echo "   └── Value: $REGISTRY_NAME"
echo ""
echo "3. Test the setup:"
echo "   - Push a commit to main/master branch"
echo "   - Check GitHub Actions tab for workflow execution"
echo ""
echo -e "${GREEN}🎉 Setup complete! Your workflow should now work automatically.${NC}"
echo ""
echo "Registry URL: registry.digitalocean.com/$REGISTRY_NAME"
echo "Image will be pushed as: registry.digitalocean.com/$REGISTRY_NAME/vibber-app:latest"