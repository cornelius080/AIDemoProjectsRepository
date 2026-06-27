"""
Streamlit Web Application for RAG-powered Web Research Assistant.

This application provides an AI-powered web research interface that integrates
web search, content extraction, and RAG-based conversational capabilities.
"""

import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv, set_key

from agent import RagWebAgent


# ============================================================================
# Configuration
# ============================================================================

# Ensure environment file is read from the config directory
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.getenv("ENV_FILE_PATH", os.path.join(PROJECT_DIR, "config", ".env"))

# Load environment variables from specific file
load_dotenv(ENV_FILE)

# Configuration mapping for environment variables
ENV_VARS = {
    "LangSmith": "LANGSMITH_API_KEY",
    "Tavily": "TAVILY_API_KEY",
    "OpenAI": "OPENAI_API_KEY",
    "Google": "GOOGLE_API_KEY",
    "Anthropic": "ANTHROPIC_API_KEY",
    "Ollama": "OLLAMA_API_KEY",
}

# Available models by provider
MODELS = {
    "Ollama": [
        "nemotron-3-super:cloud",
        "minimax-m2.5:cloud",
        "gemma4:31b-cloud",
        "qwen3-coder-next:cloud",
    ],
    "OpenAI": ["gpt-5.5", "gpt-5.4-nano", "gpt-5-nano", "gpt-4.1"],
    "Google": [
        "gemini-3.1-pro-preview",
        "gemini-3.1-flash-lite",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
    ],
    "Anthropic": [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "claude-sonnet-3-7",
    ],
}

st.set_page_config(layout="wide")


# ============================================================================
# Helper Functions
# ============================================================================

@st.cache_resource
def get_agent(model_provider: str, model_name: str, temperature: float):
    """
    Initialize and cache the RagWebAgent instance with specific model parameters.

    Args:
        model_provider: The model provider name.
        model_name: The model name.
        temperature: The temperature parameter for the model.

    Returns:
        A cached RagWebAgent instance.
    """
    return RagWebAgent(
        model_provider=model_provider,
        model_name=model_name,
        temperature=temperature,
    )


def reset_chat():
    """Reset the chat history and generate a new thread ID to clear agent memory."""
    st.session_state.messages = []
    st.session_state.chat_thread_id = (
        f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )


def extract_from_webpages():
    """Extract content from selected web pages and index for RAG."""
    search_id = st.session_state.get("search_id")
    results = st.session_state.get("search_results", [])

    selected_urls = []
    if search_id and results:
        for i, res in enumerate(results):
            if st.session_state.get(f"check_{search_id}_{i}"):
                selected_urls.append(res.get("url"))

    if selected_urls:
        with st.spinner("Extracting content from selected pages..."):
            extracted_data = agent.web_extract(selected_urls)
            if not extracted_data:
                st.warning(
                    "No content could be extracted from these sources. "
                    "Try with different URLs or advanced search depth.",
                    icon="⚠️",
                )
                return
            st.session_state["extracted_content"] = extracted_data

        with st.spinner("Indexing content for RAG..."):
            agent.ingest_documents(extracted_data)

    st.session_state.is_chat_visible = True
    st.session_state.messages = []


def search_on_click():
    """Handle search button click - capture parameters and perform search."""
    # Capture all current search parameters from session state
    settings = {
        "search_depth": st.session_state.get("search_depth"),
        "max_results": st.session_state.get("max_results"),
        "topic": st.session_state.get("topic"),
        "time_range": st.session_state.get("time_range"),
        "include_answer": st.session_state.get("include_answer"),
        "include_raw_content": st.session_state.get("include_raw_content"),
        "include_images": st.session_state.get("include_images"),
        "include_image_descriptions": st.session_state.get(
            "include_image_descriptions"
        ),
        "include_domains": [
            d.strip()
            for d in st.session_state.get("include_domains", "").split(",")
            if d.strip()
        ]
        if st.session_state.get("include_domains")
        else [],
        "exclude_domains": [
            d.strip()
            for d in st.session_state.get("exclude_domains", "").split(",")
            if d.strip()
        ]
        if st.session_state.get("exclude_domains")
        else [],
        "country": st.session_state.get("country"),
        "query": st.session_state.get("search_query_input"),
    }

    # Debug: Print all parameters to console
    print("\n--- Search Triggered ---")
    for key, value in settings.items():
        print(f"{key}: {value}")
    print("------------------------\n")

    # Update search trigger state
    st.session_state["query"] = settings["query"]
    st.session_state.is_chat_visible = False
    st.session_state.messages = []

    # Form a unique search identity (Composite Key) using ALL parameters
    settings_str = "_".join([str(v) for v in settings.values()])
    st.session_state["search_id"] = f"{settings['query']}_{hash(settings_str)}"

    # Perform the search using the agent
    with st.spinner("Searching and analyzing..."):
        overview, results = agent.web_search(settings["query"], settings)
        st.session_state["search_overview"] = overview
        st.session_state["search_results"] = results


