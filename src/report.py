import os
import base64
from datetime import datetime


class ReportGenerator:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, result, strategy_name, ticker, period,
                 chart_path=None, trades=None):
        chart_html = ''
        if chart_path and os.path.exists(chart_path):
            with open(chart_path, 'rb') as f:
                img_b64 = base64.b64encode(f.read()).decode()
            chart_html = f'<img src="data:image/png;base64,{img_b64}" style="width:100%;max-width:900px;">'

        trades_html = ''
        if trades:
            rows = ''.join(
                f'<tr><td>{t["date"]}</td><td>{t["action"]}</td>'
                f'<td>{t["price"]:,.0f}</td><td>{t.get("pnl", ""):}</td></tr>'
                for t in trades
            )
            trades_html = f'''
            <h2>Trade History</h2>
            <table>
                <tr><th>Date</th><th>Action</th><th>Price</th><th>PnL</th></tr>
                {rows}
            </table>'''

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Backtest Report - {strategy_name}</title>
<style>
    body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f5f5f5; }}
    .container {{ max-width: 960px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    h1 {{ color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 10px; }}
    h2 {{ color: #333; margin-top: 30px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 10px 14px; text-align: right; }}
    th {{ background: #1a237e; color: white; }}
    tr:nth-child(even) {{ background: #f9f9f9; }}
    .meta {{ color: #666; font-size: 14px; }}
    .positive {{ color: #00c853; font-weight: bold; }}
    .negative {{ color: #ff1744; font-weight: bold; }}
    .chart {{ margin: 20px 0; text-align: center; }}
</style>
</head>
<body>
<div class="container">
    <h1>Backtest Report</h1>
    <p class="meta">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    <h2>Strategy Info</h2>
    <table>
        <tr><th style="text-align:left">Item</th><th>Value</th></tr>
        <tr><td style="text-align:left">Strategy</td><td>{strategy_name}</td></tr>
        <tr><td style="text-align:left">Ticker</td><td>{ticker}</td></tr>
        <tr><td style="text-align:left">Period</td><td>{period}</td></tr>
    </table>

    <h2>Performance</h2>
    <table>
        <tr><th style="text-align:left">Metric</th><th>Value</th></tr>
        <tr><td style="text-align:left">Initial Cash</td><td>{result['initial_cash']:,.0f}</td></tr>
        <tr><td style="text-align:left">Final Value</td><td>{result['final_value']:,.0f}</td></tr>
        <tr><td style="text-align:left">Total Return</td>
            <td class="{'positive' if result['return_pct'] >= 0 else 'negative'}">{result['return_pct']:.2f}%</td></tr>
        <tr><td style="text-align:left">CAGR</td><td>{result['cagr_pct']:.2f}%</td></tr>
        <tr><td style="text-align:left">Max Drawdown</td>
            <td class="negative">{result['max_drawdown']:.2f}%</td></tr>
        <tr><td style="text-align:left">Sharpe Ratio</td><td>{result['sharpe_ratio']:.2f}</td></tr>
        <tr><td style="text-align:left">Total Trades</td><td>{result['total_trades']}</td></tr>
        <tr><td style="text-align:left">Win Rate</td><td>{result['win_rate']:.1f}%</td></tr>
    </table>

    {f'<h2>Chart</h2><div class="chart">{chart_html}</div>' if chart_html else ''}
    {trades_html}
</div>
</body>
</html>'''

        filename = f'report_{strategy_name}_{ticker}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'Report saved: {path}')
        return path

    def generate_comparison(self, comparison_table, chart_path=None):
        chart_html = ''
        if chart_path and os.path.exists(chart_path):
            with open(chart_path, 'rb') as f:
                img_b64 = base64.b64encode(f.read()).decode()
            chart_html = f'<img src="data:image/png;base64,{img_b64}" style="width:100%;max-width:900px;">'

        table_rows = ''
        for _, row in comparison_table.iterrows():
            ret_class = 'positive' if row['Return %'] >= 0 else 'negative'
            table_rows += f'''<tr>
                <td style="text-align:left">{row['Strategy']}</td>
                <td class="{ret_class}">{row['Return %']:.2f}%</td>
                <td>{row['CAGR %']:.2f}%</td>
                <td class="negative">{row['MDD %']:.2f}%</td>
                <td>{row['Sharpe']:.2f}</td>
                <td>{row['Trades']}</td>
                <td>{row['Win Rate %']:.1f}%</td>
            </tr>'''

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Strategy Comparison Report</title>
<style>
    body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f5f5f5; }}
    .container {{ max-width: 960px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    h1 {{ color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 10px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 10px 14px; text-align: right; }}
    th {{ background: #1a237e; color: white; }}
    tr:nth-child(even) {{ background: #f9f9f9; }}
    .meta {{ color: #666; font-size: 14px; }}
    .positive {{ color: #00c853; font-weight: bold; }}
    .negative {{ color: #ff1744; font-weight: bold; }}
    .chart {{ margin: 20px 0; text-align: center; }}
</style>
</head>
<body>
<div class="container">
    <h1>Strategy Comparison Report</h1>
    <p class="meta">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    <table>
        <tr>
            <th style="text-align:left">Strategy</th>
            <th>Return</th><th>CAGR</th><th>MDD</th>
            <th>Sharpe</th><th>Trades</th><th>Win Rate</th>
        </tr>
        {table_rows}
    </table>

    {f'<div class="chart">{chart_html}</div>' if chart_html else ''}
</div>
</body>
</html>'''

        filename = f'comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'Comparison report saved: {path}')
        return path
