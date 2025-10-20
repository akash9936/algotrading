"""
Relative Strength Sequential Trading Strategy - Alphabetical Order
===================================================================
Trades one stock at a time in alphabetical order based on RS signals.

Strategy Logic:
1. Start with full capital (₹100,000)
2. Check stocks in alphabetical order for RS signal
3. When RS condition is met, invest ALL capital into that stock
4. Hold position until sell signal (stop-loss, take-profit, or RS drops)
5. After selling, look for next opportunity in alphabetical order
6. Continue from where you left off in the alphabet

This is a concentrated, sequential momentum strategy that maximizes position size
but trades only one stock at a time.

Prerequisites:
1. Run: python download_data.py (one time to download all data)
2. Run: python strategy_relative_strength_sequential.py
"""

import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import warnings
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utills.load_data import DataLoader
warnings.filterwarnings('ignore')

###############################################################################
# CONFIGURATION PARAMETERS
###############################################################################

# Capital and Investment Settings
initial_investment = 100000  # Starting capital in INR (₹1,00,000)

# Relative Strength Strategy Settings
lookback_period = 20        # Period to calculate relative strength (days)
min_rs_threshold = 5.0      # Minimum RS% to enter a position (5% momentum)
exit_rs_threshold = -2.0    # Exit if RS drops below this (-2% momentum)

# Risk Management Settings
stop_loss_pct = 0.07        # 7% stop-loss per position
take_profit_pct = 0.15      # 15% take-profit per position

# Transaction Cost Settings
transaction_cost = 0.001    # 0.1% transaction cost per trade

# Data Configuration (Date filtering for backtest period)
start_date = "2024-01-01"   # Backtest start date
end_date = "2025-12-31"     # Backtest end date
use_date_filter = True      # Enable/disable date filtering

# Testing Configuration
test_nifty50 = True         # Test all NIFTY 50 stocks
test_indices = False        # Test indices

###############################################################################
# RELATIVE STRENGTH CALCULATION
###############################################################################

def calculate_relative_strength(data, period=20):
    """
    Calculate Relative Strength (Price Rate of Change)

    RS = ((Current Price - Price N days ago) / Price N days ago) * 100

    Interpretation:
    - Higher RS: Stock is outperforming (strong momentum)
    - Lower RS: Stock is underperforming (weak momentum)
    """
    rs = ((data['Close'] - data['Close'].shift(period)) / data['Close'].shift(period)) * 100
    return rs

###############################################################################
# SEQUENTIAL PORTFOLIO BACKTESTING
###############################################################################

