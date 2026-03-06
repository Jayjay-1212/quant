import backtrader as bt


class MovingAverageCross(bt.Strategy):
    """이동평균 교차 전략 (골든크로스/데드크로스)

    - 골든크로스: 단기 SMA가 장기 SMA를 상향 돌파 → 매수
    - 데드크로스: 단기 SMA가 장기 SMA를 하향 돌파 → 매도
    """

    params = (
        ('short_period', 20),
        ('long_period', 60),
    )

    def __init__(self):
        self.sma_short = bt.indicators.SMA(period=self.p.short_period)
        self.sma_long = bt.indicators.SMA(period=self.p.long_period)
        self.crossover = bt.indicators.CrossOver(self.sma_short, self.sma_long)
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY  @ {order.executed.price:,.0f}')
            else:
                self.log(f'SELL @ {order.executed.price:,.0f}')
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # Golden Cross → Buy
            if self.crossover > 0:
                self.order = self.buy()
        else:
            # Dead Cross → Sell
            if self.crossover < 0:
                self.order = self.close()

    def log(self, msg):
        dt = self.datas[0].datetime.date(0)
        print(f'[{dt}] {msg}')
