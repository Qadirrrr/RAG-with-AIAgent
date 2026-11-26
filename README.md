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
- **AI:** Self-hosted Ollama only. Chat uses a Qwen model
  (`qwen2.5:7b` by default) and embeddings use BGE (`bge-m3`), both
  served by Ollama on your own server. No cloud AI API keys anywhere.

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
for production deployment (manual Ubuntu VPS + Postgres, no Docker).

```bash
# Backend
cp backend/.env.example backend/.env   # fill in JWT_SECRET (no AI keys needed)
cd backend
python -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt
../.venv/bin/python run.py              # http://localhost:8000, docs at /docs

# Frontend (new terminal)
cd frontend
npm install
npm run dev                             # http://localhost:5173
```

Before the first run, install Ollama and pull the models:

```bash
ollama pull qwen2.5:7b
ollama pull bge-m3
```

Sign up in the app. The first account with the email in
`SUPER_ADMIN_EMAIL` becomes super-admin. Live AI answers need Ollama
running with the models pulled; if Ollama is unreachable the chat
returns a clear "self-hosted Ollama service is not available" message
instead of crashing.

## Public API

Anyone can ask a chatbot a question from their own code. One API key is
linked to one chatbot, and answers come only from that chatbot's own
documents, so every chatbot gives personalized answers for its owner.

- **Endpoint:** `POST /api/public/chat`
- **Auth:** header `X-Agent-Key: <your API key>` (create keys on the
  Integrations page in the dashboard)
- **Body:** `{"message": "What are your opening hours?"}`. Add
  `"conversation_id"` from a previous response to continue the same
  conversation. No agent ID is needed; the key selects the chatbot.
- **Response:** `{"conversation_id": "...", "response": "...", "sources": [], "agent_steps": []}`
- **Errors:** `401` missing or invalid key (or an `agent_id` that does not
  belong to the key), `403` chatbot deactivated, `422` missing `message`.

Runnable example (about 15 lines of Python):
[`examples/python_client.py`](examples/python_client.py)

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

- There are no cloud AI API keys: the AI runs on your own Ollama server.
- Agent API keys are stored as SHA256 hashes; the full key is shown once.
- Secrets such as `JWT_SECRET` live only in backend environment
  variables, never in code. `backend/.env` and `frontend/.env` are
  git-ignored.
- Set `CORS_ORIGINS` to your real frontend origin in production, not `*`.
