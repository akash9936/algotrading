#!/usr/bin/env python3
"""
Strategy Optimization Runner - Main Orchestrator

This script runs the complete optimization pipeline:
1. Parameter Grid Search
2. Multi-Strategy Testing
3. Market Regime Analysis
4. Stock-Specific Optimization
5. ML Insights
6. Walk-Forward Validation
7. Monte Carlo Simulation
8. Recommendations

Usage:
    python src/run_optimization.py --full      # Run everything
    python src/run_optimization.py --quick     # Quick test (fewer combinations)
    python src/run_optimization.py --phase=1   # Run specific phase
"""

import argparse
import json
import sys
import os
from datetime import datetime
import pandas as pd

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utills.load_data import DataLoader
from optimization.parameter_optimizer import ParameterOptimizer
from optimization.backtest_wrapper import run_backtest_with_params


def load_config(config_path: str = None):
    """Load optimization configuration."""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'config', 'optimization_config.json')

    with open(config_path, 'r') as f:
        config = json.load(f)

    return config


def load_data(config):
    """Load all NIFTY 50 stock data."""
    print("\n" + "="*80)
    print("LOADING DATA")
    print("="*80)

    loader = DataLoader()
    all_stock_data = loader.load_all_nifty50()

    if not all_stock_data:
        print("❌ No NIFTY 50 data found!")
        print("   Please run: python download_data.py")
        sys.exit(1)

    print(f"✓ Loaded {len(all_stock_data)} NIFTY 50 stocks")

    # Apply date filtering if specified
    data_config = config.get('data', {})
    if data_config.get('start_date') and data_config.get('end_date'):
        start_date = pd.to_datetime(data_config['start_date'])
        end_date = pd.to_datetime(data_config['end_date'])

        print(f"✓ Filtering data: {start_date.date()} to {end_date.date()}")

        filtered_data = {}
        for symbol, df in all_stock_data.items():
            # Handle timezone-aware indices
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                start_date_tz = start_date.tz_localize(df.index.tz)
                end_date_tz = end_date.tz_localize(df.index.tz)
            else:
                start_date_tz = start_date
                end_date_tz = end_date

            mask = (df.index >= start_date_tz) & (df.index <= end_date_tz)
            filtered_df = df[mask]
            if len(filtered_df) > 0:
                filtered_data[symbol] = filtered_df

        all_stock_data = filtered_data
        print(f"✓ After filtering: {len(all_stock_data)} stocks")

    return all_stock_data


def phase_1_parameter_grid_search(config, data, sample_size=None):
    """
    Phase 1: Parameter Grid Search

    Tests thousands of parameter combinations to find optimal settings.
    """
    print("\n" + "="*80)
    print("PHASE 1: PARAMETER GRID SEARCH")
    print("="*80)

    # Initialize optimizer
    param_ranges = config.get('parameter_ranges', {})
    optimizer = ParameterOptimizer(param_ranges)

    # Get sample size from config or argument
    if sample_size is None:
        sample_size = config.get('optimization_settings', {}).get('sample_size', 5000)

    print(f"Sample size: {sample_size} parameter combinations")

    # Run optimization
    n_jobs = config.get('optimization_settings', {}).get('n_jobs', -1)

    results_df = optimizer.optimize_parameters(
        backtest_func=run_backtest_with_params,
        data=data,
        sample_size=sample_size,
        n_jobs=n_jobs
    )

    # Get top parameters
    primary_metric = config.get('optimization_settings', {}).get('primary_metric', 'sharpe_ratio')
    top_n = config.get('optimization_settings', {}).get('top_n_strategies', 100)

    top_params = optimizer.get_top_parameters(n=top_n, metric=primary_metric)

    print(f"\n✓ Phase 1 Complete")
    print(f"  - Tested: {len(results_df)} combinations")
    print(f"  - Top {top_n} parameters saved")
    print(f"  - Best {primary_metric}: {top_params[primary_metric].iloc[0]:.3f}")

    return results_df, top_params


