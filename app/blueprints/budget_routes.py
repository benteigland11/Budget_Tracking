# app/blueprints/budget_routes.py
# Blueprint for budget goal management.

from flask import Blueprint, request, redirect, url_for, flash, current_app
from app.database import get_db 
from app.utils.helpers import format_month_name 
import datetime
import sqlite3


bp = Blueprint('budgets', __name__) # url_prefix='/budget'

@bp.route('/set', methods=['POST'])
def set_budget_goal():
    has_errors = False
    budget_planning_year_from_form = request.form.get('year', type=int)
    budget_planning_month_from_form = request.form.get('month', type=int)

    # MODIFICATION: Added logging
    current_app.logger.info(f"Attempting to set budget goal for Year: {budget_planning_year_from_form}, Month: {budget_planning_month_from_form}")

    try:
        year = budget_planning_year_from_form
        month = budget_planning_month_from_form
        
        category_ids_str = request.form.getlist('budget_category_id') 
        budgeted_amounts_str = request.form.getlist('budgeted_amount')

        if not all([year, month]): # year or month from form could be None if not properly submitted or type conversion failed
            flash("Year and month are required and must be valid numbers for budget setting.", "error")
            current_app.logger.error(f"Budget setting failed: Year or Month missing/invalid. Year: {year}, Month: {month}")
            has_errors = True
        elif len(category_ids_str) != len(budgeted_amounts_str):
            flash("Data mismatch: Number of category IDs does not match number of budget amounts.", "error")
            current_app.logger.error("Budget setting failed: Category IDs and amounts list length mismatch.")
            has_errors = True
        
        if not has_errors:
            conn = get_db()
            updated_count = 0
            processed_categories = 0 

            for i in range(len(category_ids_str)):
                try:
                    cat_id_str = category_ids_str[i]
                    if not cat_id_str or not cat_id_str.isdigit():
                        current_app.logger.warning(f"Skipping budget entry with invalid category_id: '{cat_id_str}' at index {i}")
                        continue 
                    
                    cat_id = int(cat_id_str)
                    amount_str = budgeted_amounts_str[i].strip()
                    processed_categories +=1
                    
                    budgeted_amount = 0.0 
                    if amount_str: 
                        try:
                            budgeted_amount = float(amount_str)
                            if budgeted_amount < 0:
                                flash(f"Budget for category ID {cat_id} cannot be negative. Setting to 0.", "warning")
                                budgeted_amount = 0.0
                        except ValueError:
                            flash(f"Invalid amount '{amount_str}' for category ID {cat_id}. Setting to 0.", "warning")
                            budgeted_amount = 0.0 
                    
                    current_app.logger.info(f"Processing budget for Cat ID: {cat_id}, Year: {year}, Month: {month}, Amount: {budgeted_amount}")
                    cursor = conn.execute("""
                        INSERT INTO budget_goals (category_id, year, month, budgeted_amount) 
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(category_id, year, month) DO UPDATE SET
                        budgeted_amount = excluded.budgeted_amount;
                    """, (cat_id, year, month, budgeted_amount))
                    if cursor.rowcount > 0 : 
                        updated_count +=1 
                except ValueError as ve: 
                    flash(f"Invalid category ID format '{category_ids_str[i]}'. Skipped.", "warning")
                    current_app.logger.warning(f"ValueError for category ID '{category_ids_str[i]}': {ve}")
                    continue 
            
            conn.commit()

            if updated_count > 0:
                flash(f"{updated_count} budget goal(s) saved successfully for {format_month_name(month)} {year}!", "success")
            elif processed_categories > 0 and updated_count == 0 :
                 flash(f"Budget goals for {format_month_name(month)} {year} were processed, but no changes were detected from previous values.", "info")
            elif processed_categories == 0 and not has_errors: 
                flash("No valid budget data submitted to save.", "info")

    except Exception as e:
        flash(f"Error saving budget goal(s): {e}", "error")
        current_app.logger.error(f"Error set_budget_goal for Y:{budget_planning_year_from_form} M:{budget_planning_month_from_form}: {e}", exc_info=True)
        has_errors = True
    
    if has_errors:
        redirect_year = budget_planning_year_from_form if budget_planning_year_from_form is not None else datetime.datetime.now().year
        redirect_month = budget_planning_month_from_form if budget_planning_month_from_form is not None else datetime.datetime.now().month
        return redirect(url_for('main.index', budget_year=redirect_year, budget_month=redirect_month, open_budget_planner='true'))
    else:
        view_year = budget_planning_year_from_form if budget_planning_year_from_form is not None else datetime.datetime.now().year
        view_month = budget_planning_month_from_form if budget_planning_month_from_form is not None else datetime.datetime.now().month
        return redirect(url_for('main.index', year=view_year, month=view_month))

