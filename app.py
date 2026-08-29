# from flask import Flask,render_template,request,redirect,session,flash, jsonify
# import sqlite3
# import os
# from PIL import Image
# from functools import wraps
# from datetime import datetime
# from werkzeug.security import generate_password_hash, check_password_hash
# import random


# app=Flask(__name__)
# app.config['MAX_CONTENT_LENGTH']=8*1024*1024
# ALLOWED_IMAGES={'png','jpg','jpeg'}
# ALLOWED_PDFS={'pdf'}

# app.secret_key=os.environ.get('secret_key')
# app.secret_key='12345'

# def admin_only(f):
#     @wraps(f)
#     def wrapper(*args,**kwags):
#         if session.get('role') != 'admin':
#             return redirect('/')
#         return f(*args,**kwags)
#     return wrapper

# def regs_only(f):
#     @wraps(f)
#     def wrapper(*args,**kwags):
#         if 'user_id' not in session:
#             return redirect('/login')
#         return f(*args,**kwags)
#     return wrapper

# def init_db():
#     conn=sqlite3.connect('users.db')
#     cur=conn.cursor()
#     cur.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             username TEXT,
#             password TEXT,
#             goal INTEGER DEFAULT 0,
#             role TEXT DEFAULT 'user',
#             avatar TEXT
#         )
#     ''')
#     cur.execute('''
#         CREATE TABLE IF NOT EXISTS tasks(
#             id INTEGER PRIMARY KEY,
#             number INTEGER,
#             source TEXT,
#             text TEXT,
#             solution TEXT,
#             answer TEXT
#         )
#     ''')
#     cur.execute('''
#         CREATE TABLE IF NOT EXISTS user_tasks(
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER NOT NULL,
#             task_id INTEGER NOT NULL,
#             status TEXT,
#             UNIQUE(user_id,task_id)
#         )
#     ''')
#     cur.execute('''
#         CREATE TABLE IF NOT EXISTS theory_table(
#             block_id INTEGER PRIMARY KEY,
#             title TEXT,
#             task_number INTEGER,
#             text TEXT,
#             pdf_path TEXT
#         )
#     ''')
#     cur.execute('''
#         CREATE TABLE IF NOT EXISTS task_attempts (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             task_id INTEGER,
#             user_id INTEGER,
#             correct INTEGER,
#             attempt_number INTEGER
#         )
#     ''')
#     cur.execute('''
#         CREATE TABLE IF NOT EXISTS variants (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER,
#             score INTEGER,
#             created_at
#         )
#     ''')
#     cur.execute('''
#         CREATE TABLE IF NOT EXISTS variant_tasks (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             var_id INTEGER,
#             task_id INTEGER,
#             task_number,
#             user_id INTEGER,
#             user_answer TEXT,
#             correct_answer TEXT,
#             correct NUMBER
#         )
#     ''')
#     conn.commit()
#     conn.close()


# @app.route('/register', methods=["GET", "POST"])
# def register():
#     error=None
#     if request.method == "POST":
#         username = request.form['username']
#         password = request.form['password']
#         conn = sqlite3.connect('users.db')
#         conn.row_factory=sqlite3.Row
#         cur = conn.cursor()
#         cur.execute('SELECT * FROM users WHERE username=?',(username,))
#         user=cur.fetchone()
#         if user:
#             conn.close()
#             error='Упс! Этот логин уже занят'
#             return render_template('register.html',error=error)
#         role='user'
#         if username=='myr':
#             role='admin'
#         reg_date=datetime.now().strftime('%d.%m.%Y')
#         password=generate_password_hash(password, method='pbkdf2:sha256')
#         cur.execute('INSERT INTO users(username, password, role, reg_date) VALUES (?, ?, ?, ?)', (username, password, role, reg_date))
#         conn.commit()
#         conn.close()
#         return redirect('/login')
#     return render_template('register.html')


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     error=None
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         conn = sqlite3.connect('users.db')
#         conn.row_factory = sqlite3.Row
#         cur = conn.cursor()
#         cur.execute('SELECT * FROM users WHERE username=?', (username,))
#         user = cur.fetchone()
#         # conn.close()
#         if user:
#             if not str(user['password']).startswith('pbkdf2:'):
#                 if user['password'] == password:
#                     new_hash = generate_password_hash(password,method='pbkdf2:sha256')
#                     cur.execute(
#                         "UPDATE users SET password=? WHERE id=?",
#                         (new_hash, user['id'])
#                     )
#                     conn.commit()
#                     session['user'] = username
#                     session['role'] = user['role']
#                     session['user_id'] = user['id']
#                     conn.close()
#                     return redirect('/')
#                 else:
#                     error = 'Упс! Неверный логин или пароль'
#             else:
#                 if check_password_hash(user['password'], password):
#                     session['user'] = username
#                     session['role'] = user['role']
#                     session['user_id'] = user['id']
#                     conn.close()
#                     return redirect('/')
#                 else:
#                     error = 'Упс! Неверный логин или пароль'
#         else:
#             error='Упс! Неверный логин или пароль'
#             return render_template('login.html', error=error)
#         conn.close()
#     return render_template('login.html',error=error)


