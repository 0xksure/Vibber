-- Vibber Database Schema
-- Version: 002
-- Description: Add organization OAuth credentials for integrations

-- Organization OAuth Credentials table
-- Stores OAuth app credentials (client_id, client_secret) per organization for each provider
-- This allows each organization to use their own OAuth apps for Slack, GitHub, Jira, etc.
CREATE TABLE organization_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL CHECK (provider IN ('slack', 'github', 'jira', 'confluence', 'elastic', 'google', 'custom')),

    -- OAuth App Credentials (encrypted at application level)
    client_id TEXT NOT NULL,
    client_secret TEXT NOT NULL,

    -- Additional provider-specific settings
    webhook_secret TEXT, -- For verifying incoming webhooks (Slack, GitHub)
    signing_secret TEXT, -- For request signing (Slack)

    -- Provider-specific configuration
    -- For Jira: site_url, cloud vs server
    -- For GitHub: enterprise_url if using GitHub Enterprise
    -- For Slack: workspace restrictions
    config JSONB DEFAULT '{}',

    -- Status and metadata
    is_active BOOLEAN DEFAULT TRUE,
    verified_at TIMESTAMPTZ, -- When credentials were last verified working
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Each org can only have one set of credentials per provider
    UNIQUE(org_id, provider)
);

-- Index for quick lookup
CREATE INDEX idx_org_credentials_org_id ON organization_credentials(org_id);
CREATE INDEX idx_org_credentials_provider ON organization_credentials(provider);
CREATE INDEX idx_org_credentials_active ON organization_credentials(org_id, provider) WHERE is_active = TRUE;

-- Trigger for updated_at
CREATE TRIGGER update_org_credentials_updated_at
    BEFORE UPDATE ON organization_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add org_id to integrations table for easier credential lookup
-- (Optional: if you want to directly link integrations to org credentials)
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS org_credential_id UUID REFERENCES organization_credentials(id) ON DELETE SET NULL;

-- Comment explaining the relationship
COMMENT ON TABLE organization_credentials IS 'Stores OAuth app credentials per organization. Organizations provide their own Slack, GitHub, Jira app credentials which are used when agents connect to these services.';
COMMENT ON COLUMN organization_credentials.client_id IS 'OAuth client ID / App ID';
COMMENT ON COLUMN organization_credentials.client_secret IS 'OAuth client secret (encrypted at application level)';
COMMENT ON COLUMN organization_credentials.webhook_secret IS 'Secret for verifying webhook payloads';
COMMENT ON COLUMN organization_credentials.signing_secret IS 'Signing secret for request verification (e.g., Slack)';
COMMENT ON COLUMN organization_credentials.config IS 'Provider-specific configuration (e.g., Jira site URL, GitHub Enterprise URL)';
