import streamlit as st
from utils.auth import signup_user

def render():
    # --- Signup Page ---
    st.title("Create an Account")
    st.write("Join LuthaMind AI to start chatting with your AI assistant.")

    # Username and Password fields
    username = st.text_input("Username", max_chars=20)
    password = st.text_input("Password", type="password", max_chars=20)

    # Signup button
    if st.button("Sign Up"):
        if signup_user(username, password):
            st.success("Account created successfully! You can now log in.")
        else:
            st.error("Username already taken or invalid. Please choose another one.")

    # Switch to login link
    if st.button("Already have an account? Log in here."):
        st.session_state.show_signup = False
        st.experimental_rerun()