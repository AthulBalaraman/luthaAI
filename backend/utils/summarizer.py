from transformers import pipeline
from chonkie import SemanticChunker

def get_text_summary(text: str, max_length: int = 5000, min_length: int = 30) -> str:
    try:
        print("Original Text Length:", len(text))
        
        # Initialize the summarizer once
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        print("[DEBUG] Summarizer pipeline initialized successfully")
        
        # For short texts, summarize directly
        if len(text) <= 500:
            result = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
            return result[0]['summary_text']
        
        # For longer texts, use semantic chunking and recursive summarization
        return semantic_chunk_and_summarize(text, summarizer)
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def semantic_chunk_and_summarize(text, summarizer, chunk_size=500, max_length=5000, min_length=30):
    print(f"[DEBUG] Processing text of length {len(text)} with chunk size {chunk_size}")
    
    # If text is short enough, summarize directly
    if len(text) <= chunk_size:
        result = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
        return result[0]['summary_text']
    
    # Create semantic chunker
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
    
    print(f"[DEBUG] Text split into {len(chunks)} semantic chunks")
    
    # Summarize each chunk
    summaries = []
    for i, chunk_text in enumerate(chunks):
        print(f"[DEBUG] Summarizing chunk {i+1}/{len(chunks)}, length: {len(chunk_text)}")
        summary = summarizer(
            chunk_text,
            max_length=chunk_size,
            min_length=min_length,
            do_sample=False
        )[0]['summary_text']
        summaries.append(summary)
    
    # Join all chunk summaries
    combined_summary = " ".join(summaries)
    print(combined_summary)
    print(f"[DEBUG] Combined summary length: {len(combined_summary)}")
    
    # # If the combined summary is still too long, recursively summarize it
    # if len(combined_summary) > chunk_size:
    #     print("[DEBUG] Combined summary still too long, recursively summarizing...")
    #     return semantic_chunk_and_summarize(combined_summary, summarizer, chunk_size, max_length, min_length)
    
    print("[DEBUG] Final summary created")
    return combined_summary
