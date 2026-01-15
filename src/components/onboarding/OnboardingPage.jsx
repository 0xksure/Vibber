import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bot,
  MessageSquare,
  Github,
  FileText,
  CheckCircle,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

const steps = [
  {
    id: 'welcome',
    title: 'Welcome to Vibber',
    description: 'Let\'s set up your AI clone in just a few minutes',
  },
  {
    id: 'name',
    title: 'Name your agent',
    description: 'Give your AI clone a name',
  },
  {
    id: 'integrations',
    title: 'Connect your tools',
    description: 'Choose the platforms your agent will work with',
  },
  {
    id: 'training',
    title: 'Train your agent',
    description: 'Share some examples of how you communicate',
  },
  {
    id: 'complete',
    title: 'You\'re all set!',
    description: 'Your AI clone is ready to help',
  },
];

const integrations = [
  { id: 'slack', name: 'Slack', icon: MessageSquare, color: 'bg-[#4A154B]' },
  { id: 'github', name: 'GitHub', icon: Github, color: 'bg-neutral-900' },
  { id: 'jira', name: 'Jira', icon: FileText, color: 'bg-[#0052CC]' },
];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [agentName, setAgentName] = useState('');
  const [selectedIntegrations, setSelectedIntegrations] = useState([]);
  const [trainingSamples, setTrainingSamples] = useState([
    { input: '', output: '' },
  ]);

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      navigate('/');
    }
  };

  const toggleIntegration = (id) => {
    setSelectedIntegrations((prev) =>
      prev.includes(id)
        ? prev.filter((i) => i !== id)
        : [...prev, id]
    );
  };

  const renderStepContent = () => {
    switch (steps[currentStep].id) {
      case 'welcome':
        return (
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 mb-6">
              <Bot className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-neutral-900 mb-2">
              Welcome to Vibber!
            </h2>
            <p className="text-neutral-500 max-w-md mx-auto">
              We'll help you create an AI clone that works just like you.
              It'll handle routine tasks across Slack, GitHub, Jira, and more.
            </p>
            <div className="mt-8 grid grid-cols-3 gap-4 max-w-lg mx-auto">
              <div className="p-4 bg-neutral-50 rounded-lg">
                <p className="text-2xl font-bold text-primary-600">5 min</p>
                <p className="text-xs text-neutral-500">Setup time</p>
              </div>
              <div className="p-4 bg-neutral-50 rounded-lg">
                <p className="text-2xl font-bold text-primary-600">20+ hrs</p>
                <p className="text-xs text-neutral-500">Saved monthly</p>
              </div>
              <div className="p-4 bg-neutral-50 rounded-lg">
                <p className="text-2xl font-bold text-primary-600">89%</p>
                <p className="text-xs text-neutral-500">Automation rate</p>
              </div>
            </div>
          </div>
        );

      case 'name':
        return (
          <div className="py-8">
            <div className="max-w-md mx-auto">
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Agent name
              </label>
              <input
                type="text"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                placeholder="e.g., John's Assistant"
                className="input text-lg h-12"
                autoFocus
              />
              <p className="mt-2 text-sm text-neutral-500">
                This name will be visible in activity logs and notifications.
              </p>
            </div>
          </div>
        );

      case 'integrations':
        return (
          <div className="py-8">
            <div className="max-w-md mx-auto space-y-4">
              {integrations.map((integration) => {
                const Icon = integration.icon;
                const isSelected = selectedIntegrations.includes(integration.id);

                return (
                  <button
                    key={integration.id}
                    onClick={() => toggleIntegration(integration.id)}
                    className={`w-full p-4 rounded-lg border-2 flex items-center gap-4 transition-colors ${
                      isSelected
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-neutral-200 hover:border-neutral-300'
                    }`}
                  >
                    <div className={`p-3 rounded-lg ${integration.color}`}>
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <span className="font-medium text-neutral-900 flex-1 text-left">
                      {integration.name}
                    </span>
                    {isSelected && (
                      <CheckCircle className="w-6 h-6 text-primary-500" />
                    )}
                  </button>
                );
              })}
              <p className="text-sm text-neutral-500 text-center pt-4">
                You can add more integrations later from Settings.
              </p>
            </div>
          </div>
        );

      case 'training':
        return (
          <div className="py-8">
            <div className="max-w-lg mx-auto">
              <p className="text-sm text-neutral-500 mb-4">
                Share a few examples of how you respond to messages. This helps
                your agent learn your communication style.
              </p>

              {trainingSamples.map((sample, index) => (
                <div key={index} className="mb-6 p-4 bg-neutral-50 rounded-lg">
                  <div className="mb-3">
                    <label className="block text-xs font-medium text-neutral-500 mb-1">
                      Someone asks you:
                    </label>
                    <input
                      type="text"
                      value={sample.input}
                      onChange={(e) => {
                        const newSamples = [...trainingSamples];
                        newSamples[index].input = e.target.value;
                        setTrainingSamples(newSamples);
                      }}
                      placeholder="e.g., When will the feature be ready?"
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-neutral-500 mb-1">
                      You would respond:
                    </label>
                    <textarea
                      value={sample.output}
                      onChange={(e) => {
                        const newSamples = [...trainingSamples];
                        newSamples[index].output = e.target.value;
                        setTrainingSamples(newSamples);
                      }}
                      placeholder="e.g., I'm targeting end of week, but I'll keep you posted!"
                      className="input min-h-[80px] resize-none"
                    />
                  </div>
                </div>
              ))}

              <button
                onClick={() =>
                  setTrainingSamples([...trainingSamples, { input: '', output: '' }])
                }
                className="btn btn-ghost w-full"
              >
                + Add another example
              </button>

              <p className="text-xs text-neutral-400 mt-4 text-center">
                More examples = better personalization. You can add more later!
              </p>
            </div>
          </div>
        );

      case 'complete':
        return (
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-success-100 mb-6">
              <Sparkles className="w-10 h-10 text-success-600" />
            </div>
            <h2 className="text-2xl font-bold text-neutral-900 mb-2">
              Your AI clone is ready!
            </h2>
            <p className="text-neutral-500 max-w-md mx-auto mb-6">
              {agentName || 'Your agent'} will start learning from your activity
              and handling routine tasks across your connected platforms.
            </p>
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-success-50 text-success-700 rounded-full text-sm">
              <CheckCircle className="w-4 h-4" />
              Agent created successfully
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* Progress */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            {steps.map((step, index) => (
              <div
                key={step.id}
                className={`flex items-center ${
                  index < steps.length - 1 ? 'flex-1' : ''
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    index <= currentStep
                      ? 'bg-primary-600 text-white'
                      : 'bg-neutral-200 text-neutral-500'
                  }`}
                >
                  {index < currentStep ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    index + 1
                  )}
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`flex-1 h-1 mx-2 ${
                      index < currentStep ? 'bg-primary-600' : 'bg-neutral-200'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="card p-8">
          <div className="text-center mb-6">
            <p className="text-sm text-primary-600 font-medium mb-1">
              Step {currentStep + 1} of {steps.length}
            </p>
            <h1 className="text-xl font-bold text-neutral-900">
              {steps[currentStep].title}
            </h1>
            <p className="text-neutral-500">{steps[currentStep].description}</p>
          </div>

          {renderStepContent()}

          <div className="flex justify-between pt-6 border-t border-neutral-200 mt-6">
            {currentStep > 0 ? (
              <button
                onClick={() => setCurrentStep(currentStep - 1)}
                className="btn btn-ghost"
              >
                Back
              </button>
            ) : (
              <div />
            )}
            <button
              onClick={nextStep}
              disabled={
                (currentStep === 1 && !agentName) ||
                (currentStep === 2 && selectedIntegrations.length === 0)
              }
              className="btn btn-primary"
            >
              {currentStep === steps.length - 1 ? (
                'Go to Dashboard'
              ) : (
                <>
                  Continue
                  <ArrowRight className="w-4 h-4 ml-2" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
