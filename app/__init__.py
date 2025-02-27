from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import dash
import dash_bootstrap_components as dbc

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_object="app.config.Config"):
    """Create the Flask application instance."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    app.config.from_pyfile('config.py', silent=True)  # Instance config

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)
    
    from app.education import bp as education_bp
    app.register_blueprint(education_bp, url_prefix='/education')
    
    from app.stock_analysis import bp as stock_analysis_bp
    app.register_blueprint(stock_analysis_bp, url_prefix='/analysis')
    
    from app.backtesting import bp as backtesting_bp
    app.register_blueprint(backtesting_bp, url_prefix='/backtesting')
    
    from app.trading import bp as trading_bp
    app.register_blueprint(trading_bp, url_prefix='/trading')

    # Initialize Dash apps and register with Flask
    with app.app_context():
        # Register Dash apps
        from app.stock_analysis.dash_app import create_dash_app as create_analysis_dash
        analysis_dash = create_analysis_dash(app)
        
        from app.backtesting.dash_app import create_dash_app as create_backtest_dash
        backtest_dash = create_backtest_dash(app)
        
        from app.trading.dash_app import create_dash_app as create_trading_dash
        trading_dash = create_trading_dash(app)

    # Create error handlers
    @app.errorhandler(404)
    def page_not_found(error):
        return "Page not found", 404

    @app.errorhandler(500)
    def server_error(error):
        return "Server error", 500

    # Shell context processor
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'User': User}
        
    return app

# Import models at the end to avoid circular imports
from app.models import User