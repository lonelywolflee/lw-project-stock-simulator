# 개발 환경 및 명령어

## 사전 요구사항

- Python >= 3.12
- Node.js >= 20
- [uv](https://docs.astral.sh/uv/) (Python 패키지 매니저)
- npm (Node.js 패키지 매니저)

## 환경 설정

```bash
# 1. Backend 환경 변수
cp backend/.env.example backend/.env  # 필요 시 값 수정

# 2. Backend 의존성 설치
cd backend && uv sync

# 3. Frontend 의존성 설치
cd frontend && npm install
```

- `DJANGO_SECRET_KEY`: 미설정 시 DEBUG 모드에서만 dev 키 사용, production에서는 필수
- 외부 인프라 불필요 (Redis, PostgreSQL 등 없음)

## 실행

### 로컬 개발 (터미널 2개)

```bash
# Backend (:8000)
cd backend && uv run python manage.py runserver

# Frontend (:5173)
cd frontend && npm run dev
```

### Docker

```bash
docker compose up  # backend + frontend 2개 서비스
```

## 명령어 레퍼런스

### Backend

```bash
# 전체 테스트
cd backend && uv run pytest tests/ -v

# 단일 파일 테스트
cd backend && uv run pytest tests/test_backtest.py -v

# 특정 테스트 클래스/메서드
cd backend && uv run pytest tests/test_backtest.py::TestDualMarketBacktest::test_dual_market_capital_split -v

# Django 개발 서버
cd backend && uv run python manage.py runserver
```

### Frontend

```bash
# 개발 서버
cd frontend && npm run dev

# 타입 체크
cd frontend && npx tsc --noEmit

# 빌드 체크
cd frontend && npx vite build

# 린트
cd frontend && npm run lint
```

## 의존성 관리

- **Backend**: `backend/pyproject.toml` → `uv sync`로 lock 파일 갱신
- **Frontend**: `frontend/package.json` → `npm install`로 lock 파일 갱신
- **Root `pyproject.toml`**: 메타데이터만 포함, 의존성 관리하지 않음
