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
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
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
        "provider": "ollama", "model": "qwen2.5:7b", "temperature": 0.2})
    assert r.status_code == 200, r.text
    agent = r.json()
    assert agent["name"] == "Support Bot"

    # Invalid model for the ollama provider is rejected.
    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Bad Bot", "provider": "ollama", "model": "gpt-4o"})
    assert r.status_code == 400, r.text

    # Upload a TXT knowledge file.
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/documents", headers=h,
                    files={"file": ("notes.txt", b"CloudNest offers VPS hosting with fast SSD storage.", "text/plain")})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "processed"
    assert r.json()["chunks_count"] >= 1

    # Playground chat with the LLM unavailable: graceful message, not a 500.
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/chat", headers=h,
                    json={"message": "What does CloudNest offer?"})
    assert r.status_code == 200, r.text
    assert "response" in r.json()
    assert "not available" in r.json()["response"]

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


def test_cloud_provider_is_rejected(client):
    """Cloud providers are removed: only self-hosted ollama is accepted."""
    token, _ = _auth(client, "olga@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Cloud Bot", "provider": "gemini", "model": "gemini-3.5-flash-lite"})
    assert r.status_code == 400, r.text
    assert "ollama" in r.json()["detail"]


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


def test_agent_calculator_is_safe():
    from app.services.agent_engine import calculate_expression
    assert calculate_expression("2*(3+4)") == "14"
    assert calculate_expression("19 * 12") == "228"
    assert calculate_expression("10 / 4") == "2.5"
    # Code execution attempts are rejected, never evaluated.
    assert calculate_expression("__import__('os')").startswith("Error")
    assert calculate_expression("open('x')").startswith("Error")
    assert calculate_expression("x + 1").startswith("Error")


def test_agent_tools_allowlist_filtering():
    from app.services.agent_engine import build_tools, parse_tools_enabled
    tools, _ = build_tools(workspace_id="ws-1", agent_id="agent-1",
                           tools_enabled="calculator,current_datetime")
    assert sorted(t.name for t in tools) == ["calculator", "current_datetime"]
    # Unknown names are dropped, duplicates removed, order kept.
    assert parse_tools_enabled("calculator,bogus,calculator, knowledge_search ") == [
        "calculator", "knowledge_search"]
    assert parse_tools_enabled("") == []
    tools, _ = build_tools(workspace_id="ws-1", agent_id="agent-1", tools_enabled="")
    assert tools == []


def test_agent_knowledge_search_tool_is_bound_to_own_agent(client):
    from app.services.agent_engine import build_tools
    from app.services.tenant_vector_store import tenant_vector_store as tvs

    calls = {}

    class FakeDoc:
        page_content = "Bound knowledge chunk."
        metadata = {"document_name": "notes.txt", "document_id": "doc-1"}

    original = tvs.similarity_search
    tvs.similarity_search = lambda agent_id, query, k=4: calls.update(
        {"agent_id": agent_id, "query": query}) or [FakeDoc()]
    try:
        tools, _ = build_tools(workspace_id="ws-9", agent_id="agent-xyz",
                               tools_enabled="knowledge_search")
        assert [t.name for t in tools] == ["knowledge_search"]
        out = tools[0].invoke({"query": "pricing"})
    finally:
        tvs.similarity_search = original
    # The tool searched ONLY the agent id it was built for.
    assert calls == {"agent_id": "agent-xyz", "query": "pricing"}
    assert "Bound knowledge chunk." in out


def test_agent_tools_enabled_via_api(client):
    token, _ = _auth(client, "mona@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Tool Bot", "mode": "agent", "tools_enabled": "calculator,knowledge_search"})
    assert r.status_code == 200, r.text
    assert r.json()["tools_enabled"] == "calculator,knowledge_search"
    # Unknown tool names are rejected.
    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Bad Tool Bot", "mode": "agent", "tools_enabled": "calculator,shell"})
    assert r.status_code == 400, r.text
    # Update narrows the allowlist.
    r = client.get(f"/api/workspaces/{ws_id}/agents", headers=h)
    bot = [a for a in r.json() if a["name"] == "Tool Bot"][0]
    r = client.patch(f"/api/workspaces/{ws_id}/agents/{bot['id']}", headers=h,
                     json={"tools_enabled": "calculator"})
    assert r.status_code == 200, r.text
    assert r.json()["tools_enabled"] == "calculator"


