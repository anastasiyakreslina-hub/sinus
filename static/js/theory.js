let quill;

/* =========================================
   ИНИЦИАЛИЗАЦИЯ
========================================= */
document.addEventListener("DOMContentLoaded", function () {
  const editorElement = document.getElementById("editor");

  if (editorElement && typeof Quill !== "undefined") {
    // Выбираем ваш кастомный #toolbar, если он есть в DOM, иначе дефолтный массив
    const customToolbar = document.getElementById("toolbar");

    quill = new Quill("#editor", {
      theme: "snow",
      placeholder: "Введите теоретический материал...",
      modules: {
        toolbar: customToolbar ? "#toolbar" : [
          [{ header: [1, 2, 3, false] }],
          ["bold", "italic", "underline", "strike"],
          [{ color: [] }, { background: [] }],
          [{ list: "ordered" }, { list: "bullet" }],
          ["link", "image", "video"],
          ["clean"]
        ]
      }
    });

    // Инициализация кастомных палитр цветов (если элементы присутствуют)
    initCustomColorPickers();

    const form = document.getElementById("theoryForm");
    if (form) {
      form.addEventListener("submit", function () {
        const hiddenInput = document.getElementById("hiddenText");
        if (hiddenInput && quill) {
          hiddenInput.value = quill.root.innerHTML;
        }
      });
    }
  }

  // Инициализация KaTeX
  if (typeof renderMathInElement !== "undefined") {
    renderMathInElement(document.body, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false }
      ]
    });
  }

  // Инициализация анимации появления блоков
  const observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("active");
        }
      });
    },
    { threshold: 0.1 }
  );

  document.querySelectorAll(".reveal").forEach(function (element) {
    observer.observe(element);
  });
});

/* =========================================
   КАСТОМНЫЕ ЦВЕТА И LOCALSTORAGE
========================================= */
function initCustomColorPickers() {
  const MAX_RECENT = 5;

  const textInput = document.getElementById("textColorPicker");
  const bgInput = document.getElementById("bgColorPicker");
  const recentTextContainer = document.getElementById("recentTextColors");
  const recentBgContainer = document.getElementById("recentBgColors");

  // Если элементов палитры нет на странице, прерываем выполнение
  if (!recentTextContainer && !recentBgContainer && !textInput && !bgInput) {
    return;
  }

  let recentText = JSON.parse(localStorage.getItem("sinus_recent_text_colors") || '["#e00560", "#2563eb", "#16a34a"]');
  let recentBg = JSON.parse(localStorage.getItem("sinus_recent_bg_colors") || '["#fef08a", "#bbf7d0", "#fed7aa"]');

  function renderSwatches(container, colors, formatType) {
    if (!container) return;
    container.innerHTML = "";
    colors.forEach(color => {
      const swatch = document.createElement("span");
      swatch.className = "colorSwatch";
      swatch.style.backgroundColor = color;
      swatch.title = color;

      swatch.addEventListener("click", () => {
        applyColor(formatType, color);
      });

      container.appendChild(swatch);
    });
  }

  function applyColor(formatType, color) {
    if (!quill) return;
    const range = quill.getSelection();
    if (range) {
      quill.format(formatType, color);
    }
    saveColor(formatType, color);
  }

  function saveColor(formatType, color) {
    if (formatType === 'color') {
      recentText = [color, ...recentText.filter(c => c !== color)].slice(0, MAX_RECENT);
      localStorage.setItem("sinus_recent_text_colors", JSON.stringify(recentText));
      renderSwatches(recentTextContainer, recentText, 'color');
    } else if (formatType === 'background') {
      recentBg = [color, ...recentBg.filter(c => c !== color)].slice(0, MAX_RECENT);
      localStorage.setItem("sinus_recent_bg_colors", JSON.stringify(recentBg));
      renderSwatches(recentBgContainer, recentBg, 'background');
    }
  }

  if (textInput) {
    textInput.addEventListener("change", (e) => applyColor("color", e.target.value));
  }
  if (bgInput) {
    bgInput.addEventListener("change", (e) => applyColor("background", e.target.value));
  }

  renderSwatches(recentTextContainer, recentText, 'color');
  renderSwatches(recentBgContainer, recentBg, 'background');
}

/* =========================================
   ОТКРЫТЬ ОКНО ДОБАВЛЕНИЯ
========================================= */
function openTheoryAdding() {
  const modal = document.getElementById("theoryAdding");
  const form = document.getElementById("theoryForm");
  const modalTitle = document.getElementById("modalTitleText");

  if (!modal) return;

  if (form) {
    const addUrl = form.dataset.addUrl || "/add_theory";
    form.setAttribute("action", addUrl);
    form.reset();
  }

  if (quill) {
    quill.root.innerHTML = "";
  }

  if (modalTitle) {
    modalTitle.innerText = "Новая теория";
  }

  modal.style.display = "flex";
}

/* =========================================
   ЗАКРЫТЬ ОКНО
========================================= */
function closeTheoryAdding() {
  const modal = document.getElementById("theoryAdding");
  if (modal) {
    modal.style.display = "none";
  }
}

/* =========================================
   РЕДАКТИРОВАНИЕ
========================================= */
function editTheory(btn) {
  const modal = document.getElementById("theoryAdding");
  const form = document.getElementById("theoryForm");
  const modalTitle = document.getElementById("modalTitleText");
  const titleInput = document.getElementById("title");
  const taskNumberInput = document.getElementById("task_number");

  if (!modal || !form) return;

  const editUrl = btn.dataset.editUrl;
  if (!editUrl) {
    console.error("Не найден data-edit-url у кнопки редактирования");
    return;
  }

  form.action = editUrl;

  if (modalTitle) modalTitle.innerText = "Редактирование теории";
  if (titleInput) titleInput.value = btn.dataset.title || "";
  if (taskNumberInput) taskNumberInput.value = btn.dataset.task || "";

  const card = btn.closest(".taskCard");
  if (card) {
    const textContainer = card.querySelector(".taskText");
    if (quill && textContainer) {
      quill.root.innerHTML = textContainer.innerHTML.trim();
    }
  }

  modal.style.display = "flex";
}

/* =========================================
   ЗАКРЫТИЕ MODAL ПРИ КЛИКЕ СНАРУЖИ
========================================= */
document.addEventListener("click", function (event) {
  const modal = document.getElementById("theoryAdding");
  if (modal && event.target === modal) {
    closeTheoryAdding();
  }
});