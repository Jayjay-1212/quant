# Design: DataLoader 강화

## 1. 개요

| 항목 | 내용 |
|------|------|
| Feature | data-loader-enhancement |
| 작성일 | 2026-03-06 |
| 상태 | Design |
| Plan 참조 | docs/01-plan/features/data-loader-enhancement.plan.md |

## 2. 클래스 설계

```python
class DataLoader:
    # 주요 지수 프리셋
    INDEX_PRESETS = {
        'KOSPI': 'KS11',
        'KOSDAQ': 'KQ11',
        'S&P500': 'US500',
        'NASDAQ': 'IXIC',
        'DOW': 'DJI',
        'NIKKEI': 'N225',
        'HSI': 'HSI',
    }

    def __init__(self, data_dir="data", cache_days=1):
        """
        data_dir: CSV 저장 디렉토리
        cache_days: CSV 캐시 유효 기간 (일)
        """
        self._memory_cache: dict[str, pd.DataFrame] = {}

    # --- 기존 인터페이스 (하위 호환) ---
    def fetch(self, ticker, start, end) -> pd.DataFrame
    def save(self, df, ticker) -> str
    def load(self, ticker) -> pd.DataFrame
    def get(self, ticker, start, end) -> pd.DataFrame

    # --- 신규 기능 ---
    def fetch_index(self, index_name, start, end) -> pd.DataFrame
    def fetch_multiple(self, tickers, start, end) -> dict[str, pd.DataFrame]
    def clear_cache(self, ticker=None) -> None
    def list_cached(self) -> list[str]
    def _is_cache_valid(self, ticker) -> bool
    def _cache_key(self, ticker) -> str
```

## 3. 메서드 상세

### fetch_index(index_name, start, end)
- INDEX_PRESETS에서 실제 코드 조회
- 없으면 KeyError 발생
- 내부적으로 get() 호출

### fetch_multiple(tickers, start, end)
- 리스트 순회하며 get() 호출
- 실패 종목은 경고 출력 후 건너뜀
- {ticker: DataFrame} 반환

### get(ticker, start, end) — 강화
1. 메모리 캐시 확인 → 히트 시 즉시 반환
2. CSV 캐시 확인 + 유효성 검증
3. 캐시 미스 → fetch() → 메모리 캐시 + CSV 저장

### _is_cache_valid(ticker)
- CSV 파일 수정일 기준 cache_days 이내면 유효

### clear_cache(ticker=None)
- ticker 지정: 해당 종목만 메모리 캐시 삭제
- None: 전체 메모리 캐시 초기화

## 4. 캐싱 흐름

```
get(ticker, start, end)
    │
    ├── [1] 메모리 캐시 히트? ──→ 반환 (즉시)
    │
    ├── [2] CSV 존재 + 유효? ──→ 로드 → 메모리 캐시 저장 → 반환
    │
    └── [3] 캐시 미스 ──→ fetch() → CSV 저장 → 메모리 캐시 저장 → 반환
```
