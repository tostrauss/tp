# app/backtesting/backtest_engine.py
import pandas as pd
import numpy as np
from datetime import datetime
import math
from app.helpers.indicators import add_technical_indicators

class Strategy:
    """Base class for all trading strategies"""
    def __init__(self, name):
        self.name = name
    
    def generate_signals(self, data):
        """Generate buy/sell signals based on the strategy logic"""
        raise NotImplementedError("Subclass must implement this method")


class MovingAverageCrossStrategy(Strategy):
    """Moving Average Crossover Strategy"""
    def __init__(self, short_window=20, long_window=50):
        super().__init__("Moving Average Crossover")
        self.short_window = short_window
        self.long_window = long_window
    
    def generate_signals(self, data):
        """Generate buy/sell signals based on MA crossover"""
        # Make a copy of the data
        signals = data.copy()
        
        # Create signals dataframe
        signals['signal'] = 0.0
        
        # Create short and long moving averages
        signals['short_ma'] = signals['close'].rolling(window=self.short_window).mean()
        signals['long_ma'] = signals['close'].rolling(window=self.long_window).mean()
        
        # Create signals
        signals['signal'] = 0.0
        
        # Buy when short MA crosses above long MA and RSI is below buy threshold
        signals.loc[(signals['short_ma'] > signals['long_ma']) & 
                   (signals['RSI'] < self.rsi_buy), 'signal'] = 1.0
                   
        # Sell when short MA crosses below long MA and RSI is above sell threshold
        signals.loc[(signals['short_ma'] < signals['long_ma']) & 
                   (signals['RSI'] > self.rsi_sell), 'signal'] = -1.0
        
        # Generate trading orders
        signals['positions'] = signals['signal'].diff()
        
        return signals


