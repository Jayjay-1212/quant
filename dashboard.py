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
    'MA 크로스 (이평선 교차)': {'class': MovingAverageCross, 'params': {'short_period': 20, 'long_period': 60},
        'desc': '단기/장기 이동평균선이 교차할 때 매매. 골든크로스=매수, 데드크로스=매도'},
    'SMA 크로스': {'class': SmaCross, 'params': {'short_period': 20, 'long_period': 60},
        'desc': '단순 이동평균선 교차 전략'},
    '볼린저 밴드': {'class': BollingerBand, 'params': {'period': 20, 'devfactor': 2.0},
        'desc': '하단 밴드 이탈 시 매수, 상단 밴드 돌파 시 매도 (평균회귀)'},
    'RSI (과매수/과매도)': {'class': RsiStrategy, 'params': {'period': 14, 'oversold': 30, 'overbought': 70},
        'desc': 'RSI 30 이하 매수, 70 이상 매도. 과매도/과매수 반전 노림'},
    'MACD': {'class': MacdStrategy, 'params': {'fast': 12, 'slow': 26, 'signal': 9},
        'desc': 'MACD선이 시그널선을 상향 돌파하면 매수, 하향 돌파하면 매도'},
    '모멘텀': {'class': Momentum, 'params': {'period': 20, 'threshold': 0.0},
        'desc': '일정 기간 수익률이 기준값 이상이면 매수 (추세 추종)'},
}

