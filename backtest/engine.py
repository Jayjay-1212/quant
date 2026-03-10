import backtrader as bt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class BacktestEngine:
    def __init__(self, cash=10_000_000, commission=0.00015):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(cash)
        self.cerebro.broker.setcommission(commission=commission)
        self.initial_cash = cash
        self._results = None
        self._data_df = None

    def add_data(self, df, name=None):
        self._data_df = df.copy()
        data = bt.feeds.PandasData(dataname=df, name=name)
        self.cerebro.adddata(data)

    def add_strategy(self, strategy_class, **kwargs):
        self.cerebro.addstrategy(strategy_class, **kwargs)

    def run(self):
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',
                                riskfreerate=0.035, annualize=True)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='time_return')

        self._results = self.cerebro.run()
        strat = self._results[0]

        final_value = self.cerebro.broker.getvalue()
        return_pct = (final_value - self.initial_cash) / self.initial_cash * 100

        # Sharpe ratio
        sharpe = strat.analyzers.sharpe.get_analysis()
        sharpe_ratio = sharpe.get('sharperatio', 0.0) or 0.0

        # Max drawdown
        drawdown = strat.analyzers.drawdown.get_analysis()
        max_dd = drawdown.get('max', {}).get('drawdown', 0.0)

        # Trade stats
        trades = strat.analyzers.trades.get_analysis()
        total = trades.get('total', {}).get('total', 0)
        won = trades.get('won', {}).get('total', 0)
        lost = trades.get('lost', {}).get('total', 0)

        # CAGR
        time_return = strat.analyzers.time_return.get_analysis()
        dates = sorted(time_return.keys())
        if len(dates) > 1:
            years = (dates[-1] - dates[0]).days / 365.25
        else:
            years = 1.0
        cagr = ((final_value / self.initial_cash) ** (1 / max(years, 0.01)) - 1) * 100

        # Equity curve
        equity = [self.initial_cash]
        for d in dates:
            equity.append(equity[-1] * (1 + time_return[d]))
        self._equity_curve = pd.Series(equity[1:], index=dates)

        return {
            'initial_cash': self.initial_cash,
            'final_value': final_value,
            'return_pct': return_pct,
            'cagr_pct': cagr,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': total,
            'winning_trades': won,
            'losing_trades': lost,
            'win_rate': (won / total * 100) if total > 0 else 0.0,
            'period_years': round(years, 2),
        }

    def get_equity_curve(self):
        return self._equity_curve

    def plot_results(self, result, title=None, save_path=None):
        equity = self._equity_curve

        fig, axes = plt.subplots(3, 1, figsize=(14, 10),
                                 gridspec_kw={'height_ratios': [3, 1, 1]})

        # 1. Equity curve
        ax1 = axes[0]
        ax1.plot(equity.index, equity.values, color='#2962FF', linewidth=1.2)
        ax1.axhline(y=self.initial_cash, color='gray', linestyle='--', alpha=0.5)
        ax1.set_title(title or 'Backtest Result')
        ax1.set_ylabel('Portfolio Value')
        ax1.grid(True, alpha=0.3)

        # Add stats text box
        stats_text = (
            f"Return: {result['return_pct']:.2f}%\n"
            f"CAGR: {result['cagr_pct']:.2f}%\n"
            f"MDD: {result['max_drawdown']:.2f}%\n"
            f"Sharpe: {result['sharpe_ratio']:.2f}"
        )
        ax1.text(0.02, 0.95, stats_text, transform=ax1.transAxes,
                 fontsize=9, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # 2. Drawdown
        ax2 = axes[1]
        peak = equity.cummax()
        dd = (equity - peak) / peak * 100
        ax2.fill_between(dd.index, dd.values, 0, color='#FF5252', alpha=0.4)
        ax2.set_ylabel('Drawdown %')
        ax2.set_title(f'Max Drawdown: {result["max_drawdown"]:.2f}%')
        ax2.grid(True, alpha=0.3)

        # 3. Price chart (if data available)
        ax3 = axes[2]
        if self._data_df is not None:
            price = self._data_df['Close']
            ax3.plot(price.index, price.values, color='#333', linewidth=0.8)
            ax3.set_ylabel('Price')
            ax3.set_title('Underlying Asset')
            ax3.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f'Chart saved: {save_path}')
        plt.show()

    def get_trade_log(self):
        if not self._results:
            return pd.DataFrame()
        strat = self._results[0]
        trades = strat.analyzers.trades.get_analysis()
        total = trades.get('total', {}).get('total', 0)
        if total == 0:
            return pd.DataFrame(columns=['date', 'action', 'price', 'size', 'pnl'])
        logs = []
        try:
            for trade_list in strat._trades.values():
                for t in trade_list:
                    if not hasattr(t, 'history'):
                        continue
                    for entry in t.history:
                        event = entry.event
                        status = entry.status
                        logs.append({
                            'date': bt.num2date(event.dt).date(),
                            'action': 'BUY' if event.size > 0 else 'SELL',
                            'price': event.price,
                            'size': abs(event.size),
                            'pnl': t.pnl if status.isclosed else 0.0,
                        })
        except Exception:
            return pd.DataFrame(columns=['date', 'action', 'price', 'size', 'pnl'])
        if not logs:
            return pd.DataFrame(columns=['date', 'action', 'price', 'size', 'pnl'])
        return pd.DataFrame(logs).sort_values('date').reset_index(drop=True)

    def print_summary(self, result):
        lines = [
            "=" * 50,
            "  Backtest Result Summary",
            "=" * 50,
            f"  Period:            {result['period_years']} years",
            f"  Initial Cash:      {result['initial_cash']:>16,.0f}",
            f"  Final Value:       {result['final_value']:>16,.0f}",
            "-" * 50,
            f"  Total Return:      {result['return_pct']:>15.2f}%",
            f"  CAGR:              {result['cagr_pct']:>15.2f}%",
            f"  Max Drawdown:      {result['max_drawdown']:>15.2f}%",
            f"  Sharpe Ratio:      {result['sharpe_ratio']:>15.2f}",
            "-" * 50,
            f"  Total Trades:      {result['total_trades']:>15d}",
            f"  Winning Trades:    {result['winning_trades']:>15d}",
            f"  Losing Trades:     {result['losing_trades']:>15d}",
            f"  Win Rate:          {result['win_rate']:>14.1f}%",
            "=" * 50,
        ]
        print("\n".join(lines))
