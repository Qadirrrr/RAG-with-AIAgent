import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == settings.PROJECT_NAME
    print("✓ Root endpoint works:", data)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✓ Health endpoint works:", data)

def test_stats():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_questions_asked" in data
    print("✓ Stats endpoint works:", data)

def test_documents_list():
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print("✓ Documents list endpoint works. Current count:", len(data))

def test_chat_without_api_key():
    response = client.post("/api/chat", json={"message": "What is company policy?"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    print("✓ Chat endpoint works and handles key status gracefully:", data["response"][:80])

if __name__ == "__main__":
    print("Running API endpoint tests...")
    test_root()
    test_health()
    test_stats()
    test_documents_list()
    test_chat_without_api_key()
    print("\nAll API endpoint unit checks PASSED successfully!")

