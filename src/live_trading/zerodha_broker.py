"""
Zerodha Broker Integration
===========================

Handles connection and trading operations with Zerodha KiteConnect API

⚠️ WARNING: This module executes REAL trades with REAL money!
"""

from kiteconnect import KiteConnect
from kiteconnect import KiteTicker
import pandas as pd
import logging
from datetime import datetime, timedelta
import json
import os

###############################################################################
# LOGGING SETUP
###############################################################################

logging.basicConfig(
    level=logging.INFO,  # INFO for production (use DEBUG for troubleshooting)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('live_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

###############################################################################
# ZERODHA BROKER CLASS
###############################################################################

class ZerodhaBroker:
    """
    Zerodha broker integration using KiteConnect API

    Features:
    - Authentication
    - Market data fetching
    - Order placement
    - Position management
    - Real-time quotes
    """

    def __init__(self, api_key, api_secret, access_token=None):
        """
        Initialize Zerodha broker connection

        Parameters:
        -----------
        api_key : str
            Zerodha API Key
        api_secret : str
            Zerodha API Secret
        access_token : str, optional
            Previously generated access token
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.kite = KiteConnect(api_key=api_key)
        self.access_token = access_token

        if access_token:
            self.kite.set_access_token(access_token)
            logger.info("✓ Connected to Zerodha with existing access token")

    def login(self):
        """
        Generate login URL for manual authentication

        Returns:
        --------
        str : Login URL
        """
        login_url = self.kite.login_url()
        logger.info(f"Login URL: {login_url}")
        return login_url

    def set_access_token_from_request_token(self, request_token):
        """
        Generate access token from request token

        Parameters:
        -----------
        request_token : str
            Request token from login callback

        Returns:
        --------
        dict : Session data including access token
        """
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = data["access_token"]
            self.kite.set_access_token(self.access_token)
            logger.info("✓ Access token generated successfully")
            return data
        except Exception as e:
            logger.error(f"❌ Error generating access token: {str(e)}")
            raise

    def get_profile(self):
        """Get user profile"""
        try:
            profile = self.kite.profile()
            logger.info(f"✓ Connected as: {profile['user_name']} ({profile['email']})")
            return profile
        except Exception as e:
            logger.error(f"❌ Error fetching profile: {str(e)}")
            return None

    def get_quote(self, symbol):
        """
        Get real-time quote for a symbol

        Parameters:
        -----------
        symbol : str
            Trading symbol (e.g., "NSE:TCS")

        Returns:
        --------
        dict : Quote data
        """
        try:
            quote = self.kite.quote([symbol])
            return quote.get(symbol, {})
        except Exception as e:
            logger.error(f"❌ Error fetching quote for {symbol}: {str(e)}")
            return None

    def get_ltp(self, symbol):
        """
        Get last traded price

        Parameters:
        -----------
        symbol : str
            Trading symbol

        Returns:
        --------
        float : Last traded price
        """
        try:
            ltp = self.kite.ltp([symbol])
            return ltp.get(symbol, {}).get('last_price', None)
        except Exception as e:
            logger.error(f"❌ Error fetching LTP for {symbol}: {str(e)}")
            return None

    def get_historical_data(self, symbol, from_date, to_date, interval="day"):
        """
        Get historical OHLC data (tries local data first, then Zerodha API)

        Parameters:
        -----------
        symbol : str
            Trading symbol (Zerodha format, e.g., "TCS")
        from_date : datetime
            Start date
        to_date : datetime
            End date
        interval : str
            Candle interval (minute, day, etc.)

        Returns:
        --------
        pd.DataFrame : Historical data
        """
        try:
            # Try to load from local data first
            df = self._load_local_historical_data(symbol, from_date, to_date)

            if not df.empty:
                logger.info(f"✓ Loaded {len(df)} candles from local data for {symbol}")
                return df

            # Fallback: Try Zerodha API (requires instrument token)
            logger.info(f"Local data not found, trying Zerodha API for {symbol}...")

            # Get instrument token
            instrument_token = self._get_instrument_token(symbol)
            if not instrument_token:
                logger.error(f"❌ Could not find instrument token for {symbol}")
                logger.warning(f"⚠️ Run download_data.py to download historical data first")
                return pd.DataFrame()

            # Fetch historical data from Zerodha
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )

            df = pd.DataFrame(data)
            if not df.empty:
                df.set_index('date', inplace=True)
                df.rename(columns={'close': 'Close', 'open': 'Open',
                                  'high': 'High', 'low': 'Low', 'volume': 'Volume'},
                         inplace=True)

            logger.info(f"✓ Fetched {len(df)} candles from Zerodha API for {symbol}")
            return df

        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def _load_local_historical_data(self, symbol, from_date, to_date):
        """
        Load historical data from local data/ folder

        Parameters:
        -----------
        symbol : str
            Stock symbol (Zerodha format, e.g., "TCS")
        from_date : datetime
            Start date
        to_date : datetime
            End date

        Returns:
        --------
        pd.DataFrame : Historical data or empty DataFrame
        """
        try:
            import glob

            # Convert symbol to Yahoo format for file lookup
            yahoo_symbol = convert_symbol_from_zerodha_format(symbol)
            clean_symbol = yahoo_symbol.replace('.', '_')

            # Get absolute path to data folder
            # Start from this file's directory and navigate to project root
            script_dir = os.path.dirname(os.path.abspath(__file__))  # /path/to/src/live_trading
            src_dir = os.path.dirname(script_dir)  # /path/to/src
            project_root = os.path.dirname(src_dir)  # /path/to/project
            data_folder = os.path.join(project_root, 'data', 'nifty50')

            logger.debug(f"Looking for data in: {data_folder}")
            logger.debug(f"Searching for pattern: {clean_symbol}_*.csv")

            if not os.path.exists(data_folder):
                logger.debug(f"Data folder not found: {data_folder}")
                return pd.DataFrame()

            # Find matching files
            pattern = os.path.join(data_folder, f"{clean_symbol}_*.csv")
            files = glob.glob(pattern)

            logger.debug(f"Found {len(files)} matching files for {symbol}")

            if not files:
                logger.debug(f"No local data files found for {symbol} (pattern: {pattern})")
                return pd.DataFrame()

            # Load the most recent file
            latest_file = max(files, key=os.path.getmtime)
            logger.debug(f"Loading file: {os.path.basename(latest_file)}")

            df = pd.read_csv(latest_file, index_col=0, parse_dates=True)

            # Filter by date range (handle timezone-aware datetimes)
            from_ts = pd.Timestamp(from_date)
            to_ts = pd.Timestamp(to_date)

            # Make timestamps timezone-aware if the dataframe index is timezone-aware
            if df.index.tz is not None:
                if from_ts.tz is None:
                    from_ts = from_ts.tz_localize(df.index.tz)
                if to_ts.tz is None:
                    to_ts = to_ts.tz_localize(df.index.tz)

            df = df[(df.index >= from_ts) & (df.index <= to_ts)]

            # Ensure required columns exist
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_columns):
                logger.warning(f"Missing required columns in local data for {symbol}")
                return pd.DataFrame()

            return df

        except Exception as e:
            logger.debug(f"Could not load local data for {symbol}: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return pd.DataFrame()

    def place_order(self, symbol, quantity, transaction_type, order_type="MARKET",
                   price=None, trigger_price=None, product="MIS", variety="regular"):
        """
        Place an order

        Parameters:
        -----------
        symbol : str
            Trading symbol (e.g., "TCS")
        quantity : int
            Number of shares
        transaction_type : str
            "BUY" or "SELL"
        order_type : str
            "MARKET", "LIMIT", "SL", "SL-M"
        price : float, optional
            Limit price
        trigger_price : float, optional
            Trigger price for SL orders
        product : str
            "MIS" (intraday) or "CNC" (delivery)
        variety : str
            Order variety ("regular", "amo", "iceberg", etc.)

        Returns:
        --------
        str : Order ID
        """
        try:
            order_params = {
                'tradingsymbol': symbol,
                'exchange': 'NSE',
                'transaction_type': transaction_type,
                'quantity': quantity,
                'order_type': order_type,
                'product': product,
                'variety': variety
            }

            if price:
                order_params['price'] = price
            if trigger_price:
                order_params['trigger_price'] = trigger_price

            logger.warning(f"⚠️ PLACING ORDER: {transaction_type} {quantity} {symbol} @ {order_type}")
            order_id = self.kite.place_order(**order_params)
            logger.info(f"✓ Order placed successfully. Order ID: {order_id}")

            return order_id

        except Exception as e:
            logger.error(f"❌ Error placing order: {str(e)}")
            raise

    def modify_order(self, order_id, quantity=None, price=None, order_type=None, trigger_price=None):
        """Modify an existing order"""
        try:
            params = {}
            if quantity:
                params['quantity'] = quantity
            if price:
                params['price'] = price
            if order_type:
                params['order_type'] = order_type
            if trigger_price:
                params['trigger_price'] = trigger_price

            self.kite.modify_order(variety="regular", order_id=order_id, **params)
            logger.info(f"✓ Order {order_id} modified successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Error modifying order {order_id}: {str(e)}")
            return False

    def cancel_order(self, order_id, variety="regular"):
        """Cancel an order"""
        try:
            self.kite.cancel_order(variety=variety, order_id=order_id)
            logger.info(f"✓ Order {order_id} cancelled successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error cancelling order {order_id}: {str(e)}")
            return False

    def get_orders(self):
        """Get all orders for the day"""
        try:
            orders = self.kite.orders()
            return orders
        except Exception as e:
            logger.error(f"❌ Error fetching orders: {str(e)}")
            return []

    def get_positions(self):
        """Get current positions"""
        try:
            positions = self.kite.positions()
            return positions
        except Exception as e:
            logger.error(f"❌ Error fetching positions: {str(e)}")
            return {'net': [], 'day': []}

    def get_holdings(self):
        """Get holdings (delivery positions)"""
        try:
            holdings = self.kite.holdings()
            return holdings
        except Exception as e:
            logger.error(f"❌ Error fetching holdings: {str(e)}")
            return []

    def get_margins(self):
        """Get account margins"""
        try:
            margins = self.kite.margins()
            return margins
        except Exception as e:
            logger.error(f"❌ Error fetching margins: {str(e)}")
            return {}

    def get_available_cash(self):
        """Get available cash balance"""
        try:
            margins = self.get_margins()
            equity = margins.get('equity', {})
            available = equity.get('available', {}).get('cash', 0)
            logger.info(f"Available cash: ₹{available:,.2f}")
            return available
        except Exception as e:
            logger.error(f"❌ Error fetching available cash: {str(e)}")
            return 0

    def _get_instrument_token(self, symbol):
        """
        Get instrument token for a symbol

        Note: This requires downloading instruments dump
        For now, this is a placeholder
        """
        # TODO: Implement instrument token lookup
        # You'll need to download and cache the instruments CSV
        return None

    def close_all_positions(self):
        """Emergency function to close all open positions"""
        try:
            positions = self.get_positions()
            net_positions = positions.get('net', [])

            for pos in net_positions:
                if pos['quantity'] != 0:
                    symbol = pos['tradingsymbol']
                    quantity = abs(pos['quantity'])
                    transaction_type = 'SELL' if pos['quantity'] > 0 else 'BUY'

                    logger.warning(f"🚨 CLOSING POSITION: {transaction_type} {quantity} {symbol}")
                    self.place_order(
                        symbol=symbol,
                        quantity=quantity,
                        transaction_type=transaction_type,
                        order_type='MARKET',
                        product=pos['product']
                    )

            logger.info("✓ All positions closed")
            return True

        except Exception as e:
            logger.error(f"❌ Error closing positions: {str(e)}")
            return False

###############################################################################
# HELPER FUNCTIONS
###############################################################################

def convert_symbol_to_zerodha_format(symbol):
    """
    Convert symbol from Yahoo format to Zerodha format

    Examples:
    TCS.NS -> TCS
    RELIANCE.NS -> RELIANCE
    """
    if symbol.endswith('.NS'):
        return symbol[:-3]
    return symbol

def convert_symbol_from_zerodha_format(symbol):
    """
    Convert symbol from Zerodha format to Yahoo format

    Examples:
    TCS -> TCS.NS
    """
    if not symbol.endswith('.NS'):
        return f"{symbol}.NS"
    return symbol
