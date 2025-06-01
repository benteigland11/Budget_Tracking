import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, flash
import datetime # Import the datetime module

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_for_budget_app_v4' # Change this in a real app
DATABASE = 'budget.db'

def get_db():
    """
    Opens a new database connection if there is none yet for the
    current application context. Enforces foreign key constraints.
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # Allows accessing columns by name
        db.execute("PRAGMA foreign_keys = ON;") # Ensure foreign keys are enforced
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database again at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_all_categories_for_dropdown():
    """ 
    Fetches all categories and formats them for a single dropdown, 
    indicating hierarchy with 'Parent → Child' display names.
    """
    db = get_db()
    # Fetch categories, joining with their parent to get the parent's name.
    # Order by the main category name (or its own name if it's a main category),
    # then ensure main categories appear before their children, then by sub-category name.
    categories_data = db.execute("""
        SELECT c.id, c.name, c.parent_id, p.name as parent_name
        FROM categories c
        LEFT JOIN categories p ON c.parent_id = p.id
        ORDER BY COALESCE(p.name, c.name), CASE WHEN c.parent_id IS NULL THEN 0 ELSE 1 END, c.name
    """).fetchall()
    
    formatted_for_dropdown = []
    for cat in categories_data:
        display_name = cat['name']
        if cat['parent_name']:
            # Example: "Housing → Rent/Mortgage"
            display_name = f"{cat['parent_name']} → {cat['name']}" 
        formatted_for_dropdown.append({'id': cat['id'], 'display_name': display_name})
    return formatted_for_dropdown

def get_categories_for_management():
    """ 
    Fetches categories hierarchically for the management UI.
    Returns a list of main categories, each with a list of its sub_categories.
    """
    db = get_db()
    main_categories_data = db.execute("""
        SELECT id, name FROM categories WHERE parent_id IS NULL ORDER BY name ASC
    """).fetchall()
    
    managed_categories = []
    for mc in main_categories_data:
        sub_categories_data = db.execute("""
            SELECT id, name FROM categories WHERE parent_id = ? ORDER BY name ASC
        """, (mc['id'],)).fetchall()
        managed_categories.append({
            'id': mc['id'],
            'name': mc['name'],
            'sub_categories': sub_categories_data # List of subcategory rows
        })
    return managed_categories


@app.route('/')
def index():
    """
    Main route. Fetches all necessary data for display:
    - Categories for dropdowns and management UI.
    - Transactions with their full category path.
    - Data for the expense chart.
    - Summary statistics (income, expenses, balance).
    """
    conn = get_db()
    
    current_year = datetime.datetime.now().year # Get current year

    categories_for_dropdown = get_all_categories_for_dropdown()
    categories_for_management = get_categories_for_management()

    # Fetch transactions, joining with categories and parent categories
    transactions_data = conn.execute("""
        SELECT t.id, t.amount, t.category_id, /* Keep category_id for debugging/internal use */
               c.name as category_name, p.name as parent_category_name, 
               t.date, t.type
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories p ON c.parent_id = p.id  /* Join categories table again for parent */
        ORDER BY t.date DESC, t.id DESC
    """).fetchall()
    
    # Prepare transactions with full category path for display
    transactions_list = []
    for t_row in transactions_data:
        full_category_name = t_row['category_name']
        if t_row['parent_category_name']: # If it's a subcategory
            full_category_name = f"{t_row['parent_category_name']} → {t_row['category_name']}"
        elif t_row['category_name'] is None and t_row['category_id'] is not None:
             # This case indicates a broken link, e.g., category_id exists but no matching category.
             # Should be rare with foreign keys and proper deletion.
             full_category_name = "Error: Invalid Category Link"
        elif t_row['category_id'] is None: # Transaction is uncategorized
            full_category_name = "Uncategorized"
        # If it's a main category, full_category_name is just t_row['category_name']

        transactions_list.append({
            'id': t_row['id'],
            'amount': t_row['amount'],
            'full_category_name': full_category_name,
            'date': t_row['date'],
            'type': t_row['type']
        })

    # Chart data: groups by the full category display name.
    expense_data = conn.execute("""
        SELECT 
            COALESCE(p.name || ' → ' || c.name, c.name) as full_category_display_name, 
            SUM(t.amount) as total_amount
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        LEFT JOIN categories p ON c.parent_id = p.id
        WHERE t.type = 'expense' AND c.name IS NOT NULL /* Ensure category exists */
        GROUP BY full_category_display_name /* Group by the constructed name */
        HAVING SUM(t.amount) > 0
        ORDER BY total_amount DESC
    """).fetchall()

    chart_labels = [row['full_category_display_name'] if row['full_category_display_name'] else 'Uncategorized' for row in expense_data]
    chart_values = [row['total_amount'] for row in expense_data]
    
    # Summary statistics
    total_income_row = conn.execute("SELECT SUM(amount) FROM transactions WHERE type = 'income'").fetchone()
    total_income = total_income_row[0] if total_income_row and total_income_row[0] is not None else 0.0

    total_expenses_row = conn.execute("SELECT SUM(amount) FROM transactions WHERE type = 'expense'").fetchone()
    total_expenses = total_expenses_row[0] if total_expenses_row and total_expenses_row[0] is not None else 0.0
    
    balance = total_income - total_expenses

    # For the "Add Subcategory" form, we need a list of main categories.
    main_categories_for_sub_add = [mc for mc in categories_for_management]


    return render_template('index.html',
                           transactions=transactions_list, # Use the processed list
                           categories_for_dropdown=categories_for_dropdown,
                           categories_for_management=categories_for_management,
                           main_categories_for_sub_add=main_categories_for_sub_add,
                           chart_labels=chart_labels,
                           chart_values=chart_values,
                           total_income=total_income,
                           total_expenses=total_expenses,
                           balance=balance,
                           current_year=current_year) # Pass current_year to the template

@app.route('/transactions/add', methods=['POST'])
def add_transaction():
    """ Handles adding a new transaction. """
    if request.method == 'POST':
        try:
            amount_str = request.form['amount']
            category_id_str = request.form.get('category_id') # This ID can be for a main or subcategory
            date = request.form['date']
            transaction_type = request.form['type']

            # Validation
            if not amount_str: flash('Amount is required.', 'error')
            elif not category_id_str: flash('Category is required.', 'error')
            elif not date: flash('Date is required.', 'error')
            elif transaction_type not in ['income', 'expense']: flash('Invalid transaction type.', 'error')
            else:
                amount = float(amount_str)
                category_id = int(category_id_str) # Ensure it's an integer
                if amount <= 0:
                    flash('Amount must be a positive number.', 'error')
                else:
                    # All checks passed, insert into database
                    conn = get_db()
                    conn.execute("INSERT INTO transactions (amount, category_id, date, type) VALUES (?, ?, ?, ?)",
                                   (amount, category_id, date, transaction_type))
                    conn.commit()
                    flash('Transaction added successfully!', 'success')
                    return redirect(url_for('index')) # Redirect after successful post
        except ValueError: # Catches float() or int() conversion errors
            flash('Invalid amount or category ID. Please check your input.', 'error')
        except sqlite3.IntegrityError: # E.g., foreign key constraint fails if category_id is invalid
            flash('Database integrity error. Does the selected category exist?', 'error')
        except Exception as e:
            flash(f'An unexpected error occurred: {e}', 'error')
            print(f"Error in /transactions/add: {e}") # Log to console for debugging
    return redirect(url_for('index')) # Redirect if not POST or if error occurred before successful redirect


@app.route('/categories/add_main', methods=['POST'])
def add_main_category():
    """ Handles adding a new main category. """
    category_name = request.form.get('main_category_name', '').strip()
    if not category_name:
        flash('Main category name cannot be empty.', 'error')
    else:
        conn = get_db()
        try:
            # parent_id is NULL for main categories
            conn.execute("INSERT INTO categories (name, parent_id) VALUES (?, NULL)", (category_name,))
            conn.commit()
            flash(f"Main category '{category_name}' added successfully!", 'success')
        except sqlite3.IntegrityError: # Handles UNIQUE (name, parent_id) constraint
            flash(f"Main category '{category_name}' already exists or is invalid.", 'error')
        except Exception as e:
            flash(f"An error occurred while adding main category: {e}", 'error')
            print(f"Error in /categories/add_main: {e}")
    return redirect(url_for('index'))

@app.route('/categories/add_sub', methods=['POST'])
def add_sub_category():
    """ Handles adding a new subcategory under a selected main category. """
    subcategory_name = request.form.get('sub_category_name', '').strip()
    parent_id_str = request.form.get('parent_category_id')

    if not subcategory_name: flash('Subcategory name cannot be empty.', 'error')
    elif not parent_id_str: flash('Parent category must be selected for subcategory.', 'error')
    else:
        conn = get_db()
        try:
            parent_id = int(parent_id_str)
            # Optional: Verify parent_id actually refers to a main category (parent_id IS NULL)
            # For simplicity, we rely on the form providing valid main category IDs.
            # The UNIQUE(name, parent_id) constraint will prevent duplicates under the same parent.
            conn.execute("INSERT INTO categories (name, parent_id) VALUES (?, ?)", (subcategory_name, parent_id))
            conn.commit()
            flash(f"Subcategory '{subcategory_name}' added successfully!", 'success')
        except ValueError:
            flash('Invalid parent category ID format.', 'error')
        except sqlite3.IntegrityError:
            flash(f"Subcategory '{subcategory_name}' already exists under this parent, or parent category is invalid.", 'error')
        except Exception as e:
            flash(f"An error occurred while adding subcategory: {e}", 'error')
            print(f"Error in /categories/add_sub: {e}")
    return redirect(url_for('index'))

@app.route('/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    """ Handles deleting a category (main or sub). """
    conn = get_db()
    # Fetch category details to check if it's main and its name for flash messages
    category_to_delete = conn.execute("SELECT name, parent_id FROM categories WHERE id = ?", (category_id,)).fetchone()

    if not category_to_delete:
        flash("Category not found.", "error")
        return redirect(url_for('index'))

    category_name = category_to_delete['name']
    is_main_category_with_no_parent = category_to_delete['parent_id'] is None

    try:
        if is_main_category_with_no_parent:
            # Check if this main category has any subcategories
            # The ON DELETE RESTRICT on categories.parent_id should prevent this at DB level too.
            subcategories = conn.execute("SELECT 1 FROM categories WHERE parent_id = ? LIMIT 1", (category_id,)).fetchone()
            if subcategories:
                flash(f"Cannot delete main category '{category_name}'. It still has subcategories. Please delete its subcategories first.", 'error')
                return redirect(url_for('index'))
        
        # If it's a subcategory, or a main category with no subcategories, proceed with deletion.
        # Transactions linked to this category_id will have their category_id set to NULL
        # due to ON DELETE SET NULL in the transactions table schema.
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        flash(f"Category '{category_name}' deleted. Any associated transactions are now uncategorized.", 'info')

    except sqlite3.IntegrityError as e:
        # This might be redundant if the subcategory check is robust, but good for safety.
        # This would typically be triggered by the ON DELETE RESTRICT if we tried to delete a parent with children.
        flash(f"Could not delete category '{category_name}'. It might have subcategories or other dependencies. DB Error: {e}", 'error')
        print(f"IntegrityError on delete category {category_id}: {e}")
    except Exception as e:
        flash(f"An unexpected error occurred while deleting category: {e}", 'error')
        print(f"Error in /categories/delete/{category_id}: {e}")
        
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
