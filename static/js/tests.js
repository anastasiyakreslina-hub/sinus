/* =========================================================
   VARIANTS — JAVASCRIPT
   ========================================================= */


/* =========================================================
   ADD VARIANT MODAL
   ========================================================= */

function openVariantAdding() {
    const modal = document.getElementById('variantAdding');

    if (!modal) {
        return;
    }

    modal.style.display = 'flex';

    // Небольшая задержка нужна, чтобы transition
    // корректно отработал, если он есть в CSS
    requestAnimationFrame(() => {
        modal.classList.add('isOpen');
    });

    document.body.classList.add('modalOpen');
}


function closeVariantAdding() {
    const modal = document.getElementById('variantAdding');

    if (!modal) {
        return;
    }

    modal.classList.remove('isOpen');

    // Если transition не используется,
    // окно просто сразу скрывается
    setTimeout(() => {
        modal.style.display = 'none';
    }, 150);

    document.body.classList.remove('modalOpen');
}


/* =========================================================
   CLOSE MODAL BY CLICKING OUTSIDE
   ========================================================= */

document.addEventListener('click', function (event) {

    const modal = document.getElementById('variantAdding');

    if (!modal) {
        return;
    }

    // Клик именно по затемнённой области,
    // а не по содержимому модального окна
    if (event.target === modal) {
        closeVariantAdding();
    }

});


/* =========================================================
   CLOSE MODAL WITH ESC
   ========================================================= */

document.addEventListener('keydown', function (event) {

    if (event.key !== 'Escape') {
        return;
    }

    const modal = document.getElementById('variantAdding');

    if (!modal) {
        return;
    }

    if (modal.style.display !== 'none') {
        closeVariantAdding();
    }

});


/* =========================================================
   CONTACTS MODAL
   ========================================================= */

function openContacts() {

    const modal = document.getElementById('contacts');

    if (!modal) {
        return;
    }

    modal.style.display = 'flex';

    requestAnimationFrame(() => {
        modal.classList.add('isOpen');
    });

    document.body.classList.add('modalOpen');
}


function closeContacts() {

    const modal = document.getElementById('contacts');

    if (!modal) {
        return;
    }

    modal.classList.remove('isOpen');

    setTimeout(() => {
        modal.style.display = 'none';
    }, 150);

    document.body.classList.remove('modalOpen');
}


/* =========================================================
   CLOSE CONTACTS BY CLICKING OUTSIDE
   ========================================================= */

document.addEventListener('click', function (event) {

    const modal = document.getElementById('contacts');

    if (!modal) {
        return;
    }

    if (event.target === modal) {
        closeContacts();
    }

});


/* =========================================================
   ESC FOR CONTACTS
   ========================================================= */

document.addEventListener('keydown', function (event) {

    if (event.key !== 'Escape') {
        return;
    }

    const modal = document.getElementById('contacts');

    if (!modal) {
        return;
    }

    if (modal.style.display !== 'none') {
        closeContacts();
    }

});


/* =========================================================
   TASK IDS — INPUT FORMATTING
   ========================================================= */

document.addEventListener('DOMContentLoaded', function () {

    const textarea = document.querySelector(
        '#variantAdding textarea[name="task_ids"]'
    );

    if (!textarea) {
        return;
    }

    textarea.addEventListener('input', function () {

        /*
         * Разрешаем:
         * 12, 45, 78
         * 12 45 78
         * 12,45,78
         *
         * При этом автоматически убираем
         * лишние символы.
         */

        let value = this.value;

        value = value.replace(/[^\d,\s]/g, '');

        this.value = value;

    });

});


/* =========================================================
   PREVENT SCROLL WHEN MODAL IS OPEN
   ========================================================= */

document.addEventListener('DOMContentLoaded', function () {

    const observer = new MutationObserver(function () {

        const variantModal = document.getElementById('variantAdding');
        const contactsModal = document.getElementById('contacts');

        const variantOpen =
            variantModal &&
            variantModal.style.display !== 'none';

        const contactsOpen =
            contactsModal &&
            contactsModal.style.display !== 'none';

        if (variantOpen || contactsOpen) {
            document.body.classList.add('modalOpen');
        } else {
            document.body.classList.remove('modalOpen');
        }

    });


    const variantModal = document.getElementById('variantAdding');
    const contactsModal = document.getElementById('contacts');

    if (variantModal) {
        observer.observe(variantModal, {
            attributes: true,
            attributeFilter: ['style', 'class']
        });
    }

    if (contactsModal) {
        observer.observe(contactsModal, {
            attributes: true,
            attributeFilter: ['style', 'class']
        });
    }

});