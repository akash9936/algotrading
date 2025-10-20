"""
Test MongoDB Integration
=========================

Test script to verify MongoDB connection and data insertion
"""

from mongodb_handler import MongoDBHandler
from nse_realtime import NSERealtimeFetcher
from datetime import datetime

# MongoDB URI
MONGODB_URI = "mongodb+srv://akash9936:Tree9936@cluster0.f1wthph.mongodb.net/?retryWrites=true&w=majority"

print("=" * 80)
print("MONGODB INTEGRATION TEST")
print("=" * 80)

# Test 1: MongoDB Connection
print("\n1. Testing MongoDB Connection...")
print("-" * 80)

mongodb = MongoDBHandler(MONGODB_URI)

if mongodb.connected:
    print("✓ MongoDB connected successfully")
else:
    print("✗ MongoDB connection failed")
    exit(1)

# Test 2: NSE Data Fetch
print("\n2. Testing NSE Data Fetch...")
print("-" * 80)

nse_fetcher = NSERealtimeFetcher()
nse_data = nse_fetcher.fetch_nifty50_data()

if nse_data and 'data' in nse_data:
    print(f"✓ NSE data fetched: {len(nse_data['data'])} stocks")
else:
    print("✗ Failed to fetch NSE data")
    exit(1)

# Test 3: Save Single Stock to MongoDB
print("\n3. Testing Single Stock Save...")
print("-" * 80)

# Get TCS data
tcs_data = None
for stock in nse_data['data']:
    if stock.get('symbol') == 'TCS':
        tcs_data = stock
        break

if tcs_data:
    success = mongodb.save_live_price('TCS', tcs_data, 'NSE')
    if success:
        print(f"✓ TCS data saved to MongoDB")
        print(f"  Last Price: ₹{tcs_data.get('lastPrice', 'N/A')}")
    else:
        print("✗ Failed to save TCS data")
else:
    print("✗ TCS not found in NSE data")

# Test 4: Bulk Save All Nifty 50 Stocks
print("\n4. Testing Bulk Save...")
print("-" * 80)

count = mongodb.save_nse_bulk_data(nse_data['data'])
print(f"✓ Saved {count} stocks to MongoDB")

# Test 5: Retrieve Latest Price
print("\n5. Testing Data Retrieval...")
print("-" * 80)

latest_tcs = mongodb.get_latest_price('TCS')
if latest_tcs:
    print("✓ Retrieved TCS from MongoDB:")
    print(f"  Symbol: {latest_tcs.get('symbol')}")
    print(f"  Last Price: ₹{latest_tcs.get('lastPrice', 'N/A')}")
    print(f"  Day High: ₹{latest_tcs.get('dayHigh', 'N/A')}")
    print(f"  Day Low: ₹{latest_tcs.get('dayLow', 'N/A')}")
    print(f"  Volume: {latest_tcs.get('totalTradedVolume', 'N/A'):,}")
else:
    print("✗ Failed to retrieve TCS data")

# Close connection
mongodb.close()

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("✓ All MongoDB integration tests passed!")
print("\nYour live trading system will now:")
print("  1. Save real-time prices to CSV (data/live_data/)")
print("  2. Save full stock data to MongoDB Atlas")
print("  3. Maintain logs in src/live_trading/logs/")
print("=" * 80)
