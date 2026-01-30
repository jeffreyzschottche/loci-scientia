"""
Embed a PDF file: extract text, chunk it, and generate embeddings.

Usage:
    python embed_pdf.py <pdf_path> [--chunk-size=500] [--overlap=50]

Output:
    JSON array of {"chunk_index": int, "text": str, "vector": list[float]}
"""

import json
import sys
from pathlib import Path
from typing import Generator

import pymupdf  # PyMuPDF (fitz)
from fastembed import TextEmbedding

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"


def extract_text(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    doc = pymupdf.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> Generator[str, None, None]:
    """Split text into overlapping chunks."""
    words = text.split()
    if not words:
        return

    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            yield chunk.strip()
        start += chunk_size - overlap


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python embed_pdf.py <pdf_path>"}))
        sys.exit(1)

    pdf_path = sys.argv[1]
    chunk_size = 500
    overlap = 50

    for arg in sys.argv[2:]:
        if arg.startswith("--chunk-size="):
            chunk_size = int(arg.split("=")[1])
        elif arg.startswith("--overlap="):
            overlap = int(arg.split("=")[1])

    if not Path(pdf_path).exists():
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)

    # Extract text
    text = extract_text(pdf_path)
    if not text.strip():
        print(json.dumps({"error": "No text could be extracted from PDF"}))
        sys.exit(1)

    # Chunk
    chunks = list(chunk_text(text, chunk_size, overlap))
    if not chunks:
        print(json.dumps({"error": "No chunks generated from text"}))
        sys.exit(1)

    # Embed
    embedder = TextEmbedding(MODEL_NAME)
    vectors = list(embedder.embed(chunks))

    # Output
    results = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        results.append({
            "chunk_index": i,
            "text": chunk,
            "vector": vector.tolist(),
        })

    print(json.dumps(results))


if __name__ == "__main__":
    main()
