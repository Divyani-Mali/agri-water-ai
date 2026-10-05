export const CROPS = [
  "wheat",
  "rice",
  "cotton",
  "sugarcane",
  "maize",
  "soybean",
  "tomato",
  "onion",
];
export const SOILS = ["sandy", "loamy", "clay"];

// soil moisture (%) at field capacity (full) and wilting point (empty)
export const SOIL_RANGE = {
  sandy: { fc: 20, wp: 8 },
  loamy: { fc: 32, wp: 14 },
  clay: { fc: 42, wp: 24 },
};

export const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "");

// irrigation is needed when soil is half-way between wilting point and field capacity
export const irrigationTrigger = (soil) => {
  const { fc, wp } = SOIL_RANGE[soil] || SOIL_RANGE.loamy;
  return wp + 0.5 * (fc - wp);
};

export const moistureStatus = (moisture, soil) => {
  const { fc, wp } = SOIL_RANGE[soil] || SOIL_RANGE.loamy;
  const pct = (moisture - wp) / (fc - wp);
  if (pct < 0.5)
    return { label: "Dry - irrigation needed", cls: "text-red-600" };
  if (pct < 0.7) return { label: "Getting dry", cls: "text-amber-600" };
  return { label: "Healthy", cls: "text-green-600" };
};

// today's date as YYYY-MM-DD in the user's own timezone
export const todayLocal = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
};

// the backend sends UTC times without a "Z"; add it so the browser converts correctly
export const toDate = (s) =>
  new Date(/[zZ]$|[+-]\d\d:?\d\d$/.test(s) ? s : s + "Z");

export const fmtTime = (s) =>
  toDate(s).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })
