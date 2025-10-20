# Portfolio & Sells Collection Integration

## Overview

The live trading system now includes **complete portfolio management** and **dedicated sell order tracking** in MongoDB. This provides real-time portfolio tracking, automatic average price calculation, and detailed sell order history.

## MongoDB Collections

**Database:** `stock_trading`

### New Collections:

1. **`portfolio`** - Current holdings/positions
   - Real-time portfolio state
   - Automatic average price calculation
   - Syncs with Zerodha holdings
   - Updates on every buy/sell

2. **`sells`** - Dedicated sell order logs
   - Every sell order logged separately
   - P&L tracking per sell
   - Exit reason tracking
   - Holding period calculations

### Existing Collections:

3. **`trades`** - Complete trade history (buy & sell)
4. **`nse50v2s`** - Live stock prices

## Portfolio Collection Schema

```javascript
{
  symbol: "TCS",              // Stock symbol
  quantity: 8,                // Current quantity held
  averagePrice: 2969.06,      // Average purchase price
  createdAt: "2025-10-18...", // When first purchased
  lastUpdated: "2025-10-18...", // Last update timestamp
  syncedFromZerodha: true     // If synced from broker
}
```

### Key Features:

- **Automatic Average Price**: When buying multiple times, calculates weighted average
- **Real-time Updates**: Updates on every buy/sell transaction
- **Zero Quantity Removal**: Positions removed when fully sold
- **Zerodha Sync**: Can sync current Zerodha holdings

## Sells Collection Schema

```javascript
{
  symbol: "TCS",
  sellDate: "2025-10-18T16:45:00",
  sellPrice: 3050.75,
  quantity: 5,
  totalValue: 15253.75,       // sellPrice * quantity
  orderId: "ORDER_789012",
  reason: "Take Profit",      // "Stop Loss" or "Take Profit"
  pnl: 400.95,                // Profit/Loss amount
  pnlPercentage: 2.70,        // P&L percentage
  entryPrice: 2969.06,        // Original purchase price
  entryDate: "2025-10-18T14:30:00",
  holdingPeriodMinutes: 135,  // How long held
  createdAt: "2025-10-18T16:45:00"
}
```

### Key Features:

- **Dedicated Sell Logs**: Every sell separately tracked
- **Full P&L Details**: Amount and percentage
- **Exit Reason**: Stop Loss vs Take Profit tracking
- **Holding Period**: Minutes held before selling

## How It Works

### Buy Order Flow

```
1. Golden Cross Signal Detected
        ↓
2. Place BUY Order on Zerodha
        ↓
3. Log to trades collection (ENTRY)
        ↓
4. Update portfolio collection
   • If new: Add position with avg_price
   • If existing: Update quantity and recalculate avg_price
        ↓
5. Save to local file (backup)
```

**Average Price Calculation:**
```python
# If buying more of existing position:
new_avg = ((old_qty * old_avg) + (new_qty * new_price)) / (old_qty + new_qty)

# Example:
# Had: 5 shares @ ₹2950.50
# Buy: 3 shares @ ₹3000.00
# New avg: ((5 * 2950.50) + (3 * 3000.00)) / 8 = ₹2969.06
```

### Sell Order Flow

```
1. Stop Loss or Take Profit Hit
        ↓
2. Place SELL Order on Zerodha
        ↓
3. Calculate P&L and holding period
        ↓
4. Log to trades collection (EXIT)
        ↓
5. Update portfolio collection
   • Reduce quantity by sold amount
   • If quantity = 0: Remove from portfolio
        ↓
6. Log to sells collection
   • Full sell details
   • P&L, reason, holding period
        ↓
7. Save to local file (backup)
```

## MongoDB Handler Methods

### Portfolio Methods

**`get_portfolio()`**
- Retrieves all current holdings from portfolio collection
- Returns list of position dictionaries
- Only returns positions with quantity > 0

**`update_portfolio(symbol, quantity, avg_price, action='BUY')`**
- **BUY action**: Adds new or updates existing position
  - Calculates new weighted average price
  - Updates quantity and timestamp
