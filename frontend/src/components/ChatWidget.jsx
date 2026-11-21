import { useEffect, useRef, useState } from "react";
import {
  errorMessage,
  sendChat,
  sendVoice,
  synthesizeSpeech,
} from "../api/client";
import { useAuth } from "../context/authContext";
import { useTranslate } from "../context/authContext";
import Icon from "./ui/Icon";

const QUICK_PROMPTS = [
  { text: "What is my soil moisture?", icon: "humidity" },
  { text: "What alerts do I have?", icon: "bell" },
  { text: "Which field is driest?", icon: "activity" },
  { text: "What can you help me with?", icon: "info" },
];

const FOLLOW_UP_PROMPTS = {
  alerts: ["What is my soil moisture?", "Which field is driest?"],
  compare: ["What is my soil moisture?", "What alerts do I have?"],
  greeting: ["What is my soil moisture?", "What alerts do I have?"],
  help: ["What is my soil moisture?", "What alerts do I have?"],
  log_irrigation: ["What is my soil moisture?", "What alerts do I have?"],
  safety: [],
  status: ["What alerts do I have?", "Which field is driest?"],
  limit: [],
  units: ["Convert 2 acres to hectares", "Convert 1 hectare to acres"],
  unknown: ["What can you help me with?", "What is my soil moisture?"],
  water_need: ["What is my soil moisture?", "Which field is driest?"],
  what_if: ["What is my soil moisture?", "Which field is driest?"],
};

const fieldSuggestions = (chat) => {
  const suggestions = chat.suggestions || [];
  const reply = (chat.reply || "").toLowerCase();
  return suggestions.length && suggestions.every((suggestion) => reply.includes(suggestion.toLowerCase()))
    ? suggestions
    : [];
};

