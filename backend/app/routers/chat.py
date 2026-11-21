import logging
import os
import tempfile
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.database import get_db
from app.i18n import normalize_lang, speakable
from app.models.models import IrrigationLog, User
from app.routers.farms import get_field_or_404
from app.schemas.chat import ChatRequest, ChatResponse, IrrigationLogOut
from app.schemas.voice import SpeechRequest, SpeechURLResponse, VoiceChatResponse, VoiceResponse
from app.services import audio_store
from app.services import stt_service as _stt
from app.services import tts_service as _tts
from app.services.chat_service import handle_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return handle_message(db, user, data.message, data.lang)


# ------------------------------------------------------------------ voice input

@router.post(
    "/chat/voice",
    response_model=VoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Voice input: upload audio and receive a chatbot reply",
    description=(
        "Upload an audio recording. The backend converts the speech to text using "
        "the configured STT provider, then passes the transcription to the existing "
        "chatbot service and returns the chatbot reply together with the transcription.\n\n"
        "**Supported formats:** WAV, WebM, Ogg, MP3, MP4/M4A.\n\n"
        "**Rate limit:** shared with POST /api/chat (200 messages per user per day).\n\n"
        "**Audio is never stored permanently.** Temporary files are deleted immediately "
        "after transcription."
    ),
)
async def voice_chat(
    audio: UploadFile,
    lang: Optional[str] = Query(
        None,
        description="Language hint: 'en', 'hi', or 'mr'. Falls back to the user's saved preference.",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VoiceResponse:
    """
    Request
    -------
    ``multipart/form-data`` with a single file field named ``audio``.
    The ``Content-Type`` of the part must be one of the accepted audio MIME types.
    Optional query parameter ``lang`` hints the spoken language.

    Response
    --------
    ``VoiceResponse`` — see schema definition in ``app/schemas/voice.py``.

    Errors
    ------
    400  Transcription returned empty text (inaudible / silence-only audio).
    413  Audio file exceeds the size or duration limit.
    415  Unsupported audio format.
    503  STT provider unavailable or not configured.
    """
    # ---- resolve language hint ----------------------------------------
    resolved_lang = lang if lang in ("en", "hi", "mr") else normalize_lang(user.preferred_language)

    # ---- read upload into memory (enforces size limit before disk write) --
    max_bytes = settings.AUDIO_MAX_MB * 1_048_576
    # Read at most (max + 1) bytes so we detect oversized files cheaply.
    chunk = await audio.read(max_bytes + 1)

    if len(chunk) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Audio file too large. Maximum allowed size is {settings.AUDIO_MAX_MB} MB."
            ),
        )

    content_type: str = audio.content_type or "application/octet-stream"

    # ---- STT via shared pipeline helper ----------------------------------
    transcript, final_lang = _stt_pipeline(chunk, content_type, resolved_lang, max_bytes)

    # ---- pass transcript to existing chatbot service ---------------------
    chat_response = handle_message(db, user, transcript, final_lang)

    return VoiceResponse(
        transcription=transcript,
        detected_lang=final_lang,
        chat=chat_response,
    )


# ------------------------------------------------------------------ helpers

def _extension_for(content_type: str) -> str:
    """Return a file extension (with leading dot) for the given MIME type."""
    base = content_type.split(";")[0].strip().lower()
    ext = _stt.ALLOWED_MIME_TYPES.get(base, "bin")
    return f".{ext}"


def _stt_pipeline(
    chunk: bytes,
    content_type: str,
    resolved_lang: str,
    max_bytes: int,
) -> tuple[str, str]:
    """Run audio validation + STT transcription.  Returns (transcript, final_lang).

    Raises HTTPException on any failure so callers stay clean.
    This helper is shared by ``voice_chat`` and ``voice_chat_full``.
    """
    # validate format / size / WAV duration
    try:
        _stt.validate_audio(
            content_type=content_type,
            data=chunk,
            max_bytes=max_bytes,
            max_seconds=settings.AUDIO_MAX_SECONDS,
        )
    except ValueError as exc:
        msg = str(exc)
        if "format" in msg.lower() or "signature" in msg.lower():
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=msg)
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=msg)

    suffix = _extension_for(content_type)
    tmp_dir = settings.AUDIO_TEMP_DIR or None
    tmp_path: Optional[Path] = None

    try:
        fd, tmp_str = tempfile.mkstemp(suffix=suffix, prefix="stt_", dir=tmp_dir)
        tmp_path = Path(tmp_str)
        with os.fdopen(fd, "wb") as fh:
            fh.write(chunk)

        try:
            provider = _stt.get_stt_provider()
        except _stt.STTError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

        try:
            result = provider.transcribe(tmp_path, resolved_lang)
        except _stt.STTError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                logger.warning("Could not delete temp STT file: %s", tmp_path)

    transcript = result.transcript.strip()
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The audio did not contain recognisable speech. Please check your microphone and try again.",
        )

    detected = result.detected_lang or resolved_lang
    final_lang = detected if detected in ("en", "hi", "mr") else resolved_lang
    return transcript, final_lang


