import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { escalationsApi } from '../../services/api';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  MessageSquare,
  GitPullRequest,
  FileText,
  ChevronRight,
  Inbox,
} from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';

const providerIcons = {
  slack: MessageSquare,
  github: GitPullRequest,
  jira: FileText,
};

const priorityColors = {
  urgent: 'bg-error-100 text-error-700 border-error-200',
  high: 'bg-warning-100 text-warning-700 border-warning-200',
  medium: 'bg-primary-100 text-primary-700 border-primary-200',
  low: 'bg-neutral-100 text-neutral-700 border-neutral-200',
};

function EscalationCard({ escalation, onSelect }) {
  const Icon = providerIcons[escalation.provider] || AlertTriangle;
  const createdAt = new Date(escalation.createdAt);
  const timeAgo = getTimeAgo(createdAt);

  return (
    <div
      onClick={() => onSelect(escalation)}
      className="card p-4 hover:border-primary-300 cursor-pointer transition-colors"
    >
      <div className="flex items-start gap-4">
        <div className={`p-2 rounded-lg ${
          escalation.priority === 'urgent' ? 'bg-error-100' :
          escalation.priority === 'high' ? 'bg-warning-100' : 'bg-neutral-100'
        }`}>
          <Icon className={`w-5 h-5 ${
            escalation.priority === 'urgent' ? 'text-error-600' :
            escalation.priority === 'high' ? 'text-warning-600' : 'text-neutral-600'
          }`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`badge border ${priorityColors[escalation.priority]}`}>
              {escalation.priority}
            </span>
            <span className="text-xs text-neutral-400">{escalation.provider}</span>
          </div>
          <p className="font-medium text-neutral-900 truncate">
            {escalation.reason}
          </p>
          <p className="text-sm text-neutral-500 line-clamp-2 mt-1">
            {escalation.context?.preview || 'No preview available'}
          </p>
        </div>

        <div className="flex flex-col items-end gap-2">
          <span className="text-xs text-neutral-400 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {timeAgo}
          </span>
          <ChevronRight className="w-5 h-5 text-neutral-400" />
        </div>
      </div>
    </div>
  );
}

