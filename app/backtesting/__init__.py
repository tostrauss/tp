# app/backtesting/__init__.py
from flask import Blueprint

bp = Blueprint('backtesting', __name__)

from app.backtesting import routes

# app/backtesting/routes.py
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app.backtesting import bp
from app.models import Backtest
from app import db
import json
from datetime import datetime

@bp.route('/')
@login_required
def index():
    """
    Main backtesting page that hosts the Dash app.
    """
    # Get user's saved backtests
    backtests = Backtest.query.filter_by(user_id=current_user.id).order_by(Backtest.created_at.desc()).all()
    
    return render_template('backtesting/index.html', 
                          title='Backtesting',
                          backtests=backtests)

@bp.route('/strategies')
@login_required
def strategies():
    """
    Page for browsing and selecting backtesting strategies.
    """
    return render_template('backtesting/strategies.html',
                          title='Trading Strategies')

@bp.route('/results/<int:backtest_id>')
@login_required
def results(backtest_id):
    """
    View detailed results of a specific backtest.
    """
    backtest = Backtest.query.filter_by(id=backtest_id, user_id=current_user.id).first_or_404()
    return render_template('backtesting/results.html',
                          title=f'Backtest Results: {backtest.name}',
                          backtest=backtest)

@bp.route('/save', methods=['POST'])
@login_required
def save_backtest():
    """
    API endpoint to save backtest results.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['name', 'ticker', 'start_date', 'end_date', 'strategy_type', 'parameters', 'results']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        # Convert date strings to datetime objects
        start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
        
        backtest = Backtest(
            name=data['name'],
            user_id=current_user.id,
            ticker=data['ticker'],
            start_date=start_date,
            end_date=end_date,
            strategy_type=data['strategy_type'],
            parameters=data['parameters'],
            results=data['results']
        )
        
        db.session.add(backtest)
        db.session.commit()
        
        return jsonify({
            'id': backtest.id,
            'name': backtest.name,
            'created_at': backtest.created_at.isoformat()
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/delete/<int:backtest_id>', methods=['DELETE'])
@login_required
def delete_backtest(backtest_id):
    """
    API endpoint to delete a saved backtest.
    """
    backtest = Backtest.query.filter_by(id=backtest_id, user_id=current_user.id).first_or_404()
    
    db.session.delete(backtest)
    db.session.commit()
    
    return jsonify({'success': True}), 200

@bp.route('/comparison')
@login_required
def comparison():
    """
    Page for comparing multiple backtest results.
    """
    return render_template('backtesting/comparison.html',
                          title='Compare Backtests')