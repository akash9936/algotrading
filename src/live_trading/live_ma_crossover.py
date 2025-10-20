"""
LIVE MA CROSSOVER STRATEGY (20/50)
===================================

⚠️ WARNING: This executes REAL trades with REAL money on Zerodha!

STRATEGY RULES:
- Entry: 20 MA crosses ABOVE 50 MA (Golden Cross)
- Stop Loss: 10%
- Take Profit: 30%

SAFETY FEATURES:
- Manual trade approval required
- Position limits enforced
- Real-time monitoring
- Emergency stop functionality
- Comprehensive logging

USAGE:
    python src/live_trading/live_ma_crossover.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import warnings
import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_trading.zerodha_broker import ZerodhaBroker, convert_symbol_to_zerodha_format
from live_trading.nse_realtime import NSERealtimeFetcher
from live_trading.mongodb_handler import MongoDBHandler
import logging
import subprocess

warnings.filterwarnings('ignore')

###############################################################################
# FOLDER SETUP
###############################################################################

# Create logs folder if it doesn't exist
script_dir = os.path.dirname(os.path.abspath(__file__))
logs_folder = os.path.join(script_dir, 'logs')
live_data_folder = os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'data', 'live_data')

os.makedirs(logs_folder, exist_ok=True)
os.makedirs(live_data_folder, exist_ok=True)

###############################################################################
# LOGGING SETUP
###############################################################################

# Generate timestamped log filename
log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(logs_folder, f'live_trading_{log_timestamp}.log')

logging.basicConfig(
    level=logging.INFO,  # INFO for production (use DEBUG for troubleshooting)
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"📁 Logs folder: {logs_folder}")
logger.info(f"📁 Live data folder: {live_data_folder}")

###############################################################################
# CONFIGURATION
###############################################################################

# Load config
config_path = os.path.join(os.path.dirname(__file__), 'config.json')

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://akash9936:Tree9936@cluster0.f1wthph.mongodb.net/?retryWrites=true&w=majority"

# Strategy Parameters
ma_short_period = 20              # 20-day MA
ma_long_period = 50               # 50-day MA
stop_loss_pct = 10.0              # 10% stop loss
take_profit_pct = 30.0            # 30% take profit

# Risk Management
max_positions = 3                 # Maximum simultaneous positions (divides capital equally)
max_trade_size = 50000            # TOTAL capital for ALL trades (₹50,000 / 3 = ₹16,666 per trade)

# Safety Settings
require_manual_approval = False    # Require manual approval for each trade
check_interval_seconds = 300      # Check every 5 minutes
trading_start_time = "01:00"      # Start trading after market opens
trading_end_time = "15:00"        # Stop trading before market closes

# Stocks to trade (Nifty 50 subset)
TRADEABLE_STOCKS = [
    "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM",
    "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK",
    "RELIANCE", "ONGC", "BPCL", "IOC",
    "MARUTI", "TATAMOTORS", "BAJAJ-AUTO", "EICHERMOT",
    "HINDUNILVR", "ITC", "BRITANNIA",
    "SUNPHARMA", "DRREDDY", "CIPLA",
    "LT", "ULTRACEMCO", "ADANIPORTS", "GRASIM",
    "BHARTIARTL", "TATASTEEL", "HINDALCO", "JSWSTEEL",
    "COALINDIA", "NTPC", "POWERGRID", "TITAN", "ASIANPAINT"
]

###############################################################################
# LIVE TRADING STRATEGY CLASS
###############################################################################

class LiveMACrossoverStrategy:
    """
    Live trading implementation of MA Crossover Strategy

    WARNING: Executes real trades with real money!
    """

    def __init__(self, broker):
        """
        Initialize live trading strategy

        Parameters:
        -----------
        broker : ZerodhaBroker
            Authenticated broker instance
        """
        self.broker = broker
        self.nse_fetcher = NSERealtimeFetcher()  # NSE real-time price fetcher
        self.active_positions = {}  # {symbol: position_data}
        self.historical_data = {}   # Cached historical data
        self.stop_trading = False
        self.trades_log = []
        self.live_prices_log = []  # Track live prices fetched from NSE

        # Initialize MongoDB handler
        self.mongodb = MongoDBHandler(MONGODB_URI)

        # File paths using logs folder
        self.positions_file = os.path.join(logs_folder, "active_positions.json")

        # Live data file for today
        today_str = datetime.now().strftime("%Y%m%d")
        self.live_data_file = os.path.join(live_data_folder, f"live_prices_{today_str}.csv")

        logger.info("=" * 80)
        logger.info("LIVE MA CROSSOVER STRATEGY INITIALIZED")
        logger.info("=" * 80)
        logger.info(f"Strategy: 20/50 MA Crossover")
        logger.info(f"Stop Loss: {stop_loss_pct}%")
        logger.info(f"Take Profit: {take_profit_pct}%")
        logger.info(f"Max Positions: {max_positions}")
        logger.info(f"Manual Approval: {require_manual_approval}")
        logger.info(f"Data Source: Local files + NSE India (real-time)")
        logger.info(f"Positions file: {self.positions_file}")
        logger.info(f"Live data file: {self.live_data_file}")
        logger.info("=" * 80)

        # Load existing positions from local file (disaster recovery)
        self.load_positions_from_file()

        # Sync with Zerodha holdings (cross-verify and update)
        self.sync_positions_from_broker()

        # Sync portfolio to MongoDB
        self.sync_portfolio_to_mongodb()

    def calculate_sma(self, prices, period):
        """Calculate Simple Moving Average"""
        return prices.rolling(window=period).mean()

    def load_positions_from_file(self):
        """
        Load active positions from local file (disaster recovery)

        This provides a backup layer if:
        - Script crashes and restarts
        - Zerodha API is temporarily unavailable
        - Network issues prevent broker sync
        """
        try:
            if not os.path.exists(self.positions_file):
                logger.info("✓ No saved positions file found (fresh start)")
                return

            with open(self.positions_file, 'r') as f:
                saved_positions = json.load(f)

            if not saved_positions:
                logger.info("✓ No saved positions found")
                return

            # Restore positions
            for symbol, position in saved_positions.items():
                # Convert entry_date string back to datetime
                if 'entry_date' in position and isinstance(position['entry_date'], str):
                    position['entry_date'] = datetime.fromisoformat(position['entry_date'])

                self.active_positions[symbol] = position

            logger.info(f"💾 Restored {len(saved_positions)} positions from local file:")
            for symbol, pos in self.active_positions.items():
                logger.info(f"  - {symbol}: {pos['quantity']} shares @ ₹{pos['entry_price']:.2f}")

        except Exception as e:
            logger.error(f"❌ Error loading positions from file: {str(e)}")
            logger.warning("⚠️  Starting with empty positions")

    def save_positions_to_file(self):
        """
        Save active positions to local file

        Called after every trade (buy/sell) to ensure positions are persisted
        """
        try:
            # Convert datetime objects to strings for JSON serialization
            serializable_positions = {}
            for symbol, position in self.active_positions.items():
                pos_copy = position.copy()
                if 'entry_date' in pos_copy and isinstance(pos_copy['entry_date'], datetime):
                    pos_copy['entry_date'] = pos_copy['entry_date'].isoformat()
                serializable_positions[symbol] = pos_copy

            with open(self.positions_file, 'w') as f:
                json.dump(serializable_positions, f, indent=4)

            logger.debug(f"💾 Saved {len(serializable_positions)} positions to {self.positions_file}")

        except Exception as e:
            logger.error(f"❌ Error saving positions to file: {str(e)}")

    def sync_positions_from_broker(self):
        """
        Sync positions from Zerodha at startup

        CRITICAL: This ensures we monitor existing positions for stop-loss/take-profit
        even if the script was restarted.
        """
        try:
            logger.info("\n🔄 Syncing positions from Zerodha...")

            # Get holdings (delivery positions)
            holdings = self.broker.get_holdings()

            if not holdings:
                logger.info("✓ No existing holdings found in Zerodha")
                return

            synced_count = 0
            updated_count = 0

            for holding in holdings:
                symbol = holding.get('tradingsymbol')
                quantity = holding.get('quantity', 0)
                avg_price = holding.get('average_price', 0)

                # Only sync if it's in our tradeable stocks list
                if symbol in TRADEABLE_STOCKS and quantity > 0:
                    # Check if we already have this position from file
                    if symbol in self.active_positions:
                        # Update quantity/price if different
                        old_qty = self.active_positions[symbol]['quantity']
                        old_price = self.active_positions[symbol]['entry_price']

                        if old_qty != quantity or abs(old_price - avg_price) > 0.01:
                            logger.info(f"  🔄 Updated {symbol}: {old_qty}→{quantity} shares, ₹{old_price:.2f}→₹{avg_price:.2f}")
                            self.active_positions[symbol]['quantity'] = quantity
                            self.active_positions[symbol]['entry_price'] = avg_price
                            updated_count += 1
                    else:
                        # New position from broker
                        self.active_positions[symbol] = {
                            'symbol': symbol,
                            'entry_date': datetime.now(),  # Unknown, use current time
                            'entry_price': avg_price,
                            'quantity': quantity,
                            'order_id': f"SYNCED_{symbol}",
                            'synced': True  # Mark as synced from broker
                        }
                        synced_count += 1
                        logger.info(f"  ✓ Synced {symbol}: {quantity} shares @ ₹{avg_price:.2f}")

            if synced_count > 0 or updated_count > 0:
                logger.info(f"\n✓ Synced {synced_count} new, updated {updated_count} existing positions")
                logger.info("  These positions will now be monitored for stop-loss/take-profit")

                # Save updated positions to file
                self.save_positions_to_file()
            else:
                logger.info("✓ No new positions found in tradeable stocks list")

        except Exception as e:
            logger.error(f"❌ Error syncing positions from broker: {str(e)}")
            logger.warning("⚠️  Continuing with existing positions")

    def sync_portfolio_to_mongodb(self):
        """
        Sync portfolio to MongoDB from active positions and Zerodha
        """
        try:
            logger.info("\n🔄 Syncing portfolio to MongoDB...")

            # Sync from Zerodha holdings
            holdings = self.broker.get_holdings()
            if holdings:
                self.mongodb.sync_portfolio_from_zerodha(holdings)

            # Also sync active positions
            for symbol, position in self.active_positions.items():
                self.mongodb.update_portfolio(
                    symbol=symbol,
                    quantity=position['quantity'],
                    avg_price=position['entry_price'],
                    action='BUY'
                )

            # Get and display portfolio
            portfolio = self.mongodb.get_portfolio()
            if portfolio:
                logger.info(f"\n📊 Current Portfolio ({len(portfolio)} positions):")
                for pos in portfolio:
                    logger.info(f"  - {pos['symbol']}: {pos['quantity']} @ ₹{pos.get('averagePrice', 0):.2f}")

        except Exception as e:
            logger.error(f"❌ Error syncing portfolio to MongoDB: {str(e)}")

    def save_live_price(self, symbol, price, source, full_data=None):
        """
        Save live price data to CSV and MongoDB for historical analysis

        Parameters:
        -----------
        symbol : str
            Stock symbol
        price : float
            Current price
        source : str
            Data source (Zerodha or NSE)
        full_data : dict, optional
            Full price data from API (for MongoDB)
        """
        try:
            timestamp = datetime.now()
            price_data = {
                'timestamp': timestamp,
                'symbol': symbol,
                'price': price,
                'source': source
            }

            # Append to live prices log
            self.live_prices_log.append(price_data)

            # Save to CSV immediately (append mode)
            df_new = pd.DataFrame([price_data])

            if not os.path.exists(self.live_data_file):
                # Create new file with header
                df_new.to_csv(self.live_data_file, index=False, mode='w')
                logger.debug(f"📊 Created live data file: {self.live_data_file}")
            else:
                # Append without header
                df_new.to_csv(self.live_data_file, index=False, mode='a', header=False)

            # Save to MongoDB
            if full_data is None:
                full_data = {'lastPrice': price, 'last_price': price}

            self.mongodb.save_live_price(symbol, full_data, source)

        except Exception as e:
            logger.error(f"❌ Error saving live price for {symbol}: {str(e)}")

    def get_realtime_price(self, symbol):
        """
        Get real-time price for a symbol (tries Zerodha quote, then NSE India)
        Also saves price data to CSV and MongoDB for analysis

        Parameters:
        -----------
        symbol : str
            Stock symbol in Zerodha format (e.g., "TCS")

        Returns:
        --------
        float : Last traded price or None
        """
        try:
            # Try Zerodha quote first (get full data, not just LTP)
            quote = self.broker.get_quote(f"NSE:{symbol}")

            if quote:
                ltp = quote.get('last_price')
                if ltp:
                    # Save full quote data to MongoDB
                    self.save_live_price(symbol, ltp, "Zerodha", full_data=quote)
                    return ltp

            # Fallback to NSE India real-time API
            logger.debug(f"Zerodha quote failed, trying NSE India for {symbol}")

            # Get full NSE data (not just price)
            nse_data = self.nse_fetcher.fetch_nifty50_data()
            if nse_data and 'data' in nse_data:
                # Find this symbol in the data
                for stock in nse_data['data']:
                    if stock.get('symbol') == symbol:
                        ltp = stock.get('lastPrice')
                        if ltp:
                            logger.info(f"✓ Using NSE India price for {symbol}: ₹{ltp:.2f}")
                            # Save full NSE data to MongoDB
                            self.save_live_price(symbol, ltp, "NSE", full_data=stock)
                            return ltp

            # If NSE data failed, try simple price fetch
            ltp = self.nse_fetcher.get_stock_price(symbol)
            if ltp:
                logger.info(f"✓ Using NSE India simple price for {symbol}: ₹{ltp:.2f}")
                self.save_live_price(symbol, ltp, "NSE")
                return ltp

            logger.warning(f"⚠️ Could not fetch price for {symbol} from any source")
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching real-time price for {symbol}: {str(e)}")
            return None

    def get_historical_data(self, symbol, days=100):
        """
        Fetch historical data for MA calculation

        Parameters:
        -----------
        symbol : str
            Stock symbol (Zerodha format)
        days : int
            Number of days of history

        Returns:
        --------
        pd.DataFrame : Historical OHLC data with MAs
        """
        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)

            df = self.broker.get_historical_data(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval="day"
            )

            if df.empty:
                logger.warning(f"⚠️ No historical data for {symbol}")
                return pd.DataFrame()

            # Validate we have enough data for 50-day MA
            if len(df) < ma_long_period:
                logger.warning(f"⚠️ Insufficient data for {symbol}: {len(df)} days (need {ma_long_period} for 50-day MA)")
                return pd.DataFrame()

            # Calculate MAs
            df['MA_20'] = self.calculate_sma(df['Close'], ma_short_period)
            df['MA_50'] = self.calculate_sma(df['Close'], ma_long_period)

            # Cache the data
            self.historical_data[symbol] = df

            return df

        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def check_entry_signal(self, symbol):
        """
        Check if there's a golden cross entry signal

        Returns:
        --------
        bool : True if entry signal detected
        """
        try:
            df = self.get_historical_data(symbol)

            if df.empty or len(df) < 2:
                return False

            # Get current and previous MA values
            ma_20_curr = df['MA_20'].iloc[-1]
            ma_50_curr = df['MA_50'].iloc[-1]
            ma_20_prev = df['MA_20'].iloc[-2]
            ma_50_prev = df['MA_50'].iloc[-2]

            # Check for NaN
            if any(pd.isna(x) for x in [ma_20_curr, ma_50_curr, ma_20_prev, ma_50_prev]):
                return False

            # Golden Cross: 20 MA crosses ABOVE 50 MA
            golden_cross = (ma_20_prev <= ma_50_prev) and (ma_20_curr > ma_50_curr)

            if golden_cross:
                logger.info(f"🎯 GOLDEN CROSS DETECTED: {symbol}")
                logger.info(f"   20 MA: {ma_20_curr:.2f} | 50 MA: {ma_50_curr:.2f}")

            return golden_cross

        except Exception as e:
            logger.error(f"❌ Error checking entry signal for {symbol}: {str(e)}")
            return False

    def check_exit_signal(self, symbol, position):
        """
        Check if position should be exited

        Returns:
        --------
        tuple : (should_exit, exit_reason)
        """
        try:
            # Get current price
            ltp = self.get_realtime_price(symbol)
            if not ltp:
                return False, ""

            entry_price = position['entry_price']
            pnl_pct = ((ltp - entry_price) / entry_price) * 100

            # Stop Loss
            if pnl_pct <= -stop_loss_pct:
                logger.warning(f"🛑 STOP LOSS HIT: {symbol} ({pnl_pct:.2f}%)")
                return True, "Stop Loss"

            # Take Profit
            if pnl_pct >= take_profit_pct:
                logger.info(f"✅ TAKE PROFIT HIT: {symbol} ({pnl_pct:.2f}%)")
                return True, "Take Profit"

            return False, ""

        except Exception as e:
            logger.error(f"❌ Error checking exit signal for {symbol}: {str(e)}")
            return False, ""

    def calculate_deployed_capital(self):
        """
        Calculate total capital currently deployed in active positions

        Returns:
        --------
        float : Total capital deployed
        """
        deployed = 0
        for symbol, position in self.active_positions.items():
            deployed += position['entry_price'] * position['quantity']

        return deployed

    def calculate_position_size(self, symbol, price):
        """
        Calculate position size based on available capital

        Logic:
        ------
        1. max_trade_size = TOTAL capital allocated for trading (e.g., ₹50,000)
        2. max_positions = Maximum simultaneous positions (e.g., 3)
        3. Per-trade allocation = max_trade_size / max_positions (e.g., ₹50,000 / 3 = ₹16,666.67)
        4. Calculate deployed capital = sum of all active position values
        5. Remaining capital = max_trade_size - deployed_capital
        6. If remaining >= per-trade allocation: Use per-trade allocation
           Else: Use remaining capital (for partial fills)

        Example:
        --------
        max_trade_size = ₹50,000, max_positions = 3
        Position 1: ₹16,666.67 → Remaining: ₹33,333.33
        Position 2: ₹16,666.67 → Remaining: ₹16,666.67
        Position 3: ₹16,666.67 → Remaining: ₹0 (exhausted, wait)
        Exit Position 2 → Freed: ₹16,666.67 → Can enter new position

        Returns:
        --------
        int : Quantity to buy
        """
        try:
            # Calculate per-trade allocation (equal division)
            per_trade_allocation = max_trade_size / max_positions

            # Calculate total deployed capital
            deployed_capital = self.calculate_deployed_capital()

            # Calculate remaining capital from total allocation
            remaining_capital = max_trade_size - deployed_capital

            logger.info(f"💰 Capital allocation:")
            logger.info(f"   Total allocated: ₹{max_trade_size:,.2f}")
            logger.info(f"   Per-trade allocation: ₹{per_trade_allocation:,.2f} (₹{max_trade_size:,.0f} / {max_positions})")
            logger.info(f"   Currently deployed: ₹{deployed_capital:,.2f}")
            logger.info(f"   Remaining: ₹{remaining_capital:,.2f}")

            # Check if we have any capital left
            if remaining_capital <= 0:
                logger.error(f"❌ All capital exhausted (₹{deployed_capital:,.2f} / ₹{max_trade_size:,.2f})")
                logger.error(f"   Waiting for positions to exit before entering new trades")
                return 0

            # Also check broker's available cash (safety check)
            available_cash = self.broker.get_available_cash()
            if available_cash <= 0:
                logger.error(f"❌ Insufficient broker balance: ₹{available_cash:,.2f}")
                logger.error(f"   Cannot place trades with zero or negative balance!")
                return 0

            # Determine capital for this trade
            if remaining_capital >= per_trade_allocation:
                # Use full per-trade allocation
                trade_capital = per_trade_allocation
                logger.info(f"   Using full allocation: ₹{trade_capital:,.2f}")
            else:
                # Use remaining capital (partial)
                trade_capital = remaining_capital
                logger.info(f"   Using remaining capital: ₹{trade_capital:,.2f} (partial allocation)")

            # Also don't exceed broker's available cash
            if trade_capital > available_cash:
                logger.warning(f"⚠️  Trade capital (₹{trade_capital:,.2f}) exceeds broker cash (₹{available_cash:,.2f})")
                trade_capital = available_cash
                logger.info(f"   Adjusted to broker's available cash: ₹{trade_capital:,.2f}")

            # Ensure trade_capital is positive
            if trade_capital <= 0:
                logger.error(f"❌ Invalid capital allocation: ₹{trade_capital:,.2f}")
                return 0

            # Calculate quantity
            quantity = int(trade_capital / price)

            if quantity == 0:
                logger.warning(f"⚠️ Calculated quantity is 0 (capital: ₹{trade_capital:,.2f}, price: ₹{price:.2f})")

            logger.info(f"📊 Position sizing: ₹{trade_capital:,.2f} / ₹{price:.2f} = {quantity} shares")

            return quantity

        except Exception as e:
            logger.error(f"❌ Error calculating position size: {str(e)}")
            return 0

    def get_user_approval(self, action, symbol, quantity, price):
        """
        Get manual approval from user

        Returns:
        --------
        bool : True if approved
        """
        if not require_manual_approval:
            return True

        print("\n" + "=" * 80)
        print("⚠️  TRADE APPROVAL REQUIRED")
        print("=" * 80)
        print(f"Action:   {action}")
        print(f"Symbol:   {symbol}")
        print(f"Quantity: {quantity}")
        print(f"Price:    ₹{price:.2f}")
        print(f"Value:    ₹{quantity * price:,.2f}")
        print("=" * 80)

        response = input("Approve this trade? (yes/no): ").strip().lower()

        if response in ['yes', 'y']:
            logger.info(f"✓ Trade approved by user")
            return True
        else:
            logger.info(f"✗ Trade rejected by user")
            return False

    def enter_position(self, symbol):
        """
        Enter a new position

        Returns:
        --------
        bool : True if position entered successfully
        """
        try:
            # Get current price
            ltp = self.get_realtime_price(symbol)
            if not ltp:
                logger.error(f"❌ Could not get LTP for {symbol}")
                return False

            # Calculate position size
            quantity = self.calculate_position_size(symbol, ltp)
            if quantity == 0:
                logger.warning(f"⚠️ Insufficient capital for {symbol}")
                return False

            # Get MA values for logging
            ma_20_val = None
            ma_50_val = None
            if symbol in self.historical_data:
                df = self.historical_data[symbol]
                if not df.empty and 'MA_20' in df.columns and 'MA_50' in df.columns:
                    ma_20_val = float(df['MA_20'].iloc[-1])
                    ma_50_val = float(df['MA_50'].iloc[-1])

            # Calculate stop loss and take profit prices
            stop_loss_price = ltp * (1 - stop_loss_pct / 100)
            take_profit_price = ltp * (1 + take_profit_pct / 100)

            # Get user approval
            if not self.get_user_approval("BUY", symbol, quantity, ltp):
                return False

            # Place order
            logger.warning(f"🔵 ENTERING POSITION: BUY {quantity} {symbol} @ ₹{ltp:.2f}")

            order_id = self.broker.place_order(
                symbol=symbol,
                quantity=quantity,
                transaction_type="BUY",
                order_type="MARKET",
                product="CNC"  # Use CNC for delivery (multi-day holding)
            )

            if order_id:
                entry_date = datetime.now()
                capital_deployed = ltp * quantity

                # Record position
                self.active_positions[symbol] = {
                    'symbol': symbol,
                    'entry_date': entry_date,
                    'entry_price': ltp,
                    'quantity': quantity,
                    'order_id': order_id
                }

                # Save to file immediately
                self.save_positions_to_file()

                # Log BUY trade to MongoDB
                trade_data = {
                    'symbol': symbol,
                    'action': 'BUY',
                    'entry_date': entry_date,
                    'entry_price': ltp,
                    'quantity': quantity,
                    'order_id': order_id,
                    'capital_deployed': capital_deployed,
                    'stop_loss_price': stop_loss_price,
                    'take_profit_price': take_profit_price,
                    'strategy': 'MA_CROSSOVER_20_50',
                    'ma_20': ma_20_val,
                    'ma_50': ma_50_val
                }
                self.mongodb.log_trade_entry(trade_data)

                # Update portfolio in MongoDB
                self.mongodb.update_portfolio(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=ltp,
                    action='BUY'
                )

                logger.info(f"✓ Position entered successfully. Order ID: {order_id}")
                logger.info(f"💾 Position saved to local file")
                logger.info(f"📊 Portfolio updated in MongoDB")
                logger.info(f"📊 Stop Loss: ₹{stop_loss_price:.2f} | Take Profit: ₹{take_profit_price:.2f}")
                return True

        except Exception as e:
            logger.error(f"❌ Error entering position for {symbol}: {str(e)}")
            return False

    def exit_position(self, symbol, reason):
        """
        Exit an existing position

        Returns:
        --------
        bool : True if position exited successfully
        """
        try:
            position = self.active_positions.get(symbol)
            if not position:
                logger.warning(f"⚠️ No position found for {symbol}")
                return False

            quantity = position['quantity']

            # Get current price
            ltp = self.get_realtime_price(symbol)
            if not ltp:
                logger.error(f"❌ Could not get LTP for {symbol}")
                return False

            # Get user approval
            if not self.get_user_approval("SELL", symbol, quantity, ltp):
                return False

            # Place sell order
            logger.warning(f"🔴 EXITING POSITION: SELL {quantity} {symbol} @ ₹{ltp:.2f} ({reason})")

            order_id = self.broker.place_order(
                symbol=symbol,
                quantity=quantity,
                transaction_type="SELL",
                order_type="MARKET",
                product="CNC"
            )

            if order_id:
                exit_date = datetime.now()
                entry_price = position['entry_price']
                entry_date = position['entry_date']

                # Calculate P&L
                pnl = (ltp - entry_price) * quantity
                pnl_pct = ((ltp - entry_price) / entry_price) * 100

                # Calculate holding period
                holding_period_minutes = int((exit_date - entry_date).total_seconds() / 60)

                # Log trade to memory
                trade = {
                    'symbol': symbol,
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'entry_price': entry_price,
                    'exit_price': ltp,
                    'quantity': quantity,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'exit_reason': reason,
                    'entry_order_id': position['order_id'],
                    'exit_order_id': order_id
                }
                self.trades_log.append(trade)

                # Log SELL trade to MongoDB (trades collection)
                self.mongodb.log_trade_exit(trade)

                # Update portfolio in MongoDB (reduce quantity or remove)
                self.mongodb.update_portfolio(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=ltp,
                    action='SELL'
                )

                # Log to sells collection with detailed sell info
                sell_data = {
                    'symbol': symbol,
                    'sellDate': exit_date,
                    'sellPrice': ltp,
                    'quantity': quantity,
                    'orderId': order_id,
                    'reason': reason,
                    'pnl': pnl,
                    'pnlPercentage': pnl_pct,
                    'holdingPeriodMinutes': holding_period_minutes
                }
                self.mongodb.log_sell_order(sell_data)

                logger.info(f"✓ Position exited. P&L: ₹{pnl:,.2f} ({pnl_pct:.2f}%)")

                # Remove from active positions
                del self.active_positions[symbol]

                # Save updated positions to file
                self.save_positions_to_file()
                logger.info(f"💾 Position removed from local file")
                logger.info(f"📊 Portfolio updated in MongoDB")
                logger.info(f"📊 Sell order logged to sells collection")

                return True

        except Exception as e:
            logger.error(f"❌ Error exiting position for {symbol}: {str(e)}")
            return False

    def scan_for_opportunities(self):
        """Scan all tradeable stocks for entry signals"""
        logger.info("\n" + "=" * 80)
        logger.info(f"SCANNING FOR OPPORTUNITIES - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        opportunities = []

        for symbol in TRADEABLE_STOCKS:
            # Skip if already holding
            if symbol in self.active_positions:
                continue

            # Check for entry signal
            if self.check_entry_signal(symbol):
                opportunities.append(symbol)

        if opportunities:
            logger.info(f"✓ Found {len(opportunities)} opportunities: {', '.join(opportunities)}")
        else:
            logger.info("No opportunities found")

        return opportunities

    def monitor_positions(self):
        """Monitor active positions for exit signals"""
        if not self.active_positions:
            logger.info("No active positions to monitor")
            return

        logger.info("\n" + "=" * 80)
        logger.info(f"MONITORING POSITIONS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        for symbol, position in list(self.active_positions.items()):
            try:
                ltp = self.get_realtime_price(symbol)
                if not ltp:
                    continue

                entry_price = position['entry_price']
                pnl_pct = ((ltp - entry_price) / entry_price) * 100

                logger.info(f"{symbol}: Entry ₹{entry_price:.2f} | Current ₹{ltp:.2f} | P&L {pnl_pct:+.2f}%")

                # Check exit signals
                should_exit, exit_reason = self.check_exit_signal(symbol, position)
                if should_exit:
                    self.exit_position(symbol, exit_reason)

            except Exception as e:
                logger.error(f"❌ Error monitoring {symbol}: {str(e)}")

    def is_trading_hours(self):
        """Check if current time is within trading hours"""
        now = datetime.now().time()
        start = datetime.strptime(trading_start_time, "%H:%M").time()
        end = datetime.strptime(trading_end_time, "%H:%M").time()

        # For testing: uncomment the line below to always return True
        # return True

        return start <= now <= end

    def run(self):
        """Main trading loop"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 STARTING LIVE TRADING")
        logger.info("=" * 80)
        logger.info(f"Trading Hours: {trading_start_time} - {trading_end_time}")
        logger.info(f"Check Interval: {check_interval_seconds} seconds")
        logger.info(f"Press Ctrl+C to stop")
        logger.info("=" * 80)

        try:
            while not self.stop_trading:
                # Check if within trading hours
                if not self.is_trading_hours():
                    logger.info("Outside trading hours. Waiting...")
                    time.sleep(60)
                    continue

                # Monitor existing positions
                self.monitor_positions()

                # Scan for new opportunities (if we have capacity)
                available_slots = max_positions - len(self.active_positions)
                if available_slots > 0:
                    opportunities = self.scan_for_opportunities()

                    for symbol in opportunities[:available_slots]:
                        self.enter_position(symbol)

                # Wait before next iteration
                logger.info(f"\n⏸ Waiting {check_interval_seconds} seconds...\n")
                time.sleep(check_interval_seconds)

        except KeyboardInterrupt:
            logger.warning("\n\n⚠️ KEYBOARD INTERRUPT - Stopping trading")
            self.stop_trading = True

        except Exception as e:
            logger.error(f"\n\n❌ UNEXPECTED ERROR: {str(e)}")
            self.stop_trading = True

        finally:
            self.shutdown()

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("\n" + "=" * 80)
        logger.info("🛑 SHUTTING DOWN")
        logger.info("=" * 80)

        # Save current positions (in case they weren't saved)
        if self.active_positions:
            self.save_positions_to_file()
            logger.info(f"💾 Active positions saved: {self.positions_file}")
            logger.info(f"   (Will be restored on next startup)")

        # Save trades log to logs folder
        if self.trades_log:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            trades_file = os.path.join(logs_folder, f"live_trades_{timestamp}.json")

            with open(trades_file, 'w') as f:
                json.dump(self.trades_log, f, indent=4, default=str)

            logger.info(f"✓ Trades log saved: {trades_file}")

        # Save live prices summary
        if self.live_prices_log:
            logger.info(f"✓ Live prices logged: {len(self.live_prices_log)} data points")
            logger.info(f"✓ Live data saved: {self.live_data_file}")

        # Summary
        logger.info(f"\nActive Positions: {len(self.active_positions)}")
        if self.active_positions:
            for symbol, pos in self.active_positions.items():
                logger.info(f"  - {symbol}: {pos['quantity']} shares @ ₹{pos['entry_price']:.2f}")

        logger.info(f"\nCompleted Trades: {len(self.trades_log)}")

        if self.trades_log:
            total_pnl = sum(t['pnl'] for t in self.trades_log)
            logger.info(f"Total P&L: ₹{total_pnl:,.2f}")

        # Close MongoDB connection
        if self.mongodb:
            self.mongodb.close()

        logger.info("\n✓ Shutdown complete")
        logger.info(f"📁 All files saved in:")
        logger.info(f"   Logs: {logs_folder}")
        logger.info(f"   Live Data: {live_data_folder}")
        logger.info("=" * 80)

