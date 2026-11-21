"""Groq LLM integration for dynamic chatbot responses.

When the rule-based NLU classifies a message as greeting, help, or unknown,
this module calls the Groq API to generate a natural, context-aware reply.
All field data shown to the LLM comes from the database so the model never
invents sensor readings.  The system prompt includes website-feature context
so the LLM can answer platform-usage questions, and allows general-knowledge
questions without forcing an agriculture context.
If the API key is missing or the call fails, ``generate_response`` returns
``None`` and the caller falls back to the existing rule-based reply.
"""
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Alert, Farm, Field, SensorReading, User

logger = logging.getLogger(__name__)

# Production model verified available for this API key via client.models.list()
GROQ_MODEL = "openai/gpt-oss-120b"

_LANG_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi"}


def _build_context(db: Session, user: User) -> str:
    """Return a compact text summary of the user's fields and latest readings."""
    fields = (
        db.query(Field)
        .join(Farm, Field.farm_id == Farm.id)
        .filter(Farm.owner_id == user.id)
        .order_by(Field.id)
        .all()
    )
    if not fields:
        return "The farmer has no fields registered yet."

    lines = []
    for f in fields:
        reading = (
            db.query(SensorReading)
            .filter(SensorReading.field_id == f.id)
            .order_by(SensorReading.timestamp.desc())
            .first()
        )
        parts = [f"Field '{f.name}': crop={f.crop_type}, soil={f.soil_type}"]
        if f.area_acres:
            parts.append(f"area={f.area_acres} acres")
        if reading:
            parts.append(
                f"latest reading ({reading.timestamp.strftime('%Y-%m-%d %H:%M')} UTC): "
                f"soil_moisture={reading.soil_moisture}%, "
                f"temperature={reading.temperature}°C, "
                f"humidity={reading.humidity}%, "
                f"rainfall={reading.rainfall}mm, "
                f"wind_speed={reading.wind_speed}km/h"
            )
        else:
            parts.append("no sensor readings yet")
        lines.append(", ".join(parts))

    unread = (
        db.query(Alert)
        .join(Field, Alert.field_id == Field.id)
        .join(Farm, Field.farm_id == Farm.id)
        .filter(Farm.owner_id == user.id, Alert.is_read.is_(False))
        .count()
    )
    if unread:
        lines.append(f"Unread alerts: {unread}")

    return "\n".join(lines)


def generate_response(db: Session, user: User, message: str, lang: str):
    """Generate a dynamic reply via Groq.

    Returns the reply text, or ``None`` when the API key is missing or the
    call fails (caller falls back to the rule-based response).
    """
    if not settings.GROQ_API_KEY:
        return None

    try:
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)
    except Exception as exc:
        logger.warning("Failed to initialise Groq client: %s", exc)
        return None

    context = _build_context(db, user)
    lang_name = _LANG_NAMES.get(lang, "English")

    system_prompt = (
        f"You are a knowledgeable AI assistant for the Smart Irrigation AI Platform, "
        f"a web application that helps farmers monitor soil moisture, forecast water "
        f"demand, and manage irrigation. You can answer ANY question — agriculture, "
        f"general knowledge, technology, cooking, science, current affairs, or "
        f"anything else. Respond naturally and helpfully.\n\n"
        f"LANGUAGE: Reply in {lang_name}. Match the user's question language exactly — "
        f"Hindi question → Hindi reply, Marathi question → Marathi reply, "
        f"English question → English reply.\n\n"
        f"The farmer's field data from the database:\n{context}\n\n"
        f"WEBSITE FEATURES (use this to answer questions about the platform):\n"
        f"- Registration: Go to the Register page (/register) and create an account "
        f"with email, full name, and password.\n"
        f"- Login: Go to the Login page (/login) and sign in with email and password.\n"
        f"- Forgot password: Use the 'Forgot Password' link on the login page.\n"
        f"- Dashboard (home page): Lists all your farms with summary cards (farm count, "
        f"field count, unread alerts). Click 'Add farm' to create a new farm.\n"
        f"- Farm detail: Click a farm card to see its fields. Click 'Add field' to add "
        f"a field to a farm.\n"
        f"- Fields page (/fields): Lists all fields across all farms with crop type, "
        f"soil type, area (acres), and planting date.\n"
        f"- Field detail: Click any field to see live sensor readings (soil moisture, "
        f"temperature, humidity, rainfall, wind speed) with charts, water demand "
        f"forecasts, irrigation history, and ML model info. Readings refresh every "
        f"5 seconds.\n"
        f"- Alerts page (/alerts): Automatic warnings from field sensors — dry soil, "
        f"heat stress, heavy rain, sensor offline. Filter unread, mark individual or "
        f"all as read. The sidebar shows an unread alert badge.\n"
        f"- Chatbot: The floating chat button in the bottom-right corner. Supports "
        f"text and voice input.\n"
        f"- Language: Set preferred language (English, Hindi, Marathi) from the "
        f"sidebar dropdown.\n"
        f"- Supported crops: wheat, rice, cotton, sugarcane, maize, soybean, tomato, "
        f"onion.\n"
        f"- Supported soil types: sandy, loamy, clay.\n\n"
        f"RULES:\n"
        f"- For questions about the user's fields, sensor readings, or alerts: use "
        f"ONLY the field data provided above. Never invent sensor readings, "
        f"forecasts, or farmer information.\n"
        f"- If field data is unavailable, tell the user clearly.\n"
        f"- For general knowledge questions (science, technology, cooking, people, "
        f"current affairs, etc.): answer normally and helpfully. Do not force an "
        f"agriculture context.\n"
        f"- If asked about pesticides, fertilisers, or medicines: advise contacting "
        f"the local Krishi Vigyan Kendra (KVK) or agriculture officer.\n"
        f"- Be friendly, practical, and concise. Keep responses under 200 words.\n"
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        return reply if reply else None
    except Exception as exc:
        logger.warning("Groq API call failed: %s", exc)
        return None
