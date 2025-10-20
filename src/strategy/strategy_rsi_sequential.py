"""
Sequential RSI Strategy - Single Position at a Time
====================================================
Trades stocks in alphabetical order with ONLY ONE position at a time.
Simulates real-world constraint of limited capital.

Strategy Logic:
- Start with ₹1,00,000 capital
- Scan stocks continuously in alphabetical order
- When capital available: invest ALL money in first stock that meets RSI condition
- While in position: skip all other signals (no capital available)
- After exit: resume scanning from next stock in alphabetical order
- Continue cycling through the list

Prerequisites:
1. Run: python download_data.py (one time to download all data)
2. Run: python strategy_rsi_sequential.py (run strategy!)
"""

import pandas as pd
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

# Technical Indicator Settings
rsi_threshold = 35  # RSI threshold for oversold condition
rsi_period = 14     # RSI calculation period

# Risk Management Settings
stop_loss_pct = 0.03     # 3% stop-loss
take_profit_pct = 0.08   # 8% take-profit
use_trailing_stop = True  # Enable trailing stop-loss
trailing_stop_activation = 0.05  # Activate trailing stop at 5% profit
trailing_stop_distance = 0.03    # Trail 3% below peak

# Transaction Cost Settings
transaction_cost = 0.001  # 0.1% transaction cost per trade

# Data Configuration
start_date = "2023-01-01"
end_date = "2025-12-31"

# Testing Configuration
test_nifty50 = True
test_indices = False

###############################################################################
# TECHNICAL INDICATORS
###############################################################################

def calculate_rsi(data, period=14):
    """Calculate Relative Strength Index (RSI)"""
    delta = data['Close'].diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

###############################################################################
# SEQUENTIAL TRADING STRATEGY
###############################################################################