###############################################################################
# DATA MANAGEMENT
###############################################################################

def check_and_download_data():
    """
    Check if historical data exists and download/update if needed

    Returns:
    --------
    bool : True if data is ready
    """
    print("\n" + "=" * 80)
    print("CHECKING HISTORICAL DATA")
    print("=" * 80)

    # Check if data folder exists
    data_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data', 'nifty50')

    if not os.path.exists(data_folder):
        print("⚠️  Historical data folder not found")
        print("📥 Downloading historical data...")
        return download_historical_data()

    # Check if data files exist
    import glob
    files = glob.glob(os.path.join(data_folder, "*.csv"))

    if not files:
        print("⚠️  No data files found")
        print("📥 Downloading historical data...")
        return download_historical_data()

    # Check if data is recent (updated today)
    from datetime import date
    today = date.today()

    # Check the modification date of files
    most_recent = max(files, key=os.path.getmtime)
    mod_time = datetime.fromtimestamp(os.path.getmtime(most_recent))
    mod_date = mod_time.date()

    if mod_date < today:
        print(f"⚠️  Data is outdated (last updated: {mod_date})")
        print("📥 Updating historical data...")
        return download_historical_data()

    print(f"✓ Historical data is up-to-date ({len(files)} files)")
    print(f"✓ Last updated: {mod_date}")
    print("=" * 80)
    return True