def phase_2_multi_strategy_testing(config, data):
    """
    Phase 2: Multi-Strategy Testing

    Tests different strategy types (mean reversion, momentum, etc.)
    """
    print("\n" + "="*80)
    print("PHASE 2: MULTI-STRATEGY TESTING")
    print("="*80)

    from optimization.strategy_tester import StrategyTester

    # Initialize tester
    initial_capital = config.get('data', {}).get('initial_capital', 100000)
    tester = StrategyTester(initial_capital=initial_capital)

    # Test all strategies
    results_df = tester.test_all_strategies(data)

    # Print comparison
    if len(results_df) > 0:
        tester.print_comparison(results_df)

        print(f"\n✓ Phase 2 Complete")
        print(f"  - Tested: {len(results_df)} strategies")
        print(f"  - Best Sharpe: {results_df['sharpe_ratio'].max():.2f}")
        print(f"  - Best Return: {results_df['total_return_pct'].max():.2f}%")

    return results_df


def phase_3_market_regime_analysis(config, data):
    """
    Phase 3: Market Regime Analysis

    Analyzes performance in different market conditions.
    """
    print("\n" + "="*80)
    print("PHASE 3: MARKET REGIME ANALYSIS")
    print("="*80)

    from optimization.regime_analyzer import RegimeAnalyzer
    from optimization.strategy_tester import StrategyTester

    # Find Nifty 50 index data
    nifty_data = None
    for symbol, df in data.items():
        if 'NIFTY' in symbol.upper() or symbol == 'NIFTY 50':
            nifty_data = df
            print(f"Using {symbol} as market index")
            break

    if nifty_data is None:
        print("⚠ No Nifty 50 index data found. Using first stock as proxy.")
        nifty_data = list(data.values())[0]

    # Initialize regime analyzer
    analyzer = RegimeAnalyzer(
        trend_ma_short=50,
        trend_ma_long=200,
        volatility_period=20
    )

    # Detect regimes
    regimes_df = analyzer.detect_regimes(nifty_data)
    analyzer.print_regime_summary()

    # Test strategies if not already done
    if not hasattr(phase_3_market_regime_analysis, 'strategy_results'):
        print("\nTesting strategies for regime analysis...")
        tester = StrategyTester(initial_capital=100000)
        tester.test_all_strategies(data)

        # Collect all trades
        all_strategy_trades = {
            name: strategy.trades
            for name, strategy in tester.strategies.items()
        }
        phase_3_market_regime_analysis.strategy_results = all_strategy_trades
    else:
        all_strategy_trades = phase_3_market_regime_analysis.strategy_results

    # Analyze strategies by regime
    comparison_df = analyzer.compare_strategies_by_regime(all_strategy_trades)

    if not comparison_df.empty:
        analyzer.print_regime_comparison(comparison_df)

        # Generate recommendations
        recommendations = analyzer.generate_regime_recommendations()

        print("\n" + "="*80)
        print("REGIME-SPECIFIC RECOMMENDATIONS")
        print("="*80)

        for strategy_name, rec in recommendations.items():
            print(f"\n{strategy_name}:")
            print(f"  {rec['recommendation']}")
            print(f"  Best: {rec['best_regime'].replace('_', ' ')} ({rec['best_win_rate']:.1f}% win rate)")
            print(f"  Worst: {rec['worst_regime'].replace('_', ' ')} ({rec['worst_win_rate']:.1f}% win rate)")

        # Save results
        analyzer.save_results()

        print(f"\n✓ Phase 3 Complete")
        print(f"  - Regimes detected: 3 trend + 3 volatility")
        print(f"  - Strategies analyzed: {len(all_strategy_trades)}")
        print(f"  - Recommendations generated")

        return comparison_df
    else:
        print("No regime comparison data available")
        return None


