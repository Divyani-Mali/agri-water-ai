import { Link } from "react-router-dom";
import Card from "./ui/Card";
import Icon from "./ui/Icon";
import { Skeleton } from "./ui/Feedback";

const TONES = {
  green: "bg-forest-50 text-forest-700",
  amber: "bg-amber-50 text-amber-700",
  red: "bg-red-50 text-red-700",
  gray: "bg-sage-100 text-ink-soft",
};

// Small statistic card used on the Farms and Admin pages. value=null shows a skeleton.
export default function SummaryCard({ icon, label, value, tone = "green", to }) {
  const body = (
    <Card className={`flex items-center gap-4 p-4 ${to ? "transition-shadow hover:shadow-md" : ""}`}>
      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${TONES[tone]}`}>
        <Icon name={icon} size={22} />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium text-ink-mute">{label}</p>
        {value === null ? <Skeleton className="mt-1 h-7 w-16" /> : <p className="text-2xl font-semibold tracking-tight text-ink">{value}</p>}
      </div>
    </Card>
  );
  return to ? <Link to={to} className="block rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest-700">{body}</Link> : body;
}
