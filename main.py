from src.data_loader import DataLoader
from src.analyzer import Analyzer
from src.visualizer import Visualizer
from backtest.engine import BacktestEngine
from strategies.sma_cross import SmaCross
from strategies.momentum import Momentum


def run_backtest(ticker, start, end, strategy_class, strategy_name, **kwargs):
    loader = DataLoader()
    df = loader.get(ticker, start, end)

    engine = BacktestEngine(cash=10_000_000, commission=0.00015)
    engine.add_data(df, name=ticker)
    engine.add_strategy(strategy_class, **kwargs)
    result = engine.run()

    print(f"\n[{strategy_name}] {ticker} ({start} ~ {end})")
    print(Analyzer.summary(result))
    return result


def main():
    ticker = "005930"   # Samsung Electronics
    start = "2020-01-01"
    end = "2025-12-31"

    # SMA Cross strategy
    sma_result = run_backtest(
        ticker, start, end,
        SmaCross, "SMA Cross",
        short_period=5, long_period=20,
    )

    # Momentum strategy
    mom_result = run_backtest(
        ticker, start, end,
        Momentum, "Momentum",
        period=20, threshold=0.0,
    )

    # Compare strategies
    results = {
        "SMA Cross": sma_result,
        "Momentum": mom_result,
    }
    Visualizer.plot_comparison(results)

    # Price chart with SMAs
    loader = DataLoader()
    df = loader.load(ticker)
    Visualizer.plot_price(df, title=f"{ticker} Price", sma_periods=[5, 20, 60])


if __name__ == "__main__":
    main()
