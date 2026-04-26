"""
Direct OpenAI-SDK agent loop — bypasses langchain-openai's max_tokens issue.
Compatible with the Euri API (OpenAI-compatible endpoint).
"""

import json
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI
from langchain_core.tools import BaseTool

from config import settings
from agent.tools import ALL_TOOLS

# Build OpenAI-format tool schemas from LangChain tools once at import time
def _lc_tool_to_openai_schema(tool: BaseTool) -> dict:
    schema = tool.get_input_schema().model_json_schema()
    schema.pop("title", None)
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": schema,
        },
    }

_TOOL_SCHEMAS = [_lc_tool_to_openai_schema(t) for t in ALL_TOOLS]
_TOOL_MAP: dict[str, BaseTool] = {t.name: t for t in ALL_TOOLS}


async def run_agent(
    user_input: str,
    system_prompt: str,
    chat_history: list[dict],
    execution_layer,
    session_id: str,
) -> tuple[str, list[dict], list[str]]:
    """
    Run the tool-calling agent and return (response_text, tool_calls, tool_outputs).
    Uses the OpenAI SDK directly so max_tokens and other params are fully controlled.
    """
    client = AsyncOpenAI(
        api_key=settings.EURI_API_KEY,
        base_url=settings.EURI_BASE_URL,
    )

    # Build message list
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in chat_history:
        role = msg.get("role", "")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_input})

    tool_call_records: list[dict] = []
    tool_outputs:      list[str]  = []

    max_iterations = 6  # safety cap
    for _ in range(max_iterations):
        completion = await client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=messages,
            tools=_TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0,
            max_tokens=4096,
        )

        msg = completion.choices[0].message

        # No tool calls → final answer
        if not msg.tool_calls:
            return msg.content or "", tool_call_records, tool_outputs

        # Append assistant message with tool_calls to history
        messages.append(msg.model_dump(exclude_none=True))

        # Execute each tool call
        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                raw_args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                raw_args = {}

            # Execution layer check
            exec_result = execution_layer.validate_tool_call(
                tool_name, str(raw_args), session_id
            )

            call_record: dict[str, Any] = {
                "tool": tool_name,
                "input": str(raw_args)[:500],
                "execution_allowed": exec_result.passed,
                "reason": exec_result.reason,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if exec_result.passed and tool_name in _TOOL_MAP:
                try:
                    output = _TOOL_MAP[tool_name].run(raw_args)
                except Exception as tool_exc:
                    output = f"Tool error: {tool_exc}"
            else:
                output = f"BLOCKED: {exec_result.reason or 'tool not allowed'}"

            call_record["output_preview"] = str(output)[:300]
            tool_call_records.append(call_record)
            tool_outputs.append(str(output)[:2000])

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(output),
            })

    # If we exhausted iterations without a final answer
    return "I processed your request but could not produce a final answer. Please try again.", tool_call_records, tool_outputs