# def allowed_file(filename, allowed_set):
#     return '.' in filename and filename.rsplit('.',1)[1].lower() in allowed_set


# @app.route('/upload_avatar',methods=['POST'])
# @regs_only
# def upload_avatar():
#     file=request.files['avatar']
#     if not file or file.filename=='':
#         return redirect ('/profile')
#     if not allowed_file(file.filename, ALLOWED_IMAGES):
#         return 'Выберите изображение формата png, jpg или jpeg'
#     ext=file.filename.rsplit('.',1)[1].lower()
#     filename=f'user_{session["user_id"]}.{ext}'
#     path=os.path.join('static','avatars',filename)
#     base=f'user_{session["user_id"]}'
#     for old in ALLOWED_IMAGES:
#         old_path=os.path.join('static','avatars',f'{base}.{old}')
#         if os.path.exists(old_path):
#             os.remove(old_path)
#     img=crop(Image.open(file))
#     new_width=250
#     rati=new_width/img.width
#     new_height=int(img.height*rati)
#     img=img.resize((new_width,new_height))
#     img.save(path)
#     conn=sqlite3.connect('users.db')
#     cur=conn.cursor()
#     cur.execute(
#         'UPDATE users SET avatar=? WHERE id=?',
#         (f'avatars/{filename}', session['user_id'])
#     )
#     conn.commit()
#     conn.close()
#     return redirect('/profile')


# def crop(img):
#     width,height=img.size
#     target=4/5
#     current=width/height
#     if current>target:
#         new_width=int(height*target)
#         left=(width-new_width)//2
#         img=img.crop((left,0,left+new_width,height))
#     else:
#         new_height=int(width/target)
#         top=(height-new_height)//2
#         img=img.crop((0,top,width,top+new_height))
#     return img


# @app.route('/')
# @regs_only
# def home():
#     if 'user' in session:
#         conn=sqlite3.connect('users.db')
#         conn.row_factory=sqlite3.Row
#         cur=conn.cursor()
#         cur.execute('SELECT * FROM users WHERE id=?',(session['user_id'],))
#         user=cur.fetchone()
#         conn.close()
#         if user is None:
#             session.clear()
#             return redirect('/login')
#         goal=user['goal']
#         solved_count=all_count(session['user_id'])
#         correct=correct_count(session['user_id'])
#         percent=int((correct/solved_count)*100) if solved_count else 0
#         return render_template('index.html', goal=goal,user=user,solved_count=solved_count,correct=correct,percent=percent)
#     return redirect('/login')


# @app.route('/profile',methods=['GET','POST'])
# @regs_only
# def profile():
#     if 'user_id' not in session:
#         return redirect('/login')
#     conn=sqlite3.connect('users.db')
#     conn.row_factory=sqlite3.Row
#     cur=conn.cursor()
#     if request.method=='POST':
#         goal=request.form['goal']
#         cur.execute(
#             'UPDATE users SET goal=? WHERE id=?',
#             (goal, session['user_id'],)
#         )
#         conn.commit()
#     cur.execute(
#         'SELECT * FROM users WHERE id=?',
#         (session['user_id'],)
#     )
#     user=cur.fetchone()
#     conn.close()
#     return render_template('profile.html',username=session['user'], user=user)


