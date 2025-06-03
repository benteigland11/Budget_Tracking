/**
 * Manages the goal scroller on the dashboard, including population,
 * animation, and click interactions.
 */
class GoalScroller {
    constructor(scrollerContentSelector, scrollerContainerSelector, initialGoals, apiService, modalManager) {
        this.scrollerContentEl = document.querySelector(scrollerContentSelector);
        this.scrollerContainerEl = document.querySelector(scrollerContainerSelector);
        this.apiService = apiService;
        this.modalManager = modalManager;

        if (!this.scrollerContentEl || !this.scrollerContainerEl) {
            console.error("Scroller content or container element not found.");
            return;
        }

        this.populateScroller(initialGoals || []);
        this._attachEventListeners();
    }

    // Add escapeHtml to prevent XSS
    escapeHtml(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    _formatCurrency(amount) {
        if (amount === null || typeof amount === 'undefined') amount = 0;
        if (typeof amount !== 'number') amount = parseFloat(amount) || 0;
        return '$' + amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    renderScrollerItem(goalData) {
        const progressPercentage = Math.min(100, Math.max(0, parseFloat(goalData.progress) || 0));
        // Escape goal name to prevent XSS
        const escapedName = this.escapeHtml(goalData.name);
        return `
            <div class="goal-scroller-item" data-goal-id="${goalData.id}" title="View/Manage: ${escapedName}">
                <span class="goal-name">${escapedName}</span>
                <span class="goal-progress-text">${this._formatCurrency(goalData.current_amount)} / ${this._formatCurrency(goalData.target_amount)}</span>
                <div class="goal-mini-progress" title="${progressPercentage.toFixed(1)}% Complete">
                    <div class="goal-mini-progress-bar" style="width: ${progressPercentage}%;"></div>
                </div>
            </div>`;
    }

    populateScroller(goals) {
        if (!this.scrollerContentEl || !this.scrollerContainerEl) return;

        this.scrollerContentEl.classList.remove('is-animating');
        this.scrollerContentEl.style.animation = 'none';
        this.scrollerContentEl.offsetHeight;
        this.scrollerContentEl.innerHTML = '';

        const activeGoals = goals.filter(goal => !goal.is_completed);

        if (!activeGoals || activeGoals.length === 0) {
            this.scrollerContentEl.innerHTML = '<div class="goal-scroller-item" style="border-right: none;"><span class="goal-name text-muted">No active goals.</span></div>';
            this.scrollerContentEl.style.justifyContent = 'center';
            return;
        }
        this.scrollerContentEl.style.justifyContent = 'flex-start';

        let originalItemsHTML = '';
        activeGoals.forEach(goal => {
            originalItemsHTML += this.renderScrollerItem(goal);
        });

        this.scrollerContentEl.innerHTML = originalItemsHTML;

        requestAnimationFrame(() => {
            const singleSetWidth = this.scrollerContentEl.scrollWidth;
            const containerWidth = this.scrollerContainerEl.offsetWidth;
            this.scrollerContentEl.style.transform = '';

            if (singleSetWidth > containerWidth) {
                this.scrollerContentEl.innerHTML = originalItemsHTML + originalItemsHTML;
                const desiredSpeedPxPerSec = 40;
                const animationDuration = singleSetWidth / desiredSpeedPxPerSec;
                this.scrollerContentEl.style.animationDuration = Math.max(15, animationDuration) + 's';
                this.scrollerContentEl.classList.add('is-animating');
            } else {
                const lastItem = this.scrollerContentEl.querySelector('.goal-scroller-item:last-child');
                if (lastItem) lastItem.style.borderRight = 'none';
                this.scrollerContentEl.classList.remove('is-animating');
            }
        });
    }

    async refresh() {
        try {
            const data = await this.apiService.fetchAllGoals();
            if (data && data.goals) {
                this.populateScroller(data.goals);
            }
        } catch (error) {
            console.error("Error refreshing scroller goals:", error);
            if (this.scrollerContentEl) this.scrollerContentEl.innerHTML = '<div class="goal-scroller-item" style="border-right: none;"><span class="goal-name text-danger">Error refreshing.</span></div>';
        }
    }

    _handleItemClick(event) {
        const clickedItem = event.target.closest('.goal-scroller-item');
        if (clickedItem && clickedItem.dataset.goalId) {
            const goalId = clickedItem.dataset.goalId;
            this.apiService.fetchGoalDetails(goalId)
                .then(data => {
                    if (data.goal && this.modalManager) {
                        this.modalManager.showModalWithGoal(data.goal);
                    } else if (!data.goal) {
                        console.warn('Goal not found for scroller click:', goalId);
                        if(this.modalManager && typeof this.modalManager.displayAlert === 'function') {
                            this.modalManager.displayAlert('Goal details not found.', 'warning');
                        }
                    }
                })
                .catch(error => {
                    console.error('Error fetching goal details from scroller click:', error);
                    if(this.modalManager && typeof this.modalManager.displayAlert === 'function') {
                        this.modalManager.displayAlert('Could not load goal details.', 'danger');
                    }
                });
        }
    }

    _attachEventListeners() {
        if (this.scrollerContentEl) {
            this.scrollerContentEl.addEventListener('click', (event) => this._handleItemClick(event));
        }
    }
}