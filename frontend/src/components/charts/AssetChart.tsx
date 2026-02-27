import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DailySnapshot } from "@/api/types";
import { formatCompact, formatDate, formatKRW } from "@/utils/formatters";
import { CHART_COLORS, CHART_FILL_COLORS } from "@/utils/colors";

interface AssetChartProps {
  snapshots: DailySnapshot[];
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2 shadow-lg">
      <p className="mb-1.5 font-mono-data text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      {payload.map((entry) => (
        <p key={entry.name} className="font-mono-data text-xs" style={{ color: entry.color }}>
          {entry.name}: {formatKRW(entry.value)}
        </p>
      ))}
    </div>
  );
}

export function AssetChart({ snapshots }: AssetChartProps) {
  const data = snapshots.map((s) => ({
    date: formatDate(s.date),
    현금: s.cash,
    주식평가액: s.stock_value,
    총자산: s.total_value,
  }));

  return (
    <div className="rounded-lg border border-border/60 bg-card p-4">
      <h3 className="mb-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        자산 추이
      </h3>
      <ResponsiveContainer width="100%" height={360}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2c2c42" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#8e8ea8" }}
            tickLine={false}
            axisLine={{ stroke: "#2c2c42" }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#8e8ea8" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={formatCompact}
            width={60}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="현금"
            stackId="1"
            stroke={CHART_COLORS.cash}
            fill={CHART_FILL_COLORS.cash}
            strokeWidth={1.5}
          />
          <Area
            type="monotone"
            dataKey="주식평가액"
            stackId="1"
            stroke={CHART_COLORS.stockValue}
            fill={CHART_FILL_COLORS.stockValue}
            strokeWidth={1.5}
          />
          <Line
            type="monotone"
            dataKey="총자산"
            stroke={CHART_COLORS.totalValue}
            strokeWidth={2}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
