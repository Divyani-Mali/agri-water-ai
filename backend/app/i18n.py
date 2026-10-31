"""Translations (English, Hindi, Marathi) for alerts, labels and the assistant's replies.

Anything shown to a farmer that comes from the backend is translated here.
Hindi and Marathi texts should be reviewed by a native speaker before a demo.
"""
import json

LANGS = ("en", "hi", "mr")
DEFAULT_LANG = "en"


def normalize_lang(value) -> str:
    return value if value in LANGS else DEFAULT_LANG


# ------------------------------------------------------------------ labels
LABELS = {
    "crop": {
        "wheat": {"en": "Wheat", "hi": "गेहूँ", "mr": "गहू"},
        "rice": {"en": "Rice", "hi": "धान", "mr": "भात"},
        "cotton": {"en": "Cotton", "hi": "कपास", "mr": "कापूस"},
        "sugarcane": {"en": "Sugarcane", "hi": "गन्ना", "mr": "ऊस"},
        "maize": {"en": "Maize", "hi": "मक्का", "mr": "मका"},
        "soybean": {"en": "Soybean", "hi": "सोयाबीन", "mr": "सोयाबीन"},
        "tomato": {"en": "Tomato", "hi": "टमाटर", "mr": "टोमॅटो"},
        "onion": {"en": "Onion", "hi": "प्याज़", "mr": "कांदा"},
    },
    "soil": {
        "sandy": {"en": "Sandy", "hi": "रेतीली", "mr": "वालुकामय"},
        "loamy": {"en": "Loamy", "hi": "दोमट", "mr": "पोयटा"},
        "clay": {"en": "Clay", "hi": "चिकनी", "mr": "चिकण माती"},
    },
    "stage": {
        "initial": {"en": "Initial", "hi": "शुरुआती", "mr": "सुरुवातीची"},
        "development": {"en": "Development", "hi": "विकास", "mr": "वाढीची"},
        "mid": {"en": "Mid-season", "hi": "मध्य अवस्था", "mr": "मध्य अवस्था"},
        "late": {"en": "Late", "hi": "अंतिम", "mr": "शेवटची"},
    },
    "status": {
        "healthy": {"en": "Healthy", "hi": "ठीक है", "mr": "ठीक आहे"},
        "getting_dry": {
            "en": "Getting dry",
            "hi": "सूख रही है",
            "mr": "कोरडी होत आहे",
        },
        "dry": {
            "en": "Dry, irrigation needed",
            "hi": "सूखी, सिंचाई ज़रूरी",
            "mr": "कोरडी, सिंचन आवश्यक",
        },
    },
}


def label(kind: str, key: str, lang: str) -> str:
    entry = LABELS.get(kind, {}).get(key)
    if not entry:
        return str(key).replace("_", " ").capitalize()
    return entry.get(lang) or entry["en"]


# ------------------------------------------------------------------ alerts
DURATION_UNITS = {
    "minutes": {"en": "minutes", "hi": "मिनट", "mr": "मिनिटे"},
    "hours": {"en": "hours", "hi": "घंटे", "mr": "तास"},
    "days": {"en": "days", "hi": "दिन", "mr": "दिवस"},
}


def duration_text(minutes: int, lang: str) -> str:
    minutes = int(minutes)
    if minutes < 120:
        number, unit = minutes, "minutes"
    elif minutes < 2880:
        number, unit = minutes // 60, "hours"
    else:
        number, unit = minutes // 1440, "days"
    return f"{number} {DURATION_UNITS[unit].get(lang, DURATION_UNITS[unit]['en'])}"


