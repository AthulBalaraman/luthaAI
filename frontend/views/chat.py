import streamlit as st
import ollama
import io
import requests
from components.sidebar import render_sidebar
from components.chat_header import render_chat_header

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
    """Create a new chat thread."""
    try:
        resp = requests.post(f"{BACKEND_URL}/create_chat", headers=build_auth_headers())
        if resp.status_code == 201:
            chat_id = resp.json().get("chat_id")
            # Initialize empty history for new chat but don't clear others
            if "local_chat_history" not in st.session_state:
                st.session_state.local_chat_history = {}
            st.session_state.local_chat_history[chat_id] = []
            return chat_id
        return None
    except Exception as e:
        print(f"[ERROR] Failed to create chat: {e}")
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

def save_user_message(chat_id, content):
    """Save user message to backend immediately when sent."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/chat/{chat_id}/send_message",
            headers=build_auth_headers(),
            json={"content": content, "role": "user"}
        )
        return resp.status_code == 201
    except Exception:
        return False

def render():
    # --- Ensure user is logged in ---
    if not st.session_state.get("logged_in") or not st.session_state.get("access_token"):
        st.error("You must be logged in to access chats.")
        st.stop()

    # --- Load user's chat threads from backend first ---
    user_chats = fetch_user_chats()
    has_chats = bool(user_chats)

    # --- Now render sidebar with loaded chats ---
    with st.sidebar:
        render_sidebar(user_chats)

    # --- Render chat header ---
    render_chat_header()

    # --- Handle new chat creation ---
    if st.session_state.get("create_new_chat"):
        new_chat_id = create_new_chat()
        if new_chat_id:
            # Add new chat to existing chats list
            user_chats.append({"chat_id": new_chat_id, "name": "New Chat"})
            st.session_state.active_chat_id = new_chat_id
            st.session_state.chat_page = 1
            st.session_state.create_new_chat = False
            st.session_state.local_chat_history = {new_chat_id: []}
            st.rerun()

    # --- Select chat_id (thread) ---
    chat_ids = [c["chat_id"] for c in user_chats]
    if not chat_ids:
        st.session_state.active_chat_id = None
        st.session_state.chat_page = 1
        st.info("No chats available. Create a new chat to get started.")
        return  # Stop rendering further
    if "active_chat_id" not in st.session_state or st.session_state.active_chat_id not in chat_ids:
        st.session_state.active_chat_id = chat_ids[0]
        st.session_state.chat_page = 1

    # --- Pagination controls ---
    if "chat_page" not in st.session_state:
        st.session_state.chat_page = 1

    # --- Fetch paginated messages for selected chat ---
    if st.session_state.active_chat_id and st.session_state.active_chat_id in chat_ids:
        messages, total_pages = fetch_chat_messages(
            st.session_state.active_chat_id,
            st.session_state.chat_page,
            MESSAGES_PER_PAGE,
        )
    else:
        messages, total_pages = [], 1

    # --- Ensure chat history is initialized from backend messages on first load or after refresh ---
    if "local_chat_history" not in st.session_state:
        st.session_state.local_chat_history = {}

    # Only sync local_chat_history with backend messages if:
    # - The chat_id is not in local_chat_history
    # - OR the local_chat_history for this chat is empty (e.g., after refresh)
    # - AND only if this is not a newly created chat (which should be empty)
    if (
        st.session_state.active_chat_id not in st.session_state.local_chat_history
        or (
            not st.session_state.local_chat_history[st.session_state.active_chat_id]
            and messages  # Only sync if there are messages in backend
        )
    ):
        st.session_state.local_chat_history[st.session_state.active_chat_id] = [
            {"role": m["role"], "content": m["content"]} for m in messages
        ]

    chat_history = st.session_state.local_chat_history.get(st.session_state.active_chat_id, [])
    chat_placeholders = []
    for idx, message in enumerate(chat_history):
        role = message["role"]
        avatar_emoji = "🤖" if role == "assistant" else "🧑" if role == "user" else None
        with st.chat_message(role, avatar=avatar_emoji):
            if (
                role == "assistant"
                and idx == len(chat_history) - 1
                and message["content"] == ""
            ):
                chat_placeholders.append(st.empty())
                chat_placeholders[-1].markdown("🤖 Thinking...")
            else:
                st.markdown(message["content"])

    # --- Chat input first ---
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

    if st.session_state.get("show_upload_expander"):
        with st.expander("Upload Documents"):
            uploaded_files = st.file_uploader("Choose a file", accept_multiple_files=True)
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    print(f"Uploaded file: {uploaded_file.name}")

    # --- Handle message sending and streaming ---
    if chat_prompt and st.session_state.active_chat_id and st.session_state.active_chat_id in chat_ids:
        # Save user message to backend immediately
        if save_user_message(st.session_state.active_chat_id, chat_prompt):
            # Add to local history only after successful backend save
            if "local_chat_history" not in st.session_state:
                st.session_state.local_chat_history = {}
            if st.session_state.active_chat_id not in st.session_state.local_chat_history:
                st.session_state.local_chat_history[st.session_state.active_chat_id] = []
            st.session_state.local_chat_history[st.session_state.active_chat_id].append({
                "role": "user", 
                "content": chat_prompt
            })

            # Prepare for assistant response
            messages_for_ollama = []
            system_prompt = "You are a helpful AI assistant."
            messages_for_ollama.append({"role": "system", "content": system_prompt})
            messages_for_ollama.extend(st.session_state.local_chat_history[st.session_state.active_chat_id])

            # Add placeholder for assistant response
            st.session_state.local_chat_history[st.session_state.active_chat_id].append({
                "role": "assistant", 
                "content": ""
            })
            # Refresh to update sidebar chat names
            st.rerun()
        else:
            st.error("Failed to save message. Please try again.")

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
            save_assistant_message(st.session_state.active_chat_id, full_response)
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

def save_assistant_message(chat_id, content):
    try:
        resp = requests.post(
            f"{BACKEND_URL}/chat/{chat_id}/send_message",
            headers=build_auth_headers(),
            json={"content": content, "role": "assistant"}
        )
        return resp.status_code == 201
    except Exception:
        return False
