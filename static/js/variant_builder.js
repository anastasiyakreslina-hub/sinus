// =========================================================
// КОНСТРУКТОР ВАРИАНТА — поиск заданий и список выбранных
// =========================================================

(function () {
    const searchInput = document.getElementById('taskSearchInput');
    const resultsBox = document.getElementById('taskSearchResults');
    const selectedList = document.getElementById('selectedTasksList');
    const selectedEmpty = document.getElementById('selectedTasksEmpty');
    const selectedCount = document.getElementById('selectedCount');
    const hiddenInput = document.getElementById('taskIdsHidden');
    const form = document.getElementById('addVariantForm');

    if (!searchInput) return;

    let selectedTasks = [];
    let debounceTimer = null;

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function syncHiddenInput() {
        hiddenInput.value = selectedTasks.map(t => t.id).join(',');
        selectedCount.textContent = selectedTasks.length;
        selectedEmpty.style.display = selectedTasks.length ? 'none' : 'block';
    }

    function renderSelected() {
        selectedList.querySelectorAll('.selectedTaskItem').forEach(el => el.remove());

        selectedTasks.forEach(task => {
            const item = document.createElement('div');
            item.className = 'selectedTaskItem';
            item.innerHTML = `
                <div>
                    <span class="taskTag taskId">#${task.id}</span>
                    <span class="taskTag">№${escapeHtml(task.number)}</span>
                    <p class="selectedTaskSnippet">${escapeHtml(task.snippet)}</p>
                </div>
                <button type="button" class="removeTaskBtn" data-id="${task.id}" title="Убрать из варианта">×</button>
            `;
            selectedList.appendChild(item);
        });

        syncHiddenInput();
    }

    function addTask(task) {
        if (selectedTasks.some(t => t.id === task.id)) return;
        selectedTasks.push(task);
        renderSelected();
    }

    function removeTask(id) {
        selectedTasks = selectedTasks.filter(t => t.id !== id);
        renderSelected();
    }

    function renderResults(tasks) {
        if (!tasks.length) {
            resultsBox.innerHTML = '<p class="filterHint">Ничего не найдено.</p>';
            return;
        }

        resultsBox.innerHTML = '';

        tasks.forEach(task => {
            const already = selectedTasks.some(t => t.id === task.id);

            const item = document.createElement('div');
            item.className = 'taskSearchResultItem';
            item.innerHTML = `
                <div>
                    <span class="taskTag taskId">#${task.id}</span>
                    <span class="taskTag">№${escapeHtml(task.number)}</span>
                    <span class="taskTag">${escapeHtml(task.source || '')}</span>
                    <p class="selectedTaskSnippet">${escapeHtml(task.snippet)}</p>
                </div>
                <button type="button" class="addTaskBtn" data-id="${task.id}" ${already ? 'disabled' : ''}>
                    ${already ? 'Добавлено' : '+ Добавить'}
                </button>
            `;
            resultsBox.appendChild(item);

            item.querySelector('.addTaskBtn').addEventListener('click', () => {
                addTask(task);
                renderResults(tasks);
            });
        });
    }

    function search(query) {
        fetch(`/api/search_tasks?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(renderResults)
            .catch(() => {
                resultsBox.innerHTML = '<p class="filterHint">Не удалось выполнить поиск.</p>';
            });
    }

    searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        const query = searchInput.value.trim();
        debounceTimer = setTimeout(() => search(query), 250);
    });

    // Показать первые задания сразу при открытии модалки
    searchInput.addEventListener('focus', () => {
        if (!resultsBox.innerHTML.trim()) {
            search('');
        }
    }, { once: true });

    selectedList.addEventListener('click', (e) => {
        const btn = e.target.closest('.removeTaskBtn');
        if (!btn) return;
        removeTask(Number(btn.dataset.id));
    });

    if (form) {
        form.addEventListener('submit', (e) => {
            if (!selectedTasks.length) {
                e.preventDefault();
                alert('Добавь хотя бы одно задание в вариант.');
            }
        });
    }
})();