- **SELL action**: Reduces quantity or removes position
  - Reduces quantity by sold amount
  - Removes position if quantity reaches 0
  - Keeps average price unchanged

**`sync_portfolio_from_zerodha(zerodha_holdings)`**
- Syncs portfolio with current Zerodha holdings
- Updates quantities and prices from broker
- Marks synced positions with `syncedFromZerodha: true`

### Sells Methods

**`log_sell_order(sell_data)`**
- Logs every sell order to sells collection
- Requires:
  - symbol, sellDate, sellPrice, quantity, orderId
  - reason (Stop Loss / Take Profit)
  - pnl, pnlPercentage, holdingPeriodMinutes
- Returns MongoDB document ID

**`get_sell_history(symbol=None, limit=100)`**
- Retrieves sell order history
- Can filter by symbol
- Sorted by sell date (newest first)

## Integration in live_ma_crossover.py

### On Startup: Portfolio Sync

```python
def sync_portfolio_to_mongodb(self):
    # Sync from Zerodha holdings
    holdings = self.broker.get_holdings()
    if holdings:
        self.mongodb.sync_portfolio_from_zerodha(holdings)

    # Sync active positions from memory
    for symbol, position in self.active_positions.items():
        self.mongodb.update_portfolio(
            symbol=symbol,
            quantity=position['quantity'],
            avg_price=position['entry_price'],
            action='BUY'
        )

    # Display current portfolio
    portfolio = self.mongodb.get_portfolio()
    logger.info(f"Current Portfolio ({len(portfolio)} positions)")
```

### On BUY Order

```python
def enter_position(self, symbol):
    # ... place order ...

    # Log to trades collection
    self.mongodb.log_trade_entry(trade_data)

    # Update portfolio
    self.mongodb.update_portfolio(
        symbol=symbol,
        quantity=quantity,
        avg_price=ltp,
        action='BUY'
    )
```

### On SELL Order

```python
def exit_position(self, symbol, reason):
    # ... place order ...

    # Calculate P&L and holding period
    pnl = (exit_price - entry_price) * quantity
    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
    holding_period_minutes = int((exit_date - entry_date).total_seconds() / 60)

    # Log to trades collection (EXIT)
    self.mongodb.log_trade_exit(trade)

    # Update portfolio (reduce/remove)
    self.mongodb.update_portfolio(
        symbol=symbol,
        quantity=quantity,
        avg_price=exit_price,
        action='SELL'
    )

    # Log to sells collection
    sell_data = {
        'symbol': symbol,
        'sellDate': exit_date,
        'sellPrice': exit_price,
        'quantity': quantity,
        'orderId': order_id,
        'reason': reason,
        'pnl': pnl,
        'pnlPercentage': pnl_pct,
        'holdingPeriodMinutes': holding_period_minutes
    }
    self.mongodb.log_sell_order(sell_data)
```

## Testing

**Run Portfolio & Sells Test:**
```bash
cd src/live_trading
python3 test_portfolio_sells.py
```

**Expected Output:**
```
✓ Portfolio updates on BUY (add/update with average price)
✓ Portfolio updates on SELL (reduce/remove)
✓ Average price calculation on multiple buys
✓ Sell order logging with P&L
✓ Complete position exit (removal from portfolio)
✓ Zerodha holdings sync to portfolio
```

## MongoDB Atlas Queries

### View Current Portfolio

```javascript
db.portfolio.find({quantity: {$gt: 0}})
```

### View All Sell Orders

```javascript
db.sells.find({}).sort({sellDate: -1})
```

### Profitable Sells

```javascript
db.sells.find({pnl: {$gt: 0}}).sort({pnl: -1})
```

### Losing Sells

```javascript
db.sells.find({pnl: {$lt: 0}}).sort({pnl: 1})
```

### Sells by Reason

```javascript
db.sells.aggregate([
  {$group: {
    _id: "$reason",
    count: {$sum: 1},
    totalPnL: {$sum: "$pnl"},
    avgPnL: {$avg: "$pnl"}
  }}
])
```

