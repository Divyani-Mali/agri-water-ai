"""Speech-to-text provider abstraction.

Supported providers
-------------------
mock            — always returns a fixed transcript; no credentials needed.
                  Useful for local development and automated tests.
openai_whisper  — calls OpenAI Whisper via the official openai SDK.
                  Requires OPENAI_API_KEY in the environment.

Selecting a provider
--------------------
Set STT_PROVIDER in your .env file:

    STT_PROVIDER=openai_whisper
    OPENAI_API_KEY=sk-...

Swapping the provider never requires changes to the chat router or any
other module; only this file and the env variable are involved.
"""
from __future__ import annotations

import abc
import io
import logging
import tempfile
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

# BCP-47 language codes that Whisper accepts for our three supported languages.
WHISPER_LANG = {"en": "en", "hi": "hi", "mr": "mr"}

# Audio MIME types we accept and their canonical extensions.
# We validate against file signatures (magic bytes) in addition to the declared
# content-type, so a renamed file is rejected.
ALLOWED_MIME_TYPES: dict[str, str] = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4": "mp4",
    "audio/mp3": "mp3",
    "audio/x-m4a": "m4a",
}

# Magic-byte signatures for a quick file-type sanity check.
_MAGIC: list[tuple[bytes, str]] = [
    (b"RIFF", "wav"),           # WAV (also covers .wav from browsers)
    (b"\x1aE\xdf\xa3", "webm"), # WebM / Matroska (browser MediaRecorder default)
    (b"OggS", "ogg"),           # Ogg Vorbis / Opus
    (b"ID3", "mp3"),            # MP3 with ID3 tag
    (b"\xff\xfb", "mp3"),       # MP3 raw frame
    (b"\xff\xf3", "mp3"),       # MP3 raw frame
    (b"\xff\xf2", "mp3"),       # MP3 raw frame
    (b"ftyp", "mp4"),           # MP4 / M4A (bytes 4-7)
]


# ------------------------------------------------------------------ validation helpers

def _sniff_format(header: bytes) -> str | None:
    """Return a format token from the first 12 bytes, or None if unrecognised."""
    for magic, fmt in _MAGIC:
        if header.startswith(magic):
            return fmt
    # MP4/M4A: ftyp box is at offset 4
    if len(header) >= 8 and header[4:8] == b"ftyp":
        return "mp4"
    return None


def _wav_duration_seconds(data: bytes) -> float | None:
    """Return the duration of a WAV file in seconds, or None if parsing fails."""
    try:
        with wave.open(io.BytesIO(data)) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / rate if rate > 0 else None
    except Exception:
        return None


def validate_audio(
    content_type: str,
    data: bytes,
    max_bytes: int,
    max_seconds: int,
) -> None:
    """Raise ValueError with a user-friendly message on any validation failure.

    Checks performed:
    1. Declared content-type is in the allow-list.
    2. File size is within the configured limit.
    3. Magic bytes match a recognised format.
    4. WAV duration is within the configured limit (best-effort for other formats).
    """
    # 1. Content-type check (browser/client declared)
    base_type = content_type.split(";")[0].strip().lower()
    if base_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Unsupported audio format '{base_type}'. "
            f"Accepted: {', '.join(sorted(ALLOWED_MIME_TYPES))}."
        )

    # 2. Size check
    if len(data) > max_bytes:
        raise ValueError(
            f"Audio file too large ({len(data) / 1_048_576:.1f} MB). "
            f"Maximum allowed: {max_bytes // 1_048_576} MB."
        )

    # 3. Magic-byte check
    header = data[:12]
    sniffed = _sniff_format(header)
    if sniffed is None:
        raise ValueError(
            "Audio file signature not recognised. "
            "Please upload a valid WAV, WebM, Ogg, MP3 or MP4/M4A file."
        )

    # 4. Duration check (WAV only — accurate; other formats best-effort via size proxy)
    if sniffed == "wav":
        duration = _wav_duration_seconds(data)
        if duration is not None and duration > max_seconds:
            raise ValueError(
                f"Audio too long ({duration:.1f} s). "
                f"Maximum allowed: {max_seconds} s."
            )


# ------------------------------------------------------------------ provider abstraction

class STTResult:
    """Value returned by every STT provider."""

    def __init__(self, transcript: str, detected_lang: str | None = None) -> None:
        # Raw text from the provider (may be empty string if speech was inaudible)
        self.transcript = transcript
        # BCP-47 language code detected by the provider, if available.
        # None means the provider did not report one (caller should fall back to
        # the lang supplied in the request).
        self.detected_lang = detected_lang

    def __repr__(self) -> str:  # pragma: no cover
        return f"STTResult(transcript={self.transcript!r}, detected_lang={self.detected_lang!r})"


