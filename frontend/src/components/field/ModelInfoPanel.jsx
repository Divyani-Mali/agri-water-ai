import { useEffect, useState } from "react";
import { errorMessage, getModelInfo } from "../../api/client";
import { fmtNum } from "../../constants";
import Card, { CardHeader } from "../ui/Card";
import Badge from "../ui/Badge";
import { ErrorState, Skeleton } from "../ui/Feedback";
import { useTranslate } from "../../context/authContext";

export default function ModelInfoPanel() {
  const t = useTranslate();
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    setInfo(null);
    try {
      const { data } = await getModelInfo();
      setInfo(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, []);

  return (
    <Card>
      <CardHeader
        title="Forecast model"
        subtitle="Model information and evaluation metrics returned by the backend"
        action={info?.best_model ? <Badge tone="green">{info.best_model}</Badge> : null}
      />
      {error && <div className="p-5"><ErrorState message={error} onRetry={load} /></div>}
      {!info && !error && (
        <div className="space-y-2 p-5" aria-busy="true">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}
      {info && (
        <div className="p-5">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-sage-50 p-3">
              <p className="text-xs text-ink-mute">{t("Test days")}</p>
              <p className="mt-1 text-lg font-semibold text-ink">{fmtNum(info.test_days)}</p>
            </div>
            <div className="rounded-lg bg-sage-50 p-3">
              <p className="text-xs text-ink-mute">{t("Training rows")}</p>
              <p className="mt-1 text-lg font-semibold text-ink">{fmtNum(info.train_rows)}</p>
            </div>
            <div className="rounded-lg bg-sage-50 p-3">
              <p className="text-xs text-ink-mute">{t("Test rows")}</p>
              <p className="mt-1 text-lg font-semibold text-ink">{fmtNum(info.test_rows)}</p>
            </div>
            <div className="rounded-lg bg-sage-50 p-3">
              <p className="text-xs text-ink-mute">{t("Best model")}</p>
              <p className="mt-1 text-sm font-semibold text-ink">{info.best_model}</p>
            </div>
          </div>
          {info.results && (
            <div className="mt-4 overflow-x-auto rounded-lg border border-sage-200">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="bg-sage-50 text-xs uppercase tracking-wide text-ink-mute">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">{t("Model")}</th>
                    <th className="px-3 py-2.5 text-right font-medium">{t("MAE")}</th>
                    <th className="px-3 py-2.5 text-right font-medium">{t("RMSE")}</th>
                    <th className="px-4 py-2.5 text-right font-medium">{t("R2")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-sage-100">
                  {Object.entries(info.results).map(([name, metrics]) => (
                    <tr key={name} className="hover:bg-sage-50">
                      <td className="px-4 py-3 font-medium text-ink">{name}</td>
                      <td className="px-3 py-3 text-right tabular-nums text-ink-soft">{metrics.mae}</td>
                      <td className="px-3 py-3 text-right tabular-nums text-ink-soft">{metrics.rmse}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-ink-soft">{metrics.r2}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