def test_agent_mode_chat_without_llm_falls_back_gracefully(client):
    token, _ = _auth(client, "nina@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    agent = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Agent Mode Bot", "mode": "agent"}).json()
    assert agent["mode"] == "agent"
    # LLM is patched to None in the fixture: same graceful Ollama
    # unavailable message as the RAG path, never a 500.
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/chat", headers=h,
                    json={"message": "What is 2 + 2?"})
    assert r.status_code == 200, r.text
    assert "not available" in r.json()["response"]
    assert r.json().get("sources") == []


def test_delete_plain_chatbot(client):
    """Deleting a chatbot with no data succeeds and the chatbot is gone."""
    token, _ = _auth(client, "deleteplain@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    agent = client.post(f"/api/workspaces/{ws_id}/agents", headers=h,
                        json={"name": "Delete Me Bot"}).json()

    r = client.delete(f"/api/workspaces/{ws_id}/agents/{agent['id']}", headers=h)
    assert r.status_code == 200, r.text

    r = client.get(f"/api/workspaces/{ws_id}/agents/{agent['id']}", headers=h)
    assert r.status_code == 404, r.text
    r = client.get(f"/api/workspaces/{ws_id}/agents", headers=h)
    assert all(a["id"] != agent["id"] for a in r.json())


def test_delete_chatbot_with_data_keeps_sibling(client):
    """Regression: deleting a USED chatbot must not 500.

    Uploading and chatting create usage_events rows whose agent_id foreign
    key used to block the delete with an FK constraint violation on
    Postgres. The delete must clean up the chatbot's documents,
    conversations and usage events, and leave a sibling chatbot untouched.
    """
    from app.db import Conversation, Document, SessionLocal, Subscription, UsageEvent

    token, _ = _auth(client, "deletebusy@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]

    # The Free plan allows 1 agent; raise this workspace's limit in the DB
    # so the sibling chatbot can exist in the same workspace.
    db = SessionLocal()
    sub = db.query(Subscription).filter(Subscription.workspace_id == ws_id).first()
    sub.agent_limit = 5
    db.commit()
    db.close()

    busy = client.post(f"/api/workspaces/{ws_id}/agents", headers=h,
                       json={"name": "Busy Bot"}).json()
    sibling = client.post(f"/api/workspaces/{ws_id}/agents", headers=h,
                          json={"name": "Sibling Bot"}).json()

    # Give Busy Bot a document and a chat (both create usage events).
    r = client.post(f"/api/workspaces/{ws_id}/agents/{busy['id']}/documents", headers=h,
                    files={"file": ("notes.txt", b"Busy Bot knowledge.", "text/plain")})
    assert r.status_code == 200, r.text
    r = client.post(f"/api/workspaces/{ws_id}/agents/{busy['id']}/chat", headers=h,
                    json={"message": "Hello"})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    assert db.query(UsageEvent).filter(UsageEvent.agent_id == busy["id"]).count() >= 1
    assert db.query(Document).filter(Document.agent_id == busy["id"]).count() == 1
    db.close()

    r = client.delete(f"/api/workspaces/{ws_id}/agents/{busy['id']}", headers=h)
    assert r.status_code == 200, r.text

    r = client.get(f"/api/workspaces/{ws_id}/agents/{busy['id']}", headers=h)
    assert r.status_code == 404, r.text

    # All of Busy Bot's own rows are gone.
    db = SessionLocal()
    assert db.query(UsageEvent).filter(UsageEvent.agent_id == busy["id"]).count() == 0
    assert db.query(Document).filter(Document.agent_id == busy["id"]).count() == 0
    assert db.query(Conversation).filter(Conversation.agent_id == busy["id"]).count() == 0
    db.close()

    # The sibling chatbot in the same workspace still works.
    r = client.get(f"/api/workspaces/{ws_id}/agents/{sibling['id']}", headers=h)
    assert r.status_code == 200, r.text
    r = client.post(f"/api/workspaces/{ws_id}/agents/{sibling['id']}/chat", headers=h,
                    json={"message": "Hello"})
    assert r.status_code == 200, r.text


def test_widget_settings_round_trip_and_validation(client):
    """Widget appearance fields save on create/update and are validated."""
    token, _ = _auth(client, "widgetform@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]

    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Widget Bot",
        "widget_title": "Ask CloudNest",
        "widget_welcome_message": "Hi there! Ask me about our VPS plans.",
        "widget_color": "#2563EB",
        "widget_position": "left",
        "widget_icon": "custom",
        "widget_icon_url": "https://example.com/logo.png"})
    assert r.status_code == 200, r.text
    agent = r.json()
    assert agent["widget_title"] == "Ask CloudNest"
    assert agent["widget_welcome_message"] == "Hi there! Ask me about our VPS plans."
    assert agent["widget_color"] == "#2563EB"
    assert agent["widget_position"] == "left"
    assert agent["widget_icon"] == "custom"
    assert agent["widget_icon_url"] == "https://example.com/logo.png"

    # Update changes only the widget fields sent.
    r = client.patch(f"/api/workspaces/{ws_id}/agents/{agent['id']}", headers=h, json={
        "widget_color": "#0F766E", "widget_position": "right", "widget_icon": "robot"})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["widget_color"] == "#0F766E"
    assert updated["widget_position"] == "right"
    assert updated["widget_icon"] == "robot"
    assert updated["widget_title"] == "Ask CloudNest"

    # Invalid values are rejected on create and update.
    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Bad Color Bot", "widget_color": "teal"})
    assert r.status_code == 400, r.text
    r = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Bad Position Bot", "widget_position": "top"})
    assert r.status_code == 400, r.text
    r = client.patch(f"/api/workspaces/{ws_id}/agents/{agent['id']}", headers=h,
                     json={"widget_color": "#12345"})
    assert r.status_code == 400, r.text
    r = client.patch(f"/api/workspaces/{ws_id}/agents/{agent['id']}", headers=h,
                     json={"widget_icon": "smiley"})
    assert r.status_code == 400, r.text


