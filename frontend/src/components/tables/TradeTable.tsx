import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Trade } from "@/api/types";
import { formatKRW, formatDate, formatNumber } from "@/utils/formatters";
import { getProfitClass } from "@/utils/colors";

interface TradeTableProps {
  trades: Trade[];
}

export function TradeTable({ trades }: TradeTableProps) {
  if (trades.length === 0) {
    return (
      <p className="py-8 text-center font-mono-data text-sm text-muted-foreground">
        거래 내역이 없습니다.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="border-border/50 hover:bg-transparent">
          <TableHead className="font-mono-data text-[10px] uppercase tracking-wider">일자</TableHead>
          <TableHead className="font-mono-data text-[10px] uppercase tracking-wider">종목</TableHead>
          <TableHead className="font-mono-data text-[10px] uppercase tracking-wider">구분</TableHead>
          <TableHead className="text-right font-mono-data text-[10px] uppercase tracking-wider">가격</TableHead>
          <TableHead className="text-right font-mono-data text-[10px] uppercase tracking-wider">수량</TableHead>
          <TableHead className="text-right font-mono-data text-[10px] uppercase tracking-wider">금액</TableHead>
          <TableHead className="text-right font-mono-data text-[10px] uppercase tracking-wider">수수료</TableHead>
          <TableHead className="text-right font-mono-data text-[10px] uppercase tracking-wider">손익</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {trades.map((t, i) => (
          <TableRow
            key={`${t.date}-${t.code}-${t.side}-${i}`}
            className="table-row-hover border-border/30"
          >
            <TableCell className="font-mono-data text-xs text-muted-foreground">
              {formatDate(t.date)}
            </TableCell>
            <TableCell>
              <span className="text-sm font-medium">{t.name}</span>
              <span className="ml-1.5 font-mono-data text-[10px] text-muted-foreground/60">
                {t.code}
              </span>
            </TableCell>
            <TableCell>
              <span
                className={`inline-flex items-center rounded px-1.5 py-0.5 font-mono-data text-[10px] font-semibold uppercase ${
                  t.side === "BUY"
                    ? "bg-mint/10 text-mint"
                    : "bg-destructive/10 text-destructive"
                }`}
              >
                {t.side === "BUY" ? "BUY" : "SELL"}
              </span>
            </TableCell>
            <TableCell className="text-right font-mono-data text-xs">
              {formatKRW(t.price)}
            </TableCell>
            <TableCell className="text-right font-mono-data text-xs">
              {formatNumber(t.quantity)}
            </TableCell>
            <TableCell className="text-right font-mono-data text-xs">
              {formatKRW(t.amount)}
            </TableCell>
            <TableCell className="text-right font-mono-data text-xs text-muted-foreground/60">
              {formatKRW(t.fee)}
            </TableCell>
            <TableCell
              className={`text-right font-mono-data text-xs font-medium ${getProfitClass(t.profit)}`}
            >
              {t.side === "SELL"
                ? formatKRW(t.profit)
                : "-"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
