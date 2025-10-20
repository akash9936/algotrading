"""
Strategy Optimization Framework

This package provides tools for optimizing trading strategies through:
- Parameter grid search
- Multi-strategy testing
- Market regime analysis
- Machine learning insights
- Monte Carlo simulations
- Recommendation generation
"""

__version__ = "1.0.0"
__author__ = "Strategy Optimization Framework"

# Import only what's implemented
try:
    from .parameter_optimizer import ParameterOptimizer
    __all__ = ['ParameterOptimizer']
except ImportError as e:
    print(f"Warning: Could not import ParameterOptimizer: {e}")
    __all__ = []

# Other imports will be added as modules are completed
# from .strategy_tester import StrategyTester
# from .regime_analyzer import RegimeAnalyzer
# from .ml_insights import MLInsights
# from .monte_carlo import MonteCarloSimulator
# from .recommendation_engine import RecommendationEngine
