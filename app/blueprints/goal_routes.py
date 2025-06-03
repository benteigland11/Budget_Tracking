# app/blueprints/goal_routes.py
# Provides API endpoints for managing financial goals and their funding,
# and a page for viewing goals.

from flask import Blueprint, request, jsonify, current_app, render_template
from app.database import get_db 
from app.utils import db_helpers 
import datetime 

bp = Blueprint('goal_routes', __name__) 

# --- Page Route ---
@bp.route('/', methods=['GET']) 
def view_goals_page():
    """
    Renders the dedicated page for viewing and managing financial goals.
    Fetches all goals and passes them to the template for initial display.
    """
    try:
        initial_goals = db_helpers.get_all_goals()
        return render_template('goals_page.html', initial_goals_data=initial_goals)
    except Exception as e:
        current_app.logger.error(f"Error loading goals page: {e}", exc_info=True)
        return render_template('goals_page.html', initial_goals_data=[], error="Could not load goals data.")

# --- API Routes ---

@bp.route('/api/create', methods=['POST'])
def create_goal():
    """
    Creates a new financial goal.
    Form params: name, target_amount, target_date (optional, YYYY-MM-DD)
    """
    try:
        name = request.form.get('name')
        target_amount_str = request.form.get('target_amount')
        target_date = request.form.get('target_date') 

        if not name or not target_amount_str:
            return jsonify({'status': 'error', 'message': 'Name and target amount are required.'}), 400
        
        try:
            target_amount = float(target_amount_str)
            if target_amount <= 0:
                return jsonify({'status': 'error', 'message': 'Target amount must be positive.'}), 400
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid target amount format.'}), 400

        if target_date: 
            try:
                datetime.datetime.strptime(target_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({'status': 'error', 'message': 'Invalid target date format. Use YYYY-MM-DD.'}), 400
        else:
            target_date = None 

        goal_id = db_helpers.add_goal(name, target_amount, target_date)

        if goal_id:
            current_app.logger.info(f"Goal '{name}' created successfully with ID: {goal_id}.")
            return jsonify({'status': 'success', 'message': 'Goal created successfully.', 'goal_id': goal_id}), 201
        else:
            existing_goals = db_helpers.get_all_goals() 
            if any(g['name'].lower() == name.lower() for g in existing_goals):
                 return jsonify({'status': 'error', 'message': f"Goal with name '{name}' already exists."}), 409
            return jsonify({'status': 'error', 'message': 'Failed to create goal. Database error or duplicate name.'}), 500
    except Exception as e:
        current_app.logger.error(f"Error in /api/create goal: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f"An unexpected error occurred: {str(e)}"}), 500

@bp.route('/api/list', methods=['GET'])
def list_goals():
    """Lists all financial goals."""
    try:
        goals = db_helpers.get_all_goals()
        return jsonify({'status': 'success', 'goals': goals, 'message': 'Goals retrieved successfully.'}), 200
    except Exception as e:
        current_app.logger.error(f"Error in /api/list goals: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f"An unexpected error occurred: {str(e)}"}), 500

@bp.route('/api/<int:goal_id>/details', methods=['GET'])
def get_goal_details_api(goal_id):
    """
    Retrieves details for a single financial goal.
    Returns: JSON response with goal data or error message.
    """
    try:
        goal = db_helpers.get_goal_by_id(goal_id)
        if goal:
            return jsonify({'status': 'success', 'goal': goal}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Goal not found.'}), 404
    except Exception as e:
        current_app.logger.error(f"Error in /api/{goal_id}/details: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f"An unexpected error occurred: {str(e)}"}), 500

@bp.route('/api/<int:goal_id>/update', methods=['POST'])
def update_goal(goal_id):
    """
    Updates an existing financial goal.
    Form params: name, target_amount, target_date (optional), is_completed (optional)
    """
    try:
        goal = db_helpers.get_goal_by_id(goal_id)
        if not goal:
            return jsonify({'status': 'error', 'message': 'Goal not found.'}), 404

        update_params = {'goal_id': goal_id}
        
        if 'name' in request.form:
            name = request.form.get('name')
            if not name.strip(): 
                 return jsonify({'status': 'error', 'message': 'Goal name cannot be empty.'}), 400
            update_params['name'] = name
        
        if 'target_amount' in request.form:
            target_amount_str = request.form.get('target_amount')
            try:
                target_amount = float(target_amount_str)
                if target_amount <= 0:
                    return jsonify({'status': 'error', 'message': 'Target amount must be positive.'}), 400
                update_params['target_amount'] = target_amount
            except (ValueError, TypeError): 
                return jsonify({'status': 'error', 'message': 'Invalid target amount format.'}), 400
        
        if 'target_date' in request.form:
            target_date = request.form.get('target_date')
            if target_date == "": 
                update_params['target_date'] = "" 
            elif target_date: 
                try:
                    datetime.datetime.strptime(target_date, '%Y-%m-%d')
                    update_params['target_date'] = target_date
                except ValueError:
                    return jsonify({'status': 'error', 'message': 'Invalid target date format. Use YYYY-MM-DD or empty to clear.'}), 400
            
        if 'is_completed' in request.form:
            is_completed_str = request.form.get('is_completed')
            if is_completed_str.lower() in ['true', '1', 'on']: 
                update_params['is_completed'] = True
            elif is_completed_str.lower() in ['false', '0', 'off']:
                update_params['is_completed'] = False
            else:
                return jsonify({'status': 'error', 'message': "Invalid 'is_completed' value. Use true/1 or false/0."}), 400
        
        if len(update_params) == 1 : 
             return jsonify({'status': 'info', 'message': 'No update parameters provided in the form.'}), 200

        success = db_helpers.update_goal_details(**update_params)

        if success:
            return jsonify({'status': 'success', 'message': 'Goal updated successfully.'}), 200
        else:
            if 'name' in update_params: 
                all_goals = db_helpers.get_all_goals()
                if any(g['name'].lower() == update_params['name'].lower() and g['id'] != goal_id for g in all_goals):
                    return jsonify({'status': 'error', 'message': f"Failed to update goal. Name '{update_params['name']}' may already be in use by another goal."}), 409
            return jsonify({'status': 'error', 'message': 'Failed to update goal. Goal not found, no changes made, or database error.'}), 500 
    except Exception as e:
        current_app.logger.error(f"Error in /api/update goal {goal_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f"An unexpected error occurred: {str(e)}"}), 500

@bp.route('/api/<int:goal_id>/delete', methods=['POST'])
def delete_goal_route(goal_id):
    """Deletes a financial goal."""
    try:
        goal = db_helpers.get_goal_by_id(goal_id)
        if not goal:
            return jsonify({'status': 'error', 'message': 'Goal not found.'}), 404
            
        if db_helpers.delete_goal(goal_id):
            return jsonify({'status': 'success', 'message': 'Goal deleted successfully.'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to delete goal.'}), 500
    except Exception as e:
        current_app.logger.error(f"Error in /api/delete goal {goal_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f"An unexpected error occurred: {str(e)}"}), 500

@bp.route('/api/<int:goal_id>/contribute', methods=['POST'])
def contribute_to_goal(goal_id):
    """Records a contribution to a goal."""
    try:
        amount_str = request.form.get('amount')
        date_str = request.form.get('date')
        description = request.form.get('description', '') 

        if not amount_str or not date_str:
            return jsonify({'status': 'error', 'message': 'Amount and date are required for contribution.'}), 400
        
        try:
            amount = float(amount_str)
            if amount <= 0:
                return jsonify({'status': 'error', 'message': 'Contribution amount must be positive.'}), 400
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid amount format.'}), 400
        
        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

        goal = db_helpers.get_goal_by_id(goal_id)
        if not goal:
            return jsonify({'status': 'error', 'message': 'Goal not found.'}), 404

        success = db_helpers.record_goal_funding_transaction(
            goal_id=goal_id,
            amount_for_goal=amount,
            transaction_date=date_str,
            description=description,
            is_contribution=True
        )

        if success:
            updated_goal = db_helpers.get_goal_by_id(goal_id) 
            return jsonify({
                'status': 'success', 
                'message': 'Contribution recorded successfully.',
                'new_current_amount': updated_goal['current_amount'] if updated_goal else goal['current_amount'] 
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to record contribution.'}), 500
    except Exception as e:
        current_app.logger.error(f"Error in /api/contribute to goal {goal_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f"An unexpected error occurred: {str(e)}"}), 500

@bp.route('/api/<int:goal_id>/withdraw', methods=['POST'])
def withdraw_from_goal(goal_id):
    """Records a withdrawal from a goal."""
    try:
        amount_str = request.form.get('amount')
        date_str = request.form.get('date')
        description = request.form.get('description', '')

        if not amount_str or not date_str:
            return jsonify({'status': 'error', 'message': 'Amount and date are required for withdrawal.'}), 400

        try:
            amount = float(amount_str)
            if amount <= 0:
                return jsonify({'status': 'error', 'message': 'Withdrawal amount must be positive.'}), 400
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid amount format.'}), 400

        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

        goal = db_helpers.get_goal_by_id(goal_id)
        if not goal:
            return jsonify({'status': 'error', 'message': 'Goal not found.'}), 404
        
        if amount > goal['current_amount']:
             return jsonify({'status': 'error', 'message': f"Withdrawal amount (${amount:.2f}) exceeds current goal balance (${goal['current_amount']:.2f})."}), 400

        success = db_helpers.record_goal_funding_transaction(
            goal_id=goal_id,
            amount_for_goal=amount,
            transaction_date=date_str,
            description=description,
            is_contribution=False 
        )

        if success:
            updated_goal = db_helpers.get_goal_by_id(goal_id)
            return jsonify({
                'status': 'success', 
                'message': 'Withdrawal recorded successfully.',
                'new_current_amount': updated_goal['current_amount'] if updated_goal else goal['current_amount']
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to record withdrawal.'}), 500
    except Exception as e:
        current_app.logger.error(f"Error in /api/withdraw from goal {goal_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f"An unexpected error occurred: {str(e)}"}), 500
