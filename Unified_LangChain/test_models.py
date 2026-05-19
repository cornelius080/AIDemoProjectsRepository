from langchain.chat_models import init_chat_model
import os

provider = 1  # 0: HuggingFace, 1: Ollama, 2: Google GenAI, 3: OpenAI, 4: Anthropic

if provider == 0:
    api_key_name = "HF_TOKEN_READ"
    model_provider = "huggingface"
    model_name = "MiniMaxAI/MiniMax-M2.7"
elif provider == 1:
    api_key_name = "OLLAMA_API_KEY"
    model_provider = "ollama"
    model_name = "minimax-m2.5:cloud"
    model_name = "gemma4:31b-cloud"
elif provider == 2:
    api_key_name = "GOOGLE_API_KEY"
    model_provider = "google_genai"  
    model_name = "gemini-2.5-flash"
elif provider == 3:
    api_key_name = "OPENAI_API_KEY"
    model_provider = "openai"  
    model_name = "gpt-4.1"
elif provider == 4:
    api_key_name = "ANTHROPIC_API_KEY"
    model_provider = "anthropic"  
    model_name = "claude-sonnet-3-7"
    

api_key = os.getenv(api_key_name)
if api_key is None:
    error = api_key_name + " environment variable not found!"
    raise ValueError(error)
print("API key loaded successfully")

model_id = f"{model_provider}:{model_name}"
model = init_chat_model(model=model_id, temperature=0.1)    
response = model.invoke("Hello, are you ready to chat?")
print(response)