class Backtester:
    """Backtesting engine for trading strategies"""
    def __init__(self, data, strategy, initial_capital=100000.0, commission=0.001):
        self.data = data
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.signals = None
        self.portfolio = None
        self.position_size = 0  # Number of shares per trade
    
    def set_position_sizing(self, method='fixed_dollar', value=10000):
        """
        Set position sizing method:
        - fixed_dollar: Fixed dollar amount per trade
        - percentage: Percentage of portfolio per trade
        - fixed_risk: Fixed percentage risk per trade
        - fixed_shares: Fixed number of shares per trade
        """
        self.position_sizing_method = method
        self.position_sizing_value = value
    
    def run_backtest(self):
        """Execute backtest based on the strategy"""
        # Generate trading signals
        self.signals = self.strategy.generate_signals(self.data)
        
        # Create a portfolio dataframe
        self.portfolio = self.signals.copy()
        
        # Initialize portfolio metrics
        self.portfolio['position'] = 0.0
        self.portfolio['holdings'] = 0.0
        self.portfolio['cash'] = self.initial_capital
        self.portfolio['total'] = self.initial_capital
        self.portfolio['returns'] = 0.0
        
        # Iterate through each point in time
        for t in range(1, len(self.portfolio)):
            # Default current time values to previous time values
            self.portfolio.iloc[t, self.portfolio.columns.get_loc('position')] = self.portfolio.iloc[t-1]['position']
            self.portfolio.iloc[t, self.portfolio.columns.get_loc('cash')] = self.portfolio.iloc[t-1]['cash']
            
            # Check for buy/sell signals
            pos_diff = self.portfolio.iloc[t]['positions']
            
            # Handle position sizing
            if pos_diff != 0:
                # Get current price
                current_price = self.portfolio.iloc[t]['close']
                
                if self.position_sizing_method == 'fixed_dollar':
                    # Fixed dollar amount per trade
                    trade_value = self.position_sizing_value
                    shares = int(trade_value / current_price)
                elif self.position_sizing_method == 'percentage':
                    # Percentage of portfolio
                    trade_value = self.portfolio.iloc[t-1]['total'] * (self.position_sizing_value / 100)
                    shares = int(trade_value / current_price)
                elif self.position_sizing_method == 'fixed_risk':
                    # Fixed percentage risk - simplistic implementation
                    trade_value = self.portfolio.iloc[t-1]['total'] * (self.position_sizing_value / 100)
                    shares = int(trade_value / current_price)
                else:  # fixed_shares
                    shares = self.position_sizing_value
                
                # Buy signal
                if pos_diff > 0:
                    self.portfolio.iloc[t, self.portfolio.columns.get_loc('position')] += shares
                    trade_cost = shares * current_price * (1 + self.commission)
                    self.portfolio.iloc[t, self.portfolio.columns.get_loc('cash')] -= trade_cost
                
                # Sell signal
                elif pos_diff < 0 and self.portfolio.iloc[t-1]['position'] > 0:
                    # Limit selling to actual position size
                    shares_to_sell = min(shares, self.portfolio.iloc[t-1]['position'])
                    self.portfolio.iloc[t, self.portfolio.columns.get_loc('position')] -= shares_to_sell
                    trade_proceeds = shares_to_sell * current_price * (1 - self.commission)
                    self.portfolio.iloc[t, self.portfolio.columns.get_loc('cash')] += trade_proceeds
            
            # Calculate holdings value
            self.portfolio.iloc[t, self.portfolio.columns.get_loc('holdings')] = \
                self.portfolio.iloc[t]['position'] * self.portfolio.iloc[t]['close']
                
            # Calculate total portfolio value
            self.portfolio.iloc[t, self.portfolio.columns.get_loc('total')] = \
                self.portfolio.iloc[t]['holdings'] + self.portfolio.iloc[t]['cash']
                
            # Calculate returns
            self.portfolio.iloc[t, self.portfolio.columns.get_loc('returns')] = \
                self.portfolio.iloc[t]['total'] / self.portfolio.iloc[t-1]['total'] - 1
        
        return self.portfolio
    
    def get_performance_metrics(self):
        """Calculate performance metrics from the backtest results"""
        if self.portfolio is None:
            return {}
        
        # Calculate annualized Sharpe ratio
        sharpe_ratio = np.sqrt(252) * (self.portfolio['returns'].mean() / self.portfolio['returns'].std())
        
        # Calculate maximum drawdown
        cum_returns = (1 + self.portfolio['returns']).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns / running_max - 1)
        max_drawdown = drawdown.min()
        
        # Calculate total return
        total_return = (self.portfolio['total'].iloc[-1] / self.initial_capital - 1) * 100
        
        # Calculate annualized return
        n_days = (self.portfolio.index[-1] - self.portfolio.index[0]).days
        if n_days > 0:
            annualized_return = ((1 + total_return/100) ** (365.0/n_days) - 1) * 100
        else:
            annualized_return = 0
        
        # Calculate trade metrics
        trades = self.portfolio[self.portfolio['positions'] != 0]
        buy_trades = trades[trades['positions'] > 0]
        sell_trades = trades[trades['positions'] < 0]
        
        trade_performance = {
            'total_trades': len(buy_trades) + len(sell_trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades)
        }
        
        # Calculate win/loss ratio and profit factor if we have complete trades
        if len(buy_trades) > 0 and len(sell_trades) > 0:
            # This is a simplified approach, actual implementation would need to match buy/sell pairs
            trade_returns = []
            
            # Extract points where we have position changes
            position_changes = self.portfolio[self.portfolio['positions'] != 0].copy()
            
            # Define variables to keep track of trades
            in_trade = False
            entry_price = 0
            entry_time = None
            
            # Go through all position changes
            for i, row in position_changes.iterrows():
                # Buy signal
                if row['positions'] > 0 and not in_trade:
                    in_trade = True
                    entry_price = row['close']
                    entry_time = i
                
                # Sell signal
                elif row['positions'] < 0 and in_trade:
                    exit_price = row['close']
                    exit_time = i
                    
                    # Calculate trade return
                    trade_return = (exit_price / entry_price - 1) * 100
                    
                    # Store trade information
                    trade_returns.append({
                        'entry_time': entry_time,
                        'exit_time': exit_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'return': trade_return,
                        'profitable': trade_return > 0
                    })
                    
                    in_trade = False
            
            # Calculate trade statistics
            if trade_returns:
                trade_df = pd.DataFrame(trade_returns)
                winning_trades = trade_df[trade_df['profitable']].shape[0]
                losing_trades = trade_df[~trade_df['profitable']].shape[0]
                
                win_rate = winning_trades / len(trade_df) * 100 if len(trade_df) > 0 else 0
                
                avg_win = trade_df[trade_df['profitable']]['return'].mean() if winning_trades > 0 else 0
                avg_loss = trade_df[~trade_df['profitable']]['return'].mean() if losing_trades > 0 else 0
                
                profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if losing_trades > 0 and avg_loss < 0 else float('inf')
                
                trade_performance.update({
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'profit_factor': profit_factor
                })
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown * 100,
            'final_equity': self.portfolio['total'].iloc[-1],
            'trade_metrics': trade_performance
        }['close'].rolling(window=self.short_window).mean()
        signals['long_ma'] = signals['close'].rolling(window=self.long_window).mean()
        
        # Create signals
        signals['signal'][self.long_window:] = np.where(
            signals['short_ma'][self.long_window:] > signals['long_ma'][self.long_window:], 1.0, 0.0
        )
        
        # Generate trading orders
        signals['positions'] = signals['signal'].diff()
        
        return signals