def phase_4_stock_specific_optimization(config, data):
    """
    Phase 4: Stock-Specific Optimization

    Finds optimal parameters for individual stocks.
    """
    print("\n" + "="*80)
    print("PHASE 4: STOCK-SPECIFIC OPTIMIZATION")
    print("="*80)

    from optimization.stock_optimizer import StockOptimizer
    from optimization.strategy_tester import StrategyTester

    optimizer = StockOptimizer()

    # Analyze stock characteristics
    char_df = optimizer.analyze_stock_characteristics(data)

    # Cluster stocks
    clustered_df = optimizer.cluster_stocks(char_df, n_clusters=3)

    # Test strategies if not done
    print("\nTesting strategies on all stocks...")
    tester = StrategyTester(initial_capital=100000)
    tester.test_all_strategies(data)

    # Collect trades
    all_trades = {name: strategy.trades for name, strategy in tester.strategies.items()}

    # Find best strategy per cluster
    cluster_strat = optimizer.find_best_strategy_per_cluster(all_trades)

    # Optimize per stock (sample 10 stocks)
    print("\nOptimizing individual stocks (sample)...")
    sample_stocks = list(data.keys())[:10]

    for symbol in sample_stocks:
        result = optimizer.optimize_per_stock(symbol, data[symbol], tester.strategies)
        print(f"  {symbol}: {result['best_strategy']} (Sharpe: {result['sharpe_ratio']:.2f})")

    # Generate recommendations
    recs_df = optimizer.generate_stock_recommendations()

    print("\n📊 Top 10 Stock Recommendations:")
    print(recs_df.head(10).to_string(index=False))

    # Save results
    optimizer.save_results()

    print(f"\n✓ Phase 4 Complete")
    print(f"  - Stocks analyzed: {len(char_df)}")
    print(f"  - Clusters created: {len(clustered_df['cluster'].unique())}")
    print(f"  - Recommendations generated")

    return recs_df


def phase_5_ml_insights(config, data, results):
    """
    Phase 5: Machine Learning Insights

    Uses ML to discover patterns and insights.
    """
    print("\n" + "="*80)
    print("PHASE 5: MACHINE LEARNING INSIGHTS")
    print("="*80)

    from optimization.ml_insights import MLInsights
    from optimization.strategy_tester import StrategyTester

    # Test strategies if not done
    tester = StrategyTester(initial_capital=100000)
    tester.test_all_strategies(data)

    # Collect all trades
    all_trades = {name: strategy.trades for name, strategy in tester.strategies.items()}

    # Run ML analysis
    ml = MLInsights()
    insights = ml.analyze_all_trades(all_trades)

    # Print key findings
    print("\n" + "="*80)
    print("KEY ML INSIGHTS")
    print("="*80)

    if ml.patterns:
        print("\n📊 Discovered Patterns:")
        for pattern in ml.patterns:
            print(f"  • {pattern['type']}: {pattern['recommendation']}")

    print(f"\n✓ Phase 5 Complete")
    print(f"  - Total trades analyzed: {insights.get('total_trades', 0)}")
    print(f"  - Patterns discovered: {len(ml.patterns)}")

    return insights


def phase_6_walk_forward_validation(config, data, top_params):
    """
    Phase 6: Walk-Forward Optimization

    Validates robustness across different time periods.
    """
    print("\n" + "="*80)
    print("PHASE 6: WALK-FORWARD VALIDATION")
    print("="*80)
    print("(To be implemented in STEP 7)")

    return None


def phase_7_monte_carlo_simulation(config, data):
    """
    Phase 7: Monte Carlo Risk Analysis

    Simulates future outcomes and calculates risk metrics.
    """
    print("\n" + "="*80)
    print("PHASE 7: MONTE CARLO SIMULATION")
    print("="*80)

    from optimization.monte_carlo import MonteCarloSimulator
    from optimization.strategy_tester import StrategyTester

    # Test strategies
    tester = StrategyTester(initial_capital=100000)
    tester.test_all_strategies(data)

    # Collect trades
    all_trades = {name: strategy.trades for name, strategy in tester.strategies.items()}

    # Run Monte Carlo analysis
    n_sims = config.get('monte_carlo', {}).get('n_simulations', 10000)
    mc = MonteCarloSimulator(n_simulations=n_sims)

    comparison_df = mc.analyze_multiple_strategies(all_trades, initial_capital=100000)

    # Save results
    mc.save_results()

    print(f"\n✓ Phase 7 Complete")
    print(f"  - Simulations per strategy: {n_sims:,}")
    print(f"  - Strategies analyzed: {len(comparison_df)}")

    return comparison_df


