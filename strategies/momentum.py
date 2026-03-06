import backtrader as bt


class Momentum(bt.Strategy):
    params = (
        ('period', 20),
        ('threshold', 0.0),
    )

    def __init__(self):
        self.roc = bt.indicators.ROC100(period=self.p.period)

    def next(self):
        if not self.position:
            if self.roc[0] > self.p.threshold:
                self.buy()
        elif self.roc[0] < self.p.threshold:
            self.close()
