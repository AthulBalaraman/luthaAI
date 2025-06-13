import streamlit as st
import requests
import json
from requests.exceptions import ConnectionError

BACKEND_URL = "http://127.0.0.1:8000"

def restore_login_from_query_params():
    # Restore access_token from query params if present and not in session_state
    if "access_token" not in st.session_state:
        token = st.query_params.get("access_token")
        if token:
            st.session_state.access_token = token
            st.session_state.logged_in = True
    # If access_token is present, ensure logged_in is set
    if st.session_state.get("access_token"):
        st.session_state.logged_in = True

def render():
    # Restore login state from query params if needed
    restore_login_from_query_params()

    # --- Login Page UI ---
    st.title("Welcome to LuthaMind AI")
    st.write("Please log in to continue.")

    with st.form("login_form"):
        # Username and password fields
        username = st.text_input("Username", "")
        password = st.text_input("Password", "", type="password")

        # Login button
        submitted = st.form_submit_button("Log In")
        
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
                return

            try:
                # Create form data
                data = {
                    "username": username,
                    "password": password
                }
                
                print(f"[DEBUG] Attempting login for user: {username}")
                
                # Make login request
                response = requests.post(
                    f"{BACKEND_URL}/token",
                    data=data,  # Use data instead of json for form submission
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10  # Add timeout
                )
                
                print(f"[DEBUG] Login response status: {response.status_code}")
                print(f"[DEBUG] Response content: {response.text}")
                
                if response.status_code == 200:
                    token_data = response.json()
                    st.session_state.access_token = token_data["access_token"]
                    st.session_state.logged_in = True 
                    # Persist token in query params for refresh persistence
                    st.query_params["access_token"] = st.session_state.access_token
                    print("[DEBUG] Login successful")
                    st.success("Login successful!")
                    st.rerun()
                elif response.status_code == 401:
                    st.error("Invalid username or password")
                elif response.status_code == 422:
                    st.error("Invalid input format")
                else:
                    st.error(f"Login failed (Status {response.status_code}). Please try again.")
                    
            except ConnectionError:
                print("[DEBUG] Connection error - backend server may be down")
                st.error("Cannot connect to server. Please check if the backend server is running.")
            except requests.Timeout:
                print("[DEBUG] Request timed out")
                st.error("Request timed out. Please try again.")
            except Exception as e:
                print(f"[DEBUG] Login error: {str(e)}")
                st.error("An unexpected error occurred. Please try again later.")

    # Signup redirect
    if st.button("Create an account"):
        st.session_state.show_signup = True
        st.experimental_rerun()