# ------------------------------------------------------------------ integrated voice-chat (STT + chatbot + TTS)

@router.post(
    "/chat/voice-chat",
    response_model=VoiceChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Integrated voice chat: audio → transcription → chatbot reply → speech",
    description=(
        "Single-request pipeline: upload audio, receive a spoken chatbot reply.\n\n"
        "**Steps performed:**\n"
        "1. Audio is validated and transcribed (STT).\n"
        "2. Transcription is sent to the existing chatbot service.\n"
        "3. The chatbot's `speech`-ready text is synthesised into audio (TTS).\n"
        "4. A structured JSON response is returned containing the transcription, "
        "detected language, full chatbot text reply, and an audio reference.\n\n"
        "**TTS is non-fatal:** if speech generation fails, the text response is still "
        "returned and `tts_error` explains what went wrong.\n\n"
        "**Audio modes** (query parameter `audio_mode`):\n"
        "* `url` *(default)* — audio stored in memory; retrieve with "
        "`GET /api/chat/audio/{audio_id}` within `AUDIO_RETENTION_MINUTES` minutes.\n"
        "* `none` — skips TTS entirely; useful when the client only needs text.\n\n"
        "**Rate limit:** shared with `POST /api/chat` (200 messages per user per day).\n\n"
        "**Supported upload formats:** WAV, WebM, Ogg, MP3, MP4/M4A."
    ),
)
async def voice_chat_full(
    audio: UploadFile,
    lang: Optional[str] = Query(
        None,
        description="Language hint: 'en', 'hi', or 'mr'. Falls back to user's saved preference.",
    ),
    audio_mode: Literal["url", "none"] = Query(
        "url",
        description=(
            "'url' generates speech and stores it for retrieval; "
            "'none' skips TTS and returns text only."
        ),
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VoiceChatResponse:
    """
    Request
    -------
    ``multipart/form-data`` with a single file field named ``audio``.

    Query parameters
    ----------------
    ``lang``        — language hint (optional)
    ``audio_mode``  — ``"url"`` (default) or ``"none"``

    Response (always JSON)
    ----------------------
    ``VoiceChatResponse`` — transcription, language, chatbot reply, audio reference.

    Errors (STT/chatbot failures abort the request)
    ------
    400  Inaudible audio / silence-only recording.
    401  Missing or invalid JWT.
    413  Audio too large or too long.
    415  Unsupported audio format.
    503  STT provider unavailable or not configured.

    TTS failures are reported inside the JSON body (``tts_error``), not as HTTP errors.
    """
    resolved_lang = lang if lang in ("en", "hi", "mr") else normalize_lang(user.preferred_language)

    # ---- read & size-guard upload ----------------------------------------
    max_bytes = settings.AUDIO_MAX_MB * 1_048_576
    chunk = await audio.read(max_bytes + 1)
    if len(chunk) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file too large. Maximum allowed size is {settings.AUDIO_MAX_MB} MB.",
        )

    content_type: str = audio.content_type or "application/octet-stream"

    # ---- STT ---------------------------------------------------------------
    # _stt_pipeline raises HTTPException on any hard failure.
    transcript, final_lang = _stt_pipeline(chunk, content_type, resolved_lang, max_bytes)

    # ---- chatbot -----------------------------------------------------------
    # handle_message owns rate-limiting; no separate counter needed.
    chat_response = handle_message(db, user, transcript, final_lang)

    # ---- TTS (non-fatal) ---------------------------------------------------
    audio_id: Optional[str] = None
    audio_mime_type: Optional[str] = None
    audio_expires_in_seconds: Optional[int] = None
    tts_error: Optional[str] = None

    if audio_mode != "none":
        # Use the speech-ready text that the chatbot already prepared.
        tts_text = chat_response.speech or speakable(chat_response.reply, final_lang)

        if tts_text and len(tts_text) <= settings.TTS_MAX_CHARS:
            try:
                tts_provider = _tts.get_tts_provider()
                tts_result = tts_provider.synthesise(tts_text, final_lang)
                audio_id = audio_store.put(
                    user_id=user.id,
                    audio_bytes=tts_result.audio_bytes,
                    mime_type=tts_result.mime_type,
                )
                audio_mime_type = tts_result.mime_type
                audio_expires_in_seconds = settings.AUDIO_RETENTION_MINUTES * 60
            except Exception as exc:
                # TTS failure is logged and surfaced in the response body,
                # but never raises an HTTP error.
                tts_error = str(exc)
                logger.warning("TTS failed in voice-chat pipeline: %s", exc)
        elif tts_text:
            tts_error = (
                f"Chatbot reply too long for speech synthesis "
                f"({len(tts_text)} chars, max {settings.TTS_MAX_CHARS})."
            )

    return VoiceChatResponse(
        transcription=transcript,
        lang=final_lang,
        chat=chat_response,
        audio_id=audio_id,
        audio_mime_type=audio_mime_type,
        audio_expires_in_seconds=audio_expires_in_seconds,
        tts_error=tts_error,
    )


# ------------------------------------------------------------------ text-to-speech

@router.post(
    "/chat/speech",
    summary="Text-to-speech: convert chatbot reply text into audio",
    description=(
        "Convert a chatbot text reply into spoken audio using the configured TTS provider.\n\n"
        "**Two response modes** (controlled by the ``mode`` query parameter):\n\n"
        "* ``stream`` *(default)* — audio bytes streamed inline as "
        "``audio/mpeg`` (or ``audio/wav`` for the mock provider).  "
        "The client plays the audio directly.\n\n"
        "* ``url`` — audio is stored temporarily in memory and an ``audio_id`` token "
        "is returned.  The client fetches the audio via "
        "``GET /api/chat/audio/{audio_id}`` within ``AUDIO_RETENTION_MINUTES`` minutes.\n\n"
        "**Input:** pass the ``speech`` field from the chatbot response (already "
        "cleaned up by ``speakable()``) or any plain text.  "
        "The backend applies ``speakable()`` again so double-processing is harmless.\n\n"
        "**Audio is never stored permanently.**"
    ),
)
async def speech(
    data: SpeechRequest,
    mode: Literal["stream", "url"] = Query(
        "stream",
        description="'stream' returns audio bytes inline; 'url' returns a retrieval token.",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Request body
    ------------
    ``{"text": "...", "lang": "en"}``

    ``lang`` must be one of ``"en"``, ``"hi"``, ``"mr"``.

    Response
    --------
    * mode=stream  → binary audio (Content-Type: audio/mpeg or audio/wav)
    * mode=url     → ``{"audio_id": "...", "mime_type": "...", "expires_in_seconds": N}``

    Errors
    ------
    400  Language not supported or text too long.
    503  TTS provider not configured or returned an error.
    """
    # ---- validate language -----------------------------------------------
    if data.lang not in ("en", "hi", "mr"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language '{data.lang}'. Must be 'en', 'hi', or 'mr'.",
        )

    # ---- clean text through speakable() ----------------------------------
    # speakable() idempotently converts symbols / dates to spoken form.
    # Passing the already-speakable speech field is safe; a plain reply field works too.
    clean_text = speakable(data.text.strip(), data.lang)

    # ---- enforce character limit -----------------------------------------
    if len(clean_text) > settings.TTS_MAX_CHARS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Text too long for speech synthesis ({len(clean_text)} characters). "
                f"Maximum: {settings.TTS_MAX_CHARS}."
            ),
        )

    # ---- get TTS provider ------------------------------------------------
    try:
        provider = _tts.get_tts_provider()
    except _tts.TTSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    # ---- synthesise -------------------------------------------------------
    try:
        result = provider.synthesise(clean_text, data.lang)
    except _tts.TTSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    # ---- return audio ----------------------------------------------------
    if mode == "stream":
        return Response(
            content=result.audio_bytes,
            media_type=result.mime_type,
            headers={"Content-Disposition": "inline; filename=speech.audio"},
        )

    # mode == "url"
    audio_id = audio_store.put(
        user_id=user.id,
        audio_bytes=result.audio_bytes,
        mime_type=result.mime_type,
    )
    return SpeechURLResponse(
        audio_id=audio_id,
        mime_type=result.mime_type,
        expires_in_seconds=settings.AUDIO_RETENTION_MINUTES * 60,
    )


@router.get(
    "/chat/audio/{audio_id}",
    summary="Retrieve TTS audio by ID",
    description=(
        "Retrieve audio generated by a previous call to "
        "``POST /api/chat/speech?mode=url``.\n\n"
        "The token is **single-use**: it is deleted immediately after a successful "
        "download.  It also expires after ``AUDIO_RETENTION_MINUTES`` minutes "
        "regardless of whether it has been fetched.\n\n"
        "Only the user who requested the audio can retrieve it."
    ),
)
def get_audio(
    audio_id: str,
    user: User = Depends(get_current_user),
):
    """
    Response
    --------
    Binary audio bytes (Content-Type matches what was generated).

    Errors
    ------
    404  Token not found, already used, expired, or belongs to another user.
    """
    # Eviction runs inside audio_store.get(); stale entries are pruned automatically.
    entry = audio_store.get(
        audio_id=audio_id,
        user_id=user.id,
        retention_minutes=settings.AUDIO_RETENTION_MINUTES,
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found, already used, or expired.",
        )
    audio_bytes, mime_type = entry
    return Response(
        content=audio_bytes,
        media_type=mime_type,
        headers={"Content-Disposition": "inline; filename=speech.audio"},
    )


@router.get("/fields/{field_id}/irrigation-logs", response_model=list[IrrigationLogOut])
def list_irrigation_logs(
    field_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    field = get_field_or_404(db, field_id, user)
    return (
        db.query(IrrigationLog)
        .filter(IrrigationLog.field_id == field.id)
        .order_by(IrrigationLog.created_at.desc(), IrrigationLog.id.desc())
        .limit(limit)
        .all()
    )