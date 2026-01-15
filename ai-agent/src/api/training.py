"""
Training API Endpoints
"""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TrainingSample(BaseModel):
    """A single training sample"""
    id: str = None
    input: str
    output: str = None
    type: str = "response"  # response, style, domain


class TrainRequest(BaseModel):
    """Request model for training an agent"""
    agent_id: str
    user_id: str
    samples: List[TrainingSample]


class TrainResponse(BaseModel):
    """Response model for training result"""
    success: bool
    samples_processed: int
    message: str = None


class SyncRequest(BaseModel):
    """Request to sync data from an integration"""
    agent_id: str
    user_id: str
    provider: str
    source_type: str  # slack_history, github_activity, etc.
    config: Dict[str, Any] = {}


@router.post("/train", response_model=TrainResponse)
async def train_agent(request: TrainRequest):
    """
    Train an agent with new samples.

    Samples can be:
    - Past conversations/responses (to learn style)
    - Domain knowledge (to learn expertise)
    - Corrections (to improve accuracy)
    """
    from src.main import get_agent_manager

    try:
        agent_manager = get_agent_manager()

        training_data = {
            "samples": [
                {
                    "id": s.id or f"sample-{i}",
                    "input": s.input,
                    "output": s.output,
                    "type": s.type
                }
                for i, s in enumerate(request.samples)
            ]
        }

        result = await agent_manager.train_agent(
            agent_id=UUID(request.agent_id),
            user_id=UUID(request.user_id),
            training_data=training_data
        )

        return TrainResponse(
            success=result.get("success", False),
            samples_processed=result.get("samples_processed", 0),
            message="Training completed successfully"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_integration_data(request: SyncRequest):
    """
    Sync historical data from an integration to train the agent.

    This pulls data like:
    - Slack message history
    - GitHub PR reviews and comments
    - Jira ticket updates

    And uses it to train the agent's personality.
    """
    # This would be implemented to pull and process historical data
    # For now, return a placeholder response

    return {
        "status": "queued",
        "message": f"Sync job queued for {request.provider}",
        "agent_id": request.agent_id,
        "source_type": request.source_type
    }


@router.get("/{agent_id}/samples")
async def get_training_samples(agent_id: str, limit: int = 50, offset: int = 0):
    """Get training samples for an agent"""
    # This would fetch from the database
    # For now, return empty list

    return {
        "samples": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }


@router.delete("/{agent_id}/samples/{sample_id}")
async def delete_training_sample(agent_id: str, sample_id: str):
    """Delete a specific training sample"""
    # This would delete from database and vector store

    return {
        "success": True,
        "message": f"Sample {sample_id} deleted"
    }


@router.post("/{agent_id}/retrain")
async def trigger_retrain(agent_id: str):
    """
    Trigger a full retrain of the agent's personality model.

    This rebuilds the personality profile from all training samples.
    """
    from src.main import get_agent_manager

    try:
        agent_manager = get_agent_manager()

        # In a real implementation, this would:
        # 1. Fetch all training samples from DB
        # 2. Regenerate all embeddings
        # 3. Rebuild personality profile
        # 4. Update vector store

        return {
            "status": "queued",
            "message": "Retrain job queued",
            "agent_id": agent_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
