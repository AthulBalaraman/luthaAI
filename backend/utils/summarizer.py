from transformers import pipeline
from chonkie import SemanticChunker

def get_text_summary(text: str, max_length: int = 5000, min_length: int = 30) -> str:
    try:
        print("Text Length:", len(text))
        def semantic_chunk_and_summarize(text, summarizer, chunk_size=500):
            chunker = SemanticChunker(
                embedding_model="minishlab/potion-base-8M",
                threshold=0.5,
                chunk_size=chunk_size,
                min_sentences=1
            )
            # Chunk the text semantically
            chunks = []
            for doc_chunks in chunker.chunk_batch([text]):
                for chunk in doc_chunks:
                    chunks.append(chunk.text)
            # Summarize each chunk
            summaries = []
            for chunk_text in chunks:
                summary = summarizer(
                    chunk_text,
                    max_length=chunk_size,
                    min_length=30,
                    do_sample=False
                )[0]['summary_text']
                summaries.append(summary)
            # Join summaries
            joined_summary = " ".join(summaries)
            # If the summary is still too long, recursively summarize
            if len(joined_summary) > chunk_size:
                return semantic_chunk_and_summarize(joined_summary, summarizer, chunk_size)
            return joined_summary

        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        print("[DEBUG] Summarizer pipeline initialized successfully")
        if len(text) > 500:
            return semantic_chunk_and_summarize(text, summarizer, chunk_size=500)
        else:
            result = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
            return result[0]['summary_text']
    except Exception as e:
        return f"Error generating summary: {str(e)}"
