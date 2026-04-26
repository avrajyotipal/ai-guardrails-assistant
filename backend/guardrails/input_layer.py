"""
Input Layer Guardrail
Validates and sanitizes user input: length limits, SQL injection, prompt injection,
XSS, and other attack vectors. Returns sanitized input on pass.
"""

import re
import html
from .base import GuardrailResult
from config import settings

SQL_INJECTION_PATTERNS = [
    r"(?i);\s*(drop|delete|truncate|alter|create|insert|update|grant)\b",
    r"(?i)\b(union\s+all\s+select|union\s+select)\b",
    r"(?i)'\s*(or|and)\s+['\d]",
    r"(?i)\bexec\s*\(",
    r"(?i)\bxp_cmdshell\b",
    r"(?i)/\*.*?\*/",
    r"(?i)\bload_file\s*\(",
    r"(?i)\boutfile\b",
    r"--\s*$",
    r"(?i)\b(sleep|benchmark|waitfor)\s*\(",
    r"(?i)0x[0-9a-f]{4,}",
]

PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(?:all\s+|previous\s+|prior\s+|above\s+)*(instructions?|prompts?|rules?|constraints?|directions?)",
    r"(?i)(you\s+are\s+now|pretend\s+(to\s+be|you\s+are)|act\s+as|roleplay\s+as|imagine\s+you\s+are)",
    r"(?i)(jailbreak|developer\s+mode|god\s+mode|dan\s+mode|unrestricted\s+mode)",
    r"(?i)(override|disable|bypass|circumvent)\s+(safety|guardrail|filter|restriction|rule)",
    r"(?i)(system\s+prompt|system\s+message)\s*(is|was|should|must|will)\s*(now|be|ignore)",
    r"(?i)\[INST\]|\[\/INST\]|<\|im_start\|>|<\|im_end\|>|<\|system\|>",
    r"(?i)(forget|disregard|neglect)\s+(everything|all|your|prior|previous|above)",
    r"(?i)new\s+instructions?\s*:",
    r"(?i)###\s*instruction",
]

XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript\s*:",
    r"on\w+\s*=",
    r"<iframe",
    r"<object",
]


class InputLayerGuardrail:
    def check(self, user_input: str) -> GuardrailResult:
        # Length check
        if len(user_input) > settings.MAX_INPUT_LENGTH:
            return GuardrailResult(
                passed=False,
                reason=f"Input exceeds maximum length of {settings.MAX_INPUT_LENGTH} characters.",
            )

        if len(user_input.strip()) < 2:
            return GuardrailResult(passed=False, reason="Input is too short.")

        # SQL injection check
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, user_input):
                return GuardrailResult(
                    passed=False,
                    reason="Potential SQL injection detected in input.",
                    metadata={"type": "sql_injection", "pattern": pattern}
                )

        # Prompt injection check
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, user_input):
                return GuardrailResult(
                    passed=False,
                    reason="Prompt injection attempt detected.",
                    metadata={"type": "prompt_injection", "pattern": pattern}
                )

        # XSS check
        for pattern in XSS_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE | re.DOTALL):
                return GuardrailResult(
                    passed=False,
                    reason="Potential XSS content detected in input.",
                    metadata={"type": "xss"}
                )

        # Sanitize: escape HTML entities, strip null bytes
        sanitized = html.escape(user_input)
        sanitized = sanitized.replace("\x00", "").strip()
        # Collapse excessive whitespace
        sanitized = re.sub(r'\s{3,}', '  ', sanitized)

        return GuardrailResult(
            passed=True,
            sanitized_input=sanitized,
            metadata={"original_length": len(user_input), "sanitized_length": len(sanitized)}
        )
