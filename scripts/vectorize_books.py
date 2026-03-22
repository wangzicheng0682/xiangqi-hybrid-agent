#!/usr/bin/env python3
"""
Vectorize Chess Books for RAG Retrieval (Sprint 2.1)

This script:
1. Reads PDF chess books from data/books/
2. Splits text into chunks
3. Generates embeddings using BGE-M3
4. Builds FAISS index for fast retrieval
5. Saves index and metadata to data/vector_db/

Usage:
    python scripts/vectorize_books.py
    python scripts/vectorize_books.py --books-dir data/books --output-dir data/vector_db
"""

import os
import sys
from pathlib import Path
import argparse
import json
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_args():
    parser = argparse.ArgumentParser(description="Vectorize chess books for RAG")
    parser.add_argument(
        "--books-dir",
        type=str,
        default="data/books",
        help="Directory containing PDF books",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/vector_db",
        help="Output directory for FAISS index",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Characters per chunk",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=50,
        help="Overlap between chunks",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="BAAI/bge-m3",
        help="Embedding model name",
    )
    return parser.parse_args()


def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text from PDF file.

    Returns:
        List of dicts with keys: 'page', 'text'
    """
    # TODO: Implement PDF extraction (Sprint 2.1)
    # Options: PyPDF2, pdfplumber, pdfminer

    print(f"  [MOCK] Would extract text from {pdf_path}")

    # Return mock data for now
    return [
        {"page": 1, "text": "当头炮势如破竹，开局首选。"},
        {"page": 2, "text": "屏风马稳健防守，适合持久战。"},
    ]


def chunk_text(
    pages: List[Dict[str, Any]],
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks.

    Returns:
        List of dicts with keys: 'book_name', 'page', 'chunk_id', 'text'
    """
    # TODO: Implement chunking logic (Sprint 2.1)

    print("  [MOCK] Would chunk text into pieces")

    # Return mock chunks
    return [
        {
            "book_name": "橘中秘",
            "page": 1,
            "chunk_id": 0,
            "text": "当头炮势如破竹，开局首选。",
        },
        {
            "book_name": "橘中秘",
            "page": 2,
            "chunk_id": 1,
            "text": "屏风马稳健防守，适合持久战。",
        },
    ]


def create_embeddings(
    chunks: List[Dict[str, Any]],
    model_name: str = "BAAI/bge-m3"
) -> List[Dict[str, Any]]:
    """
    Generate embeddings for text chunks.

    Returns:
        List of dicts with keys: 'book_name', 'page', 'text', 'embedding'
    """
    # TODO: Implement embedding generation (Sprint 2.1)
    # Use sentence-transformers library

    print(f"  [MOCK] Would generate embeddings using {model_name}")

    # Return mock embeddings
    import random
    return [
        {
            "book_name": chunk["book_name"],
            "page": chunk["page"],
            "text": chunk["text"],
            "embedding": [random.random() for _ in range(1024)],  # Mock embedding
        }
        for chunk in chunks
    ]


def build_faiss_index(
    embeddings: List[Dict[str, Any]],
    output_dir: str
):
    """
    Build FAISS index from embeddings.

    Saves:
        - books.index: FAISS index file
        - books.meta: Metadata (book names, pages, texts)
    """
    # TODO: Implement FAISS index building (Sprint 2.1)

    print(f"  [MOCK] Would build FAISS index in {output_dir}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Save mock metadata
    metadata = {
        "model": "BAAI/bge-m3",
        "dimension": 1024,
        "num_chunks": len(embeddings),
        "chunks": [
            {
                "book_name": e["book_name"],
                "page": e["page"],
                "text": e["text"],
            }
            for e in embeddings
        ],
    }

    with open(f"{output_dir}/books.meta", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"  [MOCK] Saved metadata to {output_dir}/books.meta")


def main():
    args = parse_args()

    print("=" * 60)
    print("Chess Book Vectorization (Sprint 2.1)")
    print("=" * 60)
    print()

    # Check if books directory exists
    books_dir = Path(args.books_dir)
    if not books_dir.exists():
        print(f"Error: Books directory not found: {books_dir}")
        print("Please create the directory and add PDF files.")
        sys.exit(1)

    # Find all PDF files
    pdf_files = list(books_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"Warning: No PDF files found in {books_dir}")
        print("Note: This script is a skeleton for Sprint 2.1")
        print("      Add PDF files to continue")

    print(f"Found {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    print()

    # Process each book
    all_chunks = []

    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")

        # Extract text
        pages = extract_text_from_pdf(str(pdf_path))

        # Chunk text
        chunks = chunk_text(
            pages,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap
        )

        all_chunks.extend(chunks)

    print(f"\nTotal chunks: {len(all_chunks)}")

    # Generate embeddings
    print("\nGenerating embeddings...")
    embeddings = create_embeddings(all_chunks, model_name=args.model)

    # Build FAISS index
    print("\nBuilding FAISS index...")
    build_faiss_index(embeddings, args.output_dir)

    print("\n" + "=" * 60)
    print("Vectorization Complete!")
    print("=" * 60)
    print(f"\nIndex saved to: {args.output_dir}")
    print(f"  - books.index (FAISS index)")
    print(f"  - books.meta (metadata)")
    print("\nYou can now use MockRAG or implement real RAG retrieval.")


if __name__ == "__main__":
    main()
