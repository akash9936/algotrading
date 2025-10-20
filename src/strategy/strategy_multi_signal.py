"""
Multi-Signal Combined Strategy - Using Centralized Data
=========================================================
Combines RSI, MACD, and ROC signals for higher conviction trades.
Uses pre-downloaded data for ultra-fast execution.

Strategy Logic:
- STRONG BUY: RSI oversold + MACD bullish crossover (mean-reversion + momentum)
- MOMENTUM BUY: ROC > threshold + MACD bullish (pure momentum)
- Skip trades with conflicting signals

Benefits:
- Higher win rate through signal confirmation
- Fewer but higher quality trades
- Better risk-adjusted returns

Prerequisites:
1. Run: python download_data.py (one time to download all data)
2. Run: python strategy_multi_signal.py (run strategy instantly!)
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

# Multi-Signal Settings
require_both_signals = True  # Require both RSI + MACD for entry
rsi_threshold = 35          # RSI oversold threshold
roc_threshold = 2           # ROC momentum threshold
ma_period = 50              # Trend filter period

# Technical Indicator Periods
rsi_period = 14
macd_fast = 12
macd_slow = 26
macd_signal = 9
roc_period = 10

# Risk Management Settings (IMPROVED: Higher targets for high-conviction trades)
stop_loss_pct = 0.04        # 4% stop-loss
take_profit_pct = 0.1      # 8% take-profit (realistic target)
use_trailing_stop = True    # Enable trailing stop-loss
trailing_stop_activation = 0.05  # Activate trailing stop at 5% profit
trailing_stop_distance = 0.03    # Trail 3% below peak

# Filter Settings
use_volume_filter = False   # Only trade with volume confirmation
volume_multiplier = 1.5     # Volume must be 1.5x the 20-day average
use_trend_filter = False    # Only trade in uptrends
min_avg_volume = 0          # Minimum average daily volume (0 = disabled)

# Transaction Cost Settings
transaction_cost = 0.001    # 0.1% transaction cost per trade

# Data Configuration
start_date = "2024-01-01"
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

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calculate MACD indicators"""
    exp1 = data['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = data['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_histogram = macd - macd_signal
    return macd, macd_signal, macd_histogram

def calculate_roc(data, period=10):
    """Calculate Rate of Change (ROC)"""
    roc = ((data['Close'] - data['Close'].shift(period)) / data['Close'].shift(period)) * 100
    return roc

def calculate_moving_average(data, period=50):
    """Calculate Simple Moving Average"""
    return data['Close'].rolling(window=period).mean()

def calculate_volume_average(data, period=20):
    """Calculate Average Volume"""
    if 'Volume' in data.columns:
        return data['Volume'].rolling(window=period).mean()
    return None

###############################################################################
# SIGNAL DETECTION
###############################################################################

def detect_signals(data, i):
    """
    Detect trading signals from multiple indicators

    Returns:
    - signal_type: 'STRONG_BUY', 'MOMENTUM_BUY', 'NONE'
    - signal_strength: 0-100 (confidence level)
    - signals_dict: Individual signal states
    """
    signals = {
        'rsi_oversold': False,
        'macd_bullish': False,
        'roc_positive': False,
        'volume_confirmed': False,
        'trend_confirmed': False
    }

    # Check if we have enough data
    if i == 0 or pd.isna(data['RSI'].iloc[i]) or pd.isna(data['MACD'].iloc[i]):
        return 'NONE', 0, signals

    # RSI Signal
    if data['RSI'].iloc[i] < rsi_threshold:
        signals['rsi_oversold'] = True

    # MACD Bullish Crossover
    macd_current = data['MACD'].iloc[i]
    signal_current = data['MACD_Signal'].iloc[i]
    macd_prev = data['MACD'].iloc[i-1]
    signal_prev = data['MACD_Signal'].iloc[i-1]

    if (macd_prev <= signal_prev) and (macd_current > signal_current):
        signals['macd_bullish'] = True

    # ROC Positive Momentum
    if not pd.isna(data['ROC'].iloc[i]) and data['ROC'].iloc[i] > roc_threshold:
        signals['roc_positive'] = True

    # Volume Confirmation
    if use_volume_filter and 'Volume' in data.columns and 'Volume_MA' in data.columns:
        current_volume = data['Volume'].iloc[i]
        avg_volume = data['Volume_MA'].iloc[i]
        if not pd.isna(avg_volume) and current_volume >= avg_volume * volume_multiplier:
            signals['volume_confirmed'] = True
    else:
        signals['volume_confirmed'] = True  # No volume data, skip this filter

    # Trend Confirmation
    if use_trend_filter and 'MA' in data.columns:
        ma_value = data['MA'].iloc[i]
        if not pd.isna(ma_value) and data['Close'].iloc[i] >= ma_value:
            signals['trend_confirmed'] = True
    else:
        signals['trend_confirmed'] = True

    # Determine signal type and strength
    signal_strength = 0
    signal_type = 'NONE'

    # STRONG BUY: RSI oversold + MACD bullish + filters
    if signals['rsi_oversold'] and signals['macd_bullish']:
        if signals['volume_confirmed'] and signals['trend_confirmed']:
            signal_type = 'STRONG_BUY'
            signal_strength = 90
            if signals['roc_positive']:
                signal_strength = 100  # Perfect confluence

    # MOMENTUM BUY: ROC + MACD (no RSI required)
    elif signals['roc_positive'] and signals['macd_bullish']:
        if signals['volume_confirmed'] and signals['trend_confirmed']:
            signal_type = 'MOMENTUM_BUY'
            signal_strength = 75

    # MODERATE BUY: Either RSI or MACD with filters
    elif (signals['rsi_oversold'] or signals['macd_bullish']):
        if signals['volume_confirmed'] and signals['trend_confirmed']:
            if not require_both_signals:
                signal_type = 'MODERATE_BUY'
                signal_strength = 60

    return signal_type, signal_strength, signals

###############################################################################
# BACKTESTING FUNCTION
###############################################################################

def calculate_profit_for_holding_period(data, holding_period):
    """Backtest the multi-signal strategy"""
    investment = initial_investment
    profit_loss_list = []
    in_position = False
    position_entry = None
    position_peak_price = None

    for i in range(1, len(data) - holding_period):
        current_date = data.index[i]
        current_price = data['Close'].iloc[i]
        buy_price = data['Low'].iloc[i]

        ###################################################################
        # ENTRY LOGIC: Multi-signal confirmation
        ###################################################################
        if not in_position:
            signal_type, signal_strength, signals = detect_signals(data, i)

            if signal_type in ['STRONG_BUY', 'MOMENTUM_BUY']:
                # Enter position
                in_position = True
                position_entry = {
                    'index': i,
                    'date': current_date,
                    'price': buy_price,
                    'signal_type': signal_type,
                    'signal_strength': signal_strength,
                    'rsi': data['RSI'].iloc[i],
                    'macd': data['MACD'].iloc[i],
                    'roc': data['ROC'].iloc[i]
                }
                position_peak_price = buy_price

        ###################################################################
        # EXIT LOGIC: Trailing stop and targets
        ###################################################################
        elif in_position:
            days_held = i - position_entry['index']
            entry_price = position_entry['price']

            # Update peak price for trailing stop
            if current_price > position_peak_price:
                position_peak_price = current_price

            # Calculate returns
            current_return = (current_price - entry_price) / entry_price

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
                take_profit_price = entry_price * (1 + take_profit_pct)
                sell_price = min(current_price, take_profit_price)
                exit_reason = 'Take Profit'
                should_exit = True

            # Trailing stop
            elif use_trailing_stop and current_return >= trailing_stop_activation:
                trailing_stop_price = position_peak_price * (1 - trailing_stop_distance)
                if current_price <= trailing_stop_price:
                    sell_price = trailing_stop_price
                    exit_reason = 'Trailing Stop'
                    should_exit = True

            # Check for bearish signals (early exit)
            elif not pd.isna(data['MACD'].iloc[i]) and not pd.isna(data['MACD_Signal'].iloc[i]):
                macd_current = data['MACD'].iloc[i]
                signal_current = data['MACD_Signal'].iloc[i]
                macd_prev = data['MACD'].iloc[i-1]
                signal_prev = data['MACD_Signal'].iloc[i-1]

                # MACD bearish crossover
                if (macd_prev >= signal_prev) and (macd_current < signal_current):
                    exit_reason = 'MACD Bearish Crossover'
                    should_exit = True

            # Holding period complete
            if days_held >= holding_period and not should_exit:
                exit_reason = 'Holding Period Complete'
                should_exit = True

            # Execute exit
            if should_exit:
                profit_loss = sell_price - entry_price
                trade_cost = (entry_price + sell_price) * transaction_cost
                net_profit_loss = profit_loss - trade_cost
                investment += net_profit_loss

                profit_loss_list.append({
                    'Buy Date': position_entry['date'],
                    'Sell Date': current_date,
                    'Buy Price': entry_price,
                    'Sell Price': sell_price,
                    'Peak Price': position_peak_price,
                    'Signal Type': position_entry['signal_type'],
                    'Signal Strength': position_entry['signal_strength'],
                    'RSI at Buy': position_entry['rsi'],
                    'MACD at Buy': position_entry['macd'],
                    'ROC at Buy': position_entry['roc'],
                    'Profit/Loss': net_profit_loss,
                    'Return %': (net_profit_loss / entry_price) * 100,
                    'Days Held': days_held,
                    'Exit Reason': exit_reason,
                    'Investment After Trade': investment
                })

                # Reset position
                in_position = False
                position_entry = None
                position_peak_price = None

    return investment, profit_loss_list

###############################################################################
# TEST SINGLE STOCK
###############################################################################

def test_stock(ticker, name, data):
    """Test multi-signal strategy on a single stock"""

    try:
        min_data_points = max(rsi_period, macd_slow + macd_signal, ma_period, roc_period) + 30
        if data.empty or len(data) < min_data_points:
            return None, None, None

        # Calculate all indicators
        data['RSI'] = calculate_rsi(data, period=rsi_period)
        data['MACD'], data['MACD_Signal'], data['MACD_Histogram'] = calculate_macd(
            data, fast=macd_fast, slow=macd_slow, signal=macd_signal
        )
        data['ROC'] = calculate_roc(data, period=roc_period)
        data['MA'] = calculate_moving_average(data, period=ma_period)

        if 'Volume' in data.columns:
            data['Volume_MA'] = calculate_volume_average(data, period=20)

        # Check for required columns
        if 'Low' not in data.columns or 'Close' not in data.columns:
            return None, None, None

        # Test different holding periods (1-30 days)
        best_profit = -float('inf')
        best_holding_period = None
        best_trades = None
        holding_period_results = []

        for holding_period in range(1, 31):
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

        # Calculate signal type distribution
        signal_counts = {}
        if best_trades:
            for trade in best_trades:
                sig_type = trade.get('Signal Type', 'UNKNOWN')
                signal_counts[sig_type] = signal_counts.get(sig_type, 0) + 1

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
            'Avg Profit per Trade': total_profit_loss / num_trades if num_trades > 0 else 0,
            'Strong Buy Signals': signal_counts.get('STRONG_BUY', 0),
            'Momentum Buy Signals': signal_counts.get('MOMENTUM_BUY', 0),
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
    """Run multi-signal strategy on data from data/ folder"""

    print("=" * 80)
    print("MULTI-SIGNAL COMBINED STRATEGY (RSI + MACD + ROC)")
    print("=" * 80)
    print(f"Initial Investment: ₹{initial_investment:,.2f}")
    print(f"Signals: RSI({rsi_period}) + MACD({macd_fast},{macd_slow},{macd_signal}) + ROC({roc_period})")
    print(f"Require Both Signals: {require_both_signals}")
    print(f"Stop Loss: {stop_loss_pct * 100}% | Take Profit: {take_profit_pct * 100}%")
    print(f"Trailing Stop: {use_trailing_stop} (Activate: {trailing_stop_activation*100}%, Trail: {trailing_stop_distance*100}%)")
    print(f"Volume Filter: {use_volume_filter} | Trend Filter: {use_trend_filter}")
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
    print("RUNNING MULTI-SIGNAL STRATEGY")
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
            print(f"✓ Return: {summary['Return %']:7.2f}% | Trades: {summary['Number of Trades']:3d}")
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
        summary_filename = os.path.join(result_folder, f'multi_signal_strategy_results_{timestamp}.csv')
        summary_df.to_csv(summary_filename, index=False)
        print(f"✓ Generated: {summary_filename}")

        # 2. Detailed Trades CSV
        if all_trades:
            trades_df = pd.DataFrame(all_trades)
            trades_df = trades_df.sort_values(['Ticker', 'Buy Date'])
            trades_filename = os.path.join(result_folder, f'multi_signal_strategy_trades_{timestamp}.csv')
            trades_df.to_csv(trades_filename, index=False)
            print(f"✓ Generated: {trades_filename}")

        # 3. Holding Period Analysis CSV
        if all_holding_period_results:
            holding_df = pd.DataFrame(all_holding_period_results)
            holding_filename = os.path.join(result_folder, f'multi_signal_strategy_holding_analysis_{timestamp}.csv')
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

        # Signal distribution
        if all_trades:
            trades_df = pd.DataFrame(all_trades)
            print(f"\nSignal Distribution:")
            print(f"  Strong Buy (RSI+MACD): {len(trades_df[trades_df['Signal Type'] == 'STRONG_BUY'])}")
            print(f"  Momentum Buy (ROC+MACD): {len(trades_df[trades_df['Signal Type'] == 'MOMENTUM_BUY'])}")

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
