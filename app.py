import os
import sqlite3
import re
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import safe_join
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no está configurada. "
        "Copia .env.example a .env y define un valor seguro."
    )

# Validation constants
USERNAME_MIN = 3
USERNAME_MAX = 64
PASSWORD_MIN = 8
PASSWORD_MAX = 128

# Initialize Flask App
app = Flask(
    __name__,
    static_folder='dashboard',
    static_url_path='/static_dashboard',
    template_folder='templates',
)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///users.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# WTF CSRF — habilitado por defecto al instanciar CSRFProtect
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hora

# Security headers via after_request
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-XSS-Protection'] = '0'  # Moderno: desactivar el XSS auditor roto
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self' https://d3js.org https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self' https://open.er-api.com; "
        "frame-ancestors 'none';"
    )
    return response

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder.'
login_manager.login_message_category = 'error'

# Rate limiter — almacena en memoria (aceptable para instancia única)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],  # Sin límite global; sólo en rutas específicas
    storage_uri="memory://",
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(USERNAME_MAX), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    # db.session.get es la API moderna de SQLAlchemy 2.x (User.query.get está deprecated)
    return db.session.get(User, int(user_id))


# Create database tables
with app.app_context():
    db.create_all()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _validate_username(username: str) -> str | None:
    """Devuelve mensaje de error o None si es válido."""
    if not username:
        return 'El nombre de usuario es obligatorio.'
    if len(username) < USERNAME_MIN:
        return f'El usuario debe tener al menos {USERNAME_MIN} caracteres.'
    if len(username) > USERNAME_MAX:
        return f'El usuario no puede superar {USERNAME_MAX} caracteres.'
    return None


def _validate_password(password: str) -> str | None:
    """Devuelve mensaje de error o None si es válido."""
    if not password:
        return 'La contraseña es obligatoria.'
    if len(password) < PASSWORD_MIN:
        return f'La contraseña debe tener al menos {PASSWORD_MIN} caracteres.'
    if len(password) > PASSWORD_MAX:
        return f'La contraseña no puede superar {PASSWORD_MAX} caracteres.'
    return None


def _is_safe_next(next_url: str | None) -> bool:
    """Valida que el parámetro next sea una ruta relativa interna (evita open redirect)."""
    if not next_url:
        return False
    # Sólo se permite paths que empiecen con / y no contengan //
    # (que podría interpretarse como protocolo relativo en algunos navegadores)
    return next_url.startswith('/') and not next_url.startswith('//')


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('20 per minute; 100 per hour')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        # Validación básica de presencia (sin revelar cuál campo falla)
        if not username or not password:
            flash('Credenciales inválidas.', 'error')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_url = request.form.get('next') or request.args.get('next')
            if _is_safe_next(next_url):
                return redirect(next_url)
            return redirect(url_for('dashboard'))

        # Mensaje genérico — no revela si el usuario existe o no
        flash('Credenciales inválidas.', 'error')

    return render_template('login.html', next=request.args.get('next', ''))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))


    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        err = _validate_username(username)
        if err:
            flash(err, 'error')
            return render_template('register.html')

        err = _validate_password(password)
        if err:
            flash(err, 'error')
            return render_template('register.html')

        user = User.query.filter_by(username=username).first()
        if user:
            flash('El nombre de usuario ya existe.', 'error')
            return render_template('register.html')

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Cuenta creada exitosamente.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    dashboard_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'dashboard')
    )
    return send_from_directory(dashboard_dir, 'index.html')


@app.route('/dashboard/<path:filename>')
@login_required
def serve_dashboard_assets(filename):
    """Sirve assets del dashboard validando que el path no escape del directorio."""
    dashboard_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'dashboard')
    )
    # safe_join lanza NotFound si el path intenta escapar del directorio base
    safe_path = safe_join(dashboard_dir, filename)
    if safe_path is None:
        from flask import abort
        abort(404)
    return send_from_directory(dashboard_dir, filename)


@app.route('/')
def corrupworld_index():
    return render_template('corrupworld.html')


