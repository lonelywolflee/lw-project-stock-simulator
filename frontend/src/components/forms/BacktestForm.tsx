import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { PlayIcon, Loader2Icon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { BacktestParams } from "@/api/types";

const today = new Date();
const oneYearAgo = new Date(today);
oneYearAgo.setFullYear(today.getFullYear() - 1);

const toDateStr = (d: Date) => d.toISOString().split("T")[0];

const schema = z.object({
  initial_cash: z.coerce.number().min(1_000_000, "최소 100만원"),
  start_date: z.string().min(1, "시작일 필수"),
  end_date: z.string().min(1, "종료일 필수"),
  fee_rate: z.coerce.number().min(0).max(1),
  n_rise_days: z.coerce.number().int().min(1).max(20),
  m_fall_days_1: z.coerce.number().int().min(1).max(20),
  m_fall_days_2: z.coerce.number().int().min(2).max(30),
  sell_ratio_1: z.coerce.number().int().min(0).max(90),
  y_emergency_pct: z.coerce.number().min(0.1).max(50),
  max_buy_amount: z.coerce.number().min(100_000),
  min_balance: z.coerce.number().min(0),
  sort_method: z.enum(["market_cap", "return_rate"]),
}).refine((data) => new Date(data.start_date) < new Date(data.end_date), {
  message: "종료일은 시작일보다 이후여야 합니다",
  path: ["end_date"],
}).refine((data) => data.m_fall_days_2 > data.m_fall_days_1, {
  message: "2차 매도 기간은 1차보다 커야 합니다",
  path: ["m_fall_days_2"],
});

type FormValues = z.infer<typeof schema>;

interface BacktestFormProps {
  onSubmit: (params: BacktestParams) => void;
  isLoading: boolean;
}

export function BacktestForm({ onSubmit, isLoading }: BacktestFormProps) {
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      initial_cash: 100_000_000,
      start_date: toDateStr(oneYearAgo),
      end_date: toDateStr(today),
      fee_rate: 0.015,
      n_rise_days: 3,
      m_fall_days_1: 3,
      m_fall_days_2: 5,
      sell_ratio_1: 50,
      y_emergency_pct: 5.0,
      max_buy_amount: 5_000_000,
      min_balance: 1_000_000,
      sort_method: "market_cap",
    },
  });

  const inputClass = "h-9 border-border/60 bg-background/50 font-mono-data text-sm focus:border-mint focus:ring-mint/20";
  const labelClass = "text-[11px] uppercase tracking-wider text-muted-foreground";

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
      {/* 기본 설정 */}
      <div className="rounded-lg border border-border/60 bg-card p-4">
        <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          기본 설정
        </h3>
        <div className="space-y-3">
          <div>
            <Label htmlFor="initial_cash" className={labelClass}>초기 투자금 (원)</Label>
            <Input
              id="initial_cash"
              type="number"
              step={1_000_000}
              className={inputClass}
              {...register("initial_cash")}
            />
            {errors.initial_cash && (
              <p className="mt-1 text-xs text-destructive">
                {errors.initial_cash.message}
              </p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="start_date" className={labelClass}>시작일</Label>
              <Input
                id="start_date"
                type="date"
                className={inputClass}
                {...register("start_date")}
              />
            </div>
            <div>
              <Label htmlFor="end_date" className={labelClass}>종료일</Label>
              <Input
                id="end_date"
                type="date"
                className={inputClass}
                {...register("end_date")}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="fee_rate" className={labelClass}>수수료율 (%)</Label>
            <Input
              id="fee_rate"
              type="number"
              step={0.001}
              className={inputClass}
              {...register("fee_rate")}
            />
          </div>
        </div>
      </div>

      {/* 전략 설정 */}
      <div className="rounded-lg border border-border/60 bg-card p-4">
        <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          전략 설정
        </h3>
        <div className="space-y-3">
          <div>
            <Label htmlFor="n_rise_days" className={labelClass}>연속 상승일 (매수 신호)</Label>
            <Input
              id="n_rise_days"
              type="number"
              min={1}
              max={20}
              className={inputClass}
              {...register("n_rise_days")}
            />
          </div>
          <div>
            <Label htmlFor="m_fall_days_1" className={labelClass}>1차 매도 연속 하락일</Label>
            <Input
              id="m_fall_days_1"
              type="number"
              min={1}
              max={20}
              className={inputClass}
              {...register("m_fall_days_1")}
            />
          </div>
          <div>
            <Label htmlFor="sell_ratio_1" className={labelClass}>1차 매도 비율 (%, 0=비활성)</Label>
            <Input
              id="sell_ratio_1"
              type="number"
              min={0}
              max={90}
              className={inputClass}
              {...register("sell_ratio_1")}
            />
          </div>
          <div>
            <Label htmlFor="m_fall_days_2" className={labelClass}>2차 매도 연속 하락일 (전량)</Label>
            <Input
              id="m_fall_days_2"
              type="number"
              min={2}
              max={30}
              className={inputClass}
              {...register("m_fall_days_2")}
            />
            {errors.m_fall_days_2 && (
              <p className="mt-1 text-xs text-destructive">
                {errors.m_fall_days_2.message}
              </p>
            )}
          </div>
          <div>
            <Label htmlFor="y_emergency_pct" className={labelClass}>긴급 손절 기준 (%)</Label>
            <Input
              id="y_emergency_pct"
              type="number"
              step={0.5}
              className={inputClass}
              {...register("y_emergency_pct")}
            />
          </div>
        </div>
      </div>

      {/* 자금 설정 */}
      <div className="rounded-lg border border-border/60 bg-card p-4">
        <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          자금 설정
        </h3>
        <div className="space-y-3">
          <div>
            <Label htmlFor="max_buy_amount" className={labelClass}>종목당 최대 매수액 (원)</Label>
            <Input
              id="max_buy_amount"
              type="number"
              step={100_000}
              className={inputClass}
              {...register("max_buy_amount")}
            />
          </div>
          <div>
            <Label htmlFor="min_balance" className={labelClass}>최소 잔고 유지 (원)</Label>
            <Input
              id="min_balance"
              type="number"
              step={100_000}
              className={inputClass}
              {...register("min_balance")}
            />
          </div>
          <div>
            <Label className={labelClass}>매수 후보 정렬</Label>
            <Select
              defaultValue="market_cap"
              onValueChange={(v) =>
                setValue("sort_method", v as "market_cap" | "return_rate")
              }
            >
              <SelectTrigger className="h-9 border-border/60 bg-background/50 font-mono-data text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="market_cap">시가총액순</SelectItem>
                <SelectItem value="return_rate">수익률순</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <Button
        type="submit"
        className="w-full gap-2 bg-mint text-[#06060b] font-semibold hover:bg-mint/90 glow-mint-sm"
        size="lg"
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <Loader2Icon className="size-4 animate-spin" />
            <span className="font-mono-data text-sm">실행 중...</span>
          </>
        ) : (
          <>
            <PlayIcon className="size-4" />
            백테스트 실행
          </>
        )}
      </Button>
    </form>
  );
}
