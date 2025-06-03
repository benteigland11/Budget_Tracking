# app/__init__.py
# This file contains the application factory function.

from flask import Flask
import os

def create_app(test_config=None):
    """
    Application factory function. Creates and configures the Flask app.
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- Configuration ---
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_secret_key_please_change'),
        DATABASE=os.path.join(app.instance_path, 'budget.db'), 
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass 

    # --- Initialize Database ---
    from . import database
    database.init_app(app) 

    # --- Register Blueprints ---
    from .blueprints import main_routes, transaction_routes, category_routes, budget_routes
    # MODIFICATION: Import and register the new paycheck_routes blueprint
    from .blueprints import paycheck_routes 
    
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(transaction_routes.bp, url_prefix='/transactions')
    app.register_blueprint(category_routes.bp, url_prefix='/categories')
    app.register_blueprint(budget_routes.bp, url_prefix='/budget')
    # MODIFICATION: Register new blueprint
    app.register_blueprint(paycheck_routes.bp) 
    
    # --- Custom Jinja Filters ---
    from .utils import helpers
    app.jinja_env.filters['month_name'] = helpers.format_month_name

    return app
