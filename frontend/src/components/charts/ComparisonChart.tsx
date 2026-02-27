import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BacktestResult } from "@/api/types";
import { formatDate } from "@/utils/formatters";
import { CHART_COLORS } from "@/utils/colors";

interface ComparisonChartProps {
  result: BacktestResult;
}

function normalizeToBase100(values: number[]): number[] {
  if (values.length === 0) return [];
  const base = values[0];
  if (base === 0) return values.map(() => 100);
  return values.map((v) => (v / base) * 100);
}

export function ComparisonChart({ result }: ComparisonChartProps) {
  const { daily_snapshots, kospi_index } = result;
  if (daily_snapshots.length === 0) return null;

  // 포트폴리오 정규화 (Base=100)
  const portfolioBase = daily_snapshots[0].total_value;
  const portfolioNorm = daily_snapshots.map(
    (s) => (s.total_value / portfolioBase) * 100,
  );

  // 날짜 기반 데이터 조합
  const dateMap = new Map<
    string,
    { portfolio: number; kospi?: number }
  >();

  daily_snapshots.forEach((s, i) => {
    const date = formatDate(s.date);
    dateMap.set(date, { portfolio: portfolioNorm[i] });
  });

  if (kospi_index && kospi_index.dates.length === kospi_index.values.length) {
    const kospiNorm = normalizeToBase100(kospi_index.values);
    kospi_index.dates.forEach((d, i) => {
      const date = formatDate(d);
      const entry = dateMap.get(date);
      if (entry && kospiNorm[i] !== undefined) entry.kospi = kospiNorm[i];
    });
  }

  const data = Array.from(dateMap.entries()).map(([date, vals]) => ({
    date,
    포트폴리오: Number(vals.portfolio.toFixed(2)),
    ...(vals.kospi !== undefined && {
      KOSPI: Number(vals.kospi.toFixed(2)),
    }),
  }));

  return (
    <div className="rounded-lg border border-border/60 bg-card p-4">
      <h3 className="mb-4 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        벤치마크 비교 <span className="text-muted-foreground/50">(Base=100)</span>
      </h3>
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={data}>
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
            width={50}
            domain={["auto", "auto"]}
          />
          <Tooltip
            contentStyle={{
              borderRadius: "0.375rem",
              border: "1px solid #2c2c42",
              background: "#101018",
              fontSize: "12px",
              fontFamily: "JetBrains Mono, monospace",
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="포트폴리오"
            stroke={CHART_COLORS.portfolio}
            strokeWidth={2}
            dot={false}
          />
          {kospi_index && (
            <Line
              type="monotone"
              dataKey="KOSPI"
              stroke={CHART_COLORS.kospi}
              strokeWidth={1.5}
              strokeDasharray="5 5"
              dot={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
