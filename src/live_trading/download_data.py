"""
Centralized Data Downloader
============================
Downloads stock data once and saves to organized data/ folder.
Data can then be used by multiple strategy scripts without re-downloading.

Directory Structure:
data/
├── nifty50/
│   ├── TCS_NS_2023-01-01_2023-12-31.csv
│   ├── INFY_NS_2023-01-01_2023-12-31.csv
│   └── ...
├── indices/
│   ├── BSESN_2023-01-01_2023-12-31.csv
│   └── NSEI_2023-01-01_2023-12-31.csv
└── custom/
    └── ...
"""

import yfinance as yf
import pandas as pd
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

###############################################################################
# CONFIGURATION
###############################################################################

DATA_FOLDER = "data"  # Main data folder
NIFTY50_FOLDER = os.path.join(DATA_FOLDER, "nifty50")
INDICES_FOLDER = os.path.join(DATA_FOLDER, "indices")
CUSTOM_FOLDER = os.path.join(DATA_FOLDER, "custom")

###############################################################################
# NIFTY 50 STOCKS
###############################################################################

NIFTY_50_STOCKS = {
    # IT Sector
    "TCS.NS": "Tata Consultancy Services",
    "INFY.NS": "Infosys",
    "WIPRO.NS": "Wipro",
    "HCLTECH.NS": "HCL Technologies",
    "TECHM.NS": "Tech Mahindra",
    "LTI.NS": "LTIMindtree",

    # Banking & Finance
    "HDFCBANK.NS": "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
    "SBIN.NS": "State Bank of India",
    "AXISBANK.NS": "Axis Bank",
    "KOTAKBANK.NS": "Kotak Mahindra Bank",
    "INDUSINDBK.NS": "IndusInd Bank",
    "BAJFINANCE.NS": "Bajaj Finance",
    "BAJAJFINSV.NS": "Bajaj Finserv",
    "HDFCLIFE.NS": "HDFC Life Insurance",
    "SBILIFE.NS": "SBI Life Insurance",

    # Oil & Gas
    "RELIANCE.NS": "Reliance Industries",
    "ONGC.NS": "Oil and Natural Gas Corporation",
    "BPCL.NS": "Bharat Petroleum",
    "IOC.NS": "Indian Oil Corporation",

    # Automobile
    "MARUTI.NS": "Maruti Suzuki",
    "M&M.NS": "Mahindra & Mahindra",
    "TATAMOTORS.NS": "Tata Motors",
    "BAJAJ-AUTO.NS": "Bajaj Auto",
    "EICHERMOT.NS": "Eicher Motors",

    # FMCG
    "HINDUNILVR.NS": "Hindustan Unilever",
    "ITC.NS": "ITC Limited",
    "NESTLEIND.NS": "Nestle India",
    "BRITANNIA.NS": "Britannia Industries",
    "DABUR.NS": "Dabur India",

    # Pharma
    "SUNPHARMA.NS": "Sun Pharmaceutical",
    "DRREDDY.NS": "Dr. Reddy's Laboratories",
    "CIPLA.NS": "Cipla",
    "DIVISLAB.NS": "Divi's Laboratories",
    "APOLLOHOSP.NS": "Apollo Hospitals",

    # Infrastructure & Construction
    "LT.NS": "Larsen & Toubro",
    "ULTRACEMCO.NS": "UltraTech Cement",
    "ADANIPORTS.NS": "Adani Ports",
    "GRASIM.NS": "Grasim Industries",

    # Telecom
    "BHARTIARTL.NS": "Bharti Airtel",

    # Metals
    "TATASTEEL.NS": "Tata Steel",
    "HINDALCO.NS": "Hindalco Industries",
    "JSWSTEEL.NS": "JSW Steel",
    "COALINDIA.NS": "Coal India",

    # Conglomerate
    "ADANIENT.NS": "Adani Enterprises",
    "POWERGRID.NS": "Power Grid Corporation",
    "NTPC.NS": "NTPC",

    # Consumer Durables
    "TITAN.NS": "Titan Company",
    "ASIANPAINT.NS": "Asian Paints",
}

INDIAN_INDICES = {
    "^BSESN": "BSE SENSEX",
    "^NSEI": "NIFTY 50",
    "^NSEBANK": "NIFTY BANK",
    "^CNXIT": "NIFTY IT",
    "^CNXAUTO": "NIFTY AUTO",
}

###############################################################################
# DATA DOWNLOADER CLASS
###############################################################################

