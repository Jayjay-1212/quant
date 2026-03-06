import backtrader as bt


class BollingerBand(bt.Strategy):
    """볼린저밴드 전략 (평균 회귀)

    - 주가가 하단 밴드 이탈 → 매수 (과매도)
    - 주가가 상단 밴드 이탈 → 매도 (과매수)
    """

    params = (
        ('period', 20),
        ('devfactor', 2.0),
    )

    def __init__(self):
        self.bband = bt.indicators.BollingerBands(
            period=self.p.period, devfactor=self.p.devfactor)
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
            if self.data.close[0] < self.bband.lines.bot[0]:
                self.order = self.buy()
        else:
            if self.data.close[0] > self.bband.lines.top[0]:
                self.order = self.close()

    def log(self, msg):
        dt = self.datas[0].datetime.date(0)
        print(f'[{dt}] {msg}')
