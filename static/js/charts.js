// Хранилище экземпляров графиков
const chartsStore = {};

// Получение цвета CSS-переменной из темы
function getThemeColor(variableName) {
    return getComputedStyle(document.documentElement)
        .getPropertyValue(variableName)
        .trim();
}

// Функция обновления цветов у всех активных графиков
function updateChartsColors() {
    const textColor = getThemeColor('--text-color') || '#ffffff42';
    const barBg = getThemeColor('--chart-bg') || 'rgb(215, 173, 195)';
    const barHoverBg = getThemeColor('--text-accent') || '#d70668';

    Object.values(chartsStore).forEach(chart => {
        if (!chart) return;

        // Цвета колонок
        chart.data.datasets.forEach(dataset => {
            dataset.backgroundColor = barBg;
            dataset.hoverBackgroundColor = barHoverBg;
        });

        // Цвета текста осей и легенды
        chart.options.color = textColor;
        if (chart.options.scales?.x?.ticks) chart.options.scales.x.ticks.color = textColor;
        if (chart.options.scales?.y?.ticks) chart.options.scales.y.ticks.color = textColor;
        if (chart.options.plugins?.legend?.labels) chart.options.plugins.legend.labels.color = textColor;

        chart.update();
    });
}

// Инициализация графиков после загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('Chart');
    const firstTryCtx = document.getElementById('firstTryChart');

    const commonOptions = {
        color: getThemeColor('--text-color') || '#ffffff42',
        font: { family: 'MyFont' },
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    color: getThemeColor('--text-color') || '#ffffff42',
                    font: { family: 'MyFont', size: 7 }
                }
            },
            x: {
                ticks: {
                    color: getThemeColor('--text-color') || '#ffffff42',
                    font: { family: 'MyFont' }
                }
            }
        },
        plugins: {
            legend: {
                labels: {
                    color: getThemeColor('--text-color') || '#ffffff42',
                    font: { family: 'MyFont' }
                }
            }
        }
    };

    if (ctx && typeof numbers !== 'undefined' && typeof percents !== 'undefined') {
        chartsStore.mainChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: numbers,
                datasets: [{
                    label: 'Процент правильных решений',
                    data: percents,
                    backgroundColor: getThemeColor('--chart-bg') || 'rgb(215, 173, 195)',
                    hoverBackgroundColor: getThemeColor('--text-accent') || '#d70668',
                    borderRadius: 10
                }]
            },
            options: commonOptions
        });
    }

    if (firstTryCtx && typeof first_attempts_numbers !== 'undefined' && typeof first_attempts_percents !== 'undefined') {
        chartsStore.firstTryChart = new Chart(firstTryCtx, {
            type: 'bar',
            data: {
                labels: first_attempts_numbers,
                datasets: [{
                    label: 'Процент правильных ответов с первого раза',
                    data: first_attempts_percents,
                    backgroundColor: getThemeColor('--chart-bg') || 'rgb(215, 173, 195)',
                    hoverBackgroundColor: getThemeColor('--text-accent') || '#d70668',
                    borderRadius: 10
                }]
            },
            options: commonOptions
        });
    }
});

// Наблюдатель за сменой темы (автоматически перерисовывает графики)
const themeObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.attributeName === 'data-theme') {
            updateChartsColors();
        }
    });
});

themeObserver.observe(document.documentElement, { attributes: true });