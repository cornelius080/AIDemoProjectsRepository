import os
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_tavily import TavilySearch

# Load environment variables from specific file
# Handle the directory of the current script
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(PROJECT_DIR, "apy_keys.env")
load_dotenv(ENV_FILE)

class TavilySearchInput(BaseModel):
    """Input parameters for the Tavily web search tool."""
    query: str = Field(description="The search query string.")
    max_results: int = Field(default=5, description="Maximum number of search results to return.")
    topic: Literal["general", "news", "finance"] = Field(default="general", description="Category of the search.")
    include_answer: bool = Field(default=False, description="Include a short answer to the original query in results.")
    include_raw_content: bool = Field(default=False, description="Include cleaned and parsed HTML of search results.")
    include_images: bool = Field(default=False, description="Include a list of query-related images.")
    include_image_descriptions: bool = Field(default=False, description="Include descriptive text for each image.")
    search_depth: Literal["basic", "advanced"] = Field(default="basic", description="Depth of the search.")
    time_range: str = Field(default="", description="Time range to filter results ('day', 'week', 'month', 'year') or empty string.")
    include_domains: List[str] = Field(default_factory=list, description="List of domains to specifically include.")
    exclude_domains: List[str] = Field(default_factory=list, description="List of domains to specifically exclude.")
    country: str = Field(default="", description="Country to focus the search on.")

class WebSearch:
    """Class to manage web search operations using Tavily."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the WebSearch manager.
        
        Args:
            api_key: Optional Tavily API key. If not provided, it looks for TAVILY_API_KEY in environment.
        """
        if api_key:
            os.environ["TAVILY_API_KEY"] = api_key
            
        if not os.environ.get("TAVILY_API_KEY"):
            raise ValueError("TAVILY_API_KEY not found in environment. Please set it in apy_keys.env or pass it to the constructor.")

    def search(
        self,
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
        """
        Perform a web search using TavilySearch.
        
        Follows the logic defined in the project's RAG notebook.
        """
        
        # parameters validation (Tavily needs None values for empty inputs)
        _time_range = None if not time_range else time_range
        _include_domains = None if not include_domains else include_domains
        _exclude_domains = None if not exclude_domains else exclude_domains
        _country = None if not country else country

        tool_instance = TavilySearch(
            max_results=max_results,
            topic=topic,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
            include_image_descriptions=include_image_descriptions,
            search_depth=search_depth,
            time_range=_time_range,
            include_domains=_include_domains,
            exclude_domains=_exclude_domains,
            country=_country
        )

        return tool_instance.invoke({"query": query})
