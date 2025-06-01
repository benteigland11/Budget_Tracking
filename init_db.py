import sqlite3

def initialize_database():
    """
    Connects to the SQLite database (budget.db) and creates the
    'transactions' table if it doesn't already exist.
    The table stores transaction details: id, amount, category, date, and type.
    """
    # Connect to SQLite database (this will create the file if it doesn't exist)
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()

    # Create transactions table if it doesn't exist
    # Using REAL for amount as it's more standard for SQLite than FLOAT.
    # Added a CHECK constraint to ensure 'type' is either 'income' or 'expense'.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense'))
        )
    ''')

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    print("Database initialized and 'transactions' table created (if it didn't exist).")

if __name__ == '__main__':
    # This ensures the function runs only when the script is executed directly
    initialize_database()
