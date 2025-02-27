# app/stock_analysis/__init__.py
from flask import Blueprint

bp = Blueprint('stock_analysis', __name__)

from app.stock_analysis import routes

# app/stock_analysis/routes.py
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app.stock_analysis import bp
from app.models import Watchlist, WatchlistItem
from app import db

@bp.route('/')
@login_required
def index():
    """
    Main stock analysis page that hosts the Dash app.
    """
    # Get user's watchlists for sidebar
    watchlists = Watchlist.query.filter_by(user_id=current_user.id).all()
    
    return render_template('stock_analysis/index.html', 
                          title='Stock Analysis',
                          watchlists=watchlists)

@bp.route('/charts/<ticker>')
@login_required
def stock_charts(ticker):
    """
    Dedicated page for specific stock charts.
    """
    return render_template('stock_analysis/stock_charts.html',
                          title=f'{ticker} Charts',
                          ticker=ticker)

@bp.route('/screener')
@login_required
def screener():
    """
    Stock screener page.
    """
    return render_template('stock_analysis/screener.html',
                          title='Stock Screener')

@bp.route('/watchlist/create', methods=['POST'])
@login_required
def create_watchlist():
    """
    API endpoint to create a new watchlist.
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
    watchlist = Watchlist(name=data['name'], user_id=current_user.id)
    db.session.add(watchlist)
    db.session.commit()
    
    return jsonify({
        'id': watchlist.id,
        'name': watchlist.name,
        'created_at': watchlist.created_at
    }), 201

@bp.route('/watchlist/<int:watchlist_id>/add', methods=['POST'])
@login_required
def add_to_watchlist(watchlist_id):
    """
    API endpoint to add a ticker to a watchlist.
    """
    data = request.get_json()
    if not data or 'ticker' not in data:
        return jsonify({'error': 'Ticker is required'}), 400
    
    watchlist = Watchlist.query.filter_by(id=watchlist_id, user_id=current_user.id).first_or_404()
    
    # Check if ticker already exists in this watchlist
    existing = WatchlistItem.query.filter_by(watchlist_id=watchlist_id, ticker=data['ticker']).first()
    if existing:
        return jsonify({'error': 'Ticker already in watchlist'}), 400
    
    item = WatchlistItem(watchlist_id=watchlist_id, ticker=data['ticker'], notes=data.get('notes', ''))
    db.session.add(item)
    db.session.commit()
    
    return jsonify({
        'id': item.id,
        'ticker': item.ticker,
        'added_at': item.added_at,
        'notes': item.notes
    }), 201

@bp.route('/watchlist/<int:watchlist_id>/remove/<int:item_id>', methods=['DELETE'])
@login_required
def remove_from_watchlist(watchlist_id, item_id):
    """
    API endpoint to remove a ticker from a watchlist.
    """
    watchlist = Watchlist.query.filter_by(id=watchlist_id, user_id=current_user.id).first_or_404()
    item = WatchlistItem.query.filter_by(id=item_id, watchlist_id=watchlist_id).first_or_404()
    
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({'success': True}), 200

@bp.route('/compare')
@login_required
def compare_stocks():
    """
    Page for comparing multiple stocks.
    """
    return render_template('stock_analysis/compare.html',
                          title='Compare Stocks')