import streamlit as st
import ollama
import io
import requests
from utils.session import BACKEND_URL
from typing import Optional

def render_chat():
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

        # --- Chat input with pin icon ---
        chat_input_cols = st.columns([10, 1])
        with chat_input_cols[0]:
            prompt = st.chat_input(
                "What's on your mind?",
                key=f"chat_input_{active_tab['id']}"
            )
        with chat_input_cols[1]:
            pin_key = f"show_upload_section_{active_tab['id']}"
            if pin_key not in st.session_state:
                st.session_state[pin_key] = False
            pin_label = "📌" if st.session_state[pin_key] else "📍"
            if st.button(pin_label, key=f"pin_btn_{active_tab['id']}", help="Toggle upload section"):
                st.session_state[pin_key] = not st.session_state[pin_key]

        # --- Upload section toggled by pin ---
        if st.session_state.get(pin_key, False) and st.session_state.get("access_token"):
            with st.expander("📄 Upload Documents", expanded=True):
                uploaded_files = st.file_uploader(
                    "Select one or more files to upload",
                    type=None,  # Accept any file type
                    accept_multiple_files=True,
                    key=f"doc_upload_{active_tab['id']}"
                )
                upload_btn = st.button("Upload", key=f"upload_docs_btn_{active_tab['id']}")
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

def get_active_tab():
    for tab in st.session_state.chat_tabs:
        if tab["id"] == st.session_state.active_tab_id:
            return tab
    return None

def build_auth_headers():
    """
    Returns a dict with the Authorization header using the current access token.
    """
    token = st.session_state.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}
