# app/stock_analysis/dash_app.py
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
from app.helpers.data_fetcher import fetch_stock_data, get_company_info
from app.helpers.indicators import add_technical_indicators, generate_tech_signal

def create_dash_app(flask_app):
    """
    Create a Dash app that's integrated with the Flask app.
    """
    # Create Dash app with Bootstrap styling
    dash_app = dash.Dash(
        server=flask_app,
        url_base_pathname='/analysis/dashboard/',
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
    )
    
    # Update title
    dash_app.title = "ToFu's Stock Analysis & Options Trading"
    
    # Define the layout
    dash_app.layout = html.Div([
        # Hidden divs for storing data
        dcc.Store(id="watchlist-store", data=[]),
        dcc.Store(id="options-store", data={}),
        
        # Main content
        dbc.Container([
            dbc.Row(dbc.Col(html.H2("Real‑Time Stock Analysis", className="text-primary mb-3"))),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Enter Stock Ticker"),
                    dcc.Input(id="stock-ticker-input", type="text", value="AAPL", className="form-control")
                ], md=4),
                dbc.Col([
                    dbc.Label("Select Data Period"),
                    dcc.Dropdown(id="stock-period",
                                 options=[{"label": p, "value": p} for p in ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]],
                                 value="1d", className="form-select")
                ], md=3),
                dbc.Col([
                    dbc.Label("Select Data Interval"),
                    dcc.Dropdown(id="stock-interval",
                                 options=[{"label": i, "value": i} for i in ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d"]],
                                 value="1m", className="form-select")
                ], md=3),
                dbc.Col(dbc.Button("Analyze Stock", id="analyze-stock-button", color="primary", className="mt-4"), md=2)
            ], className="mb-3"),
            dbc.Row(dbc.Col(html.Div(id="stock-error", className="text-danger"))),
            
            # Tabs for different views
            dbc.Tabs([
                dbc.Tab(label="Price Chart", tab_id="tab-price", children=[
                    dbc.Row(dbc.Col(dcc.Graph(id="price-chart")))
                ]),
                dbc.Tab(label="Technical Indicators", tab_id="tab-indicators", children=[
                    dbc.Row(dbc.Col(dcc.Graph(id="indicators-chart"))),
                    dbc.Row(dbc.Col(dcc.Graph(id="adx-chart")))
                ]),
                dbc.Tab(label="Stock Data", tab_id="tab-data", children=[
                    dbc.Row(dbc.Col(dash_table.DataTable(id="stock-data-table", page_size=10, style_table={"overflowX": "auto"})))
                ]),
                dbc.Tab(label="Fundamentals", tab_id="tab-fundamentals", children=[
                    dbc.Row(dbc.Col(html.Div(id="fundamentals-div", className="mt-3")))
                ])
            ], id="stock-tabs", active_tab="tab-price", className="my-3"),
            
            # Add to watchlist section
            dbc.Row([
                dbc.Col([
                    dbc.Label("Add to Watchlist"),
                    dcc.Dropdown(id="watchlist-dropdown", className="form-select", placeholder="Select a watchlist...")
                ], md=4),
                dbc.Col(dbc.Button("Add Current Stock", id="add-to-watchlist-button", color="success", className="mt-4"), md=2)
            ], className="my-3"),
            dbc.Row(dbc.Col(html.Div(id="watchlist-message", className="mt-2")))
        ], fluid=True)
    ])
    
    # Define callbacks
    @dash_app.callback(
        [Output("stock-data-table", "data"),
         Output("stock-data-table", "columns"),
         Output("price-chart", "figure"),
         Output("indicators-chart", "figure"),
         Output("adx-chart", "figure"),
         Output("fundamentals-div", "children"),
         Output("stock-error", "children")],
        Input("analyze-stock-button", "n_clicks"),
        [State("stock-ticker-input", "value"),
         State("stock-period", "value"),
         State("stock-interval", "value")]
    )
    def update_stock_analysis(n_clicks, ticker, period, interval):
        if not n_clicks:
            return [[], [], {}, {}, {}, "", ""]
        try:
            data = fetch_stock_data(ticker, period, interval)
            if data.empty:
                return [[], [], {}, {}, {}, "", f"No data returned for ticker: {ticker}"]
            
            table_data = data.tail(10).reset_index().to_dict("records")
            table_cols = [{"name": i, "id": i} for i in data.tail(10).reset_index().columns]

            # Price chart
            fig_price = go.Figure()
            fig_price.add_trace(go.Scatter(x=data.index, y=data["close"], mode="lines", name="Close Price"))
            fig_price.add_trace(go.Scatter(x=data.index, y=data["SMA20"], mode="lines", name="SMA20", line=dict(dash="dash", color="orange")))
            fig_price.add_trace(go.Scatter(x=data.index, y=data["SMA50"], mode="lines", name="SMA50", line=dict(dash="dash", color="green")))
            fig_price.add_trace(go.Scatter(x=data.index, y=data["SMA200"], mode="lines", name="SMA200", line=dict(dash="dash", color="red")))
            
            if "VWAP" in data.columns:
                fig_price.add_trace(go.Scatter(x=data.index, y=data["VWAP"], mode="lines", name="VWAP", line=dict(dash="dot", color="magenta")))
            
            if "BBL" in data.columns and "BBU" in data.columns:
                fig_price.add_trace(go.Scatter(x=data.index, y=data["BBL"], mode="lines", name="Bollinger Lower", line=dict(color="gray"), opacity=0.5))
                fig_price.add_trace(go.Scatter(x=data.index, y=data["BBU"], mode="lines", name="Bollinger Upper", line=dict(color="gray"), opacity=0.5, fill="tonexty"))
            
            last = data.iloc[-1]
            if "PP" in data.columns:
                fig_price.add_hline(y=last["PP"], line=dict(dash="dash", color="grey"), annotation_text="PP")
            if "R1" in data.columns:
                fig_price.add_hline(y=last["R1"], line=dict(dash="dash", color="red"), annotation_text="R1")
            if "S1" in data.columns:
                fig_price.add_hline(y=last["S1"], line=dict(dash="dash", color="green"), annotation_text="S1")
            
            fig_price.update_layout(
                title=f"{ticker} Price Chart ({period}, {interval})",
                xaxis_title="Date/Time",
                yaxis_title="Price",
                template="plotly_white",
                height=600,
                margin={"l": 40, "r": 40, "t": 40, "b": 40}
            )

            # Indicators chart
            fig_ind = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("RSI", "MACD"), vertical_spacing=0.1)
            
            fig_ind.add_trace(go.Scatter(x=data.index, y=data["RSI"], mode="lines", name="RSI"), row=1, col=1)
            fig_ind.add_hline(y=70, line=dict(dash="dash", color="red"), row=1, col=1)
            fig_ind.add_hline(y=30, line=dict(dash="dash", color="green"), row=1, col=1)
            
            fig_ind.add_trace(go.Scatter(x=data.index, y=data["MACD"], mode="lines", name="MACD"), row=2, col=1)
            fig_ind.add_trace(go.Scatter(x=data.index, y=data["Signal"], mode="lines", name="Signal"), row=2, col=1)
            
            fig_ind.update_layout(
                height=600,
                title_text="Technical Indicators",
                template="plotly_white",
                showlegend=True,
                margin={"l": 40, "r": 40, "t": 40, "b": 40}
            )

            # ADX chart
            fig_adx = go.Figure()
            fig_adx.add_trace(go.Scatter(x=data.index, y=data["ADX"], mode="lines", name="ADX"))
            fig_adx.add_hline(y=25, line=dict(dash="dash", color="red"), annotation_text="Trend Threshold")
            
            fig_adx.update_layout(
                title="Average Directional Index (ADX)",
                template="plotly_white",
                height=400,
                margin={"l": 40, "r": 40, "t": 40, "b": 40}
            )

            # Fundamentals
            try:
                info = get_company_info(ticker)
                fundamentals = html.Div([
                    html.H4("Fundamental Metrics", className="mt-3 mb-4"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Valuation"),
                                dbc.CardBody([
                                    html.P(f"Market Cap: ${info.get('marketCap', 'N/A'):,}" if isinstance(info.get('marketCap'), (int, float)) else "Market Cap: N/A"),
                                    html.P(f"P/E Ratio: {info.get('trailingPE', 'N/A'):.2f}" if isinstance(info.get('trailingPE'), (int, float)) else "P/E Ratio: N/A"),
                                    html.P(f"EPS (TTM): ${info.get('trailingEps', 'N/A'):.2f}" if isinstance(info.get('trailingEps'), (int, float)) else "EPS (TTM): N/A"),
                                    html.P(f"PEG Ratio: {info.get('pegRatio', 'N/A'):.2f}" if isinstance(info.get('pegRatio'), (int, float)) else "PEG Ratio: N/A"),
                                ])
                            ], className="h-100")
                        ], md=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Profitability"),
                                dbc.CardBody([
                                    html.P(f"Profit Margin: {info.get('profitMargins', 'N/A')*100:.2f}%" if isinstance(info.get('profitMargins'), (int, float)) else "Profit Margin: N/A"),
                                    html.P(f"Operating Margin: {info.get('operatingMargins', 'N/A')*100:.2f}%" if isinstance(info.get('operatingMargins'), (int, float)) else "Operating Margin: N/A"),
                                    html.P(f"ROE: {info.get('returnOnEquity', 'N/A')*100:.2f}%" if isinstance(info.get('returnOnEquity'), (int, float)) else "ROE: N/A"),
                                    html.P(f"ROA: {info.get('returnOnAssets', 'N/A')*100:.2f}%" if isinstance(info.get('returnOnAssets'), (int, float)) else "ROA: N/A"),
                                ])
                            ], className="h-100")
                        ], md=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Financial Health"),
                                dbc.CardBody([
                                    html.P(f"Current Ratio: {info.get('currentRatio', 'N/A'):.2f}" if isinstance(info.get('currentRatio'), (int, float)) else "Current Ratio: N/A"),
                                    html.P(f"Debt to Equity: {info.get('debtToEquity', 'N/A'):.2f}" if isinstance(info.get('debtToEquity'), (int, float)) else "Debt to Equity: N/A"),
                                    html.P(f"Quick Ratio: {info.get('quickRatio', 'N/A'):.2f}" if isinstance(info.get('quickRatio'), (int, float)) else "Quick Ratio: N/A"),
                                    html.P(f"52-Week Change: {info.get('52WeekChange', 'N/A')*100:.2f}%" if isinstance(info.get('52WeekChange'), (int, float)) else "52-Week Change: N/A"),
                                ])
                            ], className="h-100")
                        ], md=4)
                    ], className="mb-4"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Company Profile"),
                                dbc.CardBody([
                                    html.P(f"Sector: {info.get('sector', 'N/A')}"),
                                    html.P(f"Industry: {info.get('industry', 'N/A')}"),
                                    html.P(f"Employees: {info.get('fullTimeEmployees', 'N/A'):,}" if isinstance(info.get('fullTimeEmployees'), (int, float)) else "Employees: N/A"),
                                    html.P(f"Country: {info.get('country', 'N/A')}"),
                                ])
                            ], className="h-100")
                        ], md=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader("Dividends & Splits"),
                                dbc.CardBody([
                                    html.P(f"Dividend Rate: ${info.get('dividendRate', 'N/A'):.2f}" if isinstance(info.get('dividendRate'), (int, float)) else "Dividend Rate: N/A"),
                                    html.P(f"Dividend Yield: {info.get('dividendYield', 'N/A')*100:.2f}%" if isinstance(info.get('dividendYield'), (int, float)) else "Dividend Yield: N/A"),
                                    html.P(f"Ex-Dividend Date: {info.get('exDividendDate', 'N/A')}"),
                                    html.P(f"Last Split Factor: {info.get('lastSplitFactor', 'N/A')}"),
                                ])
                            ], className="h-100")
                        ], md=6)
                    ])
                ])
            except Exception as e:
                fundamentals = html.Div([
                    html.P(f"Error fetching fundamental metrics: {str(e)}", className="text-warning"),
                    html.P("This may be due to API limitations or the stock symbol not being supported.")
                ])

            return table_data, table_cols, fig_price, fig_ind, fig_adx, fundamentals, ""
        except Exception as e:
            return [[], [], {}, {}, {}, "", f"Error: {e}"]
    
    @dash_app.callback(
        Output("watchlist-dropdown", "options"),
        Input("analyze-stock-button", "n_clicks")
    )
    def update_watchlist_dropdown(n_clicks):
        # This would typically query the user's watchlists from the database
        try:
            from flask import session
            if current_user.is_authenticated:
                from app.models import Watchlist
                watchlists = Watchlist.query.filter_by(user_id=current_user.id).all()
                return [{"label": w.name, "value": w.id} for w in watchlists]
            return []
        except Exception as e:
            return []
    
    @dash_app.callback(
        Output("watchlist-message", "children"),
        Input("add-to-watchlist-button", "n_clicks"),
        [State("watchlist-dropdown", "value"),
         State("stock-ticker-input", "value")]
    )
    def add_to_watchlist(n_clicks, watchlist_id, ticker):
        if not n_clicks or not watchlist_id or not ticker:
            return ""
        
        try:
            from app.models import WatchlistItem
            
            # Check if ticker already exists in this watchlist
            existing = WatchlistItem.query.filter_by(watchlist_id=watchlist_id, ticker=ticker).first()
            if existing:
                return html.P(f"{ticker} is already in the selected watchlist.", className="text-warning")
            
            # Add the ticker to the watchlist
            item = WatchlistItem(watchlist_id=watchlist_id, ticker=ticker)
            db.session.add(item)
            db.session.commit()
            
            return html.P(f"Added {ticker} to watchlist successfully!", className="text-success")
        except Exception as e:
            return html.P(f"Error adding to watchlist: {str(e)}", className="text-danger")
    
    return dash_app