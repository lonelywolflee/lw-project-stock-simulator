import { Outlet, useNavigate } from "react-router-dom";
import { LineChartIcon, LogOut, Settings } from "lucide-react";
import { Separator } from "@/components/ui/separator";
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
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-6">
          <LineChartIcon className="size-5 text-primary" />
          <h1 className="text-base font-bold tracking-tight">
            Stock Simulator
          </h1>
          <span className="text-xs text-muted-foreground">
            KOSPI 백테스트
          </span>

          {/* 우측 메뉴 */}
          <div className="ml-auto flex items-center gap-2">
            {user?.is_staff && (
              <Button variant="ghost" size="sm" asChild>
                <a href="/admin/">
                  <Settings className="size-4" />
                  관리자
                </a>
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="size-4" />
              로그아웃
            </Button>
          </div>
        </div>
      </header>

      <Separator />

      {/* 메인 콘텐츠 */}
      <div className="mx-auto max-w-7xl px-6 py-6">
        <Outlet />
      </div>
    </div>
  );
}

export default App;
