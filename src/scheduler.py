import os
import time
import logging
from datetime import datetime

import backtrader as bt
from src.data_loader import DataLoader


logging.basicConfig(
    filename='data/scheduler.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


class SignalChecker:
    """전략 신호 감지기 - 최신 데이터에서 매수/매도 신호 확인"""

    def __init__(self, data_loader=None):
        self.loader = data_loader or DataLoader()

    def check_signal(self, ticker, strategy_class, start, end=None, **kwargs):
        """특정 종목에 대해 전략 신호 확인

        Returns:
            dict with signal ('BUY', 'SELL', 'HOLD'), ticker, strategy info
        """
        if end is None:
            end = datetime.now().strftime('%Y-%m-%d')

        try:
            df = self.loader.get(ticker, start, end)
        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")
            return {'ticker': ticker, 'signal': 'ERROR', 'message': str(e)}

        cerebro = bt.Cerebro()
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data)

        # Capture last signal
        signal_holder = {'signal': 'HOLD'}

        class SignalCapture(strategy_class):
            params = tuple(kwargs.items()) if kwargs else strategy_class.params

            def next(self):
                super().next()

            def buy(self, *args, **kw):
                signal_holder['signal'] = 'BUY'
                return super().buy(*args, **kw)

            def close(self, *args, **kw):
                signal_holder['signal'] = 'SELL'
                return super().close(*args, **kw)

        cerebro.addstrategy(SignalCapture, **kwargs)
        cerebro.run()

        result = {
            'ticker': ticker,
            'signal': signal_holder['signal'],
            'strategy': strategy_class.__name__,
            'date': end,
            'params': kwargs,
        }

        if result['signal'] != 'HOLD':
            logger.info(f"SIGNAL: {result['signal']} {ticker} ({strategy_class.__name__})")

        return result


class Scheduler:
    """일일 데이터 수집 및 신호 체크 스케줄러"""

    def __init__(self):
        self.loader = DataLoader(cache_days=0)  # 항상 갱신
        self.checker = SignalChecker(self.loader)
        self.watchlist = []
        self.strategies = []

    def add_watch(self, ticker, start='2024-01-01'):
        self.watchlist.append({'ticker': ticker, 'start': start})

    def add_strategy(self, strategy_class, **kwargs):
        self.strategies.append({'class': strategy_class, 'kwargs': kwargs})

    def run_once(self):
        """1회 실행: 데이터 갱신 + 신호 체크"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'=' * 50}")
        print(f"  Scheduler Run: {now}")
        print(f"{'=' * 50}")
        logger.info(f"Scheduler run started")

        signals = []

        for watch in self.watchlist:
            ticker = watch['ticker']
            start = watch['start']

            # Refresh data
            self.loader.clear_cache(ticker)
            try:
                df = self.loader.get(ticker, start, datetime.now().strftime('%Y-%m-%d'))
                print(f"  [{ticker}] Data refreshed: {len(df)} rows")
                logger.info(f"Data refreshed: {ticker} ({len(df)} rows)")
            except Exception as e:
                print(f"  [{ticker}] ERROR: {e}")
                logger.error(f"Data refresh failed: {ticker} - {e}")
                continue

            # Check signals
            for strat in self.strategies:
                result = self.checker.check_signal(
                    ticker, strat['class'], start, **strat['kwargs'])
                signals.append(result)

                icon = {'BUY': '>>BUY', 'SELL': '>>SELL', 'HOLD': '  HOLD', 'ERROR': '  ERR'}
                print(f"    {icon.get(result['signal'], '?'):>7s}  "
                      f"{strat['class'].__name__}")

        # Summary
        buy_signals = [s for s in signals if s['signal'] == 'BUY']
        sell_signals = [s for s in signals if s['signal'] == 'SELL']

        print(f"\n  Summary: {len(buy_signals)} BUY, {len(sell_signals)} SELL, "
              f"{len(signals) - len(buy_signals) - len(sell_signals)} HOLD")
        print(f"{'=' * 50}")

        logger.info(f"Run complete: {len(buy_signals)} BUY, {len(sell_signals)} SELL")
        return signals

    def run_loop(self, interval_minutes=60):
        """반복 실행 (Ctrl+C로 중단)"""
        print(f"Scheduler started (interval: {interval_minutes}min)")
        print("Press Ctrl+C to stop\n")
        logger.info(f"Scheduler loop started (interval: {interval_minutes}min)")

        try:
            while True:
                self.run_once()
                print(f"\nNext run in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\nScheduler stopped.")
            logger.info("Scheduler stopped by user")
