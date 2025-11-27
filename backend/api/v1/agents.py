"""
Agent endpoints for LangChain agent operations
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from services.agent_service import AgentService
from api.v1.auth import get_current_user
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentRequest(BaseModel):
    """Request model for agent execution"""
    prompt: str
    context: Optional[Dict[str, Any]] = None
    max_iterations: Optional[int] = 10


class AgentResponse(BaseModel):
    """Response model for agent execution"""
    result: str
    intermediate_steps: list
    total_tokens: Optional[int] = None


@router.post("/execute", response_model=AgentResponse)
async def execute_agent(
    request: AgentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Execute a LangChain agent with the given prompt

    Args:
        request: Agent execution request with prompt and context
        current_user: Authenticated user

    Returns:
        Agent execution result with intermediate steps
    """
    try:
        agent_service = AgentService()
        result = await agent_service.execute(
            prompt=request.prompt,
            context=request.context,
            max_iterations=request.max_iterations
        )
        return result
    except Exception as e:
        logger.error(f"Agent execution failed for user {current_user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def agent_health():
    """Check if agent service is healthy"""
    return {"status": "healthy", "service": "agents"}
