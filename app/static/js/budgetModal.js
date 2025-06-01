// app/static/js/budgetModal.js

// Assumes monthNames is available globally from index.html
// Assumes flask_urls.get_planning_data is available globally (set in index.html)

document.addEventListener('DOMContentLoaded', () => {
    console.log("Budget Modal JS Loaded");

    const budgetMonthSelectModal = document.getElementById('budget_month_select_modal');
    const budgetYearSelectModal = document.getElementById('budget_year_select_modal');
    const budgetPeriodDisplay = document.getElementById('budgetPeriodDisplay');
    const budgetPlanningTableBody = document.getElementById('budgetPlanningTableBody');
    const hiddenBudgetYearInput = document.getElementById('hiddenBudgetYearInput');
    const hiddenBudgetMonthInput = document.getElementById('hiddenBudgetMonthInput');
    const saveCurrentBudgetBtn = document.getElementById('saveCurrentBudgetBtn');
    let isBudgetFormDirty = false;
    
    // Initial values from hidden fields (set by Flask on page load)
    let currentBudgetYear = hiddenBudgetYearInput ? hiddenBudgetYearInput.value : new Date().getFullYear().toString();
    let currentBudgetMonth = hiddenBudgetMonthInput ? hiddenBudgetMonthInput.value : (new Date().getMonth() + 1).toString();

    function updateSaveButtonText(year, monthIndex) { // monthIndex is 0-11
        if (saveCurrentBudgetBtn && typeof monthNames !== 'undefined' && monthNames[monthIndex]) {
            saveCurrentBudgetBtn.textContent = `Save ${monthNames[monthIndex]} ${year} Plan`;
        } else if (saveCurrentBudgetBtn) {
            saveCurrentBudgetBtn.textContent = `Save Plan`; // Fallback
        }
    }
    
    if (budgetPeriodDisplay && saveCurrentBudgetBtn) {
        updateSaveButtonText(currentBudgetYear, parseInt(currentBudgetMonth) - 1);
    }

    function attachBudgetInputListeners() {
        if (budgetPlanningTableBody) {
            budgetPlanningTableBody.querySelectorAll('input[name="budgeted_amount"]').forEach(input => {
                input.removeEventListener('input', markBudgetFormDirty);
                input.addEventListener('input', markBudgetFormDirty);
            });
        }
    }
    function markBudgetFormDirty() {
        isBudgetFormDirty = true;
        console.log("Budget form is dirty.");
    }

    async function saveCurrentBudget(callbackAfterSave) {
        const budgetForm = document.getElementById('budgetGoalsForm');
        if (!budgetForm) return false;

        const formData = new FormData(budgetForm);
        
        try {
            const response = await fetch(budgetForm.action, { // budgetForm.action should be set by Flask
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                let errorMsg = `HTTP error! status: ${response.status}`;
                try { const errorData = await response.json(); errorMsg = errorData.message || errorMsg; } catch (e) {}
                alert(`Error saving budget: ${errorMsg}`); 
                return false; 
            }
            console.log("Budget saved successfully (or no changes detected).");
            isBudgetFormDirty = false; 
            if (callbackAfterSave && typeof callbackAfterSave === 'function') {
                callbackAfterSave();
            }
            return true; 
        } catch (error) {
            console.error("Error submitting budget form:", error);
            alert("An unexpected error occurred while saving the budget.");
            return false; 
        }
    }

    if (saveCurrentBudgetBtn) {
        saveCurrentBudgetBtn.addEventListener('click', async function(event) {
            event.preventDefault(); 
            const success = await saveCurrentBudget(() => {
                const savedYear = hiddenBudgetYearInput.value;
                const savedMonth = hiddenBudgetMonthInput.value;
                // Redirect to main dashboard showing the analytics for the period just budgeted
                // Assumes flask_urls.main_index is defined globally
                if (window.flask_urls && window.flask_urls.main_index) {
                    window.location.href = `${window.flask_urls.main_index}?year=${savedYear}&month=${savedMonth}&period_type=monthly`;
                } else {
                    window.location.reload(); // Fallback
                }
            });
        });
    }

    async function fetchAndUpdateBudgetPlanner(year, month, forceSwitch = false) {
        if (!year || !month) {
            console.warn("Year or month not provided for budget planner update.");
            return;
        }
        
        if (isBudgetFormDirty && !forceSwitch) {
            const currentMonthName = (typeof monthNames !== 'undefined' && monthNames[parseInt(currentBudgetMonth) - 1]) ? monthNames[parseInt(currentBudgetMonth) - 1] : `Month ${currentBudgetMonth}`;
            const confirmation = confirm(`You have unsaved changes for ${currentMonthName} ${currentBudgetYear}. Save changes before switching?`);
            
            if (confirmation) { 
                const saved = await saveCurrentBudget();
                if (saved) {
                    isBudgetFormDirty = false; 
                } else {
                    return; 
                }
            } else { 
                const proceedWithoutSaving = confirm(`Discard unsaved changes for ${currentMonthName} ${currentBudgetYear} and switch to ${monthNames[parseInt(month)-1]} ${year}?`);
                if (!proceedWithoutSaving) {
                    if(budgetYearSelectModal) budgetYearSelectModal.value = currentBudgetYear;
                    if(budgetMonthSelectModal) budgetMonthSelectModal.value = currentBudgetMonth;
                    return; 
                }
                isBudgetFormDirty = false; 
            }
        }

        console.log(`Fetching budget data for Year: ${year}, Month: ${month}`);
        if (budgetPlanningTableBody) {
            budgetPlanningTableBody.innerHTML = '<tr><td colspan="3" class="text-center p-5"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>';
        }
        
        try {
            // Assumes flask_urls.get_planning_data is defined globally
            if (!window.flask_urls || !window.flask_urls.get_planning_data) {
                console.error("Flask URL for get_planning_data not defined.");
                if (budgetPlanningTableBody) budgetPlanningTableBody.innerHTML = '<tr><td colspan="3" class="text-center text-danger p-3">Configuration error.</td></tr>';
                return;
            }
            const response = await fetch(`${window.flask_urls.get_planning_data}?year=${year}&month=${month}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}, message: ${await response.text()}`);
            }
            const data = await response.json();

            if (data.error) {
                console.error("Error fetching budget planning data from backend:", data.error);
                if (budgetPlanningTableBody) budgetPlanningTableBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger p-3">Error loading budget data: ${data.error}</td></tr>`;
                return;
            }

            currentBudgetYear = data.selected_year.toString();
            currentBudgetMonth = data.selected_month.toString();

            if (budgetPeriodDisplay) budgetPeriodDisplay.textContent = `${data.selected_month_name} ${data.selected_year}`;
            if (hiddenBudgetYearInput) hiddenBudgetYearInput.value = data.selected_year;
            if (hiddenBudgetMonthInput) hiddenBudgetMonthInput.value = data.selected_month;
            updateSaveButtonText(data.selected_year, data.selected_month - 1); // monthNames is 0-indexed

            if (budgetPlanningTableBody) {
                budgetPlanningTableBody.innerHTML = ''; 
                const goals = data.budget_goals_for_planning_ui || [];
                if (goals.length === 0) {
                    budgetPlanningTableBody.innerHTML = '<tr><td colspan="3" class="text-center">No categories found for budgeting. Add categories first.</td></tr>';
                } else {
                    goals.forEach(mainCat => {
                        let mainRowHtml = `
                            <tr class="budget-category-header">
                                <td colspan="2">${mainCat.name}</td>
                                <td class="text-end">`;
                        if (!mainCat.has_sub_categories) {
                            mainRowHtml += `
                                <input type="hidden" name="budget_category_id" value="${mainCat.id}">
                                <input type="number" step="0.01" name="budgeted_amount" class="form-control form-control-sm budget-input" 
                                       value="${(mainCat.budgeted_amount != null && mainCat.budgeted_amount > 0) ? parseFloat(mainCat.budgeted_amount).toFixed(2) : ''}" 
                                       placeholder="0.00">`;
                        } else {
                            mainRowHtml += `<span class="text-muted fst-italic">$${parseFloat(mainCat.budgeted_amount != null ? mainCat.budgeted_amount : 0.0).toFixed(2)}</span>`;
                        }
                        mainRowHtml += `</td></tr>`;
                        budgetPlanningTableBody.insertAdjacentHTML('beforeend', mainRowHtml);

                        if (mainCat.has_sub_categories && mainCat.sub_categories) {
                            mainCat.sub_categories.forEach(subCat => {
                                const typeBadgeClass = subCat.financial_goal_type === 'Need' ? 'primary' : 
                                                       subCat.financial_goal_type === 'Want' ? 'warning' :
                                                       subCat.financial_goal_type === 'Saving' ? 'success' : 'secondary';
                                const typeName = subCat.financial_goal_type || 'N/A';
                                let subRowHtml = `
                                    <tr class="budget-subcategory-row">
                                        <td style="padding-left: 2rem !important;">${subCat.name}</td>
                                        <td>
                                             <input type="hidden" name="budget_category_id" value="${subCat.id}">
                                             <span class="badge bg-${typeBadgeClass} text-dark">${typeName}</span>
                                        </td>
                                        <td class="text-end">
                                            <input type="number" step="0.01" name="budgeted_amount" class="form-control form-control-sm budget-input" 
                                                   value="${(subCat.budgeted_amount != null && subCat.budgeted_amount > 0) ? parseFloat(subCat.budgeted_amount).toFixed(2) : ''}" 
                                                   placeholder="0.00">
                                        </td>
                                    </tr>`;
                                budgetPlanningTableBody.insertAdjacentHTML('beforeend', subRowHtml);
                            });
                        }
                    });
                }
                attachBudgetInputListeners(); 
                isBudgetFormDirty = false; 
            }
            
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('budget_year', year);
            currentUrl.searchParams.set('budget_month', month);
            currentUrl.searchParams.set('open_budget_planner', 'true'); 
            window.history.pushState({path:currentUrl.toString()}, '', currentUrl.toString());

        } catch (error) {
            console.error("Failed to fetch or update budget planner:", error);
            if (budgetPlanningTableBody) budgetPlanningTableBody.innerHTML = '<tr><td colspan="3" class="text-center text-danger p-3">Failed to load budget data. Check console.</td></tr>';
        }
    }

    function handleBudgetPeriodChangeForAjax() {
        if (budgetMonthSelectModal && budgetYearSelectModal) {
            const selectedMonth = budgetMonthSelectModal.value;
            const selectedYear = budgetYearSelectModal.value;
            if (selectedYear !== currentBudgetYear || selectedMonth !== currentBudgetMonth) {
                fetchAndUpdateBudgetPlanner(selectedYear, selectedMonth);
            }
        }
    }

    if (budgetMonthSelectModal) {
        budgetMonthSelectModal.addEventListener('change', handleBudgetPeriodChangeForAjax);
    }
    if (budgetYearSelectModal) {
        budgetYearSelectModal.addEventListener('change', handleBudgetPeriodChangeForAjax);
    }
    attachBudgetInputListeners(); 
});
