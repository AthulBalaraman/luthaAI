import streamlit as st
from utils.auth import logout_user
from utils.ollama_utils import get_ollama_models
import requests

def delete_chat_backend(chat_id):
    # Changed import to relative to avoid ModuleNotFoundError
    from views.chat import build_auth_headers
    BACKEND_URL = "http://127.0.0.1:8000"
    try:
        resp = requests.delete(
            f"{BACKEND_URL}/chat/{chat_id}/delete",
            headers=build_auth_headers()
        )
        return resp.status_code == 204
    except Exception:
        return False

def render_sidebar(user_chats=None):
    # Inject CSS for flexbox sidebar layout and hide Streamlit's default sidebar header
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] > div:first-child {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        /* Hide the default Streamlit sidebar header to remove extra space */
        [data-testid="stSidebarHeader"] {
            display: none;
            height: 0;
            margin: 0;
            padding: 0;
        }
        .sidebar-logo {
            margin-top: 0;
            margin-bottom: 0;
            margin-left: 0;
            margin-right: 0;
            display: flex;
            align-items: center;
            justify-content: flex-start;
        }
        .sidebar-content {
            flex: 1 1 auto;
        }
        .sidebar-logout {
            margin-top: auto;
            padding-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Logo at the top left
    with st.container():
        st.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
        st.image("assets/logo1.png", width=250)
        st.markdown('</div>', unsafe_allow_html=True)
    # Sidebar content container
    with st.container():
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.header("Your Chats")
        
        # --- Model Selection ---
        st.markdown("### Model")
        if "ollama_models" in st.session_state and st.session_state.ollama_models:
            st.session_state.selected_model = st.selectbox(
                "Choose Model",
                st.session_state.ollama_models,
                index=st.session_state.ollama_models.index(st.session_state.selected_model) 
                if st.session_state.selected_model in st.session_state.ollama_models else 0
            )
        
        st.markdown("---")
        st.markdown("### Chat Actions")
        
        # New Chat button
        if st.button("➕ New Chat"):
            # Don't clear existing chat until new one is created
            st.session_state.create_new_chat = True
            st.rerun()
        
        # Only show chat list if we have chats
        if user_chats:
            st.markdown("### Recent Chats")
            for chat in user_chats:
                chat_cols = st.columns([8, 1], gap="small")
                with chat_cols[0]:
                    if st.button(
                        f"💭 {chat['name']}",
                        key=f"chat_{chat['chat_id']}",
                        use_container_width=True,
                    ):
                        st.session_state.active_chat_id = chat['chat_id']
                        st.session_state.chat_page = 1
                        st.rerun()
                with chat_cols[1]:
                    if st.button("🗑️", key=f"delete_chat_{chat['chat_id']}", help="Delete chat", use_container_width=True):
                        if delete_chat_backend(chat['chat_id']):
                            # Remove from session state if active
                            if st.session_state.get("active_chat_id") == chat['chat_id']:
                                # Try to select another chat if available
                                remaining_chats = [c for c in user_chats if c["chat_id"] != chat["chat_id"]]
                                if remaining_chats:
                                    st.session_state.active_chat_id = remaining_chats[0]["chat_id"]
                                else:
                                    st.session_state.active_chat_id = None
                            st.rerun()
                        else:
                            st.error("Failed to delete chat.")
        
        for tab in st.session_state.chat_tabs:
            is_active = (tab["id"] == st.session_state.active_tab_id)
            tab_cols = st.columns([7, 1, 1], gap="small")
            with tab_cols[0]:
                tab_button = st.button(
                    f"🗨️ {tab['name'][:20]}{'...' if len(tab['name'])>20 else ''}",
                    key=f"tab_{tab['id']}",
                    help=tab['name'],
                    use_container_width=True
                )
                if tab_button:
                    set_active_tab(tab["id"])
                    st.rerun()
            with tab_cols[1]:
                if st.button("✏️", key=f"rename_btn_{tab['id']}", help="Rename chat", use_container_width=True):
                    st.session_state[f"renaming_{tab['id']}"] = True
            with tab_cols[2]:
                if st.button("🗑️", key=f"delete_btn_{tab['id']}", help="Delete chat", use_container_width=True):
                    st.session_state.chat_tabs = [t for t in st.session_state.chat_tabs if t["id"] != tab["id"]]
                    if st.session_state.active_tab_id == tab["id"]:
                        if st.session_state.chat_tabs:
                            st.session_state.active_tab_id = st.session_state.chat_tabs[0]["id"]
                        else:
                            create_new_tab()
                    st.rerun()
            if st.session_state.get(f"renaming_{tab['id']}", False):
                new_name = st.text_input(
                    "Rename Tab",
                    value=tab["name"],
                    key=f"rename_input_{tab['id']}",
                    label_visibility="collapsed",
                    placeholder="Tab name"
                )
                if st.button("Save", key=f"save_rename_{tab['id']}"):
                    rename_tab(tab["id"], new_name)
                    st.session_state[f"renaming_{tab['id']}"] = False
                    st.rerun()
                if st.button("Cancel", key=f"cancel_rename_{tab['id']}"):
                    st.session_state[f"renaming_{tab['id']}"] = False
                    st.rerun()
        
        st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)
    # Logout button fixed at the bottom
    st.markdown('<div class="sidebar-logout">', unsafe_allow_html=True)
    if st.button("Logout"):
        logout_user()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def get_active_tab():
    for tab in st.session_state.chat_tabs:
        if tab["id"] == st.session_state.active_tab_id:
            return tab
    return None

def set_active_tab(tab_id):
    st.session_state.active_tab_id = tab_id

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

def rename_tab(tab_id, new_name):
    for tab in st.session_state.chat_tabs:
        if tab["id"] == tab_id:
            tab["name"] = new_name
            break

def clear_tab(tab_id):
    for tab in st.session_state.chat_tabs:
        if tab["id"] == tab_id:
            tab["messages"] = []
            break
