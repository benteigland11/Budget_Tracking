// app/static/js/dashboardSetup.js

// Ensure this script runs after the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log("Dashboard Setup JS Loaded");

    // Initialize Bootstrap Modal instances once
    const budgetModalEl = document.getElementById('budgetPlanningModal');
    window.budgetModalInstance = budgetModalEl ? new bootstrap.Modal(budgetModalEl) : null;

    const categoriesModalEl = document.getElementById('manageCategoriesModal');
    window.categoriesModalInstance = null; // Will be fully initialized by categoryModal.js
    if (categoriesModalEl) {
        // Basic instance for showing/hiding, specific event listeners in categoryModal.js
        window.categoriesModalInstance = new bootstrap.Modal(categoriesModalEl);
    }
    
    const addTransactionModalEl = document.getElementById('addTransactionModal');
    // Transaction modal instance is not strictly needed globally if only using data-bs-toggle
    // but its 'hidden.bs.modal' event is handled in transactionModal.js
    
    // --- Common Modal/Page Load Logic for URL parameters ---
    const urlParams = new URLSearchParams(window.location.search);
    let paramsModifiedForHistory = false;

    if (urlParams.get('open_budget_planner') === 'true') { 
        if (window.budgetModalInstance) {
            window.budgetModalInstance.show();
        }
        urlParams.delete('open_budget_planner');
        paramsModifiedForHistory = true;
    }
    if (urlParams.get('open_manage_categories') === 'true') {
        if (window.categoriesModalInstance) {
            // The 'shown.bs.modal' listener in categoryModal.js will handle its specific init
            window.categoriesModalInstance.show();
        }
        urlParams.delete('open_manage_categories');
        paramsModifiedForHistory = true;
    }
    
    if (paramsModifiedForHistory) {
        const newParamsString = urlParams.toString();
        const newRelativePathQuery = window.location.pathname + (newParamsString ? '?' + newParamsString : '');
        window.history.replaceState({}, document.title, newRelativePathQuery);
    }
});
