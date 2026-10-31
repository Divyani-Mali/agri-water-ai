import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../context/authContext";
import { fmtNum } from "../constants";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/Feedback";
import { ConfirmDialog } from "../components/ui/Modal";
import { useToast } from "../components/ui/toastContext";
import AddFarmModal from "../components/AddFarmModal";
import SummaryCard from "../components/SummaryCard";

export default function Dashboard() {
  const { user } = useAuth();
  const toast = useToast();
  const [farms, setFarms] = useState([]);
  const [fieldCounts, setFieldCounts] = useState({});
  const [unread, setUnread] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [farmRes, unreadRes] = await Promise.all([
        api.get("/api/farms"),
        api.get("/api/alerts/unread-count"),
      ]);
      const list = farmRes.data;
      // one request per farm to count its fields
      const fieldRes = await Promise.all(list.map((f) => api.get(`/api/farms/${f.id}/fields`)));
      const counts = {};
      list.forEach((f, i) => (counts[f.id] = fieldRes[i].data.length));
      setFarms(list);
      setFieldCounts(counts);
      setUnread(unreadRes.data.count);
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const confirmDelete = async () => {
    setDeleting(true);
    try {
      await api.delete(`/api/farms/${toDelete.id}`);
      toast.success(`Farm "${toDelete.name}" deleted`);
      setToDelete(null);
      await load();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setDeleting(false);
    }
  };

  const totalFields = Object.values(fieldCounts).reduce((a, b) => a + b, 0);
  const firstName = user.full_name.split(" ")[0];

  return (
    <>
      <PageHeader
        title={`Welcome back, ${firstName}`}
        subtitle="Manage your farms and open a field to see live sensor data."
        action={
          <Button icon="plus" onClick={() => setShowAdd(true)}>
            Add farm
          </Button>
        }
      />

      {error && !farms.length ? (
        <ErrorState message={error} onRetry={() => { setLoading(true); load(); }} />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <SummaryCard icon="farm" label="Farms" value={loading ? null : fmtNum(farms.length)} to="/#farm-list" />
            <SummaryCard icon="layers" label="Fields" value={loading ? null : fmtNum(totalFields)} to="/fields" />
            <SummaryCard
              icon="bell"
              label="Unread alerts"
              value={loading || unread === null ? null : fmtNum(unread)}
              tone={unread > 0 ? "amber" : "green"}
              to="/alerts"
            />
          </div>

          {error && <ErrorState message={error} onRetry={load} />}

          <div id="farm-list">
          {loading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <Card key={i} className="space-y-3 p-5">
                  <Skeleton className="h-5 w-2/3" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-8 w-full" />
                </Card>
              ))}
            </div>
          ) : farms.length === 0 ? (
            <EmptyState
              icon="sprout"
              title="No farms yet"
              text="Create your first farm, then add fields to start monitoring soil moisture and forecasting water needs."
              action={<Button icon="plus" onClick={() => setShowAdd(true)}>Add your first farm</Button>}
            />
          ) : (
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {farms.map((farm) => (
                <li key={farm.id}>
                  <Card className="flex h-full flex-col p-5 transition-shadow hover:shadow-md">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h2 className="truncate text-base font-semibold text-ink">{farm.name}</h2>
                        <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-soft">
                          <Icon name="mapPin" size={14} />
                          <span className="truncate">{farm.location}</span>
                        </p>
                      </div>
                      <button
                        onClick={() => setToDelete(farm)}
                        aria-label={`Delete farm ${farm.name}`}
                        className="rounded-md p-1.5 text-ink-mute hover:bg-red-50 hover:text-red-600"
                      >
                        <Icon name="trash" size={16} />
                      </button>
                    </div>
                    <p className="mt-4 text-xs text-ink-mute">
                      {fieldCounts[farm.id] ?? 0} {fieldCounts[farm.id] === 1 ? "field" : "fields"}
                    </p>
                    <Link
                      to={`/farms/${farm.id}`}
                      className="mt-auto inline-flex items-center gap-1.5 pt-4 text-sm font-medium text-forest-700 hover:text-forest-900"
                    >
                      Open farm <Icon name="arrowRight" size={15} />
                    </Link>
                  </Card>
                </li>
              ))}
            </ul>
          )}
          </div>
        </div>
      )}

      <AddFarmModal
        open={showAdd}
        onClose={() => setShowAdd(false)}
        onCreated={async (farm) => {
          setShowAdd(false);
          toast.success(`Farm "${farm.name}" created`);
          await load();
        }}
      />
      <ConfirmDialog
        open={Boolean(toDelete)}
        danger
        busy={deleting}
        title="Delete farm?"
        message={toDelete && `"${toDelete.name}" and all of its fields and sensor data will be permanently deleted.`}
        confirmLabel="Delete farm"
        onConfirm={confirmDelete}
        onClose={() => setToDelete(null)}
      />
    </>
  );
}
