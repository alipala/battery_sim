// Global state
const state = {
    batteryConfig: {
        capacity: 100,
        price: 40000
    },
    charts: {},
    data: null
};

// Initialize all charts
function initializeCharts() {
    // Daily Charts
    state.charts.dailyLine = new Chart(
        document.getElementById('dailyProfitLine').getContext('2d'),
        createChartConfig('line', 'Daily Profit (€)', '#3b82f6')
    );

    state.charts.dailyBar = new Chart(
        document.getElementById('dailyProfitBar').getContext('2d'),
        createChartConfig('bar', 'Daily Profit Distribution (€)', '#93c5fd')
    );

    state.charts.dailyArea = new Chart(
        document.getElementById('dailyProfitArea').getContext('2d'),
        createChartConfig('line', 'Cumulative Daily Profit (€)', '#3b82f6', true)
    );

    // Monthly Charts
    state.charts.monthlyLine = new Chart(
        document.getElementById('monthlyProfitLine').getContext('2d'),
        createChartConfig('line', 'Monthly Profit (€)', '#10b981')
    );

    state.charts.monthlyBar = new Chart(
        document.getElementById('monthlyProfitBar').getContext('2d'),
        createChartConfig('bar', 'Monthly Profit Distribution (€)', '#6ee7b7')
    );

    state.charts.monthlyArea = new Chart(
        document.getElementById('monthlyProfitArea').getContext('2d'),
        createChartConfig('line', 'Cumulative Monthly Profit (€)', '#10b981', true)
    );

    // Yearly Charts
    state.charts.yearlyLine = new Chart(
        document.getElementById('yearlyProfitLine').getContext('2d'),
        createChartConfig('line', 'Yearly Profit Projection (€)', '#8b5cf6')
    );

    state.charts.yearlyBar = new Chart(
        document.getElementById('yearlyProfitBar').getContext('2d'),
        createChartConfig('bar', 'Yearly Profit Distribution (€)', '#a78bfa')
    );

    state.charts.yearlyArea = new Chart(
        document.getElementById('yearlyProfitArea').getContext('2d'),
        createChartConfig('line', 'Cumulative Yearly Profit (€)', '#8b5cf6', true)
    );
}

function createChartConfig(type, label, color, fill = false) {
    return {
        type: type,
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                backgroundColor: fill ? `${color}33` : color,
                borderColor: color,
                fill: fill,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            animation: {
                duration: 750
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        drawBorder: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    };
}

function updateCharts(data) {
    if (!data) return;

    // Update daily charts
    const dailyData = data.daily;
    const dailyLabels = dailyData.map(d => d.date);
    const dailyProfits = dailyData.map(d => d.profit);
    
    // Calculate cumulative profits
    const cumulativeProfits = dailyProfits.reduce((acc, curr) => {
        const last = acc.length > 0 ? acc[acc.length - 1] : 0;
        acc.push(last + curr);
        return acc;
    }, []);

    updateChartData(state.charts.dailyLine, dailyLabels, dailyProfits);
    updateChartData(state.charts.dailyBar, dailyLabels, dailyProfits);
    updateChartData(state.charts.dailyArea, dailyLabels, cumulativeProfits);

    // Update monthly charts
    const monthlyData = data.monthly;
    const monthlyLabels = monthlyData.map(m => m.month);
    const monthlyProfits = monthlyData.map(m => m.total_profit);
    const monthly累計 = monthlyProfits.reduce((acc, curr) => {
        const last = acc.length > 0 ? acc[acc.length - 1] : 0;
        acc.push(last + curr);
        return acc;
    }, []);

    updateChartData(state.charts.monthlyLine, monthlyLabels, monthlyProfits);
    updateChartData(state.charts.monthlyBar, monthlyLabels, monthlyProfits);
    updateChartData(state.charts.monthlyArea, monthlyLabels, monthlyProfits);

    // Update yearly charts
    const yearlyData = data.yearly;
    const monthNames = Array.from({length: 12}, (_, i) => {
        const date = new Date();
        date.setMonth(i);
        return date.toLocaleDateString('en-US', { month: 'short' });
    });
    
    const monthlyAverage = yearlyData.total_profit / 12;
    const yearlyProjection = Array.from({length: 12}, (_, i) => monthlyAverage * (i + 1));

    updateChartData(state.charts.yearlyLine, monthNames, yearlyProjection);
    updateChartData(state.charts.yearlyBar, monthNames, Array(12).fill(monthlyAverage));
    updateChartData(state.charts.yearlyArea, monthNames, yearlyProjection);

    // Update ROI stats
    updateROIStats(yearlyData);
}

function updateChartData(chart, labels, data) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;
    chart.update('show');
}

function updateROIStats(yearlyData) {
    document.getElementById('roiPeriod').textContent = `${yearlyData.roi_years} Years`;
    document.getElementById('annualReturn').textContent = `${yearlyData.annual_return_percentage}%`;
    document.getElementById('breakEvenDate').textContent = yearlyData.breakeven_date;
    document.getElementById('totalInvestment').textContent = `€${state.batteryConfig.price.toLocaleString()}`;
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const uploadContainer = document.querySelector('.upload-container');
        const uploadStatus = document.querySelector('.upload-status');
        const statusText = document.getElementById('uploadStatus');

        uploadContainer.classList.add('uploading');
        statusText.textContent = 'Uploading...';
        uploadStatus.className = 'upload-status';

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Upload failed');

        statusText.textContent = '✓ File uploaded successfully';
        uploadStatus.className = 'upload-status success';
        await analyzeData(); // Automatically analyze after upload
        return true;
    } catch (error) {
        const uploadStatus = document.querySelector('.upload-status');
        const statusText = document.getElementById('uploadStatus');
        statusText.textContent = '✗ Upload failed';
        uploadStatus.className = 'upload-status error';
        console.error('Upload error:', error);
        return false;
    } finally {
        document.querySelector('.upload-container').classList.remove('uploading');
    }
}

async function analyzeData() {
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(state.batteryConfig)
        });

        if (!response.ok) throw new Error('Analysis failed');

        const data = await response.json();
        state.data = data;
        updateCharts(data);
    } catch (error) {
        console.error('Analysis error:', error);
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();

    // File upload handler
    document.getElementById('priceDataUpload').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            await uploadFile(file);
        }
    });

    // Battery configuration handlers
    document.querySelectorAll('.battery-option').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.battery-option').forEach(b => 
                b.classList.toggle('active', b === button));
            
            state.batteryConfig.capacity = parseInt(button.dataset.capacity);
            state.batteryConfig.price = parseInt(button.dataset.price);
            
            analyzeData();
        });
    });

    // Custom configuration handlers
    ['customCapacity', 'customPrice'].forEach(id => {
        document.getElementById(id).addEventListener('change', (e) => {
            const value = parseInt(e.target.value);
            if (!isNaN(value) && value > 0) {
                state.batteryConfig[id === 'customCapacity' ? 'capacity' : 'price'] = value;
                analyzeData();
            }
        });
    });

    // Tab navigation
    document.querySelectorAll('[data-tab]').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            
            // Update active tab
            document.querySelectorAll('[data-tab]').forEach(t => 
                t.classList.toggle('active', t === tab));
            
            // Show/hide content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.style.display = 
                    content.id === `${tabName}Tab` ? 'block' : 'none';
            });

            // Update charts if data exists
            if (state.data) {
                updateCharts(state.data);
            }
        });
    });
});