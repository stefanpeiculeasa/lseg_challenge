# 📐 Diagram Architect

A conversational AI-powered flowchart builder built with Streamlit. Describe a process in plain language and get an interactive Mermaid diagram back — with a GUI editor, session history, and style controls.

---

## Features

- **AI diagram generation** — Chat with a local LLM (via Ollama) to generate Mermaid flowcharts from natural language descriptions
- **GUI diagram editor** — Edit nodes and edges visually using table-based inputs without touching any code
- **Multi-session chat history** — Create and switch between multiple diagram sessions, each with its own conversation history
- **Style customization** — Choose from multiple Mermaid themes (`base`, `neutral`, `default`, `forest`) and diagram directions (Top-Down or Left-Right)
- **Fallback raw editor** — If a diagram fails to parse, a raw code editor is shown so you can fix it manually
- **Guardrails** — Optional input filtering to block unsafe or inappropriate prompts

---

## Requirements

- Python 3.9+
- [Ollama](https://ollama.com) running locally on `http://localhost:11434`
- A compatible model pulled in Ollama (default: `gpt-oss:20b`)

### Python dependencies

```bash
pip install streamlit requests streamlit-mermaid
```

---

## Getting Started

1. **Start Ollama** and ensure your model is available:
   ```bash
   ollama pull gpt-oss:20b   # or whichever model you prefer
   ollama serve
   ```

2. **Run the app:**
   ```bash
   streamlit run main.py
   ```

3. **Open your browser** at `http://localhost:8501`

---

## Usage

### Generating a diagram
Type a description of your process in the chat input at the bottom, e.g.:

> *"Show a user login flow with success and failure paths"*

The AI will respond with a Mermaid flowchart rendered inline.

### Editing a diagram
Expand the **✏️ Edit Diagram with GUI** panel beneath any diagram to:
- Add, rename, or remove nodes
- Add, relabel, or remove edges
- Apply a new direction (Top-Down / Left-Right) independently of the sidebar setting

Click **Save Diagram Changes** to update the diagram, or **Apply Direction** to only change the layout direction.

### Switching sessions
Use the **sidebar** to create new chats or switch between existing ones. Each session maintains its own conversation history.

### Changing style
In the sidebar under **🎨 Diagram Style**, pick a theme and a default direction. New diagrams will use these settings; existing diagrams can be updated via the GUI editor.

---

## Configuration

| Setting | Location | Default |
|---|---|---|
| Ollama API URL | `OLLAMA_URL` constant in `main.py` | `http://localhost:11434/api/chat` |
| Default model | `DEFAULT_MODEL` constant in `main.py` | `gpt-oss:20b` |
| Model name (runtime) | Sidebar → Settings | Same as default |
| Guardrails | Sidebar → Settings checkbox | Enabled |
| Banned words | `BANNED_WORDS` list in `main.py` | `["hack", "exploit", "malware"]` |

---

## Project Structure

```
main.py                  # Main application (single-file)
```

Key functions inside `main.py`:

| Function | Purpose |
|---|---|
| `parse_mermaid_to_graph()` | Parses Mermaid flowchart code into nodes and edges |
| `generate_mermaid_from_graph()` | Serializes nodes and edges back into Mermaid code |
| `call_ollama()` | Sends messages to the Ollama API and returns the response |
| `is_safe_input()` | Checks user input against the banned words list |
| `start_new_chat()` | Initializes a new session in `st.session_state` |

---

## Limitations

- Only supports Mermaid **flowchart** diagrams (`graph TD` / `graph LR`). Other diagram types (sequence, class, Gantt, etc.) are not supported.
- Node IDs must be simple alphanumeric strings — spaces and punctuation in IDs will cause parse errors.
- Session data is stored in Streamlit's in-memory session state and is lost on page refresh.
- Requires a locally running Ollama instance; no cloud LLM support out of the box.

---

## License

MIT
