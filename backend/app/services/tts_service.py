"""Text-to-speech provider abstraction.

Supported providers
-------------------
mock    — returns a minimal silent WAV; no credentials, no network.
          Use for local development and all automated tests.
openai  — calls the OpenAI Text-to-Speech API (tts-1 model).
          Reuses OPENAI_API_KEY.  Supports en, hi, mr via the alloy/nova/shimmer voices.
          Returns MP3.
google  — calls Google Cloud Text-to-Speech API.
          Requires a service-account credential file or ADC.
          Supports en-US, hi-IN, mr-IN  natively.
          Returns MP3.

Selecting a provider
--------------------
Set TTS_PROVIDER in your .env file:

    # OpenAI TTS
    TTS_PROVIDER=openai
    OPENAI_API_KEY=sk-...

    # Google Cloud TTS
    TTS_PROVIDER=google
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

Language mapping
----------------
The three application language codes map to provider-specific identifiers:

    Code   OpenAI voice   Google language code
    en     alloy          en-US
    hi     alloy          hi-IN
    mr     alloy          mr-IN

OpenAI TTS uses a single multilingual voice (alloy) which handles Devanagari
script naturally.  For Google Cloud TTS the language code drives the neural
voice selection; all three locales have WaveNet / Neural2 voices available.
"""
from __future__ import annotations

import abc
import io
import logging
import struct
import wave
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------  constants

SUPPORTED_LANGS = ("en", "hi", "mr")

# MIME type for each output format
FORMAT_MIME: dict[str, str] = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
}

# Google Cloud TTS language codes for our three locales
_GOOGLE_LANG: dict[str, str] = {
    "en": "en-US",
    "hi": "hi-IN",
    "mr": "mr-IN",
}

# Google Cloud TTS neural voice names (one per locale)
_GOOGLE_VOICE: dict[str, str] = {
    "en": "en-US-Neural2-F",
    "hi": "hi-IN-Neural2-A",
    "mr": "mr-IN-Standard-A",   # Neural2 not yet available for Marathi; Standard is fine
}


# ------------------------------------------------------------------  value objects

class TTSResult:
    """Audio produced by a TTS provider."""

    def __init__(self, audio_bytes: bytes, mime_type: str) -> None:
        if not audio_bytes:
            raise ValueError("TTS provider returned empty audio.")
        self.audio_bytes = audio_bytes
        # e.g. "audio/mpeg" or "audio/wav"
        self.mime_type = mime_type

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"TTSResult(mime_type={self.mime_type!r}, "
            f"size={len(self.audio_bytes)} bytes)"
        )


class TTSError(Exception):
    """Raised by a provider when speech cannot be generated."""


# ------------------------------------------------------------------  abstract base

class AbstractTTSProvider(abc.ABC):
    """Base class for every TTS backend.

    Subclasses must implement ``synthesise``.
    """

    @abc.abstractmethod
    def synthesise(self, text: str, lang: str) -> TTSResult:
        """Convert *text* into audio.

        Parameters
        ----------
        text:
            The speakable text to synthesise.  Callers must pass the output of
            ``i18n.speakable()`` so the text is already clean and TTS-friendly.
        lang:
            One of ``"en"``, ``"hi"``, ``"mr"``.

        Returns
        -------
        TTSResult
            The raw audio bytes and MIME type.

        Raises
        ------
        TTSError
            On any provider-side failure.
        """


# ------------------------------------------------------------------  mock provider

class MockTTSProvider(AbstractTTSProvider):
    """Deterministic provider for tests and local development.

    Returns a minimal valid WAV file containing silence.  The duration scales
    with the length of the input text (1 frame per character) so tests can
    detect length-proportional behaviour if needed.

    No network call is made and no credentials are required.
    """

    SAMPLE_RATE = 8000  # 8 kHz mono PCM — tiny but valid

    def synthesise(self, text: str, lang: str) -> TTSResult:
        num_frames = max(len(text), 1) * 10   # 10 silent frames per character
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)                     # 16-bit
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(b"\x00\x00" * num_frames)
        return TTSResult(audio_bytes=buf.getvalue(), mime_type="audio/wav")


# ------------------------------------------------------------------  OpenAI provider

