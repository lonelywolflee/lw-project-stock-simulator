# 다단계 매도 시그널 설계

## 개요

기존 단일 구간 매도(`m_fall_days`일 연속 하락 → 전량 매도)를 2단계 매도로 확장한다.

## 매도 흐름

```
종목 연속 하락 시작
  │
  ├─ 1차 기간(m_fall_days_1) 도달
  │   ├─ 보유 평가액 > max_buy_amount × sell_ratio_1 → 보유 수량의 sell_ratio_1% 매도 (반올림)
  │   └─ 보유 평가액 ≤ max_buy_amount × sell_ratio_1 → 1차 스킵 (실행 완료로 간주)
  │
  ├─ 2차 기간(m_fall_days_2) 도달 (1차 포함 연속) → 남은 수량 전량 매도
  │
  └─ 중간에 상승 발생 → 연속 하락 카운트 리셋, 1차/2차 상태 초기화

* 긴급 손절(y_emergency_pct)은 어느 단계에서든 최우선 발동 → 전량 매도
```

## 파라미터 변경

| 파라미터 | 기존 | 변경 후 | 설명 |
|----------|------|---------|------|
| `m_fall_days` | 연속 하락 일수 | **삭제** | 1차/2차로 대체 |
| `m_fall_days_1` | — | **신규** | 1차 매도 연속 하락 일수 |
| `m_fall_days_2` | — | **신규** | 2차 매도 연속 하락 일수 (1차 포함, `m_fall_days_2 > m_fall_days_1`) |
| `sell_ratio_1` | — | **신규** | 1차 매도 비율 (10~90%, 1% 단위) |

## 시그널 계산

`signals.py`의 `detect_consecutive_falls`는 그대로 재활용. `_precompute_signals`에서 1차/2차 두 개의 시그널을 각각 계산:

```python
"sell_fall_1": detect_consecutive_falls(close, m_fall_days_1)
"sell_fall_2": detect_consecutive_falls(close, m_fall_days_2)
```

## SELL 단계 로직

1차 매도 상태를 추적하기 위해 `phase1_sold: set[str]`을 일별 루프 외부에 유지:

```
매일 SELL Phase:
  for 보유 종목:
    긴급 손절 시그널? → 전량 매도, phase1_sold에서 제거
    2차 시그널(m_fall_days_2)? → 전량 매도, phase1_sold에서 제거
    1차 시그널(m_fall_days_1) AND code not in phase1_sold?
      → 보유 평가액 > threshold? → sell_ratio_1% 매도, phase1_sold에 추가
      → 보유 평가액 ≤ threshold? → 매도 스킵, phase1_sold에 추가
```

연속 하락이 끊기면(1차 시그널이 False로 전환) `phase1_sold`에서 제거하여 리셋.

## Portfolio 변경

`sell_all` 외에 부분 매도 메서드 추가:

```python
def sell_partial(self, date, code, name, price, ratio) -> bool:
    """보유 수량의 ratio%를 매도한다 (반올림)."""
```

## 소액 스킵 조건

1차 매도 시점에 해당 종목의 보유 평가액이 `max_buy_amount × sell_ratio_1` 이하이면 1차 매도를 건너뛰고 실행 완료로 간주한다. 2차 매도에는 적용하지 않으며, 무조건 전량 매도한다.

## 영향 범위

| 레이어 | 파일 | 변경 내용 |
|--------|------|-----------|
| Engine | `backtest.py` | `BacktestParams` 필드 변경, SELL 로직 2단계화, `phase1_sold` 추적 |
| Engine | `portfolio.py` | `sell_partial()` 메서드 추가 |
| Engine | `signals.py` | 변경 없음 (기존 함수 재활용) |
| API | `schemas.py` | 요청 스키마 필드 변경 (`m_fall_days` → 3개 파라미터) |
| API | `serializers.py` | 변경 없음 (출력 구조 동일) |
| Frontend | `types.ts` | `BacktestParams` 타입 필드 변경 |
| Frontend | `BacktestForm.tsx` | 기존 "연속 하락일" 입력을 1차/2차/비율 3개 입력으로 교체 |
| Docs | `05-algorithm.md` | 매도 알고리즘 명세 갱신 |
| Tests | 기존 테스트 | 파라미터 변경에 따른 수정 + 다단계 매도 테스트 추가 |