# @app.route('/change_profile', methods=['POST'])
# @regs_only
# def change_profile():
#     error=None
#     conn = sqlite3.connect('users.db')
#     conn.row_factory = sqlite3.Row
#     cur = conn.cursor()
#     cur.execute(
#         'SELECT * FROM users WHERE id=?',
#         (session['user_id'],)
#     )
#     user = cur.fetchone()
#     username = request.form['username'].strip()
#     old_password = request.form['old_password']
#     new_password = request.form['new_password']
#     repeat_password = request.form['repeat_password']
#     if username != user['username']:
#         cur.execute(
#             'SELECT id FROM users WHERE username=?',
#             (username,)
#         )
#         if cur.fetchone():
#             error='Упс! Такой логин уже существует!'
#             flash(error)
#             return redirect('/profile')
#         cur.execute(
#             'UPDATE users SET username=? WHERE id=?',
#             (username, session["user_id"])
#         )
#     if new_password:
#         if not check_password_hash(user['password'], old_password):
#             error='Упс! Неверный пароль!'
#             flash(error)
#             return redirect('/profile')
#         if new_password != repeat_password:
#             error='Упс! Пароли не совпадают'
#             flash(error)
#             return redirect('/profile')
#         if session['user']=='testacc':
#             error='Упс! Это тестовый аккаунт'
#             flash(error)
#             return redirect('/profile')
#         cur.execute(
#             'UPDATE users SET password=? WHERE id=?',
#             (generate_password_hash(new_password,method='pbkdf2:sha256'), session['user_id'])
#         )
#     conn.commit()
#     conn.close()
#     print(user['username'],old_password,new_password)
#     return redirect('/profile')

# @app.route('/logout')
# def logout():
#     session.clear()
#     return redirect('/login')

# def get_goal():
#     conn=sqlite3.connect('users.db')
#     cur=conn.cursor()
#     cur.execute(
#         'SELECT goal FROM users WHERE username=?',
#         (session['user'],)
#     )
#     data=cur.fetchone()
#     conn.close()
#     return data[0] if data else 0


# @app.route('/add_task', methods=['POST'])
# @admin_only
# def add_task():
#     error=None
#     if request.method=='POST':
#         number=request.form['number']
#         source=request.form['source']
#         text=request.form['text']
#         solution=request.form['solution']
#         image=request.files.get('image')
#         answer=request.form['answer']
#         conn=sqlite3.connect('users.db')
#         cur=conn.cursor()
#         cur.execute(
#             'INSERT INTO tasks(number, source, text, solution, answer) VALUES(?,?,?,?,?)',
#             (number,source,text,solution,answer)
#         )
#         task_id=cur.lastrowid
#         image_path=None
#         if image and image.filename!='':
#             if not allowed_file(image.filename, ALLOWED_IMAGES):
#                 error='Упс! Неверный формат изображения!'
#                 flash(error)
#                 return redirect('/profile')
#             ext=image.filename.rsplit('.',1)[1].lower()
#             image_name=f'task_{task_id}.{ext}'
#             folder=os.path.join('static','task_images')
#             os.makedirs(folder, exist_ok=True)
#             path=os.path.join(folder, image_name)
#             image.save(path)
#             image_path=f'task_images/{image_name}'
#             cur.execute(
#                 'UPDATE tasks SET image=? WHERE id=?',(image_path,task_id)
#             )
#         conn.commit()
#         conn.close()
#     return redirect('/tasks')

# @app.route('/edit_task/<int:task_id>', methods=['POST'])
# def edit_task(task_id):
#     if request.method=='POST':
#         number=request.form['number']
#         source=request.form['source']
#         text=request.form['text']
#         solution=request.form['solution']
#         answer=request.form['answer']
#         image=request.files.get('image')
#         conn=sqlite3.connect('users.db')
#         cur=conn.cursor()
#         cur.execute(
#             'UPDATE tasks SET number=?, source=?, text=?, solution=?, answer=? WHERE id=?',
#             (number,source,text,solution,answer,task_id)
#         )
#         conn.commit()
#         conn.close()
#     return redirect('/tasks')


