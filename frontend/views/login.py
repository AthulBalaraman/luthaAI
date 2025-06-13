import streamlit as st
import requests
import json

BACKEND_URL = "http://127.0.0.1:8000"

def render():
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
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                print(f"[DEBUG] Login response status: {response.status_code}")
                
                if response.status_code == 200:
                    token_data = response.json()
                    st.session_state.access_token = token_data["access_token"]
                    st.session_state.logged_in = True
                    print("[DEBUG] Login successful")
                    st.success("Login successful!")
                    st.rerun()
                else:
                    print(f"[DEBUG] Login failed: {response.text}")
                    st.error("Login failed. Please check your credentials.")
                    
            except Exception as e:
                print(f"[DEBUG] Login error: {str(e)}")
                st.error(f"An error occurred: {str(e)}")

    # Signup redirect
    if st.button("Create an account"):
        st.session_state.show_signup = True
        st.experimental_rerun()