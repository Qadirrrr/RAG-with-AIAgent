"""SaaS backend tests (FastAPI TestClient, temp SQLite DB, no real AI key).

Run from the backend/ directory:
    python -m pytest tests/test_saas.py -v
Embeddings are faked so document upload works offline; the LLM is
patched to None so chat returns the graceful no-key message, not a 500.
"""
import os
import sys
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.gettempdir(), "test_saas_%s.db" % os.getpid())
os.environ["JWT_SECRET"] = "test-secret-for-pytest-only"
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["SUPER_ADMIN_EMAIL"] = "admin@example.com"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.rag_agent import rag_agent_service
from app.services.tenant_vector_store import tenant_vector_store


class FakeEmbeddings:
    def embed_documents(self, texts):
        return [[0.1] * 8 for _ in texts]

    def embed_query(self, text):
        return [0.1] * 8


@pytest.fixture(scope="module")
def client():
    # Tables were already created at import (main.py calls init_db()).
    # Drop and recreate here instead of deleting the DB file, because
    # the engine already holds pooled connections to it.
    from app.db import Base, engine, init_db
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    init_db()
    tenant_vector_store.get_embeddings = lambda: FakeEmbeddings()
    rag_agent_service._get_llm = lambda **kwargs: None
    with TestClient(app) as c:
        yield c


def _signup(client, email, password="password123"):
    r = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(client, email, password="password123"):
    r = client.post("/api/auth/signup", json={"email": email, "password": password})
    if r.status_code == 400:
        # Already signed up in an earlier test in this module run.
        r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    return data["access_token"], data["user"]


def test_signup_login_and_me(client):
    token, user = _auth(client, "alice@example.com")
    assert user["email"] == "alice@example.com"
    r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"] == "alice@example.com"
    assert len(r.json()["workspaces"]) >= 1


def test_super_admin_email(client):
    _, user = _auth(client, "admin@example.com")
    assert user["is_super_admin"] is True


