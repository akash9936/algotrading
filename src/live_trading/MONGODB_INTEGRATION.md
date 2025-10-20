# MongoDB Integration - Live Trading System

## Overview

The live trading system now stores real-time NSE stock data to **MongoDB Atlas** in addition to local CSV files.

## Features

✅ **Dual Storage System**
- CSV files: Local backup in `data/live_data/`
- MongoDB: Cloud storage with full stock data

✅ **Full Stock Data**
- Not just prices, but complete market data
- Open, High, Low, Close (OHLC)
- Volume, Value, Year High/Low
- Percentage changes, etc.

✅ **Organized Logs**
- Trading logs: `src/live_trading/logs/`
- Live data CSV: `data/live_data/`
- MongoDB: Cloud Atlas database

## MongoDB Configuration

**Database:** `stock_trading`
**Collections:**
- `nse50v2s` - Live stock prices (real-time data)
- `trades` - Buy/Sell trade logs (execution history)
- `portfolio` - Current holdings/positions with average prices **[NEW]**
- `sells` - Dedicated sell order tracking **[NEW]**

**Connection URI:**
```
mongodb+srv://akash9936:***@cluster0.f1wthph.mongodb.net/
```

## Schema Structure

### 1. Live Stock Prices (`nse50v2s` collection)

Matching your Node.js schema (`NSE50DataV2`):

```javascript
{
  priority: Number,
  symbol: String,           // Stock symbol (e.g., "TCS")
  identifier: String,
  open: Number,             // Opening price
  dayHigh: Number,          // Day's high
  dayLow: Number,           // Day's low
  lastPrice: Number,        // Last traded price
  previousClose: Number,
  change: Number,
  pChange: Number,          // Percentage change
  ffmc: Number,
  yearHigh: Number,
  yearLow: Number,
  totalTradedVolume: Number,
  totalTradedValue: Number,
  lastUpdateTime: String,   // ISO format timestamp
  nearWKH: Number,
  nearWKL: Number,
  perChange365d: Number,
  perChange30d: Number,
  date365dAgo: String,
  chart365dPath: String,
  date30dAgo: String,
  chart30dPath: String,
  chartTodayPath: String,
  source: String,          // "Zerodha" or "NSE"
  fetchedAt: String        // When we fetched this data
}
```

### 2. Trade Logs (`trades` collection)

**BUY Trade (Entry):**
```javascript
{
  symbol: String,           // Stock symbol (e.g., "TCS")
  action: "BUY",           // Trade action
  tradeType: "ENTRY",      // Entry or Exit
  entryDate: String,       // ISO datetime
  entryPrice: Number,      // Buy price
  quantity: Number,        // Number of shares
  orderId: String,         // Zerodha order ID
  capitalDeployed: Number, // Total capital used
  stopLossPrice: Number,   // Calculated stop loss price (-10%)
  takeProfitPrice: Number, // Calculated take profit price (+30%)
  strategy: String,        // "MA_CROSSOVER_20_50"
  ma20: Number,            // 20-day MA at entry
  ma50: Number,            // 50-day MA at entry
  status: "OPEN",          // Trade status
  createdAt: String        // When logged
}
```

**SELL Trade (Exit):**
```javascript
{
  symbol: String,              // Stock symbol
  action: "SELL",             // Trade action
  tradeType: "EXIT",          // Entry or Exit
  entryDate: String,          // Original entry date
  entryPrice: Number,         // Original buy price
  exitDate: String,           // Exit date
  exitPrice: Number,          // Sell price
  quantity: Number,           // Number of shares
  entryOrderId: String,       // Original buy order ID
  exitOrderId: String,        // Sell order ID
  pnl: Number,                // Profit/Loss amount
  pnlPercentage: Number,      // P&L percentage
  exitReason: String,         // "Stop Loss" or "Take Profit"
  holdingPeriodMinutes: Number, // How long held
  capitalReturned: Number,    // Total capital returned
  status: "CLOSED",           // Trade status
  createdAt: String           // When logged
}
```

### 3. Portfolio (`portfolio` collection) **[NEW]**

Current holdings with automatic average price calculation:

