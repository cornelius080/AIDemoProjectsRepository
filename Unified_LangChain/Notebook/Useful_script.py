# HUGGINGFACE PIPELINE

from transformers import pipeline
generator = pipeline("text-generation", model="HuggingFaceTB/SmolLM2-360M")


# LANGCHAIN AGENT WITH MEMORY

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver 

agent = create_agent(
    model = generator,
    checkpointer=InMemorySaver(),  
)

