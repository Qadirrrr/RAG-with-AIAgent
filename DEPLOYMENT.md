# Deployment

## Option A: Docker Compose (recommended)

```bash
cp backend/.env.example backend/.env   # fill in real keys + JWT_SECRET
# Edit docker-compose.yml if you want different ports/passwords
docker compose up --build -d
```

Services:

- `db` — PostgreSQL 16, database `rag_saas`, data in the `pgdata` volume.
  `DATABASE_URL` is set for the backend automatically.
- `backend` — FastAPI on http://localhost:8000 (docs at `/docs`).
- `frontend` — Nginx serving the production build on
  http://localhost:3000, proxying `/api` to the backend.

Check status:

```bash
docker compose ps
docker compose logs -f backend
curl http://localhost:8000/api/health
```

Stop: `docker compose down` (add `-v` to also delete the Postgres data).

## Option B: Manual server (Ubuntu VPS)

1. Install Python 3.12, Node 20, PostgreSQL 16 and Nginx.
2. Create the database and user:

```sql
CREATE DATABASE rag_saas;
CREATE USER rag WITH PASSWORD 'change-me';
GRANT ALL PRIVILEGES ON DATABASE rag_saas TO rag;
```

3. Clone the repo, configure `backend/.env` with
   `DATABASE_URL=postgresql+psycopg2://rag:change-me@localhost:5432/rag_saas`,
   a real `GEMINI_API_KEY`/`OPENAI_API_KEY`, a long `JWT_SECRET`, and
   `CORS_ORIGINS=https://your-domain.com`.
4. Backend as a systemd service (run from the repo `backend/` directory,
   with a venv):

```ini
[Unit]
Description=RAG SaaS backend
After=network.target postgresql.service

[Service]
User=www-data
WorkingDirectory=/opt/RAG-with-AIAgent/backend
ExecStart=/opt/RAG-with-AIAgent/.venv/bin/python run.py
Restart=always
EnvironmentFile=/opt/RAG-with-AIAgent/backend/.env

[Install]
WantedBy=multi-user.target
```

5. Frontend: `cd frontend && npm install && npm run build`, then serve
   `frontend/dist/` with Nginx and proxy `/api/` to `127.0.0.1:8000`.
   Set `VITE_API_BASE_URL` to your backend URL before building.
6. Put Nginx in front with HTTPS (Certbot) and set
   `CORS_ORIGINS` to the exact frontend origin.

## Production checklist

- [ ] Real `GEMINI_API_KEY` or `OPENAI_API_KEY` (tested with a live chat)
- [ ] Long random `JWT_SECRET`, different from dev
- [ ] `DATABASE_URL` points at Postgres, with backups enabled
- [ ] `CORS_ORIGINS` is your frontend origin only, not `*`
- [ ] `SUPER_ADMIN_EMAIL` set to your admin email
- [ ] No `.env` file committed to git; rotate any key that was ever committed
- [ ] Stripe checkout wired into `backend/app/routes/plans.py`
      (currently a manual/admin upgrade path, see README)
- [ ] Uploads and Chroma data on a persistent volume, with backups
- [ ] Logs and monitoring on the backend service
