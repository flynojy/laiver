from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services.agent_orchestrator import respond

router = APIRouter()


@router.post("/respond", response_model=AgentChatResponse)
async def respond_route(payload: AgentChatRequest, db: Session = Depends(get_db)) -> AgentChatResponse:
    return await respond(db, payload)

