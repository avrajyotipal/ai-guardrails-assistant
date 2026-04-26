"""
Streamlit frontend — Chat interface + Monitoring Dashboard
"""

import streamlit as st
import requests
import uuid
import pandas as pd

API_URL = "http://localhost:8000/api/v1"


# ════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS  (defined first so they are available everywhere below)
# ════════════════════════════════════════════════════════════════════════════

def _call_chat_api(message: str, chat_history: list) -> dict:
    try:
        resp = requests.post(
            f"{API_URL}/chat",
            json={
                "session_id": st.session_state.session_id,
                "message": message,
                "chat_history": chat_history,
            },
            timeout=90,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {
            "blocked": True,
            "block_layer": "system",
            "block_reason": "Cannot connect to backend. Make sure FastAPI is running on port 8000.",
        }
    except Exception as exc:
        return {"blocked": True, "block_layer": "system", "block_reason": str(exc)}


def _fetch_stats() -> dict:
    try:
        r = requests.get(f"{API_URL}/monitoring/stats", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def _fetch_logs(session_id=None, blocked_only=False, limit=50) -> list:
    try:
        params = {"blocked_only": blocked_only, "limit": limit}
        if session_id:
            params["session_id"] = session_id
        r = requests.get(f"{API_URL}/monitoring/logs", params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("logs", [])
    except Exception:
        return []


def _render_guardrail_badge(gs: dict):
    """Renders a compact inline guardrail status strip under a message."""
    if not gs:
        return

    def badge(label: str, passed) -> str:
        if passed is None:
            cls, symbol = "badge-grey", "—"
        elif passed:
            cls, symbol = "badge-green", "&#10003;"
        else:
            cls, symbol = "badge-red", "&#10007;"
        return f'<span class="layer-badge {cls}">{label} {symbol}</span>'

    badges = "".join([
        badge("Policy",      gs.get("policy_passed")),
        badge("Input",       gs.get("input_passed")),
        badge("Instruction", gs.get("instruction_passed")),
        badge("Output",      gs.get("output_passed")),
    ])

    extras = []
    if gs.get("hallucination_detected"):
        extras.append('<span class="layer-badge badge-red">! Hallucination</span>')
    if gs.get("injection_detected"):
        extras.append('<span class="layer-badge badge-red">! Injection</span>')
    if gs.get("jailbreak_detected"):
        extras.append('<span class="layer-badge badge-red">! Jailbreak</span>')

    tools = gs.get("tools_called", [])
    if tools:
        tool_str = ", ".join(tools[:3])
        if len(tools) > 3:
            tool_str += f" +{len(tools) - 3}"
        extras.append(f'<span class="layer-badge badge-grey">Tools: {tool_str}</span>')

    ms = gs.get("processing_time_ms")
    if ms:
        extras.append(f'<span class="layer-badge badge-grey">{ms} ms</span>')

    st.markdown(
        f'<div style="margin-top:4px">{badges}{"".join(extras)}</div>',
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="AI Database Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container { padding-top: 1rem; }
.layer-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin: 2px 2px 4px 0;
}
.badge-green { background: #d4edda; color: #155724; }
.badge-red   { background: #f8d7da; color: #721c24; }
.badge-grey  { background: #e2e3e5; color: #383d41; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════════════════

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_message" not in st.session_state:
    st.session_state.pending_message = ""


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("AI Database Assistant")
    st.caption("Powered by LangChain + Euri API (gpt-4.1-nano)")
    st.divider()

    page = st.radio(
        "Navigate",
        ["Chat", "Monitoring Dashboard"],
        format_func=lambda x: f"{'💬' if x == 'Chat' else '📊'} {x}",
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown(f"**Session:** `{st.session_state.session_id[:12]}...`")
    if st.button("New Session", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("Try these queries")
    EXAMPLES = [
        "How many students are in each department?",
        "Show me Engineering courses",
        "What is the total revenue from completed transactions?",
        "List students with GPA above 3.8",
        "Which payment method is most popular?",
        "How many pending transactions are there?",
        "Show enrollment statistics",
        "Find students named John",
        "What courses are offered in Fall 2024?",
        "Give me a summary of student STU00001",
    ]
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True, key=f"ex_{ex[:25]}"):
            st.session_state.pending_message = ex
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PAGE: CHAT
# ════════════════════════════════════════════════════════════════════════════

if page == "Chat":
    st.title("Chat with your Database")
    st.caption("Ask anything about students, courses, or transactions.")

    # Render existing chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("guardrail_summary"):
                _render_guardrail_badge(msg["guardrail_summary"])

    # Input — either from sidebar example button or chat input box
    if st.session_state.pending_message:
        prompt = st.session_state.pending_message
        st.session_state.pending_message = ""
    else:
        prompt = st.chat_input("Ask about students, courses, or transactions...")

    if prompt:
        # Show user message immediately
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build history to send (exclude the just-added user message)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
            if m["role"] in ("user", "assistant")
        ]

        # Call backend
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                resp_data = _call_chat_api(prompt, history)

            if resp_data.get("blocked"):
                layer  = (resp_data.get("block_layer") or "unknown").title()
                reason = resp_data.get("block_reason", "Request blocked by guardrails.")
                answer = f"**Blocked by {layer} Layer**\n\n{reason}"
                st.error(answer)
            else:
                answer = resp_data.get("response", "Sorry, I could not get a response.")
                st.markdown(answer)

            gs = resp_data.get("guardrail_summary")
            if gs:
                _render_guardrail_badge(gs)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "guardrail_summary": resp_data.get("guardrail_summary"),
        })


# ════════════════════════════════════════════════════════════════════════════
# PAGE: MONITORING DASHBOARD
# ════════════════════════════════════════════════════════════════════════════

elif page == "Monitoring Dashboard":
    st.title("Monitoring Dashboard")
    st.caption("Live view of guardrail activity, tool usage, and system health.")

    if st.button("Refresh"):
        st.rerun()

    stats = _fetch_stats()

    if not stats or stats.get("total_queries", 0) == 0:
        st.info("No monitoring data yet. Start chatting to generate logs.")
    else:
        # KPI row
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Queries",      stats.get("total_queries", 0))
        c2.metric("Blocked",            stats.get("blocked_queries", 0),
                  delta=f"{stats.get('block_rate_pct', 0)}%", delta_color="inverse")
        c3.metric("Hallucinations",     stats.get("hallucinations_detected", 0), delta_color="inverse")
        c4.metric("Injection Attempts", stats.get("injection_attempts", 0), delta_color="inverse")
        c5.metric("Avg Response (ms)",  stats.get("avg_response_time_ms", 0))

        st.divider()
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Guardrail Layer Blocks")
            layer_data = {
                "Policy":      stats.get("policy_layer_blocks", 0),
                "Input":       stats.get("input_layer_blocks", 0),
                "Output":      stats.get("output_layer_blocks", 0),
                "Jailbreaks":  stats.get("jailbreak_attempts", 0),
            }
            df_layers = pd.DataFrame(
                list(layer_data.items()), columns=["Layer", "Blocks"]
            ).set_index("Layer")
            st.bar_chart(df_layers)

        with col_right:
            st.subheader("Tool Usage")
            tool_usage = stats.get("tool_usage", {})
            if tool_usage:
                df_tools = pd.DataFrame(
                    sorted(tool_usage.items(), key=lambda x: x[1], reverse=True),
                    columns=["Tool", "Calls"],
                ).set_index("Tool")
                st.bar_chart(df_tools)
            else:
                st.info("No tool calls recorded yet.")

        st.divider()

        # Logs table
        st.subheader("Recent Logs")
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            filter_session = st.text_input("Filter by Session ID (optional)")
        with col_f2:
            blocked_only = st.checkbox("Blocked only")
        with col_f3:
            log_limit = st.slider("Max logs", 10, 100, 25)

        logs = _fetch_logs(
            session_id=filter_session or None,
            blocked_only=blocked_only,
            limit=log_limit,
        )

        if not logs:
            st.info("No logs match the current filters.")
        else:
            rows = []
            for log in logs:
                def _flag(key):
                    val = log.get(key)
                    if val is None:
                        return "-"
                    return "YES" if val else "no"

                rows.append({
                    "Time":          (log.get("timestamp") or "")[:19].replace("T", " "),
                    "Session":       str(log.get("session_id", ""))[:8] + "...",
                    "Input":         str(log.get("user_input", ""))[:55],
                    "Policy":        "PASS" if log.get("policy_passed") else "FAIL",
                    "Input Lyr":     "PASS" if log.get("input_passed") else "FAIL",
                    "Instruction":   "PASS" if log.get("instruction_passed") else "FAIL",
                    "Output":        "PASS" if log.get("output_passed") else "FAIL",
                    "Blocked":       "YES" if log.get("total_blocked") else "no",
                    "Hallucination": _flag("hallucination_detected"),
                    "Injection":     _flag("injection_detected"),
                    "Jailbreak":     _flag("jailbreak_detected"),
                    "ms":            log.get("processing_time_ms", "-"),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Log detail inspector
            st.subheader("Log Detail Inspector")
            log_idx = st.selectbox(
                "Select a log entry to inspect",
                options=range(len(logs)),
                format_func=lambda i: (
                    f"{(logs[i].get('timestamp') or '')[:19]}  |  "
                    f"{'BLOCKED' if logs[i].get('total_blocked') else 'allowed'}  |  "
                    f"{str(logs[i].get('user_input', ''))[:45]}"
                ),
            )
            if log_idx is not None:
                sel = logs[log_idx]
                with st.expander("Full Log Entry", expanded=True):
                    ca, cb = st.columns(2)
                    with ca:
                        st.markdown("**User Input**")
                        st.code(sel.get("user_input") or "")
                        st.markdown("**Final Response**")
                        st.code(sel.get("final_response") or "(blocked / empty)")
                    with cb:
                        st.markdown("**Guardrail Decisions**")
                        st.json({
                            "policy_passed":          sel.get("policy_passed"),
                            "policy_block_reason":    sel.get("policy_block_reason"),
                            "input_passed":           sel.get("input_passed"),
                            "input_block_reason":     sel.get("input_block_reason"),
                            "injection_detected":     sel.get("injection_detected"),
                            "instruction_passed":     sel.get("instruction_passed"),
                            "jailbreak_detected":     sel.get("jailbreak_detected"),
                            "output_passed":          sel.get("output_passed"),
                            "output_block_reason":    sel.get("output_block_reason"),
                            "hallucination_detected": sel.get("hallucination_detected"),
                            "hallucination_details":  sel.get("hallucination_details"),
                            "pii_detected":           sel.get("pii_detected"),
                        })

                    st.markdown("**Tools Called**")
                    tc = sel.get("tools_called") or []
                    st.json(tc) if tc else st.caption("No tools called.")

                    st.markdown("**Tools Blocked**")
                    tb = sel.get("tools_blocked") or []
                    st.json(tb) if tb else st.caption("No tools blocked.")
