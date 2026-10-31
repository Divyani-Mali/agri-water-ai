import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../context/authContext";
import { cap } from "../constants";
import Icon from "./ui/Icon";
import Logo from "./ui/Logo";

function NavItem({ to, icon, label, end, badge, collapsed, onNavigate }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        `group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
          isActive ? "bg-forest-50 text-forest-800" : "text-ink-soft hover:bg-sage-100 hover:text-ink"
        } ${collapsed ? "justify-center" : ""}`
      }
    >
      <Icon name={icon} size={19} />
      {!collapsed && <span className="flex-1">{label}</span>}
      {badge > 0 && (
        <span
          className={`flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 text-[11px] font-semibold text-white ${
            collapsed ? "absolute right-1 top-1" : ""
          }`}
          aria-label={`${badge} unread alerts`}
        >
          {badge > 99 ? "99+" : badge}
        </span>
      )}
    </NavLink>
  );
}

function SidebarContent({ collapsed, unread, onNavigate, onToggle }) {
  const { user, logout } = useAuth();
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

      <nav aria-label="Main" className="flex-1 space-y-1 px-3 py-4">
        <NavItem to="/" end icon="farm" label="Farms" collapsed={collapsed} onNavigate={onNavigate} />
        <NavItem to="/alerts" icon="bell" label="Alerts" badge={unread} collapsed={collapsed} onNavigate={onNavigate} />
        {user.role === "admin" && (
          <NavItem to="/admin" icon="shield" label="Admin" collapsed={collapsed} onNavigate={onNavigate} />
        )}
      </nav>

      {onToggle && (
        <button
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="mx-3 mb-2 flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-ink-mute hover:bg-sage-100"
        >
          <Icon name={collapsed ? "chevronRight" : "chevronLeft"} size={16} />
          {!collapsed && "Collapse"}
        </button>
      )}

      <div className="border-t border-sage-100 p-3">
        <div className={`flex items-center gap-3 ${collapsed ? "flex-col" : ""}`}>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-forest-100 text-xs font-semibold text-forest-800">
            {initials}
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-ink">{user.full_name}</p>
              <p className="text-xs text-ink-mute">{cap(user.role)}</p>
            </div>
          )}
          <button
            onClick={logout}
            aria-label="Log out"
            title="Log out"
            className="rounded-lg p-2 text-ink-mute transition-colors hover:bg-red-50 hover:text-red-600"
          >
            <Icon name="logout" size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [unread, setUnread] = useState(0);
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
        <SidebarContent collapsed={collapsed} unread={unread} onToggle={() => setCollapsed((c) => !c)} />
      </aside>

      {/* mobile top bar */}
      <div className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-sage-200 bg-white px-4 lg:hidden">
        <Logo />
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
          className="relative rounded-lg p-2 text-ink-soft hover:bg-sage-100"
        >
          <Icon name="menu" size={22} />
          {unread > 0 && <span className="absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-red-600" />}
        </button>
      </div>

      {/* mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation menu">
          <div className="absolute inset-0 bg-ink/40" onClick={() => setMobileOpen(false)} />
          <div className="toast-in absolute inset-y-0 left-0 w-72 bg-white shadow-xl">
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation menu"
              className="absolute right-3 top-4 rounded-lg p-1.5 text-ink-mute hover:bg-sage-100"
            >
              <Icon name="x" />
            </button>
            <SidebarContent collapsed={false} unread={unread} onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <main className={`transition-[padding] duration-200 ${collapsed ? "lg:pl-[76px]" : "lg:pl-64"}`}>
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
