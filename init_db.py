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
    Initializes the database with tables for categories (hierarchical),
    transactions, and budget goals. Adds a financial goal type to categories.
    Ensures database is created in the 'instance' folder.
    """
    # --- MODIFICATION START ---
    # Define the path to the instance folder
    instance_folder_path = os.path.join(os.path.dirname(__file__), 'instance') # Assumes init_db.py is in project root

    # Create the instance folder if it doesn't exist
    if not os.path.exists(instance_folder_path):
        os.makedirs(instance_folder_path)
        print(f"Created instance folder at: {instance_folder_path}")

    db_path = os.path.join(instance_folder_path, 'budget.db')
    print(f"Initializing database at: {db_path}")
    conn = sqlite3.connect(db_path) # Connect to the DB in the instance folder
    # --- MODIFICATION END ---
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            financial_goal_type TEXT CHECK(financial_goal_type IN ('Need', 'Want', 'Saving', NULL)), /* Added */
            FOREIGN KEY (parent_id) REFERENCES categories (id) ON DELETE RESTRICT,
            UNIQUE (name, parent_id)
        )
    ''')
    print("'categories' table checked/created.")

    # Now that we're sure the table exists, try to add the financial_goal_type column
    # if it doesn't already exist.
    try:
        cursor.execute("ALTER TABLE categories ADD COLUMN financial_goal_type TEXT CHECK(financial_goal_type IN ('Need', 'Want', 'Saving', NULL))")
        print("Added 'financial_goal_type' column to 'categories' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("'financial_goal_type' column already exists in 'categories' table.")
        else: # Re-raise other operational errors
            raise e

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category_id INTEGER, 
            date TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL
        )
    ''')

    # New table for budget goals
    # category_id: Links to the specific category (main or sub) being budgeted.
    # year, month: Defines the period for the budget.
    # budgeted_amount: The expected amount for that category in that month.
    # ON DELETE CASCADE: If a category is deleted, its budget goals are also deleted.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budget_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL, /* 1-12 */
            budgeted_amount REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            UNIQUE (category_id, year, month) 
        )
    ''')
    print("'budget_goals' table checked/created.")


    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0 and custom_categories_str: # Check count again after potential ALTER
        print("Populating categories from custom list...")
        categories_to_insert_tuples = parse_categories(custom_categories_str)
        main_categories_map = {}
        for name, parent_name in categories_to_insert_tuples:
            if parent_name is None:
                try:
                    cursor.execute("INSERT INTO categories (name, parent_id, financial_goal_type) VALUES (?, NULL, NULL)", (name,))
                    main_categories_map[name] = cursor.lastrowid
                except sqlite3.IntegrityError:
                    print(f"Main category '{name}' might already exist.")
                    cursor.execute("SELECT id FROM categories WHERE name = ? AND parent_id IS NULL", (name,))
                    existing = cursor.fetchone()
                    if existing: main_categories_map[name] = existing[0]
        for name, parent_name in categories_to_insert_tuples:
            if parent_name is not None:
                if parent_name in main_categories_map:
                    parent_id = main_categories_map[parent_name]
                    try:
                        cursor.execute("INSERT INTO categories (name, parent_id, financial_goal_type) VALUES (?, ?, NULL)", (name, parent_id))
                    except sqlite3.IntegrityError:
                        print(f"Subcategory '{name}' under '{parent_name}' might already exist.")
                else:
                    print(f"Warning: Parent '{parent_name}' for subcategory '{name}' not found. Skipping.")
        print("Categories populated.")
    else:
        # Need to re-fetch count if the first condition was false
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] > 0:
            print("Categories table already has data. Default population skipped. Ensure 'financial_goal_type' is set as needed.")
        # else: (This case is covered by the first if, or if custom_categories_str is None)
        else:
            print("No custom category list provided and categories table is empty. Minimal defaults might be needed or add via UI.")


    conn.commit()
    conn.close()
    print("Database initialization complete with budget goals and financial types.")
    print("IMPORTANT: If you had a previous 'budget.db', this script attempts to ALTER the 'categories' table.")
    print("It's always safest to backup your DB before schema changes or start fresh if issues arise.")

if __name__ == '__main__':
    user_category_list = """
Housing
    Rent/Mortgage
    Property Taxes
    Renter's/HOWN Insurance
    Electricity
    Gas
    Water
    Trash
    Internet
    Cable TV/Streaming
    House Maintenance
    Furniture
    MISC
Transportation
    Car Payment
    Car Insurance
    Gas
    Parking Fees
    Vehicle Registration
    Car Maintenance
    Car Repairs
Food
    Grocercies
    Dining out
    Work Lunches
Debt Repayment
    Student Loans
    Credit Card
    Personal Loan
    Medical Debt
Savings
    Emergency Funds
    Roth IRA
    Down Payment
    Vacation
    New Tech
    Wedding
    General Investments
    Crypto
Insurance
    HI Premuims
    Dental Premuims
    Vision Premuims
    Life Insurance
    Disability Insurance
    Identify Theft Protection
Personal Spending
    Clothing
    Shoes
    Haircuts
    Toiletries
    Streaming
    Events
    Hobbies
    Books
    Video Games
    Gym Membership
    Gym Equipment
    Gifts
    Charitable Donations
    Fun Money
Health and Wellness
    Doctor Co Pays
    Dentist Co Pays
    Prescription Meds
    OTC Meds
    Therapy
Household Supplies
    Cleaning
    Laundry Detergent
    TP/PT
    MISC
MISC
    """
    # To ensure the ALTER TABLE works correctly on subsequent runs if needed,
    # and to populate if DB is fresh.
    initialize_database(custom_categories_str=user_category_list)
    # If you want to run without populating categories if they exist:
    # initialize_database() 
