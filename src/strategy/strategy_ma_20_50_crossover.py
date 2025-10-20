"""
MA CROSSOVER STRATEGY (20/50)
==============================

STRATEGY RULES:
- Entry: 20 MA crosses ABOVE 50 MA (Golden Cross)
- Stop Loss: 10%
- Take Profit: 30%
- Test on all Nifty 50 stocks

USAGE:
    python src/strategy/strategy_ma_20_50_crossover.py
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
initial_capital = 100000          # Starting capital ₹1,00,000
max_positions = 3                 # Maximum 3 simultaneous positions
capital_per_position_pct = 33.33  # 33.33% per position

# MA Crossover Parameters
ma_short_period = 20              # 20-day MA
ma_long_period = 50               # 50-day MA

# Risk Management Settings
stop_loss_pct = 10.0              # 10% stop loss
take_profit_pct = 30.0            # 30% take profit
transaction_cost_pct = 0.1        # 0.1% transaction cost

###############################################################################
# TECHNICAL INDICATORS
###############################################################################

def calculate_sma(prices, period):
    """Calculate Simple Moving Average"""
    return prices.rolling(window=period).mean()

###############################################################################
# MA CROSSOVER STRATEGY CLASS
###############################################################################

class MACrossoverStrategy:
    """
    Simple Moving Average Crossover Strategy (20/50)

    Entry: 20 MA crosses above 50 MA
    Exit: 10% stop loss OR 30% take profit
    """

    def __init__(self):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # Multi-position support
        self.active_positions = []
        self.trades = []
        self.daily_portfolio_value = []

    def calculate_indicators(self, df):
        """Add technical indicators to dataframe"""
        df = df.copy()
        df['MA_20'] = calculate_sma(df['Close'], ma_short_period)
        df['MA_50'] = calculate_sma(df['Close'], ma_long_period)
        return df

    def check_entry_signal(self, df, date):
        """
        Check for Golden Cross (20 MA crosses above 50 MA)

        Returns:
            bool: True if entry signal detected
        """
        try:
            if date not in df.index:
                return False

            idx = df.index.get_loc(date)

            # Need at least 2 periods for crossover
            if idx < 1:
                return False

            # Current and previous MA values
            ma_20_curr = df['MA_20'].iloc[idx]
            ma_50_curr = df['MA_50'].iloc[idx]
            ma_20_prev = df['MA_20'].iloc[idx - 1]
            ma_50_prev = df['MA_50'].iloc[idx - 1]

            # Check for NaN
            if any(pd.isna(x) for x in [ma_20_curr, ma_50_curr, ma_20_prev, ma_50_prev]):
                return False

            # Golden Cross: 20 MA crosses ABOVE 50 MA
            golden_cross = (ma_20_prev <= ma_50_prev) and (ma_20_curr > ma_50_curr)

            return golden_cross

        except Exception as e:
            return False

    def check_exit_signal(self, df, date, position):
        """
        Check for exit conditions:
        1. Stop Loss (10%)
        2. Take Profit (30%)

        Returns:
            tuple: (should_exit, exit_reason, exit_price)
        """
        try:
            if date not in df.index:
                return False, "", df['Close'].iloc[-1]

            idx = df.index.get_loc(date)
            current_price = df['Close'].iloc[idx]
            entry_price = position['entry_price']

            # Calculate profit/loss percentage
            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # Stop Loss (10%)
            if pnl_pct <= -stop_loss_pct:
                return True, "Stop Loss", current_price

            # Take Profit (30%)
            if pnl_pct >= take_profit_pct:
                return True, "Take Profit", current_price

            return False, "", current_price

        except Exception as e:
            return False, "", df['Close'].iloc[-1]

    def scan_for_opportunities(self, all_stock_data, current_date):
        """
        Scan all stocks for entry signals

        Returns:
            list: List of (symbol, entry_price) tuples
        """
        opportunities = []

        # Get held symbols
        held_symbols = set(pos['symbol'] for pos in self.active_positions)

        for symbol, df in all_stock_data.items():
            # Skip if already holding this stock
            if symbol in held_symbols:
                continue

            # Check for entry signal
            if self.check_entry_signal(df, current_date):
                idx = df.index.get_loc(current_date)
                entry_price = df['Close'].iloc[idx]
                opportunities.append((symbol, entry_price))

        return opportunities

    def backtest(self, all_stock_data):
        """Run backtest on all stocks"""

        print("\nPreparing stock data with technical indicators...")
        prepared_data = {}

        for symbol, df in all_stock_data.items():
            prepared_df = self.calculate_indicators(df)
            prepared_data[symbol] = prepared_df

        # Get all trading dates
        all_dates = set()
        for df in prepared_data.values():
            all_dates.update(df.index)
        all_dates = sorted(all_dates)

        if not all_dates:
            print("❌ No data available")
            return self.calculate_performance_metrics()

        print(f"\nBacktesting: {all_dates[0].date()} to {all_dates[-1].date()}")
        print(f"Trading days: {len(all_dates)}")
        print(f"Max positions: {max_positions}")
        print(f"Capital per position: ₹{initial_capital * capital_per_position_pct / 100:,.0f}")
        print(f"\nStrategy Rules:")
        print(f"  Entry: 20 MA crosses ABOVE 50 MA")
        print(f"  Stop Loss: {stop_loss_pct}%")
        print(f"  Take Profit: {take_profit_pct}%")
        print(f"\nRunning backtest...\n")

        # Main trading loop
        for current_date in all_dates:

            # Check exits for active positions
            positions_to_remove = []
            for i, position in enumerate(self.active_positions):
                symbol = position['symbol']
                df = prepared_data.get(symbol)

                if df is None or current_date not in df.index:
                    continue

                # Check exit
                should_exit, exit_reason, exit_price = self.check_exit_signal(df, current_date, position)

                if should_exit:
                    # Execute exit
                    quantity = position['quantity']
                    gross_proceeds = exit_price * quantity
                    exit_cost = gross_proceeds * (transaction_cost_pct / 100)
                    net_proceeds = gross_proceeds - exit_cost

                    self.current_capital += net_proceeds

                    pnl = net_proceeds - position['capital_invested']
                    pnl_pct = (pnl / position['capital_invested']) * 100

                    trade = {
                        'Symbol': symbol,
                        'Entry Date': position['entry_date'],
                        'Entry Price': position['entry_price'],
                        'Exit Date': current_date,
                        'Exit Price': exit_price,
                        'Quantity': quantity,
                        'Capital Invested': position['capital_invested'],
                        'Net Proceeds': net_proceeds,
                        'PnL': pnl,
                        'PnL %': pnl_pct,
                        'Exit Reason': exit_reason,
                        'Days Held': (current_date - position['entry_date']).days
                    }
                    self.trades.append(trade)

                    positions_to_remove.append(i)

            # Remove exited positions
            for i in sorted(positions_to_remove, reverse=True):
                self.active_positions.pop(i)

            # Scan for new opportunities
            available_slots = max_positions - len(self.active_positions)

            if available_slots > 0:
                opportunities = self.scan_for_opportunities(prepared_data, current_date)

                for symbol, entry_price in opportunities[:available_slots]:
                    # Calculate position size
                    max_capital_per_pos = (self.initial_capital * capital_per_position_pct) / 100
                    available_capital = min(self.current_capital, max_capital_per_pos)

                    if available_capital <= 0:
                        break

                    entry_cost = available_capital * (transaction_cost_pct / 100)
                    capital_to_invest = available_capital - entry_cost
                    quantity = int(capital_to_invest / entry_price)

                    if quantity > 0:
                        actual_investment = quantity * entry_price
                        total_cost = actual_investment + entry_cost

                        new_position = {
                            'symbol': symbol,
                            'entry_date': current_date,
                            'entry_price': entry_price,
                            'quantity': quantity,
                            'capital_invested': total_cost
                        }
                        self.active_positions.append(new_position)
                        self.current_capital -= total_cost

            # Track portfolio value
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

        # Close remaining positions at end of backtest
        for position in self.active_positions:
            symbol = position['symbol']
            df = prepared_data.get(symbol)

            if df is None:
                continue

            last_price = df['Close'].iloc[-1]
            last_date = df.index[-1]
            quantity = position['quantity']

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
                'Net Proceeds': net_proceeds,
                'PnL': pnl,
                'PnL %': pnl_pct,
                'Exit Reason': 'End of backtest',
                'Days Held': (last_date - position['entry_date']).days
            }
            self.trades.append(trade)

        self.active_positions = []

        return self.calculate_performance_metrics()

    def calculate_performance_metrics(self):
        """Calculate comprehensive performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'total_return_pct': 0
            }

        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['PnL'] > 0]
        losing_trades = [t for t in self.trades if t['PnL'] <= 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        total_pnl = sum(t['PnL'] for t in self.trades)
        total_return_pct = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100

        avg_win = sum(t['PnL'] for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss = sum(t['PnL'] for t in losing_trades) / loss_count if loss_count > 0 else 0

        total_wins = sum(t['PnL'] for t in winning_trades)
        total_losses = abs(sum(t['PnL'] for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Calculate Sharpe Ratio
        if self.daily_portfolio_value:
            portfolio_df = pd.DataFrame(self.daily_portfolio_value)
            portfolio_df['Returns'] = portfolio_df['Portfolio Value'].pct_change()
            returns = portfolio_df['Returns'].dropna()
            if len(returns) > 0 and returns.std() > 0:
                sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0

        # Max drawdown
        if self.daily_portfolio_value:
            portfolio_values = [x['Portfolio Value'] for x in self.daily_portfolio_value]
            peak = portfolio_values[0]
            max_dd = 0
            for value in portfolio_values:
                if value > peak:
                    peak = value
                dd = ((peak - value) / peak) * 100
                if dd > max_dd:
                    max_dd = dd
        else:
            max_dd = 0

        exit_reasons = {}
        for trade in self.trades:
            reason = trade['Exit Reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

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
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_dd,
            'avg_days_held': avg_days_held,
            'exit_reasons': exit_reasons
        }

    def print_summary(self, results):
        """Print formatted results"""
        print("\n" + "="*80)
        print("MA CROSSOVER 20/50 STRATEGY - BACKTEST RESULTS")
        print("="*80)

        print(f"\n💰 CAPITAL:")
        print(f"   Initial:  ₹{self.initial_capital:,.2f}")
        print(f"   Final:    ₹{self.current_capital:,.2f}")
        print(f"   PnL:      ₹{results['total_pnl']:,.2f}")
        print(f"   Return:   {results['total_return_pct']:.2f}%")

        print(f"\n📈 PERFORMANCE METRICS:")
        print(f"   Total Trades:     {results['total_trades']}")
        print(f"   Win Rate:         {results['win_rate']:.2f}%")
        print(f"   Profit Factor:    {results['profit_factor']:.2f}")
        print(f"   Sharpe Ratio:     {results['sharpe_ratio']:.2f}")
        print(f"   Max Drawdown:     {results['max_drawdown']:.2f}%")
        print(f"   Avg Days Held:    {results['avg_days_held']:.1f}")

        print(f"\n🎯 WIN/LOSS BREAKDOWN:")
        print(f"   Winning Trades:   {results['winning_trades']}")
        print(f"   Losing Trades:    {results['losing_trades']}")
        print(f"   Avg Win:          ₹{results['avg_win']:,.2f}")
        print(f"   Avg Loss:         ₹{results['avg_loss']:,.2f}")

        print(f"\n🚪 EXIT REASONS:")
        for reason, count in results['exit_reasons'].items():
            pct = (count / results['total_trades'] * 100) if results['total_trades'] > 0 else 0
            print(f"   {reason:25s}: {count:3d} ({pct:.1f}%)")

        print("\n" + "="*80)

###############################################################################
# MAIN EXECUTION
###############################################################################

def main():
    """Run MA Crossover strategy"""

    print("=" * 80)
    print("MA CROSSOVER 20/50 STRATEGY")
    print("=" * 80)
    print("Entry: 20 MA crosses ABOVE 50 MA")
    print("Stop Loss: 10%")
    print("Take Profit: 30%")
    print("=" * 80)

    print(f"\n🎯 CONFIGURATION:")
    print(f"   Initial Capital:      ₹{initial_capital:,.2f}")
    print(f"   Max Positions:        {max_positions}")
    print(f"   Capital/Position:     ₹{initial_capital * capital_per_position_pct / 100:,.0f}")
    print(f"   MA Periods:           {ma_short_period}/{ma_long_period}")
    print(f"   Stop Loss:            {stop_loss_pct}%")
    print(f"   Take Profit:          {take_profit_pct}%")

    # Load data
    print("\n" + "="*80)
    print("Loading NIFTY 50 data...")
    loader = DataLoader()
    all_stock_data = loader.load_all_nifty50()

    if not all_stock_data:
        print("❌ No data found! Run: python download_data.py")
        return

    print(f"✓ Loaded {len(all_stock_data)} stocks")

    # Run strategy
    strategy = MACrossoverStrategy()
    results = strategy.backtest(all_stock_data)

    # Print results
    strategy.print_summary(results)

    # Save results
    print("\nSaving results...")
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result_folder = os.path.join(script_dir, "result")
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if strategy.trades:
        trades_df = pd.DataFrame(strategy.trades)
        trades_filename = os.path.join(result_folder, f'ma_20_50_crossover_trades_{timestamp}.csv')
        trades_df.to_csv(trades_filename, index=False)
        print(f"✓ Trades saved: {trades_filename}")

    if strategy.daily_portfolio_value:
        portfolio_df = pd.DataFrame(strategy.daily_portfolio_value)
        portfolio_filename = os.path.join(result_folder, f'ma_20_50_crossover_portfolio_{timestamp}.csv')
        portfolio_df.to_csv(portfolio_filename, index=False)
        print(f"✓ Portfolio saved: {portfolio_filename}")

    print("\n" + "="*80)
    print("✓ BACKTEST COMPLETED!")
    print("="*80)

if __name__ == "__main__":
    main()
