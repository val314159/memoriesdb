#!/usr/bin/env python3
"""Memory-aware chat client for Ollama with tool support.

Usage:
  memory_chat.py [--model MODEL] [--no-stream] [--create]
  memory_chat.py (-h | --help | --version)

Options:
  --model MODEL    Ollama model to use [default: {default_model}].
  --no-stream      Disable streaming output (buffer full responses).
  --create         Start a new session instead of continuing the last one.
  -h --help        Show this screen.
  --version        Show version.

This script resumes the most recent session from the memories database (or
creates a new one with ``--create``), streams responses from Ollama, and
executes tools defined in ``funcs2`` when requested.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Iterable, List, Optional

import ollama
import docopt
import atexit
from pathlib import Path

import funcs2 as funcs
import db_sync
from db_ll_utils import set_current_user_id, get_current_user_id

from config import CHAT_MODEL

VERSION = "1.0.1"

TOOLS = getattr(funcs, "Tools", [])

USER_ID = os.getenv("USER_UUID")
if USER_ID:
    set_current_user_id(USER_ID)
USER_ID = get_current_user_id()


try:
    import readline  # type: ignore
except ImportError:  # pragma: no cover - platform without readline
    readline = None  # type: ignore
else:
    HISTORY_FILE = Path.home() / ".memory_chat_history"
    try:
        readline.read_history_file(HISTORY_FILE)
    except FileNotFoundError:
        pass
    readline.set_history_length(1000)

    def _save_history() -> None:
        try:
            readline.write_history_file(HISTORY_FILE)
        except FileNotFoundError:
            HISTORY_FILE.touch()
            readline.write_history_file(HISTORY_FILE)
            pass
        pass

    atexit.register(_save_history)
    pass


def call_tool(name: str, arguments: Dict[str, Any]) -> str:
    """
    Call a tool by name with the given arguments.
    """
    fn = getattr(funcs, name, None)
    if fn is None:
        return f"[tool-error] unknown tool '{name}'"
    try:
        return str(fn(**arguments))
    except Exception as exc:  # pragma: no cover - runtime diagnostic
        return f"[tool-error] {exc}"
    pass


def iter_chat(
    client: ollama.Client,
    history: List[Dict[str, Any]],
    model: str,
    stream: bool,
) -> Iterable[Dict[str, Any]]:
    """
    Iterate over the chunks of a chat response.
    """
    chat = client.chat(
        model=model,
        messages=history,
        tools=TOOLS if TOOLS else None,
        stream=stream,
    )
    # if not streaming, return the entire response as a single chunk
    return chat if stream else [ chat ]


def record_memory(
    *,
    session_id: str,
    role: str,
    content: str,
    kind: str = "history",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    meta = dict(metadata or {})
    meta.setdefault("role", role)
    meta.setdefault("source", "memory_chat")

    memory_id = db_sync.create_memory(
        content=content or "",
        user_id=USER_ID,
        kind=kind,
        metadata=meta,
    )
    db_sync.create_memory_edge(memory_id, session_id, "belongs_to")
    return memory_id


def delete_memory(memory_id: str) -> None:
    """
    Delete a memory by its ID.
    """
    db_sync.delete_memory(memory_id)


def perform_turn(
    client: ollama.Client,
    user_input: str,
    model_name: str,
    stream_mode: bool,
    *,
    session_id: str,
):

    prin = lambda s: print(s, end='', flush=True)

    assistant_fragments: List[str] = []
    pending_tool_calls: List[Dict[str, Any]] = []

    mem_id = record_memory(
        session_id=session_id,
        role="user",
        content=user_input,
    )

    while True:

        assistant_fragments.clear()
        pending_tool_calls.clear()

        history = db_sync.load_simplified_convo(session_id)

        history = list(history)

        print("HISTORY", list(history))

        try:
            chunks = iter_chat(client, history, model_name, stream_mode)
        except Exception as exc:
            print(f"[error] {exc}", file=sys.stderr)
            delete_memory(mem_id) # AVOID DECOHERENCE
            raise

        prin("asst> ")
        for chunk in chunks:
            message = chunk.get("message", {})
            content = message.get("content", "")
            if content:
                assistant_fragments.append(content)
                prin(content)
            tool_calls = message.get("tool_calls") or []
            for tool_call in tool_calls:
                if tool_call.get("function", {}).get("name") == "respond_to_user":
                    # append this as though it was a regular reponse
                    args = tool_call.get("function", {}).get("arguments", {})
                    synthetic_content = args.get("message", "")
                    assistant_fragments.append(synthetic_content)
                    prin(synthetic_content)
                    continue
                pending_tool_calls.append(tool_call)
                pass
            pass
        prin("\n")

        if assistant_fragments:
            record_memory(
                session_id=session_id,
                role="assistant",
                content="".join(assistant_fragments),
                metadata=dict(tool_calls=list(pending_tool_calls)),
            )

        if not pending_tool_calls:
            return

        for call in pending_tool_calls:
            fn = call.get("function", {})
            name = fn.get("name")
            arguments = fn.get("arguments") or {}
            result = call_tool(name, arguments)
            print(f"tool[{name}]> {result}")
            record_memory(
                session_id=session_id,
                role="tool",
                content=result,
                kind="tool",
                metadata=dict(tool_name=name, arguments=arguments),
            )
            pass
        pass

    return


def get_user_input(role: str = "user") -> str:
    while True:
        if ret:= input(f"{role}> ").strip():
            break
        pass
    return ret


def get_session_id(create_new: bool) -> str:
    if create_new:
        session_meta = {"source": "memory_chat"}
        return db_sync.create_memory(
            content="Memory chat session",
            user_id=USER_ID,
            kind="session",
            metadata=session_meta,
        )
    if last := db_sync.get_last_session(USER_ID):
        return str(last["id"])
    raise RuntimeError("No last session found for user")


def main(argv: List[str] | None = None) -> None:
    usage = __doc__.format(default_model=CHAT_MODEL)
    args = docopt.docopt(usage, argv=argv, version=VERSION)

    model_name = args.get("--model")
    stream_mode = not args.get("--no-stream")
    create_new = args.get("--create", False)

    client = ollama.Client()

    session_id = get_session_id(create_new)

    print("Type messages to chat. Use /quit to exit.\n", flush=True)

    while True:

        try:
            user_input = get_user_input()
        except EOFError:
            print("\n[EOF]\n")
            break
        except KeyboardInterrupt:
            print("\n[interrupt]\n")
            continue

        if user_input.lower() in {"/quit", "quit", "exit", "q"}:
            break

        try:
            perform_turn(
                client,
                user_input,
                model_name,
                stream_mode,
                session_id=session_id,
            )
        except Exception:
            raise
            continue # ignore error, keep on going


if __name__ == "__main__":
    main()
