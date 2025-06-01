// app/static/js/charts.js

// Assumes flaskVariables (view_month, view_year, view_period_type, focused_main_category_id) are global
// Assumes initial chart data (initialExpectedVsActualData, nwsBudgetedChartData, nwsActualChartData) are global

document.addEventListener('DOMContentLoaded', () => {
    console.log("Charts JS Loaded");

    let expectedVsActualChartInstance = null; 
    const expectedVsActualCtx = document.getElementById('expectedVsActualChart')?.getContext('2d');
    const expectedVsActualChartTitleEl = document.getElementById('expectedVsActualChartTitle');
    const backToMainCategoriesChartBtn = document.getElementById('backToMainCategoriesChartBtn');

    function renderExpectedVsActualChart(chartData) {
        if (expectedVsActualCtx) {
            if (expectedVsActualChartInstance) { expectedVsActualChartInstance.destroy(); }
            if (chartData && chartData.labels && chartData.labels.length > 0) {
                expectedVsActualChartInstance = new Chart(expectedVsActualCtx, {
                    type: 'bar',
                    data: {
                        labels: chartData.labels,
                        datasets: [
                            { label: 'Budgeted ($)', data: chartData.budgeted_data, backgroundColor: 'rgba(54, 162, 235, 0.6)', borderColor: 'rgba(54, 162, 235, 1)', borderWidth: 1 },
                            { label: 'Actual ($)', data: chartData.actual_data, backgroundColor: 'rgba(255, 99, 132, 0.6)', borderColor: 'rgba(255, 99, 132, 1)', borderWidth: 1 }
                        ]
                    },
                    options: { 
                        responsive: true, maintainAspectRatio: false, 
                        scales: { y: { beginAtZero: true, ticks: { callback: function(value) { return '$' + value; }} } }, 
                        plugins: { 
                            legend: { position: 'top' },
                            tooltip: { callbacks: { label: function(context) { let label = context.dataset.label || ''; if (label) { label += ': '; } if (context.parsed.y !== null) { label += new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(context.parsed.y); } return label;}}}
                        },
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const chartElement = elements[0];
                                const index = chartElement.index;
                                const categoryIdForDrilldown = chartData.category_ids_for_drilldown[index];
                                if (categoryIdForDrilldown) { 
                                    const currentUrl = new URL(window.location.href);
                                    currentUrl.searchParams.set('main_cat_focus', categoryIdForDrilldown);
                                    // Preserve other analytics params from current URL
                                    const params = new URLSearchParams(window.location.search);
                                    if(params.get('month')) currentUrl.searchParams.set('month', params.get('month'));
                                    else if (window.flaskVariables && window.flaskVariables.view_month !== null) currentUrl.searchParams.set('month', window.flaskVariables.view_month);
                                    
                                    if(params.get('year')) currentUrl.searchParams.set('year', params.get('year'));
                                    else if (window.flaskVariables) currentUrl.searchParams.set('year', window.flaskVariables.view_year);

                                    if(params.get('period_type')) currentUrl.searchParams.set('period_type', params.get('period_type'));
                                    else if (window.flaskVariables) currentUrl.searchParams.set('period_type', window.flaskVariables.view_period_type);
                                    
                                    window.location.href = currentUrl.toString();
                                }
                            }
                        }
                    }
                });
            } else { if (expectedVsActualCtx && expectedVsActualCtx.canvas) {expectedVsActualCtx.canvas.parentElement.innerHTML = '<p class="text-center text-muted p-5">No data for Budget vs. Actual chart.</p>';} }
        }
    }
    
    if (backToMainCategoriesChartBtn && expectedVsActualChartTitleEl) {
        if (window.flaskVariables && window.flaskVariables.focused_main_category_id) { 
            backToMainCategoriesChartBtn.style.display = 'inline-block';
            backToMainCategoriesChartBtn.addEventListener('click', () => {
                const currentUrl = new URL(window.location.href);
                currentUrl.searchParams.delete('main_cat_focus');
                const params = new URLSearchParams(window.location.search);
                if(params.get('month')) currentUrl.searchParams.set('month', params.get('month'));
                else if (window.flaskVariables && window.flaskVariables.view_month !== null) currentUrl.searchParams.set('month', window.flaskVariables.view_month);
                
                if(params.get('year')) currentUrl.searchParams.set('year', params.get('year'));
                else if (window.flaskVariables) currentUrl.searchParams.set('year', window.flaskVariables.view_year);

                if(params.get('period_type')) currentUrl.searchParams.set('period_type', params.get('period_type'));
                else if (window.flaskVariables) currentUrl.searchParams.set('period_type', window.flaskVariables.view_period_type);
                window.location.href = currentUrl.toString();
            });
        } else {
            backToMainCategoriesChartBtn.style.display = 'none';
        }
    }

    function renderNwsPieChart(canvasId, chartTitle, chartDataJsonString) {
        const ctx = document.getElementById(canvasId)?.getContext('2d');
        if (ctx) {
            const existingChart = Chart.getChart(ctx);
            if (existingChart) { existingChart.destroy(); }
            try {
                const data = JSON.parse(chartDataJsonString); 
                const nonZeroDataExists = data.data && data.data.some(d => parseFloat(d) > 0);
                if (data.labels && nonZeroDataExists) {
                    new Chart(ctx, {
                        type: 'pie',
                        data: {
                            labels: data.labels,
                            datasets: [{
                                label: chartTitle, data: data.data,
                                backgroundColor: ['rgba(255, 99, 132, 0.7)', 'rgba(255, 206, 86, 0.7)', 'rgba(75, 192, 192, 0.7)', 'rgba(201, 203, 207, 0.7)'],
                                borderColor: ['#fff'], borderWidth: 1
                            }]
                        },
                        options: { 
                            responsive: true, maintainAspectRatio: false, 
                            plugins: { 
                                legend: { position: 'bottom' }, 
                                tooltip: { callbacks: { label: (c) => `${c.label}: $${parseFloat(c.parsed).toFixed(2)} (${((parseFloat(c.parsed) / c.chart.getDatasetMeta(0).total) * 100).toFixed(1)}%)` }}
                            }
                        }
                    });
                } else {
                     if (ctx.canvas) { ctx.canvas.parentElement.innerHTML = `<p class="text-center text-muted p-5">No data for ${chartTitle}.</p>`;}
                }
            } catch(e) {
                console.error("Error parsing JSON for chart " + canvasId + ":", chartDataJsonString, e);
                if (ctx.canvas) { ctx.canvas.parentElement.innerHTML = `<p class="text-center text-danger p-5">Error loading data for ${chartTitle}.</p>`;}
            }
        }
    }
    
    // Ensure chart data is available globally (e.g., set by script tag in index.html)
    if (typeof initialExpectedVsActualData !== 'undefined') {
        renderExpectedVsActualChart(initialExpectedVsActualData);
    }
    if (typeof nwsBudgetedChartData !== 'undefined') {
        renderNwsPieChart('nwsBudgetedChart', 'Budgeted NWS', nwsBudgetedChartData);
    }
    if (typeof nwsActualChartData !== 'undefined') {
        renderNwsPieChart('nwsActualChart', 'Actual NWS', nwsActualChartData);
    }
});
