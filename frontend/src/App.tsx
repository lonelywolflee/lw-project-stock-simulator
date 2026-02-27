import { Outlet, useNavigate } from "react-router-dom";
import { ActivityIcon, LogOut, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/authStore";

function App() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* 헤더 */}
      <header className="sticky top-0 z-40 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="flex h-14 items-center gap-3 px-5">
          <div className="flex items-center gap-2.5">
            <div className="flex size-7 items-center justify-center rounded-md border border-border bg-card">
              <ActivityIcon className="size-3.5 text-mint" />
            </div>
            <h1 className="font-display text-sm font-bold tracking-tight">
              Stock Simulator
            </h1>
          </div>

          <div className="flex items-center gap-1.5 rounded-full border border-border/50 bg-card px-2.5 py-1">
            <span className="inline-block size-1.5 rounded-full bg-mint pulse-mint" />
            <span className="font-mono-data text-[10px] uppercase tracking-wider text-muted-foreground">
              KOSPI
            </span>
          </div>

          {/* 우측 메뉴 */}
          <div className="ml-auto flex items-center gap-1">
            {user && (
              <span className="mr-2 font-mono-data text-xs text-muted-foreground">
                {user.username}
              </span>
            )}
            {user?.is_staff && (
              <Button
                variant="ghost"
                size="sm"
                asChild
                className="gap-1.5 text-xs text-muted-foreground hover:text-mint"
              >
                <a href="/admin/">
                  <Settings className="size-3.5" />
                  관리자
                </a>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="gap-1.5 text-xs text-muted-foreground hover:text-destructive"
            >
              <LogOut className="size-3.5" />
              로그아웃
            </Button>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <div className="px-5 py-5">
        <Outlet />
      </div>
    </div>
  );
}

export default App;
