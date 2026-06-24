import io
import os
import tempfile
import threading
import wave
from abc import ABC, abstractmethod
from typing import Optional, Union

import pyaudio
from huggingface_hub import InferenceClient


class AudioRecorder:
    """
    Handles audio recording from the microphone using PyAudio.
    """

    def __init__(
        self,
        format_type: int = pyaudio.paInt16,
        channels: int = 1,
        rate: int = 16000,
        chunk_size: int = 1024,
    ) -> None:
        """
        Initializes the AudioRecorder.

        Args:
            format_type: The audio format (default: 16-bit PCM).
            channels: Number of audio channels (default: 1).
            rate: Sampling rate in Hz (default: 16000).
            chunk_size: Size of each audio chunk (default: 1024).
        """
        self.format = format_type
        self.channels = channels
        self.rate = rate
        self.chunk = chunk_size
        self.frames: list[bytes] = []
        self.recording = False
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.thread: Optional[threading.Thread] = None

    def start_recording(self) -> None:
        """
        Starts the audio recording process in a separate thread.
        """
        self.frames = []
        self.recording = True
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
        )
        self.thread = threading.Thread(target=self._recording_thread_logic)
        self.thread.start()

    def _recording_thread_logic(self) -> None:
        """
        Internal loop for reading audio chunks from the stream.
        """
        while self.recording:
            try:
                if self.stream:
                    data = self.stream.read(self.chunk)
                    self.frames.append(data)
            except Exception as e:
                print(f"Error during recording: {e}")
                break

    def stop_recording(self) -> bytes:
        """
        Stops the recording and returns the audio data as WAV bytes.

        Returns:
            The recorded audio data in WAV format.
        """
        self.recording = False
        if self.thread:
            self.thread.join()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        # Create WAV formatted data in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b"".join(self.frames))

        return wav_buffer.getvalue()


class ASREngine(ABC):
    """
    Abstract base class for Automatic Speech Recognition (ASR) engines.
    """

    @abstractmethod
    def transcribe(self, audio_source: Union[str, bytes]) -> str:
        """
        Transcribes the given audio data or file path.

        Args:
            audio_source: Either a path to an audio file or raw audio bytes.

        Returns:
            The transcribed text.
        """
        pass


class HubASREngine(ASREngine):
    """
    ASR engine that uses Hugging Face Inference API.
    """

    def __init__(
        self,
        model: str = "openai/whisper-large-v3-turbo",
        token: Optional[str] = None,
    ) -> None:
        """
        Initializes the HubASREngine.

        Args:
            model: The Hugging Face model ID.
            token: Hugging Face API token.
        """
        self.model = model
        self.token = token
        self.client: Optional[InferenceClient] = None

    def _ensure_client(self) -> None:
        """
        Ensures the Hugging Face InferenceClient is initialized.
        """
        if self.client is None:
            self.client = InferenceClient(model=self.model, token=self.token)

    def set_token(self, token: str) -> None:
        """
        Updates the API token and resets the client.

        Args:
            token: The new API token.
        """
        self.token = token
        self.client = None  # Force re-initialization

    def transcribe(self, audio_source: Union[str, bytes]) -> str:
        """
        Transcribes audio using the Hugging Face API.

        Args:
            audio_source: Path to an audio file or raw audio bytes.

        Returns:
            The transcribed text or an error message.
        """
        self._ensure_client()
        temp_path: Optional[str] = None
        try:
            if isinstance(audio_source, bytes):
                # Save bytes to a temp file for API compatibility
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(audio_source)
                    temp_path = tmp.name
                input_data = temp_path
            else:
                input_data = audio_source

            if self.client:
                result = self.client.automatic_speech_recognition(input_data)
                if hasattr(result, "text"):
                    return str(result.text)
                if isinstance(result, dict):
                    return str(result.get("text", ""))
                return str(result)
            return "Error: Inference client not initialized."
        except Exception as e:
            return f"Error during Hub ASR: {e}"
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass


class LocalASREngine(ASREngine):
    """
    ASR engine that runs locally using the Transformers pipeline.
    """

    def __init__(self, model: str = "openai/whisper-large-v3-turbo") -> None:
        """
        Initializes the LocalASREngine.

        Args:
            model: The Hugging Face model ID to be used locally.
        """
        self.model_name = model
        self.pipeline = None

    def _ensure_pipeline(self) -> None:
        """
        Lazy-loads the Transformers pipeline and necessary libraries.
        """
        if self.pipeline is None:
            import torch
            from transformers import pipeline

            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            self.pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                device=device,
                torch_dtype=dtype,
            )

    def transcribe(self, audio_source: Union[str, bytes]) -> str:
        """
        Transcribes audio locally.

        Args:
            audio_source: Path to an audio file or raw audio bytes.

        Returns:
            The transcribed text or an error message.
        """
        try:
            self._ensure_pipeline()
            if self.pipeline:
                result = self.pipeline(audio_source, return_timestamps=True)
                return str(result.get("text", ""))
            return "Error: Local pipeline not initialized."
        except Exception as e:
            return f"Error during Local ASR: {e}"


class ASRClient:
    """
    Main ASR client that switches between Hub and Local engines.
    """

    def __init__(
        self,
        mode: str = "hub",
        model: str = "openai/whisper-large-v3-turbo",
        token: Optional[str] = None,
    ) -> None:
        """
        Initializes the ASRClient.

        Args:
            mode: The ASR mode, either 'hub' or 'local'.
            model: The Hugging Face model ID.
            token: API token for Hub mode.
        """
        self.mode = mode.lower()
        self.hub_engine = HubASREngine(model=model, token=token)
        self.local_engine: Optional[LocalASREngine] = None
        self._local_model_name = model

    def set_mode(self, mode: str) -> None:
        """
        Changes the ASR operation mode.

        Args:
            mode: 'hub' or 'local'.
        """
        if mode.lower() in ["hub", "local"]:
            self.mode = mode.lower()

    def set_token(self, token: str) -> None:
        """
        Updates the API token for the Hub engine.

        Args:
            token: The new API token.
        """
        self.hub_engine.set_token(token)

    def transcribe_audio(self, audio_source: Union[str, bytes]) -> str:
        """
        Performs ASR on the input using the selected mode.

        Args:
            audio_source: Path to an audio file or raw audio bytes.

        Returns:
            The transcribed text.
        """
        if self.mode == "hub":
            return self.hub_engine.transcribe(audio_source)

        if self.local_engine is None:
            self.local_engine = LocalASREngine(model=self._local_model_name)
        return self.local_engine.transcribe(audio_source)

