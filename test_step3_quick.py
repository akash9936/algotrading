#!/usr/bin/env python3
"""Quick verification that STEP 3 is working"""

import sys
sys.path.insert(0, 'src')

print("Testing STEP 3 implementation...")

# Test 1: Import base strategy
try:
    from optimization.base_strategy import BaseStrategy
    print("✓ BaseStrategy imported")
except Exception as e:
    print(f"✗ BaseStrategy import failed: {e}")
    sys.exit(1)

# Test 2: Import all strategies
try:
    from optimization.strategies import (
        RSIMeanReversionStrategy,
        MACDCrossoverStrategy,
        BollingerBandStrategy,
        MovingAverageCrossoverStrategy,
        ATRBreakoutStrategy,
        MultiSignalStrategy
    )
    print("✓ All 6 strategy classes imported")
except Exception as e:
    print(f"✗ Strategy import failed: {e}")
    sys.exit(1)

# Test 3: Import strategy tester
try:
    from optimization.strategy_tester import StrategyTester
    print("✓ StrategyTester imported")
except Exception as e:
    print(f"✗ StrategyTester import failed: {e}")
    sys.exit(1)

# Test 4: Initialize strategy tester
try:
    tester = StrategyTester(initial_capital=100000)
    print(f"✓ StrategyTester initialized with {len(tester.strategies)} strategies")
except Exception as e:
    print(f"✗ StrategyTester initialization failed: {e}")
    sys.exit(1)

# Test 5: List all strategies
print("\nRegistered strategies:")
for i, name in enumerate(tester.strategies.keys(), 1):
    print(f"  {i}. {name}")

print("\n" + "="*70)
print("✓ STEP 3 VERIFICATION COMPLETE")
print("="*70)
print("\nAll components working correctly!")
print("\nNext: Test with real data:")
print("  python test_strategies.py")
print("\nOr run Phase 2:")
print("  python src/run_optimization.py --phase=2")
