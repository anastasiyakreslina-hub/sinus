# =========================================================
# ВАРИАНТЫ / ТЕСТЫ
# =========================================================

import random
from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session

from database import get_db
from decorators import admin_only, regs_only
from helpers.task_stats import record_attempt


variants_bp = Blueprint('variants', __name__)


@variants_bp.route('/tests')
@regs_only
def tests():
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('''
            SELECT id, name, year, created_at
            FROM variants
            WHERE is_public = TRUE
            ORDER BY year DESC, created_at DESC, id DESC
        ''')
        variants = cur.fetchall()

        years = {}
        for variant in variants:
            years.setdefault(variant['year'], []).append(variant)

        return render_template('tests.html', years=years)
    finally:
        cur.close()
        conn.close()


@variants_bp.route('/add_variant', methods=['POST'])
@admin_only
def add_variant():
    name = request.form.get('name', '').strip()
    year = request.form.get('year', '').strip()
    task_ids_text = request.form.get('task_ids', '').strip()

    if not name:
        flash('Введите название варианта')
        return redirect('/tests')

    try:
        year = int(year)
    except (TypeError, ValueError):
        flash('Введите корректный год')
        return redirect('/tests')

    raw_ids = task_ids_text.replace(';', ',').split(',')
    task_ids = []

    for value in raw_ids:
        value = value.strip()
        if not value:
            continue

        try:
            task_id = int(value)
        except ValueError:
            flash(f'Некорректный ID задания: {value}')
            return redirect('/tests')

        if task_id not in task_ids:
            task_ids.append(task_id)

    if not task_ids:
        flash('Добавьте хотя бы одно задание')
        return redirect('/tests')

    conn = get_db()
    cur = conn.cursor()

    try:
        placeholders = ','.join(['%s'] * len(task_ids))
        cur.execute(f'SELECT id FROM tasks WHERE id IN ({placeholders})', tuple(task_ids))

        existing_ids = {row['id'] for row in cur.fetchall()}
        missing_ids = [t_id for t_id in task_ids if t_id not in existing_ids]

        if missing_ids:
            flash('Не найдены задания: ' + ', '.join(map(str, missing_ids)))
            return redirect('/tests')

        cur.execute(
            'INSERT INTO variants(user_id, score, created_at, name, year, is_public) '
            'VALUES(NULL, NULL, %s, %s, %s, TRUE) RETURNING id',
            (datetime.now(), name, year)
        )
        var_id = cur.fetchone()['id']

        for task_id in task_ids:
            cur.execute('''
                INSERT INTO variant_tasks(var_id, task_id, task_number, user_id, user_answer, correct_answer, correct)
                SELECT %s, id, number, NULL, NULL, answer, NULL
                FROM tasks
                WHERE id = %s
            ''', (var_id, task_id))

        conn.commit()
        flash('Вариант успешно добавлен!')
        return redirect('/tests')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@variants_bp.route('/variant/<int:variant_id>')
@regs_only
def view_variant(variant_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            'SELECT id, name, year, created_at FROM variants WHERE id = %s AND is_public = TRUE',
            (variant_id,)
        )
        variant = cur.fetchone()

        if variant is None:
            flash('Вариант не найден')
            return redirect('/tests')

        cur.execute('''
            SELECT tasks.*, variant_tasks.id AS variant_task_id
            FROM variant_tasks
            JOIN tasks ON tasks.id = variant_tasks.task_id
            WHERE variant_tasks.var_id = %s
            ORDER BY variant_tasks.id
        ''', (variant_id,))
        var_tasks = cur.fetchall()

        return render_template(
            'var.html', variant=variant, var_tasks=var_tasks, variant_id=variant_id, is_saved_variant=True
        )
    finally:
        cur.close()
        conn.close()


