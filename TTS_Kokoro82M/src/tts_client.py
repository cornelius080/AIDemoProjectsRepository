from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Iterator

from huggingface_hub import InferenceClient


class TTSClient:
    """
    A tiny wrapper around ``huggingface_hub.InferenceClient`` that focuses on
    text-to-speech (TTS) calls.

    The class is intentionally simple:
        * constructor accepts only ``provider`` (default = "replicate") and
          ``model`` (default = "hexgrad/Kokoro-82M");
        * the two synthesis methods require the user to provide *text* and *voice*.
    """

    def __init__(self, provider: str = "replicate", model: str = "hexgrad/Kokoro-82M") -> None:
        self.provider = provider
        self.model = model

        token = os.getenv("HF_TOKEN_READ")
        if token is None:
            raise RuntimeError(
                "Missing HuggingFace token. Set the environment variable "
                "HF_TOKEN_READ or pass an explicit token to InferenceClient."
            )
        
        self._client = InferenceClient(provider=self.provider, api_key=token)

    
    def synthesize(self, text: str, voice: str) -> bytes:
        """
        Synthesize ``text`` using ``voice`` and the default model/provider.

        Parameters
        ----------
        text : str
            The textual content that will be spoken.
        voice : str
            One of the voice identifiers supported by the chosen model.

        Returns
        -------
        bytes
            Raw audio bytes (usually a WAV stream, format depends on the model).

        Raises
        ------
        ValueError
            If ``text`` is empty or only whitespace.
        """
        if not text.strip():
            raise ValueError("`text` must contain at least one non‑whitespace character.")

        # ``InferenceClient.text_to_speech`` expects the voice inside ``extra_body``.
        extra_body = {"voice": voice}

        # The client returns a generator of binary chunks; we concatenate them.
        audio: bytes = self._client.text_to_speech(
            text=text,
            model=self.model,
            extra_body=extra_body,
        )
        return audio

    def synthesize_to_file(
        self,
        output_path: Path | str,
        text: str,
        voice: str,
    ) -> Path:
        """
        Convenience wrapper that synthesises ``text`` with ``voice`` and writes the
        resulting audio to ``output_path``.

        Parameters
        ----------
        output_path : Path | str
            Destination file (e.g. ``"hello.wav"``).
        text : str
            Text to be spoken.
        voice : str
            Voice identifier.

        Returns
        -------
        Path
            The same ``output_path`` object (useful for chaining calls).
        """
        audio_bytes = self.synthesize(text=text, voice=voice)
        out_file = Path(output_path)
        out_file.write_bytes(audio_bytes)
        return out_file
