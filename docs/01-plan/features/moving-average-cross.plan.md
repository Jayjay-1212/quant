# Plan: 이동평균 교차(MA Cross) 전략

## 1. 개요

| 항목 | 내용 |
|------|------|
| Feature | moving-average-cross |
| 작성일 | 2026-03-06 |
| 상태 | Plan |
| 대상 파일 | strategies/moving_average_cross.py |

### 1.1 목적
20일 이동평균선과 60일 이동평균선의 교차를 이용한 추세 추종 전략을 구현한다. 골든크로스(상향 돌파) 시 매수, 데드크로스(하향 돌파) 시 매도한다.

## 2. 기능 요구사항

### FR-01: 골든크로스 매수
- 20일 SMA가 60일 SMA를 상향 돌파 시 매수 신호

### FR-02: 데드크로스 매도
- 20일 SMA가 60일 SMA를 하향 돌파 시 매도 신호

### FR-03: 파라미터 커스터마이징
- short_period (기본 20), long_period (기본 60) 조절 가능

### FR-04: backtrader 호환
- bt.Strategy 상속, backtest/engine.py와 연동 가능한 구조
