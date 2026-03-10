import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.data_loader import DataLoader
from src.analyzer import Analyzer
from src.risk_manager import RiskManager
from backtest.engine import BacktestEngine
from backtest.comparator import StrategyComparator
from backtest.optimizer import StrategyOptimizer
from src.market_scanner import MarketScanner
from strategies.moving_average_cross import MovingAverageCross
from strategies.bollinger_band import BollingerBand
from strategies.rsi import RsiStrategy
from strategies.macd import MacdStrategy
from strategies.sma_cross import SmaCross
from strategies.momentum import Momentum

STRATEGIES = {
    'MA Cross': {'class': MovingAverageCross, 'params': {'short_period': 20, 'long_period': 60}},
    'SMA Cross': {'class': SmaCross, 'params': {'short_period': 20, 'long_period': 60}},
    'Bollinger Band': {'class': BollingerBand, 'params': {'period': 20, 'devfactor': 2.0}},
    'RSI': {'class': RsiStrategy, 'params': {'period': 14, 'oversold': 30, 'overbought': 70}},
    'MACD': {'class': MacdStrategy, 'params': {'fast': 12, 'slow': 26, 'signal': 9}},
    'Momentum': {'class': Momentum, 'params': {'period': 20, 'threshold': 0.0}},
}

st.set_page_config(page_title="Quant Trading Platform", layout="wide")
st.title("Quant Trading Platform")

loader = DataLoader(cache_days=1)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Stock Analysis", "Backtesting", "Strategy Comparison",
    "Portfolio", "Optimizer", "Risk Manager", "Signal Scanner"
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

    show_bb = st.checkbox("Bollinger Bands (20, 2)", value=False, key="t1_bb")

    if st.button("Load & Analyze", key="t1_btn"):
        with st.spinner("Fetching data..."):
            df = loader.get(ticker, str(start), str(end))

        st.success(f"Loaded {len(df)} rows")

        # Interactive candlestick chart with volume
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            vertical_spacing=0.03,
                            row_heights=[0.75, 0.25],
                            subplot_titles=[f'{ticker} Candlestick Chart', 'Volume'])

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'], name='Price',
            increasing_line_color='#FF3B3B', decreasing_line_color='#2962FF',
            increasing_fillcolor='#FF3B3B', decreasing_fillcolor='#2962FF',
        ), row=1, col=1)

        # SMA overlays
        sma_colors = ['#FF6D00', '#00C853', '#AA00FF', '#00BFA5', '#FF1744', '#795548']
        for i, p in enumerate(sma_options):
            sma = df['Close'].rolling(p).mean()
            fig.add_trace(go.Scatter(
                x=df.index, y=sma, name=f'SMA {p}',
                line=dict(width=1.2, color=sma_colors[i % len(sma_colors)]),
            ), row=1, col=1)

        # Bollinger Bands
        if show_bb:
            bb_mid = df['Close'].rolling(20).mean()
            bb_std = df['Close'].rolling(20).std()
            bb_upper = bb_mid + 2 * bb_std
            bb_lower = bb_mid - 2 * bb_std
            fig.add_trace(go.Scatter(
                x=df.index, y=bb_upper, name='BB Upper',
                line=dict(width=0.8, color='rgba(150,150,150,0.5)'),
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=bb_lower, name='BB Lower',
                line=dict(width=0.8, color='rgba(150,150,150,0.5)'),
                fill='tonexty', fillcolor='rgba(150,150,150,0.08)',
            ), row=1, col=1)

        # Volume bars (colored by price direction)
        colors = ['#FF3B3B' if c >= o else '#2962FF'
                  for c, o in zip(df['Close'], df['Open'])]
        fig.add_trace(go.Bar(
            x=df.index, y=df['Volume'], name='Volume',
            marker_color=colors, opacity=0.6,
        ), row=2, col=1)

        fig.update_layout(
            height=650,
            xaxis_rangeslider_visible=False,
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
            margin=dict(l=50, r=20, t=40, b=20),
        )
        fig.update_xaxes(type='category', nticks=20, row=1, col=1)
        fig.update_xaxes(type='category', nticks=20, row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)

        # Metrics
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("Latest Close", f"{df['Close'].iloc[-1]:,.0f}")
        with col_b:
            st.metric("Period High", f"{df['High'].max():,.0f}")
        with col_c:
            st.metric("Period Low", f"{df['Low'].min():,.0f}")
        with col_d:
            ret = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
            st.metric("Period Return", f"{ret:.2f}%")

        # Data table
        st.subheader("Recent Data")
        st.dataframe(df.tail(10), use_container_width=True)

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
    strat_info = STRATEGIES[strategy_name]

    st.subheader("Parameters")
    params = {}
    cols = st.columns(len(strat_info['params']))
    for i, (k, v) in enumerate(strat_info['params'].items()):
        with cols[i]:
            if isinstance(v, float):
                params[k] = st.number_input(k, value=v, step=0.1, key=f"t2_{k}")
            else:
                params[k] = st.number_input(k, value=v, step=1, key=f"t2_{k}")

    cash = st.number_input("Initial Cash", value=10_000_000, step=1_000_000, key="t2_cash")
    commission = st.number_input("Commission (%)", value=0.015, step=0.005,
                                  format="%.3f", key="t2_comm")

    if st.button("Run Backtest", key="t2_btn"):
        with st.spinner("Running backtest..."):
            df = loader.get(bt_ticker, str(bt_start), str(bt_end))
            engine = BacktestEngine(cash=cash, commission=commission / 100)
            engine.add_data(df, name=bt_ticker)
            engine.add_strategy(strat_info['class'], **params)
            result = engine.run()
            eq = engine.get_equity_curve()

        # Metrics
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Return", f"{result['return_pct']:.2f}%")
        col_b.metric("CAGR", f"{result['cagr_pct']:.2f}%")
        col_c.metric("MDD", f"{result['max_drawdown']:.2f}%")
        col_d.metric("Sharpe", f"{result['sharpe_ratio']:.2f}")

        col_e, col_f, col_g, col_h = st.columns(4)
        col_e.metric("Trades", result['total_trades'])
        col_f.metric("Win Rate", f"{result['win_rate']:.1f}%")
        col_g.metric("Final Value", f"{result['final_value']:,.0f}")
        col_h.metric("Period", f"{result['period_years']}y")

        # Equity + Drawdown
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

        # Kelly recommendation
        kelly = RiskManager.kelly_from_backtest(result)
        st.info(f"Kelly: {kelly['recommendation']} "
                f"(Full: {kelly['kelly_pct']:.1f}%, Half: {kelly['adjusted_pct']:.1f}%)")

        # Trade log
        trade_log = engine.get_trade_log()
        if not trade_log.empty:
            st.subheader("Trade Log")
            st.dataframe(trade_log, use_container_width=True)

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
                info = STRATEGIES[name]
                comp.add_strategy(name, info['class'], **info['params'])

        table = comp.compare_table()
        st.dataframe(table, use_container_width=True)

        # Ranking (from compare_table which is already sorted by return)
        st.subheader("Ranking")
        for _, row in table.iterrows():
            st.write(f"**#{_}** {row['Strategy']} — Return: {row['Return %']:.2f}%, "
                     f"Sharpe: {row['Sharpe']:.2f}, MDD: {row['MDD %']:.2f}%")

        # Charts
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
        plt.xticks(rotation=15)
        plt.tight_layout()
        st.pyplot(fig)

