from flask import Flask,render_template,request,redirect,session
import sqlite3
import os
from PIL import Image
from functools import wraps


app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=8*1024*1024
ALLOWED_IMAGES={'png','jpg','jpeg'}
ALLOWED_PDFS={'pdf'}

app.secret_key=os.environ.get('secret_key')
app.secret_key='12345'

def admin_only(f):
    @wraps(f)
    def wrapper(*args,**kwags):
        if session.get('role') != 'admin':
            return redirect('/')
        return f(*args,**kwags)
    return wrapper

def regs_only(f):
    @wraps(f)
    def wrapper(*args,**kwags):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args,**kwags)
    return wrapper

def init_db():
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            goal INTEGER DEFAULT 0,
            role TEXT DEFAULT 'user',
            avatar TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY,
            number INTEGER,
            source TEXT,
            text TEXT,
            solution TEXT,
            answer TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            status TEXT,
            UNIQUE(user_id,task_id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS theory_table(
            block_id INTEGER PRIMARY KEY,
            title TEXT,
            task_number INTEGER,
            text TEXT,
            pdf_path TEXT
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
        cur.execute('SELECT * FROM users WHERE username=?',(username,))
        user=cur.fetchone()
        if user:
            conn.close()
            return render_template('register.html',error='Упс! Этот логин уже занят')
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
            error='Упс! Неверный логин или пароль'
    return render_template('login.html', error=error)


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in allowed_set


@app.route('/upload_avatar',methods=['POST'])
@regs_only
def upload_avatar():
    file=request.files['avatar']
    if not file or file.filename=='':
        return redirect ('/profile')
    if not allowed_file(file.filename, ALLOWED_IMAGES):
        return 'Выберите изображение формата png, jpg или jpeg'
    ext=file.filename.rsplit('.',1)[1].lower()
    filename=f'user_{session["user_id"]}.{ext}'
    path=os.path.join('static','avatars',filename)
    base=f'user_{session["user_id"]}'
    for old in ALLOWED_IMAGES:
        old_path=os.path.join('static','avatars',f'{base}.{old}')
        if os.path.exists(old_path):
            os.remove(old_path)
    img=crop(Image.open(file))
    new_width=250
    rati=new_width/img.width
    new_height=int(img.height*rati)
    img=img.resize((new_width,new_height))
    img.save(path)
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    cur.execute(
        'UPDATE users SET avatar=? WHERE id=?',
        (f'avatars/{filename}', session['user_id'])
    )
    conn.commit()
    conn.close()
    return redirect('/profile')


def crop(img):
    width,height=img.size
    target=4/5
    current=width/height
    if current>target:
        new_width=int(height*target)
        left=(width-new_width)//2
        img=img.crop((left,0,left+new_width,height))
    else:
        new_height=int(width/target)
        top=(height-new_height)//2
        img=img.crop((0,top,width,top+new_height))
    return img


@app.route('/')
@regs_only
def home():
    if 'user' in session:
        conn=sqlite3.connect('users.db')
        conn.row_factory=sqlite3.Row
        cur=conn.cursor()
        cur.execute('SELECT * FROM users WHERE id=?',(session['user_id'],))
        user=cur.fetchone()
        conn.close()
        goal=user['goal']
        solved_count=all_count(session['user_id'])
        correct=correct_count(session['user_id'])
        percent=int((correct/solved_count)*100) if solved_count else 0
        return render_template('index.html', goal=goal,user=user,solved_count=solved_count,correct=correct,percent=percent)
    return redirect('/login')


@app.route('/profile',methods=['GET','POST'])
@regs_only
def profile():
    if 'user_id' not in session:
        return redirect('/login')
    conn=sqlite3.connect('users.db')
    conn.row_factory=sqlite3.Row
    cur=conn.cursor()
    if request.method=='POST':
        goal=request.form['goal']
        cur.execute(
            'UPDATE users SET goal=? WHERE id=?',
            (goal, session['user_id'],)
        )
        conn.commit()
    cur.execute(
        'SELECT * FROM users WHERE id=?',
        (session['user_id'],)
    )
    user=cur.fetchone()
    conn.close()
    return render_template('profile.html',username=session['user'], user=user)


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
@admin_only
def add_task():
    if request.method=='POST':
        number=request.form['number']
        source=request.form['source']
        text=request.form['text']
        solution=request.form['solution']
        answer=request.form['answer']
        conn=sqlite3.connect('users.db')
        cur=conn.cursor()
        cur.execute(
            'INSERT INTO tasks(number, source, text,solution, answer) VALUES(?,?,?,?,?)',
            (number,source,text,solution,answer)
        )
        conn.commit()
        conn.close()
        return redirect('/tasks')
    return render_template('add_tasks.html')

@app.route('/tasks')
@regs_only
def tasks():
    user_id=session.get('user_id')
    if user_id is None:
        return redirect('/login')
    number=request.args.get('number')
    task_id=request.args.get('task_id')
    conn=sqlite3.connect('users.db')
    conn.row_factory=sqlite3.Row
    cur=conn.cursor()
    query='''
        SELECT tasks.*, COALESCE(user_tasks.status,'Задача еще не решена') AS status FROM tasks
        LEFT JOIN user_tasks
        ON tasks.id=user_tasks.task_id
        AND user_tasks.user_id=?
        WHERE 1=1
    '''
    options=[user_id]
    if number:
        query+='AND tasks.number=?'
        options.append(number)
    if task_id:
        query+='AND tasks.id=?'
        options.append(task_id)
    cur.execute(query, options)
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
@regs_only
def project():
    with open('static/texts/about.txt','r',encoding='utf-8') as f:
        about_text=f.read()
    with open('static/texts/functions.txt','r',encoding='utf-8') as f:
        functions_text=f.read()
    with open('static/texts/story.txt','r',encoding='utf-8') as f:
        story_text=f.read()
    with open('static/texts/forWho.txt','r', encoding='utf-8') as f:
        forWho_text=f.read()
    return render_template(
        'project.html',
        about_text=about_text,
        functions_text=functions_text,
        story_text=story_text,
        forWho_text=forWho_text
    )

@app.route('/about')
@regs_only
def about():
    with open('static/texts/about.txt','r',encoding='utf-8') as f:
        about_text=f.read()
    with open('static/texts/functions.txt','r',encoding='utf-8') as f:
        functions_text=f.read()
    with open('static/texts/forWho.txt','r', encoding='utf-8') as f:
        forWho_text=f.read()
    with open('static/texts/include.txt', 'r', encoding='utf-8') as f:
        include_text=f.read()
    return render_template(
        'about.html',
        about_text=about_text,
        functions_text=functions_text,
        forWho_text=forWho_text,
        include_text=include_text
    )


@app.route('/mistakes')
@regs_only
def mistakes():
    user_id=session.get('user_id')
    if user_id is None:
        return redirect('/login')
    conn=sqlite3.connect('users.db')
    conn.row_factory=sqlite3.Row
    cur=conn.cursor()
    cur.execute('''
        SELECT tasks.* FROM tasks JOIN user_tasks ON tasks.id=user_tasks.task_id WHERE user_tasks.user_id=?
        AND user_tasks.status="Неправильно!"''',(user_id,)
    )
    tasks=cur.fetchall()
    conn.close()
    return render_template('mistakes.html', tasks=tasks)


@app.route('/error')
@regs_only
def error():
    return render_template('error.html')


@app.route('/statistics')
@regs_only
def statistics():
    if 'user_id' not in session:
        return redirect('/login')
    conn=sqlite3.connect('users.db')
    conn.row_factory=sqlite3.Row
    cur=conn.cursor()
    cur.execute(
        'SELECT * FROM users WHERE id=?',
        (session['user_id'],)
    )
    user=cur.fetchone()
    solved_count=all_count(session['user_id'])
    correct=correct_count(session['user_id'])
    goal=user['goal']
    percent=int((correct/solved_count)*100) if solved_count else 0
    cur.execute('''
        SELECT tasks.number, ROUND(100*SUM(CASE WHEN user_tasks.status LIKE 'Правильно!' THEN 1 ELSE 0 END)/COUNT(*), 1) AS percent
        FROM user_tasks JOIN tasks ON user_tasks.task_id=tasks.id 
        WHERE user_tasks.user_id=?
        GROUP BY tasks.number
        ORDER BY tasks.number 
    ''', (session['user_id'],))
    data=cur.fetchall()
    for row in data:
        print(dict(row))
    numbers=[row['number'] for row in data]
    percents=[row['percent'] for row in data]
    conn.close()
    return render_template('statistics.html', user=user, solved_count=solved_count, correct=correct,goal=goal, percent=percent,numbers=numbers,percents=percents)


def all_count(user_id):
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    cur.execute('''
        SELECT COUNT(*) FROM user_tasks WHERE user_id=?
    ''', (user_id,))
    count=cur.fetchone()[0]
    conn.close()
    return count


def correct_count(user_id):
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    cur.execute('''
        SELECT COUNT(*) FROM user_tasks WHERE user_id=? AND status LIKE "Правильно%"
    ''',(user_id,))
    count=cur.fetchone()[0]
    conn.close()
    return count


@app.route('/add_theory', methods=['GET','POST'])
@admin_only
def add_theory():
    if request.method=='POST':
        title=request.form['title']
        task_number=request.form['task_number']
        text=request.form['text']
        pdf=request.files.get('pdf')
        pdf_path=None
        if pdf:
            pdf_path=f'static/theory/{pdf.filename}'
            pdf.save(pdf_path)
        conn=sqlite3.connect('users.db')
        cur=conn.cursor()
        cur.execute('''
            INSERT INTO theory_table(title,task_number,text,pdf_path) VALUES(?,?,?,?)
        ''',(title,task_number,text,pdf_path))
        conn.commit()
        conn.close()
    return redirect('/theory')


@app.route('/theory')
@regs_only
def theory():
    conn=sqlite3.connect('users.db')
    conn.row_factory=sqlite3.Row 
    cur=conn.cursor()
    cur.execute('SELECT block_id, title, task_number, text, pdf_path FROM theory_table')
    blocks=cur.fetchall()
    conn.close()
    return render_template('theory.html', blocks=blocks)


@app.route('/delete_theory/<int:theory_id>',methods=['POST'])
@admin_only
def delete_theory(theory_id):
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    cur.execute(
        'DELETE FROM theory_table WHERE block_id=?',
        (theory_id,)
    )
    conn.commit()
    conn.close()
    return redirect('/theory')

@app.route('/edit_theory/<int:block_id>',methods=['POST'])
@admin_only
def edit_theory(block_id):
    title=request.form['title']
    task_number=request.form['task_number']
    text=request.form['text']
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    cur.execute('''
        UPDATE theory_table SET title=?, task_number=?, text=? WHERE block_id=?
    ''',(title,task_number,text,block_id))
    conn.commit()
    conn.close()
    return redirect('/theory')


if __name__=='__main__':
    init_db()
    app.run(debug=True)