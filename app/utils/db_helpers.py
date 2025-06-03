# app/utils/db_helpers.py
# Helper functions for database interactions and data processing.

from flask import current_app # For logging
from app.database import get_db # Import get_db from the database module
import sqlite3 # For specific error handling like IntegrityError
import datetime # For date validation if needed

def get_categories_for_management():
    """
    Retrieves all main categories and their subcategories for management UI.
    """
    db = get_db()
    main_categories_data = db.execute("""
        SELECT id, name, financial_goal_type FROM categories 
        WHERE parent_id IS NULL ORDER BY name ASC
    """).fetchall()
    managed_categories = []
    for mc_row in main_categories_data:
        sub_categories_data = db.execute("""
            SELECT id, name, financial_goal_type FROM categories 
            WHERE parent_id = ? ORDER BY name ASC
        """, (mc_row['id'],)).fetchall()
        managed_categories.append({
            'id': mc_row['id'], 'name': mc_row['name'], 
            'financial_goal_type': mc_row['financial_goal_type'],
            'sub_categories': [{'id': s['id'], 'name': s['name'], 
                                'financial_goal_type': s['financial_goal_type']} 
                               for s in sub_categories_data],
            'has_sub_categories': len(sub_categories_data) > 0
        })
    return managed_categories

def get_hierarchical_categories_for_js():
    """
    Retrieves categories in a hierarchical structure suitable for JavaScript dropdowns.
    """
    db = get_db()
    main_categories_list = []
    sub_categories_map = {} # Maps main category ID to list of its subcategories
    main_cats_db = db.execute(
        "SELECT id, name, financial_goal_type FROM categories WHERE parent_id IS NULL ORDER BY name ASC"
    ).fetchall()
    for mc in main_cats_db:
        main_categories_list.append({
            "id": mc["id"], "name": mc["name"], 
            "financial_goal_type": mc["financial_goal_type"]
        })
        subs = db.execute(
            "SELECT id, name, financial_goal_type FROM categories WHERE parent_id = ? ORDER BY name ASC", 
            (mc["id"],)
        ).fetchall()
        sub_list = [{"id": s["id"], "name": s["name"], 
                     "financial_goal_type": s["financial_goal_type"]} 
                    for s in subs] if subs else []
        sub_categories_map[str(mc["id"])] = sub_list # Use string ID as key for JS
    return {"main_categories": main_categories_list, "sub_categories_map": sub_categories_map}

