import streamlit as st
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver 

@st.cache_resource
def get_chat_model():
    """
    Loads and caches the heavy LLM model.
    This runs only once and is shared across all user sessions.
    """
    llm = HuggingFacePipeline.from_model_id(
        model_id="HuggingFaceTB/SmolLM2-360M-Instruct",
        task="text-generation",
        pipeline_kwargs=dict(
            max_new_tokens=512,
        ),
    )
    return ChatHuggingFace(llm=llm)

class LLMManager:
    def __init__(self):
        # Retrieve the cached model
        self.chat_model = get_chat_model()

        # Initialize the agent (memory per-session)
        self.agent = create_agent(
            model=self.chat_model,
            checkpointer=InMemorySaver(),  
        )

    def stream(self, question: str, thread_id: str = "1"):
        """
        Synchronously streams the LLM response.
        """
        config = {"configurable": {"thread_id": thread_id}}
        messages = [{"role": "user", "content": question}]
        
        for token, metadata in self.agent.stream(  
            {"messages": messages},
            config,
            stream_mode="messages",
        ):
            if token.content:
                yield token.content
