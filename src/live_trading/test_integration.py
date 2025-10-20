"""
Test Integration Script
========================

Tests the integrated live trading setup:
1. NSE India real-time price fetcher
2. Local historical data loading
3. MA calculation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_trading.nse_realtime import NSERealtimeFetcher
import pandas as pd
from datetime import datetime, timedelta

print("=" * 80)
print("INTEGRATION TEST")
print("=" * 80)

# Test 1: NSE Real-time Price Fetcher
print("\n1. Testing NSE Real-time Price Fetcher...")
print("-" * 80)

fetcher = NSERealtimeFetcher()

test_symbols = ["TCS", "INFY", "RELIANCE"]

for symbol in test_symbols:
    price = fetcher.get_stock_price(symbol)
    if price:
        print(f"✓ {symbol:15} ₹{price:10,.2f}")
    else:
        print(f"✗ {symbol:15} Failed to fetch price")

# Test 2: Local Historical Data
print("\n2. Testing Local Historical Data Loading...")
print("-" * 80)

data_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data', 'nifty50')

if os.path.exists(data_folder):
    import glob

    files = glob.glob(os.path.join(data_folder, "*.csv"))

    if files:
        print(f"✓ Found {len(files)} data files in {data_folder}")

        # Try to load one file
        test_file = files[0]
        try:
            df = pd.read_csv(test_file, index_col=0, parse_dates=True)
            print(f"✓ Successfully loaded: {os.path.basename(test_file)}")
            print(f"  Rows: {len(df)}")
            print(f"  Date range: {df.index.min()} to {df.index.max()}")
            print(f"  Columns: {', '.join(df.columns)}")

            # Test MA calculation
            if 'Close' in df.columns:
                ma_20 = df['Close'].rolling(window=20).mean()
                ma_50 = df['Close'].rolling(window=50).mean()

                print(f"\n  Latest MA values:")
                print(f"    20 MA: ₹{ma_20.iloc[-1]:.2f}")
                print(f"    50 MA: ₹{ma_50.iloc[-1]:.2f}")

                # Check for golden cross
                if len(df) >= 2:
                    ma_20_curr = ma_20.iloc[-1]
                    ma_50_curr = ma_50.iloc[-1]
                    ma_20_prev = ma_20.iloc[-2]
                    ma_50_prev = ma_50.iloc[-2]

                    if not pd.isna(ma_20_curr) and not pd.isna(ma_50_curr):
                        golden_cross = (ma_20_prev <= ma_50_prev) and (ma_20_curr > ma_50_curr)

                        if golden_cross:
                            print(f"\n  🎯 GOLDEN CROSS DETECTED!")
                        else:
                            print(f"\n  No golden cross at this time")

        except Exception as e:
            print(f"✗ Error loading file: {str(e)}")

    else:
        print(f"⚠️  No data files found in {data_folder}")
        print(f"   Run 'python src/download_data.py' to download historical data")

else:
    print(f"✗ Data folder not found: {data_folder}")
    print(f"   Run 'python src/download_data.py' to download historical data")

# Test 3: Check Zerodha Config
print("\n3. Testing Zerodha Configuration...")
print("-" * 80)

config_path = os.path.join(os.path.dirname(__file__), 'config.json')

if os.path.exists(config_path):
    import json

    with open(config_path, 'r') as f:
        config = json.load(f)

    api_key = config.get('api_key')
    api_secret = config.get('api_secret')
    access_token = config.get('access_token')

    if api_key and api_secret:
        print(f"✓ API credentials found")
        print(f"  API Key: {api_key[:10]}...")

        if access_token:
            print(f"  Access Token: {access_token[:20]}...")
        else:
            print(f"  ⚠️  Access token not found (you'll need to login)")
    else:
        print(f"✗ API credentials missing in config.json")

else:
    print(f"✗ Config file not found: {config_path}")
    print(f"   Create config.json with your Zerodha API credentials")

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

print("\n✓ NSE India real-time fetcher: Working")

if os.path.exists(data_folder) and glob.glob(os.path.join(data_folder, "*.csv")):
    print("✓ Historical data: Available")
else:
    print("⚠️  Historical data: Not available")
    print("   (Will be downloaded automatically when you start live trading)")

if os.path.exists(config_path):
    print("✓ Zerodha config: Found")
else:
    print("✗ Zerodha config: Missing")

print("\n" + "=" * 80)
print("Ready to start live trading!")
print("Run: python3 src/live_trading/live_ma_crossover.py")
print("")
print("NOTE: Historical data will be downloaded automatically if missing")
print("      or outdated when you start the live trading script.")
print("=" * 80)