def run_sequential_strategy(all_stock_data, stock_names):
    """
    Run sequential trading strategy:
    - Only ONE position at a time
    - Scan stocks in alphabetical order continuously
    - Invest ALL capital when signal found
    - Resume from next stock after exit
    """

    # Prepare all stock data with indicators
    print("\n" + "=" * 80)
    print("PREPARING STOCK DATA WITH RSI INDICATORS")
    print("=" * 80)

    stock_data_prepared = {}
    stock_list_sorted = []

    # Convert start_date and end_date to datetime
    date_start = pd.to_datetime(start_date)
    date_end = pd.to_datetime(end_date)

    for ticker, data in all_stock_data.items():
        # Make dates timezone-aware if needed (match stock data timezone)
        if not data.empty and data.index.tzinfo is not None:
            if date_start.tzinfo is None:
                date_start = date_start.tz_localize(data.index.tzinfo)
            if date_end.tzinfo is None:
                date_end = date_end.tz_localize(data.index.tzinfo)
        ticker_ns = ticker.replace('_', '.')
        name = stock_names.get(ticker_ns, ticker_ns)

        if data.empty or len(data) < rsi_period + 20:
            continue

        # Filter data by date range
        data = data[(data.index >= date_start) & (data.index <= date_end)]

        if data.empty or len(data) < rsi_period + 20:
            continue

        # Calculate RSI
        data['RSI'] = calculate_rsi(data, period=rsi_period)

        # Check for required columns
        if 'Low' not in data.columns or 'Close' not in data.columns:
            continue

        stock_data_prepared[ticker_ns] = {
            'name': name,
            'data': data
        }
        stock_list_sorted.append(ticker_ns)

    # Sort stocks alphabetically
    stock_list_sorted.sort()

    print(f"✓ Prepared {len(stock_list_sorted)} stocks for trading")
    print(f"✓ Trading order: {', '.join(stock_list_sorted[:5])}...")

    # Get all unique dates across all stocks
    all_dates = set()
    for ticker in stock_list_sorted:
        all_dates.update(stock_data_prepared[ticker]['data'].index)
    all_dates = sorted(list(all_dates))

    # Filter dates by date range
    all_dates = [d for d in all_dates if date_start <= d <= date_end]

    print(f"✓ Total trading days: {len(all_dates)}")
    print(f"✓ Period: {all_dates[0].date()} to {all_dates[-1].date()}")

    ###########################################################################
    # RUN SEQUENTIAL TRADING SIMULATION
    ###########################################################################

    print("\n" + "=" * 80)
    print("RUNNING SEQUENTIAL TRADING SIMULATION")
    print("=" * 80)

    capital = initial_investment
    in_position = False
    position_info = None
    position_peak_price = None
    last_checked_index = 0  # Track where we left off in alphabetical list

    all_trades = []
    daily_portfolio_value = []

    for date_idx, current_date in enumerate(all_dates):
        current_capital = capital

        ###################################################################
        # CHECK IF IN POSITION - EVALUATE EXIT
        ###################################################################
        if in_position:
            ticker = position_info['ticker']
            stock_data = stock_data_prepared[ticker]['data']

            # Check if this stock has data for current date
            if current_date not in stock_data.index:
                # Stock not trading today, hold position
                daily_portfolio_value.append({
                    'Date': current_date,
                    'Capital': capital,
                    'Position': ticker,
                    'Position Value': position_info['shares'] * position_info['entry_price'],
                    'Total Value': capital
                })
                continue

            current_price = stock_data.loc[current_date, 'Close']
            entry_price = position_info['entry_price']
            shares = position_info['shares']
            days_held = (current_date - position_info['entry_date']).days

            # Update peak price for trailing stop
            if current_price > position_peak_price:
                position_peak_price = current_price

            # Calculate returns
            current_return = (current_price - entry_price) / entry_price
            position_value = shares * current_price

            # Exit conditions
            should_exit = False
            exit_reason = None
            sell_price = current_price

            # Stop loss
            stop_loss_price = entry_price * (1 - stop_loss_pct)
            if current_price <= stop_loss_price:
                sell_price = stop_loss_price
                exit_reason = 'Stop Loss'
                should_exit = True

            # Take profit
            elif current_return >= take_profit_pct:
                exit_reason = 'Take Profit'
                should_exit = True

            # Trailing stop
            elif use_trailing_stop and current_return >= trailing_stop_activation:
                trailing_stop_price = position_peak_price * (1 - trailing_stop_distance)
                if current_price <= trailing_stop_price:
                    sell_price = trailing_stop_price
                    exit_reason = 'Trailing Stop'
                    should_exit = True

            # Execute exit
            if should_exit:
                proceeds = shares * sell_price
                trade_cost = (entry_price * shares + proceeds) * transaction_cost
                net_proceeds = proceeds - trade_cost

                profit_loss = net_proceeds - (shares * entry_price)
                capital = net_proceeds

                trade_record = {
                    'Trade #': len(all_trades) + 1,
                    'Ticker': ticker,
                    'Name': position_info['name'],
                    'Buy Date': position_info['entry_date'],
                    'Sell Date': current_date,
                    'Buy Price': entry_price,
                    'Sell Price': sell_price,
                    'Peak Price': position_peak_price,
                    'Shares': shares,
                    'Investment': shares * entry_price,
                    'Proceeds': net_proceeds,
                    'Profit/Loss': profit_loss,
                    'Return %': (profit_loss / (shares * entry_price)) * 100,
                    'Days Held': days_held,
                    'Exit Reason': exit_reason,
                    'Capital After Trade': capital,
                    'RSI at Buy': position_info['rsi']
                }

                all_trades.append(trade_record)

                print(f"[Trade #{len(all_trades):3d}] EXIT  | {position_info['name']:25} | "
                      f"Return: {trade_record['Return %']:6.2f}% | "
                      f"Days: {days_held:3d} | {exit_reason:20} | "
                      f"Capital: ₹{capital:,.0f}")

                # Reset position
                in_position = False
                position_info = None
                position_peak_price = None

                # Move to next stock in alphabetical order
                current_stock_idx = stock_list_sorted.index(ticker)
                last_checked_index = (current_stock_idx + 1) % len(stock_list_sorted)

            # Record daily portfolio value
            daily_portfolio_value.append({
                'Date': current_date,
                'Capital': capital,
                'Position': ticker if in_position else None,
                'Position Value': position_value if in_position else 0,
                'Total Value': capital if not in_position else position_value
            })

        ###################################################################
        # NOT IN POSITION - SCAN FOR ENTRY
        ###################################################################
        else:
            # Scan stocks in alphabetical order starting from last_checked_index
            signal_found = False
            stocks_checked = 0

            for i in range(len(stock_list_sorted)):
                stock_idx = (last_checked_index + i) % len(stock_list_sorted)
                ticker = stock_list_sorted[stock_idx]
                stock_info = stock_data_prepared[ticker]
                stock_data = stock_info['data']
                name = stock_info['name']

                # Check if this stock has data for current date
                if current_date not in stock_data.index:
                    continue

                stocks_checked += 1

                # Get RSI value
                rsi = stock_data.loc[current_date, 'RSI']

                if pd.isna(rsi):
                    continue

                # Check RSI signal
                if rsi < rsi_threshold:
                    # SIGNAL FOUND - ENTER POSITION
                    entry_price = stock_data.loc[current_date, 'Low']
                    shares = int(capital / entry_price)  # Buy maximum shares

                    if shares == 0:
                        continue

                    investment = shares * entry_price
                    capital = capital - investment  # Should be close to 0

                    position_info = {
                        'ticker': ticker,
                        'name': name,
                        'entry_date': current_date,
                        'entry_price': entry_price,
                        'shares': shares,
                        'rsi': rsi
                    }
                    position_peak_price = entry_price
                    in_position = True
                    signal_found = True

                    print(f"[Trade #{len(all_trades)+1:3d}] ENTER | {name:25} | "
                          f"Price: ₹{entry_price:8.2f} | "
                          f"Shares: {shares:5d} | "
                          f"RSI: {rsi:5.1f} | "
                          f"Investment: ₹{investment:,.0f}")

                    # Update last checked index to next stock
                    last_checked_index = (stock_idx + 1) % len(stock_list_sorted)
                    break

            # Record daily portfolio value
            daily_portfolio_value.append({
                'Date': current_date,
                'Capital': capital,
                'Position': None,
                'Position Value': 0,
                'Total Value': capital
            })

            # If no signal found, continue to next day
            # last_checked_index stays at current position

    ###########################################################################
    # CLOSE ANY REMAINING POSITION
    ###########################################################################
    if in_position:
        ticker = position_info['ticker']
        stock_data = stock_data_prepared[ticker]['data']
        last_date = stock_data.index[-1]
        last_price = stock_data.loc[last_date, 'Close']
        shares = position_info['shares']
        entry_price = position_info['entry_price']

        proceeds = shares * last_price
        trade_cost = (entry_price * shares + proceeds) * transaction_cost
        net_proceeds = proceeds - trade_cost
        profit_loss = net_proceeds - (shares * entry_price)
        capital = net_proceeds
        days_held = (last_date - position_info['entry_date']).days

        trade_record = {
            'Trade #': len(all_trades) + 1,
            'Ticker': ticker,
            'Name': position_info['name'],
            'Buy Date': position_info['entry_date'],
            'Sell Date': last_date,
            'Buy Price': entry_price,
            'Sell Price': last_price,
            'Peak Price': position_peak_price,
            'Shares': shares,
            'Investment': shares * entry_price,
            'Proceeds': net_proceeds,
            'Profit/Loss': profit_loss,
            'Return %': (profit_loss / (shares * entry_price)) * 100,
            'Days Held': days_held,
            'Exit Reason': 'End of Period',
            'Capital After Trade': capital,
            'RSI at Buy': position_info['rsi']
        }

        all_trades.append(trade_record)
        print(f"[Trade #{len(all_trades):3d}] EXIT  | {position_info['name']:25} | "
              f"Return: {trade_record['Return %']:6.2f}% | "
              f"Days: {days_held:3d} | End of Period")

    return capital, all_trades, daily_portfolio_value

