"""
ML Insights - Machine Learning Analysis Engine

This module uses machine learning to discover patterns and insights
that improve trading strategy performance.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from datetime import datetime
import json


class MLInsights:
    """
    Machine learning based insights for strategy optimization.

    Features:
    - Feature importance analysis
    - Pattern discovery
    - Exit timing optimization
    - Risk prediction
    """

    def __init__(self):
        self.feature_importance = None
        self.patterns = []
        self.models = {}
        self.insights = {}

    def analyze_feature_importance(self, all_trades: List[Dict]) -> pd.DataFrame:
        """
        Determine which indicators/features drive profitable trades.
        """
        print("\nAnalyzing feature importance...")

        if not all_trades:
            return pd.DataFrame()

        trades_df = pd.DataFrame(all_trades)

        # Create features from trade data
        features = []
        labels = []

        for _, trade in trades_df.iterrows():
            # Extract features (if available in trade data)
            feat = {
                'days_held': trade.get('Days Held', 0),
                'entry_price': trade.get('Entry Price', 0),
                'signal_strength': trade.get('Signal Strength', 0),
            }

            # Label: 1 if profitable, 0 otherwise
            label = 1 if trade.get('PnL', 0) > 0 else 0

            features.append(feat)
            labels.append(label)

        if len(features) < 10:
            print("  Not enough trades for ML analysis")
            return pd.DataFrame()

        X = pd.DataFrame(features)
        y = np.array(labels)

        # Train Random Forest
        rf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
        rf.fit(X, y)

        # Get feature importance
        importance_df = pd.DataFrame({
            'feature': X.columns,
            'importance': rf.feature_importances_
        }).sort_values('importance', ascending=False)

        self.feature_importance = importance_df

        print("  Feature Importance:")
        for _, row in importance_df.iterrows():
            print(f"    {row['feature']}: {row['importance']:.1%}")

        return importance_df

    def discover_patterns(self, all_trades: List[Dict]) -> List[Dict]:
        """
        Discover profitable trading patterns.
        """
        print("\nDiscovering trading patterns...")

        if not all_trades:
            return []

        trades_df = pd.DataFrame(all_trades)
        winning_trades = trades_df[trades_df['PnL'] > 0]
        losing_trades = trades_df[trades_df['PnL'] <= 0]

        patterns = []

        # Pattern 1: Optimal holding period
        if len(winning_trades) > 0:
            avg_hold_win = winning_trades['Days Held'].mean()
            avg_hold_loss = losing_trades['Days Held'].mean() if len(losing_trades) > 0 else 0

            patterns.append({
                'type': 'Holding Period',
                'pattern': f"Winners held avg {avg_hold_win:.1f} days, losers {avg_hold_loss:.1f} days",
                'recommendation': f"Target holding period: {avg_hold_win:.0f} days",
                'win_rate_impact': self._calculate_win_rate_by_holding(trades_df, avg_hold_win)
            })

        # Pattern 2: Signal strength correlation
        if 'Signal Strength' in trades_df.columns:
            high_signal = trades_df[trades_df['Signal Strength'] > trades_df['Signal Strength'].median()]
            low_signal = trades_df[trades_df['Signal Strength'] <= trades_df['Signal Strength'].median()]

            high_wr = (high_signal['PnL'] > 0).sum() / len(high_signal) * 100 if len(high_signal) > 0 else 0
            low_wr = (low_signal['PnL'] > 0).sum() / len(low_signal) * 100 if len(low_signal) > 0 else 0

            patterns.append({
                'type': 'Signal Strength',
                'pattern': f"High signal win rate: {high_wr:.1f}%, Low signal: {low_wr:.1f}%",
                'recommendation': f"Only trade when signal strength > {trades_df['Signal Strength'].median():.2f}",
                'win_rate_impact': high_wr - low_wr
            })

        # Pattern 3: Exit reason analysis
        if 'Exit Reason' in trades_df.columns:
            exit_stats = trades_df.groupby('Exit Reason').agg({
                'PnL': ['mean', 'count']
            })

            best_exit = exit_stats[('PnL', 'mean')].idxmax()
            worst_exit = exit_stats[('PnL', 'mean')].idxmin()

            patterns.append({
                'type': 'Exit Timing',
                'pattern': f"Best exit: {best_exit}, Worst: {worst_exit}",
                'recommendation': f"Optimize for {best_exit} exits",
                'win_rate_impact': 0
            })

        self.patterns = patterns

        print(f"  Discovered {len(patterns)} patterns:")
        for p in patterns:
            print(f"    - {p['type']}: {p['pattern']}")

        return patterns

    def _calculate_win_rate_by_holding(self, trades_df: pd.DataFrame, target_days: float) -> float:
        """Calculate win rate for trades held near target days."""
        tolerance = 5  # days
        near_target = trades_df[
            (trades_df['Days Held'] >= target_days - tolerance) &
            (trades_df['Days Held'] <= target_days + tolerance)
        ]

        if len(near_target) == 0:
            return 0

        return (near_target['PnL'] > 0).sum() / len(near_target) * 100

    def predict_trade_success(self, trade_features: Dict) -> Tuple[float, str]:
        """
        Predict likelihood of trade success based on features.

        Returns: (probability, recommendation)
        """
        # Placeholder - would use trained model in production
        signal_strength = trade_features.get('signal_strength', 0)

        if signal_strength > 0.5:
            return 0.65, "HIGH - Good entry signal"
        elif signal_strength > 0.2:
            return 0.55, "MEDIUM - Acceptable signal"
        else:
            return 0.45, "LOW - Weak signal, consider passing"

    def analyze_risk_patterns(self, all_trades: List[Dict]) -> Dict[str, Any]:
        """
        Identify patterns that indicate high-risk trades.
        """
        print("\nAnalyzing risk patterns...")

        if not all_trades:
            return {}

        trades_df = pd.DataFrame(all_trades)

        # High-risk indicators
        risk_indicators = {}

        # Large losses pattern
        large_losses = trades_df[trades_df['PnL %'] < -5]
        if len(large_losses) > 0:
            risk_indicators['large_losses'] = {
                'count': len(large_losses),
                'avg_days_held': large_losses['Days Held'].mean(),
                'common_exit': large_losses['Exit Reason'].mode()[0] if 'Exit Reason' in large_losses.columns else 'Unknown'
            }

        # Consecutive losses
        trades_df['is_loss'] = trades_df['PnL'] < 0
        max_consecutive = self._find_max_consecutive_losses(trades_df)
        risk_indicators['max_consecutive_losses'] = max_consecutive

        print(f"  Risk Indicators:")
        print(f"    Large losses (>5%): {risk_indicators.get('large_losses', {}).get('count', 0)}")
        print(f"    Max consecutive losses: {max_consecutive}")

        return risk_indicators

    def _find_max_consecutive_losses(self, trades_df: pd.DataFrame) -> int:
        """Find maximum consecutive losing trades."""
        max_streak = 0
        current_streak = 0

        for is_loss in trades_df['is_loss']:
            if is_loss:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def generate_insights_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive ML insights report.
        """
        report = {
            'feature_importance': self.feature_importance.to_dict('records') if self.feature_importance is not None else [],
            'patterns': self.patterns,
            'insights': self.insights,
            'timestamp': datetime.now().isoformat()
        }

        return report

    def save_results(self, output_dir: str = "result/optimization"):
        """Save ML insights results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report = self.generate_insights_report()

        report_file = f"{output_dir}/ml_insights_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"✓ ML insights saved: {report_file}")

        # Save feature importance separately
        if self.feature_importance is not None:
            feat_file = f"{output_dir}/feature_importance_{timestamp}.csv"
            self.feature_importance.to_csv(feat_file, index=False)
            print(f"✓ Feature importance saved: {feat_file}")

    def analyze_all_trades(self, all_strategy_trades: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Run complete ML analysis on all strategies' trades.
        """
        print("\n" + "="*80)
        print("MACHINE LEARNING INSIGHTS ANALYSIS")
        print("="*80)

        # Combine all trades
        all_trades = []
        for strategy_name, trades in all_strategy_trades.items():
            for trade in trades:
                trade_copy = trade.copy()
                trade_copy['Strategy'] = strategy_name
                all_trades.append(trade_copy)

        print(f"Total trades to analyze: {len(all_trades)}")

        # Run analyses
        feat_importance = self.analyze_feature_importance(all_trades)
        patterns = self.discover_patterns(all_trades)
        risk_patterns = self.analyze_risk_patterns(all_trades)

        # Store insights
        self.insights = {
            'total_trades': len(all_trades),
            'feature_importance': feat_importance.to_dict('records') if not feat_importance.empty else [],
            'patterns': patterns,
            'risk_patterns': risk_patterns
        }

        # Save results
        self.save_results()

        print(f"\n✓ ML Analysis Complete")
        print(f"  - Features analyzed: {len(feat_importance)}")
        print(f"  - Patterns discovered: {len(patterns)}")
        print(f"  - Risk indicators identified: {len(risk_patterns)}")

        return self.insights
