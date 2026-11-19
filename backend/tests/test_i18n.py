from app.i18n import (
    ALERT_TEMPLATES, ASSUMPTIONS, BOT, LANGS, SUGGESTIONS, alert_message,
    duration_text, label, render_alert, translate_assumptions,
)

PARAMS = {"field": "Plot 1", "moisture": 12.0, "temperature": 43.0, "rain": 15.0, "minutes": 1320}


def test_every_alert_renders_in_every_language():
    for alert_type, severity in ALERT_TEMPLATES:
        for lang in LANGS:
            text = render_alert(alert_type, severity, PARAMS, lang)
            assert text and "{" not in text and "Plot 1" in text


def test_hindi_and_marathi_alerts_use_devanagari():
    for alert_type, severity in ALERT_TEMPLATES:
        for lang in ("hi", "mr"):
            text = render_alert(alert_type, severity, PARAMS, lang)
            assert any("\u0900" <= ch <= "\u097f" for ch in text)


def test_duration_text():
    assert duration_text(45, "en") == "45 minutes"
    assert duration_text(1320, "en") == "22 hours"
    assert duration_text(5000, "en") == "3 days"
    assert duration_text(1320, "hi") == "22 घंटे"


def test_old_alert_without_numbers_keeps_english_text():
    assert alert_message("dry_soil", "critical", None, "old english text", "hi") == "old english text"


def test_unknown_alert_type_falls_back():
    assert render_alert("unknown", "info", {}, "hi") is None
    assert alert_message("unknown", "info", '{"a": 1}', "fallback", "hi") == "fallback"


def test_every_bot_message_exists_in_all_languages():
    for key, templates in BOT.items():
        assert set(templates) == set(LANGS), key
    assert all(len(SUGGESTIONS[lang]) == 4 for lang in LANGS)


def test_labels():
    assert label("crop", "wheat", "hi") == "गेहूँ"
    assert label("crop", "wheat", "xx") == "Wheat"
    assert label("crop", "unknowncrop", "en") == "Unknowncrop"


def test_assumptions_are_translated_only_when_known():
    english = ASSUMPTIONS[0]["en"]
    assert translate_assumptions(english, "hi") == ASSUMPTIONS[0]["hi"]
    assert translate_assumptions(english, "en") == english
    assert translate_assumptions("something else", "hi") == "something else"



from app.i18n import speakable


def test_speech_text_spells_out_symbols_and_units():
    spoken = speakable("'North Plot': soil moisture 28.0% (Healthy), temperature 28.0 °C, rainfall 0.0 mm.", "en")
    assert "percent" in spoken and "degrees Celsius" in spoken and "millimetres" in spoken
    for symbol in ("%", "°", "(", ")", "'"):
        assert symbol not in spoken


def test_speech_text_reads_dates_and_lines_as_sentences():
    spoken = speakable("Water need:\n2026-10-14: 1 mm\n2026-10-15: 2 mm", "en")
    assert "14 October" in spoken and "15 October" in spoken and "\n" not in spoken
    assert "14 अक्टूबर" in speakable("2026-10-14: 1 मिमी", "hi")
    assert "14 ऑक्टोबर" in speakable("2026-10-14", "mr")


def test_speech_text_leaves_bad_dates_and_unknown_languages_alone():
    assert "2026-13-40" in speakable("date 2026-13-40", "en")
    assert speakable("Hello 2026-10-14", "xx") == "Hello 14 October"