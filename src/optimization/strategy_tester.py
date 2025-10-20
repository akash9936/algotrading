"""
Strategy Tester - Multi-Strategy Testing Engine

This module implements and tests different strategy types.
Compares performance across various trading approaches.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime
import json

from .strategies import (
    RSIMeanReversionStrategy,
    MACDCrossoverStrategy,
    BollingerBandStrategy,
    MovingAverageCrossoverStrategy,
    ATRBreakoutStrategy,
    MultiSignalStrategy
)


class StrategyTester:
    """
    Tests and compares different trading strategy types.

    Strategies included:
    - Mean Reversion (RSI, Bollinger Bands)
    - Momentum (MACD, MA Crossover)
    - Volatility Breakout (ATR)
    - Multi-Signal Confluence
    """

    def __init__(self, initial_capital: float = 100000):
        """
        Initialize strategy tester.

        Args:
            initial_capital: Starting capital for all strategies
        """
        self.initial_capital = initial_capital
        self.strategies = {}
        self.results = {}
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Register all available strategies with default parameters."""
        base_params = {
            'initial_capital': self.initial_capital,
            'transaction_cost_pct': 0.1,
            'max_positions': 3
        }

        # 1. RSI Mean Reversion
        self.strategies['RSI_Mean_Reversion'] = RSIMeanReversionStrategy({
            **base_params,
            'rsi_period': 14,
            'oversold': 30,
            'overbought': 70,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0
        })

        # 2. MACD Crossover
        self.strategies['MACD_Crossover'] = MACDCrossoverStrategy({
            **base_params,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0
        })

        # 3. Bollinger Band Mean Reversion
        self.strategies['Bollinger_Band'] = BollingerBandStrategy({
            **base_params,
            'bb_period': 20,
            'bb_std_dev': 2.0,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0
        })

        # 4. Moving Average Crossover (10/30)
        self.strategies['MA_Crossover_10_30'] = MovingAverageCrossoverStrategy({
            **base_params,
            'fast_period': 10,
            'slow_period': 30,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0
        })

        # 5. Moving Average Crossover (20/50)
        self.strategies['MA_Crossover_20_50'] = MovingAverageCrossoverStrategy({
            **base_params,
            'fast_period': 20,
            'slow_period': 50,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0
        })

        # 6. ATR Breakout
        self.strategies['ATR_Breakout'] = ATRBreakoutStrategy({
            **base_params,
            'lookback_period': 20,
            'atr_period': 14,
            'atr_multiplier': 1.5,
            'stop_loss_pct': 4.0,
            'take_profit_pct': 12.0
        })

        # 7. Multi-Signal Confluence (RSI + MACD)
        self.strategies['Multi_Signal_RSI_MACD'] = MultiSignalStrategy({
            **base_params,
            'rsi_period': 14,
            'rsi_oversold': 40,
            'rsi_overbought': 70,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0
        })

    def add_strategy(self, name: str, strategy):
        """Add a custom strategy to test."""
        self.strategies[name] = strategy

    def test_all_strategies(self, stock_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Test all registered strategies on the provided data.

        Args:
            stock_data: Dictionary of {symbol: DataFrame} with OHLC data

        Returns:
            DataFrame with comparison results
        """
        print("\n" + "="*80)
        print("MULTI-STRATEGY TESTING")
        print("="*80)
        print(f"Testing {len(self.strategies)} strategies on {len(stock_data)} stocks")
        print(f"Initial capital per strategy: ₹{self.initial_capital:,.0f}")
        print("="*80)

        results_list = []

        for strategy_name, strategy in self.strategies.items():
            print(f"\nTesting: {strategy_name}...")

            try:
                # Run backtest
                metrics = strategy.backtest(stock_data)

                # Add strategy name to metrics
                metrics['Strategy Name'] = strategy_name

                # Add to results
                results_list.append(metrics)
                self.results[strategy_name] = metrics

                # Print summary
                print(f"  ✓ Complete: {metrics['total_trades']} trades, "
                      f"{metrics['win_rate']:.1f}% win rate, "
                      f"{metrics['total_return_pct']:.2f}% return")

            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                continue

        # Create comparison DataFrame
        if results_list:
            results_df = pd.DataFrame(results_list)

            # Reorder columns for better readability
            column_order = [
                'Strategy Name', 'total_return_pct', 'sharpe_ratio', 'win_rate',
                'total_trades', 'profit_factor', 'max_drawdown', 'avg_win',
                'avg_loss', 'final_capital'
            ]

            existing_columns = [col for col in column_order if col in results_df.columns]
            results_df = results_df[existing_columns]

            # Sort by Sharpe ratio (descending)
            results_df = results_df.sort_values('sharpe_ratio', ascending=False)

            # Save results
            self._save_results(results_df)

            return results_df
        else:
            print("No results to compare")
            return pd.DataFrame()

    def test_single_strategy(self, strategy_name: str,
                            stock_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Test a single strategy.

        Args:
            strategy_name: Name of strategy to test
            stock_data: Stock data dictionary

        Returns:
            Performance metrics
        """
        if strategy_name not in self.strategies:
            raise ValueError(f"Strategy '{strategy_name}' not found")

        strategy = self.strategies[strategy_name]
        metrics = strategy.backtest(stock_data)
        self.results[strategy_name] = metrics

        return metrics

    def get_rankings(self, metric: str = 'sharpe_ratio') -> pd.DataFrame:
        """
        Get strategy rankings by a specific metric.

        Args:
            metric: Metric to rank by (sharpe_ratio, win_rate, total_return_pct, etc.)

        Returns:
            DataFrame with ranked strategies
        """
        if not self.results:
            print("No results available. Run test_all_strategies first.")
            return pd.DataFrame()

        results_df = pd.DataFrame(list(self.results.values()))

        if metric not in results_df.columns:
            print(f"Metric '{metric}' not found. Available: {list(results_df.columns)}")
            return pd.DataFrame()

        # Sort by metric
        ranked = results_df.sort_values(metric, ascending=False)

        return ranked[['strategy', metric, 'total_return_pct', 'win_rate',
                      'total_trades', 'sharpe_ratio', 'max_drawdown']]

    def print_comparison(self, results_df: pd.DataFrame = None):
        """Print formatted comparison table."""
        if results_df is None:
            if not self.results:
                print("No results to display")
                return
            results_df = pd.DataFrame(list(self.results.values()))

        print("\n" + "="*120)
        print("STRATEGY COMPARISON RESULTS")
        print("="*120)

        # Create formatted table
        print(f"\n{'Strategy':<30} {'Return %':<12} {'Sharpe':<10} {'Win Rate':<12} "
              f"{'Trades':<10} {'PF':<10} {'Max DD %':<12}")
        print("-"*120)

        for _, row in results_df.iterrows():
            strategy_name = row.get('Strategy Name', row.get('strategy', 'Unknown'))
            total_return = row.get('total_return_pct', 0)
            sharpe = row.get('sharpe_ratio', 0)
            win_rate = row.get('win_rate', 0)
            trades = row.get('total_trades', 0)
            pf = row.get('profit_factor', 0)
            max_dd = row.get('max_drawdown', 0)

            print(f"{strategy_name:<30} "
                  f"{total_return:>10.2f}%  "
                  f"{sharpe:>8.2f}  "
                  f"{win_rate:>10.1f}%  "
                  f"{trades:>8}  "
                  f"{pf:>8.2f}  "
                  f"{max_dd:>10.2f}%")

        print("="*120)

        # Highlight best performers
        if len(results_df) > 0:
            best_return = results_df.loc[results_df['total_return_pct'].idxmax()]
            best_sharpe = results_df.loc[results_df['sharpe_ratio'].idxmax()]
            best_win_rate = results_df.loc[results_df['win_rate'].idxmax()]

            print("\n🏆 BEST PERFORMERS:")
            print(f"  Highest Return: {best_return.get('Strategy Name', 'Unknown')} "
                  f"({best_return['total_return_pct']:.2f}%)")
            print(f"  Highest Sharpe: {best_sharpe.get('Strategy Name', 'Unknown')} "
                  f"({best_sharpe['sharpe_ratio']:.2f})")
            print(f"  Highest Win Rate: {best_win_rate.get('Strategy Name', 'Unknown')} "
                  f"({best_win_rate['win_rate']:.1f}%)")
            print("="*120 + "\n")

    def _save_results(self, results_df: pd.DataFrame):
        """Save strategy comparison results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save CSV
        csv_filename = f"result/optimization/strategy_comparison_{timestamp}.csv"
        results_df.to_csv(csv_filename, index=False)
        print(f"\n✓ Results saved to: {csv_filename}")

        # Save JSON rankings
        json_filename = f"result/optimization/strategy_rankings_{timestamp}.json"
        rankings = {
            'timestamp': timestamp,
            'strategies_tested': len(results_df),
            'rankings_by_sharpe': results_df.sort_values('sharpe_ratio', ascending=False)
                                            .to_dict('records'),
            'rankings_by_return': results_df.sort_values('total_return_pct', ascending=False)
                                            .to_dict('records'),
            'rankings_by_win_rate': results_df.sort_values('win_rate', ascending=False)
                                              .to_dict('records')
        }

        with open(json_filename, 'w') as f:
            json.dump(rankings, f, indent=2, default=str)

        print(f"✓ Rankings saved to: {json_filename}")

    def get_strategy_details(self, strategy_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific strategy."""
        if strategy_name not in self.strategies:
            return {}

        strategy = self.strategies[strategy_name]

        return {
            'name': strategy_name,
            'class': strategy.__class__.__name__,
            'parameters': strategy.params,
            'trades': len(strategy.trades),
            'positions': len(strategy.positions)
        }
