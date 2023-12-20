from AlgorithmImports import *
from datetime import datetime


class IndexStrategy(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2023, 1, 1)
        self.SetEndDate(2023, 3, 1)
        self.SetCash(1000000)
        self.spx500_hour = self.AddCfd("SPX500USD", Resolution.Hour).Symbol
        self.spx500_min = self.AddCfd("SPX500USD", Resolution.Minute).Symbol
        self.SetBenchmark("SPX500USD")  
        self.SetWarmUp(30)



        #time of day---------------------------------------------------------------
        self.InTheSession = None
        self.start_time = 9
        self.end_time = 12
        #--------------------------------------------------------------------------



        #daily bias----------------------------------------------------------------
        dailyConsolidator = QuoteBarConsolidator(timedelta(1))
        dailyConsolidator.DataConsolidated += self.OnDailyData
        self.SubscriptionManager.AddConsolidator("SPX500USD", dailyConsolidator)

        self.ema_9 = self.EMA("SPX500USD", 9, Resolution.Daily, Field.Close)
        self.ema_18 = self.EMA("SPX500USD", 18, Resolution.Daily, Field.Close)
        self.RegisterIndicator("SPX500USD", self.ema_9, dailyConsolidator)
        self.RegisterIndicator("SPX500USD", self.ema_18, dailyConsolidator)

        self.daily_bias = 'neutral'
        #--------------------------------------------------------------------------



        #entry trigger-------------------------------------------------------------
        self.ema_entry =  self.EMA(self.spx500_hour, 10, Resolution.Hour)
        #--------------------------------------------------------------------------



        #trade entry parameters----------------------------------------------------
        self.risk = 1
        self.stop_point = 10
        self.take_profit_rr = 3

        self.lot_size_buy = 0
        self.lot_size_sell = 0
        self.current_risk = 0
        
        self.current_balance = 0
        self.balance = 0
        #--------------------------------------------------------------------------



        #risk management-----------------------------------------------------------
        self.trades_taken = 0
        self.trade_count = 0

        self.breakeven_rr = 1.5
        self.trade_be = None
        self.slbe_balance = 0

        self.wins = 0
        self.losses = 0
        self.be = 0
        #--------------------------------------------------------------------------



        #chart trades--------------------------------------------------------------
        self.trade_count = 0
        self.trade_chart = Chart("Trade Chart")
        self.AddChart(self.trade_chart)
        self.trade_series = Series("Trades Taken", SeriesType.Line)
        self.trade_chart.AddSeries(self.trade_series)
        #--------------------------------------------------------------------------


        
        

#====================================================================================================================================================


  

    #daily bias--------------------------------------------------------------------
    def OnDailyData(self, sender, bar):
        if self.ema_9.Current.Value > self.ema_18.Current.Value:
            self.daily_bias = 'bullish'

        elif self.ema_9.Current.Value < self.ema_18.Current.Value:
            self.daily_bias = 'bearish'
    #------------------------------------------------------------------------------




