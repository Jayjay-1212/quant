import numpy as np
import pandas as pd


class RiskManager:
    """켈리 공식 + 리스크 패리티 기반 리스크 관리"""

    @staticmethod
    def kelly_criterion(win_rate, profit_loss_ratio, fraction=1.0):
        """켈리 공식으로 적정 투자 비중 계산

        Args:
            win_rate: 승률 (0~1, 예: 0.55)
            profit_loss_ratio: 손익비 (평균 수익 / 평균 손실)
            fraction: 켈리 비율 (1.0=Full, 0.5=Half, 0.25=Quarter)

        Returns:
            dict with kelly_pct, adjusted_pct, recommendation
        """
        if win_rate <= 0 or win_rate >= 1:
            raise ValueError("win_rate must be between 0 and 1 (exclusive)")
        if profit_loss_ratio <= 0:
            raise ValueError("profit_loss_ratio must be positive")

        kelly_pct = win_rate - (1 - win_rate) / profit_loss_ratio
        adjusted_pct = kelly_pct * fraction

        if kelly_pct <= 0:
            recommendation = "DO NOT TRADE - negative edge"
        elif kelly_pct < 0.1:
            recommendation = "Very small position - weak edge"
        elif kelly_pct < 0.25:
            recommendation = "Moderate position - decent edge"
        else:
            recommendation = "Strong edge - use Half/Quarter Kelly for safety"

        return {
            'kelly_pct': round(kelly_pct * 100, 2),
            'adjusted_pct': round(adjusted_pct * 100, 2),
            'fraction': fraction,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'recommendation': recommendation,
        }

    @staticmethod
    def kelly_from_backtest(result):
        """백테스트 결과에서 자동으로 켈리 비중 계산"""
        total = result.get('total_trades', 0)
        won = result.get('winning_trades', 0)
        if total == 0 or won == 0:
            return RiskManager.kelly_criterion(0.01, 1.0, fraction=0.5)

        win_rate = won / total

        # Approximate profit/loss ratio from return and win rate
        # This is a simplified estimation
        ret = result.get('return_pct', 0)
        if ret > 0:
            pl_ratio = max((ret / 100 + 1) * (1 / win_rate), 1.0)
        else:
            pl_ratio = max(0.5, abs(ret / 100) * win_rate)

        return RiskManager.kelly_criterion(win_rate, pl_ratio, fraction=0.5)

    @staticmethod
    def risk_parity(price_data, lookback=60):
        """리스크 패리티 방식으로 종목별 투자 비중 계산

        Args:
            price_data: dict[ticker, DataFrame] or DataFrame with tickers as columns
            lookback: 변동성 계산 기간 (거래일 수)

        Returns:
            dict with weights, volatilities, risk_contributions
        """
        if isinstance(price_data, dict):
            closes = pd.DataFrame({
                ticker: df['Close'] for ticker, df in price_data.items()
            })
        else:
            closes = price_data

        returns = closes.pct_change().dropna()
        recent_returns = returns.tail(lookback)

        # Annualized volatility
        volatilities = recent_returns.std() * np.sqrt(252)

        # Inverse volatility weights
        inv_vol = 1.0 / volatilities
        weights = inv_vol / inv_vol.sum()

        # Risk contribution (weight * volatility)
        risk_contrib = weights * volatilities
        risk_contrib_pct = risk_contrib / risk_contrib.sum() * 100

        return {
            'weights': {k: round(v, 4) for k, v in weights.items()},
            'volatilities': {k: round(v, 4) for k, v in volatilities.items()},
            'risk_contributions': {k: round(v, 2) for k, v in risk_contrib_pct.items()},
        }

    @staticmethod
    def position_size(total_capital, risk_per_trade, entry_price, stop_loss_price):
        """포지션 사이징: 1회 거래당 리스크 금액 기반

        Args:
            total_capital: 총 투자 가능 자본
            risk_per_trade: 1회 거래 리스크 비율 (예: 0.02 = 2%)
            entry_price: 진입 가격
            stop_loss_price: 손절 가격

        Returns:
            dict with shares, position_value, risk_amount
        """
        risk_amount = total_capital * risk_per_trade
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share <= 0:
            raise ValueError("entry_price and stop_loss_price must differ")

        shares = int(risk_amount / risk_per_share)
        position_value = shares * entry_price

        return {
            'shares': shares,
            'position_value': position_value,
            'risk_amount': round(risk_amount, 0),
            'risk_per_share': risk_per_share,
            'position_pct': round(position_value / total_capital * 100, 2),
        }

    @staticmethod
    def print_kelly(result):
        print("\n" + "=" * 50)
        print("  Kelly Criterion Analysis")
        print("=" * 50)
        print(f"  Win Rate:          {result['win_rate']:.1%}")
        print(f"  P/L Ratio:         {result['profit_loss_ratio']:.2f}")
        print(f"  Full Kelly:        {result['kelly_pct']:.2f}%")
        print(f"  Adjusted ({result['fraction']:.0%}):   {result['adjusted_pct']:.2f}%")
        print(f"  >> {result['recommendation']}")
        print("=" * 50)

    @staticmethod
    def print_risk_parity(result):
        print("\n" + "=" * 50)
        print("  Risk Parity Allocation")
        print("=" * 50)
        for ticker in result['weights']:
            w = result['weights'][ticker]
            v = result['volatilities'][ticker]
            rc = result['risk_contributions'][ticker]
            print(f"  {ticker:>10s}  Weight: {w:>6.1%}  "
                  f"Vol: {v:>6.1%}  Risk: {rc:>5.1f}%")
        print("=" * 50)
