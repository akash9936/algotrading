"""
Data Loader Utility
===================
Loads stock data from the data/ folder for use in strategy scripts.
"""

import pandas as pd
import os
import glob

###############################################################################
# CONFIGURATION
###############################################################################

# Get the absolute path to the src directory (parent of utills)
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(SRC_DIR, "data")
NIFTY50_FOLDER = os.path.join(DATA_FOLDER, "nifty50")
INDICES_FOLDER = os.path.join(DATA_FOLDER, "indices")
CUSTOM_FOLDER = os.path.join(DATA_FOLDER, "custom")

###############################################################################
# DATA LOADER CLASS
###############################################################################

class DataLoader:
    """Loads stock data from organized data folder"""

    def __init__(self, base_folder=DATA_FOLDER):
        """Initialize data loader"""
        self.base_folder = base_folder

    def _clean_ticker_name(self, ticker):
        """Clean ticker symbol for filename"""
        return ticker.replace("^", "").replace("&", "and").replace(".", "_")

    def _find_file(self, ticker, start_date=None, end_date=None, category=None):
        """
        Find data file for a ticker

        Parameters:
        -----------
        ticker : str
            Stock ticker
        start_date : str, optional
            If provided, looks for exact date match
        end_date : str, optional
            If provided, looks for exact date match
        category : str, optional
            "nifty50", "indices", "custom", or None (searches all)

        Returns:
        --------
        str : File path if found, None otherwise
        """
        clean_ticker = self._clean_ticker_name(ticker)

        # Determine search folders
        if category == "nifty50":
            folders = [NIFTY50_FOLDER]
        elif category == "indices":
            folders = [INDICES_FOLDER]
        elif category == "custom":
            folders = [CUSTOM_FOLDER]
        else:
            folders = [NIFTY50_FOLDER, INDICES_FOLDER, CUSTOM_FOLDER]

        # Build search pattern
        if start_date and end_date:
            pattern = f"{clean_ticker}_{start_date}_{end_date}.csv"
        else:
            pattern = f"{clean_ticker}_*.csv"

        # Search for file
        for folder in folders:
            if not os.path.exists(folder):
                continue

            search_path = os.path.join(folder, pattern)
            files = glob.glob(search_path)

            if files:
                # Return most recent file if multiple matches
                return max(files, key=os.path.getmtime)

        return None

    def load_stock(self, ticker, start_date=None, end_date=None, category=None):
        """
        Load stock data from file

        Parameters:
        -----------
        ticker : str
            Stock ticker (e.g., "TCS.NS")
        start_date : str, optional
            Start date (if specified, looks for exact match)
        end_date : str, optional
            End date (if specified, looks for exact match)
        category : str, optional
            Folder category to search in

        Returns:
        --------
        pd.DataFrame : Stock data with datetime index
        """
        filepath = self._find_file(ticker, start_date, end_date, category)

        if not filepath:
            print(f"❌ No data file found for {ticker}")
            if start_date and end_date:
                print(f"   Looking for: {start_date} to {end_date}")
            print(f"   Run: python download_data.py")
            return pd.DataFrame()

        try:
            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            return data
        except Exception as e:
            print(f"❌ Error loading {ticker}: {str(e)}")
            return pd.DataFrame()

    def load_multiple(self, tickers, start_date=None, end_date=None, category=None):
        """
        Load multiple stocks

        Parameters:
        -----------
        tickers : list or dict
            List of tickers or dict of {ticker: name}
        start_date : str, optional
            Start date
        end_date : str, optional
            End date
        category : str, optional
            Folder category

        Returns:
        --------
        dict : {ticker: DataFrame}
        """
        if isinstance(tickers, dict):
            ticker_list = list(tickers.keys())
        else:
            ticker_list = tickers

        data_dict = {}

        for ticker in ticker_list:
            data = self.load_stock(ticker, start_date, end_date, category)
            if not data.empty:
                data_dict[ticker] = data

        return data_dict

    def load_all_nifty50(self):
        """Load all available NIFTY 50 data files"""
        if not os.path.exists(NIFTY50_FOLDER):
            print(f"❌ NIFTY 50 folder not found: {NIFTY50_FOLDER}")
            return {}

        files = glob.glob(os.path.join(NIFTY50_FOLDER, "*.csv"))
        data_dict = {}

        print(f"Loading {len(files)} NIFTY 50 stocks...")

        for filepath in files:
            filename = os.path.basename(filepath)
            # Extract ticker from filename (e.g., TCS_NS_2023-01-01_2023-12-31.csv)
            ticker = filename.split('_')[0] + '.' + filename.split('_')[1]

            try:
                data = pd.read_csv(filepath, index_col=0, parse_dates=True)
                data_dict[ticker] = data
            except Exception as e:
                print(f"⚠ Error loading {filename}: {str(e)}")

        print(f"✓ Loaded {len(data_dict)} stocks")
        return data_dict

    def get_available_tickers(self, category=None):
        """
        Get list of available tickers

        Parameters:
        -----------
        category : str, optional
            "nifty50", "indices", "custom", or None (all)

        Returns:
        --------
        list : Available ticker symbols
        """
        if category == "nifty50":
            folders = [NIFTY50_FOLDER]
        elif category == "indices":
            folders = [INDICES_FOLDER]
        elif category == "custom":
            folders = [CUSTOM_FOLDER]
        else:
            folders = [NIFTY50_FOLDER, INDICES_FOLDER, CUSTOM_FOLDER]

        tickers = set()

        for folder in folders:
            if not os.path.exists(folder):
                continue

            files = glob.glob(os.path.join(folder, "*.csv"))
            for filepath in files:
                filename = os.path.basename(filepath)
                # Extract ticker from filename
                parts = filename.split('_')
                if len(parts) >= 2:
                    ticker = parts[0] + '.' + parts[1]
                    tickers.add(ticker)

        return sorted(list(tickers))

