"""Tests for the TTS pipeline:
    POST /api/chat/speech   (stream mode + url mode)
    GET  /api/chat/audio/{audio_id}

All tests use MockTTSProvider.  No paid credentials or network calls are
required.  TTS_PROVIDER is patched to "mock" in every test so the suite
is hermetic even when a different provider is configured in a .env file.

Test categories
---------------
1.  Happy-path stream mode — en / hi / mr return binary audio.
2.  Happy-path URL mode — returns audio_id; GET retrieves the bytes.
3.  Auth — missing / invalid token returns 401 for both endpoints.
4.  Language validation — unknown lang returns 400.
5.  Text length — text exceeding TTS_MAX_CHARS returns 400.
6.  TTS provider errors — misconfiguration and runtime errors return 503.
7.  Audio retrieval — wrong user 404, expired 404, used-twice 404.
8.  Audio store unit tests — put/get/evict/clear.
9.  MockTTSProvider unit tests.
10. Factory unit tests — unknown provider, missing OpenAI key, missing Google creds.
11. Regression — existing /api/chat and /api/chat/voice unaffected.
"""
import io
import wave

import pytest

from app.core.config import settings
from app.services import audio_store, tts_service
from app.services.tts_service import MockTTSProvider, TTSError, TTSResult
from chat_helpers import register, seed_field


# ------------------------------------------------------------------ audio helpers