def test_widget_config_endpoint(client):
    """GET /api/public/widget-config: key auth, saved values, deactivated 403."""
    token, _ = _auth(client, "widgetconfig@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    agent = client.post(f"/api/workspaces/{ws_id}/agents", headers=h, json={
        "name": "Config Bot",
        "widget_welcome_message": "Welcome to our store!",
        "widget_color": "#B45309",
        "widget_position": "left",
        "widget_icon": "robot"}).json()
    raw_key = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/api-keys",
                          headers=h, json={"name": "Website"}).json()["api_key"]

    # No key: 401. Wrong key: 401.
    r = client.get("/api/public/widget-config")
    assert r.status_code == 401, r.text
    r = client.get("/api/public/widget-config", headers={"X-Agent-Key": "sk-live-nope"})
    assert r.status_code == 401, r.text

    # Valid key: saved values come back; empty widget_title falls back to
    # the chatbot name, and no internals leak.
    r = client.get("/api/public/widget-config", headers={"X-Agent-Key": raw_key})
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert cfg["title"] == "Config Bot"
    assert cfg["agent_name"] == "Config Bot"
    assert cfg["welcome_message"] == "Welcome to our store!"
    assert cfg["color"] == "#B45309"
    assert cfg["position"] == "left"
    assert cfg["icon"] == "robot"
    assert cfg["icon_url"] == ""
    assert "instructions" not in cfg
    assert "documents" not in cfg

    # A custom widget_title wins over the chatbot name.
    r = client.patch(f"/api/workspaces/{ws_id}/agents/{agent['id']}", headers=h,
                     json={"widget_title": "Store Help"})
    assert r.status_code == 200, r.text
    r = client.get("/api/public/widget-config", headers={"X-Agent-Key": raw_key})
    assert r.json()["title"] == "Store Help"

    # Deactivated chatbot: 403, same as public chat.
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent['id']}/toggle-active", headers=h)
    assert r.json()["is_active"] is False
    r = client.get("/api/public/widget-config", headers={"X-Agent-Key": raw_key})
    assert r.status_code == 403, r.text


