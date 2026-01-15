import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../../services/api';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  CheckCircle,
  AlertTriangle,
  Clock,
  MessageSquare,
  GitPullRequest,
  FileText,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

const COLORS = ['#6366F1', '#22C55E', '#F59E0B', '#EF4444'];

function MetricCard({ title, value, change, changeType, icon: Icon }) {
  const isPositive = changeType === 'positive';

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-neutral-500">{title}</span>
        <Icon className="w-5 h-5 text-neutral-400" />
      </div>
      <div className="flex items-end justify-between">
        <p className="text-3xl font-bold text-neutral-900">{value}</p>
        {change && (
          <div className={`flex items-center gap-1 text-sm ${
            isPositive ? 'text-success-600' : 'text-error-600'
          }`}>
            {isPositive ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            <span>{change}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState('7d');

  // Fetch analytics data
  const { data: overview } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: async () => {
      const response = await analyticsApi.overview();
      return response.data;
    },
  });

  const { data: trends } = useQuery({
    queryKey: ['analytics', 'trends', timeRange],
    queryFn: async () => {
      const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
      const response = await analyticsApi.trends(null, days);
      return response.data;
    },
  });

  // Mock data
  const mockOverview = {
    totalInteractions: 1247,
    todayInteractions: 47,
    autonomousRate: 89,
    avgConfidenceScore: 85.3,
    avgProcessingTime: 1.2,
  };

  const mockTrends = [
    { date: 'Mon', interactions: 32, escalations: 4, confidence: 84 },
    { date: 'Tue', interactions: 45, escalations: 3, confidence: 86 },
    { date: 'Wed', interactions: 38, escalations: 5, confidence: 82 },
    { date: 'Thu', interactions: 52, escalations: 2, confidence: 88 },
    { date: 'Fri', interactions: 41, escalations: 3, confidence: 85 },
    { date: 'Sat', interactions: 18, escalations: 1, confidence: 90 },
    { date: 'Sun', interactions: 21, escalations: 0, confidence: 92 },
  ];

  const mockProviderData = [
    { name: 'Slack', value: 523, color: '#4A154B' },
    { name: 'GitHub', value: 312, color: '#24292e' },
    { name: 'Jira', value: 287, color: '#0052CC' },
    { name: 'Other', value: 125, color: '#6B7280' },
  ];

  const mockInteractionTypes = [
    { type: 'Messages', count: 456, success: 412 },
    { type: 'PR Reviews', count: 234, success: 198 },
    { type: 'Ticket Updates', count: 312, success: 289 },
    { type: 'Comments', count: 245, success: 221 },
  ];

  const data = overview || mockOverview;
  const trendData = trends || mockTrends;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900">Analytics</h2>
          <p className="text-neutral-500">Track your agent's performance and impact</p>
        </div>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="input w-auto"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
        </select>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Interactions"
          value={data.totalInteractions.toLocaleString()}
          change="+12%"
          changeType="positive"
          icon={Activity}
        />
        <MetricCard
          title="Autonomous Rate"
          value={`${data.autonomousRate}%`}
          change="+3%"
          changeType="positive"
          icon={CheckCircle}
        />
        <MetricCard
          title="Avg. Confidence"
          value={`${data.avgConfidenceScore}%`}
          change="+2%"
          changeType="positive"
          icon={TrendingUp}
        />
        <MetricCard
          title="Avg. Response Time"
          value={`${data.avgProcessingTime}s`}
          change="-0.3s"
          changeType="positive"
          icon={Clock}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Interactions over time */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-neutral-900 mb-4">
            Interactions Over Time
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="colorInteractions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorEscalations" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="interactions"
                  stroke="#6366F1"
                  fillOpacity={1}
                  fill="url(#colorInteractions)"
                />
                <Area
                  type="monotone"
                  dataKey="escalations"
                  stroke="#F59E0B"
                  fillOpacity={1}
                  fill="url(#colorEscalations)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Distribution by provider */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-neutral-900 mb-4">
            Distribution by Provider
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={mockProviderData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {mockProviderData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Interaction types */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-neutral-900 mb-4">
          Interaction Types Performance
        </h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={mockInteractionTypes}>
              <XAxis dataKey="type" axisLine={false} tickLine={false} />
              <YAxis axisLine={false} tickLine={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" name="Total" fill="#E4E4E7" radius={[4, 4, 0, 0]} />
              <Bar dataKey="success" name="Successful" fill="#6366F1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed stats table */}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-neutral-200">
          <h3 className="text-lg font-semibold text-neutral-900">
            Detailed Performance
          </h3>
        </div>
        <table className="w-full">
          <thead className="bg-neutral-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase">
                Provider
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase">
                Interactions
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase">
                Success Rate
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase">
                Avg. Confidence
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase">
                Avg. Time
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200">
            <tr>
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-[#4A154B]" />
                  <span className="font-medium">Slack</span>
                </div>
              </td>
              <td className="px-6 py-4">523</td>
              <td className="px-6 py-4">
                <span className="badge badge-success">94%</span>
              </td>
              <td className="px-6 py-4">87%</td>
              <td className="px-6 py-4">0.8s</td>
            </tr>
            <tr>
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <GitPullRequest className="w-4 h-4 text-neutral-900" />
                  <span className="font-medium">GitHub</span>
                </div>
              </td>
              <td className="px-6 py-4">312</td>
              <td className="px-6 py-4">
                <span className="badge badge-success">85%</span>
              </td>
              <td className="px-6 py-4">82%</td>
              <td className="px-6 py-4">2.1s</td>
            </tr>
            <tr>
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#0052CC]" />
                  <span className="font-medium">Jira</span>
                </div>
              </td>
              <td className="px-6 py-4">287</td>
              <td className="px-6 py-4">
                <span className="badge badge-success">91%</span>
              </td>
              <td className="px-6 py-4">88%</td>
              <td className="px-6 py-4">1.5s</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