ALERT_TEMPLATES = {
    ("dry_soil", "critical"): {
        "en": "Irrigation overdue in '{field}': soil moisture is {moisture}%, below the irrigation trigger.",
        "hi": "'{field}' में सिंचाई का समय निकल गया है: मिट्टी की नमी {moisture}% है, जो सिंचाई की सीमा से कम है।",
        "mr": "'{field}' मध्ये सिंचनाची वेळ उलटून गेली आहे: मातीतील ओलावा {moisture}% आहे, जो सिंचनाच्या मर्यादेपेक्षा कमी आहे.",
    },
    ("dry_soil", "warning"): {
        "en": "Soil in '{field}' is getting dry ({moisture}%). Irrigation will be needed soon.",
        "hi": "'{field}' की मिट्टी सूख रही है ({moisture}%)। जल्द ही सिंचाई की ज़रूरत पड़ेगी।",
        "mr": "'{field}' मधील माती कोरडी होत आहे ({moisture}%). लवकरच सिंचनाची गरज भासेल.",
    },
    ("heat_stress", "critical"): {
        "en": "Extreme heat in '{field}': {temperature} °C. High risk of crop heat stress.",
        "hi": "'{field}' में अत्यधिक गर्मी: {temperature} °C। फसल पर गर्मी के तनाव का खतरा ज़्यादा है।",
        "mr": "'{field}' मध्ये अति उष्णता: {temperature} °C. पिकावर उष्णतेच्या ताणाचा धोका जास्त आहे.",
    },
    ("heat_stress", "warning"): {
        "en": "High temperature in '{field}': {temperature} °C. Crops may need extra water.",
        "hi": "'{field}' में तापमान ज़्यादा है: {temperature} °C। फसलों को अतिरिक्त पानी की ज़रूरत पड़ सकती है।",
        "mr": "'{field}' मध्ये तापमान जास्त आहे: {temperature} °C. पिकांना जास्त पाण्याची गरज भासू शकते.",
    },
    ("heavy_rain", "warning"): {
        "en": "Heavy rain in '{field}' ({rain} mm). Consider postponing irrigation.",
        "hi": "'{field}' में भारी बारिश ({rain} मिमी)। सिंचाई टालने पर विचार करें।",
        "mr": "'{field}' मध्ये जोरदार पाऊस ({rain} मिमी). सिंचन पुढे ढकलण्याचा विचार करा.",
    },
    ("sensor_offline", "warning"): {
        "en": "No sensor data from '{field}' for {duration}. Please check the sensors.",
        "hi": "'{field}' से {duration} से कोई सेंसर डेटा नहीं आया है। कृपया सेंसर जाँचें।",
        "mr": "'{field}' कडून {duration} पासून सेन्सर डेटा आलेला नाही. कृपया सेन्सर तपासा.",
    },
}


def render_alert(alert_type: str, severity: str, params, lang: str):
    """Alert text in the requested language, or None if the alert type is unknown."""
    templates = ALERT_TEMPLATES.get((alert_type, severity))
    if templates is None:
        return None
    values = dict(params or {})
    for key in ("moisture", "temperature", "rain"):
        if key in values:
            values[key] = f"{float(values[key]):.1f}"
    if "minutes" in values:
        values["duration"] = duration_text(values["minutes"], lang)
    template = templates.get(lang) or templates["en"]
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        return None


def alert_message(alert_type, severity, params_json, fallback: str, lang: str) -> str:
    """Translate a stored alert. Old alerts without numbers keep their English text."""
    if params_json:
        try:
            text = render_alert(alert_type, severity, json.loads(params_json), lang)
        except (TypeError, ValueError):
            text = None
        if text:
            return text
    return fallback


# ------------------------------------------------------------------ forecast text
ASSUMPTIONS = [
    {
        "en": "Future weather is assumed equal to the average of the last 3 complete days, with no rain. Soil moisture is held at the latest reading. Connect a weather-forecast API for better accuracy.",
        "hi": "आने वाले दिनों का मौसम पिछले 3 पूरे दिनों के औसत जैसा माना गया है, बारिश नहीं। मिट्टी की नमी को ताज़ा रीडिंग पर स्थिर रखा गया है। बेहतर सटीकता के लिए मौसम पूर्वानुमान API जोड़ें।",
        "mr": "पुढील दिवसांचे हवामान मागील 3 पूर्ण दिवसांच्या सरासरीइतके गृहीत धरले आहे, पाऊस नाही. मातीतील ओलावा ताज्या नोंदीवर स्थिर ठेवला आहे. अधिक अचूकतेसाठी हवामान अंदाज API जोडा.",
    },
    {
        "en": "Weather comes from the Open-Meteo forecast for this farm's location. Days it does not cover use the last 3 days' average with no rain. Soil moisture is held at the latest reading.",
        "hi": "मौसम इस फार्म की जगह के लिए Open-Meteo पूर्वानुमान से लिया गया है। जिन दिनों का पूर्वानुमान नहीं है, उनके लिए पिछले 3 दिनों का औसत माना गया है, बारिश नहीं। मिट्टी की नमी को ताज़ा रीडिंग पर स्थिर रखा गया है।",
        "mr": "हवामान या फार्मच्या ठिकाणासाठी Open-Meteo अंदाजावरून घेतले आहे. ज्या दिवसांचा अंदाज उपलब्ध नाही त्यांच्यासाठी मागील 3 दिवसांची सरासरी, पाऊस नाही, गृहीत धरली आहे. मातीतील ओलावा ताज्या नोंदीवर स्थिर ठेवला आहे.",
    },
    {
        "en": "Live weather forecast unavailable, so future weather is assumed equal to the average of the last 3 complete days, with no rain. Soil moisture is held at the latest reading.",
        "hi": "लाइव मौसम पूर्वानुमान उपलब्ध नहीं है, इसलिए आने वाले दिनों का मौसम पिछले 3 पूरे दिनों के औसत जैसा माना गया है, बारिश नहीं। मिट्टी की नमी को ताज़ा रीडिंग पर स्थिर रखा गया है।",
        "mr": "थेट हवामान अंदाज उपलब्ध नाही, म्हणून पुढील दिवसांचे हवामान मागील 3 पूर्ण दिवसांच्या सरासरीइतके, पाऊस नाही, गृहीत धरले आहे. मातीतील ओलावा ताज्या नोंदीवर स्थिर ठेवला आहे.",
    },
]


