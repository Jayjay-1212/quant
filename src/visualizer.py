import matplotlib.pyplot as plt
import pandas as pd


class Visualizer:
    @staticmethod
    def plot_price(df, title=None, sma_periods=None):
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(df.index, df['Close'], label='Close', linewidth=1)

        if sma_periods:
            for p in sma_periods:
                sma = df['Close'].rolling(window=p).mean()
                ax.plot(df.index, sma, label=f'SMA {p}', linewidth=0.8)

        ax.set_title(title or 'Price Chart')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

    @staticmethod
    def plot_backtest_result(result, equity_curve):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})

        ax1.plot(equity_curve.index, equity_curve.values, label='Portfolio Value')
        ax1.set_title(f"Backtest Result (Return: {result['return_pct']:.2f}%)")
        ax1.set_ylabel('Portfolio Value')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak * 100
        ax2.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red')
        ax2.set_title(f"Drawdown (Max: {result['max_drawdown']:.2f}%)")
        ax2.set_ylabel('Drawdown %')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

    @staticmethod
    def plot_comparison(results):
        fig, ax = plt.subplots(figsize=(10, 6))
        names = list(results.keys())
        returns = [r['return_pct'] for r in results.values()]
        colors = ['#2ecc71' if r >= 0 else '#e74c3c' for r in returns]

        bars = ax.bar(names, returns, color=colors, alpha=0.8)
        ax.set_title('Strategy Comparison')
        ax.set_ylabel('Return (%)')
        ax.grid(True, alpha=0.3, axis='y')

        for bar, ret in zip(bars, returns):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f'{ret:.1f}%', ha='center', va='bottom' if ret >= 0 else 'top')

        plt.tight_layout()
        plt.show()
