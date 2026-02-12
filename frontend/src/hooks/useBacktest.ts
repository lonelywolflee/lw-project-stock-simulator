import { useMutation } from "@tanstack/react-query";
import { runBacktest } from "@/api/client";
import type { BacktestParams } from "@/api/types";

export function useRunBacktest() {
  return useMutation({
    mutationFn: (params: BacktestParams) => runBacktest(params),
  });
}
