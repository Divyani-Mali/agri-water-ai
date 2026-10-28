import Icon from "./Icon";
import Button from "./Button";
import Card from "./Card";

export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-md bg-sage-200/70 ${className}`} aria-hidden="true" />;
}

export function EmptyState({ icon = "sprout", title, text, action }) {
  return (
    <Card className="flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-forest-50 text-forest-600">
        <Icon name={icon} size={24} />
      </div>
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {text && <p className="mt-1 max-w-md text-sm text-ink-soft">{text}</p>}
      {action && <div className="mt-5">{action}</div>}
    </Card>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <span className="flex items-center gap-2">
        <Icon name="alertOctagon" size={18} />
        {message}
      </span>
      {onRetry && (
        <Button variant="secondary" size="sm" icon="refresh" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

const BANNER = {
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  error: "border-red-200 bg-red-50 text-red-800",
  info: "border-sky-200 bg-sky-50 text-sky-900",
  success: "border-forest-200 bg-forest-50 text-forest-800",
};
const BANNER_ICON = { warning: "alertTriangle", error: "alertOctagon", info: "info", success: "checkCircle" };

export function Banner({ tone = "info", title, children }) {
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`flex gap-3 rounded-xl border px-4 py-3 text-sm ${BANNER[tone]}`}>
      <Icon name={BANNER_ICON[tone]} size={18} className="mt-0.5" />
      <div>
        {title && <p className="font-semibold">{title}</p>}
        <div>{children}</div>
      </div>
    </div>
  );
}