def get_financial_summary(year, month=None, period_type='monthly', focused_main_category_id=None):
    """
    Calculates financial summary including budgeted vs. actual amounts for categories.
    Args:
        year (int): The year for the summary.
        month (int, optional): The month for the summary (1-12). Required if period_type is 'monthly'.
        period_type (str): 'monthly' or 'yearly'.
        focused_main_category_id (int, optional): If provided, summary focuses on this main category and its subs.
    Returns:
        dict: Contains summary table data, chart data, and period totals.
    """
    db = get_db()
    
    # Base conditions for SQL queries
    actuals_subquery_conditions_expense = "strftime('%Y', date) = ? AND type = 'expense'"
    actuals_subquery_conditions_income = "strftime('%Y', date) = ? AND type = 'income'"
    budget_subquery_conditions = "year = ?"
    
    query_params_actuals_expense = [str(year)]
    query_params_actuals_income = [str(year)]
    query_params_budget = [year]

    if period_type == 'monthly':
        if month is None:
            current_app.logger.error("Month is None for monthly period_type in get_financial_summary. This should be handled by the caller.")
            # Defaulting or raising an error might be options, but caller should ensure month is provided.
            # For now, proceed assuming month will be valid if period_type is 'monthly'.
            # If this path is reached with month=None, queries might fail or return unexpected results.
            # Consider raising ValueError("Month must be provided for monthly summary.")
            pass # Assuming month will be valid based on route logic

        actuals_subquery_conditions_expense += " AND strftime('%m', date) = ?"
        actuals_subquery_conditions_income += " AND strftime('%m', date) = ?"
        budget_subquery_conditions += " AND month = ?"
        
        query_params_actuals_expense.append(f"{month:02d}") # Format month to two digits
        query_params_actuals_income.append(f"{month:02d}")
        query_params_budget.append(month)

    # Calculate period totals
    period_total_expenses_row = db.execute(
        f"SELECT SUM(amount) FROM transactions WHERE {actuals_subquery_conditions_expense}", 
        query_params_actuals_expense
    ).fetchone()
    period_total_expenses = period_total_expenses_row[0] if period_total_expenses_row and period_total_expenses_row[0] is not None else 0.0

    period_total_income_row = db.execute(
        f"SELECT SUM(amount) FROM transactions WHERE {actuals_subquery_conditions_income}",
        query_params_actuals_income
    ).fetchone()
    period_total_income = period_total_income_row[0] if period_total_income_row and period_total_income_row[0] is not None else 0.0

    period_total_budgeted_row = db.execute(
        f"SELECT SUM(budgeted_amount) FROM budget_goals WHERE {budget_subquery_conditions}",
        query_params_budget
    ).fetchone()
    period_total_budgeted = period_total_budgeted_row[0] if period_total_budgeted_row and period_total_budgeted_row[0] is not None else 0.0

    # Query for detailed category data
    category_details_query = f"""
        SELECT 
            c.id as category_id, 
            c.name as category_name, 
            c.parent_id,
            p.name as parent_category_name, 
            c.financial_goal_type,
            COALESCE(b.total_budgeted_amount, 0) as budgeted_amount,
            COALESCE(a.total_actual_amount, 0) as actual_amount
        FROM categories c
        LEFT JOIN categories p ON c.parent_id = p.id
        LEFT JOIN (
            SELECT category_id, SUM(amount) as total_actual_amount 
            FROM transactions
            WHERE {actuals_subquery_conditions_expense} 
            GROUP BY category_id
        ) a ON c.id = a.category_id
        LEFT JOIN (
            SELECT category_id, SUM(budgeted_amount) as total_budgeted_amount 
            FROM budget_goals 
            WHERE {budget_subquery_conditions}
            GROUP BY category_id
        ) b ON c.id = b.category_id
        ORDER BY COALESCE(p.name, c.name), c.name; 
    """
    
    combined_query_params_for_details = query_params_actuals_expense + query_params_budget
    current_app.logger.debug(f"Financial Summary Query Params - Details Query: {combined_query_params_for_details}")
    all_category_data = db.execute(category_details_query, combined_query_params_for_details).fetchall()
    
    # Initialize structures for summary and chart data
    summary_table_data = []
    expected_vs_actual_chart = {'labels': [], 'budgeted_data': [], 'actual_data': [], 'category_ids_for_drilldown': []}
    nws_actual_chart = {'labels': ['Needs', 'Wants', 'Savings/Investments', 'Unclassified'], 'data': [0.0, 0.0, 0.0, 0.0]}
    nws_budgeted_chart = {'labels': ['Needs', 'Wants', 'Savings/Investments', 'Unclassified'], 'data': [0.0, 0.0, 0.0, 0.0]}
    
    current_chart_title_suffix = "Main Categories"
    focused_main_category_name = None

    # Process data based on whether a main category is focused
    if focused_main_category_id:
        focused_main_cat_row = db.execute("SELECT name FROM categories WHERE id = ?", (focused_main_category_id,)).fetchone()
        if focused_main_cat_row:
            focused_main_category_name = focused_main_cat_row['name']
            current_chart_title_suffix = f"Subcategories of {focused_main_category_name}"
        
        for cat_data in all_category_data:
            # Check if the category is the focused main category itself or one of its direct subcategories
            is_focused_main = cat_data['category_id'] == focused_main_category_id and cat_data['parent_id'] is None
            is_sub_of_focused = cat_data['parent_id'] == focused_main_category_id

            if is_focused_main or is_sub_of_focused:
                if cat_data['budgeted_amount'] > 0 or cat_data['actual_amount'] > 0: # Only include if there's data
                    full_name = cat_data['category_name']
                    # If it's the main category itself and it has subcategories, label it as "(Direct)" expenses/budget
                    if is_focused_main and not is_sub_of_focused: 
                        has_subs_check = db.execute("SELECT 1 FROM categories WHERE parent_id = ? LIMIT 1", (cat_data['category_id'],)).fetchone()
                        if has_subs_check: 
                             full_name = f"{cat_data['category_name']} (Direct)" 
                        
                    summary_table_data.append({
                        "name": full_name, "type": cat_data['financial_goal_type'], 
                        "budgeted": cat_data['budgeted_amount'], "actual": cat_data['actual_amount'], 
                        "variance": cat_data['budgeted_amount'] - cat_data['actual_amount']
                    })
                    expected_vs_actual_chart['labels'].append(full_name)
                    expected_vs_actual_chart['budgeted_data'].append(cat_data['budgeted_amount'])
                    expected_vs_actual_chart['actual_data'].append(cat_data['actual_amount'])
                    # No further drilldown from subcategory view in this chart
                    expected_vs_actual_chart['category_ids_for_drilldown'].append(None) 
                    
                    # Aggregate for NWS charts based on financial_goal_type
                    goal_type = cat_data['financial_goal_type']
                    idx = {'Need': 0, 'Want': 1, 'Saving': 2}.get(goal_type, 3) # 3 for 'Unclassified'
                    nws_actual_chart['data'][idx] += cat_data['actual_amount']
                    nws_budgeted_chart['data'][idx] += cat_data['budgeted_amount']
    else: # Main categories overview
        main_category_summary = {} # Aggregate data for main categories
        for cat_data in all_category_data:
            # Determine the main category ID to aggregate under
            main_id_to_aggregate = cat_data['parent_id'] if cat_data['parent_id'] is not None else cat_data['category_id']
            
            if main_id_to_aggregate not in main_category_summary:
                # Get the name of the main category for display
                main_cat_name_for_summary = ""
                if cat_data['parent_id'] is not None: 
                    main_cat_name_for_summary = cat_data['parent_category_name']
                else: 
                    main_cat_name_for_summary = cat_data['category_name']
                
                # Fallback if name isn't directly available (should be rare)
                if not main_cat_name_for_summary: 
                     main_cat_name_row = db.execute("SELECT name FROM categories WHERE id = ?", (main_id_to_aggregate,)).fetchone()
                     main_cat_name_for_summary = main_cat_name_row['name'] if main_cat_name_row else "Unknown Main Category"

                main_category_summary[main_id_to_aggregate] = {
                    'name': main_cat_name_for_summary, 'budgeted': 0.0, 'actual': 0.0, 
                    'id': main_id_to_aggregate, 
                    'nws_budgeted': [0.0,0.0,0.0,0.0], # Needs, Wants, Savings, Unclassified
                    'nws_actual': [0.0,0.0,0.0,0.0]
                }
            
            # Aggregate budgeted and actual amounts
            main_category_summary[main_id_to_aggregate]['budgeted'] += cat_data['budgeted_amount']
            main_category_summary[main_id_to_aggregate]['actual'] += cat_data['actual_amount']
            
            # Aggregate for NWS charts based on financial_goal_type of the specific category (main or sub)
            goal_type = cat_data['financial_goal_type']
            idx = {'Need': 0, 'Want': 1, 'Saving': 2}.get(goal_type, 3)
            main_category_summary[main_id_to_aggregate]['nws_actual'][idx] += cat_data['actual_amount']
            main_category_summary[main_id_to_aggregate]['nws_budgeted'][idx] += cat_data['budgeted_amount']

        # Prepare data for charts and table from aggregated main category summaries
        sorted_main_cat_ids = sorted(main_category_summary.keys(), key=lambda x: main_category_summary[x]['name'])
        for main_id in sorted_main_cat_ids:
            summary = main_category_summary[main_id]
            if summary['budgeted'] > 0 or summary['actual'] > 0: # Only include if there's data
                summary_table_data.append({
                    "name": summary['name'], "type": "Main", # Type for display in table
                    "budgeted": summary['budgeted'], "actual": summary['actual'], 
                    "variance": summary['budgeted'] - summary['actual']
                })
                expected_vs_actual_chart['labels'].append(summary['name'])
                expected_vs_actual_chart['budgeted_data'].append(summary['budgeted'])
                expected_vs_actual_chart['actual_data'].append(summary['actual'])
                # Allow drilldown for main categories in this chart
                expected_vs_actual_chart['category_ids_for_drilldown'].append(summary['id']) 
                
                # Sum up NWS data from each main category's aggregated NWS values
                for i in range(4): # 0:Needs, 1:Wants, 2:Savings, 3:Unclassified
                    nws_budgeted_chart['data'][i] += summary['nws_budgeted'][i]
                    nws_actual_chart['data'][i] += summary['nws_actual'][i]
                    
    return {
        "summary_table_data": summary_table_data, 
        "expected_vs_actual_chart": expected_vs_actual_chart, 
        "nws_actual_chart": nws_actual_chart, 
        "nws_budgeted_chart": nws_budgeted_chart, 
        "current_chart_title_suffix": current_chart_title_suffix, 
        "focused_main_category_id": focused_main_category_id, 
        "focused_main_category_name": focused_main_category_name,
        "period_total_expenses": period_total_expenses,
        "period_total_income": period_total_income,
        "period_total_budgeted": period_total_budgeted
    }

