"""Tests for POST /api/chat/voice (Speech-to-Text → chatbot pipeline).

All tests use the MockSTTProvider.  No paid credentials or network calls are
required.  The STT_PROVIDER setting is patched to "mock" in every test so the
suite is hermetic even when a different provider is configured in a .env file.

Test categories
---------------
1. Happy-path: English / Hindi / Marathi uploads produce a valid VoiceResponse.
2. Auth: missing or invalid token returns 401.
3. Rate limiting: voice calls share the per-user daily cap with /api/chat.
4. Format validation: unsupported MIME type returns 415.
5. Size validation: oversized files return 413.
6. STT provider errors: 503 is returned when the provider is misconfigured or fails.
7. Empty transcription: 400 is returned when the provider returns blank text.
8. Language resolution: provider-detected lang overrides the hint.
9. Existing /api/chat endpoint is unaffected (regression guard).
"""
import io
import struct
import wave

import pytest

from app.core.config import settings
from app.services import stt_service
from app.services.stt_service import MockSTTProvider, STTError, STTResult
from chat_helpers import register, seed_field


# ------------------------------------------------------------------ audio helpers

def _make_wav(duration_seconds: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Return a minimal valid mono WAV file of the given duration."""
    num_frames = int(sample_rate * duration_seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)          # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


def _make_webm() -> bytes:
    """Return four bytes that look like a WebM file header."""
    return b"\x1a\x45\xdf\xa3" + b"\x00" * 100


def _make_ogg() -> bytes:
    return b"OggS" + b"\x00" * 100


def _post_voice(client, headers, audio_bytes, content_type="audio/wav", lang=None):
    params = {}
    if lang:
        params["lang"] = lang
    return client.post(
        "/api/chat/voice",
        files={"audio": ("recording.wav", audio_bytes, content_type)},
        headers=headers,
        params=params,
    )


# ------------------------------------------------------------------ fixtures

@pytest.fixture(autouse=True)
def use_mock_stt(monkeypatch):
    """Ensure every test uses MockSTTProvider regardless of env config."""
    monkeypatch.setattr(settings, "STT_PROVIDER", "mock")


@pytest.fixture(autouse=True)
def reset_chat_usage():
    from app.services import chat_service
    chat_service._usage.clear()


# ------------------------------------------------------------------ 1. happy paths

def test_english_voice_returns_chat_response(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    wav = _make_wav()
    r = _post_voice(client, h, wav, lang="en")

    assert r.status_code == 200, r.text
    body = r.json()
    # Transcript must be the MockSTTProvider English default
    assert body["transcription"] == MockSTTProvider._DEFAULT["en"]
    assert body["detected_lang"] == "en"
    # Chat sub-object must look like a ChatResponse
    assert "reply" in body["chat"]
    assert "intent" in body["chat"]
    assert "speech" in body["chat"]
    assert body["chat"]["lang"] == "en"


def test_hindi_voice_gets_hindi_reply(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "hi")
    seed_field("a@test.com")

    wav = _make_wav()
    r = _post_voice(client, h, wav, lang="hi")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["detected_lang"] == "hi"
    assert body["transcription"] == MockSTTProvider._DEFAULT["hi"]
    assert body["chat"]["lang"] == "hi"


def test_marathi_voice_gets_marathi_reply(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "mr")
    seed_field("a@test.com")

    wav = _make_wav()
    r = _post_voice(client, h, wav, lang="mr")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["detected_lang"] == "mr"
    assert body["transcription"] == MockSTTProvider._DEFAULT["mr"]
    assert body["chat"]["lang"] == "mr"


def test_webm_format_is_accepted(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    r = _post_voice(client, h, _make_webm(), content_type="audio/webm")
    assert r.status_code == 200, r.text


def test_ogg_format_is_accepted(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    r = _post_voice(client, h, _make_ogg(), content_type="audio/ogg")
    assert r.status_code == 200, r.text


def test_voice_uses_users_saved_language_when_no_lang_hint(client):
    """When no lang query param is supplied, the user's preferred_language is used."""
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "hi")
    seed_field("a@test.com")

    wav = _make_wav()
    r = _post_voice(client, h, wav)      # no lang= param
    assert r.status_code == 200, r.text
    assert r.json()["detected_lang"] == "hi"


# ------------------------------------------------------------------ 2. auth

