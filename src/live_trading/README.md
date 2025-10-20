# Live Trading with MA Crossover Strategy

## Overview

This live trading system executes **REAL trades** with **REAL money** on Zerodha using a 20/50 Moving Average Crossover strategy.

## Key Features

✅ **Automatic Data Management**
- Automatically downloads historical data when you start live trading
- Updates data daily if outdated
- No manual data download required!

✅ **Dual Data Sources**
- **Historical Data**: Local CSV files (for MA calculation)
- **Real-time Prices**: NSE India API (for current prices)

✅ **Safety Features**
- Manual trade approval required
- Position limits enforced
- Stop loss (10%) and take profit (30%)
- Comprehensive logging

## How It Works

### 1. Data Flow

```
START live_ma_crossover.py
    ↓
Check Historical Data
    ↓
    ├─ Data missing? → Download automatically
    ├─ Data outdated? → Update automatically
    └─ Data OK? → Continue
    ↓
Calculate MAs from historical data
    ↓
Fetch real-time prices from NSE India
    ↓
Detect Golden Cross (20 MA > 50 MA)
    ↓
Execute trades on Zerodha
```

### 2. Moving Average Calculation

- Uses **100 days** of historical data
- Calculates **20-day MA** and **50-day MA**
- Detects **Golden Cross**: 20 MA crosses above 50 MA

### 3. Real-time Price Fetching

Tries multiple sources in order:
1. **Zerodha LTP** (primary)
2. **NSE India API** (fallback)

### 4. Trade Execution

- Entry: Golden Cross detected
- Exit: Stop Loss (-10%) or Take Profit (+30%)
- Product: CNC (delivery)
- Approval: Manual confirmation required

## Quick Start

### First Time Setup

1. **Configure Zerodha credentials**:
   ```bash
   # Copy template
   cp config_template.json config.json

   # Edit with your credentials
   nano config.json
   ```

2. **Authenticate**:
   ```bash
   python3 authenticate.py
   ```

### Running Live Trading

Simply run the live trading script:

```bash
python3 src/live_trading/live_ma_crossover.py
```

That's it! The script will:
- ✅ Check for historical data
- ✅ Download/update data automatically if needed
- ✅ Calculate MAs
- ✅ Start monitoring for signals

## Files

- `live_ma_crossover.py` - Main live trading script
- `zerodha_broker.py` - Zerodha API integration
- `nse_realtime.py` - NSE India real-time price fetcher
- `config.json` - Your Zerodha API credentials
- `authenticate.py` - One-time Zerodha authentication
- `test_integration.py` - Test all components

## Configuration

Edit the following in `live_ma_crossover.py`:

```python
# Strategy Parameters
ma_short_period = 20              # 20-day MA
ma_long_period = 50               # 50-day MA
stop_loss_pct = 10.0              # 10% stop loss
take_profit_pct = 30.0            # 30% take profit

# Risk Management
max_positions = 3                 # Maximum simultaneous positions
max_trade_size = 10000            # Maximum ₹50,000 per trade

# Safety Settings
require_manual_approval = True    # Require manual approval
check_interval_seconds = 300      # Check every 5 minutes
trading_start_time = "09:20"      # Start trading
trading_end_time = "15:00"        # Stop trading
```

## Data Management

### Automatic Download

When you start live trading, the script:

1. **Checks if data exists**
   - If not, downloads automatically

2. **Checks if data is current**
   - If outdated (not updated today), downloads fresh data

3. **Downloads Nifty 50 stocks**
   - From 2022-01-01 to today
   - Saves to `data/nifty50/`

### Manual Download (Optional)

If you want to download data manually:

```bash
python3 src/download_data.py
```

## Testing

Test all components before live trading:

```bash
python3 src/live_trading/test_integration.py
```

This will test:
- ✅ NSE India real-time fetcher
- ✅ Historical data loading
- ✅ MA calculation
- ✅ Zerodha configuration

## Monitoring

During trading, you'll see:

```
================================================================================
SCANNING FOR OPPORTUNITIES - 2025-10-18 09:25:00
================================================================================
🎯 GOLDEN CROSS DETECTED: TCS
   20 MA: 2950.25 | 50 MA: 2940.50

================================================================================
MONITORING POSITIONS - 2025-10-18 09:30:00
================================================================================
TCS: Entry ₹2,950.00 | Current ₹2,960.00 | P&L +0.34%
```

## Logs

All activity is logged to:
- `live_trading_strategy.log` - Trading activity
- `live_trades_YYYYMMDD_HHMMSS.json` - Completed trades

## Important Notes

⚠️ **REAL MONEY WARNING**
- This executes REAL trades with REAL money
- Always use manual approval mode for safety
- Start with small position sizes
- Test thoroughly in paper trading first

⚠️ **Data Requirements**
- Strategy needs ~100 days of historical data
- Data is automatically managed by the script
- Updates daily when you start trading

⚠️ **Market Hours**
- Trading: 09:20 AM - 3:00 PM IST
- Outside hours: Script waits until market opens

## Troubleshooting

### Data Issues

If data download fails:
```bash
# Run manual download
python3 src/download_data.py
```

### Authentication Issues

If Zerodha authentication fails:
```bash
# Re-authenticate
python3 src/live_trading/authenticate.py
```

### Real-time Price Issues

If NSE India API fails:
- Check internet connection
- Script will automatically use Zerodha LTP as fallback
- Rate limiting: Max 1 request per 2 seconds

## Support

For issues or questions:
1. Check logs: `live_trading_strategy.log`
2. Run integration test: `python3 test_integration.py`
3. Verify data: Check `data/nifty50/` folder

## Disclaimer

This is for educational purposes. Use at your own risk. Always:
- Test thoroughly before live trading
- Start with small amounts
- Use stop losses
- Monitor actively
- Understand the strategy fully
