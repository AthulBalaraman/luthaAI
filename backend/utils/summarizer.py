from transformers import pipeline

def get_text_summary(text: str, max_length: int = 130, min_length: int = 30) -> str:
    try:
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        result = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
        return result[0]['summary_text']
    except Exception as e:
        return f"Error generating summary: {str(e)}"