# @app.route('/tasks')
# @regs_only
# def tasks():
#     user_id=session.get('user_id')
#     if user_id is None:
#         return redirect('/login')
#     number=request.args.get('number')
#     task_id=request.args.get('task_id')
#     conn=sqlite3.connect('users.db')
#     conn.row_factory=sqlite3.Row
#     cur=conn.cursor()
#     query='''
#         SELECT tasks.*, COALESCE(user_tasks.status,'Задача еще не решена') AS status FROM tasks
#         LEFT JOIN user_tasks
#         ON tasks.id=user_tasks.task_id
#         AND user_tasks.user_id=?
#         WHERE 1=1
#     '''
#     options=[user_id]
#     if number:
#         query+='AND tasks.number=?'
#         options.append(number)
#     if task_id:
#         query+='AND tasks.id=?'
#         options.append(task_id)
#     cur.execute(query, options)
#     tasks=cur.fetchall()
#     cur.execute('''
#         SELECT task_id, COUNT(*) AS total, SUM(CASE WHEN attempt_number=1 AND correct=1 THEN 1 ELSE 0 END) AS correct_first_attempts
#         FROM task_attempts
#         GROUP BY task_id
#     ''')
#     stats_raw=cur.fetchall()
#     stats={}
#     for r in stats_raw:
#         task_id=r['task_id']
#         total=r[1]
#         first_attempts=r[2]
#         percent=(first_attempts/total)*100 if total>0 else 0
#         stats[task_id]=round(percent,2)
#     conn.close()
#     return render_template('tasks.html', tasks=tasks, stats=stats)


# @app.route('/check_answer/<int:task_id>', methods=['POST'])
# def check_answer(task_id):
#     data = request.get_json()
#     user_answer = data.get('answer')
#     user_id = session.get('user_id')
#     if user_id is None:
#         return {
#             'result': 'red',
#             'text': 'Сначала войдите в аккаунт'
#         }
#     conn = sqlite3.connect('users.db')
#     cur = conn.cursor()
#     cur.execute(
#         'SELECT answer FROM tasks WHERE id=?',
#         (task_id,)
#     )
#     correct = cur.fetchone()
#     if correct is None:
#         conn.close()
#         return {
#             'result': 'red',
#             'text': 'задача не найдена'
#         }
#     is_correct = int(user_answer.strip() == correct[0].strip())
#     if is_correct:
#         status='Правильно!'
#         result='correct'
#     else:
#         status='Неправильно!'
#         result='wrong'
#     cur.execute('''
#         SELECT COUNT(*) FROM task_attempts WHERE user_id=? AND task_id=?
#     ''', (user_id,task_id))
#     attempt_number = cur.fetchone()[0] + 1
#     cur.execute('''
#         INSERT INTO task_attempts(user_id,task_id,correct,attempt_number) VALUES(?,?,?,?)
#     ''', (user_id,task_id,is_correct,attempt_number))
#     cur.execute('''
#         INSERT INTO user_tasks(user_id,task_id,status) VALUES(?,?,?)
#         ON CONFLICT(user_id, task_id)
#         DO UPDATE SET  status=excluded.status
#     ''', (user_id, task_id, status))
#     conn.commit()
#     conn.close()
#     return {
#         'result':result,
#         'text':status,
#         'attempt_number':attempt_number
#     }
    
    
# @app.route('/delete_task/<int:task_id>',methods=['POST'])    
# def delete_task(task_id):
#     conn=sqlite3.connect('users.db')
#     cur=conn.cursor()
#     cur.execute(
#         'DELETE FROM tasks WHERE id=?',
#         (task_id,)
#     )
#     conn.commit()
#     conn.close()
#     return redirect('/tasks')


# @app.route('/about')
# @regs_only
# def about():
#     with open('static/texts/about.txt','r',encoding='utf-8') as f:
#         about_text=f.read()
#     with open('static/texts/functions.txt','r',encoding='utf-8') as f:
#         functions_text=f.read()
#     with open('static/texts/forWho.txt','r', encoding='utf-8') as f:
#         forWho_text=f.read()
#     with open('static/texts/include.txt', 'r', encoding='utf-8') as f:
#         include_text=f.read()
#     return render_template(
#         'about.html',
#         about_text=about_text,
#         functions_text=functions_text,
#         forWho_text=forWho_text,
#         include_text=include_text
#     )


