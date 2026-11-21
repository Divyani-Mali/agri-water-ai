import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import Card, { CardHeader } from "../ui/Card";
import { SOIL_RANGE, irrigationTrigger } from "../../constants";
import { useTranslate } from "../../context/authContext";

const AXIS = { fontSize: 11, fill: "#7d877f" };
const TOOLTIP = { borderRadius: 8, border: "1px solid #dde1d6", fontSize: 12 };

function ChartCard({ title, subtitle, hasData, children }) {
  const t = useTranslate();
  return (
    <Card>
      <CardHeader title={title} subtitle={subtitle} />
      <div className="h-72 p-4">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            {children}
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-ink-mute">
            {t("No readings to chart yet.")}
          </div>
        )}
      </div>
    </Card>
  );
}

// data: oldest -> newest, each item has { label, soil_moisture, temperature, humidity }
export default function ReadingCharts({ data, soil }) {
  const t = useTranslate();
  const range = SOIL_RANGE[soil] || SOIL_RANGE.loamy;
  const trigger = irrigationTrigger(soil);
  const hasData = data.length > 0;

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <ChartCard title="Soil moisture" subtitle={t("Last {count} readings · % volumetric", { count: data.length })} hasData={hasData}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: -12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e8ebe3" />
          <XAxis dataKey="label" tick={AXIS} minTickGap={48} tickLine={false} />
          <YAxis
            tick={AXIS}
            tickLine={false}
            domain={[Math.floor(range.wp - 2), Math.ceil(range.fc + 2)]}
            unit="%"
          />
          <Tooltip contentStyle={TOOLTIP} formatter={(v) => [`${v}%`, t("Soil moisture")]} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <ReferenceLine
            y={trigger}
            stroke="#dc2626"
            strokeDasharray="5 4"
            label={{ value: `${t("Irrigation trigger")} ${trigger}%`, position: "insideBottomRight", fontSize: 11, fill: "#dc2626" }}
          />
          <Line type="monotone" dataKey="soil_moisture" name={`${t("Soil moisture")} (%)`} stroke="#336544" strokeWidth={2.2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ChartCard>

      <ChartCard title="Temperature and humidity" subtitle="Same period as soil moisture" hasData={hasData}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: -12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e8ebe3" />
          <XAxis dataKey="label" tick={AXIS} minTickGap={48} tickLine={false} />
          <YAxis tick={AXIS} tickLine={false} />
          <Tooltip contentStyle={TOOLTIP} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="temperature" name={`${t("Temperature")} (°C)`} stroke="#c2410c" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="humidity" name={`${t("Humidity")} (%)`} stroke="#0369a1" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ChartCard>
    </div>
  );
}
