import asyncio
import json
import logging
import pyaudio
from google import genai
from google.genai import types
from fastapi import WebSocket, WebSocketDisconnect

# Import Langfuse components for telemetry
from langfuse import observe, get_client, propagate_attributes

# Setup basic logging format
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class GeminiLiveAudio:
    """
    Class to encapsulate the full-duplex live multimodal interaction
    via the Gemini Live API. (Primarily used for testing/local CLI).
    """

    def __init__(self, model: str = "gemini-3.1-flash-live-preview",
                 system_instruction: str = "You are a helpful and friendly AI assistant."):
        """
        Initializes the live audio interface logic.

        Parameters:
            model (str): The GenAI model to use.
            system_instruction (str): The prompt that dictates AI behavior.
        """
        self.client = genai.Client()
        self.model = model
        self.config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": system_instruction,
            "output_audio_transcription": {},
            "input_audio_transcription": {},
        }
        
        # Audio configuration constants
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

    async def listen_audio(self) -> None:
        """
        Listens for local microphone audio and enqueues it.
        """
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
        # Avoid overflow exception logic when debug is on
        kwargs = {"exception_on_overflow": False} if __debug__ else {}
        while True:
            try:
                data = await asyncio.to_thread(
                    self.audio_stream.read, self.CHUNK_SIZE, **kwargs
                )
                await self.audio_queue_mic.put(
                    {"data": data, "mime_type": "audio/pcm"}
                )
            except Exception as error:
                logger.error(f"[GeminiLiveAudio] Error reading audio: {error}")
                break

    async def send_realtime(self, session) -> None:
        """
        Sends audio from the microphone queue to the GenAI remote session.

        Parameters:
            session: The active GenAI session object.
        """
        while True:
            try:
                message = await self.audio_queue_mic.get()
                await session.send_realtime_input(audio=message)
            except asyncio.CancelledError:
                logger.info("[GeminiLiveAudio] Send task cancelled.")
                break
            except Exception as error:
                logger.error(f"[GeminiLiveAudio] Error sending input: {error}")
                break

    async def receive_audio(self, session) -> None:
        """
        Receives responses from GenAI and queues the audio for playback.

        Parameters:
            session: The active GenAI session object.
        """
        last_was_input = False
        while True:
            try:
                turn = session.receive()
                async for response in turn:
                    content = response.server_content
                    if not content:
                        continue
                    # Process audio model segments
                    if content.model_turn:
                        for part in content.model_turn.parts:
                            if part.inline_data and isinstance(
                                part.inline_data.data, bytes):
                                self.audio_queue_output.put_nowait(
                                    part.inline_data.data
                                )
                    # Print AI transcript
                    if content.output_transcription:
                        if last_was_input:
                            print()
                            last_was_input = False
                        text = content.output_transcription.text
                        print(text, end="", flush=True)
                        if text.rstrip()[-1:] in '.!?':
                            print()
                    # Print User transcript
                    if content.input_transcription:
                        if not last_was_input:
                            print()
                            last_was_input = True
                        text = content.input_transcription.text
                        print(f"\033[3m{text}\033[0m", end="", flush=True)
                        if text.rstrip()[-1:] in '.!?':
                            print()

                # On interruption, empty the playback queue to stop sound
                while not self.audio_queue_output.empty():
                    self.audio_queue_output.get_nowait()
            except asyncio.CancelledError:
                logger.info("[GeminiLiveAudio] Receiving cancelled gracefully.")
                break
            except Exception as error:
                logger.error(f"[GeminiLiveAudio] Error receiving: {error}")
                break

    async def play_audio(self) -> None:
        """
        Plays back audio data fetched from the output queue to speakers.
        """
        self.speaker_stream = await asyncio.to_thread(
            self.pya.open,
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            try:
                bytestream = await self.audio_queue_output.get()
                await asyncio.to_thread(self.speaker_stream.write, bytestream)
            except asyncio.CancelledError:
                logger.info("[GeminiLiveAudio] Play audio task cancelled.")
                break
            except Exception as error:
                logger.error(f"[GeminiLiveAudio] Play error: {error}")
                break

    async def run(self) -> None:
        """
        Main function to run the audio interaction tasks together.
        """
        try:
            async with self.client.aio.live.connect(
                model=self.model, config=self.config
            ) as live_session:
                print(f"Connected to Gemini ({self.model}). Start speaking!")
                async with asyncio.TaskGroup() as task_group:
                    task_group.create_task(self.send_realtime(live_session))
                    task_group.create_task(self.listen_audio())
                    task_group.create_task(self.receive_audio(live_session))
                    task_group.create_task(self.play_audio())
        except asyncio.CancelledError:
            logger.info("[GeminiLiveAudio] Main run loop cancelled.")
        except Exception as error:
            logger.error(f"[GeminiLiveAudio] Unexpected error in loop: {error}")
        finally:
            self.clean_up()

    def clean_up(self) -> None:
        """
        Cleans up system IO resources related to PyAudio.
        """
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None
        if self.speaker_stream:
            self.speaker_stream.stop_stream()
            self.speaker_stream.close()
            self.speaker_stream = None
        self.pya.terminate()
        logger.info("[GeminiLiveAudio] Audio connection successfully closed.")


class GeminiLiveBridge:
    """
    FastAPI WebSocket bridge connecting a web client API interactions.
    Includes built-in Langfuse telemetry integration.
    """
    
    MSG_USER_TEXT      = "user_text"
    MSG_ASSISTANT_TEXT = "assistant_text"
    MSG_TURN_COMPLETE  = "turn_complete"
    MSG_INTERRUPTED    = "interrupted"
    MSG_ERROR          = "error"

    def __init__(self, model: str = "gemini-3.1-flash-live-preview",
                 system_instruction: str = "You are a helpful AI assistant."):
        """
        Initializes the bridge for network relaying logic.

        Parameters:
            model (str): The specific GenAI model key.
            system_instruction (str): Instructions for the system logic.
        """
        self.client = genai.Client()
        self.model = model
        self.config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": system_instruction,
            "output_audio_transcription": {},
            "input_audio_transcription": {},
        }

    @observe(name="WebSocket_Voice_Session")
    async def handle_client(self, websocket: WebSocket) -> None:
        """
        Manage the complete interaction loop over one WebSocket connection.

        Parameters:
            websocket (WebSocket): Client socket connection.
        """
        client_info = websocket.client
        address = (f"{client_info.host}:{client_info.port}" 
                   if client_info else "unknown")
        logger.info(f"[Bridge] Client connected: {address}")
        
        # Setting conversational telemetry spanning context info
        with propagate_attributes(
            session_id=address,
            tags=["websocket", "live-audio"],
            metadata={"model": self.model}
        ):
            try:
                async with self.client.aio.live.connect(
                    model=self.model, config=self.config
                ) as session:
                    
                    task_in = asyncio.create_task(
                        self.relay_browser_to_gemini(websocket, session)
                    )
                    task_out = asyncio.create_task(
                        self.relay_gemini_to_browser(websocket, session)
                    )
                    
                    done, pending = await asyncio.wait(
                        [task_in, task_out],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for task in pending:
                        task.cancel()
                    for task in done:
                        if not task.cancelled() and task.exception():
                            raise task.exception()
                            
            except WebSocketDisconnect:
                logger.info(f"[Bridge] Client gracefully unbound: {address}")
            except Exception as exception:
                logger.error(f"[Bridge] Session disruption error: {exception}")
                try:
                    await websocket.send_text(
                        json.dumps({"type": self.MSG_ERROR, 
                                    "content": str(exception)})
                    )
                except Exception as send_error:
                    logger.error(f"[Bridge] Client messaging gap: {send_error}")
            finally:
                logger.info(f"[Bridge] Fully disengaging logic on {address}")
                # Ensure pending sync metrics commit safely to Langfuse targets
                get_client().flush()

    def log_conversational_turn(self, user_text: str, ai_text: str) -> None:
        """
        Tracks a finalized Q&A message transaction record.

        Parameters:
            user_text (str): Incoming prompt data text summary.
            ai_text (str): Computed answer response details text.
        """
        langfuse = get_client()
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="Live_Voice_Turn",
            model=self.model,
            input=user_text.strip() if user_text else "[Audio Input]"
        ) as generation:
            generation.update(output=ai_text.strip())

    async def relay_browser_to_gemini(self, websocket: WebSocket, 
                                      session) -> None:
        """
        Receive browser WebSocket messages and format them for Gemini Live.

        Parameters:
            websocket (WebSocket): The client data channel interface object.
            session: Target GenAI model context proxy.
        """
        try:
            while True:
                message = await websocket.receive()
                
                if message["type"] == "websocket.disconnect":
                    break
                
                if "text" in message:
                    try:
                        parsed = json.loads(message["text"])
                    except json.JSONDecodeError as decode_error:
                        logger.warning(
                            f"[Bridge] Malformed client packet: {decode_error}"
                        )
                        continue
                        
                    message_type = parsed.get("type")
                    if message_type == "text":
                        content = parsed.get("content", "").strip()
                        if content:
                            await session.send_client_content(
                                turns=types.Content(
                                    role="user",
                                    parts=[types.Part(text=content)],
                                ),
                                turn_complete=True,
                            )
                    elif message_type == "audio_end":
                        await session.send_client_content(turn_complete=True)
                        
                elif "bytes" in message:
                    await session.send_realtime_input(
                        audio={"data": message["bytes"], "mime_type": "audio/pcm"}
                    )
        except WebSocketDisconnect:
            logger.info("[Bridge] Input intake closed orderly.")
        except Exception as error:
            logger.error(f"[Bridge] Failed propagating upload chunk: {error}")

    async def relay_gemini_to_browser(self, websocket: WebSocket,
                                      session) -> None:
        """
        Unpack remote Gemini system streaming events to Web format for sending.

        Parameters:
            websocket (WebSocket): Connection pipeline returning status strings.
            session: Origin context returning GenAI objects.
        """
        try:
            while True:
                turn = session.receive()
                
                turn_user_text = ""
                turn_ai_text = ""
                
                async for response in turn:
                    content = response.server_content
                    if not content:
                        continue

                    # Forward generated streaming audio frames directly
                    if content.model_turn:
                        for part in content.model_turn.parts:
                            if part.inline_data and isinstance(
                                part.inline_data.data, bytes):
                                await websocket.send_bytes(part.inline_data.data)

                    # Accumulate transcription blocks targeting final payload logging
                    if content.output_transcription:
                        text = content.output_transcription.text
                        if text:
                            turn_ai_text += text
                            await websocket.send_text(json.dumps({
                                "type": self.MSG_ASSISTANT_TEXT,
                                "content": text,
                            }))

                    if content.input_transcription:
                        text = content.input_transcription.text
                        if text:
                            turn_user_text += text
                            await websocket.send_text(json.dumps({
                                "type": self.MSG_USER_TEXT,
                                "content": text,
                            }))

                    # Notify browser player instances about preemptions
                    if getattr(content, "interrupted", False):
                        await websocket.send_text(
                            json.dumps({"type": self.MSG_INTERRUPTED})
                        )

                if turn_user_text or turn_ai_text:
                    self.log_conversational_turn(turn_user_text, turn_ai_text)

                await websocket.send_text(
                    json.dumps({"type": self.MSG_TURN_COMPLETE})
                )
        except WebSocketDisconnect:
            logger.info("[Bridge] Download transmission terminated.")
        except asyncio.CancelledError:
            logger.info("[Bridge] Session process gracefully ended.")
        except Exception as error:
            logger.error(f"[Bridge] Async relay task failure: {error}")


class GeminiTextChat:
    """
    Standard text messaging mechanism querying Gemini.
    """

    def __init__(self, model: str = "gemini-3.1-flash-lite"):
        """
        Creates a text focused API structure entity.

        Parameters:
            model (str): ID of model targeting lightweight string replies.
        """
        self.client = genai.Client()
        self.model = model

    async def generate_response(self, user_text: str) -> str:
        """
        Execute API request for prompt response string.

        Parameters:
            user_text (str): Incoming prompt information for generation.

        Returns:
            str: Full response paragraph result completion block.
        """
        langfuse = get_client()
        with langfuse.start_as_current_observation(
            as_type="generation", 
            name="REST_Chat_Invoke",
            model=self.model,
            input=user_text
        ) as generation:
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=user_text
                )
                
                generation.update(output=response.text)
                return response.text
                
            except Exception as error:
                generation.update(level="ERROR", status_message=str(error))
                logger.error(f"[GeminiTextChat] Call generation broken: {error}")
                raise error