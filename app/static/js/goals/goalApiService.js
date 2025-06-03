// static/js/goals/goalApiService.js
/**
 * Provides functions for making API calls related to goals.
 */
class GoalApiService {
    constructor(flaskUrls) {
        this.flaskUrls = flaskUrls;
        if (!this.flaskUrls) {
            console.error("Flask URLs not provided to GoalApiService!");
        }
    }

    /**
     * Common fetch logic with error handling.
     * @param {string} url - The URL to fetch.
     * @param {object} options - Fetch options (method, body, headers).
     * @returns {Promise<object>} - The JSON response from the server.
     * @throws {Error} - If the network response is not ok.
     */
    async _fetch(url, options = {}) {
        if (!url) {
            console.error("URL is undefined in _fetch call.", options);
            throw new Error("API URL is not defined.");
        }
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    // If response is not JSON, use status text
                    errorData = { message: response.statusText || `HTTP error! Status: ${response.status}` };
                }
                console.error(`API Error (${response.status}):`, errorData);
                throw new Error(errorData.message || `Request failed with status ${response.status}`);
            }
            // Handle cases where response might be empty for 200/201/204
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return response.json();
            } else {
                return { status: 'success', message: 'Operation successful, no content returned.' }; // Or handle as per API design
            }
        } catch (error) {
            console.error('Fetch API Error:', error);
            throw error; // Re-throw to be caught by the caller
        }
    }

    async fetchAllGoals() {
        return this._fetch(this.flaskUrls.api_goals_list_url);
    }

    async fetchGoalDetails(goalId) {
        if (!this.flaskUrls.api_goal_details_url_template) {
            throw new Error("Goal details URL template not defined.");
        }
        const url = this.flaskUrls.api_goal_details_url_template.replace('GOAL_ID_PLACEHOLDER', goalId);
        return this._fetch(url);
    }

    /**
     * Creates a new goal.
     * @param {FormData|object} data - Form data or an object containing goal details.
     * If an object, it will be converted to URLSearchParams.
     */
    async createGoal(data) {
        const body = data instanceof FormData ? data : new URLSearchParams(data);
        return this._fetch(this.flaskUrls.api_goals_create_url, {
            method: 'POST',
            body: body
        });
    }

    /**
     * Updates an existing goal.
     * @param {string|number} goalId - The ID of the goal to update.
     * @param {FormData|object} data - Form data or an object containing goal details.
     */
    async updateGoal(goalId, data) {
        if (!this.flaskUrls.api_goals_update_url_base) {
            throw new Error("Goal update URL base not defined.");
        }
        const url = this.flaskUrls.api_goals_update_url_base + goalId;
        const body = data instanceof FormData ? data : new URLSearchParams(data);
        return this._fetch(url, {
            method: 'POST',
            body: body
        });
    }

    async deleteGoalApi(goalId) {
        if (!this.flaskUrls.api_goals_delete_url_base) {
            throw new Error("Goal delete URL base not defined.");
        }
        const url = this.flaskUrls.api_goals_delete_url_base + goalId;
        return this._fetch(url, { method: 'POST' });
    }

    /**
     * Contributes funds to a goal.
     * @param {string|number} goalId - The ID of the goal.
     * @param {FormData|object} data - Data for contribution (amount, date, description).
     */
    async contributeToGoalApi(goalId, data) {
        if (!this.flaskUrls.api_goals_contribute_url_base) {
            throw new Error("Goal contribution URL base not defined.");
        }
        const url = this.flaskUrls.api_goals_contribute_url_base + goalId;
        const body = data instanceof FormData ? data : new URLSearchParams(data);
        return this._fetch(url, {
            method: 'POST',
            body: body
        });
    }

    /**
     * Withdraws funds from a goal.
     * @param {string|number} goalId - The ID of the goal.
     * @param {FormData|object} data - Data for withdrawal (amount, date, description).
     */
    async withdrawFromGoalApi(goalId, data) {
        if (!this.flaskUrls.api_goals_withdraw_url_base) {
            throw new Error("Goal withdrawal URL base not defined.");
        }
        const url = this.flaskUrls.api_goals_withdraw_url_base + goalId;
        const body = data instanceof FormData ? data : new URLSearchParams(data);
        return this._fetch(url, {
            method: 'POST',
            body: body
        });
    }
}