def test_voice_requires_authentication(client):
    wav = _make_wav()
    r = client.post(
        "/api/chat/voice",
        files={"audio": ("rec.wav", wav, "audio/wav")},
    )
    assert r.status_code == 401


def test_voice_rejects_invalid_token(client):
    wav = _make_wav()
    r = client.post(
        "/api/chat/voice",
        files={"audio": ("rec.wav", wav, "audio/wav")},
        headers={"Authorization": "Bearer notavalidtoken"},
    )
    assert r.status_code == 401


# ------------------------------------------------------------------ 3. rate limiting

def test_voice_calls_share_the_chat_rate_limit(client, monkeypatch):
    from app.services import chat_service
    monkeypatch.setattr(chat_service, "MAX_MESSAGES_PER_DAY", 2)

    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")
    wav = _make_wav()

    # First two calls should succeed
    r1 = _post_voice(client, h, wav, lang="en")
    r2 = _post_voice(client, h, wav, lang="en")
    assert r1.status_code == 200
    assert r2.status_code == 200

    # Third call: limit exceeded — chatbot returns intent="limit", which is still a 200
    r3 = _post_voice(client, h, wav, lang="en")
    assert r3.status_code == 200
    assert r3.json()["chat"]["intent"] == "limit"


# ------------------------------------------------------------------ 4. format validation

