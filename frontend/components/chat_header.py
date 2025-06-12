import streamlit as st

def render_chat_header():
    st.title("💡 LuthaMind AI: Your Private AI Companion")
    st.markdown(f"Welcome back, **{st.session_state.username}**! This application allows you to interact with Large Language Models (LLMs) running entirely on your local machine using Ollama.")
    st.markdown("---")