# @app.route('/mistakes')
# @regs_only
# def mistakes():
#     user_id=session.get('user_id')
#     if user_id is None:
#         return redirect('/login')
#     conn=sqlite3.connect('users.db')
#     conn.row_factory=sqlite3.Row
#     cur=conn.cursor()
#     cur.execute('''
#         SELECT tasks.* FROM tasks JOIN user_tasks ON tasks.id=user_tasks.task_id WHERE user_tasks.user_id=?
#         AND user_tasks.status="Неправильно!"''',(user_id,)
#     )
#     tasks=cur.fetchall()
#     conn.close()
#     return render_template('mistakes.html', tasks=tasks)


# @app.route('/error')
# @regs_only
# def error():
#     return render_template('error.html')


# @app.route('/statistics')
# @regs_only
# def statistics():
#     if 'user_id' not in session:
#         return redirect('/login')
#     conn=sqlite3.connect('users.db')
#     conn.row_factory=sqlite3.Row
#     cur=conn.cursor()
#     cur.execute(
#         'SELECT * FROM users WHERE id=?',
#         (session['user_id'],)
#     )
#     user=cur.fetchone()
#     solved_count=all_count(session['user_id'])
#     correct=correct_count(session['user_id'])
#     goal=user['goal']
#     percent=int((correct/solved_count)*100) if solved_count else 0
#     cur.execute('''
#         SELECT tasks.number, ROUND(100*SUM(CASE WHEN user_tasks.status LIKE 'Правильно!' THEN 1 ELSE 0 END)/COUNT(*), 1) AS percent
#         FROM user_tasks JOIN tasks ON user_tasks.task_id=tasks.id 
#         WHERE user_tasks.user_id=?
#         GROUP BY tasks.number
#         ORDER BY tasks.number 
#     ''', (session['user_id'],))
#     data=cur.fetchall()
#     for row in data:
#         print(dict(row))
#     numbers=[row['number'] for row in data]
#     percents=[row['percent'] for row in data]
#     cur.execute('''
#         SELECT tasks.number, COUNT(*) AS total, SUM(CASE WHEN task_attempts.attempt_number=1 AND task_attempts.correct=1 THEN 1 ELSE 0 END) AS correct_first_attempts
#         FROM task_attempts JOIN tasks ON tasks.id=task_attempts.task_id
#         WHERE task_attempts.user_id=?
#         GROUP BY tasks.number
#         ORDER BY tasks.number
#     ''', (session['user_id'],))
#     raw=cur.fetchall()
#     first_attempts_numbers=[]
#     first_attempts_percents=[]
#     for r in raw:
#         number=r['number']
#         total=r['total']
#         first_attempts=r['correct_first_attempts']
#         percent_first=(first_attempts/total)*100 if total>0 else 0
#         first_attempts_numbers.append(number)
#         first_attempts_percents.append(round(percent_first,2))
#     cur.execute('''
#         SELECT 
#             variant_tasks.var_id,
#             tasks.number AS task_number,
#             variant_tasks.task_id,
#             variant_tasks.user_answer,
#             variant_tasks.correct_answer,
#             variant_tasks.correct,
#             variants.score,
#             variants.created_at
#         FROM variant_tasks
#         JOIN variants
#         ON variant_tasks.var_id=variants.id
#         JOIN tasks
#         ON variant_tasks.task_id=tasks.id
#         WHERE variants.user_id=?
#         ORDER BY variant_tasks.var_id, tasks.number
#     ''', (session['user_id'],)
#     )
#     variant_data=cur.fetchall()
#     variant_table={}
#     for row in variant_data:
#         var_id=row['var_id']
#         if var_id not in variant_table:
#             variant_table[var_id]={
#                 'score':row['score'],
#                 'created_at':row['created_at'],
#                 'tasks':{}
#             }
#         variant_table[var_id]['tasks'][row['task_number']]={
#             'task_id':row['task_id'],
#             'answer':row['user_answer'],
#             'correct_answer': row['correct_answer'],
#             'correct':row['correct']
#         }
#     conn.close()
#     return render_template(
#         'statistics.html', 
#         user=user, 
#         solved_count=solved_count,
#         correct=correct,
#         goal=goal,
#         percent=percent,
#         numbers=numbers,
#         percents=percents,
#         first_attempts_numbers=first_attempts_numbers,
#         first_attempts_percents=first_attempts_percents,
#         variant_table=variant_table)


