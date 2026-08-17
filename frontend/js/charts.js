let trendChartInstance = null;
let categoryChartInstance = null;

function renderTrendChart(monthlyTrendData) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    
    if (trendChartInstance) {
        trendChartInstance.destroy();
    }

    const labels = monthlyTrendData.map(d => d.month);
    const revData = monthlyTrendData.map(d => d.revenue);
    const expData = monthlyTrendData.map(d => d.expense);

    trendChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Revenue ($)',
                    data: revData,
                    backgroundColor: 'rgba(37, 99, 235, 0.85)',
                    borderColor: '#2563eb',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Expenses ($)',
                    data: expData,
                    backgroundColor: 'rgba(220, 38, 38, 0.75)',
                    borderColor: '#dc2626',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#475569', font: { family: 'Inter', size: 12, weight: 500 } } }
            },
            scales: {
                x: { ticks: { color: '#64748b', font: { family: 'Inter', size: 11 } }, grid: { color: '#f1f5f9' } },
                y: { ticks: { color: '#64748b', font: { family: 'Inter', size: 11 } }, grid: { color: '#f1f5f9' } }
            }
        }
    });
}

function renderCategoryChart(categoryData) {
    const ctx = document.getElementById('categoryChart').getContext('2d');

    if (categoryChartInstance) {
        categoryChartInstance.destroy();
    }

    const labels = Object.keys(categoryData);
    const values = Object.values(categoryData);

    const colors = [
        '#2563eb', '#059669', '#d97706', '#7c3aed', '#dc2626', '#0284c7', '#64748b'
    ];

    categoryChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#475569', font: { family: 'Inter', size: 11, weight: 500 } } }
            }
        }
    });
}

