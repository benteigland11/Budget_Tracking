# app/blueprints/category_routes.py
from flask import Blueprint, request, redirect, url_for, flash, jsonify, current_app
from app.database import get_db
import sqlite3

bp = Blueprint('categories', __name__)

@bp.route('/save_all_category_changes', methods=['POST'])
def save_all_category_changes():
    data = request.get_json()
    if not data:
        current_app.logger.error("Save_all_category_changes: No data received in request.")
        return jsonify({'status': 'error', 'message': 'Invalid request. No data received.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    
    financial_type_updates = data.get('financial_type_updates', [])
    new_main_categories_data = data.get('new_main_categories', [])
    new_sub_categories_data = data.get('new_sub_categories', [])
    deletions_ids = data.get('deletions', []) 

    current_app.logger.info(f"Save_all_category_changes invoked. Deletions requested: {deletions_ids}, New Mains: {len(new_main_categories_data)}, New Subs: {len(new_sub_categories_data)}, FT Updates: {len(financial_type_updates)}")

    temp_main_id_to_db_id = {}
    processed_messages = [] 
    deletion_errors = [] 

    try:
        # --- Stage 0: Pre-deletion checks for categories marked for deletion ---
        valid_deletions = [] 
        
        if deletions_ids:
            current_app.logger.info(f"Starting pre-deletion checks for IDs: {deletions_ids}")
            placeholders = ','.join('?' for _ in deletions_ids)
            if not placeholders: 
                current_app.logger.warning("Placeholders for deletion query are empty, though deletions_ids is not.")
            else:
                categories_to_delete_details = cursor.execute(
                    f"SELECT id, name, parent_id FROM categories WHERE id IN ({placeholders})", 
                    deletions_ids
                ).fetchall()
                
                categories_to_delete_map = {row['id']: row for row in categories_to_delete_details}
                current_app.logger.info(f"Fetched details for deletion candidates: {categories_to_delete_map}")

                main_cats_to_delete_ids = [cid for cid in deletions_ids if categories_to_delete_map.get(cid) and categories_to_delete_map[cid]['parent_id'] is None]
                sub_cats_to_delete_ids = [cid for cid in deletions_ids if categories_to_delete_map.get(cid) and categories_to_delete_map[cid]['parent_id'] is not None]
                current_app.logger.info(f"Main cats marked for del: {main_cats_to_delete_ids}, Sub cats marked for del: {sub_cats_to_delete_ids}")

                # Check all categories (subs and mains)
                for cat_id in deletions_ids: # Iterate original list to check all marked items
                    cat_info = categories_to_delete_map.get(cat_id)
                    if not cat_info:
                        current_app.logger.warning(f"Category ID {cat_id} marked for deletion not found in DB query results during pre-check.")
                        deletion_errors.append(f"Category ID {cat_id} marked for deletion was not found in the database.")
                        continue
                    
                    cat_name = cat_info['name']
                    is_main_category = cat_info['parent_id'] is None
                    current_app.logger.info(f"Pre-checking {'main' if is_main_category else 'sub'}category for deletion: '{cat_name}' (ID: {cat_id})")

                    # Check for linked transactions
                    if cursor.execute("SELECT 1 FROM transactions WHERE category_id = ? LIMIT 1", (cat_id,)).fetchone():
                        err_msg = f"Category '{cat_name}' (ID: {cat_id}) has linked transactions and cannot be deleted yet."
                        current_app.logger.warning(err_msg)
                        deletion_errors.append(err_msg)
                        continue # Move to next category in deletions_ids

                    # MODIFICATION: Refined budget goal check
                    # Check if there are any *non-zero* budget goals
                    budget_goal_check_cursor = cursor.execute(
                        "SELECT 1 FROM budget_goals WHERE category_id = ? AND budgeted_amount != 0 LIMIT 1", (cat_id,)
                    )
                    if budget_goal_check_cursor.fetchone():
                        err_msg = f"Category '{cat_name}' (ID: {cat_id}) has non-zero budget goals and cannot be deleted yet."
                        current_app.logger.warning(err_msg)
                        deletion_errors.append(err_msg)
                        continue # Move to next category in deletions_ids

                    if is_main_category:
                        sub_check_cursor = cursor.execute("SELECT id, name FROM categories WHERE parent_id = ?", (cat_id,))
                        remaining_subs_details = []
                        has_remaining_subs = False
                        for sub_row in sub_check_cursor.fetchall():
                            if sub_row['id'] not in deletions_ids: 
                                has_remaining_subs = True
                                remaining_subs_details.append(f"'{sub_row['name']}' (ID: {sub_row['id']})")
                        if has_remaining_subs:
                            err_msg = f"Main category '{cat_name}' (ID: {cat_id}) still has subcategories not marked for deletion: {', '.join(remaining_subs_details)}. Delete or mark subcategories for deletion first."
                            current_app.logger.warning(err_msg)
                            deletion_errors.append(err_msg)
                            continue # Move to next category in deletions_ids
                    
                    # If all checks passed for this cat_id
                    valid_deletions.append(cat_id)
                    current_app.logger.info(f"Category '{cat_name}' (ID: {cat_id}) PASSED all pre-deletion checks.")
        
        if deletion_errors: # If any category failed its checks
            current_app.logger.error(f"Pre-deletion checks failed for one or more categories. Errors: {deletion_errors}")
            # We join all errors found, so the user knows everything that's blocking.
            return jsonify({'status': 'error', 'message': "Deletion pre-checks failed: " + " | ".join(deletion_errors)}), 400

        # --- Start Transaction (if desired for all operations to be atomic) ---
        # conn.execute("BEGIN") # Example: Start transaction

        # --- Stage 1: Add New Main Categories ---
        for main_cat_item in new_main_categories_data:
            name = main_cat_item.get('name','').strip()
            temp_id = main_cat_item.get('temp_id') 
            if not name:
                processed_messages.append({'type': 'warning', 'text': f"A new main category with an empty name was ignored."})
                continue
            try:
                cursor.execute("INSERT INTO categories (name, parent_id, financial_goal_type) VALUES (?, NULL, NULL)", (name,))
                db_id = cursor.lastrowid
                if temp_id: 
                    temp_main_id_to_db_id[temp_id] = db_id
                processed_messages.append({'type': 'info', 'text': f"Added main category: {name}"})
            except sqlite3.IntegrityError:
                existing_main = cursor.execute("SELECT id FROM categories WHERE name = ? AND parent_id IS NULL", (name,)).fetchone()
                if existing_main and temp_id:
                    temp_main_id_to_db_id[temp_id] = existing_main['id']
                processed_messages.append({'type': 'warning', 'text': f"Main category '{name}' already exists or could not be added."})

        # --- Stage 2: Add New Subcategories ---
        for sub_cat_item in new_sub_categories_data:
            # ... (rest of add sub logic from previous version, no changes here) ...
            name = sub_cat_item.get('name','').strip()
            parent_id_or_temp_id = sub_cat_item.get('parent_id_or_temp_id')
            financial_goal_type = sub_cat_item.get('financial_goal_type')
            db_financial_goal_type = financial_goal_type if financial_goal_type in ['Need', 'Want', 'Saving'] else None
            if not name: 
                processed_messages.append({'type': 'warning', 'text': f"A new subcategory with an empty name was ignored."})
                continue
            if not parent_id_or_temp_id:
                processed_messages.append({'type': 'warning', 'text': f"Subcategory '{name}' is missing a parent reference and was ignored."})
                continue
            actual_parent_db_id = None
            if str(parent_id_or_temp_id).startswith('temp_main_'):
                actual_parent_db_id = temp_main_id_to_db_id.get(parent_id_or_temp_id)
            else: 
                try: actual_parent_db_id = int(parent_id_or_temp_id)
                except ValueError: processed_messages.append({'type': 'warning', 'text': f"Invalid parent ID format for subcategory '{name}'."}); continue
            if actual_parent_db_id is None:
                processed_messages.append({'type': 'warning', 'text': f"Could not find or resolve parent for subcategory '{name}'. Ignored."})
                continue
            try:
                cursor.execute( "INSERT INTO categories (name, parent_id, financial_goal_type) VALUES (?, ?, ?)", (name, actual_parent_db_id, db_financial_goal_type))
                processed_messages.append({'type': 'info', 'text': f"Added subcategory: {name}"})
            except sqlite3.IntegrityError: processed_messages.append({'type': 'warning', 'text': f"Subcategory '{name}' under selected parent already exists or could not be added."})
            except Exception as e_sub: processed_messages.append({'type': 'error', 'text': f"Error adding subcategory '{name}': {e_sub}"})

        # --- Stage 3: Update Financial Types ---
        updated_type_count = 0
        for type_update in financial_type_updates:
            # ... (rest of update financial types logic from previous version, no changes here) ...
            cat_id_str = type_update.get('id')
            if not cat_id_str or not cat_id_str.isdigit(): continue 
            cat_id = int(cat_id_str)
            if cat_id in valid_deletions: continue 
            new_type = type_update.get('type')
            category_info = cursor.execute("SELECT parent_id FROM categories WHERE id = ?", (cat_id,)).fetchone()
            if category_info and category_info['parent_id'] is not None:
                db_new_type = new_type if new_type in ['Need', 'Want', 'Saving'] else None
                update_cursor = cursor.execute("UPDATE categories SET financial_goal_type = ? WHERE id = ?", (db_new_type, cat_id))
                if update_cursor.rowcount > 0: updated_type_count += 1
        if updated_type_count > 0: processed_messages.append({'type': 'info', 'text': f"{updated_type_count} financial type(s) updated."})

        # --- Stage 4: Process Deletions (using valid_deletions) ---
        deleted_count = 0
        if valid_deletions: 
            current_app.logger.info(f"Proceeding to delete category IDs that passed checks: {valid_deletions}")
            # Re-fetch details to ensure correct parent_id status for ordering deletion,
            # and to get names for logging/messages.
            placeholders_del = ','.join('?' for _ in valid_deletions)
            cats_for_deletion_final = cursor.execute(
                f"SELECT id, parent_id, name FROM categories WHERE id IN ({placeholders_del})",
                valid_deletions
            ).fetchall()
            
            del_sub_ids = [r['id'] for r in cats_for_deletion_final if r['parent_id'] is not None]
            del_main_ids = [r['id'] for r in cats_for_deletion_final if r['parent_id'] is None]
            
            cat_names_deleted = []

            for cat_id_to_delete in del_sub_ids:
                cat_name_to_delete = next((r['name'] for r in cats_for_deletion_final if r['id'] == cat_id_to_delete), f"ID {cat_id_to_delete}")
                current_app.logger.info(f"Deleting subcategory '{cat_name_to_delete}' (ID {cat_id_to_delete})")
                cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id_to_delete,))
                deleted_count += 1
                cat_names_deleted.append(f"'{cat_name_to_delete}' (Subcategory)")
            
            for cat_id_to_delete in del_main_ids:
                cat_name_to_delete = next((r['name'] for r in cats_for_deletion_final if r['id'] == cat_id_to_delete), f"ID {cat_id_to_delete}")
                # Safety: Final check for remaining subcategories (should have been caught by pre-check)
                if cursor.execute("SELECT 1 FROM categories WHERE parent_id = ? LIMIT 1", (cat_id_to_delete,)).fetchone():
                    err_msg = f"Main category '{cat_name_to_delete}' (ID: {cat_id_to_delete}) still has subcategories. Deletion aborted for this item."
                    processed_messages.append({'type': 'error', 'text': err_msg})
                    current_app.logger.error(f"Critical safety check failed: {err_msg}")
                    # This indicates a flaw in pre-check logic or a race condition.
                    # For now, we just log and add to processed_messages, a full rollback might be better.
                else:
                    current_app.logger.info(f"Deleting main category '{cat_name_to_delete}' (ID {cat_id_to_delete})")
                    cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id_to_delete,))
                    deleted_count += 1
                    cat_names_deleted.append(f"'{cat_name_to_delete}' (Main Category)")
            
            if deleted_count > 0:
                 processed_messages.append({'type': 'info', 'text': f"Successfully deleted {deleted_count} categor(y/ies): {', '.join(cat_names_deleted)}."})
        
        # --- Commit all changes (or rollback if any stage had a critical failure earlier) ---
        conn.commit() 
        current_app.logger.info(f"Save_all_category_changes completed. Processed messages: {processed_messages}")
        
        # Determine overall status and flash messages
        has_critical_errors_in_ops = any(m['type'] == 'error' for m in processed_messages)
        # No changes attempted beyond deletions if pre-checks failed.
        
        if has_critical_errors_in_ops:
            status = 'error'
            final_message = "Processed with errors. Please review messages."
            flash(final_message, "error")
        elif any(m['type'] == 'warning' for m in processed_messages):
            status = 'warning'
            final_message = "Processed with warnings."
            flash(final_message, "warning")
        elif len(new_main_categories_data) + len(new_sub_categories_data) + updated_type_count + deleted_count > 0:
            status = 'success'
            final_message = "All changes saved successfully!"
            flash(final_message, "success")
        else: # No operations and no errors/warnings (e.g. empty form submitted and no deletions)
            status = 'info'
            final_message = "No changes were submitted or applied."
            flash(final_message, "info")
            
        # Flash individual operational messages if they differ from the overall status message
        for msg_info in processed_messages:
            if msg_info['type'] != status or status == 'warning': # Show all warnings and errors individually
                 flash(msg_info['text'], msg_info['type'])
        
        return jsonify({'status': status, 'message': final_message, 'details': processed_messages})

    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Critical error in save_all_category_changes: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'A critical server error occurred: {str(e)}'}), 500


