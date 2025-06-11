import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"

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
