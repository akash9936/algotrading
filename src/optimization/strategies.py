"""
Trading Strategy Implementations

This module contains implementations of various trading strategies:
- Mean Reversion (RSI, Bollinger Bands)
- Momentum (MACD, MA Crossover, ROC)
- Volatility Breakout (ATR, Donchian)
- Multi-Signal Confluence
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Any
from .base_strategy import (
    BaseStrategy,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_sma,
    calculate_ema
)


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy

    Entry: RSI < oversold_threshold
    Exit: RSI > overbought_threshold, stop loss, or take profit
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'rsi_period': 14,
            'oversold': 30,
            'overbought': 70,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0,
            'trailing_stop_pct': 3.0,
            'max_hold_days': 30
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add RSI indicator."""
        df['RSI'] = calculate_rsi(df['Close'], self.params['rsi_period'])
        return df

    def generate_signals(self, df: pd.DataFrame, date: pd.Timestamp) -> Tuple[bool, float]:
        """Generate entry signal when RSI is oversold."""
        if date not in df.index:
            return False, 0.0

        idx = df.index.get_loc(date)
        if idx < 1:
            return False, 0.0

        current_rsi = df['RSI'].iloc[idx]

        if pd.isna(current_rsi):
            return False, 0.0

        # Entry condition: RSI oversold
        if current_rsi < self.params['oversold']:
            # Signal strength: how oversold it is
            signal_strength = (self.params['oversold'] - current_rsi) / self.params['oversold']
            return True, signal_strength

        return False, 0.0

    def check_exit(self, df: pd.DataFrame, position: Dict,
                   date: pd.Timestamp) -> Tuple[bool, str]:
        """Check exit conditions."""
        if date not in df.index:
            return False, ""

        idx = df.index.get_loc(date)
        current_price = df['Close'].iloc[idx]
        current_rsi = df['RSI'].iloc[idx]

        # Stop loss
        stop_loss_price = position['entry_price'] * (1 - self.params['stop_loss_pct'] / 100)
        if current_price <= stop_loss_price:
            return True, "Stop Loss"

        # Take profit
        take_profit_price = position['entry_price'] * (1 + self.params['take_profit_pct'] / 100)
        if current_price >= take_profit_price:
            return True, "Take Profit"

        # Trailing stop
        trailing_stop_price = position['highest_price'] * (1 - self.params['trailing_stop_pct'] / 100)
        if current_price <= trailing_stop_price:
            return True, "Trailing Stop"

        # RSI overbought
        if not pd.isna(current_rsi) and current_rsi > self.params['overbought']:
            return True, "RSI Overbought"

        # Max hold period
        days_held = (date - position['entry_date']).days
        if days_held >= self.params['max_hold_days']:
            return True, "Max Hold Period"

        return False, ""


class MACDCrossoverStrategy(BaseStrategy):
    """
    MACD Crossover Strategy

    Entry: MACD crosses above signal line
    Exit: MACD crosses below signal line, stop loss, or take profit
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0,
            'trailing_stop_pct': 3.0,
            'max_hold_days': 30
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add MACD indicators."""
        macd, signal, hist = calculate_macd(
            df['Close'],
            self.params['macd_fast'],
            self.params['macd_slow'],
            self.params['macd_signal']
        )
        df['MACD'] = macd
        df['MACD_Signal'] = signal
        df['MACD_Hist'] = hist
        return df

    def generate_signals(self, df: pd.DataFrame, date: pd.Timestamp) -> Tuple[bool, float]:
        """Generate entry signal on bullish MACD crossover."""
        if date not in df.index:
            return False, 0.0

        idx = df.index.get_loc(date)
        if idx < 1:
            return False, 0.0

        current_hist = df['MACD_Hist'].iloc[idx]
        prev_hist = df['MACD_Hist'].iloc[idx - 1]

        if pd.isna(current_hist) or pd.isna(prev_hist):
            return False, 0.0

        # Bullish crossover: histogram crosses from negative to positive
        if prev_hist < 0 and current_hist > 0:
            signal_strength = abs(current_hist - prev_hist)
            return True, min(signal_strength * 10, 1.0)  # Scale and cap at 1.0

        return False, 0.0

    def check_exit(self, df: pd.DataFrame, position: Dict,
                   date: pd.Timestamp) -> Tuple[bool, str]:
        """Check exit conditions."""
        if date not in df.index:
            return False, ""

        idx = df.index.get_loc(date)
        current_price = df['Close'].iloc[idx]

        # Stop loss
        stop_loss_price = position['entry_price'] * (1 - self.params['stop_loss_pct'] / 100)
        if current_price <= stop_loss_price:
            return True, "Stop Loss"

        # Take profit
        take_profit_price = position['entry_price'] * (1 + self.params['take_profit_pct'] / 100)
        if current_price >= take_profit_price:
            return True, "Take Profit"

        # Trailing stop
        trailing_stop_price = position['highest_price'] * (1 - self.params['trailing_stop_pct'] / 100)
        if current_price <= trailing_stop_price:
            return True, "Trailing Stop"

        # MACD bearish crossover
        if idx >= 1:
            current_hist = df['MACD_Hist'].iloc[idx]
            prev_hist = df['MACD_Hist'].iloc[idx - 1]

            if not pd.isna(current_hist) and not pd.isna(prev_hist):
                if prev_hist > 0 and current_hist < 0:
                    return True, "MACD Bearish Crossover"

        # Max hold period
        days_held = (date - position['entry_date']).days
        if days_held >= self.params['max_hold_days']:
            return True, "Max Hold Period"

        return False, ""


