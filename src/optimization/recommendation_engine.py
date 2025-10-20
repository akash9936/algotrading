"""
Recommendation Engine - Actionable Trading Rules Generator

This module generates human-readable trading rules and recommendations
based on optimization results.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
import json
from datetime import datetime


def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj


class RecommendationEngine:
    """
    Generates actionable trading recommendations.

    Features:
    - Strategy ranking
    - Trading rule generation
    - Configuration file creation
    - Report generation
    """

    def __init__(self):
        self.recommendations = {}
        self.trading_rules = {}
        self.best_strategy = None

    def analyze_all_results(self,
                           strategy_comparison: pd.DataFrame = None,
                           regime_analysis: pd.DataFrame = None,
                           stock_recommendations: pd.DataFrame = None,
                           ml_insights: Dict = None,
                           monte_carlo_results: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Analyze all optimization results and generate recommendations.
        """
        print("\n" + "="*80)
        print("GENERATING FINAL RECOMMENDATIONS")
        print("="*80)

        recommendations = {}

        # 1. Best Overall Strategy
        if strategy_comparison is not None and not strategy_comparison.empty:
            best_strategy = self._find_best_strategy(strategy_comparison)
            recommendations['best_overall_strategy'] = best_strategy
            self.best_strategy = best_strategy

        # 2. Regime-Specific Recommendations
        if regime_analysis is not None and not regime_analysis.empty:
            regime_recs = self._generate_regime_recommendations(regime_analysis)
            recommendations['regime_recommendations'] = regime_recs

        # 3. Stock-Specific Recommendations
        if stock_recommendations is not None and not stock_recommendations.empty:
            stock_recs = self._generate_stock_recommendations(stock_recommendations)
            recommendations['stock_recommendations'] = stock_recs

        # 4. ML Insights Summary
        if ml_insights:
            ml_summary = self._summarize_ml_insights(ml_insights)
            recommendations['ml_insights'] = ml_summary

        # 5. Risk Assessment
        if monte_carlo_results is not None and not monte_carlo_results.empty:
            risk_assessment = self._assess_risk(monte_carlo_results)
            recommendations['risk_assessment'] = risk_assessment

        self.recommendations = recommendations

        return recommendations

    def _find_best_strategy(self, strategy_df: pd.DataFrame) -> Dict[str, Any]:
        """Find the best performing strategy."""
        # Sort by Sharpe ratio
        best = strategy_df.sort_values('sharpe_ratio', ascending=False).iloc[0]

        return {
            'name': best['Strategy Name'],
            'sharpe_ratio': best['sharpe_ratio'],
            'total_return_pct': best['total_return_pct'],
            'win_rate': best['win_rate'],
            'max_drawdown': best['max_drawdown'],
            'total_trades': best['total_trades'],
            'profit_factor': best['profit_factor']
        }

    def _generate_regime_recommendations(self, regime_df: pd.DataFrame) -> List[Dict]:
        """Generate regime-specific trading recommendations."""
        recs = []

        for regime in regime_df['Regime'].unique():
            regime_data = regime_df[regime_df['Regime'] == regime]
            best = regime_data.sort_values('Win Rate %', ascending=False).iloc[0]

            recs.append({
                'regime': regime,
                'best_strategy': best['Strategy'],
                'win_rate': best['Win Rate %'],
                'recommendation': f"Use {best['Strategy']} in {regime.replace('_', ' ')} markets"
            })

        return recs

    def _generate_stock_recommendations(self, stock_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate stock-specific recommendations."""
        # Top performers
        top_stocks = stock_df.head(10)[['Symbol', 'Best Strategy', 'Win Rate %', 'Recommendation']].to_dict('records')

        # Stocks to avoid
        avoid_stocks = stock_df[stock_df['Recommendation'].str.contains('AVOID', na=False)][['Symbol', 'Win Rate %']].to_dict('records')

        return {
            'top_10_stocks': top_stocks,
            'stocks_to_avoid': avoid_stocks
        }

    def _summarize_ml_insights(self, ml_insights: Dict) -> Dict[str, Any]:
        """Summarize ML insights."""
        summary = {
            'total_trades_analyzed': ml_insights.get('total_trades', 0),
            'key_patterns': [],
            'feature_importance': []
        }

        # Extract patterns
        if 'patterns' in ml_insights:
            for pattern in ml_insights['patterns']:
                summary['key_patterns'].append({
                    'type': pattern.get('type'),
                    'recommendation': pattern.get('recommendation')
                })

        # Extract feature importance
        if 'feature_importance' in ml_insights and ml_insights['feature_importance']:
            for feat in ml_insights['feature_importance']:
                summary['feature_importance'].append({
                    'feature': feat.get('feature'),
                    'importance': feat.get('importance')
                })

        return summary

    def _assess_risk(self, mc_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate risk assessment from Monte Carlo results."""
        if mc_df.empty:
            return {}

        best_risk = mc_df.sort_values('Risk/Reward', ascending=False).iloc[0]

        return {
            'best_risk_adjusted_strategy': best_risk['Strategy'],
            'expected_return': best_risk['Expected Return %'],
            'worst_case_5th': best_risk['Worst Case (5%) %'],
            'best_case_95th': best_risk['Best Case (95%) %'],
            'var_95': best_risk['VaR (95%) %'],
            'max_drawdown': best_risk['Max Drawdown %'],
            'prob_profit': best_risk['Prob Profit %']
        }

    def generate_trading_rules(self) -> str:
        """Generate human-readable trading rules."""
        if not self.recommendations or not self.best_strategy:
            return "No recommendations available"

        rules = []
        rules.append("="*80)
        rules.append("OPTIMAL TRADING STRATEGY RECOMMENDATIONS")
        rules.append("="*80)
        rules.append("")

        # Best Strategy
        best = self.best_strategy
        rules.append(f"📊 BEST OVERALL STRATEGY: {best['name']}")
        rules.append(f"   Expected Annual Return: {best['total_return_pct']:.2f}%")
        rules.append(f"   Win Rate: {best['win_rate']:.1f}%")
        rules.append(f"   Sharpe Ratio: {best['sharpe_ratio']:.2f}")
        rules.append(f"   Max Drawdown: {best['max_drawdown']:.2f}%")
        rules.append(f"   Total Trades: {best['total_trades']}")
        rules.append("")

        # Regime Recommendations
        if 'regime_recommendations' in self.recommendations:
            rules.append("⏰ MARKET REGIME RULES:")
            for rec in self.recommendations['regime_recommendations']:
                rules.append(f"   {rec['regime'].replace('_', ' ').title()}: {rec['best_strategy']} ({rec['win_rate']:.1f}% win rate)")
            rules.append("")

        # Stock Recommendations
        if 'stock_recommendations' in self.recommendations:
            stock_recs = self.recommendations['stock_recommendations']
            if stock_recs.get('top_10_stocks'):
                rules.append("🏢 TOP 10 STOCKS TO TRADE:")
                for stock in stock_recs['top_10_stocks'][:5]:
                    rules.append(f"   {stock['Symbol']}: {stock['Best Strategy']} ({stock['Win Rate %']:.1f}% win rate)")
                rules.append("")

        # ML Insights
        if 'ml_insights' in self.recommendations:
            ml = self.recommendations['ml_insights']
            if ml.get('key_patterns'):
                rules.append("🤖 ML INSIGHTS:")
                for pattern in ml['key_patterns']:
                    rules.append(f"   • {pattern['recommendation']}")
                rules.append("")

        # Risk Assessment
        if 'risk_assessment' in self.recommendations:
            risk = self.recommendations['risk_assessment']
            rules.append("⚠️  RISK ASSESSMENT:")
            rules.append(f"   Expected Return: {risk.get('expected_return', 0):.2f}%")
            rules.append(f"   Best Case (95th percentile): +{risk.get('best_case_95th', 0):.2f}%")
            rules.append(f"   Worst Case (5th percentile): {risk.get('worst_case_5th', 0):.2f}%")
            rules.append(f"   Maximum Drawdown Risk: {risk.get('max_drawdown', 0):.2f}%")
            rules.append(f"   Probability of Profit: {risk.get('prob_profit', 0):.1f}%")
            rules.append("")

        rules.append("="*80)

        trading_rules_text = "\n".join(rules)
        self.trading_rules = trading_rules_text

        return trading_rules_text

    def save_recommendations(self, output_dir: str = "result/optimization"):
        """Save all recommendations to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON recommendations
        json_file = f"{output_dir}/final_recommendations_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(convert_numpy_types(self.recommendations), f, indent=2, default=str)
        print(f"✓ Recommendations saved: {json_file}")

        # Save trading rules
        if self.trading_rules:
            rules_file = f"{output_dir}/TRADING_RULES_{timestamp}.txt"
            with open(rules_file, 'w') as f:
                f.write(self.trading_rules)
            print(f"✓ Trading rules saved: {rules_file}")

        # Save best strategy config
        if self.best_strategy:
            config_file = f"{output_dir}/optimal_strategy_config_{timestamp}.json"
            with open(config_file, 'w') as f:
                json.dump(convert_numpy_types(self.best_strategy), f, indent=2)
            print(f"✓ Strategy config saved: {config_file}")

    def print_recommendations(self):
        """Print recommendations to console."""
        if self.trading_rules:
            print("\n" + self.trading_rules)
        else:
            print("\nNo recommendations generated yet")
