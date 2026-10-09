import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api, { errorMessage } from "../../api/client";
import { cap, fmtDate, fmtNum } from "../../constants";
import Card, { CardHeader } from "../ui/Card";
import { Banner, ErrorState, Skeleton } from "../ui/Feedback";

const AXIS = { fontSize: 11, fill: "#7d877f" };

export default function ForecastPanel({ fieldId }) {
  const [days, setDays] = useState(3);
  const [state, setState] = useState({ status: "loading", data: null, message: "" });
  const [reloadKey, setReloadKey] = useState(0);

  // the forecast is fetched again when the field or the number of days changes
  useEffect(() => {
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState({ status: "loading", data: null, message: "" });
    api
      .get(`/api/fields/${fieldId}/forecast`, { params: { days } })
      .then((res) => {
        if (active) setState({ status: "ok", data: res.data, message: "" });
      })
      .catch((err) => {
        if (!active) return;
        // 400 = the field does not have a full day of sensor data yet
        const status = err.response?.status === 400 ? "not-ready" : "error";
        setState({ status, data: null, message: errorMessage(err) });
      });
    return () => {
      active = false;
    };
  }, [fieldId, days, reloadKey]);

  const { status, data, message } = state;
  const rows = data?.forecast ?? [];
  const chartData = rows.map((r) => ({ ...r, label: fmtDate(r.target_date) }));

  return (
    <Card>
      <CardHeader
        title="Irrigation forecast"
        subtitle="Predicted daily water requirement for this field"
        action={
          <div role="group" aria-label="Forecast length" className="inline-flex rounded-lg border border-sage-300 bg-white p-0.5">
            {[3, 5, 7].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                aria-pressed={days === d}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  days === d ? "bg-forest-700 text-white" : "text-ink-soft hover:bg-sage-100"
                }`}
              >
                {d} days
              </button>
            ))}
          </div>
        }
      />
      <div className="p-5">
        {status === "loading" && (
          <div className="space-y-3" aria-busy="true">
            <Skeleton className="h-56 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}

        {status === "not-ready" && (
          <Banner tone="warning" title="Not enough sensor data for a forecast yet">
            <p>
              {message} The model needs at least one full day of sensor readings for this field before it can predict
              water needs.
            </p>
            <p className="mt-1">
              Next step: keep the sensor simulator running for this field (it posts a reading regularly), or start it
              with its history backfill option, then check again.
            </p>
            <button onClick={() => setReloadKey((k) => k + 1)} className="mt-2 text-sm font-medium underline">
              Check again
            </button>
          </Banner>
        )}

        {status === "error" && <ErrorState message={message} onRetry={() => setReloadKey((k) => k + 1)} />}

        {status === "ok" && rows.length === 0 && (
          <p className="py-8 text-center text-sm text-ink-mute">The backend returned no forecast days.</p>
        )}

        {status === "ok" && rows.length > 0 && (
          <>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e8ebe3" vertical={false} />
                  <XAxis dataKey="label" tick={AXIS} tickLine={false} />
                  <YAxis tick={AXIS} tickLine={false} unit=" mm" width={56} />
                  <Tooltip
                    cursor={{ fill: "#f1f6f2" }}
                    contentStyle={{ borderRadius: 8, border: "1px solid #dde1d6", fontSize: 12 }}
                    formatter={(v) => [`${v} mm`, "Water requirement"]}
                  />
                  <Bar dataKey="predicted_water_mm" name="Water requirement (mm)" fill="#467d55" radius={[4, 4, 0, 0]} maxBarSize={56} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-5 overflow-x-auto rounded-lg border border-sage-200">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="bg-sage-50 text-xs uppercase tracking-wide text-ink-mute">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Date</th>
                    <th className="px-4 py-2.5 font-medium">Growth stage</th>
                    <th className="px-4 py-2.5 text-right font-medium">Crop coeff. (Kc)</th>
                    <th className="px-4 py-2.5 text-right font-medium">Water (mm)</th>
                    <th className="px-4 py-2.5 text-right font-medium">Total (litres)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-sage-100">
                  {rows.map((r) => (
                    <tr key={r.target_date} className="hover:bg-sage-50">
                      <td className="px-4 py-2.5 font-medium text-ink">{fmtDate(r.target_date)}</td>
                      <td className="px-4 py-2.5 text-ink-soft">{cap(r.growth_stage)}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{r.kc}</td>
                      <td className="px-4 py-2.5 text-right font-medium tabular-nums">{r.predicted_water_mm}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{fmtNum(r.total_liters)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <dl className="mt-4 space-y-1 rounded-lg bg-sage-50 p-4 text-xs text-ink-soft">
              <div className="flex flex-wrap gap-x-2">
                <dt className="font-semibold text-ink">Model:</dt>
                <dd>{data.model_name}</dd>
              </div>
              <div className="flex flex-wrap gap-x-2">
                <dt className="font-semibold text-ink">Based on:</dt>
                <dd>{data.based_on_days} day(s) of this field&apos;s sensor data</dd>
              </div>
              <div className="flex flex-wrap gap-x-2">
                <dt className="font-semibold text-ink">Assumptions:</dt>
                <dd>{data.assumptions}</dd>
              </div>
            </dl>
          </>
        )}
      </div>
    </Card>
  );
}
