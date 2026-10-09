import { Link } from "react-router-dom";
import Icon from "./Icon";

export default function PageHeader({ title, subtitle, crumbs = [], action, meta }) {
  return (
    <header className="mb-6">
      {crumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="mb-2 flex flex-wrap items-center gap-1 text-xs text-ink-mute">
          {crumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <Icon name="chevronRight" size={12} />}
              {c.to ? (
                <Link to={c.to} className="hover:text-forest-700 hover:underline">{c.label}</Link>
              ) : (
                <span aria-current="page" className="text-ink-soft">{c.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-ink-soft">{subtitle}</p>}
          {meta}
        </div>
        {action}
      </div>
    </header>
  );
}
