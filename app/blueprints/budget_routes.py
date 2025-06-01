# app/blueprints/budget_routes.py
# Blueprint for budget goal management.

from flask import Blueprint, request, redirect, url_for, flash
from app.database import get_db # Use get_db from the database module
from app.utils.helpers import format_month_name # Import helper
import datetime
import sqlite3


bp = Blueprint('budgets', __name__) # url_prefix='/budget'

@bp.route('/set', methods=['POST'])
def set_budget_goal():
    try:
        year = request.form.get('year', type=int)
        month = request.form.get('month', type=int)
        # These will be lists from the form
        category_ids_str = request.form.getlist('budget_category_id') 
        budgeted_amounts_str = request.form.getlist('budgeted_amount')

        if not all([year, month]):
            flash("Year and month are required for budget setting.", "error")
            return redirect(request.referrer or url_for('main.index'))
        
        if len(category_ids_str) != len(budgeted_amounts_str):
            flash("Data mismatch: Number of category IDs does not match number of budget amounts.", "error")
            return redirect(request.referrer or url_for('main.index'))

        conn = get_db()
        updated_count = 0
        for i in range(len(category_ids_str)):
            try:
                cat_id = int(category_ids_str[i])
                amount_str = budgeted_amounts_str[i].strip()
                
                budgeted_amount = 0.0 # Default to 0 if input is empty or invalid after trying
                if amount_str: # Only process if there's some input, otherwise it's 0
                    try:
                        budgeted_amount = float(amount_str)
                        if budgeted_amount < 0:
                            flash(f"Budget for category ID {cat_id} cannot be negative. Setting to 0.", "warning")
                            budgeted_amount = 0.0
                    except ValueError:
                        flash(f"Invalid amount '{amount_str}' for category ID {cat_id}. Setting to 0.", "warning")
                        budgeted_amount = 0.0 # Treat as 0 if invalid
                
                # UPSERT logic: Insert or update the budget goal
                conn.execute("""
                    INSERT INTO budget_goals (category_id, year, month, budgeted_amount) 
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(category_id, year, month) DO UPDATE SET
                    budgeted_amount = excluded.budgeted_amount;
                """, (cat_id, year, month, budgeted_amount))
                updated_count +=1 # Count even if amount is 0, as it's an explicit set/update
            except ValueError: # For cat_id conversion
                flash(f"Invalid category ID '{category_ids_str[i]}'. Skipped.", "warning")
                continue # Skip this entry
        
        conn.commit()
        if updated_count > 0:
            flash(f"{updated_count} budget goal(s) saved successfully for {format_month_name(month)} {year}!", "success")
        else:
            flash("No budget goals were explicitly submitted or changed.", "info")

    except Exception as e:
        flash(f"Error saving budget goal(s): {e}", "error")
        print(f"Error set_budget_goal: {e}")
    
    # Redirect back to the page they were on, ensuring budget planner reopens with correct period
    budget_year_redirect = request.form.get('year', default=datetime.datetime.now().year, type=int)
    budget_month_redirect = request.form.get('month', default=datetime.datetime.now().month, type=int)
    
    return redirect(url_for('main.index', budget_year=budget_year_redirect, budget_month=budget_month_redirect, open_budget_planner='true'))