```javascript
{
  symbol: String,              // Stock symbol
  quantity: Number,            // Current quantity held
  averagePrice: Number,        // Weighted average purchase price
  createdAt: String,           // When first purchased
  lastUpdated: String,         // Last update timestamp
  syncedFromZerodha: Boolean   // If synced from broker (optional)
}
```

**Features:**
- Automatic average price calculation on multiple buys
- Updates on every buy/sell transaction
- Positions removed when quantity reaches 0
- Syncs with Zerodha holdings on startup

### 4. Sells (`sells` collection) **[NEW]**

Dedicated sell order tracking:

```javascript
{
  symbol: String,
  sellDate: String,            // ISO datetime
  sellPrice: Number,
  quantity: Number,
  totalValue: Number,          // sellPrice * quantity
  orderId: String,             // Zerodha order ID
  reason: String,              // "Stop Loss" or "Take Profit"
  pnl: Number,                 // Profit/Loss amount
  pnlPercentage: Number,       // P&L percentage
  entryPrice: Number,          // Original purchase price
  entryDate: String,           // Original purchase date
  holdingPeriodMinutes: Number, // Minutes held
  createdAt: String
}
```

**Features:**
- Every sell logged separately (in addition to trades collection)
- Full P&L details per sell
- Exit reason tracking (Stop Loss vs Take Profit)
- Holding period analysis

## Data Flow

```
Live Trading Strategy
        ↓
   Get Real-time Price
        ↓
    ┌───┴───┐
    ↓       ↓
Zerodha   NSE India
  Quote     API
    ↓       ↓
    └───┬───┘
        ↓
  Save Live Price
        ↓
    ┌───┴───┐
    ↓       ↓
  CSV    MongoDB
  File   Atlas
```

## Files Created/Modified

### New Files:
1. **`mongodb_handler.py`** - MongoDB connection and data operations
2. **`test_mongodb.py`** - Test script for MongoDB integration
3. **`MONGODB_INTEGRATION.md`** - This documentation

### Modified Files:
1. **`live_ma_crossover.py`** - Integrated MongoDB saving
   - Added MongoDB initialization
   - Updated `save_live_price()` to save to both CSV and MongoDB
   - Updated `get_realtime_price()` to fetch full quote data
   - Added MongoDB connection close on shutdown

## Usage

### Running Live Trading (Auto MongoDB)
```bash
python3 src/live_trading/live_ma_crossover.py
```

MongoDB connection happens automatically. You'll see:
```
✓ Connected to MongoDB Atlas
  Database: stock_trading
  Collection: nse50v2s
```

### Testing MongoDB Integration

**Test Price Logging:**
```bash
python3 src/live_trading/test_mongodb.py
```

This will:
1. Connect to MongoDB
2. Fetch live NSE data
3. Save TCS stock to MongoDB
4. Save all Nifty 50 stocks (bulk)
5. Retrieve latest TCS data
6. Display results

**Test Trade Logging:**
```bash
python3 src/live_trading/test_trade_logging.py
```

This will:
1. Connect to MongoDB
2. Log a BUY trade (TCS at ₹2,950.50)
3. Log a SELL trade with profit (+3.40%)
4. Log another SELL trade with loss (-8.95%)
5. Retrieve trade history
6. Display trading statistics (win rate, P&L, etc.)

**Test Portfolio & Sells Collections:** **[NEW]**
```bash
python3 src/live_trading/test_portfolio_sells.py
```

This will:
1. Connect to MongoDB
2. Test portfolio updates on BUY (add/update with average price)
3. Test portfolio updates on SELL (reduce/remove)
4. Test average price calculation on multiple buys
5. Test sell order logging
6. Test Zerodha holdings sync
7. Display final portfolio state

## MongoDB Operations

### Save Single Stock Price
```python
mongodb.save_live_price('TCS', stock_data, source='NSE')
```

### Bulk Save All Nifty 50 Prices
```python
nse_data = nse_fetcher.fetch_nifty50_data()
count = mongodb.save_nse_bulk_data(nse_data['data'])
```

### Retrieve Latest Price
```python
latest = mongodb.get_latest_price('TCS')
print(f"TCS: ₹{latest['lastPrice']}")
```

