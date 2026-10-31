import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { cap, fmtDate, fmtNum } from "../constants";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/Feedback";

function Fact({ icon, label, value }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon name={icon} size={15} className="text-ink-mute" />
      <span className="text-ink-mute">{label}</span>
      <span className="ml-auto font-medium text-ink">{value}</span>
    </div>
  );
}

export default function Fields() {
  const [farms, setFarms] = useState([]);
  const [fields, setFields] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const { data: farmList } = await api.get("/api/farms");
      const fieldLists = await Promise.all(
        farmList.map(async (farm) => {
          const { data } = await api.get(`/api/farms/${farm.id}/fields`);
          return data.map((field) => ({ ...field, farmName: farm.name }));
        }),
      );
      setFarms(farmList);
      setFields(fieldLists.flat());
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Load the fields when this route becomes active.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  return (
    <>
      <PageHeader
        title="Fields"
        subtitle={loading ? "Loading fields..." : `${fmtNum(fields.length)} fields across ${fmtNum(farms.length)} farms`}
        crumbs={[{ label: "Farms", to: "/" }, { label: "Fields" }]}
        action={<Button as={Link} to="/" variant="secondary" icon="arrowLeft">Back to farms</Button>}
      />

      {error && <div className="mb-4"><ErrorState message={error} onRetry={() => { setLoading(true); load(); }} /></div>}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1, 2].map((item) => (
            <Card key={item} className="space-y-3 p-5" aria-busy="true">
              <Skeleton className="h-5 w-1/2" />
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-9 w-full" />
            </Card>
          ))}
        </div>
      ) : error ? null : fields.length === 0 ? (
        <EmptyState
          icon="layers"
          title="No fields yet"
          text="Add a field to one of your farms to start monitoring sensor readings and irrigation forecasts."
          action={farms.length ? (
            <Button as={Link} to={`/farms/${farms[0].id}`} icon="plus">Open a farm to add a field</Button>
          ) : (
            <Button as={Link} to="/" icon="farm">Go to farms</Button>
          )}
        />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {fields.map((field) => (
            <li key={field.id}>
              <Card className="flex h-full flex-col p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="truncate text-base font-semibold text-ink">{field.name}</h2>
                    <Link to={`/farms/${field.farm_id}`} className="mt-1 inline-flex items-center gap-1 text-sm text-ink-soft hover:text-forest-700 hover:underline">
                      <Icon name="farm" size={14} /> {field.farmName}
                    </Link>
                  </div>
                  <Badge tone="green">{cap(field.crop_type)}</Badge>
                </div>
                <div className="mt-4 space-y-2.5">
                  <Fact icon="mountain" label="Soil" value={cap(field.soil_type)} />
                  <Fact icon="ruler" label="Area" value={`${field.area_acres} acres`} />
                  <Fact icon="calendar" label="Planted" value={fmtDate(field.planting_date)} />
                </div>
                <Button as={Link} to={`/fields/${field.id}`} icon="activity" size="sm" className="mt-5 self-start">
                  View live data
                </Button>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}