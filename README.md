# AI Classifier

A FastAPI service that classifies internal team requests (Slack, Telegram, Email) using an LLM. Upload a CSV of raw requests and get back structured classification results with a summary report.

Built as a test assignment for Netpeak AI Solutions.

---

## How to Run

### With Docker
```bash
# 1. Copy the example env file and fill in your values
cp .env.example .env

# 2. Build and start
docker compose up --build -d
```

The API will be available at `http://localhost:8000`.  
Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key — get one free at [console.groq.com](https://console.groq.com) |
| `GROQ_URL` | `https://api.groq.com/openai/v1/chat/completions` |
| `GROQ_MODEL` | `meta-llama/llama-4-scout-17b-16e-instruct` |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/classify` | Upload a `.csv` file — classifies all rows, writes `output.json` + `report.md` |
| `GET` | `/results` | Download the latest `output.json` |
| `GET` | `/report` | Download the latest `report.md` |
| `GET` | `/health` | Healthcheck |

---

## Input CSV Format

The uploaded file must have exactly these columns:

| Column | Description |
|---|---|
| `id` | Unique request identifier |
| `channel` | Source channel (Slack, Telegram, Email) |
| `timestamp` | When the request was sent |
| `raw_text` | The raw request text |

---

## Output Schema

Each entry in `output.json`:

| Field | Type | Description |
|---|---|---|
| `id` | string | Original row ID |
| `channel` | string | Source channel |
| `timestamp` | string | Original timestamp |
| `raw_text` | string | Original request text |
| `category` | enum | `automation` / `integration` / `report/analytics` / `bug/support` / `question/consultation` / `out of scope` |
| `target_department` | string? | Requesting department or null |
| `priority` | enum | `low` / `medium` / `high` |
| `short_summary` | string | One-sentence summary in Ukrainian |
| `requested_actions` | string[] | Concrete actions requested, in Ukrainian |
| `needs_clarification` | bool | True if the request is too vague to act on |
| `estimated_effort` | string? | Rough effort estimate e.g. `"1-2h"`, `"1 day"` |
| `confidence_score` | float? | LLM self-rated confidence 0.0–1.0 |
| `llm_error` | string? | Populated if LLM returned invalid output — fallback values used |

### Why extra fields?
- `estimated_effort` — helps with sprint planning and workload estimation
- `confidence_score` — surfaces uncertain classifications for human review

---

## Where It Breaks / Limitations

### Invalid LLM output
If the LLM returns malformed JSON or a value outside the allowed enum, Pydantic validation catches it. The row gets a safe fallback: `category=out of scope`, `needs_clarification=true`, `priority=low`, and the raw error is stored in `llm_error`. The service never crashes on a bad row.

### Non-determinism
LLMs are non-deterministic — the same request may get a slightly different classification on each run. The prompt constrains allowed values tightly (`temperature=0.1`) and the fixed enum schema prevents most drift. The `confidence_score` field helps flag uncertain cases.

### Large volumes
Rows are processed concurrently using `asyncio.gather` with a semaphore of 5 — meaning up to 5 Groq requests fire in parallel at a time. For very large CSVs (200+ rows) the HTTP request may still time out on the client side. This would be addressed with a background job queue in production.

### Rate limits
Groq's free tier allows up to 14,400 requests/day on Llama 4 Scout. Concurrent processing is bounded by a semaphore of 5 to stay within rate limits. If limits are hit, affected rows fall back gracefully with the error logged in `llm_error`.

### Single result set
A new `/classify` call overwrites the previous `output.json` and `report.md`. There is no per-job history.

### Token cost
Groq's free tier has no token cost for the models used. With a paid model, each request costs roughly 300–600 input tokens + ~200 output tokens. For 100 rows expect ~$0.05–0.10 depending on the model.

---

## What I'd Do Next (given more time)

- **Async job queue** — Celery + Redis so `/classify` returns a `job_id` immediately and processing happens in the background, solving the HTTP timeout problem for very large files
- **Retry logic** — parse `retry_after` from 429 responses and retry automatically instead of failing the row
- **Telegram digest** — POST the `report.md` summary to a configured Telegram chat after each run
- **Google Sheets export** — write results directly to a Sheet via gspread for non-technical stakeholders
- **Per-job storage** — store results per job ID so multiple CSVs can be processed without overwriting each other
- **Frontend** — simple HTML upload form so non-technical users don't need Swagger UI or curl

---