# app/blueprints/main_routes.py
# Blueprint for main application routes like the dashboard.

from flask import Blueprint, render_template, request, g
from app.database import get_db # Use get_db from the database module
from app.utils import db_helpers # Import your db_helpers
import datetime
import json

bp = Blueprint('main', __name__) # No url_prefix, so this is the root

@bp.route('/')
def index():
    conn = get_db() # Use the get_db function
    current_time = datetime.datetime.now()
    current_year = current_time.year
    current_month = current_time.month

    view_year = request.args.get('year', default=current_year, type=int)
    view_month = request.args.get('month', default=current_month, type=int)
    focused_main_category_id_str = request.args.get('main_cat_focus')
    focused_main_category_id = int(focused_main_category_id_str) if focused_main_category_id_str and focused_main_category_id_str.isdigit() else None

    categories_for_management = db_helpers.get_categories_for_management()
    hierarchical_categories_for_js_data = db_helpers.get_hierarchical_categories_for_js()
    
    # Fetch transactions (simplified for brevity, actual query is more complex)
    transactions_data = conn.execute("""
        SELECT t.id, t.amount, t.category_id, c.name as category_name, 
               c.parent_id as category_parent_id, p.name as parent_category_name, 
               t.date, t.type
        FROM transactions t LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories p ON c.parent_id = p.id ORDER BY t.date DESC, t.id DESC
    """).fetchall()
    
    transactions_list = []
    for t_row in transactions_data:
        full_category_name = t_row['category_name']
        main_category_for_edit = None
        if t_row['parent_category_name']: 
            full_category_name = f"{t_row['parent_category_name']} → {t_row['category_name']}"
            main_category_for_edit = t_row['category_parent_id'] 
        elif t_row['category_name'] is None and t_row['category_id'] is not None: 
            full_category_name = "Error: Invalid Category Link"
        elif t_row['category_id'] is None: 
            full_category_name = "Uncategorized"
        else: 
            main_category_for_edit = t_row['category_id']
        transactions_list.append({
            'id': t_row['id'], 'amount': t_row['amount'], 
            'full_category_name': full_category_name, 'date': t_row['date'], 'type': t_row['type'],
            'category_id': t_row['category_id'], 'main_category_for_edit': main_category_for_edit
        })

    monthly_summary = db_helpers.get_monthly_financial_summary(view_year, view_month, focused_main_category_id)
    
    budget_planning_year = request.args.get('budget_year', default=current_year, type=int)
    budget_planning_month = request.args.get('budget_month', default=current_month, type=int)
    budget_goals_for_planning_ui = db_helpers.get_budget_goals_for_planning_ui(budget_planning_year, budget_planning_month)

    total_income_row = conn.execute("SELECT SUM(amount) FROM transactions WHERE type = 'income'").fetchone()
    total_income = total_income_row[0] if total_income_row and total_income_row[0] is not None else 0.0
    total_expenses_row = conn.execute("SELECT SUM(amount) FROM transactions WHERE type = 'expense'").fetchone()
    total_expenses = total_expenses_row[0] if total_expenses_row and total_expenses_row[0] is not None else 0.0
    balance = total_income - total_expenses
    
    main_categories_for_sub_add = [mc for mc in categories_for_management] # Simplified for example

    years_from_db = conn.execute("SELECT DISTINCT strftime('%Y', date) as year FROM transactions ORDER BY year DESC").fetchall()
    all_years_with_data = [row['year'] for row in years_from_db if row['year']]
    if not all_years_with_data: all_years_with_data.append(str(current_year))
    elif str(current_year) not in all_years_with_data: all_years_with_data.append(str(current_year)); all_years_with_data.sort(reverse=True)

    return render_template('index.html',
                           transactions=transactions_list,
                           categories_for_management=categories_for_management,
                           hierarchical_categories_data_for_js=hierarchical_categories_for_js_data, 
                           main_categories_for_sub_add=main_categories_for_sub_add,
                           monthly_summary_table_data=monthly_summary['summary_table_data'],
                           expected_vs_actual_chart_data=json.dumps(monthly_summary['expected_vs_actual_chart']),
                           nws_actual_chart_data=json.dumps(monthly_summary['nws_actual_chart']),
                           nws_budgeted_chart_data=json.dumps(monthly_summary['nws_budgeted_chart']),
                           current_chart_title_suffix=monthly_summary['current_chart_title_suffix'], 
                           focused_main_category_id=monthly_summary['focused_main_category_id'],       
                           focused_main_category_name=monthly_summary['focused_main_category_name'], 
                           view_year=view_year, view_month=view_month, 
                           budget_goals_for_planning_ui=budget_goals_for_planning_ui,
                           budget_planning_year=budget_planning_year,
                           budget_planning_month=budget_planning_month,
                           total_income=total_income, total_expenses=total_expenses,
                           balance=balance, current_year=current_year,
                           all_years_with_data=all_years_with_data
                           )