#====================================================================================================================================================




    def OnData(self, data):
        if not data.ContainsKey(self.spx500_hour):
            return
        if not data.ContainsKey(self.spx500_min):
            return
        if self.IsWarmingUp:
            return




        #sl, be, and tp------------------------------------------------------------
        self.balance = self.Portfolio.TotalPortfolioValue
        self.current_balance = self.Portfolio.Cash

        self.sl_balance = self.current_balance - (self.current_balance*(self.risk/100))
        self.be_balance = self.current_balance + ((self.current_balance*(self.risk/100))*self.breakeven_rr)
        self.tp_balance = self.current_balance + ((self.current_balance*(self.risk/100))*self.take_profit_rr)
        '''self.Log(f"sl balance: {self.sl_balance}")
        self.Log(f"balance: {self.balance}")
        self.Log(f"tp balance: {self.tp_balance}")
        self.Log(f"be balance: {self.be_balance}")'''

        #take profit
        if self.balance >= self.tp_balance:
            self.Liquidate()
            self.wins += 1
            self.Log("Win")
            self.Log(f"wins: {self.wins}")
            self.Log(f"balance: {self.balance}")
            self.Log(f"tp balance: {self.tp_balance}")
        
        #breakeven
        if self.balance >= self.be_balance:
            self.trade_be = True

        if self.trade_be == True:
            self.slbe_balance = self.current_balance
            if self.balance <= self.slbe_balance:
                self.Liquidate()
                self.be += 1
                self.Log("be")
                self.Log(f"be's: {self.be}")
                self.trade_be = False
            elif self.balance >= self.tp_balance:
                self.Liquidate()
                self.wins += 1
                self.Log("win")
                self.Log(f"wins: {self.wins}")
                self.trade_be = False

        #stop loss  
        if self.balance <= self.sl_balance:
            self.Liquidate()
            self.losses += 1
            self.Log("Loss")
            self.Log(f"losses: {self.losses}")
            self.Log(f"sl balance: {self.sl_balance}")
            self.Log(f"balance: {self.balance}")
        #--------------------------------------------------------------------------





        #reset after session-------------------------------------------------------
        if self.Time.hour == 18:
            self.Liquidate()
            self.trades_taken = 0
            self.sl_balance = 0
            self.tp_balance = 0
            self.be_balance = 0
            self.slbe_balance = 0
            self.trade_be = False
    
        '''self.Schedule.On(self.DateRules.EveryDay(self.spx500_hour), self.TimeRules.At(18, 0), self.ResetAlgorithm)'''

        #--------------------------------------------------------------------------





        #data----------------------------------------------------------------------
        self.current_bar_hour = data[self.spx500_hour]
        self.price_hour  = self.current_bar_hour.Price

        self.current_bar_min = data[self.spx500_min]
        self.price_min  = self.current_bar_min.Price
        #--------------------------------------------------------------------------





        #lot size------------------------------------------------------------------
        self.current_risk = self.current_balance * (self.risk/100)
        self.lot_size_buy = self.current_risk / self.stop_point
        self.lot_size_sell = -(self.current_risk / self.stop_point)
        #--------------------------------------------------------------------------

        



        #Session Time--------------------------------------------------------------
        if self.Time.hour >= self.start_time and self.Time.hour <= self.end_time:
            self.InTheSession = 1
        else:
            self.InTheSession = 0
        #--------------------------------------------------------------------------





        #execution-----------------------------------------------------------------
        if self.InTheSession == 1:

            if self.trades_taken < 1:

                if self.daily_bias == 'bullish' and self.price_hour > self.ema_entry.Current.Value:
                    self.Log("Buy Order")
                    self.Log(f"sl balance: {self.sl_balance}")
                    self.Log(f"balance: {self.balance}")
                    self.Log(f"tp balance: {self.tp_balance}")
                    self.Log(f"risk: ${self.current_risk}")

                    #entry
                    entry_order = self.MarketOrder(self.spx500_min, self.lot_size_buy)

                    #trades taken
                    self.trades_taken += 1

                    #chart trade
                    self.Plot("Trade Chart", "Trades Taken", self.trade_count)
                    self.trade_count += 1



                elif self.daily_bias == 'bearish' and self.price_hour < self.ema_entry.Current.Value:
                    self.Log("Sell Order")
                    self.Log(f"sl balance: {self.sl_balance}")
                    self.Log(f"balance: {self.current_balance}")
                    self.Log(f"tp balance: {self.tp_balance}")
                    self.Log(f"risk: ${self.current_risk}")

                    #entry
                    entry_order = self.MarketOrder(self.spx500_min, self.lot_size_sell)

                    #trades taken
                    self.trades_taken += 1

                    #chart trade
                    self.Plot("Trade Chart", "Trades Taken", self.trade_count)
                    self.trade_count += 1
        #--------------------------------------------------------------------------



    '''def ResetAlgorithm(self):
        self.Liquidate()
        self.trades_taken = 0
        self.sl_balance = 0
        self.tp_balance = 0
        self.be_balance = 0'''


#====================================================================================================================================================
