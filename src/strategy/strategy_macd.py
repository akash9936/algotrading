"""
MACD (Moving Average Convergence Divergence) Strategy - Using Centralized Data
===============================================================================
Runs MACD-based trading strategy using data from data/ folder.
No downloading - uses pre-downloaded data for ultra-fast execution.

MACD Strategy:
- MACD Line: 12-period EMA - 26-period EMA
- Signal Line: 9-period EMA of MACD Line
- Histogram: MACD Line - Signal Line
- Buy Signal: MACD crosses above Signal (bullish crossover)
- Sell Signal: MACD crosses below Signal (bearish crossover)

Prerequisites:
1. Run: python download_data.py (one time to download all data)
2. Run: python strategy_macd.py (run strategy instantly!)

You can run multiple strategies on the same data without re-downloading.
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

# MACD Strategy Settings
macd_fast = 12          # Fast EMA period
macd_slow = 26          # Slow EMA period
macd_signal = 9         # Signal line EMA period
use_histogram = True    # Use histogram for additional confirmation
histogram_threshold = 0 # Histogram must be > 0 for buy signal
ma_period = 50          # Moving average period for trend filter

# Risk Management Settings (IMPROVED: Better for momentum strategies)
stop_loss_pct = 0.05  # 5% stop-loss
take_profit_pct = 0.20  # 20% take-profit (increased for momentum)
use_trailing_stop = True  # Enable trailing stop-loss
trailing_stop_activation = 0.10  # Activate trailing stop at 10% profit
trailing_stop_distance = 0.05  # Trail 5% below peak

# Filter Settings (NEW: Quality filters)
use_volume_filter = True  # Only trade with volume confirmation
volume_multiplier = 1.5  # Volume must be 1.5x the 20-day average
use_trend_filter = True  # Only trade in uptrends
min_avg_volume = 0  # Minimum average daily volume (0 = disabled)

# Transaction Cost Settings
transaction_cost = 0.001  # 0.1% transaction cost per trade

# Data Configuration
start_date = "2023-01-01"  # Data date range to load
end_date = "2025-12-31"

# Testing Configuration
test_nifty50 = True  # Test all NIFTY 50 stocks
test_indices = False  # Test indices

###############################################################################
# TECHNICAL INDICATORS
###############################################################################

def calculate_macd(data, fast=12, slow=26, signal=9):
    """
    Calculate MACD (Moving Average Convergence Divergence)

    Components:
    - MACD Line: Fast EMA - Slow EMA
    - Signal Line: EMA of MACD Line
    - Histogram: MACD Line - Signal Line

    Interpretation:
    - MACD > Signal: Bullish (upward momentum)
    - MACD < Signal: Bearish (downward momentum)
    - Histogram increasing: Momentum strengthening
    - Histogram decreasing: Momentum weakening
    """
    # Calculate EMAs
    exp1 = data['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = data['Close'].ewm(span=slow, adjust=False).mean()

    # MACD Line
    data['MACD'] = exp1 - exp2

    # Signal Line
    data['MACD_Signal'] = data['MACD'].ewm(span=signal, adjust=False).mean()

    # Histogram
    data['MACD_Histogram'] = data['MACD'] - data['MACD_Signal']

    return data

def calculate_moving_average(data, period=50):
    """Calculate Simple Moving Average"""
    return data['Close'].rolling(window=period).mean()

def calculate_volume_average(data, period=20):
    """Calculate Average Volume"""
    if 'Volume' in data.columns:
        return data['Volume'].rolling(window=period).mean()
    return None

###############################################################################
# BACKTESTING FUNCTION
###############################################################################

def calculate_profit_for_holding_period(data, holding_period):
    """Backtest the MACD-based trading strategy with improved filters and trailing stop"""
    investment = initial_investment
    profit_loss_list = []
    in_position = False
    position_entry_index = None
    buy_date = None
    actual_buy_price = None
    position_peak_price = None

    for i in range(1, len(data) - holding_period):
        current_date = data.index[i]
        current_price = data['Close'].iloc[i]
        buy_price = data['Low'].iloc[i]

        macd_current = data['MACD'].iloc[i]
        signal_current = data['MACD_Signal'].iloc[i]
        histogram_current = data['MACD_Histogram'].iloc[i]

        macd_prev = data['MACD'].iloc[i-1]
        signal_prev = data['MACD_Signal'].iloc[i-1]

        # Skip if any indicator is NaN
        if pd.isna(macd_current) or pd.isna(signal_current) or pd.isna(macd_prev) or pd.isna(signal_prev):
            continue

        # Get volume data if available
        has_volume = 'Volume' in data.columns and 'Volume_MA' in data.columns

        ###################################################################
        # BUY SIGNAL: MACD crosses above Signal (bullish crossover)
        ###################################################################
        if not in_position:
            # Detect bullish crossover
            crossover = (macd_prev <= signal_prev) and (macd_current > signal_current)

            # Additional confirmation: histogram above threshold
            if use_histogram:
                crossover = crossover and (histogram_current > histogram_threshold)

            if not crossover:
                continue

            # Volume filter (NEW)
            if use_volume_filter and has_volume:
                current_volume = data['Volume'].iloc[i]
                avg_volume = data['Volume_MA'].iloc[i]
                if pd.isna(avg_volume) or current_volume < avg_volume * volume_multiplier:
                    continue

            # Trend filter (NEW)
            if use_trend_filter and 'MA' in data.columns:
                ma_value = data['MA'].iloc[i]
                if pd.isna(ma_value) or current_price < ma_value:
                    continue

            # Minimum volume filter
            if min_avg_volume > 0 and has_volume:
                avg_vol = data['Volume_MA'].iloc[i]
                if pd.isna(avg_vol) or avg_vol < min_avg_volume:
                    continue

            # Enter position
            in_position = True
            position_entry_index = i
            buy_date = current_date
            actual_buy_price = buy_price
            position_peak_price = buy_price

        ###################################################################
        # SELL SIGNAL: Check exit conditions
        ###################################################################
        elif in_position:
            # Update peak price for trailing stop
            if current_price > position_peak_price:
                position_peak_price = current_price

            # Check for bearish crossover (MACD crosses below Signal)
            bearish_crossover = (macd_prev >= signal_prev) and (macd_current < signal_current)

            # Calculate how many days we've been in position
            days_in_position = i - position_entry_index
            current_return = (current_price - actual_buy_price) / actual_buy_price

            # Determine if we should exit
            should_exit = False
            sell_price = current_price
            exit_reason = None

            # Calculate stop-loss and take-profit prices
            stop_loss_price = actual_buy_price * (1 - stop_loss_pct)
            take_profit_price = actual_buy_price * (1 + take_profit_pct)

            # Check exit conditions
            if sell_price <= stop_loss_price:
                sell_price = stop_loss_price
                exit_reason = 'Stop Loss'
                should_exit = True
            elif sell_price >= take_profit_price:
                sell_price = min(current_price, take_profit_price)
                exit_reason = 'Take Profit'
                should_exit = True
            elif use_trailing_stop and current_return >= trailing_stop_activation:
                trailing_stop_price = position_peak_price * (1 - trailing_stop_distance)
                if current_price <= trailing_stop_price:
                    sell_price = trailing_stop_price
                    exit_reason = 'Trailing Stop'
                    should_exit = True
            elif bearish_crossover:
                exit_reason = 'MACD Bearish Crossover'
                should_exit = True
            elif days_in_position >= holding_period:
                exit_reason = 'Holding Period Complete'
                should_exit = True

            # Execute exit if conditions met
            if should_exit:
                # Calculate profit/loss
                profit_loss = sell_price - actual_buy_price
                trade_cost = (actual_buy_price + sell_price) * transaction_cost
                net_profit_loss = profit_loss - trade_cost
                investment += net_profit_loss

                profit_loss_list.append({
                    'Buy Date': buy_date,
                    'Sell Date': current_date,
                    'Buy Price': actual_buy_price,
                    'Sell Price': sell_price,
                    'Peak Price': position_peak_price,
                    'MACD at Buy': data['MACD'].iloc[position_entry_index],
                    'Signal at Buy': data['MACD_Signal'].iloc[position_entry_index],
                    'MACD at Sell': macd_current,
                    'Signal at Sell': signal_current,
                    'Histogram at Buy': data['MACD_Histogram'].iloc[position_entry_index],
                    'Histogram at Sell': histogram_current,
                    'Profit/Loss': net_profit_loss,
                    'Return %': (net_profit_loss / actual_buy_price) * 100,
                    'Exit Reason': exit_reason,
                    'Days Held': days_in_position,
                    'Investment After Trade': investment
                })

                # Reset position
                in_position = False
                position_entry_index = None
                buy_date = None
                actual_buy_price = None
                position_peak_price = None

    return investment, profit_loss_list

###############################################################################
# TEST SINGLE STOCK
###############################################################################

def test_stock(ticker, name, data):
    """Test MACD strategy on a single stock"""

    try:
        if data.empty or len(data) < max(macd_slow + macd_signal, ma_period) + 30:
            return None, None, None

        # Calculate MACD
        data = calculate_macd(data, fast=macd_fast, slow=macd_slow, signal=macd_signal)

        # Calculate Moving Average for trend filter
        data['MA'] = calculate_moving_average(data, period=ma_period)

        # Calculate Volume Average
        if 'Volume' in data.columns:
            data['Volume_MA'] = calculate_volume_average(data, period=20)

        # Check for required columns
        if 'Low' not in data.columns or 'Close' not in data.columns:
            return None, None, None

        # Test different holding periods (5-60 days)
        best_profit = -float('inf')
        best_holding_period = None
        best_trades = None
        holding_period_results = []

        for holding_period in range(5, 61):
            final_investment, profit_loss_list = calculate_profit_for_holding_period(
                data.copy(), holding_period
            )

            total_profit_loss = final_investment - initial_investment
            return_percentage = (total_profit_loss / initial_investment) * 100
            num_trades = len(profit_loss_list)

            holding_period_results.append({
                'Ticker': ticker,
                'Name': name,
                'Holding Period': holding_period,
                'Final Investment': final_investment,
                'Total Profit/Loss': total_profit_loss,
                'Return %': return_percentage,
                'Number of Trades': num_trades,
                'Avg Profit per Trade': total_profit_loss / num_trades if num_trades > 0 else 0
            })

            if final_investment > best_profit:
                best_profit = final_investment
                best_holding_period = holding_period
                best_trades = profit_loss_list

        # Calculate metrics for best holding period
        total_profit_loss = best_profit - initial_investment
        return_percentage = (total_profit_loss / initial_investment) * 100
        num_trades = len(best_trades) if best_trades else 0

        winning_trades = sum(1 for trade in best_trades if trade['Profit/Loss'] > 0) if best_trades else 0
        losing_trades = num_trades - winning_trades
        win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0

        # Calculate average days held
        avg_days_held = sum(trade['Days Held'] for trade in best_trades) / num_trades if num_trades > 0 else 0

        summary_result = {
            'Ticker': ticker,
            'Name': name,
            'Best Holding Period (days)': best_holding_period,
            'Initial Investment': initial_investment,
            'Final Investment': best_profit,
            'Total Profit/Loss': total_profit_loss,
            'Return %': return_percentage,
            'Number of Trades': num_trades,
            'Winning Trades': winning_trades,
            'Losing Trades': losing_trades,
            'Win Rate %': win_rate,
            'Avg Days Held': avg_days_held,
            'Avg Profit per Trade': total_profit_loss / num_trades if num_trades > 0 else 0,
            'Data Points': len(data),
            'Test Period': f"{data.index[0].date()} to {data.index[-1].date()}"
        }

        if best_trades:
            for trade in best_trades:
                trade['Ticker'] = ticker
                trade['Name'] = name
                trade['Holding Period'] = best_holding_period

        return summary_result, best_trades, holding_period_results

    except Exception as e:
        print(f"Error testing {name} ({ticker}): {str(e)}")
        return None, None, None

###############################################################################
# MAIN EXECUTION
###############################################################################

def main():
    """Run MACD strategy on data from data/ folder"""

    print("=" * 80)
    print("MACD (MOVING AVERAGE CONVERGENCE DIVERGENCE) STRATEGY")
    print("=" * 80)
    print(f"Initial Investment: ₹{initial_investment:,.2f}")
    print(f"MACD Fast: {macd_fast} | Slow: {macd_slow} | Signal: {macd_signal}")
    print(f"Use Histogram: {use_histogram} | Threshold: {histogram_threshold}")
    print(f"Stop Loss: {stop_loss_pct * 100}% | Take Profit: {take_profit_pct * 100}%")
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
    # RUN STRATEGY
    ###########################################################################

    print("\n" + "=" * 80)
    print("RUNNING MACD STRATEGY")
    print("=" * 80)

    summary_results = []
    all_trades = []
    all_holding_period_results = []

    # Get stock names (best effort)
    from indian_stock_tickers import NIFTY_50_STOCKS as STOCK_NAMES

    for idx, (ticker, data) in enumerate(all_stock_data.items(), 1):
        # Convert ticker format back for name lookup
        ticker_ns = ticker.replace('_', '.')
        name = STOCK_NAMES.get(ticker_ns, ticker_ns)

        print(f"[{idx}/{len(all_stock_data)}] {name:30} ({ticker_ns:15})", end=" | ")

        summary, trades, holding_results = test_stock(ticker_ns, name, data.copy())

        if summary:
            summary_results.append(summary)
            print(f"✓ Return: {summary['Return %']:7.2f}%")
        else:
            print("❌ Failed")

        if trades:
            all_trades.extend(trades)

        if holding_results:
            all_holding_period_results.extend(holding_results)

    ###########################################################################
    # GENERATE REPORTS
    ###########################################################################

    if summary_results:
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

        # 1. Summary Results CSV
        summary_df = pd.DataFrame(summary_results)
        summary_df = summary_df.sort_values('Return %', ascending=False)
        summary_filename = os.path.join(result_folder, f'macd_strategy_results_{timestamp}.csv')
        summary_df.to_csv(summary_filename, index=False)
        print(f"✓ Generated: {summary_filename}")

        # 2. Detailed Trades CSV
        if all_trades:
            trades_df = pd.DataFrame(all_trades)
            trades_df = trades_df.sort_values(['Ticker', 'Buy Date'])
            trades_filename = os.path.join(result_folder, f'macd_strategy_trades_{timestamp}.csv')
            trades_df.to_csv(trades_filename, index=False)
            print(f"✓ Generated: {trades_filename}")

        # 3. Holding Period Analysis CSV
        if all_holding_period_results:
            holding_df = pd.DataFrame(all_holding_period_results)
            holding_filename = os.path.join(result_folder, f'macd_strategy_holding_analysis_{timestamp}.csv')
            holding_df.to_csv(holding_filename, index=False)
            print(f"✓ Generated: {holding_filename}")

        # Statistics
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)
        print(f"Total Stocks Tested: {len(summary_df)}")
        print(f"Profitable Stocks: {len(summary_df[summary_df['Return %'] > 0])}")
        print(f"Loss-Making Stocks: {len(summary_df[summary_df['Return %'] < 0])}")
        print(f"Average Return: {summary_df['Return %'].mean():.2f}%")
        print(f"Median Return: {summary_df['Return %'].median():.2f}%")
        print(f"Best Performer: {summary_df.iloc[0]['Name']} ({summary_df.iloc[0]['Return %']:.2f}%)")
        print(f"Worst Performer: {summary_df.iloc[-1]['Name']} ({summary_df.iloc[-1]['Return %']:.2f}%)")
        print(f"Total Trades Executed: {len(all_trades)}")
        print(f"Average Win Rate: {summary_df['Win Rate %'].mean():.2f}%")
        print(f"Average Days Held: {summary_df['Avg Days Held'].mean():.2f}")

        # Top and Bottom Performers
        print("\n" + "=" * 80)
        print("TOP 5 PERFORMERS")
        print("=" * 80)
        top_5 = summary_df.head(5)
        for idx, row in top_5.iterrows():
            print(f"{row['Name']:30} | Return: {row['Return %']:7.2f}% | Period: {row['Best Holding Period (days)']:2.0f} days | Win Rate: {row['Win Rate %']:5.1f}%")

        print("\n" + "=" * 80)
        print("BOTTOM 5 PERFORMERS")
        print("=" * 80)
        bottom_5 = summary_df.tail(5)
        for idx, row in bottom_5.iterrows():
            print(f"{row['Name']:30} | Return: {row['Return %']:7.2f}% | Period: {row['Best Holding Period (days)']:2.0f} days | Win Rate: {row['Win Rate %']:5.1f}%")

        print("\n" + "=" * 80)
        print("✓ COMPLETED!")
        print("=" * 80)
        print(f"All CSV files generated in: {result_folder}/")
        print(f"Timestamp: {timestamp}")

    else:
        print("\n❌ No results generated.")

if __name__ == "__main__":
    main()