# ─── Tab 4: Portfolio ───
with tab4:
    st.header("Portfolio Analysis")

    tickers_input = st.text_input("Tickers (comma separated)", "005930, 000660, 035720",
                                   key="t4_tickers")
    col1, col2 = st.columns(2)
    with col1:
        pf_start = st.date_input("Start", pd.Timestamp("2024-01-01"), key="t4_start")
    with col2:
        pf_end = st.date_input("End", pd.Timestamp("2024-12-31"), key="t4_end")

    lookback = st.slider("Risk Parity Lookback (days)", 20, 120, 60, key="t4_lb")
    use_risk_parity = st.checkbox("Use Risk Parity weights", value=True)

    if st.button("Analyze Portfolio", key="t4_btn"):
        tickers = [t.strip() for t in tickers_input.split(',')]

        with st.spinner("Loading data..."):
            data = loader.fetch_multiple(tickers, str(pf_start), str(pf_end))

        if not data:
            st.error("No data loaded")
        else:
            if use_risk_parity:
                rp = RiskManager.risk_parity(data, lookback=lookback)
                weights = rp['weights']
                st.subheader("Risk Parity Allocation")
                rp_df = pd.DataFrame({
                    'Ticker': list(rp['weights'].keys()),
                    'Weight': [f"{v:.1%}" for v in rp['weights'].values()],
                    'Volatility': [f"{v:.1%}" for v in rp['volatilities'].values()],
                    'Risk Contribution': [f"{v:.1f}%" for v in rp['risk_contributions'].values()],
                })
                st.dataframe(rp_df, use_container_width=True)

                # Pie chart
                fig_pie, ax_pie = plt.subplots(figsize=(6, 6))
                ax_pie.pie(list(weights.values()), labels=list(weights.keys()),
                          autopct='%1.1f%%', startangle=90)
                ax_pie.set_title('Portfolio Weights')
                st.pyplot(fig_pie)
            else:
                weights = {t: 1.0 / len(tickers) for t in tickers}

            st.subheader("Normalized Price Charts")
            fig, ax = plt.subplots(figsize=(12, 5))
            for ticker_name, df in data.items():
                normalized = df['Close'] / df['Close'].iloc[0] * 100
                ax.plot(normalized.index, normalized.values,
                        label=f"{ticker_name} ({weights.get(ticker_name, 0):.0%})")
            ax.set_title('Normalized Price (Base=100)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)

            # Correlation matrix
            st.subheader("Correlation Matrix")
            closes = pd.DataFrame({t: d['Close'] for t, d in data.items()})
            corr = closes.pct_change().dropna().corr()
            fig_corr, ax_corr = plt.subplots(figsize=(6, 5))
            im = ax_corr.imshow(corr.values, cmap='RdYlGn', vmin=-1, vmax=1, aspect='auto')
            ax_corr.set_xticks(range(len(corr)))
            ax_corr.set_xticklabels(corr.columns, rotation=45)
            ax_corr.set_yticks(range(len(corr)))
            ax_corr.set_yticklabels(corr.index)
            for i in range(len(corr)):
                for j in range(len(corr)):
                    ax_corr.text(j, i, f'{corr.values[i, j]:.2f}',
                                ha='center', va='center', fontsize=10)
            plt.colorbar(im, ax=ax_corr)
            ax_corr.set_title('Return Correlation')
            plt.tight_layout()
            st.pyplot(fig_corr)

# ─── Tab 5: Optimizer ───
with tab5:
    st.header("Strategy Optimizer")

    col1, col2, col3 = st.columns(3)
    with col1:
        opt_ticker = st.text_input("Ticker", "005930", key="t5_ticker")
    with col2:
        opt_start = st.date_input("Start", pd.Timestamp("2023-01-01"), key="t5_start")
    with col3:
        opt_end = st.date_input("End", pd.Timestamp("2024-12-31"), key="t5_end")

    opt_strategy = st.selectbox("Strategy", list(STRATEGIES.keys()), key="t5_strat")
    opt_info = STRATEGIES[opt_strategy]

    st.subheader("Parameter Ranges (comma separated values)")
    param_grid = {}
    for k, v in opt_info['params'].items():
        if isinstance(v, float):
            default_range = f"{v * 0.5:.1f}, {v:.1f}, {v * 1.5:.1f}"
            raw = st.text_input(f"{k}", default_range, key=f"t5_rng_{k}")
            param_grid[k] = [float(x.strip()) for x in raw.split(',')]
        else:
            base = max(v, 5)
            default_range = f"{max(base - 10, 2)}, {base}, {base + 10}"
            raw = st.text_input(f"{k}", default_range, key=f"t5_rng_{k}")
            param_grid[k] = [int(x.strip()) for x in raw.split(',')]

    total_combos = 1
    for vals in param_grid.values():
        total_combos *= len(vals)
    st.caption(f"Total combinations: {total_combos}")

    opt_sort = st.selectbox("Sort by", ['return_pct', 'sharpe_ratio', 'max_drawdown'],
                             key="t5_sort")

    col_a, col_b = st.columns(2)
    with col_a:
        run_grid = st.button("Grid Search", key="t5_grid")
    with col_b:
        run_wf = st.button("Walk-Forward", key="t5_wf")

    if run_grid:
        with st.spinner(f"Running grid search ({total_combos} combinations)..."):
            df = loader.get(opt_ticker, str(opt_start), str(opt_end))
            optimizer = StrategyOptimizer(df, opt_info['class'])
            top = optimizer.grid_search(param_grid, sort_by=opt_sort, top_n=10)

        st.subheader("Top Results")
        display_cols = ['params', 'return_pct', 'cagr_pct', 'sharpe_ratio',
                        'max_drawdown', 'total_trades', 'win_rate']
        st.dataframe(top[display_cols], use_container_width=True)

        # Heatmap (if exactly 2 parameters)
        param_keys = list(param_grid.keys())
        if len(param_keys) >= 2 and optimizer.results:
            st.subheader("Parameter Heatmap")
            px, py = param_keys[0], param_keys[1]
            heatmap_data = []
            for r in optimizer.results:
                heatmap_data.append({
                    px: r['params'][px],
                    py: r['params'][py],
                    'return_pct': r['return_pct'],
                })
            hdf = pd.DataFrame(heatmap_data)
            pivot = hdf.pivot_table(index=py, columns=px, values='return_pct',
                                     aggfunc='mean')

            fig, ax = plt.subplots(figsize=(10, 6))
            im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto')
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns)
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index)
            ax.set_xlabel(px)
            ax.set_ylabel(py)
            ax.set_title(f'Return (%) Heatmap: {px} vs {py}')
            for i in range(len(pivot.index)):
                for j in range(len(pivot.columns)):
                    val = pivot.values[i, j]
                    if not np.isnan(val):
                        ax.text(j, i, f'{val:.1f}', ha='center', va='center', fontsize=9)
            plt.colorbar(im, ax=ax)
            plt.tight_layout()
            st.pyplot(fig)

    if run_wf:
        with st.spinner("Running walk-forward analysis..."):
            df = loader.get(opt_ticker, str(opt_start), str(opt_end))
            optimizer = StrategyOptimizer(df, opt_info['class'])
            wf = optimizer.walk_forward(param_grid, in_sample_ratio=0.7, sort_by=opt_sort)

        if wf:
            st.subheader("Walk-Forward Results")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Best Params", str(wf['best_params']))
            col_b.metric("Degradation", f"{wf['degradation_pct']:.1f}%")
            col_c.metric("Verdict", wf['verdict'])

            is_ret = wf['in_sample'].get('return_pct', 0)
            oos_ret = wf['out_of_sample'].get('return_pct', 0)

            fig, ax = plt.subplots(figsize=(8, 4))
            bars = ax.bar(['In-Sample', 'Out-of-Sample'], [is_ret, oos_ret],
                         color=['#2962FF', '#FF6D00'], alpha=0.8)
            ax.set_title('In-Sample vs Out-of-Sample Return')
            ax.set_ylabel('Return (%)')
            ax.grid(True, alpha=0.3, axis='y')
            for bar, val in zip(bars, [is_ret, oos_ret]):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                       f'{val:.2f}%', ha='center', va='bottom')
            plt.tight_layout()
            st.pyplot(fig)

            st.write("**In-Sample:**")
            st.json({k: v for k, v in wf['in_sample'].items() if k != 'params'})
            st.write("**Out-of-Sample:**")
            st.json({k: v for k, v in wf['out_of_sample'].items() if k != 'params'})
        else:
            st.error("Walk-forward analysis failed")

