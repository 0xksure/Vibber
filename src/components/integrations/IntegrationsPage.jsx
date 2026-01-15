import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { integrationsApi } from '../../services/api';
import {
  MessageSquare,
  Github,
  FileText,
  Search,
  CheckCircle,
  XCircle,
  ExternalLink,
  Plus,
} from 'lucide-react';

const integrationsList = [
  {
    id: 'slack',
    name: 'Slack',
    description: 'Respond to messages, mentions, and handle support requests',
    icon: MessageSquare,
    color: 'bg-[#4A154B]',
    features: ['Auto-reply to DMs', 'Handle @mentions', 'Thread responses', 'Emoji reactions'],
  },
  {
    id: 'github',
    name: 'GitHub',
    description: 'Review PRs, comment on issues, and manage code reviews',
    icon: Github,
    color: 'bg-neutral-900',
    features: ['PR reviews', 'Code comments', 'Issue triage', 'Label management'],
  },
  {
    id: 'jira',
    name: 'Jira',
    description: 'Update tickets, manage workflows, and track progress',
    icon: FileText,
    color: 'bg-[#0052CC]',
    features: ['Ticket updates', 'Status changes', 'Comment replies', 'Assignment'],
  },
  {
    id: 'confluence',
    name: 'Confluence',
    description: 'Search documentation and answer questions from knowledge base',
    icon: FileText,
    color: 'bg-[#172B4D]',
    features: ['Knowledge search', 'Page updates', 'Comment management'],
  },
  {
    id: 'elastic',
    name: 'Elasticsearch',
    description: 'Monitor logs, detect errors, and create alerts',
    icon: Search,
    color: 'bg-[#00BFB3]',
    features: ['Log monitoring', 'Error detection', 'Alert creation', 'RCA analysis'],
  },
];

function IntegrationCard({ integration, isConnected, onConnect, onDisconnect }) {
  const Icon = integration.icon;

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-3 rounded-lg ${integration.color}`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-neutral-900">{integration.name}</h3>
            <p className="text-sm text-neutral-500">{integration.description}</p>
          </div>
        </div>
        {isConnected ? (
          <div className="flex items-center gap-1 text-success-600">
            <CheckCircle className="w-5 h-5" />
            <span className="text-sm font-medium">Connected</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-neutral-400">
            <XCircle className="w-5 h-5" />
            <span className="text-sm">Not connected</span>
          </div>
        )}
      </div>

      <div className="mb-4">
        <p className="text-xs text-neutral-500 mb-2">Capabilities:</p>
        <div className="flex flex-wrap gap-2">
          {integration.features.map((feature) => (
            <span
              key={feature}
              className="px-2 py-1 text-xs bg-neutral-100 text-neutral-600 rounded"
            >
              {feature}
            </span>
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        {isConnected ? (
          <>
            <button className="flex-1 btn btn-secondary">
              <ExternalLink className="w-4 h-4 mr-2" />
              Configure
            </button>
            <button
              onClick={() => onDisconnect(integration.id)}
              className="btn btn-ghost text-error-600 hover:bg-error-50"
            >
              Disconnect
            </button>
          </>
        ) : (
          <button
            onClick={() => onConnect(integration.id)}
            className="flex-1 btn btn-primary"
          >
            <Plus className="w-4 h-4 mr-2" />
            Connect
          </button>
        )}
      </div>
    </div>
  );
}

export default function IntegrationsPage() {
  // Fetch connected integrations
  const { data: connectedIntegrations = [] } = useQuery({
    queryKey: ['integrations'],
    queryFn: async () => {
      const response = await integrationsApi.list();
      return response.data;
    },
  });

  // For demo, show Slack as connected
  const connectedProviders = new Set(
    connectedIntegrations.map((i) => i.integration?.provider || i.provider) || ['slack']
  );

  const handleConnect = async (provider) => {
    // In production, this would redirect to OAuth flow
    window.location.href = `/api/v1/integrations/${provider}/connect?agent_id=demo-agent`;
  };

  const handleDisconnect = async (provider) => {
    // Find integration and disconnect
    const integration = connectedIntegrations.find(
      (i) => i.integration?.provider === provider || i.provider === provider
    );
    if (integration) {
      await integrationsApi.disconnect(integration.id);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-neutral-900">Integrations</h2>
        <p className="text-neutral-500">
          Connect your agent to the tools you use every day
        </p>
      </div>

      {/* Connection status */}
      <div className="card p-4 bg-primary-50 border-primary-200">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary-100">
            <CheckCircle className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <p className="font-medium text-primary-900">
              {connectedProviders.size || 1} integration{connectedProviders.size !== 1 ? 's' : ''} connected
            </p>
            <p className="text-sm text-primary-700">
              Your agent can interact with {connectedProviders.size || 1} service{connectedProviders.size !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Integrations grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {integrationsList.map((integration) => (
          <IntegrationCard
            key={integration.id}
            integration={integration}
            isConnected={connectedProviders.has(integration.id) || integration.id === 'slack'}
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
          />
        ))}
      </div>

      {/* Custom integration */}
      <div className="card p-6 border-dashed border-2 border-neutral-300 bg-neutral-50">
        <div className="text-center">
          <div className="inline-flex p-3 rounded-lg bg-neutral-200 mb-3">
            <Plus className="w-6 h-6 text-neutral-500" />
          </div>
          <h3 className="font-semibold text-neutral-900 mb-1">Custom Integration</h3>
          <p className="text-sm text-neutral-500 mb-4">
            Connect your agent to any service via webhooks or API
          </p>
          <button className="btn btn-secondary">Coming Soon</button>
        </div>
      </div>
    </div>
  );
}