def get_budget_goals_for_planning_ui(year, month):
    """
    Retrieves budget goals for a specific year and month, structured for UI planning.
    """
    db = get_db()
    all_categories_structured = get_categories_for_management() # Get all categories
    budget_goals_map = {} # Maps category_id to its budgeted_amount for the given period

    # Fetch existing budget goals for the specified year and month
    goals_db = db.execute(
        "SELECT category_id, budgeted_amount FROM budget_goals WHERE year = ? AND month = ?", 
        (year, month)
    ).fetchall()
    for goal in goals_db:
        budget_goals_map[goal['category_id']] = goal['budgeted_amount']

    # Populate structured categories with their budgeted amounts
    for main_cat in all_categories_structured:
        # Budgeted amount directly for the main category (if it has no subs or is budgeted directly)
        main_cat['budgeted_amount_direct'] = budget_goals_map.get(main_cat['id'], 0.0) 
        main_cat['budgeted_amount_from_subs'] = 0.0 # Initialize sum from subcategories
        
        if main_cat['has_sub_categories']:
            sum_of_sub_budgets = 0.0
            for sub_cat in main_cat['sub_categories']:
                sub_cat['budgeted_amount'] = budget_goals_map.get(sub_cat['id'], 0.0)
                sum_of_sub_budgets += sub_cat['budgeted_amount']
            main_cat['budgeted_amount_from_subs'] = sum_of_sub_budgets
            # Main category's total budget is the sum of its subcategories' budgets
            main_cat['budgeted_amount'] = sum_of_sub_budgets 
        else:
            # If no subcategories, its budget is what's directly assigned
            main_cat['budgeted_amount'] = main_cat['budgeted_amount_direct']
            
    return all_categories_structured

