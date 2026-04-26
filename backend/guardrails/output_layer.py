"""
Output Layer Guardrail
Validates LLM output before returning to the user:
- Hallucination detection (response claims facts not in tool outputs)
- PII exposure check
- Harmful content check
- Length check
"""

import re
import json
from .base import GuardrailResult
from config import settings

PII_PATTERNS = [
    (r'\b\d{3}-\d{2}-\d{4}\b', "SSN pattern"),
    (r'\b(?:\d{4}[- ]){3}\d{4}\b', "Credit card pattern"),
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "Email — review if bulk exposure"),
    (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', "Phone number pattern"),
]

HARMFUL_OUTPUT_PATTERNS = [
    r"(?i)(here is how to|step.by.step guide to).{0,60}(hack|exploit|bypass|crack|attack)",
    r"(?i)(drop table|delete from|truncate table)\s+\w+",
    r"(?i)system\s+command\s*[:=]",
]


def _extract_numbers(text: str) -> set:
    return set(re.findall(r'\b\d+(?:\.\d+)?\b', text))


def _extract_proper_names(text: str) -> set:
    # Naive: capitalized words that are 3+ chars
    return set(re.findall(r'\b[A-Z][a-z]{2,}\b', text))


class OutputLayerGuardrail:
    def check(self, response: str, tool_outputs: list[str]) -> GuardrailResult:
        if not response or not response.strip():
            return GuardrailResult(passed=False, reason="Empty response from LLM.")

        # Length check
        if len(response) > settings.MAX_OUTPUT_LENGTH:
            return GuardrailResult(
                passed=False,
                reason=f"LLM response exceeds maximum length of {settings.MAX_OUTPUT_LENGTH} characters.",
            )

        # Harmful content check
        for pattern in HARMFUL_OUTPUT_PATTERNS:
            if re.search(pattern, response):
                return GuardrailResult(
                    passed=False,
                    reason="Harmful content detected in LLM output.",
                    metadata={"pattern": pattern}
                )

        # PII bulk-exposure check
        pii_found = []
        for pattern, label in PII_PATTERNS:
            matches = re.findall(pattern, response)
            if len(matches) > 5:  # flag only if many matches (bulk exposure)
                pii_found.append(f"{label}: {len(matches)} occurrences")

        if pii_found:
            return GuardrailResult(
                passed=False,
                reason=f"Bulk PII exposure detected: {'; '.join(pii_found)}",
                metadata={"pii_types": pii_found}
            )

        # Hallucination check
        hallucination_result = self._check_hallucination(response, tool_outputs)
        if not hallucination_result.passed:
            return hallucination_result

        return GuardrailResult(passed=True)

    def _check_hallucination(self, response: str, tool_outputs: list[str]) -> GuardrailResult:
        if not tool_outputs:
            return GuardrailResult(passed=True)

        combined_tool_text = " ".join(str(o) for o in tool_outputs)

        # Check for numbers in the response that don't appear in tool outputs
        response_numbers = _extract_numbers(response)
        tool_numbers = _extract_numbers(combined_tool_text)

        # Filter out common non-hallucination numbers (years, small ordinals, etc.)
        suspicious_numbers = {
            n for n in response_numbers
            if n not in tool_numbers
            and float(n) > 100  # small numbers (counts, indices) are less suspicious
            and float(n) not in {2023, 2024, 2025, 2022}  # year references
        }

        if len(suspicious_numbers) > 2:
            return GuardrailResult(
                passed=False,
                reason="Potential hallucination: response contains numeric values not found in database results.",
                metadata={
                    "suspicious_numbers": list(suspicious_numbers)[:10],
                    "hallucination": True
                }
            )

        # Check for student/course IDs in response that weren't in tool outputs
        id_pattern = r'\b(STU\d{5}|CRS\d{4}|TXN\d{6})\b'
        response_ids = set(re.findall(id_pattern, response))
        tool_ids = set(re.findall(id_pattern, combined_tool_text))
        hallucinated_ids = response_ids - tool_ids

        if hallucinated_ids:
            return GuardrailResult(
                passed=False,
                reason=f"Hallucinated IDs detected in response: {hallucinated_ids}",
                metadata={"hallucinated_ids": list(hallucinated_ids), "hallucination": True}
            )

        return GuardrailResult(passed=True)

    def check_pii_present(self, response: str) -> bool:
        for pattern, _ in PII_PATTERNS:
            if re.search(pattern, response):
                return True
        return False
