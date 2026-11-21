import Icon from "./ui/Icon";
import Logo from "./ui/Logo";
import { useAuth } from "../context/authContext";
import { useTranslate } from "../context/authContext";

const POINTS = [
  { icon: "activity", text: "Live soil moisture, temperature, humidity and rainfall per field" },
  { icon: "droplets", text: "AI-based daily water requirement forecasts for 3 to 7 days" },
  { icon: "bell", text: "Automatic alerts for dry soil, heat stress and offline sensors" },
];

// Shared two-panel layout for the Login and Register pages.
export default function AuthShell({ title, subtitle, children, footer }) {
  const { language, setGuestLanguage } = useAuth();
  const t = useTranslate();
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden flex-col justify-between bg-forest-900 p-12 text-white lg:flex">
        <Logo light />
        <div>
          <h2 className="max-w-md text-3xl font-semibold leading-tight tracking-tight">
            {t("Irrigate when your crops need it, not by guesswork.")}
          </h2>
          <ul className="mt-8 space-y-4">
            {POINTS.map((p) => (
              <li key={p.text} className="flex max-w-md items-start gap-3 text-sm text-forest-100">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10">
                  <Icon name={p.icon} size={16} />
                </span>
                {t(p.text)}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-forest-300">{t("Smart Irrigation AI · Agricultural water demand forecasting")}</p>
      </aside>

      <main className="flex items-center justify-center bg-sage-50 px-4 py-10">
        <div className="w-full max-w-md">
          <div className="mb-4 flex justify-end">
            <label className="flex items-center gap-2 rounded-lg border border-sage-200 bg-white px-3 py-2 text-sm text-ink-soft">
              <Icon name="globe" size={16} />
              <span className="sr-only">{t("Preferred language")}</span>
              <select
                aria-label={t("Preferred language")}
                value={language}
                onChange={(event) => setGuestLanguage(event.target.value)}
                className="bg-transparent text-sm outline-none"
              >
                <option value="en">{t("English")}</option>
                <option value="hi">{t("Hindi")}</option>
                <option value="mr">{t("Marathi")}</option>
              </select>
            </label>
          </div>
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          <div className="rounded-2xl border border-sage-200 bg-white p-7 shadow-sm sm:p-8">
            <h1 className="text-2xl font-semibold tracking-tight text-ink">{t(title)}</h1>
            <p className="mt-1 text-sm text-ink-soft">{t(subtitle)}</p>
            <div className="mt-6">{children}</div>
          </div>
          <div className="mt-6 text-center text-sm text-ink-soft">{footer}</div>
        </div>
      </main>
    </div>
  );
}
