import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Union
from itertools import cycle

class FinvizScraper:
    def __init__(self, proxies: Optional[List[str]] = None):
        self.base_url = "https://finviz.com"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
        self.user_agent_cycle = cycle(self.user_agents)
        
        # Set up proxy rotation if provided
        self.proxies = None
        if proxies:
            self.proxies = cycle(proxies)
        
        self.logger = self._setup_logger()
        self.last_request_time = 0
        self.min_request_interval = 2  # Minimum seconds between requests

    def _setup_logger(self) -> logging.Logger:
        """Configure logging for the scraper."""
        logger = logging.getLogger('FinvizScraper')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    def _make_request(self, url: str) -> requests.Response:
        """
        Make an HTTP request with rate limiting, rotating user agents, and proxy support.
        
        Args:
            url (str): The URL to request
            
        Returns:
            requests.Response: The response from the server
        """
        # Implement rate limiting
        time_since_last_request = time.time() - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        # Rotate user agent
        headers = {"User-Agent": next(self.user_agent_cycle)}
        
        # Get next proxy if available
        proxies = None
        if self.proxies:
            proxy = next(self.proxies)
            proxies = {
                "http": proxy,
                "https": proxy
            }
        
        # Add some randomization to seem more human-like
        time.sleep(random.uniform(0.5, 1.5))
        
        response = requests.get(url, headers=headers, proxies=proxies)
        self.last_request_time = time.time()
        
        return response

    def get_company_data(self, url: str, debug: bool = False) -> Dict[str, Union[str, float]]:
        """
        Scrape company financial data from a Finviz stock page.
        
        Args:
            url (str): The Finviz URL for the stock
            debug (bool): If True, print debug information
        
        Returns:
            dict: Dictionary containing company financial metrics
        """
        try:
            self.logger.info(f"Fetching data from {url}")
            response = self._make_request(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            data = {}
            
            # Extract table data
            tables = soup.find_all('table', class_='snapshot-table2')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    columns = row.find_all('td')
                    for i in range(0, len(columns), 2):
                        if i + 1 < len(columns):
                            key = columns[i].text.strip()
                            value = columns[i + 1].text.strip()
                            data[key] = self._convert_value(value)
            
            if debug:
                self.logger.debug(f"Scraped data: {data}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error scraping company data: {str(e)}")
            raise

    def get_sector_data(self) -> pd.DataFrame:
        """
        Scrape sector performance data from Finviz.
        
        Returns:
            pd.DataFrame: DataFrame containing sector performance metrics
        """
        try:
            url = f"{self.base_url}/quote.ashx?t=&ty=c&p=d&b=1"  # Base sector URL
            self.logger.info("Fetching sector data from groups page")
            
            response = self._make_request(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Try different table classes as Finviz might update their HTML structure
            table = soup.find('table', class_='table-light') or \
                   soup.find('table', class_='groups-table-overview') or \
                   soup.find('table', {'id': 'groups-table-overview'})
            
            if not table:
                raise ValueError("Sector table not found")
            
            data = []
            headers = []
            
            # Get headers
            header_row = table.find('tr', class_='table-header')
            if header_row:
                headers = [th.text.strip() for th in header_row.find_all('td')]
            
            # Get sector data
            rows = table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cols = row.find_all('td')
                row_data = [col.text.strip() for col in cols]
                data.append(row_data)
            
            df = pd.DataFrame(data, columns=headers)
            
            # Convert percentage strings to floats
            for col in df.columns:
                if '%' in df[col].iloc[0]:
                    df[col] = df[col].str.rstrip('%').astype('float') / 100
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error scraping sector data: {str(e)}")
            raise

    def get_stock_rating_data(self, company_data: Dict[str, Union[str, float]]) -> Dict[str, float]:
        """
        Calculate stock ratings based on various financial metrics.
        
        Args:
            company_data (dict): Dictionary containing company financial metrics
        
        Returns:
            dict: Dictionary containing calculated ratings
        """
        try:
            ratings = {}
            
            # Valuation Rating (P/E, PEG, P/B)
            pe_ratio = company_data.get('P/E', 0)
            peg_ratio = company_data.get('PEG', 0)
            pb_ratio = company_data.get('P/B', 0)
            
            ratings['valuation_score'] = self._calculate_valuation_score(
                pe_ratio, peg_ratio, pb_ratio
            )
            
            # Growth Rating
            earnings_growth = company_data.get('EPS growth next 5 years', 0)
            sales_growth = company_data.get('Sales growth past 5 years', 0)
            
            ratings['growth_score'] = self._calculate_growth_score(
                earnings_growth, sales_growth
            )
            
            # Financial Health Rating
            current_ratio = company_data.get('Current Ratio', 0)
            debt_equity = company_data.get('Debt/Equity', 0)
            
            ratings['financial_health_score'] = self._calculate_financial_health_score(
                current_ratio, debt_equity
            )
            
            # Calculate overall rating
            ratings['overall_score'] = np.mean([
                ratings['valuation_score'],
                ratings['growth_score'],
                ratings['financial_health_score']
            ])
            
            return ratings
            
        except Exception as e:
            self.logger.error(f"Error calculating stock ratings: {str(e)}")
            raise

    def _convert_value(self, value: str) -> Union[float, str]:
        """Convert string values to appropriate numeric types."""
        try:
            # Remove any commas and percentage signs
            value = value.replace(',', '').replace('%', '')
            
            # Try converting to float
            return float(value)
        except ValueError:
            # Return original string if conversion fails
            return value

    def _calculate_valuation_score(self, pe: float, peg: float, pb: float) -> float:
        """Calculate valuation score based on P/E, PEG, and P/B ratios."""
        scores = []
        
        # P/E Score (lower is better, but should be positive)
        if pe > 0:
            pe_score = max(0, min(100, (30 - pe) * 3.33))
            scores.append(pe_score)
        
        # PEG Score (closer to 1 is better)
        if peg > 0:
            peg_score = max(0, min(100, (2 - abs(1 - peg)) * 50))
            scores.append(peg_score)
        
        # P/B Score (lower is better, but should be positive)
        if pb > 0:
            pb_score = max(0, min(100, (5 - pb) * 20))
            scores.append(pb_score)
        
        return np.mean(scores) if scores else 0

    def _calculate_growth_score(self, earnings_growth: float, sales_growth: float) -> float:
        """Calculate growth score based on earnings and sales growth."""
        scores = []
        
        # Earnings Growth Score
        if earnings_growth is not None:
            earnings_score = max(0, min(100, earnings_growth * 5))
            scores.append(earnings_score)
        
        # Sales Growth Score
        if sales_growth is not None:
            sales_score = max(0, min(100, sales_growth * 5))
            scores.append(sales_score)
        
        return np.mean(scores) if scores else 0

    def _calculate_financial_health_score(self, current_ratio: float, debt_equity: float) -> float:
        """Calculate financial health score based on current ratio and debt/equity."""
        scores = []
        
        # Current Ratio Score (higher is better, optimal around 2)
        if current_ratio > 0:
            current_ratio_score = max(0, min(100, current_ratio * 50))
            scores.append(current_ratio_score)
        
        # Debt/Equity Score (lower is better)
        if debt_equity >= 0:
            debt_equity_score = max(0, min(100, (2 - debt_equity) * 50))
            scores.append(debt_equity_score)
        
        return np.mean(scores) if scores else 0

# Usage example
if __name__ == "__main__":
    # Initialize scraper without proxies for testing
    scraper = FinvizScraper()
    
    # Example usage
    try:
        # Get company data for Apple
        company_url = "https://finviz.com/quote.ashx?t=AAPL&ty=c&p=d&b=1"
        company_data = scraper.get_company_data(company_url)
        
        # Get sector data
        sector_data = scraper.get_sector_data()
        
        # Calculate ratings
        ratings = scraper.get_stock_rating_data(company_data)
        
        print("\nCompany Data:")
        for key, value in company_data.items():
            print(f"{key}: {value}")
            
        print("\nSector Data:\n", sector_data)
        print("\nStock Ratings:")
        for metric, score in ratings.items():
            print(f"{metric}: {score:.2f}")
            
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
        scraper.logger.error(f"Detailed error: {str(e)}", exc_info=True)