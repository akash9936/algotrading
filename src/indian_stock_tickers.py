"""
Indian Stock Tickers for Yahoo Finance
========================================
Comprehensive list of Indian stocks and indices that can be tested with RSI strategy.
All tickers are formatted for Yahoo Finance (suffix: .NS for NSE, .BO for BSE)

Usage:
Replace the line: sensex = yf.Ticker("^BSESN")
With any ticker from this list
"""

###############################################################################
# MAJOR INDIAN INDICES
###############################################################################

INDICES = {
    "^BSESN": "BSE SENSEX - Benchmark index of BSE",
    "^NSEI": "NIFTY 50 - Benchmark index of NSE",
    "^NSEBANK": "NIFTY BANK - Banking sector index",
    "^CNXIT": "NIFTY IT - IT sector index",
    "^CNXAUTO": "NIFTY AUTO - Automobile sector index",
    "^CNXPHARMA": "NIFTY PHARMA - Pharmaceutical sector index",
    "^CNXFMCG": "NIFTY FMCG - Fast Moving Consumer Goods",
    "^CNXMETAL": "NIFTY METAL - Metal sector index",
    "^CNXREALTY": "NIFTY REALTY - Real estate sector index",
    "^CNXENERGY": "NIFTY ENERGY - Energy sector index",
    "^CNXMEDIA": "NIFTY MEDIA - Media sector index",
}

###############################################################################
# NIFTY 50 STOCKS (TOP 50 COMPANIES)
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

###############################################################################
# POPULAR MID-CAP STOCKS
###############################################################################

MIDCAP_STOCKS = {
    # IT
    "COFORGE.NS": "Coforge",
    "PERSISTENT.NS": "Persistent Systems",
    "MPHASIS.NS": "Mphasis",

    # Banking
    "FEDERALBNK.NS": "Federal Bank",
    "BANDHANBNK.NS": "Bandhan Bank",
    "IDFCFIRSTB.NS": "IDFC First Bank",

    # Automobile
    "TVSMOTOR.NS": "TVS Motor Company",
    "MOTHERSON.NS": "Motherson Sumi",
    "ESCORTS.NS": "Escorts",

    # Pharma
    "TORNTPHARM.NS": "Torrent Pharmaceuticals",
    "BIOCON.NS": "Biocon",
    "ALKEM.NS": "Alkem Laboratories",

    # Infrastructure
    "GODREJPROP.NS": "Godrej Properties",
    "DLF.NS": "DLF",
    "OBEROIRLTY.NS": "Oberoi Realty",

    # Consumer
    "VOLTAS.NS": "Voltas",
    "HAVELLS.NS": "Havells India",
    "BATAINDIA.NS": "Bata India",

    # Metals
    "VEDL.NS": "Vedanta",
    "NMDC.NS": "NMDC",
    "SAIL.NS": "Steel Authority of India",

    # Finance
    "LICHSGFIN.NS": "LIC Housing Finance",
    "MUTHOOTFIN.NS": "Muthoot Finance",
    "CHOLAFIN.NS": "Cholamandalam Investment",
}

###############################################################################
# PSU (PUBLIC SECTOR) STOCKS
###############################################################################

PSU_STOCKS = {
    "IRCTC.NS": "Indian Railway Catering and Tourism",
    "RAILTEL.NS": "RailTel Corporation",
    "HAL.NS": "Hindustan Aeronautics",
    "BEL.NS": "Bharat Electronics",
    "BHEL.NS": "Bharat Heavy Electricals",
    "GAIL.NS": "GAIL (India)",
    "SJVN.NS": "SJVN",
    "RECLTD.NS": "REC Limited",
    "PFC.NS": "Power Finance Corporation",
}

###############################################################################
# EMERGING SECTORS
###############################################################################

EMERGING_SECTOR_STOCKS = {
    # Electric Vehicles & Green Energy
    "TATAPOWER.NS": "Tata Power Company",
    "ADANIGREEN.NS": "Adani Green Energy",
    "SUZLON.NS": "Suzlon Energy",

    # E-commerce & Tech
    "ZOMATO.NS": "Zomato",
    "NYKAA.NS": "Nykaa (FSN E-Commerce)",
    "PAYTM.NS": "Paytm (One97 Communications)",

    # Chemicals
    "UPL.NS": "UPL Limited",
    "PIDILITIND.NS": "Pidilite Industries",
    "ATUL.NS": "Atul Ltd",
}

###############################################################################
# BSE LISTED STOCKS (Alternative .BO suffix)
###############################################################################

BSE_STOCKS = {
    "RELIANCE.BO": "Reliance Industries (BSE)",
    "TCS.BO": "Tata Consultancy Services (BSE)",
    "HDFCBANK.BO": "HDFC Bank (BSE)",
    "INFY.BO": "Infosys (BSE)",
    "ICICIBANK.BO": "ICICI Bank (BSE)",
}

###############################################################################
# HELPER FUNCTION TO LIST ALL TICKERS
###############################################################################

def print_all_tickers():
    """Print all available tickers organized by category"""

    print("=" * 80)
    print("MAJOR INDIAN INDICES")
    print("=" * 80)
    for ticker, name in INDICES.items():
        print(f"{ticker:15} - {name}")

    print("\n" + "=" * 80)
    print("NIFTY 50 STOCKS (Top Companies)")
    print("=" * 80)
    for ticker, name in NIFTY_50_STOCKS.items():
        print(f"{ticker:15} - {name}")

    print("\n" + "=" * 80)
    print("MID-CAP STOCKS")
    print("=" * 80)
    for ticker, name in MIDCAP_STOCKS.items():
        print(f"{ticker:15} - {name}")

    print("\n" + "=" * 80)
    print("PSU STOCKS")
    print("=" * 80)
    for ticker, name in PSU_STOCKS.items():
        print(f"{ticker:15} - {name}")

    print("\n" + "=" * 80)
    print("EMERGING SECTOR STOCKS")
    print("=" * 80)
    for ticker, name in EMERGING_SECTOR_STOCKS.items():
        print(f"{ticker:15} - {name}")

def get_all_tickers_list():
    """Get a flat list of all ticker symbols"""
    all_tickers = []
    all_tickers.extend(INDICES.keys())
    all_tickers.extend(NIFTY_50_STOCKS.keys())
    all_tickers.extend(MIDCAP_STOCKS.keys())
    all_tickers.extend(PSU_STOCKS.keys())
    all_tickers.extend(EMERGING_SECTOR_STOCKS.keys())
    return all_tickers

###############################################################################
# EXAMPLE USAGE
###############################################################################

if __name__ == "__main__":
    print_all_tickers()

    print("\n" + "=" * 80)
    print(f"Total tickers available: {len(get_all_tickers_list())}")
    print("=" * 80)

    print("\nTo use in RSIStock.py, replace:")
    print('  sensex = yf.Ticker("^BSESN")')
    print("\nWith any ticker from above, for example:")
    print('  stock = yf.Ticker("RELIANCE.NS")  # For Reliance Industries')
    print('  stock = yf.Ticker("INFY.NS")      # For Infosys')
    print('  stock = yf.Ticker("^NSEI")        # For NIFTY 50 Index')
