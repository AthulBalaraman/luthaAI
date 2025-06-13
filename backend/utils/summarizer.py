from transformers import pipeline

def get_text_summary(text: str, max_length: int = 5000, min_length: int = 30) -> str:
    try:
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        print("[DEBUG] Summarizer pipeline initialized successfully")
        result = summarizer(text[:3000], max_length=max_length, min_length=min_length, do_sample=False)
        return result[0]['summary_text']
    except Exception as e:
        return f"Error generating summary: {str(e)}"
