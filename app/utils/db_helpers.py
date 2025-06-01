# app/utils/db_helpers.py
# Helper functions for database interactions and data processing.

from flask import current_app # For logging
from app.database import get_db # Import get_db from the database module

def get_categories_for_management():
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
    db = get_db()
    main_categories_list = []
    sub_categories_map = {}
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
        sub_categories_map[str(mc["id"])] = sub_list
    return {"main_categories": main_categories_list, "sub_categories_map": sub_categories_map}

def get_financial_summary(year, month=None, period_type='monthly', focused_main_category_id=None):
    """
    Generates financial summary data for charts and tables.
    Can be monthly or yearly.
    - year: The year for the summary.
    - month: The month (1-12) for 'monthly' period_type. Ignored for 'yearly'.
    - period_type: 'monthly' or 'yearly'.
    - focused_main_category_id: ID of main category to drill down into its subcategories.
    """
    db = get_db()
    
    actuals_subquery_conditions = "strftime('%Y', date) = ? AND type = 'expense'"
    budget_subquery_conditions = "year = ?"
    query_params_actuals = [str(year)]
    query_params_budget = [year]

    if period_type == 'monthly':
        if month is None:
            raise ValueError("Month must be provided for monthly summary.")
        actuals_subquery_conditions += " AND strftime('%m', date) = ?"
        budget_subquery_conditions += " AND month = ?"
        query_params_actuals.append(f"{month:02d}")
        query_params_budget.append(month)
    # For 'yearly', no additional month conditions are needed for the base queries.
    # The SUM() aggregate function will handle summing over the year.

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
            WHERE {actuals_subquery_conditions}
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
    
    current_app.logger.debug(f"Financial Summary Query Params - Actuals: {query_params_actuals}, Budget: {query_params_budget}")
    all_category_data = db.execute(category_details_query, query_params_actuals + query_params_budget).fetchall()
    
    summary_table_data = []
    expected_vs_actual_chart = {'labels': [], 'budgeted_data': [], 'actual_data': [], 'category_ids_for_drilldown': []}
    nws_actual_chart = {'labels': ['Needs', 'Wants', 'Savings/Investments', 'Unclassified'], 'data': [0.0, 0.0, 0.0, 0.0]}
    nws_budgeted_chart = {'labels': ['Needs', 'Wants', 'Savings/Investments', 'Unclassified'], 'data': [0.0, 0.0, 0.0, 0.0]}
    
    current_chart_title_suffix = "Main Categories"
    focused_main_category_name = None

    if focused_main_category_id:
        focused_main_cat_row = db.execute("SELECT name FROM categories WHERE id = ?", (focused_main_category_id,)).fetchone()
        if focused_main_cat_row:
            focused_main_category_name = focused_main_cat_row['name']
            current_chart_title_suffix = f"Subcategories of {focused_main_category_name}"
        
        for cat_data in all_category_data:
            # Include if it's the focused main category itself OR a direct subcategory of the focused main category
            is_focused_main = cat_data['category_id'] == focused_main_category_id and cat_data['parent_id'] is None
            is_sub_of_focused = cat_data['parent_id'] == focused_main_category_id

            if is_focused_main or is_sub_of_focused:
                # Only add to chart/table if there's some financial activity or budget
                if cat_data['budgeted_amount'] > 0 or cat_data['actual_amount'] > 0:
                    full_name = cat_data['category_name']
                    if is_focused_main and not is_sub_of_focused: # If it's the main category itself in a sub-view context
                         # Check if it has subcategories to decide if it's "(Direct)" or just the name
                        has_subs_check = db.execute("SELECT 1 FROM categories WHERE parent_id = ? LIMIT 1", (cat_data['category_id'],)).fetchone()
                        if has_subs_check: # If it has subcategories, and we are focusing on it, this entry is for its direct budget/actuals
                             full_name = f"{cat_data['category_name']} (Direct)" 
                        # If it's a main category with no subs, just its name is fine.
                        
                    summary_table_data.append({
                        "name": full_name, 
                        "type": cat_data['financial_goal_type'], 
                        "budgeted": cat_data['budgeted_amount'], 
                        "actual": cat_data['actual_amount'], 
                        "variance": cat_data['budgeted_amount'] - cat_data['actual_amount']
                    })
                    expected_vs_actual_chart['labels'].append(full_name)
                    expected_vs_actual_chart['budgeted_data'].append(cat_data['budgeted_amount'])
                    expected_vs_actual_chart['actual_data'].append(cat_data['actual_amount'])
                    # No further drilldown from this subcategory view for the bar chart
                    expected_vs_actual_chart['category_ids_for_drilldown'].append(None) 
                    
                    goal_type = cat_data['financial_goal_type']
                    idx = {'Need': 0, 'Want': 1, 'Saving': 2}.get(goal_type, 3)
                    nws_actual_chart['data'][idx] += cat_data['actual_amount']
                    nws_budgeted_chart['data'][idx] += cat_data['budgeted_amount']
    else: # Main categories overview
        main_category_summary = {} 
        for cat_data in all_category_data:
            main_id_to_aggregate = cat_data['parent_id'] if cat_data['parent_id'] is not None else cat_data['category_id']
            
            if main_id_to_aggregate not in main_category_summary:
                main_cat_name_for_summary = ""
                if cat_data['parent_id'] is not None: 
                    main_cat_name_for_summary = cat_data['parent_category_name']
                else: 
                    main_cat_name_for_summary = cat_data['category_name']
                
                if not main_cat_name_for_summary: 
                     main_cat_name_row = db.execute("SELECT name FROM categories WHERE id = ?", (main_id_to_aggregate,)).fetchone()
                     main_cat_name_for_summary = main_cat_name_row['name'] if main_cat_name_row else "Unknown Main Category"

                main_category_summary[main_id_to_aggregate] = {
                    'name': main_cat_name_for_summary, 'budgeted': 0.0, 'actual': 0.0, 
                    'id': main_id_to_aggregate, 'nws_budgeted': [0.0,0.0,0.0,0.0], 'nws_actual': [0.0,0.0,0.0,0.0]
                }

            main_category_summary[main_id_to_aggregate]['budgeted'] += cat_data['budgeted_amount']
            main_category_summary[main_id_to_aggregate]['actual'] += cat_data['actual_amount']
            
            goal_type = cat_data['financial_goal_type']
            idx = {'Need': 0, 'Want': 1, 'Saving': 2}.get(goal_type, 3)
            main_category_summary[main_id_to_aggregate]['nws_actual'][idx] += cat_data['actual_amount']
            main_category_summary[main_id_to_aggregate]['nws_budgeted'][idx] += cat_data['budgeted_amount']

        sorted_main_cat_ids = sorted(main_category_summary.keys(), key=lambda x: main_category_summary[x]['name'])

        for main_id in sorted_main_cat_ids:
            summary = main_category_summary[main_id]
            if summary['budgeted'] > 0 or summary['actual'] > 0:
                summary_table_data.append({
                    "name": summary['name'], "type": "Main",
                    "budgeted": summary['budgeted'], "actual": summary['actual'], 
                    "variance": summary['budgeted'] - summary['actual']
                })
                expected_vs_actual_chart['labels'].append(summary['name'])
                expected_vs_actual_chart['budgeted_data'].append(summary['budgeted'])
                expected_vs_actual_chart['actual_data'].append(summary['actual'])
                expected_vs_actual_chart['category_ids_for_drilldown'].append(summary['id']) 
                
                for i in range(4):
                    nws_budgeted_chart['data'][i] += summary['nws_budgeted'][i]
                    nws_actual_chart['data'][i] += summary['nws_actual'][i]
                    
    return {
        "summary_table_data": summary_table_data, 
        "expected_vs_actual_chart": expected_vs_actual_chart, 
        "nws_actual_chart": nws_actual_chart, 
        "nws_budgeted_chart": nws_budgeted_chart, 
        "current_chart_title_suffix": current_chart_title_suffix, 
        "focused_main_category_id": focused_main_category_id, 
        "focused_main_category_name": focused_main_category_name
    }

