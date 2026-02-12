import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { PlayIcon, Loader2Icon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Slider } from "@/components/ui/slider";
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
  m_fall_days: z.coerce.number().int().min(1).max(20),
  y_emergency_pct: z.coerce.number().min(0.1).max(50),
  max_buy_amount: z.coerce.number().min(100_000),
  min_balance: z.coerce.number().min(0),
  sort_method: z.enum(["market_cap", "return_rate"]),
  kospi_ratio: z.number().min(0).max(100),
}).refine((data) => new Date(data.start_date) < new Date(data.end_date), {
  message: "종료일은 시작일보다 이후여야 합니다",
  path: ["end_date"],
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
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      initial_cash: 100_000_000,
      start_date: toDateStr(oneYearAgo),
      end_date: toDateStr(today),
      fee_rate: 0.015,
      n_rise_days: 3,
      m_fall_days: 3,
      y_emergency_pct: 5.0,
      max_buy_amount: 5_000_000,
      min_balance: 1_000_000,
      sort_method: "market_cap",
      kospi_ratio: 50,
    },
  });

  const kospiRatio = watch("kospi_ratio");
  const nasdaqRatio = 100 - kospiRatio;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* 기본 설정 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">기본 설정</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label htmlFor="initial_cash">초기 투자금 (원)</Label>
            <Input
              id="initial_cash"
              type="number"
              step={1_000_000}
              {...register("initial_cash")}
            />
            {errors.initial_cash && (
              <p className="text-xs text-destructive mt-1">
                {errors.initial_cash.message}
              </p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="start_date">시작일</Label>
              <Input
                id="start_date"
                type="date"
                {...register("start_date")}
              />
            </div>
            <div>
              <Label htmlFor="end_date">종료일</Label>
              <Input id="end_date" type="date" {...register("end_date")} />
            </div>
          </div>
          <div>
            <Label htmlFor="fee_rate">수수료율 (%)</Label>
            <Input
              id="fee_rate"
              type="number"
              step={0.001}
              {...register("fee_rate")}
            />
          </div>
        </CardContent>
      </Card>

      {/* 시장 설정 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">시장 비율</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>KOSPI {kospiRatio}%</span>
            <span>NASDAQ {nasdaqRatio}%</span>
          </div>
          <Slider
            value={[kospiRatio]}
            onValueChange={([v]) => setValue("kospi_ratio", v)}
            min={0}
            max={100}
            step={10}
          />
          <p className="text-xs text-muted-foreground">
            {kospiRatio === 100
              ? "KOSPI 단일 시장"
              : kospiRatio === 0
                ? "NASDAQ 단일 시장"
                : "이중 시장 (KOSPI + NASDAQ)"}
          </p>
        </CardContent>
      </Card>

      {/* 전략 설정 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">전략 설정</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label htmlFor="n_rise_days">연속 상승일 (매수 신호)</Label>
            <Input
              id="n_rise_days"
              type="number"
              min={1}
              max={20}
              {...register("n_rise_days")}
            />
          </div>
          <div>
            <Label htmlFor="m_fall_days">연속 하락일 (매도 신호)</Label>
            <Input
              id="m_fall_days"
              type="number"
              min={1}
              max={20}
              {...register("m_fall_days")}
            />
          </div>
          <div>
            <Label htmlFor="y_emergency_pct">긴급 손절 기준 (%)</Label>
            <Input
              id="y_emergency_pct"
              type="number"
              step={0.5}
              {...register("y_emergency_pct")}
            />
          </div>
        </CardContent>
      </Card>

      {/* 자금 설정 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">자금 설정</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label htmlFor="max_buy_amount">종목당 최대 매수액 (원)</Label>
            <Input
              id="max_buy_amount"
              type="number"
              step={100_000}
              {...register("max_buy_amount")}
            />
          </div>
          <div>
            <Label htmlFor="min_balance">최소 잔고 유지 (원)</Label>
            <Input
              id="min_balance"
              type="number"
              step={100_000}
              {...register("min_balance")}
            />
          </div>
          <div>
            <Label>매수 후보 정렬</Label>
            <Select
              defaultValue="market_cap"
              onValueChange={(v) =>
                setValue("sort_method", v as "market_cap" | "return_rate")
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="market_cap">시가총액순</SelectItem>
                <SelectItem value="return_rate">수익률순</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Separator />

      <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
        {isLoading ? (
          <>
            <Loader2Icon className="mr-2 size-4 animate-spin" />
            실행 중...
          </>
        ) : (
          <>
            <PlayIcon className="mr-2 size-4" />
            백테스트 실행
          </>
        )}
      </Button>
    </form>
  );
}
