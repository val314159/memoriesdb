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

def add_message(session_id, role, content):
    r = requests.post(f"{API_URL}/sessions/{session_id}/messages/", json={"role": role, "content": content})
    r.raise_for_status()
    return r.json()["id"]

def call_ollama(messages):
    # Format messages for Ollama API
    formatted = [{"role": m["role"], "content": m["content"]} for m in messages]
    r = requests.post(f"{OLLAMA_URL}/api/chat", json={"model": OLLAMA_MODEL, "messages": formatted})
    r.raise_for_status()
    return r.json()["message"]["content"]

def chat_loop(session_id, input_fn=input, output_fn=print):
    while True:
        history = get_session_history(session_id)
        output_fn("\n--- Conversation so far ---")
        for m in history:
            output_fn(f"{m['role']}: {m['content']}")
        user_input = input_fn("You: ").strip()
        if not user_input:
            break
        add_message(session_id, "user", user_input)
        history = get_session_history(session_id)
        if user_input.lower().startswith("/tool "):
            tool_result = f"[Tool called with: {user_input[6:]}]"
            output_fn(f"assistant: {tool_result}")
            add_message(session_id, "assistant", tool_result)
            continue
        assistant_reply = call_ollama(history)
        output_fn(f"assistant: {assistant_reply}")
        add_message(session_id, "assistant", assistant_reply)

def run_test_convo(session_id=None):
    """Run a scripted conversation and check LLM math ability."""
    import sys
    test_msgs = [
        "Hello!",
        "What is 2+2?",
        "/tool echo test",
        "What is 17*3?"
    ]
    outputs = []
    idx = 0
    def test_input(prompt):
        nonlocal idx
        if idx < len(test_msgs):
            msg = test_msgs[idx]
            idx += 1
            print(f"You: {msg}")
            return msg
        return ""
    def test_output(msg):
        print(msg)
        outputs.append(msg)
    sid = session_id or input("Session ID (existing or new): ").strip()
    if not sid:
        print("Session ID required.")
        return
    chat_loop(sid, input_fn=test_input, output_fn=test_output)
    # Check for math answers in outputs
    math_pass = any("4" in o for o in outputs if "2+2" in o) and any("51" in o for o in outputs if "17*3" in o)
    print("MATH TEST:", "PASS" if math_pass else "FAIL")

def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_test_convo()
    else:
        session_id = input("Session ID (existing or new): ").strip()
        if not session_id:
            print("Session ID required.")
            return
        chat_loop(session_id)

if __name__ == "__main__":
    main()

