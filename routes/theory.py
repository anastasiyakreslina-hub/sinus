import os
import psycopg2.extras
from flask import Blueprint, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from database import get_db
from decorators import admin_only, regs_only

theory_bp = Blueprint('theory', __name__)


@theory_bp.route('/theory')
@regs_only
def theory():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT block_id, title, task_number, text, pdf_path
        FROM theory_table
        ORDER BY block_id DESC
    """)

    blocks = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('theory.html', blocks=blocks)


@theory_bp.route('/add_theory', methods=['POST'])
@admin_only
def add_theory():
    title = request.form.get('title')
    task_number = request.form.get('task_number')
    text = request.form.get('text')
    pdf = request.files.get('pdf')
    pdf_path = None

    if pdf and pdf.filename:
        filename = secure_filename(pdf.filename)
        upload_dir = os.path.join('static', 'theory')
        os.makedirs(upload_dir, exist_ok=True)

        save_path = os.path.join(upload_dir, filename)
        pdf.save(save_path)

        pdf_path = f'theory/{filename}'

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO theory_table
        (title, task_number, text, pdf_path)
        VALUES (%s, %s, %s, %s)
        """,
        (title, task_number, text, pdf_path)
    )

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('theory.theory'))


@theory_bp.route('/theory/edit/<int:block_id>', methods=['POST'])
@admin_only
def edit_theory(block_id):
    title = request.form.get('title')
    task_number = request.form.get('task_number')
    text = request.form.get('text')
    pdf = request.files.get('pdf')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if pdf and pdf.filename:
        cur.execute(
            """
            SELECT pdf_path
            FROM theory_table
            WHERE block_id = %s
            """,
            (block_id,)
        )

        row = cur.fetchone()

        if row and row['pdf_path']:
            old_path = os.path.join('static', row['pdf_path'])
            if os.path.exists(old_path):
                os.remove(old_path)

        filename = secure_filename(pdf.filename)
        upload_dir = os.path.join('static', 'theory')
        os.makedirs(upload_dir, exist_ok=True)

        save_path = os.path.join(upload_dir, filename)
        pdf.save(save_path)

        pdf_path = f'theory/{filename}'

        cur.execute(
            """
            UPDATE theory_table
            SET
                title = %s,
                task_number = %s,
                text = %s,
                pdf_path = %s
            WHERE block_id = %s
            """,
            (title, task_number, text, pdf_path, block_id)
        )

    else:
        cur.execute(
            """
            UPDATE theory_table
            SET
                title = %s,
                task_number = %s,
                text = %s
            WHERE block_id = %s
            """,
            (title, task_number, text, block_id)
        )

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/theory')


@theory_bp.route('/delete_theory/<int:theory_id>', methods=['POST'])
@admin_only
def delete_theory(theory_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT pdf_path
        FROM theory_table
        WHERE block_id = %s
        """,
        (theory_id,)
    )

    row = cur.fetchone()

    if row and row['pdf_path']:
        full_path = os.path.join('static', row['pdf_path'])
        if os.path.exists(full_path):
            os.remove(full_path)

    cur.execute(
        """
        DELETE FROM theory_table
        WHERE block_id = %s
        """,
        (theory_id,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('theory.theory'))