import backtrader as bt


class MacdStrategy(bt.Strategy):
    """MACD 전략 (추세 추종)

    - MACD 라인이 시그널 라인을 상향 돌파 → 매수
    - MACD 라인이 시그널 라인을 하향 돌파 → 매도
    """

    params = (
        ('fast', 12),
        ('slow', 26),
        ('signal', 9),
    )

    def __init__(self):
        self.macd = bt.indicators.MACD(
            period_me1=self.p.fast,
            period_me2=self.p.slow,
            period_signal=self.p.signal,
        )
        self.crossover = bt.indicators.CrossOver(
            self.macd.macd, self.macd.signal)
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
            if self.crossover > 0:
                self.order = self.buy()
        else:
            if self.crossover < 0:
                self.order = self.close()

    def log(self, msg):
        dt = self.datas[0].datetime.date(0)
        print(f'[{dt}] {msg}')
