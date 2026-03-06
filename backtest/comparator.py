import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from backtest.engine import BacktestEngine


class StrategyComparator:
    def __init__(self, df, cash=10_000_000, commission=0.00015):
        self.df = df
        self.cash = cash
        self.commission = commission
        self.results = {}
        self.equity_curves = {}

    def add_strategy(self, name, strategy_class, **kwargs):
        engine = BacktestEngine(cash=self.cash, commission=self.commission)
        engine.add_data(self.df.copy(), name=name)
        engine.add_strategy(strategy_class, **kwargs)
        result = engine.run()
        self.results[name] = result
        self.equity_curves[name] = engine.get_equity_curve()
        return result

    def compare_table(self):
        rows = []
        for name, r in self.results.items():
            rows.append({
                'Strategy': name,
                'Return %': round(r['return_pct'], 2),
                'CAGR %': round(r['cagr_pct'], 2),
                'MDD %': round(r['max_drawdown'], 2),
                'Sharpe': round(r['sharpe_ratio'], 2),
                'Trades': r['total_trades'],
                'Win Rate %': round(r['win_rate'], 1),
            })
        df = pd.DataFrame(rows).sort_values('Return %', ascending=False)
        df.index = range(1, len(df) + 1)
        df.index.name = 'Rank'
        return df

    def print_comparison(self):
        table = self.compare_table()
        print("\n" + "=" * 80)
        print("  Strategy Comparison")
        print("=" * 80)
        print(table.to_string())
        print("=" * 80)

    def plot_equity_curves(self, title=None, save_path=None):
        fig, axes = plt.subplots(3, 1, figsize=(14, 12),
                                 gridspec_kw={'height_ratios': [3, 2, 2]})

        # 1. Equity curves overlay
        ax1 = axes[0]
        colors = ['#2962FF', '#FF6D00', '#00C853', '#AA00FF', '#FF1744', '#00BFA5']
        for i, (name, eq) in enumerate(self.equity_curves.items()):
            color = colors[i % len(colors)]
            ret = self.results[name]['return_pct']
            ax1.plot(eq.index, eq.values, label=f'{name} ({ret:+.2f}%)',
                     color=color, linewidth=1.2)
        ax1.axhline(y=self.cash, color='gray', linestyle='--', alpha=0.5)
        ax1.set_title(title or 'Strategy Comparison - Equity Curves')
        ax1.set_ylabel('Portfolio Value')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)

        # 2. Return bar chart
        ax2 = axes[1]
        names = list(self.results.keys())
        returns = [self.results[n]['return_pct'] for n in names]
        bar_colors = ['#00C853' if r >= 0 else '#FF1744' for r in returns]
        bars = ax2.bar(names, returns, color=bar_colors, alpha=0.8)
        ax2.set_title('Total Return (%)')
        ax2.set_ylabel('Return %')
        ax2.grid(True, alpha=0.3, axis='y')
        for bar, ret in zip(bars, returns):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     f'{ret:.2f}%', ha='center',
                     va='bottom' if ret >= 0 else 'top', fontsize=9)

        # 3. MDD bar chart
        ax3 = axes[2]
        mdds = [self.results[n]['max_drawdown'] for n in names]
        ax3.bar(names, mdds, color='#FF5252', alpha=0.7)
        ax3.set_title('Max Drawdown (%)')
        ax3.set_ylabel('MDD %')
        ax3.grid(True, alpha=0.3, axis='y')
        for i, (name, mdd) in enumerate(zip(names, mdds)):
            ax3.text(i, mdd, f'{mdd:.2f}%', ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f'Chart saved: {save_path}')
        plt.show()
