# Live Trading Quick Start

## 5-Minute Setup Guide

### Step 1: Get API Credentials (5 minutes)
1. Go to https://kite.trade/
2. Subscribe to Kite Connect (₹2,000/month)
3. Create app, get API Key & Secret

### Step 2: Install & Configure (2 minutes)
```bash
# Install dependencies
pip install -r requirements_live_trading.txt

# Create config file
cd src/live_trading
cp config_template.json config.json

# Edit config.json - add your API key and secret
nano config.json
```

### Step 3: Run (1 minute)
```bash
python3 src/live_trading/live_ma_crossover.py
```

Follow the on-screen instructions to:
1. Login to Zerodha (first time only)
2. Verify connection
3. Start trading

---

## Strategy at a Glance

**Entry:** 20 MA crosses above 50 MA
**Exit:** 10% Stop Loss OR 30% Take Profit
**Max Positions:** 3
**Capital per Trade:** ~₹33,333

---

## Key Commands

**Start trading:**
```bash
python3 src/live_trading/live_ma_crossover.py
```

**Stop trading:**
Press `Ctrl+C` in the terminal

**View logs:**
```bash
tail -f live_trading_strategy.log
```

---

## Safety Checklist

- ✅ Manual approval enabled (default)
- ✅ Position limits (max 3)
- ✅ Trade size limits (max ₹50,000)
- ✅ Stop loss protection (10%)
- ✅ Comprehensive logging

---

## Important Reminders

⚠️ **Start with small capital for testing**
⚠️ **Access token expires daily - re-login each morning**
⚠️ **Monitor the system actively**
⚠️ **Don't run on market holidays**

---

## Files to Know

```
src/live_trading/
├── live_ma_crossover.py       # Main script - RUN THIS
├── zerodha_broker.py          # Broker integration
├── config.json                # YOUR credentials (create this)
└── config_template.json       # Template

Logs:
├── live_trading_strategy.log  # What the strategy is doing
└── live_trading.log           # Broker API calls

Trade Records:
└── live_trades_*.json         # Completed trades
```

---

## Customization

Edit these variables in `live_ma_crossover.py`:

```python
ma_short_period = 20              # MA periods
ma_long_period = 50
stop_loss_pct = 10.0              # Risk management
take_profit_pct = 30.0
max_positions = 3                 # Position limits
max_trade_size = 50000
require_manual_approval = True    # Safety (KEEP ON!)
```

---

## Need Help?

📖 **Full Guide:** Read `LIVE_TRADING_SETUP.md`
📝 **Zerodha Docs:** https://kite.trade/docs/connect/v3/
💬 **Zerodha Support:** https://support.zerodha.com/

---

**Happy Trading! Trade Responsibly! 🚀**
