# 로그인 + Vite Proxy + Admin 접근 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 세션 기반 로그인으로 모든 페이지를 보호하고, Vite proxy를 통해 Django Admin(Unfold)에 접근할 수 있게 한다.

**Architecture:** Backend에 django-ninja auth 라우터 추가 (login/logout/me). Frontend에 React Router + Zustand 인증 상태 + 로그인 페이지 추가. Vite proxy로 /admin, /static을 Django로 프록시.

**Tech Stack:** Django 5.1 + django-ninja, React 19 + React Router + Zustand + shadcn/ui, Vite proxy

---

### Task 1: Backend — accounts 앱 + 인증 API

**Files:**
- Create: `backend/apps/accounts/__init__.py`
- Create: `backend/apps/accounts/api.py`
- Modify: `backend/config/urls.py`

**Step 1: accounts 앱 생성**

```bash
mkdir -p backend/apps/accounts
touch backend/apps/accounts/__init__.py
```

**Step 2: 인증 API 라우터 작성**

Create `backend/apps/accounts/api.py`:

```python
"""인증 API — 세션 기반 로그인/로그아웃."""

from django.contrib.auth import authenticate, login, logout
from ninja import Router, Schema

router = Router()


class LoginSchema(Schema):
    username: str
    password: str


class UserSchema(Schema):
    id: int
    username: str
    is_staff: bool


class ErrorSchema(Schema):
    detail: str


@router.post("/login", response={200: UserSchema, 401: ErrorSchema})
def login_view(request, payload: LoginSchema):
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is None:
        return 401, {"detail": "아이디 또는 비밀번호가 올바르지 않습니다."}
    login(request, user)
    return {"id": user.id, "username": user.username, "is_staff": user.is_staff}


@router.post("/logout", response={200: dict})
def logout_view(request):
    logout(request)
    return {"detail": "ok"}


@router.get("/me", response={200: UserSchema, 401: ErrorSchema})
def me(request):
    if not request.user.is_authenticated:
        return 401, {"detail": "인증되지 않았습니다."}
    user = request.user
    return {"id": user.id, "username": user.username, "is_staff": user.is_staff}
```

**Step 3: URL에 auth 라우터 등록**

Modify `backend/config/urls.py` — import 추가 및 라우터 등록:

```python
"""URL 설정."""

from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from apps.accounts.api import router as auth_router
from apps.backtests.api import router as backtests_router
from apps.market_data.api import router as market_data_router

api = NinjaAPI(
    title="Stock Simulator API",
    version="1.0.0",
    description="KOSPI 백테스트 시뮬레이터 API",
)

api.add_router("/auth", auth_router)
api.add_router("/backtests", backtests_router)
api.add_router("/market-data", market_data_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
```

**Step 4: 서버 체크**

Run: `cd backend && source .venv/bin/activate && python manage.py check`
Expected: `System check identified no issues`

**Step 5: 수동 테스트 — login API**

Run: `cd backend && source .venv/bin/activate && python manage.py runserver &`

```bash
# login 테스트
curl -s -c /tmp/cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# me 테스트 (세션 쿠키 사용)
curl -s -b /tmp/cookies.txt http://localhost:8000/api/auth/me

# logout 테스트
curl -s -b /tmp/cookies.txt -X POST http://localhost:8000/api/auth/logout
```

Expected: login → `{"id":1,"username":"admin","is_staff":true}`, me → 같은 응답, logout → `{"detail":"ok"}`

**Step 6: 커밋**

```bash
git add backend/apps/accounts/ backend/config/urls.py
git commit -m "feat: 세션 기반 인증 API 추가 (login/logout/me)"
```

---

### Task 2: Frontend — Vite proxy 추가

**Files:**
- Modify: `frontend/vite.config.ts`

**Step 1: /admin, /static 프록시 추가**

`frontend/vite.config.ts`의 `server.proxy`에 추가:

```typescript
server: {
  proxy: {
    "/api": {
      target: "http://localhost:8000",
      changeOrigin: true,
    },
    "/admin": {
      target: "http://localhost:8000",
      changeOrigin: true,
    },
    "/static": {
      target: "http://localhost:8000",
      changeOrigin: true,
    },
  },
},
```

**Step 2: 커밋**

```bash
git add frontend/vite.config.ts
git commit -m "feat: Vite proxy에 /admin, /static 경로 추가"
```

---

### Task 3: Frontend — react-router-dom 설치

**Files:**
- Modify: `frontend/package.json` (via npm/pnpm install)

**Step 1: 패키지 설치**

```bash
cd frontend && npm install react-router-dom
```

