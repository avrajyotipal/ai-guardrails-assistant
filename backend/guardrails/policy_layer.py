"""
Policy Layer Guardrail
Enforces high-level topic and intent policy: only education domain queries allowed.
Blocks requests for write operations, system access, off-topic content, or misuse.
"""

import re
from .base import GuardrailResult

ALLOWED_KEYWORDS = {
    "student", "students", "course", "courses", "transaction", "transactions",
    "enrollment", "enrolled", "enroll", "fee", "fees", "payment", "payments",
    "grade", "grades", "gpa", "department", "departments", "credit", "credits",
    "instructor", "instructors", "semester", "semesters", "academic", "university",
    "statistics", "stats", "summary", "total", "count", "average", "highest",
    "lowest", "list", "show", "find", "get", "how many", "what", "which", "who",
    "revenue", "amount", "pending", "completed", "failed", "refunded",
    "freshman", "sophomore", "junior", "senior", "graduate",
    "computer science", "mathematics", "physics", "chemistry", "biology",
    "engineering", "business", "economics", "psychology", "art",
    "active", "inactive", "capacity", "capacity"
}

FORBIDDEN_INTENT_PATTERNS = [
    (r"(?i)\b(delete|drop|truncate|alter|create|insert|update|grant|revoke)\b", "write/DDL operations are not allowed"),
    (r"(?i)\b(system|os\.system|subprocess|exec|eval|import|__)\b", "system/code execution is not allowed"),
    (r"(?i)\b(hack|crack|exploit|bypass|attack|inject|malware|virus)\b", "malicious intent detected"),
    (r"(?i)(api.?key|secret.?key|password|token|credential)", "sensitive credential access is not allowed"),
    (r"(?i)\b(admin|root|superuser|sudo)\b", "privileged access requests are not allowed"),
    (r"(?i)(send.?email|send.?message|post.?to|tweet|slack)", "external communication actions not allowed"),
    (r"(?i)\b(bitcoin|crypto|wallet|bank.?account|credit.?card.?number)\b", "financial data exfiltration not allowed"),
]

OFF_TOPIC_BLOCK_THRESHOLD = 3


class PolicyLayerGuardrail:
    def check(self, user_input: str) -> GuardrailResult:
        text = user_input.lower().strip()

        # Block empty input
        if not text:
            return GuardrailResult(passed=False, reason="Empty input is not allowed.")

        # Check for forbidden intent patterns
        for pattern, reason in FORBIDDEN_INTENT_PATTERNS:
            if re.search(pattern, text):
                return GuardrailResult(
                    passed=False,
                    reason=f"Policy violation: {reason}.",
                    metadata={"matched_pattern": pattern}
                )

        # Check domain relevance: at least one education keyword must be present
        words_in_input = set(re.findall(r'\b\w+\b', text))
        keyword_hits = words_in_input & ALLOWED_KEYWORDS
        # Also check multi-word phrases
        for kw in ALLOWED_KEYWORDS:
            if kw in text:
                keyword_hits.add(kw)

        if not keyword_hits:
            return GuardrailResult(
                passed=False,
                reason=(
                    "This assistant only handles queries about students, courses, and transactions. "
                    "Your query appears unrelated to the education database."
                ),
                metadata={"keyword_hits": 0}
            )

        return GuardrailResult(
            passed=True,
            metadata={"keyword_hits": list(keyword_hits)[:10]}
        )
