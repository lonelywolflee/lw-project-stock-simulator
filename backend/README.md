# Backend

Django 5.x + django-ninja 기반 REST API. 백테스트 엔진과 데이터 수집 모듈을 포함한다.

## 사전 요구사항

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)

## 빌드

```bash
cp .env.example .env  # 필요 시 값 수정
uv sync
```

## 실행

```bash
uv run python manage.py runserver  # :8000
```

## 테스트

```bash
uv run pytest tests/ -v
```

## 배포

TBD

## 상세 문서

- [아키텍처](../docs/architecture.md)
- [개발 가이드](../docs/development.md)
- [매매 알고리즘](../docs/algorithm.md)
