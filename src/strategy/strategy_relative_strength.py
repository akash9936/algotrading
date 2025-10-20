"""
Relative Strength Ranking Strategy - Using Centralized Data
============================================================
Runs Relative Strength-based trading strategy using data from data/ folder.
No downloading - uses pre-downloaded data for ultra-fast execution.

Relative Strength Strategy:
- Ranks all stocks based on their performance over a lookback period
- Buys top N performing stocks (highest relative strength)
- Rebalances portfolio periodically
- Relative Strength = (Current Price - Price N days ago) / Price N days ago * 100

This is a momentum/rotation strategy that favors strong performers.

Prerequisites:
1. Run: python download_data.py (one time to download all data)
2. Run: python strategy_relative_strength.py (run strategy instantly!)

You can run multiple strategies on the same data without re-downloading.
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
top_n_stocks = 5            # Number of top stocks to hold in portfolio
rebalance_period = 10       # Days between portfolio rebalancing
min_rs_threshold = 0        # Minimum RS% to consider (avoid negative momentum)

# Alternative: Use percentile ranking instead of top N
use_percentile = False      # If True, use percentile_threshold instead of top_n
percentile_threshold = 80   # Only buy stocks in top 20% (80th percentile and above)

# Risk Management Settings
stop_loss_pct = 0.07        # 7% stop-loss per position
take_profit_pct = 0.15      # 15% take-profit per position
max_position_size = 0.25    # Maximum 25% of portfolio per stock

# Transaction Cost Settings
transaction_cost = 0.001    # 0.1% transaction cost per trade

# Data Configuration
start_date = "2023-01-01"   # Data date range to load
end_date = "2025-12-31"

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

def rank_stocks_by_relative_strength(all_data, current_date, lookback):
    """
    Rank all stocks by their relative strength on a given date
    Returns: DataFrame with ticker, RS value, and rank
    """
    rs_scores = []

    for ticker, data in all_data.items():
        if current_date in data.index:
            idx = data.index.get_loc(current_date)
            if idx >= lookback and 'RS' in data.columns:
                rs_value = data['RS'].iloc[idx]
                if not pd.isna(rs_value) and rs_value >= min_rs_threshold:
                    rs_scores.append({
                        'Ticker': ticker,
                        'RS': rs_value,
                        'Close': data['Close'].iloc[idx]
                    })

    # Create DataFrame and rank
    rs_df = pd.DataFrame(rs_scores)
    if not rs_df.empty:
        rs_df = rs_df.sort_values('RS', ascending=False)
        rs_df['Rank'] = range(1, len(rs_df) + 1)

        # Calculate percentile
        rs_df['Percentile'] = rs_df['RS'].rank(pct=True) * 100

    return rs_df

###############################################################################
# PORTFOLIO BACKTESTING
###############################################################################

def backtest_relative_strength_portfolio(all_stock_data):
    """
    Backtest the Relative Strength portfolio strategy
    """
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

    # Filter to dates with enough history
    valid_dates = [d for d in all_dates if all_dates.index(d) >= lookback_period]

    if len(valid_dates) < rebalance_period:
        return None, []

    # Portfolio state
    portfolio_value = initial_investment
    cash = initial_investment
    positions = {}  # {ticker: {'shares': N, 'entry_price': P}}

    trade_log = []
    portfolio_history = []

    # Rebalance dates
    rebalance_dates = valid_dates[::rebalance_period]

    for date_idx, current_date in enumerate(valid_dates):
        # Calculate current portfolio value
        portfolio_value = cash
        tickers_to_remove = []  # Track positions to close

        for ticker, position in positions.items():
            if ticker in all_stock_data and current_date in all_stock_data[ticker].index:
                current_price = all_stock_data[ticker].loc[current_date]['Close']
                position_value = position['shares'] * current_price
                portfolio_value += position_value

                # Check stop-loss and take-profit
                price_change_pct = (current_price - position['entry_price']) / position['entry_price']

                if price_change_pct <= -stop_loss_pct:
                    # Stop loss hit - sell position
                    sell_value = position['shares'] * current_price
                    cash += sell_value * (1 - transaction_cost)

                    trade_log.append({
                        'Date': current_date,
                        'Action': 'SELL',
                        'Ticker': ticker,
                        'Reason': 'Stop Loss',
                        'Price': current_price,
                        'Shares': position['shares'],
                        'Value': sell_value,
                        'Return %': price_change_pct * 100
                    })

                    tickers_to_remove.append(ticker)

                elif price_change_pct >= take_profit_pct:
                    # Take profit hit - sell position
                    sell_value = position['shares'] * current_price
                    cash += sell_value * (1 - transaction_cost)

                    trade_log.append({
                        'Date': current_date,
                        'Action': 'SELL',
                        'Ticker': ticker,
                        'Reason': 'Take Profit',
                        'Price': current_price,
                        'Shares': position['shares'],
                        'Value': sell_value,
                        'Return %': price_change_pct * 100
                    })

                    tickers_to_remove.append(ticker)

        # Remove closed positions after iteration
        for ticker in tickers_to_remove:
            del positions[ticker]

        # Record portfolio value
        portfolio_history.append({
            'Date': current_date,
            'Portfolio Value': portfolio_value,
            'Cash': cash,
            'Positions': len(positions)
        })

        # Rebalance portfolio on rebalance dates
        if current_date in rebalance_dates:
            # Rank stocks by relative strength
            rs_ranking = rank_stocks_by_relative_strength(all_stock_data, current_date, lookback_period)

            if rs_ranking.empty:
                continue

            # Determine which stocks to hold
            if use_percentile:
                stocks_to_hold = rs_ranking[rs_ranking['Percentile'] >= percentile_threshold]['Ticker'].tolist()
            else:
                stocks_to_hold = rs_ranking.head(top_n_stocks)['Ticker'].tolist()

            # Sell positions not in top stocks
            tickers_to_sell = [t for t in positions.keys() if t not in stocks_to_hold]
            for ticker in tickers_to_sell:
                if ticker in all_stock_data and current_date in all_stock_data[ticker].index:
                    current_price = all_stock_data[ticker].loc[current_date]['Close']
                    sell_value = positions[ticker]['shares'] * current_price
                    cash += sell_value * (1 - transaction_cost)

                    price_change_pct = (current_price - positions[ticker]['entry_price']) / positions[ticker]['entry_price']

                    trade_log.append({
                        'Date': current_date,
                        'Action': 'SELL',
                        'Ticker': ticker,
                        'Reason': 'Rebalance',
                        'Price': current_price,
                        'Shares': positions[ticker]['shares'],
                        'Value': sell_value,
                        'Return %': price_change_pct * 100
                    })

                    del positions[ticker]

            # Buy new positions
            stocks_to_buy = [t for t in stocks_to_hold if t not in positions.keys()]

            if stocks_to_buy:
                # Equal weight allocation
                allocation_per_stock = min(portfolio_value / len(stocks_to_buy), portfolio_value * max_position_size)

                for ticker in stocks_to_buy:
                    if cash < allocation_per_stock:
                        break

                    if ticker in all_stock_data and current_date in all_stock_data[ticker].index:
                        buy_price = all_stock_data[ticker].loc[current_date]['Close']
                        buy_value = min(allocation_per_stock, cash)
                        shares = int(buy_value / buy_price)

                        if shares > 0:
                            actual_buy_value = shares * buy_price
                            cash -= actual_buy_value * (1 + transaction_cost)

                            positions[ticker] = {
                                'shares': shares,
                                'entry_price': buy_price
                            }

                            rs_value = rs_ranking[rs_ranking['Ticker'] == ticker]['RS'].values[0]
                            rank = rs_ranking[rs_ranking['Ticker'] == ticker]['Rank'].values[0]

                            trade_log.append({
                                'Date': current_date,
                                'Action': 'BUY',
                                'Ticker': ticker,
                                'Reason': 'Rebalance',
                                'Price': buy_price,
                                'Shares': shares,
                                'Value': actual_buy_value,
                                'RS': rs_value,
                                'Rank': rank
                            })

    # Final portfolio value
    final_value = cash
    for ticker, position in positions.items():
        if ticker in all_stock_data and valid_dates[-1] in all_stock_data[ticker].index:
            final_price = all_stock_data[ticker].loc[valid_dates[-1]]['Close']
            final_value += position['shares'] * final_price

    # Calculate summary statistics
    total_return = final_value - initial_investment
    return_pct = (total_return / initial_investment) * 100

    num_trades = len(trade_log)
    buy_trades = [t for t in trade_log if t['Action'] == 'BUY']
    sell_trades = [t for t in trade_log if t['Action'] == 'SELL']

    winning_trades = len([t for t in sell_trades if 'Return %' in t and t['Return %'] > 0])
    losing_trades = len([t for t in sell_trades if 'Return %' in t and t['Return %'] <= 0])
    win_rate = (winning_trades / len(sell_trades) * 100) if sell_trades else 0

    summary = {
        'Strategy': 'Relative Strength Ranking',
        'Initial Investment': initial_investment,
        'Final Value': final_value,
        'Total Return': total_return,
        'Return %': return_pct,
        'Number of Trades': num_trades,
        'Buy Trades': len(buy_trades),
        'Sell Trades': len(sell_trades),
        'Winning Trades': winning_trades,
        'Losing Trades': losing_trades,
        'Win Rate %': win_rate,
        'Lookback Period': lookback_period,
        'Rebalance Period': rebalance_period,
        'Top N Stocks': top_n_stocks if not use_percentile else f"Top {100-percentile_threshold}%",
        'Test Period': f"{valid_dates[0].date()} to {valid_dates[-1].date()}",
        'Trading Days': len(valid_dates)
    }

    return summary, trade_log, portfolio_history

###############################################################################
# MAIN EXECUTION
###############################################################################

def main():
    """Run Relative Strength strategy on data from data/ folder"""

    print("=" * 80)
    print("RELATIVE STRENGTH RANKING STRATEGY")
    print("=" * 80)
    print(f"Initial Investment: ₹{initial_investment:,.2f}")
    print(f"Lookback Period: {lookback_period} days")
    print(f"Rebalance Period: {rebalance_period} days")
    if use_percentile:
        print(f"Selection: Top {100-percentile_threshold}% (Percentile >= {percentile_threshold})")
    else:
        print(f"Portfolio Size: Top {top_n_stocks} stocks")
    print(f"Stop Loss: {stop_loss_pct * 100}% | Take Profit: {take_profit_pct * 100}%")
    print(f"Max Position Size: {max_position_size * 100}%")
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
    # RUN PORTFOLIO STRATEGY
    ###########################################################################

    print("\n" + "=" * 80)
    print("RUNNING RELATIVE STRENGTH PORTFOLIO STRATEGY")
    print("=" * 80)

    summary, trade_log, portfolio_history = backtest_relative_strength_portfolio(all_stock_data)

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
    summary_filename = os.path.join(result_folder, f'relative_strength_summary_{timestamp}.csv')
    summary_df.to_csv(summary_filename, index=False)
    print(f"✓ Generated: {summary_filename}")

    # 2. Trade Log
    if trade_log:
        trades_df = pd.DataFrame(trade_log)
        trades_filename = os.path.join(result_folder, f'relative_strength_trades_{timestamp}.csv')
        trades_df.to_csv(trades_filename, index=False)
        print(f"✓ Generated: {trades_filename}")

    # 3. Portfolio History
    if portfolio_history:
        history_df = pd.DataFrame(portfolio_history)
        history_filename = os.path.join(result_folder, f'relative_strength_portfolio_history_{timestamp}.csv')
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

    print("\n" + "=" * 80)
    print("✓ COMPLETED!")
    print("=" * 80)
    print(f"All CSV files generated in: {result_folder}/")
    print(f"Timestamp: {timestamp}")

if __name__ == "__main__":
    main()