export default function ChatWidget() {
  const { user } = useAuth();
  const t = useTranslate();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [serverFallbackAvailable, setServerFallbackAvailable] = useState(false);
  const [error, setError] = useState("");
  const recorderRef = useRef(null);
  const recognitionRef = useRef(null);
  const chunksRef = useRef([]);
  const chatScrollRef = useRef(null);
  const messagesEndRef = useRef(null);
  const pendingFieldRef = useRef(null);
  const lang = user?.preferred_language || "en";

  useEffect(() => {
    if (messages.length || loading) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    } else if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = 0;
    }
  }, [messages, loading]);

  useEffect(() => () => {
    recognitionRef.current?.abort();
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    window.speechSynthesis?.cancel();
  }, []);

  const rememberFieldQuestion = (chat, question) => {
    const suggestions = fieldSuggestions(chat);
    pendingFieldRef.current = suggestions.length ? { question, suggestions } : null;
  };

  const appendChat = (chat) => {
    const suggestions = fieldSuggestions(chat);
    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        text: chat.reply,
        speech: chat.speech,
        lang: chat.lang,
        intent: chat.intent,
        suggestions,
        followUps: suggestions.length ? [] : FOLLOW_UP_PROMPTS[chat.intent] || FOLLOW_UP_PROMPTS.unknown,
        source: chat.source,
      },
    ]);
  };

  const startNewChat = () => {
    if (loading || recording) return;
    window.speechSynthesis?.cancel();
    pendingFieldRef.current = null;
    setMessages([]);
    setText("");
    setError("");
    setServerFallbackAvailable(false);
  };

  const submitText = async (displayValue, requestValue = displayValue) => {
    const message = requestValue.trim();
    const visibleMessage = displayValue.trim();
    if (!message || loading) return;
    setError("");
    setServerFallbackAvailable(false);
    setMessages((current) => [...current, { role: "user", text: visibleMessage }]);
    setText("");
    setLoading(true);
    try {
      const { data } = await sendChat(message, lang);
      rememberFieldQuestion(data, message);
      appendChat(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const playText = async (speech, responseLang) => {
    setError("");
    const SpeechSynthesisUtterance = window.SpeechSynthesisUtterance;
    if (window.speechSynthesis && SpeechSynthesisUtterance) {
      const utterance = new SpeechSynthesisUtterance(speech);
      utterance.lang = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" }[responseLang] || "en-IN";
      utterance.onerror = (event) => {
        if (event.error !== "canceled" && event.error !== "interrupted") {
          setError(t("The browser could not play the generated audio."));
        }
      };
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
      return;
    }

    try {
      const { data } = await synthesizeSpeech(speech, responseLang || lang, "stream");
      const url = URL.createObjectURL(data);
      const audio = new Audio(url);
      audio.addEventListener("ended", () => URL.revokeObjectURL(url), { once: true });
      audio.addEventListener("error", () => URL.revokeObjectURL(url), { once: true });
      await audio.play();
    } catch (err) {
      setError(err.response ? errorMessage(err) : t("The browser could not play the generated audio."));
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      return;
    }
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  };

  const startRecording = async (useServerTranscription = false) => {
    setError("");
    setServerFallbackAvailable(false);
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!useServerTranscription && SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.lang = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" }[lang] || "en-IN";
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0]?.transcript || "")
          .join(" ")
          .trim();
        if (transcript) submitText(transcript);
        else setError(t("No speech was recognised. Please try again."));
      };
      recognition.onerror = (event) => {
        recognitionRef.current = null;
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          setError(t("Microphone access is blocked. Allow it in this site's browser settings, then try again."));
        } else if (event.error === "audio-capture") {
          setError(t("No microphone was found. Connect a microphone and try again."));
        } else if (event.error === "network") {
          setError(t("Browser speech recognition could not connect. Try server transcription or type your message."));
          setServerFallbackAvailable(true);
        } else if (event.error === "no-speech") {
          setError(t("No speech was recognised. Please try again."));
        } else if (event.error !== "aborted") {
          setError(t("Speech recognition failed. Please try again or type your message."));
        }
        setRecording(false);
      };
      recognition.onend = () => {
        recognitionRef.current = null;
        setRecording(false);
      };
      recognitionRef.current = recognition;
      try {
        recognition.start();
        setRecording(true);
      } catch (err) {
        recognitionRef.current = null;
        setRecording(false);
        setError(err.name === "NotAllowedError"
          ? t("Microphone access is blocked. Allow it in this site's browser settings, then try again.")
          : t("Speech recognition failed. Please try again or type your message."));
      }
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError(t("Voice recording is not supported by this browser."));
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = typeof MediaRecorder.isTypeSupported === "function"
        ? ["audio/webm", "audio/mp4", "audio/ogg"].find((type) => MediaRecorder.isTypeSupported(type))
        : undefined;
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        if (!blob.size) {
          setRecording(false);
          setError(t("No audio was recorded."));
          return;
        }
        const extension = blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm";
        const file = new File([blob], `recording.${extension}`, { type: blob.type });
        setLoading(true);
        try {
          const { data } = await sendVoice(file, lang);
          setMessages((current) => [
            ...current,
            { role: "user", text: data.transcription, voice: true },
          ]);
          rememberFieldQuestion(data.chat, data.transcription);
          appendChat(data.chat);
        } catch (err) {
          setError(errorMessage(err));
        } finally {
          setLoading(false);
          setRecording(false);
        }
      };
      recorder.start();
      setRecording(true);
    } catch (err) {
      setError(err.name === "NotAllowedError"
        ? t("Microphone permission was denied. Allow microphone access and try again.")
        : errorMessage(err));
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 sm:bottom-6 sm:right-6">
      {open && (
        <div
          role="dialog"
          aria-label={t("AI chatbot")}
          className="mb-3 flex h-[min(600px,calc(100vh-6rem))] w-[calc(100vw-2rem)] max-w-[420px] flex-col overflow-hidden rounded-2xl border border-sage-200 bg-white shadow-2xl"
        >
          <div className="flex items-center justify-between border-b border-sage-100 bg-white px-4 py-3">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-forest-700 text-white">
                <Icon name="sprout" size={21} />
              </span>
              <div className="min-w-0">
                <h2 className="truncate text-sm font-semibold text-ink">{t("Irrigation assistant")}</h2>
                <p className="mt-0.5 truncate text-xs text-ink-mute">{t("Farm insights and irrigation guidance")}</p>
              </div>
            </div>
            <div className="ml-2 flex shrink-0 items-center gap-1">
              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={startNewChat}
                  disabled={loading || recording}
                  aria-label={t("Start a new chat")}
                  title={t("Start a new chat")}
                  className="rounded-lg p-2 text-ink-mute transition-colors hover:bg-sage-100 hover:text-ink disabled:opacity-50"
                >
                  <Icon name="refresh" size={17} />
                </button>
              )}
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label={t("Close chatbot")}
                className="rounded-lg p-2 text-ink-mute transition-colors hover:bg-sage-100 hover:text-ink"
              >
                <Icon name="x" size={18} />
              </button>
            </div>
          </div>

          {error && (
            <div role="alert" className="mx-3 mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {error}
              {serverFallbackAvailable && (
                <>
                  <p className="mt-2">{t("Configure OpenAI Whisper in backend/.env to use this fallback.")}</p>
                  <button
                    type="button"
                    disabled={loading || recording}
                    onClick={() => startRecording(true)}
                    className="mt-2 block rounded-md border border-red-300 bg-white px-2 py-1 font-medium hover:bg-red-100 disabled:opacity-50"
                  >
                    {t("Record using server transcription")}
                  </button>
                </>
              )}
            </div>
          )}

          <div ref={chatScrollRef} className="flex-1 space-y-4 overflow-y-auto bg-[#f8faf7] px-4 py-4" aria-live="polite">
            {messages.length === 0 && (
              <div className="rounded-2xl border border-sage-200 bg-white p-3 shadow-sm">
                <div className="mb-2 flex items-center gap-2 text-forest-700">
                  <Icon name="sprout" size={17} />
                  <p className="text-sm font-semibold">{t("Welcome to your farm assistant")}</p>
                </div>
                <p className="text-sm leading-relaxed text-ink-soft">
                  {t("Ask about field conditions, irrigation needs, or alerts.")}
                </p>
              </div>
            )}
            {messages.map((item, index) => (
              <div key={index} className={`flex items-end gap-2 ${item.role === "user" ? "justify-end" : "justify-start"}`}>
                {item.role === "assistant" && (
                  <span className="mb-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-forest-700 text-white">
                    <Icon name="sprout" size={15} />
                  </span>
                )}
                <div className={`max-w-[84%] rounded-2xl px-3.5 py-3 text-sm shadow-sm ${
                  item.role === "user"
                    ? "rounded-br-md bg-forest-700 text-white"
                    : "rounded-bl-md border border-sage-200 bg-white text-ink"
                }`}>
                  {item.role === "assistant" && (
                    <p className="mb-1 text-[11px] font-semibold text-forest-700">{t("Irrigation assistant")}</p>
                  )}
                  {item.voice && (
                    <p className="mb-1 flex items-center gap-1 text-[11px] opacity-75">
                      <Icon name="mic" size={11} /> {t("Voice transcription")}
                    </p>
                  )}
                  <p className="whitespace-pre-wrap">{item.text}</p>
                  {item.source && <p className="mt-2 text-xs text-ink-mute">{item.source}</p>}
                  {item.role === "assistant" && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <button
                        type="button"
                        onClick={() => playText(item.speech || item.text, item.lang)}
                        className="inline-flex items-center gap-1 rounded-md border border-sage-300 bg-white px-2 py-1 text-xs text-ink-soft hover:bg-sage-100"
                      >
                        <Icon name="volume" size={12} /> {t("Play")}
                      </button>
                      {item.suggestions.map((suggestion) => (
                        <button
                          type="button"
                          key={suggestion}
                          disabled={loading || recording}
                          onClick={() => {
                            const pending = pendingFieldRef.current;
                            const request = pending?.suggestions.includes(suggestion)
                              ? `${pending.question} ${suggestion}`
                              : suggestion;
                            submitText(suggestion, request);
                          }}
                          className="rounded-md border border-sage-300 bg-white px-2 py-1 text-xs text-ink-soft hover:bg-sage-100"
                        >
                          {suggestion}
                        </button>
                      ))}
                      {index === messages.length - 1 && item.followUps?.length > 0 && (
                        <div className="mt-2 w-full border-t border-sage-100 pt-2">
                          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-ink-mute">
                            {t("Suggested questions")}
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {item.followUps.map((prompt) => (
                              <button
                                type="button"
                                key={prompt}
                                disabled={loading || recording}
                                onClick={() => submitText(t(prompt))}
                                className="rounded-lg border border-sage-300 bg-white px-2 py-1 text-left text-xs text-ink-soft transition-colors hover:bg-sage-100 disabled:opacity-50"
                              >
                                {t(prompt)}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div role="status" className="flex items-end gap-2">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-forest-700 text-white">
                  <Icon name="sprout" size={15} />
                </span>
                <div className="rounded-2xl rounded-bl-md border border-sage-200 bg-white px-3.5 py-2.5 text-sm text-ink-mute shadow-sm">
                  <span className="mr-2">{t("Thinking...")}</span>
                  <span className="inline-flex gap-1" aria-hidden="true">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-forest-600 [animation-delay:-0.3s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-forest-600 [animation-delay:-0.15s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-forest-600" />
                  </span>
                </div>
              </div>
            )}
            {messages.length === 0 && <div className="space-y-2 pt-1">
              <p className="px-1 text-xs font-semibold uppercase tracking-wide text-ink-mute">
                {t("Suggested questions")}
              </p>
              <div className="grid grid-cols-2 gap-2">
                {QUICK_PROMPTS.map(({ text: prompt, icon }) => (
                  <button
                    type="button"
                    key={prompt}
                    disabled={loading || recording}
                    onClick={() => submitText(t(prompt))}
                    className="flex min-h-14 items-start gap-2 rounded-xl border border-sage-200 bg-white p-2.5 text-left text-xs leading-relaxed text-ink-soft shadow-sm transition-colors hover:border-forest-300 hover:bg-sage-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forest-600 disabled:opacity-50"
                  >
                    <Icon name={icon} size={15} className="mt-0.5 text-forest-700" />
                    <span>{t(prompt)}</span>
                  </button>
                ))}
              </div>
            </div>}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-sage-100 bg-white p-3">
            {recording && (
              <p role="status" className="mb-2 flex items-center gap-2 px-1 text-xs font-medium text-red-700">
                <span className="h-2 w-2 animate-pulse rounded-full bg-red-600" />
                {t("Listening...")}
              </p>
            )}
            <form
              onSubmit={(event) => {
                event.preventDefault();
                submitText(text);
              }}
              className="flex gap-2"
            >
              <input
                value={text}
                onChange={(event) => setText(event.target.value)}
                maxLength={500}
                disabled={loading || recording}
                placeholder={t("Type a message...")}
                aria-label={t("Type a message...")}
                className="min-w-0 flex-1 rounded-xl border border-sage-300 px-3 py-2.5 text-sm text-ink outline-none transition focus:border-forest-600 focus:ring-2 focus:ring-forest-100 disabled:bg-sage-50"
              />
              <button
                type="button"
                onClick={() => recording ? stopRecording() : startRecording()}
                disabled={loading}
                aria-label={t(recording ? "Stop voice recording" : "Start voice chat")}
                className={`rounded-xl border px-3 py-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forest-600 ${
                  recording
                    ? "border-red-300 bg-red-50 text-red-700"
                    : "border-sage-300 bg-white text-ink-soft hover:bg-sage-50"
                }`}
              >
                <Icon name={recording ? "x" : "mic"} size={16} />
              </button>
              <button
                type="submit"
                disabled={loading || recording || !text.trim()}
                className="inline-flex items-center gap-1.5 rounded-xl bg-forest-700 px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-forest-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forest-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {t("Send")} <Icon name="arrowRight" size={15} />
              </button>
            </form>
            <p className="mt-2 px-1 text-[11px] text-ink-mute">{t("Press Enter to send")}</p>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label={t(open ? "Close chatbot" : "Open AI chatbot")}
        className="ml-auto flex h-14 w-14 items-center justify-center rounded-full bg-forest-700 text-white shadow-lg transition-colors hover:bg-forest-800"
      >
        <Icon name={open ? "x" : "message"} size={24} />
      </button>
    </div>
  );
}