def phase_8_generate_recommendations(config, all_results):
    """
    Phase 8: Generate Recommendations

    Creates actionable trading rules and reports.
    """
    print("\n" + "="*80)
    print("PHASE 8: GENERATE RECOMMENDATIONS")
    print("="*80)

    from optimization.recommendation_engine import RecommendationEngine

    # Initialize engine
    engine = RecommendationEngine()

    # Analyze all results
    recommendations = engine.analyze_all_results(
        strategy_comparison=all_results.get('strategies'),
        regime_analysis=all_results.get('regimes'),
        stock_recommendations=all_results.get('stocks'),
        ml_insights=all_results.get('ml'),
        monte_carlo_results=all_results.get('monte_carlo')
    )

    # Generate trading rules
    trading_rules = engine.generate_trading_rules()

    # Print recommendations
    engine.print_recommendations()

    # Save all recommendations
    engine.save_recommendations()

    print(f"\n✓ Phase 8 Complete")
    print(f"  - Final recommendations generated")
    print(f"  - Trading rules created")
    print(f"  - All results saved")

    return recommendations


def run_full_optimization(config, data):
    """Run all optimization phases."""
    print("\n" + "="*80)
    print("FULL OPTIMIZATION PIPELINE")
    print("="*80)

    start_time = datetime.now()

    all_results = {}

    # Phase 2: Multi-Strategy Testing (skip Phase 1 for now - too slow)
    print("\nRunning Phase 2...")
    strategy_results = phase_2_multi_strategy_testing(config, data)
    all_results['strategies'] = strategy_results

    # Phase 3: Market Regime Analysis
    print("\nRunning Phase 3...")
    regime_results = phase_3_market_regime_analysis(config, data)
    all_results['regimes'] = regime_results

    # Phase 4: Stock-Specific Optimization
    print("\nRunning Phase 4...")
    stock_results = phase_4_stock_specific_optimization(config, data)
    all_results['stocks'] = stock_results

    # Phase 5: ML Insights
    print("\nRunning Phase 5...")
    ml_insights = phase_5_ml_insights(config, data, None)
    all_results['ml'] = ml_insights

    # Phase 7: Monte Carlo Simulation
    print("\nRunning Phase 7...")
    monte_carlo_results = phase_7_monte_carlo_simulation(config, data)
    all_results['monte_carlo'] = monte_carlo_results

    # Phase 8: Generate Recommendations
    print("\nRunning Phase 8...")
    recommendations = phase_8_generate_recommendations(config, all_results)

    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)
    print(f"Total time: {duration}")
    print(f"Results saved to: result/optimization/")
    print("="*80 + "\n")


def run_quick_test(config, data):
    """Run a quick test with limited parameter combinations."""
    print("\n" + "="*80)
    print("QUICK TEST MODE")
    print("="*80)

    # Run only Phase 1 with small sample size
    grid_results, top_params = phase_1_parameter_grid_search(config, data, sample_size=100)

    print("\n✓ Quick test complete")
    print(f"  Check results in: result/optimization/")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run strategy optimization')
    parser.add_argument('--full', action='store_true',
                       help='Run full optimization (all phases)')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick test (100 combinations)')
    parser.add_argument('--phase', type=int, choices=range(1, 9),
                       help='Run specific phase (1-8)')
    parser.add_argument('--config', type=str,
                       help='Path to config file')
    parser.add_argument('--sample-size', type=int,
                       help='Number of parameter combinations to test')

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Load data
    data = load_data(config)

    # Run requested mode
    if args.quick:
        run_quick_test(config, data)
    elif args.phase:
        # Run specific phase
        if args.phase == 1:
            sample_size = args.sample_size if args.sample_size else None
            phase_1_parameter_grid_search(config, data, sample_size)
        elif args.phase == 2:
            phase_2_multi_strategy_testing(config, data)
        elif args.phase == 3:
            phase_3_market_regime_analysis(config, data)
        elif args.phase == 4:
            phase_4_stock_specific_optimization(config, data)
        elif args.phase == 5:
            phase_5_ml_insights(config, data, None)
        elif args.phase == 6:
            phase_6_walk_forward_validation(config, data, None)
        elif args.phase == 7:
            phase_7_monte_carlo_simulation(config, data)
        elif args.phase == 8:
            phase_8_generate_recommendations(config, None)
    elif args.full:
        run_full_optimization(config, data)
    else:
        # Default: show help
        parser.print_help()
        print("\nExample usage:")
        print("  python src/run_optimization.py --quick")
        print("  python src/run_optimization.py --phase=1 --sample-size=500")
        print("  python src/run_optimization.py --full")


if __name__ == "__main__":
    main()
