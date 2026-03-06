import backtrader as bt


class RsiStrategy(bt.Strategy):
    """RSI 전략 (모멘텀 반전)

    - RSI가 과매도(30 이하) 후 반등 시 매수
    - RSI가 과매수(70 이상) 후 하락 시 매도
    """

    params = (
        ('period', 14),
        ('oversold', 30),
        ('overbought', 70),
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI(period=self.p.period)
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
            if self.rsi[0] < self.p.oversold:
                self.order = self.buy()
        else:
            if self.rsi[0] > self.p.overbought:
                self.order = self.close()

    def log(self, msg):
        dt = self.datas[0].datetime.date(0)
        print(f'[{dt}] {msg}')