def backtest_sequential_rs_strategy(all_stock_data):
    """
    Backtest the Sequential RS strategy - one stock at a time in alphabetical order
    """
    # Get sorted list of tickers (alphabetical order)
    sorted_tickers = sorted(all_stock_data.keys())

    # Get common date range across all stocks
    all_dates = None
    for ticker, data in all_stock_data.items():
        if all_dates is None:
            all_dates = set(data.index)
        else:
            all_dates = all_dates.intersection(set(data.index))

    if not all_dates:
        return None, []

    all_dates = sorted(list(all_dates))

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
            return None, []

        print(f"Date filter enabled: {start_date} to {end_date}")

    # Filter to dates with enough history
    valid_dates = [d for d in all_dates if all_dates.index(d) >= lookback_period]

    if not valid_dates:
        return None, []

    print(f"Backtesting from {valid_dates[0].date()} to {valid_dates[-1].date()}...")
    print(f"Total trading days: {len(valid_dates)}")

    # Portfolio state
    cash = initial_investment
    current_position = None  # {'ticker': str, 'shares': int, 'entry_price': float, 'entry_date': date}

    trade_log = []
    portfolio_history = []

    # Track which stock to check next (alphabetical index)
    next_stock_index = 0

    for current_date in valid_dates:
        portfolio_value = cash

        # If we have a position, update its value and check exit conditions
        if current_position:
            ticker = current_position['ticker']

            if ticker in all_stock_data and current_date in all_stock_data[ticker].index:
                current_price = all_stock_data[ticker].loc[current_date]['Close']
                position_value = current_position['shares'] * current_price
                portfolio_value += position_value

                # Calculate returns
                price_change_pct = (current_price - current_position['entry_price']) / current_position['entry_price']

                # Get current RS value
                current_rs = all_stock_data[ticker].loc[current_date]['RS'] if 'RS' in all_stock_data[ticker].columns else None

                sell_reason = None

                # Check exit conditions
                if price_change_pct <= -stop_loss_pct:
                    sell_reason = 'Stop Loss'
                elif price_change_pct >= take_profit_pct:
                    sell_reason = 'Take Profit'
                elif current_rs is not None and current_rs < exit_rs_threshold:
                    sell_reason = 'RS Below Threshold'

                # Execute sell if any exit condition met
                if sell_reason:
                    sell_value = current_position['shares'] * current_price
                    cash = sell_value * (1 - transaction_cost)

                    trade_log.append({
                        'Date': current_date,
                        'Action': 'SELL',
                        'Ticker': ticker,
                        'Reason': sell_reason,
                        'Price': current_price,
                        'Shares': current_position['shares'],
                        'Value': sell_value,
                        'Return %': price_change_pct * 100,
                        'Entry Date': current_position['entry_date'],
                        'Days Held': (current_date - current_position['entry_date']).days,
                        'RS at Exit': current_rs if current_rs is not None else np.nan
                    })

                    # Clear position and reset to search from beginning
                    current_position = None
                    next_stock_index = 0

        # Record portfolio value
        portfolio_history.append({
            'Date': current_date,
            'Portfolio Value': portfolio_value,
            'Cash': cash,
            'Has Position': 1 if current_position else 0,
            'Current Ticker': current_position['ticker'] if current_position else None
        })

        # If no position, look for next buy opportunity (in alphabetical order)
        if not current_position and cash > 0:
            stocks_checked = 0
            found_opportunity = False

            # Check stocks in alphabetical order starting from next_stock_index
            while stocks_checked < len(sorted_tickers) and not found_opportunity:
                ticker = sorted_tickers[next_stock_index]

                # Check if this stock meets RS criteria
                if ticker in all_stock_data and current_date in all_stock_data[ticker].index:
                    stock_data = all_stock_data[ticker]
                    idx = stock_data.index.get_loc(current_date)

                    if idx >= lookback_period and 'RS' in stock_data.columns:
                        rs_value = stock_data['RS'].iloc[idx]

                        # Buy condition: RS above minimum threshold
                        if not pd.isna(rs_value) and rs_value >= min_rs_threshold:
                            buy_price = stock_data['Close'].iloc[idx]

                            # Invest ALL available cash
                            shares = int(cash / (buy_price * (1 + transaction_cost)))

                            if shares > 0:
                                actual_buy_value = shares * buy_price
                                total_cost = actual_buy_value * (1 + transaction_cost)
                                cash -= total_cost

                                current_position = {
                                    'ticker': ticker,
                                    'shares': shares,
                                    'entry_price': buy_price,
                                    'entry_date': current_date
                                }

                                trade_log.append({
                                    'Date': current_date,
                                    'Action': 'BUY',
                                    'Ticker': ticker,
                                    'Reason': 'RS Signal',
                                    'Price': buy_price,
                                    'Shares': shares,
                                    'Value': actual_buy_value,
                                    'RS': rs_value,
                                    'Alphabetical Position': next_stock_index + 1
                                })

                                found_opportunity = True

                # Move to next stock in alphabetical order
                next_stock_index = (next_stock_index + 1) % len(sorted_tickers)
                stocks_checked += 1

    # Final portfolio value
    final_value = cash
    if current_position:
        ticker = current_position['ticker']
        if ticker in all_stock_data and valid_dates[-1] in all_stock_data[ticker].index:
            final_price = all_stock_data[ticker].loc[valid_dates[-1]]['Close']
            final_value += current_position['shares'] * final_price

            # Log final position if still held
            price_change_pct = (final_price - current_position['entry_price']) / current_position['entry_price']
            trade_log.append({
                'Date': valid_dates[-1],
                'Action': 'FINAL POSITION',
                'Ticker': ticker,
                'Reason': 'End of Period',
                'Price': final_price,
                'Shares': current_position['shares'],
                'Value': current_position['shares'] * final_price,
                'Return %': price_change_pct * 100,
                'Entry Date': current_position['entry_date'],
                'Days Held': (valid_dates[-1] - current_position['entry_date']).days
            })

    # Calculate summary statistics
    total_return = final_value - initial_investment
    return_pct = (total_return / initial_investment) * 100

    buy_trades = [t for t in trade_log if t['Action'] == 'BUY']
    sell_trades = [t for t in trade_log if t['Action'] == 'SELL']

    winning_trades = len([t for t in sell_trades if 'Return %' in t and t['Return %'] > 0])
    losing_trades = len([t for t in sell_trades if 'Return %' in t and t['Return %'] <= 0])
    win_rate = (winning_trades / len(sell_trades) * 100) if sell_trades else 0

    # Calculate average holding period
    trades_with_days = [t for t in sell_trades if 'Days Held' in t]
    avg_holding_days = np.mean([t['Days Held'] for t in trades_with_days]) if trades_with_days else 0

    summary = {
        'Strategy': 'Sequential RS (Alphabetical)',
        'Initial Investment': initial_investment,
        'Final Value': final_value,
        'Total Return': total_return,
        'Return %': return_pct,
        'Number of Trades': len(trade_log),
        'Buy Trades': len(buy_trades),
        'Sell Trades': len(sell_trades),
        'Winning Trades': winning_trades,
        'Losing Trades': losing_trades,
        'Win Rate %': win_rate,
        'Avg Holding Days': avg_holding_days,
        'Min RS Threshold': min_rs_threshold,
        'Exit RS Threshold': exit_rs_threshold,
        'Lookback Period': lookback_period,
        'Test Period': f"{valid_dates[0].date()} to {valid_dates[-1].date()}",
        'Trading Days': len(valid_dates)
    }

    return summary, trade_log, portfolio_history

