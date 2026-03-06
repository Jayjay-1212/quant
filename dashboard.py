import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.data_loader import DataLoader
from src.analyzer import Analyzer
from src.risk_manager import RiskManager
from backtest.engine import BacktestEngine
from backtest.comparator import StrategyComparator
from strategies.moving_average_cross import MovingAverageCross
from strategies.bollinger_band import BollingerBand
from strategies.rsi import RsiStrategy
from strategies.macd import MacdStrategy
from strategies.sma_cross import SmaCross
from strategies.momentum import Momentum

STRATEGIES = {
    'MA Cross (20/60)': (MovingAverageCross, {'short_period': 20, 'long_period': 60}),
    'SMA Cross (20/60)': (SmaCross, {'short_period': 20, 'long_period': 60}),
    'Bollinger Band': (BollingerBand, {'period': 20, 'devfactor': 2.0}),
    'RSI': (RsiStrategy, {'period': 14, 'oversold': 30, 'overbought': 70}),
    'MACD': (MacdStrategy, {'fast': 12, 'slow': 26, 'signal': 9}),
    'Momentum': (Momentum, {'period': 20, 'threshold': 0.0}),
}

st.set_page_config(page_title="Quant Trading Platform", layout="wide")
st.title("Quant Trading Platform")

loader = DataLoader(cache_days=1)

tab1, tab2, tab3, tab4 = st.tabs([
    "Stock Analysis", "Backtesting", "Strategy Comparison", "Portfolio"
])

# ─── Tab 1: Stock Analysis ───
with tab1:
    st.header("Stock Analysis")
    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("Ticker", "005930", key="t1_ticker")
    with col2:
        start = st.date_input("Start", pd.Timestamp("2024-01-01"), key="t1_start")
    with col3:
        end = st.date_input("End", pd.Timestamp("2024-12-31"), key="t1_end")

    sma_options = st.multiselect("SMA Periods", [5, 10, 20, 40, 60, 120], default=[20, 60])

    if st.button("Load & Analyze", key="t1_btn"):
        with st.spinner("Fetching data..."):
            df = loader.get(ticker, str(start), str(end))

        st.success(f"Loaded {len(df)} rows")
        st.dataframe(df.tail(10), use_container_width=True)

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df.index, df['Close'], label='Close', linewidth=1)
        for p in sma_options:
            sma = df['Close'].rolling(p).mean()
            ax.plot(df.index, sma, label=f'SMA {p}', linewidth=0.8)
        ax.set_title(f'{ticker} Price Chart')
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Latest Close", f"{df['Close'].iloc[-1]:,.0f}")
            st.metric("Period High", f"{df['High'].max():,.0f}")
        with col_b:
            st.metric("Period Low", f"{df['Low'].min():,.0f}")
            ret = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
            st.metric("Period Return", f"{ret:.2f}%")

# ─── Tab 2: Backtesting ───
with tab2:
    st.header("Backtesting")
    col1, col2, col3 = st.columns(3)
    with col1:
        bt_ticker = st.text_input("Ticker", "005930", key="t2_ticker")
    with col2:
        bt_start = st.date_input("Start", pd.Timestamp("2024-01-01"), key="t2_start")
    with col3:
        bt_end = st.date_input("End", pd.Timestamp("2024-12-31"), key="t2_end")

    strategy_name = st.selectbox("Strategy", list(STRATEGIES.keys()))
    strat_class, default_params = STRATEGIES[strategy_name]

    st.subheader("Parameters")
    params = {}
    cols = st.columns(len(default_params))
    for i, (k, v) in enumerate(default_params.items()):
        with cols[i]:
            if isinstance(v, float):
                params[k] = st.number_input(k, value=v, step=0.1, key=f"t2_{k}")
            else:
                params[k] = st.number_input(k, value=v, step=1, key=f"t2_{k}")

    cash = st.number_input("Initial Cash", value=10_000_000, step=1_000_000, key="t2_cash")

    if st.button("Run Backtest", key="t2_btn"):
        with st.spinner("Running backtest..."):
            df = loader.get(bt_ticker, str(bt_start), str(bt_end))
            engine = BacktestEngine(cash=cash)
            engine.add_data(df, name=bt_ticker)
            engine.add_strategy(strat_class, **params)
            result = engine.run()
            eq = engine.get_equity_curve()

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Return", f"{result['return_pct']:.2f}%")
        col_b.metric("CAGR", f"{result['cagr_pct']:.2f}%")
        col_c.metric("MDD", f"{result['max_drawdown']:.2f}%")
        col_d.metric("Sharpe", f"{result['sharpe_ratio']:.2f}")

        col_e, col_f, col_g = st.columns(3)
        col_e.metric("Trades", result['total_trades'])
        col_f.metric("Win Rate", f"{result['win_rate']:.1f}%")
        col_g.metric("Final Value", f"{result['final_value']:,.0f}")

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7),
                                        gridspec_kw={'height_ratios': [3, 1]})
        ax1.plot(eq.index, eq.values, color='#2962FF')
        ax1.axhline(y=cash, color='gray', linestyle='--', alpha=0.5)
        ax1.set_title('Equity Curve')
        ax1.set_ylabel('Value')
        ax1.grid(True, alpha=0.3)

        peak = eq.cummax()
        dd = (eq - peak) / peak * 100
        ax2.fill_between(dd.index, dd.values, 0, color='#FF5252', alpha=0.4)
        ax2.set_title('Drawdown')
        ax2.set_ylabel('%')
        ax2.grid(True, alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig)

        # Kelly
        kelly = RiskManager.kelly_from_backtest(result)
        st.info(f"Kelly Recommendation: {kelly['recommendation']} "
                f"(Full: {kelly['kelly_pct']:.1f}%, Half: {kelly['adjusted_pct']:.1f}%)")

