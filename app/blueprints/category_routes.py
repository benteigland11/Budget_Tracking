# app/blueprints/category_routes.py
# Blueprint for category management actions.

from flask import Blueprint, request, redirect, url_for, flash
from app.database import get_db # Use get_db from the database module
import sqlite3

bp = Blueprint('categories', __name__) # url_prefix='/categories'

@bp.route('/add_main', methods=['POST'])
def add_main_category():
    category_name = request.form.get('main_category_name', '').strip()
    if not category_name: flash('Main category name cannot be empty.', 'error')
    else:
        conn = get_db()
        try:
            conn.execute("INSERT INTO categories (name, parent_id, financial_goal_type) VALUES (?, NULL, NULL)", (category_name,))
            conn.commit()
            flash(f"Main category '{category_name}' added!", 'success')
        except sqlite3.IntegrityError: flash(f"Main category '{category_name}' already exists.", 'error')
        except Exception as e: flash(f"Error: {e}", 'error'); print(f"Error add_main_category: {e}")
    return redirect(url_for('main.index')) # Redirect to main dashboard

@bp.route('/add_sub', methods=['POST'])
def add_sub_category():
    subcategory_name = request.form.get('sub_category_name', '').strip()
    parent_id_str = request.form.get('parent_category_id')
    if not subcategory_name: flash('Subcategory name cannot be empty.', 'error')
    elif not parent_id_str: flash('Parent category must be selected.', 'error')
    else:
        conn = get_db()
        try:
            parent_id = int(parent_id_str)
            conn.execute("INSERT INTO categories (name, parent_id, financial_goal_type) VALUES (?, ?, NULL)", (subcategory_name, parent_id))
            conn.commit()
            flash(f"Subcategory '{subcategory_name}' added!", 'success')
        except ValueError: flash('Invalid parent ID.', 'error')
        except sqlite3.IntegrityError: flash(f"Subcategory '{subcategory_name}' already exists under this parent.", 'error')
        except Exception as e: flash(f"Error: {e}", 'error'); print(f"Error add_sub_category: {e}")
    return redirect(url_for('main.index'))

@bp.route('/update_financial_types_batch', methods=['POST'])
def update_category_financial_types_batch():
    conn = get_db()
    updated_count = 0
    try:
        for key, new_type_value in request.form.items():
            if key.startswith('financial_goal_type_'): # Name convention from HTML form
                category_id_str = key.replace('financial_goal_type_', '')
                if category_id_str.isdigit():
                    category_id = int(category_id_str)
                    if new_type_value not in ['Need', 'Want', 'Saving', '']:
                        flash(f'Invalid financial goal type "{new_type_value}" for category ID {category_id}. Skipped.', 'warning')
                        continue
                    db_value = new_type_value if new_type_value else None
                    conn.execute("UPDATE categories SET financial_goal_type = ? WHERE id = ?", (db_value, category_id))
                    updated_count += 1
        conn.commit()
        if updated_count > 0: flash(f'{updated_count} category financial type(s) updated successfully!', 'success')
        else: flash('No category financial types were updated.', 'info')
    except Exception as e:
        flash(f'Error updating category financial types: {e}', 'error')
        print(f"Error update_category_financial_types_batch: {e}")
    return redirect(url_for('main.index'))

@bp.route('/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    conn = get_db()
    category_to_delete = conn.execute("SELECT name, parent_id FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not category_to_delete: flash("Category not found.", "error"); return redirect(url_for('main.index'))
    category_name = category_to_delete['name']
    is_main_category_with_no_parent = category_to_delete['parent_id'] is None
    try:
        if is_main_category_with_no_parent:
            subcategories = conn.execute("SELECT 1 FROM categories WHERE parent_id = ? LIMIT 1", (category_id,)).fetchone()
            if subcategories: flash(f"Cannot delete '{category_name}'. Delete subcategories first.", 'error'); return redirect(url_for('main.index'))
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        flash(f"Category '{category_name}' deleted.", 'info')
    except sqlite3.IntegrityError as e: flash(f"Could not delete '{category_name}'. Dependencies exist? DB Error: {e}", 'error'); print(f"IntegrityError delete_category: {e}")
    except Exception as e: flash(f"Error: {e}", 'error'); print(f"Error delete_category: {e}")
    return redirect(url_for('main.index'))
