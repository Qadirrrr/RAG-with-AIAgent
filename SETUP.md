# Setup and Installation

## Requirements

- Python 3.11+ (3.12 tested)
- Node.js 18+ and npm
- PostgreSQL 15+ (optional for local dev; SQLite is the default)
- Ollama installed on the same machine (or another server you point
  `OLLAMA_BASE_URL` at). No cloud AI API keys are used anywhere.
  Install Ollama from https://ollama.com, then pull the models:

```bash
ollama pull qwen2.5:7b
ollama pull bge-m3
```

  `qwen2.5:7b` needs about 8 GB of RAM and runs on CPU when there is
  no GPU, so answers are slower than a cloud model. On a smaller
  machine, set `OLLAMA_MODEL=qwen2.5:3b` in `backend/.env` and pull
  that model instead.

## 1. Clone and configure

```bash
git clone https://github.com/Qadirrrr/RAG-with-AIAgent.git
cd RAG-with-AIAgent
cp backend/.env.example backend/.env
cp .env.example .env        # optional, root copy
```

Edit `backend/.env` and set at least:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
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

Optional but recommended on the server: install the headless browser
used to read JavaScript-built websites (React/Vue single-page apps)
when adding knowledge from a URL. Static websites work without it.
Run once, as the same user that runs the backend service (root in the
systemd deployment):

```bash
../.venv/bin/pip install playwright
../.venv/bin/playwright install --with-deps chromium
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
a patched LLM, so they pass without a running Ollama. Live RAG needs
Ollama running with the models pulled (see Requirements above).

## Troubleshooting

- `The self-hosted Ollama service is not available` in chat: Ollama
  is not running, or the chat model is not pulled. Start Ollama and
  run `ollama pull qwen2.5:7b`, then try again.
- `model 'qwen2.5:7b' not found` in chat: the model tag in the
  chatbot settings is not pulled on the Ollama server. Pull it with
  `ollama pull qwen2.5:7b` (check `ollama list` for what is installed).
- Document upload fails with an embeddings error: pull the embedding
  model with `ollama pull bge-m3` and make sure Ollama is running.
- Adding a website URL says no readable text was found: the page is
  probably built with JavaScript. Install the headless browser (see
  section 2) so the backend can render such pages, then try again.
- `Please provide a valid email address` on signup: use a real
  deliverable email address (`.local` addresses are rejected).
- `429` on chat: the workspace hit its monthly message limit for its
  plan. Upgrade the plan or wait for the next month.
- `404` when opening another workspace's agent: this is tenant
  isolation working as designed.
- Frontend shows "Offline": the backend is not running on the URL in
  `VITE_API_BASE_URL`, or CORS does not allow the frontend origin.