### Log BUY Trade
```python
trade_data = {
    'symbol': 'TCS',
    'entry_date': datetime.now(),
    'entry_price': 2950.50,
    'quantity': 5,
    'order_id': 'ORDER_123',
    'capital_deployed': 14752.50,
    'stop_loss_price': 2655.45,
    'take_profit_price': 3835.65,
    'strategy': 'MA_CROSSOVER_20_50',
    'ma_20': 2945.25,
    'ma_50': 2920.75
}
mongodb.log_trade_entry(trade_data)
```

### Log SELL Trade
```python
trade_data = {
    'symbol': 'TCS',
    'entry_date': entry_datetime,
    'entry_price': 2950.50,
    'exit_date': datetime.now(),
    'exit_price': 3050.75,
    'quantity': 5,
    'entry_order_id': 'ORDER_123',
    'exit_order_id': 'ORDER_456',
    'pnl': 501.25,
    'pnl_pct': 3.40,
    'exit_reason': 'Take Profit'
}
mongodb.log_trade_exit(trade_data)
```

### Get Trade Statistics
```python
stats = mongodb.get_trade_statistics()
print(f"Total Trades: {stats['totalTrades']}")
print(f"Win Rate: {stats['winRate']:.2f}%")
print(f"Total P&L: ₹{stats['totalPnL']:,.2f}")
```

### Get Portfolio **[NEW]**
```python
portfolio = mongodb.get_portfolio()
for pos in portfolio:
    print(f"{pos['symbol']}: {pos['quantity']} @ ₹{pos['averagePrice']:.2f}")
```

### Update Portfolio **[NEW]**
```python
# On BUY
mongodb.update_portfolio(
    symbol='TCS',
    quantity=5,
    avg_price=2950.50,
    action='BUY'
)

# On SELL
mongodb.update_portfolio(
    symbol='TCS',
    quantity=5,
    avg_price=3050.75,
    action='SELL'
)
```

### Log Sell Order **[NEW]**
```python
sell_data = {
    'symbol': 'TCS',
    'sellDate': datetime.now(),
    'sellPrice': 3050.75,
    'quantity': 5,
    'orderId': 'ORDER_456',
    'reason': 'Take Profit',
    'pnl': 501.25,
    'pnlPercentage': 3.40,
    'holdingPeriodMinutes': 135
}
mongodb.log_sell_order(sell_data)
```

### Sync Portfolio from Zerodha **[NEW]**
```python
holdings = broker.get_holdings()
synced_count = mongodb.sync_portfolio_from_zerodha(holdings)
print(f"Synced {synced_count} positions from Zerodha")
```

## Folder Structure

```
StockBackTest/
├── data/
│   └── live_data/              # CSV files (daily)
│       └── live_prices_20251018.csv
│
└── src/
    └── live_trading/
        ├── logs/               # Trading logs
        │   ├── live_trading_20251018_020530.log
        │   ├── live_trades_20251018_020530.json
        │   └── active_positions.json
        │
        ├── mongodb_handler.py  # MongoDB integration
        ├── test_mongodb.py     # Test script
        └── live_ma_crossover.py # Main strategy
```

## Data Stored

### Every Price Fetch:
- **CSV:** Timestamp, Symbol, Price, Source
- **MongoDB (nse50v2s):** Full stock data (20+ fields)

### Trade Execution (BUY):
- **JSON:** Active positions (disaster recovery)
- **MongoDB (trades):** Complete BUY details
  - Entry price, quantity, capital deployed
  - Stop loss & take profit prices
  - MA values at entry (20 & 50)
  - Order ID, timestamp

### Trade Execution (SELL):
- **JSON:** Completed trades with P&L
- **MongoDB (trades):** Complete SELL details
  - Exit price, P&L, P&L percentage
  - Exit reason (Stop Loss / Take Profit)
  - Holding period in minutes
  - Both order IDs (entry & exit)

### Position Tracking:
- **JSON:** Active positions (local backup)
- **Log files:** All trading activity
- **MongoDB:** Complete trade history with statistics

## Benefits

1. **Cloud Backup** - Data safe even if local files lost
2. **Rich Data** - Full market data, not just prices
3. **Complete Trade History** - Every buy/sell logged with full details
4. **Trade Analytics** - Win rate, P&L stats, holding periods
5. **Easy Analysis** - Query MongoDB for insights
6. **Scalability** - Cloud storage grows with you
7. **Accessibility** - Access data from anywhere
8. **Strategy Tracking** - MA values at entry for backtesting
9. **Performance Monitoring** - Real-time trading statistics