def test_workspace_agent_upload_chat_flow(client):
    token, _ = _auth(client, "bob@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]

    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Support Bot", "instructions": "Be helpful.", "language": "en",
        "provider": "gemini", "model": "gemini-3.5-flash-lite", "temperature": 0.2})
    assert r.status_code == 200, r.text
    agent = r.json()
    assert agent["name"] == "Support Bot"

    # Invalid provider/model combo is rejected.
    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Bad Bot", "provider": "gemini", "model": "gpt-4o"})
    assert r.status_code == 400, r.text

    # Upload a TXT knowledge file.
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/documents", headers=h,
                    files={"file": ("notes.txt", b"CloudNest offers VPS hosting with fast SSD storage.", "text/plain")})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "processed"
    assert r.json()["chunks_count"] >= 1

    # Playground chat without a real AI key: graceful message, not a 500.
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/chat", headers=h,
                    json={"message": "What does CloudNest offer?"})
    assert r.status_code == 200, r.text
    assert "response" in r.json()
    assert "not configured" in r.json()["response"]

    # Analytics works.
    r = client.get(f"/api/workspaces/{ws_id}/analytics", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["documents_count"] == 1

    # Plans list works.
    r = client.get("/api/plans")
    assert r.status_code == 200, r.text
    assert any(p["id"] == "free" for p in r.json())


def test_public_chat_without_key_returns_401(client):
    token, _ = _auth(client, "carol@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    agent = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={"name": "Bot"}).json()
    r = client.post("/api/public/chat", json={"agent_id": agent["id"], "message": "Hello"})
    assert r.status_code == 401, r.text


def test_public_chat_with_api_key(client):
    token, _ = _auth(client, "dave@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    agent = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={"name": "Bot"}).json()
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/api-keys", headers=h, json={"name": "Website"})
    assert r.status_code == 200, r.text
    raw_key = r.json()["api_key"]
    assert raw_key.startswith("sk-live-")
    # Key list must not leak the full key.
    r = client.get(f"/api/workspaces/{ws_id}/agents/{agent['id']}/api-keys", headers=h)
    assert r.status_code == 200
    assert "api_key" not in r.json()[0]
    # Public chat with the key works (graceful no-LLM message).
    r = client.post("/api/public/chat", headers={"X-Agent-Key": raw_key},
                    json={"agent_id": agent["id"], "message": "Hello"})
    assert r.status_code == 200, r.text
    assert "response" in r.json()


def test_cross_workspace_access_is_blocked(client):
    token_a, _ = _auth(client, "eve@example.com")
    token_b, _ = _auth(client, "frank@example.com")
    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}
    ws_a = client.get("/api/auth/me", headers=ha).json()["workspaces"][0]["id"]
    agent_a = client.post(f"/api/workspaces/{ws_a}/agents", headers=ha, json={"name": "Private Bot"}).json()
    # Second user cannot read the first user's workspace or agent.
    r = client.get(f"/api/workspaces/{ws_a}", headers=hb)
    assert r.status_code in (403, 404), r.text
    r = client.get(f"/api/workspaces/{ws_a}/agents/{agent_a['id']}", headers=hb)
    assert r.status_code in (403, 404), r.text
    r = client.get(f"/api/workspaces/{ws_a}/analytics", headers=hb)
    assert r.status_code in (403, 404), r.text


def test_admin_endpoints_require_super_admin(client):
    token, _ = _auth(client, "grace@example.com")
    r = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403, r.text
    admin_token, _ = _auth(client, "admin@example.com")
    r = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, r.text
    assert "totals" in r.json()


def test_cross_project_agent_access_returns_404(client):
    """Chatbot A created in project 1 must not be readable or chattable under project 2."""
    token, _ = _auth(client, "ivan@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws1 = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    r = client.post("/api/workspaces", headers=h, json={"name": "Project Two"})
    assert r.status_code == 200, r.text
    ws2 = r.json()["id"]

    agent = client.post(f"/api/workspaces/{ws1}/agents", headers=h, json={"name": "Project One Bot"}).json()

    r = client.get(f"/api/workspaces/{ws2}/agents/{agent['id']}", headers=h)
    assert r.status_code == 404, r.text
    r = client.post(f"/api/workspaces/{ws2}/agents/{agent['id']}/chat", headers=h, json={"message": "Hi"})
    assert r.status_code == 404, r.text
    r = client.get(f"/api/workspaces/{ws2}/agents/{agent['id']}/documents", headers=h)
    assert r.status_code == 404, r.text


def test_deactivated_chatbot_public_chat_returns_403(client):
    token, _ = _auth(client, "judy@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    agent = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={"name": "Toggle Bot"}).json()
    assert agent["is_active"] is True
    raw_key = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/api-keys",
                          headers=h, json={"name": "Website"}).json()["api_key"]

    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/toggle-active", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is False

    r = client.post("/api/public/chat", headers={"X-Agent-Key": raw_key},
                    json={"agent_id": agent["id"], "message": "Hello"})
    assert r.status_code == 403, r.text
    assert "deactivated" in r.json()["detail"]

    # Playground chat is refused too.
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/chat", headers=h,
                    json={"message": "Hello"})
    assert r.status_code == 403, r.text


def test_csv_upload_is_ingested(client):
    token, _ = _auth(client, "karl@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    agent = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={"name": "CSV Bot"}).json()
    csv_bytes = b"plan,price\nStarter,19\nPro,49\n"
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/documents", headers=h,
                    files={"file": ("plans.csv", csv_bytes, "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "processed"
    assert r.json()["chunks_count"] >= 1


def test_ollama_agent_creation_without_cloud_key(client):
    token, _ = _auth(client, "lena@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Local Bot", "provider": "ollama", "model": "qwen2.5:7b",
        "description": "Self-hosted bot", "mode": "agent", "show_citations": True})
    assert r.status_code == 200, r.text
    agent = r.json()
    assert agent["provider"] == "ollama"
    assert agent["description"] == "Self-hosted bot"
    assert agent["mode"] == "agent"
    assert agent["show_citations"] is True

    # Any qwen tag is accepted for ollama.
    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Local Bot 2", "provider": "ollama", "model": "qwen2.5:1.5b"})
    assert r.status_code in (200, 403), r.text  # 403 only if the plan agent limit is hit

    # Chat fails gracefully (LLM patched to None in this fixture), never a 500.
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/chat", headers=h,
                    json={"message": "Hello"})
    assert r.status_code == 200, r.text
    assert "Ollama" in r.json()["response"]


def test_new_workspace_stats_are_zero_and_isolated(client):
    """A fresh workspace must show only its own data: zeros, no other workspace's docs."""
    token, _ = _auth(client, "heidi@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]

    r = client.get(f"/api/workspaces/{ws_id}/stats", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["total_documents"] == 0
    assert r.json()["total_questions_asked"] == 0
    assert r.json()["total_chunks"] == 0
    assert r.json()["recent_activity"] == []

    r = client.get(f"/api/workspaces/{ws_id}/documents", headers=h)
    assert r.status_code == 200, r.text
    assert r.json() == []

    # Chat responses must not expose sources.
    agent = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={"name": "Bot"}).json()
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/chat", headers=h,
                    json={"message": "Hello"})
    assert r.status_code == 200, r.text
    assert r.json().get("sources") == []
