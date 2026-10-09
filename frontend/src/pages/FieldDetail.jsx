import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { cap, fmtClock, fmtDate, fmtNum, fmtTime, moistureStatus, timeAgo, toDate } from "../constants";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import PageHeader from "../components/ui/PageHeader";
import { Banner, EmptyState, ErrorState, Skeleton } from "../components/ui/Feedback";
import MetricCard, { MoistureCard } from "../components/field/MetricCard";
import ReadingCharts from "../components/field/ReadingCharts";
import ForecastPanel from "../components/field/ForecastPanel";

const OFFLINE_AFTER_MINUTES = 10;
const POLL_MS = 5000;

export default function FieldDetail() {
  const { fieldId } = useParams();
  const [field, setField] = useState(null);
  const [farm, setFarm] = useState(null);
  const [fieldError, setFieldError] = useState("");
  const [readings, setReadings] = useState(null);
  const [readingsError, setReadingsError] = useState("");
  const [now, setNow] = useState(() => Date.now());
  const inFlight = useRef(false);

  const loadField = useCallback(async () => {
    try {
      const { data } = await api.get(`/api/fields/${fieldId}`);
      setField(data);
      setFieldError("");
      api.get(`/api/farms/${data.farm_id}`).then((r) => setFarm(r.data)).catch(() => {});
    } catch (err) {
      setFieldError(errorMessage(err));
    }
  }, [fieldId]);

  useEffect(() => {
    // Clear data from the previous field before loading the new route parameter.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setField(null);
    setFarm(null);
    setReadings(null);
    loadField();
  }, [loadField]);

  // live readings every 5 seconds; skip a tick if the previous request is still running
  useEffect(() => {
    let active = true;
    const load = async () => {
      if (inFlight.current) return;
      inFlight.current = true;
      try {
        const { data } = await api.get(`/api/fields/${fieldId}/readings`, { params: { limit: 100 } });
        if (!active) return;
        setReadings(data);
        setReadingsError("");
        setNow(Date.now());
      } catch (err) {
        if (active) setReadingsError(errorMessage(err));
      } finally {
        inFlight.current = false;
      }
    };
    load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      active = false;
      inFlight.current = false;
      clearInterval(timer);
    };
  }, [fieldId]);

  // API returns newest first; charts need oldest first
  const chartData = useMemo(
    () => (readings ? [...readings].reverse().map((r) => ({ ...r, label: fmtClock(r.timestamp) })) : []),
    [readings],
  );

  if (fieldError) {
    return (
      <>
        <PageHeader title="Field" crumbs={[{ label: "Farms", to: "/" }, { label: "Not available" }]} />
        <ErrorState message={fieldError} onRetry={loadField} />
        <Link to="/" className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-forest-700 hover:underline">
          <Icon name="arrowLeft" size={15} /> Back to farms
        </Link>
      </>
    );
  }

  if (!field) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-8 w-1/3" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-32" />)}
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  const latest = readings && readings.length > 0 ? readings[0] : null;
  const ageMinutes = latest ? Math.max(0, Math.round((now - toDate(latest.timestamp).getTime()) / 60000)) : null;
  const offline = latest && ageMinutes > OFFLINE_AFTER_MINUTES;
  const status = latest ? moistureStatus(latest.soil_moisture, field.soil_type) : null;

  let connection = <Badge tone="gray">Waiting for data</Badge>;
  if (latest) {
    connection = offline ? (
      <Badge tone="red"><Icon name="wifiOff" size={12} /> Sensors offline</Badge>
    ) : (
      <Badge tone="green"><Icon name="wifi" size={12} /> Sensors online</Badge>
    );
  }

  return (
    <>
      <PageHeader
        title={field.name}
        crumbs={[
          { label: "Farms", to: "/" },
          { label: farm ? farm.name : "Farm", to: `/farms/${field.farm_id}` },
          { label: field.name },
        ]}
        action={
          <Button as={Link} to={`/farms/${field.farm_id}`} variant="secondary" icon="arrowLeft">
            Back to farm
          </Button>
        }
        meta={
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <Badge tone="green">{cap(field.crop_type)}</Badge>
            <Badge>{cap(field.soil_type)} soil</Badge>
            <Badge>{field.area_acres} acres</Badge>
            <Badge>Planted {fmtDate(field.planting_date)}</Badge>
            {connection}
          </div>
        }
      />

      <div className="space-y-6">
        {readingsError && <ErrorState message={readingsError} />}

        {offline && (
          <Banner tone="warning" title="Sensors appear to be offline">
            The last reading arrived {timeAgo(latest.timestamp, now)} ({fmtTime(latest.timestamp)}). Values below are
            the last known readings.
          </Banner>
        )}

        {readings === null && !readingsError && (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5" aria-busy="true">
            {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-36" />)}
          </div>
        )}

        {readings && readings.length === 0 && (
          <EmptyState
            icon="activity"
            title="No sensor readings yet"
            text={`The sensor simulator must be started for this field (Field ID ${field.id}). Once it posts its first reading, live values appear here automatically.`}
          />
        )}

        {latest && (
          <>
            <section aria-label="Live readings">
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
                <div className="col-span-2 lg:col-span-2">
                  <MoistureCard moisture={latest.soil_moisture} soil={field.soil_type} status={status} />
                </div>
                <MetricCard icon="thermometer" label="Temperature" value={latest.temperature} unit="°C" accent="bg-orange-50 text-orange-700" />
                <MetricCard icon="humidity" label="Humidity" value={latest.humidity} unit="%" accent="bg-sky-50 text-sky-700" />
                <div className="col-span-2 grid grid-cols-2 gap-4 lg:col-span-1 lg:grid-cols-1">
                  <MetricCard icon="cloudRain" label="Rainfall" value={latest.rainfall} unit="mm" accent="bg-sky-50 text-sky-700" />
                  <MetricCard icon="wind" label="Wind speed" value={fmtNum(latest.wind_speed, 1)} unit="km/h" accent="bg-sage-100 text-ink-soft" />
                </div>
              </div>
              <p className="mt-3 flex items-center gap-1.5 text-xs text-ink-mute">
                <Icon name="refresh" size={12} />
                Latest reading {fmtTime(latest.timestamp)} · refreshes every 5 seconds
              </p>
            </section>

            <ReadingCharts data={chartData} soil={field.soil_type} />
          </>
        )}

        <ForecastPanel fieldId={fieldId} />
      </div>
    </>
  );
}