def translate_assumptions(text: str, lang: str) -> str:
    if lang == "en":
        return text
    for entry in ASSUMPTIONS:
        if text == entry["en"]:
            return entry.get(lang) or text
    return text


# ------------------------------------------------------------------ chat assistant
BOT = {
    "greeting": {
        "en": "Hello! I can answer questions about your fields. Try one of the suggestions below.",
        "hi": "नमस्ते! मैं आपके खेतों के बारे में सवालों के जवाब दे सकता हूँ। नीचे दिए सुझावों में से कोई एक आज़माएँ।",
        "mr": "नमस्कार! मी तुमच्या शेतांबद्दलच्या प्रश्नांची उत्तरे देऊ शकतो. खालील सूचनांपैकी एक वापरून पहा.",
    },
    "help": {
        "en": "I can tell you how much water a field needs, the latest soil readings, your alerts, which field is driest, and what happens if you skip watering. I can also log your irrigation and convert acre, guntha and hectare. Ask in English, Hindi or Marathi.",
        "hi": "मैं बता सकता हूँ कि किसी खेत को कितना पानी चाहिए, मिट्टी की ताज़ा रीडिंग, आपके अलर्ट, कौन सा खेत सबसे सूखा है, और सिंचाई छोड़ने पर क्या होगा। मैं आपकी सिंचाई दर्ज भी कर सकता हूँ और एकड़, गुंठा और हेक्टेयर बदल सकता हूँ। आप हिंदी, मराठी या अंग्रेज़ी में पूछ सकते हैं।",
        "mr": "मी सांगू शकतो की एखाद्या शेताला किती पाणी हवे, मातीच्या ताज्या नोंदी, तुमचे अलर्ट, कोणते शेत सर्वात कोरडे आहे, आणि सिंचन वगळल्यास काय होईल. मी तुमचे सिंचन नोंदवू शकतो आणि एकर, गुंठा व हेक्टर रूपांतरित करू शकतो. तुम्ही मराठी, हिंदी किंवा इंग्रजीत विचारू शकता.",
    },
    "no_fields": {
        "en": "You have no fields yet. Add a farm and a field first, then ask me again.",
        "hi": "आपका अभी कोई खेत नहीं है। पहले एक फार्म और खेत जोड़ें, फिर मुझसे दोबारा पूछें।",
        "mr": "तुमचे अजून कोणतेही शेत नाही. आधी एक फार्म आणि शेत जोडा, मग मला पुन्हा विचारा.",
    },
    "ask_field": {
        "en": "Which field do you mean? {fields}",
        "hi": "आप किस खेत की बात कर रहे हैं? {fields}",
        "mr": "तुम्ही कोणत्या शेताबद्दल बोलत आहात? {fields}",
    },
    "no_data": {
        "en": "There is no sensor data yet for '{field}'.",
        "hi": "'{field}' के लिए अभी कोई सेंसर डेटा नहीं है।",
        "mr": "'{field}' साठी अजून सेन्सर डेटा नाही.",
    },
    "status": {
        "en": "'{field}': soil moisture {moisture}% ({status}), temperature {temperature} °C, humidity {humidity}%, rainfall {rain} mm.",
        "hi": "'{field}': मिट्टी की नमी {moisture}% ({status}), तापमान {temperature} °C, आर्द्रता {humidity}%, बारिश {rain} मिमी।",
        "mr": "'{field}': मातीतील ओलावा {moisture}% ({status}), तापमान {temperature} °C, आर्द्रता {humidity}%, पाऊस {rain} मिमी.",
    },
    "status_source": {
        "en": "Latest sensor reading ({time} UTC)",
        "hi": "ताज़ा सेंसर रीडिंग ({time} UTC)",
        "mr": "ताजी सेन्सर नोंद ({time} UTC)",
    },
    "water_need": {
        "en": "Estimated water need for '{field}' ({crop}):\n{lines}",
        "hi": "'{field}' ({crop}) के लिए अनुमानित पानी की ज़रूरत:\n{lines}",
        "mr": "'{field}' ({crop}) साठी अंदाजे पाण्याची गरज:\n{lines}",
    },
    "water_line": {
        "en": "{date}: {mm} mm (about {liters} litres)",
        "hi": "{date}: {mm} मिमी (लगभग {liters} लीटर)",
        "mr": "{date}: {mm} मिमी (सुमारे {liters} लिटर)",
    },
    "water_source": {
        "en": "Forecast model ({model}), based on {days} days of sensor data. An estimate, not a guarantee.",
        "hi": "पूर्वानुमान मॉडल ({model}), {days} दिनों के सेंसर डेटा पर आधारित। यह अनुमान है, गारंटी नहीं।",
        "mr": "अंदाज मॉडेल ({model}), {days} दिवसांच्या सेन्सर डेटावर आधारित. हा अंदाज आहे, हमी नाही.",
    },
    "need_data": {
        "en": "I cannot forecast '{field}' yet. It needs at least one full day of sensor readings.",
        "hi": "मैं अभी '{field}' का पूर्वानुमान नहीं लगा सकता। इसके लिए कम से कम एक पूरे दिन की सेंसर रीडिंग चाहिए।",
        "mr": "मी अजून '{field}' चा अंदाज देऊ शकत नाही. त्यासाठी किमान एका पूर्ण दिवसाच्या सेन्सर नोंदी लागतात.",
    },
    "no_model": {
        "en": "The forecast model is not available right now.",
        "hi": "पूर्वानुमान मॉडल अभी उपलब्ध नहीं है।",
        "mr": "अंदाज मॉडेल सध्या उपलब्ध नाही.",
    },
    "alerts_none": {
        "en": "You have no unread alerts.",
        "hi": "आपका कोई अपठित अलर्ट नहीं है।",
        "mr": "तुमचा एकही न वाचलेला अलर्ट नाही.",
    },
    "alerts_list": {
        "en": "You have {count} unread alert(s). Latest:\n{lines}",
        "hi": "आपके {count} अपठित अलर्ट हैं। ताज़ा:\n{lines}",
        "mr": "तुमचे {count} न वाचलेले अलर्ट आहेत. ताजे:\n{lines}",
    },
    "compare": {
        "en": "Driest field right now: '{field}' with soil moisture {moisture}% ({status}).{others}",
        "hi": "इस समय सबसे सूखा खेत: '{field}', मिट्टी की नमी {moisture}% ({status})।{others}",
        "mr": "सध्या सर्वात कोरडे शेत: '{field}', मातीतील ओलावा {moisture}% ({status}).{others}",
    },
    "compare_others": {
        "en": " Others: {list}.",
        "hi": " अन्य: {list}।",
        "mr": " इतर: {list}.",
    },
    "compare_nodata": {
        "en": "There is no sensor data yet for your fields.",
        "hi": "आपके खेतों के लिए अभी कोई सेंसर डेटा नहीं है।",
        "mr": "तुमच्या शेतांसाठी अजून सेन्सर डेटा नाही.",
    },
    "whatif": {
        "en": "If you skip irrigation on '{field}' for {days} day(s), soil moisture may fall from {now}% to about {then}% (estimate). {verdict}",
        "hi": "यदि आप '{field}' में {days} दिन सिंचाई छोड़ दें, तो मिट्टी की नमी {now}% से घटकर लगभग {then}% हो सकती है (अनुमान)। {verdict}",
        "mr": "जर तुम्ही '{field}' मध्ये {days} दिवस सिंचन वगळले, तर मातीतील ओलावा {now}% वरून सुमारे {then}% पर्यंत कमी होऊ शकतो (अंदाज). {verdict}",
    },
    "whatif_low": {
        "en": "That is below the irrigation trigger of {trigger}%, so crops may be stressed.",
        "hi": "यह सिंचाई की सीमा {trigger}% से कम है, इसलिए फसलों पर तनाव पड़ सकता है।",
        "mr": "हे सिंचनाच्या मर्यादेपेक्षा ({trigger}%) कमी आहे, त्यामुळे पिकांवर ताण येऊ शकतो.",
    },
    "whatif_ok": {
        "en": "That stays above the irrigation trigger of {trigger}%.",
        "hi": "यह सिंचाई की सीमा {trigger}% से ऊपर रहती है।",
        "mr": "हे सिंचनाच्या मर्यादेपेक्षा ({trigger}%) जास्त राहते.",
    },
    "log_need_minutes": {
        "en": "Please tell me how long you watered, for example: I watered {field} for 30 minutes.",
        "hi": "कृपया बताएँ कि आपने कितनी देर पानी दिया, जैसे: मैंने {field} में 30 मिनट पानी दिया।",
        "mr": "कृपया सांगा की तुम्ही किती वेळ पाणी दिले, उदा.: मी {field} मध्ये 30 मिनिटे पाणी दिले.",
    },
    "logged": {
        "en": "Saved: '{field}' was irrigated for {minutes} minutes.",
        "hi": "दर्ज किया गया: '{field}' में {minutes} मिनट सिंचाई हुई।",
        "mr": "नोंदवले: '{field}' मध्ये {minutes} मिनिटे सिंचन झाले.",
    },
    "units": {
        "en": "{value} {unit} = {acre} acre = {guntha} guntha = {hectare} hectare",
        "hi": "{value} {unit} = {acre} एकड़ = {guntha} गुंठा = {hectare} हेक्टेयर",
        "mr": "{value} {unit} = {acre} एकर = {guntha} गुंठे = {hectare} हेक्टर",
    },
    "safety": {
        "en": "I cannot advise on pesticides, fertilisers or medicines. Please contact your local Krishi Vigyan Kendra (KVK) or agriculture officer.",
        "hi": "मैं कीटनाशक, खाद या दवाओं पर सलाह नहीं दे सकता। कृपया अपने स्थानीय कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से संपर्क करें।",
        "mr": "मी कीटकनाशके, खते किंवा औषधांबद्दल सल्ला देऊ शकत नाही. कृपया तुमच्या स्थानिक कृषी विज्ञान केंद्राशी (KVK) किंवा कृषी अधिकाऱ्याशी संपर्क साधा.",
    },
    "unknown": {
        "en": "I did not understand that. You can ask about water need, soil moisture, alerts, or which field is driest.",
        "hi": "मैं यह समझ नहीं पाया। आप पानी की ज़रूरत, मिट्टी की नमी, अलर्ट, या सबसे सूखे खेत के बारे में पूछ सकते हैं।",
        "mr": "मला हे समजले नाही. तुम्ही पाण्याची गरज, मातीतील ओलावा, अलर्ट किंवा सर्वात कोरडे शेत याबद्दल विचारू शकता.",
    },
    "limit": {
        "en": "You have reached today's message limit. Please try again tomorrow.",
        "hi": "आप आज की संदेश सीमा तक पहुँच चुके हैं। कृपया कल फिर कोशिश करें।",
        "mr": "तुम्ही आजची संदेश मर्यादा गाठली आहे. कृपया उद्या पुन्हा प्रयत्न करा.",
    },
}

UNIT_NAMES = {
    "acre": {"en": "acre", "hi": "एकड़", "mr": "एकर"},
    "guntha": {"en": "guntha", "hi": "गुंठा", "mr": "गुंठा"},
    "hectare": {"en": "hectare", "hi": "हेक्टेयर", "mr": "हेक्टर"},
}

SUGGESTIONS = {
    "en": [
        "How much water do I need?",
        "What is my soil moisture?",
        "Show my alerts",
        "Which field is driest?",
    ],
    "hi": [
        "मुझे कितना पानी चाहिए?",
        "मिट्टी की नमी कितनी है?",
        "मेरे अलर्ट दिखाओ",
        "कौन सा खेत सबसे सूखा है?",
    ],
    "mr": [
        "मला किती पाणी हवे?",
        "मातीतील ओलावा किती आहे?",
        "माझे अलर्ट दाखवा",
        "कोणते शेत सर्वात कोरडे आहे?",
    ],
}


def say(key: str, lang: str, **params) -> str:
    templates = BOT[key]
    return (templates.get(lang) or templates["en"]).format(**params)