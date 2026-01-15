import { create } from 'zustand';

export const useAgentStore = create((set, get) => ({
  agents: [],
  selectedAgent: null,
  isLoading: false,
  error: null,

  setAgents: (agents) => set({ agents }),

  setSelectedAgent: (agent) => set({ selectedAgent: agent }),

  addAgent: (agent) => set({ agents: [...get().agents, agent] }),

  updateAgent: (agentId, updates) => {
    set({
      agents: get().agents.map((a) =>
        a.id === agentId ? { ...a, ...updates } : a
      ),
      selectedAgent:
        get().selectedAgent?.id === agentId
          ? { ...get().selectedAgent, ...updates }
          : get().selectedAgent,
    });
  },

  removeAgent: (agentId) => {
    set({
      agents: get().agents.filter((a) => a.id !== agentId),
      selectedAgent:
        get().selectedAgent?.id === agentId ? null : get().selectedAgent,
    });
  },

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),
}));
