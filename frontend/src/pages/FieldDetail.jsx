import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api, { errorMessage } from "../api/client";
import {
  SOIL_RANGE,
  cap,
  fmtTime,
  irrigationTrigger,
  moistureStatus,
  toDate,
} from "../constants";

function StatCard({ title, value, unit, note, noteClass = "text-gray-400" }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow">
      <p className="text-xs uppercase tracking-wide text-gray-400">{title}</p>
      <p className="mt-1 text-2xl font-bold text-gray-800">
        {value}
        <span className="ml-1 text-sm font-normal text-gray-500">{unit}</span>
      </p>
      {note && (
        <p className={`mt-1 text-xs font-medium ${noteClass}`}>{note}</p>
      )}
    </div>
  );
}

export default function FieldDetail() {
  const { fieldId } = useParams();

  const [field, setField] = useState(null);
  const [fieldError, setFieldError] = useState("");

  const [readings, setReadings] = useState(null);
  const [readingsError, setReadingsError] = useState("");
  const [now, setNow] = useState(() => Date.now());

  const [days, setDays] = useState(3);
  const [forecast, setForecast] = useState(null);
  const [forecastError, setForecastError] = useState("");
  const [forecastLoading, setForecastLoading] = useState(true);

  // field info
  useEffect(() => {
    api
      .get(`/api/fields/${fieldId}`)
      .then((res) => setField(res.data))
      .catch((err) => setFieldError(errorMessage(err)));
  }, [fieldId]);

  // live sensor readings: refresh every 5 seconds
  useEffect(() => {
    let active = true;
    const load = () =>
      api
        .get(`/api/fields/${fieldId}/readings`, { params: { limit: 72 } })
        .then((res) => {
          if (!active) return;
          setReadings(res.data);
          setReadingsError("");
          setNow(Date.now());
        })
        .catch((err) => {
          if (active) setReadingsError(errorMessage(err));
        });
    load();
    const timer = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [fieldId]);

  // AI forecast
  useEffect(() => {
    let active = true;
    api
      .get(`/api/fields/${fieldId}/forecast`, { params: { days } })
      .then((res) => {
        if (!active) return;
        setForecast(res.data);
        setForecastError("");
      })
      .catch((err) => {
        if (!active) return;
        setForecast(null);
        setForecastError(errorMessage(err));
      })
      .finally(() => {
        if (active) setForecastLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fieldId, days]);

  const chartData = useMemo(
    () =>
      readings
        ? [...readings]
            .reverse()
            .map((r) => ({ ...r, label: fmtTime(r.timestamp) }))
        : [],
    [readings],
  );

  if (fieldError) {
    return (
      <div className="space-y-3">
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">
          {fieldError}
        </div>
        <Link to="/" className="text-green-700 underline">
          ← Back to dashboard
        </Link>
      </div>
    );
  }
  if (!field) return <p className="text-gray-500">Loading...</p>;

  const latest = readings && readings.length > 0 ? readings[0] : null;
  const range = SOIL_RANGE[field.soil_type] || SOIL_RANGE.loamy;
  const status = latest
    ? moistureStatus(latest.soil_moisture, field.soil_type)
    : null;
  const ageMinutes = latest
    ? Math.round((now - toDate(latest.timestamp)) / 60000)
    : null;
  const offline = latest && ageMinutes > 10;

  return (
    <div className="space-y-6">
      <div>
        <Link
          to={`/farms/${field.farm_id}`}
          className="text-sm text-green-700 hover:underline"
        >
          ← Back to farm
        </Link>
        <h1 className="mt-1 text-2xl font-bold text-gray-800">{field.name}</h1>
        <p className="text-sm text-gray-500">
          {cap(field.crop_type)} · {cap(field.soil_type)} soil ·{" "}
          {field.area_acres} acres · planted {field.planting_date}
        </p>
      </div>

      {readingsError && (
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">
          {readingsError}
        </div>
      )}

      {readings && readings.length === 0 && (
        <div className="rounded bg-amber-50 p-4 text-sm text-amber-800">
          No sensor data yet for this field. Start the sensor simulator for
          field ID <b>{field.id}</b> (see the steps below the code).
        </div>
      )}

      {offline && (
        <div className="rounded bg-amber-50 p-3 text-sm text-amber-800">
          ⚠ Sensors offline: the last reading arrived {ageMinutes} minutes ago.
        </div>
      )}

      {latest && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <StatCard
              title="Soil moisture"
              value={latest.soil_moisture}
              unit="%"
              note={status.label}
              noteClass={status.cls}
            />
            <StatCard
              title="Temperature"
              value={latest.temperature}
              unit="°C"
            />
            <StatCard title="Humidity" value={latest.humidity} unit="%" />
            <StatCard title="Rainfall" value={latest.rainfall} unit="mm" />
            <StatCard title="Wind" value={latest.wind_speed} unit="km/h" />
          </div>
          <p className="-mt-3 text-xs text-gray-400">
            Last reading: {fmtTime(latest.timestamp)} · refreshes every 5
            seconds
          </p>

          <div className="rounded-xl bg-white p-5 shadow">
            <h2 className="mb-3 font-semibold text-gray-700">
              Soil moisture (%)
            </h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="label"
                    minTickGap={50}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    domain={[Math.floor(range.wp - 2), Math.ceil(range.fc + 2)]}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip />
                  <ReferenceLine
                    y={irrigationTrigger(field.soil_type)}
                    stroke="#dc2626"
                    strokeDasharray="5 5"
                    label={{
                      value: "Irrigation trigger",
                      fontSize: 11,
                      fill: "#dc2626",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="soil_moisture"
                    name="Soil moisture"
                    stroke="#2e7d32"
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-xl bg-white p-5 shadow">
            <h2 className="mb-3 font-semibold text-gray-700">
              Temperature and humidity
            </h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="label"
                    minTickGap={50}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="temperature"
                    name="Temperature (°C)"
                    stroke="#ef6c00"
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="humidity"
                    name="Humidity (%)"
                    stroke="#1565c0"
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      <div className="rounded-xl bg-white p-5 shadow">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-gray-700">
            🤖 AI irrigation forecast
          </h2>
          <select
            value={days}
            onChange={(e) => {
              setForecastLoading(true);
              setDays(Number(e.target.value));
            }}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            {[3, 5, 7].map((d) => (
              <option key={d} value={d}>
                Next {d} days
              </option>
            ))}
          </select>
        </div>

        {forecastLoading && (
          <p className="text-gray-500">Calculating forecast...</p>
        )}

        {!forecastLoading && forecastError && (
          <div className="rounded bg-amber-50 p-3 text-sm text-amber-800">
            {forecastError}
          </div>
        )}

        {!forecastLoading && forecast && (
          <>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={forecast.forecast}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="target_date" tick={{ fontSize: 11 }} />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    label={{
                      value: "mm/day",
                      angle: -90,
                      position: "insideLeft",
                      fontSize: 11,
                    }}
                  />
                  <Tooltip />
                  <Bar
                    dataKey="predicted_water_mm"
                    name="Water needed (mm)"
                    fill="#1565c0"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b text-xs uppercase text-gray-400">
                  <tr>
                    <th className="py-2">Date</th>
                    <th>Growth stage</th>
                    <th>Kc</th>
                    <th>Water (mm)</th>
                    <th>Total (liters)</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {forecast.forecast.map((d) => (
                    <tr key={d.target_date}>
                      <td className="py-2">{d.target_date}</td>
                      <td>{cap(d.growth_stage)}</td>
                      <td>{d.kc}</td>
                      <td className="font-medium">{d.predicted_water_mm}</td>
                      <td>{d.total_liters.toLocaleString("en-IN")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="mt-3 text-xs text-gray-400">
              Model: {forecast.model_name} · based on {forecast.based_on_days}{" "}
              days of sensor data · {forecast.assumptions}
            </p>
          </>
        )}
      </div>
    </div>
  )
}
