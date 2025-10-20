# Strategy Optimization Framework

## Overview
This package provides a comprehensive framework for optimizing trading strategies through systematic analysis, testing, and machine learning insights.

## Implementation Status

✅ **STEP 1 COMPLETE**: Project Structure Setup
✅ **STEP 2 COMPLETE**: Parameter Grid Generator
✅ **STEP 3 COMPLETE**: Multi-Strategy Testing Engine
⏳ **STEP 4-8**: Pending

## Directory Structure

```
src/optimization/
├── __init__.py                    # Package initialization
├── base_strategy.py               # ✅ Abstract base class for all strategies
├── strategies.py                  # ✅ 7 strategy implementations
├── parameter_optimizer.py         # ✅ Grid search engine
├── strategy_tester.py             # ✅ Multi-strategy comparison engine
├── backtest_wrapper.py            # ✅ Integration wrapper
├── regime_analyzer.py             # ⏳ Market regime detection
├── ml_insights.py                 # ⏳ Machine learning analysis
├── monte_carlo.py                 # ⏳ Risk simulation
└── recommendation_engine.py       # ⏳ Trading rules generation

config/
└── optimization_config.json       # ✅ Configuration settings

result/optimization/
└── (auto-generated results)       # All optimization outputs
```

## Implemented Modules

### 1. Base Strategy (`base_strategy.py`) ✅
- Abstract `BaseStrategy` class
- Standardized backtesting interface
- Multi-position support
- Risk management (stop loss, take profit, trailing stop)
- Performance metrics (Sharpe, max drawdown, etc.)
- Technical indicator helpers

### 2. Strategies (`strategies.py`) ✅
**7 Trading Strategies Implemented:**
1. RSI Mean Reversion
2. MACD Crossover
3. Bollinger Band Mean Reversion
4. Moving Average Crossover (10/30)
5. Moving Average Crossover (20/50)
6. ATR Breakout
7. Multi-Signal Confluence (RSI + MACD)

### 3. Parameter Optimizer (`parameter_optimizer.py`) ✅
- Systematic grid search across parameter space
- Intelligent sampling (test 5K instead of 1.5M combinations)
- Parallel backtesting with joblib
- Top N parameter identification
- Auto-save results to CSV/JSON

### 4. Strategy Tester (`strategy_tester.py`) ✅
- Automatic strategy registration
- Parallel testing of all strategies
- Fair comparison (same data, same capital)
- Performance ranking by multiple metrics
- Formatted comparison tables
- Auto-save results

### 5. Backtest Wrapper (`backtest_wrapper.py`) ✅
- Integration with existing strategies
- Comprehensive metrics calculation
- Sharpe, Sortino, Calmar ratios
- Recovery factor, expectancy

## Usage Examples

### Quick Test (5 stocks, 2024 data)
```bash
python test_step3_quick.py      # Verify imports
python test_strategies.py       # Run full test
```

### Run Optimization Phases
```bash
# Phase 1: Parameter Grid Search
python src/run_optimization.py --phase=1 --sample-size=500

# Phase 2: Multi-Strategy Testing
python3 src/run_optimization.py --phase=2

# Full optimization (all phases)
python src/run_optimization.py --full
```

### Programmatic Usage
```python
from optimization.strategy_tester import StrategyTester
from utills.load_data import DataLoader

# Load data
loader = DataLoader()
data = loader.load_all_nifty50()

# Test all strategies
tester = StrategyTester(initial_capital=100000)
results = tester.test_all_strategies(data)

# View comparison
tester.print_comparison(results)

# Get best strategy
best = results.sort_values('sharpe_ratio', ascending=False).iloc[0]
print(f"Best: {best['Strategy Name']} - Sharpe: {best['sharpe_ratio']:.2f}")
```

### Add Custom Strategy
```python
from optimization.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def prepare_data(self, df):
        # Add indicators
        return df

    def generate_signals(self, df, date):
        # Entry logic
        return has_signal, signal_strength

    def check_exit(self, df, position, date):
        # Exit logic
        return should_exit, exit_reason

# Add to tester
tester.add_strategy('My_Strategy', MyStrategy(params))
results = tester.test_all_strategies(data)
```

## Performance Metrics

All strategies calculate:
- **Total Return (%)**: Overall profit/loss percentage
- **Sharpe Ratio**: Risk-adjusted returns
- **Sortino Ratio**: Downside risk-adjusted returns
- **Calmar Ratio**: Return / max drawdown
- **Win Rate (%)**: Percentage of profitable trades
- **Profit Factor**: Gross profit / gross loss
- **Max Drawdown (%)**: Largest peak-to-trough decline
- **Average Win/Loss**: Mean profit/loss per trade
- **Average Days Held**: Mean holding period
- **Total Trades**: Number of trades executed

## Output Files

### Strategy Comparison (Phase 2)
- `strategy_comparison_YYYYMMDD_HHMMSS.csv` - All metrics
- `strategy_rankings_YYYYMMDD_HHMMSS.json` - Rankings by Sharpe, return, win rate

### Parameter Grid Search (Phase 1)
- `grid_search_results_YYYYMMDD_HHMMSS.csv` - All tested combinations
- `top_100_parameters_YYYYMMDD_HHMMSS.json` - Best performing parameters

## Configuration

Edit `config/optimization_config.json` to customize:
- Parameter ranges to test
- Strategies to include
- Optimization settings (sample size, n_jobs)
- Data filtering (date ranges, stocks)
- Output preferences

## Next Steps

### STEP 4: Market Regime Analysis
- Bull/Bear/Sideways detection
- High/Low volatility regimes
- Strategy performance by regime
- Regime-specific recommendations

### STEP 5-8: Advanced Features
- Stock-specific optimization
- ML insights and patterns
- Walk-forward validation
- Monte Carlo simulations
- Final recommendations

---

**Current Status**: 3/8 steps complete (37.5%)
**Lines of Code**: ~2,500+ LOC
**Strategies**: 7 implemented, extensible framework
**Ready for**: Phase 2 testing on full dataset
