# CLAUDE.md

이 저장소의 Claude Code 진입점. 실제 내용은 `docs/`에 분리되어 있다.

## 문서 구조

| 문서 | 내용 |
|------|------|
| [`docs/architecture.md`](docs/architecture.md) | 아키텍처, 기술 스택, 프로젝트 구조, 주요 파일, 모듈 API |
| [`docs/development.md`](docs/development.md) | 환경 설정, 실행 방법, 명령어 레퍼런스, 의존성 관리 |
| [`docs/conventions.md`](docs/conventions.md) | 코딩 규칙, Import 규칙, UI 컨벤션, 주의사항(Gotchas) |
| [`docs/testing.md`](docs/testing.md) | 테스트 전략, 실행 방법, 테스트 데이터 헬퍼 |
| [`docs/algorithm.md`](docs/algorithm.md) | 매매 알고리즘 상세 명세 (입력/출력, 이중 시장 모델) |
| [`docs/prd-v0.1.0.md`](docs/prd-v0.1.0.md) | v0.1.0 원본 기획서 (역사적 기록, 수정 금지) |

## 문서 관리 규칙

1. **CLAUDE.md는 목차만 포함한다** — 코드 블록, 명령어, 기술 설명을 직접 넣지 않는다
2. **새 문서 추가** → `docs/`에 생성 후 위 테이블에 링크 추가
3. **기존 문서 수정** → `docs/` 파일을 직접 수정, CLAUDE.md는 링크만 갱신
4. **CLAUDE.md 100줄 초과 금지** — 초과 시 `docs/`로 분리

## README 작성 규칙

1. Root README: 프로젝트 소개 + 기능 요약 + docs/ 링크. Quick Start 코드블록 금지
2. `backend/` · `frontend/` README: 해당 서비스의 빌드/실행/배포 단계만 포함
3. README 간 내용 중복 금지 — 공통 정보는 `docs/` 링크로 대체

## 커밋 규칙

커밋 타입: `docs:`, `feat:`, `refactor:`, `fix:` (한국어 메시지). `/commit` 커맨드 사용 시 자동으로 목적별 분리 커밋.
