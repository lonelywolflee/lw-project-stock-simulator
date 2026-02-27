import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ActivityIcon, ArrowRightIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useAuthStore } from "@/stores/authStore";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { error, login } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch {
      // error는 store에서 관리
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      {/* 배경 그라데이션 오브 */}
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(0,212,170,0.08)_0%,transparent_70%)]" />
      <div className="pointer-events-none absolute -bottom-20 -right-20 h-[400px] w-[400px] rounded-full bg-[radial-gradient(circle,rgba(91,127,255,0.06)_0%,transparent_70%)]" />

      <div className="relative w-full max-w-[380px]">
        {/* 로고 영역 */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center gap-2.5">
            <div className="flex size-10 items-center justify-center rounded-lg border border-border bg-card glow-mint-sm">
              <ActivityIcon className="size-5 text-mint" />
            </div>
            <span className="font-display text-2xl font-bold tracking-tight text-foreground">
              Stock Simulator
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            KOSPI 알고리즘 백테스트 시뮬레이터
          </p>
        </div>

        {/* 로그인 카드 */}
        <div className="glass-card rounded-xl p-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            {error && (
              <Alert variant="destructive" className="border-destructive/30 bg-destructive/10">
                <AlertDescription className="text-sm">{error}</AlertDescription>
              </Alert>
            )}

            <div className="flex flex-col gap-2">
              <Label htmlFor="username" className="text-xs uppercase tracking-wider text-muted-foreground">
                Username
              </Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="h-11 border-border/60 bg-background/50 font-mono-data text-sm placeholder:text-muted-foreground/40 focus:border-mint focus:ring-mint/20"
                placeholder="admin"
                autoFocus
                required
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="password" className="text-xs uppercase tracking-wider text-muted-foreground">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-11 border-border/60 bg-background/50 font-mono-data text-sm placeholder:text-muted-foreground/40 focus:border-mint focus:ring-mint/20"
                placeholder="********"
                required
              />
            </div>

            <Button
              type="submit"
              disabled={submitting}
              className="mt-1 h-11 gap-2 bg-mint text-[#06060b] font-semibold hover:bg-mint/90 glow-mint-sm"
            >
              {submitting ? (
                <span className="font-mono-data text-sm">인증 중...</span>
              ) : (
                <>
                  로그인
                  <ArrowRightIcon className="size-4" />
                </>
              )}
            </Button>
          </form>
        </div>

        {/* 하단 상태 */}
        <div className="mt-6 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <span className="inline-block size-1.5 rounded-full bg-mint pulse-mint" />
          시스템 정상 운영 중
        </div>
      </div>
    </div>
  );
}
