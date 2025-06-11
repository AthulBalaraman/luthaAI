import os
import streamlit as st
import ollama
import json # Still needed for other potential JSON operations, but not for the problematic print
import requests # New: For making HTTP requests to FastAPI
from typing import Optional
import io

# --- IMPORTANT: Set Ollama Host Environment Variable ---
# This ensures that the 'ollama' library explicitly connects to the correct local address.
# This should be set BEFORE any 'ollama' related functions are called.
os.environ['OLLAMA_HOST'] = 'http://127.0.0.1:11434'

# --- Backend API Configuration ---
# Configure the URL for your FastAPI backend.
# Ensure this matches where your FastAPI app is running.
BACKEND_URL = "http://127.0.0.1:8000" # Default FastAPI address and port

# --- Configuration and Setup ---
st.set_page_config(page_title="LuthaMind AI", layout="wide")

# --- Helper: Build Authorization Headers ---
def build_auth_headers():
    """
    Returns a dict with the Authorization header using the current access token.
    """
    token = st.session_state.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

# --- Utility Functions ---

@st.cache_data
def get_ollama_models():
    """
    Fetches the list of available Ollama models.
    This function is cached to avoid repeated calls to Ollama on every Streamlit rerun,
    which improves performance.
    """
    try:
        models_info = ollama.list()
        
        # --- Debugging Start ---
        # Changed this line: models_info is a custom object, not directly JSON serializable
        # You can print the object directly for debugging purposes.
        print(f"Raw models_info from ollama.list():\n{models_info}") 
        # If you really need JSON, you might need to convert it to a dict first,
        # e.g., print(f"Raw models_info from ollama.list():\n{json.dumps(models_info.model_dump(), indent=2)}")
        # but for now, direct printing is sufficient to confirm it works.
        # --- Debugging End ---

        model_names = []
        if 'models' in models_info and isinstance(models_info['models'], list):
            for model in models_info['models']:
                if isinstance(model, dict) and 'name' in model: # Check if 'model' is dict (older ollama versions)
                    model_names.append(model['name'])
                elif hasattr(model, 'model') and isinstance(getattr(model, 'model'), str): # Check if 'model' is an object with a 'model' attribute (newer ollama versions)
                    model_names.append(model.model) # Access the attribute directly
                else:
                    # Improved warning for unexpected model format
                    print(f"Warning: Unexpected model format in ollama.list() response: {type(model)} - {model}")
        else:
            print(f"Warning: 'models' key not found or not a list in ollama.list() response: {models_info}")

        return model_names
    except ollama.ResponseError as e:
        st.error(f"Error connecting to Ollama: {e.error}")
        st.warning("Please ensure the Ollama server is running and models are pulled.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_ollama_models: {e}")
        st.error(f"An unexpected error occurred while fetching models: {e}")
        return []

# --- Session State Initialization ---
# Persist access_token in query params for session restoration after refresh

def restore_session_from_query_params():
    # Use st.query_params instead of st.experimental_get_query_params
    token = st.query_params.get("access_token", None)
    if token and not st.session_state.get("access_token"):
        st.session_state.access_token = token
    if st.session_state.get("access_token") and not st.session_state.get("logged_in", False):
        try:
            headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
            resp = requests.get(f"{BACKEND_URL}/current_user", headers=headers)
            if resp.status_code == 200:
                userinfo = resp.json()
                st.session_state.username = userinfo.get("username")
                st.session_state.logged_in = True
            else:
                st.session_state.access_token = None
                st.session_state.logged_in = False
                st.session_state.username = None
                st.query_params.clear()  # Clear token from URL if invalid
        except Exception:
            st.session_state.access_token = None
            st.session_state.logged_in = False
            st.session_state.username = None
            st.query_params.clear()  # Clear token from URL if error

restore_session_from_query_params()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "ollama_models" not in st.session_state:
    st.session_state.ollama_models = get_ollama_models()

