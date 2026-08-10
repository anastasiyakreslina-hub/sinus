document.addEventListener('DOMContentLoaded', () => {
    const varForm = document.getElementById('var_form');
    if (varForm) {
        varForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const formData = new FormData(varForm);
            const response = await fetch('/check_var', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            document.getElementById('result_text').textContent = `Правильных ответов: ${data.score} из 19`;
            document.getElementById('result_modal').style.display = 'block';
        });
    }
});

function closeResults() {
    document.getElementById('result_modal').style.display = 'none';
}

function checkAnswer(taskId) {
    const input = document.getElementById(`input-${taskId}`);
    const resultBox = document.getElementById(`result-${taskId}`);
    fetch(`/check_answer/${taskId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            answer: input.value
        })
    })
    .then(res => res.json())
    .then(data => {
        resultBox.innerText = data.text;
        const solution = document.getElementById(`solution-${taskId}`);
        if (solution) {
            solution.style.display = 'block';
        }
        resultBox.classList.remove('blue', 'red', 'white');
        if (data.result === 'correct') {
            resultBox.classList.add('blue');
            if (window.location.pathname === '/mistakes') {
                const taskBlock = document.getElementById(`task-${taskId}`);
                if (taskBlock) taskBlock.remove();
            }
        } else {
            resultBox.classList.add('red');
        }
    });
}

function openTaskAdding() {
    document.getElementById('taskAdding').style.display = 'block';
}

function closeTaskAdding() {
    document.getElementById('taskAdding').style.display = 'none';
}

function openTheoryAdding() {
    document.getElementById('theoryAdding').style.display = 'block';
}

function closeTheoryAdding() {
    document.getElementById('theoryAdding').style.display = 'none';
}

function editTask(btn) {
    const id = btn.dataset.id;
    document.getElementById('number').value = btn.dataset.number;
    document.getElementById('source').value = btn.dataset.source;
    document.getElementById('text').value = btn.dataset.text;
    document.getElementById('solution').value = btn.dataset.solution;
    document.getElementById('answer').value = btn.dataset.answer;
    
    const form = document.getElementById('taskForm');
    form.action = '/edit_task/' + id;
    openTaskAdding();
}

function editTheory(btn) {
    const id = btn.dataset.id;
    document.getElementById('title').value = btn.dataset.title;
    document.getElementById('task_number').value = btn.dataset.task;
    document.getElementById('text').value = btn.dataset.text;
    
    const form = document.getElementById('theoryForm');
    form.action = '/edit_theory/' + id;
    openTheoryAdding();
}