### Average Holding Period by Exit Reason

```javascript
db.sells.aggregate([
  {$group: {
    _id: "$reason",
    avgHoldingMinutes: {$avg: "$holdingPeriodMinutes"},
    avgPnL: {$avg: "$pnl"},
    count: {$sum: 1}
  }}
])
```

### Portfolio Value

```javascript
db.portfolio.aggregate([
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

## Benefits

### 1. Real-time Portfolio Tracking
- Know exactly what you hold at any moment
- Automatic average price calculation
- Syncs with Zerodha on startup

### 2. Detailed Sell Analytics
- Every sell tracked separately
- P&L per sell (not just aggregated)
- Exit reason tracking (Stop Loss vs Take Profit)
- Holding period analysis

### 3. Performance Insights
Query MongoDB to answer:
- Which stocks have best sell performance?
- Do Stop Loss sells perform better or worse than Take Profit?
- What's the average holding period for profitable sells?
- Which stocks contribute most to portfolio value?

### 4. Risk Management
Track:
- Current exposure per stock
- Average entry prices vs current prices
- P&L distribution across sells
- Exit reason effectiveness

### 5. Multi-layer Persistence
Portfolio tracked in:
1. **MongoDB** (primary, cloud)
2. **Local JSON** (disaster recovery)
3. **Zerodha** (broker holdings)

All three stay in sync!

## Files Modified

### 1. `mongodb_handler.py`
**Added:**
- `portfolio_collection` - Line 48
- `sells_collection` - Line 49
- `get_portfolio()` - Line 425
- `update_portfolio()` - Line 445
- `log_sell_order()` - Line 535
- `get_sell_history()` - Line 592
- `sync_portfolio_from_zerodha()` - Line 619

### 2. `live_ma_crossover.py`
**Added:**
- `sync_portfolio_to_mongodb()` - Line 300
- Portfolio update on BUY - Line 767
- Portfolio update on SELL - Line 853
- Sell order logging - Line 861

**Modified:**
- `enter_position()` - Added portfolio update after BUY
- `exit_position()` - Added portfolio update and sell logging after SELL

### 3. `test_portfolio_sells.py`
**New file** - Complete test suite for portfolio and sells integration

## Example Data

### Portfolio Document (MongoDB)
```json
{
  "_id": "68f3ed9abf1647a2ac5ad86c",
  "symbol": "TCS",
  "quantity": 8,
  "averagePrice": 2969.06,
  "createdAt": "2025-10-18T16:30:00",
  "lastUpdated": "2025-10-18T16:35:00"
}
```

### Sell Document (MongoDB)
```json
{
  "_id": "68f3ed9bbf1647a2ac5ad86e",
  "symbol": "TCS",
  "sellDate": "2025-10-18T16:45:00",
  "sellPrice": 3050.75,
  "quantity": 5,
  "totalValue": 15253.75,
  "orderId": "ORDER_789012",
  "reason": "Take Profit",
  "pnl": 400.95,
  "pnlPercentage": 2.70,
  "entryPrice": 2969.06,
  "entryDate": "2025-10-18T14:30:00",
  "holdingPeriodMinutes": 135,
  "createdAt": "2025-10-18T16:45:00"
}
```

## Summary

Your live trading system now provides:

✅ **Real-time Portfolio Tracking** - Know exactly what you hold
✅ **Automatic Average Pricing** - Weighted average on multiple buys
✅ **Dedicated Sell Logs** - Every sell tracked separately
✅ **P&L Per Sell** - Not just aggregated, per-order tracking
✅ **Exit Reason Tracking** - Stop Loss vs Take Profit analysis
✅ **Holding Period Analysis** - Minutes held per sell
✅ **Zerodha Sync** - Portfolio syncs with broker on startup
✅ **Multi-layer Backup** - MongoDB + Local File + Broker

Everything is automatically logged and updated with every trade!

---

**Status:** ✅ Fully Operational
**Last Updated:** 2025-10-18
**Version:** 3.0 (with Portfolio & Sells Collections)
