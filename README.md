# 🤖 Claude Agent Examples

A collection of simple, well-commented Python agents built with the Anthropic SDK — showing how to wire up tool use, agentic loops, and a web chat UI across three different backends.

---

## 📁 Project Structure

```
├── simple_agent.py          # Agent using Anthropic API directly
├── simple_agent_ollama.py   # Agent using a local Ollama model
├── simple_agent_proxy.py    # Agent using a local LLM proxy (interactive CLI)
├── agent_server.py          # Flask backend for the web UI
├── agent_ui.html            # Web chat interface
└── .gitignore
```

---

## 🛠️ Tools the Agent Has

| Tool | Description |
|---|---|
| `weather` | Returns current weather for a city (stub — easy to swap for a real API) |
| `calculator` | Performs add, subtract, multiply, divide |

The agent autonomously chains tool calls to answer multi-step questions like:
> *"What's the weather in London and Tokyo? If London is cooler, multiply the difference by 3."*

---

## ⚙️ Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/) **or** a running LLM proxy / Ollama instance

Install the base dependency:

```bash
pip install anthropic
```

---

## 🚀 Quickstart

### 1. Direct Anthropic API

Uses the Anthropic API straight from the SDK.

```bash
pip install anthropic

export ANTHROPIC_API_KEY=your_key_here   # Mac/Linux
set ANTHROPIC_API_KEY=your_key_here      # Windows

python simple_agent.py
```

---

### 2. Ollama (Local Model)

Runs against a local model via [Ollama](https://ollama.com). No API key needed.

```bash
pip install ollama

# Pull a tool-capable model (one-time)
ollama pull llama3.1

# Start the Ollama server
ollama serve

python simple_agent_ollama.py
```

> **Note:** Ollama uses the OpenAI-style tool schema, so the tool definitions look slightly different from the Anthropic version — see the comments in the file.

---

### 3. LLM Proxy (Interactive CLI)

Points the Anthropic SDK at a local proxy that speaks the Anthropic API format.
Runs as an interactive chat loop — type messages, get responses, type `clear` to reset.

```bash
pip install anthropic

export ANTHROPIC_API_KEY=your_proxy_key
python simple_agent_proxy.py
```

**Commands while running:**

| Input | Action |
|---|---|
| Any text | Send message to the agent |
| `clear` | Wipe conversation history and start fresh |
| `quit` / `exit` | Exit the program |

**Configuration** (top of `simple_agent_proxy.py`):

```python
client = anthropic.Anthropic(
    base_url="http://localhost:6655/anthropic",   # your proxy endpoint
    api_key=os.environ["ANTHROPIC_API_KEY"],
    default_headers={
        "Authorization": f"Bearer {os.environ['ANTHROPIC_API_KEY']}",
    },
)
```

> The SDK automatically appends `/v1/messages`, so set `base_url` **without** the trailing `/v1`.

---

### 4. Web Chat UI

A browser-based chat interface backed by Flask. Conversations persist in memory per browser tab.

```bash
pip install anthropic flask

export ANTHROPIC_API_KEY=your_proxy_key

python agent_server.py
```

Then open **http://localhost:5000** in your browser.

**Features:**
- 💬 Chat bubbles — user messages on the right, assistant on the left
- 🔧 Collapsible tool call cards showing input & output for every tool invocation
- ✨ Animated typing indicator while the agent is thinking
- 🗑️ Clear button to reset conversation history

![Web UI preview](https://placehold.co/800x450/f0f2f5/71717a?text=Agent+Chat+UI)

---

## 🔄 SDK Differences at a Glance

| | Anthropic SDK | Ollama SDK |
|---|---|---|
| Tool schema key | `input_schema` | `parameters` (inside `function`) |
| Tool wrapper | none | `{"type": "function", "function": {...}}` |
| API call | `client.messages.create()` | `client.chat()` |
| "Done" signal | `stop_reason == "end_turn"` | `not response.message.tool_calls` |
| Tool result format | `{"type": "tool_result", "tool_use_id": ...}` | `{"role": "tool", "content": ...}` |

---

## 🏗️ How the Agentic Loop Works

```
User message
     │
     ▼
┌─────────────────────┐
│  Call LLM with      │
│  tools + messages   │
└────────┬────────────┘
         │
    stop_reason?
    ┌────┴────┐
  tool_use  end_turn
    │          │
    ▼          ▼
Execute    Print final
tools      answer & stop
    │
    └──► append results
         to messages
         └──► loop again
```

---

## 📄 License

MIT
