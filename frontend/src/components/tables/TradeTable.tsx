import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { Trade } from "@/api/types";
import { formatCurrency, formatDate, formatNumber } from "@/utils/formatters";
import { getProfitClass } from "@/utils/colors";

interface TradeTableProps {
  trades: Trade[];
}

export function TradeTable({ trades }: TradeTableProps) {
  if (trades.length === 0) {
    return (
      <p className="py-8 text-center text-muted-foreground">
        거래 내역이 없습니다.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>일자</TableHead>
          <TableHead>시장</TableHead>
          <TableHead>종목</TableHead>
          <TableHead>구분</TableHead>
          <TableHead className="text-right">가격</TableHead>
          <TableHead className="text-right">수량</TableHead>
          <TableHead className="text-right">금액</TableHead>
          <TableHead className="text-right">수수료</TableHead>
          <TableHead className="text-right">손익</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {trades.map((t, i) => (
          <TableRow key={`${t.date}-${t.code}-${t.side}-${i}`}>
            <TableCell className="tabular-nums">
              {formatDate(t.date)}
            </TableCell>
            <TableCell>
              <Badge variant="outline" className="text-xs">
                {t.market}
              </Badge>
            </TableCell>
            <TableCell>
              <span className="font-medium">{t.name}</span>
              <span className="ml-1 text-xs text-muted-foreground">
                {t.code}
              </span>
            </TableCell>
            <TableCell>
              <Badge
                variant={t.side === "BUY" ? "default" : "destructive"}
                className="text-xs"
              >
                {t.side === "BUY" ? "매수" : "매도"}
              </Badge>
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatCurrency(t.price, t.market)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatNumber(t.quantity)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatCurrency(t.amount, t.market)}
            </TableCell>
            <TableCell className="text-right tabular-nums text-muted-foreground">
              {formatCurrency(t.fee, t.market)}
            </TableCell>
            <TableCell
              className={`text-right tabular-nums font-medium ${getProfitClass(t.profit)}`}
            >
              {t.side === "SELL"
                ? formatCurrency(t.profit, t.market)
                : "-"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
