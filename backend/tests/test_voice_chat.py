"""Integration tests for POST /api/chat/voice-chat.

This endpoint runs the full pipeline in one request:
    audio upload → STT → chatbot → TTS → structured JSON response.

All external providers are mocked; no network calls or paid credentials
are needed.  The existing STT and TTS provider tests are unmodified.

Test categories
---------------
1.  Happy-path — URL audio mode (default): en / hi / mr all produce a
    VoiceChatResponse with transcription, chat reply, and an audio_id.
2.  audio_mode=none — TTS is skipped; audio fields are null.
3.  Audio retrieval — the audio_id returned can be fetched via GET /api/chat/audio/.
4.  Language propagation — STT-detected language is used for chatbot and TTS.
5.  TTS failure is non-fatal — text reply still returned, tts_error is set.
6.  STT failures abort with the correct HTTP status codes.
7.  Auth — missing / invalid token returns 401.
8.  Rate limiting — shared counter with /api/chat.
9.  Upload validation — format, size and duration limits.
10. Regression — existing /api/chat, /api/chat/voice and /api/chat/speech unchanged.
"""
import io
import wave

import pytest

from app.core.config import settings
from app.services import audio_store
from app.services.stt_service import MockSTTProvider, STTError, STTResult
from app.services.tts_service import MockTTSProvider, TTSError, TTSResult
from chat_helpers import register, seed_field


# ------------------------------------------------------------------ audio helpers

