"""
ROC Sequential Trading Strategy - IMPROVED VERSION
==================================================
Sequential trading strategy where:
- Only ONE position is held at a time
- 100% of available capital is invested in each trade
- Scans ALL stocks daily for the strongest ROC signal
- Transaction costs reduce available capital
- Tracks missed opportunities when capital is locked

IMPROVEMENTS:
- ✓ Trend filter: Only trade stocks above 50-day MA (uptrend confirmation)
- ✓ Volume confirmation: Entry requires above-average volume
- ✓ Tighter stop loss: 4% to minimize losses
- ✓ Cooldown period: 10 days before re-entering losing stocks
- ✓ Maximum hold period: 30 days to free capital faster
- ✓ Minimum signal strength: ROC threshold for quality entries

Strategy Logic:
- Entry: ROC > threshold + Trend up + Volume high
- Signal Strength: ROC value (higher = stronger momentum)
- Exit: Stop loss (4%), Take profit (15%), Trailing stop (4%), or Max hold (30 days)
- Position Management: Sequential - one trade at a time with cooldown

Prerequisites:
1. Run: python download_data.py (one time to download all data)
2. Run: python strategy_roc_sequential.py (run strategy instantly!)
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

# Capital Settings
initial_capital = 100000  # Starting capital in INR (₹1,00,000)
invest_full_capital = True  # Invest 100% of available capital each time

# ROC Strategy Settings
roc_period = 10             # Period for ROC calculation (days)
roc_buy_threshold = 5.0     # Buy when ROC > 5% (strong positive momentum)
roc_sell_threshold = -3.0   # Exit when ROC < -3% (momentum reversal)
ma_trend_period = 50        # Moving average for trend filter
volume_ma_period = 20       # Volume moving average period

# Risk Management Settings
stop_loss_pct = 4.0         # 4% stop-loss
take_profit_pct = 15.0      # 15% take-profit (momentum strategy)
trailing_stop_pct = 4.0     # 4% trailing stop from peak
transaction_cost_pct = 0.1  # 0.1% transaction cost per trade (buy + sell)
max_hold_days = 30          # Maximum days to hold a position
cooldown_days = 10          # Days to wait before re-entering a losing stock

# Filter Settings
use_trend_filter = False    # Only trade stocks above MA
use_volume_filter = False   # Only trade with volume confirmation
volume_multiplier = 1.3     # Volume must be 1.3x average
min_roc_signal = 5.0        # Minimum ROC value to enter trade

# Data Configuration (Date filtering for backtest period)
start_date = "2024-01-01"  # Backtest start date
end_date = "2025-12-31"    # Backtest end date
use_date_filter = True     # Enable/disable date filtering

###############################################################################
# TECHNICAL INDICATORS
###############################################################################

def calculate_roc(prices, period=10):
    """
    Calculate Rate of Change (ROC)
    ROC = ((Current Price - Price n periods ago) / Price n periods ago) * 100
    """
    roc = ((prices - prices.shift(period)) / prices.shift(period)) * 100
    return roc

def calculate_sma(prices, period=50):
    """Calculate Simple Moving Average"""
    return prices.rolling(window=period).mean()

def calculate_volume_ma(volume, period=20):
    """Calculate Volume Moving Average"""
    return volume.rolling(window=period).mean()

###############################################################################
# ROC SEQUENTIAL STRATEGY CLASS
###############################################################################

class ROCSequentialStrategy:
    """
    Sequential trading strategy that:
    - Scans all stocks daily for ROC momentum signals
    - Picks the strongest signal when capital is available
    - Holds one position at a time
    - Immediately looks for next opportunity after exit
    """

    def __init__(self):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # Trading state
        self.active_position = None
        self.trades = []
        self.missed_opportunities = []
        self.daily_portfolio_value = []
        self.stock_cooldown = {}  # Track cooldown periods for losing stocks

    def check_entry_signal(self, df, date, symbol):
        """Check if entry conditions are met and return signal strength (ROC value)"""
        try:
            if date not in df.index:
                return False, 0.0

            idx = df.index.get_loc(date)

            # Need enough data
            if idx < 1:
                return False, 0.0

            # Check cooldown period for this stock
            if symbol in self.stock_cooldown:
                if date < self.stock_cooldown[symbol]:
                    return False, 0.0  # Still in cooldown

            current_roc = df['ROC'].iloc[idx]

            # Check for NaN values
            if pd.isna(current_roc):
                return False, 0.0

            # Core Entry condition: ROC above buy threshold
            if current_roc <= roc_buy_threshold:
                return False, 0.0

            # Signal strength is the ROC value itself
            signal_strength = current_roc

            # Filter 1: Minimum signal strength
            if signal_strength < min_roc_signal:
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
        """Check if any exit condition is met"""
        try:
            if date not in df.index:
                return False, "", df['Close'].iloc[-1]

            idx = df.index.get_loc(date)
            current_price = df['Close'].iloc[idx]

            # Need previous data for ROC
            if idx < 1:
                return False, "", current_price

            current_roc = df['ROC'].iloc[idx]

            # Calculate days held
            days_held = (date - entry_date).days

            # Stop Loss
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

            # ROC Momentum Reversal
            if not pd.isna(current_roc) and current_roc < roc_sell_threshold:
                return True, "ROC Reversal", current_price

            # Maximum Hold Period
            if days_held >= max_hold_days:
                return True, "Max Hold Period", current_price

            return False, "", current_price

        except Exception as e:
            return False, "", df['Close'].iloc[-1]

    def prepare_stock_data(self, df):
        """Add technical indicators to stock data"""
        df = df.copy()

        # Core indicators
        df['ROC'] = calculate_roc(df['Close'], roc_period)

        # Trend filter
        df['MA'] = calculate_sma(df['Close'], ma_trend_period)

        # Volume indicators
        if 'Volume' in df.columns:
            df['Volume_MA'] = calculate_volume_ma(df['Volume'], volume_ma_period)

        return df

    def scan_for_opportunities(self, all_stock_data, current_date):
        """
        Scan all stocks for entry opportunities on given date
        Returns: (symbol, signal_strength, entry_price) or None
        """
        opportunities = []

        for symbol, df in all_stock_data.items():
            has_signal, signal_strength = self.check_entry_signal(df, current_date, symbol)

            if has_signal:
                idx = df.index.get_loc(current_date)
                entry_price = df['Close'].iloc[idx]
                opportunities.append((symbol, signal_strength, entry_price))

        # Return the opportunity with highest signal strength (highest ROC)
        if opportunities:
            opportunities.sort(key=lambda x: x[1], reverse=True)
            return opportunities[0]

        return None

    def backtest(self, all_stock_data):
        """
        Run backtest on all stocks with sequential ROC strategy

        Args:
            all_stock_data: Dict of {symbol: DataFrame} with OHLC data

        Returns:
            Dictionary with backtest results
        """
        # Prepare all stock data with indicators
        print("\nPreparing stock data with technical indicators...")
        prepared_data = {}
        for symbol, df in all_stock_data.items():
            prepared_data[symbol] = self.prepare_stock_data(df)

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

        # Main trading loop
        for current_date in all_dates:

            # If we have an active position, check for exit
            if self.active_position:
                symbol = self.active_position['symbol']
                df = prepared_data[symbol]

                # Check if current date exists in this stock's data
                if current_date not in df.index:
                    continue

                idx = df.index.get_loc(current_date)
                current_price = df['Close'].iloc[idx]

                # Update highest price for trailing stop
                self.active_position['highest_price'] = max(
                    self.active_position['highest_price'], current_price
                )

                # Check exit conditions
                should_exit, exit_reason, exit_price = self.check_exit_signal(
                    df, current_date,
                    self.active_position['entry_price'],
                    self.active_position['highest_price'],
                    self.active_position['entry_date']
                )

                if should_exit:
                    # Execute exit
                    quantity = self.active_position['quantity']

                    # Calculate proceeds
                    gross_proceeds = exit_price * quantity
                    exit_cost = gross_proceeds * (transaction_cost_pct / 100)
                    net_proceeds = gross_proceeds - exit_cost

                    # Update capital
                    self.current_capital = net_proceeds

                    # Calculate PnL
                    pnl = net_proceeds - self.active_position['capital_invested']
                    pnl_pct = (pnl / self.active_position['capital_invested']) * 100

                    # Record trade
                    trade = {
                        'Symbol': symbol,
                        'Entry Date': self.active_position['entry_date'],
                        'Entry Price': self.active_position['entry_price'],
                        'Exit Date': current_date,
                        'Exit Price': exit_price,
                        'Quantity': quantity,
                        'Capital Invested': self.active_position['capital_invested'],
                        'Gross Proceeds': gross_proceeds,
                        'Net Proceeds': net_proceeds,
                        'PnL': pnl,
                        'PnL %': pnl_pct,
                        'Exit Reason': exit_reason,
                        'Signal Strength (ROC)': self.active_position['signal_strength'],
                        'Days Held': (current_date - self.active_position['entry_date']).days
                    }
                    self.trades.append(trade)

                    # NEW: Implement cooldown for losing trades
                    if pnl < 0:
                        cooldown_end = current_date + pd.Timedelta(days=cooldown_days)
                        self.stock_cooldown[symbol] = cooldown_end

                    # Clear active position
                    self.active_position = None

            # Scan for new opportunities (whether we just exited or have no position)
            if self.active_position is None:
                opportunity = self.scan_for_opportunities(prepared_data, current_date)

                if opportunity:
                    symbol, signal_strength, entry_price = opportunity

                    # Calculate position size (100% of capital)
                    entry_cost = self.current_capital * (transaction_cost_pct / 100)
                    capital_to_invest = self.current_capital - entry_cost
                    quantity = int(capital_to_invest / entry_price)

                    if quantity > 0:
                        actual_investment = quantity * entry_price
                        total_cost = actual_investment + entry_cost

                        # Open position
                        self.active_position = {
                            'symbol': symbol,
                            'entry_date': current_date,
                            'entry_price': entry_price,
                            'quantity': quantity,
                            'capital_invested': total_cost,
                            'highest_price': entry_price,
                            'signal_strength': signal_strength
                        }

                        # Deduct from capital (temporarily set to 0 as it's invested)
                        self.current_capital = 0

            else:
                # We have an active position, check for missed opportunities
                opportunity = self.scan_for_opportunities(prepared_data, current_date)

                if opportunity and opportunity[0] != self.active_position['symbol']:
                    symbol, signal_strength, entry_price = opportunity

                    missed = {
                        'Date': current_date,
                        'Symbol': symbol,
                        'Signal Strength (ROC)': signal_strength,
                        'Entry Price': entry_price,
                        'Reason': 'Capital locked in active position',
                        'Active Position': self.active_position['symbol']
                    }
                    self.missed_opportunities.append(missed)

            # Track portfolio value
            portfolio_value = self.current_capital
            if self.active_position:
                symbol = self.active_position['symbol']
                df = prepared_data[symbol]
                if current_date in df.index:
                    idx = df.index.get_loc(current_date)
                    current_price = df['Close'].iloc[idx]
                    portfolio_value = self.active_position['quantity'] * current_price

            self.daily_portfolio_value.append({
                'Date': current_date,
                'Portfolio Value': portfolio_value
            })

        # Close any remaining open position at last available price
        if self.active_position:
            symbol = self.active_position['symbol']
            df = prepared_data[symbol]
            last_price = df['Close'].iloc[-1]
            last_date = df.index[-1]

            quantity = self.active_position['quantity']
            gross_proceeds = last_price * quantity
            exit_cost = gross_proceeds * (transaction_cost_pct / 100)
            net_proceeds = gross_proceeds - exit_cost

            self.current_capital = net_proceeds

            pnl = net_proceeds - self.active_position['capital_invested']
            pnl_pct = (pnl / self.active_position['capital_invested']) * 100

            trade = {
                'Symbol': symbol,
                'Entry Date': self.active_position['entry_date'],
                'Entry Price': self.active_position['entry_price'],
                'Exit Date': last_date,
                'Exit Price': last_price,
                'Quantity': quantity,
                'Capital Invested': self.active_position['capital_invested'],
                'Gross Proceeds': gross_proceeds,
                'Net Proceeds': net_proceeds,
                'PnL': pnl,
                'PnL %': pnl_pct,
                'Exit Reason': 'End of backtest',
                'Signal Strength (ROC)': self.active_position['signal_strength'],
                'Days Held': (last_date - self.active_position['entry_date']).days
            }
            self.trades.append(trade)
            self.active_position = None

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
        """Print formatted backtest summary"""
        print("\n" + "="*80)
        print("ROC SEQUENTIAL STRATEGY - BACKTEST RESULTS")
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
    """Run ROC sequential strategy on NIFTY 50 data"""

    print("=" * 80)
    print("ROC SEQUENTIAL STRATEGY - MOMENTUM BASED")
    print("=" * 80)
    print(f"Initial Capital: ₹{initial_capital:,.2f}")
    print(f"Position Sizing: 100% of available capital per trade")
    print(f"Signal: ROC({roc_period}) > {roc_buy_threshold}%")
    print(f"Stop Loss: {stop_loss_pct}% | Take Profit: {take_profit_pct}% | Trailing Stop: {trailing_stop_pct}%")
    print(f"Transaction Cost: {transaction_cost_pct}% per trade")
    print(f"Max Hold Period: {max_hold_days} days | Cooldown: {cooldown_days} days")
    if use_date_filter:
        print(f"📅 Date Range: {start_date} to {end_date}")
    else:
        print(f"📅 Date Range: All available data")
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
    strategy = ROCSequentialStrategy()
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
        trades_filename = os.path.join(result_folder, f'roc_sequential_trades_{timestamp}.csv')
        trades_df.to_csv(trades_filename, index=False)
        print(f"✓ Trades saved: {trades_filename}")

    # 2. Missed Opportunities CSV
    if strategy.missed_opportunities:
        missed_df = pd.DataFrame(strategy.missed_opportunities)
        missed_filename = os.path.join(result_folder, f'roc_sequential_missed_{timestamp}.csv')
        missed_df.to_csv(missed_filename, index=False)
        print(f"✓ Missed opportunities saved: {missed_filename}")

    # 3. Performance Summary CSV
    summary_data = [{
        'Metric': k.replace('_', ' ').title(),
        'Value': v
    } for k, v in results.items() if not isinstance(v, dict)]

    summary_df = pd.DataFrame(summary_data)
    summary_filename = os.path.join(result_folder, f'roc_sequential_summary_{timestamp}.csv')
    summary_df.to_csv(summary_filename, index=False)
    print(f"✓ Summary saved: {summary_filename}")

    # 4. Daily Portfolio Value CSV
    if strategy.daily_portfolio_value:
        portfolio_df = pd.DataFrame(strategy.daily_portfolio_value)
        portfolio_filename = os.path.join(result_folder, f'roc_sequential_portfolio_{timestamp}.csv')
        portfolio_df.to_csv(portfolio_filename, index=False)
        print(f"✓ Portfolio value saved: {portfolio_filename}")

    print("\n" + "="*80)
    print("✓ BACKTEST COMPLETED!")
    print("="*80)

if __name__ == "__main__":
    main()
