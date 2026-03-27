import streamlit as st
import requests
import json
import re
from typing import List, Dict
import streamlit_mermaid as st_mermaid

# ---------- Configuration ----------
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "gpt-oss:20b"

# ---------- Guardrails ----------
BANNED_WORDS = ["hack", "exploit", "malware"]  # extend as needed

def is_safe_input(text: str) -> bool:
    text_lower = text.lower()
    for word in BANNED_WORDS:
        if word in text_lower:
            return False
    return True

# ---------- System Prompt ----------
SYSTEM_PROMPT = """
You are a diagram generator. Output ONLY valid Mermaid flowchart code (graph TD) that matches the user's description.
Do not include any explanations, markdown fences, or extra text.
If colors are specified (e.g., "green" or "red"), use fill:#90EE90 for green and fill:#FFCCCC for red.
"""

# ---------- Helper Functions ----------
def extract_mermaid_code(text: str) -> str:
    """Extract Mermaid code from LLM response, removing markdown fences if present."""
    match = re.search(r"```mermaid\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # If no fences, assume the whole response is the diagram code
    return text.strip()

def call_ollama(messages: List[Dict[str, str]], model: str) -> str:
    """Send messages to Ollama chat endpoint and return the assistant's content."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]
    except Exception as e:
        st.error(f"Ollama error: {e}")
        return None

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Diagram Generator", layout="wide")
st.title("📐 Natural Language to Diagram Generator")
st.markdown("Describe a system or process, and I'll generate a Mermaid flowchart. Colors like 'red' and 'green' are respected.")

# ---------- Session State ----------
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": "user"/"assistant", "content": str}
if "model_name" not in st.session_state:
    st.session_state.model_name = DEFAULT_MODEL

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Settings")
    model = st.text_input("Ollama model name", value=st.session_state.model_name)
    if model != st.session_state.model_name:
        st.session_state.model_name = model
        st.rerun()

    if st.button("Clear conversation history"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("### Guardrails")
    guardrails_enabled = st.checkbox("Enable input filtering", value=True)
    st.markdown("---")
    st.markdown("### About")
    st.info("""
    - Uses a local Ollama LLM to generate Mermaid diagrams.
    - Supports conversation history (append history).
    - Simple content filtering (guardrails) can be enabled.
    - Each diagram can be edited directly in the UI.
    """)

# ---------- Display Chat History ----------
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]

    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:  # assistant
        with st.chat_message("assistant"):
            # Extract and display diagram
            diagram_code = extract_mermaid_code(content)
            st_mermaid.st_mermaid(diagram_code)

            # Editable raw code area
            with st.expander("✏️ Edit diagram code"):
                new_code = st.text_area("Mermaid code", diagram_code, height=200,
                                        key=f"edit_{len(st.session_state.messages)}")
                if st.button("Update diagram", key=f"update_{len(st.session_state.messages)}"):
                    # Replace the assistant message with the new code
                    # (We keep it as a simple string, but we also want to preserve any extra text)
                    st.session_state.messages[-1]["content"] = new_code
                    st.rerun()
            st.caption("Double‑click on nodes to edit in Mermaid Live? – not available here, but you can edit the code above.")

# ---------- Input Area ----------
user_input = st.chat_input("Describe your system or process...")

if user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Guardrails check
    if guardrails_enabled and not is_safe_input(user_input):
        st.error("Input blocked by guardrails. Please rephrase.")
        # Remove the just-added user message
        st.session_state.messages.pop()
        st.rerun()

    # Prepare messages for Ollama (system prompt + history)
    ollama_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    ollama_messages.extend(st.session_state.messages)  # includes the new user message

    # Call LLM
    with st.spinner("Generating diagram..."):
        response = call_ollama(ollama_messages, st.session_state.model_name)

    if response:
        st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        # Remove the user message if LLM failed
        st.session_state.messages.pop()
        st.error("Failed to get a response from Ollama. Check that the model is running and the name is correct.")

    st.rerun()