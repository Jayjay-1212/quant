# Design: 개인용 퀀트 트레이딩 플랫폼

## 1. 개요

| 항목 | 내용 |
|------|------|
| Feature | quant-trading-platform |
| 작성일 | 2026-03-06 |
| 상태 | Design |
| Plan 참조 | docs/01-plan/features/quant-trading-platform.plan.md |

## 2. 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                    main.py (진입점)                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ data_loader   │  │  strategies  │  │ visualizer│ │
│  │              │  │              │  │           │ │
│  │ - fetch()    │  │ - SmaCross   │  │ - plot()  │ │
│  │ - load()     │  │ - Momentum   │  │ - compare│ │
│  │ - save()     │  │              │  │           │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
│         │                 │                │       │
│         └────────┬────────┘                │       │
│                  ▼                         │       │
│         ┌──────────────┐                   │       │
│         │   backtest    │───────────────────┘       │
│         │   engine      │                           │
│         │              │                           │
│         │ - run()      │                           │
│         │ - results()  │                           │
│         └──────────────┘                           │
│                                                     │
├─────────────────────────────────────────────────────┤
│               data/ (CSV 파일 저장소)                  │
└─────────────────────────────────────────────────────┘
```

## 3. 모듈 상세 설계

### 3.1 src/data_loader.py — 데이터 수집 모듈

```python
class DataLoader:
    """주식 데이터 수집 및 관리"""

    def __init__(self, data_dir: str = "data"):
        """data_dir: CSV 파일 저장 디렉토리"""

    def fetch(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        """FinanceDataReader로 주식 데이터 수집
        - ticker: 종목코드 (예: '005930', 'AAPL')
        - start/end: 'YYYY-MM-DD' 형식
        - 반환: OHLCV DataFrame
        """

    def save(self, df: pd.DataFrame, ticker: str) -> str:
        """DataFrame을 CSV로 저장, 파일 경로 반환"""

    def load(self, ticker: str) -> pd.DataFrame:
        """저장된 CSV 파일 로드"""

    def get(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        """캐시 우선 로드, 없으면 fetch 후 save"""
```

### 3.2 strategies/ — 전략 모듈

#### 3.2.1 strategies/sma_cross.py — SMA 크로스오버

```python
class SmaCross(bt.Strategy):
    """단순 이동평균 크로스오버 전략"""

    params = (
        ('short_period', 20),
        ('long_period', 60),
    )

    def __init__(self):
        """SMA 인디케이터 초기화"""

    def next(self):
        """골든크로스 매수, 데드크로스 매도"""
```

#### 3.2.2 strategies/momentum.py — 모멘텀 전략

```python
class Momentum(bt.Strategy):
    """모멘텀 기반 전략"""

    params = (
        ('period', 20),
        ('threshold', 0.0),
    )

    def __init__(self):
        """ROC(Rate of Change) 인디케이터 초기화"""

    def next(self):
        """모멘텀 양수 매수, 음수 매도"""
```

### 3.3 backtest/engine.py — 백테스팅 엔진

```python
class BacktestEngine:
    """backtrader 래퍼 클래스"""

    def __init__(self, cash: float = 10_000_000, commission: float = 0.00015):
        """
        - cash: 초기 투자금 (기본 1000만원)
        - commission: 수수료율 (기본 0.015%)
        """

    def add_data(self, df: pd.DataFrame, name: str = None):
        """pandas DataFrame을 backtrader 데이터피드로 변환 및 추가"""

    def add_strategy(self, strategy_class, **kwargs):
        """전략 클래스 및 파라미터 추가"""

    def run(self) -> dict:
        """백테스트 실행, 결과 dict 반환
        반환값:
        {
            'initial_cash': float,
            'final_value': float,
            'return_pct': float,
            'max_drawdown': float,
            'sharpe_ratio': float,
            'total_trades': int,
            'winning_trades': int,
            'losing_trades': int,
        }
        """

    def get_trade_log(self) -> pd.DataFrame:
        """거래 내역 DataFrame 반환"""
```

### 3.4 src/analyzer.py — 분석 모듈

```python
class Analyzer:
    """백테스팅 결과 분석"""

    @staticmethod
    def calculate_mdd(equity_curve: pd.Series) -> float:
        """최대 낙폭(MDD) 계산"""

    @staticmethod
    def calculate_sharpe(returns: pd.Series, risk_free_rate: float = 0.035) -> float:
        """샤프 비율 계산 (무위험수익률 기본 3.5%)"""

    @staticmethod
    def calculate_cagr(initial: float, final: float, years: float) -> float:
        """연평균 복합 성장률 계산"""

    @staticmethod
    def summary(result: dict) -> str:
        """결과를 보기 좋은 텍스트 요약으로 반환"""
```

### 3.5 src/visualizer.py — 시각화 모듈

```python
class Visualizer:
    """차트 시각화"""

    @staticmethod
    def plot_price(df: pd.DataFrame, title: str = None, sma_periods: list = None):
        """주가 차트 + 선택적 SMA 오버레이"""

    @staticmethod
    def plot_backtest_result(result: dict, equity_curve: pd.Series):
        """백테스팅 결과 시각화 (수익률 곡선 + 드로다운)"""

    @staticmethod
    def plot_comparison(results: dict):
        """여러 전략 수익률 비교 차트
        results: {'전략명': result_dict, ...}
        """
```

## 4. 데이터 흐름

```
1. 데이터 수집
   DataLoader.get("005930", "2020-01-01", "2025-12-31")
       → CSV 캐시 확인 → 없으면 FinanceDataReader 호출
       → DataFrame 반환 + CSV 저장

2. 백테스팅 실행
   engine = BacktestEngine(cash=10_000_000)
   engine.add_data(df)
   engine.add_strategy(SmaCross, short_period=5, long_period=20)
   result = engine.run()

3. 결과 분석 및 시각화
   Analyzer.summary(result)
   Visualizer.plot_backtest_result(result, equity_curve)
```

## 5. 구현 순서

| 순서 | 파일 | 의존성 |
|------|------|--------|
| 1 | src/data_loader.py | 없음 |
| 2 | src/analyzer.py | 없음 |
| 3 | strategies/sma_cross.py | 없음 |
| 4 | strategies/momentum.py | 없음 |
| 5 | backtest/engine.py | data_loader, strategies |
| 6 | src/visualizer.py | analyzer |
| 7 | main.py | 모든 모듈 |

## 6. 설정 및 상수

```python
# 기본 설정값
DEFAULT_CASH = 10_000_000       # 초기 투자금 1000만원
DEFAULT_COMMISSION = 0.00015    # 수수료 0.015%
DEFAULT_DATA_DIR = "data"       # 데이터 저장 디렉토리
DEFAULT_RISK_FREE = 0.035       # 무위험수익률 3.5%
```

## 7. 에러 처리 방침

| 상황 | 처리 |
|------|------|
| 잘못된 종목코드 | FinanceDataReader가 빈 DataFrame 반환 → ValueError 발생 |
| 네트워크 오류 | requests 예외 그대로 전파 |
| CSV 파일 없음 | fetch 후 자동 저장 (get 메서드) |
| 데이터 기간 부족 | backtrader가 자체 처리 |
