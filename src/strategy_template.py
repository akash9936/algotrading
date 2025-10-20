"""
Strategy Template - Using Centralized Data
===========================================
Template for creating new trading strategies using data from data/ folder.

How to use:
1. Copy this file and rename (e.g., strategy_macd.py, strategy_bollinger.py)
2. Modify the strategy logic in calculate_profit_for_holding_period()
3. Adjust configuration parameters
4. Run your strategy!

The data loading is already handled - focus on strategy logic only.
"""

import pandas as pd
from datetime import timedelta, datetime
import warnings
import os
from utills.load_data import DataLoader
warnings.filterwarnings('ignore')

###############################################################################
# CONFIGURATION PARAMETERS
###############################################################################

# Capital and Investment Settings
initial_investment = 100000  # Starting capital in INR

# YOUR STRATEGY PARAMETERS HERE
# Example:
# moving_average_short = 20
# moving_average_long = 50
# bollinger_bands_period = 20
# macd_fast = 12
# macd_slow = 26

# Risk Management Settings
stop_loss_pct = 0.05  # 5% stop-loss
take_profit_pct = 0.1  # 10% take-profit

# Transaction Cost Settings
transaction_cost = 0.001  # 0.1% transaction cost per trade

###############################################################################
# YOUR INDICATOR CALCULATIONS
###############################################################################

def calculate_your_indicator(data):
    """
    Calculate your custom indicator

    Example for Moving Average:
    data['MA_20'] = data['Close'].rolling(window=20).mean()
    data['MA_50'] = data['Close'].rolling(window=50).mean()

    Example for MACD:
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

    Example for Bollinger Bands:
    data['BB_Middle'] = data['Close'].rolling(window=20).mean()
    data['BB_Std'] = data['Close'].rolling(window=20).std()
    data['BB_Upper'] = data['BB_Middle'] + (data['BB_Std'] * 2)
    data['BB_Lower'] = data['BB_Middle'] - (data['BB_Std'] * 2)
    """

    # TODO: Add your indicator calculations here
    # Example:
    data['MA_20'] = data['Close'].rolling(window=20).mean()
    data['MA_50'] = data['Close'].rolling(window=50).mean()

    return data

###############################################################################
# YOUR STRATEGY LOGIC
###############################################################################

def calculate_profit_for_holding_period(data, holding_period):
    """
    Backtest your trading strategy

    Modify the buy/sell logic below based on your strategy.
    """
    investment = initial_investment
    profit_loss_list = []

    for i in range(len(data) - holding_period):
        current_date = data.index[i]
        buy_price = data['Low'].iloc[i]
        sell_date = current_date + timedelta(days=holding_period)

        ###################################################################
        # YOUR BUY SIGNAL LOGIC HERE
        ###################################################################
        # Example: Buy when short MA crosses above long MA
        # if data['MA_20'].iloc[i] > data['MA_50'].iloc[i]:
        #     should_buy = True

        # Example: Buy when price touches lower Bollinger Band
        # if data['Close'].iloc[i] <= data['BB_Lower'].iloc[i]:
        #     should_buy = True

        # Example: Buy when MACD crosses above signal line
        # if data['MACD'].iloc[i] > data['Signal'].iloc[i]:
        #     should_buy = True

        # TODO: Replace with your buy logic
        should_buy = data['MA_20'].iloc[i] > data['MA_50'].iloc[i]

        if not should_buy:
            continue

        ###################################################################
        # SELL LOGIC (with stop-loss and take-profit)
        ###################################################################
        if sell_date in data.index:
            sell_price = data.loc[sell_date]['Close']

            # Calculate stop-loss and take-profit prices
            stop_loss_price = buy_price * (1 - stop_loss_pct)
            take_profit_price = buy_price * (1 + take_profit_pct)

            # Determine exit reason
            if sell_price <= stop_loss_price:
                sell_price = stop_loss_price
                exit_reason = 'Stop Loss'
            elif sell_price >= take_profit_price:
                sell_price = take_profit_price
                exit_reason = 'Take Profit'
            else:
                exit_reason = 'Holding Period Complete'

            # Calculate profit/loss
            profit_loss = sell_price - buy_price
            trade_cost = (buy_price + sell_price) * transaction_cost
            net_profit_loss = profit_loss - trade_cost
            investment += net_profit_loss

            profit_loss_list.append({
                'Buy Date': current_date,
                'Sell Date': sell_date,
                'Buy Price': buy_price,
                'Sell Price': sell_price,
                'Profit/Loss': net_profit_loss,
                'Return %': (net_profit_loss / buy_price) * 100,
                'Exit Reason': exit_reason,
                'Investment After Trade': investment
            })

    return investment, profit_loss_list

