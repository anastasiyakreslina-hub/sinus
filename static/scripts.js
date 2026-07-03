const ctx=document.getElementById('Chart');
const sidebar = document.getElementById('sidebar');

document.addEventListener("DOMContentLoaded", () => {
    const toast = document.getElementById("toast");
    if (toast) {
        setTimeout(() => {
            toast.style.opacity = "0";
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }
});

if (sidebar) {
    sidebar.addEventListener('click',()=> {
        sidebar.classList.toggle('open');
    });
}

if (ctx) {
    new Chart(ctx, {
        type:'bar',
        data: {
            labels: numbers,
            datasets: [{
                label: 'Процент правильных решений',
                data: percents,
                backgroundColor: 'rgb(215, 173, 195)',
                hoverBackgroundColor:'#d70668',
                borderRadius:10
            }]
        },
        options: {
            color:'#ffffff42',
            font: {
                family:'MyFont',
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color:'#ffffff42',
                        font: {
                            family:'MyFont'
                        }
                    }
                },
                x: {
                    ticks: {
                        color:'#ffffff42',
                        font: {
                            family:'MyFont'
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color:'#ffffff42',
                        font: {
                            family:'MyFont'
                        }
                    }
                }
            }
        }
    });
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
            solution.style.display='block';
        }
        resultBox.classList.remove('green','red','white');
        if (data.result==='correct') {
            resultBox.classList.add('green');
            if (window.location.pathname==='/mistakes') {
                const taskBlock=document.getElementById(`task-${taskId}`);
                if (taskBlock) taskBlock.remove();
            }
        } else {
            resultBox.classList.add('red');
        }
    });
}


function  openTheoryAdding() {
    document.getElementById('theoryAdding').style.display='block';
}
function closeTheoryAdding() {
    document.getElementById('theoryAdding').style.display='none'
}
function editTheory(btn) {
    const id=btn.dataset.id;
    const title = btn.dataset.title;
    const task = btn.dataset.task;
    const text = btn.dataset.text;
    document.getElementById('title').value=title;
    document.getElementById('task_number').value=task;
    document.getElementById('text').value=text
    const form = document.getElementById('theoryForm');
    form.action='/edit_theory/'+id
    openTheoryAdding();
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
updateTime()
setInterval(updateTime,1000)