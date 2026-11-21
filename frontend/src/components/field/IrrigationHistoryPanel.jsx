import { useCallback, useEffect, useState } from "react";
import { errorMessage, getIrrigationLogs } from "../../api/client";
import { fmtTime } from "../../constants";
import Card, { CardHeader } from "../ui/Card";
import Badge from "../ui/Badge";
import { EmptyState, ErrorState, Skeleton } from "../ui/Feedback";
import { useTranslate } from "../../context/authContext";

export default function IrrigationHistoryPanel({ fieldId }) {
  const t = useTranslate();
  const [logs, setLogs] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const { data } = await getIrrigationLogs(fieldId, 50);
      setLogs(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [fieldId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  return (
    <Card>
      <CardHeader title="Irrigation history" subtitle="Recent irrigation events recorded for this field" />
      {error && <div className="p-5"><ErrorState message={error} onRetry={load} /></div>}
      {logs === null && !error && (
        <div className="space-y-2 p-5" aria-busy="true">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
        </div>
      )}
      {logs?.length === 0 && (
        <EmptyState icon="clock" title="No irrigation history" text="Irrigation events logged from the chatbot will appear here." />
      )}
      {logs?.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-left text-sm">
            <thead className="bg-sage-50 text-xs uppercase tracking-wide text-ink-mute">
              <tr>
                <th className="px-5 py-2.5 font-medium">{t("Date")}</th>
                <th className="px-3 py-2.5 text-right font-medium">{t("Duration")}</th>
                <th className="px-5 py-2.5 text-right font-medium">{t("Source")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sage-100">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-sage-50">
                  <td className="px-5 py-3 text-ink-soft">
                    <time dateTime={log.created_at}>{fmtTime(log.created_at)}</time>
                  </td>
                  <td className="px-3 py-3 text-right font-medium tabular-nums text-ink">
                    {log.minutes} {t("min")}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <Badge tone="gray">{t(log.source)}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