# ─── Tab 6: Risk Manager ───
with tab6:
    st.header("Risk Manager")

    sub1, sub2 = st.tabs(["Kelly Criterion", "Position Sizing"])

    with sub1:
        st.subheader("Kelly Criterion Calculator")

        mode = st.radio("Input Mode", ["Manual", "From Backtest"], key="t6_mode")

        if mode == "Manual":
            col1, col2, col3 = st.columns(3)
            with col1:
                win_rate = st.slider("Win Rate (%)", 1, 99, 55, key="t6_wr")
            with col2:
                pl_ratio = st.number_input("P/L Ratio", value=1.5, step=0.1,
                                            min_value=0.1, key="t6_pl")
            with col3:
                fraction = st.selectbox("Kelly Fraction",
                                         [("Full", 1.0), ("Half", 0.5), ("Quarter", 0.25)],
                                         format_func=lambda x: x[0], key="t6_frac")

            if st.button("Calculate Kelly", key="t6_calc"):
                result = RiskManager.kelly_criterion(win_rate / 100, pl_ratio,
                                                      fraction=fraction[1])
                col_a, col_b = st.columns(2)
                col_a.metric("Full Kelly %", f"{result['kelly_pct']:.2f}%")
                col_b.metric(f"Adjusted ({fraction[0]})", f"{result['adjusted_pct']:.2f}%")
                if result['kelly_pct'] > 0:
                    st.success(result['recommendation'])
                else:
                    st.error(result['recommendation'])

                # Visual
                fig, ax = plt.subplots(figsize=(8, 3))
                kelly_val = result['kelly_pct']
                adj_val = result['adjusted_pct']
                ax.barh(['Full Kelly', f'{fraction[0]} Kelly'],
                       [max(kelly_val, 0), max(adj_val, 0)],
                       color=['#FF6D00', '#2962FF'], alpha=0.8)
                ax.set_xlabel('Portfolio Allocation (%)')
                ax.set_title('Kelly Criterion Recommendation')
                ax.axvline(x=25, color='red', linestyle='--', alpha=0.5, label='Danger Zone')
                ax.legend()
                ax.grid(True, alpha=0.3, axis='x')
                plt.tight_layout()
                st.pyplot(fig)

        else:
            st.write("Run a backtest in Tab 2 first, then enter results here:")
            col1, col2, col3 = st.columns(3)
            with col1:
                total_trades = st.number_input("Total Trades", value=20, min_value=1,
                                                key="t6_tt")
            with col2:
                winning_trades = st.number_input("Winning Trades", value=11, min_value=0,
                                                  key="t6_wt")
            with col3:
                return_pct = st.number_input("Return %", value=5.0, step=0.5, key="t6_ret")

            if st.button("Calculate", key="t6_calc2"):
                mock_result = {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'return_pct': return_pct,
                }
                kelly = RiskManager.kelly_from_backtest(mock_result)
                col_a, col_b = st.columns(2)
                col_a.metric("Full Kelly %", f"{kelly['kelly_pct']:.2f}%")
                col_b.metric("Half Kelly %", f"{kelly['adjusted_pct']:.2f}%")
                st.info(kelly['recommendation'])

    with sub2:
        st.subheader("Position Sizing Calculator")

        col1, col2 = st.columns(2)
        with col1:
            total_capital = st.number_input("Total Capital", value=50_000_000,
                                             step=1_000_000, key="t6_cap")
            risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 2.0, 0.5, key="t6_risk")
        with col2:
            entry_price = st.number_input("Entry Price", value=70000, step=1000,
                                           key="t6_entry")
            stop_loss = st.number_input("Stop Loss Price", value=65000, step=1000,
                                         key="t6_sl")

        if st.button("Calculate Position", key="t6_pos"):
            if entry_price == stop_loss:
                st.error("Entry and stop loss must differ")
            else:
                pos = RiskManager.position_size(total_capital, risk_pct / 100,
                                                 entry_price, stop_loss)
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Shares", f"{pos['shares']:,}")
                col_b.metric("Position Value", f"{pos['position_value']:,.0f}")
                col_c.metric("Portfolio %", f"{pos['position_pct']:.1f}%")

                st.write(f"**Risk Amount:** {pos['risk_amount']:,.0f} KRW")
                st.write(f"**Risk per Share:** {pos['risk_per_share']:,.0f} KRW")

                # Visual
                fig, ax = plt.subplots(figsize=(8, 3))
                ax.barh(['Position', 'Cash'],
                       [pos['position_value'], total_capital - pos['position_value']],
                       color=['#2962FF', '#E0E0E0'], alpha=0.8)
                ax.set_xlabel('KRW')
                ax.set_title(f'Capital Allocation ({pos["position_pct"]:.1f}% invested)')
                plt.tight_layout()
                st.pyplot(fig)

