"""
Backtest Wrapper - Integrates existing strategy with optimizer

This module wraps existing strategy code to work with the optimization framework.
"""

import pandas as pd
import numpy as np
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_backtest_with_params(data: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, float]:
    """
    Run a backtest with specific parameters and return performance metrics.

    This function wraps the existing AlphabeticalMultiSignalStrategy to work
    with the parameter optimizer.

    Args:
        data: Dictionary of {symbol: DataFrame} with OHLC data
        params: Parameter dictionary with structure:
                {
                    'rsi': {'period': 14, 'oversold': 40, 'overbought': 70},
                    'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                    'risk_management': {'stop_loss': 0.03, 'take_profit': 0.10, ...},
                    'position_management': {'max_positions': 5, ...},
                    'filters': {'ma_trend_period': 50, ...}
                }

    Returns:
        Dictionary with performance metrics:
        {
            'total_return': float,
            'sharpe_ratio': float,
            'win_rate': float,
            'max_drawdown': float,
            'profit_factor': float,
            'total_trades': int,
            'avg_win': float,
            'avg_loss': float
        }
    """

    # Import the strategy class (we'll modify this to accept parameters)
    from strategy.strategy_multi_signal_sequential import AlphabeticalMultiSignalStrategy

    # Create a modified strategy instance with custom parameters
    strategy = create_strategy_with_params(params)

    # Run backtest
    results = strategy.backtest(data)

    # Calculate additional metrics
    metrics = calculate_metrics(strategy, results)

    return metrics


def create_strategy_with_params(params: Dict[str, Any]):
    """
    Create a strategy instance with custom parameters.

    This is a placeholder that will be implemented to dynamically set
    strategy parameters.
    """
    # TODO: Implement dynamic parameter injection
    # For now, return a basic strategy
    pass


def calculate_metrics(strategy, results: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate comprehensive performance metrics for optimization.

    Args:
        strategy: Strategy instance with trades and portfolio history
        results: Basic results from strategy.calculate_performance_metrics()

    Returns:
        Dictionary with all required metrics
    """

    # Basic metrics from strategy
    total_return = results.get('total_return_pct', 0)
    win_rate = results.get('win_rate', 0)
    total_trades = results.get('total_trades', 0)
    profit_factor = results.get('profit_factor', 0)
    avg_win = results.get('avg_win', 0)
    avg_loss = results.get('avg_loss', 0)

    # Calculate Sharpe Ratio
    sharpe_ratio = calculate_sharpe_ratio(strategy.daily_portfolio_value, strategy.initial_capital)

    # Calculate Maximum Drawdown
    max_drawdown = calculate_max_drawdown(strategy.daily_portfolio_value, strategy.initial_capital)

    # Calculate Sortino Ratio (downside risk)
    sortino_ratio = calculate_sortino_ratio(strategy.daily_portfolio_value, strategy.initial_capital)

    # Calculate Calmar Ratio (return / max drawdown)
    calmar_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # Calculate expectancy
    if total_trades > 0:
        expectancy = (win_rate / 100 * avg_win + (100 - win_rate) / 100 * avg_loss)
    else:
        expectancy = 0

    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'calmar_ratio': calmar_ratio,
        'win_rate': win_rate,
        'max_drawdown': max_drawdown,
        'profit_factor': profit_factor,
        'total_trades': total_trades,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy
    }


def calculate_sharpe_ratio(daily_portfolio_value: list, initial_capital: float,
                          risk_free_rate: float = 0.05) -> float:
    """
    Calculate Sharpe Ratio from daily portfolio values.

    Args:
        daily_portfolio_value: List of {'Date': date, 'Portfolio Value': value}
        initial_capital: Starting capital
        risk_free_rate: Annual risk-free rate (default 5%)

    Returns:
        Sharpe Ratio
    """
    if not daily_portfolio_value or len(daily_portfolio_value) < 2:
        return 0.0

    # Convert to DataFrame
    df = pd.DataFrame(daily_portfolio_value)
    df = df.sort_values('Date')

    # Calculate daily returns
    df['Returns'] = df['Portfolio Value'].pct_change()

    # Remove NaN values
    returns = df['Returns'].dropna()

    if len(returns) < 2:
        return 0.0

    # Calculate annualized metrics
    trading_days_per_year = 252

    # Mean return (annualized)
    mean_return = returns.mean() * trading_days_per_year

    # Standard deviation (annualized)
    std_return = returns.std() * np.sqrt(trading_days_per_year)

    if std_return == 0:
        return 0.0

    # Sharpe ratio
    sharpe = (mean_return - risk_free_rate) / std_return

    return sharpe


def calculate_sortino_ratio(daily_portfolio_value: list, initial_capital: float,
                           risk_free_rate: float = 0.05) -> float:
    """
    Calculate Sortino Ratio (considers only downside volatility).
    """
    if not daily_portfolio_value or len(daily_portfolio_value) < 2:
        return 0.0

    df = pd.DataFrame(daily_portfolio_value)
    df = df.sort_values('Date')
    df['Returns'] = df['Portfolio Value'].pct_change()
    returns = df['Returns'].dropna()

    if len(returns) < 2:
        return 0.0

    trading_days_per_year = 252
    mean_return = returns.mean() * trading_days_per_year

    # Downside deviation (only negative returns)
    downside_returns = returns[returns < 0]
    if len(downside_returns) < 2:
        return 0.0

    downside_std = downside_returns.std() * np.sqrt(trading_days_per_year)

    if downside_std == 0:
        return 0.0

    sortino = (mean_return - risk_free_rate) / downside_std

    return sortino


def calculate_max_drawdown(daily_portfolio_value: list, initial_capital: float) -> float:
    """
    Calculate Maximum Drawdown from daily portfolio values.

    Returns:
        Maximum drawdown as a percentage (negative value)
    """
    if not daily_portfolio_value:
        return 0.0

    df = pd.DataFrame(daily_portfolio_value)
    df = df.sort_values('Date')

    # Calculate running maximum
    df['Cumulative_Max'] = df['Portfolio Value'].cummax()

    # Calculate drawdown
    df['Drawdown'] = (df['Portfolio Value'] - df['Cumulative_Max']) / df['Cumulative_Max'] * 100

    # Maximum drawdown (most negative value)
    max_dd = df['Drawdown'].min()

    return max_dd


def calculate_recovery_factor(total_return: float, max_drawdown: float) -> float:
    """
    Calculate Recovery Factor = Total Return / |Max Drawdown|

    Higher is better (shows how much return per unit of drawdown risk)
    """
    if max_drawdown == 0:
        return 0.0

    return total_return / abs(max_drawdown)
