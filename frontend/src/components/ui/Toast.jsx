import { useCallback, useMemo, useState } from "react";
import Icon from "./Icon";
import { ToastContext } from "./toastContext";

const TONE = {
  success: { cls: "border-forest-200 text-forest-800", icon: "checkCircle" },
  error: { cls: "border-red-200 text-red-800", icon: "alertOctagon" },
  info: { cls: "border-sage-300 text-ink", icon: "info" },
};

export default function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const push = useCallback(
    (type, message) => {
      const id = Date.now() + Math.random();
      setToasts((t) => [...t.slice(-3), { id, type, message }]);
      setTimeout(() => remove(id), 4500);
    },
    [remove],
  );

  const api = useMemo(
    () => ({
      success: (m) => push("success", m),
      error: (m) => push("error", m),
      info: (m) => push("info", m),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div aria-live="polite" className="fixed bottom-4 right-4 z-[60] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} className={`toast-in flex items-start gap-3 rounded-lg border bg-white px-4 py-3 text-sm shadow-lg ${TONE[t.type].cls}`}>
            <Icon name={TONE[t.type].icon} size={18} className="mt-0.5" />
            <p className="flex-1">{t.message}</p>
            <button onClick={() => remove(t.id)} aria-label="Dismiss notification" className="text-ink-mute hover:text-ink">
              <Icon name="x" size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
