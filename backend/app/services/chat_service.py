"""Farm-aware assistant. Every number in a reply comes from the database or the forecast model."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.i18n import SUGGESTIONS, UNIT_NAMES, alert_message, label, say
from app.models.models import Alert, Farm, IrrigationLog, SensorReading, User
from app.models.models import Field as FieldModel
from app.schemas.chat import ChatResponse
from app.services import chat_nlu as nlu
from app.services.forecast_service import ModelNotReady, NotEnoughData, forecast_field
from ml.agronomy import SOILS

MM_TO_PCT = 0.25            # 1 mm of water = 0.25 % soil moisture (400 mm root zone)
MAX_MESSAGES_PER_DAY = 200  # per user; the counter resets when the server restarts
_usage: dict = {}


def _over_limit(user_id: int) -> bool:
    today = datetime.now(timezone.utc).date()
    for key in [k for k in _usage if k[1] != today]:
        del _usage[key]
    _usage[(user_id, today)] = _usage.get((user_id, today), 0) + 1
    return _usage[(user_id, today)] > MAX_MESSAGES_PER_DAY


def _fmt(number: float) -> str:
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _reply(lang, intent, text, source=None, suggestions=True) -> ChatResponse:
    return ChatResponse(
        reply=text,
        lang=lang,
        intent=intent,
        source=source,
        suggestions=SUGGESTIONS[lang] if suggestions else [],
    )


def _user_fields(db: Session, user: User):
    return (
        db.query(FieldModel)
        .join(Farm, FieldModel.farm_id == Farm.id)
        .filter(Farm.owner_id == user.id)
        .order_by(FieldModel.id)
        .all()
    )


def _latest(db: Session, field_id: int):
    return (
        db.query(SensorReading)
        .filter(SensorReading.field_id == field_id)
        .order_by(SensorReading.timestamp.desc())
        .first()
    )


def _moisture_level(soil_type: str, moisture: float):
    soil = SOILS.get(soil_type, SOILS["loamy"])
    ratio = (moisture - soil["wp"]) / (soil["fc"] - soil["wp"])
    if ratio < 0.5:
        return ratio, "dry"
    if ratio < 0.7:
        return ratio, "getting_dry"
    return ratio, "healthy"


# ------------------------------------------------------------------ answers
def _units(text: str, lang: str) -> ChatResponse:
    parsed = nlu.parse_area(text)
    if parsed is None:
        return _reply(lang, "units", say("unknown", lang))
    value, unit = parsed
    acre, guntha, hectare = nlu.convert_area(value, unit)
    reply = say(
        "units", lang,
        value=_fmt(value), unit=UNIT_NAMES[unit][lang],
        acre=_fmt(acre), guntha=_fmt(guntha), hectare=_fmt(hectare),
    )
    return _reply(lang, "units", reply, suggestions=False)


def _status(db: Session, field, lang: str) -> ChatResponse:
    reading = _latest(db, field.id)
    if reading is None:
        return _reply(lang, "status", say("no_data", lang, field=field.name))
    _, level = _moisture_level(field.soil_type, reading.soil_moisture)
    text = say(
        "status", lang,
        field=field.name,
        moisture=f"{reading.soil_moisture:.1f}",
        status=label("status", level, lang),
        temperature=f"{reading.temperature:.1f}",
        humidity=f"{reading.humidity:.0f}",
        rain=f"{reading.rainfall:.1f}",
    )
    source = say("status_source", lang, time=reading.timestamp.strftime("%Y-%m-%d %H:%M"))
    return _reply(lang, "status", text, source)


def _water_need(db: Session, field, lang: str) -> ChatResponse:
    try:
        result = forecast_field(db, field, 3)
    except NotEnoughData:
        return _reply(lang, "water_need", say("need_data", lang, field=field.name))
    except ModelNotReady:
        return _reply(lang, "water_need", say("no_model", lang))

    lines = "\n".join(
        say(
            "water_line", lang,
            date=str(d["target_date"]),
            mm=_fmt(d["predicted_water_mm"]),
            liters=f"{int(d['total_liters']):,}",
        )
        for d in result["forecast"]
    )
    text = say(
        "water_need", lang,
        field=field.name, crop=label("crop", field.crop_type, lang), lines=lines,
    )
    source = say("water_source", lang, model=result["model_name"], days=result["based_on_days"])
    return _reply(lang, "water_need", text, source)


def _what_if(db: Session, field, text: str, lang: str) -> ChatResponse:
    reading = _latest(db, field.id)
    if reading is None:
        return _reply(lang, "what_if", say("no_data", lang, field=field.name))

    days = nlu.parse_days(text)
    try:
        result = forecast_field(db, field, days)
    except NotEnoughData:
        return _reply(lang, "what_if", say("need_data", lang, field=field.name))
    except ModelNotReady:
        return _reply(lang, "what_if", say("no_model", lang))

    soil = SOILS.get(field.soil_type, SOILS["loamy"])
    trigger = soil["wp"] + 0.5 * (soil["fc"] - soil["wp"])
    now = float(reading.soil_moisture)
    total_mm = sum(d["predicted_water_mm"] for d in result["forecast"])
    then = max(soil["wp"], now - total_mm * MM_TO_PCT)

    verdict = say("whatif_low" if then < trigger else "whatif_ok", lang, trigger=_fmt(trigger))
    reply = say(
        "whatif", lang,
        field=field.name, days=days, now=f"{now:.1f}", then=f"{then:.1f}", verdict=verdict,
    )
    source = say("water_source", lang, model=result["model_name"], days=result["based_on_days"])
    return _reply(lang, "what_if", reply, source)


def _log_irrigation(db: Session, user: User, field, text: str, lang: str) -> ChatResponse:
    minutes = nlu.parse_minutes(text)
    if minutes is None or not 1 <= minutes <= 1440:
        return _reply(
            lang, "log_irrigation",
            say("log_need_minutes", lang, field=field.name), suggestions=False,
        )
    db.add(IrrigationLog(field_id=field.id, user_id=user.id, minutes=minutes, source="chat"))
    db.commit()
    return _reply(
        lang, "log_irrigation",
        say("logged", lang, field=field.name, minutes=_fmt(minutes)), suggestions=False,
    )


def _alerts(db: Session, user: User, lang: str) -> ChatResponse:
    query = (
        db.query(Alert)
        .join(FieldModel, Alert.field_id == FieldModel.id)
        .join(Farm, FieldModel.farm_id == Farm.id)
        .filter(Farm.owner_id == user.id, Alert.is_read.is_(False))
    )
    count = query.count()
    if count == 0:
        return _reply(lang, "alerts", say("alerts_none", lang))
    rows = query.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(5).all()
    lines = "\n".join(
        "- " + alert_message(a.alert_type, a.severity, a.params, a.message, lang)
        for a in rows
    )
    return _reply(lang, "alerts", say("alerts_list", lang, count=count, lines=lines))


def _compare(db: Session, fields, lang: str) -> ChatResponse:
    rows = []
    for f in fields:
        reading = _latest(db, f.id)
        if reading is not None:
            ratio, level = _moisture_level(f.soil_type, reading.soil_moisture)
            rows.append((ratio, f, reading, level))
    if not rows:
        return _reply(lang, "compare", say("compare_nodata", lang))

    rows.sort(key=lambda row: row[0])
    _, field, reading, level = rows[0]
    others = ""
    if len(rows) > 1:
        names = ", ".join(f"{row[1].name} ({row[2].soil_moisture:.1f}%)" for row in rows[1:])
        others = say("compare_others", lang, list=names)
    text = say(
        "compare", lang,
        field=field.name,
        moisture=f"{reading.soil_moisture:.1f}",
        status=label("status", level, lang),
        others=others,
    )
    return _reply(lang, "compare", text)


# ------------------------------------------------------------------ entry point
def handle_message(db: Session, user: User, message: str, requested_lang=None) -> ChatResponse:
    lang = nlu.pick_language(message, requested_lang, user.preferred_language)
    if _over_limit(user.id):
        return _reply(lang, "limit", say("limit", lang), suggestions=False)

    text, tokens = nlu.prepare(message)
    intent = nlu.detect_intent(text, tokens)

    if intent == "safety":
        return _reply(lang, intent, say("safety", lang), suggestions=False)
    if intent == "greeting":
        return _reply(lang, intent, say("greeting", lang))
    if intent == "help":
        return _reply(lang, intent, say("help", lang))
    if intent == "unknown":
        return _reply(lang, intent, say("unknown", lang))
    if intent == "units":
        return _units(text, lang)

    fields = _user_fields(db, user)  # only the user's own fields, always
    if not fields:
        return _reply(lang, intent, say("no_fields", lang), suggestions=False)
    if intent == "alerts":
        return _alerts(db, user, lang)
    if intent == "compare":
        return _compare(db, fields, lang)

    field = nlu.match_field(text, fields)
    if field is None:
        names = ", ".join(f.name for f in fields)
        return ChatResponse(
            reply=say("ask_field", lang, fields=names),
            lang=lang,
            intent=intent,
            suggestions=[f.name for f in fields[:6]],
        )

    if intent == "water_need":
        return _water_need(db, field, lang)
    if intent == "what_if":
        return _what_if(db, field, text, lang)
    if intent == "log_irrigation":
        return _log_irrigation(db, user, field, text, lang)
    return _status(db, field, lang)