def _make_wav(duration_seconds: float = 0.3, sample_rate: int = 16000) -> bytes:
    num_frames = int(sample_rate * duration_seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


def _make_webm() -> bytes:
    return b"\x1a\x45\xdf\xa3" + b"\x00" * 100


def _post_vc(client, headers, audio_bytes=None, content_type="audio/wav",
             lang=None, audio_mode=None):
    """Helper: POST to /api/chat/voice-chat."""
    if audio_bytes is None:
        audio_bytes = _make_wav()
    params = {}
    if lang:
        params["lang"] = lang
    if audio_mode:
        params["audio_mode"] = audio_mode
    return client.post(
        "/api/chat/voice-chat",
        files={"audio": ("rec.wav", audio_bytes, content_type)},
        headers=headers,
        params=params,
    )


# ------------------------------------------------------------------ fixtures

@pytest.fixture(autouse=True)
def use_mock_providers(monkeypatch):
    monkeypatch.setattr(settings, "STT_PROVIDER", "mock")
    monkeypatch.setattr(settings, "TTS_PROVIDER", "mock")


@pytest.fixture(autouse=True)
def reset_audio_store():
    audio_store.clear()
    yield
    audio_store.clear()


@pytest.fixture(autouse=True)
def reset_chat_usage():
    from app.services import chat_service
    chat_service._usage.clear()


# ------------------------------------------------------------------ 1. happy-path URL mode

def test_english_pipeline_returns_all_fields(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    r = _post_vc(client, h, lang="en", audio_mode="url")

    assert r.status_code == 200, r.text
    body = r.json()

    # STT output
    assert body["transcription"] == MockSTTProvider._DEFAULT["en"]
    assert body["lang"] == "en"

    # Chatbot output — full ChatResponse structure
    assert "reply" in body["chat"]
    assert "speech" in body["chat"]
    assert "intent" in body["chat"]
    assert body["chat"]["lang"] == "en"

    # TTS output
    assert body["audio_id"] is not None
    assert body["audio_mime_type"] is not None
    assert body["audio_expires_in_seconds"] is not None
    assert body["audio_expires_in_seconds"] > 0
    assert body["tts_error"] is None


def test_hindi_pipeline_uses_hindi_throughout(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "hi")
    seed_field("a@test.com")

    r = _post_vc(client, h, lang="hi", audio_mode="url")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lang"] == "hi"
    assert body["transcription"] == MockSTTProvider._DEFAULT["hi"]
    assert body["chat"]["lang"] == "hi"
    assert body["audio_id"] is not None


def test_marathi_pipeline_uses_marathi_throughout(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "mr")
    seed_field("a@test.com")

    r = _post_vc(client, h, lang="mr", audio_mode="url")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lang"] == "mr"
    assert body["transcription"] == MockSTTProvider._DEFAULT["mr"]
    assert body["chat"]["lang"] == "mr"
    assert body["audio_id"] is not None


def test_default_audio_mode_is_url(client):
    """Omitting audio_mode behaves the same as audio_mode=url."""
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    r = _post_vc(client, h, lang="en")   # no audio_mode param

    assert r.status_code == 200, r.text
    assert r.json()["audio_id"] is not None


# ------------------------------------------------------------------ 2. audio_mode=none skips TTS

def test_audio_mode_none_skips_tts(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    r = _post_vc(client, h, lang="en", audio_mode="none")

    assert r.status_code == 200, r.text
    body = r.json()
    # Text response must still be present
    assert body["transcription"]
    assert body["chat"]["reply"]
    # Audio fields must all be null
    assert body["audio_id"] is None
    assert body["audio_mime_type"] is None
    assert body["audio_expires_in_seconds"] is None
    assert body["tts_error"] is None


def test_audio_mode_none_stores_nothing_in_audio_store(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    _post_vc(client, h, lang="en", audio_mode="none")
    assert audio_store.size() == 0


# ------------------------------------------------------------------ 3. audio retrieval

def test_audio_id_can_be_fetched(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    body = _post_vc(client, h, lang="en", audio_mode="url").json()
    audio_id = body["audio_id"]

    r = client.get(f"/api/chat/audio/{audio_id}", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("audio/")
    assert len(r.content) > 0


def test_audio_id_is_single_use(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    body = _post_vc(client, h, lang="en", audio_mode="url").json()
    audio_id = body["audio_id"]

    r1 = client.get(f"/api/chat/audio/{audio_id}", headers=h)
    r2 = client.get(f"/api/chat/audio/{audio_id}", headers=h)
    assert r1.status_code == 200
    assert r2.status_code == 404


def test_other_user_cannot_fetch_audio(client):
    register(client, "admin@test.com")
    h_a = register(client, "a@test.com")
    h_b = register(client, "b@test.com")
    seed_field("a@test.com")

    body = _post_vc(client, h_a, lang="en", audio_mode="url").json()
    audio_id = body["audio_id"]

    assert client.get(f"/api/chat/audio/{audio_id}", headers=h_b).status_code == 404


# ------------------------------------------------------------------ 4. language propagation

def test_stt_detected_language_is_used_for_chatbot_and_tts(client, monkeypatch):
    """When the STT provider detects a different language than the hint,
    the detected language flows through to the chatbot and TTS."""
    from app.routers import chat as chat_router

    class _MarathiSTT:
        def transcribe(self, path, lang):
            return STTResult(transcript="मला किती पाणी हवे?", detected_lang="mr")

    monkeypatch.setattr(chat_router._stt, "get_stt_provider", lambda: _MarathiSTT())

    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    r = _post_vc(client, h, lang="en", audio_mode="url")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lang"] == "mr"
    assert body["chat"]["lang"] == "mr"
    assert body["audio_id"] is not None   # TTS ran with Marathi


def test_user_preference_used_when_no_lang_hint(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "hi")   # saved preference = Hindi
    seed_field("a@test.com")

    r = _post_vc(client, h)   # no lang param

    body = r.json()
    assert body["lang"] == "hi"
    assert body["chat"]["lang"] == "hi"


# ------------------------------------------------------------------ 5. TTS failure is non-fatal

def test_tts_failure_still_returns_text_response(client, monkeypatch):
    from app.routers import chat as chat_router

    class _FailingTTS:
        def synthesise(self, text, lang):
            raise TTSError("Simulated TTS failure")

    monkeypatch.setattr(chat_router._tts, "get_tts_provider", lambda: _FailingTTS())

    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    r = _post_vc(client, h, lang="en", audio_mode="url")

    # HTTP status is still 200
    assert r.status_code == 200, r.text
    body = r.json()

    # Text response is complete
    assert body["transcription"]
    assert body["chat"]["reply"]
    assert body["chat"]["lang"] == "en"

    # Audio fields are null; tts_error explains why
    assert body["audio_id"] is None
    assert body["audio_mime_type"] is None
    assert body["tts_error"] is not None
    assert "tts failure" in body["tts_error"].lower()


def test_tts_provider_config_error_is_non_fatal(client, monkeypatch):
    monkeypatch.setattr(settings, "TTS_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")   # misconfigured

    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    r = _post_vc(client, h, lang="en", audio_mode="url")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chat"]["reply"]          # text still present
    assert body["audio_id"] is None       # no audio
    assert body["tts_error"] is not None  # explains the failure


# ------------------------------------------------------------------ 6. STT failures abort

def test_stt_provider_config_error_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "STT_PROVIDER", "openai_whisper")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    r = _post_vc(client, h)
    assert r.status_code == 503


def test_stt_runtime_error_returns_503(client, monkeypatch):
    from app.routers import chat as chat_router

    class _FailingSTT:
        def transcribe(self, path, lang):
            raise STTError("Simulated STT failure")

    monkeypatch.setattr(chat_router._stt, "get_stt_provider", lambda: _FailingSTT())

    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    r = _post_vc(client, h)
    assert r.status_code == 503


def test_empty_transcription_returns_400(client, monkeypatch):
    from app.routers import chat as chat_router

    class _SilentSTT:
        def transcribe(self, path, lang):
            return STTResult(transcript="", detected_lang=lang)

    monkeypatch.setattr(chat_router._stt, "get_stt_provider", lambda: _SilentSTT())

    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    r = _post_vc(client, h)
    assert r.status_code == 400


# ------------------------------------------------------------------ 7. auth

def test_requires_authentication(client):
    r = client.post(
        "/api/chat/voice-chat",
        files={"audio": ("rec.wav", _make_wav(), "audio/wav")},
    )
    assert r.status_code == 401


def test_rejects_invalid_token(client):
    r = client.post(
        "/api/chat/voice-chat",
        files={"audio": ("rec.wav", _make_wav(), "audio/wav")},
        headers={"Authorization": "Bearer notvalid"},
    )
    assert r.status_code == 401


# ------------------------------------------------------------------ 8. rate limiting

def test_voice_chat_counts_toward_daily_limit(client, monkeypatch):
    from app.services import chat_service
    monkeypatch.setattr(chat_service, "MAX_MESSAGES_PER_DAY", 2)

    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    r1 = _post_vc(client, h, lang="en", audio_mode="url")
    r2 = _post_vc(client, h, lang="en", audio_mode="url")
    # Both succeed
    assert r1.status_code == 200
    assert r2.status_code == 200

    # Third call: limit hit — chatbot returns intent="limit", still 200
    r3 = _post_vc(client, h, lang="en", audio_mode="url")
    assert r3.status_code == 200
    assert r3.json()["chat"]["intent"] == "limit"


def test_voice_chat_and_text_chat_share_the_same_counter(client, monkeypatch):
    from app.services import chat_service
    monkeypatch.setattr(chat_service, "MAX_MESSAGES_PER_DAY", 1)

    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    # Consume the one allowed message via text chat
    client.post("/api/chat", json={"message": "hello"}, headers=h)

    # voice-chat should now hit the limit
    r = _post_vc(client, h, lang="en", audio_mode="url")
    assert r.status_code == 200
    assert r.json()["chat"]["intent"] == "limit"


# ------------------------------------------------------------------ 9. upload validation

def test_unsupported_format_returns_415(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _post_vc(client, h, audio_bytes=b"FAKE", content_type="video/mp4")
    assert r.status_code == 415


def test_bad_magic_bytes_returns_415(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _post_vc(client, h, audio_bytes=b"GARBAGE_BYTES_XXXX", content_type="audio/wav")
    assert r.status_code == 415


def test_oversized_file_returns_413(client, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_MAX_MB", 1)
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    big = b"\x00" * (1 * 1_048_576 + 1)
    r = _post_vc(client, h, audio_bytes=big)
    assert r.status_code == 413


def test_wav_too_long_returns_413(client, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_MAX_SECONDS", 1)
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _post_vc(client, h, audio_bytes=_make_wav(duration_seconds=3.0))
    assert r.status_code == 413


def test_webm_format_is_accepted(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")
    r = _post_vc(client, h, audio_bytes=_make_webm(), content_type="audio/webm")
    assert r.status_code == 200


# ------------------------------------------------------------------ 10. regression

def test_text_chat_endpoint_unaffected(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = client.post("/api/chat", json={"message": "hello"}, headers=h)
    assert r.status_code == 200
    assert r.json()["intent"] == "greeting"


def test_stt_only_voice_endpoint_unaffected(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")
    r = client.post(
        "/api/chat/voice",
        files={"audio": ("rec.wav", _make_wav(), "audio/wav")},
        headers=h,
        params={"lang": "en"},
    )
    assert r.status_code == 200
    body = r.json()
    # VoiceResponse still has detected_lang (not lang)
    assert "detected_lang" in body
    assert "transcription" in body
    assert "chat" in body
    # VoiceChatResponse fields must NOT appear here
    assert "audio_id" not in body or body.get("audio_id") is None


def test_tts_speech_endpoint_unaffected(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = client.post(
        "/api/chat/speech",
        json={"text": "Hello.", "lang": "en"},
        headers=h,
        params={"mode": "stream"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/")
