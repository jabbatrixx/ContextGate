# ContextGate 🔒

**Generic LLM context-pruning middleware.** Strip irrelevant metadata, mask sensitive fields, and return a minimal token-optimized payload for any LLM — Gemini, GPT-4, Claude, or any other.

---

## The Problem

When an AI agent queries Salesforce, Snowflake, Slack, or any enterprise system, it receives massive JSON payloads with hundreds of irrelevant fields. Dumping that raw data into an LLM causes:

| Problem | Impact |
|---|---|
| **Token Bloat** | You pay for the LLM to read thousands of lines of noise |
| **Latency** | Larger prompts = slower responses |
| **Data Leakage** | Sensitive fields (SSNs, API keys, tokens) touch the LLM |

## The Solution

ContextGate sits between your data source and the LLM. You define what to keep and what to mask in a YAML file. The rest is stripped automatically.

```
[Salesforce / Snowflake / Slack / Discord / Any API]
        │  raw, bloated JSON
        ▼
  ┌─────────────────┐
  │   ContextGate     │  ← reads profiles.yaml
  │   FastAPI API   │  ← masks sensitive fields
  │                 │  ← writes audit log
  └─────────────────┘
        │  clean, minimal JSON
        ▼
  [Your LLM — Gemini / GPT-4 / Claude]
```

### Does Pruning Affect LLM Quality?

**No.** When profiles are configured correctly, the LLM gets *exactly* the fields it needs — nothing more, nothing less.

- **Noise fields** (e.g. `SystemModstamp`, `IsDeleted`, `PhotoUrl`) are system metadata the LLM never uses for reasoning. Removing them **improves** response quality by reducing noise.
- **Masked fields** (e.g. `SSN → "***REDACTED***"`) let the LLM see a field *exists* without exposing the actual value. This is a security boundary.
- **Kept fields** are exactly what the LLM needs to answer the user's question.

> Think of it like giving an analyst a clean spreadsheet with 4 relevant columns instead of a raw database dump with 50.

---

## Dashboard

ContextGate includes a built-in real-time dashboard at `/dashboard`:

- **Live stats** — operations processed, bytes saved, tokens saved (auto-refreshes every 5s)
- **Interactive prune tester** — paste any JSON, pick a profile, and see the pruned result instantly
- **Auto-profiler** — paste any raw API payload, get a profile suggestion with color-coded field tags
- **Audit log** — every pruning operation with % reduction and timestamp

```bash
# Start ContextGate, then open:
http://localhost:8001/dashboard
```

---

## Auto-Profiling

No manual YAML writing needed. Paste any raw API response and ContextGate analyzes it automatically:

- 🟢 **keep** — business-relevant fields (Name, Email, Revenue)
- 🟡 **mask** — sensitive data detected by pattern (SSN, api_token, passwords)
- 🔴 **strip** — system metadata (SystemModstamp, IsDeleted, CreatedById)

### Via Dashboard

Open `/dashboard`, scroll to **🤖 Auto-Profiler**, paste your JSON, click **Analyze →**. Copy the generated YAML into `profiles.yaml`.

### Via API

```bash
curl -X POST http://localhost:8001/api/v1/profile/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "profile_name": "my_crm_source",
    "payload": {
      "Name": "Acme Corp",
      "SSN": "123-45-6789",
      "api_token": "sk-abc123",
      "SystemModstamp": "2024-01-01",
      "IsDeleted": false
    }
  }'
```

**Response:**
```json
{
  "profile_name": "my_crm_source",
  "keep": ["Name", "SSN", "api_token"],
  "mask": ["SSN", "api_token"],
  "strip": ["SystemModstamp", "IsDeleted"],
  "confidence": 0.8,
  "yaml_preview": "my_crm_source:\n  keep:\n  - Name\n  - SSN\n  - api_token\n  mask:\n  - SSN\n  - api_token\n  mask_pattern: '***REDACTED***'\n"
}
```

---

## Quickstart

### 1. Clone & configure

```bash
git clone https://github.com/jabbatrixx/ContextGate.git
cd ContextGate
cp .env.example .env
```

### 2. Add your source in 5 lines of YAML

Open `profiles.yaml` and add a block for your data source:

```yaml
my_api_source:
  keep:
    - name
    - status
    - created_at
  mask:
    - api_token
    - user_email
  mask_pattern: "***REDACTED***"
```

That's it. No Python changes required.

### 3. Run with Docker

```bash
docker compose up --build
```

API is live at `http://localhost:8001`. Interactive docs at `http://localhost:8001/docs`. Dashboard at `http://localhost:8001/dashboard`.

### 4. Prune your first payload

```bash
curl -X POST http://localhost:8001/api/v1/prune \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "salesforce_account",
    "payload": {
      "Name": "Acme Corp",
      "Industry": "Technology",
      "AnnualRevenue": 5000000,
      "SSN": "123-45-6789",
      "SystemModstamp": "2024-01-01",
      "IsDeleted": false,
      "PhotoUrl": "/services/images/photo.png",
      "BillingStreet": "123 Main St"
    }
  }'
```

