"""
Execution Layer Guardrail
Controls which tools the agent is allowed to call, validates tool inputs,
enforces rate limits per session, and prevents destructive operations.
"""

import re
import time
from collections import defaultdict
from .base import GuardrailResult

ALLOWED_TOOLS = {
    "get_students",
    "get_courses",
    "get_transactions",
    "get_student_by_id",
    "get_enrollment_stats",
    "get_revenue_stats",
    "search_students_by_name",
    "get_course_enrollment",
    "get_department_stats",
    "get_transaction_summary",
}

DESTRUCTIVE_SQL_PATTERNS = [
    r"(?i)\b(drop|delete|truncate|alter|create|insert|update|grant|revoke)\b",
    r"(?i)\bexec\b",
    r"(?i)\bxp_",
]

MAX_CALLS_PER_SESSION = 30
WINDOW_SECONDS = 60


class ExecutionLayerGuardrail:
    def __init__(self):
        self._session_calls: dict[str, list[float]] = defaultdict(list)

    def _rate_check(self, session_id: str) -> bool:
        now = time.time()
        calls = self._session_calls[session_id]
        # Remove calls outside the window
        self._session_calls[session_id] = [t for t in calls if now - t < WINDOW_SECONDS]
        if len(self._session_calls[session_id]) >= MAX_CALLS_PER_SESSION:
            return False
        self._session_calls[session_id].append(now)
        return True

    def validate_tool_call(self, tool_name: str, tool_input: str, session_id: str) -> GuardrailResult:
        # Check tool allowlist
        if tool_name not in ALLOWED_TOOLS:
            return GuardrailResult(
                passed=False,
                reason=f"Tool '{tool_name}' is not in the allowed tools list.",
                metadata={"tool": tool_name, "allowed_tools": list(ALLOWED_TOOLS)}
            )

        # Check rate limit
        if not self._rate_check(session_id):
            return GuardrailResult(
                passed=False,
                reason=f"Rate limit exceeded: maximum {MAX_CALLS_PER_SESSION} tool calls per {WINDOW_SECONDS}s.",
                metadata={"session_id": session_id}
            )

        # Check for destructive SQL in tool input string
        input_str = str(tool_input)
        for pattern in DESTRUCTIVE_SQL_PATTERNS:
            if re.search(pattern, input_str):
                return GuardrailResult(
                    passed=False,
                    reason=f"Destructive SQL pattern detected in tool input for '{tool_name}'.",
                    metadata={"tool": tool_name, "pattern": pattern}
                )

        return GuardrailResult(
            passed=True,
            metadata={"tool": tool_name, "session_id": session_id}
        )

    def get_allowed_tools(self) -> list[str]:
        return sorted(ALLOWED_TOOLS)
