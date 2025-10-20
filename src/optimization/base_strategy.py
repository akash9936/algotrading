"""
Base Strategy Class - Abstract Interface

This module defines the base class that all trading strategies must inherit from.
Provides standardized interface for backtesting and comparison.
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.

    All strategy implementations must inherit from this class and implement
    the required methods.
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        Initialize strategy with parameters.

        Args:
            params: Dictionary of strategy parameters
        """
        self.params = params or {}
        self.name = self.__class__.__name__

        # Trading state
        self.initial_capital = self.params.get('initial_capital', 100000)
        self.current_capital = self.initial_capital
        self.positions = []
        self.trades = []
        self.daily_portfolio_value = []

        # Risk management defaults
        self.transaction_cost_pct = self.params.get('transaction_cost_pct', 0.1)
        self.max_positions = self.params.get('max_positions', 1)

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, date: pd.Timestamp) -> Tuple[bool, float]:
        """
        Generate entry signals for a given stock and date.

        Args:
            df: DataFrame with OHLC data and indicators
            date: Current date to evaluate

        Returns:
            Tuple of (has_signal: bool, signal_strength: float)
        """
        pass

    @abstractmethod
    def check_exit(self, df: pd.DataFrame, position: Dict, date: pd.Timestamp) -> Tuple[bool, str]:
        """
        Check if position should be exited.

        Args:
            df: DataFrame with OHLC data and indicators
            position: Current position dictionary
            date: Current date

        Returns:
            Tuple of (should_exit: bool, exit_reason: str)
        """
        pass

    @abstractmethod
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators required by this strategy.

        Args:
            df: Raw OHLC DataFrame

        Returns:
            DataFrame with added indicators
        """
        pass

    def calculate_position_size(self, available_capital: float, entry_price: float) -> int:
        """
        Calculate position size based on available capital.

        Args:
            available_capital: Cash available for this trade
            entry_price: Entry price per share

        Returns:
            Number of shares to buy
        """
        # Account for transaction costs
        entry_cost = available_capital * (self.transaction_cost_pct / 100)
        capital_to_invest = available_capital - entry_cost

        # Calculate quantity
        quantity = int(capital_to_invest / entry_price)

        return quantity

    def enter_position(self, symbol: str, date: pd.Timestamp, price: float,
                      signal_strength: float) -> Optional[Dict]:
        """
        Enter a new position.

        Args:
            symbol: Stock symbol
            date: Entry date
            price: Entry price
            signal_strength: Strength of entry signal

        Returns:
            Position dictionary or None if cannot enter
        """
        # Check if we can add more positions
        if len(self.positions) >= self.max_positions:
            return None

        # Calculate capital allocation
        if self.max_positions > 1:
            max_capital_per_position = self.initial_capital / self.max_positions
            available_capital = min(self.current_capital, max_capital_per_position)
        else:
            available_capital = self.current_capital

        if available_capital <= 0:
            return None

        # Calculate position size
        quantity = self.calculate_position_size(available_capital, price)

        if quantity <= 0:
            return None

        # Calculate actual costs
        actual_investment = quantity * price
        entry_cost = actual_investment * (self.transaction_cost_pct / 100)
        total_cost = actual_investment + entry_cost

        if total_cost > self.current_capital:
            return None

        # Create position
        position = {
            'symbol': symbol,
            'entry_date': date,
            'entry_price': price,
            'quantity': quantity,
            'capital_invested': total_cost,
            'highest_price': price,
            'signal_strength': signal_strength,
            'strategy': self.name
        }

        # Update state
        self.positions.append(position)
        self.current_capital -= total_cost

        return position

    def exit_position(self, position: Dict, date: pd.Timestamp,
                     exit_price: float, exit_reason: str) -> Dict:
        """
        Exit a position and record the trade.

        Args:
            position: Position dictionary
            date: Exit date
            exit_price: Exit price
            exit_reason: Reason for exit

        Returns:
            Trade dictionary
        """
        quantity = position['quantity']

        # Calculate proceeds
        gross_proceeds = exit_price * quantity
        exit_cost = gross_proceeds * (self.transaction_cost_pct / 100)
        net_proceeds = gross_proceeds - exit_cost

        # Update capital
        self.current_capital += net_proceeds

        # Calculate PnL
        pnl = net_proceeds - position['capital_invested']
        pnl_pct = (pnl / position['capital_invested']) * 100

        # Create trade record
        trade = {
            'Symbol': position['symbol'],
            'Strategy': self.name,
            'Entry Date': position['entry_date'],
            'Entry Price': position['entry_price'],
            'Exit Date': date,
            'Exit Price': exit_price,
            'Quantity': quantity,
            'Capital Invested': position['capital_invested'],
            'Gross Proceeds': gross_proceeds,
            'Net Proceeds': net_proceeds,
            'PnL': pnl,
            'PnL %': pnl_pct,
            'Exit Reason': exit_reason,
            'Signal Strength': position['signal_strength'],
            'Days Held': (date - position['entry_date']).days
        }

        self.trades.append(trade)

        # Remove from positions
        if position in self.positions:
            self.positions.remove(position)

        return trade

    def backtest(self, all_stock_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Run backtest on all provided stock data.

        Args:
            all_stock_data: Dictionary of {symbol: DataFrame}

        Returns:
            Dictionary with performance metrics
        """
        # Reset state
        self.current_capital = self.initial_capital
        self.positions = []
        self.trades = []
        self.daily_portfolio_value = []

        # Prepare all data
        prepared_data = {}
        for symbol, df in all_stock_data.items():
            prepared_data[symbol] = self.prepare_data(df.copy())

        # Get all dates
        all_dates = set()
        for df in prepared_data.values():
            all_dates.update(df.index)
        all_dates = sorted(all_dates)

        # Main trading loop
        for current_date in all_dates:
            # Check exits for existing positions
            positions_to_exit = []
            for position in self.positions:
                symbol = position['symbol']
                df = prepared_data.get(symbol)

                if df is None or current_date not in df.index:
                    continue

                # Update highest price for trailing stop
                idx = df.index.get_loc(current_date)
                current_price = df['Close'].iloc[idx]
                position['highest_price'] = max(position['highest_price'], current_price)

                # Check exit conditions
                should_exit, exit_reason = self.check_exit(df, position, current_date)

                if should_exit:
                    positions_to_exit.append((position, exit_reason, current_price))

            # Execute exits
            for position, exit_reason, exit_price in positions_to_exit:
                self.exit_position(position, current_date, exit_price, exit_reason)

            # Scan for new entries
            available_slots = self.max_positions - len(self.positions)
            if available_slots > 0:
                opportunities = []

                for symbol, df in prepared_data.items():
                    # Skip if already holding
                    if any(p['symbol'] == symbol for p in self.positions):
                        continue

                    if current_date not in df.index:
                        continue

                    # Check for entry signal
                    has_signal, signal_strength = self.generate_signals(df, current_date)

                    if has_signal:
                        idx = df.index.get_loc(current_date)
                        entry_price = df['Close'].iloc[idx]
                        opportunities.append((symbol, signal_strength, entry_price))

                # Sort by signal strength and enter top N
                opportunities.sort(key=lambda x: x[1], reverse=True)

                for symbol, signal_strength, entry_price in opportunities[:available_slots]:
                    self.enter_position(symbol, current_date, entry_price, signal_strength)

            # Track portfolio value
            portfolio_value = self.current_capital
            for position in self.positions:
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

        # Close remaining positions
        for position in list(self.positions):
            symbol = position['symbol']
            df = prepared_data.get(symbol)
            if df is not None:
                last_price = df['Close'].iloc[-1]
                last_date = df.index[-1]
                self.exit_position(position, last_date, last_price, 'End of backtest')

        # Calculate metrics
        return self.calculate_metrics()

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from trades."""
        if not self.trades:
            return {
                'strategy': self.name,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'total_return_pct': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'profit_factor': 0
            }

        trades_df = pd.DataFrame(self.trades)

        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['PnL'] > 0])
        losing_trades = len(trades_df[trades_df['PnL'] <= 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # PnL metrics
        total_pnl = trades_df['PnL'].sum()
        total_return_pct = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100

        # Win/Loss metrics
        wins = trades_df[trades_df['PnL'] > 0]['PnL']
        losses = trades_df[trades_df['PnL'] <= 0]['PnL']

        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0

        total_wins = wins.sum() if len(wins) > 0 else 0
        total_losses = abs(losses.sum()) if len(losses) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Calculate Sharpe Ratio
        sharpe_ratio = self._calculate_sharpe_ratio()

        # Calculate Max Drawdown
        max_drawdown = self._calculate_max_drawdown()

        return {
            'strategy': self.name,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_return': total_pnl,
            'total_return_pct': total_return_pct,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_days_held': trades_df['Days Held'].mean(),
            'final_capital': self.current_capital
        }

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.05) -> float:
        """Calculate Sharpe Ratio."""
        if len(self.daily_portfolio_value) < 2:
            return 0.0

        df = pd.DataFrame(self.daily_portfolio_value)
        df['Returns'] = df['Portfolio Value'].pct_change()
        returns = df['Returns'].dropna()

        if len(returns) < 2:
            return 0.0

        mean_return = returns.mean() * 252  # Annualized
        std_return = returns.std() * np.sqrt(252)

        if std_return == 0:
            return 0.0

        sharpe = (mean_return - risk_free_rate) / std_return
        return sharpe

    def _calculate_max_drawdown(self) -> float:
        """Calculate Maximum Drawdown."""
        if not self.daily_portfolio_value:
            return 0.0

        df = pd.DataFrame(self.daily_portfolio_value)
        df['Cumulative_Max'] = df['Portfolio Value'].cummax()
        df['Drawdown'] = (df['Portfolio Value'] - df['Cumulative_Max']) / df['Cumulative_Max'] * 100

        max_dd = df['Drawdown'].min()
        return max_dd


# Technical Indicator Helper Functions
def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26,
                   signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD, Signal line, and Histogram."""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices: pd.Series, period: int = 20,
                              std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands."""
    ma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = ma + (std * std_dev)
    lower_band = ma - (std * std_dev)
    return upper_band, ma, lower_band


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
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


def calculate_sma(prices: pd.Series, period: int = 50) -> pd.Series:
    """Calculate Simple Moving Average."""
    return prices.rolling(window=period).mean()


def calculate_ema(prices: pd.Series, period: int = 50) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return prices.ewm(span=period, adjust=False).mean()
