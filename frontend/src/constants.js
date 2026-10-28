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

// relative level 0..1 between wilting point and field capacity
export const moistureLevel = (moisture, soil) => {
  const { fc, wp } = SOIL_RANGE[soil] || SOIL_RANGE.loamy;
  return (moisture - wp) / (fc - wp);
};

// below 0.5 = Dry, 0.5 to 0.7 = Getting dry, above 0.7 = Healthy
export const moistureStatus = (moisture, soil) => {
  const level = moistureLevel(moisture, soil);
  if (level < 0.5) return { label: "Dry", tone: "red", level };
  if (level <= 0.7) return { label: "Getting dry", tone: "amber", level };
  return { label: "Healthy", tone: "green", level };
};

// Indian number formatting, e.g. 1250000 -> 12,50,000
export const fmtNum = (n, digits = 0) =>
  Number(n).toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

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
  });

export const fmtDate = (s) =>
  new Date(s + (s.length === 10 ? "T00:00:00" : "")).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

export const fmtClock = (s) =>
  toDate(s).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

// "5 min ago" style label
export const timeAgo = (s, now = Date.now()) => {
  const mins = Math.max(0, Math.round((now - toDate(s).getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  return `${Math.floor(hrs / 24)} d ago`;
};