class BollingerBandStrategy(BaseStrategy):
    """
    Bollinger Band Mean Reversion Strategy

    Entry: Price touches or goes below lower band
    Exit: Price touches or goes above upper band, or standard exits
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'bb_period': 20,
            'bb_std_dev': 2.0,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0,
            'max_hold_days': 30
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Bollinger Bands."""
        upper, middle, lower = calculate_bollinger_bands(
            df['Close'],
            self.params['bb_period'],
            self.params['bb_std_dev']
        )
        df['BB_Upper'] = upper
        df['BB_Middle'] = middle
        df['BB_Lower'] = lower
        return df

    def generate_signals(self, df: pd.DataFrame, date: pd.Timestamp) -> Tuple[bool, float]:
        """Generate entry signal when price touches lower band."""
        if date not in df.index:
            return False, 0.0

        idx = df.index.get_loc(date)
        current_price = df['Close'].iloc[idx]
        lower_band = df['BB_Lower'].iloc[idx]
        middle_band = df['BB_Middle'].iloc[idx]

        if pd.isna(lower_band) or pd.isna(middle_band):
            return False, 0.0

        # Entry: price at or below lower band
        if current_price <= lower_band:
            # Signal strength: how far below lower band
            distance = (lower_band - current_price) / middle_band
            signal_strength = min(distance * 10, 1.0)
            return True, signal_strength

        return False, 0.0

    def check_exit(self, df: pd.DataFrame, position: Dict,
                   date: pd.Timestamp) -> Tuple[bool, str]:
        """Check exit conditions."""
        if date not in df.index:
            return False, ""

        idx = df.index.get_loc(date)
        current_price = df['Close'].iloc[idx]
        upper_band = df['BB_Upper'].iloc[idx]

        # Price reaches upper band
        if not pd.isna(upper_band) and current_price >= upper_band:
            return True, "BB Upper Band"

        # Stop loss
        stop_loss_price = position['entry_price'] * (1 - self.params['stop_loss_pct'] / 100)
        if current_price <= stop_loss_price:
            return True, "Stop Loss"

        # Take profit
        take_profit_price = position['entry_price'] * (1 + self.params['take_profit_pct'] / 100)
        if current_price >= take_profit_price:
            return True, "Take Profit"

        # Max hold period
        days_held = (date - position['entry_date']).days
        if days_held >= self.params['max_hold_days']:
            return True, "Max Hold Period"

        return False, ""


class MovingAverageCrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy

    Entry: Fast MA crosses above slow MA
    Exit: Fast MA crosses below slow MA, or standard exits
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'fast_period': 10,
            'slow_period': 30,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0,
            'trailing_stop_pct': 3.0,
            'max_hold_days': 45
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add moving averages."""
        df['MA_Fast'] = calculate_sma(df['Close'], self.params['fast_period'])
        df['MA_Slow'] = calculate_sma(df['Close'], self.params['slow_period'])
        return df

    def generate_signals(self, df: pd.DataFrame, date: pd.Timestamp) -> Tuple[bool, float]:
        """Generate entry signal on golden cross."""
        if date not in df.index:
            return False, 0.0

        idx = df.index.get_loc(date)
        if idx < 1:
            return False, 0.0

        current_fast = df['MA_Fast'].iloc[idx]
        current_slow = df['MA_Slow'].iloc[idx]
        prev_fast = df['MA_Fast'].iloc[idx - 1]
        prev_slow = df['MA_Slow'].iloc[idx - 1]

        if pd.isna(current_fast) or pd.isna(current_slow):
            return False, 0.0

        # Golden cross: fast MA crosses above slow MA
        if prev_fast <= prev_slow and current_fast > current_slow:
            # Signal strength based on separation
            separation = (current_fast - current_slow) / current_slow
            signal_strength = min(separation * 100, 1.0)
            return True, signal_strength

        return False, 0.0

    def check_exit(self, df: pd.DataFrame, position: Dict,
                   date: pd.Timestamp) -> Tuple[bool, str]:
        """Check exit conditions."""
        if date not in df.index:
            return False, ""

        idx = df.index.get_loc(date)
        current_price = df['Close'].iloc[idx]

        # Death cross: fast MA crosses below slow MA
        if idx >= 1:
            current_fast = df['MA_Fast'].iloc[idx]
            current_slow = df['MA_Slow'].iloc[idx]
            prev_fast = df['MA_Fast'].iloc[idx - 1]
            prev_slow = df['MA_Slow'].iloc[idx - 1]

            if not pd.isna(current_fast) and not pd.isna(current_slow):
                if prev_fast >= prev_slow and current_fast < current_slow:
                    return True, "Death Cross"

        # Stop loss
        stop_loss_price = position['entry_price'] * (1 - self.params['stop_loss_pct'] / 100)
        if current_price <= stop_loss_price:
            return True, "Stop Loss"

        # Take profit
        take_profit_price = position['entry_price'] * (1 + self.params['take_profit_pct'] / 100)
        if current_price >= take_profit_price:
            return True, "Take Profit"

        # Trailing stop
        trailing_stop_price = position['highest_price'] * (1 - self.params['trailing_stop_pct'] / 100)
        if current_price <= trailing_stop_price:
            return True, "Trailing Stop"

        # Max hold period
        days_held = (date - position['entry_date']).days
        if days_held >= self.params['max_hold_days']:
            return True, "Max Hold Period"

        return False, ""


class ATRBreakoutStrategy(BaseStrategy):
    """
    ATR Breakout Strategy

    Entry: Price breaks above recent high + ATR buffer
    Exit: Price breaks below recent low - ATR buffer, or standard exits
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'lookback_period': 20,
            'atr_period': 14,
            'atr_multiplier': 1.5,
            'stop_loss_pct': 4.0,
            'take_profit_pct': 12.0,
            'trailing_stop_pct': 4.0,
            'max_hold_days': 30
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ATR and rolling highs/lows."""
        df['ATR'] = calculate_atr(df, self.params['atr_period'])
        df['Rolling_High'] = df['High'].rolling(window=self.params['lookback_period']).max()
        df['Rolling_Low'] = df['Low'].rolling(window=self.params['lookback_period']).min()
        return df

    def generate_signals(self, df: pd.DataFrame, date: pd.Timestamp) -> Tuple[bool, float]:
        """Generate entry signal on breakout above recent high."""
        if date not in df.index:
            return False, 0.0

        idx = df.index.get_loc(date)
        current_price = df['Close'].iloc[idx]
        rolling_high = df['Rolling_High'].iloc[idx]
        atr = df['ATR'].iloc[idx]

        if pd.isna(rolling_high) or pd.isna(atr):
            return False, 0.0

        # Breakout threshold
        breakout_level = rolling_high + (atr * self.params['atr_multiplier'])

        # Entry: price breaks above threshold
        if current_price > breakout_level:
            # Signal strength based on breakout magnitude
            breakout_strength = (current_price - rolling_high) / atr
            signal_strength = min(breakout_strength / 3, 1.0)
            return True, signal_strength

        return False, 0.0

    def check_exit(self, df: pd.DataFrame, position: Dict,
                   date: pd.Timestamp) -> Tuple[bool, str]:
        """Check exit conditions."""
        if date not in df.index:
            return False, ""

        idx = df.index.get_loc(date)
        current_price = df['Close'].iloc[idx]
        rolling_low = df['Rolling_Low'].iloc[idx]
        atr = df['ATR'].iloc[idx]

        # Breakdown below recent low
        if not pd.isna(rolling_low) and not pd.isna(atr):
            breakdown_level = rolling_low - (atr * self.params['atr_multiplier'])
            if current_price < breakdown_level:
                return True, "ATR Breakdown"

        # Stop loss
        stop_loss_price = position['entry_price'] * (1 - self.params['stop_loss_pct'] / 100)
        if current_price <= stop_loss_price:
            return True, "Stop Loss"

        # Take profit
        take_profit_price = position['entry_price'] * (1 + self.params['take_profit_pct'] / 100)
        if current_price >= take_profit_price:
            return True, "Take Profit"

        # Trailing stop
        trailing_stop_price = position['highest_price'] * (1 - self.params['trailing_stop_pct'] / 100)
        if current_price <= trailing_stop_price:
            return True, "Trailing Stop"

        # Max hold period
        days_held = (date - position['entry_date']).days
        if days_held >= self.params['max_hold_days']:
            return True, "Max Hold Period"

        return False, ""


class MultiSignalStrategy(BaseStrategy):
    """
    Multi-Signal Confluence Strategy

    Entry: RSI oversold + MACD bullish crossover (requires both)
    Exit: Any exit signal from RSI or MACD, or standard exits
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'rsi_period': 14,
            'rsi_oversold': 40,
            'rsi_overbought': 70,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'stop_loss_pct': 3.0,
            'take_profit_pct': 10.0,
            'trailing_stop_pct': 3.0,
            'max_hold_days': 30
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add RSI and MACD indicators."""
        df['RSI'] = calculate_rsi(df['Close'], self.params['rsi_period'])
        macd, signal, hist = calculate_macd(
            df['Close'],
            self.params['macd_fast'],
            self.params['macd_slow'],
            self.params['macd_signal']
        )
        df['MACD'] = macd
        df['MACD_Signal'] = signal
        df['MACD_Hist'] = hist
        return df

    def generate_signals(self, df: pd.DataFrame, date: pd.Timestamp) -> Tuple[bool, float]:
        """Generate entry signal when BOTH RSI and MACD conditions met."""
        if date not in df.index:
            return False, 0.0

        idx = df.index.get_loc(date)
        if idx < 1:
            return False, 0.0

        current_rsi = df['RSI'].iloc[idx]
        current_hist = df['MACD_Hist'].iloc[idx]
        prev_hist = df['MACD_Hist'].iloc[idx - 1]

        if pd.isna(current_rsi) or pd.isna(current_hist) or pd.isna(prev_hist):
            return False, 0.0

        # Condition 1: RSI oversold
        rsi_condition = current_rsi < self.params['rsi_oversold']

        # Condition 2: MACD bullish crossover
        macd_condition = prev_hist < 0 and current_hist > 0

        # Both conditions must be true
        if rsi_condition and macd_condition:
            # Combined signal strength
            rsi_strength = (self.params['rsi_oversold'] - current_rsi) / self.params['rsi_oversold']
            macd_strength = abs(current_hist - prev_hist) * 5  # Scale up
            signal_strength = (rsi_strength + macd_strength) / 2
            signal_strength = min(signal_strength, 1.0)
            return True, signal_strength

        return False, 0.0

    def check_exit(self, df: pd.DataFrame, position: Dict,
                   date: pd.Timestamp) -> Tuple[bool, str]:
        """Check exit conditions."""
        if date not in df.index:
            return False, ""

        idx = df.index.get_loc(date)
        current_price = df['Close'].iloc[idx]
        current_rsi = df['RSI'].iloc[idx]

        # Stop loss
        stop_loss_price = position['entry_price'] * (1 - self.params['stop_loss_pct'] / 100)
        if current_price <= stop_loss_price:
            return True, "Stop Loss"

        # Take profit
        take_profit_price = position['entry_price'] * (1 + self.params['take_profit_pct'] / 100)
        if current_price >= take_profit_price:
            return True, "Take Profit"

        # Trailing stop
        trailing_stop_price = position['highest_price'] * (1 - self.params['trailing_stop_pct'] / 100)
        if current_price <= trailing_stop_price:
            return True, "Trailing Stop"

        # RSI overbought
        if not pd.isna(current_rsi) and current_rsi > self.params['rsi_overbought']:
            return True, "RSI Overbought"

        # MACD bearish crossover
        if idx >= 1:
            current_hist = df['MACD_Hist'].iloc[idx]
            prev_hist = df['MACD_Hist'].iloc[idx - 1]

            if not pd.isna(current_hist) and not pd.isna(prev_hist):
                if prev_hist > 0 and current_hist < 0:
                    return True, "MACD Bearish Crossover"

        # Max hold period
        days_held = (date - position['entry_date']).days
        if days_held >= self.params['max_hold_days']:
            return True, "Max Hold Period"

        return False, ""
