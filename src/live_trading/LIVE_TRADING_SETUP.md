# Live Trading Setup Guide

## ⚠️ IMPORTANT WARNINGS

**THIS SYSTEM EXECUTES REAL TRADES WITH REAL MONEY!**

- Start with a **small amount** of capital for testing
- Understand that you can **lose money**
- Always monitor the system when it's running
- Test thoroughly before using significant capital
- The developers are NOT responsible for any losses

---

## Prerequisites

1. **Zerodha Trading Account** with sufficient funds
2. **Zerodha Kite Connect API** subscription (₹2,000/month)
3. **Python 3.8+** installed
4. Basic understanding of stock trading and technical analysis

---

## Step 1: Get Zerodha API Credentials

### 1.1 Subscribe to Kite Connect API

1. Visit [https://kite.trade/](https://kite.trade/)
2. Login with your Zerodha credentials
3. Subscribe to Kite Connect (₹2,000/month + 18% GST)
4. Create a new app:
   - App Name: `MA Crossover Strategy` (or any name)
   - App Type: `Connect`
   - Redirect URL: `http://127.0.0.1:5000/callback` (or any URL)

### 1.2 Get API Key and Secret

1. After creating the app, you'll receive:
   - **API Key** (e.g., `abc123xyz`)
   - **API Secret** (e.g., `def456uvw`)
2. **Keep these credentials secure!** Never share them or commit to Git

---

## Step 2: Install Dependencies

### 2.1 Install Python packages

```bash
pip install -r requirements_live_trading.txt
```

This will install:
- `kiteconnect` - Zerodha API library
- Other required dependencies

---

## Step 3: Configure the System

### 3.1 Create config file

```bash
cd src/live_trading
cp config_template.json config.json
```

### 3.2 Edit config.json

Open `config.json` and add your credentials:

```json
{
  "api_key": "YOUR_ACTUAL_API_KEY",
  "api_secret": "YOUR_ACTUAL_API_SECRET",
  "access_token": null
}
```

**NEVER commit config.json to Git!** (It's already in .gitignore)

---

## Step 4: First-Time Login

### 4.1 Run the live trading script

```bash
cd /Users/akashsingh/Downloads/propelld/Codes/StockProjects/StockBackTest
python3 src/live_trading/live_ma_crossover.py
```

### 4.2 Complete authentication

The script will:
1. Show you a login URL
2. Ask you to open it in a browser
3. After you login, Zerodha will redirect to a URL like:
   ```
   http://127.0.0.1:5000/callback?request_token=XXXXXX&action=login&status=success
   ```
4. Copy the `request_token` value (the `XXXXXX` part)
5. Paste it into the terminal when prompted
6. The script will generate an `access_token` and save it to config.json

**Note:** Access tokens expire daily. You'll need to re-login each day.

---

## Step 5: Verify Setup

### 5.1 Check connection

The script will show:
- Your Zerodha account name
- Available cash balance
- List of stocks to monitor

### 5.2 Review strategy parameters

The strategy uses:
- **Entry Signal:** 20 MA crosses above 50 MA (Golden Cross)
- **Stop Loss:** 10%
- **Take Profit:** 30%
- **Max Positions:** 3 simultaneous positions
- **Capital per Position:** ~₹33,333 (adjustable)
- **Max Trade Size:** ₹50,000 per trade

---

## Step 6: Start Live Trading

### 6.1 Final confirmation

The script will ask for final confirmation:
```
Proceed with live trading? (yes/no):
```

Type `yes` to start.

### 6.2 Trading loop begins

The system will:
1. Check if market is open (9:20 AM - 3:00 PM)
2. Scan for Golden Cross signals every 5 minutes
3. Monitor existing positions for stop loss/take profit
4. **Ask for manual approval** before each trade (by default)

### 6.3 Approve trades

When a trade opportunity is found:
```
================================================================================
⚠️  TRADE APPROVAL REQUIRED
================================================================================
Action:   BUY
Symbol:   TCS
Quantity: 100
Price:    ₹3500.00
Value:    ₹350,000.00
================================================================================
Approve this trade? (yes/no):
```

Type `yes` to execute or `no` to skip.

---

## Step 7: Monitor the System

### 7.1 Real-time logs

The system logs all activity to:
- **Console output** (real-time)
- **live_trading_strategy.log** (file)
- **live_trading.log** (broker operations)

### 7.2 Check positions

The system will show position updates:
```
TCS: Entry ₹3500.00 | Current ₹3550.00 | P&L +1.43%
```

### 7.3 Emergency stop

Press **Ctrl+C** to stop the system gracefully.

---

## Step 8: End of Day

### 8.1 System shutdown

When you stop the system (Ctrl+C), it will:
1. Save all trades to `live_trades_YYYYMMDD_HHMMSS.json`
2. Show summary of active positions and P&L
3. **NOT automatically close positions** (you manage this)

### 8.2 Close positions manually (optional)

If you want to close all positions:

```python
from live_trading.zerodha_broker import ZerodhaBroker
import json

# Load config
with open('src/live_trading/config.json', 'r') as f:
    config = json.load(f)

# Connect
broker = ZerodhaBroker(config['api_key'], config['api_secret'], config['access_token'])

# Close all positions (EMERGENCY USE ONLY!)
broker.close_all_positions()
```

---

## Configuration Options

You can customize the strategy in `src/live_trading/live_ma_crossover.py`:

```python
# Strategy Parameters
ma_short_period = 20              # Short MA period
ma_long_period = 50               # Long MA period
stop_loss_pct = 10.0              # Stop loss %
take_profit_pct = 30.0            # Take profit %

# Risk Management
max_positions = 3                 # Max simultaneous positions
capital_per_position_pct = 33.33  # Capital % per position
max_trade_size = 50000            # Max ₹ per trade

# Safety Settings
require_manual_approval = True    # Require manual approval (RECOMMENDED)
check_interval_seconds = 300      # Check every 5 minutes
trading_start_time = "09:20"      # Start time
trading_end_time = "15:00"        # End time

# Stocks to trade
TRADEABLE_STOCKS = [
    "TCS", "INFY", "RELIANCE", ...
]
```

---

## Safety Features

### Built-in Protections

1. **Manual Approval** - Every trade requires your approval (by default)
2. **Position Limits** - Maximum 3 simultaneous positions
3. **Trade Size Limits** - Maximum ₹50,000 per trade
4. **Trading Hours** - Only trades during market hours (9:20 AM - 3:00 PM)
5. **Stop Loss** - Automatic 10% stop loss
6. **Comprehensive Logging** - All actions are logged

### Recommendations

1. **Start Small** - Begin with minimal capital
2. **Monitor Actively** - Don't leave the system unattended
3. **Review Daily** - Check trade logs and performance
4. **Keep Manual Approval ON** - Don't disable manual approval initially
5. **Set Alerts** - Monitor your Zerodha app for order notifications
6. **Test During Calm Markets** - Avoid highly volatile days initially

---

## Troubleshooting

### Issue: "Access token expired"

**Solution:** Re-login each trading day (access tokens expire daily)

### Issue: "Insufficient funds"

**Solution:** Ensure you have enough cash in your Zerodha account

### Issue: "Order rejected"

**Possible reasons:**
- Stock in ban period (F&O stocks)
- Circuit limits hit
- Invalid quantity (check lot size for derivatives)
- Insufficient margin

**Solution:** Check the error message in logs and Zerodha app

### Issue: "No historical data"

**Solution:**
- Ensure stock symbol is correct (use NSE format: "TCS" not "TCS.NS")
- Check if the stock has sufficient trading history (50+ days)

### Issue: Script crashes

**Solution:**
- Check logs for error messages
- Verify internet connection
- Ensure Zerodha API is working (check https://kite.trade/docs)

---

## Important Notes

### Daily Workflow

1. **Morning (before 9:15 AM)**
   - Run the script
   - Complete authentication (access token expires daily)
   - Verify connection and available funds
   - Confirm start

2. **During Market Hours (9:20 AM - 3:00 PM)**
   - Monitor console/logs
   - Approve/reject trades as they appear
   - Check positions periodically

3. **End of Day (after 3:30 PM)**
   - Stop the script (Ctrl+C)
   - Review trade logs
   - Decide whether to hold overnight or square off

### Market Holidays

The system doesn't check for market holidays automatically. **Don't run the system on market holidays!**

### Data Costs

- Zerodha Kite Connect: ₹2,000/month + 18% GST
- Historical data: Included in API subscription
- Real-time data: Included in API subscription

### Tax Implications

- All trades executed are reported to tax authorities
- Maintain proper records for tax filing
- Consult a tax advisor for your specific situation

---

## File Structure

```
src/
├── live_trading/
│   ├── __init__.py                    # Package init
│   ├── zerodha_broker.py              # Broker integration
│   ├── live_ma_crossover.py           # Live trading strategy
│   ├── config_template.json           # Config template
│   ├── config.json                    # Your credentials (DO NOT COMMIT!)
│   └── .gitignore                     # Ignore sensitive files
├── strategy/
│   └── strategy_ma_20_50_crossover.py # Backtest version
└── ...

Logs and data:
├── live_trading_strategy.log          # Strategy log
├── live_trading.log                   # Broker operations log
└── live_trades_YYYYMMDD_HHMMSS.json  # Trade records
```

---

## Support and Resources

### Zerodha Documentation
- Kite Connect Docs: https://kite.trade/docs/connect/v3/
- API Python Client: https://github.com/zerodhatech/pykiteconnect

### Getting Help
- Zerodha Support: https://support.zerodha.com/
- Kite Connect Forum: https://kite.trade/forum/

---

## Disclaimer

This software is provided "as is" without warranty of any kind. Trading in stocks involves risk of loss. Past performance (from backtests) does not guarantee future results. The creators and contributors are not responsible for any financial losses incurred through use of this software.

**Use at your own risk. Trade responsibly.**

---

## Quick Start Checklist

- [ ] Zerodha trading account with funds
- [ ] Kite Connect API subscription
- [ ] API Key and Secret obtained
- [ ] Dependencies installed (`pip install -r requirements_live_trading.txt`)
- [ ] `config.json` created with credentials
- [ ] Completed first-time authentication
- [ ] Verified connection and available cash
- [ ] Reviewed and customized strategy parameters
- [ ] Understood the risks
- [ ] Ready to start with small capital

**Good luck and trade safely!** 🚀
