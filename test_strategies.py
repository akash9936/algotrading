#!/usr/bin/env python3
"""
Test Multi-Strategy Framework

This script tests all implemented trading strategies on a small subset
of data to verify functionality before running full optimization.
"""

import sys
import os
sys.path.insert(0, 'src')

from optimization.strategy_tester import StrategyTester
from utills.load_data import DataLoader
import pandas as pd


def main():
    print("="*80)
    print("MULTI-STRATEGY FRAMEWORK TEST")
    print("="*80)

    # Load data (small subset for testing)
    print("\n1. Loading data...")
    loader = DataLoader()
    all_stock_data = loader.load_all_nifty50()

    if not all_stock_data:
        print("❌ No data found. Run: python download_data.py")
        return

    # Use only 5 stocks for quick test
    test_stocks = dict(list(all_stock_data.items())[:5])
    print(f"✓ Loaded {len(test_stocks)} stocks for testing")
    print(f"  Stocks: {', '.join(test_stocks.keys())}")

    # Filter to recent data (2024 only)
    print("\n2. Filtering to 2024 data...")
    filtered_stocks = {}
    start_date = pd.to_datetime('2024-01-01')
    end_date = pd.to_datetime('2024-12-31')

    for symbol, df in test_stocks.items():
        # Handle timezone if needed
        if hasattr(df.index[0], 'tz') and df.index[0].tz is not None:
            start_date = start_date.tz_localize(df.index[0].tz)
            end_date = end_date.tz_localize(df.index[0].tz)

        mask = (df.index >= start_date) & (df.index <= end_date)
        filtered_df = df[mask]

        if len(filtered_df) > 0:
            filtered_stocks[symbol] = filtered_df
            print(f"  {symbol}: {len(filtered_df)} days")

    # Initialize strategy tester
    print("\n3. Initializing strategy tester...")
    tester = StrategyTester(initial_capital=100000)
    print(f"✓ Registered {len(tester.strategies)} strategies:")
    for name in tester.strategies.keys():
        print(f"  - {name}")

    # Test all strategies
    print("\n4. Testing all strategies...")
    results_df = tester.test_all_strategies(filtered_stocks)

    # Print comparison
    if len(results_df) > 0:
        print("\n5. Results:")
        tester.print_comparison(results_df)

        print("\n6. Summary Statistics:")
        print(f"  Strategies tested: {len(results_df)}")
        print(f"  Best return: {results_df['total_return_pct'].max():.2f}%")
        print(f"  Best Sharpe: {results_df['sharpe_ratio'].max():.2f}")
        print(f"  Average win rate: {results_df['win_rate'].mean():.1f}%")
    else:
        print("❌ No results generated")

    print("\n" + "="*80)
    print("✓ TEST COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Run Phase 2 with all stocks:")
    print("   python src/run_optimization.py --phase=2")
    print("\n2. Or run full optimization:")
    print("   python src/run_optimization.py --full")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
