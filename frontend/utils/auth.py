import streamlit as st
import requests
from typing import Optional
from .session import BACKEND_URL

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
