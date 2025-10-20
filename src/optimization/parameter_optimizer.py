"""
Parameter Optimizer - Grid Search Engine

This module handles systematic parameter optimization through grid search.
Tests thousands of parameter combinations to find optimal settings.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from itertools import product
from joblib import Parallel, delayed
import json
from datetime import datetime


class ParameterOptimizer:
    """
    Optimizes strategy parameters through systematic grid search.

    Features:
    - Intelligent parameter sampling
    - Parallel backtesting
    - Performance tracking
    - Top N parameter identification
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the parameter optimizer.

        Args:
            config: Configuration dictionary with parameter ranges
        """
        self.config = config or self._default_config()
        self.results = []

    def _default_config(self) -> Dict[str, Any]:
        """Default parameter ranges to test."""
        return {
            'rsi': {
                'period': [10, 12, 14, 16, 18, 20],
                'oversold': [25, 30, 35, 40, 45],
                'overbought': [60, 65, 70, 75, 80]
            },
            'macd': {
                'fast_period': [8, 10, 12, 14, 16],
                'slow_period': [20, 24, 26, 28, 30],
                'signal_period': [7, 9, 11, 12]
            },
            'risk_management': {
                'stop_loss': [0.02, 0.025, 0.03, 0.035, 0.04, 0.05],
                'take_profit': [0.05, 0.07, 0.10, 0.12, 0.15],
                'trailing_stop': [0.02, 0.025, 0.03, 0.04, 0.05],
                'max_hold_days': [10, 20, 30, 45, 60]
            },
            'position_management': {
                'max_positions': [1, 2, 3, 4, 5],
                'capital_per_position': [1.0, 0.5, 0.33, 0.25, 0.2]
            },
            'filters': {
                'ma_trend_period': [20, 50, 100, 200],
                'volume_multiplier': [1.0, 1.2, 1.5, 2.0],
                'min_signal_strength': [0.0, 0.05, 0.1, 0.15, 0.2]
            }
        }

    def generate_parameter_grid(self, sample_size: int = None) -> List[Dict[str, Any]]:
        """
        Generate parameter combinations to test.

        Args:
            sample_size: Number of combinations to sample (None = all)

        Returns:
            List of parameter dictionaries
        """
        # Generate all combinations
        param_names = []
        param_values = []

        for category, params in self.config.items():
            for param_name, values in params.items():
                param_names.append(f"{category}.{param_name}")
                param_values.append(values)

        # Create all combinations
        all_combinations = list(product(*param_values))

        # Sample if requested
        if sample_size and sample_size < len(all_combinations):
            indices = np.random.choice(len(all_combinations), sample_size, replace=False)
            all_combinations = [all_combinations[i] for i in indices]

        # Convert to dictionaries
        param_grids = []
        for combo in all_combinations:
            param_dict = {}
            for name, value in zip(param_names, combo):
                category, param = name.split('.')
                if category not in param_dict:
                    param_dict[category] = {}
                param_dict[category][param] = value
            param_grids.append(param_dict)

        return param_grids

    def optimize_parameters(self,
                          backtest_func,
                          data: pd.DataFrame,
                          sample_size: int = 5000,
                          n_jobs: int = -1) -> pd.DataFrame:
        """
        Run optimization across parameter grid.

        Args:
            backtest_func: Function to run backtest with parameters
            data: Historical data for backtesting
            sample_size: Number of parameter combinations to test
            n_jobs: Number of parallel jobs (-1 = all cores)

        Returns:
            DataFrame with all results
        """
        print(f"Generating parameter grid (sample_size={sample_size})...")
        param_grids = self.generate_parameter_grid(sample_size)

        print(f"Testing {len(param_grids)} parameter combinations...")
        print(f"Using {n_jobs if n_jobs > 0 else 'all available'} CPU cores")

        # Run backtests in parallel
        results = Parallel(n_jobs=n_jobs, verbose=10)(
            delayed(self._run_single_backtest)(backtest_func, data, params, i)
            for i, params in enumerate(param_grids)
        )

        # Convert to DataFrame
        results_df = pd.DataFrame(results)
        self.results = results_df

        # Save results
        self._save_results(results_df)

        return results_df

    def _run_single_backtest(self,
                            backtest_func,
                            data: pd.DataFrame,
                            params: Dict[str, Any],
                            index: int) -> Dict[str, Any]:
        """
        Run a single backtest with given parameters.

        Args:
            backtest_func: Backtesting function
            data: Historical data
            params: Parameter dictionary
            index: Combination index

        Returns:
            Dictionary with results
        """
        try:
            # Run backtest
            metrics = backtest_func(data, params)

            # Flatten parameters for storage
            flat_params = {}
            for category, param_dict in params.items():
                for param_name, value in param_dict.items():
                    flat_params[f"{category}_{param_name}"] = value

            # Combine parameters and metrics
            result = {**flat_params, **metrics, 'combination_id': index}
            return result

        except Exception as e:
            print(f"Error in combination {index}: {str(e)}")
            return {'combination_id': index, 'error': str(e)}

    def get_top_parameters(self,
                          n: int = 100,
                          metric: str = 'sharpe_ratio') -> pd.DataFrame:
        """
        Get top N parameter combinations.

        Args:
            n: Number of top combinations to return
            metric: Metric to rank by

        Returns:
            DataFrame with top N combinations
        """
        if self.results is None or len(self.results) == 0:
            raise ValueError("No results available. Run optimize_parameters first.")

        # Sort by metric
        sorted_results = self.results.sort_values(metric, ascending=False)
        top_n = sorted_results.head(n)

        # Save top parameters
        self._save_top_parameters(top_n)

        return top_n

    def _save_results(self, results_df: pd.DataFrame):
        """Save all optimization results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result/optimization/grid_search_results_{timestamp}.csv"
        results_df.to_csv(filename, index=False)
        print(f"Results saved to: {filename}")

    def _save_top_parameters(self, top_df: pd.DataFrame):
        """Save top parameter combinations."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result/optimization/top_100_parameters_{timestamp}.json"

        top_params = top_df.to_dict('records')
        with open(filename, 'w') as f:
            json.dump(top_params, f, indent=2)

        print(f"Top parameters saved to: {filename}")
