# 📈 Bullish-AI – AI-Powered Sentiment-Driven Trading Agent

Jarvis is an automated trading bot built in Python that uses **technical indicators**, **news sentiment**, and **Alpaca's API** to make intelligent trading decisions. It combines real-time price analysis with NLP-powered sentiment evaluation to simulate autonomous, risk-managed stock trading.

---

## 🧠 Features

- 📰 **News Sentiment Analysis** — Leverages `FinBERT` (via `estimate_sentiment`) to analyze stock news.
- 📊 **Technical Indicators** — Calculates **RSI** and **MACD Histogram** for price momentum and reversal signals.
- 💼 **Risk-Based Position Sizing** — Dynamically adjusts trade size based on sentiment strength, RSI, and MACD.
- 🔁 **Automated Trading Loop** — Trades every N hours (configurable) during market hours.
- 📉 **Trailing Stop Orders** — Uses trailing stop loss for exit automation.
- ☁️ **Alpaca Paper Trading** — Fully integrated with Alpaca’s paper trading API.

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| `Alpaca API` | Brokerage and real-time data |
| `FinBERT` | Financial news sentiment analysis |
| `NumPy` | Technical indicator calculations |
| `pytz` | Timezone management (Pacific Time) |
| `datetime` | Trade interval and market hours control |

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/jarvis-trading-bot.git
cd jarvis-trading-bot
