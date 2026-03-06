import os
import time
import pandas as pd
import FinanceDataReader as fdr


class DataLoader:
    INDEX_PRESETS = {
        'KOSPI': 'KS11',
        'KOSDAQ': 'KQ11',
        'S&P500': 'US500',
        'NASDAQ': 'IXIC',
        'DOW': 'DJI',
        'NIKKEI': 'N225',
        'HSI': 'HSI',
        'VIX': 'VIX',
    }

    def __init__(self, data_dir="data", cache_days=1):
        self.data_dir = data_dir
        self.cache_days = cache_days
        self._memory_cache = {}
        os.makedirs(data_dir, exist_ok=True)

    def fetch(self, ticker, start, end):
        df = fdr.DataReader(ticker, start, end)
        if df.empty:
            raise ValueError(f"No data found for ticker '{ticker}'")
        return df

    def save(self, df, ticker):
        path = os.path.join(self.data_dir, f"{ticker}.csv")
        df.to_csv(path)
        return path

    def load(self, ticker):
        path = os.path.join(self.data_dir, f"{ticker}.csv")
        return pd.read_csv(path, index_col=0, parse_dates=True)

    def get(self, ticker, start, end):
        key = self._cache_key(ticker)

        # 1. Memory cache
        if key in self._memory_cache:
            return self._memory_cache[key]

        # 2. CSV cache (valid)
        if self._is_cache_valid(ticker):
            df = self.load(ticker)
            self._memory_cache[key] = df
            return df

        # 3. Fetch from API
        df = self.fetch(ticker, start, end)
        self.save(df, ticker)
        self._memory_cache[key] = df
        return df

    def fetch_index(self, index_name, start, end):
        if index_name not in self.INDEX_PRESETS:
            raise KeyError(
                f"Unknown index '{index_name}'. "
                f"Available: {list(self.INDEX_PRESETS.keys())}"
            )
        ticker = self.INDEX_PRESETS[index_name]
        return self.get(ticker, start, end)

    def fetch_multiple(self, tickers, start, end):
        results = {}
        for ticker in tickers:
            try:
                results[ticker] = self.get(ticker, start, end)
            except Exception as e:
                print(f"[WARN] Failed to fetch '{ticker}': {e}")
        return results

    def clear_cache(self, ticker=None):
        if ticker is None:
            self._memory_cache.clear()
        else:
            key = self._cache_key(ticker)
            self._memory_cache.pop(key, None)

    def list_cached(self):
        cached = []
        for f in os.listdir(self.data_dir):
            if f.endswith('.csv'):
                cached.append(f.replace('.csv', ''))
        return sorted(cached)

    def _is_cache_valid(self, ticker):
        path = os.path.join(self.data_dir, f"{ticker}.csv")
        if not os.path.exists(path):
            return False
        mtime = os.path.getmtime(path)
        age_days = (time.time() - mtime) / 86400
        return age_days < self.cache_days

    def _cache_key(self, ticker):
        return ticker.upper()
