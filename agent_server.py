import anthropic
import json
import os
from typing import Any

# NEW: Flask for the web server
from flask import Flask, request, jsonify, send_from_directory

# ── Client (same as simple_agent_proxy.py) ───────────────────────────────────

_api_key = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(
    base_url="http://localhost:6655/anthropic",
    api_key=_api_key,
    default_headers={"Authorization": f"Bearer {_api_key}"},
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
    if name == "calculator":
        result = calculator(**inputs)
    elif name == "weather":
        result = weather(**inputs)
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result)


# ── Agentic loop ──────────────────────────────────────────────────────────────
# CHANGED vs simple_agent_proxy.py:
#   • Returns (messages, final_text, tool_logs) instead of None
#   • tool_logs is a plain-dict list safe to JSON-serialize for the HTTP response

def run_agent(user_message: str, messages: list) -> tuple[list, str, list]:
    messages.append({"role": "user", "content": user_message})
    tool_logs: list[dict] = []
    final_text = ""

    while True:
        response = client.messages.create(
            model="anthropic--claude-sonnet-latest",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    final_text = block.text
                    break
            messages.append({"role": "assistant", "content": response.content})
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    output = run_tool(block.name, block.input)
                    tool_logs.append({           # ← NEW: collect logs for the UI
                        "name":   block.name,
                        "input":  block.input,
                        "output": json.loads(output),
                    })
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     output,
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            break

    return messages, final_text, tool_logs


# ── Flask app ─────────────────────────────────────────────────────────────────
# NEW: everything below is new

app = Flask(__name__)

# In-memory session store: session_id → messages list
# (resets when the server restarts)
sessions: dict[str, list] = {}

_HERE = os.path.dirname(os.path.abspath(__file__))


@app.route("/")
def index():
    """Serve the chat UI."""
    return send_from_directory(_HERE, "agent_ui.html")


@app.route("/chat", methods=["POST"])
def chat():
    """Accept a user message, run the agent, return response + tool logs."""
    data = request.get_json()
    session_id   = data.get("session_id", "default")
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    if session_id not in sessions:
        sessions[session_id] = []

    try:
        messages, final_text, tool_logs = run_agent(user_message, sessions[session_id])
        sessions[session_id] = messages
        return jsonify({"response": final_text, "tool_calls": tool_logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/clear", methods=["POST"])
def clear():
    """Wipe the conversation history for a session."""
    session_id = (request.get_json() or {}).get("session_id", "default")
    sessions.pop(session_id, None)
    return jsonify({"status": "cleared"})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  ✓  Agent UI  →  http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
