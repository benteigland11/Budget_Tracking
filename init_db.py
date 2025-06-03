import sqlite3
import os

def parse_categories(category_list_str):
    """
    Parses a multi-line string with indentation to represent hierarchy.
    Returns a list of tuples: (name, parent_name_or_None)
    """
    parsed = []
    lines = category_list_str.strip().split('\n')
    current_main_category = None
    main_category_indent = -1

    for line in lines:
        stripped_line = line.lstrip()
        if not stripped_line:
            continue
        
        indentation = len(line) - len(stripped_line)

        if main_category_indent == -1 or indentation <= main_category_indent:
            current_main_category = stripped_line
            main_category_indent = indentation
            parsed.append((stripped_line, None))
        else:
            if current_main_category:
                parsed.append((stripped_line, current_main_category))
            else:
                print(f"Warning: Subcategory '{stripped_line}' found without a parent, treating as main.")
                parsed.append((stripped_line, None))
                current_main_category = stripped_line 
                main_category_indent = indentation
    return parsed

def initialize_database(custom_categories_str=None):
    """
    Initializes the database with tables for categories, transactions, 
    budget goals, paychecks, and paycheck deductions.
    Ensures database is created in the 'instance' folder.
    """
    instance_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')

    if not os.path.exists(instance_folder_path):
        os.makedirs(instance_folder_path)
        print(f"Created instance folder at: {instance_folder_path}")

    db_path = os.path.join(instance_folder_path, 'budget.db')
    print(f"Initializing database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # Categories Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            financial_goal_type TEXT CHECK(financial_goal_type IN ('Need', 'Want', 'Saving', NULL)),
            FOREIGN KEY (parent_id) REFERENCES categories (id) ON DELETE RESTRICT,
            UNIQUE (name, parent_id)
        )
    ''')
    print("'categories' table checked/created.")
    try:
        cursor.execute("ALTER TABLE categories ADD COLUMN financial_goal_type TEXT CHECK(financial_goal_type IN ('Need', 'Want', 'Saving', NULL))")
        print("Attempted to add 'financial_goal_type' column to 'categories' table.")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("'financial_goal_type' column already exists in 'categories' table.")
        else:
            print(f"Could not add 'financial_goal_type' (may already exist or other issue): {e}")

    # Transactions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category_id INTEGER, 
            date TEXT NOT NULL, 
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            description TEXT, 
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL
        )
    ''')
    print("'transactions' table checked/created.")
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN description TEXT")
        print("Attempted to add 'description' column to 'transactions' table.")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("'description' column already exists in 'transactions' table.")
        else:
             print(f"Could not add 'description' column (may already exist or other issue): {e}")

    # Budget Goals Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budget_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL, 
            budgeted_amount REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE, 
            UNIQUE (category_id, year, month) 
        )
    ''')
    print("'budget_goals' table checked/created.")

    # --- MODIFICATION: New Tables for Paycheck Data ---
    # Paychecks Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paychecks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pay_date TEXT NOT NULL,      -- YYYY-MM-DD
            employer_name TEXT,
            gross_pay REAL NOT NULL,
            net_pay_transaction_id INTEGER, -- FK to the 'income' transaction in transactions table
            notes TEXT,
            FOREIGN KEY (net_pay_transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
        )
    ''')
    print("'paychecks' table checked/created.")

    # Paycheck Deductions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paycheck_deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paycheck_id INTEGER NOT NULL,
            description TEXT NOT NULL,     -- e.g., "Federal Income Tax", "401k Contribution", "Health Insurance Premium"
            amount REAL NOT NULL,
            type TEXT NOT NULL,            -- e.g., 'TAX', 'PRETAX_RETIREMENT', 'PRETAX_HEALTH', 'POSTTAX_EXPENSE'
            FOREIGN KEY (paycheck_id) REFERENCES paychecks(id) ON DELETE CASCADE
        )
    ''')
    print("'paycheck_deductions' table checked/created.")
    # --- End New Tables ---


    # Populate categories if a custom list is provided and the table is empty
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0 and custom_categories_str:
        # ... (category population logic remains the same as init_db_py_v2) ...
        print("Populating categories from custom list...")
        categories_to_insert_tuples = parse_categories(custom_categories_str)
        main_categories_map = {} 
        for name, parent_name in categories_to_insert_tuples:
            if parent_name is None: 
                try:
                    cursor.execute("INSERT INTO categories (name, parent_id, financial_goal_type) VALUES (?, NULL, NULL)", (name,))
                    main_categories_map[name] = cursor.lastrowid
                except sqlite3.IntegrityError:
                    print(f"Main category '{name}' might already exist. Fetching its ID.")
                    existing_main_cat = cursor.execute("SELECT id FROM categories WHERE name = ? AND parent_id IS NULL", (name,)).fetchone()
                    if existing_main_cat:
                        main_categories_map[name] = existing_main_cat[0]
                    else:
                        print(f"Could not confirm or add main category '{name}'. Subcategories might be affected.")
        for name, parent_name in categories_to_insert_tuples:
            if parent_name is not None: 
                if parent_name in main_categories_map:
                    parent_id = main_categories_map[parent_name]
                    try:
                        cursor.execute("INSERT INTO categories (name, parent_id, financial_goal_type) VALUES (?, ?, NULL)", (name, parent_id))
                    except sqlite3.IntegrityError:
                        print(f"Subcategory '{name}' under '{parent_name}' might already exist.")
                else:
                    print(f"Warning: Parent '{parent_name}' for subcategory '{name}' not found or not added. Skipping subcategory.")
        print("Categories populated.")
    elif custom_categories_str: 
        print("Categories table already has data. Custom population skipped.")
    else: 
        print("No custom category list provided and categories table is empty. Add categories via UI.")

    conn.commit()
    conn.close()
    print("Database initialization complete (with paycheck tables).")

if __name__ == '__main__':
    user_category_list = """
Housing
    Rent/Mortgage
    Property Taxes
Food
    Grocercies
    Dining out
Transportation
    Gas
    Car Insurance
Savings
    Emergency Fund
    401k
    HSA
    """ # Example shorter list
    initialize_database(custom_categories_str=user_category_list)
