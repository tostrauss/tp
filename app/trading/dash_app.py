# app/trading/dash_app.py
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from numpy import nan as npNaN
import datetime
from flask_login import current_user
from app.helpers.data_fetcher import fetch_stock_data
from app.helpers.options_calc import (
    get_option_chain, black_scholes_greeks, calculate_option_profit_loss,
    calculate_option_breakeven, binomial_option_price
)

def create_dash_app(flask_app):
    """
    Create a Dash app for options trading that's integrated with the Flask app.
    """
    # Create Dash app with Bootstrap styling
    dash_app = dash.Dash(
        server=flask_app,
        url_base_pathname='/trading/dashboard/',
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
    )
    
    # Update title
    dash_app.title = "ToFu's Options Trading Platform"
    
    # Define the layout
    dash_app.layout = html.Div([
        # Hidden divs for storing data
        dcc.Store(id="options-store", data={}),
        
        # Main content
        dbc.Container([
            # Tabs for different trading tools
            dbc.Tabs([
                # Options Chain Tab
                dbc.Tab(label="Options Chain", tab_id="tab-options", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Enter Stock Ticker"),
                            dcc.Input(id="option-ticker-input", type="text", value="AAPL", className="form-control mb-2"),
                            dbc.Button("Get Option Chain", id="get-option-chain", color="primary", className="mb-3")
                        ], md=4),
                        dbc.Col([
                            html.Div(id="expiration-div", children=[
                                dbc.Label("Select Expiration Date"),
                                dcc.Dropdown(id="expiration-dropdown", className="mb-3")
                            ])
                        ], md=4),
                        dbc.Col([
                            html.Div(id="option-summary", className="mt-4")
                        ], md=4)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col(html.Div(id="options-output"))
                    ])
                ]),
                
                # Options Calculator Tab
                dbc.Tab(label="Options Calculator", tab_id="tab-calculator", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Option Parameters"),
                                dbc.CardBody([
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Label("Option Type"),
                                            dcc.Dropdown(
                                                id="calc-option-type",
                                                options=[
                                                    {"label": "Call Option", "value": "call"},
                                                    {"label": "Put Option", "value": "put"}
                                                ],
                                                value="call",
                                                className="mb-2"
                                            )
                                        ]),
                                        dbc.Col([
                                            dbc.Label("Contract Style"),
                                            dcc.Dropdown(
                                                id="calc-contract-style",
                                                options=[
                                                    {"label": "European", "value": "european"},
                                                    {"label": "American", "value": "american"}
                                                ],
                                                value="european",
                                                className="mb-2"
                                            )
                                        ])
                                    ]),
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Label("Underlying Price (S)"),
                                            dcc.Input(id="calc-stock-price", type="number", value=100, className="form-control mb-2")
                                        ]),
                                        dbc.Col([
                                            dbc.Label("Strike Price (K)"),
                                            dcc.Input(id="calc-strike-price", type="number", value=100, className="form-control mb-2")
                                        ])
                                    ]),
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Label("Days to Expiration"),
                                            dcc.Input(id="calc-days", type="number", value=30, className="form-control mb-2")
                                        ]),
                                        dbc.Col([
                                            dbc.Label("Risk-Free Rate (%)"),
                                            dcc.Input(id="calc-rate", type="number", value=1.0, step=0.1, className="form-control mb-2")
                                        ])
                                    ]),
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Label("Implied Volatility (%)"),
                                            dcc.Input(id="calc-volatility", type="number", value=25.0, step=0.1, className="form-control mb-2")
                                        ]),
                                        dbc.Col([
                                            dbc.Label("Number of Contracts"),
                                            dcc.Input(id="calc-contracts", type="number", value=1, min=1, className="form-control mb-2")
                                        ])
                                    ]),
                                    dbc.Button("Calculate Option", id="calculate-option", color="primary", className="w-100 mt-2")
                                ])
                            ])
                        ], md=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Option Pricing Results"),
                                dbc.CardBody([
                                    html.Div(id="option-pricing-results")
                                ])
                            ], className="mb-3"),
                            dbc.Card([
                                dbc.CardHeader("Option Greeks"),
                                dbc.CardBody([
                                    html.Div(id="option-greeks-results")
                                ])
                            ])
                        ], md=6)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Profit/Loss Analysis"),
                                dbc.CardBody([
                                    dcc.Graph(id="option-pl-chart")
                                ])
                            ])
                        ])
                    ])
                ]),
                
                # Risk/Reward Calculator Tab
                dbc.Tab(label="Risk/Reward Calculator", tab_id="tab-risk-reward", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Trade Parameters"),
                                dbc.CardBody([
                                    dbc.Label("Select Trade Type"),
                                    dcc.Dropdown(
                                        id="trade-type",
                                        options=[
                                            {"label": "Long Stock", "value": "long"},
                                            {"label": "Short Stock", "value": "short"}
                                        ],
                                        value="long",
                                        className="mb-2"
                                    ),
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Label("Entry Price"),
                                            dcc.Input(id="entry-price", type="number", value=100.0, className="form-control mb-2")
                                        ]),
                                        dbc.Col([
                                            dbc.Label("Stop Loss Price"),
                                            dcc.Input(id="stop-loss", type="number", value=95.0, className="form-control mb-2")
                                        ])
                                    ]),
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Label("Target Price"),
                                            dcc.Input(id="target-price", type="number", value=110.0, className="form-control mb-2")
                                        ]),
                                        dbc.Col([
                                            dbc.Label("Position Size (shares)"),
                                            dcc.Input(id="position-size", type="number", value=100, min=1, className="form-control mb-2")
                                        ])
                                    ]),
                                    dbc.Button("Calculate Risk/Reward", id="calc-risk-reward", color="primary", className="w-100 mt-2")
                                ])
                            ])
                        ], md=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Risk/Reward Results"),
                                dbc.CardBody([
                                    html.Div(id="risk-reward-output", className="mb-3"),
                                    dcc.Graph(id="risk-reward-chart")
                                ])
                            ])
                        ], md=6)
                    ])
                ]),
                
                # Crypto Trading Tab
                dbc.Tab(label="Crypto Analysis", tab_id="tab-crypto", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Enter Crypto Ticker (e.g., BTC-USD, ETH-USD)"),
                            dcc.Input(id="crypto-ticker", type="text", value="BTC-USD", className="form-control mb-2")
                        ], md=3),
                        dbc.Col([
                            dbc.Label("Select Data Period"),
                            dcc.Dropdown(
                                id="crypto-period",
                                options=[{"label": p, "value": p} for p in ["1d", "5d", "1mo", "3mo", "6mo", "1y"]],
                                value="1mo",
                                className="mb-2"
                            )
                        ], md=3),
                        dbc.Col([
                            dbc.Label("Select Data Interval"),
                            dcc.Dropdown(
                                id="crypto-interval",
                                options=[{"label": id, "value": id} for p in ["1m", "5m", "15m", "30m", "1h", "1d"]],
                                value="1d",
                                className="mb-2"
                            )
                        ], md=3),
                        dbc.Col([
                            dbc.Button("Analyze Crypto", id="analyze-crypto", color="primary", className="mt-4")
                        ], md=3)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col(html.Div(id="crypto-output")),
                    ]),
                    dbc.Row([
                        dbc.Col(dcc.Graph(id="crypto-chart"))
                    ])
                ])
            ], id="trading-tabs", active_tab="tab-options", className="mb-3")
        ], fluid=True)
    ])
    
    # Define callbacks
    @dash_app.callback(
        [Output("expiration-div", "children"),
         Output("options-store", "data")],
        Input("get-option-chain", "n_clicks"),
        State("option-ticker-input", "value")
    )
    def update_expiration_dropdown(n_clicks, ticker):
        """Update the expiration date dropdown when an option chain is requested."""
        if not n_clicks:
            return [
                dbc.Label("Select Expiration Date"),
                dcc.Dropdown(id="expiration-dropdown", className="mb-3")
            ], {}
        
        # Get option chain data
        calls, puts, exp_selected, expirations = get_option_chain(ticker)
        
        if not expirations:
            return [
                dbc.Label("Select Expiration Date"),
                dcc.Dropdown(id="expiration-dropdown", className="mb-3"),
                html.P("No expiration dates available for this ticker.", className="text-danger")
            ], {}
        
        # Store data for future use
        store_data = {
            "ticker": ticker,
            "expirations": expirations,
            "current_expiration": exp_selected
        }
        
        # Create dropdown with available expirations
        dropdown = [
            dbc.Label("Select Expiration Date"),
            dcc.Dropdown(
                id="expiration-dropdown",
                options=[{"label": exp, "value": exp} for exp in expirations],
                value=exp_selected,
                className="mb-3"
            )
        ]
        
        return dropdown, store_data
    
    @dash_app.callback(
        [Output("options-output", "children"),
         Output("option-summary", "children")],
        [Input("expiration-dropdown", "value")],
        [State("option-ticker-input", "value"),
         State("options-store", "data")]
    )
    def update_options_chain(expiration, ticker, store_data):
        """Update the options chain table and graphs when an expiration date is selected."""
        if not expiration or not ticker:
            return html.P("Please select an expiration date."), ""
        
        # Get option chain data for the selected expiration
        calls, puts, _, _ = get_option_chain(ticker, expiration)
        
        if calls is None or puts is None:
            return html.P(f"No options data available for {ticker} on {expiration}."), ""
        
        # Format data for tables
        calls_table = dash_table.DataTable(
            id="calls-table",
            data=calls.to_dict("records"),
            columns=[{"name": i, "id": i} for i in calls.columns],
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={
                'textAlign': 'center',
                'padding': '5px'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold',
                'border': '1px solid black'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ],
            tooltip_data=[
                {
                    column: {'value': f'{value}', 'type': 'markdown'}
                    for column, value in row.items()
                } for row in calls.to_dict('records')
            ],
            tooltip_duration=None
        )
        
        puts_table = dash_table.DataTable(
            id="puts-table",
            data=puts.to_dict("records"),
            columns=[{"name": i, "id": i} for i in puts.columns],
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={
                'textAlign': 'center',
                'padding': '5px'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold',
                'border': '1px solid black'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ],
            tooltip_data=[
                {
                    column: {'value': f'{value}', 'type': 'markdown'}
                    for column, value in row.items()
                } for row in puts.to_dict('records')
            ],
            tooltip_duration=None
        )
        
        # Create a figure to visualize the option chain
        # Get the current stock price
        try:
            current_price = calls["BS_Price"].iloc[0] + calls["strike"].iloc[0] - calls["Delta"].iloc[0] * calls["strike"].iloc[0]
        except:
            try:
                current_price = puts["BS_Price"].iloc[0] + puts["strike"].iloc[0] - (1 + puts["Delta"].iloc[0]) * puts["strike"].iloc[0]
            except:
                current_price = 0
        
        # Create a plot of option prices vs. strike prices
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Call Options", "Put Options"), vertical_spacing=0.1)
        
        # Add call options data if available
        if not calls.empty:
            fig.add_trace(
                go.Scatter(
                    x=calls["strike"],
                    y=calls["lastPrice"],
                    mode="markers",
                    name="Call Last Price",
                    marker=dict(color="green", size=8)
                ),
                row=1, col=1
            )
            
            # Add theoretical prices
            fig.add_trace(
                go.Scatter(
                    x=calls["strike"],
                    y=calls["BS_Price"],
                    mode="lines",
                    name="Call BS Price",
                    line=dict(color="green", dash="dash")
                ),
                row=1, col=1
            )
        
        # Add put options data if available
        if not puts.empty:
            fig.add_trace(
                go.Scatter(
                    x=puts["strike"],
                    y=puts["lastPrice"],
                    mode="markers",
                    name="Put Last Price",
                    marker=dict(color="red", size=8)
                ),
                row=2, col=1
            )
            
            # Add theoretical prices
            fig.add_trace(
                go.Scatter(
                    x=puts["strike"],
                    y=puts["BS_Price"],
                    mode="lines",
                    name="Put BS Price",
                    line=dict(color="red", dash="dash")
                ),
                row=2, col=1
            )
        
        # Add vertical line for current stock price
        if current_price > 0:
            fig.add_vline(x=current_price, line_dash="dash", line_color="blue", 
                         annotation_text=f"Current: ${current_price:.2f}", row=1, col=1)
            fig.add_vline(x=current_price, line_dash="dash", line_color="blue", row=2, col=1)
        
        # Update layout
        fig.update_layout(
            height=600,
            title_text=f"Option Chain for {ticker} - Expiration: {expiration}",
            showlegend=True
        )
        
        # Create the output
        chain_display = html.Div([
            dbc.Tabs([
                dbc.Tab(label="Call Options", tab_id="tab-calls", children=[
                    calls_table
                ]),
                dbc.Tab(label="Put Options", tab_id="tab-puts", children=[
                    puts_table
                ])
            ], id="options-chain-tabs", active_tab="tab-calls", className="mb-3"),
            dcc.Graph(figure=fig)
        ])
        
        # Create summary information
        days_to_expiration = (datetime.datetime.strptime(expiration, "%Y-%m-%d") - datetime.datetime.now()).days
        
        summary = html.Div([
            html.H5(f"{ticker} Options Summary", className="text-primary"),
            html.P(f"Expiration Date: {expiration}", className="mb-1"),
            html.P(f"Days to Expiration: {days_to_expiration}", className="mb-1"),
            html.P(f"Current Price: ${current_price:.2f}", className="mb-1"),
            html.P(f"Number of Calls: {len(calls)}", className="mb-1"),
            html.P(f"Number of Puts: {len(puts)}", className="mb-1")
        ])
        
        return chain_display, summary
    
    @dash_app.callback(
        [Output("option-pricing-results", "children"),
         Output("option-greeks-results", "children"),
         Output("option-pl-chart", "figure")],
        Input("calculate-option", "n_clicks"),
        [State("calc-option-type", "value"),
         State("calc-contract-style", "value"),
         State("calc-stock-price", "value"),
         State("calc-strike-price", "value"),
         State("calc-days", "value"),
         State("calc-rate", "value"),
         State("calc-volatility", "value"),
         State("calc-contracts", "value")]
    )
    def calculate_option_results(n_clicks, option_type, contract_style, stock_price, strike_price, days, rate, volatility, contracts):
        """Calculate and display option pricing results and P/L chart."""
        if not n_clicks:
            # Return empty results
            empty_fig = go.Figure()
            empty_fig.update_layout(title="Please calculate option to see P/L chart")
            return "", "", empty_fig
        
        # Convert inputs to proper format
        S = float(stock_price)
        K = float(strike_price)
        T = float(days) / 365.0  # Convert days to years
        r = float(rate) / 100.0  # Convert percentage to decimal
        sigma = float(volatility) / 100.0  # Convert percentage to decimal
        is_american = contract_style == "american"
        
        # Calculate option price and Greeks
        delta, gamma, theta, vega, rho, bs_price = black_scholes_greeks(S, K, T, r, sigma, option_type)
        
        # Calculate American option price if selected
        if is_american:
            american_price = binomial_option_price(S, K, T, r, sigma, 50, option_type, american=True)
        else:
            american_price = bs_price
        
        # Calculate breakeven
        breakeven = calculate_option_breakeven(K, bs_price, option_type)
        
        # Calculate P/L at different prices
        pl_results = calculate_option_profit_loss(S, K, bs_price, option_type)
        
        # Create pricing results display
        pricing_results = html.Div([
            html.H5("Option Price", className="text-primary mb-2"),
            html.P(f"European Price (Black-Scholes): ${bs_price:.2f} per share", className="mb-1"),
            html.P(f"American Price (Binomial): ${american_price:.2f} per share", className="mb-1"),
            html.P(f"Total Premium (per contract): ${bs_price * 100:.2f}", className="mb-1"),
            html.P(f"Total Premium (all contracts): ${bs_price * 100 * contracts:.2f}", className="mb-1"),
            html.Hr(),
            html.H5("Key Metrics", className="text-primary mb-2"),
            html.P(f"Breakeven Price: ${breakeven:.2f}", className="mb-1"),
            html.P(f"Maximum Risk: ${bs_price * 100 * contracts:.2f}", className="mb-1"),
            html.P(f"Potential Profit: {'Unlimited' if option_type == 'call' else f'${(K - bs_price) * 100 * contracts:.2f}'}" if option_type == 'call' else f"Potential Profit: {'${(K - bs_price) * 100 * contracts:.2f}' if bs_price < K else 'Limited'}", className="mb-1"),
        ])
        
        # Create Greeks display
        greeks_results = html.Div([
            html.H5("Option Greeks", className="text-primary mb-2"),
            html.P(f"Delta: {delta:.4f}", className="mb-1"),
            html.P(f"Gamma: {gamma:.4f}", className="mb-1"),
            html.P(f"Theta: {theta:.4f} (per day)", className="mb-1"),
            html.P(f"Vega: {vega:.4f} (per 1% change in volatility)", className="mb-1"),
            html.P(f"Rho: {rho:.4f} (per 1% change in interest rate)", className="mb-1"),
            html.Hr(),
            html.H5("Interpretation", className="text-primary mb-2"),
            html.P(f"Delta indicates that for a $1 move in the underlying, the option price will change by ${delta:.2f}.", className="mb-1"),
            html.P(f"Theta indicates the option loses ${abs(theta):.2f} in value each day, all else equal.", className="mb-1"),
        ])
        
        # Create P/L chart
        fig = go.Figure()
        
        # Plot the profit/loss line
        fig.add_trace(go.Scatter(
            x=pl_results['price'],
            y=pl_results['total_payoff'] * contracts,
            mode='lines',
            name='P/L at Expiration',
            line=dict(color='blue')
        ))
        
        # Add horizontal line at y=0 (break-even line)
        fig.add_hline(y=0, line=dict(color='black', dash='dash'))
        
        # Add vertical line at current stock price
        fig.add_vline(x=S, line=dict(color='red', dash='dash'), annotation_text=f"Current: ${S}")
        
        # Add vertical line at strike price
        fig.add_vline(x=K, line=dict(color='green', dash='dash'), annotation_text=f"Strike: ${K}")
        
        # Add vertical line at breakeven
        fig.add_vline(x=breakeven, line=dict(color='purple', dash='dash'), annotation_text=f"Breakeven: ${breakeven:.2f}")
        
        # Update layout
        fig.update_layout(
            title=f"{option_type.capitalize()} Option P/L at Expiration (Stock Price vs P/L)",
            xaxis_title="Stock Price at Expiration",
            yaxis_title="Profit/Loss ($)",
            height=500,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        return pricing_results, greeks_results, fig
    
    @dash_app.callback(
        [Output("risk-reward-output", "children"),
         Output("risk-reward-chart", "figure")],
        Input("calc-risk-reward", "n_clicks"),
        [State("trade-type", "value"),
         State("entry-price", "value"),
         State("stop-loss", "value"),
         State("target-price", "value"),
         State("position-size", "value")]
    )
    def update_risk_reward(n_clicks, trade_type, entry, stop, target, pos_size):
        """Calculate and display risk/reward metrics and chart."""
        if not n_clicks:
            empty_fig = go.Figure()
            empty_fig.update_layout(title="Please calculate risk/reward to see chart")
            return "", empty_fig
        
        # Convert inputs to proper format
        entry = float(entry)
        stop = float(stop)
        target = float(target)
        pos_size = int(pos_size)
        
        # Calculate risk and reward based on trade type
        if trade_type == "long":
            risk_per_share = entry - stop
            reward_per_share = target - entry
            if risk_per_share <= 0:
                error_msg = "Invalid parameters: Stop loss must be below entry price for long trades."
                empty_fig = go.Figure()
                empty_fig.update_layout(title="Error in parameters")
                return html.P(error_msg, className="text-danger"), empty_fig
        else:  # short
            risk_per_share = stop - entry
            reward_per_share = entry - target
            if risk_per_share <= 0:
                error_msg = "Invalid parameters: Stop loss must be above entry price for short trades."
                empty_fig = go.Figure()
                empty_fig.update_layout(title="Error in parameters")
                return html.P(error_msg, className="text-danger"), empty_fig
        
        # Calculate metrics
        risk_reward_ratio = reward_per_share / risk_per_share
        total_risk = risk_per_share * pos_size
        total_reward = reward_per_share * pos_size
        probability_required = 1 / (1 + risk_reward_ratio)
        
        # Create results display
        results = html.Div([
            html.H5("Risk/Reward Analysis", className="text-primary mb-2"),
            html.P(f"Trade Type: {trade_type.capitalize()}", className="mb-1"),
            html.P(f"Entry Price: ${entry:.2f}", className="mb-1"),
            html.P(f"Stop Loss: ${stop:.2f}", className="mb-1"),
            html.P(f"Target Price: ${target:.2f}", className="mb-1"),
            html.P(f"Position Size: {pos_size} shares", className="mb-1"),
            html.Hr(),
            html.H5("Risk/Reward Metrics", className="text-primary mb-2"),
            html.P(f"Risk per Share: ${risk_per_share:.2f}", className="mb-1"),
            html.P(f"Reward per Share: ${reward_per_share:.2f}", className="mb-1"),
            html.P(f"Risk/Reward Ratio: 1:{risk_reward_ratio:.2f}", className="mb-1"),
            html.P(f"Total Risk: ${total_risk:.2f}", className="mb-1"),
            html.P(f"Total Potential Profit: ${total_reward:.2f}", className="mb-1"),
            html.P(f"Win Rate Required to Break Even: {probability_required*100:.1f}%", className="mb-1")
        ])
        
        # Create P/L chart
        # Generate a range of prices for x-axis
        min_price = min(entry, stop, target) * 0.95
        max_price = max(entry, stop, target) * 1.05
        prices = np.linspace(min_price, max_price, 100)
        
        # Calculate P/L at each price point
        if trade_type == "long":
            pl = [(price - entry) * pos_size for price in prices]
        else:  # short
            pl = [(entry - price) * pos_size for price in prices]
        
        # Create the figure
        fig = go.Figure()
        
        # Add P/L line
        fig.add_trace(go.Scatter(
            x=prices,
            y=pl,
            mode='lines',
            name='P/L',
            line=dict(color='blue')
        ))
        
        # Add horizontal line at y=0 (break-even line)
        fig.add_hline(y=0, line=dict(color='black', dash='dash'))
        
        # Add vertical lines for key prices
        fig.add_vline(x=entry, line=dict(color='blue', dash='dash'), annotation_text=f"Entry: ${entry}")
        fig.add_vline(x=stop, line=dict(color='red', dash='dash'), annotation_text=f"Stop: ${stop}")
        fig.add_vline(x=target, line=dict(color='green', dash='dash'), annotation_text=f"Target: ${target}")
        
        # Update layout
        fig.update_layout(
            title=f"{trade_type.capitalize()} Trade Risk/Reward Analysis",
            xaxis_title="Price",
            yaxis_title="Profit/Loss ($)",
            height=400,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        return results, fig
    
    @dash_app.callback(
        [Output("crypto-output", "children"),
         Output("crypto-chart", "figure")],
        Input("analyze-crypto", "n_clicks"),
        [State("crypto-ticker", "value"),
         State("crypto-period", "value"),
         State("crypto-interval", "value")]
    )
    def analyze_crypto(n_clicks, ticker, period, interval):
        """Analyze crypto and display chart."""
        if not n_clicks:
            empty_fig = go.Figure()
            empty_fig.update_layout(title="Click Analyze Crypto to see chart")
            return "", empty_fig
        
        try:
            # Fetch data
            data = fetch_stock_data(ticker, period, interval)
            if data.empty:
                return html.P(f"No data returned for {ticker}", className="text-danger"), go.Figure()
            
            # Create data table
            table = dash_table.DataTable(
                data=data.tail(10).reset_index().to_dict("records"),
                columns=[{"name": i, "id": i} for i in data.tail(10).reset_index().columns],
                page_size=10,
                style_table={"overflowX": "auto"},
                style_cell={
                    'textAlign': 'center',
                    'padding': '5px'
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                }
            )
            
            # Create chart
            fig = go.Figure()
            
            # Add candlestick chart
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data["open"],
                high=data["high"],
                low=data["low"],
                close=data["close"],
                name="OHLC"
            ))
            
            # Add volume bars
            fig.add_trace(go.Bar(
                x=data.index,
                y=data["volume"],
                name="Volume",
                marker_color="rgba(0, 0, 128, 0.3)",
                yaxis="y2"
            ))
            
            # Update layout
            fig.update_layout(
                title=f"{ticker} Price Chart",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                yaxis2=dict(
                    title="Volume",
                    overlaying="y",
                    side="right",
                    showgrid=False
                ),
                height=600,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            
            return table, fig
        except Exception as e:
            return html.P(f"Error analyzing {ticker}: {str(e)}", className="text-danger"), go.Figure()
    
    return dash_app