st.set_page_config(page_title="퀀트 트레이딩", layout="wide", page_icon="📈")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0D1B2A 0%, #1B2838 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid #2962FF33;
    }
    .main-header h1 { color: #FAFAFA; margin: 0; font-size: 1.8rem; }
    .main-header p { color: #90A4AE; margin: 0.3rem 0 0 0; font-size: 0.9rem; }
    [data-testid="stMetric"] {
        background: #1A1D2366; border: 1px solid #2962FF22;
        border-radius: 8px; padding: 12px 16px;
    }
    [data-testid="stMetricValue"] { font-size: 1.3rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 20px; border-radius: 8px 8px 0 0; }
    .stButton > button {
        border-radius: 8px; font-weight: 600;
        border: 1px solid #2962FF; transition: all 0.2s;
    }
    .stButton > button:hover {
        border-color: #448AFF; box-shadow: 0 0 12px rgba(41,98,255,0.3);
    }
    .guide-box {
        background: #1A1D23; border: 1px solid #333; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 16px; font-size: 0.85rem; color: #B0BEC5;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>퀀트 트레이딩 플랫폼</h1>
    <p>종목 분석, 백테스트, 전략 비교, 포트폴리오 최적화, 시장 스캐너</p>
</div>
""", unsafe_allow_html=True)

loader = DataLoader(cache_days=1)

PLOTLY_LAYOUT = dict(
    template='plotly_dark',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#FAFAFA'),
    xaxis=dict(gridcolor='#333', zerolinecolor='#555'),
    yaxis=dict(gridcolor='#333', zerolinecolor='#555'),
)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 종목 분석", "🔬 백테스트", "⚔️ 전략 비교",
    "💼 포트폴리오", "🎯 최적화", "🛡️ 리스크", "📡 신호 스캐너"
])

# ─── Tab 1: 종목 분석 ───
with tab1:
    st.markdown('<div class="guide-box">'
                '💡 <b>사용법:</b> 종목코드 입력 → 기간 설정 → "차트 보기" 클릭<br>'
                '예시: 005930(삼성전자), 000660(SK하이닉스), 035420(네이버), 035720(카카오)'
                '</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("종목코드", "005930", key="t1_ticker",
                                help="6자리 종목코드 입력 (예: 005930 = 삼성전자)")
    with col2:
        start = st.date_input("시작일", pd.Timestamp("2024-01-01"), key="t1_start")
    with col3:
        end = st.date_input("종료일", pd.Timestamp.now(), key="t1_end")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        sma_options = st.multiselect("이동평균선 (일)", [5, 10, 20, 40, 60, 120], default=[20, 60],
                                      help="차트에 표시할 이동평균선 기간을 선택하세요")
    with col_opt2:
        show_bb = st.checkbox("볼린저 밴드 표시", value=False, key="t1_bb",
                               help="20일 볼린저 밴드 (상단/하단) 표시")

    if st.button("📊 차트 보기", key="t1_btn", use_container_width=True):
        with st.spinner("데이터 불러오는 중..."):
            df = loader.get(ticker, str(start), str(end))

        st.success(f"✅ {len(df)}개 데이터 로드 완료")

        # Candlestick chart
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            vertical_spacing=0.03,
                            row_heights=[0.75, 0.25],
                            subplot_titles=[f'{ticker} 봉차트', '거래량'])

        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'], name='가격',
            increasing_line_color='#FF3B3B', decreasing_line_color='#2962FF',
            increasing_fillcolor='#FF3B3B', decreasing_fillcolor='#2962FF',
        ), row=1, col=1)

        sma_colors = ['#FF6D00', '#00C853', '#AA00FF', '#00BFA5', '#FF1744', '#795548']
        for i, p in enumerate(sma_options):
            sma = df['Close'].rolling(p).mean()
            fig.add_trace(go.Scatter(
                x=df.index, y=sma, name=f'{p}일 이평선',
                line=dict(width=1.2, color=sma_colors[i % len(sma_colors)]),
            ), row=1, col=1)

        if show_bb:
            bb_mid = df['Close'].rolling(20).mean()
            bb_std = df['Close'].rolling(20).std()
            fig.add_trace(go.Scatter(
                x=df.index, y=bb_mid + 2 * bb_std, name='BB 상단',
                line=dict(width=0.8, color='rgba(150,150,150,0.5)'),
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=bb_mid - 2 * bb_std, name='BB 하단',
                line=dict(width=0.8, color='rgba(150,150,150,0.5)'),
                fill='tonexty', fillcolor='rgba(150,150,150,0.08)',
            ), row=1, col=1)

        vol_colors = ['#FF3B3B' if c >= o else '#2962FF'
                      for c, o in zip(df['Close'], df['Open'])]
        fig.add_trace(go.Bar(
            x=df.index, y=df['Volume'], name='거래량',
            marker_color=vol_colors, opacity=0.6,
        ), row=2, col=1)

        fig.update_layout(
            **PLOTLY_LAYOUT, height=650,
            xaxis_rangeslider_visible=False, showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
            margin=dict(l=50, r=20, t=40, b=20),
        )
        fig.update_xaxes(type='category', nticks=20, row=1, col=1)
        fig.update_xaxes(type='category', nticks=20, row=2, col=1)
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("현재가", f"{df['Close'].iloc[-1]:,.0f}원")
        col_b.metric("기간 최고가", f"{df['High'].max():,.0f}원")
        col_c.metric("기간 최저가", f"{df['Low'].min():,.0f}원")
        ret = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
        col_d.metric("기간 수익률", f"{ret:.2f}%")

        st.subheader("최근 10일 데이터")
        st.dataframe(df.tail(10), use_container_width=True)

# ─── Tab 2: 백테스트 ───
with tab2:
    st.markdown('<div class="guide-box">'
                '💡 <b>사용법:</b> 종목코드 + 전략 선택 + 파라미터 조정 → "백테스트 실행" 클릭<br>'
                '과거 데이터로 전략을 시뮬레이션하여 수익률, 승률, 최대 낙폭 등을 확인합니다.'
                '</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        bt_ticker = st.text_input("종목코드", "005930", key="t2_ticker")
    with col2:
        bt_start = st.date_input("시작일", pd.Timestamp("2024-01-01"), key="t2_start")
    with col3:
        bt_end = st.date_input("종료일", pd.Timestamp.now(), key="t2_end")

    strategy_name = st.selectbox("전략 선택", list(STRATEGIES.keys()),
                                  help="적용할 매매 전략을 선택하세요")
    strat_info = STRATEGIES[strategy_name]
    st.caption(f"ℹ️ {strat_info['desc']}")

    st.subheader("파라미터 설정")
    params = {}
    cols = st.columns(len(strat_info['params']))
    for i, (k, v) in enumerate(strat_info['params'].items()):
        with cols[i]:
            label_map = {
                'short_period': '단기 이평 (일)', 'long_period': '장기 이평 (일)',
                'period': '기간 (일)', 'devfactor': '표준편차 배수',
                'oversold': '과매도 기준', 'overbought': '과매수 기준',
                'fast': '빠른선 (일)', 'slow': '느린선 (일)', 'signal': '시그널 (일)',
                'threshold': '기준값',
            }
            label = label_map.get(k, k)
            if isinstance(v, float):
                params[k] = st.number_input(label, value=v, step=0.1, key=f"t2_{k}")
            else:
                params[k] = st.number_input(label, value=v, step=1, key=f"t2_{k}")

    col_cash, col_comm = st.columns(2)
    with col_cash:
        cash = st.number_input("초기 자본금 (원)", value=10_000_000, step=1_000_000, key="t2_cash",
                                help="백테스트 시작 시 투자 금액")
    with col_comm:
        commission = st.number_input("수수료 (%)", value=0.015, step=0.005,
                                      format="%.3f", key="t2_comm",
                                      help="매매 시 수수료율 (증권사 기본 0.015%)")

    if st.button("🔬 백테스트 실행", key="t2_btn", use_container_width=True):
        with st.spinner("백테스트 실행 중..."):
            df = loader.get(bt_ticker, str(bt_start), str(bt_end))
            engine = BacktestEngine(cash=cash, commission=commission / 100)
            engine.add_data(df, name=bt_ticker)
            engine.add_strategy(strat_info['class'], **params)
            result = engine.run()
            eq = engine.get_equity_curve()

        st.subheader("📈 성과 요약")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("총 수익률", f"{result['return_pct']:.2f}%")
        col_b.metric("연평균 수익률 (CAGR)", f"{result['cagr_pct']:.2f}%")
        col_c.metric("최대 낙폭 (MDD)", f"{result['max_drawdown']:.2f}%")
        col_d.metric("샤프 비율", f"{result['sharpe_ratio']:.2f}")

        col_e, col_f, col_g, col_h = st.columns(4)
        col_e.metric("총 거래 횟수", result['total_trades'])
        col_f.metric("승률", f"{result['win_rate']:.1f}%")
        col_g.metric("최종 자산", f"{result['final_value']:,.0f}원")
        col_h.metric("투자 기간", f"{result['period_years']}년")

        # Equity + Drawdown
        peak = eq.cummax()
        dd = (eq - peak) / peak * 100

        fig_bt = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                vertical_spacing=0.05, row_heights=[0.7, 0.3],
                                subplot_titles=['자산 변화 (에쿼티 커브)', '낙폭 (Drawdown)'])

        fig_bt.add_trace(go.Scatter(
            x=eq.index, y=eq.values, name='포트폴리오',
            line=dict(color='#2962FF', width=2),
            fill='tozeroy', fillcolor='rgba(41,98,255,0.08)',
        ), row=1, col=1)
        fig_bt.add_trace(go.Scatter(
            x=eq.index, y=[cash] * len(eq), name='초기 자본',
            line=dict(color='gray', width=1, dash='dash'),
        ), row=1, col=1)
        fig_bt.add_trace(go.Scatter(
            x=dd.index, y=dd.values, name='낙폭',
            line=dict(color='#FF5252', width=1),
            fill='tozeroy', fillcolor='rgba(255,82,82,0.3)',
        ), row=2, col=1)

        fig_bt.update_layout(
            **PLOTLY_LAYOUT, height=500, showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
            margin=dict(l=50, r=20, t=30, b=20),
        )
        st.plotly_chart(fig_bt, use_container_width=True)

        # Kelly
        kelly = RiskManager.kelly_from_backtest(result)
        if kelly['kelly_pct'] > 0:
            st.success(f"💰 켈리 추천: {kelly['recommendation']} "
                       f"(풀 켈리: {kelly['kelly_pct']:.1f}%, 하프 켈리: {kelly['adjusted_pct']:.1f}%)")
        else:
            st.error(f"⚠️ 켈리 추천: {kelly['recommendation']}")

        # Trade log
        trade_log = engine.get_trade_log()
        if not trade_log.empty:
            st.subheader("📋 매매 내역")
            st.dataframe(trade_log, use_container_width=True)

# ─── Tab 3: 전략 비교 ───
with tab3:
    st.markdown('<div class="guide-box">'
                '💡 <b>사용법:</b> 종목코드 입력 → 비교할 전략 선택 → "비교 실행" 클릭<br>'
                '같은 종목에 여러 전략을 동시 적용하여 어떤 전략이 가장 효과적인지 비교합니다.'
                '</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        cmp_ticker = st.text_input("종목코드", "005930", key="t3_ticker")
    with col2:
        cmp_start = st.date_input("시작일", pd.Timestamp("2024-01-01"), key="t3_start")
    with col3:
        cmp_end = st.date_input("종료일", pd.Timestamp.now(), key="t3_end")

    selected = st.multiselect("비교할 전략 선택", list(STRATEGIES.keys()),
                               default=list(STRATEGIES.keys())[:4],
                               help="2개 이상 선택하면 성과를 비교합니다")

    if st.button("⚔️ 비교 실행", key="t3_btn", use_container_width=True) and selected:
        with st.spinner("전략 비교 중..."):
            df = loader.get(cmp_ticker, str(cmp_start), str(cmp_end))
            comp = StrategyComparator(df)
            for name in selected:
                info = STRATEGIES[name]
                comp.add_strategy(name, info['class'], **info['params'])

        st.subheader("📊 비교 결과표")
        table = comp.compare_table()
        st.dataframe(table, use_container_width=True)

        st.subheader("🏆 순위")
        for _, row in table.iterrows():
            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(_, f'#{_}')
            st.write(f"**{medal} {row['Strategy']}** — 수익률: {row['Return %']:.2f}%, "
                     f"샤프: {row['Sharpe']:.2f}, MDD: {row['MDD %']:.2f}%")

        # Charts
        colors = ['#2962FF', '#FF6D00', '#00C853', '#AA00FF', '#FF1744', '#00BFA5']
        fig_cmp = make_subplots(rows=2, cols=1, shared_xaxes=False,
                                 vertical_spacing=0.12, row_heights=[0.6, 0.4],
                                 subplot_titles=['자산 변화 비교', '수익률 비교 (%)'])

        for i, (name, eq) in enumerate(comp.equity_curves.items()):
            ret = comp.results[name]['return_pct']
            fig_cmp.add_trace(go.Scatter(
                x=eq.index, y=eq.values, name=f'{name} ({ret:+.2f}%)',
                line=dict(color=colors[i % len(colors)], width=1.5),
            ), row=1, col=1)

        names = list(comp.results.keys())
        returns = [comp.results[n]['return_pct'] for n in names]
        bar_colors = ['#00C853' if r >= 0 else '#FF1744' for r in returns]
        fig_cmp.add_trace(go.Bar(
            x=names, y=returns, name='수익률',
            marker_color=bar_colors, opacity=0.85,
            text=[f'{r:.2f}%' for r in returns], textposition='outside',
            showlegend=False,
        ), row=2, col=1)

        fig_cmp.update_layout(
            **PLOTLY_LAYOUT, height=600, showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
            margin=dict(l=50, r=20, t=30, b=20),
        )
        st.plotly_chart(fig_cmp, use_container_width=True)

# ─── Tab 4: 포트폴리오 ───
with tab4:
    st.markdown('<div class="guide-box">'
                '💡 <b>사용법:</b> 여러 종목코드를 쉼표(,)로 구분 입력 → "포트폴리오 분석" 클릭<br>'
                '리스크 패리티: 변동성이 큰 종목은 비중을 줄여 위험을 균등 배분합니다.'
                '</div>', unsafe_allow_html=True)

    tickers_input = st.text_input("종목코드 (쉼표로 구분)",
                                   "005930, 000660, 035720",
                                   key="t4_tickers",
                                   help="예: 005930(삼성전자), 000660(SK하이닉스), 035720(카카오)")
    col1, col2 = st.columns(2)
    with col1:
        pf_start = st.date_input("시작일", pd.Timestamp("2024-01-01"), key="t4_start")
    with col2:
        pf_end = st.date_input("종료일", pd.Timestamp.now(), key="t4_end")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        lookback = st.slider("변동성 계산 기간 (일)", 20, 120, 60, key="t4_lb",
                              help="최근 N일간 변동성을 기준으로 비중 계산")
    with col_opt2:
        use_risk_parity = st.checkbox("리스크 패리티 비중 사용", value=True,
                                       help="체크 해제 시 동일 비중(1/N)으로 배분")

    if st.button("💼 포트폴리오 분석", key="t4_btn", use_container_width=True):
        tickers = [t.strip() for t in tickers_input.split(',')]

        with st.spinner("데이터 불러오는 중..."):
            data = loader.fetch_multiple(tickers, str(pf_start), str(pf_end))

        if not data:
            st.error("❌ 데이터를 불러올 수 없습니다. 종목코드를 확인하세요.")
        else:
            if use_risk_parity:
                rp = RiskManager.risk_parity(data, lookback=lookback)
                weights = rp['weights']
                st.subheader("📊 리스크 패리티 배분 결과")
                rp_df = pd.DataFrame({
                    '종목': list(rp['weights'].keys()),
                    '투자 비중': [f"{v:.1%}" for v in rp['weights'].values()],
                    '연간 변동성': [f"{v:.1%}" for v in rp['volatilities'].values()],
                    '위험 기여도': [f"{v:.1f}%" for v in rp['risk_contributions'].values()],
                })
                st.dataframe(rp_df, use_container_width=True)

                fig_pie, ax_pie = plt.subplots(figsize=(6, 6))
                ax_pie.pie(list(weights.values()), labels=list(weights.keys()),
                          autopct='%1.1f%%', startangle=90)
                ax_pie.set_title('투자 비중')
                st.pyplot(fig_pie)
            else:
                weights = {t: 1.0 / len(tickers) for t in tickers}

            st.subheader("📈 가격 비교 (기준=100)")
            fig, ax = plt.subplots(figsize=(12, 5))
            for ticker_name, df in data.items():
                normalized = df['Close'] / df['Close'].iloc[0] * 100
                ax.plot(normalized.index, normalized.values,
                        label=f"{ticker_name} ({weights.get(ticker_name, 0):.0%})")
            ax.set_title('정규화 가격 비교')
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)

            st.subheader("🔗 상관관계 매트릭스")
            st.caption("1에 가까울수록 같이 움직이고, -1에 가까울수록 반대로 움직입니다")
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
            ax_corr.set_title('수익률 상관관계')
            plt.tight_layout()
            st.pyplot(fig_corr)

# ─── Tab 5: 최적화 ───
with tab5:
    st.markdown('<div class="guide-box">'
                '💡 <b>사용법:</b> 전략 선택 → 파라미터 범위를 쉼표로 입력 → "그리드 서치" 또는 "워크포워드" 클릭<br>'
                '<b>그리드 서치:</b> 모든 파라미터 조합을 테스트하여 최적 조합을 찾습니다<br>'
                '<b>워크포워드:</b> 과거(70%)로 최적화한 후 나머지(30%)로 검증하여 과적합 위험을 체크합니다'
                '</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        opt_ticker = st.text_input("종목코드", "005930", key="t5_ticker")
    with col2:
        opt_start = st.date_input("시작일", pd.Timestamp("2023-01-01"), key="t5_start")
    with col3:
        opt_end = st.date_input("종료일", pd.Timestamp.now(), key="t5_end")

    opt_strategy = st.selectbox("전략 선택", list(STRATEGIES.keys()), key="t5_strat")
    opt_info = STRATEGIES[opt_strategy]
    st.caption(f"ℹ️ {opt_info['desc']}")

    st.subheader("파라미터 범위 (쉼표로 구분)")
    param_grid = {}
    label_map = {
        'short_period': '단기 이평', 'long_period': '장기 이평',
        'period': '기간', 'devfactor': '표준편차 배수',
        'oversold': '과매도', 'overbought': '과매수',
        'fast': '빠른선', 'slow': '느린선', 'signal': '시그널',
        'threshold': '기준값',
    }
    for k, v in opt_info['params'].items():
        label = label_map.get(k, k)
        if isinstance(v, float):
            default_range = f"{v * 0.5:.1f}, {v:.1f}, {v * 1.5:.1f}"
            raw = st.text_input(f"{label} ({k})", default_range, key=f"t5_rng_{k}")
            param_grid[k] = [float(x.strip()) for x in raw.split(',')]
        else:
            base = max(v, 5)
            default_range = f"{max(base - 10, 2)}, {base}, {base + 10}"
            raw = st.text_input(f"{label} ({k})", default_range, key=f"t5_rng_{k}")
            param_grid[k] = [int(x.strip()) for x in raw.split(',')]

    total_combos = 1
    for vals in param_grid.values():
        total_combos *= len(vals)
    st.caption(f"🔢 총 {total_combos}개 조합 테스트")

    sort_labels = {'return_pct': '수익률', 'sharpe_ratio': '샤프 비율', 'max_drawdown': '최대 낙폭'}
    opt_sort = st.selectbox("정렬 기준", list(sort_labels.keys()),
                             format_func=lambda x: sort_labels[x], key="t5_sort")

    col_a, col_b = st.columns(2)
    with col_a:
        run_grid = st.button("🔍 그리드 서치", key="t5_grid", use_container_width=True)
    with col_b:
        run_wf = st.button("📐 워크포워드 분석", key="t5_wf", use_container_width=True)

    if run_grid:
        with st.spinner(f"그리드 서치 실행 중 ({total_combos}개 조합)..."):
            df = loader.get(opt_ticker, str(opt_start), str(opt_end))
            optimizer = StrategyOptimizer(df, opt_info['class'])
            top = optimizer.grid_search(param_grid, sort_by=opt_sort, top_n=10)

        st.subheader("🏆 상위 결과")
        display_cols = ['params', 'return_pct', 'cagr_pct', 'sharpe_ratio',
                        'max_drawdown', 'total_trades', 'win_rate']
        st.dataframe(top[display_cols], use_container_width=True)

        param_keys = list(param_grid.keys())
        if len(param_keys) >= 2 and optimizer.results:
            st.subheader("🗺️ 파라미터 히트맵")
            st.caption("색이 초록일수록 수익률이 높은 조합입니다")
            px, py = param_keys[0], param_keys[1]
            heatmap_data = []
            for r in optimizer.results:
                heatmap_data.append({
                    px: r['params'][px], py: r['params'][py],
                    'return_pct': r['return_pct'],
                })
            hdf = pd.DataFrame(heatmap_data)
            pivot = hdf.pivot_table(index=py, columns=px, values='return_pct', aggfunc='mean')

            fig, ax = plt.subplots(figsize=(10, 6))
            im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto')
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns)
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index)
            ax.set_xlabel(label_map.get(px, px))
            ax.set_ylabel(label_map.get(py, py))
            ax.set_title(f'수익률 (%) 히트맵')
            for i in range(len(pivot.index)):
                for j in range(len(pivot.columns)):
                    val = pivot.values[i, j]
                    if not np.isnan(val):
                        ax.text(j, i, f'{val:.1f}', ha='center', va='center', fontsize=9)
            plt.colorbar(im, ax=ax)
            plt.tight_layout()
            st.pyplot(fig)

    if run_wf:
        with st.spinner("워크포워드 분석 실행 중..."):
            df = loader.get(opt_ticker, str(opt_start), str(opt_end))
            optimizer = StrategyOptimizer(df, opt_info['class'])
            wf = optimizer.walk_forward(param_grid, in_sample_ratio=0.7, sort_by=opt_sort)

        if wf:
            st.subheader("📐 워크포워드 결과")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("최적 파라미터", str(wf['best_params']))
            col_b.metric("성과 하락률", f"{wf['degradation_pct']:.1f}%")
            col_c.metric("판정", wf['verdict'])

            is_ret = wf['in_sample'].get('return_pct', 0)
            oos_ret = wf['out_of_sample'].get('return_pct', 0)

            fig, ax = plt.subplots(figsize=(8, 4))
            bars = ax.bar(['학습 구간 (In-Sample)', '검증 구간 (Out-of-Sample)'],
                         [is_ret, oos_ret], color=['#2962FF', '#FF6D00'], alpha=0.8)
            ax.set_title('학습 vs 검증 수익률')
            ax.set_ylabel('수익률 (%)')
            ax.grid(True, alpha=0.3, axis='y')
            for bar, val in zip(bars, [is_ret, oos_ret]):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                       f'{val:.2f}%', ha='center', va='bottom')
            plt.tight_layout()
            st.pyplot(fig)

            st.caption("💡 학습과 검증 수익률 차이가 작을수록 과적합 위험이 낮습니다")
        else:
            st.error("❌ 워크포워드 분석 실패")

# ─── Tab 6: 리스크 ───
with tab6:
    st.markdown('<div class="guide-box">'
                '💡 <b>켈리 공식:</b> 승률과 손익비로 최적 투자 비중을 계산합니다<br>'
                '💡 <b>포지션 사이징:</b> 1회 거래에서 감당할 손실액 기준으로 몇 주를 살지 계산합니다'
                '</div>', unsafe_allow_html=True)

    sub1, sub2 = st.tabs(["🎰 켈리 공식", "📏 포지션 사이징"])

    with sub1:
        mode = st.radio("입력 방식", ["직접 입력", "백테스트 결과 입력"],
                          horizontal=True, key="t6_mode")

        if mode == "직접 입력":
            col1, col2, col3 = st.columns(3)
            with col1:
                win_rate = st.slider("승률 (%)", 1, 99, 55, key="t6_wr",
                                      help="전체 거래 중 수익 거래 비율")
            with col2:
                pl_ratio = st.number_input("손익비", value=1.5, step=0.1,
                                            min_value=0.1, key="t6_pl",
                                            help="평균 수익 / 평균 손실 (1.5면 이길 때 1.5배 벌림)")
            with col3:
                fraction = st.selectbox("켈리 비율",
                                         [("풀 켈리", 1.0), ("하프 켈리 (권장)", 0.5), ("쿼터 켈리", 0.25)],
                                         index=1,
                                         format_func=lambda x: x[0], key="t6_frac")

            if st.button("🎰 켈리 계산", key="t6_calc", use_container_width=True):
                result = RiskManager.kelly_criterion(win_rate / 100, pl_ratio,
                                                      fraction=fraction[1])
                col_a, col_b = st.columns(2)
                col_a.metric("풀 켈리 비중", f"{result['kelly_pct']:.2f}%")
                col_b.metric(f"적용 비중 ({fraction[0]})", f"{result['adjusted_pct']:.2f}%")
                if result['kelly_pct'] > 0:
                    st.success(f"✅ {result['recommendation']}")
                else:
                    st.error(f"⚠️ {result['recommendation']}")

                fig, ax = plt.subplots(figsize=(8, 3))
                kelly_val = result['kelly_pct']
                adj_val = result['adjusted_pct']
                ax.barh([f'{fraction[0]}', '풀 켈리'],
                       [max(adj_val, 0), max(kelly_val, 0)],
                       color=['#2962FF', '#FF6D00'], alpha=0.8)
                ax.set_xlabel('투자 비중 (%)')
                ax.set_title('켈리 공식 추천 비중')
                ax.axvline(x=25, color='red', linestyle='--', alpha=0.5, label='위험 구간')
                ax.legend()
                ax.grid(True, alpha=0.3, axis='x')
                plt.tight_layout()
                st.pyplot(fig)

        else:
            st.caption("백테스트 탭에서 결과를 확인한 후 아래에 입력하세요")
            col1, col2, col3 = st.columns(3)
            with col1:
                total_trades = st.number_input("총 거래 횟수", value=20, min_value=1, key="t6_tt")
            with col2:
                winning_trades = st.number_input("수익 거래 횟수", value=11, min_value=0, key="t6_wt")
            with col3:
                return_pct = st.number_input("총 수익률 (%)", value=5.0, step=0.5, key="t6_ret")

            if st.button("🎰 계산", key="t6_calc2", use_container_width=True):
                mock_result = {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'return_pct': return_pct,
                }
                kelly = RiskManager.kelly_from_backtest(mock_result)
                col_a, col_b = st.columns(2)
                col_a.metric("풀 켈리", f"{kelly['kelly_pct']:.2f}%")
                col_b.metric("하프 켈리 (권장)", f"{kelly['adjusted_pct']:.2f}%")
                st.info(f"💡 {kelly['recommendation']}")

    with sub2:
        st.caption("진입가와 손절가 사이 리스크 금액으로 적정 매수 수량을 계산합니다")
        col1, col2 = st.columns(2)
        with col1:
            total_capital = st.number_input("총 자본금 (원)", value=50_000_000,
                                             step=1_000_000, key="t6_cap")
            risk_pct = st.slider("1회 거래 리스크 (%)", 0.5, 5.0, 2.0, 0.5, key="t6_risk",
                                  help="1회 거래에서 감당할 최대 손실 비율 (총 자본 대비)")
        with col2:
            entry_price = st.number_input("진입가 (원)", value=70000, step=1000, key="t6_entry",
                                           help="매수 예정 가격")
            stop_loss = st.number_input("손절가 (원)", value=65000, step=1000, key="t6_sl",
                                         help="손절 예정 가격 (진입가보다 낮게)")

        if st.button("📏 포지션 계산", key="t6_pos", use_container_width=True):
            if entry_price == stop_loss:
                st.error("❌ 진입가와 손절가가 같으면 계산할 수 없습니다")
            else:
                pos = RiskManager.position_size(total_capital, risk_pct / 100,
                                                 entry_price, stop_loss)
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("매수 수량", f"{pos['shares']:,}주")
                col_b.metric("투자 금액", f"{pos['position_value']:,.0f}원")
                col_c.metric("자본 대비", f"{pos['position_pct']:.1f}%")

                st.write(f"**리스크 금액:** {pos['risk_amount']:,.0f}원 "
                         f"(자본의 {risk_pct}%)")
                st.write(f"**주당 리스크:** {pos['risk_per_share']:,.0f}원 "
                         f"(진입가 - 손절가)")

                fig, ax = plt.subplots(figsize=(8, 3))
                ax.barh(['투자', '현금'],
                       [pos['position_value'], total_capital - pos['position_value']],
                       color=['#2962FF', '#424242'], alpha=0.8)
                ax.set_xlabel('원')
                ax.set_title(f'자본 배분 ({pos["position_pct"]:.1f}% 투자)')
                plt.tight_layout()
                st.pyplot(fig)

# ─── Tab 7: 신호 스캐너 ───
with tab7:
    st.markdown('<div class="guide-box">'
                '💡 <b>사용법:</b> 스캔 방식 선택 → 전략 선택 → "신호 스캔" 클릭<br>'
                '<b>종목 직접 입력:</b> 관심 종목만 빠르게 체크<br>'
                '<b>시총 필터:</b> 시가총액 범위로 종목을 자동 선별하여 전체 스캔'
                '</div>', unsafe_allow_html=True)

    scan_mode = st.radio("스캔 방식",
                          ["종목 직접 입력", "시가총액 필터"],
                          horizontal=True, key="t7_mode")

    if scan_mode == "종목 직접 입력":
        scan_tickers_input = st.text_input(
            "종목코드 (쉼표로 구분)",
            "005930, 000660, 035720, 051910", key="t7_tickers",
            help="스캔할 종목코드를 쉼표로 구분하여 입력")
    else:
        st.subheader("시가총액 필터")
        col1, col2, col3 = st.columns(3)
        with col1:
            market_sel = st.selectbox("시장", ['ALL', 'KOSPI', 'KOSDAQ'], key="t7_mkt",
                                       format_func=lambda x: {'ALL': '전체', 'KOSPI': 'KOSPI', 'KOSDAQ': 'KOSDAQ'}[x])
        with col2:
            min_cap = st.number_input("최소 시총 (조원)", value=5, min_value=0,
                                       step=1, key="t7_min")
        with col3:
            max_cap = st.number_input("최대 시총 (조원, 0=제한없음)",
                                       value=0, min_value=0, step=1, key="t7_max")

        min_억 = min_cap * 10000
        max_억 = max_cap * 10000 if max_cap > 0 else None
        filtered_stocks = MarketScanner.filter_by_market_cap(min_억, max_억, market_sel)
        st.caption(f"📋 조건에 맞는 종목: {len(filtered_stocks)}개")

        if not filtered_stocks.empty:
            preview_df = filtered_stocks[['ticker', 'name', 'market_cap_조']].copy()
            preview_df.columns = ['종목코드', '종목명', '시총 (조)']
            st.dataframe(preview_df, use_container_width=True, height=200)

    scan_start = st.date_input("데이터 시작일", pd.Timestamp("2024-06-01"), key="t7_start",
                                help="이 날짜부터의 데이터로 신호를 판단합니다")

    scan_strategies = st.multiselect("적용할 전략", list(STRATEGIES.keys()),
                                      default=list(STRATEGIES.keys())[:3], key="t7_strats",
                                      help="선택한 전략으로 각 종목의 매수/매도 신호를 감지합니다")

    max_tickers = st.slider("최대 스캔 종목 수", 5, 60, 20, key="t7_max_tk",
                              help="시총 필터 시 상위 N개 종목만 스캔 (많을수록 오래 걸림)")

    if st.button("📡 신호 스캔 시작", key="t7_btn", use_container_width=True) and scan_strategies:
        if scan_mode == "종목 직접 입력":
            tickers = [t.strip() for t in scan_tickers_input.split(',')]
        else:
            tickers = filtered_stocks['ticker'].tolist()[:max_tickers]

        if not tickers:
            st.error("❌ 스캔할 종목이 없습니다")
        else:
            from src.scheduler import SignalChecker
            checker = SignalChecker(loader)

            results = []
            progress = st.progress(0)
            status_text = st.empty()
            total = len(tickers) * len(scan_strategies)
            done = 0

            stock_list = MarketScanner.get_stock_list()
            name_map = dict(zip(stock_list['ticker'], stock_list['name']))

            for tk in tickers:
                tk_name = name_map.get(tk, tk)
                for sname in scan_strategies:
                    info = STRATEGIES[sname]
                    status_text.text(f"스캔 중: {tk_name} ({tk}) / {sname}...")
                    try:
                        sig = checker.check_signal(tk, info['class'], str(scan_start),
                                                   **info['params'])
                        sig['name'] = tk_name
                        results.append(sig)
                    except Exception:
                        results.append({
                            'ticker': tk, 'name': tk_name,
                            'signal': 'ERROR', 'strategy': sname,
                        })
                    done += 1
                    progress.progress(done / total)

            progress.empty()
            status_text.empty()

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

            rename_map = {'name': '종목명', 'ticker': '종목코드', 'signal': '신호', 'strategy': '전략'}
            display_df = df_results[display_cols].rename(columns=rename_map)
            styled = display_df.style.map(signal_style, subset=['신호'])
            st.dataframe(styled, use_container_width=True)

            buy_signals = [r for r in results if r['signal'] == 'BUY']
            sell_signals = [r for r in results if r['signal'] == 'SELL']
            hold_count = len([r for r in results if r['signal'] == 'HOLD'])
            err_count = len([r for r in results if r['signal'] == 'ERROR'])

            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("🟢 매수", len(buy_signals))
            col_b.metric("🔴 매도", len(sell_signals))
            col_c.metric("⚪ 관망", hold_count)
            col_d.metric("⚠️ 오류", err_count)

            if buy_signals:
                st.success("**🟢 매수 신호 감지:**")
                for b in buy_signals:
                    st.write(f"  - **{b.get('name', '')}** ({b['ticker']}) — {b.get('strategy', '')}")
            if sell_signals:
                st.warning("**🔴 매도 신호 감지:**")
                for s in sell_signals:
                    st.write(f"  - **{s.get('name', '')}** ({s['ticker']}) — {s.get('strategy', '')}")
            if not buy_signals and not sell_signals:
                st.info("현재 매수/매도 신호 없음. 모든 종목 관망 상태입니다.")

# ─── 사이드바 ───
with st.sidebar:
    st.markdown("### 퀀트 트레이딩")
    st.caption("v2.0 | 인터랙티브 대시보드")
    st.divider()

    st.markdown("**6가지 전략**")
    for name, info in STRATEGIES.items():
        st.markdown(f"<span style='color:#B0BEC5; font-size:0.82rem'>• {name}</span>",
                    unsafe_allow_html=True)
    st.divider()

    st.markdown("**사용 가이드**")
    guide = {
        "📊 종목 분석": "종목코드 입력 → 봉차트 + 이평선 확인",
        "🔬 백테스트": "전략 선택 → 파라미터 조정 → 과거 수익률 확인",
        "⚔️ 전략 비교": "여러 전략을 동시 적용 → 최적 전략 찾기",
        "💼 포트폴리오": "여러 종목 입력 → 리스크 패리티 비중 계산",
        "🎯 최적화": "파라미터 범위 설정 → 최적 조합 탐색",
        "🛡️ 리스크": "켈리 공식 + 포지션 사이징 계산",
        "📡 신호 스캐너": "시장 전체 매수/매도 신호 탐색",
    }
    for tab_name, desc in guide.items():
        st.markdown(f"<span style='font-size:0.82rem'>{tab_name}</span><br>"
                    f"<span style='color:#78909C; font-size:0.75rem'>{desc}</span>",
                    unsafe_allow_html=True)
    st.divider()
    st.markdown("**주요 종목코드**")
    stock_ref = "005930 삼성전자 | 000660 SK하이닉스\n035420 네이버 | 035720 카카오\n005380 현대차 | 051910 LG화학"
    st.code(stock_ref, language=None)