# --- NEW Goal Management Helper Functions ---

def get_or_create_special_category_id(category_name: str, desired_transaction_type: str, parent_category_name: str = "System") -> int:
    """
    Finds or creates a special category (e.g., "Goal Contributions") under a parent (e.g., "System").
    Args:
        category_name (str): The name of the special category (e.g., "Goal Contributions").
        desired_transaction_type (str): 'expense' or 'income'. Used for context, not directly in category creation logic here.
        parent_category_name (str): The name of the parent category. Defaults to "System".
    Returns:
        int: The ID of the found or created special category, or None on failure.
    """
    db = get_db()
    cursor = db.cursor()
    parent_id = None

    # 1. Find or create the parent category (e.g., "System")
    try:
        cursor.execute("SELECT id FROM categories WHERE name = ? AND parent_id IS NULL", (parent_category_name,))
        parent_row = cursor.fetchone()
        if parent_row:
            parent_id = parent_row['id']
        else:
            cursor.execute("INSERT INTO categories (name, parent_id) VALUES (?, NULL)", (parent_category_name,))
            parent_id = cursor.lastrowid
            current_app.logger.info(f"Created parent category '{parent_category_name}' with ID: {parent_id}")
    except sqlite3.IntegrityError: # Should be caught by the SELECT first, but as a safeguard
        cursor.execute("SELECT id FROM categories WHERE name = ? AND parent_id IS NULL", (parent_category_name,))
        parent_row = cursor.fetchone()
        if parent_row: parent_id = parent_row['id']
        else: # This case indicates a more complex issue if IntegrityError occurred but SELECT fails
            current_app.logger.error(f"IntegrityError for parent category '{parent_category_name}', but could not retrieve it.")
            db.rollback() # Rollback if parent creation failed unexpectedly
            return None
    except Exception as e:
        current_app.logger.error(f"Error finding/creating parent category '{parent_category_name}': {e}")
        db.rollback()
        return None
        
    if parent_id is None:
        current_app.logger.error(f"Failed to obtain ID for parent category '{parent_category_name}'.")
        return None

    # 2. Find or create the special child category (e.g., "Goal Contributions")
    try:
        cursor.execute("SELECT id FROM categories WHERE name = ? AND parent_id = ?", (category_name, parent_id))
        child_row = cursor.fetchone()
        if child_row:
            child_id = child_row['id']
        else:
            cursor.execute("INSERT INTO categories (name, parent_id) VALUES (?, ?)", (category_name, parent_id))
            child_id = cursor.lastrowid
            current_app.logger.info(f"Created special category '{category_name}' under '{parent_category_name}' with ID: {child_id}")
        
        db.commit() # Commit changes for category creation
        return child_id
    except sqlite3.IntegrityError: # Should be caught by SELECT first
        cursor.execute("SELECT id FROM categories WHERE name = ? AND parent_id = ?", (category_name, parent_id))
        child_row = cursor.fetchone()
        if child_row: 
            db.commit() # Commit if it was just a concurrent write that already succeeded
            return child_row['id']
        current_app.logger.error(f"IntegrityError for child category '{category_name}', but could not retrieve it.")
        db.rollback()
        return None
    except Exception as e:
        current_app.logger.error(f"Error finding/creating child category '{category_name}': {e}")
        db.rollback()
        return None

