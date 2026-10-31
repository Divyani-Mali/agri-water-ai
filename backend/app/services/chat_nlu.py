"""Rule-based understanding of farmer questions in English, Hindi, Marathi and
Roman-script Hindi/Marathi. No database and no AI service: easy to test and fully predictable."""
import re

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# ------------------------------------------------------------------ word lists
# Matching rules (see _has): phrases (with a space) match anywhere in the text,
# short words must match a whole word, longer words match as a word prefix.
SAFETY_WORDS = [
    "pesticide", "insecticide", "fungicide", "herbicide", "spray", "fertili",
    "urea", "dosage", "dose", "medicine", "disease", "pest", "pests",
    "kitnashak", "khad", "dawa", "dawai", "davai", "khat", "favarni", "fawarni",
    "कीटनाशक", "किटकनाशक", "उर्वरक", "खाद", "दवा", "दवाई", "औषध", "औषधे",
    "रोग", "बीमारी", "खत", "खते", "फवारणी", "कीड़",
]
LOG_STRONG = [
    "watered", "irrigated", "paani diya", "pani diya", "paani dila", "pani dila",
    "paani dile", "pani dile", "पानी दिया", "पाणी दिले", "पाणी दिलं", "पाणी दिल",
    "सिंचन केले", "सिंचन केलं", "सिंचन केल",
]
LOG_WEAK = ["sinchai ki", "sinchai kar", "सिंचाई की", "सिंचाई कर"]  # also appear in questions
NEED_WORDS = [
    "need", "needs", "forecast", "how much", "kitna", "kitni", "kitne", "कितना",
    "कितनी", "कितने", "किती", "tomorrow", "kal", "कल", "उद्या", "irrigat",
    "sinchai", "सिंचाई", "सिंचन", "paani", "pani", "पानी", "पाणी", "water",
    "chahiye", "चाहिए", "हवे", "pahije", "पाहिजे",
]
STATUS_WORDS = [
    "moisture", "nami", "नमी", "ओलावा", "ओलसर", "reading", "temperature",
    "humidity", "status", "sensor", "तापमान", "स्थिति", "हालत", "परिस्थिती",
    "condition",
]
ALERT_WORDS = [
    "alert", "warning", "alarm", "notification", "अलर्ट", "चेतावनी", "इशारा", "सूचना",
]
COMPARE_WORDS = [
    "driest", "which field", "most dry", "compare", "sabse sukha", "sabse sukhi",
    "सबसे सूखा", "सबसे सूखी", "सर्वात कोरडे", "सर्वात कोरडी", "कौन सा खेत",
    "कौन-सा खेत", "कोणते शेत", "कोणत्या शेताला", "तुलना",
]
WHATIF_WORDS = [
    "what if", "if i skip", "skip", "don't water", "dont water", "without water",
    "agar", "अगर", "jar", "जर", "नहीं दूं", "नहीं दूँ", "न दूं", "न दूँ",
    "नाही दिले", "नाही दिलं", "नाही दिल", "छोड़ दूं", "छोड़ दूँ", "वगळल",
]
CONVERT_WORDS = [
    "convert", "into", "equal", "in acre", "to acre", "to guntha", "to hectare",
    "kitne acre", "how many acre", "how many guntha", "कितने एकड़", "कितने एकड",
    "बराबर", "म्हणजे", "किती एकर", "किती गुंठे",
]
HELP_WORDS = ["help", "what can you do", "मदद", "मदत", "सहायता", "सहाय्य"]
GREETINGS = {"hi", "hello", "hey", "namaste", "namaskar", "नमस्ते", "नमस्कार"}

MARATHI_MARKERS = {
    "आहे", "आहेत", "किती", "माझे", "माझ्या", "माझी", "मला", "पाहिजे",
    "उद्या", "नाही", "कोणते", "कोणत्या",
}

DURATION_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|ghant\w*|घंट\w*|घण्ट\w*|तास\w*|"
    r"minutes?|mins?|mint\w*|मिनट\w*|मिनिट\w*)"
)
DAYS_RE = re.compile(r"(\d+)\s*(?:days?|din|divas|दिन|दिवस)")
AREA_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(acres?|guntha\w*|hectares?|ha\b|एकड़|एकड|एकर|गुंठ\w*|हेक्ट\w*)"
)