# ---------------------------------------------------------------------------
# API: Búsqueda SECOP (FTS5 SQLite)
# ---------------------------------------------------------------------------
_SEARCH_DB = Path(__file__).parent / 'instance' / 'search.db'
_SEARCH_COLS = ('id','objeto','entidad','nit_entidad','contratista',
                'doc_contratista','valor','fecha','estado',
                'depto','ciudad','url','fuente','numero')

def _get_search_conn():
    conn = sqlite3.connect(_SEARCH_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA query_only=ON')
    return conn


def _sanitize_fts(q: str) -> str:
    """Convierte la query del usuario a una query FTS5 segura."""
    q = q.strip()
    if not q:
        return ''
    # Quitar caracteres especiales de FTS5 excepto espacios
    q = re.sub(r'["\'\(\)\[\]\{\}\^\*\?\+\-\~\!\\]', ' ', q)
    # Cada token con comillas para búsqueda de frase exacta si es un número,
    # o prefijo para texto
    tokens = q.split()
    if not tokens:
        return ''
    # Si es un único número (NIT/cédula), buscar exact match en doc_contratista
    if len(tokens) == 1 and tokens[0].isdigit():
        return None  # señal para hacer búsqueda por columna
    return ' '.join(f'"{t}"' for t in tokens if t)


@app.route('/api/search')
@login_required
def api_search():
    if not _SEARCH_DB.exists():
        return jsonify({
            'error': 'Índice de búsqueda no construido. Ejecuta: python3 scripts/construir_indice_search.py',
            'results': [], 'total': 0, 'page': 1, 'pages': 0
        }), 503

    raw_q  = (request.args.get('q') or '').strip()
    page   = max(1, int(request.args.get('page', 1) or 1))
    limit  = min(100, max(10, int(request.args.get('limit', 50) or 50)))
    offset = (page - 1) * limit

    try:
        conn = _get_search_conn()

        if not raw_q:
            # Sin query: mostrar contratos recientes
            rows  = conn.execute(
                'SELECT * FROM contratos ORDER BY fecha DESC LIMIT ? OFFSET ?',
                (limit, offset)
            ).fetchall()
            total = conn.execute('SELECT COUNT(*) FROM contratos').fetchone()[0]

        else:
            fts_q = _sanitize_fts(raw_q)

            if fts_q is None:
                # Búsqueda por NIT/cédula exacta
                rows  = conn.execute(
                    'SELECT * FROM contratos WHERE doc_contratista=? ORDER BY fecha DESC LIMIT ? OFFSET ?',
                    (raw_q, limit, offset)
                ).fetchall()
                total = conn.execute(
                    'SELECT COUNT(*) FROM contratos WHERE doc_contratista=?', (raw_q,)
                ).fetchone()[0]

            elif not fts_q.strip('"').strip():
                rows  = []
                total = 0

            else:
                rows  = conn.execute('''
                    SELECT c.* FROM contratos c
                    JOIN contratos_fts f ON c.id = f.rowid
                    WHERE contratos_fts MATCH ?
                    ORDER BY rank
                    LIMIT ? OFFSET ?
                ''', (fts_q, limit, offset)).fetchall()
                total = conn.execute('''
                    SELECT COUNT(*) FROM contratos c
                    JOIN contratos_fts f ON c.id = f.rowid
                    WHERE contratos_fts MATCH ?
                ''', (fts_q,)).fetchone()[0]

        conn.close()
        return jsonify({
            'results': [dict(r) for r in rows],
            'total':   total,
            'page':    page,
            'pages':   max(1, (total + limit - 1) // limit),
            'query':   raw_q,
        })

    except Exception as e:
        return jsonify({'error': str(e), 'results': [], 'total': 0, 'page': 1, 'pages': 0}), 500


# ---------------------------------------------------------------------------
# Entry point (solo para desarrollo local)
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    print("╔══════════════════════════════════════════════╗")
    print("║        CorupCol — Authenticated Server        ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  URL:  http://localhost:5000                   ║")
    print("║  Admin: Login required to view dashboard     ║")
    print("╚══════════════════════════════════════════════╝")
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
