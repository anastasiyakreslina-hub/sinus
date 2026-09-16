import os

import psycopg2.extras
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename

from database import get_db
from decorators import admin_only, regs_only

theory_bp = Blueprint('theory', __name__)


@theory_bp.route('/theory')
@regs_only
def theory():
    task_number = request.args.get('task_number')
    block_id = request.args.get('block_id')
    sort = request.args.get('sort', 'new')
    status = request.args.get('status')

    user_id = session.get('user_id')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        query = '''
            SELECT
                t.block_id,
                t.title,
                t.task_number,
                t.text,
                t.pdf_path,
                COALESCE(p.is_completed, FALSE) AS is_completed
            FROM theory_table t
            LEFT JOIN theory_progress p
                ON p.block_id = t.block_id AND p.user_id = %s
            WHERE 1=1
        '''
        params = [user_id]

        if task_number:
            query += ' AND t.task_number = %s'
            params.append(task_number)

        if block_id:
            query += ' AND t.block_id = %s'
            params.append(block_id)

        if status == 'done':
            query += ' AND COALESCE(p.is_completed, FALSE) = TRUE'
        elif status == 'undone':
            query += ' AND COALESCE(p.is_completed, FALSE) = FALSE'

        query += ' ORDER BY t.block_id ' + ('ASC' if sort == 'old' else 'DESC')

        cur.execute(query, params)
        blocks = cur.fetchall()

        return render_template('theory.html', blocks=blocks)
    finally:
        cur.close()
        conn.close()


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
        pdf.save(os.path.join(upload_dir, filename))
        pdf_path = f'theory/{filename}'

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            'INSERT INTO theory_table(title, task_number, text, pdf_path) VALUES (%s, %s, %s, %s)',
            (title, task_number, text, pdf_path)
        )
        conn.commit()
        return redirect(url_for('theory.theory'))
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@theory_bp.route('/theory/edit/<int:block_id>', methods=['POST'])
@admin_only
def edit_theory(block_id):
    title = request.form.get('title')
    task_number = request.form.get('task_number')
    text = request.form.get('text')
    pdf = request.files.get('pdf')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        if pdf and pdf.filename:
            cur.execute('SELECT pdf_path FROM theory_table WHERE block_id = %s', (block_id,))
            row = cur.fetchone()

            if row and row['pdf_path']:
                old_path = os.path.join('static', row['pdf_path'])
                if os.path.exists(old_path):
                    os.remove(old_path)

            filename = secure_filename(pdf.filename)
            upload_dir = os.path.join('static', 'theory')
            os.makedirs(upload_dir, exist_ok=True)
            pdf.save(os.path.join(upload_dir, filename))
            pdf_path = f'theory/{filename}'

            cur.execute(
                'UPDATE theory_table SET title = %s, task_number = %s, text = %s, pdf_path = %s WHERE block_id = %s',
                (title, task_number, text, pdf_path, block_id)
            )
        else:
            cur.execute(
                'UPDATE theory_table SET title = %s, task_number = %s, text = %s WHERE block_id = %s',
                (title, task_number, text, block_id)
            )

        conn.commit()
        return redirect('/theory')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@theory_bp.route('/delete_theory/<int:theory_id>', methods=['POST'])
@admin_only
def delete_theory(theory_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute('SELECT pdf_path FROM theory_table WHERE block_id = %s', (theory_id,))
        row = cur.fetchone()

        if row and row['pdf_path']:
            full_path = os.path.join('static', row['pdf_path'])
            if os.path.exists(full_path):
                os.remove(full_path)

        cur.execute('DELETE FROM theory_table WHERE block_id = %s', (theory_id,))
        conn.commit()
        return redirect(url_for('theory.theory'))
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@theory_bp.route('/theory/toggle_complete/<int:block_id>', methods=['POST'])
@regs_only
def toggle_complete(block_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(status='error', message='Не авторизован'), 401

    data = request.get_json(silent=True) or {}
    completed = bool(data.get('completed'))

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            '''
            INSERT INTO theory_progress (user_id, block_id, is_completed)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, block_id)
            DO UPDATE SET is_completed = EXCLUDED.is_completed
            ''',
            (user_id, block_id, completed)
        )
        conn.commit()
        return jsonify(status='ok', completed=completed)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()