def test_unsupported_mime_type_returns_415(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    r = _post_voice(client, h, b"FAKE", content_type="video/mp4")
    assert r.status_code == 415
    assert "Unsupported" in r.json()["detail"]


def test_mismatched_signature_returns_415(client):
    """A file with an accepted MIME type but wrong magic bytes is rejected."""
    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    # Claim it's a WAV but send garbage bytes
    r = _post_voice(client, h, b"GARBAGE_BYTES_HERE_XXXX", content_type="audio/wav")
    assert r.status_code == 415


# ------------------------------------------------------------------ 5. size validation

def test_oversized_file_returns_413(client, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_MAX_MB", 1)
    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    # 1 MB + 1 byte → exceeds the 1 MB limit
    big = b"\x00" * (1 * 1_048_576 + 1)
    r = _post_voice(client, h, big, content_type="audio/wav")
    assert r.status_code == 413


def test_wav_exceeding_duration_limit_returns_413(client, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_MAX_SECONDS", 1)
    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    # 3-second WAV: above the 1-second limit
    long_wav = _make_wav(duration_seconds=3.0)
    r = _post_voice(client, h, long_wav, content_type="audio/wav")
    assert r.status_code == 413
    assert "long" in r.json()["detail"].lower()


# ------------------------------------------------------------------ 6. STT provider errors

def test_misconfigured_provider_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "STT_PROVIDER", "openai_whisper")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")     # deliberately blank

    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    r = _post_voice(client, h, _make_wav())
    assert r.status_code == 503
    assert "OPENAI_API_KEY" in r.json()["detail"]


def test_provider_runtime_error_returns_503(client, monkeypatch):
    """Simulate a provider that raises STTError during transcription."""
    from app.routers import chat as chat_router

    class FailingProvider:
        def transcribe(self, path, lang):
            raise STTError("Simulated provider failure")

    monkeypatch.setattr(chat_router._stt, "get_stt_provider", lambda: FailingProvider())

    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    r = _post_voice(client, h, _make_wav())
    assert r.status_code == 503
    assert "provider failure" in r.json()["detail"].lower()


def test_unknown_provider_name_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "STT_PROVIDER", "nonexistent_provider")

    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    r = _post_voice(client, h, _make_wav())
    assert r.status_code == 503


# ------------------------------------------------------------------ 7. empty transcription

def test_empty_transcription_returns_400(client, monkeypatch):
    """When the provider returns blank text the endpoint rejects with 400."""
    from app.routers import chat as chat_router

    class _SilentProvider:
        def transcribe(self, path, lang):
            return STTResult(transcript="", detected_lang=lang)

    monkeypatch.setattr(chat_router._stt, "get_stt_provider", lambda: _SilentProvider())

    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    r = _post_voice(client, h, _make_wav())
    assert r.status_code == 400
    assert "speech" in r.json()["detail"].lower()


def test_whitespace_only_transcription_returns_400(client, monkeypatch):
    from app.routers import chat as chat_router

    class _WhitespaceProvider:
        def transcribe(self, path, lang):
            return STTResult(transcript="   \n  ", detected_lang=lang)

    monkeypatch.setattr(chat_router._stt, "get_stt_provider", lambda: _WhitespaceProvider())

    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    r = _post_voice(client, h, _make_wav())
    assert r.status_code == 400


# ------------------------------------------------------------------ 8. language resolution

def test_provider_detected_lang_overrides_hint(client, monkeypatch):
    """If the provider returns a different valid lang, the chat reply uses it."""
    from app.routers import chat as chat_router

    class _MarathiProvider:
        def transcribe(self, path, lang):
            # Provider detects Marathi regardless of the hint
            return STTResult(transcript="मला किती पाणी हवे?", detected_lang="mr")

    monkeypatch.setattr(chat_router._stt, "get_stt_provider", lambda: _MarathiProvider())

    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")

    # Caller hints English, but provider says Marathi
    r = _post_voice(client, h, _make_wav(), lang="en")
    assert r.status_code == 200
    body = r.json()
    assert body["detected_lang"] == "mr"
    assert body["chat"]["lang"] == "mr"


def test_invalid_lang_hint_falls_back_to_user_preference(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "hi")     # saved preference = Hindi
    seed_field("a@test.com")

    wav = _make_wav()
    r = client.post(
        "/api/chat/voice",
        files={"audio": ("rec.wav", wav, "audio/wav")},
        headers=h,
        params={"lang": "fr"},   # unsupported lang hint
    )
    assert r.status_code == 200
    assert r.json()["detected_lang"] == "hi"


# ------------------------------------------------------------------ 9. regression: existing /api/chat still works

def test_text_chat_endpoint_still_works_after_voice_addition(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = client.post("/api/chat", json={"message": "hello"}, headers=h)
    assert r.status_code == 200
    assert r.json()["intent"] == "greeting"


# ------------------------------------------------------------------ unit tests for helpers

def test_validate_audio_rejects_bad_mime():
    from app.services.stt_service import validate_audio
    with pytest.raises(ValueError, match="Unsupported"):
        validate_audio("video/mp4", _make_wav(), 10 * 1_048_576, 120)


def test_validate_audio_rejects_oversized_data():
    from app.services.stt_service import validate_audio
    with pytest.raises(ValueError, match="too large"):
        validate_audio("audio/wav", b"RIFF" + b"\x00" * 200, max_bytes=10, max_seconds=120)


def test_validate_audio_rejects_bad_magic():
    from app.services.stt_service import validate_audio
    with pytest.raises(ValueError, match="signature"):
        validate_audio("audio/wav", b"INVALID_HEADER_BYTES", 10 * 1_048_576, 120)


def test_validate_audio_accepts_valid_wav():
    from app.services.stt_service import validate_audio
    wav = _make_wav(0.5)
    # Should not raise
    validate_audio("audio/wav", wav, 10 * 1_048_576, 120)


def test_validate_audio_rejects_long_wav():
    from app.services.stt_service import validate_audio
    wav = _make_wav(duration_seconds=5.0)
    with pytest.raises(ValueError, match="long"):
        validate_audio("audio/wav", wav, 10 * 1_048_576, max_seconds=3)


def test_mock_provider_returns_language_specific_text():
    from pathlib import Path
    p = MockSTTProvider()
    for lang in ("en", "hi", "mr"):
        result = p.transcribe(Path("/dev/null"), lang)
        assert result.transcript == MockSTTProvider._DEFAULT[lang]
        assert result.detected_lang == lang


def test_mock_provider_uses_seeded_transcript():
    from pathlib import Path
    p = MockSTTProvider(transcript="custom text")
    result = p.transcribe(Path("/dev/null"), "en")
    assert result.transcript == "custom text"


def test_get_stt_provider_returns_mock_by_default(monkeypatch):
    monkeypatch.setattr(settings, "STT_PROVIDER", "mock")
    provider = stt_service.get_stt_provider()
    assert isinstance(provider, MockSTTProvider)


def test_get_stt_provider_raises_for_missing_openai_key(monkeypatch):
    monkeypatch.setattr(settings, "STT_PROVIDER", "openai_whisper")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    with pytest.raises(STTError, match="OPENAI_API_KEY"):
        stt_service.get_stt_provider()


def test_get_stt_provider_raises_for_unknown_provider(monkeypatch):
    monkeypatch.setattr(settings, "STT_PROVIDER", "banana")
    with pytest.raises(STTError, match="Unknown STT_PROVIDER"):
        stt_service.get_stt_provider()
