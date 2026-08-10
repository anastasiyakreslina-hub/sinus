document.addEventListener("DOMContentLoaded", () => {
    // Исчезновение уведомительного тоаста
    const toast = document.getElementById("toast");
    if (toast) {
        setTimeout(() => {
            toast.style.opacity = "0";
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }

    // Переключение сайдбара
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // Инициализация часов
    updateTime();
    setInterval(updateTime, 1000);
});

function openSettings() {
    document.getElementById("settingsModal").style.display = "flex";
}

function closeSettings() {
    document.getElementById("settingsModal").style.display = "none";
}

function openContacts() {
    document.getElementById('contacts').style.display = 'block';
}

function closeContacts() {
    document.getElementById('contacts').style.display = 'none';
}

function updateTime() {
    const timeEl = document.getElementById('time');
    const greetingEl = document.getElementById('greeting');
    if (!timeEl && !greetingEl) return;
    
    const now = new Date();
    if (timeEl) {
        timeEl.textContent = now.toLocaleTimeString();
    }
    if (greetingEl) {
        const hour = now.getHours();
        let greeting = '';
        if (hour >= 5 && hour < 12) greeting = 'доброе утро';
        else if (hour < 18) greeting = 'добрый день';
        else if (hour < 23) greeting = 'добрый вечер';
        else greeting = 'доброй ночи';
        greetingEl.textContent = greeting;
    }
}