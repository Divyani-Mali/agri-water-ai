import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../context/authContext";
import { cap } from "../constants";
import Icon from "./ui/Icon";
import Logo from "./ui/Logo";
import ChatWidget from "./ChatWidget";
import { useTranslate } from "../context/authContext";

function NavItem({ to, icon, label, end, badge, collapsed, onNavigate }) {
  const t = useTranslate();
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      title={collapsed ? t(label) : undefined}
      className={({ isActive }) =>
        `group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
          isActive ? "bg-forest-50 text-forest-800" : "text-ink-soft hover:bg-sage-100 hover:text-ink"
        } ${collapsed ? "justify-center" : ""}`
      }
    >
      <Icon name={icon} size={19} />
      {!collapsed && <span className="flex-1">{t(label)}</span>}
      {badge > 0 && (
        <span
          className={`flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 text-[11px] font-semibold text-white ${
            collapsed ? "absolute right-1 top-1" : ""
          }`}
          aria-label={t("{count} unread alerts", { count: badge })}
        >
          {badge > 99 ? "99+" : badge}
        </span>
      )}
    </NavLink>
  );
}

function SidebarContent({ collapsed, unread, schemeUnread, onNavigate, onToggle }) {
  const { user, logout, updateLanguage } = useAuth();
  const t = useTranslate();
  const [languageLoading, setLanguageLoading] = useState(false);
  const [languageError, setLanguageError] = useState("");
  const initials = user.full_name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");

  return (
    <div className="flex h-full flex-col">
      <div className={`flex h-16 items-center border-b border-sage-100 px-4 ${collapsed ? "justify-center" : ""}`}>
        <Logo compact={collapsed} />
      </div>

      <nav aria-label={t("Main")} className="flex-1 space-y-1 px-3 py-4">
        <NavItem to="/" end icon="farm" label="Farms" collapsed={collapsed} onNavigate={onNavigate} />
        <NavItem to="/alerts" icon="bell" label="Alerts" badge={unread} collapsed={collapsed} onNavigate={onNavigate} />
        <NavItem to="/schemes" icon="globe" label="Schemes" badge={schemeUnread} collapsed={collapsed} onNavigate={onNavigate} />
        {user.role === "admin" && (
          <NavItem to="/admin" icon="shield" label="Admin" collapsed={collapsed} onNavigate={onNavigate} />
        )}
      </nav>

      {onToggle && (
        <button
          onClick={onToggle}
          aria-label={t(collapsed ? "Expand sidebar" : "Collapse sidebar")}
          className="mx-3 mb-2 flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-ink-mute hover:bg-sage-100"
        >
          <Icon name={collapsed ? "chevronRight" : "chevronLeft"} size={16} />
          {!collapsed && t("Collapse")}
        </button>
      )}

      <div className="border-t border-sage-100 p-3">
        {!collapsed && (
          <div className="mb-3">
            <label className="mb-1 block text-xs text-ink-mute" htmlFor="preferred-language">
              {t("Preferred language")}
            </label>
            <select
              id="preferred-language"
              value={user.preferred_language || "en"}
              disabled={languageLoading}
              onChange={async (event) => {
                setLanguageLoading(true);
                setLanguageError("");
                try {
                  await updateLanguage(event.target.value);
                } catch (err) {
                  setLanguageError(errorMessage(err));
                } finally {
                  setLanguageLoading(false);
                }
              }}
              className="w-full rounded-lg border border-sage-300 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-forest-600"
            >
              <option value="en">{t("English")}</option>
              <option value="hi">{t("Hindi")}</option>
              <option value="mr">{t("Marathi")}</option>
            </select>
            {languageError && <p className="mt-1 text-xs text-red-600">{languageError}</p>}
          </div>
        )}
        <div className={`flex items-center gap-3 ${collapsed ? "flex-col" : ""}`}>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-forest-100 text-xs font-semibold text-forest-800">
            {initials}
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-ink">{user.full_name}</p>
              <p className="text-xs text-ink-mute">{t(cap(user.role))}</p>
            </div>
          )}
          <button
            onClick={logout}
            aria-label={t("Log out")}
            title={t("Log out")}
            className="rounded-lg p-2 text-ink-mute transition-colors hover:bg-red-50 hover:text-red-600"
          >
            <Icon name="logout" size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

