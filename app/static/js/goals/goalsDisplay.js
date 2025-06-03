// static/js/goals/goalsDisplay.js
/**
 * Manages rendering goal cards/list in #goalsDisplayArea on goals_page.html
 * and their interactions.
 */
class GoalsDisplay {
    constructor(displayAreaSelector, initialGoals, apiService, modalManager) {
        this.displayAreaEl = document.querySelector(displayAreaSelector);
        this.apiService = apiService;
        this.modalManager = modalManager; // For opening modal for edit/fund

        if (!this.displayAreaEl) {
            console.error(`Goals display area element not found for selector: ${displayAreaSelector}`);
            return;
        }
        
        this.displayGoals(initialGoals || []);
        this._attachEventListeners();
    }

    _formatCurrency(amount) { // Local helper or use a global one
        if (amount === null || typeof amount === 'undefined') amount = 0;
        if (typeof amount !== 'number') amount = parseFloat(amount) || 0;
        return '$' + amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    renderGoalCard(goalData) {
        const cardCol = document.createElement('div');
        cardCol.className = 'col'; 
        const progress = Math.min(100, Math.max(0, parseFloat(goalData.progress) || 0));
        const targetAmountFormatted = this._formatCurrency(goalData.target_amount);
        const currentAmountFormatted = this._formatCurrency(goalData.current_amount);
        const isCompletedClass = goalData.is_completed ? 'border-success bg-success-subtle text-success-emphasis' : 'border-light';
        const headerBgClass = goalData.is_completed ? 'bg-success-subtle' : 'bg-light';

        // Using page-goal-action-btn class for event delegation
        cardCol.innerHTML = `
            <div class="card h-100 shadow-sm ${isCompletedClass}">
                <div class="card-header d-flex justify-content-between align-items-center ${headerBgClass}">
                    <h5 class="card-title mb-0 text-truncate fs-6" title="${goalData.name}">${goalData.name}</h5>
                    ${goalData.is_completed ? '<span class="badge bg-success">Completed</span>' : `<span class="badge bg-info-subtle border border-info-subtle text-info-emphasis">${progress.toFixed(0)}%</span>`}
                </div>
                <div class="card-body">
                    <p class="card-text small mb-1"><strong>Progress:</strong> ${currentAmountFormatted} / ${targetAmountFormatted}</p>
                    <div class="progress mb-2" style="height: 20px;">
                        <div class="progress-bar ${goalData.is_completed ? 'bg-success' : 'bg-primary'} progress-bar-striped${!goalData.is_completed ? ' progress-bar-animated' : ''}" role="progressbar" style="width: ${progress.toFixed(2)}%;" aria-valuenow="${progress.toFixed(2)}" aria-valuemin="0" aria-valuemax="100">${progress.toFixed(1)}%</div>
                    </div>
                    ${goalData.target_date ? `<p class="card-text small text-muted mb-0"><strong>Target:</strong> ${goalData.target_date}</p>` : '<p class="card-text small text-muted mb-0">No target date</p>'}
                    <p class="card-text small text-muted"><small>Created: ${new Date(goalData.created_at).toLocaleDateString()}</small></p>
                </div>
                <div class="card-footer bg-transparent border-top-0 text-center pt-0">
                    <button type="button" class="btn btn-sm btn-outline-primary page-goal-action-btn me-1" data-goal-id="${goalData.id}" data-action="edit" title="Edit Goal Details">
                        <svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" class="bi bi-pencil-square me-1" viewBox="0 0 16 16"><path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293z"/><path d="m10.79 6.355.647.646.646-.646a.5.5 0 0 1 .708 0l.646.646-.646.647.646.646a.5.5 0 0 1 0 .708l-.646.646.646.646-.646.646a.5.5 0 0 1-.708 0l-.646-.646.646-.647-.646-.646a.5.5 0 0 1 0-.708zm-8.617 1.524-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l3.206-3.206z"/><path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5z"/></svg> Manage
                    </button>
                    ${!goalData.is_completed ? `<button type="button" class="btn btn-sm btn-outline-success page-goal-action-btn" data-goal-id="${goalData.id}" data-action="fund" title="Contribute/Withdraw Funds">
                        <svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" class="bi bi-piggy-bank me-1" viewBox="0 0 16 16"><path d="M5 6.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0"/><path d="M1.5 2A1.5 1.5 0 0 0 0 3.5v5h1.53a.5.5 0 0 1 .458.223l.494.86a1 1 0 0 0 .868.617h4.299a1 1 0 0 0 .868-.617l.494-.86A.5.5 0 0 1 10.47 8.5H12v5A1.5 1.5 0 0 0 13.5 15h.25A1.25 1.25 0 0 0 15 13.75V5a.5.5 0 0 0-.5-.5H14V3.5A1.5 1.5 0 0 0 12.5 2zM12 5.5V13c0 .276-.224.5-.5.5H1.52c-.276 0-.5-.224-.5-.5V5.5zm0-2A.5.5 0 0 1 12.5 3H4.19c-.276 0-.5.224-.5.5V5h-.5z"/></svg> Fund
                    </button>` : ''}
                     <button type="button" class="btn btn-sm btn-outline-danger page-goal-action-btn" data-goal-id="${goalData.id}" data-action="delete" title="Delete Goal">
                        <svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" class="bi bi-trash3" viewBox="0 0 16 16"><path d="M6.5 1h3a.5.5 0 0 1 .5.5v1H6v-1a.5.5 0 0 1 .5-.5M11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3A1.5 1.5 0 0 0 5 1.5v1H1.5a.5.5 0 0 0 0 1h.538l.853 10.66A2 2 0 0 0 4.885 16h6.23a2 2 0 0 0 1.994-1.84l.853-10.66H14.5a.5.5 0 0 0 0-1zM4.5 5.024l.5 8.5a.5.5 0 1 0 .998-.06l-.5-8.5a.5.5 0 1 0-.998.06m3.5-.05.5 8.5a.5.5 0 1 0 .998-.06l-.5-8.5a.5.5 0 1 0-.998.06m3.5.056l-.5 8.5a.5.5 0 1 0 .998.06l.5-8.5a.5.5 0 1 0-.998-.06Z"/></svg> Delete
                    </button>
                </div>
            </div>
        `;
        return cardCol;
    }

    displayGoals(goals) {
        if (!this.displayAreaEl) return;
        this.displayAreaEl.innerHTML = ''; // Clear previous goals

        if (!goals || goals.length === 0) {
            this.displayAreaEl.innerHTML = '<div class="col-12"><p class="text-muted text-center fs-5 mt-5">No financial goals set up yet. Click "Add/Manage Goals" to create your first one!</p></div>';
            return;
        }
        goals.forEach(goal => {
            this.displayAreaEl.appendChild(this.renderGoalCard(goal));
        });
    }

    async refresh() {
        try {
            const data = await this.apiService.fetchAllGoals();
            if (data && data.goals) {
                this.displayGoals(data.goals);
            }
        } catch (error) {
            console.error("Error refreshing goals display:", error);
            if (this.displayAreaEl) this.displayAreaEl.innerHTML = '<div class="col-12"><p class="text-danger text-center fs-5 mt-5">Could not refresh goals. Please try again later.</p></div>';
        }
    }

    _handleCardAction(event) {
        const button = event.target.closest('button.page-goal-action-btn');
        if (!button) return;

        const goalId = button.dataset.goalId;
        const action = button.dataset.action;

        if (!goalId) return;

        if (action === 'edit') {
            this.apiService.fetchGoalDetails(goalId)
                .then(data => {
                    if (data.goal && this.modalManager) {
                        this.modalManager.showModalWithGoal(data.goal);
                    } else if (!data.goal) {
                        console.warn('Goal not found for edit:', goalId);
                         if(this.modalManager) this.modalManager.displayAlert('Goal details not found.', 'warning');
                    }
                })
                .catch(err => {
                    console.error('Error fetching goal for edit:', err);
                    if(this.modalManager) this.modalManager.displayAlert('Could not load goal details for editing.', 'danger');
                });
        } else if (action === 'fund') {
            if (this.modalManager) {
                const goal = currentGoalsData.find(g => g.id.toString() === goalId); // Assuming currentGoalsData is accessible or passed
                this.modalManager.showModalForFunding(goalId, goal ? goal.name : 'Selected Goal');
            }
        } else if (action === 'delete') {
            const goal = currentGoalsData.find(g => g.id.toString() === goalId.toString());
            const goalName = goal ? goal.name : `Goal ID ${goalId}`;
            if (confirm(`Are you sure you want to delete the goal "${goalName}"? This action cannot be undone.`)) {
                this.apiService.deleteGoalApi(goalId)
                    .then(result => {
                        if (result.status === 'success') {
                            if(this.modalManager) this.modalManager.displayAlert(result.message || 'Goal deleted successfully.', 'success'); // Show alert in modal if open
                            this.refresh(); // Refresh the main display
                        } else {
                            if(this.modalManager) this.modalManager.displayAlert(result.message || 'Failed to delete goal.', 'danger');
                        }
                    })
                    .catch(err => {
                        console.error('Error deleting goal:', err);
                        if(this.modalManager) this.modalManager.displayAlert('An error occurred while deleting the goal.', 'danger');
                    });
            }
        }
    }

    _attachEventListeners() {
        if (this.displayAreaEl) {
            this.displayAreaEl.addEventListener('click', (event) => this._handleCardAction(event));
        }
    }
}
