// static/js/goals/goalModal.js
/**
 * Manages interactions with the #manageGoalsModal, including form population,
 * submission, and alerts.
 */
class GoalModalManager {
    constructor(modalSelector, apiService, onUpdateCallback) {
        this.modalElement = document.querySelector(modalSelector);
        if (!this.modalElement) {
            console.error(`Modal element not found for selector: ${modalSelector}`);
            return;
        }
        this.apiService = apiService;
        this.onUpdateCallback = onUpdateCallback; // Callback to refresh external displays
        this.modalInstance = bootstrap.Modal.getOrCreateInstance(this.modalElement);

        // Cache form elements
        this.goalFormEl = this.modalElement.querySelector('#goalForm');
        this.modalGoalIdEl = this.modalElement.querySelector('#modalGoalId');
        this.modalGoalNameEl = this.modalElement.querySelector('#modalGoalName');
        this.modalGoalTargetAmountEl = this.modalElement.querySelector('#modalGoalTargetAmount');
        this.modalGoalTargetDateEl = this.modalElement.querySelector('#modalGoalTargetDate');
        this.modalGoalIsCompletedEl = this.modalElement.querySelector('#modalGoalIsCompleted');
        this.saveGoalBtnEl = this.modalElement.querySelector('#saveGoalBtn');
        this.clearGoalFormBtnEl = this.modalElement.querySelector('#clearGoalFormBtn'); // Optional

        this.goalFundTransferFormEl = this.modalElement.querySelector('#goalFundTransferForm');
        this.modalTransferGoalSelectEl = this.modalElement.querySelector('#modalTransferGoalSelect');
        this.modalTransferAmountEl = this.modalElement.querySelector('#modalTransferAmount');
        this.modalTransferDateEl = this.modalElement.querySelector('#modalTransferDate');
        this.modalTransferDescriptionEl = this.modalElement.querySelector('#modalTransferDescription');
        this.contributeToGoalBtnEl = this.modalElement.querySelector('#contributeToGoalBtn');
        this.withdrawFromGoalBtnEl = this.modalElement.querySelector('#withdrawFromGoalBtn');
        
        this.alertContainerEl = this.modalElement.querySelector('#goal-modal-alerts');
        this.modalTitleEl = this.modalElement.querySelector('.modal-title');

        this._attachEventListeners();
    }

    _attachEventListeners() {
        if (this.goalFormEl) {
            this.goalFormEl.addEventListener('submit', (event) => {
                event.preventDefault();
                this._handleFormSubmit('save');
            });
        }
        if (this.contributeToGoalBtnEl) {
            this.contributeToGoalBtnEl.addEventListener('click', () => this._handleFormSubmit('contribute'));
        }
        if (this.withdrawFromGoalBtnEl) {
            this.withdrawFromGoalBtnEl.addEventListener('click', () => this._handleFormSubmit('withdraw'));
        }
        if (this.clearGoalFormBtnEl) {
            this.clearGoalFormBtnEl.addEventListener('click', () => {
                this.resetForm();
                if (this.modalGoalIdEl) this.modalGoalIdEl.value = '';
                if (this.saveGoalBtnEl) this.saveGoalBtnEl.textContent = 'Save Goal';
                if (this.modalTitleEl) this.modalTitleEl.textContent = 'Manage Financial Goals';
                this.clearGoalFormBtnEl.style.display = 'none';
            });
        }

        this.modalElement.addEventListener('hidden.bs.modal', () => {
            this.resetForm();
            this.clearAlerts();
             if (this.modalTitleEl) this.modalTitleEl.textContent = 'Manage Financial Goals';
             if (this.saveGoalBtnEl) this.saveGoalBtnEl.textContent = 'Save Goal';
             if (this.modalGoalIdEl) this.modalGoalIdEl.value = '';
             if (this.clearGoalFormBtnEl) this.clearGoalFormBtnEl.style.display = 'none';
        });
    }

    populateForm(goalData) {
        if (!this.goalFormEl) return;
        this.resetForm(); // Start fresh

        if (this.modalGoalIdEl) this.modalGoalIdEl.value = goalData.id;
        if (this.modalGoalNameEl) this.modalGoalNameEl.value = goalData.name;
        if (this.modalGoalTargetAmountEl) this.modalGoalTargetAmountEl.value = parseFloat(goalData.target_amount).toFixed(2);
        if (this.modalGoalTargetDateEl) this.modalGoalTargetDateEl.value = goalData.target_date ? goalData.target_date.split('T')[0] : '';
        if (this.modalGoalIsCompletedEl) this.modalGoalIsCompletedEl.checked = goalData.is_completed;
        
        if (this.saveGoalBtnEl) this.saveGoalBtnEl.textContent = 'Update Goal';
        if (this.modalTitleEl) this.modalTitleEl.textContent = 'View/Edit Goal: ' + goalData.name;
        if (this.clearGoalFormBtnEl) this.clearGoalFormBtnEl.style.display = 'inline-block';
    }

    showModalWithGoal(goalData) {
        this.populateForm(goalData);
        const manageTabTrigger = this.modalElement.querySelector('#goalTabs button[data-bs-target="#manageTabPane"]');
        if (manageTabTrigger) new bootstrap.Tab(manageTabTrigger).show();
        this.modalInstance.show();
    }

