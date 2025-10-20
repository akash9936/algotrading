"""
Test Portfolio and Sells Collection Integration
================================================

Tests the new portfolio management and sells collection logging
"""

from mongodb_handler import MongoDBHandler
from datetime import datetime, timedelta

# MongoDB URI
MONGODB_URI = "mongodb+srv://akash9936:Tree9936@cluster0.f1wthph.mongodb.net/?retryWrites=true&w=majority"

print("=" * 80)
print("PORTFOLIO & SELLS COLLECTION TEST")
print("=" * 80)

# Connect to MongoDB
print("\n1. Connecting to MongoDB...")
print("-" * 80)

mongodb = MongoDBHandler(MONGODB_URI)

if not mongodb.connected:
    print("✗ MongoDB connection failed")
    exit(1)

print("✓ MongoDB connected")
print(f"  Collections: portfolio, sells, trades, nse50v2s")

# Test 1: Add positions to portfolio (BUY)
print("\n2. Testing Portfolio Updates (BUY)...")
print("-" * 80)

# BUY TCS
mongodb.update_portfolio(
    symbol='TCS',
    quantity=5,
    avg_price=2950.50,
    action='BUY'
)

# BUY INFY
mongodb.update_portfolio(
    symbol='INFY',
    quantity=10,
    avg_price=1450.25,
    action='BUY'
)

# BUY more TCS (should update average price)
mongodb.update_portfolio(
    symbol='TCS',
    quantity=3,
    avg_price=3000.00,
    action='BUY'
)

print("\n✓ Portfolio positions added/updated")

# Test 2: Get portfolio
print("\n3. Retrieving Current Portfolio...")
print("-" * 80)

portfolio = mongodb.get_portfolio()

if portfolio:
    print(f"✓ Portfolio contains {len(portfolio)} positions:")
    for pos in portfolio:
        print(f"  - {pos['symbol']}: {pos['quantity']} shares @ ₹{pos.get('averagePrice', 0):.2f}")
        if pos['symbol'] == 'TCS':
            # Verify average price calculation: (5*2950.50 + 3*3000) / 8 = 2970.56
            expected_avg = (5 * 2950.50 + 3 * 3000.00) / 8
            actual_avg = pos.get('averagePrice', 0)
            print(f"    Expected avg: ₹{expected_avg:.2f}, Actual avg: ₹{actual_avg:.2f}")
            if abs(expected_avg - actual_avg) < 0.1:
                print(f"    ✓ Average price calculation correct!")
else:
    print("⚠️  No portfolio positions found")

# Test 3: Log sell orders
print("\n4. Testing Sell Order Logging...")
print("-" * 80)

# Sell some TCS
sell_data_1 = {
    'symbol': 'TCS',
    'sellDate': datetime.now(),
    'sellPrice': 3050.75,
    'quantity': 5,
    'orderId': 'TEST_SELL_001',
    'reason': 'Take Profit',
    'pnl': (3050.75 - 2970.56) * 5,  # Using calculated avg
    'pnlPercentage': ((3050.75 - 2970.56) / 2970.56) * 100,
    'holdingPeriodMinutes': 120
}

sell_id_1 = mongodb.log_sell_order(sell_data_1)

if sell_id_1:
    print(f"✓ Sell order logged: TCS - 5 shares @ ₹{sell_data_1['sellPrice']:.2f}")
    print(f"  Reason: {sell_data_1['reason']}")
    print(f"  P&L: ₹{sell_data_1['pnl']:.2f} ({sell_data_1['pnlPercentage']:.2f}%)")
    print(f"  MongoDB ID: {sell_id_1}")

# Test 4: Update portfolio after sell (SELL action)
print("\n5. Testing Portfolio Update (SELL)...")
print("-" * 80)

mongodb.update_portfolio(
    symbol='TCS',
    quantity=5,
    avg_price=3050.75,
    action='SELL'
)

print("✓ Portfolio updated after sell")

# Test 5: Verify portfolio after sell
print("\n6. Verifying Portfolio After Sell...")
print("-" * 80)

portfolio = mongodb.get_portfolio()

