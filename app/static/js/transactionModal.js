// app/static/js/transactionModal.js

// Assumes hierarchicalDataFromFlask is available globally from index.html
// Assumes view_year, view_month, view_period_type are available globally from index.html for defaults

document.addEventListener('DOMContentLoaded', () => {
    console.log("Transaction Modal JS Loaded");

    const addTransactionModalEl = document.getElementById('addTransactionModal');
    const transactionForm = document.getElementById('transactionFormInModal'); 
    const modalTransactionTitle = document.getElementById('addTransactionModalLabel');
    const modalAmountInput = document.getElementById('modal_amount');
    const modalDateInput = document.getElementById('modal_date');
    const modalTypeSelect = document.getElementById('modal_type');
    const mainCategorySelectForTransaction = document.getElementById('modal_main_category_select');
    const subCategorySelectForTransaction = document.getElementById('modal_sub_category_select');
    const subCategoryWrapperForTransaction = document.getElementById('modal_subcategory_wrapper');
    const finalCategoryIdInputForTransaction = document.getElementById('final_category_id');
    const transactionIdEditInput = document.getElementById('transaction_id_edit');

    // Make sure Flask-provided default view variables are accessible
    // These would be set in a <script> tag in index.html before this file is loaded
    // e.g., <script>
    //          var defaultViewYear = {{ view_year|tojson }};
    //          var defaultViewMonth = {{ view_month|tojson }}; // Could be null
    //          var defaultViewPeriodType = {{ view_period_type|tojson }};
    //       </script>
    // For simplicity, using the global `flaskVariables` object we'll define in index.html
    const flaskViewYear = window.flaskVariables ? window.flaskVariables.view_year : new Date().getFullYear();
    const flaskViewMonth = window.flaskVariables ? window.flaskVariables.view_month : new Date().getMonth() + 1;
    const flaskViewPeriodType = window.flaskVariables ? window.flaskVariables.view_period_type : 'monthly';


    function resetTransactionForm() {
        if (transactionForm) transactionForm.reset(); 
        if (transactionIdEditInput) transactionIdEditInput.value = ''; 
        if (modalTransactionTitle) modalTransactionTitle.textContent = 'Add New Transaction';
        const saveBtnInFooter = document.querySelector('#addTransactionModal .modal-footer button[type="submit"]');
        if (saveBtnInFooter) saveBtnInFooter.textContent = 'Save Transaction';

        if (transactionForm) {
            const currentUrlParamsForTx = new URLSearchParams(window.location.search);
            let actionUrl = transactionForm.dataset.addActionUrl; // Get base URL from data attribute
            
            const paramsForTxRedirect = new URLSearchParams();
            paramsForTxRedirect.append('year', currentUrlParamsForTx.get('year') || flaskViewYear);
            let monthForRedirect = currentUrlParamsForTx.get('month');
            if (!monthForRedirect && flaskViewMonth !== null) { // Ensure flaskViewMonth is not None
                 monthForRedirect = flaskViewMonth;
            }
            if (monthForRedirect) paramsForTxRedirect.append('month', monthForRedirect);

            paramsForTxRedirect.append('period_type', currentUrlParamsForTx.get('period_type') || flaskViewPeriodType);
            if (currentUrlParamsForTx.get('main_cat_focus')) {
                paramsForTxRedirect.append('main_cat_focus', currentUrlParamsForTx.get('main_cat_focus'));
            }
            transactionForm.action = actionUrl + '?' + paramsForTxRedirect.toString();
        }
        if (mainCategorySelectForTransaction) mainCategorySelectForTransaction.value = "";
        if (subCategorySelectForTransaction) subCategorySelectForTransaction.innerHTML = '<option value="">-- Select subcategory (optional) --</option>';
        if (subCategoryWrapperForTransaction) subCategoryWrapperForTransaction.style.display = 'none';
        if (finalCategoryIdInputForTransaction) finalCategoryIdInputForTransaction.value = "";
        if (modalDateInput) {
            const today = new Date();
            modalDateInput.value = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');
        }
        if(modalTypeSelect) modalTypeSelect.value = 'expense';
    } 

    if (mainCategorySelectForTransaction && typeof hierarchicalDataFromFlask !== 'undefined') {
        const mainCategoriesForTxModal = hierarchicalDataFromFlask.main_categories || [];
        mainCategorySelectForTransaction.innerHTML = '<option value="" disabled selected>Select main category...</option>';
        mainCategoriesForTxModal.forEach(mainCat => {
            const option = document.createElement('option');
            option.value = mainCat.id;
            option.textContent = mainCat.name;
            mainCategorySelectForTransaction.appendChild(option);
        });

        mainCategorySelectForTransaction.addEventListener('change', function() {
            if (finalCategoryIdInputForTransaction) finalCategoryIdInputForTransaction.value = this.value; 
            populateSubcategoriesForTransaction(this.value);
            if (subCategorySelectForTransaction) subCategorySelectForTransaction.value = ""; 
        });
    } 
    
    function populateSubcategoriesForTransaction(selectedMainId, selectedSubId = null) {
        if (!subCategorySelectForTransaction || !subCategoryWrapperForTransaction || typeof hierarchicalDataFromFlask === 'undefined') return;
        const subCategoriesMapForTxModal = hierarchicalDataFromFlask.sub_categories_map || {};
        subCategorySelectForTransaction.innerHTML = '<option value="">-- Select subcategory (optional) --</option>';
        const subs = subCategoriesMapForTxModal[selectedMainId] || [];

        if (subs.length > 0) {
            subs.forEach(subCat => {
                const option = document.createElement('option');
                option.value = subCat.id;
                option.textContent = subCat.name;
                if (selectedSubId && subCat.id.toString() === selectedSubId.toString()) {
                    option.selected = true;
                }
                subCategorySelectForTransaction.appendChild(option);
            });
            subCategoryWrapperForTransaction.style.display = 'block';
        } else {
            subCategoryWrapperForTransaction.style.display = 'none';
        }
    }
    
    if (subCategorySelectForTransaction) { 
        subCategorySelectForTransaction.addEventListener('change', function() {
            if (this.value && finalCategoryIdInputForTransaction) { 
                finalCategoryIdInputForTransaction.value = this.value; 
            } else if (mainCategorySelectForTransaction && finalCategoryIdInputForTransaction) { 
                finalCategoryIdInputForTransaction.value = mainCategorySelectForTransaction.value; 
            }
        });
    } 
    
    document.getElementById('openAddTransactionModalBtn')?.addEventListener('click', function() { 
        if (transactionForm) { // Set data attribute for add action URL
            transactionForm.dataset.addActionUrl = this.dataset.addActionUrl; // Assuming button has this
        }
        resetTransactionForm(); 
    });
    
    document.querySelectorAll('.edit-btn').forEach(button => { 
        button.addEventListener('click', function() {
            if (transactionForm) { // Set data attribute for update action URL
                 transactionForm.dataset.updateActionUrlBase = this.dataset.updateActionUrlBase; // Assuming button has this
            }
            resetTransactionForm(); 
            const transactionId = this.dataset.id;
            if (modalTransactionTitle) modalTransactionTitle.textContent = 'Edit Transaction';
            const saveBtnInFooter = document.querySelector('#addTransactionModal .modal-footer button[type="submit"]');
            if (saveBtnInFooter) saveBtnInFooter.textContent = 'Save Changes';
            
            if (transactionForm) {
                const currentUrlParamsForTx = new URLSearchParams(window.location.search);
                let actionUrl = transactionForm.dataset.updateActionUrlBase.replace('0', transactionId); // Replace placeholder 0
                
                const paramsForTxRedirect = new URLSearchParams();
                paramsForTxRedirect.append('year', currentUrlParamsForTx.get('year') || flaskViewYear);
                let monthForRedirect = currentUrlParamsForTx.get('month');
                if (!monthForRedirect && flaskViewMonth !== null) {
                     monthForRedirect = flaskViewMonth;
                }
                if (monthForRedirect) paramsForTxRedirect.append('month', monthForRedirect);

                paramsForTxRedirect.append('period_type', currentUrlParamsForTx.get('period_type') || flaskViewPeriodType);
                if (currentUrlParamsForTx.get('main_cat_focus')) {
                    paramsForTxRedirect.append('main_cat_focus', currentUrlParamsForTx.get('main_cat_focus'));
                }
                transactionForm.action = actionUrl + '?' + paramsForTxRedirect.toString();
            }

            if (transactionIdEditInput) transactionIdEditInput.value = transactionId; 
            if (modalAmountInput) modalAmountInput.value = this.dataset.amount;
            if (modalDateInput) modalDateInput.value = this.dataset.date;
            if (modalTypeSelect) modalTypeSelect.value = this.dataset.type;
            
            const categoryId = this.dataset.category_id; 
            const mainCategoryForEdit = this.dataset.main_category_for_edit; 

            if (mainCategoryForEdit && mainCategorySelectForTransaction) { 
                mainCategorySelectForTransaction.value = mainCategoryForEdit;
                populateSubcategoriesForTransaction(mainCategoryForEdit, categoryId); 
                if(finalCategoryIdInputForTransaction) finalCategoryIdInputForTransaction.value = categoryId;
            } else if (categoryId && mainCategorySelectForTransaction) { 
                mainCategorySelectForTransaction.value = categoryId; 
                populateSubcategoriesForTransaction(categoryId); 
                if(finalCategoryIdInputForTransaction) finalCategoryIdInputForTransaction.value = categoryId;
            } else { 
                if(mainCategorySelectForTransaction) mainCategorySelectForTransaction.value = "";
                populateSubcategoriesForTransaction(""); 
                if(finalCategoryIdInputForTransaction) finalCategoryIdInputForTransaction.value = ""; 
            }
        });
    }); 
    
    if (addTransactionModalEl) {
        addTransactionModalEl.addEventListener('hidden.bs.modal', resetTransactionForm);
    }
});