    showModalForCreate() {
        this.resetForm();
        if (this.modalTitleEl) this.modalTitleEl.textContent = 'Create New Goal';
        if (this.saveGoalBtnEl) this.saveGoalBtnEl.textContent = 'Save Goal';
        if (this.modalGoalIdEl) this.modalGoalIdEl.value = ''; // Ensure ID is empty for create
        if (this.clearGoalFormBtnEl) this.clearGoalFormBtnEl.style.display = 'none';

        const manageTabTrigger = this.modalElement.querySelector('#goalTabs button[data-bs-target="#manageTabPane"]');
        if (manageTabTrigger) new bootstrap.Tab(manageTabTrigger).show();
        this.modalInstance.show();
    }
    
    // Added for Fund/Withdraw tab direct opening
    showModalForFunding(goalId, goalName = "Selected Goal") {
        this.resetForm(); // Reset create/edit form
        if (this.modalTransferGoalSelectEl) {
            // Attempt to select the goal if options are already populated
            // Options are populated by GoalScroller or GoalsDisplay via global currentGoalsData
            // This might need GoalModalManager to have access to populateGoalSelectForFunding
            // or rely on it being populated externally before this call.
            // For now, just try to set value.
            this.modalTransferGoalSelectEl.value = goalId;
        }
        if (this.modalTransferDateEl && !this.modalTransferDateEl.value) {
            this.modalTransferDateEl.value = new Date().toISOString().split('T')[0];
        }
        if (this.modalTitleEl) this.modalTitleEl.textContent = `Fund/Withdraw: ${goalName}`;

        const fundTabTrigger = this.modalElement.querySelector('#goalTabs button[data-bs-target="#fundTabPane"]');
        if (fundTabTrigger) new bootstrap.Tab(fundTabTrigger).show();
        this.modalInstance.show();
    }


    resetForm() {
        if (this.goalFormEl) this.goalFormEl.reset();
        if (this.goalFundTransferFormEl) {
            // Don't reset goal selection, but clear amount/desc
            if (this.modalTransferAmountEl) this.modalTransferAmountEl.value = '';
            if (this.modalTransferDescriptionEl) this.modalTransferDescriptionEl.value = '';
            // Keep date or reset? For now, keep, set on modal show.
        }
        if (this.modalGoalIdEl) this.modalGoalIdEl.value = '';
        if (this.saveGoalBtnEl) this.saveGoalBtnEl.textContent = 'Save Goal';
        if (this.clearGoalFormBtnEl) this.clearGoalFormBtnEl.style.display = 'none';
        if (this.modalGoalIsCompletedEl) this.modalGoalIsCompletedEl.checked = false;
        // Default title reset is handled by hidden.bs.modal listener
    }

    async _handleFormSubmit(actionType) {
        this.clearAlerts();
        let promise;
        let formData;
        const goalId = this.modalGoalIdEl.value; // For 'save' (update)
        const transferGoalId = this.modalTransferGoalSelectEl ? this.modalTransferGoalSelectEl.value : null; // For 'contribute'/'withdraw'

        try {
            switch (actionType) {
                case 'save':
                    if (!this.goalFormEl) throw new Error("Goal form not found.");
                    formData = new FormData(this.goalFormEl);
                    // Ensure checkbox value is correctly represented for the backend
                    formData.set('is_completed', this.modalGoalIsCompletedEl.checked ? '1' : '0');
                    promise = goalId ? this.apiService.updateGoal(goalId, formData) : this.apiService.createGoal(formData);
                    break;
                case 'contribute':
                    if (!this.goalFundTransferFormEl || !transferGoalId) {
                        this.displayAlert("Please select a goal to contribute to.", "warning"); return;
                    }
                    formData = new FormData(this.goalFundTransferFormEl); // Contains amount, date, desc
                    promise = this.apiService.contributeToGoalApi(transferGoalId, formData);
                    break;
                case 'withdraw':
                    if (!this.goalFundTransferFormEl || !transferGoalId) {
                        this.displayAlert("Please select a goal to withdraw from.", "warning"); return;
                    }
                    formData = new FormData(this.goalFundTransferFormEl);
                    promise = this.apiService.withdrawFromGoalApi(transferGoalId, formData);
                    break;
                default:
                    throw new Error("Invalid action type for form submission.");
            }

            const result = await promise;
            if (result.status === 'success') {
                this.displayAlert(result.message || 'Operation successful!', 'success');
                if (actionType === 'save') this.resetForm(); // Reset create/edit form
                else if (this.goalFundTransferFormEl) { // Clear amount/desc for fund/withdraw
                    if(this.modalTransferAmountEl) this.modalTransferAmountEl.value = '';
                    if(this.modalTransferDescriptionEl) this.modalTransferDescriptionEl.value = '';
                }
                
                if (typeof this.onUpdateCallback === 'function') {
                    this.onUpdateCallback(); // Refresh external displays
                }
                // Optionally hide modal after certain actions
                if (actionType === 'contribute' || actionType === 'withdraw' || (actionType === 'save' && !goalId)) {
                    // this.modalInstance.hide(); // Example: hide after funding or creating
                }
            } else {
                this.displayAlert(result.message || 'Operation failed.', 'danger');
            }
        } catch (error) {
            console.error(`Error during ${actionType}:`, error);
            this.displayAlert(error.message || `An unexpected error occurred during ${actionType}.`, 'danger');
        }
    }

    displayAlert(message, type = 'danger') {
        if (!this.alertContainerEl) {
            console.warn("Modal alert container not found. Alert:", message);
            return;
        }
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-2`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
        this.alertContainerEl.innerHTML = ''; // Clear previous alerts
        this.alertContainerEl.appendChild(alertDiv);
    }

    clearAlerts() {
        if (this.alertContainerEl) this.alertContainerEl.innerHTML = '';
    }
}
