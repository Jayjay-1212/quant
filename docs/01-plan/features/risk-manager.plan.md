# Plan: 리스크 매니저 (Kelly + Risk Parity)

## 1. 개요

| 항목 | 내용 |
|------|------|
| Feature | risk-manager |
| 작성일 | 2026-03-06 |
| 상태 | Plan |
| 대상 파일 | src/risk_manager.py |

### 1.1 목적
켈리 공식 기반 적정 투자 비중 산출과 리스크 패리티 기반 다종목 분산 투자 비중 조절 기능을 제공한다.

## 2. 기능 요구사항

### FR-01: 켈리 공식 (Kelly Criterion)
- 승률(win_rate)과 손익비(profit_loss_ratio)를 입력받아 적정 투자 비중 계산
- Kelly % = W - (1-W)/R (W: 승률, R: 손익비)
- Half-Kelly, Quarter-Kelly 등 보수적 변형 지원

### FR-02: 리스크 패리티 (Risk Parity)
- 각 종목의 변동성(std)을 기반으로 동일 위험 기여도가 되도록 비중 배분
- 비중 = (1/변동성) / sum(1/변동성)
- DataFrame 입력으로 여러 종목 동시 계산

### FR-03: 포지션 사이징
- 총 자산, 리스크 허용도, 종목별 변동성을 고려한 포지션 크기 산출
