import streamlit as st
import ollama
import io
import requests
from components.sidebar import render_sidebar

BACKEND_URL = "http://127.0.0.1:8000"

def build_auth_headers():
    token = st.session_state.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

def get_active_tab():
    for tab in st.session_state.chat_tabs:
        if tab["id"] == st.session_state.active_tab_id:
            return tab
    return None

def create_new_tab(name=None):
    import uuid
    tab_id = str(uuid.uuid4())
    tab_name = name or f"Chat {len(st.session_state.chat_tabs)+1}"
    tab = {
        "id": tab_id,
        "name": tab_name,
        "messages": [],
        "system_prompt": "You are a helpful AI assistant.",
        "selected_model": st.session_state.ollama_models[0] if st.session_state.ollama_models else "llama3"
    }
    st.session_state.chat_tabs.append(tab)
    st.session_state.active_tab_id = tab_id

def render():
    # --- Ensure at least one tab exists and is active ---
    if "chat_tabs" not in st.session_state:
        st.session_state.chat_tabs = []
    if not st.session_state.chat_tabs:
        create_new_tab()
    if "active_tab_id" not in st.session_state or st.session_state.active_tab_id is None:
        st.session_state.active_tab_id = st.session_state.chat_tabs[0]["id"]

    # --- Ensure session state keys are initialized early ---
    if "show_upload_expander" not in st.session_state:
        st.session_state.show_upload_expander = False
    if "file_uploader_key" not in st.session_state:
        st.session_state.file_uploader_key = 0
    if "selected_files" not in st.session_state:
        st.session_state.selected_files = []

    # --- Render the sidebar ---
    with st.sidebar:
        render_sidebar()

    # --- Main Chat Area ---
    st.title("💡 LuthaMind AI: Your Private AI Companion")
    st.markdown(
        f"""
        Welcome back, **{st.session_state.username}**! This application allows you to interact with Large Language Models
        (LLMs) running entirely on your local machine using Ollama.
        """
    )

    active_tab = get_active_tab()
    if not active_tab:
        st.warning("No active chat tab found.")
        return

    # System Persona at the top of chat area
    st.subheader("System Persona")
    persona = st.text_area(
        "Set the AI's persona for this chat:",
        value=active_tab["system_prompt"],
        height=100,
        key=f"system_persona_{active_tab['id']}",
        help="Define the AI's initial instructions or role for this chat.",
        placeholder="e.g., You are a highly sarcastic robot."
    )
    if persona != active_tab["system_prompt"]:
        active_tab["system_prompt"] = persona

    st.markdown("---")

    # --- Display chat history above the chat input ---
    chat_placeholders = []
    for idx, message in enumerate(active_tab["messages"]):
        role = message["role"]
        avatar_emoji = "🤖" if role == "assistant" else "🧑" if role == "user" else None
        with st.chat_message(role, avatar=avatar_emoji):
            # Show a placeholder for the last assistant message if streaming
            if (
                role == "assistant"
                and idx == len(active_tab["messages"]) - 1
                and message["content"] == ""
                and st.session_state.get("streaming_assistant")
            ):
                # Show "🤖 Thinking..." until streaming starts
                chat_placeholders.append(st.empty())
                chat_placeholders[-1].markdown("🤖 Thinking...")
            else:
                st.markdown(message["content"])

    # --- File Upload Expander at the top (acts as a modal alternative) ---
    if st.session_state.get("show_upload_expander") and st.session_state.get("access_token"):
        # Place the upload expander BEFORE the chat input
        exp_col1, exp_col2 = st.columns([12, 1])
        with exp_col1:
            with st.expander("📄 Upload Documents", expanded=True):
                uploaded_files = st.file_uploader(
                    "Attach file(s)",
                    type=None,
                    accept_multiple_files=True,
                    key=f"doc_upload_expander_{st.session_state.file_uploader_key}"
                )
                if uploaded_files is not None:
                    st.session_state.selected_files = list(uploaded_files)
                if st.session_state.get("selected_files"):
                    unique_files = []
                    seen_names = set()
                    for f in st.session_state.selected_files:
                        if f.name not in seen_names:
                            unique_files.append(f)
                            seen_names.add(f.name)
                    st.session_state.selected_files = unique_files
                    for idx, f in enumerate(st.session_state.selected_files):
                        cols = st.columns([6,1])
                        with cols[0]:
                            st.markdown(f"- {f.name}")
                        with cols[1]:
                            if st.button("✖", key=f"remove_file_expander_{idx}", help="Remove file"):
                                files = list(st.session_state.selected_files)
                                files.pop(idx)
                                st.session_state.selected_files = files
                                st.session_state.file_uploader_key += 1
                                if not files:
                                    st.session_state.selected_files = []
                                st.rerun()
        with exp_col2:
            if st.button("❌", key="close_upload_expander_btn", help="Close file upload"):
                st.session_state.show_upload_expander = False

    # --- Chat input and Plus Button ---
    col1, col2 = st.columns([10, 1])
    with col1:
        prompt = st.chat_input("What's on your mind?", key=f"chat_input_{active_tab['id']}")
    with col2:
        plus_clicked = st.button("➕", key="plus_upload_btn", help="Attach document(s)")
        if plus_clicked:
            st.session_state.show_upload_expander = True

    # --- Upload files if present when sending a message ---
    if prompt:
        # Upload files if any are selected
        if st.session_state.get("selected_files") and st.session_state.get("access_token"):
            with st.spinner("Uploading files..."):
                try:
                    files = []
                    for f in st.session_state.selected_files:
                        file_bytes = f.read()
                        files.append(
                            ("files", (f.name, io.BytesIO(file_bytes), f.type or "application/octet-stream"))
                        )
                    resp = requests.post(
                        f"{BACKEND_URL}/upload_document",
                        headers=build_auth_headers(),
                        files=files,
                        timeout=60
                    )
                    if resp.status_code == 200:
                        st.success(f"Uploaded {len(st.session_state.selected_files)} file(s) successfully!")
                    else:
                        try:
                            err = resp.json().get("detail", resp.text)
                        except Exception:
                            err = resp.text
                        st.error(f"Upload failed: {err}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Network error during upload: {e}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")
            # Clear files and hide uploader after upload
            st.session_state.selected_files = []
            st.session_state.show_upload_expander = False

        # Add user message first
        active_tab["messages"].append({"role": "user", "content": prompt})

        # Generate assistant response and append after user message
        if not active_tab["selected_model"]:
            active_tab["messages"].append({"role": "assistant", "content": "Cannot generate response: No LLM model is selected or available."})
        else:
            # Prepare messages for ollama (including system and all previous messages)
            messages_for_ollama = []
            if active_tab["system_prompt"].strip():
                messages_for_ollama.append({"role": "system", "content": active_tab["system_prompt"]})
            messages_for_ollama.extend([
                {"role": m["role"], "content": m["content"]}
                for m in active_tab["messages"]
            ])
            # Add a placeholder for the assistant's streaming response
            active_tab["messages"].append({"role": "assistant", "content": ""})
            st.session_state.streaming_assistant = True
            # Rerun to show the placeholder
            st.rerun()

    # --- Streaming logic (runs after rerun) ---
    if st.session_state.get("streaming_assistant", False):
        st.session_state.streaming_assistant = False  # Prevent re-entry on rerun
        active_tab = get_active_tab()  # Refresh after rerun
        messages_for_ollama = []
        if active_tab["system_prompt"].strip():
            messages_for_ollama.append({"role": "system", "content": active_tab["system_prompt"]})
        messages_for_ollama.extend([
            {"role": m["role"], "content": m["content"]}
            for m in active_tab["messages"][:-1]  # Exclude the last assistant message (will be filled)
        ])
        try:
            stream = ollama.chat(
                model=active_tab["selected_model"],
                messages=messages_for_ollama,
                stream=True,
                options={
                    "temperature": st.session_state.temperature,
                }
            )
            full_response = ""
            assistant_idx = None
            for idx, message in reversed(list(enumerate(active_tab["messages"]))):
                if message["role"] == "assistant" and message["content"] == "":
                    assistant_idx = idx
                    break
            # Live update the placeholder as chunks arrive
            if assistant_idx is not None:
                # Find the placeholder for the streaming assistant message
                if len(chat_placeholders) > 0:
                    placeholder = chat_placeholders[-1]
                else:
                    placeholder = st.empty()
                got_first_chunk = False
                for chunk in stream:
                    full_response += chunk['message']['content']
                    if not got_first_chunk:
                        got_first_chunk = True
                    placeholder.markdown(full_response + "▌")
                if not got_first_chunk:
                    # If no data was streamed, keep "Thinking..."
                    placeholder.markdown("🤖 Thinking...")
                else:
                    # Finalize the response
                    placeholder.markdown(full_response)
                active_tab["messages"][assistant_idx]["content"] = full_response
            st.session_state.streaming_assistant = False
            st.rerun()
        except ollama.ResponseError as e:
            error_message = f"Error communicating with Ollama: {e.error}. Please ensure Ollama is running and the model '{active_tab['selected_model']}' is pulled."
            if assistant_idx is not None:
                active_tab["messages"][assistant_idx]["content"] = error_message
            st.session_state.streaming_assistant = False
            st.rerun()
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            if assistant_idx is not None:
                active_tab["messages"][assistant_idx]["content"] = error_message
            st.session_state.streaming_assistant = False
            st.rerun()

    # --- Force scroll to top of the page after rerun ---
    st.markdown(
        """
        <script>
        window.parent.document.querySelector('section.main').scrollTo({top: 0, behavior: 'auto'});
        </script>
        """,
        unsafe_allow_html=True,
    )