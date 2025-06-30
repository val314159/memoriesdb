#!/usr/bin/env python3
"""
Simple LLM chatbot using Ollama (llama3.1) with tool calling, loading full chat session from DB and appending new messages.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
USER_ID = os.getenv("CHAT_USER_ID", "user_001")


def get_session_history(session_id):
    r = requests.get(f"{API_URL}/sessions/{session_id}/history")
    r.raise_for_status()
    return r.json()

def add_user_message(session_id, content):
    r = requests.post(f"{API_URL}/sessions/{session_id}/messages/", json={"role": "user", "content": content})
    r.raise_for_status()
    return r.json()["id"]

def add_assistant_message(session_id, content):
    r = requests.post(f"{API_URL}/sessions/{session_id}/messages/", json={"role": "assistant", "content": content})
    r.raise_for_status()
    return r.json()["id"]

def call_ollama(messages):
    # Format messages for Ollama API
    formatted = [{"role": m["role"], "content": m["content"]} for m in messages]
    r = requests.post(f"{OLLAMA_URL}/api/chat", json={"model": OLLAMA_MODEL, "messages": formatted})
    r.raise_for_status()
    return r.json()["message"]["content"]

def main():
    session_id = input("Session ID (existing or new): ").strip()
    if not session_id:
        print("Session ID required.")
        return
    while True:
        history = get_session_history(session_id)
        print("\n--- Conversation so far ---")
        for m in history:
            print(f"{m['role']}: {m['content']}")
        user_input = input("You: ").strip()
        if not user_input:
            break
        add_user_message(session_id, user_input)
        # Reload history to include user message
        history = get_session_history(session_id)
        # Tool calling: (simple demo, add your own logic here)
        if user_input.lower().startswith("/tool "):
            tool_result = f"[Tool called with: {user_input[6:]}]"
            print(f"assistant: {tool_result}")
            add_assistant_message(session_id, tool_result)
            continue
        # LLM response
        assistant_reply = call_ollama(history)
        print(f"assistant: {assistant_reply}")
        add_assistant_message(session_id, assistant_reply)

if __name__ == "__main__":
    main()
