# Deployment

Manual server deployment (Ubuntu VPS). No Docker is used in this project.

## Server requirements

| Requirement | Minimum | Recommended |
| --- | --- | --- |
| Server | Ubuntu 22.04 / 24.04 VPS | Linode g6-standard-1 or similar |
| CPU / RAM / Disk | 2 vCPU, 8 GB RAM, 40 GB disk (for qwen2.5:7b) | 4 vCPU, 16 GB RAM, 80 GB disk |
| Python | 3.12 | 3.12 |
| Node.js | 20 | 20 LTS |
| PostgreSQL | 16 | 16 with backups |
| Web server | Nginx | Nginx + Certbot HTTPS |
| Domain | A domain pointing at the server | `app.yourdomain.com` |
| Ports | 80 and 443 open | 8000 and 5432 localhost only |
| AI runtime | Ollama installed on the server, models `qwen2.5:7b` and `bge-m3` pulled | Same, Ollama kept updated |
| Secrets | Long random `JWT_SECRET`, `SUPER_ADMIN_EMAIL` (no AI API keys exist) | Same, stored only in `backend/.env` |

Notes: the AI is fully self-hosted through Ollama, there are no cloud
AI keys to configure. Without Ollama running, signup and agents work
but chat returns a clear "self-hosted Ollama service is not available"
message. Stripe checkout is a TODO stub; plan changes are manual/admin
upgrades for now.

1. Install Python 3.12, Node 20, PostgreSQL 16, Nginx and Ollama, then
   pull the models: `ollama pull qwen2.5:7b` and `ollama pull bge-m3`.
2. Create the database and user:

```sql
CREATE DATABASE rag_saas;
CREATE USER rag WITH PASSWORD 'change-me';
GRANT ALL PRIVILEGES ON DATABASE rag_saas TO rag;
```

3. Clone the repo, configure `backend/.env` with
   `DATABASE_URL=postgresql+psycopg2://rag:change-me@localhost:5432/rag_saas`,
   `OLLAMA_BASE_URL=http://localhost:11434`, a long `JWT_SECRET`, and
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

Check health after deployment:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/plans
```

## Production checklist

- [ ] Ollama running, `qwen2.5:7b` and `bge-m3` pulled (tested with a live chat)
- [ ] Long random `JWT_SECRET`, different from dev
- [ ] `DATABASE_URL` points at Postgres, with backups enabled
- [ ] `CORS_ORIGINS` is your frontend origin only, not `*`
- [ ] `SUPER_ADMIN_EMAIL` set to your admin email
- [ ] No `.env` file committed to git
- [ ] Stripe checkout wired into `backend/app/routes/plans.py`
      (currently a manual/admin upgrade path, see README)
- [ ] Uploads and Chroma data on a persistent volume, with backups
- [ ] Logs and monitoring on the backend service
