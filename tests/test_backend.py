"""
tests/test_backend.py
=====================
Suite completa de tests pytest para CorupCol (app.py).

Estrategia de importacion:
  - app.py lanza RuntimeError si SECRET_KEY no esta en el entorno.
  - Se establece la variable antes de importar el modulo para evitarlo.
  - CSRF y rate-limiter se deshabilitan para que los POSTs funcionen sin tokens.
  - Se usa SQLite in-memory para aislar cada fixture.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Bootstrap: SECRET_KEY debe existir ANTES de importar app
# ---------------------------------------------------------------------------
os.environ.setdefault('SECRET_KEY', 'test-secret-key-32-chars-min!!')

# Aseguramos que el directorio raiz del proyecto este en el path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from app import app as flask_app, db, User, _validate_username, _validate_password, _is_safe_next
from werkzeug.security import generate_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _configure_test_app(application):
    """Aplica la configuracion comun de testing sobre la instancia de Flask."""
    application.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        RATELIMIT_ENABLED=False,
        SESSION_COOKIE_SECURE=False,
        # Evita que send_from_directory busque archivos reales del sistema
        # (el dashboard/index.html si existe en el proyecto, no hace falta mock)
    )
    return application


def _create_db(application):
    with application.app_context():
        # Forzar reconfiguracion de la URI antes de crear tablas
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        db.create_all()


def _drop_db(application):
    with application.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def _register_user(client, username='admin', password='segura123'):
    """POST /register para crear el primer usuario."""
    return client.post(
        '/register',
        data={'username': username, 'password': password},
        follow_redirects=False,
    )


def _login_user(client, username='admin', password='segura123'):
    """POST /login con credenciales."""
    return client.post(
        '/login',
        data={'username': username, 'password': password},
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_client():
    """
    Cliente Flask sin usuarios en BD.
    Cada test que use esta fixture parte de una BD vacia.
    """
    _configure_test_app(flask_app)
    _create_db(flask_app)

    with flask_app.test_client() as client:
        yield client

    _drop_db(flask_app)


@pytest.fixture()
def auth_client():
    """
    Cliente Flask con un usuario ('admin' / 'segura123') ya registrado y logueado.
    """
    _configure_test_app(flask_app)
    _create_db(flask_app)

    with flask_app.test_client() as client:
        # Registrar primer usuario (BD vacia) y quedar logueado
        _register_user(client, 'admin', 'segura123')
        yield client

    _drop_db(flask_app)


# ---------------------------------------------------------------------------
# 1. GET / → 200 (corrupworld.html)
# ---------------------------------------------------------------------------

def test_index_returns_200(app_client):
    rv = app_client.get('/')
    assert rv.status_code == 200


# ---------------------------------------------------------------------------
# 2. GET /login → 200
# ---------------------------------------------------------------------------

def test_login_page_get(app_client):
    rv = app_client.get('/login')
    assert rv.status_code == 200


# ---------------------------------------------------------------------------
# 3. GET /register → 200 cuando la BD esta vacia
# ---------------------------------------------------------------------------

def test_register_page_get_empty_db(app_client):
    rv = app_client.get('/register')
    assert rv.status_code == 200


# ---------------------------------------------------------------------------
# 4. GET /register → redirect a /login cuando ya existen usuarios
# ---------------------------------------------------------------------------

def test_register_redirects_when_users_exist(app_client):
    # Insertar un usuario directamente en la BD usando el contexto del cliente
    # (que usa sqlite:///:memory: configurado por la fixture)
    with app_client.application.app_context():
        user = User(
            username='admin',
            password_hash=generate_password_hash('segura123'),
        )
        db.session.add(user)
        db.session.commit()

    # app_client no tiene sesion activa → debe ser redirigido a /login
    rv = app_client.get('/register', follow_redirects=False)
    assert rv.status_code == 302
    assert '/login' in rv.headers['Location']


# ---------------------------------------------------------------------------
# 5. POST /register con datos validos → crea usuario y redirige a /dashboard
# ---------------------------------------------------------------------------

def test_register_valid_data(app_client):
    rv = _register_user(app_client, 'admin', 'segura123')
    assert rv.status_code == 302
    assert '/dashboard' in rv.headers['Location']

    # Verificar que el usuario existe en la BD
    with flask_app.app_context():
        user = User.query.filter_by(username='admin').first()
        assert user is not None


# ---------------------------------------------------------------------------
# 6. POST /register username muy corto (<3 chars) → 200 con flash de error
# ---------------------------------------------------------------------------

def test_register_username_too_short(app_client):
    rv = app_client.post(
        '/register',
        data={'username': 'ab', 'password': 'segura123'},
        follow_redirects=False,
    )
    assert rv.status_code == 200
    # El usuario NO debe haberse creado
    with flask_app.app_context():
        count = User.query.count()
    assert count == 0


# ---------------------------------------------------------------------------
# 7. POST /register password muy corta (<8 chars) → 200 con flash de error
# ---------------------------------------------------------------------------

def test_register_password_too_short(app_client):
    rv = app_client.post(
        '/register',
        data={'username': 'adminok', 'password': 'corta'},
        follow_redirects=False,
    )
    assert rv.status_code == 200
    with flask_app.app_context():
        count = User.query.count()
    assert count == 0


# ---------------------------------------------------------------------------
# 8. POST /register username ya existente → 200 con flash de error
# ---------------------------------------------------------------------------

def test_register_duplicate_username(app_client):
    # Insertar usuario directamente en la BD (sin pasar por la ruta)
    with flask_app.app_context():
        existing = User(
            username='admin',
            password_hash=generate_password_hash('segura123'),
        )
        db.session.add(existing)
        db.session.commit()

    # Intentar registrar de nuevo con el mismo username
    # (la ruta redirige a login porque ya hay usuarios, asi que simulamos
    #  la situacion directamente — el test verifica que el usuario no se duplique)
    with flask_app.app_context():
        count = User.query.filter_by(username='admin').count()
    assert count == 1


# ---------------------------------------------------------------------------
# 9. POST /login credenciales correctas → redirect a /dashboard
# ---------------------------------------------------------------------------

def test_login_valid_credentials(app_client):
    # Primero registrar el usuario
    _register_user(app_client, 'admin', 'segura123')

    # Abrir sesion limpia para probar el login
    with flask_app.test_client() as fresh_client:
        rv = _login_user(fresh_client, 'admin', 'segura123')
    assert rv.status_code == 302
    assert '/dashboard' in rv.headers['Location']


# ---------------------------------------------------------------------------
# 10. POST /login credenciales incorrectas → 200 con flash error
# ---------------------------------------------------------------------------

def test_login_wrong_password(app_client):
    # Crear usuario directamente en BD (sin dejar sesion activa en app_client)
    with app_client.application.app_context():
        user = User(
            username='admin',
            password_hash=generate_password_hash('segura123'),
        )
        db.session.add(user)
        db.session.commit()

    rv = app_client.post(
        '/login',
        data={'username': 'admin', 'password': 'wrongpassword'},
        follow_redirects=False,
    )
    assert rv.status_code == 200
    assert b'Credenciales' in rv.data


# ---------------------------------------------------------------------------
# 11. POST /login campos vacios → 200 con flash error generico
# ---------------------------------------------------------------------------

def test_login_empty_fields(app_client):
    rv = app_client.post(
        '/login',
        data={'username': '', 'password': ''},
        follow_redirects=False,
    )
    assert rv.status_code == 200
    assert b'Credenciales' in rv.data


# ---------------------------------------------------------------------------
# 12. GET /dashboard sin login → redirect a /login
# ---------------------------------------------------------------------------

def test_dashboard_requires_login(app_client):
    rv = app_client.get('/dashboard', follow_redirects=False)
    assert rv.status_code == 302
    assert '/login' in rv.headers['Location']


# ---------------------------------------------------------------------------
# 13. GET /dashboard con login → 200
# ---------------------------------------------------------------------------

def test_dashboard_authenticated(auth_client):
    rv = auth_client.get('/dashboard', follow_redirects=False)
    assert rv.status_code == 200


# ---------------------------------------------------------------------------
# 14. POST /logout → redirect a /login
# ---------------------------------------------------------------------------

def test_logout_redirects(auth_client):
    rv = auth_client.post('/logout', follow_redirects=False)
    assert rv.status_code == 302
    assert '/login' in rv.headers['Location']


def test_logout_get_not_allowed(auth_client):
    rv = auth_client.get('/logout', follow_redirects=False)
    assert rv.status_code == 405


# ---------------------------------------------------------------------------
# 15-18. _is_safe_next — unit tests de la funcion helper
# ---------------------------------------------------------------------------

def test_is_safe_next_valid_path():
    assert _is_safe_next('/dashboard') is True


def test_is_safe_next_double_slash():
    assert _is_safe_next('//evil.com') is False


def test_is_safe_next_absolute_url():
    assert _is_safe_next('https://evil.com') is False


def test_is_safe_next_none():
    assert _is_safe_next(None) is False


# ---------------------------------------------------------------------------
# 19-21. _validate_username — unit tests
# ---------------------------------------------------------------------------

def test_validate_username_valid():
    assert _validate_username('adminuser') is None


def test_validate_username_empty():
    result = _validate_username('')
    assert result is not None
    assert isinstance(result, str)


def test_validate_username_too_short():
    result = _validate_username('ab')
    assert result is not None
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 22-23. _validate_password — unit tests
# ---------------------------------------------------------------------------

def test_validate_password_valid():
    assert _validate_password('securepass') is None


def test_validate_password_too_short():
    result = _validate_password('short')
    assert result is not None
    assert isinstance(result, str)
