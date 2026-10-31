import { useCallback, useEffect, useState } from "react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../context/authContext";
import { cap, fmtDate, fmtNum } from "../constants";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Card, { CardHeader } from "../components/ui/Card";
import PageHeader from "../components/ui/PageHeader";
import { ErrorState, Skeleton } from "../components/ui/Feedback";
import { ConfirmDialog } from "../components/ui/Modal";
import { useToast } from "../components/ui/toastContext";
import SummaryCard from "../components/SummaryCard";

export default function Admin() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(null); // { user, body, title, message, label }
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, u] = await Promise.all([api.get("/api/admin/stats"), api.get("/api/admin/users")]);
      setStats(s.data);
      setUsers(u.data);
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    // Fetching on mount is the external synchronization for this page.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const askDisable = (u) =>
    setPending({
      user: u,
      body: { is_active: !u.is_active },
      title: u.is_active ? "Disable account?" : "Enable account?",
      message: u.is_active
        ? `${u.full_name} will no longer be able to log in or use the platform.`
        : `${u.full_name} will be able to log in again.`,
      label: u.is_active ? "Disable account" : "Enable account",
      danger: u.is_active,
    });

  const askRole = (u) => {
    const next = u.role === "admin" ? "farmer" : "admin";
    setPending({
      user: u,
      body: { role: next },
      title: `Make ${cap(next)}?`,
      message: `${u.full_name} will become ${next === "admin" ? "an admin with full access to user management" : "a farmer without admin access"}.`,
      label: `Make ${cap(next)}`,
      danger: next === "farmer",
    });
  };

  const confirm = async () => {
    setSaving(true);
    try {
      await api.patch(`/api/admin/users/${pending.user.id}`, pending.body);
      toast.success(`${pending.user.full_name} updated`);
      setPending(null);
      await load();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const retry = () => {
    setError("");
    load();
  };

  return (
    <>
      <PageHeader
        title="Admin panel"
        subtitle="System overview and user management."
        crumbs={[{ label: "Farms", to: "/" }, { label: "Admin" }]}
      />

      {error && !stats ? (
        <ErrorState message={error} onRetry={retry} />
      ) : (
        <div className="space-y-6">
          {error && <ErrorState message={error} onRetry={retry} />}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
            <SummaryCard icon="users" label="Total users" value={stats ? fmtNum(stats.users) : null} />
            <SummaryCard icon="farm" label="Total farms" value={stats ? fmtNum(stats.farms) : null} />
            <SummaryCard icon="layers" label="Total fields" value={stats ? fmtNum(stats.fields) : null} />
            <SummaryCard icon="database" label="Sensor readings" value={stats ? fmtNum(stats.readings) : null} />
            <SummaryCard
              icon="bell"
              label="Unread alerts"
              value={stats ? fmtNum(stats.unread_alerts) : null}
              tone={stats && stats.unread_alerts > 0 ? "amber" : "green"}
            />
          </div>

          <Card>
            <CardHeader title={`Users${users ? ` (${fmtNum(users.length)})` : ""}`} subtitle="Disable accounts or change roles. You cannot change your own account." />
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead className="bg-sage-50 text-xs uppercase tracking-wide text-ink-mute">
                  <tr>
                    <th className="px-5 py-2.5 font-medium">Name</th>
                    <th className="px-3 py-2.5 font-medium">Email</th>
                    <th className="px-3 py-2.5 font-medium">Role</th>
                    <th className="px-3 py-2.5 font-medium">Status</th>
                    <th className="px-3 py-2.5 font-medium">Joined</th>
                    <th className="px-5 py-2.5 text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-sage-100">
                  {users === null &&
                    [0, 1, 2].map((i) => (
                      <tr key={i}>
                        <td colSpan={6} className="px-5 py-3"><Skeleton className="h-6 w-full" /></td>
                      </tr>
                    ))}
                  {users?.map((u) => {
                    const isMe = u.id === me.id;
                    return (
                      <tr key={u.id} className="hover:bg-sage-50">
                        <td className="px-5 py-3 font-medium text-ink">
                          {u.full_name} {isMe && <span className="ml-1 text-xs font-normal text-ink-mute">(you)</span>}
                        </td>
                        <td className="px-3 py-3 text-ink-soft">{u.email}</td>
                        <td className="px-3 py-3"><Badge tone={u.role === "admin" ? "blue" : "gray"}>{cap(u.role)}</Badge></td>
                        <td className="px-3 py-3"><Badge tone={u.is_active ? "green" : "red"}>{u.is_active ? "Active" : "Disabled"}</Badge></td>
                        <td className="whitespace-nowrap px-3 py-3 text-ink-soft">{fmtDate(u.created_at.slice(0, 10))}</td>
                        <td className="whitespace-nowrap px-5 py-3 text-right">
                          <div className="inline-flex gap-2">
                            <Button variant="secondary" size="sm" disabled={isMe} onClick={() => askDisable(u)} title={isMe ? "You cannot change your own account" : undefined}>
                              {u.is_active ? "Disable" : "Enable"}
                            </Button>
                            <Button variant="secondary" size="sm" disabled={isMe} onClick={() => askRole(u)} title={isMe ? "You cannot change your own account" : undefined}>
                              Make {u.role === "admin" ? "Farmer" : "Admin"}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      <ConfirmDialog
        open={Boolean(pending)}
        title={pending?.title}
        message={pending?.message}
        confirmLabel={pending?.label}
        danger={pending?.danger}
        busy={saving}
        onConfirm={confirm}
        onClose={() => setPending(null)}
      />
    </>
  );
}
