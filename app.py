from flask import Flask,render_template,request,redirect,session
import sqlite3
app=Flask(__name__)
app.secret_key='12345'

def init_db():
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT,
            goal INTEGER DEFAULT 0,
            role TEXT DEFAULT 'user'
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks(
                id INTEGER PRIMARY KEY,
                number INTEGER,
                source TEXT,
                text TEXT,
                answer TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENt,
        user_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        
        status TEXT,
        UNIQUE(user_id,task_id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        role='user'
        if username=='myr':
            role='admin'
        cur.execute('INSERT INTO users(username, password, role) VALUES (?, ?, ?)', (username, password, role))
        conn.commit()
        conn.close()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error=None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cur.fetchone()
        conn.close()
        if user:
            session['user'] = username
            session['role']=user[4]
            session['user_id']=user[0]
            return redirect('/')
        else:
            error='Неверный логин или пароль'
    return render_template('login.html', error=error)

@app.route('/')
def home():
    if 'user' in session:
        return render_template('index.html', goal=get_goal())
    return redirect('/login')

@app.route('/profile',methods=['GET','POST'])
def profile():
    if 'user' not in session:
        return redirect('/login')
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    if request.method=='POST':
        goal=request.form['goal']
        cur.execute(
            'UPDATE users SET goal=? WHERE username=?',
            (goal, session['user'],)
        )
        conn.commit()
    cur.execute(
        'SELECT goal FROM users WHERE username=?',
        (session['user'],)
    )
    data=cur.fetchone()
    conn.close()
    goal=data[0] if data else 0
    return render_template('profile.html',username=session['user'], goal=goal)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def get_goal():
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    cur.execute(
        'SELECT goal FROM users WHERE username=?',
        (session['user'],)
    )
    data=cur.fetchone()
    conn.close()
    return data[0] if data else 0


@app.route('/add_tasks', methods=['GET','POST'])
def get_task():
    print('METHOD:', request.method)
    if request.method=='POST':
        number=request.form['number']
        source=request.form['source']
        text=request.form['text']
        answer=request.form['answer']
        conn=sqlite3.connect('users.db')
        cur=conn.cursor()
        cur.execute(
            'INSERT INTO tasks(number, source, text, answer) VALUES(?,?,?,?)',
            (number,source,text,answer)
        )
        conn.commit()
        conn.close()
        return redirect('/tasks')
    return render_template('add_tasks.html')

@app.route('/tasks')
def tasks():
    user_id=session.get('user_id')
    if user_id is None:
        return redirect('/login')
    conn=sqlite3.connect('users.db')
    conn.row_factory=sqlite3.Row
    cur=conn.cursor()
    cur.execute('''
        SELECT tasks.*, COALESCE(user_tasks.status,'Задача еще не решена') AS status 
        FROM tasks
        LEFT JOIN user_tasks ON tasks.id=user_tasks.task_id
        AND user_tasks.user_id=?
    ''',(user_id,))
    tasks=cur.fetchall()
    conn.close()
    return render_template('tasks.html', tasks=tasks)

@app.route('/check_answer/<int:task_id>', methods=['POST'])
def check_answer(task_id):
    data = request.get_json()
    user_answer = data.get('answer')
    user_id = session.get('user_id')
    if user_id is None:
        return {
            'result': 'red',
            'text': 'Сначала войдите в аккаунт'
        }
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute(
        'SELECT answer FROM tasks WHERE id=?',
        (task_id,)
    )
    correct = cur.fetchone()
    if correct is None:
        conn.close()
        return {
            'result': 'red',
            'text': 'задача не найдена'
        }
    if user_answer.strip() == correct[0].strip():
        status='Правильно!'
        result='correct'
    else:
        status='Неправильно!'
        result='wrong'
    cur.execute('''
        INSERT INTO user_tasks(user_id,task_id,status) VALUES(?,?,?)
        ON CONFLICT(user_id, task_id)
        DO UPDATE SET  status=excluded.status
    ''', (user_id, task_id, status))
    conn.commit()
    conn.close()
    return {
        'result':result,
        'text':status
    }
    
    
@app.route('/delete_task/<int:task_id>',methods=['POST'])    
def delete_task(task_id):
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    cur.execute(
        'DELETE FROM tasks WHERE id=?',
        (task_id,)
    )
    conn.commit()
    conn.close()
    return redirect('/tasks')

@app.route('/project')
def project():
    with open('static/texts/about.txt','r',encoding='utf-8') as f:
        about_text=f.read()
    with open('static/texts/functions.txt','r',encoding='utf-8') as f:
        functions_text=f.read()
    with open('static/texts/story.txt','r',encoding='utf-8') as f:
        story_text=f.read()
    return render_template(
        'project.html',
        about_text=about_text,
        functions_text=functions_text,
        story_text=story_text
    )

@app.route('/mistakes')
def mistakes():
    user_id=session.get('user_id')
    if user_id is None:
        return redirect('/login')
    conn=sqlite3.connect('users.db')
    conn.row_factory=sqlite3.Row
    cur=conn.cursor()
    cur.execute('''
        SELECT tasks.* FROM tasks JOIN user_tasks ON tasks.id=user_tasks.task_id WHERE user_tasks.user_id=?''',(user_id,)
    )
    tasks=cur.fetchall()
    conn.close()
    return render_template('mistakes.html', tasks=tasks)

@app.route('/error')
def error():
    return render_template('error.html')


init_db()
app.run(debug=True)