###############################################################################
# TEST SINGLE STOCK (NO CHANGES NEEDED)
###############################################################################

def test_stock(ticker, name, data):
    """Test strategy on a single stock - generally no changes needed here"""

    try:
        if data.empty or len(data) < 50:  # Adjust min data points as needed
            return None, None

        # Calculate your indicators
        data = calculate_your_indicator(data)

        # Check for required columns
        if 'Low' not in data.columns or 'Close' not in data.columns:
            return None, None

        # Test different holding periods (1-30 days)
        best_profit = -float('inf')
        best_holding_period = None
        best_trades = None

        for holding_period in range(1, 31):
            final_investment, profit_loss_list = calculate_profit_for_holding_period(
                data.copy(), holding_period
            )

            if final_investment > best_profit:
                best_profit = final_investment
                best_holding_period = holding_period
                best_trades = profit_loss_list

        # Calculate metrics for best holding period
        total_profit_loss = best_profit - initial_investment
        return_percentage = (total_profit_loss / initial_investment) * 100
        num_trades = len(best_trades) if best_trades else 0

        winning_trades = sum(1 for trade in best_trades if trade['Profit/Loss'] > 0) if best_trades else 0
        win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0

        summary_result = {
            'Ticker': ticker,
            'Name': name,
            'Best Holding Period (days)': best_holding_period,
            'Final Investment': best_profit,
            'Total Profit/Loss': total_profit_loss,
            'Return %': return_percentage,
            'Number of Trades': num_trades,
            'Winning Trades': winning_trades,
            'Win Rate %': win_rate,
        }

        if best_trades:
            for trade in best_trades:
                trade['Ticker'] = ticker
                trade['Name'] = name

        return summary_result, best_trades

    except Exception as e:
        print(f"Error testing {name} ({ticker}): {str(e)}")
        return None, None

###############################################################################
# MAIN EXECUTION (NO CHANGES NEEDED)
###############################################################################

def main():
    """Run strategy on data from data/ folder"""

    print("=" * 80)
    print("YOUR STRATEGY NAME - USING CENTRALIZED DATA")
    print("=" * 80)
    print(f"Initial Investment: ₹{initial_investment:,.2f}")
    print("=" * 80)

    # Load data
    print("\nLoading data from data/ folder...")
    loader = DataLoader()
    all_stock_data = loader.load_all_nifty50()

    if not all_stock_data:
        print("❌ No data found! Run: python download_data.py")
        return

    print(f"✓ Loaded {len(all_stock_data)} stocks\n")

    # Run strategy
    print("Running strategy...")
    print("=" * 80)

    summary_results = []
    all_trades = []

    from indian_stock_tickers import NIFTY_50_STOCKS as STOCK_NAMES

    for idx, (ticker, data) in enumerate(all_stock_data.items(), 1):
        ticker_ns = ticker.replace('_', '.')
        name = STOCK_NAMES.get(ticker_ns, ticker_ns)

        print(f"[{idx}/{len(all_stock_data)}] {name:30}", end=" | ")

        summary, trades = test_stock(ticker_ns, name, data.copy())

        if summary:
            summary_results.append(summary)
            print(f"✓ Return: {summary['Return %']:7.2f}%")
        else:
            print("❌ Failed")

        if trades:
            all_trades.extend(trades)

    # Generate reports
    if summary_results:
        # Create result folder if it doesn't exist
        result_folder = "result"
        if not os.path.exists(result_folder):
            os.makedirs(result_folder)
            print(f"✓ Created folder: {result_folder}/")

        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        summary_df = pd.DataFrame(summary_results)
        summary_df = summary_df.sort_values('Return %', ascending=False)

        summary_filename = os.path.join(result_folder, f'your_strategy_results_{timestamp}.csv')
        summary_df.to_csv(summary_filename, index=False)

        if all_trades:
            trades_df = pd.DataFrame(all_trades)
            trades_filename = os.path.join(result_folder, f'your_strategy_trades_{timestamp}.csv')
            trades_df.to_csv(trades_filename, index=False)

        # Show summary
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"Profitable: {len(summary_df[summary_df['Return %'] > 0])}/{len(summary_df)}")
        print(f"Average Return: {summary_df['Return %'].mean():.2f}%")
        print(f"Best: {summary_df.iloc[0]['Name']} ({summary_df.iloc[0]['Return %']:.2f}%)")
        print(f"Worst: {summary_df.iloc[-1]['Name']} ({summary_df.iloc[-1]['Return %']:.2f}%)")
        print(f"\n✓ Results saved to: {result_folder}/")
        print(f"Timestamp: {timestamp}")

if __name__ == "__main__":
    main()
