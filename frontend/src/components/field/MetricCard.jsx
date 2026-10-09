import Card from "../ui/Card";
import Icon from "../ui/Icon";
import Badge from "../ui/Badge";
import { SOIL_RANGE, irrigationTrigger } from "../../constants";

export default function MetricCard({ icon, label, value, unit, accent = "text-forest-700 bg-forest-50", children }) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 text-xs font-medium text-ink-mute">
        <span className={`flex h-7 w-7 items-center justify-center rounded-md ${accent}`}>
          <Icon name={icon} size={15} />
        </span>
        {label}
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">
        {value}
        <span className="ml-1 text-sm font-normal text-ink-mute">{unit}</span>
      </p>
      {children}
    </Card>
  );
}

// Soil moisture card: value, status badge and a gauge from wilting point to field capacity.
export function MoistureCard({ moisture, soil, status }) {
  const { wp, fc } = SOIL_RANGE[soil] || SOIL_RANGE.loamy;
  const clamp = (v) => Math.min(100, Math.max(0, v));
  const pos = clamp(((moisture - wp) / (fc - wp)) * 100);
  const triggerPos = clamp(((irrigationTrigger(soil) - wp) / (fc - wp)) * 100);
  const bar = { green: "bg-forest-600", amber: "bg-amber-500", red: "bg-red-600" }[status.tone];

  return (
    <MetricCard icon="droplets" label="Soil moisture" value={moisture} unit="%">
      <div className="mt-2">
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>
      <div className="mt-4">
        <div
          className="relative h-2 rounded-full bg-sage-200"
          role="meter"
          aria-label="Soil moisture between wilting point and field capacity"
          aria-valuemin={wp}
          aria-valuemax={fc}
          aria-valuenow={moisture}
        >
          <div className={`h-2 rounded-full transition-all duration-500 ${bar}`} style={{ width: `${pos}%` }} />
          <div className="absolute -top-1 h-4 w-0.5 bg-ink/70" style={{ left: `${triggerPos}%` }} title="Irrigation trigger" />
        </div>
        <div className="mt-1.5 flex justify-between text-[11px] text-ink-mute">
          <span>{wp}% wilting</span>
          <span>{fc}% capacity</span>
        </div>
      </div>
    </MetricCard>
  );
}
