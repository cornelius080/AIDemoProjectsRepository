import os
import streamlit as st
from typing import List, Optional, Tuple
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

class RAGManager:
    """Class to manage RAG operations (loading, splitting, embedding, and retrieval)."""
    
    def __init__(self, collection_name: str = "webpages_content_collection"):
        """
        Initialize the RAG Manager.
        
        Args:
            collection_name: Name of the Chroma collection.
        """
        self.collection_name = collection_name
        # Using the same embedding model as in the notebook
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        
        # Initialize an in-memory vector store (no persist_directory)
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
        )

    def load_documents(self, tool_results: List[dict]) -> List[Document]:
        """
        Convert raw tool results into LangChain Document objects.
        
        Args:
            tool_results: List of dictionaries containing 'raw_content', 'url', and 'title'.
        """
        docs = []
        for result in tool_results:
            raw_content = result.get("raw_content")
            if raw_content:
                docs.append(
                    Document(
                        page_content=raw_content,
                        metadata={"url": result.get("url"), "title": result.get("title")},
                    )
                )
        return docs

    def split_documents(self, docs: List[Document]) -> List[Document]:
        """
        Split documents into chunks following the notebook's logic.
        Adds metadata headers to each chunk.
        
        Args:
            docs: List of Document objects.
        """
        # Specific parameters from the notebook
        r_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=120,
            # separators=[r"\n## ", r"\n### ", r"\n#### ", r"\n\n", r"\n", r"(?<=\. )", " ", ""], 
            separators=[r"\n## ", r"\n### ",], 
            is_separator_regex=True
        )

        raw_splits = r_splitter.split_documents(docs)

        # Post-processing to add metadata headers to content
        splits = []
        for split in raw_splits:
            allowed_meta = ["url", "title"]
            meta_parts = []
            for key in allowed_meta:
                if key in split.metadata:
                    value = split.metadata[key]
                    meta_parts.append(f"{key}: {value}")
            
            metadata_header = f"[{', '.join(meta_parts)}]\n"
            split.page_content = metadata_header + split.page_content
            splits.append(split)
        
        return splits

    def add_documents(self, splits: List[Document]):
        """
        Add document chunks to the in-memory vector store.
        (No IDs and no persistence as requested).
        
        Args:
            splits: List of Document chunks.
        """
        self.vector_store.add_documents(documents=splits)

    def clear_all_documents(self):
        """
        Clear all documents from the in-memory vector store by deleting and re-creating the collection.
        """
        # Delete the existing collection to truly clear all documents
        self.vector_store.delete_collection()
        
        # Re-initialize an empty vector store with the same collection name
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
        )

    def retrieve(self, query: str, k: int = 10) -> Tuple[str, List[Document]]:
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
            (f"Source: {doc.metadata}\nContent: {doc.page_content}")
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs

# Global instance for tool usage managed by Streamlit cache
@st.cache_resource
def get_rag_manager() -> RAGManager:
    """
    Get or create a cached RAGManager instance.
    Using @st.cache_resource ensures the embedding model and vector store
    are loaded only once and persist across reruns.
    """
    return RAGManager()