# def all_count(user_id):
#     conn=sqlite3.connect('users.db')
#     cur=conn.cursor()
#     cur.execute('''
#         SELECT COUNT(*) FROM user_tasks WHERE user_id=?
#     ''', (user_id,))
#     count=cur.fetchone()[0]
#     conn.close()
#     return count


# def correct_count(user_id):
#     conn=sqlite3.connect('users.db')
#     cur=conn.cursor()
#     cur.execute('''
#         SELECT COUNT(*) FROM user_tasks WHERE user_id=? AND status LIKE "Правильно%"
#     ''',(user_id,))
#     count=cur.fetchone()[0]
#     conn.close()
#     return count


# @app.route('/add_theory', methods=['GET','POST'])
# @admin_only
# def add_theory():
#     if request.method=='POST':
#         title=request.form['title']
#         task_number=request.form['task_number']
#         text=request.form['text']
#         pdf=request.files.get('pdf')
#         pdf_path=None
#         if pdf:
#             pdf_path=f'static/theory/{pdf.filename}'
#             pdf.save(pdf_path)
#         conn=sqlite3.connect('users.db')
#         cur=conn.cursor()
#         cur.execute('''
#             INSERT INTO theory_table(title,task_number,text,pdf_path) VALUES(?,?,?,?)
#         ''',(title,task_number,text,pdf_path))
#         conn.commit()
#         conn.close()
#     return redirect('/theory')


# @app.route('/theory')
# @regs_only
# def theory():
#     conn=sqlite3.connect('users.db')
#     conn.row_factory=sqlite3.Row 
#     cur=conn.cursor()
#     cur.execute('SELECT block_id, title, task_number, text, pdf_path FROM theory_table')
#     blocks=cur.fetchall()
#     conn.close()
#     return render_template('theory.html', blocks=blocks)


# @app.route('/delete_theory/<int:theory_id>',methods=['POST'])
# @admin_only
# def delete_theory(theory_id):
#     conn=sqlite3.connect('users.db')
#     cur=conn.cursor()
#     cur.execute(
#         'DELETE FROM theory_table WHERE block_id=?',
#         (theory_id,)
#     )
#     conn.commit()
#     conn.close()
#     return redirect('/theory')

# @app.route('/edit_theory/<int:block_id>',methods=['POST'])
# @admin_only
# def edit_theory(block_id):
#     title=request.form['title']
#     task_number=request.form['task_number']
#     text=request.form['text']
#     conn=sqlite3.connect('users.db')
#     cur=conn.cursor()
#     cur.execute('''
#         UPDATE theory_table SET title=?, task_number=?, text=? WHERE block_id=?
#     ''',(title,task_number,text,block_id))
#     conn.commit()
#     conn.close()
#     return redirect('/theory')

# @app.route('/privacypolicy')
# def privacypolicy():
#     with open('static/texts/policy.txt','r',encoding='utf-8') as f:
#         policy_text=f.read()
#     return render_template('privacypolicy.html',policy_text=policy_text)

# @app.route('/tests')
# @regs_only
# def tests():
#     return render_template('tests.html')

# @app.route('/generate_var')
# @regs_only
# def generate_var():
#     conn=sqlite3.connect('users.db')
#     conn.row_factory=sqlite3.Row
#     cur=conn.cursor()
#     var_tasks=[]
#     nums=list(range(1,20))
#     for number in nums:
#         cur.execute(
#             'SELECT * FROM tasks WHERE number=?',
#             (number,)
#         )
#         tasks=cur.fetchall()
#         if tasks:
#             var_tasks.append(random.choice(tasks))
#     conn.close()
#     return render_template('var.html', var_tasks=var_tasks)