###############################################################################
# MAIN EXECUTION
###############################################################################

def main():
    """Run Sequential RSI Strategy"""

    print("=" * 80)
    print("SEQUENTIAL RSI STRATEGY - ONE POSITION AT A TIME")
    print("=" * 80)
    print(f"Initial Investment: ₹{initial_investment:,.2f}")
    print(f"RSI Threshold: {rsi_threshold}")
    print(f"RSI Period: {rsi_period}")
    print(f"Stop Loss: {stop_loss_pct * 100}%")
    print(f"Take Profit: {take_profit_pct * 100}%")
    print(f"Trading Mode: Sequential (Alphabetical Order)")
    print(f"Position Limit: ONE at a time (ALL capital invested)")
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

    # Load indices
    if test_indices:
        print("\nLoading indices...")
        indices = ["^BSESN", "^NSEI", "^NSEBANK"]
        index_data = loader.load_multiple(indices, category="indices")
        if index_data:
            all_stock_data.update(index_data)
            print(f"✓ Loaded {len(index_data)} indices")

    ###########################################################################
    # GET STOCK NAMES
    ###########################################################################
    from indian_stock_tickers import NIFTY_50_STOCKS as STOCK_NAMES

    ###########################################################################
    # RUN SEQUENTIAL STRATEGY
    ###########################################################################

    final_capital, all_trades, daily_portfolio = run_sequential_strategy(
        all_stock_data, STOCK_NAMES
    )

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

    # 1. Trades CSV
    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_filename = os.path.join(result_folder, f'rsi_sequential_trades_{timestamp}.csv')
        trades_df.to_csv(trades_filename, index=False)
        print(f"✓ Generated: {trades_filename}")

    # 2. Daily Portfolio Value CSV
    if daily_portfolio:
        portfolio_df = pd.DataFrame(daily_portfolio)
        portfolio_filename = os.path.join(result_folder, f'rsi_sequential_portfolio_{timestamp}.csv')
        portfolio_df.to_csv(portfolio_filename, index=False)
        print(f"✓ Generated: {portfolio_filename}")

    ###########################################################################
    # STATISTICS
    ###########################################################################

    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)

    total_profit_loss = final_capital - initial_investment
    total_return_pct = (total_profit_loss / initial_investment) * 100

    print(f"Initial Capital: ₹{initial_investment:,.2f}")
    print(f"Final Capital: ₹{final_capital:,.2f}")
    print(f"Total Profit/Loss: ₹{total_profit_loss:,.2f}")
    print(f"Total Return: {total_return_pct:.2f}%")
    print(f"Total Trades: {len(all_trades)}")

    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        winning_trades = len(trades_df[trades_df['Profit/Loss'] > 0])
        losing_trades = len(trades_df[trades_df['Profit/Loss'] < 0])
        win_rate = (winning_trades / len(all_trades)) * 100

        print(f"Winning Trades: {winning_trades}")
        print(f"Losing Trades: {losing_trades}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Average Return per Trade: {trades_df['Return %'].mean():.2f}%")
        print(f"Average Days Held: {trades_df['Days Held'].mean():.1f}")
        print(f"Best Trade: {trades_df['Return %'].max():.2f}%")
        print(f"Worst Trade: {trades_df['Return %'].min():.2f}%")

        # Top 5 trades
        print("\n" + "=" * 80)
        print("TOP 5 TRADES")
        print("=" * 80)
        top_5 = trades_df.nlargest(5, 'Return %')
        for idx, row in top_5.iterrows():
            print(f"{row['Name']:30} | Return: {row['Return %']:7.2f}% | "
                  f"Days: {row['Days Held']:3d} | "
                  f"Entry: {row['Buy Date'].strftime('%Y-%m-%d')} | "
                  f"Exit: {row['Sell Date'].strftime('%Y-%m-%d')}")

        # Bottom 5 trades
        print("\n" + "=" * 80)
        print("BOTTOM 5 TRADES")
        print("=" * 80)
        bottom_5 = trades_df.nsmallest(5, 'Return %')
        for idx, row in bottom_5.iterrows():
            print(f"{row['Name']:30} | Return: {row['Return %']:7.2f}% | "
                  f"Days: {row['Days Held']:3d} | "
                  f"Entry: {row['Buy Date'].strftime('%Y-%m-%d')} | "
                  f"Exit: {row['Sell Date'].strftime('%Y-%m-%d')}")

    print("\n" + "=" * 80)
    print("✓ COMPLETED!")
    print("=" * 80)
    print(f"All CSV files generated in: {result_folder}/")
    print(f"Timestamp: {timestamp}")

if __name__ == "__main__":
    main()
