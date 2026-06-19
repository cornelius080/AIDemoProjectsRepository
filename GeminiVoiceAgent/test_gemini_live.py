import asyncio
from gemini_live import GeminiLiveAudio

async def main() -> None:
    """
    Main asynchronous testing function for GeminiLiveAudio logic.
    Connects to the API using default parameters.
    """
    # Create the test agent using the relevant preview model
    agent = GeminiLiveAudio(
        model="gemini-3.1-flash-live-preview",
        system_instruction="You are a helpful and friendly AI assistant."
    )
    
    # Run the continuous audio connection
    await agent.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user.")
