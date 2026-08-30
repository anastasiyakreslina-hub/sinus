document.addEventListener('DOMContentLoaded', () => {
    // =========================================================
    // CALENDAR LOGIC
    // =========================================================
    let currentDate = new Date();

    const monthNames = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ];
    const dayNames = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

    function renderCalendar() {
        const grid = document.getElementById('calendarGrid');
        const monthYearText = document.getElementById('calendarMonthYear');
        
        if (!grid || !monthYearText) return;

        grid.innerHTML = '';

        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();

        monthYearText.innerText = `${monthNames[month]} ${year}`;

        // Дни недели
        dayNames.forEach(day => {
            const head = document.createElement('div');
            head.className = 'calendarDayHead';
            head.innerText = day;
            grid.appendChild(head);
        });

        const firstDayOfMonth = new Date(year, month, 1);
        let firstDayIndex = firstDayOfMonth.getDay() - 1; // 0 - Пн
        if (firstDayIndex === -1) firstDayIndex = 6; // Вс

        const daysInMonth = new Date(year, month + 1, 0).getDate();

        // Пустые ячейки до первого дня месяца
        for (let i = 0; i < firstDayIndex; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'calendarCell empty';
            grid.appendChild(emptyCell);
        }

        const today = new Date();
        const activityData = window.activityData || {};

        // Дни месяца
        for (let day = 1; day <= daysInMonth; day++) {
            const cell = document.createElement('div');
            cell.className = 'calendarCell';

            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const count = activityData[dateStr] || 0;

            if (today.getFullYear() === year && today.getMonth() === month && today.getDate() === day) {
                cell.classList.add('today');
            }

            cell.innerHTML = `<span>${day}</span>`;

            if (count > 0) {
                if (count >= 5) {
                    cell.classList.add('hasTasksHigh');
                } else {
                    cell.classList.add('hasTasks');
                }
                cell.innerHTML += `<span class="taskBadge">${count} зад.</span>`;
                cell.title = `Решено задач: ${count}`;
            }

            grid.appendChild(cell);
        }
    }

    const prevBtn = document.getElementById('prevMonthBtn');
    const nextBtn = document.getElementById('nextMonthBtn');

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            currentDate.setMonth(currentDate.getMonth() - 1);
            renderCalendar();
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            currentDate.setMonth(currentDate.getMonth() + 1);
            renderCalendar();
        });
    }

    renderCalendar();

    // =========================================================
    // TABLE SLIDER LOGIC
    // =========================================================
    const tableWrapper = document.getElementById('variantsTableWrapper');
    const leftButton = document.querySelector('.tableArrowLeft');
    const rightButton = document.querySelector('.tableArrowRight');

    if (tableWrapper && leftButton && rightButton) {
        function updateTableArrows() {
            const maxScroll = tableWrapper.scrollWidth - tableWrapper.clientWidth;
            leftButton.disabled = tableWrapper.scrollLeft <= 5;
            rightButton.disabled = tableWrapper.scrollLeft >= maxScroll - 5;
        }

        leftButton.addEventListener('click', () => {
            tableWrapper.scrollBy({ left: -450, behavior: 'smooth' });
        });

        rightButton.addEventListener('click', () => {
            tableWrapper.scrollBy({ left: 450, behavior: 'smooth' });
        });

        tableWrapper.addEventListener('scroll', updateTableArrows);
        window.addEventListener('resize', updateTableArrows);
        updateTableArrows();
    }
});