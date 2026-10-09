import Icon from "./Icon";

export default function Logo({ compact = false, light = false }) {
  return (
    <span className="flex items-center gap-2.5">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-forest-700 text-white">
        <Icon name="droplets" size={20} />
      </span>
      {!compact && (
        <span className={`text-[15px] font-semibold leading-tight tracking-tight ${light ? "text-white" : "text-ink"}`}>
          Smart Irrigation
          <span className="block text-xs font-medium text-forest-500">AI platform</span>
        </span>
      )}
    </span>
  );
}
