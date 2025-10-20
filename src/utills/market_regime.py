"""
Market Regime Detection Utility
=================================
Detects market conditions to help strategies adapt to different environments.

Market Regimes:
1. BULL MARKET (Trending Up): Trade momentum strategies
2. BEAR MARKET (Trending Down): Avoid or use defensive strategies
3. SIDEWAYS (Range-bound): Use mean-reversion strategies
4. HIGH VOLATILITY: Reduce position sizes, widen stops
5. LOW VOLATILITY: Increase position sizes, tighten stops

Usage:
------
from utills.market_regime import MarketRegimeDetector

detector = MarketRegimeDetector()
regime = detector.detect_regime(nifty_data)
print(f"Current Regime: {regime['regime']}")
print(f"Trend Strength: {regime['trend_strength']}")
"""

import pandas as pd
import numpy as np

class MarketRegimeDetector:
    """Detect market regime using multiple indicators"""

    def __init__(self):
        self.sma_50 = 50
        self.sma_200 = 200
        self.adx_period = 14
        self.atr_period = 14

    def calculate_sma(self, data, period):
        """Calculate Simple Moving Average"""
        return data['Close'].rolling(window=period).mean()

    def calculate_adx(self, data, period=14):
        """
        Calculate Average Directional Index (ADX)
        Measures trend strength (0-100)

        ADX < 25: Weak or no trend (sideways)
        ADX 25-50: Strong trend
        ADX > 50: Very strong trend
        """
        high = data['High']
        low = data['Low']
        close = data['Close']

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # Smoothed indicators
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / atr

        # ADX calculation
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx, plus_di, minus_di

    def calculate_atr(self, data, period=14):
        """
        Calculate Average True Range (ATR)
        Measures volatility
        """
        high = data['High']
        low = data['Low']
        close = data['Close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=period).mean()
        return atr

    def calculate_volatility(self, data, period=20):
        """Calculate historical volatility (standard deviation of returns)"""
        returns = data['Close'].pct_change()
        volatility = returns.rolling(window=period).std() * np.sqrt(252) * 100  # Annualized
        return volatility

    def detect_regime(self, data):
        """
        Detect current market regime

        Returns:
        --------
        dict with:
        - regime: 'BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE'
        - trend_strength: 0-100
        - volatility_state: 'HIGH', 'NORMAL', 'LOW'
        - is_tradeable: bool (whether conditions are good for trading)
        - confidence: 0-100 (confidence in regime detection)
        """
        if data.empty or len(data) < self.sma_200:
            return {
                'regime': 'UNKNOWN',
                'trend_strength': 0,
                'volatility_state': 'UNKNOWN',
                'is_tradeable': False,
                'confidence': 0,
                'details': 'Insufficient data'
            }

        # Calculate indicators
        sma_50 = self.calculate_sma(data, self.sma_50)
        sma_200 = self.calculate_sma(data, self.sma_200)
        adx, plus_di, minus_di = self.calculate_adx(data, self.adx_period)
        atr = self.calculate_atr(data, self.atr_period)
        volatility = self.calculate_volatility(data, period=20)

        # Get latest values
        current_price = data['Close'].iloc[-1]
        current_sma_50 = sma_50.iloc[-1]
        current_sma_200 = sma_200.iloc[-1]
        current_adx = adx.iloc[-1]
        current_plus_di = plus_di.iloc[-1]
        current_minus_di = minus_di.iloc[-1]
        current_volatility = volatility.iloc[-1]

        # Skip if any indicator is NaN
        if pd.isna(current_adx) or pd.isna(current_sma_50) or pd.isna(current_sma_200):
            return {
                'regime': 'UNKNOWN',
                'trend_strength': 0,
                'volatility_state': 'UNKNOWN',
                'is_tradeable': False,
                'confidence': 0,
                'details': 'Indicators not ready'
            }

        ###################################################################
        # TREND DETECTION
        ###################################################################
        trend_direction = None
        trend_strength = current_adx

        # Price vs Moving Averages
        price_above_50 = current_price > current_sma_50
        price_above_200 = current_price > current_sma_200
        sma_50_above_200 = current_sma_50 > current_sma_200

        # Directional Indicators
        bullish_di = current_plus_di > current_minus_di
        bearish_di = current_minus_di > current_plus_di

        # Determine trend
        if price_above_50 and price_above_200 and sma_50_above_200:
            if bullish_di:
                trend_direction = 'BULL'
            else:
                trend_direction = 'BULL_WEAK'
        elif not price_above_50 and not price_above_200 and not sma_50_above_200:
            if bearish_di:
                trend_direction = 'BEAR'
            else:
                trend_direction = 'BEAR_WEAK'
        else:
            trend_direction = 'SIDEWAYS'

        ###################################################################
        # VOLATILITY STATE
        ###################################################################
        # Calculate percentile of current volatility
        vol_percentile = (volatility.rank(pct=True).iloc[-1]) * 100

        if vol_percentile > 75:
            volatility_state = 'HIGH'
        elif vol_percentile < 25:
            volatility_state = 'LOW'
        else:
            volatility_state = 'NORMAL'

        ###################################################################
        # REGIME CLASSIFICATION
        ###################################################################
        regime = 'UNKNOWN'
        confidence = 50

        # Strong Bull Market
        if trend_direction == 'BULL' and current_adx > 25:
            regime = 'BULL_TRENDING'
            confidence = min(100, 60 + current_adx / 2)

        # Weak Bull Market
        elif trend_direction == 'BULL_WEAK':
            regime = 'BULL_WEAK'
            confidence = 55

        # Strong Bear Market
        elif trend_direction == 'BEAR' and current_adx > 25:
            regime = 'BEAR_TRENDING'
            confidence = min(100, 60 + current_adx / 2)

        # Weak Bear Market
        elif trend_direction == 'BEAR_WEAK':
            regime = 'BEAR_WEAK'
            confidence = 55

        # Sideways / Range-bound
        elif current_adx < 25:
            regime = 'SIDEWAYS'
            confidence = 60 + (25 - current_adx)  # Higher confidence for lower ADX

        # High Volatility Override
        if volatility_state == 'HIGH':
            regime = regime + '_VOLATILE'

        ###################################################################
        # TRADING RECOMMENDATIONS
        ###################################################################
        is_tradeable = True
        recommendations = []

        # Bull market: Favor momentum strategies
        if regime in ['BULL_TRENDING', 'BULL_WEAK']:
            recommendations.append("✓ Use momentum strategies (MACD, ROC)")
            recommendations.append("✓ Long-only positions")
            recommendations.append("✓ Wider stop-losses")

        # Bear market: Defensive or avoid
        elif regime in ['BEAR_TRENDING', 'BEAR_WEAK']:
            is_tradeable = False
            recommendations.append("⚠ Avoid long positions")
            recommendations.append("⚠ Use tight stop-losses if trading")
            recommendations.append("⚠ Consider defensive stocks only")

        # Sideways: Mean-reversion strategies
        elif regime == 'SIDEWAYS':
            recommendations.append("✓ Use mean-reversion strategies (RSI)")
            recommendations.append("✓ Tighter profit targets")
            recommendations.append("✓ Quick in-and-out trades")

        # High volatility: Adjust risk
        if volatility_state == 'HIGH':
            recommendations.append("⚠ Reduce position sizes")
            recommendations.append("⚠ Widen stop-losses")
            recommendations.append("⚠ Avoid tight trading ranges")
        elif volatility_state == 'LOW':
            recommendations.append("✓ Can increase position sizes")
            recommendations.append("✓ Tighter stop-losses acceptable")

        return {
            'regime': regime,
            'trend_direction': trend_direction,
            'trend_strength': round(trend_strength, 2),
            'adx': round(current_adx, 2),
            'plus_di': round(current_plus_di, 2),
            'minus_di': round(current_minus_di, 2),
            'volatility_state': volatility_state,
            'volatility_annual': round(current_volatility, 2),
            'price': round(current_price, 2),
            'sma_50': round(current_sma_50, 2),
            'sma_200': round(current_sma_200, 2),
            'is_tradeable': is_tradeable,
            'confidence': round(confidence, 2),
            'recommendations': recommendations
        }

    def get_position_size_multiplier(self, regime_info):
        """
        Get position size multiplier based on market regime

        Returns: float (0.5 to 1.5)
        """
        multiplier = 1.0

        # Reduce in bear markets
        if 'BEAR' in regime_info['regime']:
            multiplier *= 0.5

        # Reduce in high volatility
        if regime_info['volatility_state'] == 'HIGH':
            multiplier *= 0.7

        # Increase in strong bull with low volatility
        if regime_info['regime'] == 'BULL_TRENDING' and regime_info['volatility_state'] == 'LOW':
            multiplier *= 1.3

        return round(multiplier, 2)

    def should_trade(self, regime_info, strategy_type='momentum'):
        """
        Determine if should trade based on regime and strategy type

        Parameters:
        -----------
        regime_info: dict (output from detect_regime)
        strategy_type: 'momentum', 'mean_reversion', or 'combined'

        Returns:
        --------
        bool, str (should_trade, reason)
        """
        regime = regime_info['regime']

        # Never trade in bear markets with momentum
        if 'BEAR' in regime and strategy_type == 'momentum':
            return False, "Bear market - avoid momentum strategies"

        # Don't trade sideways markets with momentum
        if regime == 'SIDEWAYS' and strategy_type == 'momentum':
            return False, "Sideways market - momentum not effective"

        # Don't trade trending markets with mean-reversion
        if 'TRENDING' in regime and strategy_type == 'mean_reversion':
            return False, "Strong trend - mean-reversion risky"

        # Reduce trading in high volatility
        if regime_info['volatility_state'] == 'HIGH':
            return False, "High volatility - wait for stability"

        # Low confidence
        if regime_info['confidence'] < 50:
            return False, "Low confidence in regime detection"

        return True, "Market conditions favorable"


###############################################################################
# EXAMPLE USAGE
###############################################################################

if __name__ == "__main__":
    from load_data import DataLoader

    print("=" * 80)
    print("MARKET REGIME DETECTOR - EXAMPLE")
    print("=" * 80)

    # Load Nifty 50 index data
    loader = DataLoader()

    # Try to load Nifty 50 index first
    nifty_data = loader.load_stock("^NSEI", category="indices")

    # If no index data, use a representative Nifty 50 stock as proxy
    if nifty_data.empty:
        print("\n⚠️  No Nifty 50 index data found. Trying to use a stock as market proxy...")
        nifty_data = loader.load_stock("RELIANCE.NS", category="nifty50")
        ticker_name = "RELIANCE.NS (Market Proxy)"
    else:
        ticker_name = "Nifty 50 Index"

    if nifty_data.empty:
        print("\n❌ No data found!")
        print("\n📥 Please download data first:")
        print("   1. Go to project root: cd ../..")
        print("   2. Run: python3 src/download_data.py")
        print("\n   This will download:")
        print("   - Nifty 50 index data")
        print("   - All Nifty 50 stocks")
        print("\n   Then try again: python3 src/utills/market_regime.py")
    else:
        # Detect current regime
        detector = MarketRegimeDetector()
        regime_info = detector.detect_regime(nifty_data)

        print(f"\n📊 MARKET REGIME ANALYSIS ({ticker_name})")
        print("=" * 80)
        print(f"Regime: {regime_info['regime']}")
        print(f"Trend Direction: {regime_info['trend_direction']}")
        print(f"Trend Strength (ADX): {regime_info['adx']} / 100")
        print(f"Volatility State: {regime_info['volatility_state']} ({regime_info['volatility_annual']}% annual)")
        print(f"Tradeable: {'YES' if regime_info['is_tradeable'] else 'NO'}")
        print(f"Confidence: {regime_info['confidence']}%")

        print(f"\n📈 TECHNICAL LEVELS")
        print("=" * 80)
        print(f"Current Price: ₹{regime_info['price']:,.2f}")
        print(f"50-day SMA: ₹{regime_info['sma_50']:,.2f}")
        print(f"200-day SMA: ₹{regime_info['sma_200']:,.2f}")
        print(f"+DI: {regime_info['plus_di']:.2f}")
        print(f"-DI: {regime_info['minus_di']:.2f}")

        print(f"\n💡 RECOMMENDATIONS")
        print("=" * 80)
        for rec in regime_info['recommendations']:
            print(f"  {rec}")

        print(f"\n🎯 STRATEGY SUGGESTIONS")
        print("=" * 80)

        # Test different strategy types
        strategies = ['momentum', 'mean_reversion', 'combined']
        for strategy in strategies:
            should_trade, reason = detector.should_trade(regime_info, strategy)
            status = "✓" if should_trade else "✗"
            print(f"{status} {strategy.upper()}: {reason}")

        # Position sizing
        multiplier = detector.get_position_size_multiplier(regime_info)
        print(f"\n📊 Position Size Multiplier: {multiplier}x")
        if multiplier < 1.0:
            print(f"   → Reduce position sizes to {int(multiplier * 100)}% of normal")
        elif multiplier > 1.0:
            print(f"   → Can increase position sizes to {int(multiplier * 100)}% of normal")

        print("\n" + "=" * 80)