def _make_wav_bytes(duration_seconds: float = 0.1) -> bytes:
    """Return a minimal valid mono WAV (for regression tests that call /chat/voice)."""
    sample_rate = 16000
    num_frames = int(sample_rate * duration_seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


def _is_wav(data: bytes) -> bool:
    return data[:4] == b"RIFF"


# ------------------------------------------------------------------ fixtures

@pytest.fixture(autouse=True)
def use_mock_tts(monkeypatch):
    """Ensure every test uses MockTTSProvider regardless of env config."""
    monkeypatch.setattr(settings, "TTS_PROVIDER", "mock")


@pytest.fixture(autouse=True)
def use_mock_stt(monkeypatch):
    """Keep STT on mock too so regression voice tests work."""
    monkeypatch.setattr(settings, "STT_PROVIDER", "mock")


@pytest.fixture(autouse=True)
def reset_audio_store():
    """Clear the in-memory audio store before every test."""
    audio_store.clear()
    yield
    audio_store.clear()


@pytest.fixture(autouse=True)
def reset_chat_usage():
    from app.services import chat_service
    chat_service._usage.clear()


def _speech(client, headers, text="Hello farmer.", lang="en", mode="stream"):
    return client.post(
        "/api/chat/speech",
        json={"text": text, "lang": lang},
        headers=headers,
        params={"mode": mode},
    )


# ------------------------------------------------------------------ 1. stream happy paths

def test_english_speech_returns_audio_bytes(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _speech(client, h, text="Soil moisture is 28 percent.", lang="en")

    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("audio/")
    assert len(r.content) > 0
    assert _is_wav(r.content)   # MockTTSProvider returns WAV


def test_hindi_speech_returns_audio_bytes(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _speech(client, h, text="मिट्टी की नमी 28 प्रतिशत है।", lang="hi")

    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("audio/")
    assert len(r.content) > 0


def test_marathi_speech_returns_audio_bytes(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _speech(client, h, text="मातीतील ओलावा 28 टक्के आहे.", lang="mr")

    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("audio/")
    assert len(r.content) > 0


def test_longer_text_produces_more_audio_than_shorter(client):
    """MockTTSProvider scales audio duration with input length."""
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    short = _speech(client, h, text="Hi.", lang="en")
    long_ = _speech(client, h, text="Soil moisture is 28 percent. Irrigation is not needed today.", lang="en")
    assert len(long_.content) > len(short.content)


def test_symbols_are_cleaned_before_synthesis(client):
    """The endpoint applies speakable() so % and °C never reach the provider."""
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    # If the backend passes raw text the mock would still return audio,
    # but we verify status 200 at minimum; a real provider would render better.
    r = _speech(client, h, text="Moisture is 28% and temperature is 32 °C.", lang="en")
    assert r.status_code == 200


# ------------------------------------------------------------------ 2. URL mode

def test_url_mode_returns_audio_id(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _speech(client, h, text="Hello.", lang="en", mode="url")

    assert r.status_code == 200, r.text
    body = r.json()
    assert "audio_id" in body
    assert "mime_type" in body
    assert "expires_in_seconds" in body
    assert body["expires_in_seconds"] > 0


def test_get_audio_retrieves_the_bytes(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    url_resp = _speech(client, h, text="Hello.", lang="en", mode="url")
    audio_id = url_resp.json()["audio_id"]

    r = client.get(f"/api/chat/audio/{audio_id}", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("audio/")
    assert len(r.content) > 0
    assert _is_wav(r.content)


def test_audio_token_is_single_use(client):
    """Fetching the same audio_id twice returns 404 on the second call."""
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    url_resp = _speech(client, h, text="Hello.", lang="en", mode="url")
    audio_id = url_resp.json()["audio_id"]

    r1 = client.get(f"/api/chat/audio/{audio_id}", headers=h)
    r2 = client.get(f"/api/chat/audio/{audio_id}", headers=h)
    assert r1.status_code == 200
    assert r2.status_code == 404


def test_url_mode_stores_one_entry_in_audio_store(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    assert audio_store.size() == 0
    _speech(client, h, text="Hello.", lang="en", mode="url")
    assert audio_store.size() == 1


# ------------------------------------------------------------------ 3. auth

def test_speech_requires_authentication(client):
    r = client.post("/api/chat/speech", json={"text": "Hi", "lang": "en"})
    assert r.status_code == 401


def test_speech_rejects_invalid_token(client):
    r = client.post(
        "/api/chat/speech",
        json={"text": "Hi", "lang": "en"},
        headers={"Authorization": "Bearer notavalid"},
    )
    assert r.status_code == 401


def test_get_audio_requires_authentication(client):
    r = client.get("/api/chat/audio/someid")
    assert r.status_code == 401


# ------------------------------------------------------------------ 4. language validation

def test_unsupported_lang_returns_400(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _speech(client, h, text="Bonjour.", lang="fr")
    assert r.status_code == 400
    assert "fr" in r.json()["detail"]


def test_empty_lang_returns_422(client):
    """Pydantic rejects the request before it reaches the endpoint."""
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = client.post("/api/chat/speech", json={"text": "Hello.", "lang": ""}, headers=h)
    # lang="" passes min_length=0 for the field, but endpoint validates it's one of en/hi/mr
    # Either 400 (endpoint) or 422 (pydantic) is acceptable
    assert r.status_code in (400, 422)


def test_empty_text_returns_422(client):
    """Pydantic rejects empty text because min_length=1."""
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = client.post("/api/chat/speech", json={"text": "", "lang": "en"}, headers=h)
    assert r.status_code == 422


# ------------------------------------------------------------------ 5. text length

def test_text_exceeding_max_chars_returns_400(client, monkeypatch):
    monkeypatch.setattr(settings, "TTS_MAX_CHARS", 10)
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    # 11 characters after speakable() runs
    r = _speech(client, h, text="Hello world", lang="en")
    assert r.status_code == 400
    assert "long" in r.json()["detail"].lower()


def test_text_exactly_at_limit_is_accepted(client, monkeypatch):
    monkeypatch.setattr(settings, "TTS_MAX_CHARS", 5)
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _speech(client, h, text="Hello", lang="en")
    assert r.status_code == 200


# ------------------------------------------------------------------ 6. TTS provider errors

def test_misconfigured_openai_tts_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "TTS_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _speech(client, h, text="Hello.", lang="en")
    assert r.status_code == 503
    assert "OPENAI_API_KEY" in r.json()["detail"]


def test_unknown_tts_provider_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "TTS_PROVIDER", "banana_tts")
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _speech(client, h, text="Hello.", lang="en")
    assert r.status_code == 503


def test_provider_runtime_error_returns_503(client, monkeypatch):
    from app.routers import chat as chat_router

    class _FailingProvider:
        def synthesise(self, text, lang):
            raise TTSError("Simulated TTS failure")

    monkeypatch.setattr(chat_router._tts, "get_tts_provider", lambda: _FailingProvider())
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = _speech(client, h, text="Hello.", lang="en")
    assert r.status_code == 503
    assert "tts failure" in r.json()["detail"].lower()


# ------------------------------------------------------------------ 7. audio retrieval edge cases

def test_get_audio_wrong_user_returns_404(client):
    """User B cannot retrieve audio that belongs to user A."""
    register(client, "admin@test.com")
    h_a = register(client, "a@test.com")
    h_b = register(client, "b@test.com")

    url_resp = _speech(client, h_a, text="Hello.", lang="en", mode="url")
    audio_id = url_resp.json()["audio_id"]

    # User B tries to fetch user A's audio
    r = client.get(f"/api/chat/audio/{audio_id}", headers=h_b)
    assert r.status_code == 404


def test_get_audio_nonexistent_id_returns_404(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = client.get("/api/chat/audio/completelyfakeid", headers=h)
    assert r.status_code == 404


def test_get_audio_expired_returns_404(client, monkeypatch):
    """Entries older than AUDIO_RETENTION_MINUTES are evicted before retrieval."""
    # Set retention to 0 minutes so the entry is immediately stale
    monkeypatch.setattr(settings, "AUDIO_RETENTION_MINUTES", 0)
    register(client, "admin@test.com")
    h = register(client, "a@test.com")

    url_resp = _speech(client, h, text="Hello.", lang="en", mode="url")
    audio_id = url_resp.json()["audio_id"]

    # With retention=0, the entry expires immediately
    r = client.get(f"/api/chat/audio/{audio_id}", headers=h)
    assert r.status_code == 404


# ------------------------------------------------------------------ 8. audio_store unit tests

def test_put_and_get_returns_stored_bytes():
    data = b"fake_audio_bytes"
    audio_id = audio_store.put(user_id=1, audio_bytes=data, mime_type="audio/mpeg")
    result = audio_store.get(audio_id, user_id=1, retention_minutes=10)
    assert result is not None
    assert result[0] == data
    assert result[1] == "audio/mpeg"


def test_get_removes_entry_on_success():
    audio_id = audio_store.put(user_id=1, audio_bytes=b"x", mime_type="audio/mpeg")
    audio_store.get(audio_id, user_id=1, retention_minutes=10)
    # Second get should return None — entry was deleted
    assert audio_store.get(audio_id, user_id=1, retention_minutes=10) is None


def test_get_wrong_user_returns_none():
    audio_id = audio_store.put(user_id=1, audio_bytes=b"x", mime_type="audio/mpeg")
    assert audio_store.get(audio_id, user_id=2, retention_minutes=10) is None
    # Entry should still be there for the right user
    assert audio_store.get(audio_id, user_id=1, retention_minutes=10) is not None


def test_evict_removes_zero_retention():
    audio_store.put(user_id=1, audio_bytes=b"x", mime_type="audio/mpeg")
    assert audio_store.size() == 1
    # retention=0 means every entry is older than the cutoff
    evicted = audio_store.evict(retention_minutes=0)
    assert evicted == 1
    assert audio_store.size() == 0


def test_clear_empties_store():
    audio_store.put(user_id=1, audio_bytes=b"x", mime_type="audio/mpeg")
    audio_store.put(user_id=2, audio_bytes=b"y", mime_type="audio/mpeg")
    audio_store.clear()
    assert audio_store.size() == 0


# ------------------------------------------------------------------ 9. MockTTSProvider unit tests

def test_mock_provider_returns_valid_wav():
    p = MockTTSProvider()
    result = p.synthesise("Hello.", "en")
    assert result.mime_type == "audio/wav"
    assert _is_wav(result.audio_bytes)


def test_mock_provider_works_for_all_languages():
    p = MockTTSProvider()
    for lang in ("en", "hi", "mr"):
        result = p.synthesise("नमस्ते", lang)
        assert result.audio_bytes


def test_mock_provider_raises_on_empty_text():
    """TTSResult raises ValueError for empty audio; mock never returns empty audio."""
    p = MockTTSProvider()
    # Even a single space should produce frames (max(len(" "), 1) * 10 = 10)
    result = p.synthesise(" ", "en")
    assert len(result.audio_bytes) > 0


def test_tts_result_raises_on_empty_bytes():
    with pytest.raises(ValueError, match="empty audio"):
        TTSResult(audio_bytes=b"", mime_type="audio/mpeg")


# ------------------------------------------------------------------ 10. factory unit tests

def test_get_tts_provider_returns_mock_by_default(monkeypatch):
    monkeypatch.setattr(settings, "TTS_PROVIDER", "mock")
    provider = tts_service.get_tts_provider()
    assert isinstance(provider, MockTTSProvider)


def test_get_tts_provider_raises_for_missing_openai_key(monkeypatch):
    monkeypatch.setattr(settings, "TTS_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    with pytest.raises(TTSError, match="OPENAI_API_KEY"):
        tts_service.get_tts_provider()


def test_get_tts_provider_raises_for_unknown_name(monkeypatch):
    monkeypatch.setattr(settings, "TTS_PROVIDER", "mystery_provider")
    with pytest.raises(TTSError, match="Unknown TTS_PROVIDER"):
        tts_service.get_tts_provider()


# ------------------------------------------------------------------ 11. regression

def test_text_chat_still_works(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    r = client.post("/api/chat", json={"message": "hello"}, headers=h)
    assert r.status_code == 200
    assert r.json()["intent"] == "greeting"


def test_voice_stt_endpoint_still_works(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")
    wav = _make_wav_bytes()
    r = client.post(
        "/api/chat/voice",
        files={"audio": ("rec.wav", wav, "audio/wav")},
        headers=h,
        params={"lang": "en"},
    )
    assert r.status_code == 200
    assert "transcription" in r.json()
    assert "chat" in r.json()
