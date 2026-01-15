"""
Agent API Endpoints
"""

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()


class ProcessRequest(BaseModel):
    """Request model for processing an interaction"""
    agent_id: str
    user_id: str
    provider: str
    interaction_type: str
    input_data: Dict[str, Any]


class ProcessResponse(BaseModel):
    """Response model for processing result"""
    status: str
    action: str = None
    response: Dict[str, Any] = None
    confidence: int = None
    processing_time: int = None
    error: str = None


class SettingsRequest(BaseModel):
    """Request model for updating agent settings"""
    confidence_threshold: int = None
    auto_mode: bool = None
    model: str = None


@router.post("/process", response_model=ProcessResponse)
async def process_interaction(request: ProcessRequest):
    """
    Process an interaction through an agent.

    This is the main endpoint for processing incoming events
    from integrations like Slack, GitHub, Jira, etc.
    """
    from src.main import get_agent_manager

    try:
        agent_manager = get_agent_manager()

        result = await agent_manager.process_interaction(
            agent_id=UUID(request.agent_id),
            user_id=UUID(request.user_id),
            interaction_data={
                "provider": request.provider,
                "interaction_type": request.interaction_type,
                "input_data": request.input_data
            }
        )

        return ProcessResponse(
            status=result.get("status", "unknown"),
            action=result.get("action"),
            response=result.get("response"),
            confidence=result.get("confidence"),
            processing_time=result.get("processing_time"),
            error=result.get("error")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get the current status of an agent"""
    from src.main import get_agent_manager

    try:
        agent_manager = get_agent_manager()
        status = await agent_manager.get_agent_status(UUID(agent_id))
        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}/settings")
async def update_agent_settings(agent_id: str, request: SettingsRequest):
    """Update agent configuration"""
    from src.main import get_agent_manager

    try:
        agent_manager = get_agent_manager()

        settings = {}
        if request.confidence_threshold is not None:
            settings["confidence_threshold"] = request.confidence_threshold
        if request.auto_mode is not None:
            settings["auto_mode"] = request.auto_mode
        if request.model is not None:
            settings["model"] = request.model

        # Need user_id for get_or_create_agent, use a placeholder for now
        # In production, this would come from auth
        result = await agent_manager.update_agent_settings(
            agent_id=UUID(agent_id),
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            settings=settings
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
