import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAgentStore } from '../../store/agentStore';
import { agentsApi, analyticsApi, escalationsApi } from '../../services/api';
import {
  Activity,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  Clock,
  MessageSquare,
  GitPullRequest,
  Ticket,
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

function MetricCard({ title, value, subtitle, icon: Icon, trend, color = 'primary' }) {
  const colorClasses = {
    primary: 'bg-primary-50 text-primary-600',
    success: 'bg-success-50 text-success-600',
    warning: 'bg-warning-50 text-warning-600',
    error: 'bg-error-50 text-error-600',
  };

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-neutral-500">{title}</p>
          <p className="mt-2 text-3xl font-semibold text-neutral-900">{value}</p>
          {subtitle && (
            <p className="mt-1 text-sm text-neutral-500">{subtitle}</p>
          )}
          {trend && (
            <div className="flex items-center gap-1 mt-2">
              <TrendingUp className="w-4 h-4 text-success-500" />
              <span className="text-sm text-success-600">{trend}</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

function ActivityItem({ type, provider, title, time, status }) {
  const providerIcons = {
    slack: MessageSquare,
    github: GitPullRequest,
    jira: Ticket,
  };

  const statusColors = {
    completed: 'text-success-500',
    escalated: 'text-warning-500',
    failed: 'text-error-500',
  };

  const Icon = providerIcons[provider] || Activity;

  return (
    <div className="flex items-start gap-3 py-3">
      <div className={`p-2 rounded-lg bg-neutral-100 ${statusColors[status] || 'text-neutral-500'}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-neutral-900 truncate">{title}</p>
        <p className="text-xs text-neutral-500">{provider} - {type}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-neutral-400">{time}</span>
        {status === 'completed' && <CheckCircle className="w-4 h-4 text-success-500" />}
        {status === 'escalated' && <AlertTriangle className="w-4 h-4 text-warning-500" />}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { selectedAgent } = useAgentStore();

  // Fetch agents
  const { data: agents = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const response = await agentsApi.list();
      return response.data;
    },
  });

  // Fetch analytics overview
  const { data: analytics } = useQuery({
    queryKey: ['analytics', 'overview', selectedAgent?.id],
    queryFn: async () => {
      const response = await analyticsApi.overview(selectedAgent?.id);
      return response.data;
    },
    enabled: !!selectedAgent?.id,
  });

  // Mock data for demo
  const mockAnalytics = {
    totalInteractions: 1247,
    todayInteractions: 47,
    autonomousRate: 89,
    pendingEscalations: 3,
    avgConfidenceScore: 85.3,
  };

  const mockTrends = [
    { date: 'Mon', interactions: 32, escalations: 4 },
    { date: 'Tue', interactions: 45, escalations: 3 },
    { date: 'Wed', interactions: 38, escalations: 5 },
    { date: 'Thu', interactions: 52, escalations: 2 },
    { date: 'Fri', interactions: 41, escalations: 3 },
    { date: 'Sat', interactions: 18, escalations: 1 },
    { date: 'Sun', interactions: 21, escalations: 0 },
  ];

  const mockActivities = [
    { type: 'message', provider: 'slack', title: 'Replied to @sarah in #support', time: '2m ago', status: 'completed' },
    { type: 'pr_review', provider: 'github', title: 'Reviewed PR #234 in backend repo', time: '15m ago', status: 'completed' },
    { type: 'ticket', provider: 'jira', title: 'Updated JIRA-1234 status', time: '32m ago', status: 'completed' },
    { type: 'message', provider: 'slack', title: 'Complex refund request - needs review', time: '45m ago', status: 'escalated' },
    { type: 'pr_review', provider: 'github', title: 'Commented on PR #231', time: '1h ago', status: 'completed' },
  ];

  const data = analytics || mockAnalytics;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900">Dashboard</h2>
          <p className="text-neutral-500">Monitor your AI agent's performance</p>
        </div>
        {agents.length === 0 && (
          <button className="btn btn-primary">Create Your Agent</button>
        )}
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Today's Interactions"
          value={data.todayInteractions}
          subtitle="Across all integrations"
          icon={Activity}
          trend="+12% from yesterday"
          color="primary"
        />
        <MetricCard
          title="Autonomous Rate"
          value={`${data.autonomousRate}%`}
          subtitle="Handled without escalation"
          icon={CheckCircle}
          color="success"
        />
        <MetricCard
          title="Pending Escalations"
          value={data.pendingEscalations}
          subtitle="Require your attention"
          icon={AlertTriangle}
          color={data.pendingEscalations > 0 ? 'warning' : 'success'}
        />
        <MetricCard
          title="Avg. Confidence"
          value={`${data.avgConfidenceScore?.toFixed(1)}%`}
          subtitle="Response confidence score"
          icon={TrendingUp}
          color="primary"
        />
      </div>

      {/* Charts and Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity chart */}
        <div className="lg:col-span-2 card p-6">
          <h3 className="text-lg font-semibold text-neutral-900 mb-4">
            Weekly Activity
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockTrends}>
                <defs>
                  <linearGradient id="colorInteractions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#71717A', fontSize: 12 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#71717A', fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #E4E4E7',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.07)',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="interactions"
                  stroke="#6366F1"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorInteractions)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent activity */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-neutral-900">
              Recent Activity
            </h3>
            <button className="text-sm text-primary-600 hover:text-primary-700 font-medium">
              View all
            </button>
          </div>
          <div className="divide-y divide-neutral-100">
            {mockActivities.map((activity, index) => (
              <ActivityItem key={index} {...activity} />
            ))}
          </div>
        </div>
      </div>

      {/* Escalations preview */}
      {data.pendingEscalations > 0 && (
        <div className="card p-6 border-l-4 border-l-warning-500">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-warning-100">
              <AlertTriangle className="w-6 h-6 text-warning-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-neutral-900">
                {data.pendingEscalations} items need your attention
              </h3>
              <p className="text-sm text-neutral-500">
                Your agent escalated some interactions that require human review
              </p>
            </div>
            <button className="btn btn-secondary">Review Now</button>
          </div>
        </div>
      )}
    </div>
  );
}
