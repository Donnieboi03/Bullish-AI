from datetime import datetime, timedelta
from fin_setiment import estimate_sentiment
import alpaca_backtrader_api
import alpaca_trade_api as trade
import numpy as np
import pandas as pd
import backtrader as bt
import pytz
import matplotlib.pyplot as plt

# ✅ Alpaca API Keys
KEY = {
    "API_KEY": "PKRZNR6AK4ACDNEUH2SK",
    "API_SECRET": "KhS30cEFNtfRGMtxW0Y9TOWwpAtlkf6QhKopqGMx",
    "PAPER": True
}

# Create Alpaca API object for backtesting (historical data)
api = trade.REST(
    base_url="https://paper-api.alpaca.markets" if KEY["PAPER"] else "https://api.alpaca.markets",
    key_id=KEY["API_KEY"],
    secret_key=KEY["API_SECRET"]
)

store = alpaca_backtrader_api.AlpacaStore(
    key_id=KEY["API_KEY"],
    secret_key=KEY["API_SECRET"],
    paper=KEY["PAPER"]
)

cerebro = bt.Cerebro()
# Set Alpaca Broker
Broker = store.getbroker()
cerebro.setbroker(Broker)

# ✅ Backtrader Strategy Definition
class SentimentStrategy(bt.Strategy):
    params = {
        'symbol': 'AAPL',
        'cash_at_risk': 1.0,
        'stop_loss_pct': 0.05,  # 5% stop loss
        'start': datetime.now(),
        'end': datetime.now(),
        'bars': None
    }

    def __init__(self):
        self.symbol = self.params.symbol
        self.cash_at_risk = self.params.cash_at_risk
        self.iteration = self.params.start.replace(tzinfo=pytz.utc)  # Ensure UTC timezone
        self.last_trade = None
        self.data_close = self.datas[0].close  # Close price for Backtrader data
        self.equity_curve = []  
        self.bar_curve = self.params.bars
        self.stop_loss_pct = self.params.stop_loss_pct
        self.entry_price = None

    def get_cash(self):
        return self.broker.get_cash()

    def get_last_price(self):
        return self.data_close[0]  

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price()
        quantity = round((cash * self.cash_at_risk) / last_price, 0)
        return cash, last_price, quantity

    def get_sentiment(self, hours_prior=6):
        """
        Fetch news from the past `hours_prior` hours instead of days.
        """
        news_start = (self.iteration - timedelta(hours=hours_prior)).strftime("%Y-%m-%dT%H:%M:%SZ")
        news_end = self.iteration.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        news_list = api.get_news(symbol=self.symbol, start=news_start, end=news_end, limit=10)
        news = [(n.headline + ". " + n.summary) for n in news_list if hasattr(n, 'headline') and hasattr(n, 'summary')]

        if not news:
            return 0.5, "neutral"  # Default to neutral if no news is found
        
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def next(self):
        # Convert iteration time to EST (market time)
        current_time = self.iteration.astimezone(pytz.timezone('America/New_York'))

        # Skip non-trading hours
        if current_time.hour < 9 or (current_time.hour == 9 and current_time.minute < 30) or current_time.hour >= 16:
            self.iteration += timedelta(hours=3)
            return

        cash, last_price, quantity = self.position_sizing()
        if last_price is None:
            return  

        # Stop-Loss Condition
        if self.entry_price and last_price < (self.entry_price * (1 - self.stop_loss_pct)):
            print(f"Stop-loss triggered at {last_price:.2f}, Selling position.")
            self.close()
            self.last_trade = "sell"
            self.entry_price = None  
            return

        probability, sentiment = self.get_sentiment()

        if cash > last_price and probability > 0.5:
            print(probability, sentiment)
            if sentiment == "positive":
                if self.last_trade == "sell": 
                    self.close()
                self.buy(size=quantity)
                self.last_trade = "buy"
                self.entry_price = last_price
                
            elif sentiment == "negative":
                if self.last_trade == "buy": 
                    self.close()
                self.sell(size=quantity)
                self.last_trade = "sell"
                self.entry_price = None

        self.iteration += timedelta(hours=3)  # Move forward by 3 hours

        # Append the portfolio value to the equity curve list
        self.equity_curve.append(self.broker.get_value())

    def stop(self):
        print("Backtest Complete")
        self.plot_equity_curve()

    def plot_equity_curve(self):
        plt.figure(figsize=(10, 6))

        stock_prices = self.bar_curve['close'].values
        normalized_stock_prices = (stock_prices - stock_prices.min()) / (stock_prices.max() - stock_prices.min())

        equity_curve = np.array(self.equity_curve)
        normalized_equity_curve = (equity_curve - equity_curve.min()) / (equity_curve.max() - equity_curve.min())

        plt.plot(normalized_stock_prices, label='Stock Price (Normalized)', color='green')
        plt.plot(normalized_equity_curve, label='Strategy Equity Curve (Normalized)', color='blue')

        plt.title(f'{self.symbol} Strategy vs. Stock Price')
        plt.xlabel('Time (Hours)')
        plt.ylabel('Normalized Value')
        plt.legend(loc='upper left')

        plt.show()

        
# ✅ Setup for Backtesting using Alpaca Data and Backtrader
if __name__ == "__main__":
    account = api.get_account()
    print("ACCOUNT STATUS:", account.status, "\n")

    # Define start and end times for hourly trading
    start_date = datetime(2023, 1, 1, 9, 30, tzinfo=pytz.utc)  # Start at market open
    end_date = datetime(2025, 1, 1, 16, 0, tzinfo=pytz.utc)    # End at market close
    symbol = "PLTR"
    
    # ✅ Fetch historical hourly data from Alpaca
    bars = api.get_bars(
        symbol=symbol,  
        timeframe=trade.TimeFrame.Hour,  
        start=start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        end=end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    ).df

    bars.index = pd.to_datetime(bars.index).tz_localize(None)
    bars = bars.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        
    data_feed = bt.feeds.PandasData(dataname=bars)
    
    cerebro = bt.Cerebro()
    cerebro.addstrategy(SentimentStrategy, symbol=symbol, cash_at_risk=1, start=start_date, end=end_date, bars=bars)
    cerebro.adddata(data_feed)
    
    cerebro.broker.set_cash(float(account.cash))

    start_value = cerebro.broker.get_value()
    print(f"Starting Portfolio Value: {cerebro.broker.get_value():.2f}, {symbol} Price: {bars['close'].iloc[0]}")
    
    # Run the Backtrader backtest
    cerebro.run()

    end_value = cerebro.broker.get_value()
    print(f"Ending Portfolio Value: {cerebro.broker.get_value():.2f}, {symbol} Price: {bars['close'].iloc[-1]}")

    print(f"Strategy Equity {end_value/start_value}")
    print(f"Standard Equity {bars['close'].iloc[-1]/bars['close'].iloc[0]}")
