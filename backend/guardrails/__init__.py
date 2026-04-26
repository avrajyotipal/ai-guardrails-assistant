"""
Guardrail pipeline — orchestrates all 6 layers in sequence.
"""

import time
from .base import GuardrailResult, MonitoringLogEntry
from .policy_layer import PolicyLayerGuardrail
from .input_layer import InputLayerGuardrail
from .instruction_layer import InstructionLayerGuardrail
from .execution_layer import ExecutionLayerGuardrail
from .output_layer import OutputLayerGuardrail
from .monitoring_layer import MonitoringLayerGuardrail
from models import ChatResponse, GuardrailSummary


class GuardrailPipeline:
    def __init__(self):
        self.policy = PolicyLayerGuardrail()
        self.input_guard = InputLayerGuardrail()
        self.instruction = InstructionLayerGuardrail()
        self.execution = ExecutionLayerGuardrail()
        self.output_guard = OutputLayerGuardrail()
        self.monitoring = MonitoringLayerGuardrail()

    async def process(
        self,
        session_id: str,
        user_input: str,
        chat_history: list,
    ) -> ChatResponse:
        from agent.agent import run_agent

        start_ms = time.time()
        log = MonitoringLogEntry(session_id=session_id, user_input=user_input)

        def elapsed() -> int:
            return int((time.time() - start_ms) * 1000)

        def _blocked(layer: str, reason: str) -> ChatResponse:
            log.total_blocked = True
            log.processing_time_ms = elapsed()
            self.monitoring.log(log)
            return ChatResponse(
                session_id=session_id,
                blocked=True,
                block_reason=reason,
                block_layer=layer,
                guardrail_summary=_summary(log),
                processing_time_ms=log.processing_time_ms,
            )

        # ── 1. POLICY LAYER ──────────────────────────────────────────────────
        policy_result = self.policy.check(user_input)
        log.policy_passed = policy_result.passed
        log.policy_block_reason = policy_result.reason
        if not policy_result.passed:
            return _blocked("policy", policy_result.reason)

        # ── 2. INPUT LAYER ───────────────────────────────────────────────────
        input_result = self.input_guard.check(user_input)
        log.input_passed = input_result.passed
        log.input_block_reason = input_result.reason
        log.input_sanitized = input_result.sanitized_input
        if input_result.metadata and input_result.metadata.get("type") in ("sql_injection", "prompt_injection"):
            log.injection_detected = True
        if not input_result.passed:
            return _blocked("input", input_result.reason)

        sanitized = input_result.sanitized_input or user_input

        # ── 3. INSTRUCTION LAYER ─────────────────────────────────────────────
        system_prompt, instr_result = self.instruction.build_safe_instructions(sanitized)
        log.instruction_passed = instr_result.passed
        log.instruction_block_reason = instr_result.reason
        log.system_prompt_used = system_prompt[:500]
        if not instr_result.passed:
            log.jailbreak_detected = True
            return _blocked("instruction", instr_result.reason)

        # ── 4. AGENT EXECUTION (with execution-layer callback) ────────────────
        response, tool_calls, tool_outputs = await run_agent(
            user_input=sanitized,
            system_prompt=system_prompt,
            chat_history=chat_history,
            execution_layer=self.execution,
            session_id=session_id,
        )

        log.tools_called = [t for t in tool_calls if t.get("execution_allowed", True)]
        log.tools_blocked = [t for t in tool_calls if not t.get("execution_allowed", True)]
        log.tool_execution_details = tool_calls
        log.llm_raw_output = response

        # ── 5. OUTPUT LAYER ──────────────────────────────────────────────────
        output_result = self.output_guard.check(response, tool_outputs)
        log.output_passed = output_result.passed
        log.output_block_reason = output_result.reason
        if output_result.metadata and output_result.metadata.get("hallucination"):
            log.hallucination_detected = True
            log.hallucination_details = output_result.reason
        log.pii_detected = self.output_guard.check_pii_present(response)

        if not output_result.passed:
            return _blocked("output", output_result.reason)

        # ── 6. MONITORING LAYER ───────────────────────────────────────────────
        log.final_response = response
        log.processing_time_ms = elapsed()
        self.monitoring.log(log)

        return ChatResponse(
            session_id=session_id,
            response=response,
            guardrail_summary=_summary(log),
            processing_time_ms=log.processing_time_ms,
        )


def _summary(log: MonitoringLogEntry) -> GuardrailSummary:
    return GuardrailSummary(
        policy_passed=log.policy_passed,
        input_passed=log.input_passed,
        instruction_passed=log.instruction_passed,
        output_passed=log.output_passed,
        hallucination_detected=log.hallucination_detected,
        injection_detected=log.injection_detected,
        jailbreak_detected=log.jailbreak_detected,
        tools_called=[t.get("tool", "") for t in log.tools_called],
        tools_blocked=[t.get("tool", "") for t in log.tools_blocked],
        processing_time_ms=log.processing_time_ms,
    )
