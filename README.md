# RAG AI Agent SaaS

A complete, production-ready **multi-tenant AI Agent SaaS platform**. Anyone can
sign up, create a workspace, upload their own knowledge (PDF, DOCX, TXT or a
website URL), build their own AI agent, test it in a playground, and embed it
on their website with a chat widget or a REST API. No programming needed.

## Stack

- **Frontend:** React 18 + Vite 6 + Tailwind CSS 3
- **Backend:** Python + FastAPI
- **RAG:** LangChain + ChromaDB (per-agent collections)
- **Database:** PostgreSQL (production) or SQLite (local dev, default)
- **AI:** OpenAI (`gpt-4o-mini` / `gpt-4o`) and Google Gemini
  (`gemini-2.0-flash` / `gemini-3.5-flash-lite`), embeddings to match

## What is included

- Signup, login (JWT), individual workspaces, super-admin dashboard
- Multiple AI agents per workspace, each with its own name, instructions,
  language, provider, model and temperature
- Knowledge upload: PDF, DOCX, TXT, MD (10 MB each) and website URLs
  (text extracted, chunked, embedded and stored)
- Complete RAG pipeline with citations (document name + snippet)
- Agent playground, conversation history, analytics and usage tracking
- Website chatbot widget (`frontend/public/widget.js`) and REST API
  (`POST /api/public/chat` with `X-Agent-Key`)
- Subscription plans (Free / Starter $19 / Pro $49 / Scale $99) with
  monthly message, agent and document limits, enforced server-side
- Tenant isolation: every agent has its own Chroma collection
  (`agent_<agent_id>`) and every chunk carries `workspace_id` /
  `agent_id` / `document_id`. Cross-workspace access returns 404.
- Legacy single-tenant routes (`/api/documents`, `/api/chat`,
  `/api/health`, `/api/stats`) still work unchanged.

## Quick start

See [SETUP.md](SETUP.md) for local setup and [DEPLOYMENT.md](DEPLOYMENT.md)
for production deployment (Docker Compose + Postgres).

```bash
# Backend
cp backend/.env.example backend/.env   # fill in GEMINI_API_KEY or OPENAI_API_KEY + JWT_SECRET
cd backend
python -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt
../.venv/bin/python run.py              # http://localhost:8000, docs at /docs

# Frontend (new terminal)
cd frontend
npm install
npm run dev                             # http://localhost:5173
```

Sign up in the app. The first account with the email in
`SUPER_ADMIN_EMAIL` becomes super-admin. A fresh valid Gemini key is
required for live AI answers; without a key the chat returns a clear
"AI API Key is not configured" message instead of crashing.

## Plans

| Plan | Price | Messages/month | Agents | Documents |
| --- | --- | --- | --- | --- |
| Free | $0 | 100 | 1 | 5 |
| Starter | $19 | 1,000 | 5 | 50 |
| Pro | $49 | 10,000 | 20 | 200 |
| Scale | $99 | 50,000 | 100 | 1,000 |

Stripe checkout is a documented TODO (see `backend/app/routes/plans.py`);
plan changes in the MVP are manual / admin upgrades.

## Tests

```bash
cd backend
python -m pytest tests/test_saas.py -v   # 7 tests: auth, tenants, upload, chat, public API, admin
python test_endpoints.py                 # legacy endpoints
cd ../frontend
npm run build                            # production build
```

## Security notes

- API keys live only in backend environment variables, never in code.
- Agent API keys are stored as SHA256 hashes; the full key is shown once.
- `backend/.env` and `frontend/.env` are git-ignored. If a real key was
  ever committed to a repo, rotate it at the provider, removing the file
  from tracking does not erase git history.
- Set `CORS_ORIGINS` to your real frontend origin in production, not `*`.
