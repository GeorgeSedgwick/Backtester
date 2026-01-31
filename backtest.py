


from __future__ import (absolute_import, division, print_function, unicode_literals)
import datetime
import os.path
import sys
import matplotlib
matplotlib.use('Agg')
import yfinance as yf
import pandas as pd
import backtrader as bt
import streamlit as st
import matplotlib.pyplot as plt
from datetime import date, timedelta


class BollingerRSIStrategy(bt.Strategy):
    params = (
        ('bollinger_period', 20),
        ('devfactor', 2.2),
        ('rsi_period', 14),
        ('rsi_oversold', 40),
        ('rsi_overbought', 60),
        ('stop_loss_pct', 0.03),
        ('printlog', False),
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            st.write('%s, %s' % (dt.isoformat(), txt))



    def __init__(self):
        self.dataclose = self.datas[0].close
        self.bb = bt.indicators.BollingerBands(self.datas[0],
            period=self.params.bollinger_period,
            devfactor=self.params.devfactor
        )

        self.rsi = bt.indicators.RSI(self.datas[0],
            period=self.params.rsi_period
        )

        self.order = None
        self.entry_price = None

        

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                if self.position.size > 0:
                    self.log('BUY EXECUTED @ %.2f, Commission: %.2f' %
                         (order.executed.price,
                          order.executed.comm))
                    
                else:
                    self.log('SHORT COVERED @ %.2f, Commission: %.2f' %
                             (order.executed.price,
                              order.executed.comm))
                    

            else:
                if self.position.size < 0:
                    self.log('SHORT ENTERED @ %.2f, Commission: %.2f' %
                         (order.executed.price,
                          order.executed.comm))
                else:
                    self.log('SELL EXECUTED @ %.2f, Commission: %.2f' %
                             (order.executed.price, order.executed.comm))
                    
                self.bar_executed = len(self)
                
        elif order.status in [order.Canceled, order.Rejected, order.Margin]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        self.log('PNL: %.2f, PNL(incl Comm.): %.2f' %
                 (trade.pnl, trade.pnlcomm))
        
    def next(self):
        self.log('Close: %.2f' % self.dataclose[0])

        if self.order:
            return
        
        if not self.position:
            if self.data.close[-1] < self.bb.bot[-1] and self.data.close[0] > self.bb.bot[0]:
                if self.rsi[0] < self.params.rsi_oversold:
                    self.order = self.buy()
                    self.entry_price = self.data.close[0]
            
            elif self.data.close[-1] > self.bb.top[-1] and self.data.close[0] < self.bb.top[0]:
                if self.rsi[0] > self.params.rsi_overbought:
                    self.order = self.sell()
                    self.entry_price = self.data.close[0]

        else:
            if self.position.size > 0:
                if self.data.close[0] <= self.entry_price * (1 - self.params.stop_loss_pct):
                    self.order = self.sell()
                    self.log('LONG STOP LOSS TRIGGERED')
                elif self.data.close[-1] > self.bb.top[-1] and self.data.close[0] < self.bb.top[0]:
                    if self.rsi[0] > self.params.rsi_overbought:
                        self.order = self.sell()
                elif self.data.close[0] < self.bb.mid[0] and self.data.close[-1] > self.bb.mid[-1]:
                    self.order = self.sell()
                    self.log('LONG EXIT: BELOW MID BAND')
            
            elif self.position.size < 0:
                if self.data.close[0] >= self.entry_price * (1 + self.params.stop_loss_pct):
                    self.order = self.buy()
                    self.log('SHORT STOP LOSS TRIGGERED')
                elif self.data.close[-1] < self.bb.bot[-1] and self.data.close[0] > self.bb.bot[0]:
                    if self.rsi[0] < self.params.rsi_oversold:
                        self.order = self.buy()
                elif self.data.close[0] > self.bb.mid[0] and self.data.close[-1] < self.bb.mid[-1]:
                    self.order = self.buy()
                    self.log('SHORT EXIT: ABOVE MID BAND')




class TestSMAStrategy(bt.Strategy):
    params = (
        ('maperiod', 30),
        ('printlog', False),
    )

    def log(self, txt, dt=None, doprint=False): #switch to doprint=True when optimising
        if self.params.printlog or doprint:    
            dt = dt or self.datas[0].datetime.date(0)
            st.write('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        #keping a reference to the close line in data[0] data series
        self.dataclose = self.datas[0].close

        self.order = None
        self.buyprice = None
        self.buycomm = None

        self.sma = bt.indicators.MovingAverageSimple(self.datas[0], period=self.params.maperiod)
        #self.dummy = CustomInd()
        self.ema = bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        #bt.indicators.WeightedMovingAverage(self.datas[0], period=25, subplot=True)

        #bt.indicators.StochasticSlow(self.datas[0])
        #bt.indicators.MACDHisto(self.datas[0])
        #rsi = bt.indicators.RSI(self.datas[0])
        #bt.indicators.SmoothedMovingAverage(rsi, period=10)
        #bt.indicators.ATR(self.datas[0], plot=False)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            #order has been submitted/accepted, we need do nothing
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' % 
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm


            else: 
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' % 
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        #simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

        #check if an order is pending, if yes we cannot send a second one
        if self.order:
            return
        
        #check if we are in the market
        if not self.position:

            #buy conditions
            if self.dataclose[0] > self.sma[0]:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                #print(f"Dummy Indicator Value: {self.dummy.dummyline[0]}")
                self.order = self.buy()
            
        else:

        #if already in the market, we might sell
            if self.dataclose[0] < self.sma[0]:
                #exit condition
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                self.order = self.sell()

class BollingerEMAStrategy(bt.Strategy):
    params = (
        ('bollinger_period', 20),
        ('devfactor', 1.8),
        ('ema_period', 100),
        ('printlog', False),
    )

    def log(self, txt, dt=None, doprint=True):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))



    def __init__(self):
        self.dataclose = self.datas[0].close
        self.bb = bt.indicators.BollingerBands(
            period=self.params.bollinger_period,
            devfactor=self.params.devfactor
        )

        self.ema = bt.indicators.EMA(self.datas[0],
            period=self.params.ema_period,

        )
        self.order = None
        self.buyprice = None
        self.buycomm = None

        

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('Bought at: %.2f, Commission: %.2f' %
                         (order.executed.price,
                          order.executed.comm))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm

            else:
                self.log('Sold at: %.2f, Bought for: %.2f Commission: %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                
                self.bar_executed = len(self)
                
        elif order.status in [order.Canceled, order.Rejected, order.Margin]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        self.log('PNL: %.2f, PNL(incl Comm.): %.2f' %
                 (trade.pnl, trade.pnlcomm))
        
    def next(self):
        self.log('Close: %.2f' % self.dataclose[0])

        if self.order:
            return
        
        if not self.position:
            if self.data.close[0] > self.ema[0] and self.data.close[0] > self.bb.top[0]:
                self.order = self.buy() 

        else:
            if self.data.close[0] < self.bb.mid[0]:
                self.order = self.sell()


        


class FixedCommissionScheme(bt.CommInfoBase):

    params = (
        ('commission', 3.0),
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
    )

    def _getcommission(self, size, price, pseudoexec):
        return self.p.commission
    



    
## use bt.Max in __init__: Backtrader creates a vectorised object
## use max() in next(): compares current values

#a) all at once
#b) one-by-one

st.title("George's Backtester")

ticker = st.text_input("Asset to trade: ")

start_date = date.today() - timedelta(days=7614)
end_date = date.today()

start_slide = st.slider("Select start date: ",
          min_value=start_date,
          max_value=end_date,
          value=start_date)


end_slide = st.slider("Select end date: ",
          min_value=start_date,
          max_value=end_date,
          value=start_date)


if start_slide > end_slide:
    st.write("Date range invalid")

strategy_options = {
    'Bollinger Bands + RSI': BollingerRSIStrategy,
    'SMA Reversion': TestSMAStrategy,
    'Bollinger Bands + EMA': BollingerEMAStrategy,
}
strategy = st.selectbox(
    "Select Strategy", list(strategy_options.keys())
)



if st.button("Run Backtest"):
    selected_start_date = str(start_slide)
    selected_end_date = str(end_slide)
    selected_strategy = strategy_options[strategy]

    if __name__ == '__main__':
        cerebro = bt.Cerebro()
        cerebro.addstrategy(selected_strategy)
        
    #FOR OPTIMISING STRATEGY: ##########    
    #    strats = cerebro.optstrategy( #
    #       TestSMAStrategy,           #
    #       maperiod=range(10, 31))    #
    ####################################

        df = yf.download(ticker, start=selected_start_date, end=selected_end_date, auto_adjust=False)
        #s&p500 futures: ES=F
        #fx: GBPUSD=X
        #gold: GC=F


        if len(df.columns.names) > 1:
            df.columns = df.columns.droplevel(1)
        
        data = bt.feeds.PandasData(dataname=df)




        cerebro.adddata(data, name=ticker)
        #cerebro.adddata(data, name="GBP/USD")

        cerebro.broker.setcash(100000.0)
        cerebro.broker.set_shortcash(True)
        cerebro.addsizer(bt.sizers.FixedSize, stake=10)
        comminfo = FixedCommissionScheme(commission=3.0)
        cerebro.broker.addcommissioninfo(comminfo)


        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        
        st.write("-------------------------------------")
        st.write('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
        results = cerebro.run()
        st.write("-------------------------------------")
        st.write("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())
        strat = results[0]
        trade_analysis = strat.analyzers.trade_analyzer.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        won = trade_analysis.won.total if 'won' in trade_analysis else 0
        lost = trade_analysis.lost.total if 'lost' in trade_analysis else 0
        total_trades = trade_analysis.total.total
        
        st.write("-------------------------------------")
        st.write(f"Wins: {won}")
        st.write(f"Losses: {lost}")
        st.write(f"Total trades: {total_trades}")

        if lost == 0:
            st.write(f"Win/Loss Ratio: {won:.2f}")
        else:
            st.write(f"Win/Loss Ratio: {won/lost:.2f}")

        st.write("-------------------------------------")

        st.write("Max Drawdown: {:.2f}%".format(drawdown.max.drawdown))
        st.write("Max Drawdown Duration: {} bars".format(drawdown.max.len))

        try:
            figs = cerebro.plot(iplot=True, volume=True, width=20, height=12, dpi=100)
            for fig_list in figs:
                for fig in fig_list:
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)
        except Exception as e:
            st.error(f"Plotting failed: {e}")
#st.dataframe()