def download_historical_data():
    """
    Download historical data using download_data.py

    Returns:
    --------
    bool : True if successful
    """
    try:
        # Get path to download_data.py (in same folder as this script)
        download_script = os.path.join(os.path.dirname(__file__), 'download_data.py')

        if not os.path.exists(download_script):
            print(f"❌ Download script not found: {download_script}")
            return False

        print("\nRunning automated data download...")
        print("This will download Nifty 50 stocks data (may take a few minutes)")
        print("-" * 80)

        # Use the DataDownloader class directly
        sys.path.insert(0, os.path.dirname(__file__))
        from download_data import DataDownloader

        downloader = DataDownloader()

        # Download Nifty 50 data
        start_date = "2022-01-01"
        end_date = datetime.now().strftime("%Y-%m-%d")

        print(f"\nDownloading data from {start_date} to {end_date}...")
        results = downloader.download_nifty50(start_date, end_date)

        successful = sum(1 for v in results.values() if v)
        total = len(results)

        print("\n" + "=" * 80)
        if successful == total:
            print(f"✓ Successfully downloaded {successful}/{total} stocks")
            print("=" * 80)
            return True
        elif successful > 0:
            # Calculate success rate
            success_rate = (successful / total) * 100
            print(f"⚠️  Partial download: {successful}/{total} stocks ({success_rate:.1f}% success)")
            print("=" * 80)

            # Auto-continue if we have at least 90% of stocks
            if success_rate >= 90:
                print(f"✓ Success rate {success_rate:.1f}% is acceptable, continuing...")
                return True
            else:
                print(f"❌ Success rate {success_rate:.1f}% is too low (need at least 90%)")
                return False
        else:
            print(f"❌ Failed to download data")
            print("=" * 80)
            return False

    except Exception as e:
        print(f"❌ Error downloading data: {str(e)}")
        print("=" * 80)
        return False