###############################################################################
# CONVENIENCE FUNCTIONS
###############################################################################

def quick_load(ticker, start_date=None, end_date=None):
    """Quick load function for single stock"""
    loader = DataLoader()
    return loader.load_stock(ticker, start_date, end_date)

def load_nifty50():
    """Quick load all NIFTY 50 stocks"""
    loader = DataLoader()
    return loader.load_all_nifty50()

###############################################################################
# EXAMPLE USAGE
###############################################################################

if __name__ == "__main__":
    loader = DataLoader()

    print("=" * 80)
    print("DATA LOADER - EXAMPLES")
    print("=" * 80)

    # Example 1: Load single stock
    print("\nExample 1: Load single stock")
    print("-" * 80)
    data = loader.load_stock("TCS.NS", "2023-01-01", "2023-12-31", category="nifty50")
    if not data.empty:
        print(f"✓ Loaded TCS data: {len(data)} days")
        print(data.head())

    # Example 2: Load without date specification (loads latest)
    print("\n\nExample 2: Load latest available data")
    print("-" * 80)
    data = loader.load_stock("RELIANCE.NS")
    if not data.empty:
        print(f"✓ Loaded RELIANCE data: {len(data)} days")
        print(f"Date range: {data.index[0]} to {data.index[-1]}")

    # Example 3: Load multiple stocks
    print("\n\nExample 3: Load multiple stocks")
    print("-" * 80)
    tickers = ["TCS.NS", "INFY.NS", "WIPRO.NS"]
    all_data = loader.load_multiple(tickers, category="nifty50")
    print(f"✓ Loaded {len(all_data)} stocks")
    for ticker in all_data:
        print(f"  - {ticker}: {len(all_data[ticker])} days")

    # Example 4: Get available tickers
    print("\n\nExample 4: Available tickers")
    print("-" * 80)
    nifty50_tickers = loader.get_available_tickers("nifty50")
    print(f"NIFTY 50: {len(nifty50_tickers)} stocks available")
    print(f"First 10: {nifty50_tickers[:10]}")

    # Example 5: Load all NIFTY 50
    print("\n\nExample 5: Load all NIFTY 50 stocks")
    print("-" * 80)
    all_nifty50 = loader.load_all_nifty50()
    print(f"✓ Loaded {len(all_nifty50)} NIFTY 50 stocks")