# Old /delete route - can be kept for other uses or removed if modal is the only way.
@bp.route('/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    # ... (This route's logic remains unchanged from category_routes_py_v4) ...
    conn = get_db()
    category_to_delete = conn.execute("SELECT name, parent_id FROM categories WHERE id = ?", (category_id,)).fetchone()
    redirect_url = url_for('main.index', open_manage_categories='true') 
    if not category_to_delete: 
        flash("Category not found.", "error")
        return redirect(redirect_url)
    category_name = category_to_delete['name']
    is_main_category_with_no_parent = category_to_delete['parent_id'] is None
    try:
        if is_main_category_with_no_parent:
            subcategories = conn.execute("SELECT 1 FROM categories WHERE parent_id = ? LIMIT 1", (category_id,)).fetchone()
            if subcategories: 
                flash(f"Cannot delete main category '{category_name}'. It still has subcategories. Please delete or reassign them first.", 'error')
                return redirect(redirect_url)
        transactions_linked = conn.execute("SELECT 1 FROM transactions WHERE category_id = ? LIMIT 1", (category_id,)).fetchone()
        if transactions_linked:
            flash(f"Cannot delete category '{category_name}'. It is used in transactions. Please reassign them first or ensure transactions are deleted.", 'error')
            return redirect(redirect_url)
        # MODIFIED CHECK: Only block if there are NON-ZERO budget goals
        non_zero_budget_goals = conn.execute(
            "SELECT 1 FROM budget_goals WHERE category_id = ? AND budgeted_amount != 0 LIMIT 1", (category_id,)
        ).fetchone()
        if non_zero_budget_goals:
            flash(f"Cannot delete category '{category_name}'. It has non-zero budget goals assigned. Please remove these budget goals first.", 'error')
            return redirect(redirect_url)
        
        # If we reach here, and it had only zero-value budget goals, we should delete them first
        # or ensure ON DELETE CASCADE for budget_goals table handles it (which it should).
        # Assuming ON DELETE CASCADE is working as defined in init_db.py for budget_goals.

        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        flash(f"Category '{category_name}' deleted successfully.", 'success')
        return redirect(redirect_url)
    except sqlite3.IntegrityError as e: 
        flash(f"Could not delete '{category_name}'. It might be referenced elsewhere. DB Error: {e}", 'error')
        current_app.logger.error(f"IntegrityError delete_category for ID {category_id}: {e}")
    except Exception as e: 
        flash(f"An unexpected error occurred while deleting '{category_name}': {e}", 'error')
        current_app.logger.error(f"Error delete_category for ID {category_id}: {e}")
    return redirect(redirect_url)

