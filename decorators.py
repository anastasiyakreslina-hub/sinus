# Декораторы доступа (@admin_only, @regs_only)

from functools import wraps
from flask import session, redirect

def admin_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper

def regs_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper