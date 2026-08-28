document.addEventListener("DOMContentLoaded", () => {
const html = document.documentElement;
const themeButton = document.getElementById("themeToggleBtn");

function updateThemeButton() {
    if (!themeButton) return;

    const isDark = html.getAttribute("data-theme") === "dark";

    themeButton.innerHTML = isDark
        ? "☀️ Светлая тема"
        : "🌙 Тёмная тема";
}

const savedTheme = localStorage.getItem("theme");

if (savedTheme) {
    html.setAttribute("data-theme", savedTheme);
}

updateThemeButton();

if (themeButton) {
    themeButton.addEventListener("click", () => {

        const currentTheme =
            html.getAttribute("data-theme");

        const newTheme =
            currentTheme === "dark"
                ? "light"
                : "dark";

        html.setAttribute("data-theme", newTheme);

        localStorage.setItem("theme", newTheme);

        updateThemeButton();
    });
}});