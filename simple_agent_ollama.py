import ollama                          # ← CHANGED  (was: import anthropic)
import json
from typing import Any

# ┌─────────────────────────────────────────────────────────────────────────┐
# │  SUMMARY OF ALL CHANGES vs simple_agent.py (Anthropic version)         │
# │                                                                         │
# │  1. Import        : anthropic → ollama                                  │
# │  2. Client        : anthropic.Anthropic() → ollama.Client()             │
# │  3. Tool schema   : "input_schema" → "type"+"function"+"parameters"     │
# │  4. API call      : client.messages.create() → client.chat()            │
# │  5. Model name    : "claude-opus-4-5" → "llama3.1"                      │
# │  6. max_tokens    : removed (not supported by Ollama)                   │
# │  7. "Done" check  : stop_reason=="end_turn" → not tool_calls            │
# │  8. Response text : response.content[].text → response.message.content  │
# │  9. Tool calls    : response.content[].type=="tool_use" → tool_calls[]  │
# │ 10. Tool input    : block.input (dict) → tool_call.function.arguments   │
# │ 11. Asst message  : {"content": response.content} → response.message    │
# │ 12. Tool result   : {"type":"tool_result","tool_use_id":...}             │
# │                     → {"role":"tool","content":...,"name":...}           │
# └─────────────────────────────────────────────────────────────────────────┘

# ── Client ───────────────────────────────────────────────────────────────────

# CHANGED: Ollama runs locally — no API key needed.
# Default connects to http://localhost:11434
# Make sure Ollama is running: `ollama serve`
# Pull a tool-capable model first: `ollama pull llama3.1`
client = ollama.Client()              # ← CHANGED  (was: client = anthropic.Anthropic())

# ── Tool definitions ─────────────────────────────────────────────────────────
#
# CHANGED: Ollama uses the OpenAI-style tool schema:
#   • Each tool is wrapped in {"type": "function", "function": {...}}
#   • Tool details live under the "function" key
#   • The schema key is "parameters"  (was "input_schema" in Anthropic)
#
# Was (Anthropic):
#   {"name": "calculator", "description": "...", "input_schema": {...}}
#
# Now (Ollama / OpenAI):
#   {"type": "function", "function": {"name": "calculator", "description": "...", "parameters": {...}}}

tools = [
    {
        "type": "function",                       # ← CHANGED  (new required wrapper)
        "function": {                             # ← CHANGED  (details now nested here)
            "name": "calculator",
            "description": "Performs basic arithmetic: add, subtract, multiply, divide",
            "parameters": {                       # ← CHANGED  (was "input_schema")
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
        }
    },
    {
        "type": "function",                       # ← CHANGED  (new required wrapper)
        "function": {                             # ← CHANGED  (details now nested here)
            "name": "weather",
            "description": "Returns current weather for a given city",
            "parameters": {                       # ← CHANGED  (was "input_schema")
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
    }
]

# ── Tool implementations ──────────────────────────────────────────────────────
# UNCHANGED: pure Python logic — no SDK dependency here

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
    # UNCHANGED
    if name == "calculator":
        result = calculator(**inputs)
    elif name == "weather":
        result = weather(**inputs)
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result)


# ── Agentic loop ──────────────────────────────────────────────────────────────

def run_agent(user_message: str) -> None:
    print(f"\n{'='*60}")
    print(f"User: {user_message}")
    print(f"{'='*60}")

    messages = [{"role": "user", "content": user_message}]  # UNCHANGED

    while True:
        response = client.chat(           # ← CHANGED  (was: client.messages.create)
            model="llama3.1",             # ← CHANGED  (was: "claude-opus-4-5")
            tools=tools,                  # UNCHANGED
            messages=messages,            # UNCHANGED
                                          # ← CHANGED  (removed: max_tokens=1024)
        )

        # ── Model is done (no tool calls in the response) ─────────
        # CHANGED: Ollama signals "done" when tool_calls is empty/None.
        # Was: if response.stop_reason == "end_turn":
        #          for block in response.content: print(block.text)
        if not response.message.tool_calls:           # ← CHANGED
            print(f"\nAssistant: {response.message.content}")  # ← CHANGED
            break

        # ── Model wants to call one or more tools ─────────────────
        # CHANGED: tool calls live in response.message.tool_calls (not response.content)
        # Was: if response.stop_reason == "tool_use":

        # 1. Save the assistant message (with tool_calls) to history
        # CHANGED: was messages.append({"role":"assistant","content":response.content})
        messages.append(response.message)             # ← CHANGED

        # 2. Execute each tool and append its result as a "tool" message
        for tool_call in response.message.tool_calls:  # ← CHANGED  (was: for block in response.content)

            # CHANGED: access via .function.name / .function.arguments
            # Was: block.name, block.input
            name   = tool_call.function.name           # ← CHANGED
            inputs = tool_call.function.arguments      # ← CHANGED  (already a dict)

            print(f"\n  → Tool call : {name}")
            print(f"    Input     : {json.dumps(inputs)}")

            output = run_tool(name, inputs)            # UNCHANGED
            print(f"    Output    : {output}")

            # 3. Append tool result as a separate "tool" role message
            # CHANGED: Ollama uses role="tool" messages (one per tool call),
            # not a bundled list under role="user" with type="tool_result".
            # Was:
            #   tool_results.append({"type":"tool_result","tool_use_id":block.id,...})
            #   messages.append({"role":"user","content":tool_results})
            messages.append({                          # ← CHANGED
                "role": "tool",                        # ← CHANGED
                "content": output,                     # ← CHANGED
                "name": name,                          # ← CHANGED
            })
        # (loop continues — Ollama will now see the tool results and reply)


# ── Run it ────────────────────────────────────────────────────────────────────
# UNCHANGED

if __name__ == "__main__":
    run_agent(
        "What's the weather in London and Tokyo? "
        "Also, if London's temp is lower, multiply the difference by 3."
    )
