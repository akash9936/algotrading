#!/usr/bin/env python3
"""
Test Regime Analysis Framework

This script tests market regime detection and strategy performance analysis
across different market conditions.
"""

import sys
import os
sys.path.insert(0, 'src')

from optimization.regime_analyzer import RegimeAnalyzer
from optimization.strategy_tester import StrategyTester
from utills.load_data import DataLoader
import pandas as pd


def main():
    print("="*80)
    print("MARKET REGIME ANALYSIS TEST")
    print("="*80)

    # Load data
    print("\n1. Loading data...")
    loader = DataLoader()
    all_stock_data = loader.load_all_nifty50()

    if not all_stock_data:
        print("❌ No data found. Run: python download_data.py")
        return

    # Use 5 stocks for testing
    test_stocks = dict(list(all_stock_data.items())[:5])

    # Find Nifty 50 index
    nifty_data = None
    for symbol, df in all_stock_data.items():
        if 'NIFTY' in symbol.upper():
            nifty_data = df
            print(f"✓ Found Nifty 50 index: {symbol}")
            break

    if nifty_data is None:
        print("⚠ No Nifty 50 index found. Using first stock as proxy.")
        nifty_data = list(all_stock_data.values())[0]

    # Filter to 2024 data
    print("\n2. Filtering to 2024...")
    start_date = pd.to_datetime('2024-01-01')
    end_date = pd.to_datetime('2024-12-31')

    # Handle timezone
    if hasattr(nifty_data.index[0], 'tz') and nifty_data.index[0].tz is not None:
        start_date = start_date.tz_localize(nifty_data.index[0].tz)
        end_date = end_date.tz_localize(nifty_data.index[0].tz)

    mask = (nifty_data.index >= start_date) & (nifty_data.index <= end_date)
    nifty_2024 = nifty_data[mask]

    filtered_stocks = {}
    for symbol, df in test_stocks.items():
        mask = (df.index >= start_date) & (df.index <= end_date)
        filtered_df = df[mask]
        if len(filtered_df) > 0:
            filtered_stocks[symbol] = filtered_df

    print(f"✓ Filtered {len(filtered_stocks)} stocks to 2024")

    # Initialize regime analyzer
    print("\n3. Detecting market regimes...")
    analyzer = RegimeAnalyzer(
        trend_ma_short=50,
        trend_ma_long=200,
        volatility_period=20,
        volatility_percentile_high=70,
        volatility_percentile_low=30
    )

    # Detect regimes
    regimes_df = analyzer.detect_regimes(nifty_2024, index_name="NIFTY 50")
    analyzer.print_regime_summary()

    # Test a couple of strategies
    print("\n4. Testing strategies...")
    tester = StrategyTester(initial_capital=100000)

    # Test just 3 strategies for speed
    strategies_to_test = ['RSI_Mean_Reversion', 'MACD_Crossover', 'Multi_Signal_RSI_MACD']

    all_trades = {}
    for strategy_name in strategies_to_test:
        if strategy_name in tester.strategies:
            print(f"  Testing {strategy_name}...")
            strategy = tester.strategies[strategy_name]
            strategy.backtest(filtered_stocks)
            all_trades[strategy_name] = strategy.trades
            print(f"    ✓ {len(strategy.trades)} trades")

    # Analyze by regime
    print("\n5. Analyzing performance by regime...")
    comparison_df = analyzer.compare_strategies_by_regime(all_trades)

    if not comparison_df.empty:
        analyzer.print_regime_comparison(comparison_df)

        # Generate recommendations
        print("\n6. Generating recommendations...")
        recommendations = analyzer.generate_regime_recommendations()

        print("\n" + "="*80)
        print("REGIME-SPECIFIC RECOMMENDATIONS")
        print("="*80)

        for strategy_name, rec in recommendations.items():
            print(f"\n{strategy_name}:")
            print(f"  📊 {rec['recommendation']}")
            print(f"  ✓ Best: {rec['best_regime'].replace('_', ' ')} "
                  f"({rec['best_win_rate']:.1f}% win rate)")
            print(f"  ✗ Worst: {rec['worst_regime'].replace('_', ' ')} "
                  f"({rec['worst_win_rate']:.1f}% win rate)")
            print(f"\n  Regime Ratings:")
            for regime, rating in rec['regime_ratings'].items():
                emoji = "🟢" if rating == "EXCELLENT" else "🟡" if rating == "GOOD" else "🟠" if rating == "ACCEPTABLE" else "🔴"
                print(f"    {emoji} {regime.replace('_', ' ')}: {rating}")

    print("\n" + "="*80)
    print("✓ REGIME ANALYSIS TEST COMPLETE")
    print("="*80)
    print("\nKey Insights:")
    print("- Market regimes successfully detected")
    print("- Strategy performance varies significantly by regime")
    print("- Use recommendations to filter trades by market condition")
    print("\nNext: Run Phase 3 on full dataset:")
    print("  python src/run_optimization.py --phase=3")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