class OpenAITTSProvider(AbstractTTSProvider):
    """Calls the OpenAI TTS API (model: tts-1).

    Configuration
    -------------
    TTS_PROVIDER=openai
    OPENAI_API_KEY=sk-...

    OpenAI TTS supports multilingual text natively; Devanagari (Hindi/Marathi)
    is handled by the alloy voice without any extra configuration.

    The model ``tts-1`` is used for low-latency responses.  ``tts-1-hd`` can be
    substituted in the MODEL constant for higher quality if latency is acceptable.

    Output format is MP3 (openai SDK default).
    """

    MODEL = "tts-1"
    VOICE = "alloy"   # multilingual voice; works for en/hi/mr

    def __init__(self, api_key: str) -> None:
        try:
            import openai  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "The openai package is required for OpenAITTSProvider. "
                "Run: pip install openai"
            ) from exc
        self._client = openai.OpenAI(api_key=api_key)

    def synthesise(self, text: str, lang: str) -> TTSResult:
        try:
            response = self._client.audio.speech.create(
                model=self.MODEL,
                voice=self.VOICE,
                input=text,
                response_format="mp3",
            )
            audio_bytes = response.read()
            return TTSResult(audio_bytes=audio_bytes, mime_type="audio/mpeg")
        except Exception as exc:
            logger.error("OpenAI TTS error: %s", exc)
            raise TTSError(f"Text-to-speech service error: {exc}") from exc


# ------------------------------------------------------------------  Google Cloud provider

class GoogleCloudTTSProvider(AbstractTTSProvider):
    """Calls the Google Cloud Text-to-Speech API.

    Configuration
    -------------
    TTS_PROVIDER=google
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
        OR rely on Application Default Credentials (ADC) set by the host.

    All three target locales have dedicated neural/WaveNet voices:
        en-US → en-US-Neural2-F
        hi-IN → hi-IN-Neural2-A
        mr-IN → mr-IN-Standard-A  (Neural2 not yet available for Marathi)

    Output is MP3 (LINEAR16 is also possible but larger).
    """

    def __init__(self, credentials_path: str = "") -> None:
        try:
            from google.cloud import texttospeech  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "The google-cloud-texttospeech package is required for "
                "GoogleCloudTTSProvider.  Run: pip install google-cloud-texttospeech"
            ) from exc

        import os
        if credentials_path:
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", credentials_path)

        self._texttospeech = texttospeech
        self._client = texttospeech.TextToSpeechClient()

    def synthesise(self, text: str, lang: str) -> TTSResult:
        tts = self._texttospeech
        language_code = _GOOGLE_LANG.get(lang, "en-US")
        voice_name = _GOOGLE_VOICE.get(lang, _GOOGLE_VOICE["en"])
        try:
            response = self._client.synthesize_speech(
                input=tts.SynthesisInput(text=text),
                voice=tts.VoiceSelectionParams(
                    language_code=language_code,
                    name=voice_name,
                ),
                audio_config=tts.AudioConfig(
                    audio_encoding=tts.AudioEncoding.MP3,
                ),
            )
            return TTSResult(
                audio_bytes=response.audio_content,
                mime_type="audio/mpeg",
            )
        except Exception as exc:
            logger.error("Google Cloud TTS error: %s", exc)
            raise TTSError(f"Text-to-speech service error: {exc}") from exc


# ------------------------------------------------------------------  factory

def get_tts_provider() -> AbstractTTSProvider:
    """Return the configured TTS provider instance.

    Called once per request; instances are lightweight and stateless.
    Raises ``TTSError`` for missing credentials or unknown provider name.
    """
    from app.core.config import settings  # local import avoids circular deps

    name = (settings.TTS_PROVIDER or "mock").lower().strip()

    if name == "mock":
        return MockTTSProvider()

    if name == "openai":
        if not settings.OPENAI_API_KEY:
            raise TTSError(
                "TTS_PROVIDER is set to 'openai' but OPENAI_API_KEY is not configured. "
                "Set OPENAI_API_KEY in your .env file."
            )
        return OpenAITTSProvider(api_key=settings.OPENAI_API_KEY)

    if name == "google":
        return GoogleCloudTTSProvider(
            credentials_path=settings.GOOGLE_APPLICATION_CREDENTIALS,
        )

    raise TTSError(
        f"Unknown TTS_PROVIDER '{name}'. Supported values: 'mock', 'openai', 'google'."
    )
