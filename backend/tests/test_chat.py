import pytest
from datetime import date, timedelta
from types import SimpleNamespace

from app.i18n import LANGS, SUGGESTIONS
from app.services import chat_nlu as nlu
from app.services import chat_service

from chat_helpers import add_alert, register, seed_field


# ---------------------------------------------------------------- understanding
def intent_of(message):
    text, tokens = nlu.prepare(message)
    return nlu.detect_intent(text, tokens)


@pytest.mark.parametrize("lang", LANGS)
def test_suggestion_buttons_map_to_their_intent(lang):
    expected = ["water_need", "status", "alerts", "compare"]
    for message, intent in zip(SUGGESTIONS[lang], expected):
        assert intent_of(message) == intent, message


@pytest.mark.parametrize(
    "message,intent",
    [
        ("I watered North Plot for 30 minutes", "log_irrigation"),
        ("मैंने 45 मिनट पानी दिया", "log_irrigation"),
        ("My plot is 20 guntha", "units"),
        ("20 guntha kitne acre", "units"),
        ("What if I skip watering for 3 days?", "what_if"),
        ("Which pesticide should I spray?", "safety"),
        ("urea kitna dalun", "safety"),
        ("paani kitna dena hai", "water_need"),
        ("hello", "greeting"),
        ("help", "help"),
        ("खतरा है क्या", "unknown"),
        ("asdf qwer", "unknown"),
    ],
)
def test_more_intents(message, intent):
    assert intent_of(message) == intent


def test_parsing_numbers():
    assert nlu.parse_minutes("30 minutes") == 30
    assert nlu.parse_minutes("2 hours") == 120
    assert nlu.parse_minutes(nlu.prepare("१५ मिनट")[0]) == 15
    assert nlu.parse_minutes("no number here") is None
    assert nlu.parse_days("for 5 days") == 5
    assert nlu.parse_days("for 20 days") == 7
    assert nlu.parse_days("hmm") == 3
    assert nlu.parse_area("20 guntha") == (20.0, "guntha")
    assert nlu.parse_area("2 acres") == (2.0, "acre")
    assert nlu.parse_area("1.5 hectare") == (1.5, "hectare")


def test_area_conversion():
    acre, guntha, hectare = nlu.convert_area(20, "guntha")
    assert acre == 0.5 and guntha == 20 and round(hectare, 3) == 0.202


def test_language_choice():
    assert nlu.pick_language("hello", None, "hi") == "hi"
    assert nlu.pick_language("hello", "mr", "hi") == "mr"
    assert nlu.pick_language("मला किती पाणी हवे?", None, "en") == "mr"
    assert nlu.pick_language("मुझे कितना पानी चाहिए", None, "en") == "hi"


def test_field_matching():
    fields = [SimpleNamespace(name="North Plot"), SimpleNamespace(name="South Plot")]
    assert nlu.match_field("soil moisture of south plot", fields).name == "South Plot"
    assert nlu.match_field("soil moisture", fields) is None
    assert nlu.match_field("soil moisture", fields[:1]).name == "North Plot"


# ---------------------------------------------------------------- the assistant
@pytest.fixture(autouse=True)
def reset_usage():
    chat_service._usage.clear()