# ============================================================================
# Initialize Agent
# ============================================================================

# Get model parameters from session state, with defaults
_model_provider = st.session_state.get("model_provider", "ollama")
_model_name = st.session_state.get("model_name", "minimax-m2.5:cloud")
_model_temperature = st.session_state.get("model_temperature", 0.1)

# Define the agent with cache key based on model parameters
agent = get_agent(_model_provider, _model_name, _model_temperature)

# Initialization of chat session
if "chat_thread_id" not in st.session_state:
    st.session_state.chat_thread_id = (
        f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

# SIDEBAR
with st.sidebar:
    st.title("Settings")

    # Tavily Configuration
    with st.container(border=True):
        tavily_env_key = os.environ.get(ENV_VARS["Tavily"], "")
        tavily_api_key = st.text_input(
            "Tavily API Key", 
            value=tavily_env_key,
            type="password", 
            help=f"Loaded from file ({ENV_VARS['Tavily']})" if tavily_env_key else "Mandatory: Enter Tavily key and Save",
            key="tavily_api_key_input"
        )
        if not tavily_api_key:
            st.warning("⚠️ Tavily API Key is required for search functionality.", icon="🔑")
    
    # LangSmith Configuration
    with st.container(border=True):
        tracking_enabled = st.checkbox("Tracing", value=False, help="Enable Tracking", key="ls_enabled")
        
        ls_env_key = os.environ.get(ENV_VARS["LangSmith"], "")
        langsmith_api_key = st.text_input(
            "LangSmith API Key (Optional)", 
            value=ls_env_key,
            type="password", 
            disabled=not tracking_enabled,
            help=f"Loaded from environment ({ENV_VARS['LangSmith']})" if ls_env_key else "Enter key or set environment variable",
            key="ls_api_key"
        )
    
    # Model Configuration
    with st.container(border=True):
        # Model Provider Selection
        provider = st.radio(
            "Model Provider",
            options=list(MODELS.keys()),
            horizontal=True
        )
        
        # Model Provider API Key
        provider_env_var = ENV_VARS.get(provider)
        current_env_value = os.environ.get(provider_env_var, "")
        
        provider_api_key = st.text_input(
            f"{provider} API Key", 
            value=current_env_value,
            type="password",
            help=f"Loaded from environment ({provider_env_var})" if current_env_value else f"Enter {provider} key",
            key=f"{provider}_api_key"
        )
        if not provider_api_key:
            st.warning(f"⚠️ {provider} API Key is required.", icon="🔑")
        
        # Model Selection (Dynamic)
        selected_model = st.selectbox("Select Model", options=MODELS[provider])
        
        # Temperature Control
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.1, step=0.1)

    # Save Settings Button
    save_disabled = not (tavily_api_key and provider_api_key)
    if st.button("Save Settings", type="primary", use_container_width=True, disabled=save_disabled):
        saved_any = False
        # Save LangSmith key if provided
        if langsmith_api_key:
            set_key(ENV_FILE, ENV_VARS["LangSmith"], langsmith_api_key)
            saved_any = True
        
        # Save active provider key
        current_provider_key = f"{provider}_api_key"
        if st.session_state.get(current_provider_key):
            set_key(ENV_FILE, provider_env_var, st.session_state[current_provider_key])
            saved_any = True
            
        # Save Tavily key
        if st.session_state.get("tavily_api_key_input"):
            set_key(ENV_FILE, ENV_VARS["Tavily"], st.session_state["tavily_api_key_input"])
            saved_any = True
            
        if saved_any:
            st.success(f"Settings saved to {ENV_FILE} successfully!", icon="✅")
            # Reload environment variables to reflect changes
            load_dotenv(ENV_FILE, override=True)
            
            # Store model parameters in session state for agent initialization
            st.session_state["model_provider"] = provider.lower()
            st.session_state["model_name"] = selected_model
            st.session_state["model_temperature"] = temperature
            
            st.rerun()
        else:
            st.warning("No keys to save.")

# ============================================================================
# LangSmith Tracing Configuration
# ============================================================================

if st.session_state.get("ls_enabled"):
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = "rag_web"
    os.environ["LANGSMITH_ENDPOINT"] = "https://eu.api.smith.langchain.com"
    # Ensure we use the current value from the input field
    if st.session_state.get("ls_api_key"):
        os.environ["LANGSMITH_API_KEY"] = st.session_state.get("ls_api_key")
else:
    os.environ["LANGSMITH_TRACING"] = "false"


# ============================================================================
# Main UI
# ============================================================================

# Initialize chat visibility state
if "is_chat_visible" not in st.session_state:
    st.session_state.is_chat_visible = False

