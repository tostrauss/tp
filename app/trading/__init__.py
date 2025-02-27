# app/trading/__init__.py
from flask import Blueprint

bp = Blueprint('trading', __name__)

from app.trading import routes

# app/trading/routes.py
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app.trading import bp
from app import db
import json
from datetime import datetime

@bp.route('/')
@login_required
def index():
    """
    Main trading dashboard page that hosts the Dash app.
    """
    return render_template('trading/index.html', 
                          title='Trading Dashboard')

@bp.route('/options')
@login_required
def options():
    """
    Options trading page.
    """
    return render_template('trading/options.html',
                          title='Options Trading')

@bp.route('/futures')
@login_required
def futures():
    """
    Futures trading page.
    """
    return render_template('trading/futures.html',
                          title='Futures Trading')

@bp.route('/risk-calculator')
@login_required
def risk_calculator():
    """
    Risk/reward calculator page.
    """
    return render_template('trading/risk_calculator.html',
                          title='Risk/Reward Calculator')

@bp.route('/paper-trading')
@login_required
def paper_trading():
    """
    Paper trading simulator page.
    """
    return render_template('trading/paper_trading.html',
                          title='Paper Trading Simulator')

@bp.route('/api/options-chain/<ticker>')
@login_required
def get_options_chain(ticker):
    """
    API endpoint to get options chain data.
    """
    from app.helpers.options_calc import get_option_chain
    
    expiration = request.args.get('expiration')
    
    try:
        calls, puts, exp_selected, expirations = get_option_chain(ticker, expiration)
        
        if calls is None or puts is None:
            return jsonify({
                'error': 'No options data available'
            }), 404
        
        return jsonify({
            'calls': calls.to_dict('records') if not calls.empty else [],
            'puts': puts.to_dict('records') if not puts.empty else [],
            'selected_expiration': exp_selected,
            'expirations': expirations
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@bp.route('/api/calculate-greeks', methods=['POST'])
@login_required
def calculate_greeks():
    """
    API endpoint to calculate option greeks.
    """
    from app.helpers.options_calc import black_scholes_greeks
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['S', 'K', 'T', 'r', 'sigma', 'option_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        delta, gamma, theta, vega, rho, bs_price = black_scholes_greeks(
            data['S'], data['K'], data['T'], data['r'], data['sigma'], data['option_type']
        )
        
        return jsonify({
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho,
            'price': bs_price
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500