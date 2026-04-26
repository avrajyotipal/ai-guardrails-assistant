from pydantic import BaseModel
from typing import Optional, List, Any, Dict


class ChatRequest(BaseModel):
    session_id: str
    message: str
    chat_history: Optional[List[Dict[str, str]]] = []


class GuardrailSummary(BaseModel):
    policy_passed: Optional[bool] = None
    input_passed: Optional[bool] = None
    instruction_passed: Optional[bool] = None
    output_passed: Optional[bool] = None
    hallucination_detected: bool = False
    injection_detected: bool = False
    jailbreak_detected: bool = False
    tools_called: List[str] = []
    tools_blocked: List[str] = []
    processing_time_ms: Optional[int] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str = ""
    blocked: bool = False
    block_reason: Optional[str] = None
    block_layer: Optional[str] = None
    guardrail_summary: Optional[GuardrailSummary] = None
    processing_time_ms: Optional[int] = None


class MonitoringFilter(BaseModel):
    session_id: Optional[str] = None
    blocked_only: bool = False
    limit: int = 50
    offset: int = 0
