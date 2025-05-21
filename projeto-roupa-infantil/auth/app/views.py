from app import app, db, JWT_SECRET
from app.models import User
from flask import request, render_template, redirect, url_for, make_response
import jwt
from datetime import datetime

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return "Username and password required", 400
        # Verifica existência de usuário
        existing = User.query.filter_by(username=username).first()
        if existing:
            return "Username already exists", 400
        # Cria novo usuário (role 'user') e hash da senha
        user = User(username=username, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        # Gera JWT de sessão
        payload = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'iat': datetime.utcnow().timestamp()
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        resp = make_response(redirect('http://localhost:5001/'))  # vai para página de produtos
        resp.set_cookie('token', token, httponly=True, samesite='Lax')
        return resp
    # GET: exibe formulário de registro
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return "Username and password required", 400
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return "Invalid credentials", 401
        # Credenciais ok, gera token JWT
        payload = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'iat': datetime.utcnow().timestamp()
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        # Redireciona com base no papel do usuário
        if user.role == 'admin':
            redirect_url = 'http://localhost:5004/admin'
        else:
            redirect_url = 'http://localhost:5001/'
        resp = make_response(redirect(redirect_url))
        resp.set_cookie('token', token, httponly=True, samesite='Lax')
        return resp
    # GET: exibe formulário de login
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Encerra sessão removendo o cookie JWT
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('token', '', expires=0)
    return resp

@app.route('/')
def index():
    # Rota raiz – redireciona para login por conveniência
    return redirect(url_for('login'))
