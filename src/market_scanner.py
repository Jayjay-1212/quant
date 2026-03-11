"""KRX 마켓 스캐너 - 시가총액 기반 종목 필터링 + 신호 감지"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta


class MarketScanner:
    """KRX 전체 종목에서 시총 필터링 후 전략 신호를 스캔

    데이터 소스 우선순위:
    1. data/krx_stocks.csv (fetch_krx_stocks.py로 수집한 전체 리스트)
    2. FinanceDataReader 실시간 조회
    3. KOSPI_MAJOR / KOSDAQ_MAJOR 하드코딩 fallback
    """

    # CSV 파일 경로
    _CSV_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'krx_stocks.csv'
    )

    # 주요 종목 사전 (KRX API 접근 불가 시 fallback)
    # 값: (이름, 시총_만원단위)
    KOSPI_MAJOR = {
        '005930': ('삼성전자', 400_0000_0000),      # 400조
        '000660': ('SK하이닉스', 150_0000_0000),     # 150조
        '373220': ('LG에너지솔루션', 90_0000_0000),
        '207940': ('삼성바이오로직스', 55_0000_0000),
        '005380': ('현대차', 50_0000_0000),
        '006400': ('삼성SDI', 30_0000_0000),
        '051910': ('LG화학', 28_0000_0000),
        '035420': ('NAVER', 35_0000_0000),
        '000270': ('기아', 35_0000_0000),
        '068270': ('셀트리온', 30_0000_0000),
        '105560': ('KB금융', 28_0000_0000),
        '055550': ('신한지주', 24_0000_0000),
        '035720': ('카카오', 18_0000_0000),
        '003670': ('포스코퓨처엠', 12_0000_0000),
        '028260': ('삼성물산', 25_0000_0000),
        '012330': ('현대모비스', 22_0000_0000),
        '066570': ('LG전자', 18_0000_0000),
        '032830': ('삼성생명', 18_0000_0000),
        '096770': ('SK이노베이션', 15_0000_0000),
        '003550': ('LG', 14_0000_0000),
        '034730': ('SK', 14_0000_0000),
        '015760': ('한국전력', 14_0000_0000),
        '010130': ('고려아연', 10_0000_0000),
        '009150': ('삼성전기', 12_0000_0000),
        '033780': ('KT&G', 12_0000_0000),
        '086790': ('하나금융지주', 16_0000_0000),
        '316140': ('우리금융지주', 13_0000_0000),
        '010950': ('S-Oil', 8_0000_0000),
        '017670': ('SK텔레콤', 12_0000_0000),
        '030200': ('KT', 10_0000_0000),
        '018260': ('삼성에스디에스', 10_0000_0000),
        '011200': ('HMM', 8_0000_0000),
        '034020': ('두산에너빌리티', 8_0000_0000),
        '003490': ('대한항공', 8_0000_0000),
        '009540': ('한국조선해양', 7_0000_0000),
        '042660': ('한화오션', 9_0000_0000),
        '329180': ('HD현대중공업', 12_0000_0000),
        '267250': ('HD현대', 8_0000_0000),
        '138040': ('메리츠금융지주', 14_0000_0000),
        '259960': ('크래프톤', 12_0000_0000),
    }

    KOSDAQ_MAJOR = {
        '247540': ('에코프로비엠', 15_0000_0000),
        '091990': ('셀트리온헬스케어', 8_0000_0000),
        '086520': ('에코프로', 10_0000_0000),
        '028300': ('HLB', 8_0000_0000),
        '196170': ('알테오젠', 12_0000_0000),
        '403870': ('HPSP', 5_0000_0000),
        '377300': ('카카오페이', 5_0000_0000),
        '293490': ('카카오게임즈', 2_0000_0000),
        '145020': ('휴젤', 4_0000_0000),
        '263750': ('펄어비스', 2_0000_0000),
        '357780': ('솔브레인', 3_0000_0000),
        '112040': ('위메이드', 1_5000_0000),
        '036570': ('엔씨소프트', 4_0000_0000),
        '352820': ('하이브', 6_0000_0000),
        '383220': ('F&F', 3_0000_0000),
        '041510': ('에스엠', 2_0000_0000),
        '035900': ('JYP Ent.', 2_0000_0000),
        '067160': ('아프리카TV', 1_5000_0000),
        '240810': ('원익IPS', 1_5000_0000),
        '058470': ('리노공업', 4_0000_0000),
    }

    @classmethod
    def _load_from_csv(cls, market='ALL'):
        """data/krx_stocks.csv에서 종목 리스트 로드

        CSV 컬럼: Code, Name, Market, MarketCap (원 단위)
        Returns DataFrame with columns: ticker, name, market, market_cap (만원), market_cap_조
                or None if CSV not found / empty
        """
        if not os.path.exists(cls._CSV_PATH):
            return None

        try:
            df = pd.read_csv(cls._CSV_PATH, dtype={'Code': str})
            if df is None or len(df) == 0:
                return None

            # Market 필터
            if market == 'KOSPI':
                df = df[df['Market'] == 'KOSPI']
            elif market == 'KOSDAQ':
                df = df[df['Market'] == 'KOSDAQ']
            # 'ALL' -> 전체

            # CSV의 MarketCap은 원 단위 -> 만원으로 변환 (내부 기준)
            market_cap_won = pd.to_numeric(df['MarketCap'], errors='coerce').fillna(0)
            market_cap_만원 = market_cap_won / 10000

            rows = pd.DataFrame({
                'ticker': df['Code'].astype(str).str.zfill(6),
                'name': df['Name'].astype(str),
                'market': df['Market'].astype(str),
                'market_cap': market_cap_만원,
                'market_cap_조': (market_cap_만원 / 1_0000_0000).round(1),
            })

            rows = rows.sort_values('market_cap', ascending=False).reset_index(drop=True)
            return rows

        except Exception:
            return None

    @classmethod
    def _load_from_hardcoded(cls, market='ALL'):
        """하드코딩된 KOSPI_MAJOR / KOSDAQ_MAJOR에서 로드 (fallback)"""
        stocks = {}
        if market in ('ALL', 'KOSPI'):
            for code, (name, mcap) in cls.KOSPI_MAJOR.items():
                stocks[code] = (name, 'KOSPI', mcap)
        if market in ('ALL', 'KOSDAQ'):
            for code, (name, mcap) in cls.KOSDAQ_MAJOR.items():
                stocks[code] = (name, 'KOSDAQ', mcap)

        rows = []
        for code, (name, mkt, mcap) in stocks.items():
            rows.append({
                'ticker': code,
                'name': name,
                'market': mkt,
                'market_cap': mcap,
                'market_cap_조': round(mcap / 1_0000_0000, 1),
            })

        df = pd.DataFrame(rows).sort_values('market_cap', ascending=False)
        return df.reset_index(drop=True)

    @classmethod
    def get_stock_list(cls, market='ALL'):
        """종목 리스트 반환 (ticker, name, market, market_cap, market_cap_조)

        우선순위:
        1. data/krx_stocks.csv (캐시된 전체 리스트)
        2. FinanceDataReader 실시간
        3. 하드코딩된 주요 종목
        """
        # 1. CSV 캐시에서 로드
        df = cls._load_from_csv(market)
        if df is not None and len(df) > 0:
            return df

        # 2. FinanceDataReader 실시간
        live = cls._fetch_krx_listing()
        if live is not None and len(live) > 0:
            stocks = {}
            for _, row in live.iterrows():
                stocks[row['Code']] = (row['Name'], 'KRX', row['Marcap'])

            rows = []
            for code, (name, mkt, mcap) in stocks.items():
                rows.append({
                    'ticker': code,
                    'name': name,
                    'market': mkt,
                    'market_cap': mcap,
                    'market_cap_조': round(mcap / 1_0000_0000, 1),
                })
            df = pd.DataFrame(rows).sort_values('market_cap', ascending=False)
            return df.reset_index(drop=True)

        # 3. 하드코딩 fallback
        return cls._load_from_hardcoded(market)

    @classmethod
    def _fetch_krx_listing(cls):
        """KRX에서 실시간 종목 리스트 시도 (실패하면 None)"""
        try:
            import FinanceDataReader as fdr
            df = fdr.StockListing('KRX')
            if df is not None and len(df) > 0:
                # Standardize columns
                cols = df.columns.tolist()
                result = pd.DataFrame()
                if 'Code' in cols:
                    result['Code'] = df['Code']
                elif 'Symbol' in cols:
                    result['Code'] = df['Symbol']
                else:
                    return None

                if 'Name' in cols:
                    result['Name'] = df['Name']
                else:
                    return None

                if 'Marcap' in cols:
                    result['Marcap'] = pd.to_numeric(df['Marcap'], errors='coerce')
                elif 'MarketCap' in cols:
                    result['Marcap'] = pd.to_numeric(df['MarketCap'], errors='coerce')
                else:
                    return None

                return result.dropna()
        except Exception:
            pass
        return None

    @classmethod
    def filter_by_market_cap(cls, min_cap_억=0, max_cap_억=None, market='ALL'):
        """시가총액 범위로 필터링 (단위: 억원)

        Args:
            min_cap_억: 최소 시총 (억원), 예: 10000 = 1조
            max_cap_억: 최대 시총 (억원), None이면 제한 없음
            market: 'ALL', 'KOSPI', 'KOSDAQ'
        """
        df = cls.get_stock_list(market)
        min_val = min_cap_억 * 1_0000  # 억 → 만원 단위 환산 (내부는 만원 기준)

        # market_cap is in 만원 units
        filtered = df[df['market_cap'] >= min_val]
        if max_cap_억 is not None:
            max_val = max_cap_억 * 1_0000
            filtered = filtered[filtered['market_cap'] <= max_val]

        return filtered.reset_index(drop=True)

    @classmethod
    def scan_signals(cls, tickers, strategy_class, strategy_params,
                     data_loader, lookback_start='2024-06-01', progress_callback=None):
        """여러 종목에 대해 전략 신호 스캔

        Args:
            tickers: list of ticker codes
            strategy_class: backtrader Strategy class
            strategy_params: dict of strategy parameters
            data_loader: DataLoader instance
            lookback_start: 데이터 시작일
            progress_callback: fn(current, total) for progress updates
        """
        from src.scheduler import SignalChecker
        checker = SignalChecker(data_loader)
        results = []

        for i, ticker in enumerate(tickers):
            try:
                sig = checker.check_signal(ticker, strategy_class,
                                           lookback_start, **strategy_params)
                results.append(sig)
            except Exception as e:
                results.append({
                    'ticker': ticker,
                    'signal': 'ERROR',
                    'strategy': strategy_class.__name__,
                    'message': str(e),
                })

            if progress_callback:
                progress_callback(i + 1, len(tickers))

        return results
