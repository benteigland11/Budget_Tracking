# app/blueprints/transaction_routes.py
# Blueprint for transaction-related actions.

from flask import Blueprint, request, redirect, url_for, flash
from app.database import get_db # Use get_db from the database module
import sqlite3

bp = Blueprint('transactions', __name__) # url_prefix='/transactions' will be set in app/__init__.py

@bp.route('/add', methods=['POST'])
def add_transaction():
    if request.method == 'POST':
        try:
            amount_str = request.form['amount']
            category_id_str = request.form.get('final_category_id') 
            date = request.form['date']
            transaction_type = request.form['type']
            if not amount_str: flash('Amount is required.', 'error')
            elif not category_id_str: flash('Category selection is required.', 'error')
            elif not date: flash('Date is required.', 'error')
            elif transaction_type not in ['income', 'expense']: flash('Invalid transaction type.', 'error')
            else:
                amount = float(amount_str)
                category_id = int(category_id_str)
                if amount <= 0: flash('Amount must be a positive number.', 'error')
                else:
                    conn = get_db()
                    conn.execute("INSERT INTO transactions (amount, category_id, date, type) VALUES (?, ?, ?, ?)", 
                                 (amount, category_id, date, transaction_type))
                    conn.commit()
                    flash('Transaction added successfully!', 'success')
                    # Preserve analytics view period on redirect
                    return redirect(url_for('main.index', 
                                            year=request.args.get('year'), 
                                            month=request.args.get('month'),
                                            main_cat_focus=request.args.get('main_cat_focus')))
        except ValueError: flash('Invalid amount or category ID.', 'error')
        except sqlite3.IntegrityError: flash('DB integrity error. Category exists?', 'error')
        except Exception as e: flash(f'Error: {e}', 'error'); print(f"Error add_transaction: {e}")
    # Fallback redirect, try to preserve params
    return redirect(url_for('main.index', 
                            year=request.args.get('year'), 
                            month=request.args.get('month'),
                            main_cat_focus=request.args.get('main_cat_focus')))


@bp.route('/update/<int:transaction_id>', methods=['POST'])
def update_transaction(transaction_id):
    if request.method == 'POST':
        try:
            amount_str = request.form['amount']
            category_id_str = request.form.get('final_category_id') 
            date = request.form['date']
            transaction_type = request.form['type']
            if not amount_str: flash('Amount is required.', 'error')
            elif not category_id_str: flash('Category selection is required.', 'error')
            elif not date: flash('Date is required.', 'error')
            elif transaction_type not in ['income', 'expense']: flash('Invalid transaction type.', 'error')
            else:
                amount = float(amount_str)
                category_id = int(category_id_str)
                if amount <= 0: flash('Amount must be a positive number.', 'error')
                else:
                    conn = get_db()
                    conn.execute("UPDATE transactions SET amount = ?, category_id = ?, date = ?, type = ? WHERE id = ?", 
                                 (amount, category_id, date, transaction_type, transaction_id))
                    conn.commit()
                    flash('Transaction updated!', 'success')
                    return redirect(url_for('main.index', 
                                            year=request.args.get('year'), 
                                            month=request.args.get('month'),
                                            main_cat_focus=request.args.get('main_cat_focus')))
        except ValueError: flash('Invalid amount or category ID.', 'error')
        except sqlite3.IntegrityError: flash('DB integrity error. Category exists?', 'error')
        except Exception as e: flash(f'Error: {e}', 'error'); print(f"Error update_transaction: {e}")
    return redirect(url_for('main.index', 
                            year=request.args.get('year'), 
                            month=request.args.get('month'),
                            main_cat_focus=request.args.get('main_cat_focus')))

@bp.route('/delete/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    try:
        conn = get_db()
        conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        flash('Transaction deleted!', 'success')
    except Exception as e: flash(f'Error deleting: {e}', 'error'); print(f"Error delete_transaction: {e}")
    return redirect(url_for('main.index', 
                            year=request.args.get('year'), 
                            month=request.args.get('month'),
                            main_cat_focus=request.args.get('main_cat_focus')))
