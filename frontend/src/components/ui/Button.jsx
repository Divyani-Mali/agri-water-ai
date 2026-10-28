import Icon from "./Icon";

const VARIANTS = {
  primary: "bg-forest-700 text-white hover:bg-forest-800 shadow-sm",
  secondary: "bg-white text-ink border border-sage-300 hover:bg-sage-50",
  danger: "bg-red-600 text-white hover:bg-red-700 shadow-sm",
  ghost: "text-ink-soft hover:bg-sage-100",
  dangerGhost: "text-red-600 hover:bg-red-50",
};
const SIZES = { sm: "px-3 py-1.5 text-xs", md: "px-4 py-2 text-sm" };

export function Spinner({ className = "" }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
}

export default function Button({
  variant = "primary",
  size = "md",
  icon,
  loading = false,
  disabled = false,
  className = "",
  children,
  as: Tag = "button",
  ...rest
}) {
  const props = Tag === "button" ? { type: "button", disabled: disabled || loading } : {};
  return (
    <Tag
      {...props}
      {...rest}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
    >
      {loading ? <Spinner /> : icon && <Icon name={icon} size={size === "sm" ? 14 : 16} />}
      {children}
    </Tag>
  );
}
