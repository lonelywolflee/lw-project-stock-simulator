# 로그인 + Vite Proxy + Admin 접근 설계

## 아키텍처

```
Browser → Vite(:5173)
  ├── /login       → React 로그인 페이지
  ├── /            → BacktestDashboard (인증 필요)
  ├── /admin/*     → proxy → Django(:8000) Unfold Admin
  ├── /api/*       → proxy → Django(:8000) API
  └── /static/*    → proxy → Django(:8000) static files
```

Production에서는 Nginx/Caddy가 Vite dev server 역할을 대체한다.

## 인증 방식

- 세션 기반 (Django 기본 세션)
- Django admin과 세션 공유 → 한 번 로그인으로 admin까지 접근
- 회원가입 페이지 없음 — Admin에서 사용자 관리
- 초기 관리자는 `createsuperuser`로 생성

## Backend 변경

### 인증 API (`apps/accounts/api.py`)

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/auth/login` | POST | username/password → 세션 생성 |
| `/api/auth/logout` | POST | 세션 파기 |
| `/api/auth/me` | GET | 현재 사용자 정보 (비인증 시 401) |

### URL 등록 (`config/urls.py`)

`api.add_router("/auth", auth_router)`

### CSRF 처리

django-ninja는 API에 CSRF 면제 기본 적용. 세션 쿠키로 인증.

## Frontend 변경

### 라우팅 (React Router)

- `/login` → LoginPage
- `/` → BacktestDashboard (ProtectedRoute)
- 미인증 시 `/login` 리다이렉트

### 인증 상태 (Zustand)

`stores/authStore.ts` — user, isAuthenticated, login(), logout(), checkAuth()

### 로그인 페이지

shadcn/ui Card + Input + Button. 에러 메시지 표시.

### Vite proxy 추가

`/admin`, `/static` → `:8000` 프록시 추가.

### 네비게이션

헤더에 로그아웃 버튼 + Admin 링크.

## 파일 목록

| 위치 | 파일 | 작업 |
|------|------|------|
| Backend | `apps/accounts/__init__.py` | 새 앱 |
| Backend | `apps/accounts/api.py` | 인증 API 라우터 |
| Backend | `config/urls.py` | auth 라우터 등록 |
| Frontend | `vite.config.ts` | proxy 추가 |
| Frontend | `package.json` | react-router-dom 추가 |
| Frontend | `src/stores/authStore.ts` | 인증 상태 |
| Frontend | `src/api/auth.ts` | 인증 API 호출 |
| Frontend | `src/pages/LoginPage.tsx` | 로그인 페이지 |
| Frontend | `src/components/ProtectedRoute.tsx` | 인증 가드 |
| Frontend | `src/App.tsx` | 라우터 적용 |
