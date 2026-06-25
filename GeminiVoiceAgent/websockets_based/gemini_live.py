import asyncio
import json
from google import genai
from google.genai import types
import pyaudio

class GeminiLiveAudio:
    """
    Class to encapsulate the full-duplex live multimodal interaction
    via the Gemini Live API.
    """
    def __init__(self, model="gemini-3.1-flash-live-preview", system_instruction="You are a helpful and friendly AI assistant."):
        self.client = genai.Client()
        self.model = model
        self.config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": system_instruction,
            "output_audio_transcription": {},
            "input_audio_transcription": {},
        }
        
        # --- pyaudio config ---
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.SEND_SAMPLE_RATE = 16000
        self.RECEIVE_SAMPLE_RATE = 24000
        self.CHUNK_SIZE = 1024
        
        self.pya = pyaudio.PyAudio()

        self.audio_queue_output = asyncio.Queue()
        self.audio_queue_mic = asyncio.Queue(maxsize=5)
        
        self.audio_stream = None
        self.speaker_stream = None

    async def listen_audio(self):
        """Listens for audio and puts it into the mic audio queue."""
        mic_info = self.pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            self.pya.open,
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=self.CHUNK_SIZE,
        )
        kwargs = {"exception_on_overflow": False} if __debug__ else {}
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, self.CHUNK_SIZE, **kwargs)
            await self.audio_queue_mic.put({"data": data, "mime_type": "audio/pcm"})

    async def send_realtime(self, session):
        """Sends audio from the mic audio queue to the GenAI session."""
        while True:
            msg = await self.audio_queue_mic.get()
            await session.send_realtime_input(audio=msg)

    async def receive_audio(self, session):
        """Receives responses from GenAI and puts audio data into the speaker audio queue."""
        last_was_input = False
        while True:
            try:
                turn = session.receive()
                async for response in turn:
                    sc = response.server_content
                    if not sc:
                        continue
                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if part.inline_data and isinstance(part.inline_data.data, bytes):
                                self.audio_queue_output.put_nowait(part.inline_data.data)
                    if sc.output_transcription:
                        if last_was_input:
                            print()
                            last_was_input = False
                        t = sc.output_transcription.text
                        print(t, end="", flush=True)
                        if t.rstrip()[-1:] in '.!?':
                            print()
                    if sc.input_transcription:
                        if not last_was_input:
                            print()
                            last_was_input = True
                        t = sc.input_transcription.text
                        print(f"\033[3m{t}\033[0m", end="", flush=True)
                        if t.rstrip()[-1:] in '.!?':
                            print()

                # Empty the queue on interruption to stop playback
                while not self.audio_queue_output.empty():
                    self.audio_queue_output.get_nowait()
            except asyncio.CancelledError:
                break

    async def play_audio(self):
        """Plays audio from the speaker audio queue."""
        self.speaker_stream = await asyncio.to_thread(
            self.pya.open,
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_queue_output.get()
            await asyncio.to_thread(self.speaker_stream.write, bytestream)

    async def run(self):
        """Main function to run the audio loop."""
        try:
            async with self.client.aio.live.connect(
                model=self.model, config=self.config
            ) as live_session:
                print(f"Connected to Gemini ({self.model}). Start speaking!")
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.send_realtime(live_session))
                    tg.create_task(self.listen_audio())
                    tg.create_task(self.receive_audio(live_session))
                    tg.create_task(self.play_audio())
        except asyncio.CancelledError:
            pass
        finally:
            self._cleanup()

    def _cleanup(self):
        """Cleans up the PyAudio streams and resources."""
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None
        if self.speaker_stream:
            self.speaker_stream.stop_stream()
            self.speaker_stream.close()
            self.speaker_stream = None
        self.pya.terminate()
        print("\nAudio connection successfully closed.")


