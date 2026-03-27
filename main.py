import streamlit as st
import requests
import json
import re
import uuid
from typing import List, Dict
import streamlit_mermaid as st_mermaid

# ---------- Configuration ----------
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "gpt-oss:20b"

# ---------- Guardrails ----------
BANNED_WORDS = ["hack", "exploit", "malware"]


def is_safe_input(text: str) -> bool:
    text_lower = text.lower()
    return not any(word in text_lower for word in BANNED_WORDS)


# ---------- Helper Functions ----------
def extract_mermaid_code(text: str) -> str:
    match = re.search(r"```mermaid\s*\n(.*?)\n```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def call_ollama(messages: List[Dict[str, str]], model: str) -> str:
    payload = {"model": model, "messages": messages, "stream": False}
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        st.error(f"Ollama error: {e}")
        return None


# ---------- Session Management ----------
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "model_name" not in st.session_state:
    st.session_state.model_name = DEFAULT_MODEL

# --- New Styling State ---
if "diag_theme" not in st.session_state:
    st.session_state.diag_theme = "base"      # Changed default to 'base' (light)
if "diag_dir" not in st.session_state:
    st.session_state.diag_dir = "TD"


def start_new_chat():
    new_id = str(uuid.uuid4())
    st.session_state.sessions[new_id] = {"name": f"New Diagram {len(st.session_state.sessions) + 1}", "messages": []}
    st.session_state.current_session_id = new_id


if not st.session_state.sessions:
    start_new_chat()

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Diagram Architect", layout="wide")

# --- Aggressive CSS for forcing white background ---
st.markdown(
    """
    <style>
    /* Use a more specific selector for the card */
    div[data-testid="stChatMessage"] .diagram-card {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1) !important;
    }

    /* Target the SVG directly within the mermaid component for a white background */
    div[data-testid="stChatMessage"] .diagram-card div[data-mermaid] svg {
        background: #ffffff !important;
        border-radius: 8px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Sidebar: History & Customization ----------
with st.sidebar:
    st.title("Saved Chats")
    if st.button("➕ New Chat", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.write("---")
    for session_id, session_data in st.session_state.sessions.items():
        btn_type = "primary" if session_id == st.session_state.current_session_id else "secondary"
        if st.button(session_data["name"], key=session_id, use_container_width=True, type=btn_type):
            st.session_state.current_session_id = session_id
            st.rerun()

    st.write("---")
    st.header("🎨 Diagram Style")

    # Theme selection – only light-friendly themes are shown (or keep all but ensure background is forced)
    # We'll keep all options but the injected init will always enforce white background.
    st.session_state.diag_theme = st.selectbox(
        "Theme",
        ["base", "neutral", "default", "forest"],   # Removed 'dark' to avoid confusion
        index=0
    )

    # Layout Direction
    st.session_state.diag_dir = st.radio(
        "Direction",
        ["TD", "LR"],
        format_func=lambda x: "Vertical (Top-Down)" if x == "TD" else "Horizontal (Left-Right)",
        horizontal=True
    )

    st.write("---")
    st.header("⚙️ Settings")
    st.session_state.model_name = st.text_input("Ollama model", value=st.session_state.model_name)
    guardrails_enabled = st.checkbox("Enable Guardrails", value=True)

# ---------- Dynamic System Prompt ----------
current_dir = st.session_state.diag_dir
SYSTEM_PROMPT = f"""
You are a diagram generator. Output ONLY valid Mermaid flowchart code.
The graph MUST start with 'graph {current_dir}'.
Do not include any explanations or markdown fences.
Colors: green (fill:#90EE90), red (fill:#FFCCCC).
"""

# ---------- Main Chat Interface ----------
current_session = st.session_state.sessions[st.session_state.current_session_id]
st.title(f"📐 {current_session['name']}")

# Display Messages
for idx, msg in enumerate(current_session["messages"]):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            raw_code = extract_mermaid_code(msg["content"])

            # --- Force white background with minimal theme overrides ---
            # This ensures that regardless of the selected theme, the background is white.
            theme_init = (
                f"%%{{init: {{'theme': '{st.session_state.diag_theme}', "
                "'themeVariables': {"
                "'background': '#FFFFFF'"
                "}}}}%%\n"
            )
            styled_code = theme_init + raw_code

            st.markdown("<div class='diagram-card'>", unsafe_allow_html=True)
            st_mermaid.st_mermaid(styled_code, key=f"viz_{idx}")
            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("✏️ Edit Code"):
                edited = st.text_area("Source", raw_code, key=f"edit_{idx}")
                if st.button("Save Changes", key=f"btn_{idx}"):
                    current_session["messages"][idx]["content"] = edited
                    st.rerun()

# ---------- Chat Input ----------
if user_input := st.chat_input("Describe your flow..."):
    if not current_session["messages"]:
        current_session["name"] = (user_input[:25] + '...') if len(user_input) > 25 else user_input

    if guardrails_enabled and not is_safe_input(user_input):
        st.error("Input blocked by guardrails.")
    else:
        current_session["messages"].append({"role": "user", "content": user_input})
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + current_session["messages"]

        with st.spinner("Drawing..."):
            response = call_ollama(api_messages, st.session_state.model_name)
            if response:
                current_session["messages"].append({"role": "assistant", "content": response})
                st.rerun()