# ─── Tab 7: Signal Scanner ───
with tab7:
    st.header("Signal Scanner")

    scan_mode = st.radio("Scan Mode",
                          ["Individual Tickers", "Market Cap Filter"],
                          horizontal=True, key="t7_mode")

    if scan_mode == "Individual Tickers":
        scan_tickers_input = st.text_input(
            "Tickers (comma separated)",
            "005930, 000660, 035720, 051910", key="t7_tickers")
    else:
        st.subheader("Market Cap Filter")
        col1, col2, col3 = st.columns(3)
        with col1:
            market_sel = st.selectbox("Market", ['ALL', 'KOSPI', 'KOSDAQ'], key="t7_mkt")
        with col2:
            min_cap = st.number_input("Min Market Cap (조원)", value=5, min_value=0,
                                       step=1, key="t7_min")
        with col3:
            max_cap = st.number_input("Max Market Cap (조원, 0=no limit)",
                                       value=0, min_value=0, step=1, key="t7_max")

        # Preview filtered stocks
        min_억 = min_cap * 10000  # 조 → 억
        max_억 = max_cap * 10000 if max_cap > 0 else None
        filtered_stocks = MarketScanner.filter_by_market_cap(min_억, max_억, market_sel)
        st.caption(f"Found {len(filtered_stocks)} stocks matching criteria")

        if not filtered_stocks.empty:
            preview_df = filtered_stocks[['ticker', 'name', 'market_cap_조']].copy()
            preview_df.columns = ['Ticker', 'Name', 'Market Cap (조)']
            st.dataframe(preview_df, use_container_width=True, height=200)

    scan_start = st.date_input("Lookback Start", pd.Timestamp("2024-06-01"), key="t7_start")

    scan_strategies = st.multiselect("Strategies to Check", list(STRATEGIES.keys()),
                                      default=['MA Cross', 'RSI', 'MACD'], key="t7_strats")

    max_tickers = st.slider("Max Tickers to Scan", 5, 60, 20, key="t7_max_tk")

    if st.button("Scan Signals", key="t7_btn") and scan_strategies:
        # Determine ticker list
        if scan_mode == "Individual Tickers":
            tickers = [t.strip() for t in scan_tickers_input.split(',')]
        else:
            tickers = filtered_stocks['ticker'].tolist()[:max_tickers]

        if not tickers:
            st.error("No tickers to scan")
        else:
            from src.scheduler import SignalChecker
            checker = SignalChecker(loader)

            results = []
            progress = st.progress(0)
            status_text = st.empty()
            total = len(tickers) * len(scan_strategies)
            done = 0

            # Get names for display
            stock_list = MarketScanner.get_stock_list()
            name_map = dict(zip(stock_list['ticker'], stock_list['name']))

            for tk in tickers:
                tk_name = name_map.get(tk, tk)
                for sname in scan_strategies:
                    info = STRATEGIES[sname]
                    status_text.text(f"Scanning {tk_name} ({tk}) / {sname}...")
                    try:
                        sig = checker.check_signal(tk, info['class'], str(scan_start),
                                                   **info['params'])
                        sig['name'] = tk_name
                        results.append(sig)
                    except Exception as e:
                        results.append({
                            'ticker': tk, 'name': tk_name,
                            'signal': 'ERROR', 'strategy': sname,
                        })
                    done += 1
                    progress.progress(done / total)

            progress.empty()
            status_text.empty()

            # Results table
            df_results = pd.DataFrame(results)
            display_cols = [c for c in ['name', 'ticker', 'signal', 'strategy'] if c in df_results.columns]

            def signal_style(val):
                if val == 'BUY':
                    return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold'
                elif val == 'SELL':
                    return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold'
                elif val == 'ERROR':
                    return 'background-color: #FFF9C4; color: #F57F17'
                return ''

            styled = df_results[display_cols].style.map(signal_style, subset=['signal'])
            st.dataframe(styled, use_container_width=True)

            # Summary
            buy_signals = [r for r in results if r['signal'] == 'BUY']
            sell_signals = [r for r in results if r['signal'] == 'SELL']
            hold_count = len([r for r in results if r['signal'] == 'HOLD'])
            err_count = len([r for r in results if r['signal'] == 'ERROR'])

            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("BUY", len(buy_signals))
            col_b.metric("SELL", len(sell_signals))
            col_c.metric("HOLD", hold_count)
            col_d.metric("ERROR", err_count)

            # Actionable signals detail
            if buy_signals:
                st.success("**BUY Signals:**")
                for b in buy_signals:
                    st.write(f"  - **{b.get('name', '')}** ({b['ticker']}) — {b.get('strategy', '')}")
            if sell_signals:
                st.warning("**SELL Signals:**")
                for s in sell_signals:
                    st.write(f"  - **{s.get('name', '')}** ({s['ticker']}) — {s.get('strategy', '')}")

            if not buy_signals and not sell_signals:
                st.info("No actionable signals found. All positions HOLD.")

# ─── Sidebar Info ───
with st.sidebar:
    st.header("About")
    st.write("Personal Quant Trading Platform")
    st.divider()
    st.subheader("Strategies")
    for name in STRATEGIES:
        st.write(f"- {name}")
    st.divider()
    st.subheader("Data Source")
    st.write("FinanceDataReader (KRX, Yahoo)")
    st.caption("Index Presets: KOSPI, KOSDAQ, S&P500, NASDAQ, DOW, NIKKEI")
    st.divider()
    st.subheader("Quick Guide")
    st.markdown("""
    1. **Stock Analysis** - View price/volume charts
    2. **Backtesting** - Test strategies with parameters
    3. **Comparison** - Compare multiple strategies
    4. **Portfolio** - Risk parity allocation
    5. **Optimizer** - Grid search & walk-forward
    6. **Risk Manager** - Kelly criterion & sizing
    7. **Signal Scanner** - Live signal detection
    """)
