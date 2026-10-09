import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { cap, fmtDate } from "../constants";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/Feedback";
import { ConfirmDialog } from "../components/ui/Modal";
import { useToast } from "../components/ui/toastContext";
import AddFieldModal from "../components/AddFieldModal";

function Fact({ icon, label, value }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon name={icon} size={15} className="text-ink-mute" />
      <span className="text-ink-mute">{label}</span>
      <span className="ml-auto font-medium text-ink">{value}</span>
    </div>
  );
}

export default function FarmDetail() {
  const { farmId } = useParams();
  const toast = useToast();
  const [farm, setFarm] = useState(null);
  const [fields, setFields] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [farmRes, fieldsRes] = await Promise.all([
        api.get(`/api/farms/${farmId}`),
        api.get(`/api/farms/${farmId}/fields`),
      ]);
      setFarm(farmRes.data);
      setFields(fieldsRes.data);
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [farmId]);

  useEffect(() => {
    // Reset page state when navigating between farm IDs.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    load();
  }, [load]);

  const confirmDelete = async () => {
    setDeleting(true);
    try {
      await api.delete(`/api/fields/${toDelete.id}`);
      toast.success(`Field "${toDelete.name}" deleted`);
      setToDelete(null);
      await load();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setDeleting(false);
    }
  };

  if (!farm && !loading) {
    return (
      <>
        <PageHeader title="Farm" crumbs={[{ label: "Farms", to: "/" }, { label: "Not available" }]} />
        <ErrorState message={error || "Farm not found"} onRetry={() => { setLoading(true); load(); }} />
        <Link to="/" className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-forest-700 hover:underline">
          <Icon name="arrowLeft" size={15} /> Back to farms
        </Link>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={farm ? farm.name : "Loading farm..."}
        crumbs={[{ label: "Farms", to: "/" }, { label: farm ? farm.name : "..." }]}
        subtitle={
          farm && (
            <span className="inline-flex items-center gap-1.5">
              <Icon name="mapPin" size={14} /> {farm.location}
            </span>
          )
        }
        action={
          <div className="flex gap-2">
            <Button as={Link} to="/" variant="secondary" icon="arrowLeft">Back</Button>
            <Button icon="plus" onClick={() => setShowAdd(true)} disabled={!farm}>Add field</Button>
          </div>
        }
      />

      {error && farm && <div className="mb-4"><ErrorState message={error} onRetry={load} /></div>}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[0, 1].map((i) => (
            <Card key={i} className="space-y-3 p-5">
              <Skeleton className="h-5 w-1/2" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-9 w-1/3" />
            </Card>
          ))}
        </div>
      ) : fields.length === 0 ? (
        <EmptyState
          icon="layers"
          title="No fields in this farm"
          text="Add a field with its crop, soil type and planting date to start live monitoring."
          action={<Button icon="plus" onClick={() => setShowAdd(true)}>Add field</Button>}
        />
      ) : (
        <>
          <h2 className="mb-3 text-sm font-semibold text-ink-soft">Fields ({fields.length})</h2>
          <ul className="grid gap-4 md:grid-cols-2">
            {fields.map((f) => (
              <li key={f.id}>
                <Card className="flex h-full flex-col p-5 transition-shadow hover:shadow-md">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="truncate text-base font-semibold text-ink">{f.name}</h3>
                      <p className="text-xs text-ink-mute">Field ID: {f.id}</p>
                    </div>
                    <Badge tone="green">{cap(f.crop_type)}</Badge>
                  </div>
                  <div className="mt-4 space-y-2.5">
                    <Fact icon="mountain" label="Soil" value={cap(f.soil_type)} />
                    <Fact icon="ruler" label="Area" value={`${f.area_acres} acres`} />
                    <Fact icon="calendar" label="Planted" value={fmtDate(f.planting_date)} />
                  </div>
                  <div className="mt-5 flex items-center justify-between pt-1">
                    <Button as={Link} to={`/fields/${f.id}`} icon="activity" size="sm">View live data</Button>
                    <Button variant="dangerGhost" size="sm" icon="trash" onClick={() => setToDelete(f)} aria-label={`Delete field ${f.name}`}>
                      Delete
                    </Button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        </>
      )}

      <AddFieldModal
        open={showAdd}
        farmId={farmId}
        onClose={() => setShowAdd(false)}
        onCreated={async (field) => {
          setShowAdd(false);
          toast.success(`Field "${field.name}" added`);
          await load();
        }}
      />
      <ConfirmDialog
        open={Boolean(toDelete)}
        danger
        busy={deleting}
        title="Delete field?"
        message={toDelete && `"${toDelete.name}" and all of its sensor readings will be permanently deleted.`}
        confirmLabel="Delete field"
        onConfirm={confirmDelete}
        onClose={() => setToDelete(null)}
      />
    </>
  );
}
