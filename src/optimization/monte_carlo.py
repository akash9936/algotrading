"""
Monte Carlo Simulator - Risk Analysis

This module performs Monte Carlo simulations to assess potential
future outcomes and risk metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from datetime import datetime
import json


class MonteCarloSimulator:
    """
    Monte Carlo simulation for risk assessment.

    Features:
    - Trade outcome simulations
    - Risk metric calculation (VaR, CVaR)
    - Probability distributions
    - Worst-case scenario analysis
    """

    def __init__(self, n_simulations: int = 10000):
        self.n_simulations = n_simulations
        self.simulation_results = None
        self.risk_metrics = {}

    def run_simulations(self, trades: List[Dict], initial_capital: float = 100000) -> pd.DataFrame:
        """
        Run Monte Carlo simulations by randomly sampling from historical trades.

        Args:
            trades: List of historical trades
            initial_capital: Starting capital

        Returns:
            DataFrame with simulation results
        """
        print(f"\nRunning {self.n_simulations:,} Monte Carlo simulations...")

        if not trades or len(trades) < 10:
            print("  Not enough trades for simulation")
            return pd.DataFrame()

        trades_df = pd.DataFrame(trades)
        pnl_values = trades_df['PnL'].values

        # Run simulations
        simulation_outcomes = []

        for sim in range(self.n_simulations):
            # Randomly sample trades with replacement
            sampled_pnls = np.random.choice(pnl_values, size=len(pnl_values), replace=True)

            # Calculate cumulative return
            final_capital = initial_capital + sampled_pnls.sum()
            total_return_pct = ((final_capital - initial_capital) / initial_capital) * 100

            # Calculate max drawdown for this simulation
            cumulative_pnl = np.cumsum(sampled_pnls)
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = cumulative_pnl - running_max
            max_drawdown = (drawdown.min() / initial_capital) * 100

            simulation_outcomes.append({
                'simulation_id': sim,
                'final_capital': final_capital,
                'total_return_pct': total_return_pct,
                'max_drawdown_pct': max_drawdown
            })

        results_df = pd.DataFrame(simulation_outcomes)
        self.simulation_results = results_df

        print(f"✓ Simulations complete")

        return results_df

    def calculate_risk_metrics(self, confidence_level: float = 0.95) -> Dict[str, Any]:
        """
        Calculate risk metrics from simulation results.

        Args:
            confidence_level: Confidence level for VaR/CVaR (default 95%)

        Returns:
            Dictionary with risk metrics
        """
        if self.simulation_results is None or len(self.simulation_results) == 0:
            return {}

        print("\nCalculating risk metrics...")

        returns = self.simulation_results['total_return_pct']

        # Percentiles
        percentiles = {
            'p95': np.percentile(returns, 95),  # Best case (95th percentile)
            'p50': np.percentile(returns, 50),  # Median
            'p5': np.percentile(returns, 5),    # Worst case (5th percentile)
        }

        # Value at Risk (VaR)
        var_level = (1 - confidence_level) * 100
        var = np.percentile(returns, var_level)

        # Conditional Value at Risk (CVaR) - average of worst outcomes
        var_threshold = np.percentile(returns, var_level)
        worst_outcomes = returns[returns <= var_threshold]
        cvar = worst_outcomes.mean() if len(worst_outcomes) > 0 else var

        # Probability metrics
        prob_profit = (returns > 0).sum() / len(returns) * 100
        prob_loss = (returns < 0).sum() / len(returns) * 100
        prob_large_gain = (returns > 20).sum() / len(returns) * 100
        prob_large_loss = (returns < -10).sum() / len(returns) * 100

        # Drawdown metrics
        max_dd = self.simulation_results['max_drawdown_pct'].min()
        avg_dd = self.simulation_results['max_drawdown_pct'].mean()

        metrics = {
            'percentiles': percentiles,
            'var_95': var,
            'cvar_95': cvar,
            'prob_profit': prob_profit,
            'prob_loss': prob_loss,
            'prob_large_gain_20pct': prob_large_gain,
            'prob_large_loss_10pct': prob_large_loss,
            'max_drawdown': max_dd,
            'avg_drawdown': avg_dd,
            'expected_return': returns.mean(),
            'return_std': returns.std()
        }

        self.risk_metrics = metrics

        # Print metrics
        print(f"  Expected Return: {metrics['expected_return']:.2f}%")
        print(f"  Best Case (95th): {percentiles['p95']:.2f}%")
        print(f"  Median (50th): {percentiles['p50']:.2f}%")
        print(f"  Worst Case (5th): {percentiles['p5']:.2f}%")
        print(f"  VaR (95%): {var:.2f}%")
        print(f"  CVaR (95%): {cvar:.2f}%")
        print(f"  Probability of Profit: {prob_profit:.1f}%")
        print(f"  Max Drawdown: {max_dd:.2f}%")

        return metrics

    def generate_distribution_stats(self) -> Dict[str, Any]:
        """Generate detailed distribution statistics."""
        if self.simulation_results is None:
            return {}

        returns = self.simulation_results['total_return_pct']

        stats = {
            'mean': returns.mean(),
            'median': returns.median(),
            'std': returns.std(),
            'min': returns.min(),
            'max': returns.max(),
            'skewness': returns.skew(),
            'kurtosis': returns.kurtosis(),
            'percentiles': {
                'p1': np.percentile(returns, 1),
                'p5': np.percentile(returns, 5),
                'p10': np.percentile(returns, 10),
                'p25': np.percentile(returns, 25),
                'p50': np.percentile(returns, 50),
                'p75': np.percentile(returns, 75),
                'p90': np.percentile(returns, 90),
                'p95': np.percentile(returns, 95),
                'p99': np.percentile(returns, 99),
            }
        }

        return stats

    def analyze_multiple_strategies(self, all_strategy_trades: Dict[str, List[Dict]],
                                   initial_capital: float = 100000) -> pd.DataFrame:
        """
        Run Monte Carlo for multiple strategies and compare risk profiles.

        Args:
            all_strategy_trades: Dict of {strategy_name: list of trades}
            initial_capital: Starting capital

        Returns:
            Comparison DataFrame
        """
        print("\n" + "="*80)
        print("MONTE CARLO RISK ANALYSIS - MULTIPLE STRATEGIES")
        print("="*80)

        comparison_results = []

        for strategy_name, trades in all_strategy_trades.items():
            print(f"\nAnalyzing: {strategy_name}...")

            if not trades or len(trades) < 10:
                print(f"  Skipping - not enough trades")
                continue

            # Run simulations
            sim_results = self.run_simulations(trades, initial_capital)

            if sim_results.empty:
                continue

            # Calculate metrics
            metrics = self.calculate_risk_metrics()

            # Add to comparison
            comparison_results.append({
                'Strategy': strategy_name,
                'Expected Return %': metrics['expected_return'],
                'Median Return %': metrics['percentiles']['p50'],
                'Best Case (95%) %': metrics['percentiles']['p95'],
                'Worst Case (5%) %': metrics['percentiles']['p5'],
                'VaR (95%) %': metrics['var_95'],
                'CVaR (95%) %': metrics['cvar_95'],
                'Prob Profit %': metrics['prob_profit'],
                'Max Drawdown %': metrics['max_drawdown'],
                'Risk/Reward': abs(metrics['expected_return'] / metrics['max_drawdown']) if metrics['max_drawdown'] != 0 else 0
            })

        comparison_df = pd.DataFrame(comparison_results)

        if not comparison_df.empty:
            # Sort by expected return
            comparison_df = comparison_df.sort_values('Expected Return %', ascending=False)

            # Print comparison table
            print("\n" + "="*120)
            print("RISK COMPARISON ACROSS STRATEGIES")
            print("="*120)
            print(comparison_df.to_string(index=False))
            print("="*120)

        return comparison_df

    def save_results(self, output_dir: str = "result/optimization"):
        """Save Monte Carlo results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save simulation results
        if self.simulation_results is not None:
            sim_file = f"{output_dir}/monte_carlo_simulations_{timestamp}.csv"
            self.simulation_results.to_csv(sim_file, index=False)
            print(f"✓ Simulations saved: {sim_file}")

        # Save risk metrics
        if self.risk_metrics:
            metrics_file = f"{output_dir}/monte_carlo_metrics_{timestamp}.json"
            with open(metrics_file, 'w') as f:
                json.dump(self.risk_metrics, f, indent=2, default=str)
            print(f"✓ Risk metrics saved: {metrics_file}")
