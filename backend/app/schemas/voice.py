"""Pydantic schemas for voice-input and speech-output endpoints."""
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.chat import ChatResponse


class VoiceResponse(BaseModel):
    """Full response returned by POST /api/chat/voice.

    Fields
    ------
    transcription:
        The text that the speech-to-text provider extracted from the audio.
        May be an empty string if the audio was inaudible or contained only
        silence (the chatbot will then return an ``unknown`` intent reply).
    detected_lang:
        The language code the STT provider believes was spoken.
        One of ``"en"``, ``"hi"``, ``"mr"``.  Falls back to the ``lang``
        query parameter (or the user's saved preference) when the provider
        does not report a language.
    chat:
        The normal chatbot response, identical in structure to the response
        returned by POST /api/chat.  The transcribed text was passed to the
        existing chatbot service unchanged.
    """

    transcription: str
    detected_lang: str
    chat: ChatResponse


# ------------------------------------------------------------------  TTS schemas

class SpeechRequest(BaseModel):
    """Request body for POST /api/chat/speech."""

    model_config = {"json_schema_extra": {
        "example": {
            "text": "Soil moisture is 28 percent. Irrigation is not needed today.",
            "lang": "en",
        }
    }}

    text: str = Field(
        min_length=1,
        max_length=2000,
        description="The chatbot reply text to convert into speech.",
    )
    lang: str = Field(
        description="Language of the text: 'en', 'hi', or 'mr'.",
    )


class SpeechURLResponse(BaseModel):
    """Returned by POST /api/chat/speech?mode=url.

    Fields
    ------
    audio_id:
        Opaque token used to retrieve the audio via GET /api/chat/audio/{audio_id}.
        Single-use and expires after AUDIO_RETENTION_MINUTES minutes.
    mime_type:
        MIME type of the audio (e.g. ``"audio/mpeg"``).
    expires_in_seconds:
        Approximate lifetime of the audio_id.
    """

    audio_id: str
    mime_type: str
    expires_in_seconds: int


# ------------------------------------------------------------------  integrated voice-chat schema

class VoiceChatResponse(BaseModel):
    """Response returned by POST /api/chat/voice-chat.

    This endpoint runs the complete pipeline in a single request:
    audio upload → STT → chatbot → TTS (optional).

    Fields
    ------
    transcription:
        Text extracted from the uploaded audio by the STT provider.
    lang:
        Language code used throughout the pipeline: ``"en"``, ``"hi"``, or ``"mr"``.
        Reflects the STT provider's detection, falling back to the ``lang`` query
        parameter or the user's saved preference.
    chat:
        Full chatbot response (same structure as ``POST /api/chat``).  Always
        present; a TTS failure does not suppress the text response.
    audio_id:
        Opaque token to retrieve the generated speech audio via
        ``GET /api/chat/audio/{audio_id}``.  ``null`` when ``audio_mode`` is
        ``"none"`` or when TTS failed.
    audio_mime_type:
        MIME type of the generated audio (e.g. ``"audio/mpeg"``).  ``null`` when
        no audio was generated.
    audio_expires_in_seconds:
        Lifetime of the ``audio_id`` token in seconds.  ``null`` when no audio
        was generated.
    tts_error:
        Human-readable description of the TTS failure, if any.  ``null`` when
        speech generation succeeded or was not requested.  The presence of this
        field does not affect the HTTP status code — the response is always
        ``200 OK`` as long as STT and the chatbot succeeded.
    """

    transcription: str
    lang: str
    chat: ChatResponse
    audio_id: Optional[str] = None
    audio_mime_type: Optional[str] = None
    audio_expires_in_seconds: Optional[int] = None
    tts_error: Optional[str] = None
