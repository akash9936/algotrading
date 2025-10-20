# Stock Models

A collection of Python-based stock market analysis and trading strategy tools for backtesting and evaluating investment strategies using technical indicators.

## Overview

This repository contains multiple trading strategies and analysis tools focused on Indian stock markets (particularly BSE SENSEX) using technical indicators like RSI (Relative Strength Index) and machine learning for stock prediction.

## Features

### 1. Web Scraping & Machine Learning Prediction ([Scrap.py](Scrap.py))
- Web scraping capabilities for stock data (both static and dynamic using Selenium)
- Machine learning-based stock prediction using Logistic Regression
- Automated data collection from NSE India
- Model training and persistence using scikit-learn
- Features:
  - `WebScraper`: Scrapes stock data from websites
  - `StockPredictor`: Trains ML models to predict stock movements

### 2. RSI-Based Trading Strategy ([RSIStock.py](RSIStock.py))
- Backtests RSI-based trading strategy on SENSEX
- Implements stop-loss and take-profit mechanisms
- Features:
  - Calculates RSI for identifying oversold/overbought conditions
  - Tests multiple holding periods (1-30 days) to find optimal strategy
  - Transaction cost consideration
  - Trade-by-trade analysis with profit/loss tracking

**Parameters:**
- Initial Investment: ₹100,000
- RSI Threshold: 30 (oversold)
- Stop Loss: 5%
- Take Profit: 10%
- Transaction Cost: 0.1%

### 3. Minimum Stock Buy Strategy ([MinimumStockBuy.py](MinimumStockBuy.py))
- RSI-based stock selection and backtesting
- Simulates buying stocks during oversold conditions
- Tests different holding periods
- Provides detailed trade analysis

**Key Features:**
- Fetches data from Yahoo Finance
- RSI calculation with customizable window (default: 14)
- Backtest strategy with configurable RSI thresholds (default: 30/70)
- Average return calculation per trade

### 4. Enhanced Investment Strategy ([macProfit.py](macProfit.py))
- Comprehensive investment strategy combining multiple indicators
- Features:
  - Daily opening price comparison logic
  - RSI-based oversold signal detection
  - Automatic stop-loss and take-profit execution
  - Portfolio value tracking over time
  - Visual performance charts with RSI overlay

**Strategy Rules:**
- Doubles investment when stock opens lower than previous day
- Increases investment by 1.5x when RSI shows oversold (<30)
- Automatic sell on 5% loss (stop-loss)
- Automatic sell on 10% gain (take-profit)

**Outputs:**
- Daily portfolio value tracking
- Complete trade log
- Performance visualization charts
- CSV exports for detailed analysis
- Strategy comparison tool for parameter optimization

## Installation

```bash
pip install pandas numpy yfinance scikit-learn matplotlib beautifulsoup4 selenium requests joblib
```

### Additional Requirements
- Chrome WebDriver (for Selenium-based scraping)

## Usage

### Running RSI Strategy Backtest
```bash
python RSIStock.py
```

### Running Minimum Stock Buy Strategy
```bash
python MinimumStockBuy.py
```

### Running Enhanced Investment Strategy
```bash
python macProfit.py
```

### Running Web Scraper & ML Predictor
```bash
python Scrap.py
```

## Configuration

Each script has configurable parameters at the top:

- **Date Range**: Modify `start_date` and `end_date`
- **Investment Amount**: Adjust `initial_investment` or `base_amount`
- **RSI Parameters**: Change `rsi_threshold`, `rsi_window`
- **Risk Management**: Modify `stop_loss_pct`, `take_profit_pct`
- **Ticker Symbol**: Change stock/index symbol (e.g., "^BSESN" for SENSEX)

## Output Files

- `investment_daily_results.csv`: Daily portfolio performance
- `investment_trade_log.csv`: Detailed trade history
- `enhanced_investment_results.png`: Performance visualization chart
- `stock_predictor.joblib`: Trained ML model
- `strategy_comparison.csv`: Parameter optimization results

## Technical Indicators

### RSI (Relative Strength Index)
- Momentum oscillator measuring speed and magnitude of price changes
- Values range from 0 to 100
- RSI < 30: Oversold condition (potential buy signal)
- RSI > 70: Overbought condition (potential sell signal)

## Risk Management

All strategies implement risk management techniques:
- **Stop-Loss**: Automatic sell to limit losses
- **Take-Profit**: Automatic sell to lock in gains
- **Transaction Costs**: Factored into profit calculations
- **Position Sizing**: Dynamic investment amounts based on signals

## 🚀 NEW: Centralized Data System

**Download once, test unlimited strategies!**

### Quick Start:
```bash
# 1. Download all data once (5 minutes)
python download_data.py

# 2. Run any strategy instantly (10-20 seconds)
python strategy_rsi.py

# 3. Create your own strategies using the same data
cp strategy_template.py strategy_YOUR_IDEA.py
# Edit and run!
```

### File Organization:
```
data/
├── nifty50/     # All NIFTY 50 stocks
├── indices/     # Market indices
└── custom/      # Your custom stocks

Strategies:
├── strategy_rsi.py          # RSI-based strategy
├── strategy_template.py     # Template for new strategies
└── your_strategies...       # Your custom strategies
```

### Benefits:
- ✅ 15-20x faster after initial download
- ✅ Test multiple strategies on same data
- ✅ No repeated API calls
- ✅ Easy strategy comparison

### Documentation:
- **[DATA_FOLDER_GUIDE.md](DATA_FOLDER_GUIDE.md)** - Complete guide to data system
- **[CACHE_USAGE_GUIDE.md](CACHE_USAGE_GUIDE.md)** - Legacy caching system

## Available Stock Tickers

See [indian_stock_tickers.py](indian_stock_tickers.py) for 100+ Indian stock tickers including:
- NIFTY 50 stocks
- Major indices (SENSEX, NIFTY, BANK NIFTY)
- Mid-cap and PSU stocks
- Emerging sector stocks

## Limitations

- Historical backtesting does not guarantee future performance
- Market conditions change and past patterns may not repeat
- Transaction costs and slippage may vary in real trading
- Strategies are designed for educational purposes
- Web scraping functionality may break if website structures change

## Contributing

Feel free to fork this repository and submit pull requests for improvements.

## License

This project is provided as-is for educational and research purposes.

## Disclaimer

These tools are for educational and research purposes only. They are not financial advice. Always consult with a qualified financial advisor before making investment decisions. Past performance does not guarantee future results.
