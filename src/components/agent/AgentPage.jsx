import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentsApi } from '../../services/api';
import { useAgentStore } from '../../store/agentStore';
import {
  Bot,
  Settings,
  Zap,
  Brain,
  Shield,
  Clock,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import * as Slider from '@radix-ui/react-slider';
import * as Switch from '@radix-ui/react-switch';

function AgentAvatar({ status, size = 'lg' }) {
  const sizeClasses = {
    sm: 'w-12 h-12',
    md: 'w-16 h-16',
    lg: 'w-24 h-24',
  };

  const statusColors = {
    active: 'from-success-400 to-success-600',
    training: 'from-warning-400 to-warning-600',
    paused: 'from-neutral-400 to-neutral-600',
    error: 'from-error-400 to-error-600',
  };

  return (
    <div className={`relative ${sizeClasses[size]}`}>
      <div className={`absolute inset-0 rounded-full bg-gradient-to-br ${statusColors[status]} animate-pulse-slow opacity-50`} />
      <div className="absolute inset-1 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
        <Bot className="w-1/2 h-1/2 text-white" />
      </div>
      <div className={`absolute bottom-0 right-0 w-5 h-5 rounded-full border-2 border-white ${
        status === 'active' ? 'bg-success-500' :
        status === 'training' ? 'bg-warning-500' :
        status === 'error' ? 'bg-error-500' : 'bg-neutral-400'
      }`} />
    </div>
  );
}

function StatCard({ label, value, icon: Icon }) {
  return (
    <div className="p-4 bg-neutral-50 rounded-lg">
      <div className="flex items-center gap-2 text-neutral-500 mb-1">
        <Icon className="w-4 h-4" />
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="text-xl font-semibold text-neutral-900">{value}</p>
    </div>
  );
}

export default function AgentPage() {
  const queryClient = useQueryClient();
  const { selectedAgent, setSelectedAgent } = useAgentStore();
  const [confidenceThreshold, setConfidenceThreshold] = useState(70);
  const [autoMode, setAutoMode] = useState(false);

  // Fetch agents
  const { data: agents = [], isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const response = await agentsApi.list();
      return response.data;
    },
  });

  // Get agent status
  const { data: agentStatus } = useQuery({
    queryKey: ['agent', 'status', selectedAgent?.id],
    queryFn: async () => {
      const response = await agentsApi.getStatus(selectedAgent.id);
      return response.data;
    },
    enabled: !!selectedAgent?.id,
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Update agent settings
  const updateSettingsMutation = useMutation({
    mutationFn: async (settings) => {
      return agentsApi.updateSettings(selectedAgent.id, settings);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['agent', 'status', selectedAgent?.id]);
    },
  });

  // Train agent
  const trainMutation = useMutation({
    mutationFn: async () => {
      return agentsApi.train(selectedAgent.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['agent', 'status', selectedAgent?.id]);
    },
  });

  // Select first agent if none selected
  React.useEffect(() => {
    if (agents.length > 0 && !selectedAgent) {
      setSelectedAgent(agents[0]);
      setConfidenceThreshold(agents[0].confidenceThreshold || 70);
      setAutoMode(agents[0].autoMode || false);
    }
  }, [agents, selectedAgent, setSelectedAgent]);

  const handleConfidenceChange = (value) => {
    setConfidenceThreshold(value[0]);
    updateSettingsMutation.mutate({ confidence_threshold: value[0] });
  };

  const handleAutoModeChange = (checked) => {
    setAutoMode(checked);
    updateSettingsMutation.mutate({ auto_mode: checked });
  };

  // Mock data for demo
  const mockAgent = {
    id: 'demo-agent',
    name: 'My AI Clone',
    status: 'active',
    confidenceThreshold: 70,
    autoMode: false,
    createdAt: new Date().toISOString(),
  };

  const mockStatus = {
    todayInteractions: 47,
    successRate: 92,
    avgResponseTime: 1.2,
    confidenceScore: 85.3,
  };

  const agent = selectedAgent || mockAgent;
  const status = agentStatus || mockStatus;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900">My Agent</h2>
          <p className="text-neutral-500">Configure and train your AI clone</p>
        </div>
        <button
          onClick={() => trainMutation.mutate()}
          disabled={trainMutation.isPending}
          className="btn btn-primary"
        >
          {trainMutation.isPending ? (
            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Brain className="w-4 h-4 mr-2" />
          )}
          Train Agent
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agent profile */}
        <div className="lg:col-span-1">
          <div className="card p-6 text-center">
            <div className="flex justify-center mb-4">
              <AgentAvatar status={agent.status} />
            </div>
            <h3 className="text-xl font-semibold text-neutral-900">
              {agent.name || 'My AI Clone'}
            </h3>
            <p className="text-sm text-neutral-500 mb-4">
              Created {new Date(agent.createdAt).toLocaleDateString()}
            </p>
            <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
              agent.status === 'active' ? 'bg-success-100 text-success-700' :
              agent.status === 'training' ? 'bg-warning-100 text-warning-700' :
              'bg-neutral-100 text-neutral-700'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                agent.status === 'active' ? 'bg-success-500' :
                agent.status === 'training' ? 'bg-warning-500' :
                'bg-neutral-500'
              }`} />
              {agent.status === 'active' ? 'Active' :
               agent.status === 'training' ? 'Training' : 'Paused'}
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-2 gap-3 mt-6">
              <StatCard
                label="Today"
                value={status.todayInteractions}
                icon={Zap}
              />
              <StatCard
                label="Success Rate"
                value={`${status.successRate}%`}
                icon={Shield}
              />
              <StatCard
                label="Avg. Response"
                value={`${status.avgResponseTime}s`}
                icon={Clock}
              />
              <StatCard
                label="Confidence"
                value={`${status.confidenceScore}%`}
                icon={Brain}
              />
            </div>
          </div>
        </div>

        {/* Settings */}
        <div className="lg:col-span-2 space-y-6">
          {/* Confidence threshold */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-primary-100">
                <Shield className="w-5 h-5 text-primary-600" />
              </div>
              <div>
                <h4 className="font-semibold text-neutral-900">Confidence Threshold</h4>
                <p className="text-sm text-neutral-500">
                  Actions below this confidence level will be escalated for review
                </p>
              </div>
            </div>
            <div className="space-y-4">
              <Slider.Root
                className="relative flex items-center select-none touch-none w-full h-5"
                value={[confidenceThreshold]}
                onValueChange={handleConfidenceChange}
                max={100}
                step={5}
              >
                <Slider.Track className="bg-neutral-200 relative grow rounded-full h-2">
                  <Slider.Range className="absolute bg-primary-500 rounded-full h-full" />
                </Slider.Track>
                <Slider.Thumb
                  className="block w-5 h-5 bg-white border-2 border-primary-500 rounded-full shadow-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  aria-label="Confidence threshold"
                />
              </Slider.Root>
              <div className="flex justify-between text-sm">
                <span className="text-neutral-500">More autonomous</span>
                <span className="font-medium text-primary-600">{confidenceThreshold}%</span>
                <span className="text-neutral-500">More cautious</span>
              </div>
            </div>
          </div>

          {/* Auto mode */}
          <div className="card p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-warning-100">
                  <Sparkles className="w-5 h-5 text-warning-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-neutral-900">Autonomous Mode</h4>
                  <p className="text-sm text-neutral-500">
                    Allow agent to take actions automatically when confident
                  </p>
                </div>
              </div>
              <Switch.Root
                checked={autoMode}
                onCheckedChange={handleAutoModeChange}
                className="w-11 h-6 bg-neutral-200 rounded-full relative data-[state=checked]:bg-primary-500 outline-none cursor-pointer transition-colors"
              >
                <Switch.Thumb className="block w-5 h-5 bg-white rounded-full shadow-md transition-transform translate-x-0.5 will-change-transform data-[state=checked]:translate-x-[22px]" />
              </Switch.Root>
            </div>
            {autoMode && (
              <div className="mt-4 p-3 bg-warning-50 rounded-lg text-sm text-warning-700">
                <strong>Caution:</strong> When enabled, your agent will execute actions
                automatically for interactions above the confidence threshold.
              </div>
            )}
          </div>

          {/* Working hours */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-neutral-100">
                <Clock className="w-5 h-5 text-neutral-600" />
              </div>
              <div>
                <h4 className="font-semibold text-neutral-900">Working Hours</h4>
                <p className="text-sm text-neutral-500">
                  Set when your agent should be active
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Start Time
                </label>
                <input type="time" defaultValue="09:00" className="input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  End Time
                </label>
                <input type="time" defaultValue="17:00" className="input" />
              </div>
            </div>
            <p className="mt-3 text-xs text-neutral-500">
              Outside working hours, all interactions will be queued for review.
            </p>
          </div>

          {/* Personality preview */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-primary-100">
                <Brain className="w-5 h-5 text-primary-600" />
              </div>
              <div>
                <h4 className="font-semibold text-neutral-900">Personality Profile</h4>
                <p className="text-sm text-neutral-500">
                  How your agent has learned to communicate
                </p>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-neutral-600">Communication Style</span>
                <span className="text-sm font-medium">Professional & Helpful</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-neutral-600">Tone</span>
                <span className="text-sm font-medium">Friendly but Concise</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-neutral-600">Training Samples</span>
                <span className="text-sm font-medium">247 samples</span>
              </div>
            </div>
            <button className="mt-4 w-full btn btn-secondary">
              View Full Profile
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
