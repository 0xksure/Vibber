-- Vibber Database Schema
-- Version: 001
-- Description: Initial schema for AI Agent Cloning Platform

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector"; -- For embeddings (pgvector)

-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'starter' CHECK (plan IN ('starter', 'professional', 'enterprise')),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    avatar_url TEXT,
    role VARCHAR(50) DEFAULT 'member' CHECK (role IN ('admin', 'member', 'viewer')),
    provider VARCHAR(50), -- oauth provider (google, github, etc.)
    provider_id VARCHAR(255), -- external provider user id
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    UNIQUE(provider, provider_id)
);

-- Agents table (AI clones)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    avatar_url TEXT,
    status VARCHAR(50) DEFAULT 'training' CHECK (status IN ('training', 'active', 'paused', 'error')),
    confidence_threshold INTEGER DEFAULT 70 CHECK (confidence_threshold >= 0 AND confidence_threshold <= 100),
    auto_mode BOOLEAN DEFAULT FALSE,
    working_hours JSONB, -- e.g., {"timezone": "UTC", "start": "09:00", "end": "17:00", "days": [1,2,3,4,5]}
    personality_config JSONB DEFAULT '{}', -- Style preferences, tone, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Integrations table (connected services)
CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL CHECK (provider IN ('slack', 'github', 'jira', 'confluence', 'elastic', 'custom')),
    access_token TEXT NOT NULL, -- Encrypted
    refresh_token TEXT, -- Encrypted
    scopes TEXT[],
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'error', 'revoked')),
    external_id VARCHAR(255), -- External workspace/org ID
    metadata JSONB DEFAULT '{}', -- Provider-specific data
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(agent_id, provider)
);

-- Interactions table (agent activities)
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    integration_id UUID REFERENCES integrations(id) ON DELETE SET NULL,
    provider VARCHAR(50) NOT NULL,
    interaction_type VARCHAR(100) NOT NULL, -- message, pr_review, ticket_update, alert, etc.
    input_data JSONB NOT NULL, -- Original event data
    output_data JSONB, -- Agent's response/action
    confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'escalated', 'failed')),
    escalated BOOLEAN DEFAULT FALSE,
    human_feedback VARCHAR(50) CHECK (human_feedback IN ('approved', 'rejected', 'corrected')),
    processing_time INTEGER, -- milliseconds
    error_message TEXT,
    external_ref VARCHAR(255), -- External message/PR/ticket ID
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Escalations table
CREATE TABLE escalations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    interaction_id UUID NOT NULL REFERENCES interactions(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    priority VARCHAR(50) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'resolved', 'dismissed', 'expired')),
    context JSONB, -- Additional context for the human
    proposed_action JSONB, -- What the agent wanted to do
    resolution TEXT,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ, -- Auto-expire if not resolved
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Training samples table (for personality learning)
CREATE TABLE training_samples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    provider VARCHAR(50),
    sample_type VARCHAR(50) NOT NULL CHECK (sample_type IN ('message', 'response', 'style', 'domain', 'correction', 'negative')),
    input_text TEXT NOT NULL,
    output_text TEXT,
    embedding VECTOR(1536), -- OpenAI embedding dimension
    is_positive BOOLEAN DEFAULT TRUE,
    source VARCHAR(100), -- Where the sample came from
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent knowledge base (RAG storage)
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    provider VARCHAR(50),
    source_type VARCHAR(100) NOT NULL, -- confluence_page, slack_history, github_readme, etc.
    source_id VARCHAR(255), -- External ID of the source
    title VARCHAR(500),
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}',
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Billing/subscription table
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'past_due', 'trialing')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage tracking table
CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    metric_type VARCHAR(100) NOT NULL, -- interactions, api_calls, tokens_used, etc.
    quantity INTEGER NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_agents_user_id ON agents(user_id);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_integrations_agent_id ON integrations(agent_id);
CREATE INDEX idx_integrations_provider ON integrations(provider);
CREATE INDEX idx_interactions_agent_id ON interactions(agent_id);
CREATE INDEX idx_interactions_created_at ON interactions(created_at DESC);
CREATE INDEX idx_interactions_status ON interactions(status);
CREATE INDEX idx_interactions_provider ON interactions(provider);
CREATE INDEX idx_escalations_agent_id ON escalations(agent_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_priority ON escalations(priority);
CREATE INDEX idx_training_samples_agent_id ON training_samples(agent_id);
CREATE INDEX idx_knowledge_base_agent_id ON knowledge_base(agent_id);
CREATE INDEX idx_audit_logs_org_id ON audit_logs(org_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Vector indexes for similarity search (using IVFFlat)
CREATE INDEX idx_training_samples_embedding ON training_samples USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Trigger for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
