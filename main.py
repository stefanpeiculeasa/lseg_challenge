import streamlit as st
import requests
import json
import re
import uuid
from typing import List, Dict, Tuple, Optional
import streamlit_mermaid as st_mermaid

# ---------- Configuration ----------
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "gpt-oss:20b"

# ---------- Guardrails ----------
BANNED_WORDS = ["hack", "exploit", "malware"]


def is_safe_input(text: str) -> bool:
    text_lower = text.lower()
    return not any(word in text_lower for word in BANNED_WORDS)


# ---------- Diagram Parsing and Generation ----------
def parse_mermaid_to_graph(code: str) -> Tuple[str, Dict[str, str], List[Dict[str, str]]]:
    """
    Parse Mermaid flowchart code into direction, nodes, and edges.
    Returns (direction, nodes_dict, edges_list)
    Raises ValueError if code is invalid.
    """
    lines = code.strip().split("\n")
    if not lines:
        raise ValueError("Empty diagram code")
    
    # Extract direction from first line
    first_line = lines[0].strip()
    direction = "TD"
    if first_line.startswith("graph "):
        direction = first_line.split()[1].strip()
        lines = lines[1:]  # remove the graph line
    else:
        raise ValueError("Missing 'graph' directive in first line")
    
    nodes = {}  # id -> label
    edges = []
    
    # Patterns
    node_def_pattern = re.compile(r'(\w+)\[([^\]]+)\]')  # A[Label]
    simple_node_pattern = re.compile(r'^(\w+)$')  # A
    edge_pattern = re.compile(r'(\w+)\s*-->\s*(?:\|([^|]+)\|)?\s*(\w+)')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for node definitions
        for match in node_def_pattern.finditer(line):
            node_id, label = match.groups()
            nodes[node_id] = label
        
        # Check for edges
        for match in edge_pattern.finditer(line):
            source, label, target = match.groups()
            edges.append({
                "source": source,
                "target": target,
                "label": label or ""
            })
            # Add nodes if not already present (default label = id)
            if source not in nodes:
                nodes[source] = source
            if target not in nodes:
                nodes[target] = target
        
        # Also check for simple node definitions (like "A" alone)
        simple_match = simple_node_pattern.match(line)
        if simple_match and simple_match.group(1) not in nodes:
            node_id = simple_match.group(1)
            nodes[node_id] = node_id
    
    # If no nodes or edges were found, raise error
    if not nodes and not edges:
        raise ValueError("No valid nodes or edges found in code")
    
    return direction, nodes, edges


def generate_mermaid_from_graph(direction: str, nodes: Dict[str, str], edges: List[Dict[str, str]]) -> str:
    """
    Generate Mermaid flowchart code from direction, nodes, and edges.
    """
    lines = [f"graph {direction}"]
    
    # Node definitions (only those with custom labels)
    for node_id, label in nodes.items():
        if label != node_id:
            lines.append(f"{node_id}[{label}]")
    
    # Edges
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        label = edge.get("label", "")
        if label:
            lines.append(f"{source} -->|{label}| {target}")
        else:
            lines.append(f"{source} --> {target}")
    
    return "\n".join(lines)


# ---------- Ollama Call ----------
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
if "diag_theme" not in st.session_state:
    st.session_state.diag_theme = "base"
if "diag_dir" not in st.session_state:
    st.session_state.diag_dir = "TD"


def start_new_chat():
    new_id = str(uuid.uuid4())
    st.session_state.sessions[new_id] = {
        "name": f"New Diagram {len(st.session_state.sessions) + 1}",
        "messages": []
    }
    st.session_state.current_session_id = new_id


if not st.session_state.sessions:
    start_new_chat()

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Diagram Architect", layout="wide")

