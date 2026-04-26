from fastapi import APIRouter, HTTPException
from models import ChatRequest, ChatResponse
from guardrails import GuardrailPipeline
import uuid

router = APIRouter()
_pipeline = GuardrailPipeline()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.session_id:
        request.session_id = str(uuid.uuid4())

    try:
        response = await _pipeline.process(
            session_id=request.session_id,
            user_input=request.message,
            chat_history=request.chat_history or [],
        )
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
