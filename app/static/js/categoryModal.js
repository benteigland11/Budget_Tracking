// app/static/js/categoryModal.js

// Assumes hierarchicalDataFromFlask is available globally from index.html
// Assumes flask_urls.save_all_category_changes is available globally

document.addEventListener('DOMContentLoaded', () => {
    // This function will be called when the manageCategoriesModal is shown
    // It's attached in dashboardSetup.js or directly if this script is loaded after DOM is ready
    // and manageCategoriesModalEl is available.
    window.initializeManageCategoriesModal = function() {
        console.log("Initializing Manage Categories Modal JS...");
        window.pendingNewMainCategories = [];
        window.pendingNewSubCategories = [];
        window.pendingDeletions = []; 
        window.tempCategoryIdCounter = 0;
        
        const alertContainer = document.getElementById('category-modal-alerts');
        if(alertContainer) alertContainer.innerHTML = '';

        const parentSelect = document.getElementById('newSubCategoryParentSelect');
        if (parentSelect && typeof hierarchicalDataFromFlask !== 'undefined') {
            parentSelect.innerHTML = '<option value="" disabled selected>Select parent...</option>';
            const mainCategoriesForSubAdd = hierarchicalDataFromFlask.main_categories || [];
            mainCategoriesForSubAdd.forEach(mc => {
                const option = document.createElement('option');
                option.value = mc.id; 
                option.textContent = mc.name;
                parentSelect.appendChild(option);
            });
        }

        const clientAddMainBtn = document.getElementById('clientAddMainCategoryBtn');
        const clientAddSubBtn = document.getElementById('clientAddSubCategoryBtn');
        const saveAllBtn = document.getElementById('saveAllCategoryChangesBtn');

        if (clientAddMainBtn) {
            clientAddMainBtn.removeEventListener('click', clientSideAddMainCategory); 
            clientAddMainBtn.addEventListener('click', clientSideAddMainCategory);
        }
        if (clientAddSubBtn) {
            clientAddSubBtn.removeEventListener('click', clientSideAddSubCategory);
            clientAddSubBtn.addEventListener('click', clientSideAddSubCategory);
        }
        if (saveAllBtn) {
            saveAllBtn.removeEventListener('click', saveAllCategoryChanges);
            saveAllBtn.addEventListener('click', saveAllCategoryChanges);
        }

        document.querySelectorAll('.delete-existing-category-btn').forEach(button => {
            const newButton = button.cloneNode(true); // Clone to remove old listeners
            button.parentNode.replaceChild(newButton, button);
            newButton.addEventListener('click', handleMarkExistingForDeletion);
        });
        
        // Restore visual state for items not in pendingDeletions
        document.querySelectorAll('#categoryListContainer .list-group-item[data-category-id]').forEach(li => {
            if (!li.dataset.isPending || li.dataset.isPending === "false") { 
                const catId = li.dataset.categoryId;
                if (!window.pendingDeletions.includes(parseInt(catId))) { 
                     li.classList.remove('marked-for-deletion');
                     const actionContainer = li.querySelector('.action-buttons-container');
                     if (actionContainer && !actionContainer.querySelector('.delete-existing-category-btn')) {
                        const originalDeleteButton = document.createElement('button');
                        originalDeleteButton.type = 'button';
                        originalDeleteButton.className = 'btn btn-sm delete-existing-category-btn';
                        originalDeleteButton.dataset.categoryId = catId;
                        originalDeleteButton.dataset.categoryName = li.dataset.categoryName;
                        originalDeleteButton.innerHTML = '&times;';
                        if (li.classList.contains('main-category-item')) {
                            originalDeleteButton.classList.add('btn-danger');
                            originalDeleteButton.title = `Mark to delete main category ${li.dataset.categoryName}`;
                        } else {
                            originalDeleteButton.classList.add('btn-outline-danger');
                            originalDeleteButton.title = `Mark to delete subcategory ${li.dataset.categoryName}`;
                        }
                        actionContainer.innerHTML = ''; 
                        if (li.classList.contains('sub-category-item')) { 
                            const financialSelect = document.createElement('select');
                            financialSelect.name = `financial_goal_type_${catId}`;
                            financialSelect.className = 'form-select form-select-sm financial-type-select me-2 existing-financial-type-select';
                            const currentFGType = li.querySelector('.existing-financial-type-select')?.value || "";
                            financialSelect.innerHTML = `
                                <option value="" ${currentFGType === "" ? "selected" : ""}>Unset</option>
                                <option value="Need" ${currentFGType === "Need" ? "selected" : ""}>Need</option>
                                <option value="Want" ${currentFGType === "Want" ? "selected" : ""}>Want</option>
                                <option value="Saving" ${currentFGType === "Saving" ? "selected" : ""}>Saving</option>
                            `;
                            actionContainer.appendChild(financialSelect);
                        }
                        actionContainer.appendChild(originalDeleteButton);
                        originalDeleteButton.addEventListener('click', handleMarkExistingForDeletion);
                     }
                     const finSelect = li.querySelector('.existing-financial-type-select');
                     if (finSelect) finSelect.disabled = false;
                } else { // Is in pendingDeletions
                    li.classList.add('marked-for-deletion');
                    const finSelect = li.querySelector('.existing-financial-type-select');
                    if (finSelect) finSelect.disabled = true;
                    const actionContainer = li.querySelector('.action-buttons-container');
                    if(actionContainer && !actionContainer.querySelector('.undo-delete-btn')) {
                        actionContainer.innerHTML = `<button type="button" class="btn btn-warning btn-sm undo-delete-btn" data-category-id="${catId}">Undo</button>`;
                        actionContainer.querySelector('.undo-delete-btn').addEventListener('click', handleUndoMarkForDeletion);
                    }
                }
            }
        });
        console.log("Manage Categories Modal JS Initialized and listeners attached.");
    }
    
    function handleMarkExistingForDeletion(event) {
        const button = event.currentTarget;
        const categoryId = parseInt(button.dataset.categoryId);
        const categoryName = button.dataset.categoryName;
        const listItem = button.closest('li');

        if (confirm(`Mark "${categoryName}" for deletion? This will be permanent when you save all changes.`)) {
            if (!window.pendingDeletions.includes(categoryId)) {
                window.pendingDeletions.push(categoryId);
            }
            listItem.classList.add('marked-for-deletion');
            const financialSelect = listItem.querySelector('.existing-financial-type-select');
            if (financialSelect) financialSelect.disabled = true;

            const actionContainer = listItem.querySelector('.action-buttons-container');
            actionContainer.innerHTML = `<button type="button" class="btn btn-warning btn-sm undo-delete-btn" data-category-id="${categoryId}">Undo</button>`;
            actionContainer.querySelector('.undo-delete-btn').addEventListener('click', handleUndoMarkForDeletion);
        }
    }

    function handleUndoMarkForDeletion(event) {
        const button = event.currentTarget;
        const categoryId = parseInt(button.dataset.categoryId);
        const listItem = button.closest('li');

        window.pendingDeletions = window.pendingDeletions.filter(id => id !== categoryId);
        listItem.classList.remove('marked-for-deletion');
        const financialSelect = listItem.querySelector('.existing-financial-type-select');
        if (financialSelect) financialSelect.disabled = false;
        
        const actionContainer = listItem.querySelector('.action-buttons-container');
        const originalDeleteButton = document.createElement('button');
        originalDeleteButton.type = 'button';
        originalDeleteButton.dataset.categoryId = categoryId;
        originalDeleteButton.dataset.categoryName = listItem.dataset.categoryName;
        originalDeleteButton.innerHTML = '&times;';

        if (listItem.classList.contains('main-category-item')) {
            originalDeleteButton.className = 'btn btn-danger btn-sm delete-existing-category-btn';
            originalDeleteButton.title = `Mark to delete main category ${listItem.dataset.categoryName}`;
        } else {
            originalDeleteButton.className = 'btn btn-outline-danger btn-sm delete-existing-category-btn';
            originalDeleteButton.title = `Mark to delete subcategory ${listItem.dataset.categoryName}`;
        }
        
        actionContainer.innerHTML = ''; 
        if (listItem.classList.contains('sub-category-item')) { 
            const currentSelectValue = financialSelect ? financialSelect.value : ""; 
            const newFinancialSelect = document.createElement('select');
            newFinancialSelect.name = `financial_goal_type_${categoryId}`;
            newFinancialSelect.className = 'form-select form-select-sm financial-type-select me-2 existing-financial-type-select';
            newFinancialSelect.innerHTML = `
                <option value="" ${currentSelectValue === "" ? "selected" : ""}>Unset</option>
                <option value="Need" ${currentSelectValue === "Need" ? "selected" : ""}>Need</option>
                <option value="Want" ${currentSelectValue === "Want" ? "selected" : ""}>Want</option>
                <option value="Saving" ${currentSelectValue === "Saving" ? "selected" : ""}>Saving</option>
            `;
            actionContainer.appendChild(newFinancialSelect);
        }
        actionContainer.appendChild(originalDeleteButton);
        originalDeleteButton.addEventListener('click', handleMarkExistingForDeletion);
    }
    
    function clientSideAddMainCategory() { 
        const nameInput = document.getElementById('newMainCategoryNameInput');
        const name = nameInput.value.trim();
        if (!name) { displayCategoryModalAlert('Main category name cannot be empty.', 'warning'); return; }
        if (window.pendingNewMainCategories.some(cat => cat.name.toLowerCase() === name.toLowerCase()) || 
            Array.from(document.querySelectorAll('#mainCategoryListUl > .main-category-item')).some(item => item.dataset.categoryName && item.dataset.categoryName.toLowerCase() === name.toLowerCase() && !item.dataset.tempId && !item.classList.contains('marked-for-deletion')) ) {
            displayCategoryModalAlert('Main category name already exists or is pending.', 'warning'); return;
        }
        const tempId = `temp_main_${window.tempCategoryIdCounter++}`;
        window.pendingNewMainCategories.push({ temp_id: tempId, name: name });
        const mainListUl = document.getElementById('mainCategoryListUl') || createMainCategoryListUl();
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item main-category-item d-flex justify-content-between align-items-center pending-category';
        listItem.dataset.tempId = tempId; listItem.dataset.categoryName = name; listItem.dataset.isPending = "true";
        listItem.innerHTML = `<span>${name} (New)</span><div class="d-flex align-items-center action-buttons-container"><button type="button" class="btn btn-outline-warning btn-sm pending-delete-btn" data-temp-id="${tempId}" data-type="main">&times; Remove</button></div>`;
        mainListUl.appendChild(listItem);
        attachPendingDeleteListener(listItem.querySelector('.pending-delete-btn'));
        const parentSelect = document.getElementById('newSubCategoryParentSelect');
        if (parentSelect) {
            const option = document.createElement('option'); option.value = tempId; option.textContent = name + " (New)"; parentSelect.appendChild(option);
        }
        nameInput.value = ''; document.getElementById('noCategoriesDefinedMsg')?.remove();
        clearCategoryModalAlerts();
    }
    function clientSideAddSubCategory() { 
        const nameInput = document.getElementById('newSubCategoryNameInput');
        const parentSelect = document.getElementById('newSubCategoryParentSelect');
        const name = nameInput.value.trim();
        const parentIdOrTempId = parentSelect.value;
        const parentName = parentSelect.options[parentSelect.selectedIndex]?.textContent.replace(" (New)","") || "Unknown Parent";
        if (!name) { displayCategoryModalAlert('Subcategory name cannot be empty.', 'warning'); return; }
        if (!parentIdOrTempId) { displayCategoryModalAlert('Parent category must be selected.', 'warning'); return; }
        const tempId = `temp_sub_${window.tempCategoryIdCounter++}`;
        
        let parentLi = document.querySelector(`#mainCategoryListUl > .main-category-item[data-category-id="${parentIdOrTempId}"]`) || document.querySelector(`#mainCategoryListUl > .main-category-item[data-temp-id="${parentIdOrTempId}"]`);
        if (!parentLi) { displayCategoryModalAlert('Parent category element not found in list.', 'danger'); return; }
        let subListUl = parentLi.nextElementSibling;
        if (!subListUl || !subListUl.matches('ul.list-group-flush')) {
            subListUl = document.createElement('ul'); subListUl.className = 'list-group list-group-flush ms-3'; 
            subListUl.dataset.parentIdOrTempId = parentIdOrTempId; parentLi.insertAdjacentElement('afterend', subListUl);
        }
        if (Array.from(subListUl.children).some(item => item.dataset.categoryName && item.dataset.categoryName.toLowerCase() === name.toLowerCase() && !item.classList.contains('marked-for-deletion'))) {
            displayCategoryModalAlert(`Subcategory "${name}" already exists or is pending under "${parentName}".`, 'warning'); return;
        }
        window.pendingNewSubCategories.push({ temp_id: tempId, name: name, parent_id_or_temp_id: parentIdOrTempId, parent_name_for_display: parentName });
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item sub-category-item d-flex justify-content-between align-items-center pending-category';
        listItem.dataset.tempId = tempId; listItem.dataset.categoryName = name; listItem.dataset.isPending = "true";
        listItem.innerHTML = `<small>${name} (New)</small><div class="d-flex align-items-center action-buttons-container"><select name="financial_goal_type_${tempId}" class="form-select form-select-sm financial-type-select me-2 pending-financial-type-select"><option value="" selected>Unset</option><option value="Need">Need</option><option value="Want">Want</option><option value="Saving">Saving</option></select><button type="button" class="btn btn-outline-warning btn-sm pending-delete-btn" data-temp-id="${tempId}" data-type="sub">&times; Remove</button></div>`;
        subListUl.appendChild(listItem);
        attachPendingDeleteListener(listItem.querySelector('.pending-delete-btn'));
        nameInput.value = ''; parentSelect.value = '';
        clearCategoryModalAlerts();
    }
    function attachPendingDeleteListener(button) { 
        button.addEventListener('click', function() {
            const tempId = this.dataset.tempId; const type = this.dataset.type;
            if (type === 'main') {
                window.pendingNewMainCategories = window.pendingNewMainCategories.filter(cat => cat.temp_id !== tempId);
                window.pendingNewSubCategories = window.pendingNewSubCategories.filter(sub => sub.parent_id_or_temp_id !== tempId);
                const parentSelect = document.getElementById('newSubCategoryParentSelect');
                if(parentSelect){ const optToRemove = parentSelect.querySelector(`option[value="${tempId}"]`); if(optToRemove) optToRemove.remove(); }
                const mainLi = document.querySelector(`.main-category-item[data-temp-id="${tempId}"]`);
                const subUl = mainLi?.nextElementSibling;
                if (subUl && subUl.matches('ul') && subUl.dataset.parentIdOrTempId === tempId) { subUl.remove(); }
            } else if (type === 'sub') {
                window.pendingNewSubCategories = window.pendingNewSubCategories.filter(cat => cat.temp_id !== tempId);
            }
            this.closest('li').remove();
        });
    }
    function createMainCategoryListUl() { 
        const container = document.getElementById('categoryListContainer');
        document.getElementById('noCategoriesDefinedMsg')?.remove();
        const ul = document.createElement('ul'); ul.className = 'list-group'; ul.id = 'mainCategoryListUl';
        container.appendChild(ul); return ul;
    }
    
    function displayCategoryModalAlert(message, type = 'danger') {
        const alertContainer = document.getElementById('category-modal-alerts');
        if (alertContainer) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
            alertDiv.role = 'alert';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            alertContainer.innerHTML = ''; 
            alertContainer.appendChild(alertDiv);
        } else {
            alert(message); 
        }
    }
    function clearCategoryModalAlerts() {
        const alertContainer = document.getElementById('category-modal-alerts');
        if (alertContainer) alertContainer.innerHTML = '';
    }

    async function saveAllCategoryChanges() { 
        clearCategoryModalAlerts();
        const financialTypeUpdates = [];
        document.querySelectorAll('.existing-financial-type-select').forEach(select => {
            const listItem = select.closest('li');
            if (listItem && !listItem.classList.contains('marked-for-deletion')) {
                const categoryId = select.name.replace('financial_goal_type_', '');
                financialTypeUpdates.push({ id: categoryId, type: select.value });
            }
        });
        const pendingSubsWithTypes = window.pendingNewSubCategories.map(sub => {
            const selectElement = document.querySelector(`select[name="financial_goal_type_${sub.temp_id}"]`);
            return { temp_id: sub.temp_id, name: sub.name, parent_id_or_temp_id: sub.parent_id_or_temp_id, financial_goal_type: selectElement ? selectElement.value : "" };
        });
        const payload = {
            financial_type_updates: financialTypeUpdates,
            new_main_categories: window.pendingNewMainCategories.map(m => ({ name: m.name, temp_id: m.temp_id })), 
            new_sub_categories: pendingSubsWithTypes,
            deletions: window.pendingDeletions 
        };
        try {
            // Assumes flask_urls.save_all_category_changes is defined globally
            if (!window.flask_urls || !window.flask_urls.save_all_category_changes) {
                console.error("Flask URL for save_all_category_changes not defined.");
                displayCategoryModalAlert("Configuration error saving categories.", "danger");
                return;
            }
            const response = await fetch(window.flask_urls.save_all_category_changes, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (response.ok && result.status === 'success') {
                const manageCategoriesModalInstance = bootstrap.Modal.getInstance(document.getElementById('manageCategoriesModal'));
                if(manageCategoriesModalInstance) manageCategoriesModalInstance.hide();
                setTimeout(() => { window.location.reload(); }, 100); 
            } else { 
                displayCategoryModalAlert(result.message || 'Could not save changes. Please check data and try again.', 'danger');
            }
        } catch (error) { 
            console.error('Error saving category changes:', error); 
            displayCategoryModalAlert('An unexpected network error occurred while saving. Check console.', 'danger');
        }
    }
    
    // Ensure this is attached correctly if the element exists
    const manageCategoriesModalElGlobal = document.getElementById('manageCategoriesModal');
    if (manageCategoriesModalElGlobal && window.categoriesModalInstance) { 
        // Event listener 'shown.bs.modal' is already added when categoriesModalInstance is created.
    } else if (manageCategoriesModalElGlobal && !window.categoriesModalInstance) {
        // Fallback if instance wasn't created but element exists (should be rare)
        window.categoriesModalInstance = new bootstrap.Modal(manageCategoriesModalElGlobal);
        manageCategoriesModalElGlobal.addEventListener('shown.bs.modal', initializeManageCategoriesModal);
    }
});
</script>
{% endblock %}
