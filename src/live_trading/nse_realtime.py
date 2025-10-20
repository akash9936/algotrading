"""
NSE India Real-Time Price Fetcher
==================================

Fetches real-time stock prices from NSE India public API.
This is used as a fallback when Zerodha LTP is not available or for cross-verification.

WARNING: This scrapes public NSE India data. Use responsibly and respect rate limits.
"""

import requests
import time
import random
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

###############################################################################
# NSE REALTIME PRICE FETCHER
###############################################################################

class NSERealtimeFetcher:
    """
    Fetch real-time stock prices from NSE India

    Features:
    - Cookie-based session management
    - Automatic retry with exponential backoff
    - Rate limiting protection
    - Real-time Nifty 50 stock prices
    """

    def __init__(self):
        """Initialize NSE fetcher with session management"""
        self.session = requests.Session()
        self.base_url = "https://www.nseindia.com"
        self.cookies_obtained = False
        self.last_fetch_time = 0
        self.min_fetch_interval = 2  # Minimum 2 seconds between requests
        self.cache = {}
        self.cache_duration = 30  # Cache for 30 seconds

        # Headers mimicking a real browser (Linux/Ubuntu)
        self.headers = {
            'authority': 'www.nseindia.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'dnt': '1',
            'referer': 'https://www.nseindia.com/market-data/live-equity-market',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }

    def get_cookies(self) -> bool:
        """
        Obtain cookies from NSE India website

        Returns:
        --------
        bool : True if cookies obtained successfully
        """
        try:
            logger.debug("Obtaining cookies from NSE India...")

            # Visit the main page to get cookies
            response = self.session.get(
                f"{self.base_url}/market-data/live-equity-market",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                self.cookies_obtained = True
                logger.debug("✓ Cookies obtained successfully")
                return True
            else:
                logger.warning(f"Failed to obtain cookies. Status: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error obtaining cookies: {str(e)}")
            return False

    def fetch_nifty50_data(self, retry_count=5) -> Optional[Dict]:
        """
        Fetch Nifty 50 stocks data with real-time prices

        Parameters:
        -----------
        retry_count : int
            Number of retries on failure

        Returns:
        --------
        dict : Stock data or None on failure
        """
        # Rate limiting
        current_time = time.time()
        time_since_last_fetch = current_time - self.last_fetch_time

        if time_since_last_fetch < self.min_fetch_interval:
            wait_time = self.min_fetch_interval - time_since_last_fetch
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)

        # Try to fetch data with retries
        for attempt in range(retry_count):
            try:
                # Ensure we have cookies
                if not self.cookies_obtained:
                    if not self.get_cookies():
                        logger.warning(f"Retry {attempt + 1}/{retry_count}: Failed to obtain cookies")
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue

                    # Random delay after getting cookies
                    time.sleep(1 + random.random() * 2)

                # Fetch data
                api_url = f"{self.base_url}/api/equity-stockIndices?index=NIFTY%2050"

                response = self.session.get(
                    api_url,
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    self.last_fetch_time = time.time()
                    logger.info("✓ NSE data fetched successfully")
                    return data

                elif response.status_code == 401:
                    # Cookies expired, try to refresh
                    logger.warning("Cookies expired, refreshing...")
                    self.cookies_obtained = False
                    time.sleep(2 ** attempt)
                    continue

                else:
                    logger.warning(f"Retry {attempt + 1}/{retry_count}: Status {response.status_code}")
                    time.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Retry {attempt + 1}/{retry_count}: {str(e)}")
                time.sleep(2 ** attempt)

        logger.error("Failed to fetch NSE data after all retries")
        return None

    def get_stock_price(self, symbol: str) -> Optional[float]:
        """
        Get real-time price for a single stock

        Parameters:
        -----------
        symbol : str
            Stock symbol in NSE format (e.g., "TCS", "INFY")

        Returns:
        --------
        float : Last traded price or None
        """
        # Check cache first
        cache_key = f"{symbol}_{int(time.time() / self.cache_duration)}"
        if cache_key in self.cache:
            logger.debug(f"Using cached price for {symbol}")
            return self.cache[cache_key]

        # Fetch fresh data
        data = self.fetch_nifty50_data()

        if not data or 'data' not in data:
            return None

        # Find the symbol in the data
        for stock in data['data']:
            if stock.get('symbol') == symbol:
                ltp = stock.get('lastPrice')

                if ltp:
                    # Cache the result
                    self.cache[cache_key] = ltp
                    logger.info(f"{symbol}: ₹{ltp:.2f}")
                    return ltp

        logger.warning(f"Symbol {symbol} not found in NSE data")
        return None

    def get_multiple_prices(self) -> Dict[str, float]:
        """
        Get prices for all Nifty 50 stocks at once

        Returns:
        --------
        dict : {symbol: price} mapping
        """
        data = self.fetch_nifty50_data()

        if not data or 'data' not in data:
            return {}

        prices = {}
        for stock in data['data']:
            symbol = stock.get('symbol')
            ltp = stock.get('lastPrice')

            if symbol and ltp:
                prices[symbol] = ltp

        logger.info(f"Fetched prices for {len(prices)} stocks")
        return prices

    def get_stock_details(self, symbol: str) -> Optional[Dict]:
        """
        Get detailed information for a stock

        Parameters:
        -----------
        symbol : str
            Stock symbol in NSE format

        Returns:
        --------
        dict : Stock details including price, change, volume, etc.
        """
        data = self.fetch_nifty50_data()

        if not data or 'data' not in data:
            return None

        for stock in data['data']:
            if stock.get('symbol') == symbol:
                return {
                    'symbol': stock.get('symbol'),
                    'last_price': stock.get('lastPrice'),
                    'change': stock.get('change'),
                    'pct_change': stock.get('pChange'),
                    'open': stock.get('open'),
                    'high': stock.get('dayHigh'),
                    'low': stock.get('dayLow'),
                    'previous_close': stock.get('previousClose'),
                    'volume': stock.get('totalTradedVolume'),
                    'value': stock.get('totalTradedValue'),
                    'year_high': stock.get('yearHigh'),
                    'year_low': stock.get('yearLow'),
                }

        return None

###############################################################################
# HELPER FUNCTIONS
###############################################################################

def convert_zerodha_to_nse_symbol(symbol: str) -> str:
    """
    Convert Zerodha symbol format to NSE format

    Examples:
    TCS.NS -> TCS
    HDFCBANK -> HDFCBANK
    """
    if symbol.endswith('.NS'):
        return symbol[:-3]
    return symbol

def convert_nse_to_zerodha_symbol(symbol: str) -> str:
    """
    Convert NSE symbol format to Zerodha format

    Examples:
    TCS -> TCS.NS
    """
    if not symbol.endswith('.NS'):
        return f"{symbol}.NS"
    return symbol

###############################################################################
# TEST SCRIPT
###############################################################################

if __name__ == "__main__":
    # Test the NSE fetcher
    print("=" * 80)
    print("NSE REALTIME PRICE FETCHER - TEST")
    print("=" * 80)

    fetcher = NSERealtimeFetcher()

    # Test single stock
    print("\nFetching TCS price...")
    price = fetcher.get_stock_price("TCS")
    if price:
        print(f"✓ TCS: ₹{price:.2f}")
    else:
        print("✗ Failed to fetch TCS price")

    # Test multiple stocks
    print("\nFetching all Nifty 50 prices...")
    prices = fetcher.get_multiple_prices()

    if prices:
        print(f"✓ Fetched {len(prices)} stocks")
        print("\nSample prices:")
        for symbol, price in list(prices.items())[:10]:
            print(f"  {symbol:15} ₹{price:10,.2f}")
    else:
        print("✗ Failed to fetch prices")

    # Test detailed info
    print("\nFetching detailed info for RELIANCE...")
    details = fetcher.get_stock_details("RELIANCE")
    if details:
        print("✓ Details fetched:")
        for key, value in details.items():
            print(f"  {key:20} {value}")
    else:
        print("✗ Failed to fetch details")
