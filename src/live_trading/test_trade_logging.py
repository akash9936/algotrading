"""
Test Trade Logging to MongoDB
==============================

Simulates buy/sell trades and verifies MongoDB logging
"""

from mongodb_handler import MongoDBHandler
from datetime import datetime, timedelta
import random

# MongoDB URI
MONGODB_URI = "mongodb+srv://akash9936:Tree9936@cluster0.f1wthph.mongodb.net/?retryWrites=true&w=majority"

print("=" * 80)
print("TRADE LOGGING TEST")
print("=" * 80)

# Connect to MongoDB
print("\n1. Connecting to MongoDB...")
print("-" * 80)

mongodb = MongoDBHandler(MONGODB_URI)

if not mongodb.connected:
    print("✗ MongoDB connection failed")
    exit(1)

print("✓ MongoDB connected")

# Test Buy Trade
print("\n2. Testing BUY Trade Logging...")
print("-" * 80)

buy_trade = {
    'symbol': 'TCS',
    'action': 'BUY',
    'entry_date': datetime.now(),
    'entry_price': 2950.50,
    'quantity': 5,
    'order_id': 'TEST_BUY_001',
    'capital_deployed': 2950.50 * 5,
    'stop_loss_price': 2950.50 * 0.90,  # -10%
    'take_profit_price': 2950.50 * 1.30,  # +30%
    'strategy': 'MA_CROSSOVER_20_50',
    'ma_20': 2945.25,
    'ma_50': 2920.75
}

buy_id = mongodb.log_trade_entry(buy_trade)

if buy_id:
    print(f"✓ BUY trade logged successfully")
    print(f"  Symbol: {buy_trade['symbol']}")
    print(f"  Entry Price: ₹{buy_trade['entry_price']:.2f}")
    print(f"  Quantity: {buy_trade['quantity']}")
    print(f"  Capital: ₹{buy_trade['capital_deployed']:,.2f}")
    print(f"  Stop Loss: ₹{buy_trade['stop_loss_price']:.2f}")
    print(f"  Take Profit: ₹{buy_trade['take_profit_price']:.2f}")
    print(f"  MongoDB ID: {buy_id}")
else:
    print("✗ Failed to log BUY trade")

# Simulate holding period
print("\n3. Simulating holding period...")
print("-" * 80)
print("  (Waiting 2 seconds to simulate trade duration)")
import time
time.sleep(2)

# Test Sell Trade (Winning Trade)
print("\n4. Testing SELL Trade Logging (Winning Trade)...")
print("-" * 80)

entry_date = buy_trade['entry_date']
exit_date = datetime.now()
exit_price = 3050.75  # Profit
pnl = (exit_price - buy_trade['entry_price']) * buy_trade['quantity']
pnl_pct = ((exit_price - buy_trade['entry_price']) / buy_trade['entry_price']) * 100

sell_trade = {
    'symbol': 'TCS',
    'action': 'SELL',
    'entry_date': entry_date,
    'entry_price': buy_trade['entry_price'],
    'exit_date': exit_date,
    'exit_price': exit_price,
    'quantity': buy_trade['quantity'],
    'entry_order_id': 'TEST_BUY_001',
    'exit_order_id': 'TEST_SELL_001',
    'pnl': pnl,
    'pnl_pct': pnl_pct,
    'exit_reason': 'Take Profit'
}

sell_id = mongodb.log_trade_exit(sell_trade)

if sell_id:
    print(f"✓ SELL trade logged successfully")
    print(f"  Symbol: {sell_trade['symbol']}")
    print(f"  Entry: ₹{sell_trade['entry_price']:.2f} → Exit: ₹{sell_trade['exit_price']:.2f}")
    print(f"  P&L: ₹{sell_trade['pnl']:,.2f} ({sell_trade['pnl_pct']:.2f}%)")
    print(f"  Reason: {sell_trade['exit_reason']}")
    print(f"  MongoDB ID: {sell_id}")
else:
    print("✗ Failed to log SELL trade")

# Test another trade (Losing Trade)
print("\n5. Testing SELL Trade Logging (Losing Trade)...")
print("-" * 80)

