# app/education/__init__.py
from flask import Blueprint

bp = Blueprint('education', __name__)

from app.education import routes

# app/education/routes.py
from flask import render_template, redirect, url_for, request, session
from flask_login import login_required, current_user
from app.education import bp
from app import db
from app.models import User

@bp.route('/onboarding')
@login_required
def onboarding():
    """
    Educational onboarding for new users.
    """
    # Track onboarding progress in session
    session['onboarding_started'] = True
    
    return render_template('education/onboarding.html', 
                          title='Welcome to ToFu\'s Trading Platform',
                          step=1)

@bp.route('/onboarding/<int:step>')
@login_required
def onboarding_step(step):
    """
    Individual steps in the onboarding process.
    """
    # Validate step number
    if step < 1 or step > 5:
        return redirect(url_for('education.onboarding'))
    
    # Set step-specific data
    step_titles = {
        1: 'Platform Overview',
        2: 'Stock Analysis Basics',
        3: 'Technical Indicators',
        4: 'Backtesting Strategies',
        5: 'Options & Trading'
    }
    
    # Mark user as no longer new if they complete step 5
    if step == 5 and current_user.last_login is None:
        current_user.last_login = db.func.now()
        db.session.commit()
    
    return render_template('education/onboarding_step.html',
                          title=f'Onboarding: {step_titles[step]}',
                          step=step,
                          step_title=step_titles[step],
                          total_steps=5)

@bp.route('/fundamentals')
@login_required
def fundamentals():
    """
    Fundamental analysis educational content.
    """
    return render_template('education/fundamentals.html', 
                          title='Fundamental Analysis')

@bp.route('/technical')
@login_required
def technical():
    """
    Technical analysis educational content.
    """
    return render_template('education/technical.html', 
                          title='Technical Analysis')

@bp.route('/options-basics')
@login_required
def options_basics():
    """
    Options trading educational content.
    """
    return render_template('education/options_basics.html', 
                          title='Options Trading Basics')

@bp.route('/strategies')
@login_required
def strategies():
    """
    Trading strategies educational content.
    """
    return render_template('education/strategies.html', 
                          title='Trading Strategies')

@bp.route('/glossary')
@login_required
def glossary():
    """
    Financial terms glossary.
    """
    return render_template('education/glossary.html', 
                          title='Financial Glossary')