class DataDownloader:
    """Downloads and manages stock data in organized folders"""

    def __init__(self, base_folder=DATA_FOLDER):
        """Initialize downloader and create folder structure"""
        self.base_folder = base_folder
        self._create_folders()

    def _create_folders(self):
        """Create data folder structure"""
        folders = [
            self.base_folder,
            NIFTY50_FOLDER,
            INDICES_FOLDER,
            CUSTOM_FOLDER
        ]
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
                print(f"✓ Created folder: {folder}")

    def _clean_ticker_name(self, ticker):
        """Clean ticker symbol for filename"""
        return ticker.replace("^", "").replace("&", "and").replace(".", "_")

    def _get_filepath(self, ticker, start_date, end_date, category="custom"):
        """Generate file path for a ticker"""
        clean_ticker = self._clean_ticker_name(ticker)
        filename = f"{clean_ticker}_{start_date}_{end_date}.csv"

        if category == "nifty50":
            return os.path.join(NIFTY50_FOLDER, filename)
        elif category == "indices":
            return os.path.join(INDICES_FOLDER, filename)
        else:
            return os.path.join(CUSTOM_FOLDER, filename)

    def _get_existing_data_files(self, ticker, category):
        """Get all existing data files for a ticker"""
        clean_ticker = self._clean_ticker_name(ticker)

        if category == "nifty50":
            folder = NIFTY50_FOLDER
        elif category == "indices":
            folder = INDICES_FOLDER
        else:
            folder = CUSTOM_FOLDER

        # Find all files for this ticker
        import glob
        pattern = os.path.join(folder, f"{clean_ticker}_*.csv")
        return glob.glob(pattern)

    def _merge_data_files(self, ticker, new_data, category):
        """Merge new data with existing data, avoiding duplicates"""
        existing_files = self._get_existing_data_files(ticker, category)

        if not existing_files:
            return new_data

        # Load all existing data
        all_existing_data = []
        for file in existing_files:
            try:
                df = pd.read_csv(file, index_col=0, parse_dates=True)
                all_existing_data.append(df)
            except Exception as e:
                print(f"⚠ Warning: Could not read {file}: {str(e)}")

        if all_existing_data:
            # Combine all existing data
            combined_existing = pd.concat(all_existing_data, ignore_index=False)
            combined_existing = combined_existing[~combined_existing.index.duplicated(keep='first')]

            # Merge with new data
            combined = pd.concat([combined_existing, new_data], ignore_index=False)
            combined = combined[~combined.index.duplicated(keep='last')]  # Fixed: use combined, not combined_existing
            combined = combined.sort_index()

            return combined

        return new_data

    def download_stock(self, ticker, start_date, end_date, category="custom", force_refresh=False):
        """
        Download single stock data and merge with existing data intelligently

        Parameters:
        -----------
        ticker : str
            Stock ticker (e.g., "TCS.NS")
        start_date : str
            Start date YYYY-MM-DD
        end_date : str
            End date YYYY-MM-DD
        category : str
            Folder category: "nifty50", "indices", or "custom"
        force_refresh : bool
            If True, re-download and replace all existing data

        Returns:
        --------
        bool : Success status
        """
        filepath = self._get_filepath(ticker, start_date, end_date, category)

        # Check if exact file exists
        if os.path.exists(filepath) and not force_refresh:
            print(f"✓ Already exists: {ticker}")
            return True

        # Download new data
        try:
            print(f"⬇ Downloading {ticker}...", end=" ")
            stock = yf.Ticker(ticker)
            new_data = stock.history(start=start_date, end=end_date)

            if new_data.empty:
                print("❌ No data available")
                return False

            # Check for existing data files
            existing_files = self._get_existing_data_files(ticker, category)

            if existing_files and not force_refresh:
                # Load existing data to check date ranges
                all_dates = set()
                for file in existing_files:
                    try:
                        df = pd.read_csv(file, index_col=0, parse_dates=True)
                        all_dates.update(df.index.date)
                    except:
                        pass

                # Check if new data is already covered
                new_dates = set(new_data.index.date)
                if new_dates.issubset(all_dates):
                    print(f"✓ Data already exists")
                    return True

                # Merge with existing data
                merged_data = self._merge_data_files(ticker, new_data, category)

                # Create filename with combined date range
                min_date = merged_data.index.min().strftime('%Y-%m-%d')
                max_date = merged_data.index.max().strftime('%Y-%m-%d')
                merged_filepath = self._get_filepath(ticker, min_date, max_date, category)

                # Save merged data
                merged_data.to_csv(merged_filepath)

                # Remove old files (keep only the merged file)
                for old_file in existing_files:
                    if old_file != merged_filepath:
                        try:
                            os.remove(old_file)
                        except:
                            pass

                print(f"✓ Merged ({len(merged_data)} days total: {min_date} to {max_date})")
                return True
            else:
                # No existing data or force_refresh - save new data
                new_data.to_csv(filepath)
                print(f"✓ Saved ({len(new_data)} days)")
                return True

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

    def download_multiple(self, ticker_dict, start_date, end_date, category="custom", force_refresh=False):
        """
        Download multiple stocks

        Parameters:
        -----------
        ticker_dict : dict
            Dictionary of {ticker: name} pairs
        start_date : str
            Start date YYYY-MM-DD
        end_date : str
            End date YYYY-MM-DD
        category : str
            Folder category
        force_refresh : bool
            Re-download existing files

        Returns:
        --------
        dict : {ticker: success_status}
        """
        results = {}
        total = len(ticker_dict)

        print(f"\nDownloading {total} stocks to '{category}' folder...")
        print("=" * 80)

        for idx, (ticker, name) in enumerate(ticker_dict.items(), 1):
            print(f"[{idx}/{total}] {name:35} ({ticker:15})", end=" | ")
            success = self.download_stock(ticker, start_date, end_date, category, force_refresh)
            results[ticker] = success

        successful = sum(1 for v in results.values() if v)
        print("=" * 80)
        print(f"✓ Downloaded {successful}/{total} stocks successfully\n")

        return results

    def download_nifty50(self, start_date, end_date, force_refresh=False):
        """Download all NIFTY 50 stocks"""
        print("\n" + "=" * 80)
        print("DOWNLOADING NIFTY 50 STOCKS")
        print("=" * 80)
        return self.download_multiple(NIFTY_50_STOCKS, start_date, end_date, "nifty50", force_refresh)

    def download_indices(self, start_date, end_date, force_refresh=False):
        """Download Indian indices"""
        print("\n" + "=" * 80)
        print("DOWNLOADING INDIAN INDICES")
        print("=" * 80)
        return self.download_multiple(INDIAN_INDICES, start_date, end_date, "indices", force_refresh)

    def get_downloaded_files(self, category=None):
        """Get list of downloaded files"""
        if category == "nifty50":
            folder = NIFTY50_FOLDER
        elif category == "indices":
            folder = INDICES_FOLDER
        elif category == "custom":
            folder = CUSTOM_FOLDER
        else:
            # Get all files
            files = []
            for folder in [NIFTY50_FOLDER, INDICES_FOLDER, CUSTOM_FOLDER]:
                files.extend([os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')])
            return files

        return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]

    def show_summary(self):
        """Show summary of downloaded data"""
        print("\n" + "=" * 80)
        print("DATA SUMMARY")
        print("=" * 80)

        categories = {
            "NIFTY 50 Stocks": NIFTY50_FOLDER,
            "Indices": INDICES_FOLDER,
            "Custom": CUSTOM_FOLDER
        }

        total_files = 0
        total_size = 0

        for cat_name, folder in categories.items():
            if os.path.exists(folder):
                files = [f for f in os.listdir(folder) if f.endswith('.csv')]
                size = sum(os.path.getsize(os.path.join(folder, f)) for f in files) / 1024  # KB

                print(f"\n{cat_name}:")
                print(f"  Files: {len(files)}")
                print(f"  Size: {size:.1f} KB")

                if files:
                    print(f"  Latest files:")
                    for f in sorted(files)[:5]:
                        file_path = os.path.join(folder, f)
                        modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                        print(f"    - {f} ({modified.strftime('%Y-%m-%d %H:%M')})")
                    if len(files) > 5:
                        print(f"    ... and {len(files) - 5} more")

                total_files += len(files)
                total_size += size

        print("\n" + "=" * 80)
        print(f"Total Files: {total_files}")
        print(f"Total Size: {total_size/1024:.2f} MB")
        print("=" * 80)

###############################################################################
# MAIN EXECUTION
###############################################################################

def main():
    """Main function to download data"""

    print("=" * 80)
    print("STOCK DATA DOWNLOADER")
    print("=" * 80)
    print("Downloads stock data and saves to organized data/ folder")
    print("Data can be reused by multiple strategy scripts")
    print("=" * 80)

    # Initialize downloader
    downloader = DataDownloader()

    # Configuration
    start_date = "2022-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")

    print(f"\nDate Range: {start_date} to {end_date}")

    # Menu
    print("\nWhat would you like to download?")
    print("1. NIFTY 50 stocks (50+ stocks)")
    print("2. Indian indices (5 indices)")
    print("3. Both NIFTY 50 and indices")
    print("4. Custom stock (specify ticker)")
    print("5. Show downloaded data summary")

    choice = input("\nEnter choice (1-5): ").strip()

    if choice == "1":
        downloader.download_nifty50(start_date, end_date)

    elif choice == "2":
        downloader.download_indices(start_date, end_date)

    elif choice == "3":
        downloader.download_indices(start_date, end_date)
        downloader.download_nifty50(start_date, end_date)

    elif choice == "4":
        ticker = input("Enter ticker symbol (e.g., TCS.NS): ").strip()
        name = input("Enter stock name: ").strip()
        downloader.download_multiple({ticker: name}, start_date, end_date, "custom")

    elif choice == "5":
        downloader.show_summary()

    else:
        print("Invalid choice")

    # Show summary
    print("\n")
    downloader.show_summary()

    print("\n" + "=" * 80)
    print("DATA READY!")
    print("=" * 80)
    print("You can now run any strategy script using this data.")
    print("Data location: ./data/")
    print("  - NIFTY 50: ./data/nifty50/")
    print("  - Indices: ./data/indices/")
    print("  - Custom: ./data/custom/")

if __name__ == "__main__":
    main()
