"""
RAG Web Agent Module.

This module provides the RagWebAgent class, which integrates web search,
webpage extraction, and RAG (Retrieval-Augmented Generation) capabilities
using LangChain and LangGraph.
"""

import json
from dataclasses import dataclass
from typing import Callable, Iterator, List, Optional

# LangChain / LangGraph imports
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

# Local imports
from rag import get_rag_manager
from web_extract import TavilyExtractInput, WebExtract
from web_search import TavilySearchInput, WebSearch


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ToolType:
    """Context schema to determine which tool to use."""
    tool_type: str = "retrieve"


# ============================================================================
# Tool Definitions
# ============================================================================

@tool(args_schema=TavilySearchInput)
def tavily_search(
    query: str,
    max_results: int = 5,
    topic: str = "general",
    include_answer: bool = False,
    include_raw_content: bool = False,
    include_images: bool = False,
    include_image_descriptions: bool = False,
    search_depth: str = "basic",
    time_range: str = "",
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    country: str = ""
) -> str:
    """Execution of the Tavily web search tool."""
    searcher = WebSearch()
    # WebSearch search method accepts kwargs matching TavilySearchInput
    return searcher.search(
        query=query,
        max_results=max_results,
        topic=topic,
        include_answer=include_answer,
        include_raw_content=include_raw_content,
        include_images=include_images,
        include_image_descriptions=include_image_descriptions,
        search_depth=search_depth,
        time_range=time_range,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        country=country
    )

@tool(args_schema=TavilyExtractInput)
def tavily_extract(
    urls: List[str],
    include_images: bool = False,
    extract_depth: str = "basic",
    chunks_per_source: int = 3,
    include_favicon: bool = False,
    format_text: str = "markdown"
) -> str:
    """Execution of the Tavily webpage extraction tool."""
    extractor = WebExtract()
    return extractor.extract(
        urls=urls,
        include_images=include_images,
        extract_depth=extract_depth,
        chunks_per_source=chunks_per_source,
        include_favicon=include_favicon,
        format_text=format_text
    )

@tool(response_format="content_and_artifact")
def retrieve_context(query: str, k: int = 10):
    """
    Retrieve information to help answer a query based on the current context.
    
    Args:
        query: The question or query to search for.
        k: Number of retrieved documents.
    """
    manager = get_rag_manager()
    return manager.retrieve(query, k=k)


# ============================================================================
# Middleware
# ============================================================================

