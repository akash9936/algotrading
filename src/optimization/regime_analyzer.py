"""
Regime Analyzer - Market Regime Detection and Analysis

This module identifies market regimes and analyzes strategy performance
in different market conditions.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from enum import Enum
from datetime import datetime
import json


class MarketRegime(Enum):
    """Market regime types."""
    BULL = "bull_market"
    BEAR = "bear_market"
    SIDEWAYS = "sideways_market"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


class RegimeAnalyzer:
    """
    Detects market regimes and analyzes strategy performance by regime.

    Features:
    - Bull/Bear/Sideways detection using moving averages
    - Volatility regime identification using ATR
    - Performance analysis by regime
    - Regime-specific recommendations
    """

    def __init__(self,
                 trend_ma_short: int = 50,
                 trend_ma_long: int = 200,
                 volatility_period: int = 20,
                 volatility_percentile_high: float = 70,
                 volatility_percentile_low: float = 30):
        """
        Initialize regime analyzer.

        Args:
            trend_ma_short: Short moving average for trend (default 50)
            trend_ma_long: Long moving average for trend (default 200)
            volatility_period: Period for volatility calculation (default 20)
            volatility_percentile_high: Percentile for high volatility (default 70)
            volatility_percentile_low: Percentile for low volatility (default 30)
        """
        self.trend_ma_short = trend_ma_short
        self.trend_ma_long = trend_ma_long
        self.volatility_period = volatility_period
        self.volatility_percentile_high = volatility_percentile_high
        self.volatility_percentile_low = volatility_percentile_low

        self.regimes = None
        self.regime_performance = {}
        self.regime_stats = {}

    def detect_regimes(self, index_data: pd.DataFrame,
                      index_name: str = "NIFTY 50") -> pd.DataFrame:
        """
        Detect market regimes from index data.

        Args:
            index_data: DataFrame with OHLCV data for market index
            index_name: Name of the index (for reporting)

        Returns:
            DataFrame with regime labels for each date
        """
        print(f"\nDetecting market regimes for {index_name}...")

        df = index_data.copy()

        # Calculate moving averages for trend detection
        df['MA_Short'] = df['Close'].rolling(window=self.trend_ma_short).mean()
        df['MA_Long'] = df['Close'].rolling(window=self.trend_ma_long).mean()

        # Calculate ATR for volatility
        df['ATR'] = self._calculate_atr(df, self.volatility_period)
        df['ATR_Pct'] = (df['ATR'] / df['Close']) * 100

        # Detect trend regimes
        df['Trend_Regime'] = self._detect_trend_regime(df)

        # Detect volatility regimes
        df['Volatility_Regime'] = self._detect_volatility_regime(df)

        # Combine regimes
        df['Combined_Regime'] = df.apply(
            lambda row: f"{row['Trend_Regime']}_{row['Volatility_Regime']}"
            if pd.notna(row['Trend_Regime']) and pd.notna(row['Volatility_Regime'])
            else None,
            axis=1
        )

        # Calculate regime statistics
        self._calculate_regime_stats(df)

        self.regimes = df

        print(f"✓ Regime detection complete")
        print(f"  Date range: {df.index[0].date()} to {df.index[-1].date()}")
        print(f"  Total days: {len(df)}")

        return df

    def _detect_trend_regime(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect trend regime (Bull/Bear/Sideways).

        Bull: Price > MA_Short > MA_Long and price making higher highs
        Bear: Price < MA_Short < MA_Long and price making lower lows
        Sideways: Otherwise
        """
        regime = pd.Series(index=df.index, dtype=object)

        for i in range(len(df)):
            if pd.isna(df['MA_Short'].iloc[i]) or pd.isna(df['MA_Long'].iloc[i]):
                regime.iloc[i] = None
                continue

            price = df['Close'].iloc[i]
            ma_short = df['MA_Short'].iloc[i]
            ma_long = df['MA_Long'].iloc[i]

            # Bull market conditions
            if price > ma_short and ma_short > ma_long:
                regime.iloc[i] = MarketRegime.BULL.value

            # Bear market conditions
            elif price < ma_short and ma_short < ma_long:
                regime.iloc[i] = MarketRegime.BEAR.value

            # Sideways market
            else:
                regime.iloc[i] = MarketRegime.SIDEWAYS.value

        return regime

    def _detect_volatility_regime(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect volatility regime (High/Low).

        Uses percentiles of ATR% to classify volatility.
        """
        regime = pd.Series(index=df.index, dtype=object)

        # Calculate percentiles
        atr_pct = df['ATR_Pct'].dropna()
        if len(atr_pct) == 0:
            return regime

        high_threshold = np.percentile(atr_pct, self.volatility_percentile_high)
        low_threshold = np.percentile(atr_pct, self.volatility_percentile_low)

        for i in range(len(df)):
            if pd.isna(df['ATR_Pct'].iloc[i]):
                regime.iloc[i] = None
                continue

            atr_pct_value = df['ATR_Pct'].iloc[i]

            if atr_pct_value >= high_threshold:
                regime.iloc[i] = MarketRegime.HIGH_VOLATILITY.value
            elif atr_pct_value <= low_threshold:
                regime.iloc[i] = MarketRegime.LOW_VOLATILITY.value
            else:
                # Medium volatility (not classified as high or low)
                regime.iloc[i] = "medium_volatility"

        return regime

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range."""
        high = df['High']
        low = df['Low']
        close = df['Close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    def _calculate_regime_stats(self, df: pd.DataFrame):
        """Calculate statistics for each regime."""
        stats = {}

        # Trend regime stats
        for regime in [MarketRegime.BULL.value, MarketRegime.BEAR.value,
                      MarketRegime.SIDEWAYS.value]:
            regime_data = df[df['Trend_Regime'] == regime]
            if len(regime_data) > 0:
                stats[regime] = {
                    'days': len(regime_data),
                    'percentage': len(regime_data) / len(df) * 100,
                    'avg_return': regime_data['Close'].pct_change().mean() * 100,
                    'volatility': regime_data['ATR_Pct'].mean()
                }

        # Volatility regime stats
        for regime in [MarketRegime.HIGH_VOLATILITY.value,
                      MarketRegime.LOW_VOLATILITY.value, "medium_volatility"]:
            regime_data = df[df['Volatility_Regime'] == regime]
            if len(regime_data) > 0:
                stats[regime] = {
                    'days': len(regime_data),
                    'percentage': len(regime_data) / len(df) * 100,
                    'avg_return': regime_data['Close'].pct_change().mean() * 100,
                    'volatility': regime_data['ATR_Pct'].mean()
                }

        self.regime_stats = stats

    def print_regime_summary(self):
        """Print summary of detected regimes."""
        if self.regimes is None:
            print("No regimes detected. Run detect_regimes() first.")
            return

        print("\n" + "="*80)
        print("MARKET REGIME SUMMARY")
        print("="*80)

        print("\n📊 TREND REGIMES:")
        for regime in [MarketRegime.BULL.value, MarketRegime.BEAR.value,
                      MarketRegime.SIDEWAYS.value]:
            if regime in self.regime_stats:
                stats = self.regime_stats[regime]
                print(f"  {regime.replace('_', ' ').title()}:")
                print(f"    Days: {stats['days']} ({stats['percentage']:.1f}%)")
                print(f"    Avg Daily Return: {stats['avg_return']:.3f}%")
                print(f"    Avg Volatility: {stats['volatility']:.2f}%")

        print("\n📈 VOLATILITY REGIMES:")
        for regime in [MarketRegime.HIGH_VOLATILITY.value,
                      "medium_volatility",
                      MarketRegime.LOW_VOLATILITY.value]:
            if regime in self.regime_stats:
                stats = self.regime_stats[regime]
                print(f"  {regime.replace('_', ' ').title()}:")
                print(f"    Days: {stats['days']} ({stats['percentage']:.1f}%)")
                print(f"    Avg Volatility: {stats['volatility']:.2f}%")

        print("="*80)

    def analyze_strategy_by_regime(self,
                                   strategy_trades: List[Dict],
                                   strategy_name: str) -> Dict[str, Any]:
        """
        Analyze strategy performance in different market regimes.

        Args:
            strategy_trades: List of trade dictionaries from a strategy
            strategy_name: Name of the strategy

        Returns:
            Dictionary with performance by regime
        """
        if self.regimes is None:
            raise ValueError("Regimes not detected. Run detect_regimes() first.")

        if not strategy_trades:
            return {}

        trades_df = pd.DataFrame(strategy_trades)

        # Map trades to regimes
        trades_df['Entry_Regime'] = trades_df['Entry Date'].apply(
            lambda date: self._get_regime_for_date(date, 'Trend_Regime')
        )
        trades_df['Entry_Volatility'] = trades_df['Entry Date'].apply(
            lambda date: self._get_regime_for_date(date, 'Volatility_Regime')
        )

        # Analyze by trend regime
        regime_performance = {}

        for regime in [MarketRegime.BULL.value, MarketRegime.BEAR.value,
                      MarketRegime.SIDEWAYS.value]:
            regime_trades = trades_df[trades_df['Entry_Regime'] == regime]

            if len(regime_trades) > 0:
                winning = regime_trades[regime_trades['PnL'] > 0]
                losing = regime_trades[regime_trades['PnL'] <= 0]

                regime_performance[regime] = {
                    'total_trades': len(regime_trades),
                    'winning_trades': len(winning),
                    'losing_trades': len(losing),
                    'win_rate': len(winning) / len(regime_trades) * 100,
                    'total_pnl': regime_trades['PnL'].sum(),
                    'avg_pnl': regime_trades['PnL'].mean(),
                    'avg_win': winning['PnL'].mean() if len(winning) > 0 else 0,
                    'avg_loss': losing['PnL'].mean() if len(losing) > 0 else 0,
                    'profit_factor': (
                        winning['PnL'].sum() / abs(losing['PnL'].sum())
                        if len(losing) > 0 and losing['PnL'].sum() != 0
                        else float('inf')
                    )
                }

        # Store for this strategy
        self.regime_performance[strategy_name] = regime_performance

        return regime_performance

    def _get_regime_for_date(self, date: pd.Timestamp,
                            regime_type: str) -> Optional[str]:
        """Get regime for a specific date."""
        if date not in self.regimes.index:
            return None

        return self.regimes.loc[date, regime_type]

    def compare_strategies_by_regime(self,
                                    all_strategy_results: Dict[str, List[Dict]]) -> pd.DataFrame:
        """
        Compare all strategies' performance across regimes.

        Args:
            all_strategy_results: Dict of {strategy_name: list of trades}

        Returns:
            DataFrame with comparison across regimes
        """
        comparison_data = []

        for strategy_name, trades in all_strategy_results.items():
            regime_perf = self.analyze_strategy_by_regime(trades, strategy_name)

            for regime, metrics in regime_perf.items():
                comparison_data.append({
                    'Strategy': strategy_name,
                    'Regime': regime,
                    'Total Trades': metrics['total_trades'],
                    'Win Rate %': metrics['win_rate'],
                    'Total PnL': metrics['total_pnl'],
                    'Avg PnL': metrics['avg_pnl'],
                    'Profit Factor': metrics['profit_factor']
                })

        if comparison_data:
            df = pd.DataFrame(comparison_data)
            return df
        else:
            return pd.DataFrame()

    def generate_regime_recommendations(self) -> Dict[str, Any]:
        """
        Generate trading recommendations based on regime analysis.

        Returns:
            Dictionary with recommendations for each strategy
        """
        if not self.regime_performance:
            return {}

        recommendations = {}

        for strategy_name, regime_perf in self.regime_performance.items():
            best_regime = None
            best_win_rate = 0
            worst_regime = None
            worst_win_rate = 100

            regime_ratings = {}

            for regime, metrics in regime_perf.items():
                win_rate = metrics['win_rate']
                profit_factor = metrics['profit_factor']

                # Rate regime for this strategy
                if win_rate > 60 and profit_factor > 1.5:
                    rating = "EXCELLENT"
                elif win_rate > 55 and profit_factor > 1.3:
                    rating = "GOOD"
                elif win_rate > 50 and profit_factor > 1.0:
                    rating = "ACCEPTABLE"
                else:
                    rating = "AVOID"

                regime_ratings[regime] = rating

                # Track best/worst
                if win_rate > best_win_rate:
                    best_win_rate = win_rate
                    best_regime = regime

                if win_rate < worst_win_rate:
                    worst_win_rate = win_rate
                    worst_regime = regime

            recommendations[strategy_name] = {
                'best_regime': best_regime,
                'best_win_rate': best_win_rate,
                'worst_regime': worst_regime,
                'worst_win_rate': worst_win_rate,
                'regime_ratings': regime_ratings,
                'recommendation': self._generate_strategy_recommendation(
                    regime_ratings, best_regime, worst_regime
                )
            }

        return recommendations

    def _generate_strategy_recommendation(self,
                                         regime_ratings: Dict[str, str],
                                         best_regime: str,
                                         worst_regime: str) -> str:
        """Generate human-readable recommendation text."""
        excellent_regimes = [r for r, rating in regime_ratings.items()
                           if rating == "EXCELLENT"]
        avoid_regimes = [r for r, rating in regime_ratings.items()
                        if rating == "AVOID"]

        if excellent_regimes:
            rec = f"Use ONLY in {', '.join(excellent_regimes).replace('_', ' ')} markets."
        elif best_regime:
            rec = f"Best in {best_regime.replace('_', ' ')} markets."
        else:
            rec = "No clear regime preference."

        if avoid_regimes:
            rec += f" AVOID in {', '.join(avoid_regimes).replace('_', ' ')} markets."

        return rec

    def print_regime_comparison(self, comparison_df: pd.DataFrame):
        """Print formatted regime comparison table."""
        if comparison_df.empty:
            print("No regime comparison data available.")
            return

        print("\n" + "="*100)
        print("STRATEGY PERFORMANCE BY MARKET REGIME")
        print("="*100)

        for regime in [MarketRegime.BULL.value, MarketRegime.BEAR.value,
                      MarketRegime.SIDEWAYS.value]:
            regime_data = comparison_df[comparison_df['Regime'] == regime]

            if len(regime_data) == 0:
                continue

            print(f"\n📊 {regime.replace('_', ' ').upper()}:")
            print(f"{'Strategy':<30} {'Trades':<10} {'Win Rate':<12} {'Total PnL':<15} {'Profit Factor':<15}")
            print("-"*100)

            # Sort by win rate
            regime_data = regime_data.sort_values('Win Rate %', ascending=False)

            for _, row in regime_data.iterrows():
                pf = row['Profit Factor']
                pf_str = "∞" if pf == float('inf') else f"{pf:.2f}"

                print(f"{row['Strategy']:<30} "
                      f"{row['Total Trades']:<10} "
                      f"{row['Win Rate %']:<10.1f}%  "
                      f"₹{row['Total PnL']:<13,.0f} "
                      f"{pf_str:<15}")

        print("="*100)

    def save_results(self, output_dir: str = "result/optimization"):
        """Save regime analysis results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save regime data
        if self.regimes is not None:
            regime_file = f"{output_dir}/market_regimes_{timestamp}.csv"
            self.regimes.to_csv(regime_file)
            print(f"✓ Regimes saved: {regime_file}")

        # Save regime performance
        if self.regime_performance:
            perf_file = f"{output_dir}/regime_performance_{timestamp}.json"
            with open(perf_file, 'w') as f:
                json.dump(self.regime_performance, f, indent=2, default=str)
            print(f"✓ Performance saved: {perf_file}")

        # Save recommendations
        recommendations = self.generate_regime_recommendations()
        if recommendations:
            rec_file = f"{output_dir}/regime_recommendations_{timestamp}.json"
            with open(rec_file, 'w') as f:
                json.dump(recommendations, f, indent=2)
            print(f"✓ Recommendations saved: {rec_file}")
