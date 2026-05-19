"""
Web Extraction Module.

This module provides the WebExtract class for extracting content from
web pages using the Tavily extraction API.
"""

import os
from typing import List, Literal, Optional

from dotenv import load_dotenv
from langchain_tavily import TavilyExtract
from pydantic import BaseModel, Field


# Load environment variables from specific file
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(PROJECT_DIR, "apy_keys.env")
load_dotenv(ENV_FILE)


# ============================================================================
# Input Schema
# ============================================================================

class TavilyExtractInput(BaseModel):
    """Input parameters for the Tavily web page extraction tool."""

    urls: List[str] = Field(description="List of URLs to extract content from.")
    extract_depth: Literal["basic", "advanced"] = Field(
        default="basic", description="Extraction depth."
    )
    chunks_per_source: Literal["1", "2", "3", "4", "5"] = Field(
        default="3", description="Number of text chunks to extract per source (max 5)."
    )
    include_images: bool = Field(
        default=False, description="Whether to include images in the extraction."
    )
    include_favicon: bool = Field(
        default=False, description="Whether to include favicons in the extraction."
    )
    format_text: Literal["markdown", "text"] = Field(
        default="markdown", description="Output formatting type."
    )


# ============================================================================
# Web Extraction Class
# ============================================================================

class WebExtract:
    """Manages web page extraction operations using Tavily."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the WebExtract manager.

        Args:
            api_key: Optional Tavily API key. If not provided, it looks for
                TAVILY_API_KEY in environment.
        """
        if api_key:
            os.environ["TAVILY_API_KEY"] = api_key

        if not os.environ.get("TAVILY_API_KEY"):
            raise ValueError(
                "TAVILY_API_KEY not found in environment. "
                "Please set it in apy_keys.env or pass it to the constructor."
            )

    def extract(
        self,
        urls: List[str],
        extract_depth: str = "basic",
        chunks_per_source: str = "3",
        include_images: bool = False,
        include_favicon: bool = False,
        format_text: str = "markdown",
    ) -> str:
        """
        Extract content from web pages using TavilyExtract.

        Args:
            urls: List of URLs to extract content from.
            extract_depth: Extraction depth (basic or advanced).
            chunks_per_source: Number of text chunks per source.
            include_images: Whether to include images in extraction.
            include_favicon: Whether to include favicons in extraction.
            format_text: Output format (markdown or text).

        Returns:
            Extracted content as a string.
        """
        # Convert string to int for Tavily API (handles both string and int inputs)
        chunks = (
            int(chunks_per_source)
            if isinstance(chunks_per_source, str)
            else chunks_per_source
        )

        tool_instance = TavilyExtract(
            extract_depth=extract_depth,
            chunks_per_source=chunks,
            include_images=include_images,
            include_favicon=include_favicon,
            format=format_text,
        )

        return tool_instance.invoke({"urls": urls})