st.title("🔎 AI-powered Web Research Assistant")
st.markdown("Unlock the Web's Intelligence. Discover, digest, and discuss any topic with a powerful AI companion by your side.")

# SEARCH BAR
with st.container(border=True):
    col1, col2 = st.columns([5, 1], vertical_alignment="bottom")
    with col1:
        query = st.text_input("🔍 Insert your search query", key="search_query_input")
    with col2:
        with st.popover("Search Settings", use_container_width=True):
                st.subheader("Advanced Search Settings")
                
                search_depth = st.radio(
                    "Search Depth",
                    options=["basic", "advanced"],
                    index=0,
                    horizontal=True,
                    help="Depth of the search.",
                    key="search_depth"
                )
                
                max_results = st.slider(
                    "Max Results",
                    min_value=1,
                    max_value=10,
                    value=5,
                    help="Maximum number of search results to return.",
                    key="max_results"
                )
                
                topic = st.selectbox(
                    "Topic",
                    options=["general", "news", "finance"],
                    index=0,
                    help="Category of the search.",
                    key="topic"
                )
                
                time_range = st.selectbox(
                    "Time Range",
                    options=["", "day", "week", "month", "year"], 
                    index=0,
                    format_func=lambda x: "any time" if x == "" else f"last {x}", 
                    help="Time range to filter results.",
                    key="time_range"
                )

                
                st.divider()
                
                include_answer = st.toggle(
                    "Include Answer",
                    value=False,
                    help="Include a short answer to the original query in results.",
                    key="include_answer"
                )
                
                include_raw_content = st.toggle(
                    "Include Raw Content",
                    value=False,
                    help="Include cleaned and parsed HTML of search results.",
                    key="include_raw_content"
                )
                
                include_images = st.toggle(
                    "Include Images",
                    value=False,
                    help="Include a list of query-related images.",
                    key="include_images"
                )
                
                include_image_descriptions = st.toggle(
                    "Include Image Descriptions",
                    value=False,
                    disabled=not st.session_state.get("include_images", False),
                    help="Include descriptive text for each image.",
                    key="include_image_descriptions"
                )
                
                st.divider()
                
                include_domains = st.text_input(
                    "Include Domains",
                    placeholder="es.   *.com, wikipedia.org",
                    help="List of domains to specifically include (comma separated).",
                    key="include_domains"
                )
                
                exclude_domains = st.text_input(
                    "Exclude Domains",
                    placeholder="es.   *.com, wikipedia.org",
                    help="List of domains to specifically exclude (comma separated).",
                    key="exclude_domains"
                )
                
                country = st.selectbox(
                    "Country",
                    options=["france", "germany", "italy", "spain", "united kingdom", "united states"],
                    index=5,
                    help="Country to focus the search on.",
                    key="country"
                )


    if st.button("Search", on_click=search_on_click):
        pass

def display_results():
    if "query" in st.session_state and st.session_state["query"]:
        # The search_id (composite key) forces a full reload of this block 
        # whenever the query or any search parameter changes.
        search_id = st.session_state.get("search_id", "initial")
        
        with st.container(border=True, key=f"results_block_{search_id}"):
            col1, col2 = st.columns([2, 1])
            with col1:
                with st.container(height=400, border=False):
                    st.subheader("🌐 Web Results")
                    results = st.session_state.get("search_results", [])
                    if results:
                        for i, res in enumerate(results):
                            col_check, col_exp = st.columns([1, 15], vertical_alignment="top")
                            with col_check:
                                st.checkbox(f"select_{i}", label_visibility="collapsed", value=True, key=f"check_{search_id}_{i}")
                            with col_exp:
                                with st.expander(f"{res.get('title', 'Untitled')}"):
                                    st.write(res.get('content', 'No description available.'))
                                    st.markdown(f"[Go to page]({res.get('url', '#')})")
                    else:
                        st.info("No results found.")
            with col2:
                with st.container(height=400, border=False):
                    st.subheader("🧠 AI Overview")
                    overview = st.session_state.get("search_overview", "")
                    if overview:
                        st.info(overview)
                    else:
                        st.write("Initializing overview...")
            
            st.button("Extract Info and Chat", on_click=extract_from_webpages, use_container_width=True)

# Main Flow: Display Results
display_results()



# FOLLOW-UP CHAT
if st.session_state.is_chat_visible:
    chat_col1, chat_col2 = st.columns([4, 1])
    with chat_col1:
        st.subheader("💬 Chat on the retrieved content")
    with chat_col2:
        st.button("🗑️ Reset Chat", on_click=reset_chat, use_container_width=True, help="Clear history and start a new session")

    st.write(f"Conversing with **{selected_model}** from **{provider}**")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("Ask AI"):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            response = st.write_stream(agent.chat_stream(prompt, thread_id=st.session_state.chat_thread_id))
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
