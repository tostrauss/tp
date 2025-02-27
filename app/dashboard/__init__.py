# app/dashboard/__init__.py
from flask import Blueprint

bp = Blueprint('dashboard', __name__)

from app.dashboard import routes

# app/dashboard/routes.py
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app.dashboard import bp
from app.models import Watchlist, Backtest

@bp.route('/')
@bp.route('/dashboard')
@login_required
def index():
    """
    Main dashboard view displaying an overview of the user's account and recent activity.
    """
    # Get user's watchlists
    watchlists = Watchlist.query.filter_by(user_id=current_user.id).all()
    
    # Get user's recent backtests
    recent_backtests = Backtest.query.filter_by(user_id=current_user.id).order_by(Backtest.created_at.desc()).limit(5).all()
    
    # Check if the user is new (first login)
    is_new_user = current_user.last_login is None
    
    # If it's a new user, redirect to educational onboarding
    if is_new_user:
        return redirect(url_for('education.onboarding'))
    
    return render_template('dashboard/index.html', 
                          title='Dashboard',
                          watchlists=watchlists,
                          recent_backtests=recent_backtests)

@bp.route('/quick-view')
@login_required
def quick_view():
    """
    Quick summary view of market trends and user's tracked stocks.
    """
    return render_template('dashboard/quick_view.html', title='Market Quick View')

@bp.route('/settings')
@login_required
def settings():
    """
    User settings page.
    """
    return render_template('dashboard/settings.html', title='Settings')