# ─── Tab 3: Strategy Comparison ───
with tab3:
    st.header("Strategy Comparison")
    col1, col2, col3 = st.columns(3)
    with col1:
        cmp_ticker = st.text_input("Ticker", "005930", key="t3_ticker")
    with col2:
        cmp_start = st.date_input("Start", pd.Timestamp("2024-01-01"), key="t3_start")
    with col3:
        cmp_end = st.date_input("End", pd.Timestamp("2024-12-31"), key="t3_end")

    selected = st.multiselect("Select Strategies", list(STRATEGIES.keys()),
                               default=list(STRATEGIES.keys())[:4])

    if st.button("Compare", key="t3_btn") and selected:
        with st.spinner("Running comparisons..."):
            df = loader.get(cmp_ticker, str(cmp_start), str(cmp_end))
            comp = StrategyComparator(df)

            for name in selected:
                cls, prm = STRATEGIES[name]
                comp.add_strategy(name, cls, **prm)

        table = comp.compare_table()
        st.dataframe(table, use_container_width=True)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8),
                                        gridspec_kw={'height_ratios': [3, 2]})
        colors = ['#2962FF', '#FF6D00', '#00C853', '#AA00FF', '#FF1744', '#00BFA5']
        for i, (name, eq) in enumerate(comp.equity_curves.items()):
            ret = comp.results[name]['return_pct']
            ax1.plot(eq.index, eq.values, label=f'{name} ({ret:+.2f}%)',
                     color=colors[i % len(colors)])
        ax1.legend(fontsize=8)
        ax1.set_title('Equity Curves')
        ax1.grid(True, alpha=0.3)

        names = list(comp.results.keys())
        returns = [comp.results[n]['return_pct'] for n in names]
        bar_colors = ['#00C853' if r >= 0 else '#FF1744' for r in returns]
        ax2.bar(names, returns, color=bar_colors, alpha=0.8)
        ax2.set_title('Returns (%)')
        ax2.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        st.pyplot(fig)

# ─── Tab 4: Portfolio ───
with tab4:
    st.header("Portfolio Analysis")

    tickers_input = st.text_input("Tickers (comma separated)", "005930, 000660", key="t4_tickers")
    col1, col2 = st.columns(2)
    with col1:
        pf_start = st.date_input("Start", pd.Timestamp("2024-01-01"), key="t4_start")
    with col2:
        pf_end = st.date_input("End", pd.Timestamp("2024-12-31"), key="t4_end")

    use_risk_parity = st.checkbox("Use Risk Parity weights", value=True)

    if st.button("Analyze Portfolio", key="t4_btn"):
        tickers = [t.strip() for t in tickers_input.split(',')]

        with st.spinner("Loading data..."):
            data = loader.fetch_multiple(tickers, str(pf_start), str(pf_end))

        if not data:
            st.error("No data loaded")
        else:
            if use_risk_parity:
                rp = RiskManager.risk_parity(data)
                weights = rp['weights']
                st.subheader("Risk Parity Allocation")
                rp_df = pd.DataFrame({
                    'Ticker': list(rp['weights'].keys()),
                    'Weight': [f"{v:.1%}" for v in rp['weights'].values()],
                    'Volatility': [f"{v:.1%}" for v in rp['volatilities'].values()],
                    'Risk Contribution': [f"{v:.1f}%" for v in rp['risk_contributions'].values()],
                })
                st.dataframe(rp_df, use_container_width=True)
            else:
                weights = {t: 1.0 / len(tickers) for t in tickers}

            st.subheader("Price Charts")
            fig, ax = plt.subplots(figsize=(12, 5))
            for ticker_name, df in data.items():
                normalized = df['Close'] / df['Close'].iloc[0] * 100
                ax.plot(normalized.index, normalized.values,
                        label=f"{ticker_name} ({weights.get(ticker_name, 0):.0%})")
            ax.set_title('Normalized Price (Base=100)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
