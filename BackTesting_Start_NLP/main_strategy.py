from datetime import datetime, timedelta
from fin_setiment import estimate_sentiment
import alpaca_trade_api as trade
import numpy as np
import time
import pytz

# Define the Pacific Time Zone
pacific_tz = pytz.timezone('America/Los_Angeles')

KEY = {
    "API_KEY": "PKRZNR6AK4ACDNEUH2SK",
    "API_SECRET": "KhS30cEFNtfRGMtxW0Y9TOWwpAtlkf6QhKopqGMx",
    "PAPER" : True
}
api = trade.REST(
    base_url = "https://paper-api.alpaca.markets" if KEY["PAPER"] else "https://api.alpaca.markets",
    key_id = KEY["API_KEY"],
    secret_key = KEY["API_SECRET"]
)
account = api.get_account()
print("ACCOUNT:", account.status, "\n")

class TradingBot():
    def __init__(self, symbol, trade_interval_hrs, cash_at_risk):
        self.symbols_cache = {symbol}
        self.symbols_portfolio = {}
        self.cash_at_risk = cash_at_risk
        self.last_trade = {}
        self.trade_interval_hrs = trade_interval_hrs

    def get_cash(self):
        try:
            return float(api.get_account().cash)
        
        except Exception as error:
            return -1

    def get_price_data(self, symbol):
        try:
            stock = api.get_bars(symbol, timeframe="1D", limit=30).df
            # Check if stock data is returned
            if stock.empty:
                return -1

            return stock['close']
        
        except Exception as error:
            print(f"Error fetching data: {error}")
            return -1
    
    def get_metrics(self, symbol):
        stock = self.get_price_data(symbol=symbol)
        if stock == -1:
            return -1, -1, -1
        
        # Process the stock data
        def calculate_rsi(data, window=14):
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        # Calculate MACD Histogram
        def calculate_macd_histogram(data, fast_period=12, slow_period=26, signal_period=9):
            # Fast and Slow EMAs
            ema_fast = data['close'].ewm(span=fast_period, adjust=False).mean()
            ema_slow = data['close'].ewm(span=slow_period, adjust=False).mean()
            macd = ema_fast - ema_slow
            # MACD Signal Line (9-period EMA of MACD)
            signal = macd.ewm(span=signal_period, adjust=False).mean()
            # MACD Histogram (difference between MACD and Signal Line)
            macd_histogram = macd - signal
            return macd_histogram
        
        last_price = stock['close'].iloc[-1]
        rsi = calculate_rsi(stock).iloc[-1]
        macd = calculate_macd_histogram(stock).iloc[-1]

        if np.isnan(rsi) or np.isnan(macd):
            return -1, -1, -1

        return last_price, rsi, macd
    
    def get_trail_percent(self, symbol, bias = 0.05):
        stock = self.get_price_data(symbol=symbol)
        if stock == -1:
            return -1
        
        def calculate_normalized_volatility(prices):
            returns = prices.pct_change()  # daily returns
            volatility = np.std(returns)  # standard deviation of daily returns
            mean_price = np.mean(prices)  # average price
            normalized_volatility = volatility / mean_price  # normalize the volatility by mean price
            return normalized_volatility
        
        return calculate_normalized_volatility(stock) + bias
    
    def get_sentiment(self, symbol, hours_prior= 24):
        news_start = (datetime.now(pacific_tz) - timedelta(hours=hours_prior)).strftime("%Y-%m-%dT%H:%M:%SZ")
        news_end = datetime.now(pacific_tz).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        try:
            news_list = api.get_news(symbol=symbol, start=news_start, end=news_end, limit=20)

            news = []
            for n in news_list:
                if hasattr(n, 'headline'):
                    self.symbols_cache.update(n.symbols)
                    news.append(f"{n.headline}. {n.summary}")
                
            if not news:
                return 0.5, "neutral"  
            
            probability, sentiment = estimate_sentiment(news)
            return probability, sentiment
        
        except Exception as error:
            return 0.5, "neutral"  
        
    def order(self, symbol, qty, side):
        try:
            if side in ["buy", "sell"]:
                api.submit_order(
                    symbol= symbol,
                    qty= qty,
                    side= side,
                    type= 'trailing_stop',
                    trail_percent= self.get_trail_percent(symbol)
                )
                print("Ordered: ", symbol, qty, side, datetime.now(pacific_tz))
        except Exception as e:
            print(e)

    def position_sizing(self, symbol, sentiment):
        cash = self.get_cash()
        
        last_price, rsi, macd = self.get_metrics(symbol)

        if sentiment == "buy":
            buy_size = round(((cash * self.cash_at_risk) / last_price), 0)
            # Over Sold
            if rsi <= 30:
                buy_size *= 1.5
            # Over Bought
            elif rsi >= 70:
                buy_size *= 0.5
            # Bullish Trend
            if macd > 0.1:
                buy_size *= 1.2
            # Bearish Trend
            elif macd < 0:
                buy_size *= 0.8

            if cash < (last_price * buy_size):
                return cash, last_price, 0
            return cash, last_price, buy_size

        elif sentiment == "sell":
            try:
                position = api.get_position(symbol)
                sell_size = float(position.qty)  # Convert to float for safety

                if rsi <= 30:
                    sell_size *= 0.5
                elif rsi >= 70:
                    sell_size *= 1.5
                if macd > 0.1:
                    sell_size *= 0.8
                elif macd < 0:
                    sell_size *= 1.2

                return cash, last_price, sell_size

            except trade.rest.APIError as e:
                print(f"No open position for {symbol}. Cannot sell. Error: {e}")
                return cash, last_price, 0  # No position to sell
    # TODO: integrate a stock screener such that I can pull the stocks with the most potential first
    def main(self):
        # Limit for stocks you should analyze
        for _ in range(100):
            if not self.symbols_cache:
                if self.symbols_portfolio:
                    self.symbols_cache = self.symbols_portfolio
                else:
                    self.symbols_cache = {"NVDA", "AAPL", "MSFT", "GOOG"}
                return
            
            symbol = self.symbols_cache.pop()

            probability, sentiment = self.get_sentiment(symbol=symbol, hours_prior=self.trade_interval_hrs)

            cash, last_price, quantity = self.position_sizing(symbol=symbol, sentiment=sentiment)
            if -1 in (cash, last_price, quantity):
                return
            
            if probability > 0.7:
                if sentiment == "positive" and cash > (last_price * quantity):
                    if self.last_trade.get(symbol) == "sell":
                        api.close_position(symbol=symbol)
                    self.order(symbol=symbol, qty=quantity, side="buy")
                    self.last_trade[symbol] = "buy"
                    self.symbols_portfolio.add(symbol)

                elif sentiment == "negative":
                    if self.last_trade.get(symbol) == "buy":
                        api.close_position(symbol=symbol)
                    self.order(symbol=symbol, qty=quantity, side="sell")
                    self.last_trade[symbol] = "sell"
                    self.symbols_portfolio.remove(symbol)
                
        if self.symbols_portfolio:
            self.symbols_cache = self.symbols_portfolio
        else:
            self.symbols_cache = {"NVDA", "AAPL", "MSFT", "GOOG"}
        return
    # TODO: add Multi-Threading for Scalibility
    def run(self):
        while True:
            if 6 <= datetime.now(pacific_tz).hour < 13:
                self.main()
            print(f"Waiting for the next interval... {datetime.now(pacific_tz)}")
            time.sleep(max(1, self.trade_interval_hrs * 60 * 60 - 5))


if __name__ == "__main__":
    start_symbol = "NVDA"
    trade_interval_hrs = 1
    cash_at_risk = 0.1

    t = TradingBot(symbol=start_symbol, trade_interval_hrs=trade_interval_hrs, cash_at_risk=cash_at_risk)
    print("Starting...")
    t.run()
    print("Ending...")