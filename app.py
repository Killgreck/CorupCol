import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask App
app = Flask(__name__, static_folder='dashboard', static_url_path='/static_dashboard', template_folder='templates')
app.config['SECRET_KEY'] = 'dev-secret-key-replace-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Failed. Check your username and password.', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))

        new_user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Protect the dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    # Send the main dashboard html file which is in the dashboard directory
    return send_from_directory('dashboard', 'index.html')

# Protect all dashboard assets
@app.route('/<path:filename>')
@login_required
def serve_dashboard_assets(filename):
    return send_from_directory('dashboard', filename)

@app.route('/')
def corrupworld_index():
    return render_template('corrupworld.html')

if __name__ == '__main__':
    print("╔══════════════════════════════════════════════╗")
    print("║        CorupCol — Authenticated Server        ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  URL:  http://localhost:5000                   ║")
    print("║  Admin: Login required to view dashboard     ║")
    print("╚══════════════════════════════════════════════╝")
    app.run(host='0.0.0.0', port=5000)