class GeminiLiveBridge:
    """
    WebSocket bridge between a browser client and the Gemini Live API.
    Receives text (and optionally raw PCM audio) from the browser,
    forwards it to Gemini Live, and streams back:
      - raw PCM audio bytes  (binary WebSocket frame)  → played in browser
      - JSON {type, content} frames                    → shown in chat UI
    """

    # Supported JSON message types sent to the browser
    MSG_USER_TEXT      = "user_text"
    MSG_ASSISTANT_TEXT = "assistant_text"
    MSG_TURN_COMPLETE  = "turn_complete"
    MSG_INTERRUPTED    = "interrupted"
    MSG_ERROR          = "error"

    def __init__(
        self,
        model: str = "gemini-3.1-flash-live-preview",
        system_instruction: str = "You are a helpful and friendly AI assistant.",
    ):
        self.client = genai.Client()
        self.model = model
        self.config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": system_instruction,
            "output_audio_transcription": {},
            "input_audio_transcription": {},
        }

    # ------------------------------------------------------------------
    # Public entry point called by the WebSocket server for each client
    # ------------------------------------------------------------------

    async def handle_client(self, websocket):
        """Manage the full lifecycle of one browser connection."""
        addr = getattr(websocket, "remote_address", "unknown")
        print(f"[Bridge] Client connected: {addr}")
        try:
            async with self.client.aio.live.connect(
                model=self.model, config=self.config
            ) as session:
                # Run both directions concurrently; cancel the other when one ends
                t_in  = asyncio.create_task(self._browser_to_gemini(websocket, session))
                t_out = asyncio.create_task(self._gemini_to_browser(websocket, session))
                done, pending = await asyncio.wait(
                    [t_in, t_out], return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                # Re-raise any exception from the completed task
                for task in done:
                    if not task.cancelled() and task.exception():
                        raise task.exception()
        except Exception as exc:
            print(f"[Bridge] Session error: {exc}")
            try:
                await websocket.send(json.dumps({"type": self.MSG_ERROR, "content": str(exc)}))
            except Exception:
                pass
        finally:
            print(f"[Bridge] Client disconnected: {addr}")

    # ------------------------------------------------------------------
    # Browser  →  Gemini
    # ------------------------------------------------------------------

    async def _browser_to_gemini(self, websocket, session):
        """Forward messages arriving from the browser to the Gemini session."""
        async for raw in websocket:
            if isinstance(raw, str):
                # JSON control message
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                msg_type = msg.get("type")
                if msg_type == "text":
                    content = msg.get("content", "").strip()
                    if content:
                        await session.send_client_content(
                            turns=types.Content(
                                role="user",
                                parts=[types.Part(text=content)],
                            ),
                            turn_complete=True,
                        )
                elif msg_type == "audio_end":
                    # User finished speaking - send turn_complete to Gemini
                    await session.send_client_content(turn_complete=True)
                    print("[Bridge] Received audio_end, sent turn_complete to Gemini")
            elif isinstance(raw, bytes):
                # Raw PCM audio from browser mic
                await session.send_realtime_input(
                    audio={"data": raw, "mime_type": "audio/pcm"}
                )

    # ------------------------------------------------------------------
    # Gemini  →  Browser
    # ------------------------------------------------------------------

    async def _gemini_to_browser(self, websocket, session):
        """Forward Gemini responses to the browser."""
        while True:
            turn = session.receive()
            async for response in turn:
                sc = response.server_content
                if not sc:
                    continue

                # --- audio chunks ---
                if sc.model_turn:
                    for part in sc.model_turn.parts:
                        if part.inline_data and isinstance(part.inline_data.data, bytes):
                            await websocket.send(part.inline_data.data)

                # --- assistant transcription ---
                if sc.output_transcription:
                    t = sc.output_transcription.text
                    if t:
                        await websocket.send(json.dumps({
                            "type": self.MSG_ASSISTANT_TEXT,
                            "content": t,
                        }))

                # --- user (input) transcription ---
                if sc.input_transcription:
                    t = sc.input_transcription.text
                    if t:
                        await websocket.send(json.dumps({
                            "type": self.MSG_USER_TEXT,
                            "content": t,
                        }))

                # --- interruption signal ---
                if getattr(sc, "interrupted", False):
                    await websocket.send(json.dumps({"type": self.MSG_INTERRUPTED}))

            # End of one turn
            await websocket.send(json.dumps({"type": self.MSG_TURN_COMPLETE}))
