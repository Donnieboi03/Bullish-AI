import yfinance as yf

class Stock:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.cache: list = []

    def get_rating(self, ticker: str) -> tuple:
        try:
            stock = yf.Ticker(ticker);
            info = stock.get_info();  # Fetch info once
            PRICE = info.get("currentPrice", 0);
            MA50 = info.get("fiftyDayAverage", 0);
            MA200 = info.get("twoHundredDayAverage", 0);
            return float(PRICE), float(MA50), float(MA200);
        except Exception as error:
            print("Get Error:", error)
            return 0, 0, 0  # Return zeros on error

    def _stock_scrapper_(self, search_limit: int) -> list:
        queue = [self.symbol]
        viewed = set([self.symbol])  # Use a set for faster lookups
        count = 0

        while queue and count < search_limit:
            current = queue.pop(0)
            try:
                stock = yf.Ticker(current)
                articles = stock.get_news()
                for article in articles:
                    for relevant_ticker in article['relatedTickers']:
                        if relevant_ticker not in viewed and relevant_ticker[0] != "^":
                            viewed.add(relevant_ticker)
                            queue.append(relevant_ticker)
                            count += 1
                            if count >= search_limit:
                                break
            except Exception as error:
                pass;

        return list(viewed)

    def related_stocks(self, separation_limit: int, mod: str = "") -> list:
        arr = self._stock_scrapper_(separation_limit)
        for TICKER in arr:
            PRICE, MA50, MA200 = self.get_rating(TICKER);
            stats = {
                "TICKER": TICKER,
                "PRICE": PRICE,
                "MA50": MA50,
                "MA200": MA200
            }

            if mod == "swing":
                if (MA200 < PRICE < MA50 + (MA50 * 0.05)):
                    self.cache.append(stats)
            else:
                self.cache.append(stats)

# Example usage
#stock = Stock("AAPL")
#stock.related_stocks(100, "swing")
#print(stock.cache);
