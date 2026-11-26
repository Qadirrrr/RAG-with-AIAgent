"""Minimal Python client for the public chat API.

Before running, set two environment variables:
  RAG_API_URL   Base URL of the platform, for example http://localhost:8000
  RAG_API_KEY   An API key from the Integrations page (it selects the chatbot)

Run:  python examples/python_client.py
"""
import os

import requests

API_URL = os.environ.get("RAG_API_URL", "http://localhost:8000") + "/api/public/chat"
API_KEY = os.environ["RAG_API_KEY"]
HEADERS = {"X-Agent-Key": API_KEY, "Content-Type": "application/json"}


def ask(message, conversation_id=None):
    body = {"message": message}
    if conversation_id:  # pass this to continue the same conversation
        body["conversation_id"] = conversation_id
    resp = requests.post(API_URL, headers=HEADERS, json=body, timeout=120)
    resp.raise_for_status()
    return resp.json()


first = ask("What are your opening hours?")
print(first["response"])

follow_up = ask("And on Sundays?", conversation_id=first["conversation_id"])
print(follow_up["response"])
