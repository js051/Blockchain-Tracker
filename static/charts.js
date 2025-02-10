// static/charts.js

// 用於數據可視化的 JS
function renderChart(data) {
    if (!data || !data.labels || !data.values) {
        console.error("無效的圖表數據");
        return;
    }
    const ctx = document.getElementById('chart').getContext('2d');
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels,
            datasets: [{
                label: '交易金額 (ETH)',
                data: data.values,
                backgroundColor: [
                    '#36a2eb',
                    '#ff6384',
                    '#ffcd56',
                    '#4bc0c0',
                    '#9966ff'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: '交易摘要'
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            return `${label}: ${value} ETH`;
                        }
                    }
                }
            }
        }
    });
}