# --- CSS to remove white bar ---
st.markdown(
    """
    <style>
    /* Remove extra spacing from chat message container */
    div[data-testid="stChatMessage"] {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    /* Diagram card styling - remove top margin/padding */
    .diagram-card {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1) !important;
    }
    /* Ensure SVG background is white */
    div[data-mermaid] svg {
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
    st.session_state.diag_theme = st.selectbox(
        "Theme",
        ["base", "neutral", "default", "forest"],
        index=0
    )
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

# ---------- Main Chat Interface ----------
current_session = st.session_state.sessions[st.session_state.current_session_id]
st.title(f"📐 {current_session['name']}")

# Cache for parsed graphs to avoid re-parsing
if "graph_cache" not in st.session_state:
    st.session_state.graph_cache = {}

# Display Messages
for idx, msg in enumerate(current_session["messages"]):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            raw_code = msg["content"]
            
            # Attempt to parse the diagram
            cache_key = f"{st.session_state.current_session_id}_{idx}"
            try:
                if cache_key not in st.session_state.graph_cache:
                    direction, nodes, edges = parse_mermaid_to_graph(raw_code)
                    st.session_state.graph_cache[cache_key] = {
                        "direction": direction,
                        "nodes": nodes,
                        "edges": edges
                    }
                graph_data = st.session_state.graph_cache[cache_key]
                parse_success = True
            except ValueError as e:
                # Parsing failed, show raw editor and warning
                parse_success = False
                st.warning(f"⚠️ Could not parse diagram: {e}. You can edit the raw code below.")
            
            # Show diagram only if parsing succeeded
            if parse_success:
                # Apply theme
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
            else:
                # Fallback: show raw code editor
                st.markdown("<div class='diagram-card'>", unsafe_allow_html=True)
                st.markdown("**Raw Mermaid Code (invalid)**")
                edited = st.text_area("", raw_code, height=200, key=f"raw_{idx}")
                if st.button("Save Changes", key=f"raw_save_{idx}"):
                    current_session["messages"][idx]["content"] = edited
                    # Invalidate cache
                    if cache_key in st.session_state.graph_cache:
                        del st.session_state.graph_cache[cache_key]
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                # Don't show GUI editor because we can't parse
                continue
            
            # --- GUI Diagram Editor (only if parsing succeeded) ---
            with st.expander("✏️ Edit Diagram with GUI", expanded=False):
                # Node Editor
                st.subheader("Nodes")
                node_initial = [{"ID": node_id, "Label": label} for node_id, label in graph_data["nodes"].items()]
                node_edited = st.data_editor(
                    node_initial,
                    column_config={
                        "ID": st.column_config.TextColumn("Node ID", required=True),
                        "Label": st.column_config.TextColumn("Display Label")
                    },
                    num_rows="dynamic",
                    key=f"node_editor_{idx}"
                )
                # Convert to list of dicts
                if node_edited is not None:
                    if hasattr(node_edited, 'to_dict'):
                        node_rows = node_edited.to_dict('records')
                    elif isinstance(node_edited, list):
                        node_rows = node_edited
                    else:
                        node_rows = []
                else:
                    node_rows = []
                
                new_nodes = {}
                for row in node_rows:
                    node_id = row.get("ID", "").strip()
                    node_label = row.get("Label", "").strip()
                    if node_id:
                        new_nodes[node_id] = node_label if node_label else node_id
                
                # Edge Editor
                st.subheader("Edges")
                edge_initial = []
                for e in graph_data["edges"]:
                    edge_initial.append({
                        "Source": e["source"],
                        "Target": e["target"],
                        "Label": e.get("label", "")
                    })
                edge_edited = st.data_editor(
                    edge_initial,
                    column_config={
                        "Source": st.column_config.TextColumn("Source", required=True),
                        "Target": st.column_config.TextColumn("Target", required=True),
                        "Label": st.column_config.TextColumn("Label")
                    },
                    num_rows="dynamic",
                    key=f"edge_editor_{idx}"
                )
                if edge_edited is not None:
                    if hasattr(edge_edited, 'to_dict'):
                        edge_rows = edge_edited.to_dict('records')
                    elif isinstance(edge_edited, list):
                        edge_rows = edge_edited
                    else:
                        edge_rows = []
                else:
                    edge_rows = []
                
                new_edges = []
                for row in edge_rows:
                    source = row.get("Source", "").strip()
                    target = row.get("Target", "").strip()
                    label = row.get("Label", "").strip()
                    if source and target:
                        new_edges.append({
                            "source": source,
                            "target": target,
                            "label": label
                        })
                
                # Buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Apply Direction", key=f"apply_dir_{idx}"):
                        new_direction = st.session_state.diag_dir
                        new_code = generate_mermaid_from_graph(new_direction, new_nodes, new_edges)
                        current_session["messages"][idx]["content"] = new_code
                        graph_data["direction"] = new_direction
                        graph_data["nodes"] = new_nodes
                        graph_data["edges"] = new_edges
                        st.success("Diagram updated with new direction!")
                        st.rerun()
                with col2:
                    if st.button("Save Diagram Changes", key=f"save_graph_{idx}"):
                        direction_to_use = graph_data.get("direction", st.session_state.diag_dir)
                        new_code = generate_mermaid_from_graph(direction_to_use, new_nodes, new_edges)
                        current_session["messages"][idx]["content"] = new_code
                        graph_data["direction"] = direction_to_use
                        graph_data["nodes"] = new_nodes
                        graph_data["edges"] = new_edges
                        st.success("Diagram saved!")
                        st.rerun()

# ---------- Chat Input ----------
if user_input := st.chat_input("Describe your flow..."):
    if not current_session["messages"]:
        current_session["name"] = (user_input[:25] + '...') if len(user_input) > 25 else user_input

    if guardrails_enabled and not is_safe_input(user_input):
        st.error("Input blocked by guardrails.")
    else:
        current_session["messages"].append({"role": "user", "content": user_input})
        # Use current direction in system prompt
        system_prompt = f"""
You are a diagram generator. Output ONLY valid Mermaid flowchart code.
The graph MUST start with 'graph {st.session_state.diag_dir}'.
Do not include any explanations or markdown fences.
Colors: green (fill:#90EE90), red (fill:#FFCCCC).
Ensure node IDs are simple alphanumeric (no spaces, no punctuation).
Edge definitions must be of the form: A --> B or A -->|label| B.
"""
        api_messages = [{"role": "system", "content": system_prompt}] + current_session["messages"]

        with st.spinner("Drawing..."):
            response = call_ollama(api_messages, st.session_state.model_name)
            if response:
                current_session["messages"].append({"role": "assistant", "content": response})
                # Invalidate graph cache for this message (new message)
                st.rerun()