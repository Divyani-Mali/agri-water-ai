"""Multilingual backend audit tests — Feature 4.

Covers all ten areas from the audit:
  1.  Authentication messages and validation errors.
  2.  Farm and field API responses.
  3.  Sensor reading APIs.
  4.  Forecast responses (labels, assumptions).
  5.  Alert messages in all three languages.
  6.  Chatbot intent detection and responses.
  7.  Suggestions and fallback messages.
  8.  Voice (STT) and TTS language handling.
  9.  preferred_language storage and retrieval.
  10. Missing translation keys and language fallback.

All tests use in-process mocks; no paid API credentials are required.
"""
import io
import json
import wave
from datetime import date, datetime, timedelta, timezone

import pytest

from app.i18n import (
    ASSUMPTIONS, BOT, LANGS, LABELS, SUGGESTIONS, UNIT_NAMES,
    alert_message, duration_text, label, normalize_lang,
    render_alert, say, speakable, translate_assumptions,
)
from app.services import chat_nlu as nlu
from app.core.config import settings
from app.services import audio_store
from chat_helpers import add_alert, db_session, register, seed_field


# ============================================================ helpers

def _make_wav(duration_seconds: float = 0.3) -> bytes:
    sample_rate = 16000
    num_frames = int(sample_rate * duration_seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


def me(client, headers):
    return client.get("/api/auth/me", headers=headers).json()


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


# ============================================================
# 1. Authentication messages and validation errors
# ============================================================

class TestAuthMessages:
    """Auth messages are intentionally English-only (user may not be authenticated).
    These tests confirm the existing behavior is consistent and stable."""

    def test_duplicate_email_returns_english_detail(self, client):
        register(client, "admin@test.com")
        register(client, "a@test.com")
        # Attempt to register with the same email again
        r = client.post(
            "/api/auth/register",
            json={"email": "a@test.com", "full_name": "Test User", "password": "Test1234"},
        )
        assert r.status_code == 400
        assert r.json()["detail"] == "Email already registered"

    def test_wrong_password_returns_english_detail(self, client):
        register(client, "admin@test.com")
        r = client.post(
            "/api/auth/login",
            data={"username": "admin@test.com", "password": "WrongPass1"},
        )
        assert r.status_code == 401
        assert r.json()["detail"] == "Incorrect email or password"

    def test_invalid_token_returns_english_detail(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
        assert r.status_code == 401
        assert "token" in r.json()["detail"].lower()

    def test_weak_password_returns_english_validation_message(self, client):
        r = client.post(
            "/api/auth/register",
            json={"email": "b@test.com", "full_name": "X", "password": "onlyletters"},
        )
        assert r.status_code == 422
        body = r.json()
        # Pydantic validation details are nested; find any mention of the error
        assert "letter" in str(body).lower() or "number" in str(body).lower()

    def test_invalid_preferred_language_rejected_on_register(self, client):
        r = client.post(
            "/api/auth/register",
            json={
                "email": "c@test.com",
                "full_name": "Test",
                "password": "Test1234",
                "preferred_language": "fr",
            },
        )
        assert r.status_code == 422

    def test_password_updated_message_is_english(self, client, monkeypatch):
        monkeypatch.setattr(settings, "SMTP_HOST", "")
        monkeypatch.setattr(settings, "SMTP_FROM", "")
        monkeypatch.setattr(settings, "PASSWORD_RESET_DEV_MODE", True)
        register(client, "admin@test.com")
        from urllib.parse import parse_qs, urlparse
        req = client.post("/api/auth/password-reset/request", json={"email": "admin@test.com"})
        token = parse_qs(urlparse(req.json()["reset_url"]).query)["token"][0]
        r = client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "password": "NewPass123"},
        )
        assert r.status_code == 200
        assert "Password updated" in r.json()["message"]


# ============================================================
# 2. Farm and field API responses
# ============================================================