**Response:**
```json
{
  "source": "salesforce_account",
  "pruned_payload": {
    "Name": "Acme Corp",
    "Industry": "Technology",
    "AnnualRevenue": 5000000,
    "SSN": "***-REDACTED-***"
  },
  "original_bytes": 312,
  "pruned_bytes": 87,
  "bytes_saved": 225,
  "tokens_saved_estimate": 56,
  "timestamp": "2026-02-23T15:25:00Z"
}
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/prune` | Prune a single JSON payload |
| `POST` | `/api/v1/prune/batch` | Prune a list of payloads |
| `POST` | `/api/v1/profile/suggest` | Auto-generate a profile from a sample payload |
| `GET` | `/api/v1/profiles` | List available profiles |
| `GET` | `/api/v1/audit/logs` | View paginated audit log |
| `GET` | `/api/v1/audit/stats` | Aggregate token savings stats |
| `GET` | `/health` | Liveness probe |
| `GET` | `/dashboard` | Real-time pruning dashboard |

### POST /api/v1/prune

```json
{
  "profile": "salesforce_account",
  "payload": { "...": "raw json from your source" }
}
```

### POST /api/v1/prune/batch

```json
{
  "profile": "snowflake_sales_report",
  "payloads": [ { "...": "record 1" }, { "...": "record 2" } ]
}
```

---

## Built-in Profiles

ContextGate ships with example profiles for common enterprise sources:

| Profile | Source | Keep Fields |
|---|---|---|
| `salesforce_account` | Salesforce CRM | Name, Industry, AnnualRevenue |
| `salesforce_contact` | Salesforce CRM | FirstName, LastName, Email, Title |
| `snowflake_sales_report` | Snowflake DW | REGION, REVENUE, PERIOD, REP_NAME |
| `slack_message` | Slack | text, user, channel |
| `discord_event` | Discord | content, author_username, guild_name |
| `hubspot_contact` | HubSpot | firstname, lastname, company, jobtitle |
| `github_issue` | GitHub | title, body, state, labels |

All of these are starting points — copy, modify, and add your own.

---

## Integrating with an AI Agent

ContextGate is designed to sit between your data sources and the LLM. Here's a Python example:

```python
import httpx

async def prune_before_llm(raw_payload: dict, profile: str) -> dict:
    """Call ContextGate before passing data to your LLM."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/api/v1/prune",
            json={"profile": profile, "payload": raw_payload},
        )
        response.raise_for_status()
        return response.json()["pruned_payload"]

# Usage in a Google ADK / LangChain / custom agent:
raw = salesforce_client.get_accounts()
clean = await prune_before_llm(raw[0], "salesforce_account")
# Pass `clean` to Gemini — not `raw`
```

---

## Local Development (without Docker)

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies
uv sync --all-extras

# Run with SQLite (no PostgreSQL needed for dev)
DATABASE_URL="sqlite+aiosqlite:///./dev.db" \
PROFILES_PATH="profiles.yaml" \
uv run uvicorn app.main:app --reload --port 8001
```

Or use the helper script:

```bash
chmod +x run_local.sh
./run_local.sh
```

---

## Running Tests

```bash
uv sync --all-extras
uv run pytest tests/ -v
```

Tests use SQLite in-memory — no Docker or PostgreSQL needed.

---

## Code Quality

```bash
# Lint (PEP 8, PEP 257, security, imports)
uv run ruff check .

# Format
uv run ruff format .

# Pre-commit hooks
uv run pre-commit install
uv run pre-commit run --all-files
```

---

## Project Structure

```
ContextGate/
├── pyproject.toml         # Project config, deps, ruff, pytest
├── uv.lock                # Locked dependency versions
├── .pre-commit-config.yaml
├── profiles.yaml          # All pruning rules — edit this to add sources
├── docker-compose.yml
├── Dockerfile
├── app/
│   ├── config.py          # Centralized Pydantic Settings
│   ├── main.py            # FastAPI entrypoint
│   ├── engine.py          # Generic PruneEngine (YAML-driven)
│   ├── dashboard.py       # Real-time pruning dashboard
│   ├── schemas.py         # Pydantic request/response models
│   ├── database.py        # Async SQLAlchemy engine
│   ├── models.py          # PruneAuditLog ORM model
│   └── routers/
│       ├── prune.py       # POST /api/v1/prune[/batch]
│       └── audit.py       # GET /api/v1/profiles, /audit/*
└── tests/
    ├── conftest.py        # Shared fixtures and test profiles
    ├── test_engine.py     # Unit tests for PruneEngine
    ├── test_masking.py    # Sensitive field masking tests
    └── test_routes.py     # API integration tests
```

---

## Contributing

1. Fork the repo
2. Add your profile to `profiles.yaml`
3. Add tests in `tests/`
4. Run `uv run ruff check .` and `uv run pytest`
5. Open a PR

The most valuable contributions are new `profiles.yaml` examples for real-world APIs.

---

## License

MIT — free to use in commercial and open-source projects.
