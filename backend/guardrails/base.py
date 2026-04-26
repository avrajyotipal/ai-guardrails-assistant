from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class GuardrailResult:
    passed: bool
    reason: Optional[str] = None
    sanitized_input: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MonitoringLogEntry:
    session_id: str
    user_input: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Policy layer
    policy_passed: Optional[bool] = None
    policy_block_reason: Optional[str] = None

    # Input layer
    input_passed: Optional[bool] = None
    input_block_reason: Optional[str] = None
    input_sanitized: Optional[str] = None
    injection_detected: bool = False

    # Instruction layer
    instruction_passed: Optional[bool] = None
    instruction_block_reason: Optional[str] = None
    jailbreak_detected: bool = False
    system_prompt_used: Optional[str] = None

    # Execution layer
    tools_called: List[Dict] = field(default_factory=list)
    tools_blocked: List[Dict] = field(default_factory=list)
    tool_execution_details: List[Dict] = field(default_factory=list)

    # Output layer
    llm_raw_output: Optional[str] = None
    output_passed: Optional[bool] = None
    output_block_reason: Optional[str] = None
    hallucination_detected: bool = False
    hallucination_details: Optional[str] = None
    pii_detected: bool = False

    # Final
    final_response: Optional[str] = None
    total_blocked: bool = False
    processing_time_ms: Optional[int] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_input": self.user_input[:2000] if self.user_input else None,
            "timestamp": self.timestamp.isoformat(),
            "policy_passed": self.policy_passed,
            "policy_block_reason": self.policy_block_reason,
            "input_passed": self.input_passed,
            "input_block_reason": self.input_block_reason,
            "input_sanitized": self.input_sanitized[:2000] if self.input_sanitized else None,
            "injection_detected": self.injection_detected,
            "instruction_passed": self.instruction_passed,
            "instruction_block_reason": self.instruction_block_reason,
            "jailbreak_detected": self.jailbreak_detected,
            "tools_called": self.tools_called,
            "tools_blocked": self.tools_blocked,
            "tool_execution_details": self.tool_execution_details,
            "llm_raw_output": self.llm_raw_output[:4000] if self.llm_raw_output else None,
            "output_passed": self.output_passed,
            "output_block_reason": self.output_block_reason,
            "hallucination_detected": self.hallucination_detected,
            "hallucination_details": self.hallucination_details,
            "pii_detected": self.pii_detected,
            "final_response": self.final_response[:4000] if self.final_response else None,
            "total_blocked": self.total_blocked,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
        }