function EscalationDetail({ escalation, onApprove, onReject, onClose }) {
  const [rejectReason, setRejectReason] = useState('');
  const [correction, setCorrection] = useState('');
  const Icon = providerIcons[escalation?.provider] || AlertTriangle;

  if (!escalation) return null;

  return (
    <Dialog.Root open={!!escalation} onOpenChange={() => onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-hidden z-50">
          <div className="p-6 border-b border-neutral-200">
            <div className="flex items-start gap-4">
              <div className={`p-3 rounded-lg ${
                escalation.priority === 'urgent' ? 'bg-error-100' :
                escalation.priority === 'high' ? 'bg-warning-100' : 'bg-neutral-100'
              }`}>
                <Icon className={`w-6 h-6 ${
                  escalation.priority === 'urgent' ? 'text-error-600' :
                  escalation.priority === 'high' ? 'text-warning-600' : 'text-neutral-600'
                }`} />
              </div>
              <div>
                <Dialog.Title className="text-lg font-semibold text-neutral-900">
                  Escalation Review
                </Dialog.Title>
                <Dialog.Description className="text-sm text-neutral-500">
                  {escalation.reason}
                </Dialog.Description>
              </div>
            </div>
          </div>

          <div className="p-6 space-y-6 max-h-[50vh] overflow-y-auto">
            {/* Original input */}
            <div>
              <h4 className="text-sm font-medium text-neutral-700 mb-2">Original Input</h4>
              <div className="p-4 bg-neutral-50 rounded-lg text-sm">
                {escalation.interaction?.inputData?.text ||
                 escalation.interaction?.inputData?.content ||
                 JSON.stringify(escalation.interaction?.inputData, null, 2)}
              </div>
            </div>

            {/* Agent's proposed response */}
            <div>
              <h4 className="text-sm font-medium text-neutral-700 mb-2">
                Agent's Proposed Response
              </h4>
              <div className="p-4 bg-primary-50 rounded-lg text-sm border border-primary-200">
                {escalation.proposedAction?.response_text || 'No proposed response'}
              </div>
              <p className="text-xs text-neutral-500 mt-2">
                Confidence: {escalation.proposedAction?.confidence || 'N/A'}%
              </p>
            </div>

            {/* Rejection reason (shown when rejecting) */}
            <div>
              <h4 className="text-sm font-medium text-neutral-700 mb-2">
                Your Correction (optional)
              </h4>
              <textarea
                value={correction}
                onChange={(e) => setCorrection(e.target.value)}
                placeholder="Provide the correct response if rejecting..."
                className="input min-h-[100px] resize-none"
              />
              <p className="text-xs text-neutral-500 mt-1">
                This will be used to train your agent for better future responses.
              </p>
            </div>
          </div>

          <div className="p-6 border-t border-neutral-200 flex justify-end gap-3">
            <button onClick={onClose} className="btn btn-ghost">
              Cancel
            </button>
            <button
              onClick={() => onReject(escalation.id, { reason: rejectReason, correction })}
              className="btn btn-danger"
            >
              <XCircle className="w-4 h-4 mr-2" />
              Reject
            </button>
            <button
              onClick={() => onApprove(escalation.id)}
              className="btn btn-primary"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Approve & Execute
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);
  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function EscalationsPage() {
  const queryClient = useQueryClient();
  const [selectedEscalation, setSelectedEscalation] = useState(null);
  const [filter, setFilter] = useState('all');

  // Fetch escalations
  const { data: escalations = [], isLoading } = useQuery({
    queryKey: ['escalations'],
    queryFn: async () => {
      const response = await escalationsApi.list();
      return response.data;
    },
  });

  // Mock data for demo
  const mockEscalations = [
    {
      id: '1',
      provider: 'slack',
      priority: 'high',
      reason: 'Complex refund request - policy clarification needed',
      status: 'pending',
      createdAt: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
      context: {
        preview: 'Customer requesting refund for subscription after 45 days. Our policy is 30 days...',
      },
      interaction: {
        inputData: {
          text: 'Hi, I need a refund for my subscription. I signed up 45 days ago but haven\'t used it much.',
        },
      },
      proposedAction: {
        response_text: 'I understand you\'d like a refund. While our standard policy is 30 days, let me check if we can make an exception for your case.',
        confidence: 62,
      },
    },
    {
      id: '2',
      provider: 'github',
      priority: 'medium',
      reason: 'PR involves security-sensitive code changes',
      status: 'pending',
      createdAt: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
      context: {
        preview: 'Changes to authentication flow in auth/middleware.go',
      },
      interaction: {
        inputData: {
          content: 'PR #234: Update authentication middleware',
        },
      },
      proposedAction: {
        response_text: 'The changes look good overall. A few suggestions for the token validation...',
        confidence: 58,
      },
    },
    {
      id: '3',
      provider: 'jira',
      priority: 'low',
      reason: 'Unclear ticket requirements',
      status: 'pending',
      createdAt: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
      context: {
        preview: 'JIRA-1234: Implement new feature',
      },
      interaction: {
        inputData: {
          content: 'Need to implement the new dashboard feature as discussed',
        },
      },
      proposedAction: {
        response_text: 'Could you provide more details about the specific requirements?',
        confidence: 45,
      },
    },
  ];

  const displayEscalations = escalations.length > 0 ? escalations : mockEscalations;

  const filteredEscalations = displayEscalations.filter((e) => {
    if (filter === 'all') return true;
    return e.priority === filter;
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: async (id) => {
      return escalationsApi.approve(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['escalations']);
      setSelectedEscalation(null);
    },
  });

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: async ({ id, data }) => {
      return escalationsApi.reject(id, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['escalations']);
      setSelectedEscalation(null);
    },
  });

  const handleApprove = (id) => {
    approveMutation.mutate(id);
  };

  const handleReject = (id, data) => {
    rejectMutation.mutate({ id, data });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900">Escalations</h2>
          <p className="text-neutral-500">
            Review and resolve items that need your attention
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-neutral-500">Filter:</span>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input w-auto"
          >
            <option value="all">All</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-sm text-neutral-500">Total Pending</p>
          <p className="text-2xl font-semibold text-neutral-900">
            {displayEscalations.length}
          </p>
        </div>
        <div className="card p-4 border-l-4 border-l-error-500">
          <p className="text-sm text-neutral-500">Urgent</p>
          <p className="text-2xl font-semibold text-error-600">
            {displayEscalations.filter((e) => e.priority === 'urgent').length}
          </p>
        </div>
        <div className="card p-4 border-l-4 border-l-warning-500">
          <p className="text-sm text-neutral-500">High</p>
          <p className="text-2xl font-semibold text-warning-600">
            {displayEscalations.filter((e) => e.priority === 'high').length}
          </p>
        </div>
        <div className="card p-4 border-l-4 border-l-primary-500">
          <p className="text-sm text-neutral-500">Medium/Low</p>
          <p className="text-2xl font-semibold text-primary-600">
            {displayEscalations.filter((e) => ['medium', 'low'].includes(e.priority)).length}
          </p>
        </div>
      </div>

      {/* Escalation list */}
      {filteredEscalations.length > 0 ? (
        <div className="space-y-3">
          {filteredEscalations.map((escalation) => (
            <EscalationCard
              key={escalation.id}
              escalation={escalation}
              onSelect={setSelectedEscalation}
            />
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <Inbox className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-neutral-900 mb-1">
            All caught up!
          </h3>
          <p className="text-neutral-500">
            No escalations need your attention right now.
          </p>
        </div>
      )}

      {/* Detail modal */}
      <EscalationDetail
        escalation={selectedEscalation}
        onApprove={handleApprove}
        onReject={handleReject}
        onClose={() => setSelectedEscalation(null)}
      />
    </div>
  );
}
