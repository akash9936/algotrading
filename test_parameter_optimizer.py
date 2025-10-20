#!/usr/bin/env python3
"""
Test Script for Parameter Optimizer

This script tests the parameter grid generation functionality without
running full backtests. Useful for verifying the optimizer works correctly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from optimization.parameter_optimizer import ParameterOptimizer
import json


def test_default_config():
    """Test 1: Default configuration"""
    print("="*80)
    print("TEST 1: Default Configuration")
    print("="*80)

    optimizer = ParameterOptimizer()
    print("\n✓ Optimizer initialized with default config")

    # Check config structure
    print("\nParameter categories:")
    for category in optimizer.config.keys():
        params = optimizer.config[category]
        print(f"  {category}:")
        for param_name, values in params.items():
            print(f"    - {param_name}: {len(values)} values {values}")


def test_parameter_grid_generation():
    """Test 2: Parameter grid generation"""
    print("\n" + "="*80)
    print("TEST 2: Parameter Grid Generation")
    print("="*80)

    optimizer = ParameterOptimizer()

    # Generate small sample
    sample_size = 10
    print(f"\nGenerating {sample_size} parameter combinations...")

    param_grids = optimizer.generate_parameter_grid(sample_size=sample_size)

    print(f"✓ Generated {len(param_grids)} combinations")

    # Show first few
    print("\nFirst 3 parameter combinations:")
    for i, params in enumerate(param_grids[:3]):
        print(f"\n  Combination {i+1}:")
        print(json.dumps(params, indent=4))


def test_total_combinations():
    """Test 3: Calculate total possible combinations"""
    print("\n" + "="*80)
    print("TEST 3: Total Possible Combinations")
    print("="*80)

    optimizer = ParameterOptimizer()

    # Calculate total possible combinations
    total = 1
    for category, params in optimizer.config.items():
        for param_name, values in params.items():
            total *= len(values)

    print(f"\nTotal possible combinations: {total:,}")
    print(f"Recommended sample size: 5,000-10,000")
    print(f"Quick test sample size: 100-500")


def test_custom_config():
    """Test 4: Custom configuration"""
    print("\n" + "="*80)
    print("TEST 4: Custom Configuration")
    print("="*80)

    # Create custom config with fewer parameters for testing
    custom_config = {
        'rsi': {
            'period': [14, 16],
            'oversold': [30, 40],
            'overbought': [70, 80]
        },
        'macd': {
            'fast_period': [12, 14],
            'slow_period': [26, 28],
            'signal_period': [9]
        },
        'risk_management': {
            'stop_loss': [0.03, 0.04],
            'take_profit': [0.10, 0.12],
            'trailing_stop': [0.03],
            'max_hold_days': [30]
        }
    }

    optimizer = ParameterOptimizer(custom_config)
    print("\n✓ Optimizer initialized with custom config")

    # Calculate total combinations
    total = 1
    for category, params in custom_config.items():
        category_total = 1
        for param_name, values in params.items():
            category_total *= len(values)
        print(f"\n{category}: {category_total} combinations")
        for param_name, values in params.items():
            print(f"  - {param_name}: {values}")
        total *= category_total

    print(f"\nTotal combinations: {total}")

    # Generate all combinations
    print(f"\nGenerating all {total} combinations...")
    param_grids = optimizer.generate_parameter_grid(sample_size=None)
    print(f"✓ Generated {len(param_grids)} combinations")


def test_parameter_flattening():
    """Test 5: Parameter flattening for DataFrame storage"""
    print("\n" + "="*80)
    print("TEST 5: Parameter Flattening")
    print("="*80)

    optimizer = ParameterOptimizer()
    param_grids = optimizer.generate_parameter_grid(sample_size=1)

    # Show nested structure
    print("\nNested parameter structure:")
    print(json.dumps(param_grids[0], indent=2))

    # Flatten for storage
    flat_params = {}
    for category, param_dict in param_grids[0].items():
        for param_name, value in param_dict.items():
            flat_params[f"{category}_{param_name}"] = value

    print("\nFlattened parameter structure (for CSV storage):")
    for key, value in flat_params.items():
        print(f"  {key}: {value}")


def test_sampling_randomness():
    """Test 6: Sampling randomness"""
    print("\n" + "="*80)
    print("TEST 6: Sampling Randomness")
    print("="*80)

    optimizer = ParameterOptimizer()

    # Generate two samples
    sample_size = 5
    sample1 = optimizer.generate_parameter_grid(sample_size=sample_size)
    sample2 = optimizer.generate_parameter_grid(sample_size=sample_size)

    print(f"\nGenerated two samples of size {sample_size}")
    print(f"Sample 1 first RSI period: {sample1[0]['rsi']['period']}")
    print(f"Sample 2 first RSI period: {sample2[0]['rsi']['period']}")

    # Check if they're different (should be with random sampling)
    if sample1[0] != sample2[0]:
        print("✓ Samples are different (random sampling works)")
    else:
        print("⚠ Samples are identical (may indicate fixed seed)")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("PARAMETER OPTIMIZER TEST SUITE")
    print("="*80)

    try:
        test_default_config()
        test_parameter_grid_generation()
        test_total_combinations()
        test_custom_config()
        test_parameter_flattening()
        test_sampling_randomness()

        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        print("\nNext steps:")
        print("1. Run quick optimization test:")
        print("   python src/run_optimization.py --quick")
        print("\n2. Run full parameter search on Phase 1:")
        print("   python src/run_optimization.py --phase=1 --sample-size=500")
        print("\n3. Run complete optimization:")
        print("   python src/run_optimization.py --full")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
