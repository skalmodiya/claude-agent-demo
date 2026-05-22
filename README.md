# 🤖 Claude Agent Examples

A simple, well-commented Python agent built with the Anthropic SDK — demonstrating tool use, agentic loops, and a web chat UI against a local LLM proxy.

---

## 📁 Project Structure

```
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
- A running LLM proxy that speaks the Anthropic API format
- An API key for your proxy

```bash
pip install anthropic flask
```

---

## 🚀 Quickstart

### 1. Interactive CLI

Runs as an interactive chat loop in your terminal. Type messages, get responses, type `clear` to reset history.

```bash
export ANTHROPIC_API_KEY=your_proxy_key   # Mac/Linux
set ANTHROPIC_API_KEY=your_proxy_key      # Windows

python simple_agent_proxy.py
```

**Commands while running:**

| Input | Action |
|---|---|
| Any text | Send a message to the agent |
| `clear` | Wipe conversation history and start fresh |
| `quit` / `exit` | Exit the program |

---

### 2. Web Chat UI

A browser-based chat interface backed by Flask. Conversations persist in memory per browser tab.

```bash
export ANTHROPIC_API_KEY=your_proxy_key   # Mac/Linux
set ANTHROPIC_API_KEY=your_proxy_key      # Windows

python agent_server.py
```

Then open **http://localhost:5000** in your browser.

**Features:**
- 💬 Chat bubbles — user messages on the right, assistant on the left
- 🔧 Collapsible tool call cards showing input & output for every tool invocation
- ✨ Animated typing indicator while the agent is thinking
- 🗑️ Clear button to reset conversation history

---

## 🔧 Proxy Configuration

Both files point to the same proxy. To change the endpoint or model, edit the client block at the top of `simple_agent_proxy.py` and `agent_server.py`:

```python
client = anthropic.Anthropic(
    base_url="http://localhost:6655/anthropic",   # proxy URL — without trailing /v1
    api_key=os.environ["ANTHROPIC_API_KEY"],
    default_headers={
        "Authorization": f"Bearer {os.environ['ANTHROPIC_API_KEY']}",
    },
)
```

> **Note:** The SDK automatically appends `/v1/messages` to `base_url`, so omit the `/v1` suffix.

To change the model, update this line in both files:

```python
model="anthropic--claude-sonnet-latest"   # replace with your proxy's model name
```

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
