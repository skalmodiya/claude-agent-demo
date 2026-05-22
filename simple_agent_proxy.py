import anthropic                       # UNCHANGED
import json
import os
from typing import Any

# ┌─────────────────────────────────────────────────────────────────────────┐
# │  SUMMARY OF ALL CHANGES vs simple_agent.py (direct Anthropic version)  │
# │                                                                         │
# │  Only 2 lines changed — both in the client setup:                       │
# │                                                                         │
# │  1. base_url  : added → "http://localhost:6655/anthropic/v1"            │
# │  2. api_key   : added → "dummy"  (proxy handles auth, no real key)      │
# │                                                                         │
# │  Everything else is IDENTICAL to simple_agent.py                        │
# └─────────────────────────────────────────────────────────────────────────┘

# ── Client ───────────────────────────────────────────────────────────────────

# CHANGED: point the Anthropic SDK at your local LLM proxy instead of
#          Anthropic's servers. The SDK appends /v1/messages automatically, so:
#            {base_url} + /v1/messages  →  http://localhost:6655/anthropic/v1/messages
#
# Was:
#   client = anthropic.Anthropic()
#
# Now:
_api_key = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(
    base_url="http://localhost:6655/anthropic",      # ← FIXED: SDK appends /v1/messages automatically
    api_key=_api_key,                               # SDK needs this (sends as x-api-key)
    default_headers={
        "Authorization": f"Bearer {_api_key}",      # ← CHANGED: proxy expects Bearer token
    },
)

# ── Tool definitions (UNCHANGED) ─────────────────────────────────────────────

tools = [
    {
        "name": "calculator",
        "description": "Performs basic arithmetic: add, subtract, multiply, divide",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "Arithmetic operation to perform"
                },
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["operation", "a", "b"]
        }
    },
    {
        "name": "weather",
        "description": "Returns current weather for a given city",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. 'London'"
                }
            },
            "required": ["city"]
        }
    }
]

# ── Tool implementations (UNCHANGED) ─────────────────────────────────────────

def calculator(operation: str, a: float, b: float) -> dict[str, Any]:
    ops = {
        "add":      a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide":   a / b if b != 0 else "Error: division by zero"
    }
    return {"result": ops[operation], "expression": f"{a} {operation} {b}"}


def weather(city: str) -> dict[str, Any]:
    mock_data = {
        "New York": {"temp_f": 72, "condition": "Sunny"},
        "London":   {"temp_f": 61, "condition": "Cloudy"},
        "Tokyo":    {"temp_f": 78, "condition": "Rainy"},
        "Paris":    {"temp_f": 68, "condition": "Partly cloudy"},
    }
    data = mock_data.get(city, {"error": f"No data for '{city}'"})
    return {"city": city, **data}


def run_tool(name: str, inputs: dict) -> str:
    """Dispatch a tool call and return the result as a JSON string."""
    if name == "calculator":
        result = calculator(**inputs)
    elif name == "weather":
        result = weather(**inputs)
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result)


# ── Agentic loop ─────────────────────────────────────────────────────────────
# CHANGED: now accepts `messages` list so history is shared across turns,
#          and returns it so the caller can pass it into the next turn.
# Was: def run_agent(user_message: str) -> None  (created a fresh list each call)

def run_agent(user_message: str, messages: list) -> list:   # ← CHANGED signature
    """
    Append user_message to messages, call the model (looping through tool calls),
    and return the updated messages list including the assistant's final reply.
    """
    messages.append({"role": "user", "content": user_message})  # ← CHANGED (was: messages = [...])

    while True:
        response = client.messages.create(
            model="anthropic--claude-sonnet-latest",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        # ── Done ──────────────────────────────────────────────────
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nAssistant: {block.text}\n")
            messages.append({"role": "assistant", "content": response.content})  # ← CHANGED: save reply to history
            break

        # ── Tool call ─────────────────────────────────────────────
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n  → Tool call : {block.name}")
                    print(f"    Input     : {json.dumps(block.input)}")

                    output = run_tool(block.name, block.input)
                    print(f"    Output    : {output}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            print(f"Unexpected stop_reason: {response.stop_reason}")
            break

    return messages                                             # ← CHANGED: return updated history


# ── Interactive chat loop ─────────────────────────────────────────────────────
# CHANGED: replaced the single hardcoded run_agent(...) call with a REPL loop.

def chat_loop() -> None:
    """Read user input, run the agent, repeat. Type 'quit' or 'exit' to stop,
    'clear' to wipe conversation history and start fresh."""

    print("=" * 60)
    print("  Interactive Agent  —  proxy: localhost:6655")
    print("  Commands: 'clear' = new conversation | 'quit' = exit")
    print("=" * 60)

    messages: list = []                  # shared history across all turns

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("Bye!")
            break

        if user_input.lower() == "clear":
            messages = []
            print("--- conversation cleared ---")
            continue

        messages = run_agent(user_input, messages)


if __name__ == "__main__":
    chat_loop()                          # ← CHANGED (was: run_agent("hardcoded prompt"))
