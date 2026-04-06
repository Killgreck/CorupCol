"""
Security tests for CorrupCol Flask app.
Covers: security headers, path traversal, open redirect, auth enforcement,
        registration restrictions, input validation, and generic error messages.
"""
import os
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-tests')
from pathlib import Path

import pytest
from app import app as flask_app, db, User
from werkzeug.security import generate_password_hash


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'RATELIMIT_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-for-tests',
        'SESSION_COOKIE_SECURE': False,
    })
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        yield flask_app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client_with_user(client):
    with flask_app.app_context():
        user = User(
            username='admin',
            password_hash=generate_password_hash('securepass123'),
        )
        db.session.add(user)
        db.session.commit()
    return client


def login(client, username='admin', password='securepass123'):
    return client.post(
        '/login',
        data={'username': username, 'password': password},
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# 1. Security Headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        resp = client.get('/')
        assert resp.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_x_frame_options(self, client):
        resp = client.get('/')
        assert resp.headers.get('X-Frame-Options') == 'DENY'

    def test_referrer_policy(self, client):
        resp = client.get('/')
        assert resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

    def test_x_xss_protection(self, client):
        resp = client.get('/')
        assert resp.headers.get('X-XSS-Protection') == '0'

    def test_csp_present_and_contains_frame_ancestors(self, client):
        resp = client.get('/')
        csp = resp.headers.get('Content-Security-Policy', '')
        assert csp, "Content-Security-Policy header is missing"
        assert 'frame-ancestors' in csp

    def test_csp_does_not_allow_inline_styles(self, client):
        resp = client.get('/')
        csp = resp.headers.get('Content-Security-Policy', '')
        assert "'unsafe-inline'" not in csp
        assert "style-src 'self' https://fonts.googleapis.com" in csp
        assert "object-src 'none'" in csp
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp


# ---------------------------------------------------------------------------
# 2 & 3. Path Traversal — unauthenticated users get 302 to /login, not 200/500
# ---------------------------------------------------------------------------

class TestPathTraversal:
    """
    Unauthenticated requests to /dashboard/<path> redirect to /login (302).
    A 200 would mean the file was served without auth — a critical failure.
    A 500 would mean an unhandled error leaking internals.
    Neither 200 nor 500 is acceptable; 302 (to login) or 404 are both safe.
    """

    def _assert_safe_response(self, resp):
        assert resp.status_code not in (200, 500), (
            f"Unsafe response {resp.status_code}: path traversal may have succeeded "
            "or caused an internal error."
        )

    def test_path_traversal_etc_passwd(self, client):
        resp = client.get('/dashboard/../../../etc/passwd', follow_redirects=False)
        self._assert_safe_response(resp)

    def test_path_traversal_app_py(self, client):
        resp = client.get('/dashboard/../../app.py', follow_redirects=False)
        self._assert_safe_response(resp)

    def test_path_traversal_etc_passwd_redirects_to_login(self, client):
        """Unauthenticated traversal attempt should redirect to login, not serve file."""
        resp = client.get('/dashboard/../../../etc/passwd', follow_redirects=False)
        # Must not reach the file — either blocked (404) or auth-gated (302)
        if resp.status_code == 302:
            assert 'login' in resp.headers.get('Location', '').lower()

    def test_path_traversal_authenticated_returns_404(self, client_with_user):
        """Even authenticated, traversal paths outside dashboard/ must return 404."""
        login(client_with_user)
        resp = client_with_user.get(
            '/dashboard/../../../etc/passwd', follow_redirects=False
        )
        # werkzeug safe_join prevents escape; the path will either be 404 or 302
        assert resp.status_code not in (200, 500)


# ---------------------------------------------------------------------------
# 4, 5, 6. Open Redirect
# ---------------------------------------------------------------------------

class TestOpenRedirect:
    def test_open_redirect_external_url_blocked(self, client_with_user):
        """POST /login with next=https://evil.com must not redirect externally."""
        resp = client_with_user.post(
            '/login',
            data={
                'username': 'admin',
                'password': 'securepass123',
                'next': 'https://evil.com',
            },
            follow_redirects=False,
        )
        location = resp.headers.get('Location', '')
        assert 'evil.com' not in location

    def test_open_redirect_protocol_relative_blocked(self, client_with_user):
        """POST /login with next=//evil.com must not redirect to protocol-relative URL."""
        resp = client_with_user.post(
            '/login',
            data={
                'username': 'admin',
                'password': 'securepass123',
                'next': '//evil.com',
            },
            follow_redirects=False,
        )
        location = resp.headers.get('Location', '')
        assert 'evil.com' not in location

    def test_open_redirect_internal_path_allowed(self, client_with_user):
        """POST /login with next=/dashboard must redirect internally (safe)."""
        resp = client_with_user.post(
            '/login',
            data={
                'username': 'admin',
                'password': 'securepass123',
                'next': '/dashboard',
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        location = resp.headers.get('Location', '')
        assert '/dashboard' in location

    @pytest.mark.parametrize('next_url', [
        '/\\evil.com',
        '/%5C%5Cevil.com',
        '/%5C/evil.com',
        '/∕∕evil.com',
    ])
    def test_open_redirect_slashlike_values_blocked(self, client_with_user, next_url):
        resp = client_with_user.post(
            '/login',
            data={
                'username': 'admin',
                'password': 'securepass123',
                'next': next_url,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers.get('Location') == '/dashboard'


# ---------------------------------------------------------------------------
# 7 & 8. Auth Enforcement
# ---------------------------------------------------------------------------

class TestAuthEnforcement:
    def test_dashboard_requires_login(self, client):
        """GET /dashboard without session must redirect to /login."""
        resp = client.get('/dashboard', follow_redirects=False)
        assert resp.status_code == 302
        assert 'login' in resp.headers.get('Location', '').lower()

    def test_dashboard_asset_requires_login(self, client):
        """GET /dashboard/js/main.js without session must redirect to /login."""
        resp = client.get('/dashboard/js/main.js', follow_redirects=False)
        assert resp.status_code == 302
        assert 'login' in resp.headers.get('Location', '').lower()

    def test_static_dashboard_data_not_public(self, client):
        """The Flask static shortcut must not expose dashboard data without auth."""
        resp = client.get('/static_dashboard/data/stats.json', follow_redirects=False)
        assert resp.status_code == 404

    def test_static_dashboard_js_not_public(self, client):
        """Dashboard JS must only be served through the authenticated route."""
        resp = client.get('/static_dashboard/js/main.js', follow_redirects=False)
        assert resp.status_code == 404

    def test_dashboard_data_requires_login(self, client):
        resp = client.get('/dashboard/data/stats.json', follow_redirects=False)
        assert resp.status_code == 302
        assert 'login' in resp.headers.get('Location', '').lower()

    def test_public_css_is_available_without_login(self, client):
        resp = client.get('/public/css/style.css', follow_redirects=False)
        assert resp.status_code == 200

    def test_public_auth_css_is_available_without_login(self, client):
        resp = client.get('/public/css/auth.css', follow_redirects=False)
        assert resp.status_code == 200

    def test_public_corrupworld_css_is_available_without_login(self, client):
        resp = client.get('/public/css/corrupworld.css', follow_redirects=False)
        assert resp.status_code == 200

    def test_dashboard_css_still_requires_login(self, client):
        resp = client.get('/dashboard/css/dashboard-pages.css', follow_redirects=False)
        assert resp.status_code == 302
        assert 'login' in resp.headers.get('Location', '').lower()

    def test_js_rendered_css_still_requires_login(self, client):
        resp = client.get('/dashboard/css/js-rendered.css', follow_redirects=False)
        assert resp.status_code == 302
        assert 'login' in resp.headers.get('Location', '').lower()

    def test_untrusted_host_header_blocked(self, client):
        resp = client.get(
            '/dashboard//data/stats.json',
            headers={'Host': 'evil.example'},
            follow_redirects=False,
        )
        assert resp.status_code == 400

    def test_trusted_host_header_allows_request(self, client):
        resp = client.get(
            '/dashboard/data/stats.json',
            headers={'Host': 'localhost'},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert 'login' in resp.headers.get('Location', '').lower()


class TestInlineStyleRegression:
    def test_templates_and_dashboard_html_do_not_use_inline_styles(self):
        project_root = Path(__file__).resolve().parents[1]
        paths = list((project_root / 'templates').glob('*.html'))
        paths.extend((project_root / 'dashboard').glob('*.html'))
        for path in paths:
            content = path.read_text(encoding='utf-8')
            assert '<style' not in content, f"Inline <style> found in {path}"
            assert 'style="' not in content, f'Inline style attribute found in {path}'
            assert "style='" not in content, f'Inline style attribute found in {path}'

    def test_dashboard_js_does_not_generate_inline_style_attributes(self):
        project_root = Path(__file__).resolve().parents[1]
        for path in (project_root / 'dashboard' / 'js').glob('*.js'):
            content = path.read_text(encoding='utf-8')
            assert 'style="' not in content, f'Generated inline style found in {path}'
            assert "style='" not in content, f'Generated inline style found in {path}'


# ---------------------------------------------------------------------------
# 9. Registration Closed When Users Exist
# ---------------------------------------------------------------------------

class TestRegistrationClosed:
    def test_register_blocked_when_users_exist(self, client_with_user):
        """POST /register when a user already exists must not create a new user."""
        resp = client_with_user.post(
            '/register',
            data={'username': 'hacker', 'password': 'hackerpass123'},
            follow_redirects=False,
        )
        # Must redirect away (to login) and not create the new user
        assert resp.status_code == 302
        assert 'login' in resp.headers.get('Location', '').lower()

        with flask_app.app_context():
            assert User.query.filter_by(username='hacker').first() is None


# ---------------------------------------------------------------------------
# 10, 11, 12, 13. Input Validation on Registration
# ---------------------------------------------------------------------------

class TestRegistrationValidation:
    """
    These tests run against a fresh DB (no users), so registration is open.
    They verify that invalid inputs are rejected before any user is persisted.
    """

    def test_username_too_long_rejected(self, client):
        long_username = 'a' * 65  # > USERNAME_MAX (64)
        resp = client.post(
            '/register',
            data={'username': long_username, 'password': 'validpass123'},
            follow_redirects=False,
        )
        # Should not redirect to dashboard (i.e., no user created and logged in)
        assert resp.status_code != 302 or 'dashboard' not in resp.headers.get('Location', '')
        with flask_app.app_context():
            assert User.query.filter_by(username=long_username).first() is None

    def test_password_too_long_rejected(self, client):
        long_password = 'p' * 129  # > PASSWORD_MAX (128)
        resp = client.post(
            '/register',
            data={'username': 'validuser', 'password': long_password},
            follow_redirects=False,
        )
        assert resp.status_code != 302 or 'dashboard' not in resp.headers.get('Location', '')
        with flask_app.app_context():
            assert User.query.filter_by(username='validuser').first() is None

    def test_empty_username_rejected(self, client):
        resp = client.post(
            '/register',
            data={'username': '', 'password': 'validpass123'},
            follow_redirects=False,
        )
        assert resp.status_code != 302 or 'dashboard' not in resp.headers.get('Location', '')
        with flask_app.app_context():
            assert db.session.query(db.func.count(User.id)).scalar() == 0

    def test_empty_password_rejected(self, client):
        resp = client.post(
            '/register',
            data={'username': 'validuser', 'password': ''},
            follow_redirects=False,
        )
        assert resp.status_code != 302 or 'dashboard' not in resp.headers.get('Location', '')
        with flask_app.app_context():
            assert db.session.query(db.func.count(User.id)).scalar() == 0


# ---------------------------------------------------------------------------
# 14. Generic Login Error Message (no user enumeration)
# ---------------------------------------------------------------------------

class TestNoUserEnumeration:
    def test_nonexistent_user_returns_generic_message(self, client_with_user):
        """POST /login with non-existent username must return the same error as wrong password."""
        resp_nonexistent = client_with_user.post(
            '/login',
            data={'username': 'doesnotexist', 'password': 'somepassword'},
            follow_redirects=True,
        )
        resp_wrong_password = client_with_user.post(
            '/login',
            data={'username': 'admin', 'password': 'wrongpassword'},
            follow_redirects=True,
        )
        # Both responses must be 200 (re-rendered login page)
        assert resp_nonexistent.status_code == 200
        assert resp_wrong_password.status_code == 200

        body_nonexistent = resp_nonexistent.data.decode()
        body_wrong_password = resp_wrong_password.data.decode()

        # The generic error message must appear in both cases
        assert 'Credenciales inválidas' in body_nonexistent
        assert 'Credenciales inválidas' in body_wrong_password

        # Neither response should hint at whether the user exists
        assert 'usuario no existe' not in body_nonexistent.lower()
        assert 'usuario no encontrado' not in body_nonexistent.lower()


# ---------------------------------------------------------------------------
# 15. Logout Requires Login
# ---------------------------------------------------------------------------

class TestLogoutRequiresLogin:
    def test_logout_post_without_session_redirects_to_login(self, client):
        """POST /logout without an active session must redirect to login (not 200/500)."""
        resp = client.post('/logout', follow_redirects=False)
        assert resp.status_code == 302
        assert 'login' in resp.headers.get('Location', '').lower()

    def test_logout_get_not_allowed(self, client_with_user):
        """GET /logout must not be a state-changing action."""
        login(client_with_user)
        resp = client_with_user.get('/logout', follow_redirects=False)
        assert resp.status_code == 405
