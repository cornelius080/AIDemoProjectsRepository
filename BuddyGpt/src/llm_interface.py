
import os
import aiosqlite
from typing import Optional, Dict, Any
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents.middleware import SummarizationMiddleware

class LLMInterface:
    """Interface for interacting with LangChain and LangGraph for LLM operations."""
    def __init__(self, db_path: Optional[str] = None):
        """
        Initializes the LLMInterface with a database path.
        
        Args:
            db_path: Path to the SQLite database. Defaults to storage/data/conversations.db.
        """
        # Determine the project root and storage path
        # Assuming src/llm_interface.py, so go up one level to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if db_path is None:
            # Default to storage/data/conversations.db
            storage_dir = os.path.join(project_root, "storage", "data")
            os.makedirs(storage_dir, exist_ok=True)
            self.db_path = os.path.join(storage_dir, "conversations.db")
        else:
            # If user provided a path, ensure directory exists
            self.db_path = db_path
            directory = os.path.dirname(self.db_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
        # Initialize connection and checkpointer placeholders
        self.conn = None
        self.checkpointer = None
        self.agent = None
        self.model = None

    def get_api_key_path(self) -> str:
        """Returns the path to the .env file in the project root."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, ".env")

    def load_api_key(self, key_name: str = "HUGGINGFACE_API_KEY_READ") -> Optional[str]:
        """
        Loads an API key from the .env file.
        For HUGGINGFACE_API_KEY_READ, it also checks the environment.
        """
        # 1. If HF key, check environment first
        if key_name == "HUGGINGFACE_API_KEY_READ":
            env_token = os.environ.get("HUGGINGFACE_API_KEY_READ")
            if env_token:
                return env_token

        # 2. Check .env file
        path = self.get_api_key_path()
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    for line in f:
                        if line.startswith(f"{key_name}="):
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception as e:
                print(f"Error reading .env for {key_name}: {e}")
        return None

    def save_api_key(self, key_value: str, key_name: str = "HUGGINGFACE_API_KEY_READ"):
        """Saves an API key to the .env file, preserving other keys."""
        path = self.get_api_key_path()
        lines = []
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"Error reading .env during save: {e}")

        new_lines = []
        found = False
        for line in lines:
            if line.startswith(f"{key_name}="):
                new_lines.append(f"{key_name}={key_value}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"{key_name}={key_value}\n")

        try:
            with open(path, "w") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"Error saving {key_name} to .env: {e}")

    async def initialize_memory(self):
        """
        Initializes the async sqlite connection and checkpointer.
        Must be called/awaited before using agent functionality.
        """
        self.conn = await aiosqlite.connect(self.db_path)
        
        # Monkey-patch is_alive for LangGraph compatibility if missing
        if not hasattr(self.conn, 'is_alive'):
            self.conn.is_alive = lambda: True
            
        self.checkpointer = AsyncSqliteSaver(self.conn)
        await self.checkpointer.setup()

    async def close(self):
        """Closes the database connection."""
        if self.conn:
            await self.conn.close()

    def setup_langsmith_tracing(self, project_name: str = "buddygpt_project"):
        """
        Enables LangSmith tracing if the API key is present in the .env file.
        
        Args:
            project_name: Name of the project for LangSmith.
        """
        # Load strictly from .env
        api_key = self.load_api_key("LANGSMITH_API_KEY")
        
        if api_key:
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_PROJECT"] = project_name
            os.environ["LANGSMITH_ENDPOINT"] = "https://eu.api.smith.langchain.com"
            os.environ["LANGSMITH_API_KEY"] = api_key
        else:
            # Explicitly disable tracing if no key is found
            os.environ["LANGSMITH_TRACING"] = "false"

    def initialize_model(
        self,  
        temperature: float = 0.2, 
        top_p: float = 0.95, 
        max_new_tokens: int = 2000,
        api_token: Optional[str] = None,
        **kwargs
    ):
        """
        Initializes the LLM model. If api_token is not provided, it attempts to load it from .env.
        
        Args:
            temperature: Sampling temperature.
            top_p: Nucleus sampling threshold.
            max_new_tokens: Maximum tokens to generate.
            api_token: Optional Hugging Face API token.
            **kwargs: Additional arguments for the model.
            
        Returns:
            The initialized model or None if the token is missing.
        """
        token = api_token or self.load_api_key()
        
        if not token:
            # We don't raise here, let the UI handle the missing key
            return None

        llm = HuggingFaceEndpoint(
            repo_id="HuggingFaceTB/SmolLM3-3B",
            huggingfacehub_api_token=token,
            temperature=temperature,
            top_p=top_p,
            max_new_tokens=max_new_tokens,
        )

        self.model = ChatHuggingFace(llm=llm, verbose=True)
        return self.model

    def create_agent_with_memory(self, trigger_count: int = 12, keep_count: int = 10):
        """
        Creates an agent with persistent memory using AsyncSqliteSaver.
        Includes SummarizationMiddleware for managing long conversations.
        
        Args:
            trigger_count: Number of messages after which summarization is triggered.
            keep_count: Number of messages to keep after summarization.
            
        Returns:
            The created agent.
        """
        if not self.model:
            raise ValueError("Model not initialized. Call initialize_model first.")
        if not self.checkpointer:
            raise ValueError("Checkpointer not initialized. Call await initialize_memory() first.")
        
        self.agent = create_agent(
            model=self.model,
            checkpointer=self.checkpointer,
            middleware=[
                SummarizationMiddleware(
                    model=self.model,
                    trigger=("messages", trigger_count),
                    keep=("messages", keep_count)
                )
            ],
        )
        return self.agent

    async def ainvoke_agent(self, thread_id: str, message: str) -> Dict[str, Any]:
        """
        Handles an asynchronous conversation within a specific thread.
        
        Args:
            thread_id: Unique identifier for the conversation thread.
            message: User message content.
            
        Returns:
            The response from the agent.
        """
        if not self.agent:
            raise ValueError("Agent not created. Call create_agent_with_memory first.")
        config = {"configurable": {"thread_id": thread_id}}
        
        input_message = {"role": "user", "content": message}
        
        response = await self.agent.ainvoke(
            {"messages": [input_message]}, 
            config
        )
        return response

    async def astream_agent(self, thread_id: str, message: str):
        """
        Streams response tokens asynchronously for a given thread.
        
        Args:
            thread_id: Unique identifier for the conversation thread.
            message: User message content.
            
        Yields:
            Token content as it is generated.
        """
        if not self.agent:
            raise ValueError("Agent not created. Call create_agent_with_memory first.")
        
        config = {"configurable": {"thread_id": thread_id}}
        input_message = {"role": "user", "content": message}
        
        async for msg, metadata in self.agent.astream(
            {"messages": [input_message]}, 
            config, 
            stream_mode="messages"
        ):
            if msg.content:
                yield msg.content

    async def get_conversation_history(self, thread_id: str):
        """
        Retrieves the saved conversation history from the database.
        
        Args:
            thread_id: Unique identifier for the conversation thread.
            
        Returns:
            List of messages in the conversation.
        """
        if not self.checkpointer:
             raise ValueError("Checkpointer not initialized.")

        config = {"configurable": {"thread_id": thread_id}}
        
        state = await self.checkpointer.aget(config)
        
        messages = []
        if state and "channel_values" in state and "messages" in state["channel_values"]:
            messages = state["channel_values"]["messages"]
            
        return messages

    async def get_saved_thread_ids(self):
        """
        Retrieves all saved thread IDs from the database.
        
        Returns:
            List of thread IDs.
        """
        if not self.conn:
             return []
        try:
            async with self.conn.execute("SELECT DISTINCT thread_id FROM checkpoints") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            return []
