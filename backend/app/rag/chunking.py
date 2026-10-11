import re
from typing import List

def clean_text(text: str) -> str:
    """Clean and normalize input text for ingestion and evaluation."""
    if not text:
        return ""
    # Normalize unicode whitespace and line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Replace multiple spaces with a single space while keeping double newlines
    text = re.sub(r'[ \t]+', ' ', text)
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Strip leading and trailing whitespace
    return text.strip()

def chunk_text(text: str, chunk_size: int = 300, chunk_overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks respecting sentence/word boundaries.
    """
    text = clean_text(text)
    if not text:
        return []
    
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    # Split by paragraphs or sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sentence_len = len(sentence)
        
        # If single sentence is greater than chunk_size, split by words
        if sentence_len > chunk_size:
            words = sentence.split(' ')
            sub_chunk = []
            sub_len = 0
            for w in words:
                if sub_len + len(w) + 1 > chunk_size and sub_chunk:
                    chunk_str = " ".join(sub_chunk)
                    chunks.append(chunk_str)
                    # Maintain overlap
                    overlap_words = sub_chunk[-max(1, int(chunk_overlap / 10)):] if chunk_overlap > 0 else []
                    sub_chunk = list(overlap_words)
                    sub_len = sum(len(x) + 1 for x in sub_chunk)
                sub_chunk.append(w)
                sub_len += len(w) + 1
            if sub_chunk:
                chunks.append(" ".join(sub_chunk))
            continue

        if current_length + sentence_len + 1 > chunk_size and current_chunk:
            chunk_str = " ".join(current_chunk)
            chunks.append(chunk_str)
            
            # Prepare overlap for next chunk
            overlap_sentences = []
            overlap_len = 0
            for s in reversed(current_chunk):
                if overlap_len + len(s) + 1 <= chunk_overlap:
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s) + 1
                else:
                    break
            current_chunk = overlap_sentences
            current_length = sum(len(s) + 1 for s in current_chunk)

        current_chunk.append(sentence)
        current_length += sentence_len + 1

    if current_chunk:
        chunk_str = " ".join(current_chunk)
        if not chunks or chunks[-1] != chunk_str:
            chunks.append(chunk_str)

    return chunks
