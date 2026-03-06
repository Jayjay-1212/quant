import backtrader as bt


class SmaCross(bt.Strategy):
    params = (
        ('short_period', 20),
        ('long_period', 60),
    )

    def __init__(self):
        sma_short = bt.indicators.SMA(period=self.p.short_period)
        sma_long = bt.indicators.SMA(period=self.p.long_period)
        self.crossover = bt.indicators.CrossOver(sma_short, sma_long)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()