## Viewing Data in MongoDB Atlas

1. Go to: https://cloud.mongodb.com/
2. Login with your credentials
3. Navigate to: **Cluster0** → **Collections**
4. Database: `stock_trading`
5. Collections:
   - **`nse50v2s`** - Live stock prices with full market data
   - **`trades`** - Complete buy/sell trade history
   - **`portfolio`** - Current holdings **[NEW]**
   - **`sells`** - Sell order history **[NEW]**

### Sample Queries in MongoDB Atlas

**View all trades:**
```javascript
db.trades.find({}).sort({createdAt: -1})
```

**View only winning trades:**
```javascript
db.trades.find({tradeType: "EXIT", pnl: {$gt: 0}}).sort({pnl: -1})
```

**View trades for specific stock:**
```javascript
db.trades.find({symbol: "TCS"})
```

**Get win rate:**
```javascript
db.trades.aggregate([
  {$match: {tradeType: "EXIT"}},
  {$group: {
    _id: null,
    total: {$sum: 1},
    wins: {$sum: {$cond: [{$gt: ["$pnl", 0]}, 1, 0]}}
  }}
])
```

**View current portfolio:** **[NEW]**
```javascript
db.portfolio.find({quantity: {$gt: 0}}).sort({symbol: 1})
```

**Calculate total portfolio value:** **[NEW]**
```javascript
db.portfolio.aggregate([
  {$match: {quantity: {$gt: 0}}},
  {$project: {
    symbol: 1,
    quantity: 1,
    averagePrice: 1,
    value: {$multiply: ["$quantity", "$averagePrice"]}
  }},
  {$group: {
    _id: null,
    totalValue: {$sum: "$value"},
    positions: {$sum: 1}
  }}
])
```

**View all sell orders:** **[NEW]**
```javascript
db.sells.find({}).sort({sellDate: -1})
```

**Profitable sells only:** **[NEW]**
```javascript
db.sells.find({pnl: {$gt: 0}}).sort({pnl: -1})
```

**Sells by exit reason:** **[NEW]**
```javascript
db.sells.aggregate([
  {$group: {
    _id: "$reason",
    count: {$sum: 1},
    totalPnL: {$sum: "$pnl"},
    avgPnL: {$avg: "$pnl"},
    avgHoldingMinutes: {$avg: "$holdingPeriodMinutes"}
  }}
])
```

## Capital Allocation

The system now implements:
- **Total capital:** ₹50,000 (across all positions)
- **Per-trade:** ₹50,000 / 3 = ₹16,666.67
- **Equal division:** Each position gets exactly ₹16,666.67
- **Wait on exhaustion:** When all capital deployed, wait for exits

Example:
```
Position 1: ₹16,666.67 → Remaining: ₹33,333.33
Position 2: ₹16,666.67 → Remaining: ₹16,666.67
Position 3: ₹16,666.67 → Remaining: ₹0 (WAIT)
Exit Pos 2 → Freed: ₹16,666.67 (Can enter new position)
```

## Troubleshooting

### MongoDB Connection Failed
- Check internet connection
- Verify MongoDB URI is correct
- Ensure IP address is whitelisted in Atlas
- Database name: `stock_trading` (auto-created)

### Data Not Appearing in MongoDB
- Check logs for MongoDB errors
- Verify collection name: `nse50v2s`
- Test with: `python3 test_mongodb.py`

### Permission Errors
- Check MongoDB user has write permissions
- Verify database access settings in Atlas

## Support

For issues:
1. Check logs: `src/live_trading/logs/`
2. Run test: `python3 test_mongodb.py`
3. Verify MongoDB Atlas dashboard
4. Check live data CSV for comparison

---

**Status:** ✅ Fully Operational
**Last Updated:** 2025-10-18
**Version:** 3.0 (with Portfolio & Sells Collections)

## Additional Documentation

For detailed information about the new portfolio and sells collections:
- See **`PORTFOLIO_SELLS_INTEGRATION.md`** for complete portfolio management guide
- See **`TRADE_LOGGING_SUMMARY.md`** for trade logging details
