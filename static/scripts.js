const ctx=document.getElementById('Chart');

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



function updateTime() {
    const now = new Date();
    document.getElementById('time').textContent=now.toLocaleTimeString();
    const hour = now.getHours();
    let greeting='';
    if (hour>=5 && hour<12) {
        greeting = 'доброе утро'
    } else if (hour>=12 && hour<18) {
        greeting = 'добрый день'
    } else if (hour>=18 && hour<23) {
        greeting='добрый вечер'
    } else {
        greeting = 'доброй ночи'
    }

    document.getElementById('greeting').textContent=greeting;
}
updateTime()
setInterval(updateTime,1000)

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

