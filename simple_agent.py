import anthropic
import json
from typing import Any

# Initialize the Anthropic client
# Make sure ANTHROPIC_API_KEY is set in your environment
client = anthropic.Anthropic()

# ── Tool definitions (tell Claude what tools are available) ──────────────────

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

# ── Tool implementations (the actual Python functions) ───────────────────────

def calculator(operation: str, a: float, b: float) -> dict[str, Any]:
    ops = {
        "add":      a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide":   a / b if b != 0 else "Error: division by zero"
    }
    return {"result": ops[operation], "expression": f"{a} {operation} {b}"}


def weather(city: str) -> dict[str, Any]:
    # Stub — replace with a real API call if you like
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

def run_agent(user_message: str) -> None:
    """
    Send a message to Claude and loop until it finishes.
    Claude may call tools multiple times before giving a final answer.
    """
    print(f"\n{'='*60}")
    print(f"User: {user_message}")
    print(f"{'='*60}")

    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        # ── Claude is done ────────────────────────────────────────
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nAssistant: {block.text}")
            break

        # ── Claude wants to call one or more tools ────────────────
        if response.stop_reason == "tool_use":
            # 1. Save Claude's response (including tool_use blocks) to history
            messages.append({"role": "assistant", "content": response.content})

            # 2. Execute each requested tool
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n  → Tool call : {block.name}")
                    print(f"    Input     : {json.dumps(block.input)}")

                    output = run_tool(block.name, block.input)
                    print(f"    Output    : {output}")

                    # 3. Package the result so Claude can read it
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,   # must match the tool_use id
                        "content": output,
                    })

            # 4. Send all tool results back to Claude and loop again
            messages.append({"role": "user", "content": tool_results})

        else:
            print(f"Unexpected stop_reason: {response.stop_reason}")
            break


# ── Run it ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_agent(
        "What's the weather in London and Tokyo? "
        "Also, if London's temp is lower, multiply the difference by 3."
    )
