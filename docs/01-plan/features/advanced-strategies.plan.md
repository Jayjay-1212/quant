# Plan: 고급 트레이딩 전략 확장

## 1. 개요

| 항목 | 내용 |
|------|------|
| Feature | advanced-strategies |
| 작성일 | 2026-03-06 |
| 상태 | Plan |
| 우선순위 | 1 |

### 1.1 목적
볼린저밴드, RSI, MACD 기반 전략을 추가하여 다양한 시장 상황에 대응 가능한 전략 라이브러리를 구축한다.

## 2. 기능 요구사항

### FR-01: 볼린저밴드 전략 (bollinger_band.py)
- 주가가 하단 밴드 이탈 시 매수 (과매도)
- 주가가 상단 밴드 이탈 시 매도 (과매수)
- 파라미터: period(20), devfactor(2.0)

### FR-02: RSI 전략 (rsi.py)
- RSI가 과매도 구간(30 이하) 진입 후 반등 시 매수
- RSI가 과매수 구간(70 이상) 진입 후 하락 시 매도
- 파라미터: period(14), oversold(30), overbought(70)

### FR-03: MACD 전략 (macd.py)
- MACD 라인이 시그널 라인을 상향 돌파 시 매수
- MACD 라인이 시그널 라인을 하향 돌파 시 매도
- 파라미터: fast(12), slow(26), signal(9)

## 3. 구현 파일

| 파일 | 전략 | 유형 |
|------|------|------|
| strategies/bollinger_band.py | BollingerBand | 평균 회귀 |
| strategies/rsi.py | RsiStrategy | 모멘텀 반전 |
| strategies/macd.py | MacdStrategy | 추세 추종 |
