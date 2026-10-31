export default function Card({ className = "", children, as: Tag = "div", ...rest }) {
  return (
    <Tag
      className={`rounded-xl border border-sage-200 bg-white shadow-[0_1px_2px_rgba(31,38,34,0.04)] ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}

export function CardHeader({ title, subtitle, action }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-sage-100 px-5 py-4">
      <div>
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {subtitle && <p className="mt-0.5 text-xs text-ink-mute">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