###############################################################################
# MAIN EXECUTION
###############################################################################

def main():
    """Main entry point"""

    print("=" * 80)
    print("LIVE MA CROSSOVER STRATEGY - ZERODHA")
    print("=" * 80)
    print("⚠️  WARNING: This will execute REAL trades with REAL money!")
    print("=" * 80)
    print()
    print("📊 DATA SOURCES:")
    print("  - Historical: Local data files (data/nifty50/)")
    print("  - Real-time: NSE India API")
    print("=" * 80)

    # Check and download historical data if needed
    data_ready = check_and_download_data()

    if not data_ready:
        print("\n❌ Cannot proceed without historical data")
        print("Historical data is required for MA calculation")
        return

    # Load configuration
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        print("Please create config.json with your Zerodha API credentials")
        print("See config_template.json for reference")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    api_key = config.get('api_key')
    api_secret = config.get('api_secret')
    access_token = config.get('access_token')

    if not api_key or not api_secret:
        print("❌ API credentials missing in config.json")
        return

    # Initialize broker
    print("Connecting to Zerodha...")
    broker = ZerodhaBroker(api_key, api_secret, access_token)

    # Check if we need to login
    if not access_token:
        print("\n⚠️ Access token not found. You need to login first.")
        login_url = broker.login()
        print(f"\n1. Open this URL in your browser:")
        print(f"   {login_url}")
        print(f"\n2. Login and authorize the app")
        print(f"\n3. Copy the request_token from the redirect URL")
        request_token = input("\nEnter request_token: ").strip()

        if request_token:
            session_data = broker.set_access_token_from_request_token(request_token)
            access_token = session_data['access_token']

            # Save access token to config
            config['access_token'] = access_token
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)

            print("✓ Access token saved to config.json")

    # Verify connection
    profile = broker.get_profile()
    if not profile:
        print("❌ Failed to connect to Zerodha")
        return

    print(f"✓ Connected as: {profile['user_name']}")

    # Show available cash
    available_cash = broker.get_available_cash()
    print(f"✓ Available cash: ₹{available_cash:,.2f}")

    # Final confirmation
    print("\n" + "=" * 80)
    print("⚠️  FINAL CONFIRMATION")
    print("=" * 80)
    print(f"This strategy will:")
    print(f"  - Monitor {len(TRADEABLE_STOCKS)} stocks")
    print(f"  - Execute up to {max_positions} simultaneous positions")
    print(f"  - Use TOTAL capital of ₹{max_trade_size:,} (across all positions)")
    print(f"  - Allocate ₹{max_trade_size / max_positions:,.2f} per trade (₹{max_trade_size:,} / {max_positions})")
    print(f"  - {'REQUIRE' if require_manual_approval else 'NOT REQUIRE'} manual approval for each trade")
    print("=" * 80)

    response = input("\nProceed with live trading? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("✗ Live trading cancelled")
        return

    # Initialize and run strategy
    strategy = LiveMACrossoverStrategy(broker)
    strategy.run()

if __name__ == "__main__":
    main()