function MobileLanguageSelector() {
  const { user, updateLanguage } = useAuth();
  const t = useTranslate();
  const [languageLoading, setLanguageLoading] = useState(false);
  const [languageError, setLanguageError] = useState("");

  const changeLanguage = async (event) => {
    setLanguageLoading(true);
    setLanguageError("");
    try {
      await updateLanguage(event.target.value);
    } catch (err) {
      setLanguageError(errorMessage(err));
    } finally {
      setLanguageLoading(false);
    }
  };

  return (
    <>
      <label className="flex items-center gap-1.5 rounded-lg border border-sage-200 bg-white px-2 py-1.5 text-ink-soft">
        <Icon name="globe" size={16} />
        <span className="sr-only">{t("Preferred language")}</span>
        <select
          aria-label={t("Preferred language")}
          value={user.preferred_language || "en"}
          disabled={languageLoading}
          onChange={changeLanguage}
          className="max-w-[100px] bg-transparent text-xs font-medium text-ink outline-none disabled:opacity-60"
        >
          <option value="en">{t("English")}</option>
          <option value="hi">{t("Hindi")}</option>
          <option value="mr">{t("Marathi")}</option>
        </select>
      </label>
      {languageError && (
        <p
          role="alert"
          className="absolute right-4 top-full mt-1 max-w-[calc(100vw-2rem)] rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 shadow-sm"
        >
          {languageError}
        </p>
      )}
    </>
  );
}

export default function Layout() {
  const t = useTranslate();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [schemeUnread, setSchemeUnread] = useState(0);
  const location = useLocation();

  // unread alert badge: refresh every 15 seconds and whenever the Alerts page changes something
  useEffect(() => {
    let active = true;
    const load = () =>
      api
        .get("/api/alerts/unread-count")
        .then((res) => {
          if (active) setUnread(res.data.count);
        })
        .catch(() => {});
    load();
    const timer = setInterval(load, 15000);
    window.addEventListener("alerts-changed", load);
    return () => {
      active = false;
      clearInterval(timer);
      window.removeEventListener("alerts-changed", load);
    };
  }, []);

  // scheme notification badge: refresh every 30 seconds
  useEffect(() => {
    let active = true;
    const load = () =>
      api
        .get("/api/schemes/notifications/unread-count")
        .then((res) => {
          if (active) setSchemeUnread(res.data.count);
        })
        .catch(() => {});
    load();
    const timer = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  // scroll to top on navigation
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-sage-50">
      {/* desktop sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 hidden border-r border-sage-200 bg-white transition-[width] duration-200 lg:block ${
          collapsed ? "w-[76px]" : "w-64"
        }`}
      >
        <SidebarContent collapsed={collapsed} unread={unread} schemeUnread={schemeUnread} onToggle={() => setCollapsed((c) => !c)} />
      </aside>

      {/* mobile top bar */}
      <div className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-sage-200 bg-white px-4 lg:hidden">
        <Logo />
        <div className="relative flex items-center gap-2">
          <MobileLanguageSelector />
          <button
            onClick={() => setMobileOpen(true)}
            aria-label={t("Open navigation menu")}
            className="relative rounded-lg p-2 text-ink-soft hover:bg-sage-100"
          >
            <Icon name="menu" size={22} />
            {unread > 0 && <span className="absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-red-600" />}
          </button>
        </div>
      </div>

      {/* mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label={t("Navigation menu")}>
          <div className="absolute inset-0 bg-ink/40" onClick={() => setMobileOpen(false)} />
          <div className="toast-in absolute inset-y-0 left-0 w-72 bg-white shadow-xl">
            <button
              onClick={() => setMobileOpen(false)}
              aria-label={t("Close navigation menu")}
              className="absolute right-3 top-4 rounded-lg p-1.5 text-ink-mute hover:bg-sage-100"
            >
              <Icon name="x" />
            </button>
            <SidebarContent collapsed={false} unread={unread} schemeUnread={schemeUnread} onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <main className={`transition-[padding] duration-200 ${collapsed ? "lg:pl-[76px]" : "lg:pl-64"}`}>
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>
      <ChatWidget />
    </div>
  );
}
