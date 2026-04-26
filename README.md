# AI Database Assistant with 6-Layer Guardrails

A production-ready agentic system that lets users query an education database through natural language — protected by a comprehensive 6-layer guardrail pipeline.

## Architecture

```
User (Streamlit Chat UI)
        │
        ▼
  FastAPI Backend
        │
  ┌─────▼─────────────────────────────────┐
  │         Guardrail Pipeline             │
  │  1. Policy Layer      (intent check)  │
  │  2. Input Layer       (injection/XSS) │
  │  3. Instruction Layer (jailbreak)     │
  │  4. Execution Layer   (tool control)  │
  │  5. Output Layer      (hallucination) │
  │  6. Monitoring Layer  (full logging)  │
  └─────┬─────────────────────────────────┘
        │
  LangChain Agent (Euri API / gpt-4.1-nano)
        │
  ┌─────▼──────┐
  │  Supabase  │  (PostgreSQL)
  │  students  │
  │  courses   │
  │  transactions       │
  │  monitoring_logs    │
  └────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI + Python |
| Agent Framework | LangChain + OpenAI SDK |
| LLM | Euri API (gpt-4.1-nano) |
| Database | Supabase (PostgreSQL) |

## The 6 Guardrail Layers

| Layer | What It Does |
|---|---|
| **Policy** | Enforces topic policy — only education domain queries allowed. Blocks write ops, credential requests, off-topic prompts. |
| **Input** | Detects SQL injection, prompt injection, XSS, and other attack vectors. Sanitizes input before it reaches the LLM. |
| **Instruction** | Jailbreak detection. Builds a hardened, unoverridable system prompt. Blocks attempts to change the assistant's persona. |
| **Execution** | Tool allowlist with 10 read-only DB tools. Rate limiting (30 calls/60s per session). Blocks destructive SQL patterns. |
| **Output** | Hallucination detection (cross-references LLM claims against actual DB results). Bulk PII exposure check. Harmful content filter. |
| **Monitoring** | Logs every request end-to-end to `monitoring_logs` table — inputs, guardrail decisions, tool calls, LLM I/O, timings. |

## Database

Seeded with **761 data points** across 4 tables:

| Table | Rows |
|---|---|
| `students` | 200 |
| `courses` | 60 |
| `transactions` | 501 |
| `monitoring_logs` | grows with usage |

## Setup

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/ai-guardrails-assistant.git
cd ai-guardrails-assistant
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```
SUPABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.your-ref.supabase.co:5432/postgres
EURI_API_KEY=your_euri_api_key
EURI_BASE_URL=https://api.euron.one/api/v1/euri
MODEL_NAME=gpt-4.1-nano
```

### 3. Create tables & seed data

Run `scripts/create_tables.sql` in your Supabase SQL Editor, then:

```bash
python scripts/seed_data.py
```

### 4. Run

```bash
# Terminal 1 — backend
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
cd frontend
python -m streamlit run app.py --server.port 8501
```

Open **http://localhost:8501** in your browser.

## Agent Tools

The agent has access to 10 read-only database tools:

- `get_students` — filter by department, GPA, grade level
- `get_student_by_id` — full student record
- `search_students_by_name` — fuzzy name search
- `get_courses` — filter by department, semester, year
- `get_course_enrollment` — fill rate and seat availability
- `get_transactions` — filter by status, payment method
- `get_enrollment_stats` — totals, averages, breakdowns
- `get_revenue_stats` — financial summary by method and status
- `get_department_stats` — per-department student and course counts
- `get_transaction_summary` — full history for one student

## Monitoring Dashboard

The Streamlit app includes a live monitoring dashboard showing:
- Total queries, block rate, hallucination count
- Guardrail layer block breakdown (bar chart)
- Tool usage frequency (bar chart)
- Full log table with per-request detail inspector

## Example Queries

```
How many students are enrolled in each department?
Show me all Engineering courses in Fall 2024
What is the total revenue from completed transactions?
List students with a GPA above 3.8
Which payment method is most popular?
Give me a transaction summary for student STU00042
```

## Project Structure

```
guardrails/
├── backend/
│   ├── main.py                  # FastAPI app
│   ├── config.py                # Settings
│   ├── database.py              # psycopg2 connection pool
│   ├── models.py                # Pydantic request/response models
│   ├── agent/
│   │   ├── agent.py             # OpenAI SDK agent loop
│   │   └── tools.py             # 10 read-only LangChain tools
│   ├── guardrails/
│   │   ├── policy_layer.py
│   │   ├── input_layer.py
│   │   ├── instruction_layer.py
│   │   ├── execution_layer.py
│   │   ├── output_layer.py
│   │   └── monitoring_layer.py
│   └── routers/
│       ├── chat.py
│       └── monitoring.py
├── frontend/
│   └── app.py                   # Streamlit UI
├── scripts/
│   ├── create_tables.sql
│   └── seed_data.py
├── requirements.txt
└── .env.example
```

## License

MIT
