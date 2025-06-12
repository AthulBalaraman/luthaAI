import streamlit as st
import ollama
import io
import requests
from components.sidebar import render_sidebar

BACKEND_URL = "http://127.0.0.1:8000"

# --- Pagination settings ---
MESSAGES_PER_PAGE = 20

def build_auth_headers():
    token = st.session_state.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

def fetch_user_chats():
    """
    Fetch all chat threads (chat_ids) for the current user from backend.
    If loading fails, return an empty list silently.
    """
    try:
        resp = requests.get(f"{BACKEND_URL}/user_chats", headers=build_auth_headers())
        if resp.status_code == 200:
            return resp.json().get("chats", [])
        else:
            # Do not show error in UI, just return empty
            return []
    except Exception:
        # Do not show error in UI, just return empty
        return []

def fetch_chat_messages(chat_id, page=1, per_page=MESSAGES_PER_PAGE):
    """
    Fetch paginated messages for a chat_id, only if user is authorized.
    """
    try:
        params = {"page": page, "per_page": per_page}
        resp = requests.get(
            f"{BACKEND_URL}/chat/{chat_id}/messages",
            headers=build_auth_headers(),
            params=params
        )
        if resp.status_code == 200:
            return resp.json().get("messages", []), resp.json().get("total_pages", 1)
        elif resp.status_code == 403:
            st.error("You are not authorized to access this chat.")
            return [], 1
        else:
            st.error("Failed to load chat messages.")
            return [], 1
    except Exception as e:
        st.error(f"Error loading messages: {e}")
        return [], 1

def create_new_chat():
    """
    Create a new chat thread for the user via backend.
    If creation fails, do not show an error in the UI—just return None.
    """
    try:
        resp = requests.post(f"{BACKEND_URL}/create_chat", headers=build_auth_headers())
        if resp.status_code == 201:
            return resp.json().get("chat_id")
        else:
            # Do not show error in UI, just return None
            return None
    except Exception:
        # Do not show error in UI, just return None
        return None

def fetch_ollama_models():
    """
    Fetch available Ollama models for selection.
    """
    try:
        import frontend.utils.ollama_utils as ollama_utils
        return ollama_utils.get_ollama_models()
    except Exception:
        return []

