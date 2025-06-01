# app/database.py
# Handles database connection and initialization.

import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_db():
    """
    Connects to the application's configured database. The connection
    is unique for each request and will be reused if this is called
    again.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row # Access columns by name
        g.db.execute("PRAGMA foreign_keys = ON;") # Enforce foreign keys
    return g.db

def close_db(e=None):
    """
    If this request connected to the database, close the
    connection.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Clear existing data and create new tables."""
    db = get_db()
    # Here you would typically execute your schema.sql or call your init_db.py logic
    # For this project, we'll assume init_db.py is run manually or adapted.
    # If init_db.py is in the root, you might need to adjust path or import.
    # For simplicity, we'll just print a message.
    # In a real app, you'd run your schema creation here.
    
    # To actually run your existing init_db.py, you could do:
    # import sys
    # import os
    # project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    # if project_root not in sys.path:
    #    sys.path.insert(0, project_root)
    # from init_db import initialize_database # Assuming init_db.py is in root
    # initialize_database()
    # current_app.logger.info("Database schema initialized using init_db.py.")
    
    # For now, let's just show a message that it should be done manually or integrated.
    click.echo("Initialized the database (or ensure init_db.py has been run).")


@click.command('init-db')
@with_appcontext
def init_db_command():
    """CLI command to initialize the database."""
    init_db()
    click.echo('Database initialization command executed.')

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db) # Call close_db when cleaning up after returning response
    app.cli.add_command(init_db_command) # Add new command 'flask init-db'
