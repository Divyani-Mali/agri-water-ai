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
import { useToast } from "../components/ui/toastContext";

const SEVERITY = {
  critical: { label: "Critical", icon: "alertOctagon", tone: "red", bar: "bg-red-600", iconCls: "bg-red-50 text-red-700" },
  warning: { label: "Warning", icon: "alertTriangle", tone: "amber", bar: "bg-amber-500", iconCls: "bg-amber-50 text-amber-700" },
  info: { label: "Info", icon: "info", tone: "blue", bar: "bg-sky-500", iconCls: "bg-sky-50 text-sky-700" },
};

const TYPE_LABEL = {
  dry_soil: "Dry soil",
  heat_stress: "Heat stress",
  heavy_rain: "Heavy rain",
  sensor_offline: "Sensor offline",
};

const notifySidebar = () => window.dispatchEvent(new Event("alerts-changed"));

function AlertItem({ alert, busy, onRead }) {
  const s = SEVERITY[alert.severity] || SEVERITY.info;
  return (
    <li>
      <Card className={`relative overflow-hidden ${alert.is_read ? "opacity-70" : ""}`}>
        <span className={`absolute inset-y-0 left-0 w-1 ${s.bar}`} aria-hidden="true" />
        <div className="flex flex-wrap items-start gap-4 p-4 pl-5">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${s.iconCls}`}>
            <Icon name={s.icon} size={20} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={s.tone}>{s.label}</Badge>
              {TYPE_LABEL[alert.alert_type] && <span className="text-xs text-ink-mute">{TYPE_LABEL[alert.alert_type]}</span>}
              {!alert.is_read && <span className="h-2 w-2 rounded-full bg-forest-600" aria-label="Unread" />}
            </div>
            <p className={`mt-2 text-sm text-ink ${alert.is_read ? "" : "font-medium"}`}>{alert.message}</p>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-mute">
              <time dateTime={alert.created_at} title={fmtTime(alert.created_at)}>
                {fmtTime(alert.created_at)} · {timeAgo(alert.created_at)}
              </time>
              <Link to={`/fields/${alert.field_id}`} className="inline-flex items-center gap-1 font-medium text-forest-700 hover:underline">
                {alert.field_name} <Icon name="arrowRight" size={12} />
              </Link>
            </div>
          </div>
          {!alert.is_read && (
            <Button variant="secondary" size="sm" icon="check" loading={busy} onClick={() => onRead(alert.id)}>
              Mark as read
            </Button>
          )}
        </div>
      </Card>
    </li>
  );
}

export default function Alerts() {
  const toast = useToast();
  const [alerts, setAlerts] = useState([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [markingAll, setMarkingAll] = useState(false);
  const requestId = useRef(0);

  // newest first; ignore responses from outdated requests (filter changed meanwhile)
  const load = useCallback(async () => {
    const id = ++requestId.current;
    try {
      const { data } = await api.get("/api/alerts", { params: { unread_only: unreadOnly, limit: 100 } });
      if (id !== requestId.current) return;
      setAlerts([...data].sort((a, b) => b.id - a.id));
      setError("");
    } catch (err) {
      if (id === requestId.current) setError(errorMessage(err));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => {
    // Fetch on mount and poll while this page is active.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
  }, [load]);

  const markRead = async (id) => {
    setBusyId(id);
    try {
      await api.post(`/api/alerts/${id}/read`);
      toast.success("Alert marked as read");
      await load();
      notifySidebar();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const markAll = async () => {
    setMarkingAll(true);
    try {
      await api.post("/api/alerts/read-all");
      toast.success("All alerts marked as read");
      await load();
      notifySidebar();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setMarkingAll(false);
    }
  };

  const unreadCount = alerts.filter((a) => !a.is_read).length;

  return (
    <>
      <PageHeader
        title="Alert centre"
        subtitle="Automatic warnings from your field sensors. This page refreshes every 10 seconds."
        crumbs={[{ label: "Farms", to: "/" }, { label: "Alerts" }]}
        action={
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-sage-300 bg-white px-3 py-2 text-sm text-ink-soft">
              <input
                type="checkbox"
                checked={unreadOnly}
                onChange={(e) => {
                  setLoading(true);
                  setUnreadOnly(e.target.checked);
                }}
                className="h-4 w-4 accent-forest-700"
              />
              Unread only
            </label>
            <Button icon="checkCheck" onClick={markAll} loading={markingAll} disabled={unreadCount === 0}>
              Mark all as read
            </Button>
            <Button as={Link} to="/" variant="secondary" icon="arrowLeft">
              Back to farms
            </Button>
          </div>
        }
      />

      {error && (
        <div className="mb-4">
          <ErrorState message={error} onRetry={load} />
        </div>
      )}

      {loading ? (
        <div className="space-y-3" aria-busy="true">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-24 w-full" />)}
        </div>
      ) : alerts.length === 0 ? (
        !error && (
          <EmptyState
            icon="checkCircle"
            title={unreadOnly ? "No unread alerts" : "No alerts"}
            text={unreadOnly ? "You are all caught up." : "Everything looks fine. Alerts appear here when sensors detect a problem."}
          />
        )
      ) : (
        <ul className="space-y-3">
          {alerts.map((a) => (
            <AlertItem key={a.id} alert={a} busy={busyId === a.id} onRead={markRead} />
          ))}
        </ul>
      )}
    </>
  );
}
