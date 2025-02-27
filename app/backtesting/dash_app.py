# app/backtesting/dash_app.py
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import datetime
from flask_login import current_user
from app.helpers.data_fetcher import fetch_stock_data
from app.backtesting.backtest_engine import MovingAverageCrossStrategy, RSIStrategy, MACDStrategy, MAWithRSIStrategy, Backtester

def create_dash_app(flask_app):
    """
    Create a Dash app for backtesting that's integrated with the Flask app.
    """
    # Create Dash app with Bootstrap styling
    dash_app = dash.Dash(
        server=flask_app,
        url_base_pathname='/backtesting/dashboard/',
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
    )
    
    # Update title
    dash_app.title = "ToFu's Backtesting Platform"
    
    # Define the layout
    dash_app.layout = html.Div([
        # Hidden divs for storing data
        dcc.Store(id="backtest-results-store", data={}),
        
        # Main content
        dbc.Container([
            dbc.Row(dbc.Col(html.H2("Strategy Backtesting", className="text-primary mb-3"))),
            
            # Strategy Selection and Parameters
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Strategy Selection"),
                        dbc.CardBody([
                            dbc.Label("Select Strategy"),
                            dcc.Dropdown(
                                id="strategy-dropdown",
                                options=[
                                    {"label": "Moving Average Crossover", "value": "ma_cross"},
                                    {"label": "RSI Overbought/Oversold", "value": "rsi"},
                                    {"label": "MACD Crossover", "value": "macd"},
                                    {"label": "MA with RSI Filter", "value": "ma_rsi"}
                                ],
                                value="ma_cross",
                                className="mb-3"
                            ),
                            
                            # Moving Average Parameters
                            html.Div(id="ma-params", children=[
                                dbc.Label("Short Moving Average Window"),
                                dcc.Input(id="ma-short", type="number", value=20, min=1, max=200, step=1, className="form-control mb-2"),
                                dbc.Label("Long Moving Average Window"),
                                dcc.Input(id="ma-long", type="number", value=50, min=5, max=500, step=1, className="form-control")
                            ]),
                            
                            # RSI Parameters
                            html.Div(id="rsi-params", style={"display": "none"}, children=[
                                dbc.Label("RSI Period"),
                                dcc.Input(id="rsi-period", type="number", value=14, min=1, max=50, step=1, className="form-control mb-2"),
                                dbc.Label("Overbought Level"),
                                dcc.Input(id="rsi-overbought", type="number", value=70, min=50, max=90, step=1, className="form-control mb-2"),
                                dbc.Label("Oversold Level"),
                                dcc.Input(id="rsi-oversold", type="number", value=30, min=10, max=50, step=1, className="form-control")
                            ]),
                            
                            # MA + RSI Parameters
                            html.Div(id="ma-rsi-params", style={"display": "none"}, children=[
                                dbc.Label("Short Moving Average Window"),
                                dcc.Input(id="ma-rsi-short", type="number", value=20, min=1, max=200, step=1, className="form-control mb-2"),
                                dbc.Label("Long Moving Average Window"),
                                dcc.Input(id="ma-rsi-long", type="number", value=50, min=5, max=500, step=1, className="form-control mb-2"),
                                dbc.Label("RSI Buy Level"),
                                dcc.Input(id="ma-rsi-buy", type="number", value=30, min=10, max=50, step=1, className="form-control mb-2"),
                                dbc.Label("RSI Sell Level"),
                                dcc.Input(id="ma-rsi-sell", type="number", value=70, min=50, max=90, step=1, className="form-control")
                            ])
                        ])
                    ], className="mb-3")
                ], md=4),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Backtest Settings"),
                        dbc.CardBody([
                            dbc.Label("Stock Ticker"),
                            dcc.Input(id="backtest-ticker", type="text", value="AAPL", className="form-control mb-2"),
                            
                            dbc.Label("Data Period"),
                            dcc.Dropdown(
                                id="backtest-period",
                                options=[
                                    {"label": "1 Month", "value": "1mo"},
                                    {"label": "3 Months", "value": "3mo"},
                                    {"label": "6 Months", "value": "6mo"},
                                    {"label": "1 Year", "value": "1y"},
                                    {"label": "2 Years", "value": "2y"},
                                    {"label": "5 Years", "value": "5y"},
                                    {"label": "10 Years", "value": "10y"},
                                    {"label": "Max", "value": "max"}
                                ],
                                value="1y",
                                className="mb-3"
                            ),
                            
                            dbc.Label("Data Interval"),
                            dcc.Dropdown(
                                id="backtest-interval",
                                options=[
                                    {"label": "1 Day", "value": "1d"},
                                    {"label": "1 Week", "value": "1wk"},
                                    {"label": "1 Month", "value": "1mo"}
                                ],
                                value="1d",
                                className="mb-3"
                            ),
                            
                            dbc.Label("Initial Capital"),
                            dcc.Input(id="initial-capital", type="number", value=100000, min=1000, className="form-control mb-2"),
                            
                            dbc.Label("Position Sizing"),
                            dcc.Dropdown(
                                id="position-sizing",
                                options=[
                                    {"label": "Fixed Dollar Amount", "value": "fixed_dollar"},
                                    {"label": "Percentage of Portfolio", "value": "percentage"},
                                    {"label": "Fixed Risk Percentage", "value": "fixed_risk"},
                                    {"label": "Fixed Number of Shares", "value": "fixed_shares"}
                                ],
                                value="fixed_dollar",
                                className="mb-2"
                            ),
                            
                            dbc.Label("Position Size Value"),
                            dcc.Input(id="position-size-value", type="number", value=10000, className="form-control")
                        ])
                    ], className="mb-3")
                ], md=4),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Save Backtest"),
                        dbc.CardBody([
                            dbc.Label("Backtest Name"),
                            dcc.Input(id="backtest-name", type="text", placeholder="Enter a name for this backtest", className="form-control mb-3"),
                            dbc.Button("Run Backtest", id="run-backtest-button", color="primary", className="w-100 mb-2"),
                            dbc.Button("Save Results", id="save-backtest-button", color="success", className="w-100", disabled=True)
                        ])
                    ], className="mb-3"),
                    
                    html.Div(id="backtest-message")
                ], md=4)
            ]),
            
            # Results Section
            dbc.Row([
                dbc.Col([
                    html.Div(id="backtest-results", className="mt-3")
                ])
            ]),
            
            # Charts Section
            dbc.Tabs([
                dbc.Tab(label="Price & Signals", tab_id="tab-price", children=[
                    dbc.Row(dbc.Col(dcc.Graph(id="backtest-chart")))
                ]),
                dbc.Tab(label="Equity Curve", tab_id="tab-equity", children=[
                    dbc.Row(dbc.Col(dcc.Graph(id="equity-curve-chart")))
                ]),
                dbc.Tab(label="Drawdown", tab_id="tab-drawdown", children=[
                    dbc.Row(dbc.Col(dcc.Graph(id="drawdown-chart")))
                ]),
                dbc.Tab(label="Trade Analysis", tab_id="tab-trades", children=[
                    dbc.Row(dbc.Col(dcc.Graph(id="trade-profit-chart")))
                ])
            ], id="backtest-tabs", active_tab="tab-price", className="my-3")
            
        ], fluid=True)
    ])
    
    # Define callbacks
    @dash_app.callback(
        [Output("ma-params", "style"),
         Output("rsi-params", "style"),
         Output("ma-rsi-params", "style")],
        [Input("strategy-dropdown", "value")]
    )
    def update_strategy_params(strategy):
        """Show/hide strategy parameter sections based on selected strategy."""
        ma_style = {"display": "block" if strategy == "ma_cross" else "none"}
        rsi_style = {"display": "block" if strategy == "rsi" else "none"}
        ma_rsi_style = {"display": "block" if strategy == "ma_rsi" else "none"}
        return ma_style, rsi_style, ma_rsi_style
    
    @dash_app.callback(
        [Output("backtest-results", "children"),
         Output("backtest-chart", "figure"),
         Output("equity-curve-chart", "figure"),
         Output("drawdown-chart", "figure"),
         Output("trade-profit-chart", "figure"),
         Output("backtest-results-store", "data"),
         Output("save-backtest-button", "disabled"),
         Output("backtest-message", "children")],
        [Input("run-backtest-button", "n_clicks"),
         Input("save-backtest-button", "n_clicks")],
        [State("strategy-dropdown", "value"),
         State("ma-short", "value"),
         State("ma-long", "value"),
         State("rsi-period", "value"),
         State("rsi-overbought", "value"),
         State("rsi-oversold", "value"),
         State("ma-rsi-short", "value"),
         State("ma-rsi-long", "value"),
         State("ma-rsi-buy", "value"),
         State("ma-rsi-sell", "value"),
         State("backtest-ticker", "value"),
         State("backtest-period", "value"),
         State("backtest-interval", "value"),
         State("initial-capital", "value"),
         State("position-sizing", "value"),
         State("position-size-value", "value"),
         State("backtest-name", "value"),
         State("backtest-results-store", "data")]
    )
    def run_and_save_backtest(run_clicks, save_clicks, 
                             strategy, ma_short, ma_long, 
                             rsi_period, rsi_overbought, rsi_oversold,
                             ma_rsi_short, ma_rsi_long, ma_rsi_buy, ma_rsi_sell,
                             ticker, period, interval,
                             initial_capital, position_sizing, position_size_value,
                             backtest_name, stored_results):
        """Run backtest and save results."""
        # Default empty figures
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="No data to display",
            template="plotly_white"
        )
        
        # Determine which button was clicked
        ctx = callback_context
        if not ctx.triggered:
            return html.Div("Click 'Run Backtest' to start"), empty_fig, empty_fig, empty_fig, empty_fig, {}, True, ""
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Handle save backtest button
        if button_id == "save-backtest-button" and save_clicks:
            if not backtest_name:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, False, html.P("Please enter a name for the backtest", className="text-danger")
            
            # Prepare data for saving to database
            save_data = {
                'name': backtest_name,
                'ticker': ticker,
                'start_date': stored_results.get('start_date', ''),
                'end_date': stored_results.get('end_date', ''),
                'strategy_type': strategy,
                'parameters': {
                    'ma_short': ma_short,
                    'ma_long': ma_long,
                    'rsi_period': rsi_period,
                    'rsi_overbought': rsi_overbought,
                    'rsi_oversold': rsi_oversold,
                    'ma_rsi_short': ma_rsi_short,
                    'ma_rsi_long': ma_rsi_long,
                    'ma_rsi_buy': ma_rsi_buy,
                    'ma_rsi_sell': ma_rsi_sell,
                    'initial_capital': initial_capital,
                    'position_sizing': position_sizing,
                    'position_size_value': position_size_value
                },
                'results': stored_results.get('metrics', {})
            }
            
            # In a real app, this would save to the database
            # For now, we just show a success message
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, True, html.P(f"Backtest '{backtest_name}' saved successfully!", className="text-success")
        
        # If run backtest wasn't clicked, return no updates
        if button_id != "run-backtest-button" or not run_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, True, ""
        
        # Run the backtest
        try:
            # Fetch data
            data = fetch_stock_data(ticker, period, interval)
            if data.empty:
                return html.P(f"No data returned for ticker: {ticker}", className="text-danger"), empty_fig, empty_fig, empty_fig, empty_fig, {}, True, ""
            
            # Create strategy
            if strategy == "ma_cross":
                strat = MovingAverageCrossStrategy(short_window=ma_short, long_window=ma_long)
            elif strategy == "rsi":
                strat = RSIStrategy(rsi_period=rsi_period, overbought=rsi_overbought, oversold=rsi_oversold)
            elif strategy == "macd":
                strat = MACDStrategy()
            elif strategy == "ma_rsi":
                strat = MAWithRSIStrategy(short_window=ma_rsi_short, long_window=ma_rsi_long, 
                                         rsi_buy=ma_rsi_buy, rsi_sell=ma_rsi_sell)
            else:
                return html.P("Invalid strategy selected", className="text-danger"), empty_fig, empty_fig, empty_fig, empty_fig, {}, True, ""
            
            # Create backtester
            backtester = Backtester(data, strat, initial_capital=initial_capital)
            backtester.set_position_sizing(method=position_sizing, value=position_size_value)
            
            # Run backtest
            results = backtester.run_backtest()
            metrics = backtester.get_performance_metrics()
            
            # Store results for saving
            stored_data = {
                'start_date': data.index[0].isoformat(),
                'end_date': data.index[-1].isoformat(),
                'metrics': metrics
            }
            
            # Create results summary
            results_summary = html.Div([
                html.H4("Backtest Results Summary", className="mt-3 mb-4"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Performance Metrics"),
                            dbc.CardBody([
                                html.P(f"Total Return: {metrics['total_return']:.2f}%", className="mb-1"),
                                html.P(f"Annualized Return: {metrics['annualized_return']:.2f}%", className="mb-1"),
                                html.P(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}", className="mb-1"),
                                html.P(f"Maximum Drawdown: {metrics['max_drawdown']:.2f}%", className="mb-1"),
                                html.P(f"Final Equity: ${metrics['final_equity']:.2f}", className="mb-1")
                            ])
                        ], className="h-100")
                    ], md=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Trade Metrics"),
                            dbc.CardBody([
                                html.P(f"Total Trades: {metrics['trade_metrics'].get('total_trades', 0)}", className="mb-1"),
                                html.P(f"Win Rate: {metrics['trade_metrics'].get('win_rate', 0):.2f}%", className="mb-1"),
                                html.P(f"Profit Factor: {metrics['trade_metrics'].get('profit_factor', 0):.2f}", className="mb-1"),
                                html.P(f"Average Win: {metrics['trade_metrics'].get('avg_win', 0):.2f}%", className="mb-1"),
                                html.P(f"Average Loss: {metrics['trade_metrics'].get('avg_loss', 0):.2f}%", className="mb-1")
                            ])
                        ], className="h-100")
                    ], md=6)
                ])
            ])
            
            # Create price chart with buy/sell signals
            fig_price = go.Figure()
            fig_price.add_trace(go.Scatter(x=results.index, y=results["close"], mode="lines", name="Close Price"))
            
            # Add strategy-specific traces
            if strategy in ["ma_cross", "ma_rsi"]:
                fig_price.add_trace(go.Scatter(x=results.index, y=results["short_ma"], mode="lines", name="Short MA", line=dict(dash="dash", color="orange")))
                fig_price.add_trace(go.Scatter(x=results.index, y=results["long_ma"], mode="lines", name="Long MA", line=dict(dash="dash", color="green")))
            
            # Add buy signals
            buy_signals = results[results["positions"] > 0]
            if not buy_signals.empty:
                buy_prices = buy_signals["close"]
                fig_price.add_trace(go.Scatter(
                    x=buy_signals.index, 
                    y=buy_prices, 
                    mode="markers",
                    name="Buy Signal",
                    marker=dict(
                        symbol="triangle-up",
                        size=10,
                        color="green"
                    )
                ))
            
            # Add sell signals
            sell_signals = results[results["positions"] < 0]
            if not sell_signals.empty:
                sell_prices = sell_signals["close"]
                fig_price.add_trace(go.Scatter(
                    x=sell_signals.index, 
                    y=sell_prices, 
                    mode="markers",
                    name="Sell Signal",
                    marker=dict(
                        symbol="triangle-down",
                        size=10,
                        color="red"
                    )
                ))
            
            fig_price.update_layout(
                title=f"{ticker} Price Chart with Trading Signals",
                xaxis_title="Date",
                yaxis_title="Price",
                template="plotly_white",
                height=600,
                margin={"l": 40, "r": 40, "t": 40, "b": 40}
            )
            
            # Create equity curve chart
            fig_equity = go.Figure()
            fig_equity.add_trace(go.Scatter(x=results.index, y=results["total"], mode="lines", name="Portfolio Value"))
            fig_equity.add_trace(go.Scatter(x=results.index, y=[initial_capital] * len(results), mode="lines", name="Initial Capital", line=dict(dash="dash", color="gray")))
            
            fig_equity.update_layout(
                title="Portfolio Equity Curve",
                xaxis_title="Date",
                yaxis_title="Portfolio Value ($)",
                template="plotly_white",
                height=400,
                margin={"l": 40, "r": 40, "t": 40, "b": 40}
            )
            
            # Create drawdown chart
            returns = results["returns"]
            cum_returns = (1 + returns).cumprod()
            running_max = cum_returns.cummax()
            drawdown = (cum_returns / running_max - 1) * 100
            
            fig_drawdown = go.Figure()
            fig_drawdown.add_trace(go.Scatter(x=results.index, y=drawdown, mode="lines", name="Drawdown", fill="tozeroy", fillcolor="rgba(255, 0, 0, 0.1)"))
            
            fig_drawdown.update_layout(
                title="Portfolio Drawdown",
                xaxis_title="Date",
                yaxis_title="Drawdown (%)",
                template="plotly_white",
                height=400,
                margin={"l": 40, "r": 40, "t": 40, "b": 40}
            )
            
            # Create trade profit chart
            if 'trade_metrics' in metrics and metrics['trade_metrics'].get('total_trades', 0) > 0:
                # Extract trade data (this is a simplified version)
                trades = []
                position_changes = results[results["positions"] != 0].copy()
                in_trade = False
                entry_price = 0
                entry_time = None
                
                for i, row in position_changes.iterrows():
                    # Buy signal
                    if row["positions"] > 0 and not in_trade:
                        in_trade = True
                        entry_price = row["close"]
                        entry_time = i
                    
                    # Sell signal
                    elif row["positions"] < 0 and in_trade:
                        exit_price = row["close"]
                        exit_time = i
                        
                        # Calculate trade return
                        trade_return = (exit_price / entry_price - 1) * 100
                        
                        # Store trade information
                        trades.append({
                            "entry_time": entry_time,
                            "exit_time": exit_time,
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "return": trade_return,
                            "profitable": trade_return > 0
                        })
                        
                        in_trade = False
                
                if trades:
                    trade_df = pd.DataFrame(trades)
                    
                    # Create bar chart of trade returns
                    fig_trades = go.Figure()
                    fig_trades.add_trace(go.Bar(
                        x=range(1, len(trade_df) + 1),
                        y=trade_df["return"],
                        marker_color=["green" if p else "red" for p in trade_df["profitable"]],
                        name="Trade P/L"
                    ))
                    
                    fig_trades.update_layout(
                        title="Trade Returns",
                        xaxis_title="Trade Number",
                        yaxis_title="Return (%)",
                        template="plotly_white",
                        height=400,
                        margin={"l": 40, "r": 40, "t": 40, "b": 40}
                    )
                else:
                    fig_trades = empty_fig
            else:
                fig_trades = empty_fig
            
            return results_summary, fig_price, fig_equity, fig_drawdown, fig_trades, stored_data, False, ""
            
        except Exception as e:
            error_message = html.P(f"Error running backtest: {str(e)}", className="text-danger")
            return error_message, empty_fig, empty_fig, empty_fig, empty_fig, {}, True, ""
    
    return dash_app