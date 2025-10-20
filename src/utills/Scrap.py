
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
import joblib
import time
from typing import List, Dict

class WebScraper:
    def __init__(self, use_selenium: bool = False):
        self.use_selenium = use_selenium
        if use_selenium:
            self.options = Options()
            self.options.add_argument('--headless')
            self.options.add_argument('--no-sandbox')
            self.options.add_argument('--disable-dev-shm-usage')
            self.driver = None

    def setup_selenium(self):
        """Setup Selenium for headless Chrome"""
        if self.use_selenium:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            self.driver = webdriver.Chrome(options=chrome_options)

    def stop_selenium(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape_stocks(self, url: str) -> List[Dict]:
        """Scrape stock data from the given URL"""
        if self.use_selenium:
            return self._scrape_dynamic(url)
        return self._scrape_static(url)

    def _scrape_static(self, url: str) -> List[Dict]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            stocks = []
            stock_rows = soup.select('table.stock-table tr')

            for row in stock_rows[1:]:
                cells = row.select('td')
                if len(cells) >= 4:
                    stock_data = {
                        'symbol': cells[0].text.strip(),
                        'price': cells[1].text.strip(),
                        'change': cells[2].text.strip(),
                        'volume': cells[3].text.strip()
                    }
                    stocks.append(stock_data)

            return stocks
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return []

    def _scrape_dynamic(self, url: str) -> List[Dict]:
        try:
            if not self.driver:
                self.setup_selenium()

            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.stock-table'))
            )

            stocks = []
            stock_rows = self.driver.find_elements(By.CSS_SELECTOR, 'table.stock-table tr')

            for row in stock_rows[1:]:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) >= 4:
                    stock_data = {
                        'symbol': cells[0].text.strip(),
                        'price': cells[1].text.strip(),
                        'change': cells[2].text.strip(),
                        'volume': cells[3].text.strip()
                    }
                    stocks.append(stock_data)

            return stocks
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return []

class StockPredictor:
    def __init__(self):
        self.model = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', LogisticRegression(max_iter=1000))
        ])

    def prepare_data(self, stocks: List[Dict]) -> pd.DataFrame:
        """Convert stock data to DataFrame and clean numeric fields"""
        df = pd.DataFrame(stocks)

        df['price'] = df['price'].str.replace('$', '').astype(float)
        df['volume'] = df['volume'].str.replace(',', '').astype(float)
        df['change'] = df['change'].str.rstrip('%').astype(float) / 100

        return df

    def create_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create labels: 1 if stock went up, 0 if down"""
        df['label'] = np.where(df['change'] > 0, 1, 0)
        return df

    def train(self, df: pd.DataFrame):
        """Train the model"""
        X = df[['price', 'volume']]
        y = df['label']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        print("\nModel Performance:")
        print(classification_report(y_test, y_pred))

        return X_test, y_test

    def save_model(self, filename: str):
        """Save trained model"""
        joblib.dump(self.model, filename)

    def load_model(self, filename: str):
        """Load a trained model"""
        self.model = joblib.load(filename)

def main():
    url = "https://www.nseindia.com/market-data/live-equity-market"

    scraper = WebScraper(use_selenium=True)
    predictor = StockPredictor()

    try:
        print("Scraping stock data...")
        stocks = scraper.scrape_stocks(url)

        if stocks:
            print("\nPreparing data...")
            df = predictor.prepare_data(stocks)
            df = predictor.create_labels(df)

            print("\nTraining model...")
            X_test, y_test = predictor.train(df)

            predictor.save_model('stock_predictor.joblib')

            print("\nModel saved as 'stock_predictor.joblib'")
        else:
            print("No data was scraped. Please check the URL and selectors.")

    finally:
        scraper.stop_selenium()

if __name__ == "__main__":
    main()