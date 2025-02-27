# app/helpers/data_fetcher.py
import pandas as pd
import numpy as np
import yfinance as yf
import os
from datetime import datetime, timedelta
import logging
from app.helpers.indicators import add_technical_indicators

logger = logging.getLogger(__name__)

def fetch_stock_data(ticker, period="1d", interval="1m"):
    """
    Fetch stock data from Yahoo Finance.
    
    Parameters:
    ticker (str): Stock symbol
    period (str): Time period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max)
    interval (str): Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
    
    Returns:
    pandas.DataFrame: Stock data with added technical indicators
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        data = ticker_obj.history(period=period, interval=interval)
        
        if data.empty:
            logger.warning(f"No data returned for ticker: {ticker}")
            return pd.DataFrame()
        
        # Convert column names to lowercase
        data.columns = [col.lower() for col in data.columns]
        
        # Remove timezone information
        if data.index.tzinfo is not None:
            data.index = data.index.tz_localize(None)
        
        # Add technical indicators
        data = add_technical_indicators(data)
        
        return data
    
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

def get_company_info(ticker):
    """
    Get company information and fundamental data.
    
    Parameters:
    ticker (str): Stock symbol
    
    Returns:
    dict: Company information
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        return info
    except Exception as e:
        logger.error(f"Error fetching company info for {ticker}: {e}")
        return {}

def get_intraday_data(ticker, interval="1m", days=1):
    """
    Get intraday data for the specified number of days.
    
    Parameters:
    ticker (str): Stock symbol
    interval (str): Data interval (1m, 2m, 5m, 15m, 30m, 60m)
    days (int): Number of days of data to fetch
    
    Returns:
    pandas.DataFrame: Intraday stock data
    """
    try:
        # For intraday data, Yahoo Finance requires period to be set appropriately
        if days <= 7:
            period = f"{days}d"
        else:
            # For longer periods, we need to fetch in chunks
            period = "7d"
        
        data = yf.download(ticker, period=period, interval=interval)
        
        if data.empty:
            logger.warning(f"No intraday data returned for ticker: {ticker}")
            return pd.DataFrame()
        
        # Convert column names to lowercase
        data.columns = [col.lower() for col in data.columns]
        
        # Add technical indicators
        data = add_technical_indicators(data)
        
        return data
    
    except Exception as e:
        logger.error(f"Error fetching intraday data for {ticker}: {e}")
        return pd.DataFrame()

def get_crypto_data(symbol, period="1y", interval="1d"):
    """
    Fetch cryptocurrency data from Yahoo Finance.
    
    Parameters:
    symbol (str): Crypto symbol (e.g., BTC-USD, ETH-USD)
    period (str): Time period to fetch
    interval (str): Data interval
    
    Returns:
    pandas.DataFrame: Crypto data with technical indicators
    """
    try:
        crypto = yf.Ticker(symbol)
        data = crypto.history(period=period, interval=interval)
        
        if data.empty:
            logger.warning(f"No data returned for crypto: {symbol}")
            return pd.DataFrame()
        
        # Convert column names to lowercase
        data.columns = [col.lower() for col in data.columns]
        
        # Remove timezone information
        if data.index.tzinfo is not None:
            data.index = data.index.tz_localize(None)
        
        # Add technical indicators
        data = add_technical_indicators(data)
        
        return data
    
    except Exception as e:
        logger.error(f"Error fetching crypto data for {symbol}: {e}")
        return pd.DataFrame()