class RSIStrategy(Strategy):
    """RSI Overbought/Oversold Strategy"""
    def __init__(self, rsi_period=14, overbought=70, oversold=30):
        super().__init__("RSI Strategy")
        self.rsi_period = rsi_period
        self.overbought = overbought
        self.oversold = oversold
    
    def generate_signals(self, data):
        """Generate buy/sell signals based on RSI values"""
        # Make a copy of the data
        signals = data.copy()
        
        # Ensure RSI is calculated
        if 'RSI' not in signals.columns:
            signals = add_technical_indicators(signals)
            
        # Create signals dataframe
        signals['signal'] = 0.0
        
        # Generate buy signal when RSI crosses below oversold level
        signals['signal'] = np.where(signals['RSI'] < self.oversold, 1.0, 0.0)
        
        # Generate sell signal when RSI crosses above overbought level
        signals['signal'] = np.where(signals['RSI'] > self.overbought, -1.0, signals['signal'])
        
        # Generate trading orders
        signals['positions'] = signals['signal'].diff()
        
        return signals


class MACDStrategy(Strategy):
    """MACD Crossover Strategy"""
    def __init__(self):
        super().__init__("MACD Strategy")
    
    def generate_signals(self, data):
        """Generate buy/sell signals based on MACD crossover"""
        # Make a copy of the data
        signals = data.copy()
        
        # Ensure MACD is calculated
        if 'MACD' not in signals.columns or 'Signal' not in signals.columns:
            signals = add_technical_indicators(signals)
        
        # Create signals dataframe
        signals['signal'] = 0.0
        
        # Generate buy signal when MACD crosses above signal line
        signals['signal'] = np.where(
            (signals['MACD'] > signals['Signal']) & 
            (signals['MACD'].shift(1) <= signals['Signal'].shift(1)),
            1.0, 0.0
        )
        
        # Generate sell signal when MACD crosses below signal line
        signals['signal'] = np.where(
            (signals['MACD'] < signals['Signal']) & 
            (signals['MACD'].shift(1) >= signals['Signal'].shift(1)),
            -1.0, signals['signal']
        )
        
        # Generate trading orders
        signals['positions'] = signals['signal'].diff()
        
        return signals


class MAWithRSIStrategy(Strategy):
    """Moving Average Crossover Strategy with RSI Filter"""
    def __init__(self, short_window=20, long_window=50, rsi_buy=30, rsi_sell=70):
        super().__init__("MA with RSI Filter")
        self.short_window = short_window
        self.long_window = long_window
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell
    
    def generate_signals(self, data):
        """
        Generate buy/sell signals based on MA crossover with RSI filter.
        Buy when MA_short > MA_long and RSI < rsi_buy.
        Sell when MA_short < MA_long and RSI > rsi_sell.
        """
        # Make a copy of the data
        signals = data.copy()
        
        # Ensure RSI and MA are calculated
        if 'RSI' not in signals.columns:
            signals = add_technical_indicators(signals)
        
        signals['short_ma'] = signals