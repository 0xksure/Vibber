"""
Agent Manager - Orchestrates AI agent instances and their lifecycle
"""

import asyncio
from typing import Dict, Optional
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from src.config import settings
from src.core.agent import Agent
from src.core.personality import PersonalityEngine
from src.embeddings.embedder import Embedder
from src.memory.vector_store import VectorStore
from src.memory.redis_cache import RedisCache

logger = structlog.get_logger()


class AgentManager:
    """
    Manages the lifecycle and orchestration of AI agents.
    Implements patterns inspired by Cursor and Anthropic's agent architectures.
    """

    def __init__(self):
        self.agents: Dict[UUID, Agent] = {}
        self.anthropic_client: Optional[AsyncAnthropic] = None
        self.openai_client: Optional[AsyncOpenAI] = None
        self.embedder: Optional[Embedder] = None
        self.vector_store: Optional[VectorStore] = None
        self.cache: Optional[RedisCache] = None
        self.personality_engine: Optional[PersonalityEngine] = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize all AI service connections"""
        logger.info("Initializing Agent Manager")

        # Initialize AI clients
        if settings.anthropic_api_key:
            self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            logger.info("Anthropic client initialized")

        if settings.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info("OpenAI client initialized")

        # Initialize embedder
        self.embedder = Embedder(self.openai_client)
        await self.embedder.initialize()

        # Initialize vector store
        self.vector_store = VectorStore()
        await self.vector_store.initialize()

        # Initialize cache
        self.cache = RedisCache()
        await self.cache.initialize()

        # Initialize personality engine
        self.personality_engine = PersonalityEngine(
            self.embedder,
            self.vector_store,
            self.cache
        )

        logger.info("Agent Manager initialized successfully")

    async def shutdown(self):
        """Cleanup resources"""
        logger.info("Shutting down Agent Manager")

        # Stop all active agents
        for agent_id in list(self.agents.keys()):
            await self.unload_agent(agent_id)

        # Close connections
        if self.cache:
            await self.cache.close()
        if self.vector_store:
            await self.vector_store.close()

        logger.info("Agent Manager shutdown complete")

    async def get_or_create_agent(self, agent_id: UUID, user_id: UUID) -> Agent:
        """Get existing agent or create new one"""
        async with self._lock:
            if agent_id not in self.agents:
                agent = Agent(
                    agent_id=agent_id,
                    user_id=user_id,
                    anthropic_client=self.anthropic_client,
                    openai_client=self.openai_client,
                    embedder=self.embedder,
                    vector_store=self.vector_store,
                    cache=self.cache,
                    personality_engine=self.personality_engine,
                )
                await agent.load()
                self.agents[agent_id] = agent
                logger.info("Agent loaded", agent_id=str(agent_id))

            return self.agents[agent_id]

    async def unload_agent(self, agent_id: UUID):
        """Unload an agent from memory"""
        async with self._lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                await agent.save_state()
                del self.agents[agent_id]
                logger.info("Agent unloaded", agent_id=str(agent_id))

    async def process_interaction(
        self,
        agent_id: UUID,
        user_id: UUID,
        interaction_data: dict
    ) -> dict:
        """
        Process an incoming interaction through the appropriate agent.

        This is the main entry point for all agent interactions.
        """
        agent = await self.get_or_create_agent(agent_id, user_id)

        # Process the interaction
        result = await agent.process(interaction_data)

        return result

    async def train_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
        training_data: dict
    ) -> dict:
        """Train an agent with new samples"""
        agent = await self.get_or_create_agent(agent_id, user_id)

        result = await agent.train(training_data)

        return result

    async def get_agent_status(self, agent_id: UUID) -> dict:
        """Get the current status of an agent"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            return await agent.get_status()

        return {
            "loaded": False,
            "status": "inactive"
        }

    async def update_agent_settings(
        self,
        agent_id: UUID,
        user_id: UUID,
        settings: dict
    ) -> dict:
        """Update agent configuration"""
        agent = await self.get_or_create_agent(agent_id, user_id)

        await agent.update_settings(settings)

        return {"success": True}
