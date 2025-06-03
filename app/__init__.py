# app/__init__.py
# This file contains the application factory function.

from flask import Flask
import os
# It's good practice to import datetime if you plan to use it, e.g., for context processors
import datetime

def create_app(test_config=None):
    """
    Application factory function. Creates and configures the Flask app.
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- Configuration ---
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_secret_key_please_change_in_production'), 
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
    from .blueprints import paycheck_routes 
    from .blueprints import goal_routes 
    
    app.register_blueprint(main_routes.bp) 
    app.register_blueprint(transaction_routes.bp, url_prefix='/transactions') 
    app.register_blueprint(category_routes.bp, url_prefix='/categories') 
    app.register_blueprint(budget_routes.bp, url_prefix='/budget') 
    app.register_blueprint(paycheck_routes.bp, url_prefix='/paychecks') 
    
    # Updated registration for goal_routes blueprint
    app.register_blueprint(goal_routes.bp, url_prefix='/goals') 
    
    # --- Custom Jinja Filters (if any) ---
    from .utils import helpers
    app.jinja_env.filters['month_name'] = helpers.format_month_name

    app.logger.info("Flask app created and configured.")
    return app

