#!/usr/bin/env python3
"""Simple synchronous chat client for Ollama with tool support.

Usage:
  simple_chat.py [--model MODEL] [--no-stream]
  simple_chat.py (-h | --help | --version)

Options:
  --model MODEL    Ollama model to use [default: {default_model}].
  --no-stream      Disable streaming output (buffer full responses).
  -h --help        Show this screen.
  --version        Show version.

This script keeps an in-memory conversation history, streams responses from
Ollama, and executes tools defined in ``funcs2`` when requested. It bypasses
all pub/sub and database persistence layers.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, Iterable, List

import ollama
import docopt
import atexit
from pathlib import Path

import funcs2 as funcs
from config import CHAT_MODEL

TOOLS = getattr(funcs, "Tools", [])

try:
    import readline  # type: ignore
except ImportError:  # pragma: no cover - platform without readline
    readline = None  # type: ignore
else:
    HISTORY_FILE = Path.home() / ".simple_chat_history"
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

    atexit.register(_save_history)


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


def perform_turn(
    client: ollama.Client,
    history: List[Dict[str, Any]],
    user_input: str,
    model_name: str,
    stream_mode: bool,
) -> None:

    prin = lambda s: print(s, end='', flush=True)

    assistant_fragments: List[str] = []
    pending_tool_calls: List[Dict[str, Any]] = []

    history.append({"role": "user", "content": user_input})

    while True:

        assistant_fragments.clear()
        pending_tool_calls.clear()

        try:
            chunks = iter_chat(client, history, model_name, stream_mode)
        except Exception as exc:
            print(f"[error] {exc}", file=sys.stderr)
            history.pop() # AVOID DECOHERENCE
            raise

        prin("asst>")
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
                else:
                    pending_tool_calls.append(tool_call)
                    pass
                pass
            pass
        prin("\n")

        if assistant_fragments:
            history.append({
                "role": "assistant",
                "content": "".join(assistant_fragments),
            })

        if not pending_tool_calls:
            return

        for call in pending_tool_calls:
            fn = call.get("function", {})
            name = fn.get("name")
            arguments = fn.get("arguments") or {}
            result = call_tool(name, arguments)
            print(f"tool[{name}]> {result}")
            history.append({
                "role": "tool",
                "name": name,
                "content": result,
            })


def get_user_input(role: str = "user") -> str:
    while True:
        if ret:= input(f"{role}> ").strip():
            return ret


def main(argv: List[str] | None = None) -> None:
    usage = __doc__.format(default_model=CHAT_MODEL)
    args = docopt.docopt(usage, argv=argv, version="simple_chat 1.0.1")

    model_name = args.get("--model")
    stream_mode = not args.get("--no-stream")

    history: List[Dict[str, Any]] = []

    client = ollama.Client()

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
            perform_turn(client, history, user_input, model_name, stream_mode)
        except Exception:
            raise
            continue # ignore error, keep on going


if __name__ == "__main__":
    main()
