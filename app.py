import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, flash

app = Flask(__name__)
app.secret_key = 'your_very_secret_key' # Important for flash messages
DATABASE = 'budget.db'

def get_db():
    """
    Opens a new database connection if there is none yet for the
    current application context.
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Allows accessing columns by name (e.g., row['amount'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database again at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    """
    Main route. Fetches all transactions and expense summary data
    to display on the index.html page.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Fetch all transactions, ordered by date descending
    cursor.execute("SELECT id, amount, category, date, type FROM transactions ORDER BY date DESC, id DESC")
    transactions = cursor.fetchall()

    # Fetch chart data: sum of expenses grouped by category
    cursor.execute("""
        SELECT category, SUM(amount) as total_amount
        FROM transactions
        WHERE type = 'expense'
        GROUP BY category
        HAVING SUM(amount) > 0 -- Only include categories with expenses
        ORDER BY total_amount DESC
    """)
    expense_data = cursor.fetchall()

    chart_labels = [row['category'] for row in expense_data]
    chart_values = [row['total_amount'] for row in expense_data]

    # Calculate total income, total expenses, and balance
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'income'")
    total_income_row = cursor.fetchone()
    total_income = total_income_row[0] if total_income_row and total_income_row[0] is not None else 0.0

    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'expense'")
    total_expenses_row = cursor.fetchone()
    total_expenses = total_expenses_row[0] if total_expenses_row and total_expenses_row[0] is not None else 0.0
    
    balance = total_income - total_expenses

    return render_template('index.html',
                           transactions=transactions,
                           chart_labels=chart_labels,
                           chart_values=chart_values,
                           total_income=total_income,
                           total_expenses=total_expenses,
                           balance=balance)

@app.route('/add', methods=['POST'])
def add_transaction():
    """
    Handles the form submission for adding a new transaction.
    Validates input and inserts data into the database.
    """
    if request.method == 'POST':
        try:
            amount_str = request.form['amount']
            category = request.form['category'].strip() # Remove leading/trailing whitespace
            date = request.form['date']
            transaction_type = request.form['type']

            # Basic validation
            if not amount_str:
                flash('Amount is required.', 'error')
                return redirect(url_for('index'))
            
            amount = float(amount_str) # Convert to float

            if amount <= 0:
                flash('Amount must be a positive number.', 'error')
                return redirect(url_for('index'))
            if not category:
                flash('Category is required.', 'error')
                return redirect(url_for('index'))
            if not date:
                flash('Date is required.', 'error')
                return redirect(url_for('index'))
            if transaction_type not in ['income', 'expense']:
                flash('Invalid transaction type.', 'error')
                return redirect(url_for('index'))

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transactions (amount, category, date, type) VALUES (?, ?, ?, ?)",
                           (amount, category, date, transaction_type))
            conn.commit()
            flash('Transaction added successfully!', 'success')

        except ValueError:
            flash('Invalid amount entered. Please enter a number.', 'error')
        except sqlite3.Error as e:
            flash(f'Database error: {e}', 'error')
        except Exception as e:
            flash(f'An unexpected error occurred: {e}', 'error')
            # For debugging, you might want to print the error to the console
            print(f"Error in /add: {e}")

        return redirect(url_for('index')) # Redirect back to the main page

if __name__ == '__main__':
    # debug=True enables the Flask debugger and auto-reloads on code changes.
    # Use host='0.0.0.0' to make it accessible from other devices on your network.
    app.run(debug=True, host='0.0.0.0', port=5000)
