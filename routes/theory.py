# Теория (просмотр, добавление, редактирование)

from flask import Blueprint, render_template, request, redirect
from database import get_db
from decorators import admin_only, regs_only

theory_bp = Blueprint('theory', __name__)

@theory_bp.route('/theory')
@regs_only
def theory():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT block_id, title, task_number, text, pdf_path FROM theory_table')
    blocks = cur.fetchall()
    conn.close()
    return render_template('theory.html', blocks=blocks)

@theory_bp.route('/add_theory', methods=['POST'])
@admin_only
def add_theory():
    title = request.form['title']
    task_number = request.form['task_number']
    text = request.form['text']
    pdf = request.files.get('pdf')
    pdf_path = None
    if pdf:
        pdf_path = f'static/theory/{pdf.filename}'
        pdf.save(pdf_path)
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO theory_table(title,task_number,text,pdf_path) VALUES(?,?,?,?)',
                (title, task_number, text, pdf_path))
    conn.commit()
    conn.close()
    return redirect('/theory')

@theory_bp.route('/delete_theory/<int:theory_id>', methods=['POST'])
@admin_only
def delete_theory(theory_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM theory_table WHERE block_id=?', (theory_id,))
    conn.commit()
    conn.close()
    return redirect('/theory')

@theory_bp.route('/edit_theory/<int:block_id>', methods=['POST'])
@admin_only
def edit_theory(block_id):
    title = request.form['title']
    task_number = request.form['task_number']
    text = request.form['text']
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE theory_table SET title=?, task_number=?, text=? WHERE block_id=?',
                (title, task_number, text, block_id))
    conn.commit()
    conn.close()
    return redirect('/theory')