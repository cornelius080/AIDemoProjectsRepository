import asyncio
from gemini_live import GeminiLiveAudio

async def main():
    # You can pass a different model or system_instruction if you want
    agent = GeminiLiveAudio(
        model="gemini-3.1-flash-live-preview",
        system_instruction="You are a helpful and friendly AI assistant."
    )
    await agent.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user.")
