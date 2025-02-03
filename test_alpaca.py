import alpaca_trade_api as trade
import pandas as pd
from datetime import datetime, timedelta

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

class trade_bot():
    def __init__(self, symbol:str, cash_yeild:int= 0.5, start: str= datetime(2020, 1, 1), end: str= datetime.now()):
        self.symbol= symbol
        self.cash_yeild= 0.5
        self.start= start
        self.end= end
        self.symbol_list: dict[dict]= {}
        
    def order(self, qty:int, side: str, take_p:int= 1.25, stop_l:int= 0.95):
        try:
            if side == "buy" or "sell":
                api.submit_order(
                    symbol= self.symbol,
                    qty= qty,
                    side= side,
                    take_profit= take_p,
                    stop_loss= stop_l
                )
                print("Ordered: ", self.symbol, qty, side, datetime.now())
        except Exception as e:
            print(e)
            
    def pre_processing(self, data_list) ->dict:
        def pack(data) ->tuple:
            try:
                stock = api.get_bars(
                    symbol,
                    timeframe="1D",
                    start=(self.start - timedelta(days=75)).strftime("%Y-%m-%d"),
                    end=self.start.strftime("%Y-%m-%d")
                ).df
                
                # Check if stock data is returned
                if stock.empty:
                    return 0, 0, 0, 0
                
                # Process the stock data
                def calculate_rsi(data, window=14):
                    delta = data['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    return rsi
                
                stock["ma10"] = stock['close'].rolling(window=10).mean()  # Calculate MA10
                stock["ma50"] = stock['close'].rolling(window=50).mean()  # Calculate MA50
                stock['rsi'] = calculate_rsi(stock) # Calculate RSI
                
                data = (
                    float(stock["close"].iloc[-1]),
                    float(stock["ma10"].iloc[-1]),
                    float(stock["ma50"].iloc[-1]),
                    int(stock["rsi"].iloc[-1])
                )
                return data
            
            except Exception as error:
                return 0, 0, 0, 0  # Return zeros on error
            
        # Fetch the historical bars
        label_list: dict[str]= {}
        for symbol in data_list:
            PRICE, MA10, MA50, RSI = pack(symbol)
            # filter hueristic -> Start of Trend that is not Overbought
            if MA50 < MA10 and RSI < 70:
                self.symbol_list[symbol] = {
                    "ma10": MA10,
                    "ma50": MA50,
                    "rsi": RSI,
                }
                FUTURE_PRICE = stock = api.get_bars(
                    symbol,
                    timeframe="1D",
                    start= (self.start + timedelta(days=7)).strftime("%Y-%m-%d"),
                    end= (self.start + timedelta(days=7)).strftime("%Y-%m-%d")
                ).df['close'].iloc[-1]
                # BUY, SELL, or HOLD labels
                if FUTURE_PRICE >= PRICE * (1.05):
                    label_list[symbol] = 1
                elif FUTURE_PRICE < (PRICE * .95):
                    label_list[symbol] = 0
                else:
                    label_list[symbol] = 0.5
                    
        print("Finished pre processing")
        print(pd.DataFrame(self.symbol_list), "\n")
        return self.symbol_list, label_list
       
    def stock_data(self, period) -> list:
        start: str= (self.start - timedelta(days= period)).strftime("%Y-%m-%d")
        end: str= self.start.strftime("%Y-%m-%d")
        queue = [self.symbol]
        viewed = set([self.symbol])  # Use a set for faster lookups
        while queue and start <= end:
            current = queue.pop(0)
            try:
                articles = api.get_news(current, start, end, 3)
                for article in articles:
                    for symbol in article.symbols:
                        if symbol not in viewed and symbol[:3] != "CSE" and symbol[:3] != "TSX":
                            viewed.add(symbol)
                            queue.append(symbol)
                period -= 1
                start= (self.start - timedelta(period)).strftime("%Y-%m-%d")
                
            except Exception as error:
                print(error, "defefefefef")
                pass
            
        print("Finished data scraping")
        print(list(viewed), "\n")
        return list(viewed)
            
    #def strat(self):
#t= trade_bot("AAPL")
#data, labels = t.pre_processing(t.stock_data(5))

# USE torch NN
# FEATURES: ma10, ma50, rsi, last_buy/sell
# if last_buy is true and stock is buy; then buy more and maybe adjust
# if last_buy is false and stock is sell; then sell more and maybe adjust
# if last_buy is false and stock is buy; then buy and maybe adjust
# simple predictor either BUY or SELL output
# layer 4 -> ... -> 2