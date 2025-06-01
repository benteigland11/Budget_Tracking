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
    # Set a default secret key. In a real app, use a strong, random key
    # and consider loading it from an environment variable or config file.
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_secret_key_please_change'),
        DATABASE=os.path.join(app.instance_path, 'budget.db'), # Default DB path
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        # You can create a config.py in the 'instance' folder
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists (Flask doesn't create it automatically)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass # Instance folder already exists

    # --- Initialize Database ---
    from . import database
    database.init_app(app) # Register DB commands (like init-db) and teardown

    # --- Register Blueprints ---
    from .blueprints import main_routes, transaction_routes, category_routes, budget_routes
    
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(transaction_routes.bp, url_prefix='/transactions')
    app.register_blueprint(category_routes.bp, url_prefix='/categories')
    app.register_blueprint(budget_routes.bp, url_prefix='/budget')
    
    # --- Custom Jinja Filters (moved to helpers.py, registered via app context or directly) ---
    from .utils import helpers
    app.jinja_env.filters['month_name'] = helpers.format_month_name

    return app
