import streamlit as st
from utils.auth import login_user

def render():
    # --- Login Page UI ---
    st.title("Welcome to LuthaMind AI")
    st.write("Please log in to continue.")

    # Username and password fields
    username = st.text_input("Username", "")
    password = st.text_input("Password", "", type="password")

    # Login button
    if st.button("Log In"):
        if login_user(username, password):
            st.success("Logged in successfully!")
            st.session_state.logged_in = True
            st.session_state.username = username
            st.experimental_rerun()
        else:
            st.error("Invalid username or password. Please try again.")

    # Signup redirect
    if st.button("Create an account"):
        st.session_state.show_signup = True
        st.experimental_rerun()