# # @app.route('/check_var', methods=['POST'])
# # @regs_only
# # def check_var():
# #     conn=sqlite3.connect('users.db')
# #     conn.row_factory=sqlite3.Row
# #     cur=conn.cursor()
# #     task_ids=request.form.getlist('task_id')
# #     results=[]
# #     score=0
# #     cur.execute(
# #         'INSERT INTO variants(user_id, score, total, created_at) VALUES (?, ?, ?, ?)',(session['user_id'], score, datetime.now().strftime("%d.%m.%Y %H:%M")
# #     ))
# #     var_id=cur.lastrowid
# #     for task_id in task_ids:
# #         cur.execute(
# #             'SELECT * FROM tasks WHERE id=?',
# #             (task_id,)
# #         )
# #         task=cur.fetchone()
# #         user_answer=request.form.get(f'answer_{task_id}','').strip()
# #         correct=task['answer'].strip()
# #         if user_answer==correct:
# #             score+=1
# #         cur.execute('''
# #             INSERT INTO var_tasks(
# #                 var_id, task_id,user_id, user_answer, correct_answer, correct
# #             )
# #             VALUES(?,?,?,?,?)
# #         ''')
# #         results.append({
# #             'task':task,
# #             'user_answer':user_answer,
# #             'correct_answer':correct,
# #         })

# #     conn.commit()
# #     conn.close()
# #     return jsonify({
# #         'score':score
# #     })

# @app.route('/check_var', methods=['POST'])
# @regs_only
# def check_var():
#     conn = sqlite3.connect('users.db')
#     conn.row_factory = sqlite3.Row
#     cur = conn.cursor()
#     task_ids = request.form.getlist('task_id')
#     results = []
#     score = 0
#     answers = []
#     for task_id in task_ids:
#         cur.execute(
#             'SELECT * FROM tasks WHERE id=?',
#             (task_id,)
#         )
#         task = cur.fetchone()
#         user_answer = request.form.get(
#             f'answer_{task_id}',
#             ''
#         ).strip()
#         correct = task['answer'].strip()
#         is_correct = int(user_answer == correct)
#         if is_correct:
#             score += 1
#         answers.append({
#             'task_id': task_id,
#             'task_number': task['number'],
#             'user_answer': user_answer,
#             'correct_answer': correct,
#             'correct': is_correct
#         })
#     cur.execute(
#         '''
#         INSERT INTO variants(
#             user_id,
#             score,
#             created_at
#         )
#         VALUES(?,?,?)
#         ''',
#         (
#             session['user_id'],
#             score,
#             datetime.now().strftime("%d.%m.%Y %H:%M")
#         )
#     )
#     var_id = cur.lastrowid
#     for answer in answers:
#         cur.execute(
#             '''
#             INSERT INTO variant_tasks(
#                 var_id,
#                 task_id,
#                 task_number,
#                 user_id,
#                 user_answer,
#                 correct_answer,
#                 correct
#             )
#             VALUES(?,?,?,?,?,?,?)
#             ''',
#             (
#                 var_id,
#                 answer['task_id'],
#                 answer['task_number'],
#                 session['user_id'],
#                 answer['user_answer'],
#                 answer['correct_answer'],
#                 answer['correct']
#             )
#         )
#     conn.commit()
#     conn.close()
#     return {
#         'score': score,
#         'total': len(task_ids)
#     }

# if __name__=='__main__':
#     init_db()
#     app.run(debug=True)

import os
from flask import Flask, session

from database import init_db, get_user_by_id
from rate import get_tariff_info
from routes.payment import payment_bp
from routes.main import main_bp
from routes.auth import auth_bp
from routes.tasks import tasks_bp
from routes.theory import theory_bp


def create_app() -> Flask:
    app = Flask(__name__)

    # Ограничение на размер загружаемых файлов (8 МБ)
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

    # Секретный ключ для сессий
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-12345")

    # ============================================================
    # ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
    # ============================================================
    init_db()

    # ============================================================
    # КОНТЕКСТНЫЕ ПЕРЕМЕННЫЕ ДЛЯ SHABLONOV JINJA2
    # ============================================================
    @app.context_processor
    def inject_user_and_tariff():
        """Автоматически передаёт current_user и tariff_info во все HTML-шаблоны."""
        user_id = session.get("user_id")
        user = get_user_by_id(user_id) if user_id else None
        tariff_info = get_tariff_info(user) if user else None

        return {
            "current_user": user,
            "tariff_info": tariff_info,
        }

    # ============================================================
    # РЕГИСТРАЦИЯ BLUEPRINTS
    # ============================================================
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(theory_bp)
    app.register_blueprint(payment_bp)

    return app


# Точка входа для локального запуска приложения
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)