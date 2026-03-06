import itertools
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from backtest.engine import BacktestEngine


class StrategyOptimizer:
    def __init__(self, df, strategy_class, cash=10_000_000, commission=0.00015):
        self.df = df
        self.strategy_class = strategy_class
        self.cash = cash
        self.commission = commission
        self.results = []

    def grid_search(self, param_grid, sort_by='return_pct', top_n=10):
        """그리드 서치로 모든 파라미터 조합 탐색

        Args:
            param_grid: dict, 예: {'short_period': [5,10,20], 'long_period': [20,40,60]}
            sort_by: 정렬 기준 ('return_pct', 'sharpe_ratio', 'max_drawdown')
            top_n: 상위 N개 결과 반환
        """
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combos = list(itertools.product(*values))

        print(f"Optimizing {len(combos)} parameter combinations...")
        self.results = []

        for i, combo in enumerate(combos):
            params = dict(zip(keys, combo))
            try:
                engine = BacktestEngine(cash=self.cash, commission=self.commission)
                engine.add_data(self.df.copy())
                engine.add_strategy(self.strategy_class, **params)
                result = engine.run()
                result['params'] = params
                self.results.append(result)
            except Exception as e:
                pass

            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{len(combos)}")

        print(f"Completed: {len(self.results)} successful runs")

        ascending = True if sort_by == 'max_drawdown' else False
        df_results = pd.DataFrame(self.results)
        df_results = df_results.sort_values(sort_by, ascending=ascending)

        return df_results.head(top_n)

    def walk_forward(self, param_grid, in_sample_ratio=0.7, sort_by='return_pct'):
        """워크포워드 분석: in-sample 최적화 → out-of-sample 검증

        Args:
            param_grid: 파라미터 범위
            in_sample_ratio: in-sample 비율 (기본 70%)
        """
        split_idx = int(len(self.df) * in_sample_ratio)
        in_sample = self.df.iloc[:split_idx]
        out_sample = self.df.iloc[split_idx:]

        print(f"In-sample:  {in_sample.index[0].date()} ~ {in_sample.index[-1].date()} ({len(in_sample)} rows)")
        print(f"Out-sample: {out_sample.index[0].date()} ~ {out_sample.index[-1].date()} ({len(out_sample)} rows)")

        # In-sample optimization
        print("\n--- In-Sample Optimization ---")
        opt_in = StrategyOptimizer(in_sample, self.strategy_class, self.cash, self.commission)
        top_in = opt_in.grid_search(param_grid, sort_by=sort_by, top_n=3)

        if top_in.empty:
            print("No valid results in in-sample period")
            return None

        best_params = top_in.iloc[0]['params']
        print(f"\nBest params (in-sample): {best_params}")
        print(f"  Return: {top_in.iloc[0]['return_pct']:.2f}%")

        # Out-of-sample validation
        print("\n--- Out-of-Sample Validation ---")
        engine = BacktestEngine(cash=self.cash, commission=self.commission)
        engine.add_data(out_sample.copy())
        engine.add_strategy(self.strategy_class, **best_params)
        oos_result = engine.run()
        oos_result['params'] = best_params

        print(f"  Return: {oos_result['return_pct']:.2f}%")
        print(f"  Sharpe: {oos_result['sharpe_ratio']:.2f}")
        print(f"  MDD:    {oos_result['max_drawdown']:.2f}%")

        # Overfit check
        is_ratio = top_in.iloc[0]['return_pct']
        oos_ratio = oos_result['return_pct']
        if is_ratio != 0:
            degradation = (1 - oos_ratio / is_ratio) * 100
        else:
            degradation = 0

        if degradation > 50:
            verdict = "HIGH OVERFIT RISK"
        elif degradation > 20:
            verdict = "MODERATE OVERFIT RISK"
        else:
            verdict = "LOW OVERFIT RISK - params look robust"

        print(f"\n  Performance degradation: {degradation:.1f}%")
        print(f"  Verdict: {verdict}")

        return {
            'best_params': best_params,
            'in_sample': top_in.iloc[0].to_dict(),
            'out_of_sample': oos_result,
            'degradation_pct': round(degradation, 1),
            'verdict': verdict,
        }

    def plot_heatmap(self, param_x, param_y, metric='return_pct', save_path=None):
        """2D 파라미터 히트맵"""
        if not self.results:
            print("No results to plot. Run grid_search first.")
            return

        data = []
        for r in self.results:
            data.append({
                param_x: r['params'][param_x],
                param_y: r['params'][param_y],
                metric: r[metric],
            })

        df = pd.DataFrame(data)
        pivot = df.pivot_table(index=param_y, columns=param_x, values=metric)

        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto')

        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)
        ax.set_xlabel(param_x)
        ax.set_ylabel(param_y)
        ax.set_title(f'Parameter Optimization: {metric}')

        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                val = pivot.values[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f'{val:.1f}', ha='center', va='center', fontsize=8)

        plt.colorbar(im, ax=ax)
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f'Heatmap saved: {save_path}')
        plt.show()

    def print_top_results(self, top_df):
        print("\n" + "=" * 70)
        print("  Optimization Results (Top Parameters)")
        print("=" * 70)
        for i, (_, row) in enumerate(top_df.iterrows(), 1):
            params_str = ', '.join(f'{k}={v}' for k, v in row['params'].items())
            print(f"  #{i}  {params_str}")
            print(f"      Return: {row['return_pct']:>7.2f}%  "
                  f"Sharpe: {row['sharpe_ratio']:>5.2f}  "
                  f"MDD: {row['max_drawdown']:>6.2f}%  "
                  f"Trades: {row['total_trades']}")
        print("=" * 70)