@wrap_model_call
def dynamic_tool_call(
    request: ModelRequest, 
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Dynamically switch tools based on the runtime context."""
    tool_type = request.runtime.context.tool_type
    
    if tool_type == "search":
        tools = [tavily_search]
        request = request.override(tools=tools) 
    elif tool_type == "extract":
        tools = [tavily_extract]
        request = request.override(tools=tools)
    else:
        # Default to retrieval
        tools = [retrieve_context]
        request = request.override(tools=tools)

    return handler(request)


# ============================================================================
# Agent Class
# ============================================================================

class RagWebAgent:
    """
    An advanced AI agent that integrates web search, webpage extraction, 
    and RAG (Retrieval-Augmented Generation) capabilities.
    """
    
    def __init__(self, model_provider: str = "ollama", model_name: str = "minimax-m2.5:cloud", temperature: float = 0.1):
        """
        Initialize the agent with a specific model provider and model.
        
        Args:
            model_provider: The model provider (e.g., "openai", "google", "anthropic", "ollama")
            model_name: The model name (e.g., "gpt-5.5", "gemini-2.5-pro", "claude-3-7-sonnet", "minimax-m2.5:cloud", "gemma4:31b-cloud")
            temperature: The temperature parameter for the model.
        """
        # Map UI provider names to LangChain provider names
        provider_mapping = {
            "google": "google_genai",
            "anthropic": "anthropic",
            "openai": "openai",
            "ollama": "ollama",
        }
        # Get the LangChain provider name, default to the original if not in mapping
        lc_provider = provider_mapping.get(model_provider.lower(), model_provider)
        
        # Format: "provider:model" as required by init_chat_model
        model_id = f"{lc_provider}:{model_name}"
        self.model = init_chat_model(model=model_id, temperature=temperature)
        self.model_provider = model_provider
        self.model_name = model_name
        self.temperature = temperature       
        
        # System prompt exactly as defined in the notebook
        self.system_prompt = """
        You are an advanced web research and conversational RAG assistant.

        CRITICAL INSTRUCTION: You MUST use EXACTLY ONE tool per task. Do NOT chain multiple tools together or make sequential tool calls. You will be provided with a SINGLE tool for each task, and MUST complete the entire task using ONLY that tool.

        ---

        TOOL USAGE RULES (STRICT - NO EXCEPTIONS):

        1. WHEN USING 'tavily_search':
        - This is the ONLY tool available for this task.
        - The user input will consist of a query and a dictionary of parameters.
        - Extract ALL parameters from the user input and pass them EXACTLY as they are into the tool schema.
        - Do NOT invent or add parameters.
        - Make ONE search call and report results directly.
        - NEVER follow up with extract or retrieve_context after search.

        2. WHEN USING 'tavily_extract':
        - This is the ONLY tool available for this task.
        - Pass ONLY the URLs to the tool exactly as provided.
        - Rely entirely on the tool's default settings.
        - Retrieve the entire original content from the webpage without any modifications, adjustments or alterations whatsoever (no changes to the lexicon, punctuation, format, or language).
        - REPORTING RULES (CRITICAL): Your final response MUST be a verbatim report of the extracted content. Do NOT modify the content, summarize it, or add any introductory/concluding text.
        - Format each source strictly like this:
            ---------- SOURCE: <url>
            
            <raw_content>
        - Separate different sources with TWO NEWLINES.
        - Do NOT make multiple extract calls.
        - Do NOT follow up with search or retrieve_context after extraction.

        3. WHEN USING 'retrieve_context' (CONVERSATIONAL RAG & QUESTION/ANSWERING):
        - This is the ONLY tool available for this task.
        - Query the vector store with the user's question.
        - Make ONE retrieval call and answer based entirely on the results.
        - Do NOT follow up with search or extract.
        - CRITICAL RULE: Base your answer **EXCLUSIVELY** on the retrieved context.
        - If the answer is not in the retrieved context, state clearly that you do not have enough information. DO NOT guess or hallucinate.
        - Maintain a helpful, clear, and conversational tone while answering in the user's language.

        ---

        OPTIMIZATION RULES:
        - Complete each task in a SINGLE tool invocation.
        - NO sequential tool chaining.
        - NO looping or retry attempts.
        - Provide the final answer immediately after the tool execution.
        """
        
        # Initialize the agent graph
        self.agent = create_agent(
            model=self.model,
            tools=[tavily_search, tavily_extract, retrieve_context],
            checkpointer=InMemorySaver(),
            middleware=[dynamic_tool_call],
            context_schema=ToolType,
            system_prompt=self.system_prompt
        )

    def invoke_agent(self, query: str, tool_type: str = "search", thread_id: str = "conversation_1"):
        """
        Invokes the agent for a single turn with a specific tool context.
        """
        return self.agent.invoke(
            {"messages": [{"role": "user", "content": query}]},
            {"configurable": {"thread_id": thread_id}},
            context={"tool_type": tool_type}
        )

    def stream_agent(self, query: str, tool_type: str = "search", thread_id: str = "conversation_1") -> Iterator[str]:
        """
        Synchronously streams the LLM response tokens based on the tool context.
        """        
        for token, metadata in self.agent.stream(  
            {"messages": [{"role": "user", "content": query}] },
            {"configurable": {"thread_id": thread_id}},
            context={"tool_type": tool_type},
            stream_mode="messages",
        ):
            if isinstance(token, AIMessageChunk) and token.content:
                yield token.content

    def web_search(self, research_query: str, params: dict):
        """
        Performs a web search using the agent with 'search' context.
        Returns a tuple (overview: str, results: list).
        """
        params_json = json.dumps(params)
        query = f"text: {research_query}, params: {params_json}"
        
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": query}]},
            {"configurable": {"thread_id": "search_thread"}},
            context={"tool_type": "search"},
        )
        
        # Extraction logic as defined in the notebook:
        # - overview: the last message from the AI
        # - results: parsed from the tool message (penultimate message)
        
        overview = result["messages"][-1].content
        
        # The tool message is the one before the final AI response
        tool_msg_content = result["messages"][-2].content
        try:
            tool_data = json.loads(tool_msg_content)
            results = tool_data.get("results", [])
        except (json.JSONDecodeError, AttributeError):
            results = []
            
        return overview, results

    def web_extract(self, urls: List[str]):
        """
        Extracts content from a list of URLs using the agent with 'extract' context.
        Returns the parsed results from the tool message.
        """
        query = HumanMessage(content=[
            {"type": "text", "text": str(urls)},
        ])
        
        result = self.agent.invoke(
            {"messages": [query]},
            {"configurable": {"thread_id": "extract_thread"}},
            context={"tool_type": "extract"},
        )
        
        # Extraction logic consistent with the notebook:
        # - The tool message is the penultimate message
        tool_msg_content = result["messages"][-2].content
        try:
            tool_data = json.loads(tool_msg_content)
            extracted_results = tool_data.get("results", [])
        except (json.JSONDecodeError, AttributeError):
            extracted_results = []
            
        return extracted_results

    def ingest_documents(self, extracted_results: List[dict], thread_id: str = "extract_thread"):
        """
        Orchestrates the RAG pipeline: resets the vector store and adds new documents.
        Then clears the tool message from the agent's history to free context window.
        """
        if not extracted_results:
            return
            
        manager = get_rag_manager()
        
        # 1. Clear previous documents to ensure "exclusive" context
        manager.clear_all_documents()
        
        # 2. Loading
        docs = manager.load_documents(extracted_results)
        
        # 3. Splitting
        splits = manager.split_documents(docs)
        
        # 4. Adding to vector store (Embeddings)
        manager.add_documents(splits)
        
        # 5. Clear the tool message from agent history to prevent context overflow
        self._clear_tool_message_from_history(thread_id)
    
    def _clear_tool_message_from_history(self, thread_id: str):
        """
        Clears the last tool message from the agent's history for the given thread.
        This prevents the raw_content from consuming context window space.
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = self.agent.get_state(config)
            
            if state and state.messages:
                # Delete the state to clear messages
                self.agent.delete_state(config)
        except Exception:
            # If clearing fails, continue anyway - not critical
            pass

    def chat_stream(self, query: str, thread_id: str = "chat_session") -> Iterator[str]:
        """
        Streams AI response tokens for the RAG-based conversation (retrieve context).
        """        
        for token, _ in self.agent.stream(
            {"messages": [{"role": "user", "content": query}]},
            {"configurable": {"thread_id": thread_id}},
            context={"tool_type": "retrieve"},
            stream_mode="messages",
        ):
            if isinstance(token, AIMessageChunk):
                content = token.content
                
                # Handle structured content (JSON strings from Google models)
                if isinstance(content, str) and content.startswith("["):
                    try:
                        parsed = json.loads(content)
                        # Extract text from structured content
                        if parsed and isinstance(parsed, list):
                            for item in parsed:
                                if item.get("type") == "text":
                                    yield item.get("text", "")
                                    return
                    except (json.JSONDecodeError, TypeError):
                        # Not valid JSON, yield as-is
                        pass
                
                if content:
                    yield content