@variants_bp.route('/delete_variant/<int:variant_id>', methods=['POST'])
@admin_only
def delete_variant(variant_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('SELECT id FROM variants WHERE id = %s', (variant_id,))
        variant = cur.fetchone()

        if variant is None:
            flash('Вариант не найден')
            return redirect('/tests')

        cur.execute('DELETE FROM variant_tasks WHERE var_id = %s', (variant_id,))
        cur.execute('DELETE FROM variants WHERE id = %s', (variant_id,))
        conn.commit()

        flash('Вариант успешно удалён!')
        return redirect('/tests')
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@variants_bp.route('/check_saved_variant/<int:variant_id>', methods=['POST'])
@regs_only
def check_saved_variant(variant_id):
    user_id = session['user_id']

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('SELECT * FROM variants WHERE id = %s AND is_public = TRUE', (variant_id,))
        variant = cur.fetchone()

        if variant is None:
            return jsonify({'success': False, 'error': 'Вариант не найден'}), 404

        cur.execute('''
            SELECT tasks.*
            FROM variant_tasks
            JOIN tasks ON tasks.id = variant_tasks.task_id
            WHERE variant_tasks.var_id = %s
            ORDER BY variant_tasks.id
        ''', (variant_id,))
        var_tasks = cur.fetchall()

        score = 0
        results = []

        for task in var_tasks:
            task_id = task['id']
            user_answer = request.form.get(f'answer_{task_id}', '').strip()
            correct_answer = (task['answer'] or '').strip()
            is_correct = int(user_answer == correct_answer)

            if is_correct:
                score += 1

            results.append({
                'task_id': task_id,
                'task_number': task['number'],
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'correct': is_correct
            })

            record_attempt(cur, user_id, task_id, is_correct)

        cur.execute(
            'INSERT INTO variants(user_id, score, created_at, name, year, is_public) '
            'VALUES(%s, %s, %s, %s, %s, FALSE) RETURNING id',
            (user_id, score, datetime.now(), variant['name'], variant['year'])
        )
        result_variant_id = cur.fetchone()['id']

        for res in results:
            cur.execute('''
                INSERT INTO variant_tasks(var_id, task_id, task_number, user_id, user_answer, correct_answer, correct)
                VALUES(%s, %s, %s, %s, %s, %s, %s)
            ''', (
                result_variant_id, res['task_id'], res['task_number'],
                user_id, res['user_answer'], res['correct_answer'], res['correct']
            ))

        conn.commit()

        return jsonify({
            'success': True,
            'variant_id': variant_id,
            'score': score,
            'total': len(var_tasks),
            'results': results
        })
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@variants_bp.route('/generate_var')
@regs_only
def generate_var():
    conn = get_db()
    cur = conn.cursor()

    try:
        var_tasks = []

        for number in range(1, 20):
            cur.execute('SELECT * FROM tasks WHERE number = %s', (number,))
            t_list = cur.fetchall()

            if t_list:
                var_tasks.append(random.choice(t_list))

        return render_template('var.html', variant=None, var_tasks=var_tasks, is_saved_variant=False)
    finally:
        cur.close()
        conn.close()


@variants_bp.route('/check_var', methods=['POST'])
@regs_only
def check_var():
    conn = get_db()
    cur = conn.cursor()

    try:
        task_ids = request.form.getlist('task_id')
        score = 0
        answers = []

        for task_id in task_ids:
            cur.execute('SELECT * FROM tasks WHERE id = %s', (task_id,))
            task = cur.fetchone()

            if task is None:
                continue

            user_answer = request.form.get(f'answer_{task_id}', '').strip()
            correct = (task['answer'] or '').strip()
            is_correct = int(user_answer == correct)

            if is_correct:
                score += 1

            answers.append({
                'task_id': task_id,
                'task_number': task['number'],
                'user_answer': user_answer,
                'correct_answer': correct,
                'correct': is_correct
            })

        cur.execute(
            'INSERT INTO variants(user_id, score, created_at, name, year, is_public) '
            'VALUES(%s, %s, %s, %s, %s, FALSE) RETURNING id',
            (session['user_id'], score, datetime.now(), 'Сгенерированный вариант', datetime.now().year)
        )
        var_id = cur.fetchone()['id']

        for ans in answers:
            cur.execute('''
                INSERT INTO variant_tasks(var_id, task_id, task_number, user_id, user_answer, correct_answer, correct)
                VALUES(%s, %s, %s, %s, %s, %s, %s)
            ''', (
                var_id, ans['task_id'], ans['task_number'],
                session['user_id'], ans['user_answer'], ans['correct_answer'], ans['correct']
            ))

        conn.commit()
        return {'score': score, 'total': len(task_ids)}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()