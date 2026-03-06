import numpy as np
import pandas as pd


class Analyzer:
    @staticmethod
    def calculate_mdd(equity_curve):
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak
        return drawdown.min()

    @staticmethod
    def calculate_sharpe(returns, risk_free_rate=0.035):
        if returns.std() == 0:
            return 0.0
        excess = returns.mean() - risk_free_rate / 252
        return excess / returns.std() * np.sqrt(252)

    @staticmethod
    def calculate_cagr(initial, final, years):
        if years <= 0 or initial <= 0:
            return 0.0
        return (final / initial) ** (1 / years) - 1

    @staticmethod
    def summary(result):
        lines = [
            "=" * 40,
            "  Backtest Result Summary",
            "=" * 40,
            f"  Initial Cash:    {result['initial_cash']:>14,.0f}",
            f"  Final Value:     {result['final_value']:>14,.0f}",
            f"  Return:          {result['return_pct']:>13.2f}%",
            f"  Max Drawdown:    {result['max_drawdown']:>13.2f}%",
            f"  Sharpe Ratio:    {result['sharpe_ratio']:>13.2f}",
            f"  Total Trades:    {result['total_trades']:>13d}",
            f"  Winning Trades:  {result['winning_trades']:>13d}",
            f"  Losing Trades:   {result['losing_trades']:>13d}",
            "=" * 40,
        ]
        return "\n".join(lines)
