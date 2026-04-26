"""
Monitoring Layer Guardrail
Persists every log entry to the monitoring_logs table via psycopg2.
Also exposes retrieval methods for the monitoring dashboard.
"""

import json
from typing import Optional
from .base import MonitoringLogEntry


class MonitoringLayerGuardrail:
    def log(self, entry: MonitoringLogEntry) -> None:
        try:
            from database import get_db
            record = entry.to_dict()

            def _safe_json(v):
                return json.dumps(v, default=str) if v is not None else json.dumps([])

            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO monitoring_logs (
                        session_id, timestamp, user_input,
                        policy_passed, policy_block_reason,
                        input_passed, input_block_reason, input_sanitized, injection_detected,
                        instruction_passed, instruction_block_reason, jailbreak_detected,
                        tools_called, tools_blocked, tool_execution_details,
                        llm_raw_output, output_passed, output_block_reason,
                        hallucination_detected, hallucination_details, pii_detected,
                        final_response, total_blocked, processing_time_ms, metadata
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s
                    )
                """, (
                    record["session_id"], record["timestamp"], record["user_input"],
                    record["policy_passed"], record["policy_block_reason"],
                    record["input_passed"], record["input_block_reason"],
                    record["input_sanitized"], record["injection_detected"],
                    record["instruction_passed"], record["instruction_block_reason"],
                    record["jailbreak_detected"],
                    _safe_json(record["tools_called"]),
                    _safe_json(record["tools_blocked"]),
                    _safe_json(record["tool_execution_details"]),
                    record["llm_raw_output"], record["output_passed"],
                    record["output_block_reason"],
                    record["hallucination_detected"], record["hallucination_details"],
                    record["pii_detected"],
                    record["final_response"], record["total_blocked"],
                    record["processing_time_ms"],
                    json.dumps(record["metadata"], default=str),
                ))
        except Exception as exc:
            print(f"[MonitoringLayer] Logging failed: {exc}")

    def get_logs(
        self,
        session_id: Optional[str] = None,
        blocked_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        try:
            from database import get_db, fetchall_as_dicts
            conditions, params = [], []
            if session_id:
                conditions.append("session_id = %s")
                params.append(session_id)
            if blocked_only:
                conditions.append("total_blocked = TRUE")

            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            params += [limit, offset]

            with get_db() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"SELECT * FROM monitoring_logs {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    params
                )
                return fetchall_as_dicts(cur)
        except Exception as exc:
            print(f"[MonitoringLayer] Log retrieval failed: {exc}")
            return []

    def get_stats(self) -> dict:
        try:
            from database import get_db, fetchone_as_dict, fetchall_as_dicts
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE total_blocked) AS blocked,
                        COUNT(*) FILTER (WHERE hallucination_detected) AS hallucinations,
                        COUNT(*) FILTER (WHERE injection_detected) AS injections,
                        COUNT(*) FILTER (WHERE jailbreak_detected) AS jailbreaks,
                        COUNT(*) FILTER (WHERE policy_passed = FALSE) AS policy_fails,
                        COUNT(*) FILTER (WHERE input_passed = FALSE) AS input_fails,
                        COUNT(*) FILTER (WHERE output_passed = FALSE) AS output_fails,
                        ROUND(AVG(processing_time_ms)::numeric, 1) AS avg_ms
                    FROM monitoring_logs
                """)
                row = fetchone_as_dict(cur)

                cur.execute("SELECT tools_called FROM monitoring_logs WHERE tools_called IS NOT NULL")
                tool_rows = fetchall_as_dicts(cur)

            total = int(row["total"] or 0)
            if total == 0:
                return {"total_queries": 0}

            blocked = int(row["blocked"] or 0)

            # Count tool usage across all log entries
            tool_counts: dict[str, int] = {}
            for r in tool_rows:
                calls = r.get("tools_called") or []
                if isinstance(calls, str):
                    try:
                        calls = json.loads(calls)
                    except Exception:
                        calls = []
                for tc in calls:
                    t = tc.get("tool", "unknown") if isinstance(tc, dict) else str(tc)
                    tool_counts[t] = tool_counts.get(t, 0) + 1

            return {
                "total_queries": total,
                "blocked_queries": blocked,
                "block_rate_pct": round(blocked / total * 100, 1),
                "hallucinations_detected": int(row["hallucinations"] or 0),
                "injection_attempts": int(row["injections"] or 0),
                "jailbreak_attempts": int(row["jailbreaks"] or 0),
                "policy_layer_blocks": int(row["policy_fails"] or 0),
                "input_layer_blocks": int(row["input_fails"] or 0),
                "output_layer_blocks": int(row["output_fails"] or 0),
                "tool_usage": tool_counts,
                "avg_response_time_ms": float(row["avg_ms"] or 0),
            }
        except Exception as exc:
            print(f"[MonitoringLayer] Stats retrieval failed: {exc}")
            return {}