def add_goal(name: str, target_amount: float, target_date: str = None) -> int:
    """
    Adds a new financial goal to the database.
    Args:
        name (str): Name of the goal.
        target_amount (float): The target monetary amount for the goal.
        target_date (str, optional): Target date in 'YYYY-MM-DD' format.
    Returns:
        int: The ID of the newly created goal, or None on failure.
    """
    db = get_db()
    try:
        # Validate target_date format if provided
        if target_date:
            datetime.datetime.strptime(target_date, '%Y-%m-%d')

        cursor = db.execute(
            "INSERT INTO goals (name, target_amount, target_date) VALUES (?, ?, ?)",
            (name, target_amount, target_date)
        )
        db.commit()
        current_app.logger.info(f"Added goal '{name}' with ID: {cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Handles UNIQUE constraint on name
        current_app.logger.warning(f"Goal with name '{name}' already exists.")
        db.rollback()
        return None
    except ValueError: # For invalid date format
        current_app.logger.error(f"Invalid target_date format for goal '{name}': {target_date}. Must be YYYY-MM-DD.")
        db.rollback()
        return None
    except Exception as e:
        current_app.logger.error(f"Error adding goal '{name}': {e}")
        db.rollback()
        return None

def get_goal_by_id(goal_id: int) -> dict:
    """
    Retrieves a specific goal by its ID.
    Args:
        goal_id (int): The ID of the goal.
    Returns:
        dict: Goal details (as a dictionary) or None if not found.
    """
    db = get_db()
    row = db.execute(
        "SELECT id, name, target_amount, current_amount, target_date, is_completed, created_at FROM goals WHERE id = ?",
        (goal_id,)
    ).fetchone()
    if row:
        goal = dict(row)
        goal['progress'] = (goal['current_amount'] / goal['target_amount'] * 100) if goal['target_amount'] > 0 else 0
        return goal
    return None

def get_all_goals() -> list:
    """
    Retrieves all financial goals from the database.
    Returns:
        list: A list of dictionaries, where each dictionary represents a goal,
              including a calculated 'progress' percentage.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT id, name, target_amount, current_amount, target_date, is_completed, created_at 
        FROM goals ORDER BY created_at DESC
        """
    ).fetchall()
    goals_list = []
    for row in rows:
        goal = dict(row)
        goal['progress'] = (goal['current_amount'] / goal['target_amount'] * 100) if goal['target_amount'] > 0 else 0
        goals_list.append(goal)
    return goals_list

