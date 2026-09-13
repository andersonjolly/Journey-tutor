# Journey Tutor

AI-powered personalised learning MVP. Given a **topic**, **duration**, and **difficulty**, the API returns a structured lesson plan with learning objectives, ordered sections, and a narrated script.

> Google Maps is intentionally **not** in scope for this milestone.

## Architecture

| Package | Responsibility |
|---|---|
| `journey_tutor.api` | FastAPI routes, request/response schemas, dependency injection |
| `journey_tutor.domain` | Deterministic business logic (word budget) and `LessonService` orchestration |
| `journey_tutor.ai` | Replaceable LLM providers (`GeminiLessonGenerator`, `FakeLessonGenerator`) behind a protocol |
| `journey_tutor.config` | Settings from environment variables (no hard-coded secrets) |

FastAPI route handlers never call Gemini directly. They depend on `LessonService`, which talks to a `LessonGenerator` implementation.

```
POST /lessons  →  LessonService  →  LessonGenerator (Gemini | Fake)
                      ↑
               estimate_word_budget()
```

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- A Gemini API key for live generation (optional for local tests — fake provider is used when unset)

## Local setup

```bash
# Install dependencies (creates .venv)
uv sync

# Optional: configure Gemini
cp .env.example .env
# edit .env and set GEMINI_API_KEY=...

# Run the API
uv run uvicorn journey_tutor.main:app --reload --host 0.0.0.0 --port 8000
```

Open interactive docs at <http://127.0.0.1:8000/docs>.

### Docker

```bash
docker build -t journey-tutor .
docker run --rm -p 8000:8000 -e GEMINI_API_KEY="$GEMINI_API_KEY" journey-tutor
```

## API usage

### `GET /health`

```bash
curl -s http://127.0.0.1:8000/health
```

### `POST /lessons`

```bash
curl -s -X POST http://127.0.0.1:8000/lessons \
  -H 'Content-Type: application/json' \
  -d '{
    "topic": "photosynthesis",
    "duration_minutes": 20,
    "difficulty": "beginner"
  }'
```

**Request**

| Field | Type | Notes |
|---|---|---|
| `topic` | string | 1–200 characters |
| `duration_minutes` | int | 1–120 |
| `difficulty` | enum | `beginner` \| `intermediate` \| `advanced` |

**Response** includes `title`, `topic`, `duration_minutes`, `difficulty`, `word_budget`, `learning_objectives`, and ordered `sections` (each with `title`, `estimated_word_count`, `narration_script`).

Word budget is computed deterministically as `duration_minutes × WORDS_PER_MINUTE` (default **130**).

Without `GEMINI_API_KEY`, the API uses `FakeLessonGenerator` so you can exercise the full path offline.

## Development

```bash
# Unit + API tests (no real LLM calls)
uv run pytest

# Lint
uv run ruff check src tests

# Type check
uv run mypy
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | _(empty)_ | Enables live Gemini generation |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Model id |
| `WORDS_PER_MINUTE` | `130` | Narration speaking-rate for word budgets |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Server bind (CLI `journey-tutor`) |

## Out of scope (this milestone)

Auth, database, frontend, payments, cloud deploy orchestration, background workers, RAG / vector DB, and Google Maps.
