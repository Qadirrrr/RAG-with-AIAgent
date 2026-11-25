# Setup and Installation

## Requirements

- Python 3.11+ (3.12 tested)
- Node.js 18+ and npm
- PostgreSQL 15+ (optional for local dev; SQLite is the default)
- A Google Gemini API key (free at https://aistudio.google.com) **or**
  an OpenAI API key. The key must be a real provider key
  (`AIza...` for Gemini, `sk-...` for OpenAI). An OAuth access token
  (`AQ...`) is not a Gemini API key and will be rejected with 401
  UNAUTHENTICATED.

## 1. Clone and configure

```bash
git clone https://github.com/Qadirrrr/RAG-with-AIAgent.git
cd RAG-with-AIAgent
cp backend/.env.example backend/.env
cp .env.example .env        # optional, root copy
```

Edit `backend/.env` and set at least:

```env
GEMINI_API_KEY=AIza...your_real_key...
# or OPENAI_API_KEY=sk-...
JWT_SECRET=<long random string, e.g. output of: openssl rand -hex 32>
SUPER_ADMIN_EMAIL=you@example.com
CORS_ORIGINS=http://localhost:5173
```

For production Postgres, also set:

```env
DATABASE_URL=postgresql+psycopg2://rag:password@localhost:5432/rag_saas
```

Without `DATABASE_URL` the backend uses SQLite at `./data/app.db`
(created automatically on startup).

## 2. Backend

```bash
cd backend
python -m venv ../.venv
../.venv/bin/pip install --no-cache-dir -r requirements.txt
../.venv/bin/python run.py
```

Backend runs at http://localhost:8000, API docs at
http://localhost:8000/docs. Check health:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/plans
```

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173. For a production build:

```bash
npm run build
npm run preview
```

Set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env`
(or your deployed backend URL) before building for production.

## 4. First use

1. Open http://localhost:5173, click **Sign up**, create an account.
   A workspace and a Free subscription are created automatically.
2. If your email matches `SUPER_ADMIN_EMAIL`, you are super-admin
   (Admin page in the sidebar).
3. Go to **Agents**, create an agent (name, instructions, language,
   provider/model, temperature, greeting).
4. Open the agent's **Knowledge** page, upload a PDF/DOCX/TXT file
   or add a website URL.
5. Open **Playground** and ask a question about the document.
6. Go to **Integrations** to create an API key and copy the website
   widget snippet or the REST API example.

## 5. Tests

```bash
cd backend
python -m pytest tests/test_saas.py -v
python test_endpoints.py
cd ../frontend
npm run build
```

The SaaS tests use a temporary SQLite database and fake embeddings /
a patched LLM, so they pass with no real AI key. Live RAG needs a
valid key (see Requirements above).

## Troubleshooting

- `AI API Key is not configured` in chat: set `GEMINI_API_KEY` (or
  `OPENAI_API_KEY`) in `backend/.env` and restart the backend.
- `401 UNAUTHENTICATED` from Gemini: the key is not a valid Gemini
  API key. Create a new one at Google AI Studio and replace it.
- `Please provide a valid email address` on signup: use a real
  deliverable email address (`.local` addresses are rejected).
- `429` on chat: the workspace hit its monthly message limit for its
  plan. Upgrade the plan or wait for the next month.
- `404` when opening another workspace's agent: this is tenant
  isolation working as designed.
- Frontend shows "Offline": the backend is not running on the URL in
  `VITE_API_BASE_URL`, or CORS does not allow the frontend origin.
