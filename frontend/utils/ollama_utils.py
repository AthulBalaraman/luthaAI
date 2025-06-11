import streamlit as st
import ollama
import json

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
