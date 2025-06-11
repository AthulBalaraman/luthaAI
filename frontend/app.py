import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import streamlit as st
st.set_page_config(page_title="LuthaMind AI", layout="wide")  # <-- MUST be first Streamlit command

from utils.session import restore_session_from_query_params
from utils.ollama_utils import get_ollama_models
from views.login import render as login_render
from views.signup import render as signup_render
from views.chat import render as chat_render

# --- Session State Initialization ---
if "ollama_models" not in st.session_state:
    st.session_state.ollama_models = get_ollama_models()
if "selected_model" not in st.session_state:
    st.session_state.selected_model = st.session_state.ollama_models[0] if st.session_state.ollama_models else "llama3"
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "You are a helpful AI assistant."
if "messages" not in st.session_state:
    st.session_state.messages = []
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "show_signup" not in st.session_state:
    st.session_state.show_signup = False
if "chat_tabs" not in st.session_state:
    st.session_state.chat_tabs = []
if "active_tab_id" not in st.session_state:
    st.session_state.active_tab_id = None

# Restore session if needed
restore_session_from_query_params()

# Routing logic
if not st.session_state.get("logged_in", False):
    if st.session_state.get("show_signup", False):
        signup_render()
    else:
        login_render()
else:
    chat_render()