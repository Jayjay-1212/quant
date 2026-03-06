import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.data_loader import DataLoader
from backtest.engine import BacktestEngine


class PortfolioBacktest:
    def __init__(self, cash=10_000_000, commission=0.00015):
        self.cash = cash
        self.commission = commission
        self.loader = DataLoader()
        self.results = {}
        self.equity_curves = {}

    def run(self, tickers, start, end, strategy_class, weights=None, **kwargs):
        if weights is None:
            weights = {t: 1.0 / len(tickers) for t in tickers}

        for ticker in tickers:
            df = self.loader.get(ticker, start, end)
            allocated_cash = self.cash * weights.get(ticker, 0)
            engine = BacktestEngine(cash=allocated_cash, commission=self.commission)
            engine.add_data(df, name=ticker)
            engine.add_strategy(strategy_class, **kwargs)
            result = engine.run()
            self.results[ticker] = result
            self.equity_curves[ticker] = engine.get_equity_curve()

        return self.summary()

    def summary(self):
        total_initial = sum(r['initial_cash'] for r in self.results.values())
        total_final = sum(r['final_value'] for r in self.results.values())
        total_return = (total_final - total_initial) / total_initial * 100

        # Portfolio equity curve
        all_eq = pd.DataFrame(self.equity_curves)
        portfolio_eq = all_eq.sum(axis=1)

        # Portfolio MDD
        peak = portfolio_eq.cummax()
        dd = (portfolio_eq - peak) / peak * 100
        portfolio_mdd = dd.min()

        # Portfolio daily returns for Sharpe
        daily_ret = portfolio_eq.pct_change().dropna()
        if daily_ret.std() > 0:
            sharpe = (daily_ret.mean() - 0.035 / 252) / daily_ret.std() * np.sqrt(252)
        else:
            sharpe = 0.0

        self._portfolio_equity = portfolio_eq

        return {
            'total_initial': total_initial,
            'total_final': total_final,
            'return_pct': total_return,
            'portfolio_mdd': portfolio_mdd,
            'portfolio_sharpe': sharpe,
            'per_ticker': self.results,
        }

    def print_summary(self, result):
        print("\n" + "=" * 60)
        print("  Portfolio Backtest Summary")
        print("=" * 60)
        print(f"  Total Initial:     {result['total_initial']:>16,.0f}")
        print(f"  Total Final:       {result['total_final']:>16,.0f}")
        print(f"  Portfolio Return:  {result['return_pct']:>15.2f}%")
        print(f"  Portfolio MDD:     {result['portfolio_mdd']:>15.2f}%")
        print(f"  Portfolio Sharpe:  {result['portfolio_sharpe']:>15.2f}")
        print("-" * 60)
        for ticker, r in result['per_ticker'].items():
            print(f"  {ticker:>10s}  Return: {r['return_pct']:>7.2f}%  "
                  f"MDD: {r['max_drawdown']:>6.2f}%  Trades: {r['total_trades']}")
        print("=" * 60)

    def plot(self, result, title=None, save_path=None):
        fig, axes = plt.subplots(2, 1, figsize=(14, 8),
                                 gridspec_kw={'height_ratios': [3, 1]})

        # 1. Per-ticker equity curves + portfolio
        ax1 = axes[0]
        colors = ['#2962FF', '#FF6D00', '#00C853', '#AA00FF', '#FF1744']
        for i, (ticker, eq) in enumerate(self.equity_curves.items()):
            color = colors[i % len(colors)]
            ax1.plot(eq.index, eq.values, label=ticker, color=color,
                     linewidth=0.8, alpha=0.6)
        ax1.plot(self._portfolio_equity.index, self._portfolio_equity.values,
                 label='Portfolio', color='black', linewidth=1.5)
        ax1.set_title(title or 'Portfolio Backtest')
        ax1.set_ylabel('Value')
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)

        # 2. Portfolio drawdown
        ax2 = axes[1]
        peak = self._portfolio_equity.cummax()
        dd = (self._portfolio_equity - peak) / peak * 100
        ax2.fill_between(dd.index, dd.values, 0, color='#FF5252', alpha=0.4)
        ax2.set_title(f'Portfolio Drawdown (MDD: {result["portfolio_mdd"]:.2f}%)')
        ax2.set_ylabel('Drawdown %')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f'Chart saved: {save_path}')
        plt.show()
