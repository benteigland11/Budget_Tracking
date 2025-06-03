// app/static/js/paycheckModal.js

document.addEventListener('DOMContentLoaded', () => {
    const logPaycheckModalEl = document.getElementById('logPaycheckModal');
    if (!logPaycheckModalEl) {
        return; 
    }
    console.log("Paycheck Modal JS Loaded");

    const paycheckForm = document.getElementById('logPaycheckForm');
    const grossPayInput = document.getElementById('paycheck_gross_pay');
    const deductionsContainer = document.getElementById('paycheckDeductionsContainer');
    const addDeductionBtn = document.getElementById('addPaycheckDeductionBtn');
    const calculatedNetPayDisplay = document.getElementById('calculatedNetPayDisplay');
    const payDateField = document.getElementById('paycheck_date');
    const paycheckAlertContainer = document.getElementById('paycheck-modal-alerts'); // Get the alert container

    let deductionRowCounter = 0;

    // Helper function to display alerts within the paycheck modal
    function displayPaycheckModalAlert(message, type = 'danger') {
        if (paycheckAlertContainer) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
            alertDiv.role = 'alert';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            paycheckAlertContainer.innerHTML = ''; // Clear previous alerts
            paycheckAlertContainer.appendChild(alertDiv);
        } else {
            alert(message); // Fallback if container not found (should not happen)
        }
    }

    function clearPaycheckModalAlerts() {
        if (paycheckAlertContainer) paycheckAlertContainer.innerHTML = '';
    }


    function calculateNetPay() {
        if (!grossPayInput || !calculatedNetPayDisplay) return;
        let grossPay = parseFloat(grossPayInput.value) || 0;
        let totalDeductions = 0;
        deductionsContainer.querySelectorAll('.deduction-row').forEach(row => {
            const amountInput = row.querySelector('input[name="deduction_amount[]"]');
            totalDeductions += parseFloat(amountInput.value) || 0;
        });
        const netPay = grossPay - totalDeductions;
        calculatedNetPayDisplay.textContent = `$${netPay.toFixed(2)}`;
        if (netPay < 0) {
            calculatedNetPayDisplay.classList.add('text-danger');
        } else {
            calculatedNetPayDisplay.classList.remove('text-danger');
        }
    }

    function addDeductionRow() {
        deductionRowCounter++;
        const newRow = document.createElement('div');
        newRow.className = 'row gx-2 mb-2 deduction-row align-items-center';
        newRow.innerHTML = `
            <div class="col-md-5">
                <input type="text" class="form-control form-control-sm" name="deduction_description[]" placeholder="Deduction Description (e.g., Federal Tax)" required>
            </div>
            <div class="col-md-3">
                <div class="input-group input-group-sm">
                    <span class="input-group-text">$</span>
                    <input type="number" step="0.01" min="0" class="form-control form-control-sm deduction-amount-input" name="deduction_amount[]" placeholder="Amount" required>
                </div>
            </div>
            <div class="col-md-3">
                <select class="form-select form-select-sm" name="deduction_type[]" required>
                    <option value="" selected disabled>Type...</option>
                    <option value="TAX_FEDERAL">Tax: Federal</option>
                    <option value="TAX_STATE">Tax: State</option>
                    <option value="TAX_LOCAL">Tax: Local</option>
                    <option value="TAX_FICA">Tax: FICA (SS/Med)</option>
                    <option value="PRETAX_RETIREMENT">Pre-Tax: Retirement (401k/403b)</option>
                    <option value="PRETAX_HSA">Pre-Tax: HSA</option>
                    <option value="PRETAX_INSURANCE_HEALTH">Pre-Tax: Health Insurance</option>
                    <option value="PRETAX_INSURANCE_DENTAL">Pre-Tax: Dental Insurance</option>
                    <option value="PRETAX_INSURANCE_VISION">Pre-Tax: Vision Insurance</option>
                    <option value="PRETAX_OTHER">Pre-Tax: Other</option>
                    <option value="POSTTAX_RETIREMENT_ROTH">Post-Tax: Roth Retirement</option>
                    <option value="POSTTAX_GARNISHMENT">Post-Tax: Garnishment</option>
                    <option value="POSTTAX_INSURANCE">Post-Tax: Insurance</option>
                    <option value="POSTTAX_OTHER">Post-Tax: Other</option>
                </select>
            </div>
            <div class="col-md-1 text-end">
                <button type="button" class="btn btn-sm btn-outline-danger remove-deduction-btn" title="Remove Deduction">&times;</button>
            </div>
        `;
        deductionsContainer.appendChild(newRow);
        newRow.querySelector('.remove-deduction-btn').addEventListener('click', function() {
            this.closest('.deduction-row').remove();
            calculateNetPay();
        });
        newRow.querySelector('.deduction-amount-input').addEventListener('input', calculateNetPay);
        calculateNetPay(); // Recalculate when a row is added
    }

    if (grossPayInput) {
        grossPayInput.addEventListener('input', calculateNetPay);
    }
    if (addDeductionBtn) {
        addDeductionBtn.addEventListener('click', addDeductionRow);
    }

    if (paycheckForm) {
        paycheckForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            clearPaycheckModalAlerts(); // Clear old alerts
            const formData = new FormData(paycheckForm);
            const deductions = [];
            const descriptions = formData.getAll('deduction_description[]');
            const amounts = formData.getAll('deduction_amount[]');
            const types = formData.getAll('deduction_type[]');

            for (let i = 0; i < descriptions.length; i++) {
                if (descriptions[i] && amounts[i] && types[i]) {
                    deductions.push({
                        description: descriptions[i],
                        amount: parseFloat(amounts[i]),
                        type: types[i]
                    });
                } else if (descriptions[i] || amounts[i] || types[i]) { 
                    // If any part of a deduction row is filled, all parts are required
                    displayPaycheckModalAlert("All fields (Description, Amount, Type) are required for each deduction row.", "warning");
                    return;
                }
            }

            const payload = {
                pay_date: formData.get('pay_date'),
                employer_name: formData.get('employer_name'),
                gross_pay: parseFloat(formData.get('gross_pay')),
                notes: formData.get('notes'),
                deductions: deductions
            };

            if (!payload.pay_date || isNaN(payload.gross_pay)) { // Check if gross_pay is NaN after parseFloat
                displayPaycheckModalAlert("Pay Date and a valid Gross Pay amount are required.", "danger");
                return;
            }
            
            const saveButton = document.getElementById('savePaycheckBtn');
            saveButton.disabled = true;
            saveButton.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Logging...`;

            try {
                if (!window.flask_urls || !window.flask_urls.log_paycheck) {
                    console.error("Flask URL for log_paycheck not defined.");
                    displayPaycheckModalAlert("Configuration error: Log paycheck URL not found.", "danger");
                    saveButton.disabled = false;
                    saveButton.textContent = "Log Paycheck & Record Net Income";
                    return;
                }

                const response = await fetch(window.flask_urls.log_paycheck, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();

                if (response.ok && result.status === 'success') {
                    // Success message will be flashed by Flask on page reload
                    paycheckForm.reset();
                    deductionsContainer.innerHTML = ''; 
                    calculateNetPay(); 
                    const logPaycheckModalBootstrapInstance = bootstrap.Modal.getInstance(logPaycheckModalEl);
                    if (logPaycheckModalBootstrapInstance) {
                        logPaycheckModalBootstrapInstance.hide();
                    }
                    window.location.reload(); // Reload to see new transaction and flashed message
                } else {
                    displayPaycheckModalAlert(result.message || 'Could not log paycheck.', 'danger');
                }
            } catch (error) {
                console.error("Error logging paycheck:", error);
                displayPaycheckModalAlert("An unexpected network error occurred. Please try again.", "danger");
            } finally {
                saveButton.disabled = false;
                saveButton.textContent = "Log Paycheck & Record Net Income";
            }
        });
    }
    
    logPaycheckModalEl.addEventListener('shown.bs.modal', () => {
        clearPaycheckModalAlerts();
        if (payDateField && !payDateField.value) {
            const today = new Date();
            const yyyy = today.getFullYear();
            const mm = String(today.getMonth() + 1).padStart(2, '0');
            const dd = String(today.getDate()).padStart(2, '0');
            payDateField.value = `${yyyy}-${mm}-${dd}`;
        }
        if (deductionsContainer.children.length === 0) {
            addDeductionRow(); // Add one initial deduction row
        }
        calculateNetPay(); 
    });

    // Initial calculation if there are pre-filled values (e.g. from form repopulation on error)
    calculateNetPay();
});
