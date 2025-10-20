"""
MongoDB Handler for Live NSE Data
==================================

Stores live stock prices and trading data to MongoDB Atlas
"""

from pymongo import MongoClient
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MongoDBHandler:
    """
    MongoDB handler for storing live stock data
    """

    def __init__(self, mongodb_uri):
        """
        Initialize MongoDB connection

        Parameters:
        -----------
        mongodb_uri : str
            MongoDB connection URI
        """
        self.mongodb_uri = mongodb_uri
        self.client = None
        self.db = None
        self.nse50_collection = None
        self.connected = False

        self._connect()

    def _connect(self):
        """Connect to MongoDB"""
        try:
            # Connect to MongoDB
            self.client = MongoClient(self.mongodb_uri)

            # Get database - specify 'stock_trading' as default database name
            self.db = self.client['stock_trading']  # Create/use 'stock_trading' database

            # Get collections
            self.nse50_collection = self.db['nse50v2s']  # Live stock prices
            self.trades_collection = self.db['trades']    # Trade executions (buy/sell)
            self.portfolio_collection = self.db['portfolio']  # Current portfolio/holdings
            self.sells_collection = self.db['sells']      # Sell orders specifically

            # Test connection
            self.client.admin.command('ping')

            self.connected = True
            logger.info("✓ Connected to MongoDB Atlas")
            logger.info(f"  Database: {self.db.name}")
            logger.info(f"  Collections: {self.nse50_collection.name}, {self.trades_collection.name}, {self.portfolio_collection.name}, {self.sells_collection.name}")

        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
            self.connected = False

    def save_live_price(self, symbol, price_data, source="Zerodha"):
        """
        Save live price data to MongoDB

        Parameters:
        -----------
        symbol : str
            Stock symbol (e.g., "TCS")
        price_data : dict
            Price data from NSE/Zerodha
        source : str
            Data source (Zerodha or NSE)

        Returns:
        --------
        bool : True if successful
        """
        if not self.connected:
            logger.warning("⚠️  MongoDB not connected, skipping save")
            return False

        try:
            # Prepare document matching the NSE50DataV2 schema
            document = {
                'symbol': symbol,
                'lastPrice': price_data.get('lastPrice') or price_data.get('last_price'),
                'lastUpdateTime': datetime.now().isoformat(),
                'source': source,  # Additional field to track data source

                # Optional fields (will be None if not available)
                'open': price_data.get('open') or price_data.get('ohlc', {}).get('open'),
                'dayHigh': price_data.get('dayHigh') or price_data.get('ohlc', {}).get('high'),
                'dayLow': price_data.get('dayLow') or price_data.get('ohlc', {}).get('low'),
                'previousClose': price_data.get('previousClose') or price_data.get('ohlc', {}).get('close'),
                'change': price_data.get('change'),
                'pChange': price_data.get('pChange'),
                'totalTradedVolume': price_data.get('totalTradedVolume') or price_data.get('volume'),
                'totalTradedValue': price_data.get('totalTradedValue'),
                'yearHigh': price_data.get('yearHigh'),
                'yearLow': price_data.get('yearLow'),
                'nearWKH': price_data.get('nearWKH'),
                'nearWKL': price_data.get('nearWKL'),
                'perChange365d': price_data.get('perChange365d'),
                'perChange30d': price_data.get('perChange30d'),
            }

            # Insert document
            result = self.nse50_collection.insert_one(document)

            if result.acknowledged and result.inserted_id:
                logger.debug(f"✅ MongoDB insert successful for {symbol}. ID: {result.inserted_id}")
                return True
            else:
                logger.error(f"❌ MongoDB insert failed for {symbol}: No acknowledgment from server")
                return False

        except Exception as e:
            logger.error(f"❌ Error saving to MongoDB for {symbol}: {str(e)}")
            return False

    def save_nse_bulk_data(self, nse_data_list):
        """
        Save bulk NSE data (all Nifty 50 stocks at once)

        Parameters:
        -----------
        nse_data_list : list
            List of stock data dictionaries from NSE API

        Returns:
        --------
        int : Number of documents inserted
        """
        if not self.connected:
            logger.warning("⚠️  MongoDB not connected, skipping bulk save")
            return 0

        try:
            documents = []
            timestamp = datetime.now().isoformat()

            for stock_data in nse_data_list:
                document = {
                    'priority': stock_data.get('priority'),
                    'symbol': stock_data.get('symbol'),
                    'identifier': stock_data.get('identifier'),
                    'open': stock_data.get('open'),
                    'dayHigh': stock_data.get('dayHigh'),
                    'dayLow': stock_data.get('dayLow'),
                    'lastPrice': stock_data.get('lastPrice'),
                    'previousClose': stock_data.get('previousClose'),
                    'change': stock_data.get('change'),
                    'pChange': stock_data.get('pChange'),
                    'ffmc': stock_data.get('ffmc'),
                    'yearHigh': stock_data.get('yearHigh'),
                    'yearLow': stock_data.get('yearLow'),
                    'totalTradedVolume': stock_data.get('totalTradedVolume'),
                    'totalTradedValue': stock_data.get('totalTradedValue'),
                    'lastUpdateTime': stock_data.get('lastUpdateTime', timestamp),
                    'nearWKH': stock_data.get('nearWKH'),
                    'nearWKL': stock_data.get('nearWKL'),
                    'perChange365d': stock_data.get('perChange365d'),
                    'date365dAgo': stock_data.get('date365dAgo'),
                    'chart365dPath': stock_data.get('chart365dPath'),
                    'date30dAgo': stock_data.get('date30dAgo'),
                    'perChange30d': stock_data.get('perChange30d'),
                    'chart30dPath': stock_data.get('chart30dPath'),
                    'chartTodayPath': stock_data.get('chartTodayPath'),
                    'fetchedAt': timestamp,  # Track when we fetched this data
                }
                documents.append(document)

            if documents:
                result = self.nse50_collection.insert_many(documents)
                logger.info(f"✅ MongoDB bulk insert successful: {len(result.inserted_ids)} documents")
                return len(result.inserted_ids)
            else:
                logger.warning("⚠️  No documents to insert")
                return 0

        except Exception as e:
            logger.error(f"❌ Error saving bulk data to MongoDB: {str(e)}")
            return 0

    def get_latest_price(self, symbol):
        """
        Get latest price for a symbol from MongoDB

        Parameters:
        -----------
        symbol : str
            Stock symbol

        Returns:
        --------
        dict : Latest price data or None
        """
        if not self.connected:
            return None

        try:
            # Find latest document for this symbol
            result = self.nse50_collection.find_one(
                {'symbol': symbol},
                sort=[('lastUpdateTime', -1)]
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error fetching from MongoDB for {symbol}: {str(e)}")
            return None

    def log_trade_entry(self, trade_data):
        """
        Log a BUY trade to MongoDB

        Parameters:
        -----------
        trade_data : dict
            Trade details
            {
                'symbol': str,
                'action': 'BUY',
                'entry_date': datetime,
                'entry_price': float,
                'quantity': int,
                'order_id': str,
                'capital_deployed': float,
                'stop_loss_price': float,
                'take_profit_price': float,
                'strategy': str,
                'ma_20': float,
                'ma_50': float
            }

        Returns:
        --------
        str : MongoDB document ID or None
        """
        if not self.connected:
            logger.warning("⚠️  MongoDB not connected, skipping trade log")
            return None

        try:
            # Prepare trade document
            document = {
                'symbol': trade_data['symbol'],
                'action': 'BUY',
                'tradeType': 'ENTRY',
                'entryDate': trade_data['entry_date'].isoformat() if hasattr(trade_data['entry_date'], 'isoformat') else str(trade_data['entry_date']),
                'entryPrice': trade_data['entry_price'],
                'quantity': trade_data['quantity'],
                'orderId': trade_data['order_id'],
                'capitalDeployed': trade_data.get('capital_deployed', trade_data['entry_price'] * trade_data['quantity']),
                'stopLossPrice': trade_data.get('stop_loss_price'),
                'takeProfitPrice': trade_data.get('take_profit_price'),
                'strategy': trade_data.get('strategy', 'MA_CROSSOVER_20_50'),
                'ma20': trade_data.get('ma_20'),
                'ma50': trade_data.get('ma_50'),
                'status': 'OPEN',
                'createdAt': datetime.now().isoformat(),
            }

            # Insert document
            result = self.trades_collection.insert_one(document)

            if result.acknowledged and result.inserted_id:
                logger.info(f"✅ BUY trade logged to MongoDB for {trade_data['symbol']}. ID: {result.inserted_id}")
                return str(result.inserted_id)
            else:
                logger.error(f"❌ Failed to log BUY trade for {trade_data['symbol']}")
                return None

        except Exception as e:
            logger.error(f"❌ Error logging BUY trade to MongoDB: {str(e)}")
            return None

    def log_trade_exit(self, trade_data):
        """
        Log a SELL trade to MongoDB

        Parameters:
        -----------
        trade_data : dict
            Trade details
            {
                'symbol': str,
                'action': 'SELL',
                'entry_date': datetime,
                'entry_price': float,
                'exit_date': datetime,
                'exit_price': float,
                'quantity': int,
                'entry_order_id': str,
                'exit_order_id': str,
                'pnl': float,
                'pnl_pct': float,
                'exit_reason': str,
                'holding_period_minutes': int
            }

        Returns:
        --------
        str : MongoDB document ID or None
        """
        if not self.connected:
            logger.warning("⚠️  MongoDB not connected, skipping trade log")
            return None

        try:
            # Calculate holding period
            holding_period = 0
            if 'entry_date' in trade_data and 'exit_date' in trade_data:
                entry = trade_data['entry_date']
                exit_dt = trade_data['exit_date']
                if hasattr(entry, 'timestamp') and hasattr(exit_dt, 'timestamp'):
                    holding_period = int((exit_dt - entry).total_seconds() / 60)  # minutes

            # Prepare trade document
            document = {
                'symbol': trade_data['symbol'],
                'action': 'SELL',
                'tradeType': 'EXIT',
                'entryDate': trade_data['entry_date'].isoformat() if hasattr(trade_data['entry_date'], 'isoformat') else str(trade_data['entry_date']),
                'entryPrice': trade_data['entry_price'],
                'exitDate': trade_data['exit_date'].isoformat() if hasattr(trade_data['exit_date'], 'isoformat') else str(trade_data['exit_date']),
                'exitPrice': trade_data['exit_price'],
                'quantity': trade_data['quantity'],
                'entryOrderId': trade_data.get('entry_order_id'),
                'exitOrderId': trade_data.get('exit_order_id'),
                'pnl': trade_data['pnl'],
                'pnlPercentage': trade_data['pnl_pct'],
                'exitReason': trade_data['exit_reason'],
                'holdingPeriodMinutes': holding_period,
                'capitalReturned': trade_data['exit_price'] * trade_data['quantity'],
                'status': 'CLOSED',
                'createdAt': datetime.now().isoformat(),
            }

            # Insert document
            result = self.trades_collection.insert_one(document)

            if result.acknowledged and result.inserted_id:
                logger.info(f"✅ SELL trade logged to MongoDB for {trade_data['symbol']}. P&L: ₹{trade_data['pnl']:,.2f} ({trade_data['pnl_pct']:.2f}%). ID: {result.inserted_id}")
                return str(result.inserted_id)
            else:
                logger.error(f"❌ Failed to log SELL trade for {trade_data['symbol']}")
                return None

        except Exception as e:
            logger.error(f"❌ Error logging SELL trade to MongoDB: {str(e)}")
            return None

    def get_trade_history(self, symbol=None, limit=100):
        """
        Get trade history from MongoDB

        Parameters:
        -----------
        symbol : str, optional
            Filter by symbol
        limit : int
            Maximum number of trades to return

        Returns:
        --------
        list : Trade documents
        """
        if not self.connected:
            return []

        try:
            query = {'symbol': symbol} if symbol else {}
            trades = list(self.trades_collection.find(query).sort('createdAt', -1).limit(limit))
            return trades

        except Exception as e:
            logger.error(f"❌ Error fetching trade history: {str(e)}")
            return []

    def get_trade_statistics(self):
        """
        Get trading statistics from MongoDB

        Returns:
        --------
        dict : Trading statistics
        """
        if not self.connected:
            return {}

        try:
            pipeline = [
                {'$match': {'tradeType': 'EXIT', 'status': 'CLOSED'}},
                {'$group': {
                    '_id': None,
                    'totalTrades': {'$sum': 1},
                    'totalPnL': {'$sum': '$pnl'},
                    'avgPnL': {'$avg': '$pnl'},
                    'winningTrades': {
                        '$sum': {'$cond': [{'$gt': ['$pnl', 0]}, 1, 0]}
                    },
                    'losingTrades': {
                        '$sum': {'$cond': [{'$lt': ['$pnl', 0]}, 1, 0]}
                    },
                    'avgHoldingPeriod': {'$avg': '$holdingPeriodMinutes'}
                }}
            ]

            result = list(self.trades_collection.aggregate(pipeline))

            if result:
                stats = result[0]
                stats['winRate'] = (stats['winningTrades'] / stats['totalTrades'] * 100) if stats['totalTrades'] > 0 else 0
                return stats
            else:
                return {'totalTrades': 0, 'totalPnL': 0}

        except Exception as e:
            logger.error(f"❌ Error fetching trade statistics: {str(e)}")
            return {}

    def get_portfolio(self):
        """
        Get current portfolio from MongoDB

        Returns:
        --------
        list : Portfolio holdings
        """
        if not self.connected:
            return []

        try:
            portfolio = list(self.portfolio_collection.find({'quantity': {'$gt': 0}}))
            logger.info(f"✓ Retrieved {len(portfolio)} positions from portfolio")
            return portfolio

        except Exception as e:
            logger.error(f"❌ Error fetching portfolio: {str(e)}")
            return []

    def update_portfolio(self, symbol, quantity, avg_price, action='BUY'):
        """
        Update portfolio in MongoDB

        Parameters:
        -----------
        symbol : str
            Stock symbol
        quantity : int
            Quantity (positive for buy, negative for sell)
        avg_price : float
            Average price
        action : str
            'BUY' or 'SELL'

        Returns:
        --------
        bool : Success status
        """
        if not self.connected:
            return False

        try:
            # Check if position exists
            existing = self.portfolio_collection.find_one({'symbol': symbol})

            if action == 'BUY':
                if existing:
                    # Update existing position
                    old_qty = existing.get('quantity', 0)
                    old_avg = existing.get('averagePrice', 0)

                    # Calculate new average price
                    total_qty = old_qty + quantity
                    new_avg = ((old_qty * old_avg) + (quantity * avg_price)) / total_qty if total_qty > 0 else avg_price

                    result = self.portfolio_collection.update_one(
                        {'symbol': symbol},
                        {
                            '$set': {
                                'quantity': total_qty,
                                'averagePrice': new_avg,
                                'lastUpdated': datetime.now().isoformat()
                            }
                        }
                    )
                else:
                    # Create new position
                    result = self.portfolio_collection.insert_one({
                        'symbol': symbol,
                        'quantity': quantity,
                        'averagePrice': avg_price,
                        'createdAt': datetime.now().isoformat(),
                        'lastUpdated': datetime.now().isoformat()
                    })

                logger.info(f"✓ Portfolio updated: {symbol} +{quantity} @ ₹{avg_price:.2f}")
                return True

            elif action == 'SELL':
                if existing:
                    old_qty = existing.get('quantity', 0)
                    new_qty = old_qty - quantity

                    if new_qty <= 0:
                        # Remove position if fully sold
                        result = self.portfolio_collection.delete_one({'symbol': symbol})
                        logger.info(f"✓ Portfolio: {symbol} position closed (sold {quantity})")
                    else:
                        # Reduce quantity
                        result = self.portfolio_collection.update_one(
                            {'symbol': symbol},
                            {
                                '$set': {
                                    'quantity': new_qty,
                                    'lastUpdated': datetime.now().isoformat()
                                }
                            }
                        )
                        logger.info(f"✓ Portfolio updated: {symbol} -{quantity} (remaining: {new_qty})")

                    return True
                else:
                    logger.warning(f"⚠️  Cannot sell {symbol}: no position in portfolio")
                    return False

        except Exception as e:
            logger.error(f"❌ Error updating portfolio: {str(e)}")
            return False

    def log_sell_order(self, sell_data):
        """
        Log a sell order to sells collection

        Parameters:
        -----------
        sell_data : dict
            {
                'symbol': str,
                'sellDate': datetime,
                'sellPrice': float,
                'quantity': int,
                'totalValue': float,
                'orderId': str,
                'reason': str,  # 'Stop Loss', 'Take Profit', 'Manual', etc.
                'pnl': float,
                'pnlPercentage': float
            }

        Returns:
        --------
        str : MongoDB document ID or None
        """
        if not self.connected:
            logger.warning("⚠️  MongoDB not connected, skipping sell log")
            return None

        try:
            document = {
                'symbol': sell_data['symbol'],
                'sellDate': sell_data['sellDate'].isoformat() if hasattr(sell_data['sellDate'], 'isoformat') else str(sell_data['sellDate']),
                'sellPrice': sell_data['sellPrice'],
                'quantity': sell_data['quantity'],
                'totalValue': sell_data.get('totalValue', sell_data['sellPrice'] * sell_data['quantity']),
                'orderId': sell_data.get('orderId'),
                'reason': sell_data.get('reason', 'Manual'),
                'pnl': sell_data.get('pnl'),
                'pnlPercentage': sell_data.get('pnlPercentage'),
                'entryPrice': sell_data.get('entryPrice'),
                'entryDate': sell_data.get('entryDate').isoformat() if hasattr(sell_data.get('entryDate'), 'isoformat') else str(sell_data.get('entryDate', '')),
                'holdingPeriodMinutes': sell_data.get('holdingPeriodMinutes', 0),
                'createdAt': datetime.now().isoformat()
            }

            result = self.sells_collection.insert_one(document)

            if result.acknowledged and result.inserted_id:
                logger.info(f"✅ Sell order logged: {sell_data['symbol']} - {sell_data['quantity']} @ ₹{sell_data['sellPrice']:.2f}. ID: {result.inserted_id}")
                return str(result.inserted_id)
            else:
                logger.error(f"❌ Failed to log sell order for {sell_data['symbol']}")
                return None

        except Exception as e:
            logger.error(f"❌ Error logging sell order: {str(e)}")
            return None

    def get_sell_history(self, symbol=None, limit=100):
        """
        Get sell order history

        Parameters:
        -----------
        symbol : str, optional
            Filter by symbol
        limit : int
            Maximum number of sells to return

        Returns:
        --------
        list : Sell order documents
        """
        if not self.connected:
            return []

        try:
            query = {'symbol': symbol} if symbol else {}
            sells = list(self.sells_collection.find(query).sort('sellDate', -1).limit(limit))
            return sells

        except Exception as e:
            logger.error(f"❌ Error fetching sell history: {str(e)}")
            return []

    def sync_portfolio_from_zerodha(self, zerodha_holdings):
        """
        Sync portfolio with Zerodha holdings

        Parameters:
        -----------
        zerodha_holdings : list
            Holdings from Zerodha API

        Returns:
        --------
        int : Number of positions synced
        """
        if not self.connected:
            return 0

        try:
            synced_count = 0

            for holding in zerodha_holdings:
                symbol = holding.get('tradingsymbol')
                quantity = holding.get('quantity', 0)
                avg_price = holding.get('average_price', 0)

                if quantity > 0:
                    # Update portfolio
                    existing = self.portfolio_collection.find_one({'symbol': symbol})

                    if existing:
                        # Update if different
                        if existing.get('quantity') != quantity or abs(existing.get('averagePrice', 0) - avg_price) > 0.01:
                            self.portfolio_collection.update_one(
                                {'symbol': symbol},
                                {
                                    '$set': {
                                        'quantity': quantity,
                                        'averagePrice': avg_price,
                                        'lastUpdated': datetime.now().isoformat(),
                                        'syncedFromZerodha': True
                                    }
                                }
                            )
                            synced_count += 1
                    else:
                        # Create new position
                        self.portfolio_collection.insert_one({
                            'symbol': symbol,
                            'quantity': quantity,
                            'averagePrice': avg_price,
                            'createdAt': datetime.now().isoformat(),
                            'lastUpdated': datetime.now().isoformat(),
                            'syncedFromZerodha': True
                        })
                        synced_count += 1

            logger.info(f"✓ Synced {synced_count} positions from Zerodha to MongoDB portfolio")
            return synced_count

        except Exception as e:
            logger.error(f"❌ Error syncing portfolio from Zerodha: {str(e)}")
            return 0

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("✓ MongoDB connection closed")
            self.connected = False
