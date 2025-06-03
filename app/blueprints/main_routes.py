# app/blueprints/main_routes.py
# Blueprint for main application routes like the dashboard.

from flask import Blueprint, render_template, request, g, current_app
from app.database import get_db 
from app.utils import db_helpers # Ensure db_helpers is imported
import datetime
import json

bp = Blueprint('main', __name__)

def get_dynamic_year_options(conn, current_year_int):
    """Generates a list of years for dropdowns. Ensures current_year_int is an int."""
    transaction_years_cursor = conn.execute("SELECT DISTINCT strftime('%Y', date) as year FROM transactions WHERE year IS NOT NULL ORDER BY year DESC")
    transaction_years = {row['year'] for row in transaction_years_cursor.fetchall() if row['year'] and row['year'].strip().isdigit()}

    budget_years_cursor = conn.execute("SELECT DISTINCT year FROM budget_goals ORDER BY year DESC")
    budget_years = {str(row['year']) for row in budget_years_cursor.fetchall() if row['year'] is not None} 
    
    all_years_str = transaction_years.union(budget_years)
    all_years_str.add(str(current_year_int))
    all_years_str.add(str(current_year_int - 1)) 
    all_years_str.add(str(current_year_int + 1)) 
    all_years_str.add(str(current_year_int + 2)) 

    valid_years_int = []
    for y_str in all_years_str:
        if y_str and y_str.strip().isdigit(): 
            try:
                valid_years_int.append(int(y_str))
            except ValueError:
                current_app.logger.warning(f"Could not convert year string '{y_str}' to int for sorting in get_dynamic_year_options.")
    
    sorted_years_str = sorted(list(set(valid_years_int)), reverse=True)
    
    if not sorted_years_str: 
        return [str(current_year_int)]
        
    return [str(y) for y in sorted_years_str] 


@bp.route('/')
def index():
    conn = get_db()
    current_time = datetime.datetime.now()
    current_year_int = current_time.year 
    current_month_int = current_time.month 

    current_app.logger.info(f"--- main.index route called ---")
    # ... (existing analytics period and budget planning period logic remains the same) ...
    analytics_period_type = request.args.get('period_type', default='monthly') 
    try:
        analytics_view_year = int(request.args.get('year')) if request.args.get('year') and request.args.get('year').isdigit() else current_year_int
    except (ValueError, TypeError): 
        analytics_view_year = current_year_int
    
    analytics_view_month_str = request.args.get('month') 
    if analytics_period_type == 'yearly':
        analytics_view_month = None 
    elif analytics_view_month_str and analytics_view_month_str.isdigit():
        analytics_view_month = int(analytics_view_month_str)
        if not (1 <= analytics_view_month <= 12): 
            analytics_view_month = current_month_int 
    else: 
        analytics_view_month = current_month_int if analytics_period_type == 'monthly' else None
    
    modal_budget_year_from_args = request.args.get('budget_year')
    modal_budget_month_from_args = request.args.get('budget_month')
    
    if modal_budget_year_from_args and modal_budget_year_from_args.isdigit():
        year_for_budget_modal_data = int(modal_budget_year_from_args)
    else:
        year_for_budget_modal_data = current_year_int
    
    if modal_budget_month_from_args and modal_budget_month_from_args.isdigit():
        month_for_budget_modal_data = int(modal_budget_month_from_args)
        if not (1 <= month_for_budget_modal_data <= 12): 
             month_for_budget_modal_data = current_month_int
    else:
        month_for_budget_modal_data = current_month_int
        
    budget_goals_for_planning_ui = db_helpers.get_budget_goals_for_planning_ui(
        year_for_budget_modal_data, 
        month_for_budget_modal_data
    )
    
    categories_for_management = db_helpers.get_categories_for_management()
    hierarchical_categories_for_js_data = db_helpers.get_hierarchical_categories_for_js()
    
    transactions_data = conn.execute("""
        SELECT t.id, t.amount, t.category_id, c.name as category_name, 
               c.parent_id as category_parent_id, p.name as parent_category_name, 
               t.date, t.type, t.description
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
            'description': t_row['description'], 
            'category_id': t_row['category_id'], 
            'main_category_for_edit': main_category_for_edit
        })

    financial_summary = db_helpers.get_financial_summary(
        year=analytics_view_year, 
        month=analytics_view_month, 
        period_type=analytics_period_type,
        focused_main_category_id=request.args.get('main_cat_focus', type=int) 
    )
    
    total_income_row = conn.execute("SELECT SUM(amount) FROM transactions WHERE type = 'income'").fetchone()
    total_income = total_income_row[0] if total_income_row and total_income_row[0] is not None else 0.0
    total_expenses_row = conn.execute("SELECT SUM(amount) FROM transactions WHERE type = 'expense'").fetchone()
    total_expenses = total_expenses_row[0] if total_expenses_row and total_expenses_row[0] is not None else 0.0
    balance = total_income - total_expenses
    
    main_categories_for_sub_add = categories_for_management if categories_for_management else []
    
    all_years_for_dropdowns = get_dynamic_year_options(conn, current_year_int) 

    # ADDED: Fetch initial goals data for the dashboard scroller
    initial_goals = db_helpers.get_all_goals()

    return render_template('index.html',
                           transactions=transactions_list,
                           categories_for_management=categories_for_management,
                           hierarchical_categories_data_for_js=hierarchical_categories_for_js_data, 
                           main_categories_for_sub_add=main_categories_for_sub_add,
                           
                           monthly_summary_table_data=financial_summary['summary_table_data'],
                           expected_vs_actual_chart_data=json.dumps(financial_summary['expected_vs_actual_chart']),
                           nws_actual_chart_data=json.dumps(financial_summary['nws_actual_chart']),
                           nws_budgeted_chart_data=json.dumps(financial_summary['nws_budgeted_chart']),
                           current_chart_title_suffix=financial_summary['current_chart_title_suffix'], 
                           focused_main_category_id=financial_summary['focused_main_category_id'],       
                           focused_main_category_name=financial_summary['focused_main_category_name'], 
                           
                           period_total_expenses=financial_summary.get('period_total_expenses', 0.0),
                           period_total_income=financial_summary.get('period_total_income', 0.0),
                           period_total_budgeted=financial_summary.get('period_total_budgeted', 0.0),
                           
                           view_period_type=analytics_period_type, 
                           view_year=analytics_view_year, 
                           view_month=analytics_view_month, 
                           
                           budget_planning_year=year_for_budget_modal_data, 
                           budget_planning_month=month_for_budget_modal_data, 
                           budget_goals_for_planning_ui=budget_goals_for_planning_ui, 
                           
                           total_income=total_income, 
                           total_expenses=total_expenses, 
                           balance=balance, 
                           
                           current_year=current_year_int, 
                           current_month=current_month_int,

                           all_years_for_dropdowns=all_years_for_dropdowns,
                           initial_goals_data=initial_goals # ADDED: Pass goals data to index.html
                           )
