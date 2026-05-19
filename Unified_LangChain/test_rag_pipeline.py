"""
Test script for RAG pipeline with web extraction.

This script:
1. Extracts content from a list of URLs using web_extract
2. Loads documents using RAGManager
3. Splits documents into chunks
4. Prints all splits with URL and content separation
"""

import os
import sys

# Add project root to path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from web_extract import WebExtract
from rag import RAGManager


# URLs to extract content from
URLS = [
    "https://ricetta.it/polpo-alla-luciana",
    "https://spadellandia.it/secondi/pesce/polpo-alla-luciana/",
    "https://www.cookist.it/polpo-alla-luciana-la-ricetta/",
    "https://ricette.giallozafferano.it/Polpo-alla-Luciana.html",
    "https://www.martinarosa.it/en/polpo-alla-luciana-the-octopus-taste-in-seafood-cuisine/",
]


def main():
    """Main test function."""
    print("=" * 60)
    print("TEST RAG PIPELINE - WEB EXTRACTION")
    print("=" * 60)
    
    # Step 1: Extract content from URLs
    print("\n>>> Step 1: Extracting content from URLs...")
    extractor = WebExtract()
    extracted_results = extractor.extract(
        urls=URLS,
        extract_depth="advanced",
        chunks_per_source=3,
        format_text="markdown"
    )
    
    print(f"Extracted result type: {type(extracted_results)}")
    print(f"Extracted result preview: {str(extracted_results)[:500]}...")
    
    # Extract results from the dict
    if isinstance(extracted_results, dict):
        extracted_results = extracted_results.get("results", [])
    
    print(f"Extracted {len(extracted_results)} result(s)")
    
    # Step 2: Load documents
    print("\n>>> Step 2: Loading documents...")
    manager = RAGManager(collection_name="test_polpo_luciana")
    docs = manager.load_documents(extracted_results)
    print(f"Loaded {len(docs)} document(s)")
    
    # Step 3: Split documents
    print("\n>>> Step 3: Splitting documents...")
    splits = manager.split_documents(docs)
    print(f"Created {len(splits)} split(s)")
    
    # Step 4: Print all splits
    print("\n" + "=" * 60)
    print("ALL SPLITS")
    print("=" * 60)
    
    current_url = None
    for i, split in enumerate(splits):
        url = split.metadata.get("url", "unknown")
        content = split.page_content
        
        # Add spacing between different URLs (5 lines)
        if current_url is not None and url != current_url:
            print("\n\n\n\n\n")  # 5 newlines
        
        current_url = url
        
        print(f"\n--- Split {i + 1} ---")
        #print(f"URL: {url}")
        print(f"\n{content}")
    
    print("\n" + "=" * 60)
    print(f"Total splits: {len(splits)}")
    print("=" * 60)


if __name__ == "__main__":
    main()