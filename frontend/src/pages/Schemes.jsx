import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { fmtTime, timeAgo } from "../constants";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/Feedback";
import Modal from "../components/ui/Modal";
import { useToast } from "../components/ui/toastContext";
import { useTranslate } from "../context/authContext";

const LEVEL_TONE = { central: "green", maharashtra: "blue" };
const LEVEL_LABEL = { central: "Central", maharashtra: "Maharashtra" };

function SchemeCard({ scheme, onOpen, t }) {
  return (
    <li>
      <Card className="flex h-full flex-col p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-ink">{scheme.name}</h2>
            <div className="mt-1.5 flex flex-wrap gap-2">
              <Badge tone={LEVEL_TONE[scheme.level] || "gray"}>{t(LEVEL_LABEL[scheme.level] || scheme.level)}</Badge>
              {scheme.category && <Badge tone="gray">{t(scheme.category)}</Badge>}
            </div>
          </div>
        </div>
        <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-ink-soft">{scheme.description}</p>
        {scheme.deadline && (
          <p className="mt-2 flex items-center gap-1 text-xs text-amber-700">
            <Icon name="calendar" size={13} />
            {t("Deadline")}: {scheme.deadline}
          </p>
        )}
        <div className="mt-auto flex items-center gap-2 pt-4">
          <Button variant="secondary" size="sm" icon="info" onClick={() => onOpen(scheme)}>
            {t("View details")}
          </Button>
          {scheme.application_url && (
            <a
              href={scheme.application_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm font-medium text-forest-700 hover:text-forest-900"
            >
              {t("Apply")} <Icon name="arrowRight" size={14} />
            </a>
          )}
        </div>
      </Card>
    </li>
  );
}

function SchemeDetailModal({ scheme, onClose, t }) {
  if (!scheme) return null;
  const fields = [
    { icon: "checkCircle", label: "Benefits", value: scheme.benefits },
    { icon: "users", label: "Eligibility", value: scheme.eligibility },
    { icon: "layers", label: "Documents required", value: scheme.documents_required },
    { icon: "info", label: "Application process", value: scheme.application_process },
  ];
  return (
    <Modal open={Boolean(scheme)} title={scheme.name} onClose={onClose} busy={false}>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge tone={LEVEL_TONE[scheme.level] || "gray"}>{t(LEVEL_LABEL[scheme.level] || scheme.level)}</Badge>
          {scheme.category && <Badge tone="gray">{t(scheme.category)}</Badge>}
          {scheme.deadline && <Badge tone="amber">{t("Deadline")}: {scheme.deadline}</Badge>}
        </div>
        <p className="text-sm leading-relaxed text-ink">{scheme.description}</p>
        {fields.map(({ icon, label, value }) => (
          <div key={label} className="rounded-lg border border-sage-200 bg-sage-50 p-3">
            <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-forest-700">
              <Icon name={icon} size={14} /> {t(label)}
            </p>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-soft">{value}</p>
          </div>
        ))}
        {scheme.applicable_crops && (
          <p className="text-xs text-ink-mute">
            {t("Applicable crops")}: {scheme.applicable_crops}
          </p>
        )}
        <div className="flex items-center justify-between border-t border-sage-100 pt-3">
          <p className="text-xs text-ink-mute">
            {t("Source")}:{" "}
            <a href={scheme.source_url} target="_blank" rel="noopener noreferrer" className="text-forest-700 hover:underline">
              {scheme.source_url}
            </a>
            {" · "}
            {t("Verified")}: {scheme.last_verified}
          </p>
          {scheme.application_url && (
            <a
              href={scheme.application_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg bg-forest-700 px-3 py-2 text-sm font-medium text-white hover:bg-forest-800"
            >
              {t("Apply on official portal")} <Icon name="arrowRight" size={14} />
            </a>
          )}
        </div>
      </div>
    </Modal>
  );
}

function NotificationItem({ notif, busy, onRead, t }) {
  const TYPE_ICON = { new_scheme: "info", deadline_approaching: "alertTriangle", scheme_updated: "refresh" };
  return (
    <li>
      <Card className={`relative overflow-hidden ${notif.is_read ? "opacity-70" : ""}`}>
        <span className={`absolute inset-y-0 left-0 w-1 ${notif.is_read ? "bg-sage-200" : "bg-forest-600"}`} aria-hidden="true" />
        <div className="flex flex-wrap items-start gap-3 p-4 pl-5">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-sage-50 text-forest-700">
            <Icon name={TYPE_ICON[notif.notification_type] || "info"} size={18} />
          </span>
          <div className="min-w-0 flex-1">
            <p className={`text-sm text-ink ${notif.is_read ? "" : "font-medium"}`}>{notif.message}</p>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 text-xs text-ink-mute">
              <time>{fmtTime(notif.created_at)} · {timeAgo(notif.created_at)}</time>
              <Link to="/schemes" className="font-medium text-forest-700 hover:underline">
                {notif.scheme_name}
              </Link>
            </div>
          </div>
          {!notif.is_read && (
            <Button variant="secondary" size="sm" icon="check" loading={busy} onClick={() => onRead(notif.id)}>
              {t("Mark as read")}
            </Button>
          )}
        </div>
      </Card>
    </li>
  );
}

export default function Schemes() {
  const t = useTranslate();
  const toast = useToast();
  const [tab, setTab] = useState("all");
  const [schemes, setSchemes] = useState([]);
  const [recommended, setRecommended] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [selected, setSelected] = useState(null);
  const [busyNotif, setBusyNotif] = useState(null);
  const [notifCount, setNotifCount] = useState(0);
  const requestId = useRef(0);

  const loadSchemes = useCallback(async () => {
    const id = ++requestId.current;
    try {
      const params = {};
      if (search) params.search = search;
      if (levelFilter) params.level = levelFilter;
      const { data } = await api.get("/api/schemes", { params });
      if (id === requestId.current) {
        setSchemes(data);
        setError("");
      }
    } catch (err) {
      if (id === requestId.current) setError(errorMessage(err));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [search, levelFilter]);

  const loadRecommended = useCallback(async () => {
    try {
      const { data } = await api.get("/api/schemes/recommended");
      setRecommended(data);
    } catch { /* non-fatal */ }
  }, []);

  const loadNotifications = useCallback(async () => {
    try {
      const [listRes, countRes] = await Promise.all([
        api.get("/api/schemes/notifications", { params: { limit: 100 } }),
        api.get("/api/schemes/notifications/unread-count"),
      ]);
      setNotifications(listRes.data);
      setNotifCount(countRes.data.count);
    } catch { /* non-fatal */ }
  }, []);

  useEffect(() => {
    setLoading(true);
    loadSchemes();
    loadRecommended();
    loadNotifications();
  }, [loadSchemes, loadRecommended, loadNotifications]);

  const markRead = async (id) => {
    setBusyNotif(id);
    try {
      await api.post(`/api/schemes/notifications/${id}/read`);
      toast.success(t("Notification marked as read"));
      await loadNotifications();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusyNotif(null);
    }
  };

  const tabs = [
    { key: "all", label: "All Schemes", icon: "globe" },
    { key: "recommended", label: "Recommended", icon: "checkCircle" },
    { key: "notifications", label: "Notifications", icon: "bell", badge: notifCount },
  ];

  return (
    <>
      <PageHeader
        title="Government Schemes"
        subtitle={t("Verified Indian government agriculture schemes and personalized recommendations.")}
        crumbs={[{ label: "Farms", to: "/" }, { label: "Schemes" }]}
        action={
          <Button as={Link} to="/" variant="secondary" icon="arrowLeft">
            {t("Back to farms")}
          </Button>
        }
      />

      {/* Tab bar */}
      <div className="mb-4 flex gap-2 border-b border-sage-200">
        {tabs.map(({ key, label, icon, badge }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`relative flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              tab === key
                ? "border-forest-700 text-forest-800"
                : "border-transparent text-ink-soft hover:text-ink"
            }`}
          >
            <Icon name={icon} size={16} />
            {t(label)}
            {badge > 0 && (
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 text-[11px] font-semibold text-white">
                {badge > 99 ? "99+" : badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {error && <div className="mb-4"><ErrorState message={error} onRetry={loadSchemes} /></div>}

      {/* All Schemes tab */}
      {tab === "all" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t("Search schemes...")}
                className="w-full rounded-lg border border-sage-300 bg-white px-3 py-2 pl-9 text-sm text-ink outline-none focus:border-forest-600 focus:ring-2 focus:ring-forest-100"
              />
              <Icon name="info" size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-mute" />
            </div>
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="rounded-lg border border-sage-300 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-forest-600"
            >
              <option value="">{t("All levels")}</option>
              <option value="central">{t("Central")}</option>
              <option value="maharashtra">{t("Maharashtra")}</option>
            </select>
          </div>

          {loading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <Card key={i} className="space-y-3 p-5">
                  <Skeleton className="h-5 w-2/3" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-12 w-full" />
                </Card>
              ))}
            </div>
          ) : schemes.length === 0 && !error ? (
            <EmptyState
              icon="globe"
              title={t("No schemes found")}
              text={t("Try changing the search or filter.")}
            />
          ) : (
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {schemes.map((s) => (
                <SchemeCard key={s.id} scheme={s} onOpen={setSelected} t={t} />
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Recommended tab */}
      {tab === "recommended" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <Icon name="info" size={16} className="mr-1.5 inline" />
            {t("Recommendations are based on your farm location and crops. They do not guarantee eligibility — always verify on the official portal.")}
          </div>
          {recommended.length === 0 ? (
            <EmptyState
              icon="checkCircle"
              title={t("No recommendations yet")}
              text={t("Add a farm and fields with crop details to get personalized scheme recommendations.")}
            />
          ) : (
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {recommended.map((s) => (
                <SchemeCard key={s.id} scheme={s} onOpen={setSelected} t={t} />
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Notifications tab */}
      {tab === "notifications" && (
        <div className="space-y-3">
          {notifications.length === 0 ? (
            <EmptyState
              icon="bell"
              title={t("No notifications")}
              text={t("You will be notified when new schemes are added or deadlines approach.")}
            />
          ) : (
            <>
              {notifCount > 0 && (
                <div className="mb-2 flex justify-end">
                  <Button variant="secondary" size="sm" icon="checkCheck" onClick={async () => {
                    try {
                      await api.post("/api/schemes/notifications/read-all");
                      toast.success(t("All notifications marked as read"));
                      await loadNotifications();
                    } catch (err) { toast.error(errorMessage(err)); }
                  }}>
                    {t("Mark all as read")}
                  </Button>
                </div>
              )}
              <ul className="space-y-3">
                {notifications.map((n) => (
                  <NotificationItem key={n.id} notif={n} busy={busyNotif === n.id} onRead={markRead} t={t} />
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      <SchemeDetailModal scheme={selected} onClose={() => setSelected(null)} t={t} />
    </>
  );
}