HOUR_PREFIXES = ("hour", "hr", "ghant", "घंट", "घण्ट", "तास")


# ------------------------------------------------------------------ basics
def prepare(message: str):
    """Lower-case text with Devanagari digits turned into 0-9, plus its word tokens."""
    text = message.translate(DEVANAGARI_DIGITS).lower().strip()
    tokens = re.findall(r"[a-z0-9\u0900-\u097f]+", text)
    return text, tokens


def has_devanagari(text: str) -> bool:
    return re.search(r"[\u0900-\u097f]", text) is not None


def _has(text: str, tokens, words) -> bool:
    for word in words:
        if " " in word or "'" in word or "-" in word:
            if word in text:
                return True
        elif word.isascii():
            if len(word) >= 5:
                if any(t.startswith(word) for t in tokens):
                    return True
            elif word in tokens:
                return True
        else:  # Devanagari
            if len(word) <= 3:
                if word in tokens:
                    return True
            elif word in text:
                return True
    return False


def pick_language(message: str, requested, user_language) -> str:
    """Reply language: explicit request, else Devanagari text, else the user's setting."""
    if requested in ("en", "hi", "mr"):
        return requested
    if has_devanagari(message):
        if user_language in ("hi", "mr"):
            return user_language
        _, tokens = prepare(message)
        return "mr" if MARATHI_MARKERS & set(tokens) else "hi"
    return user_language if user_language in ("en", "hi", "mr") else "en"


# ------------------------------------------------------------------ intents
def detect_intent(text: str, tokens) -> str:
    if _has(text, tokens, SAFETY_WORDS):
        return "safety"

    has_duration = DURATION_RE.search(text) is not None
    if _has(text, tokens, LOG_STRONG) or (has_duration and _has(text, tokens, LOG_WEAK)):
        return "log_irrigation"

    needs_water = _has(text, tokens, NEED_WORDS)
    if AREA_RE.search(text) and (not needs_water or _has(text, tokens, CONVERT_WORDS)):
        return "units"
    if _has(text, tokens, WHATIF_WORDS):
        return "what_if"
    if _has(text, tokens, COMPARE_WORDS):
        return "compare"
    if _has(text, tokens, ALERT_WORDS):
        return "alerts"

    has_status = _has(text, tokens, STATUS_WORDS)
    if needs_water and not has_status:
        return "water_need"
    if has_status:
        return "status"

    if GREETINGS & set(tokens):
        return "greeting"
    if _has(text, tokens, HELP_WORDS):
        return "help"
    return "unknown"


# ------------------------------------------------------------------ parsing
def parse_minutes(text: str):
    match = DURATION_RE.search(text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    return value * 60 if unit.startswith(HOUR_PREFIXES) else value


def parse_days(text: str, default: int = 3) -> int:
    match = DAYS_RE.search(text)
    days = int(match.group(1)) if match else default
    return max(1, min(7, days))


def parse_area(text: str):
    """Returns (value, 'acre' | 'guntha' | 'hectare') or None."""
    match = AREA_RE.search(text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    if unit.startswith(("acre", "एकड", "एकर")):
        return value, "acre"
    if unit.startswith(("guntha", "गुंठ")):
        return value, "guntha"
    return value, "hectare"


def convert_area(value: float, unit: str):
    """Returns (acre, guntha, hectare). 1 acre = 40 guntha = 0.404686 hectare."""
    if unit == "acre":
        acre = value
    elif unit == "guntha":
        acre = value / 40
    else:
        acre = value * 2.47105
    return acre, acre * 40, acre / 2.47105


def match_field(text: str, fields):
    """The field whose name appears in the message (longest name wins), else the only field."""
    named = [f for f in fields if f.name.lower() in text]
    if named:
        return max(named, key=lambda f: len(f.name))
    if len(fields) == 1:
        return fields[0]
    return None