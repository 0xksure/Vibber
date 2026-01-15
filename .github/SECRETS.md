# GitHub Secrets Configuration

This document lists all the secrets required for the CI/CD pipeline to work correctly.

## Required Secrets

Navigate to your repository settings: **Settings > Secrets and variables > Actions > New repository secret**

### DigitalOcean Secrets

| Secret Name | Description | How to Obtain |
|------------|-------------|---------------|
| `DIGITALOCEAN_ACCESS_TOKEN` | DigitalOcean API token for deploying infrastructure | [DigitalOcean API Tokens](https://cloud.digitalocean.com/account/api/tokens) - Create a new token with read/write access |
| `DIGITALOCEAN_CLUSTER_NAME` | Name of your Kubernetes cluster | The name you specified when creating the cluster (e.g., `vibber-k8s-production`) |

### AI Service Secrets

| Secret Name | Description | How to Obtain |
|------------|-------------|---------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude AI | [Anthropic Console](https://console.anthropic.com/) - Create API key |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | [OpenAI Platform](https://platform.openai.com/api-keys) - Create new secret key |

### Application Secrets

| Secret Name | Description | How to Obtain |
|------------|-------------|---------------|
| `JWT_SECRET` | Secret key for JWT token signing | Generate a secure random string: `openssl rand -hex 32` |
| `INTERNAL_SERVICE_KEY` | Secret key for AI agent to backend communication | Generate a secure random string: `openssl rand -hex 32` |
| `MIXPANEL_TOKEN` | Mixpanel project token for analytics | [Mixpanel Settings](https://mixpanel.com/settings/project) - Project Token |

### OAuth Integration Secrets

#### Slack
| Secret Name | Description | How to Obtain |
|------------|-------------|---------------|
| `SLACK_CLIENT_ID` | Slack OAuth app client ID | [Slack API Apps](https://api.slack.com/apps) - OAuth & Permissions |
| `SLACK_CLIENT_SECRET` | Slack OAuth app client secret | Same location as Client ID |
| `SLACK_SIGNING_SECRET` | Slack app signing secret | App Credentials > Signing Secret |

#### GitHub
| Secret Name | Description | How to Obtain |
|------------|-------------|---------------|
| `GITHUB_CLIENT_ID` | GitHub OAuth app client ID | [GitHub Developer Settings](https://github.com/settings/developers) - OAuth Apps |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app client secret | Same location as Client ID |

#### Jira/Atlassian
| Secret Name | Description | How to Obtain |
|------------|-------------|---------------|
| `JIRA_CLIENT_ID` | Atlassian OAuth app client ID | [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/) |
| `JIRA_CLIENT_SECRET` | Atlassian OAuth app client secret | Same location as Client ID |

## Setting Up Secrets via GitHub CLI

You can use the GitHub CLI to set secrets:

```bash
# Install GitHub CLI if not already installed
# https://cli.github.com/

# Login to GitHub
gh auth login

# Set secrets (replace with your actual values)
gh secret set DIGITALOCEAN_ACCESS_TOKEN --body "your-do-token"
gh secret set DIGITALOCEAN_CLUSTER_NAME --body "vibber-k8s-production"
gh secret set ANTHROPIC_API_KEY --body "sk-ant-..."
gh secret set OPENAI_API_KEY --body "sk-..."
gh secret set JWT_SECRET --body "$(openssl rand -hex 32)"
gh secret set INTERNAL_SERVICE_KEY --body "$(openssl rand -hex 32)"
gh secret set MIXPANEL_TOKEN --body "your-mixpanel-token"
gh secret set SLACK_CLIENT_ID --body "your-slack-client-id"
gh secret set SLACK_CLIENT_SECRET --body "your-slack-client-secret"
gh secret set SLACK_SIGNING_SECRET --body "your-slack-signing-secret"
gh secret set GITHUB_CLIENT_ID --body "your-github-client-id"
gh secret set GITHUB_CLIENT_SECRET --body "your-github-client-secret"
gh secret set JIRA_CLIENT_ID --body "your-jira-client-id"
gh secret set JIRA_CLIENT_SECRET --body "your-jira-client-secret"
```

## Environment-Specific Secrets

For multiple environments (staging, production), you can use GitHub Environments:

1. Go to **Settings > Environments**
2. Create environments: `staging`, `production`
3. Add environment-specific secrets to each environment

## Verifying Secrets

After setting up secrets, you can verify they're configured by:

1. Going to **Settings > Secrets and variables > Actions**
2. Checking that all required secrets are listed
3. Running a workflow manually to test

## Security Best Practices

1. **Never commit secrets** to the repository
2. **Rotate secrets** regularly (at least every 90 days)
3. **Use least privilege** - only grant necessary permissions
4. **Enable secret scanning** in repository settings
5. **Review access** - audit who has access to secrets

## Troubleshooting

### Common Issues

1. **"Secret not found" error**: Ensure the secret name matches exactly (case-sensitive)
2. **API authentication fails**: Check that the API key is valid and has correct permissions
3. **Deployment fails**: Verify DigitalOcean token has cluster access permissions

### Getting Help

- Check the [GitHub Actions documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- Review workflow run logs for specific error messages
- Contact support@vibber.io for platform-specific issues
