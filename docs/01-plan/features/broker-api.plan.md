# Plan: 증권사 API 연동 (KIS API)

## 1. 개요

| 항목 | 내용 |
|------|------|
| Feature | broker-api |
| 작성일 | 2026-03-06 |
| 상태 | Plan |
| 대상 파일 | src/broker_api.py |

### 1.1 목적
한국투자증권 KIS Developers Open API를 연동하여 실전 투자 기능의 기반을 구축한다.
REST API 방식으로 인증, 잔고 조회, 시장가 주문을 지원한다.

## 2. 기능 요구사항

### FR-01: 인증
- .env 파일에서 APP_KEY, APP_SECRET, ACCOUNT_NO 로드
- OAuth 토큰 발급 및 관리

### FR-02: 잔고 조회
- 보유 종목 목록, 수량, 평가금액, 수익률 조회

### FR-03: 시장가 주문
- 매수/매도 주문 (시장가)
- 주문 결과 반환

### FR-04: 보안
- API Key는 .env 파일로 분리
- .env는 .gitignore에 포함 (이미 설정됨)
