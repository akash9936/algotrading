"""
Stock-Specific Optimizer

Optimizes strategies for individual stocks and groups stocks by characteristics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime
import json
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


class StockOptimizer:
    """
    Optimizes strategies for individual stocks and creates stock clusters.
    """

    def __init__(self):
        self.stock_performance = {}
        self.stock_characteristics = {}
        self.clusters = None
        self.cluster_strategies = {}

    def analyze_stock_characteristics(self, stock_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Calculate characteristics for each stock."""
        print("\nCalculating stock characteristics...")

        characteristics = []

        for symbol, df in stock_data.items():
            if len(df) < 50:
                continue

            # Calculate characteristics
            returns = df['Close'].pct_change()

            char = {
                'symbol': symbol,
                'avg_return': returns.mean() * 252,  # Annualized
                'volatility': returns.std() * np.sqrt(252),
                'sharpe': (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0,
                'max_drawdown': self._calculate_max_dd(df['Close']),
                'avg_volume': df['Volume'].mean() if 'Volume' in df.columns else 0,
                'price_range': (df['High'].max() - df['Low'].min()) / df['Close'].mean(),
                'trend': self._calculate_trend(df['Close']),
                'days': len(df)
            }

            characteristics.append(char)
            self.stock_characteristics[symbol] = char

        df_chars = pd.DataFrame(characteristics)
        print(f"✓ Analyzed {len(df_chars)} stocks")

        return df_chars

    def _calculate_max_dd(self, prices: pd.Series) -> float:
        """Calculate maximum drawdown."""
        cummax = prices.cummax()
        drawdown = (prices - cummax) / cummax * 100
        return drawdown.min()

    def _calculate_trend(self, prices: pd.Series) -> float:
        """Calculate overall trend strength."""
        if len(prices) < 50:
            return 0
        ma50 = prices.rolling(50).mean().iloc[-1]
        current = prices.iloc[-1]
        return (current - ma50) / ma50 if not pd.isna(ma50) else 0

    def optimize_per_stock(self, symbol: str, stock_data: pd.DataFrame,
                          strategies: Dict) -> Dict[str, Any]:
        """Find best strategy for a specific stock."""

        best_strategy = None
        best_sharpe = -999
        best_metrics = None

        for strategy_name, strategy in strategies.items():
            # Reset strategy
            strategy.current_capital = strategy.initial_capital
            strategy.positions = []
            strategy.trades = []
            strategy.daily_portfolio_value = []

            # Backtest on single stock
            metrics = strategy.backtest({symbol: stock_data})

            if metrics['sharpe_ratio'] > best_sharpe:
                best_sharpe = metrics['sharpe_ratio']
                best_strategy = strategy_name
                best_metrics = metrics

        result = {
            'symbol': symbol,
            'best_strategy': best_strategy,
            'sharpe_ratio': best_sharpe,
            'total_return': best_metrics['total_return_pct'] if best_metrics else 0,
            'win_rate': best_metrics['win_rate'] if best_metrics else 0,
            'total_trades': best_metrics['total_trades'] if best_metrics else 0
        }

        self.stock_performance[symbol] = result

        return result

    def cluster_stocks(self, characteristics_df: pd.DataFrame,
                      n_clusters: int = 3) -> pd.DataFrame:
        """Group stocks by characteristics using K-means clustering."""
        print(f"\nClustering stocks into {n_clusters} groups...")

        # Select features for clustering
        features = ['volatility', 'avg_return', 'trend', 'price_range']

        X = characteristics_df[features].fillna(0)

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        characteristics_df['cluster'] = kmeans.fit_predict(X_scaled)

        # Analyze clusters
        for cluster_id in range(n_clusters):
            cluster_stocks = characteristics_df[characteristics_df['cluster'] == cluster_id]

            print(f"\n  Cluster {cluster_id + 1}: {len(cluster_stocks)} stocks")
            print(f"    Avg Volatility: {cluster_stocks['volatility'].mean():.2%}")
            print(f"    Avg Return: {cluster_stocks['avg_return'].mean():.2%}")
            print(f"    Avg Trend: {cluster_stocks['trend'].mean():.2%}")
            print(f"    Stocks: {', '.join(cluster_stocks['symbol'].head(5).tolist())}" +
                  (f" (+{len(cluster_stocks)-5} more)" if len(cluster_stocks) > 5 else ""))

        self.clusters = characteristics_df

        return characteristics_df

    def find_best_strategy_per_cluster(self, all_strategy_results: Dict[str, List[Dict]]) -> Dict:
        """Determine best strategy for each cluster."""
        if self.clusters is None:
            return {}

        print("\nAnalyzing best strategies per cluster...")

        cluster_performance = {}

        for cluster_id in self.clusters['cluster'].unique():
            cluster_stocks = self.clusters[self.clusters['cluster'] == cluster_id]['symbol'].tolist()

            # Analyze each strategy's performance on cluster stocks
            strategy_scores = {}

            for strategy_name, trades in all_strategy_results.items():
                if not trades:
                    continue

                trades_df = pd.DataFrame(trades)
                cluster_trades = trades_df[trades_df['Symbol'].isin(cluster_stocks)]

                if len(cluster_trades) == 0:
                    continue

                winning = cluster_trades[cluster_trades['PnL'] > 0]
                win_rate = len(winning) / len(cluster_trades) * 100
                avg_pnl = cluster_trades['PnL'].mean()

                strategy_scores[strategy_name] = {
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'total_trades': len(cluster_trades),
                    'score': win_rate * 0.6 + (avg_pnl / 100) * 0.4  # Weighted score
                }

            if strategy_scores:
                best_strategy = max(strategy_scores.items(), key=lambda x: x[1]['score'])

                cluster_performance[f'cluster_{cluster_id}'] = {
                    'stocks': cluster_stocks,
                    'count': len(cluster_stocks),
                    'best_strategy': best_strategy[0],
                    'win_rate': best_strategy[1]['win_rate'],
                    'avg_pnl': best_strategy[1]['avg_pnl'],
                    'total_trades': best_strategy[1]['total_trades']
                }

                print(f"  Cluster {cluster_id + 1}: Best = {best_strategy[0]} "
                      f"(Win Rate: {best_strategy[1]['win_rate']:.1f}%)")

        self.cluster_strategies = cluster_performance

        return cluster_performance

    def generate_stock_recommendations(self) -> pd.DataFrame:
        """Generate trading recommendations for each stock."""

        recommendations = []

        for symbol, perf in self.stock_performance.items():
            char = self.stock_characteristics.get(symbol, {})

            rec = {
                'Symbol': symbol,
                'Best Strategy': perf['best_strategy'],
                'Win Rate %': perf['win_rate'],
                'Total Return %': perf['total_return'],
                'Sharpe Ratio': perf['sharpe_ratio'],
                'Volatility': char.get('volatility', 0),
                'Recommendation': self._generate_rec_text(perf, char)
            }

            recommendations.append(rec)

        df = pd.DataFrame(recommendations)
        df = df.sort_values('Sharpe Ratio', ascending=False)

        return df

    def _generate_rec_text(self, perf: Dict, char: Dict) -> str:
        """Generate recommendation text."""
        if perf['win_rate'] > 60 and perf['sharpe_ratio'] > 1.0:
            return "STRONG BUY - Use recommended strategy"
        elif perf['win_rate'] > 55 and perf['sharpe_ratio'] > 0.5:
            return "BUY - Good opportunity"
        elif perf['win_rate'] > 50:
            return "HOLD - Moderate potential"
        else:
            return "AVOID - Low win rate"

    def save_results(self, output_dir: str = "result/optimization"):
        """Save stock-specific optimization results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save stock characteristics
        if self.stock_characteristics:
            char_df = pd.DataFrame(list(self.stock_characteristics.values()))
            char_file = f"{output_dir}/stock_characteristics_{timestamp}.csv"
            char_df.to_csv(char_file, index=False)
            print(f"✓ Characteristics saved: {char_file}")

        # Save clusters
        if self.clusters is not None:
            cluster_file = f"{output_dir}/stock_clusters_{timestamp}.csv"
            self.clusters.to_csv(cluster_file, index=False)
            print(f"✓ Clusters saved: {cluster_file}")

        # Save cluster strategies
        if self.cluster_strategies:
            strat_file = f"{output_dir}/cluster_strategies_{timestamp}.json"
            with open(strat_file, 'w') as f:
                json.dump(self.cluster_strategies, f, indent=2, default=str)
            print(f"✓ Cluster strategies saved: {strat_file}")

        # Save stock performance
        if self.stock_performance:
            perf_file = f"{output_dir}/stock_performance_{timestamp}.json"
            with open(perf_file, 'w') as f:
                json.dump(self.stock_performance, f, indent=2)
            print(f"✓ Stock performance saved: {perf_file}")
