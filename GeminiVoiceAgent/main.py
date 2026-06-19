import os
import sys
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Gemini Live classes
sys.path.insert(0, os.path.dirname(__file__))
from gemini_live import GeminiLiveBridge, GeminiTextChat


# ====================================================================
# BLOCK 1: Setup & CORS
# ====================================================================

app = FastAPI(
    title="Gemini Live Voice Agent",
    version="2.0.0",
    description="FastAPI server for real-time Gemini Live audio interaction"
)

# Configure CORS to allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to actual domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================================================================
# BLOCK 2: REST API Routes
# ====================================================================

class MessagePayload(BaseModel):
    """
    Data model representing a message payload from the client.

    Attributes:
        message (str): The text message string sent by the user.
    """
    message: str


# Instantiate the text chat logic
text_chat = GeminiTextChat(model="gemini-3.1-flash-lite")


@app.get("/api/status")
async def get_status() -> dict:
    """
    Health check endpoint to verify the service is running.

    Returns:
        dict: A dictionary indicating the service status.
    """
    return {"status": "ok", "service": "gemini-live-bridge"}


@app.post("/api/invoke_chat")
async def invoke_chat(payload: MessagePayload) -> dict:
    """
    Process a text message via REST API using Gemini.

    Parameters:
        payload (MessagePayload): The incoming payload containing the message.

    Returns:
        dict: A dictionary containing the processing status and AI response.
    """
    try:
        # Call the decoupled logic to get the AI's response
        ai_response = await text_chat.generate_response(payload.message)
        
        return {
            "status": "success",
            "user_message": payload.message,
            "ai_response": ai_response
        }
    except Exception as error:
        # If Gemini fails, return a clean 500 internal server error
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(error))


# ====================================================================
# BLOCK 3: WebSocket Endpoint
# ====================================================================

# Create bridge instance
bridge = GeminiLiveBridge(
    model="gemini-3.1-flash-live-preview",
    system_instruction="You are a helpful and friendly AI assistant.",
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Handles full-duplex real-time communication with Gemini Live.

    Delegates processing to GeminiLiveBridge.

    Parameters:
        websocket (WebSocket): The active WebSocket connection.
    """
    await websocket.accept()
    try:
        await bridge.handle_client(websocket)
    except Exception as error:
        print(f"[Bridge] Error: {error}")
    finally:
        print("[Bridge] Client disconnected")


# ====================================================================
# BLOCK 4: Static Files (Frontend)
# ====================================================================

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
# Mount the frontend directory to serve static HTML, JS, and CSS files
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ====================================================================
# Entry point (for direct execution)
# ====================================================================

if __name__ == "__main__":
    import uvicorn
    print("\n  ╔══════════════════════════════════════╗")
    print("  ║   Gemini Live — FastAPI Server       ║")
    print("  ╚══════════════════════════════════════╝")
    print("\n  Frontend (HTTP)   →  http://localhost:8000")
    print("  WebSocket          →  ws://localhost:8000/ws")
    print("  Health check       →  http://localhost:8000/api/status")
    print("\n  Press Ctrl+C to stop.\n")
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("\nShutting down... Done.")