def test_delete_chatbot_in_other_workspace_returns_404(client):
    """Deleting under the wrong workspace id is a 404 and deletes nothing."""
    token, _ = _auth(client, "deletecross@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws1 = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    r = client.post("/api/workspaces", headers=h, json={"name": "Second Project"})
    assert r.status_code == 200, r.text
    ws2 = r.json()["id"]

    agent = client.post(f"/api/workspaces/{ws1}/agents", headers=h,
                        json={"name": "Project One Bot"}).json()

    r = client.delete(f"/api/workspaces/{ws2}/agents/{agent['id']}", headers=h)
    assert r.status_code == 404, r.text

    r = client.get(f"/api/workspaces/{ws1}/agents/{agent['id']}", headers=h)
    assert r.status_code == 200, r.text


def _chat_conversation_id(client, h, ws_id, agent_id, message="Hello"):
    r = client.post(f"/api/workspaces/{ws_id}/agents/{agent_id}/chat", headers=h,
                    json={"message": message})
    assert r.status_code == 200, r.text
    conv_id = r.json()["conversation_id"]
    assert conv_id
    return conv_id


def test_delete_conversation_removes_it_and_its_messages(client):
    """Deleting a conversation returns 200, removes its messages, and
    leaves the chatbot itself untouched."""
    from app.db import Conversation, Message, SessionLocal

    token, _ = _auth(client, "convdelete@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    agent = client.post(f"/api/workspaces/{ws_id}/agents", headers=h,
                        json={"name": "Chatty Bot"}).json()

    conv_id = _chat_conversation_id(client, h, ws_id, agent["id"])

    r = client.get(f"/api/workspaces/{ws_id}/conversations/{conv_id}", headers=h)
    assert r.status_code == 200, r.text
    assert len(r.json()["messages"]) >= 1

    r = client.delete(f"/api/workspaces/{ws_id}/conversations/{conv_id}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["id"] == conv_id

    r = client.get(f"/api/workspaces/{ws_id}/conversations/{conv_id}", headers=h)
    assert r.status_code == 404, r.text

    db = SessionLocal()
    assert db.query(Conversation).filter(Conversation.id == conv_id).count() == 0
    assert db.query(Message).filter(Message.conversation_id == conv_id).count() == 0
    db.close()

    # The chatbot itself still exists and still chats.
    r = client.get(f"/api/workspaces/{ws_id}/agents/{agent['id']}", headers=h)
    assert r.status_code == 200, r.text


def test_delete_conversation_in_other_workspace_returns_404(client):
    """Deleting under the wrong workspace id is a 404 and deletes nothing."""
    token, _ = _auth(client, "convcross@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws1 = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    r = client.post("/api/workspaces", headers=h, json={"name": "Second Project"})
    assert r.status_code == 200, r.text
    ws2 = r.json()["id"]

    agent = client.post(f"/api/workspaces/{ws1}/agents", headers=h,
                        json={"name": "Project One Bot"}).json()
    conv_id = _chat_conversation_id(client, h, ws1, agent["id"])

    r = client.delete(f"/api/workspaces/{ws2}/conversations/{conv_id}", headers=h)
    assert r.status_code == 404, r.text

    r = client.get(f"/api/workspaces/{ws1}/conversations/{conv_id}", headers=h)
    assert r.status_code == 200, r.text
    assert len(r.json()["messages"]) >= 1


def test_delete_one_conversation_keeps_the_other(client):
    """Deleting one conversation of a chatbot keeps its other conversations."""
    token, _ = _auth(client, "convkeep@example.com")
    h = {"Authorization": f"Bearer {token}"}
    ws_id = client.get("/api/auth/me", headers=h).json()["workspaces"][0]["id"]
    agent = client.post(f"/api/workspaces/{ws_id}/agents", headers=h,
                        json={"name": "Two Chats Bot"}).json()

    first = _chat_conversation_id(client, h, ws_id, agent["id"], "First chat")
    second = _chat_conversation_id(client, h, ws_id, agent["id"], "Second chat")
    assert first != second

    r = client.delete(f"/api/workspaces/{ws_id}/conversations/{first}", headers=h)
    assert r.status_code == 200, r.text

    r = client.get(f"/api/workspaces/{ws_id}/conversations/{first}", headers=h)
    assert r.status_code == 404, r.text

    r = client.get(f"/api/workspaces/{ws_id}/conversations/{second}", headers=h)
    assert r.status_code == 200, r.text
    assert len(r.json()["messages"]) >= 1

    r = client.get(f"/api/workspaces/{ws_id}/conversations", headers=h)
    assert r.status_code == 200, r.text
    assert [c["id"] for c in r.json()] == [second]


# ---------------------------------------------------------------------------
# Pulled-model fallback: a chatbot stored with a model that is not pulled
# on the Ollama server must chat with the default model instead of 404ing.
# ---------------------------------------------------------------------------

def test_resolve_chat_model_falls_back_when_stored_model_not_pulled(monkeypatch):
    import app.services.rag_agent as rag
    monkeypatch.setattr(rag, "_get_pulled_model_names",
                        lambda: {"qwen2.5:7b", "qwen2.5:3b", "bge-m3:latest"})
    # qwen2.5:14b is a valid tag but not pulled: fall back to the default.
    assert rag.resolve_chat_model("qwen2.5:14b") == "qwen2.5:7b"


def test_resolve_chat_model_keeps_pulled_model(monkeypatch):
    import app.services.rag_agent as rag
    monkeypatch.setattr(rag, "_get_pulled_model_names",
                        lambda: {"qwen2.5:7b", "qwen2.5:3b", "bge-m3:latest"})
    assert rag.resolve_chat_model("qwen2.5:3b") == "qwen2.5:3b"
    assert rag.resolve_chat_model("qwen2.5:7b") == "qwen2.5:7b"


def test_resolve_chat_model_unchanged_when_tags_fetch_fails(monkeypatch):
    import app.services.rag_agent as rag
    monkeypatch.setattr(rag, "_get_pulled_model_names", lambda: None)
    # Ollama unreachable: today's behaviour, stored model returned as is
    # and the normal unavailable/error handling takes over downstream.
    assert rag.resolve_chat_model("qwen2.5:14b") == "qwen2.5:14b"
    assert rag.resolve_chat_model("qwen2.5:3b") == "qwen2.5:3b"


def test_get_llm_builds_fallback_model(monkeypatch):
    import types

    import app.services.rag_agent as rag

    captured = {}

    class FakeChatOllama:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_module = types.ModuleType("langchain_ollama")
    fake_module.ChatOllama = FakeChatOllama
    monkeypatch.setitem(sys.modules, "langchain_ollama", fake_module)
    monkeypatch.setattr(rag, "_get_pulled_model_names", lambda: {"qwen2.5:7b"})

    llm = rag.RAGAgentService()._get_llm(model="qwen2.5:14b")
    assert llm is not None
    assert captured["model"] == "qwen2.5:7b"


# ---------------------------------------------------------------------------
# GET /api/ollama/models: dynamic model list for the chatbot form.
# ---------------------------------------------------------------------------

def test_ollama_models_endpoint_lists_pulled_chat_models(client, monkeypatch):
    import app.services.rag_agent as rag
    monkeypatch.setattr(rag, "_get_pulled_model_names",
                        lambda: {"qwen2.5:7b", "qwen2.5:3b", "bge-m3:latest"})
    token, _ = _auth(client, "models@example.com")
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/ollama/models", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    # The BGE embedding model is excluded; only chat models are listed.
    assert sorted(data["models"]) == ["qwen2.5:3b", "qwen2.5:7b"]
    assert data["default"] == "qwen2.5:7b"
    # The endpoint is authenticated.
    r = client.get("/api/ollama/models")
    assert r.status_code == 401, r.text


def test_ollama_models_endpoint_when_ollama_unreachable(client, monkeypatch):
    import app.services.rag_agent as rag
    monkeypatch.setattr(rag, "_get_pulled_model_names", lambda: None)
    token, _ = _auth(client, "modelsdown@example.com")
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/ollama/models", headers=h)
    assert r.status_code == 200, r.text
    assert r.json() == {"models": [], "default": "qwen2.5:7b"}