class TestFarmFieldMessages:
    """Error strings are English-only by design (infrastructure layer).
    These tests confirm coverage of the most important error paths."""

    def test_farm_not_found_returns_english_detail(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com")
        r = client.get("/api/farms/9999", headers=h)
        assert r.status_code == 404
        assert r.json()["detail"] == "Farm not found"

    def test_field_not_found_returns_english_detail(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com")
        r = client.get("/api/fields/9999", headers=h)
        assert r.status_code == 404
        assert r.json()["detail"] == "Field not found"

    def test_duplicate_farm_name_returns_english_detail(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com")
        client.post("/api/farms", json={"name": "MyFarm", "location": "Pune"}, headers=h)
        r = client.post("/api/farms", json={"name": "MyFarm", "location": "Pune"}, headers=h)
        assert r.status_code == 400
        assert "farm" in r.json()["detail"].lower()

    def test_field_out_contains_machine_crop_and_soil_codes(self, client):
        """FieldOut intentionally returns machine codes; localization is in forecast."""
        register(client, "admin@test.com")
        h = register(client, "a@test.com")
        farm_id = client.post(
            "/api/farms", json={"name": "F1", "location": "Pune"}, headers=h
        ).json()["id"]
        field = client.post(
            f"/api/farms/{farm_id}/fields",
            json={"name": "P1", "crop_type": "wheat", "soil_type": "loamy", "area_acres": 1.0},
            headers=h,
        ).json()
        assert field["crop_type"] == "wheat"
        assert field["soil_type"] == "loamy"
        # Localized labels are NOT present in FieldOut (by design)
        assert "crop_label" not in field
        assert "soil_label" not in field

    def test_future_planting_date_validation_is_english(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com")
        farm_id = client.post(
            "/api/farms", json={"name": "F2", "location": "Pune"}, headers=h
        ).json()["id"]
        future = (date.today() + timedelta(days=10)).isoformat()
        r = client.post(
            f"/api/farms/{farm_id}/fields",
            json={"name": "P2", "crop_type": "wheat", "soil_type": "loamy",
                  "area_acres": 1.0, "planting_date": future},
            headers=h,
        )
        assert r.status_code == 422
        assert "future" in str(r.json()).lower()


# ============================================================
# 3. Sensor reading APIs
# ============================================================

class TestSensorReadingMessages:
    def test_no_readings_404_is_english(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com")
        fid = seed_field("a@test.com", reading=False)
        r = client.get(f"/api/fields/{fid}/readings/latest", headers=h)
        assert r.status_code == 404
        assert "readings" in r.json()["detail"].lower() or "no readings" in r.json()["detail"].lower()

    def test_invalid_api_key_returns_401(self, client):
        register(client, "admin@test.com")
        register(client, "a@test.com")
        fid = seed_field("a@test.com", reading=False)
        r = client.post(
            f"/api/fields/{fid}/readings",
            json={"soil_moisture": 20.0, "temperature": 25.0, "humidity": 60.0},
            headers={"X-API-Key": "wrong-key"},
        )
        assert r.status_code == 401


# ============================================================
# 4. Forecast responses — labels and assumptions
# ============================================================

class TestForecastLocalization:
    def test_crop_labels_translated_in_forecast(self, client, monkeypatch):
        def _fake_forecast(db, field, days):
            return {
                "field_id": field.id,
                "crop_type": "wheat",
                "soil_type": "loamy",
                "model_name": "xgboost",
                "based_on_days": 7,
                "current_soil_moisture": 28.0,
                "assumptions": ASSUMPTIONS[0]["en"],
                "forecast": [
                    {"target_date": date.today(), "growth_stage": "initial",
                     "kc": 0.3, "predicted_water_mm": 1.0, "total_liters": 4000.0}
                ],
            }

        monkeypatch.setattr("app.routers.forecast.forecast_field", _fake_forecast)
        # Use the same user (admin) for both seeding and querying
        h = register(client, "admin@test.com")
        fid = seed_field("admin@test.com")

        for lang, expected_crop, expected_soil, expected_stage in [
            ("en", "Wheat", "Loamy", "Initial"),
            ("hi", "गेहूँ", "दोमट", "शुरुआती"),
            ("mr", "गहू", "पोयटा", "सुरुवातीची"),
        ]:
            r = client.get(f"/api/fields/{fid}/forecast?days=1&lang={lang}", headers=h)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["crop_label"] == expected_crop, f"crop_label mismatch for {lang}"
            assert body["soil_label"] == expected_soil, f"soil_label mismatch for {lang}"
            assert body["forecast"][0]["growth_stage_label"] == expected_stage, f"stage_label for {lang}"

    @pytest.mark.parametrize("lang", LANGS)
    def test_assumptions_translated_for_all_languages(self, client, monkeypatch, lang):
        def _fake_forecast(db, field, days):
            return {
                "field_id": field.id, "crop_type": "rice", "soil_type": "clay",
                "model_name": "xgboost", "based_on_days": 7,
                "current_soil_moisture": 28.0,
                "assumptions": ASSUMPTIONS[0]["en"],
                "forecast": [{"target_date": date.today(), "growth_stage": "mid",
                               "kc": 1.1, "predicted_water_mm": 2.0, "total_liters": 8000.0}],
            }

        monkeypatch.setattr("app.routers.forecast.forecast_field", _fake_forecast)
        # Admin user owns the field; use admin's token for every lang variant
        h = register(client, "admin@test.com")
        fid = seed_field("admin@test.com")
        r = client.get(f"/api/fields/{fid}/forecast?days=1&lang={lang}", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        if lang == "en":
            assert body["assumptions"] == ASSUMPTIONS[0]["en"]
        else:
            assert body["assumptions"] == ASSUMPTIONS[0][lang]
            # Must contain Devanagari
            assert any("\u0900" <= ch <= "\u097f" for ch in body["assumptions"])

    def test_assumptions_string_in_forecast_service_matches_i18n(self):
        """Confirm forecast_service.py references ASSUMPTIONS[0]['en'] directly
        so translate_assumptions() can find it by exact match."""
        from app.services.forecast_service import forecast_field  # noqa
        # The only way to verify without running the full ML pipeline is to check
        # that the ASSUMPTIONS[0]['en'] string is translatable.
        translated = translate_assumptions(ASSUMPTIONS[0]["en"], "hi")
        assert translated == ASSUMPTIONS[0]["hi"]
        assert any("\u0900" <= ch <= "\u097f" for ch in translated)

    def test_unknown_assumptions_text_returns_itself_unchanged(self):
        result = translate_assumptions("Some completely unknown text.", "hi")
        assert result == "Some completely unknown text."

    @pytest.mark.parametrize("lang", LANGS)
    def test_all_stage_labels_translate(self, lang):
        for stage in ("initial", "development", "mid", "late"):
            lbl = label("stage", stage, lang)
            if lang == "en":
                assert lbl  # truthy string
            else:
                assert any("\u0900" <= ch <= "\u097f" for ch in lbl), \
                    f"Stage '{stage}' label for {lang} has no Devanagari: {lbl!r}"

    @pytest.mark.parametrize("lang", LANGS)
    def test_all_crop_labels_translate(self, lang):
        from app.schemas.farm import CropType
        for crop in ("wheat", "rice", "cotton", "sugarcane", "maize", "soybean", "tomato", "onion"):
            lbl = label("crop", crop, lang)
            assert lbl, f"Empty label for crop={crop} lang={lang}"
            if lang != "en":
                assert any("\u0900" <= ch <= "\u097f" for ch in lbl), \
                    f"Crop '{crop}' for {lang}: {lbl!r}"

    @pytest.mark.parametrize("lang", LANGS)
    def test_all_soil_labels_translate(self, lang):
        for soil in ("sandy", "loamy", "clay"):
            lbl = label("soil", soil, lang)
            assert lbl, f"Empty label for soil={soil} lang={lang}"
            if lang != "en":
                assert any("\u0900" <= ch <= "\u097f" for ch in lbl), \
                    f"Soil '{soil}' for {lang}: {lbl!r}"


# ============================================================
# 5. Alert messages in all three languages
# ============================================================

class TestAlertLocalization:
    PARAMS = {
        "field": "North Plot",
        "moisture": 12.0,
        "temperature": 43.5,
        "rain": 15.0,
        "minutes": 1320,
    }

    @pytest.mark.parametrize("lang", LANGS)
    @pytest.mark.parametrize("alert_type,severity", [
        ("dry_soil", "critical"), ("dry_soil", "warning"),
        ("heat_stress", "critical"), ("heat_stress", "warning"),
        ("heavy_rain", "warning"), ("sensor_offline", "warning"),
    ])
    def test_all_alert_types_render_in_all_languages(self, alert_type, severity, lang):
        text = render_alert(alert_type, severity, self.PARAMS, lang)
        assert text, f"render_alert returned falsy for {alert_type}/{severity}/{lang}"
        assert "{" not in text, f"Unfilled placeholder in {alert_type}/{severity}/{lang}: {text}"
        assert "North Plot" in text

    @pytest.mark.parametrize("lang", ("hi", "mr"))
    @pytest.mark.parametrize("alert_type,severity", [
        ("dry_soil", "critical"), ("dry_soil", "warning"),
        ("heat_stress", "critical"), ("heat_stress", "warning"),
        ("heavy_rain", "warning"), ("sensor_offline", "warning"),
    ])
    def test_non_english_alerts_contain_devanagari(self, alert_type, severity, lang):
        text = render_alert(alert_type, severity, self.PARAMS, lang)
        assert any("\u0900" <= ch <= "\u097f" for ch in text), \
            f"No Devanagari in {alert_type}/{severity}/{lang}: {text!r}"

    def test_alert_via_api_respects_user_language(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com", "hi")
        fid = seed_field("a@test.com")
        add_alert(fid)
        alerts = client.get("/api/alerts", headers=h).json()
        assert len(alerts) > 0
        # Hindi message must contain Devanagari
        assert any("\u0900" <= ch <= "\u097f" for ch in alerts[0]["message"])

    def test_alert_via_api_lang_override(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com", "hi")
        fid = seed_field("a@test.com")
        add_alert(fid)
        en_alerts = client.get("/api/alerts?lang=en", headers=h).json()
        mr_alerts = client.get("/api/alerts?lang=mr", headers=h).json()
        assert en_alerts[0]["message"].startswith("Irrigation overdue")
        assert any("\u0900" <= ch <= "\u097f" for ch in mr_alerts[0]["message"])

    def test_duration_text_in_all_languages(self):
        assert duration_text(45, "en") == "45 minutes"
        assert duration_text(1320, "hi") == "22 घंटे"
        assert duration_text(1320, "mr") == "22 तास"
        assert duration_text(5000, "en") == "3 days"
        assert duration_text(5000, "hi") == "3 दिन"
        assert duration_text(5000, "mr") == "3 दिवस"

    def test_unknown_alert_type_returns_none(self):
        assert render_alert("unknown_type", "info", {}, "hi") is None

    def test_old_alert_without_params_returns_english_fallback(self):
        result = alert_message("dry_soil", "critical", None, "Old English text", "hi")
        assert result == "Old English text"


# ============================================================
# 6. Chatbot intent detection and responses
# ============================================================

class TestChatbotIntentsAndResponses:
    @pytest.mark.parametrize("message,expected_intent", [
        ("How much water does my field need?", "water_need"),
        ("मुझे कितना पानी चाहिए?", "water_need"),
        ("मला किती पाणी हवे?", "water_need"),
        ("What is my soil moisture?", "status"),
        ("मिट्टी की नमी कितनी है?", "status"),
        ("मातीतील ओलावा किती आहे?", "status"),
        ("Show my alerts", "alerts"),
        ("मेरे अलर्ट दिखाओ", "alerts"),
        ("माझे अलर्ट दाखवा", "alerts"),
        ("Which field is driest?", "compare"),
        ("सबसे सूखा खेत कौन सा है?", "compare"),
        ("सर्वात कोरडे शेत कोणते आहे?", "compare"),
        ("What if I skip watering for 3 days?", "what_if"),
        ("Which pesticide should I use?", "safety"),
        ("urea dalna chahiye?", "safety"),
        ("hello", "greeting"),
        ("help", "help"),
        ("asdfgh", "unknown"),
    ])
    def test_intent_detection_multilingual(self, message, expected_intent):
        text, tokens = nlu.prepare(message)
        assert nlu.detect_intent(text, tokens) == expected_intent, \
            f"Expected intent={expected_intent} for: {message!r}"

    @pytest.mark.parametrize("lang", LANGS)
    def test_all_suggestion_buttons_map_to_their_intended_intents(self, lang):
        expected_intents = ["water_need", "status", "alerts", "compare"]
        for message, intent in zip(SUGGESTIONS[lang], expected_intents):
            text, tokens = nlu.prepare(message)
            assert nlu.detect_intent(text, tokens) == intent, \
                f"Suggestion '{message}' (lang={lang}) expected intent={intent}"

    def test_greeting_reply_uses_requested_lang(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com")
        for lang, expected_word in [("en", "Hello"), ("hi", "नमस्ते"), ("mr", "नमस्कार")]:
            r = client.post("/api/chat", json={"message": "hello", "lang": lang}, headers=h)
            assert r.status_code == 200, r.text
            assert expected_word in r.json()["reply"], \
                f"greeting not in {lang}: {r.json()['reply']!r}"

    def test_chatbot_uses_user_preferred_language(self, client):
        register(client, "admin@test.com")
        for lang, word in [("hi", "नमस्ते"), ("mr", "नमस्कार")]:
            h = register(client, f"{lang}chat@test.com", lang)
            r = client.post("/api/chat", json={"message": "hello"}, headers=h)
            assert r.status_code == 200
            assert word in r.json()["reply"], f"Expected {lang} greeting, got: {r.json()['reply']!r}"

    def test_devanagari_message_selects_correct_language(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com")  # preferred_language = "en"
        # Marathi marker word "आहे" should identify Marathi
        r = client.post("/api/chat", json={"message": "मातीतील ओलावा किती आहे?"}, headers=h)
        assert r.json()["lang"] == "mr"

    def test_chatbot_reply_has_speech_field_in_all_languages(self, client):
        register(client, "admin@test.com")
        for lang in LANGS:
            h = register(client, f"sp{lang}@test.com", lang)
            r = client.post("/api/chat", json={"message": "hello", "lang": lang}, headers=h)
            assert r.status_code == 200
            body = r.json()
            assert "speech" in body
            assert isinstance(body["speech"], str) and len(body["speech"]) > 0


# ============================================================
# 7. Suggestions and fallback messages
# ============================================================

class TestSuggestionsAndFallback:
    @pytest.mark.parametrize("lang", LANGS)
    def test_suggestions_exist_for_all_languages(self, lang):
        assert lang in SUGGESTIONS
        assert len(SUGGESTIONS[lang]) == 4

    @pytest.mark.parametrize("lang", LANGS)
    def test_all_bot_keys_exist_for_all_languages(self, lang):
        for key, templates in BOT.items():
            assert lang in templates, f"BOT['{key}'] missing '{lang}' entry"

    def test_say_falls_back_to_english_for_unknown_language(self):
        result = say("greeting", "xx")
        assert result == BOT["greeting"]["en"]

    def test_say_returns_key_for_completely_unknown_key(self):
        result = say("nonexistent_bot_key", "en")
        assert result == "nonexistent_bot_key"

    def test_normalize_lang_returns_en_for_unknown_code(self):
        for bad in ("fr", "de", "xx", "", None):
            assert normalize_lang(bad) == "en", f"normalize_lang({bad!r}) should be 'en'"

    def test_normalize_lang_accepts_valid_codes(self):
        for code in LANGS:
            assert normalize_lang(code) == code

    @pytest.mark.parametrize("lang", LANGS)
    def test_unknown_intent_reply_in_all_languages(self, client, lang):
        register(client, "admin@test.com")
        h = register(client, f"unk{lang}@test.com", lang)
        r = client.post("/api/chat", json={"message": "xyzabcdef", "lang": lang}, headers=h)
        assert r.status_code == 200
        assert r.json()["intent"] == "unknown"
        # Non-English replies must contain Devanagari
        if lang != "en":
            assert any("\u0900" <= ch <= "\u097f" for ch in r.json()["reply"])

    @pytest.mark.parametrize("lang", LANGS)
    def test_no_fields_message_in_all_languages(self, client, lang):
        register(client, "admin@test.com")
        h = register(client, f"nf{lang}@test.com", lang)
        r = client.post("/api/chat", json={"message": "How much water?", "lang": lang}, headers=h)
        assert r.status_code == 200
        assert r.json()["intent"] == "water_need"
        if lang == "en":
            assert "no fields" in r.json()["reply"].lower()
        else:
            assert any("\u0900" <= ch <= "\u097f" for ch in r.json()["reply"])

    @pytest.mark.parametrize("lang", LANGS)
    def test_rate_limit_message_in_all_languages(self, client, monkeypatch, lang):
        from app.services import chat_service
        monkeypatch.setattr(chat_service, "MAX_MESSAGES_PER_DAY", 1)
        register(client, "admin@test.com")
        h = register(client, f"rl{lang}@test.com", lang)
        client.post("/api/chat", json={"message": "hello", "lang": lang}, headers=h)
        r = client.post("/api/chat", json={"message": "hello", "lang": lang}, headers=h)
        assert r.json()["intent"] == "limit"
        if lang != "en":
            assert any("\u0900" <= ch <= "\u097f" for ch in r.json()["reply"])


# ============================================================
# 8. Voice (STT) and TTS language handling
# ============================================================

class TestVoiceSTTTTSLanguage:
    def test_stt_voice_uses_lang_hint(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com")
        seed_field("a@test.com")
        for lang in LANGS:
            r = client.post(
                "/api/chat/voice",
                files={"audio": ("rec.wav", _make_wav(), "audio/wav")},
                headers=h,
                params={"lang": lang},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["detected_lang"] == lang
            assert body["chat"]["lang"] == lang

    def test_stt_voice_falls_back_to_user_preference(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com", "mr")
        seed_field("a@test.com")
        r = client.post(
            "/api/chat/voice",
            files={"audio": ("rec.wav", _make_wav(), "audio/wav")},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["detected_lang"] == "mr"

    def test_voice_chat_pipeline_uses_consistent_lang(self, client):
        """The integrated voice-chat endpoint uses the same lang for STT, chatbot and TTS."""
        register(client, "admin@test.com")
        h = register(client, "a@test.com")
        seed_field("a@test.com")
        for lang in LANGS:
            r = client.post(
                "/api/chat/voice-chat",
                files={"audio": ("rec.wav", _make_wav(), "audio/wav")},
                headers=h,
                params={"lang": lang, "audio_mode": "url"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["lang"] == lang
            assert body["chat"]["lang"] == lang
            assert body["audio_id"] is not None   # TTS ran and stored audio

    @pytest.mark.parametrize("lang", LANGS)
    def test_tts_speech_endpoint_accepts_all_supported_languages(self, client, lang):
        register(client, "admin@test.com")
        h = register(client, f"tts{lang}@test.com", lang)
        r = client.post(
            "/api/chat/speech",
            json={"text": "Hello.", "lang": lang},
            headers=h,
            params={"mode": "stream"},
        )
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("audio/")

    def test_tts_rejects_unsupported_language(self, client):
        register(client, "admin@test.com")
        h = register(client, "a@test.com")
        r = client.post("/api/chat/speech", json={"text": "Hi", "lang": "fr"}, headers=h)
        assert r.status_code == 400
        assert "fr" in r.json()["detail"]

    def test_speakable_converts_symbols_in_hindi(self):
        text = "नमी 28.0% और तापमान 32.5 °C है।"
        spoken = speakable(text, "hi")
        assert "%" not in spoken
        assert "°" not in spoken
        assert "प्रतिशत" in spoken
        assert "डिग्री सेल्सियस" in spoken

    def test_speakable_converts_symbols_in_marathi(self):
        text = "ओलावा 28.0% आणि तापमान 32.5 °C आहे."
        spoken = speakable(text, "mr")
        assert "%" not in spoken
        assert "°" not in spoken
        assert "टक्के" in spoken
        assert "अंश सेल्सिअस" in spoken

    def test_speakable_converts_hindi_dates_to_words(self):
        spoken = speakable("2026-10-14: 1 मिमी", "hi")
        assert "14 अक्टूबर" in spoken

    def test_speakable_converts_marathi_dates_to_words(self):
        spoken = speakable("2026-10-14: 1 मिमी", "mr")
        assert "14 ऑक्टोबर" in spoken

    def test_speakable_fallback_for_unknown_language(self):
        # Unknown lang defaults to English processing
        spoken = speakable("moisture 28%", "xx")
        assert "percent" in spoken


# ============================================================
# 9. preferred_language storage and retrieval
# ============================================================

class TestPreferredLanguage:
    def test_default_language_is_english(self, client):
        h = register(client, "admin@test.com")
        assert me(client, h)["preferred_language"] == "en"

    @pytest.mark.parametrize("lang", LANGS)
    def test_register_with_each_language_persists(self, client, lang):
        register(client, "admin@test.com")
        h = register(client, f"reg{lang}@test.com", lang)
        assert me(client, h)["preferred_language"] == lang

    @pytest.mark.parametrize("from_lang,to_lang", [
        ("en", "hi"), ("hi", "mr"), ("mr", "en"), ("en", "mr"),
    ])
    def test_language_update_persists_across_requests(self, client, from_lang, to_lang):
        register(client, "admin@test.com")
        h = register(client, f"upd{from_lang}{to_lang}@test.com", from_lang)
        assert me(client, h)["preferred_language"] == from_lang
        r = client.patch("/api/auth/me", json={"preferred_language": to_lang}, headers=h)
        assert r.status_code == 200
        assert r.json()["preferred_language"] == to_lang
        # Fresh GET confirms persistence
        assert me(client, h)["preferred_language"] == to_lang

    def test_invalid_language_update_rejected(self, client):
        h = register(client, "admin@test.com")
        r = client.patch("/api/auth/me", json={"preferred_language": "fr"}, headers=h)
        assert r.status_code == 422

    def test_language_preference_used_in_chatbot_reply(self, client):
        register(client, "admin@test.com")
        for lang, word in [("en", "Hello"), ("hi", "नमस्ते"), ("mr", "नमस्कार")]:
            h = register(client, f"pref{lang}@test.com", lang)
            r = client.post("/api/chat", json={"message": "hello"}, headers=h)
            assert word in r.json()["reply"], \
                f"Expected greeting in {lang}, got: {r.json()['reply']!r}"

    def test_language_preference_used_in_alerts(self, client):
        register(client, "admin@test.com")
        for lang in ("hi", "mr"):
            h = register(client, f"alrt{lang}@test.com", lang)
            fid = seed_field(f"alrt{lang}@test.com")
            add_alert(fid)
            alerts = client.get("/api/alerts", headers=h).json()
            assert any("\u0900" <= ch <= "\u097f" for ch in alerts[0]["message"]), \
                f"Expected Devanagari in {lang} alert"


# ============================================================
# 10. Missing translation keys and fallback behavior
# ============================================================

class TestTranslationFallback:
    def test_label_unknown_kind_returns_capitalized_key(self):
        result = label("nonexistent_kind", "somekey", "hi")
        assert result == "Somekey"

    def test_label_unknown_key_within_known_kind_returns_capitalized(self):
        result = label("crop", "banana", "hi")
        assert result == "Banana"

    def test_label_known_key_unknown_lang_falls_back_to_english(self):
        result = label("crop", "wheat", "fr")
        assert result == "Wheat"

    def test_say_unknown_language_falls_back_to_english(self):
        # Only test keys whose templates require no format parameters
        no_param_keys = [
            k for k, templates in BOT.items()
            if "{" not in templates["en"]
        ]
        assert no_param_keys, "Expected at least some parameter-free BOT keys"
        for key in no_param_keys:
            result = say(key, "fr")
            assert result == say(key, "en"), \
                f"say('{key}', 'fr') should equal English fallback"

    def test_say_unknown_key_returns_key_string(self):
        assert say("this_key_does_not_exist", "en") == "this_key_does_not_exist"
        assert say("this_key_does_not_exist", "hi") == "this_key_does_not_exist"

    def test_speakable_unknown_language_defaults_to_english_processing(self):
        result_unknown = speakable("moisture 28%", "zz")
        result_english = speakable("moisture 28%", "en")
        assert result_unknown == result_english

    def test_pick_language_explicit_always_wins(self):
        for explicit in LANGS:
            result = nlu.pick_language("some text", explicit, "en")
            assert result == explicit

    def test_pick_language_devanagari_marathi_markers_win_over_hindi_preference(self):
        """The fix: even if the user prefers Hindi, Marathi markers in the text
        should return 'mr'."""
        marathi_message = "मातीतील ओलावा किती आहे?"  # contains "आहे" (Marathi marker)
        result = nlu.pick_language(marathi_message, None, "hi")
        assert result == "mr", (
            "Marathi markers in text should override a Hindi preference. "
            f"Got: {result!r}"
        )

    def test_pick_language_devanagari_no_markers_uses_saved_preference(self):
        """With no Marathi markers, the saved preference is the tiebreaker."""
        hindi_message = "नमस्ते"  # Devanagari, no Marathi markers
        assert nlu.pick_language(hindi_message, None, "hi") == "hi"
        assert nlu.pick_language(hindi_message, None, "mr") == "mr"
        assert nlu.pick_language(hindi_message, None, "en") == "hi"  # defaults to hi

    def test_pick_language_roman_script_uses_saved_preference(self):
        assert nlu.pick_language("kitna paani hai", None, "hi") == "hi"
        assert nlu.pick_language("kitna paani hai", None, "mr") == "mr"
        assert nlu.pick_language("kitna paani hai", None, "en") == "en"
        assert nlu.pick_language("kitna paani hai", None, None) == "en"

    def test_pick_language_none_saved_preference_defaults_to_english(self):
        assert nlu.pick_language("hello", None, None) == "en"
        assert nlu.pick_language("hello", None, "invalid") == "en"

    @pytest.mark.parametrize("lang", LANGS)
    def test_every_bot_key_has_all_three_languages(self, lang):
        for key, templates in BOT.items():
            assert lang in templates, f"BOT['{key}'] missing '{lang}'"

    def test_suggestions_have_all_three_languages(self):
        for lang in LANGS:
            assert lang in SUGGESTIONS
            assert len(SUGGESTIONS[lang]) == 4

    def test_unit_names_have_all_three_languages(self):
        for unit_key, translations in UNIT_NAMES.items():
            for lang in LANGS:
                assert lang in translations, \
                    f"UNIT_NAMES['{unit_key}'] missing '{lang}'"

    def test_all_label_kinds_have_all_three_languages(self):
        for kind, entries in LABELS.items():
            for key, translations in entries.items():
                for lang in LANGS:
                    assert lang in translations, \
                        f"LABELS['{kind}']['{key}'] missing '{lang}'"

    def test_all_assumptions_entries_have_all_three_languages(self):
        for i, assumption in enumerate(ASSUMPTIONS):
            for lang in LANGS:
                assert lang in assumption, f"ASSUMPTIONS[{i}] missing '{lang}'"

    @pytest.mark.parametrize("lang", ("hi", "mr"))
    def test_all_assumptions_entries_contain_devanagari(self, lang):
        for i, assumption in enumerate(ASSUMPTIONS):
            text = assumption[lang]
            assert any("\u0900" <= ch <= "\u097f" for ch in text), \
                f"ASSUMPTIONS[{i}]['{lang}'] has no Devanagari: {text[:60]!r}"
