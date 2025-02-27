# app/helpers/indicators.py
import pandas as pd
import numpy as np
import pandas_ta as ta
import logging

logger = logging.getLogger(__name__)

def add_technical_indicators(data):
    """
    Add technical indicators to the stock data.
    
    Parameters:
    data (pandas.DataFrame): Stock data with OHLCV columns
    
    Returns:
    pandas.DataFrame: Stock data with technical indicators
    """
    if data is None or data.empty:
        return data
    
    # Make a copy to avoid modifying the original dataframe
    df = data.copy()
    
    # Ensure required columns are filled to avoid None values
    for col in ["close", "high", "low"]:
        if col in df.columns:
            df[col] = df[col].ffill()
    
    try:
        # RSI (Relative Strength Index)
        df["RSI"] = ta.rsi(df["close"], length=14)
        
        # MACD (Moving Average Convergence Divergence)
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        if macd is not None:
            df["MACD"] = macd.get("MACD_12_26_9", np.nan)
            df["Signal"] = macd.get("MACDs_12_26_9", np.nan)
            df["MACD_Hist"] = macd.get("MACDh_12_26_9", np.nan)
        else:
            df["MACD"] = np.nan
            df["Signal"] = np.nan
            df["MACD_Hist"] = np.nan

        # Bollinger Bands
        bb = ta.bbands(df["close"], length=20, std=2)
        if bb is not None:
            df["BBL"] = bb.get("BBL_20_2.0", np.nan)
            df["BBM"] = bb.get("BBM_20_2.0", np.nan)
            df["BBU"] = bb.get("BBU_20_2.0", np.nan)
        else:
            df["BBL"] = np.nan
            df["BBM"] = np.nan
            df["BBU"] = np.nan

        # Simple Moving Averages
        df["SMA20"] = ta.sma(df["close"], length=20)
        df["SMA50"] = ta.sma(df["close"], length=50)
        df["SMA200"] = ta.sma(df["close"], length=200)

        # VWAP (Volume Weighted Average Price)
        if {"high", "low", "close", "volume"}.issubset(df.columns):
            df["VWAP"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"])

        # ADX (Average Directional Index)
        adx = ta.adx(df["high"], df["low"], df["close"], length=14)
        if adx is not None:
            df["ADX"] = adx.get("ADX_14", np.nan)
        else:
            df["ADX"] = np.nan

        # Pivot Points
        df["PP"] = (df["high"] + df["low"] + df["close"]) / 3
        df["R1"] = 2 * df["PP"] - df["low"]
        df["S1"] = 2 * df["PP"] - df["high"]

        # Day High/Low tracking
        df["Day_High"] = df["high"].cummax()
        df["Day_Low"] = df["low"].cummin()
        
        # Stochastic Oscillator
        stoch = ta.stoch(df["high"], df["low"], df["close"], k=14, d=3, smooth_k=3)
        if stoch is not None:
            df["STOCH_K"] = stoch.get("STOCHk_14_3_3", np.nan)
            df["STOCH_D"] = stoch.get("STOCHd_14_3_3", np.nan)
        else:
            df["STOCH_K"] = np.nan
            df["STOCH_D"] = np.nan
        
        # Average True Range (ATR)
        df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        
        # Percentage Price Oscillator (PPO)
        ppo = ta.ppo(df["close"], fast=12, slow=26, signal=9)
        if ppo is not None:
            df["PPO"] = ppo.get("PPO_12_26_9", np.nan)
            df["PPO_Signal"] = ppo.get("PPOs_12_26_9", np.nan)
            df["PPO_Hist"] = ppo.get("PPOh_12_26_9", np.nan)
        else:
            df["PPO"] = np.nan
            df["PPO_Signal"] = np.nan
            df["PPO_Hist"] = np.nan
        
        # On-Balance Volume (OBV)
        if "volume" in df.columns:
            df["OBV"] = ta.obv(df["close"], df["volume"])
        
    except Exception as e:
        logger.error(f"Error adding technical indicators: {e}")
    
    return df

def generate_tech_signal(rsi, rsi_buy=30, rsi_sell=70):
    """
    Generate trading signal based on RSI values.
    
    Parameters:
    rsi (float): RSI value
    rsi_buy (float): RSI level for buy signal
    rsi_sell (float): RSI level for sell signal
    
    Returns:
    str: Trading signal (STRONG BUY, BUY, HOLD, SELL, STRONG SELL)
    """
    if pd.isna(rsi):
        return "UNKNOWN"
    
    if rsi < rsi_buy:
        return "STRONG BUY"
    elif rsi < 45:
        return "BUY"
    elif rsi > rsi_sell:
        return "STRONG SELL"
    elif rsi > 55:
        return "SELL"
    else:
        return "HOLD"

def calculate_drawdown(equity_curve):
    """
    Calculate drawdown from an equity curve.
    
    Parameters:
    equity_curve (pandas.Series): Equity curve values
    
    Returns:
    tuple: (drawdown series, maximum drawdown value)
    """
    # Calculate running maximum
    running_max = equity_curve.cummax()
    
    # Calculate drawdown
    drawdown = (equity_curve - running_max) / running_max
    
    # Get maximum drawdown
    max_dd = drawdown.min()
    
    return drawdown, max_dd