def update_goal_details(goal_id: int, name: str = None, target_amount: float = None, target_date: str = None, is_completed: bool = None) -> bool:
    """
    Updates details of an existing financial goal.
    Only provided fields are updated.
    Args:
        goal_id (int): The ID of the goal to update.
        name (str, optional): New name for the goal.
        target_amount (float, optional): New target amount.
        target_date (str, optional): New target date ('YYYY-MM-DD'). Pass empty string to clear.
        is_completed (bool, optional): New completion status.
    Returns:
        bool: True on success, False on failure.
    """
    db = get_db()
    fields_to_update = []
    params = []

    if name is not None:
        fields_to_update.append("name = ?")
        params.append(name)
    if target_amount is not None:
        fields_to_update.append("target_amount = ?")
        params.append(float(target_amount))
    if target_date is not None: # Allows clearing the date with an empty string
        if target_date == "":
            fields_to_update.append("target_date = NULL")
        else:
            try: # Validate date format before attempting to set it
                datetime.datetime.strptime(target_date, '%Y-%m-%d')
                fields_to_update.append("target_date = ?")
                params.append(target_date)
            except ValueError:
                current_app.logger.error(f"Invalid target_date format for goal update (ID: {goal_id}): {target_date}. Date not updated.")
                # Optionally, return False or raise an error here if strict date validation is required for updates
    if is_completed is not None:
        fields_to_update.append("is_completed = ?")
        params.append(1 if is_completed else 0)

    if not fields_to_update:
        current_app.logger.info(f"No fields provided to update for goal ID: {goal_id}")
        return True # No changes attempted, considered success

    params.append(goal_id)
    update_query = f"UPDATE goals SET {', '.join(fields_to_update)} WHERE id = ?"
    
    try:
        cursor = db.execute(update_query, tuple(params))
        db.commit()
        if cursor.rowcount > 0:
            current_app.logger.info(f"Updated goal ID: {goal_id}")
            return True
        else:
            current_app.logger.warning(f"Goal ID: {goal_id} not found for update, or no changes made.")
            return False # Goal not found or data was the same
    except sqlite3.IntegrityError: # Handles UNIQUE constraint on name if name is being changed
        current_app.logger.warning(f"Failed to update goal ID: {goal_id} due to integrity error (e.g., name conflict).")
        db.rollback()
        return False
    except Exception as e:
        current_app.logger.error(f"Error updating goal ID {goal_id}: {e}")
        db.rollback()
        return False

