// Применяем сохранённую тему сразу
(function applyTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
})();


// Обновляем текст кнопки
function updateThemeButtonText() {
    const button = document.getElementById('themeToggleBtn');

    if (!button) return;

    const currentTheme =
        document.documentElement.getAttribute('data-theme');

    if (currentTheme === 'light') {
        button.textContent = '☀️ Светлая тема';
    } else {
        button.textContent = '🌙 Тёмная тема';
    }
}


// После загрузки страницы
document.addEventListener('DOMContentLoaded', () => {
    updateThemeButtonText();
});


// Нажатие на кнопку
document.addEventListener('click', (event) => {
    const button = event.target.closest('#themeToggleBtn');

    if (!button) return;

    event.preventDefault();

    const currentTheme =
        document.documentElement.getAttribute('data-theme') || 'dark';

    // Переключаем тему
    const newTheme =
        currentTheme === 'dark' ? 'light' : 'dark';

    // Применяем новую тему
    document.documentElement.setAttribute('data-theme', newTheme);

    // Сохраняем выбор
    localStorage.setItem('theme', newTheme);

    // Меняем текст кнопки
    updateThemeButtonText();
});

function updateChartTheme() {
    if (typeof myChart !== 'undefined') {
        // Обновляем цвета колонок
        myChart.data.datasets[0].backgroundColor = getThemeColor('--btn-change-bg');
        myChart.data.datasets[0].borderColor = getThemeColor('--card-border');
        
        // Обновляем цвет текста осей
        myChart.options.scales.x.ticks.color = getThemeColor('--text-color');
        myChart.options.scales.y.ticks.color = getThemeColor('--text-color');

        // Перерисовываем график
        myChart.update();
    }
}