# app/blueprints/paycheck_routes.py
from flask import Blueprint, request, jsonify, current_app, g
from app.database import get_db
import sqlite3
import datetime

bp = Blueprint('paychecks', __name__, url_prefix='/paychecks')

# Helper to get category ID for "Net Pay Deposit" or similar
# This is a placeholder - you might want a more robust way to manage this
# (e.g., a configuration setting or a dedicated category lookup)
def get_net_pay_category_id(conn):
    # Try to find a category named "Salary" or "Paycheck Deposit"
    # This assumes such a category exists and is a main category (no parent_id)
    cursor = conn.execute(
        "SELECT id FROM categories WHERE name IN (?, ?) AND parent_id IS NULL LIMIT 1",
        ("Salary", "Paycheck Deposit")
    )
    row = cursor.fetchone()
    if row:
        return row['id']
    
    # Fallback: If not found, create a default "Salary" category
    try:
        cursor = conn.execute("INSERT INTO categories (name, parent_id) VALUES (?, NULL)", ("Salary",))
        conn.commit() # Commit this individual insert
        current_app.logger.info("Created default 'Salary' category for net pay deposits.")
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Should not happen if previous check was thorough
        current_app.logger.error("Failed to create or find default 'Salary' category due to integrity error after check.")
        # As a last resort, return None or raise an error. For now, returning None.
        # In a real app, ensure this category always exists or handle this case gracefully.
        return None 
    except Exception as e:
        current_app.logger.error(f"Error creating/finding net pay category: {e}")
        return None


@bp.route('/log', methods=['POST'])
def log_paycheck():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data received.'}), 400

    pay_date_str = data.get('pay_date')
    employer_name = data.get('employer_name')
    gross_pay_str = data.get('gross_pay')
    notes = data.get('notes')
    deductions_data = data.get('deductions', []) # List of deduction objects

    # Validate required fields
    if not pay_date_str:
        return jsonify({'status': 'error', 'message': 'Pay date is required.'}), 400
    try:
        # Ensure date is in YYYY-MM-DD format for SQLite
        datetime.datetime.strptime(pay_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid pay date format. Use YYYY-MM-DD.'}), 400
        
    if gross_pay_str is None: # Check for None explicitly because 0 is a valid gross pay
        return jsonify({'status': 'error', 'message': 'Gross pay is required.'}), 400
    try:
        gross_pay = float(gross_pay_str)
        if gross_pay < 0:
            return jsonify({'status': 'error', 'message': 'Gross pay cannot be negative.'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid gross pay amount.'}), 400

    conn = get_db()
    try:
        # Calculate total deductions and net pay
        total_deductions = 0
        for ded in deductions_data:
            try:
                ded_amount = float(ded.get('amount', 0))
                if ded_amount < 0 :
                     return jsonify({'status': 'error', 'message': f"Deduction amount for '{ded.get('description')}' cannot be negative."}), 400
                total_deductions += ded_amount
            except (ValueError, TypeError):
                return jsonify({'status': 'error', 'message': f"Invalid amount for deduction: {ded.get('description')}"}), 400
            if not ded.get('description') or not ded.get('type'):
                return jsonify({'status': 'error', 'message': 'Each deduction must have a description and type.'}), 400


        net_pay = gross_pay - total_deductions
        if net_pay < 0:
            # This could be valid if deductions exceed gross, but flag it.
            current_app.logger.warning(f"Net pay is negative for gross: {gross_pay}, deductions: {total_deductions}")
            # Depending on policy, you might want to return an error or just proceed.

        # 1. Create the Net Pay income transaction
        net_pay_category_id = get_net_pay_category_id(conn)
        if net_pay_category_id is None:
            # This is a critical setup issue if category can't be found/created
            current_app.logger.error("Net pay category ID could not be determined. Aborting paycheck log.")
            return jsonify({'status': 'error', 'message': 'Could not determine category for net pay. Please ensure a "Salary" or "Paycheck Deposit" category exists.'}), 500

        net_pay_description = f"Net Pay - {employer_name if employer_name else 'Paycheck'}"
        
        cursor = conn.execute(
            "INSERT INTO transactions (amount, category_id, date, type, description) VALUES (?, ?, ?, ?, ?)",
            (net_pay, net_pay_category_id, pay_date_str, 'income', net_pay_description)
        )
        net_pay_transaction_id = cursor.lastrowid
        current_app.logger.info(f"Logged net pay income transaction. ID: {net_pay_transaction_id}, Amount: {net_pay}")

        # 2. Create the Paycheck record
        cursor = conn.execute(
            "INSERT INTO paychecks (pay_date, employer_name, gross_pay, net_pay_transaction_id, notes) VALUES (?, ?, ?, ?, ?)",
            (pay_date_str, employer_name, gross_pay, net_pay_transaction_id, notes)
        )
        paycheck_id = cursor.lastrowid
        current_app.logger.info(f"Logged paycheck record. ID: {paycheck_id}")

        # 3. Create Paycheck Deduction records
        for ded in deductions_data:
            conn.execute(
                "INSERT INTO paycheck_deductions (paycheck_id, description, amount, type) VALUES (?, ?, ?, ?)",
                (paycheck_id, ded['description'], float(ded['amount']), ded['type'])
            )
        current_app.logger.info(f"Logged {len(deductions_data)} deductions for paycheck ID: {paycheck_id}")

        conn.commit()
        return jsonify({'status': 'success', 'message': 'Paycheck logged successfully!', 'paycheck_id': paycheck_id, 'net_pay_transaction_id': net_pay_transaction_id}), 201

    except sqlite3.Error as e:
        conn.rollback()
        current_app.logger.error(f"Database error logging paycheck: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Database error: {e}'}), 500
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Unexpected error logging paycheck: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'An unexpected error occurred: {e}'}), 500