def delete_goal(goal_id: int) -> bool:
    """
    Deletes a financial goal from the database.
    Also attempts to delete related "Goal Contributions" and "Goal Withdrawals" transactions.
    Args:
        goal_id (int): The ID of the goal to delete.
    Returns:
        bool: True on success, False on failure.
    """
    db = get_db()
    try:
        # Before deleting the goal, consider handling related transactions.
        # For simplicity here, we'll delete the goal. In a real app, you might archive
        # or re-categorize transactions linked to this goal if they are not managed by specific
        # "Goal Contribution/Withdrawal" categories that are also being cleaned up.
        # The prompt does not specify cascading delete for transactions linked to goals
        # via the special categories, as transactions are linked to categories, not goals directly.

        # Check if the goal exists
        goal_check = db.execute("SELECT 1 FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not goal_check:
            current_app.logger.warning(f"Attempted to delete non-existent goal ID: {goal_id}")
            return False

        # Note: Transactions for goal funding are linked via categories like "Goal Contributions".
        # Deleting the goal itself doesn't automatically delete these transactions unless
        # those categories are also deleted and have ON DELETE CASCADE for transactions.
        # The prompt implies these categories are persistent ("System" categories).
        # Thus, deleting a goal here means the funding transactions remain under those system categories.
        # If the requirement was to also delete all funding transactions for this specific goal,
        # that would require a more complex lookup (e.g., if transactions stored goal_id, or via description parsing).
        # Given the current schema, we just delete the goal record.

        cursor = db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        db.commit()
        if cursor.rowcount > 0:
            current_app.logger.info(f"Deleted goal ID: {goal_id}")
            return True
        else:
            # This case should be caught by the goal_check above.
            current_app.logger.warning(f"Goal ID: {goal_id} not found for deletion (after initial check).")
            return False
    except Exception as e:
        current_app.logger.error(f"Error deleting goal ID {goal_id}: {e}")
        db.rollback()
        return False

def record_goal_funding_transaction(goal_id: int, amount_for_goal: float, transaction_date: str, description: str, is_contribution: bool) -> bool:
    """
    Records a transaction related to funding a goal and updates the goal's current amount.
    Args:
        goal_id (int): The ID of the goal.
        amount_for_goal (float): The amount to contribute or withdraw. Must be positive.
        transaction_date (str): Date of the transaction ('YYYY-MM-DD').
        description (str): Description for the transaction.
        is_contribution (bool): True if adding money to the goal (expense), False if withdrawing (income).
    Returns:
        bool: True on success, False on failure.
    """
    db = get_db()
    if amount_for_goal <= 0:
        current_app.logger.error(f"Amount for goal funding must be positive. Goal ID: {goal_id}, Amount: {amount_for_goal}")
        return False

    try:
        # Validate transaction_date format
        datetime.datetime.strptime(transaction_date, '%Y-%m-%d')
    except ValueError:
        current_app.logger.error(f"Invalid transaction_date format for goal funding (ID: {goal_id}): {transaction_date}. Must be YYYY-MM-DD.")
        return False

    goal = get_goal_by_id(goal_id) # Fetch goal to check existence and current amount
    if not goal:
        current_app.logger.error(f"Goal ID: {goal_id} not found for funding transaction.")
        return False
    if goal['is_completed'] and is_contribution:
        current_app.logger.warning(f"Attempting to contribute to an already completed goal ID: {goal_id}.")
        # Allow contribution to completed goals if needed, or return False here. For now, allowing.

    category_name = "Goal Contributions" if is_contribution else "Goal Withdrawals"
    transaction_type = 'expense' if is_contribution else 'income'
    
    category_id = get_or_create_special_category_id(category_name, transaction_type)
    if category_id is None:
        current_app.logger.error(f"Failed to get or create category '{category_name}' for goal funding.")
        return False # get_or_create_special_category_id handles its own rollback/commit for category creation

    try:
        # Start a transaction for updating goal and inserting transaction record
        db.execute("BEGIN")

        # 1. Insert the transaction
        full_description = f"{description} (Goal: {goal['name']})" if description else f"{category_name} for Goal: {goal['name']}"
        db.execute(
            "INSERT INTO transactions (amount, category_id, date, type, description) VALUES (?, ?, ?, ?, ?)",
            (amount_for_goal, category_id, transaction_date, transaction_type, full_description)
        )
        current_app.logger.info(f"Inserted funding transaction: Type={transaction_type}, Amount={amount_for_goal}, CatID={category_id} for GoalID={goal_id}")

        # 2. Update the goal's current_amount
        new_current_amount = goal['current_amount'] + (amount_for_goal if is_contribution else -amount_for_goal)
        
        # Ensure current_amount doesn't go below zero due to withdrawal
        if new_current_amount < 0 and not is_contribution:
            current_app.logger.warning(f"Withdrawal for goal ID {goal_id} would make current_amount negative. Setting to 0.")
            new_current_amount = 0
            # Optionally, adjust the actual withdrawn transaction amount if it exceeds current_amount,
            # or prevent the transaction. For now, goal current_amount won't go negative.

        db.execute(
            "UPDATE goals SET current_amount = ? WHERE id = ?",
            (new_current_amount, goal_id)
        )
        current_app.logger.info(f"Updated goal ID {goal_id} current_amount to {new_current_amount}")
        
        db.commit() # Commit both operations
        return True
    except Exception as e:
        db.rollback() # Rollback if any operation failed
        current_app.logger.error(f"Error recording goal funding for Goal ID {goal_id}: {e}")
        return False

