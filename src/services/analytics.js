// Mixpanel Analytics Service for Vibber
import mixpanel from 'mixpanel-browser';

const MIXPANEL_TOKEN = process.env.REACT_APP_MIXPANEL_TOKEN;

class Analytics {
  constructor() {
    this.initialized = false;
  }

  init() {
    if (this.initialized || !MIXPANEL_TOKEN) {
      if (!MIXPANEL_TOKEN) {
        console.warn('Mixpanel token not configured');
      }
      return;
    }

    mixpanel.init(MIXPANEL_TOKEN, {
      debug: process.env.NODE_ENV === 'development',
      track_pageview: true,
      persistence: 'localStorage',
      ignore_dnt: false,
    });

    this.initialized = true;
  }

  // Identify user
  identify(userId, traits = {}) {
    if (!this.initialized) return;

    mixpanel.identify(userId);
    mixpanel.people.set({
      $email: traits.email,
      $name: traits.name,
      organization: traits.organization,
      role: traits.role,
      plan: traits.plan,
      ...traits,
    });
  }

  // Track page views
  pageView(pageName, properties = {}) {
    if (!this.initialized) return;

    mixpanel.track('Page View', {
      page: pageName,
      url: window.location.href,
      path: window.location.pathname,
      ...properties,
    });
  }

  // Track events
  track(eventName, properties = {}) {
    if (!this.initialized) return;

    mixpanel.track(eventName, {
      timestamp: new Date().toISOString(),
      ...properties,
    });
  }

  // Agent events
  agentCreated(agentId, agentName) {
    this.track('Agent Created', { agentId, agentName });
  }

  agentTrained(agentId, samplesCount) {
    this.track('Agent Trained', { agentId, samplesCount });
  }

  agentActivated(agentId) {
    this.track('Agent Activated', { agentId });
  }

  agentDeactivated(agentId) {
    this.track('Agent Deactivated', { agentId });
  }

  // Integration events
  integrationConnected(provider, agentId) {
    this.track('Integration Connected', { provider, agentId });
  }

  integrationDisconnected(provider, agentId) {
    this.track('Integration Disconnected', { provider, agentId });
  }

  // Escalation events
  escalationCreated(escalationId, provider, reason) {
    this.track('Escalation Created', { escalationId, provider, reason });
  }

  escalationResolved(escalationId, resolution) {
    this.track('Escalation Resolved', { escalationId, resolution });
  }

  // Interaction events
  interactionProcessed(provider, interactionType, confidence, wasAutomatic) {
    this.track('Interaction Processed', {
      provider,
      interactionType,
      confidence,
      wasAutomatic,
    });
  }

  // User events
  userSignedUp(userId, plan) {
    this.track('User Signed Up', { userId, plan });
  }

  userLoggedIn(userId) {
    this.track('User Logged In', { userId });
  }

  userLoggedOut(userId) {
    this.track('User Logged Out', { userId });
  }

  // Settings events
  settingsUpdated(settingType, changes) {
    this.track('Settings Updated', { settingType, changes });
  }

  confidenceThresholdChanged(agentId, oldThreshold, newThreshold) {
    this.track('Confidence Threshold Changed', {
      agentId,
      oldThreshold,
      newThreshold,
    });
  }

  autoModeToggled(agentId, enabled) {
    this.track('Auto Mode Toggled', { agentId, enabled });
  }

  // Billing events
  planUpgraded(oldPlan, newPlan) {
    this.track('Plan Upgraded', { oldPlan, newPlan });
  }

  planDowngraded(oldPlan, newPlan) {
    this.track('Plan Downgraded', { oldPlan, newPlan });
  }

  // Feature usage
  featureUsed(featureName, context = {}) {
    this.track('Feature Used', { featureName, ...context });
  }

  // Error tracking
  errorOccurred(errorType, errorMessage, context = {}) {
    this.track('Error Occurred', {
      errorType,
      errorMessage,
      ...context,
    });
  }

  // Reset on logout
  reset() {
    if (!this.initialized) return;
    mixpanel.reset();
  }
}

export const analytics = new Analytics();
export default analytics;
