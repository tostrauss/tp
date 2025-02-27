from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class User(UserMixin, db.Model):
    """User model for authentication and profile data."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Profile information
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    
    # Subscription info
    subscription_level = db.Column(db.String(20), default='free')
    subscription_expires = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    watchlists = db.relationship('Watchlist', backref='user', lazy='dynamic')
    backtests = db.relationship('Backtest', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Set the user's password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def is_premium(self):
        """Check if the user has an active premium subscription."""
        if self.subscription_level == 'free':
            return False
        if self.subscription_expires and self.subscription_expires < datetime.utcnow():
            return False
        return True


class Watchlist(db.Model):
    """Model for user watchlists."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    stocks = db.relationship('WatchlistItem', backref='watchlist', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Watchlist {self.name}>'


class WatchlistItem(db.Model):
    """Model for individual stocks in a watchlist."""
    id = db.Column(db.Integer, primary_key=True)
    watchlist_id = db.Column(db.Integer, db.ForeignKey('watchlist.id'), nullable=False)
    ticker = db.Column(db.String(20), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<WatchlistItem {self.ticker}>'


class Backtest(db.Model):
    """Model for saved backtests."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Strategy parameters
    ticker = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    strategy_type = db.Column(db.String(50), nullable=False)
    parameters = db.Column(db.JSON, nullable=False)
    
    # Results
    results = db.Column(db.JSON, nullable=True)
    
    def __repr__(self):
        return f'<Backtest {self.name}>'


@login_manager.user_loader
def load_user(user_id):
    """Function to load a user for Flask-Login."""
    return User.query.get(int(user_id))