**Step 2: 커밋**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat: react-router-dom 의존성 추가"
```

---

### Task 4: Frontend — 인증 API 클라이언트

**Files:**
- Create: `frontend/src/api/auth.ts`

**Step 1: auth API 함수 작성**

Create `frontend/src/api/auth.ts`:

```typescript
import axios from "axios";

const api = axios.create({
  baseURL: "/api/auth",
  headers: { "Content-Type": "application/json" },
});

export interface User {
  id: number;
  username: string;
  is_staff: boolean;
}

export async function loginApi(
  username: string,
  password: string,
): Promise<User> {
  const { data } = await api.post<User>("/login", { username, password });
  return data;
}

export async function logoutApi(): Promise<void> {
  await api.post("/logout");
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>("/me");
  return data;
}
```

**Step 2: 커밋**

```bash
git add frontend/src/api/auth.ts
git commit -m "feat: 인증 API 클라이언트 함수 추가"
```

---

### Task 5: Frontend — Zustand 인증 스토어

**Files:**
- Create: `frontend/src/stores/authStore.ts`

**Step 1: authStore 작성**

Create `frontend/src/stores/authStore.ts`:

```typescript
import { create } from "zustand";
import { fetchMe, loginApi, logoutApi, type User } from "@/api/auth";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  login: async (username, password) => {
    set({ error: null });
    try {
      const user = await loginApi(username, password);
      set({ user, isAuthenticated: true, error: null });
    } catch {
      set({ error: "아이디 또는 비밀번호가 올바르지 않습니다." });
      throw new Error("login failed");
    }
  },

  logout: async () => {
    await logoutApi();
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const user = await fetchMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
```

**Step 2: 커밋**

```bash
git add frontend/src/stores/authStore.ts
git commit -m "feat: Zustand 인증 상태 스토어 추가"
```

---

### Task 6: Frontend — 로그인 페이지

**Files:**
- Create: `frontend/src/pages/LoginPage.tsx`

**Step 1: LoginPage 작성**

Create `frontend/src/pages/LoginPage.tsx`:

```tsx
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { LineChartIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex items-center gap-2">
            <LineChartIcon className="size-5 text-primary" />
            <CardTitle className="text-lg">Stock Simulator</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="flex flex-col gap-2">
              <Label htmlFor="username">사용자명</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">비밀번호</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "로그인 중..." : "로그인"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 2: 커밋**

```bash
git add frontend/src/pages/LoginPage.tsx
git commit -m "feat: 로그인 페이지 UI 추가"
```

---

### Task 7: Frontend — ProtectedRoute + Router 적용

**Files:**
- Create: `frontend/src/components/ProtectedRoute.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

**Step 1: ProtectedRoute 컴포넌트 작성**

Create `frontend/src/components/ProtectedRoute.tsx`:

```tsx
import { useEffect } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">로딩 중...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
```

**Step 2: App.tsx를 레이아웃 컴포넌트로 변경**

헤더에 로그아웃 버튼 + Admin 링크 추가. 기존 `<BacktestDashboard />`를 `<Outlet />`으로 교체.

Modify `frontend/src/App.tsx`:

```tsx
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
```

**Step 3: main.tsx에 라우터 설정**

Modify `frontend/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import App from "./App";
import { LoginPage } from "@/pages/LoginPage";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { BacktestDashboard } from "@/features/backtest/BacktestDashboard";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<App />}>
              <Route index element={<BacktestDashboard />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
```

**Step 4: TypeScript 빌드 확인**

Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음

**Step 5: 커밋**

```bash
git add frontend/src/components/ProtectedRoute.tsx frontend/src/App.tsx frontend/src/main.tsx
git commit -m "feat: React Router + ProtectedRoute + 헤더 네비게이션 추가"
```

---

### Task 8: 통합 테스트

**Step 1: Backend 서버 실행**

```bash
cd backend && source .venv/bin/activate && python manage.py runserver
```

**Step 2: Frontend dev 서버 실행**

```bash
cd frontend && npm run dev
```

**Step 3: 수동 확인 체크리스트**

1. `http://localhost:5173/` → `/login`으로 리다이렉트되는지
2. 잘못된 비밀번호 → 에러 메시지 표시되는지
3. `admin` / `admin`으로 로그인 → BacktestDashboard 표시되는지
4. 헤더에 "관리자" 버튼 표시되는지 (is_staff=true)
5. "관리자" 클릭 → `/admin/` Unfold 페이지 표시되는지 (재로그인 없이)
6. "로그아웃" 클릭 → `/login`으로 이동하는지
7. 로그아웃 후 `/` 직접 접근 → `/login`으로 리다이렉트되는지
