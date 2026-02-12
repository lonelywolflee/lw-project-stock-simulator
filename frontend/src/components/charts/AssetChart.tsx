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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <div className="rounded-lg border bg-card p-3 shadow-md">
      <p className="mb-1 text-xs font-medium">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="text-xs" style={{ color: entry.color }}>
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
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">자산 추이</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={360}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickLine={false}
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
      </CardContent>
    </Card>
  );
}
