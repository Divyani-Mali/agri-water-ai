import { useId } from "react";

const inputClass = (invalid) =>
  `w-full rounded-lg border bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-mute transition-colors disabled:bg-sage-100 disabled:text-ink-mute ${
    invalid ? "border-red-400 focus:border-red-500" : "border-sage-300 focus:border-forest-500"
  }`;

// Label + control + inline validation message. `children` is optional: pass a
// <select> as children, otherwise a plain <input> is rendered.
export default function FormField({ label, error, hint, children, ...inputProps }) {
  const id = useId();
  const errId = `${id}-err`;
  const common = {
    id,
    "aria-invalid": Boolean(error),
    "aria-describedby": error ? errId : undefined,
  };
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-ink">
        {label}
      </label>
      {children ? (
        children(common, inputClass(Boolean(error)))
      ) : (
        <input {...common} {...inputProps} className={inputClass(Boolean(error))} />
      )}
      {hint && !error && <p className="mt-1 text-xs text-ink-mute">{hint}</p>}
      {error && (
        <p id={errId} className="mt-1 text-xs font-medium text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
