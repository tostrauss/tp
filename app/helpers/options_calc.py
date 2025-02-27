# app/helpers/options_calc.py
import math
import numpy as np
import pandas as pd
from scipy.stats import norm
import yfinance as yf
from datetime import datetime

def black_scholes_greeks(S, K, T, r, sigma, option_type='call'):
    """
    Calculate option price and Greeks using Black-Scholes model.
    
    Parameters:
    S: Stock price
    K: Strike price
    T: Time to expiration (in years)
    r: Risk-free interest rate (annual rate, expressed as a decimal)
    sigma: Volatility (annual, expressed as a decimal)
    option_type: 'call' or 'put'
    
    Returns:
    delta, gamma, theta, vega, rho, bs_price
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return (np.nan,)*6
    
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
    except Exception as e:
        print(f"Error computing d1, d2: {e}")
        return (np.nan,)*6

    try:
        if option_type.lower() == 'call':
            delta = norm.cdf(d1)
            theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T))
                     - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365.0
            bs_price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
            rho = K * T * math.exp(-r * T) * norm.cdf(d2) / 100.0
        else:
            delta = -norm.cdf(-d1)
            theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T))
                     + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365.0
            bs_price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            rho = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100.0

        gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
        vega = S * norm.pdf(d1) * math.sqrt(T) / 100.0
    except Exception as e:
        print(f"Error computing Greeks: {e}")
        return (np.nan,)*6

    return delta, gamma, theta, vega, rho, bs_price

def get_option_chain(ticker, expiration=None):
    """
    Get options chain data for a given ticker.
    
    Parameters:
    ticker: Stock symbol
    expiration: Optional expiration date (YYYY-MM-DD)
    
    Returns:
    calls, puts, selected_expiration, available_expirations
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        expirations = ticker_obj.options
        
        if not expirations:
            return None, None, None, []
        
        if expiration is None or expiration not in expirations:
            expiration = expirations[0]
        
        chain = ticker_obj.option_chain(expiration)
        
        # Add computed Greeks to the options data
        current_price = ticker_obj.history(period="1d")['Close'].iloc[-1]
        exp_date = datetime.strptime(expiration, "%Y-%m-%d")
        today = datetime.now()
        T = max((exp_date - today).days / 365.0, 0.001)  # Time in years
        r = 0.01  # Placeholder for risk-free rate, ideally should be fetched from a reliable source
        
        calls = add_greeks(chain.calls, current_price, T, r, 'call')
        puts = add_greeks(chain.puts, current_price, T, r, 'put')
        
        return calls, puts, expiration, expirations
    
    except Exception as e:
        print(f"Error retrieving options chain: {e}")
        return None, None, None, []

def add_greeks(options_df, S, T, r=0.01, option_type='call'):
    """
    Add Greeks calculations to options DataFrame.
    
    Parameters:
    options_df: DataFrame with options data
    S: Current stock price
    T: Time to expiration (in years)
    r: Risk-free interest rate
    option_type: 'call' or 'put'
    
    Returns:
    DataFrame with added Greeks columns
    """
    if options_df is None or options_df.empty:
        return pd.DataFrame()
    
    def compute_row(row):
        if pd.notna(row.get("impliedVolatility", np.nan)):
            return pd.Series(
                black_scholes_greeks(S, row["strike"], T, r, row["impliedVolatility"], option_type)
            )
        else:
            return pd.Series([np.nan] * 6)
    
    greeks = options_df.apply(compute_row, axis=1)
    greeks.columns = ["Delta", "Gamma", "Theta", "Vega", "Rho", "BS_Price"]
    
    result = pd.concat([options_df, greeks], axis=1)
    return result

def calculate_option_profit_loss(S, K, premium, option_type='call', contract_size=100):
    """
    Calculate profit/loss for an option position at different underlying prices.
    
    Parameters:
    S: Current stock price
    K: Strike price
    premium: Option premium (per share)
    option_type: 'call' or 'put'
    contract_size: Number of shares per contract (typically 100)
    
    Returns:
    DataFrame with price points and corresponding P/L values
    """
    # Generate a range of potential stock prices
    price_range = np.linspace(0.7 * S, 1.3 * S, 100)
    
    if option_type.lower() == 'call':
        # For call option: P/L = max(0, price - strike) - premium
        payoff = np.maximum(price_range - K, 0) - premium
    else:
        # For put option: P/L = max(0, strike - price) - premium
        payoff = np.maximum(K - price_range, 0) - premium
    
    # Calculate total P/L per contract
    total_payoff = payoff * contract_size
    
    # Create DataFrame with results
    results = pd.DataFrame({
        'price': price_range,
        'payoff_per_share': payoff,
        'total_payoff': total_payoff
    })
    
    return results

def calculate_option_breakeven(K, premium, option_type='call'):
    """
    Calculate the breakeven point for an option.
    
    Parameters:
    K: Strike price
    premium: Option premium
    option_type: 'call' or 'put'
    
    Returns:
    Breakeven price
    """
    if option_type.lower() == 'call':
        return K + premium
    else:
        return K - premium

def binomial_option_price(S, K, T, r, sigma, steps, option_type='call', american=False):
    """
    Calculate option price using binomial tree model, which can handle American options.
    
    Parameters:
    S: Stock price
    K: Strike price
    T: Time to expiration (in years)
    r: Risk-free interest rate
    sigma: Volatility
    steps: Number of time steps in the tree
    option_type: 'call' or 'put'
    american: Whether the option is American (can be exercised early)
    
    Returns:
    Option price
    """
    # Calculate parameters
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    p = (math.exp(r * dt) - d) / (u - d)
    
    # Initialize stock price tree
    stock_tree = np.zeros((steps + 1, steps + 1))
    for i in range(steps + 1):
        for j in range(i + 1):
            stock_tree[j, i] = S * (u ** (i - j)) * (d ** j)
    
    # Initialize option value tree
    option_tree = np.zeros((steps + 1, steps + 1))
    
    # Calculate option value at expiration
    if option_type.lower() == 'call':
        option_tree[:, steps] = np.maximum(np.zeros(steps + 1), stock_tree[:, steps] - K)
    else:
        option_tree[:, steps] = np.maximum(np.zeros(steps + 1), K - stock_tree[:, steps])
    
    # Calculate option value at earlier nodes
    for i in range(steps - 1, -1, -1):
        for j in range(i + 1):
            option_tree[j, i] = math.exp(-r * dt) * (p * option_tree[j, i + 1] + (1 - p) * option_tree[j + 1, i + 1])
            
            # For American options, check if early exercise is optimal
            if american:
                if option_type.lower() == 'call':
                    option_tree[j, i] = max(option_tree[j, i], stock_tree[j, i] - K)
                else:
                    option_tree[j, i] = max(option_tree[j, i], K - stock_tree[j, i])
    
    return option_tree[0, 0]