def get_budget_goals_for_planning_ui(year, month):
    db = get_db()
    all_categories_structured = get_categories_for_management() 
    budget_goals_map = {}
    goals_db = db.execute(
        "SELECT category_id, budgeted_amount FROM budget_goals WHERE year = ? AND month = ?", 
        (year, month)
    ).fetchall()
    for goal in goals_db:
        budget_goals_map[goal['category_id']] = goal['budgeted_amount']

    for main_cat in all_categories_structured:
        main_cat['budgeted_amount_direct'] = budget_goals_map.get(main_cat['id'], 0.0) # Budget directly set on main_cat
        main_cat['budgeted_amount_from_subs'] = 0.0 # Sum of its subcategories' budgets

        if main_cat['has_sub_categories']:
            sum_of_sub_budgets = 0.0
            for sub_cat in main_cat['sub_categories']:
                sub_cat['budgeted_amount'] = budget_goals_map.get(sub_cat['id'], 0.0)
                sum_of_sub_budgets += sub_cat['budgeted_amount']
            main_cat['budgeted_amount_from_subs'] = sum_of_sub_budgets
            # The effective budgeted amount for display if it has subs is the sum of subs
            main_cat['budgeted_amount'] = sum_of_sub_budgets
        else:
            # If no subs, its effective budget is what's directly set on it
            main_cat['budgeted_amount'] = main_cat['budgeted_amount_direct']
            
    return all_categories_structured