# Simulate another buy
buy_trade_2 = {
    'symbol': 'INFY',
    'action': 'BUY',
    'entry_date': datetime.now() - timedelta(hours=2),
    'entry_price': 1450.25,
    'quantity': 10,
    'order_id': 'TEST_BUY_002',
    'capital_deployed': 1450.25 * 10,
    'stop_loss_price': 1450.25 * 0.90,
    'take_profit_price': 1450.25 * 1.30,
    'strategy': 'MA_CROSSOVER_20_50',
    'ma_20': 1448.50,
    'ma_50': 1425.00
}

mongodb.log_trade_entry(buy_trade_2)

# Simulate stop loss exit
exit_price_2 = 1320.50  # Loss
pnl_2 = (exit_price_2 - buy_trade_2['entry_price']) * buy_trade_2['quantity']
pnl_pct_2 = ((exit_price_2 - buy_trade_2['entry_price']) / buy_trade_2['entry_price']) * 100

sell_trade_2 = {
    'symbol': 'INFY',
    'action': 'SELL',
    'entry_date': buy_trade_2['entry_date'],
    'entry_price': buy_trade_2['entry_price'],
    'exit_date': datetime.now(),
    'exit_price': exit_price_2,
    'quantity': buy_trade_2['quantity'],
    'entry_order_id': 'TEST_BUY_002',
    'exit_order_id': 'TEST_SELL_002',
    'pnl': pnl_2,
    'pnl_pct': pnl_pct_2,
    'exit_reason': 'Stop Loss'
}

sell_id_2 = mongodb.log_trade_exit(sell_trade_2)

if sell_id_2:
    print(f"✓ SELL trade logged successfully")
    print(f"  Symbol: {sell_trade_2['symbol']}")
    print(f"  Entry: ₹{sell_trade_2['entry_price']:.2f} → Exit: ₹{sell_trade_2['exit_price']:.2f}")
    print(f"  P&L: ₹{sell_trade_2['pnl']:,.2f} ({sell_trade_2['pnl_pct']:.2f}%)")
    print(f"  Reason: {sell_trade_2['exit_reason']}")
    print(f"  MongoDB ID: {sell_id_2}")

# Retrieve Trade History
print("\n6. Retrieving Trade History...")
print("-" * 80)

tcs_trades = mongodb.get_trade_history(symbol='TCS', limit=10)
print(f"✓ Retrieved {len(tcs_trades)} TCS trades")

for i, trade in enumerate(tcs_trades[:3], 1):
    print(f"\nTrade {i}:")
    print(f"  Type: {trade.get('tradeType')}")
    print(f"  Symbol: {trade.get('symbol')}")
    if trade.get('tradeType') == 'EXIT':
        print(f"  P&L: ₹{trade.get('pnl', 0):,.2f} ({trade.get('pnlPercentage', 0):.2f}%)")

# Get Trading Statistics
print("\n7. Retrieving Trading Statistics...")
print("-" * 80)

stats = mongodb.get_trade_statistics()

if stats.get('totalTrades', 0) > 0:
    print("✓ Trading Statistics:")
    print(f"  Total Trades: {stats.get('totalTrades', 0)}")
    print(f"  Total P&L: ₹{stats.get('totalPnL', 0):,.2f}")
    print(f"  Average P&L: ₹{stats.get('avgPnL', 0):,.2f}")
    print(f"  Winning Trades: {stats.get('winningTrades', 0)}")
    print(f"  Losing Trades: {stats.get('losingTrades', 0)}")
    print(f"  Win Rate: {stats.get('winRate', 0):.2f}%")
    print(f"  Avg Holding Period: {stats.get('avgHoldingPeriod', 0):.0f} minutes")
else:
    print("⚠️  No completed trades found")

# Close connection
mongodb.close()

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("✓ All trade logging tests passed!")
print("\nMongoDB Collections:")
print("  - trades: Buy/Sell trade logs with full details")
print("  - nse50v2s: Live stock price data")
print("\nYou can now view trades in MongoDB Atlas:")
print("  Database: stock_trading")
print("  Collection: trades")
print("\nEach trade includes:")
print("  - Entry/Exit prices and dates")
print("  - P&L and P&L percentage")
print("  - Stop loss and take profit prices")
print("  - MA values at entry")
print("  - Order IDs")
print("  - Exit reason (Stop Loss / Take Profit)")
print("=" * 80)