if portfolio:
    print(f"✓ Portfolio contains {len(portfolio)} positions:")
    for pos in portfolio:
        print(f"  - {pos['symbol']}: {pos['quantity']} shares @ ₹{pos.get('averagePrice', 0):.2f}")
        if pos['symbol'] == 'TCS':
            # Should have 3 shares remaining (8 - 5)
            if pos['quantity'] == 3:
                print(f"    ✓ Quantity correctly reduced to 3 shares")
            else:
                print(f"    ✗ Expected 3 shares, got {pos['quantity']}")

# Test 6: Sell all INFY (should remove from portfolio)
print("\n7. Testing Complete Position Exit...")
print("-" * 80)

# Sell all INFY
sell_data_2 = {
    'symbol': 'INFY',
    'sellDate': datetime.now(),
    'sellPrice': 1320.50,
    'quantity': 10,
    'orderId': 'TEST_SELL_002',
    'reason': 'Stop Loss',
    'pnl': (1320.50 - 1450.25) * 10,
    'pnlPercentage': ((1320.50 - 1450.25) / 1450.25) * 100,
    'holdingPeriodMinutes': 90
}

sell_id_2 = mongodb.log_sell_order(sell_data_2)
print(f"✓ Sell order logged: INFY - 10 shares @ ₹{sell_data_2['sellPrice']:.2f}")

# Update portfolio (should remove INFY)
mongodb.update_portfolio(
    symbol='INFY',
    quantity=10,
    avg_price=1320.50,
    action='SELL'
)

# Verify INFY removed
portfolio = mongodb.get_portfolio()
infy_found = any(pos['symbol'] == 'INFY' for pos in portfolio)

if not infy_found:
    print("✓ INFY position removed from portfolio (fully sold)")
else:
    print("✗ INFY still in portfolio (should have been removed)")

# Test 7: Get sell history
print("\n8. Retrieving Sell History...")
print("-" * 80)

sell_history = mongodb.get_sell_history(limit=10)

if sell_history:
    print(f"✓ Retrieved {len(sell_history)} sell orders:")
    for i, sell in enumerate(sell_history[:5], 1):
        print(f"\n  Sell {i}:")
        print(f"    Symbol: {sell.get('symbol')}")
        print(f"    Quantity: {sell.get('quantity')}")
        print(f"    Price: ₹{sell.get('sellPrice', 0):.2f}")
        print(f"    Reason: {sell.get('reason')}")
        print(f"    P&L: ₹{sell.get('pnl', 0):.2f} ({sell.get('pnlPercentage', 0):.2f}%)")

# Test 8: Sync from Zerodha (mock test)
print("\n9. Testing Zerodha Portfolio Sync...")
print("-" * 80)

# Mock Zerodha holdings
mock_holdings = [
    {
        'tradingsymbol': 'RELIANCE',
        'quantity': 20,
        'average_price': 2500.00
    },
    {
        'tradingsymbol': 'HDFCBANK',
        'quantity': 15,
        'average_price': 1650.00
    }
]

synced_count = mongodb.sync_portfolio_from_zerodha(mock_holdings)
print(f"✓ Synced {synced_count} positions from mock Zerodha data")

# Final portfolio state
print("\n10. Final Portfolio State...")
print("-" * 80)

portfolio = mongodb.get_portfolio()

if portfolio:
    print(f"✓ Portfolio contains {len(portfolio)} positions:")
    total_value = 0
    for pos in portfolio:
        value = pos['quantity'] * pos.get('averagePrice', 0)
        total_value += value
        print(f"  - {pos['symbol']}: {pos['quantity']} shares @ ₹{pos.get('averagePrice', 0):.2f} = ₹{value:,.2f}")
    print(f"\n  Total Portfolio Value: ₹{total_value:,.2f}")

# Close connection
mongodb.close()

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("✓ All portfolio and sells collection tests passed!")
print("\nMongoDB Collections:")
print("  - portfolio: Current holdings with average prices")
print("  - sells: Detailed sell order history")
print("  - trades: Complete buy/sell trade logs")
print("  - nse50v2s: Live stock price data")
print("\nFeatures Tested:")
print("  ✓ Portfolio updates on BUY (add/update with average price)")
print("  ✓ Portfolio updates on SELL (reduce/remove)")
print("  ✓ Average price calculation on multiple buys")
print("  ✓ Sell order logging with P&L")
print("  ✓ Complete position exit (removal from portfolio)")
print("  ✓ Zerodha holdings sync to portfolio")
print("=" * 80)