def ask(client, headers, message, **extra):
    r = client.post("/api/chat", json={"message": message, **extra}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def fake_forecast(mm_per_day):
    def _forecast(db, field, days):
        start = date.today()
        return {
            "model_name": "xgboost",
            "based_on_days": 7,
            "forecast": [
                {
                    "target_date": start + timedelta(days=i),
                    "predicted_water_mm": mm_per_day,
                    "total_liters": 8000.0,
                }
                for i in range(days)
            ],
        }
    return _forecast


def test_status_uses_the_real_reading(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com", moisture=28.0)
    body = ask(client, h, "What is my soil moisture?")
    assert body["intent"] == "status"
    assert "28.0%" in body["reply"]
    assert "UTC" in body["source"]


def test_hindi_user_gets_a_hindi_reply(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "hi")
    seed_field("a@test.com")
    body = ask(client, h, "What is my soil moisture?")
    assert body["lang"] == "hi" and "मिट्टी" in body["reply"]


def test_devanagari_question_gets_a_marathi_reply(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")
    body = ask(client, h, "मातीतील ओलावा किती आहे?")
    assert body["lang"] == "mr" and body["intent"] == "status"


def test_asks_which_field_when_there_are_several(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com", "North Plot")
    seed_field("a@test.com", "South Plot")
    body = ask(client, h, "What is my soil moisture?")
    assert "North Plot" in body["reply"] and "South Plot" in body["reply"]
    assert body["suggestions"] == ["North Plot", "South Plot"]
    assert "'South Plot'" in ask(client, h, "soil moisture of south plot")["reply"]


def test_a_farmer_never_sees_someone_elses_fields(client):
    register(client, "admin@test.com")
    register(client, "a@test.com")
    b = register(client, "b@test.com")
    seed_field("a@test.com")
    body = ask(client, b, "What is my soil moisture?")
    assert body["reply"].startswith("You have no fields")


def test_water_need_comes_from_the_forecast(client, monkeypatch):
    monkeypatch.setattr(chat_service, "forecast_field", fake_forecast(1.0))
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")
    body = ask(client, h, "How much water does North Plot need tomorrow?")
    assert body["intent"] == "water_need"
    assert "1 mm" in body["reply"] and "8,000" in body["reply"]
    assert "xgboost" in body["source"]


def test_forecast_without_enough_data_gives_a_clear_message(client, monkeypatch):
    def not_enough(db, field, days):
        raise chat_service.NotEnoughData()

    monkeypatch.setattr(chat_service, "forecast_field", not_enough)
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com")
    body = ask(client, h, "How much water do I need?")
    assert "at least one full day" in body["reply"]


@pytest.mark.parametrize(
    "mm,expected", [(1.0, "stays above"), (10.0, "below the irrigation trigger")]
)
def test_what_if_skip_watering(client, monkeypatch, mm, expected):
    monkeypatch.setattr(chat_service, "forecast_field", fake_forecast(mm))
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com", moisture=28.0)
    body = ask(client, h, "What if I skip watering for 3 days?")
    assert body["intent"] == "what_if" and expected in body["reply"]


def test_logging_irrigation_by_chat(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    fid = seed_field("a@test.com")
    body = ask(client, h, "I watered North Plot for 30 minutes")
    assert body["intent"] == "log_irrigation" and "30 minutes" in body["reply"]
    logs = client.get(f"/api/fields/{fid}/irrigation-logs", headers=h).json()
    assert len(logs) == 1 and logs[0]["minutes"] == 30


def test_log_without_duration_asks_and_saves_nothing(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    fid = seed_field("a@test.com")
    body = ask(client, h, "I watered North Plot")
    assert "how long" in body["reply"]
    assert client.get(f"/api/fields/{fid}/irrigation-logs", headers=h).json() == []


def test_area_conversion_reply(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    body = ask(client, h, "My plot is 20 guntha")
    assert "0.5 acre" in body["reply"] and "20 guntha" in body["reply"]


def test_pesticide_questions_are_refused(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    body = ask(client, h, "Which pesticide should I spray?")
    assert body["intent"] == "safety" and "Krishi Vigyan Kendra" in body["reply"]


def test_alerts_are_listed_in_the_users_language(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "hi")
    fid = seed_field("a@test.com")
    add_alert(fid)
    body = ask(client, h, "Show my alerts")
    assert body["intent"] == "alerts" and "सिंचाई" in body["reply"]


def test_driest_field(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    seed_field("a@test.com", "North Plot", moisture=30.0)
    seed_field("a@test.com", "South Plot", moisture=16.0)
    body = ask(client, h, "Which field is driest?")
    assert "'South Plot'" in body["reply"]


def test_daily_message_limit(client, monkeypatch):
    monkeypatch.setattr(chat_service, "MAX_MESSAGES_PER_DAY", 2)
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    ask(client, h, "hello")
    ask(client, h, "hello")
    assert ask(client, h, "hello")["intent"] == "limit"


def test_chat_needs_login_and_valid_input(client):
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 401
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    assert client.post("/api/chat", json={"message": "   "}, headers=h).status_code == 422
    assert client.post("/api/chat", json={"message": "x" * 501}, headers=h).status_code == 422
    assert client.post("/api/chat", json={"message": "hi", "lang": "fr"}, headers=h).status_code == 422