###############################################################################
# MAIN EXECUTION
###############################################################################

def main():
    """Run Sequential RS strategy on data from data/ folder"""

    print("=" * 80)
    print("SEQUENTIAL RELATIVE STRENGTH STRATEGY (ALPHABETICAL ORDER)")
    print("=" * 80)
    print(f"Initial Investment: ₹{initial_investment:,.2f}")
    print(f"Lookback Period: {lookback_period} days")
    print(f"Entry Condition: RS >= {min_rs_threshold}%")
    print(f"Exit Condition: RS < {exit_rs_threshold}%")
    print(f"Stop Loss: {stop_loss_pct * 100}% | Take Profit: {take_profit_pct * 100}%")
    print(f"Trading Mode: ONE STOCK AT A TIME (Full Capital)")
    if use_date_filter:
        print(f"📅 Date Range: {start_date} to {end_date}")
    else:
        print(f"📅 Date Range: All available data")
    print("=" * 80)

    ###########################################################################
    # LOAD DATA FROM data/ FOLDER
    ###########################################################################

    print("\n" + "=" * 80)
    print("LOADING DATA FROM data/ FOLDER")
    print("=" * 80)

    loader = DataLoader()

    # Load NIFTY 50 stocks
    if test_nifty50:
        print("Loading NIFTY 50 stocks...")
        all_stock_data = loader.load_all_nifty50()

        if not all_stock_data:
            print("❌ No NIFTY 50 data found!")
            print("   Run: python download_data.py")
            return

        print(f"✓ Loaded {len(all_stock_data)} NIFTY 50 stocks")
        print(f"Alphabetical order: {', '.join(sorted(list(all_stock_data.keys())[:5]))}...")

    # Load indices
    if test_indices:
        print("\nLoading indices...")
        indices = ["^BSESN", "^NSEI", "^NSEBANK"]
        index_data = loader.load_multiple(indices, category="indices")
        if index_data:
            all_stock_data.update(index_data)
            print(f"✓ Loaded {len(index_data)} indices")

    ###########################################################################
    # CALCULATE RELATIVE STRENGTH FOR ALL STOCKS
    ###########################################################################

    print("\n" + "=" * 80)
    print("CALCULATING RELATIVE STRENGTH")
    print("=" * 80)

    for ticker, data in all_stock_data.items():
        data['RS'] = calculate_relative_strength(data, period=lookback_period)
        all_stock_data[ticker] = data

    print(f"✓ Calculated RS for {len(all_stock_data)} stocks")

    ###########################################################################
    # RUN SEQUENTIAL STRATEGY
    ###########################################################################

    print("\n" + "=" * 80)
    print("RUNNING SEQUENTIAL RS STRATEGY")
    print("=" * 80)

    summary, trade_log, portfolio_history = backtest_sequential_rs_strategy(all_stock_data)

    if not summary:
        print("❌ Could not run strategy - insufficient data")
        return

    ###########################################################################
    # GENERATE REPORTS
    ###########################################################################

    print("\n" + "=" * 80)
    print("GENERATING REPORTS")
    print("=" * 80)

    # Create result folder if it doesn't exist
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result_folder = os.path.join(script_dir, "result")
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)
        print(f"✓ Created folder: {result_folder}/")

    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Summary Results
    summary_df = pd.DataFrame([summary])
    summary_filename = os.path.join(result_folder, f'rs_sequential_summary_{timestamp}.csv')
    summary_df.to_csv(summary_filename, index=False)
    print(f"✓ Generated: {summary_filename}")

    # 2. Trade Log
    if trade_log:
        trades_df = pd.DataFrame(trade_log)
        trades_filename = os.path.join(result_folder, f'rs_sequential_trades_{timestamp}.csv')
        trades_df.to_csv(trades_filename, index=False)
        print(f"✓ Generated: {trades_filename}")

    # 3. Portfolio History
    if portfolio_history:
        history_df = pd.DataFrame(portfolio_history)
        history_filename = os.path.join(result_folder, f'rs_sequential_portfolio_history_{timestamp}.csv')
        history_df.to_csv(history_filename, index=False)
        print(f"✓ Generated: {history_filename}")

    # Display Results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Initial Investment: ₹{summary['Initial Investment']:,.2f}")
    print(f"Final Value: ₹{summary['Final Value']:,.2f}")
    print(f"Total Return: ₹{summary['Total Return']:,.2f}")
    print(f"Return %: {summary['Return %']:.2f}%")
    print(f"Total Trades: {summary['Number of Trades']}")
    print(f"Win Rate: {summary['Win Rate %']:.2f}%")
    print(f"Winning Trades: {summary['Winning Trades']}")
    print(f"Losing Trades: {summary['Losing Trades']}")
    print(f"Avg Holding Period: {summary['Avg Holding Days']:.1f} days")

    # Trade breakdown
    if trade_log:
        buy_trades = [t for t in trade_log if t['Action'] == 'BUY']
        sell_trades = [t for t in trade_log if t['Action'] == 'SELL']

        print("\n" + "=" * 80)
        print("TRADE BREAKDOWN")
        print("=" * 80)
        print(f"Total Buy Trades: {len(buy_trades)}")
        print(f"Total Sell Trades: {len(sell_trades)}")

        if sell_trades:
            sell_reasons = {}
            for trade in sell_trades:
                reason = trade.get('Reason', 'Unknown')
                sell_reasons[reason] = sell_reasons.get(reason, 0) + 1

            print("\nSell Reasons:")
            for reason, count in sell_reasons.items():
                print(f"  {reason}: {count}")

        # Show first few trades
        if buy_trades:
            print("\nFirst 5 Trades:")
            for i, trade in enumerate(buy_trades[:5], 1):
                print(f"  {i}. {trade['Date'].date()} - BUY {trade['Ticker']} @ ₹{trade['Price']:.2f} (RS: {trade.get('RS', 'N/A'):.2f}%)")

    print("\n" + "=" * 80)
    print("✓ COMPLETED!")
    print("=" * 80)
    print(f"All CSV files generated in: {result_folder}/")
    print(f"Timestamp: {timestamp}")

if __name__ == "__main__":
    main()