def render():
    # --- Ensure user is logged in and has a valid access token ---
    if not st.session_state.get("logged_in") or not st.session_state.get("access_token"):
        st.error("You must be logged in to access chats.")
        st.stop()  # Stop execution if not authenticated

    # --- Always render sidebar first ---
    with st.sidebar:
        render_sidebar()
        # (No extra "Create New Chat" button here)

    # --- Load user's chat threads from backend ---
    user_chats = fetch_user_chats()
    has_chats = bool(user_chats)

    # --- If no chats, try to create one automatically (ChatGPT-like experience) ---
    if not has_chats:
        new_chat_id = create_new_chat()
        if new_chat_id:
            user_chats = [{"chat_id": new_chat_id, "name": "New Chat"}]
            st.session_state.active_chat_id = new_chat_id
            st.session_state.chat_page = 1
            has_chats = True
        else:
            st.title("💡 LuthaMind AI: Your Private AI Companion")
            st.markdown(f"Welcome back, **{st.session_state.username}**! This application allows you to interact with Large Language Models (LLMs) running entirely on your local machine using Ollama.")
            st.markdown("---")
            st.write("Once you create a chat, your conversation will appear here.")
            st.chat_input("Create a chat to start messaging...", disabled=True)
            return

    # --- Select chat_id (thread) ---
    chat_ids = [c["chat_id"] for c in user_chats]
    if "active_chat_id" not in st.session_state or st.session_state.active_chat_id not in chat_ids:
        st.session_state.active_chat_id = chat_ids[0]
        st.session_state.chat_page = 1

    # --- Pagination controls ---
    if "chat_page" not in st.session_state:
        st.session_state.chat_page = 1

    # --- Fetch paginated messages for selected chat ---
    if st.session_state.active_chat_id and st.session_state.active_chat_id in chat_ids:
        messages, total_pages = fetch_chat_messages(st.session_state.active_chat_id, st.session_state.chat_page, MESSAGES_PER_PAGE)
    else:
        messages, total_pages = [], 1

    # --- Model selection (Ollama) ---
    if "ollama_models" not in st.session_state:
        st.session_state.ollama_models = fetch_ollama_models()
    if "selected_model" not in st.session_state or st.session_state.selected_model not in st.session_state.ollama_models:
        st.session_state.selected_model = st.session_state.ollama_models[0] if st.session_state.ollama_models else "llama3"

    st.markdown("#### Model Selection")
    if st.session_state.ollama_models:
        st.session_state.selected_model = st.selectbox(
            "Choose Ollama Model",
            st.session_state.ollama_models,
            index=st.session_state.ollama_models.index(st.session_state.selected_model) if st.session_state.selected_model in st.session_state.ollama_models else 0,
            key="ollama_model_select",
            help="Select the language model to use for this chat."
        )
    else:
        st.warning("No Ollama models found. Please ensure Ollama is running and models are pulled.")

    # --- File Upload Expander (preserved) ---
    if "show_upload_expander" not in st.session_state:
        st.session_state.show_upload_expander = False
    if "file_uploader_key" not in st.session_state:
        st.session_state.file_uploader_key = 0
    if "selected_files" not in st.session_state:
        st.session_state.selected_files = []

    # Upload expander at the top (acts as a modal alternative)
    if st.session_state.get("show_upload_expander") and st.session_state.get("access_token"):
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

    # --- Main Chat Area ---
    st.title("💡 LuthaMind AI: Your Private AI Companion")
    st.markdown(f"Welcome back, **{st.session_state.username}**! This application allows you to interact with Large Language Models (LLMs) running entirely on your local machine using Ollama.")

    # --- Display chat history (paginated) ---
    chat_history = st.session_state.local_chat_history.get(st.session_state.active_chat_id, []) if "local_chat_history" in st.session_state else []
    # Prepare placeholders for streaming assistant message
    chat_placeholders = []
    for idx, message in enumerate(chat_history):
        role = message["role"]
        avatar_emoji = "🤖" if role == "assistant" else "🧑" if role == "user" else None
        with st.chat_message(role, avatar=avatar_emoji):
            # Show a placeholder for the last assistant message if streaming
            if (
                role == "assistant"
                and idx == len(chat_history) - 1
                and message["content"] == ""
            ):
                chat_placeholders.append(st.empty())
                chat_placeholders[-1].markdown("🤖 Thinking...")
            else:
                st.markdown(message["content"])

    # --- Chat input and response generation ---
    col1, col2 = st.columns([10, 1])
    with col1:
        chat_prompt = st.chat_input(
            "What's on your mind?",
            key=f"chat_input_{st.session_state.active_chat_id}_{st.session_state.chat_page}",
            disabled=not (st.session_state.active_chat_id and st.session_state.active_chat_id in chat_ids)
        )
    with col2:
        plus_clicked = st.button("➕", key="plus_upload_btn", help="Attach document(s)")
        if plus_clicked:
            st.session_state.show_upload_expander = True

    # --- Upload files if present when sending a message ---
    if chat_prompt and st.session_state.active_chat_id and st.session_state.active_chat_id in chat_ids:
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

        # Add user message to chat history (local, for streaming)
        if "local_chat_history" not in st.session_state:
            st.session_state.local_chat_history = {}
        if st.session_state.active_chat_id not in st.session_state.local_chat_history:
            st.session_state.local_chat_history[st.session_state.active_chat_id] = []
        st.session_state.local_chat_history[st.session_state.active_chat_id].append({"role": "user", "content": chat_prompt})

        # Prepare messages for ollama (system + history)
        messages_for_ollama = []
        system_prompt = "You are a helpful AI assistant."
        messages_for_ollama.append({"role": "system", "content": system_prompt})
        messages_for_ollama.extend(st.session_state.local_chat_history[st.session_state.active_chat_id])

        # Add a placeholder for the assistant's streaming response
        st.session_state.local_chat_history[st.session_state.active_chat_id].append({"role": "assistant", "content": ""})
        assistant_idx = len(st.session_state.local_chat_history[st.session_state.active_chat_id]) - 1

        # Rerun to show the "Thinking..." placeholder in the chat history (above the input)
        st.rerun()

    # --- Streaming logic (runs after rerun) ---
    # If the last message is an assistant with empty content, stream the response
    if (
        "local_chat_history" in st.session_state
        and st.session_state.active_chat_id in st.session_state.local_chat_history
        and st.session_state.local_chat_history[st.session_state.active_chat_id]
        and st.session_state.local_chat_history[st.session_state.active_chat_id][-1]["role"] == "assistant"
        and st.session_state.local_chat_history[st.session_state.active_chat_id][-1]["content"] == ""
    ):
        messages_for_ollama = []
        system_prompt = "You are a helpful AI assistant."
        messages_for_ollama.append({"role": "system", "content": system_prompt})
        messages_for_ollama.extend(
            st.session_state.local_chat_history[st.session_state.active_chat_id][:-1]
        )
        assistant_idx = len(st.session_state.local_chat_history[st.session_state.active_chat_id]) - 1
        try:
            stream = ollama.chat(
                model=st.session_state.selected_model,
                messages=messages_for_ollama,
                stream=True,
                options={
                    "temperature": 0.7,
                }
            )
            full_response = ""
            # Use the chat_placeholders to stream in the correct place in the chat history
            if len(chat_placeholders) > 0:
                placeholder = chat_placeholders[-1]
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    placeholder = st.empty()
            got_first_chunk = False
            for chunk in stream:
                full_response += chunk['message']['content']
                placeholder.markdown(full_response + "▌")
                got_first_chunk = True
            if not got_first_chunk:
                placeholder.markdown("🤖 Thinking...")
            else:
                placeholder.markdown(full_response)
            st.session_state.local_chat_history[st.session_state.active_chat_id][assistant_idx]["content"] = full_response
            st.rerun()
        except ollama.ResponseError as e:
            error_message = f"Error communicating with Ollama: {e.error}. Please ensure Ollama is running and the model '{st.session_state.selected_model}' is pulled."
            st.session_state.local_chat_history[st.session_state.active_chat_id][assistant_idx]["content"] = error_message
            st.error(error_message)
            st.rerun()
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            st.session_state.local_chat_history[st.session_state.active_chat_id][assistant_idx]["content"] = error_message
            st.error(error_message)
            st.rerun()