"""
RAG Manager Module.

This module provides the RAGManager class for managing RAG operations
including document loading, splitting, embedding, and retrieval using
Chroma vector store and HuggingFace embeddings.
"""

import streamlit as st
from typing import List, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ============================================================================
# RAG Manager Class
# ============================================================================

class RAGManager:
    """
    Manages RAG operations including document loading, splitting, embedding,
    and retrieval using Chroma vector store.
    """

    # Default embedding model used across the application
    DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

    # Default chunking parameters
    DEFAULT_CHUNK_SIZE = 600
    DEFAULT_CHUNK_OVERLAP = 120

    def __init__(self, collection_name: str = "webpages_content_collection"):
        """
        Initialize the RAG Manager.

        Args:
            collection_name: Name of the Chroma collection.
        """
        self.collection_name = collection_name
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.DEFAULT_EMBEDDING_MODEL
        )

        # Initialize an in-memory vector store (no persistence)
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
        )

    def load_documents(self, tool_results: List[dict]) -> List[Document]:
        """
        Convert raw tool results into LangChain Document objects.

        Args:
            tool_results: List of dictionaries containing 'raw_content', 'url', and 'title'.

        Returns:
            List of Document objects.
        """
        docs = []
        for result in tool_results:
            raw_content = result.get("raw_content")
            if raw_content:
                docs.append(
                    Document(
                        page_content=raw_content,
                        metadata={
                            "url": result.get("url"),
                            "title": result.get("title"),
                        },
                    )
                )
        return docs

    def split_documents(self, docs: List[Document]) -> List[Document]:
        """
        Split documents into chunks using recursive text splitting.
        Adds metadata headers to each chunk for context.

        Args:
            docs: List of Document objects.

        Returns:
            List of Document chunks with metadata headers.
        """
        r_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.DEFAULT_CHUNK_SIZE,
            chunk_overlap=self.DEFAULT_CHUNK_OVERLAP,
            separators=[r"\n## ", r"\n### "],
            is_separator_regex=True,
        )

        raw_splits = r_splitter.split_documents(docs)

        # Add metadata headers to each chunk for context
        splits = []
        allowed_meta = ["url", "title"]

        for split in raw_splits:
            meta_parts = [
                f"{key}: {split.metadata[key]}"
                for key in allowed_meta
                if key in split.metadata
            ]
            metadata_header = f"[{', '.join(meta_parts)}]\n"
            split.page_content = metadata_header + split.page_content
            splits.append(split)

        return splits

    def add_documents(self, splits: List[Document]) -> None:
        """
        Add document chunks to the in-memory vector store.

        Args:
            splits: List of Document chunks.
        """
        self.vector_store.add_documents(documents=splits)

    def clear_all_documents(self) -> None:
        """
        Clear all documents from the in-memory vector store by deleting
        and re-creating the collection.
        """
        self.vector_store.delete_collection()

        # Re-initialize an empty vector store with the same collection name
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
        )

    def retrieve(
        self, query: str, k: int = 10
    ) -> Tuple[str, List[Document]]:
        """
        Retrieve relevant context from the vector store.

        Args:
            query: The search query.
            k: Number of documents to retrieve.

        Returns:
            A tuple of (serialized_content, list_of_documents).
        """
        retrieved_docs = self.vector_store.similarity_search(query, k=k)

        serialized = "\n\n".join(
            f"Source: {doc.metadata}\nContent: {doc.page_content}"
            for doc in retrieved_docs
        )

        return serialized, retrieved_docs


# ============================================================================
# Module Functions
# ============================================================================

@st.cache_resource
def get_rag_manager() -> RAGManager:
    """
    Get or create a cached RAGManager instance.

    Using @st.cache_resource ensures the embedding model and vector store
    are loaded only once and persist across reruns.

    Returns:
        A cached RAGManager instance.
    """
    return RAGManager()
