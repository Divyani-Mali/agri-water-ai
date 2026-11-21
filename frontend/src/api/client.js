import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const isLoginCall = err.config?.url?.includes("/api/auth/login");
    if (err.response?.status === 401 && !isLoginCall) {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login")
        window.location.href = "/login";
    }
    return Promise.reject(err);
  },
);

export function errorMessage(err) {
  if (!err.response)
    return "Cannot reach the server. Please check that the backend is running.";
  const status = err.response.status;
  const detail = err.response.data?.detail;
  if (status === 403 && typeof detail !== "string")
    return "You do not have permission to do that.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail[0].msg.replace("Value error, ", "");
  }
  return "Something went wrong. Please try again.";
}

export function sendChat(message, lang) {
  return api.post("/api/chat", { message, lang });
}

export function sendVoice(audio, lang) {
  const form = new FormData();
  form.append("audio", audio);
  return api.post("/api/chat/voice", form, {
    params: lang ? { lang } : undefined,
  });
}

export function sendVoiceChat(audio, lang, audioMode = "url") {
  const form = new FormData();
  form.append("audio", audio);
  return api.post("/api/chat/voice-chat", form, {
    params: { ...(lang ? { lang } : {}), audio_mode: audioMode },
  });
}

export function synthesizeSpeech(text, lang, mode = "stream") {
  return api.post("/api/chat/speech", { text, lang }, {
    params: { mode },
    ...(mode === "stream" ? { responseType: "blob" } : {}),
  });
}

export function getChatAudio(audioId) {
  return api.get(`/api/chat/audio/${audioId}`, { responseType: "blob" });
}

export function getIrrigationLogs(fieldId, limit = 50) {
  return api.get(`/api/fields/${fieldId}/irrigation-logs`, {
    params: { limit },
  });
}

export function getModelInfo() {
  return api.get("/api/ml/model-info");
}

export function updatePreferredLanguage(preferredLanguage) {
  return api.patch("/api/auth/me", { preferred_language: preferredLanguage });
}

export default api;