if "selected_model" not in st.session_state:
    if st.session_state.ollama_models:
        st.session_state.selected_model = st.session_state.ollama_models[0]
    else:
        st.session_state.selected_model = "llama3" # Fallback if no models found initially

if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7

if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "You are a helpful AI assistant."

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "show_signup" not in st.session_state:
    st.session_state.show_signup = False # To toggle between login and signup forms

# --- Authentication Functions ---

def login_user(username, password):
    """
    Sends login request to FastAPI backend.
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/token",
            data={"username": username, "password": password}
        )
        if response.status_code == 200:
            token_data = response.json()
            st.session_state.access_token = token_data.get("access_token")
            # Save token to query params for persistence
            st.query_params["access_token"] = st.session_state.access_token
            # Fetch user info using the token
            headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
            resp = requests.get(f"{BACKEND_URL}/current_user", headers=headers)
            if resp.status_code == 200:
                userinfo = resp.json()
                st.session_state.username = userinfo.get("username")
                st.session_state.logged_in = True
                st.success(f"Logged in as {st.session_state.username}!")
                st.rerun() # Rerun to show the main chat interface
            else:
                st.error("Login failed: Unable to fetch user info.")
        else:
            st.error(f"Login failed: {response.json().get('detail', 'Unknown error')}")
    except requests.exceptions.ConnectionError:
        st.error(f"Could not connect to backend at {BACKEND_URL}. Please ensure the backend is running.")
    except Exception as e:
        st.error(f"An unexpected error occurred during login: {e}")

def signup_user(username, password, email: Optional[str] = None):
    """
    Sends signup request to FastAPI backend.
    """
    try:
        data = {"username": username, "password": password}
        if email:
            data["email"] = email
        response = requests.post(
            f"{BACKEND_URL}/signup",
            json=data # Use json for signup as UserCreate expects JSON
        )
        if response.status_code == 201: # 201 Created
            token_data = response.json()
            st.session_state.access_token = token_data.get("access_token")
            # Save token to query params for persistence
            st.query_params["access_token"] = st.session_state.access_token
            # Fetch user info using the token
            headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
            resp = requests.get(f"{BACKEND_URL}/current_user", headers=headers)
            if resp.status_code == 200:
                userinfo = resp.json()
                st.session_state.username = userinfo.get("username")
                st.session_state.logged_in = True
                st.success(f"Account created and logged in as {st.session_state.username}!")
                st.rerun() # Rerun to show the main chat interface
            else:
                st.error("Signup failed: Unable to fetch user info.")
        else:
            st.error(f"Signup failed: {response.json().get('detail', 'Unknown error')}")
    except requests.exceptions.ConnectionError:
        st.error(f"Could not connect to backend at {BACKEND_URL}. Please ensure the backend is running.")
    except Exception as e:
        st.error(f"An unexpected error occurred during signup: {e}")

def logout_user():
    """
    Logs out the user by clearing session state.
    """
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.access_token = None
    st.session_state.messages = [] # Clear chat history on logout
    st.query_params.clear()  # Remove token from URL
    st.info("Logged out successfully.")
    # Do NOT call st.rerun() here

# --- Session State Initialization for Tabs ---
if "chat_tabs" not in st.session_state:
    # Each tab: {"id": str, "name": str, "messages": [], "system_prompt": str, "selected_model": str}
    st.session_state.chat_tabs = []
if "active_tab_id" not in st.session_state:
    st.session_state.active_tab_id = None

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

def get_active_tab():
    for tab in st.session_state.chat_tabs:
        if tab["id"] == st.session_state.active_tab_id:
            return tab
    return None

def set_active_tab(tab_id):
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

# Ensure at least one tab exists
if not st.session_state.chat_tabs:
    create_new_tab()

if st.session_state.active_tab_id is None:
    st.session_state.active_tab_id = st.session_state.chat_tabs[0]["id"]

# --- Main Application Logic ---

# Conditional rendering based on login status
if not st.session_state.logged_in:
    st.title("Welcome to LuthaMind AI!")
    st.markdown("Please log in or sign up to continue.")

    # Login / Signup forms
    if st.session_state.show_signup:
        st.subheader("Create a New Account")
        with st.form("signup_form"):
            new_username = st.text_input("Username", key="new_username_input")
            new_password = st.text_input("Password", type="password", key="new_password_input")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password_input")
            new_email = st.text_input("Email (Optional)", key="new_email_input")
            signup_button = st.form_submit_button("Sign Up")

            if signup_button:
                if not new_username or not new_password:
                    st.error("Username and password are required.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    signup_user(new_username, new_password, new_email)
        st.markdown("Already have an account? [Login here](#)")
        if st.button("Login"): # Dummy button to switch view
            st.session_state.show_signup = False
            st.rerun()

    else:
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username_input")
            password = st.text_input("Password", type="password", key="login_password_input")
            login_button = st.form_submit_button("Login")

            if login_button:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    login_user(username, password)
        st.markdown("Don't have an account? [Sign Up here](#)")
        if st.button("Sign Up"): # Dummy button to switch view
            st.session_state.show_signup = True
            st.rerun()

else: # User is logged in, show the chat interface
    st.title("💡 LuthaMind AI: Your Private AI Companion")
    st.markdown(
        f"""
        Welcome back, **{st.session_state.username}**! This application allows you to interact with Large Language Models
        (LLMs) running entirely on your local machine using Ollama.
        """
    )

    # --- Sidebar: Tab Management ---
    with st.sidebar:
        # Inject CSS for flexbox sidebar layout
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] > div:first-child {
                display: flex;
                flex-direction: column;
                height: 100vh;
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
        # Sidebar content container
        with st.container():
            st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
            st.header("Your Chats")
            
            # Model Selection in Sidebar (Moved to top)
            available_models = st.session_state.ollama_models
            active_tab = get_active_tab()
            if available_models and active_tab:
                model_index = available_models.index(active_tab["selected_model"]) if active_tab["selected_model"] in available_models else 0
                selected_model = st.selectbox(
                    "Choose a model",
                    available_models,
                    index=model_index,
                    key=f"model_select_{active_tab['id']}",
                    help="Select the language model to use for this chat."
                )
                if selected_model != active_tab["selected_model"]:
                    active_tab["selected_model"] = selected_model
            elif not available_models:
                st.warning("No Ollama models found. Please ensure Ollama is running and models are pulled.")
            # st.markdown("---")
            if st.button("➕ Create New Chat", key="new_tab_button"):
                create_new_tab()
                st.rerun()
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
            # st.markdown("---")
            
            # Model Selection in Sidebar
            # available_models = st.session_state.ollama_models
            # if available_models:
            #     model_index = available_models.index(tab["selected_model"]) if tab["selected_model"] in available_models else 0
            #     selected_model = st.selectbox(
            #         "Choose a model",
            #         available_models,
            #         index=model_index,
            #         key=f"model_select_{tab['id']}",
            #         help="Select the language model to use for this chat."
            #     )
            #     if selected_model != tab["selected_model"]:
            #         tab["selected_model"] = selected_model
            # else:
            #     st.warning("No Ollama models found. Please ensure Ollama is running and models are pulled.")
            
            st.markdown("---")
            st.markdown('</div>', unsafe_allow_html=True)
        # Logout button fixed at the bottom
        st.markdown('<div class="sidebar-logout">', unsafe_allow_html=True)
        if st.button("Logout"):
            logout_user()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    active_tab = get_active_tab()
    if not active_tab:
        st.warning("No active chat tab found.")
    else:
        # System Persona at the top of chat area
        st.subheader("System Persona")
        persona = st.text_area(
            "Set the AI's persona for this chat:",
            value=active_tab["system_prompt"],  # <-- changed from system_persona
            height=100,
            key=f"system_persona_{active_tab['id']}",
            help="Define the AI's initial instructions or role for this chat.",
            placeholder="e.g., You are a highly sarcastic robot."
        )
        if persona != active_tab["system_prompt"]:  # <-- changed from system_persona
            active_tab["system_prompt"] = persona   # <-- changed from system_persona

        st.markdown("---")

        # --- Document Upload UI (only when logged in) ---
        if st.session_state.get("access_token"):
            with st.expander("📄 Upload Documents", expanded=True):
                uploaded_files = st.file_uploader(
                    "Select one or more files to upload",
                    type=None,  # Accept any file type
                    accept_multiple_files=True,
                    key="doc_upload"
                )
                upload_btn = st.button("Upload", key="upload_docs_btn")
                if upload_btn and uploaded_files:
                    with st.spinner("Uploading files..."):
                        try:
                            files = []
                            for f in uploaded_files:
                                # Read file content as bytes
                                file_bytes = f.read()
                                files.append(
                                    ("files", (f.name, io.BytesIO(file_bytes), f.type or "application/octet-stream"))
                                )
                            # POST to backend
                            resp = requests.post(
                                f"{BACKEND_URL}/upload_document",
                                headers=build_auth_headers(),
                                files=files,
                                timeout=60
                            )
                            if resp.status_code == 200:
                                # You can parse resp.json() for chunk count or similar info
                                # Example: chunk_count = resp.json().get("chunks", len(uploaded_files))
                                st.success(f"Uploaded {len(uploaded_files)} file(s) successfully!")
                                # TODO: Display chunk count or processing progress here in future
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

        st.markdown("---")

        # Chat input
        prompt = st.chat_input("What's on your mind?", key=f"chat_input_{active_tab['id']}")

        # Display chat history
        for message in active_tab["messages"]:
            role = message["role"]
            with st.chat_message(role):
                st.markdown(message["content"])

        # --- Handle Sending Message ---
        if prompt:
            # Add user message first
            active_tab["messages"].append({"role": "user", "content": prompt})

            # Generate assistant response and append after user message
            if not active_tab["selected_model"]:
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    st.error("Cannot generate response: No LLM model is selected or available.")
                active_tab["messages"].append({"role": "assistant", "content": "Cannot generate response: No LLM model is selected or available."})
            else:
                with st.chat_message("user"):
                    st.markdown(prompt)
                # Prepare messages for ollama (including system and all previous messages)
                messages_for_ollama = []
                if active_tab["system_prompt"].strip():
                    messages_for_ollama.append({"role": "system", "content": active_tab["system_prompt"]})
                messages_for_ollama.extend([
                    {"role": m["role"], "content": m["content"]}
                    for m in active_tab["messages"]
                ])
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    full_response = ""
                    try:
                        stream = ollama.chat(
                            model=active_tab["selected_model"],
                            messages=messages_for_ollama,
                            stream=True,
                            options={
                                "temperature": st.session_state.temperature,
                            }
                        )
                        for chunk in stream:
                            full_response += chunk['message']['content']
                            message_placeholder.markdown(full_response + "▌")
                        message_placeholder.markdown(full_response)
                    except ollama.ResponseError as e:
                        error_message = f"Error communicating with Ollama: {e.error}. Please ensure Ollama is running and the model '{active_tab['selected_model']}' is pulled."
                        st.error(error_message)
                        full_response = f"I'm sorry, I encountered an error: {e.error}. Please check the server status and ensure the model is downloaded."
                        message_placeholder.markdown(full_response)
                    except Exception as e:
                        error_message = f"An unexpected error occurred: {e}"
                        st.error(error_message)
                        full_response = "I'm sorry, an unexpected error occurred. Please try again later."
                        message_placeholder.markdown(full_response)
                active_tab["messages"].append({"role": "assistant", "content": full_response})