class AbstractSTTProvider(abc.ABC):
    """Base class for every STT backend.

    Subclasses must implement ``transcribe``.
    """

    @abc.abstractmethod
    def transcribe(self, audio_path: Path, lang: str) -> STTResult:
        """Convert the audio file at *audio_path* to text.

        Parameters
        ----------
        audio_path:
            Path to a temporary audio file. The caller owns the file and will
            delete it after this method returns.
        lang:
            BCP-47 hint for the dominant language (``"en"`` / ``"hi"`` / ``"mr"``).
            Providers may ignore this if they auto-detect.

        Returns
        -------
        STTResult
            The transcription and optional detected language.

        Raises
        ------
        STTError
            On provider-side failure (network error, quota exceeded, etc.).
        """


class STTError(Exception):
    """Raised by a provider when transcription cannot be completed."""


# ------------------------------------------------------------------ mock provider

class MockSTTProvider(AbstractSTTProvider):
    """Deterministic provider for tests and local development.

    Returns a canned transcript that depends on the requested language so tests
    can verify that the language hint is forwarded correctly.  No network call
    is made and no credentials are required.

    Can be seeded with a fixed transcript for more specific test assertions:

        provider = MockSTTProvider(transcript="मला पाणी हवे")
    """

    _DEFAULT: dict[str, str] = {
        "en": "How much water does my field need?",
        "hi": "मुझे कितना पानी चाहिए?",
        "mr": "मला किती पाणी हवे?",
    }

    def __init__(self, transcript: str | None = None) -> None:
        self._transcript = transcript

    def transcribe(self, audio_path: Path, lang: str) -> STTResult:
        transcript = self._transcript or self._DEFAULT.get(lang, self._DEFAULT["en"])
        return STTResult(transcript=transcript, detected_lang=lang)


# ------------------------------------------------------------------ OpenAI Whisper provider

class OpenAIWhisperProvider(AbstractSTTProvider):
    """Calls OpenAI Whisper via the official ``openai`` Python SDK.

    Configuration
    -------------
    STT_PROVIDER=openai_whisper
    OPENAI_API_KEY=sk-...

    The model used is ``whisper-1`` (the only currently available Whisper model
    through the OpenAI API).  Whisper natively supports Hindi and Marathi
    alongside English, so no special handling is needed for the three target
    languages.

    ``lang`` is forwarded to Whisper as the ``language`` parameter.  This
    improves accuracy and avoids mis-detection for short or noisy utterances.
    For Marathi (``"mr"``) Whisper uses the ISO 639-1 code ``"mr"``; Whisper
    has strong Marathi support as of whisper-1.

    The provider raises ``STTError`` on any OpenAI-side failure so the caller
    can return a clean HTTP 503 without leaking SDK internals.
    """

    MODEL = "whisper-1"

    def __init__(self, api_key: str) -> None:
        try:
            import openai  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "The openai package is required for OpenAIWhisperProvider. "
                "Run: pip install openai"
            ) from exc

        self._client = openai.OpenAI(api_key=api_key)

    def transcribe(self, audio_path: Path, lang: str) -> STTResult:
        whisper_lang = WHISPER_LANG.get(lang, "en")
        try:
            with audio_path.open("rb") as fh:
                response = self._client.audio.transcriptions.create(
                    model=self.MODEL,
                    file=fh,
                    language=whisper_lang,
                    response_format="verbose_json",
                )
            transcript = response.text or ""
            detected = getattr(response, "language", None)
            return STTResult(transcript=transcript, detected_lang=detected or lang)
        except Exception as exc:
            logger.error("OpenAI Whisper error: %s", exc)
            raise STTError(f"Speech-to-text service error: {exc}") from exc


# ------------------------------------------------------------------ factory

def get_stt_provider() -> AbstractSTTProvider:
    """Return the configured STT provider instance.

    Called once per request; the returned object is lightweight and stateless.
    """
    from app.core.config import settings  # local import avoids circular deps at module load

    name = (settings.STT_PROVIDER or "mock").lower().strip()

    if name == "mock":
        return MockSTTProvider()

    if name == "openai_whisper":
        if not settings.OPENAI_API_KEY:
            raise STTError(
                "STT_PROVIDER is set to 'openai_whisper' but OPENAI_API_KEY is not "
                "configured. Set OPENAI_API_KEY in your .env file."
            )
        return OpenAIWhisperProvider(api_key=settings.OPENAI_API_KEY)

    raise STTError(
        f"Unknown STT_PROVIDER '{name}'. Supported values: 'mock', 'openai_whisper'."
    )
