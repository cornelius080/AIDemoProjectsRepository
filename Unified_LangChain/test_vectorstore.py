"""
Test script for RAG pipeline with vector store.

This script:
1. Loads simulated extracted content from web pages
2. Runs the RAG pipeline (loading, splitting, adding to vector store)
3. Clears the vector store
4. Runs the RAG pipeline again with new content
5. Allows inspection of the vector store contents
"""

import os
import sys

# Add project root to path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from dotenv import load_dotenv

# Load environment variables
ENV_FILE = os.path.join(PROJECT_DIR, "apy_keys.env")
load_dotenv(ENV_FILE)

from rag import RAGManager


# Simulated extracted content (as would come from web_extract tool)
SIMULATED_CONTENT_1 = {
    "url": "https://example.com/python-guide",
    "title": "Python Programming Guide",
    "raw_content": """
## Introduction to Python

Python is a high-level, interpreted programming language known for its simplicity and readability.

### Key Features

- Easy to learn and read
- Versatile (web, data science, AI, automation)
- Large ecosystem of libraries
- Cross-platform compatibility

### Getting Started

To start with Python, you need to install it from the official website or use a distribution like Anaconda.

## Variables and Data Types

Python supports various data types including strings, integers, floats, booleans, lists, tuples, and dictionaries.

### Example Code

```python
name = "Alice"
age = 30
is_student = False
grades = [85, 90, 78]
person = {"name": "Alice", "age": 30}
```

## Functions

Functions in Python are defined using the def keyword.

### Example

```python
def greet(name):
    return f"Hello, {name}!"

result = greet("World")
```
"""
}

SIMULATED_CONTENT_2 = {
    "url": "https://example.com/javascript-guide",
    "title": "JavaScript Programming Guide",
    "raw_content": """
## Introduction to JavaScript

JavaScript is a versatile programming language primarily used for web development.

### Key Features

- Client-side scripting
- Event-driven programming
- Dynamic content manipulation
- Large ecosystem (Node.js, frameworks)

### Getting Started

JavaScript can be run in browsers or using Node.js on the server.

## Variables and Data Types

JavaScript has let, const, and var for variable declarations.

### Example Code

```javascript
let name = "Alice";
const age = 30;
let isStudent = false;
let grades = [85, 90, 78];
let person = {name: "Alice", age: 30};
```

## Functions

Functions in JavaScript can be defined using function keyword or arrow syntax.

### Example

```javascript
function greet(name) {
    return `Hello, ${name}!`;
}

const greetArrow = (name) => `Hello, ${name}!`;
```
"""
}


def print_vector_store_contents(manager: RAGManager, label: str = "Current"):
    """Print the contents of the vector store for inspection."""
    print(f"\n{'='*60}")
    print(f"VECTOR STORE CONTENTS - {label}")
    print(f"{'='*60}")
    
    # Get collection to inspect
    collection = manager.vector_store.get()
    
    print(f"Total documents in store: {len(collection['ids'])}")
    print(f"Collection name: {manager.collection_name}")
    print(f"\nDocuments:")
    
    for i, (doc_id, doc) in enumerate(zip(collection['ids'], collection['documents'])):
        print(f"\n--- Document {i+1} ---")
        print(f"ID: {doc_id}")
        print(f"Content preview: {doc[:200]}..." if len(doc) > 200 else f"Content: {doc}")
        print(f"Metadata: {collection['metadatas'][i]}")
    
    print(f"\n{'='*60}\n")


def run_rag_pipeline(manager: RAGManager, content: dict, label: str):
    """Run the full RAG pipeline: load, split, add."""
    print(f"\n>>> Running RAG pipeline for: {content.get('title', 'Unknown')}")
    
    # Step 1: Load documents
    print("  1. Loading documents...")
    docs = manager.load_documents([content])
    print(f"      Loaded {len(docs)} document(s)")
    
    # Step 2: Split documents
    print("  2. Splitting documents...")
    splits = manager.split_documents(docs)
    print(f"      Created {len(splits)} chunk(s)")
    
    # Step 3: Add to vector store
    print("  3. Adding to vector store...")
    manager.add_documents(splits)
    print(f"      Added {len(splits)} chunk(s) to vector store")
    
    # Print contents
    print_vector_store_contents(manager, label)


def test_retrieval(manager: RAGManager, query: str):
    """Test retrieval from the vector store."""
    print(f"\n>>> Testing retrieval with query: '{query}'")
    serialized, docs = manager.retrieve(query, k=2)
    print(f"Retrieved {len(docs)} document(s)")
    print(f"\nSerialized results:\n{serialized}")
    return docs


def main():
    """Main test function."""
    print("="*60)
    print("TEST VECTOR STORE - RAG PIPELINE")
    print("="*60)
    
    # Initialize RAG Manager
    print("\nInitializing RAG Manager...")
    manager = RAGManager(collection_name="test_collection")
    print(f"Collection name: {manager.collection_name}")
    
    # ============================================================
    # PHASE 1: Add first content (Python Guide)
    # ============================================================
    print("\n" + "#"*60)
    print("# PHASE 1: Adding first content (Python Guide)")
    print("#"*60)
    
    run_rag_pipeline(manager, SIMULATED_CONTENT_1, "After Python content")
    
    # Test retrieval
    test_retrieval(manager, "How do I define a function in Python?")
    
    # ============================================================
    # PHASE 2: Clear vector store
    # ============================================================
    print("\n" + "#"*60)
    print("# PHASE 2: Clearing vector store")
    print("#"*60)
    
    print("\nClearing all documents from vector store...")
    manager.clear_all_documents()
    print("Vector store cleared!")
    
    print_vector_store_contents(manager, "After clearing")
    
    # ============================================================
    # PHASE 3: Add second content (JavaScript Guide)
    # ============================================================
    print("\n" + "#"*60)
    print("# PHASE 3: Adding second content (JavaScript Guide)")
    print("#"*60)
    
    run_rag_pipeline(manager, SIMULATED_CONTENT_2, "After JavaScript content")
    
    # Test retrieval
    test_retrieval(manager, "How do I define a function in JavaScript?")
    
    # ============================================================
    # PHASE 4: Add both contents and test mixed retrieval
    # ============================================================
    print("\n" + "#"*60)
    print("# PHASE 4: Adding both contents and testing mixed retrieval")
    print("#"*60)
    
    # Clear first
    print("\nClearing vector store for fresh start...")
    manager.clear_all_documents()
    
    # Add both contents
    run_rag_pipeline(manager, SIMULATED_CONTENT_1, "Python + JavaScript")
    run_rag_pipeline(manager, SIMULATED_CONTENT_2, "Python + JavaScript")
    
    # Test mixed retrieval
    test_retrieval(manager, "variable declaration")
    
    print("\n" + "="*60)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("="*60)
    
    # Keep vector store in memory for manual inspection
    print("\nVector store is still in memory.")
    print("You can inspect it programmatically or access manager.vector_store directly.")
    print("\nTo inspect manually in Python:")
    print("  >>> from test_vectorstore import manager")
    print("  >>> manager.vector_store.get()  # Get all documents")
    print("  >>> manager.vector_store.similarity_search('your query')")
    
    return manager


if __name__ == "__main__":
    manager = main()