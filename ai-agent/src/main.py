"""
Vibber AI Agent Service
Main entry point for the AI agent that powers employee clones
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.core.agent_manager import AgentManager
from src.core.message_consumer import MessageConsumer
from src.api import agents, training, health, ralph

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.env == "production" else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global instances
agent_manager: AgentManager = None
message_consumer: MessageConsumer = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Manage application lifecycle"""
    global agent_manager, message_consumer

    logger.info("Starting Vibber AI Agent Service", env=settings.env)

    # Initialize agent manager
    agent_manager = AgentManager()
    await agent_manager.initialize()

    # Initialize and start message consumer
    message_consumer = MessageConsumer(agent_manager)
    asyncio.create_task(message_consumer.start())

    logger.info("AI Agent Service started successfully")

    yield

    # Cleanup
    logger.info("Shutting down AI Agent Service")
    if message_consumer:
        await message_consumer.stop()
    if agent_manager:
        await agent_manager.shutdown()
    logger.info("AI Agent Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Vibber AI Agent Service",
    description="AI Agent service for employee clone automation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(training.router, prefix="/api/v1/training", tags=["Training"])
app.include_router(ralph.router, prefix="/api/v1/ralph", tags=["Ralph Wiggum"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Vibber AI Agent",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "Employee clone agents",
            "Ralph Wiggum iterative task execution",
            "MCP integration",
        ],
        "endpoints": {
            "agents": "/api/v1/agents",
            "training": "/api/v1/training",
            "ralph": "/api/v1/ralph",
            "docs": "/docs",
        }
    }


def get_agent_manager() -> AgentManager:
    """Dependency to get agent manager"""
    if agent_manager is None:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")
    return agent_manager


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.env == "development",
        log_level="info",
    )
