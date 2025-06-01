import sqlite3

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
            # This is a main category
            current_main_category = stripped_line
            main_category_indent = indentation
            parsed.append((stripped_line, None))
        else:
            # This is a subcategory
            if current_main_category:
                parsed.append((stripped_line, current_main_category))
            else:
                # Should not happen if list is well-formed, treat as main if no current parent
                print(f"Warning: Subcategory '{stripped_line}' found without a parent, treating as main.")
                parsed.append((stripped_line, None))
                current_main_category = stripped_line # It becomes the new context
                main_category_indent = indentation


    return parsed

def initialize_database(custom_categories_str=None):
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # Create categories table with parent_id for hierarchy
    # parent_id: FK to itself. NULL for main categories.
    # ON DELETE RESTRICT: Prevents deleting a parent category if subcategories exist.
    # UNIQUE(name, parent_id): Ensures category names are unique under the same parent (or globally for main categories)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            FOREIGN KEY (parent_id) REFERENCES categories (id) ON DELETE RESTRICT,
            UNIQUE (name, parent_id)
        )
    ''')

    # Transactions table links to categories
    # ON DELETE SET NULL: If a category is deleted, transactions under it become 'uncategorized'.
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

    # Populate categories if the table is empty
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        print("Populating categories...")
        if custom_categories_str is None:
            # Fallback to a minimal default if no custom list is provided during init
            # This part is just a fallback, usually custom_categories_str will be provided.
            default_categories_structure = [
                ("Income", None),
                ("Salary", "Income"),
                ("Housing", None),
                ("Rent/Mortgage", "Housing"),
                ("Utilities", "Housing"),
                ("Groceries", None),
                ("Transportation", None),
                ("Miscellaneous", None)
            ]
            categories_to_insert_tuples = default_categories_structure # Use this as is for this small example
        else:
            categories_to_insert_tuples = parse_categories(custom_categories_str)

        # Insert main categories first
        main_categories_map = {} # To store name -> id for main categories
        for name, parent_name in categories_to_insert_tuples:
            if parent_name is None:
                try:
                    cursor.execute("INSERT INTO categories (name, parent_id) VALUES (?, NULL)", (name,))
                    main_categories_map[name] = cursor.lastrowid
                except sqlite3.IntegrityError:
                    print(f"Main category '{name}' might already exist or name conflict.")
                    # If it already exists, try to fetch its ID for subcategories
                    cursor.execute("SELECT id FROM categories WHERE name = ? AND parent_id IS NULL", (name,))
                    existing = cursor.fetchone()
                    if existing:
                        main_categories_map[name] = existing[0]


        # Insert subcategories
        for name, parent_name in categories_to_insert_tuples:
            if parent_name is not None:
                if parent_name in main_categories_map:
                    parent_id = main_categories_map[parent_name]
                    try:
                        cursor.execute("INSERT INTO categories (name, parent_id) VALUES (?, ?)", (name, parent_id))
                    except sqlite3.IntegrityError:
                        print(f"Subcategory '{name}' under '{parent_name}' might already exist or name conflict.")
                else:
                    print(f"Warning: Parent category '{parent_name}' for subcategory '{name}' not found or not inserted. Skipping.")
        
        print("Categories populated.")
    else:
        print("Categories table already has data. Skipping population.")

    conn.commit()
    conn.close()
    print("Database initialized with hierarchical categories structure.")
    print("IMPORTANT: If you had a previous 'budget.db', it should have been deleted or renamed before running this.")

if __name__ == '__main__':
    # User's provided category list
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
General MISC
MISC
    """
    initialize_database(custom_categories_str=user_category_list)
