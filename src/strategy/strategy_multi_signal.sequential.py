"""
Multi-Position Trading Strategy v3.0 - ALL FEATURES ENABLED
============================================================

🎯 OPTION A: Multi-Position Strategy
- Hold 3-5 positions simultaneously (configurable)
- Split capital: ₹20,000-33,000 per position (for ₹1L capital)
- Diversification reduces risk
- Catch more opportunities

⏰ OPTION B: Market Regime Filter
- Only trade when Nifty 50 is in bull market (above 50-day MA)
- Stay in cash during bear/choppy markets
- Reduces losses during market downturns

🔄 OPTION C: Reverse Strategy (Short Selling)
- Optional short selling in bearish markets
- Buy when RSI overbought (fade the rallies)
- Profit from both bull and bear markets

📅 OPTION D: Flexible Time Periods
- Test on different periods (2022-2023, 2024, etc.)
- Find which periods these strategies work
- Easy configuration via start_date and end_date

🛑 OPTION E: Circuit Breakers (Stop Trading Rules)
- Maximum drawdown limit: Stop trading if down 10%
- Consecutive loss limit: Stop after 3 losses in a row
- Preserve capital during bad periods
- Auto-resume after cooling-off period

Strategy Logic:
- Entry: RSI oversold + MACD bullish (or reversed for shorts)
- Signal Strength: Combined score of RSI + MACD momentum
- Exit: Stop loss (3%), Take profit (10%), Trailing stop (3%), MACD bearish, Max hold (30 days)
- Position Management: Multi-position with intelligent capital allocation

Prerequisites:
1. Run: python download_data.py (one time to download all data)
2. Run: python strategy_multi_signal.sequential.py (run strategy instantly!)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utills.load_data import DataLoader
warnings.filterwarnings('ignore')

###############################################################################
# CONFIGURATION PARAMETERS
###############################################################################
#
# 🎯 HOW TO USE EACH OPTION:
#
# OPTION A (Multi-Position):
#   - Set use_multi_position = True
#   - Adjust max_positions (3-5 recommended)
#   - capital_per_position_pct will auto-calculate
#
# OPTION B (Market Regime):
#   - Set use_market_regime_filter = True
#   - Ensure Nifty 50 data is available
#   - Adjust market_regime_ma_period (50 recommended)
#
# OPTION C (Short Selling):
#   - Set enable_short_strategy = True (automatic shorts in bear markets)
#   - OR set reverse_signals = True (always reverse signals)
#
# OPTION D (Time Period):
#   - Set use_date_filter = True
#   - Adjust start_date and end_date
#   - Try: "2022-01-01" to "2023-12-31" for bull market
#   - Try: "2024-01-01" to "2024-12-31" for recent data
#
# OPTION E (Circuit Breakers):
#   - Set use_stop_trading_rules = True
#   - Adjust max_drawdown_pct (10% recommended)
#   - Adjust max_consecutive_losses (3 recommended)
#
###############################################################################

# Capital Settings
initial_capital = 100000  # Starting capital in INR (₹1,00,000)
invest_full_capital = True  # Invest 100% of available capital each time
use_dynamic_sizing = True   # Use ATR-based position sizing

# OPTION A: Multi-Position Settings
max_positions = 5           # Maximum simultaneous positions (1-5)
use_multi_position = True   # Enable multi-position trading
capital_per_position_pct = 20  # % of total capital per position (100/max_positions)

# Technical Indicator Periods
rsi_period = 14
rsi_oversold = 40
rsi_overbought = 70
macd_fast = 12
macd_slow = 26
macd_signal = 9
ma_trend_period = 50        # Moving average for trend filter
atr_period = 14             # ATR for volatility measurement
volume_ma_period = 20       # Volume moving average period

# Risk Management Settings (IMPROVED)
stop_loss_pct = 3.0         # 3% stop-loss (tighter to minimize losses)
take_profit_pct = 10.0      # 10% take-profit
trailing_stop_pct = 3.0     # 3% trailing stop from peak
transaction_cost_pct = 0.1  # 0.1% transaction cost per trade (buy + sell)
max_hold_days = 30          # Maximum days to hold a position
cooldown_days = 10          # Days to wait before re-entering a losing stock

# Filter Settings (NEW)
use_trend_filter = False    # Only trade stocks above MA (disabled for now)
use_volume_filter = False   # Only trade with volume confirmation (disabled for now)
volume_multiplier = 1.2     # Volume must be 1.2x average
min_signal_strength = 0.05  # Minimum signal strength to enter trade (lowered)
atr_risk_multiplier = 2.0   # ATR multiplier for dynamic stop loss

# OPTION B: Market Regime Filter
use_market_regime_filter = True  # Only trade when market is bullish
nifty_symbol = "NIFTY 50"        # Nifty 50 index symbol for market regime
market_regime_ma_period = 50     # MA period for market regime detection

# OPTION C: Reverse Strategy (Short Selling)
enable_short_strategy = False    # Enable shorting in bearish markets
reverse_signals = False          # Reverse entry/exit signals for shorting

# OPTION E: Stop Trading Rules
use_stop_trading_rules = True    # Enable circuit breakers
max_drawdown_pct = 10.0          # Stop trading if drawdown exceeds 10%
max_consecutive_losses = 3       # Stop trading after 3 consecutive losses
resume_after_days = 5            # Resume trading after N days of cooling off

# Data Configuration (Date filtering for backtest period)
start_date = "2024-01-01"  # Backtest start date
end_date = "2024-12-31"    # Backtest end date
use_date_filter = True     # Enable/disable date filtering

###############################################################################
# TECHNICAL INDICATORS
###############################################################################

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD, Signal line, and Histogram"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_atr(df, period=14):
    """Calculate Average True Range (ATR) for volatility measurement"""
    high = df['High']
    low = df['Low']
    close = df['Close']

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calculate_sma(prices, period=50):
    """Calculate Simple Moving Average"""
    return prices.rolling(window=period).mean()

def calculate_volume_ma(volume, period=20):
    """Calculate Volume Moving Average"""
    return volume.rolling(window=period).mean()

###############################################################################
# ALPHABETICAL ORDER STRATEGY CLASS
###############################################################################

class AlphabeticalMultiSignalStrategy:
    """
    Multi-position trading strategy with advanced features:
    - Scans all stocks daily for entry signals
    - Can hold multiple positions simultaneously (Option A)
    - Market regime filter using Nifty 50 trend (Option B)
    - Optional short selling in bearish markets (Option C)
    - Circuit breakers for drawdown/consecutive losses (Option E)
    """

    def __init__(self):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # Trading state (OPTION A: Multi-position support)
        self.active_positions = []  # List of active positions
        self.trades = []
        self.missed_opportunities = []
        self.daily_portfolio_value = []
        self.stock_cooldown = {}  # Track cooldown periods for losing stocks

        # OPTION E: Circuit breaker state
        self.peak_capital = initial_capital
        self.consecutive_losses = 0
        self.trading_halted = False
        self.halt_resume_date = None

        # OPTION B: Market regime tracking
        self.market_regime = None  # 'bull', 'bear', or None

    def detect_market_regime(self, nifty_data, current_date):
        """
        OPTION B: Detect market regime using Nifty 50 trend
        Returns: 'bull', 'bear', or None
        """
        if not use_market_regime_filter or nifty_data is None:
            return 'bull'  # Default to bullish if filter disabled

        try:
            if current_date not in nifty_data.index:
                return None

            idx = nifty_data.index.get_loc(current_date)

            # Need enough data for MA calculation
            if 'MA' not in nifty_data.columns:
                return None

            current_price = nifty_data['Close'].iloc[idx]
            current_ma = nifty_data['MA'].iloc[idx]

            if pd.isna(current_ma):
                return None

            # Bull market: price above MA
            # Bear market: price below MA
            if current_price > current_ma:
                return 'bull'
            else:
                return 'bear'

        except Exception as e:
            return None

    def check_circuit_breakers(self, current_date):
        """
        OPTION E: Check if trading should be halted due to circuit breakers
        Returns: True if trading should continue, False if halted
        """
        if not use_stop_trading_rules:
            return True

        # Check if we're in a halt period
        if self.trading_halted:
            if current_date >= self.halt_resume_date:
                # Resume trading
                self.trading_halted = False
                self.consecutive_losses = 0
                print(f"   ▶ Trading RESUMED on {current_date.date()}")
                return True
            else:
                return False  # Still halted

        # Calculate current drawdown
        current_total_value = self.get_total_portfolio_value(current_date)
        drawdown = ((self.peak_capital - current_total_value) / self.peak_capital) * 100

        # Update peak capital
        if current_total_value > self.peak_capital:
            self.peak_capital = current_total_value

        # Check max drawdown breach
        if drawdown >= max_drawdown_pct:
            self.trading_halted = True
            self.halt_resume_date = current_date + pd.Timedelta(days=resume_after_days)
            print(f"   ⛔ CIRCUIT BREAKER: Max drawdown {drawdown:.2f}% exceeded. Halting until {self.halt_resume_date.date()}")
            return False

        # Check consecutive losses
        if self.consecutive_losses >= max_consecutive_losses:
            self.trading_halted = True
            self.halt_resume_date = current_date + pd.Timedelta(days=resume_after_days)
            print(f"   ⛔ CIRCUIT BREAKER: {self.consecutive_losses} consecutive losses. Halting until {self.halt_resume_date.date()}")
            return False

        return True

    def get_total_portfolio_value(self, current_date):
        """Calculate total portfolio value including cash and positions"""
        total_value = self.current_capital
        # Add value of all active positions (will be calculated in main loop)
        return total_value

    def calculate_signal_strength(self, rsi, macd_hist, macd_prev_hist):
        """
        Calculate combined signal strength score

        Higher score = stronger signal
        - RSI: More oversold = higher score
        - MACD: Bullish crossover momentum
        """
        # RSI component: lower RSI = higher score (more oversold = stronger)
        rsi_score = (rsi_oversold - rsi) / rsi_oversold if rsi < rsi_oversold else 0

        # MACD component: momentum of crossover (histogram change)
        macd_momentum = macd_hist - macd_prev_hist if macd_prev_hist < 0 and macd_hist > 0 else 0
        macd_score = abs(macd_momentum) * 10  # Scale up for visibility

        # Combined score (weighted: 60% RSI, 40% MACD)
        combined_score = (rsi_score * 0.6) + (macd_score * 0.4)

        return combined_score

    def check_entry_signal(self, df, date, symbol, is_short=False):
        """
        Check if entry conditions are met and return signal strength
        OPTION C: Support for short selling when is_short=True
        """
        try:
            if date not in df.index:
                return False, 0.0

            idx = df.index.get_loc(date)

            # Need previous data for MACD crossover
            if idx < 1:
                return False, 0.0

            # Check cooldown period for this stock
            if symbol in self.stock_cooldown:
                if date < self.stock_cooldown[symbol]:
                    return False, 0.0  # Still in cooldown

            current_rsi = df['RSI'].iloc[idx]
            current_macd_hist = df['MACD_Hist'].iloc[idx]
            prev_macd_hist = df['MACD_Hist'].iloc[idx - 1]

            # Check for NaN values
            if pd.isna(current_rsi) or pd.isna(current_macd_hist) or pd.isna(prev_macd_hist):
                return False, 0.0

            # OPTION C: Core Entry conditions (can be reversed for shorting)
            if is_short or reverse_signals:
                # Short entry: RSI overbought + MACD bearish crossover
                rsi_condition = current_rsi > rsi_overbought
                macd_bearish_crossover = prev_macd_hist > 0 and current_macd_hist < 0

                if not (rsi_condition and macd_bearish_crossover):
                    return False, 0.0
            else:
                # Long entry: RSI oversold + MACD bullish crossover
                rsi_condition = current_rsi < rsi_oversold
                macd_bullish_crossover = prev_macd_hist < 0 and current_macd_hist > 0

                if not (rsi_condition and macd_bullish_crossover):
                    return False, 0.0

            # Calculate signal strength
            signal_strength = self.calculate_signal_strength(
                current_rsi, current_macd_hist, prev_macd_hist
            )

            # Filter 1: Minimum signal strength
            if signal_strength < min_signal_strength:
                return False, 0.0

            # Filter 2: Trend filter - price above MA
            if use_trend_filter:
                if 'MA' in df.columns:
                    current_ma = df['MA'].iloc[idx]
                    current_price = df['Close'].iloc[idx]
                    if pd.isna(current_ma) or current_price < current_ma:
                        return False, 0.0

            # Filter 3: Volume confirmation
            if use_volume_filter:
                if 'Volume' in df.columns and 'Volume_MA' in df.columns:
                    current_volume = df['Volume'].iloc[idx]
                    avg_volume = df['Volume_MA'].iloc[idx]
                    if pd.isna(avg_volume) or current_volume < avg_volume * volume_multiplier:
                        return False, 0.0

            return True, signal_strength

        except Exception as e:
            return False, 0.0

    def check_exit_signal(self, df, date, entry_price, highest_price, entry_date):
        """Check if any exit condition is met (with improved exits)"""
        try:
            if date not in df.index:
                return False, "", df['Close'].iloc[-1]

            idx = df.index.get_loc(date)
            current_price = df['Close'].iloc[idx]

            # Need previous data for MACD crossover
            if idx < 1:
                return False, "", current_price

            current_macd_hist = df['MACD_Hist'].iloc[idx]
            prev_macd_hist = df['MACD_Hist'].iloc[idx - 1]

            # Calculate days held
            days_held = (date - entry_date).days

            # Stop Loss (tighter at 3%)
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
            if current_price <= stop_loss_price:
                return True, "Stop Loss", stop_loss_price

            # Take Profit
            take_profit_price = entry_price * (1 + take_profit_pct / 100)
            if current_price >= take_profit_price:
                return True, "Take Profit", take_profit_price

            # Trailing Stop
            trailing_stop_price = highest_price * (1 - trailing_stop_pct / 100)
            if current_price <= trailing_stop_price:
                return True, "Trailing Stop", trailing_stop_price

            # MACD Bearish Crossover
            if not pd.isna(prev_macd_hist) and not pd.isna(current_macd_hist):
                if prev_macd_hist > 0 and current_macd_hist < 0:
                    return True, "MACD Bearish Crossover", current_price

            # Maximum Hold Period (NEW)
            if days_held >= max_hold_days:
                return True, "Max Hold Period", current_price

            return False, "", current_price

        except Exception as e:
            return False, "", df['Close'].iloc[-1]

    def prepare_stock_data(self, df):
        """Add technical indicators to stock data (with new filters)"""
        df = df.copy()

        # Core indicators
        df['RSI'] = calculate_rsi(df['Close'], rsi_period)
        macd, signal, hist = calculate_macd(df['Close'], macd_fast, macd_slow, macd_signal)
        df['MACD'] = macd
        df['MACD_Signal'] = signal
        df['MACD_Hist'] = hist

        # NEW: Trend filter
        df['MA'] = calculate_sma(df['Close'], ma_trend_period)

        # NEW: ATR for volatility
        df['ATR'] = calculate_atr(df, atr_period)

        # NEW: Volume indicators
        if 'Volume' in df.columns:
            df['Volume_MA'] = calculate_volume_ma(df['Volume'], volume_ma_period)

        return df

    def scan_for_opportunities(self, all_stock_data, current_date, nifty_data=None):
        """
        OPTION A & B: Scan all stocks for entry opportunities
        Returns: List of (symbol, signal_strength, entry_price, is_short) sorted by signal strength
        """
        opportunities = []

        # OPTION B: Detect market regime
        market_regime = self.detect_market_regime(nifty_data, current_date)
        self.market_regime = market_regime

        # Determine if we should look for shorts or longs
        is_short = False
        if enable_short_strategy and market_regime == 'bear':
            is_short = True
        elif use_market_regime_filter and market_regime == 'bear':
            # Don't trade in bear markets unless shorting is enabled
            return []

        # Get currently held symbols to avoid duplicates
        held_symbols = set(pos['symbol'] for pos in self.active_positions)

        for symbol, df in all_stock_data.items():
            # Skip if already holding this stock
            if symbol in held_symbols:
                continue

            has_signal, signal_strength = self.check_entry_signal(df, current_date, symbol, is_short)

            if has_signal:
                idx = df.index.get_loc(current_date)
                entry_price = df['Close'].iloc[idx]
                opportunities.append((symbol, signal_strength, entry_price, is_short))

        # OPTION A: Return multiple opportunities sorted by signal strength
        if opportunities:
            opportunities.sort(key=lambda x: x[1], reverse=True)
            return opportunities

        return []

    def backtest(self, all_stock_data):
        """
        UPDATED: Run backtest with multi-position support and all new features

        Args:
            all_stock_data: Dict of {symbol: DataFrame} with OHLC data

        Returns:
            Dictionary with backtest results
        """
        # Prepare all stock data with indicators
        print("\nPreparing stock data with technical indicators...")
        prepared_data = {}
        nifty_data = None

        for symbol, df in all_stock_data.items():
            prepared_df = self.prepare_stock_data(df)
            prepared_data[symbol] = prepared_df

            # OPTION B: Store Nifty 50 data for market regime detection
            if symbol == nifty_symbol or 'NIFTY' in symbol.upper():
                nifty_data = prepared_df
                print(f"✓ Nifty 50 data found for market regime filter: {symbol}")

        # Get all unique dates across all stocks and sort
        all_dates = set()
        for df in prepared_data.values():
            all_dates.update(df.index)
        all_dates = sorted(all_dates)

        # Apply date filtering if enabled
        if use_date_filter:
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)

            # Handle timezone-aware dates
            if len(all_dates) > 0 and hasattr(all_dates[0], 'tz') and all_dates[0].tz is not None:
                # Make start and end timezone-aware to match the data
                start = start.tz_localize(all_dates[0].tz)
                end = end.tz_localize(all_dates[0].tz)

            all_dates = [d for d in all_dates if start <= d <= end]

            if not all_dates:
                print(f"❌ No data available in date range {start_date} to {end_date}")
                return self.calculate_performance_metrics()

            print(f"Date filter enabled: {start_date} to {end_date}")

        print(f"Backtesting from {all_dates[0].date()} to {all_dates[-1].date()}...")
        print(f"Total trading days: {len(all_dates)}")
        print(f"Max positions: {max_positions if use_multi_position else 1}")

        # Main trading loop
        for current_date in all_dates:

            # OPTION E: Check circuit breakers
            if not self.check_circuit_breakers(current_date):
                # Trading is halted, skip this day
                # Track portfolio value even when halted
                portfolio_value = self.current_capital
                for position in self.active_positions:
                    symbol = position['symbol']
                    df = prepared_data.get(symbol)
                    if df is not None and current_date in df.index:
                        idx = df.index.get_loc(current_date)
                        current_price = df['Close'].iloc[idx]
                        portfolio_value += position['quantity'] * current_price

                self.daily_portfolio_value.append({
                    'Date': current_date,
                    'Portfolio Value': portfolio_value
                })
                continue

            # OPTION A: Check exits for all active positions
            positions_to_remove = []
            for i, position in enumerate(self.active_positions):
                symbol = position['symbol']
                df = prepared_data.get(symbol)

                if df is None or current_date not in df.index:
                    continue

                idx = df.index.get_loc(current_date)
                current_price = df['Close'].iloc[idx]

                # Update highest price for trailing stop
                position['highest_price'] = max(position['highest_price'], current_price)

                # Check exit conditions
                should_exit, exit_reason, exit_price = self.check_exit_signal(
                    df, current_date,
                    position['entry_price'],
                    position['highest_price'],
                    position['entry_date']
                )

                if should_exit:
                    # Execute exit
                    quantity = position['quantity']
                    is_short = position.get('is_short', False)

                    # Calculate proceeds (handle shorts differently)
                    if is_short:
                        # Short: profit when price falls
                        gross_proceeds = position['capital_invested'] + (position['entry_price'] - exit_price) * quantity
                    else:
                        # Long: normal calculation
                        gross_proceeds = exit_price * quantity

                    exit_cost = gross_proceeds * (transaction_cost_pct / 100)
                    net_proceeds = gross_proceeds - exit_cost

                    # Update capital
                    self.current_capital += net_proceeds

                    # Calculate PnL
                    pnl = net_proceeds - position['capital_invested']
                    pnl_pct = (pnl / position['capital_invested']) * 100

                    # Record trade
                    trade = {
                        'Symbol': symbol,
                        'Entry Date': position['entry_date'],
                        'Entry Price': position['entry_price'],
                        'Exit Date': current_date,
                        'Exit Price': exit_price,
                        'Quantity': quantity,
                        'Capital Invested': position['capital_invested'],
                        'Gross Proceeds': gross_proceeds,
                        'Net Proceeds': net_proceeds,
                        'PnL': pnl,
                        'PnL %': pnl_pct,
                        'Exit Reason': exit_reason,
                        'Signal Strength': position['signal_strength'],
                        'Days Held': (current_date - position['entry_date']).days,
                        'Position Type': 'SHORT' if is_short else 'LONG',
                        'Market Regime': self.market_regime
                    }
                    self.trades.append(trade)

                    # OPTION E: Track consecutive losses
                    if pnl < 0:
                        self.consecutive_losses += 1
                        cooldown_end = current_date + pd.Timedelta(days=cooldown_days)
                        self.stock_cooldown[symbol] = cooldown_end
                    else:
                        self.consecutive_losses = 0  # Reset on win

                    # Mark for removal
                    positions_to_remove.append(i)

            # Remove exited positions
            for i in sorted(positions_to_remove, reverse=True):
                self.active_positions.pop(i)

            # OPTION A: Scan for new opportunities (can add multiple positions)
            max_positions_allowed = max_positions if use_multi_position else 1
            available_slots = max_positions_allowed - len(self.active_positions)

            if available_slots > 0:
                opportunities = self.scan_for_opportunities(prepared_data, current_date, nifty_data)

                # Take top N opportunities based on available slots
                for opp_idx, opportunity in enumerate(opportunities[:available_slots]):
                    if len(opportunity) == 4:
                        symbol, signal_strength, entry_price, is_short = opportunity
                    else:
                        # Backward compatibility
                        symbol, signal_strength, entry_price = opportunity[:3]
                        is_short = False

                    # Calculate position size
                    if use_multi_position:
                        # Split capital evenly across max positions
                        max_capital_per_position = (self.initial_capital * capital_per_position_pct) / 100
                        available_capital = min(self.current_capital, max_capital_per_position)
                    else:
                        available_capital = self.current_capital

                    if available_capital <= 0:
                        break

                    entry_cost = available_capital * (transaction_cost_pct / 100)
                    capital_to_invest = available_capital - entry_cost
                    quantity = int(capital_to_invest / entry_price)

                    if quantity > 0:
                        actual_investment = quantity * entry_price
                        total_cost = actual_investment + entry_cost

                        # Open position
                        new_position = {
                            'symbol': symbol,
                            'entry_date': current_date,
                            'entry_price': entry_price,
                            'quantity': quantity,
                            'capital_invested': total_cost,
                            'highest_price': entry_price,
                            'signal_strength': signal_strength,
                            'is_short': is_short
                        }
                        self.active_positions.append(new_position)

                        # Deduct from capital
                        self.current_capital -= total_cost

            # Track missed opportunities if positions are full
            if len(self.active_positions) >= max_positions_allowed:
                opportunities = self.scan_for_opportunities(prepared_data, current_date, nifty_data)
                held_symbols = set(pos['symbol'] for pos in self.active_positions)

                for opportunity in opportunities:
                    if len(opportunity) == 4:
                        symbol, signal_strength, entry_price, is_short = opportunity
                    else:
                        symbol, signal_strength, entry_price = opportunity[:3]
                        is_short = False

                    if symbol not in held_symbols:
                        missed = {
                            'Date': current_date,
                            'Symbol': symbol,
                            'Signal Strength': signal_strength,
                            'Entry Price': entry_price,
                            'Reason': 'All position slots full',
                            'Active Positions': ', '.join(held_symbols)
                        }
                        self.missed_opportunities.append(missed)
                        break  # Only track one missed per day

            # Track portfolio value
            portfolio_value = self.current_capital
            for position in self.active_positions:
                symbol = position['symbol']
                df = prepared_data.get(symbol)
                if df is not None and current_date in df.index:
                    idx = df.index.get_loc(current_date)
                    current_price = df['Close'].iloc[idx]
                    if position.get('is_short', False):
                        # Short position value
                        portfolio_value += position['capital_invested'] + (position['entry_price'] - current_price) * position['quantity']
                    else:
                        # Long position value
                        portfolio_value += position['quantity'] * current_price

            self.daily_portfolio_value.append({
                'Date': current_date,
                'Portfolio Value': portfolio_value
            })

        # Close any remaining open positions at last available price
        for position in self.active_positions:
            symbol = position['symbol']
            df = prepared_data.get(symbol)

            if df is None:
                continue

            last_price = df['Close'].iloc[-1]
            last_date = df.index[-1]
            quantity = position['quantity']
            is_short = position.get('is_short', False)

            if is_short:
                gross_proceeds = position['capital_invested'] + (position['entry_price'] - last_price) * quantity
            else:
                gross_proceeds = last_price * quantity

            exit_cost = gross_proceeds * (transaction_cost_pct / 100)
            net_proceeds = gross_proceeds - exit_cost

            self.current_capital += net_proceeds

            pnl = net_proceeds - position['capital_invested']
            pnl_pct = (pnl / position['capital_invested']) * 100

            trade = {
                'Symbol': symbol,
                'Entry Date': position['entry_date'],
                'Entry Price': position['entry_price'],
                'Exit Date': last_date,
                'Exit Price': last_price,
                'Quantity': quantity,
                'Capital Invested': position['capital_invested'],
                'Gross Proceeds': gross_proceeds,
                'Net Proceeds': net_proceeds,
                'PnL': pnl,
                'PnL %': pnl_pct,
                'Exit Reason': 'End of backtest',
                'Signal Strength': position['signal_strength'],
                'Days Held': (last_date - position['entry_date']).days,
                'Position Type': 'SHORT' if is_short else 'LONG',
                'Market Regime': self.market_regime
            }
            self.trades.append(trade)

        self.active_positions = []

        # Calculate performance metrics
        return self.calculate_performance_metrics()

    def calculate_performance_metrics(self):
        """Calculate comprehensive performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_return_pct': 0,
                'avg_profit_per_trade': 0,
                'missed_opportunities_count': len(self.missed_opportunities)
            }

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['PnL'] > 0]
        losing_trades = [t for t in self.trades if t['PnL'] <= 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        # PnL metrics
        total_pnl = sum(t['PnL'] for t in self.trades)
        total_return_pct = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        avg_profit_per_trade = total_pnl / total_trades if total_trades > 0 else 0

        # Win/Loss metrics
        avg_win = sum(t['PnL'] for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss = sum(t['PnL'] for t in losing_trades) / loss_count if loss_count > 0 else 0
        total_wins = sum(t['PnL'] for t in winning_trades)
        total_losses = abs(sum(t['PnL'] for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Exit reason breakdown
        exit_reasons = {}
        for trade in self.trades:
            reason = trade['Exit Reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        # Stock-wise performance
        stock_performance = {}
        for trade in self.trades:
            symbol = trade['Symbol']
            if symbol not in stock_performance:
                stock_performance[symbol] = {
                    'trades': 0,
                    'total_pnl': 0,
                    'wins': 0
                }
            stock_performance[symbol]['trades'] += 1
            stock_performance[symbol]['total_pnl'] += trade['PnL']
            if trade['PnL'] > 0:
                stock_performance[symbol]['wins'] += 1

        # Days held statistics
        days_held_list = [t['Days Held'] for t in self.trades]
        avg_days_held = sum(days_held_list) / len(days_held_list) if days_held_list else 0

        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_pnl': total_pnl,
            'total_return_pct': total_return_pct,
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'avg_profit_per_trade': avg_profit_per_trade,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_days_held': avg_days_held,
            'exit_reasons': exit_reasons,
            'stock_performance': stock_performance,
            'missed_opportunities_count': len(self.missed_opportunities)
        }

    def print_summary(self, results):
        """Print formatted backtest summary with new features"""
        print("\n" + "="*80)
        print("MULTI-POSITION STRATEGY - BACKTEST RESULTS v3.0")
        print("="*80)
        print(f"Features: Multi-Position | Market Regime | Circuit Breakers | Short Selling")
        print("="*80)

        print(f"\n💰 CAPITAL:")
        print(f"   Initial Capital:  ₹{self.initial_capital:,.2f}")
        print(f"   Final Capital:    ₹{self.current_capital:,.2f}")
        print(f"   Total PnL:        ₹{results.get('total_pnl', 0):,.2f}")
        print(f"   Total Return:     {results.get('total_return_pct', 0):.2f}%")

        print(f"\n📈 TRADE STATISTICS:")
        print(f"   Total Trades:     {results.get('total_trades', 0)}")
        print(f"   Winning Trades:   {results.get('winning_trades', 0)}")
        print(f"   Losing Trades:    {results.get('losing_trades', 0)}")
        print(f"   Win Rate:         {results.get('win_rate', 0):.2f}%")
        print(f"   Avg Profit/Trade: ₹{results.get('avg_profit_per_trade', 0):,.2f}")
        print(f"   Avg Days Held:    {results.get('avg_days_held', 0):.1f}")

        if results.get('winning_trades', 0) > 0 or results.get('losing_trades', 0) > 0:
            print(f"   Avg Win:          ₹{results.get('avg_win', 0):,.2f}")
            print(f"   Avg Loss:         ₹{results.get('avg_loss', 0):,.2f}")
            pf = results.get('profit_factor', 0)
            if pf == float('inf'):
                print(f"   Profit Factor:    ∞")
            else:
                print(f"   Profit Factor:    {pf:.2f}")

        print(f"\n🚫 MISSED OPPORTUNITIES:")
        print(f"   Total Missed:     {results.get('missed_opportunities_count', 0)}")

        # Position type breakdown
        if self.trades:
            long_trades = [t for t in self.trades if t.get('Position Type', 'LONG') == 'LONG']
            short_trades = [t for t in self.trades if t.get('Position Type', 'LONG') == 'SHORT']
            long_pnl = sum(t['PnL'] for t in long_trades)
            short_pnl = sum(t['PnL'] for t in short_trades)

            print(f"\n📊 POSITION TYPE BREAKDOWN:")
            print(f"   Long Trades:      {len(long_trades)} (₹{long_pnl:,.2f} PnL)")
            print(f"   Short Trades:     {len(short_trades)} (₹{short_pnl:,.2f} PnL)")

        print(f"\n🚪 EXIT REASONS:")
        for reason, count in results.get('exit_reasons', {}).items():
            pct = (count / results['total_trades'] * 100) if results.get('total_trades', 0) > 0 else 0
            print(f"   {reason:25s}: {count:3d} ({pct:.1f}%)")

        print(f"\n🏢 TOP 10 MOST TRADED STOCKS:")
        sorted_stocks = sorted(results.get('stock_performance', {}).items(),
                              key=lambda x: x[1]['trades'], reverse=True)
        for symbol, perf in sorted_stocks[:10]:
            win_rate = (perf['wins'] / perf['trades'] * 100) if perf['trades'] > 0 else 0
            print(f"   {symbol:15s}: {perf['trades']:2d} trades, "
                  f"₹{perf['total_pnl']:9,.2f} PnL, {win_rate:.1f}% win rate")

        print("\n" + "="*80 + "\n")

###############################################################################
# MAIN EXECUTION
###############################################################################

def main():
    """Run multi-position strategy with all enhancements"""

    print("=" * 80)
    print("MULTI-POSITION STRATEGY v3.0 - ALL FEATURES ENABLED")
    print("=" * 80)
    print(f"💰 Initial Capital: ₹{initial_capital:,.2f}")

    print(f"\n🎯 OPTION A - Multi-Position:")
    if use_multi_position:
        print(f"   ✓ ENABLED: Max {max_positions} positions | ₹{initial_capital * capital_per_position_pct / 100:,.0f} per position")
    else:
        print(f"   ✗ DISABLED: Single position only")

    print(f"\n⏰ OPTION B - Market Regime Filter:")
    if use_market_regime_filter:
        print(f"   ✓ ENABLED: Only trade in bull markets (Nifty 50 > {market_regime_ma_period}MA)")
    else:
        print(f"   ✗ DISABLED")

    print(f"\n🔄 OPTION C - Short Selling:")
    if enable_short_strategy:
        print(f"   ✓ ENABLED: Short in bear markets")
    elif reverse_signals:
        print(f"   ✓ ENABLED: Reversed signals")
    else:
        print(f"   ✗ DISABLED")

    print(f"\n📅 OPTION D - Time Period:")
    if use_date_filter:
        print(f"   {start_date} to {end_date}")
    else:
        print(f"   All available data")

    print(f"\n🛑 OPTION E - Circuit Breakers:")
    if use_stop_trading_rules:
        print(f"   ✓ ENABLED: Max Drawdown {max_drawdown_pct}% | {max_consecutive_losses} consecutive losses")
        print(f"   Cooldown: {resume_after_days} days")
    else:
        print(f"   ✗ DISABLED")

    print(f"\n📊 Strategy Parameters:")
    print(f"   Signals: RSI({rsi_period}) < {rsi_oversold} + MACD Bullish Crossover")
    print(f"   Stop Loss: {stop_loss_pct}% | Take Profit: {take_profit_pct}% | Trailing: {trailing_stop_pct}%")
    print(f"   Transaction Cost: {transaction_cost_pct}% | Max Hold: {max_hold_days} days")
    print("=" * 80)

    # Load data
    print("\nLoading NIFTY 50 data...")
    loader = DataLoader()
    all_stock_data = loader.load_all_nifty50()

    if not all_stock_data:
        print("❌ No NIFTY 50 data found!")
        print("   Run: python download_data.py")
        return

    print(f"✓ Loaded {len(all_stock_data)} NIFTY 50 stocks")

    # Initialize and run strategy
    strategy = AlphabeticalMultiSignalStrategy()
    results = strategy.backtest(all_stock_data)

    # Print summary
    strategy.print_summary(results)

    # Save results
    print("Saving results...")
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result_folder = os.path.join(script_dir, "result")
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Trades CSV
    if strategy.trades:
        trades_df = pd.DataFrame(strategy.trades)
        trades_filename = os.path.join(result_folder, f'alphabetical_strategy_trades_{timestamp}.csv')
        trades_df.to_csv(trades_filename, index=False)
        print(f"✓ Trades saved: {trades_filename}")

    # 2. Missed Opportunities CSV
    if strategy.missed_opportunities:
        missed_df = pd.DataFrame(strategy.missed_opportunities)
        missed_filename = os.path.join(result_folder, f'alphabetical_strategy_missed_{timestamp}.csv')
        missed_df.to_csv(missed_filename, index=False)
        print(f"✓ Missed opportunities saved: {missed_filename}")

    # 3. Performance Summary CSV
    summary_data = [{
        'Metric': k.replace('_', ' ').title(),
        'Value': v
    } for k, v in results.items() if not isinstance(v, dict)]

    summary_df = pd.DataFrame(summary_data)
    summary_filename = os.path.join(result_folder, f'alphabetical_strategy_summary_{timestamp}.csv')
    summary_df.to_csv(summary_filename, index=False)
    print(f"✓ Summary saved: {summary_filename}")

    # 4. Daily Portfolio Value CSV
    if strategy.daily_portfolio_value:
        portfolio_df = pd.DataFrame(strategy.daily_portfolio_value)
        portfolio_filename = os.path.join(result_folder, f'alphabetical_strategy_portfolio_{timestamp}.csv')
        portfolio_df.to_csv(portfolio_filename, index=False)
        print(f"✓ Portfolio value saved: {portfolio_filename}")

    print("\n" + "="*80)
    print("✓ BACKTEST COMPLETED!")
    print("="*80)

if __name__ == "__main__":
    main()