"""End-to-end tests for the login / logout / registration callback.

The callback is exercised through Dash's own HTTP endpoint so the tests cover
the exact request/response contract the browser uses, including the subtle
`n_clicks == 0` re-render calls and the `localStorage` session restore.

The real auth helpers are monkeypatched so the tests never touch Supabase.
"""

import json
import os

import app as app_module
from app import app, server

CALLBACK = '..app-root.children...session-user.data..'
ENDPOINT = '/_dash-update-component'


def _body(trigger, *, login=0, logout=0, logout_visible=0, register=0,
          session=None, username='', password='',
          reg_user='', reg_pw='', reg_pw2='', fired=True):
    """Build the JSON Dash sends to /_dash-update-component."""
    inputs = [
        {'id': 'login-button', 'property': 'n_clicks', 'value': login},
        {'id': 'logout-button', 'property': 'n_clicks', 'value': logout},
        {'id': 'logout-button-visible', 'property': 'n_clicks', 'value': logout_visible},
        {'id': 'register-button', 'property': 'n_clicks', 'value': register},
        {'id': 'session-user', 'property': 'data', 'value': session},
    ]
    state = [
        {'id': 'username', 'property': 'value', 'value': username},
        {'id': 'password', 'property': 'value', 'value': password},
        {'id': 'register-username', 'property': 'value', 'value': reg_user},
        {'id': 'register-password', 'property': 'value', 'value': reg_pw},
        {'id': 'register-confirm-password', 'property': 'value', 'value': reg_pw2},
    ]
    if not fired:
        changed = []
    elif trigger == 'session-user':
        changed = ['session-user.data']
    else:
        changed = ['%s.n_clicks' % trigger]
    return {
        'output': CALLBACK,
        'outputs': [{'id': 'app-root', 'property': 'children'},
                    {'id': 'session-user', 'property': 'data'}],
        'inputs': inputs,
        'changedPropIds': changed,
        'state': state,
    }


def _call(trigger, **kwargs):
    """Invoke the callback and return the decoded JSON response.

    Dash answers ``204`` with an empty body when every output is ``no_update``
    (the same response ``PreventUpdate`` produces), so both codes are valid.
    """
    response = server.test_client().post(ENDPOINT, json=_body(trigger, **kwargs))
    assert response.status_code in (200, 204), response.get_data(as_text=True)
    return response.get_json() or {}


def _outputs(response):
    return response.get('response', {})


def _html(response):
    return json.dumps(_outputs(response).get('app-root', {}).get('children'))


def _session(response):
    return _outputs(response).get('session-user', {}).get('data')


# ---------------------------------------------------------------------------
# Page load / session persistence
# ---------------------------------------------------------------------------


def test_first_paint_never_clears_the_saved_session():
    """Before localStorage is read the store must stay untouched.

    Writing {'username': None} here used to wipe the saved session, which is
    why the app never kept anybody signed in after a refresh.
    """
    response = _call('login-button', fired=False)
    assert 'User Name' in _html(response)
    assert 'session-user' not in _outputs(response)


def test_stored_session_restores_the_dashboard():
    response = _call('session-user', session={'username': 'nehal'})
    assert 'Welcome, nehal!' in _html(response)
    assert 'session-user' not in _outputs(response)  # value is already correct


def test_empty_stored_session_shows_the_login_form():
    response = _call('session-user', session=None)
    assert 'User Name' in _html(response)
    assert 'session-user' not in _outputs(response)


# ---------------------------------------------------------------------------
# Re-render calls (n_clicks == 0) must not change anything
# ---------------------------------------------------------------------------


def test_newly_rendered_logout_button_does_not_log_the_user_out():
    """The regression that made every login bounce straight back to the form."""
    response = _call('logout-button-visible', logout_visible=0,
                     session={'username': 'nehal'})
    assert _outputs(response) == {}


def test_newly_rendered_login_and_register_buttons_are_ignored():
    assert _outputs(_call('login-button', login=0)) == {}
    assert _outputs(_call('register-button', register=0)) == {}


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_valid_credentials_open_the_dashboard(monkeypatch):
    monkeypatch.setattr(app_module, 'validate_user', lambda user, pw: True)
    response = _call('login-button', login=1, username='nehal', password='secret')
    assert 'Welcome, nehal!' in _html(response)
    assert _session(response) == {'username': 'nehal'}


def test_invalid_credentials_keep_the_login_form(monkeypatch):
    monkeypatch.setattr(app_module, 'validate_user', lambda user, pw: False)
    response = _call('login-button', login=1, username='nehal', password='nope')
    assert 'Invalid username or password' in _html(response)
    assert 'session-user' not in _outputs(response)


def test_empty_fields_are_rejected(monkeypatch):
    monkeypatch.setattr(app_module, 'validate_user', lambda user, pw: True)
    response = _call('login-button', login=1, username='', password='')
    assert 'Please enter both User Name and Password.' in _html(response)


def test_validate_user_rejects_blank_input_without_network(monkeypatch):
    monkeypatch.setattr(app_module, 'get_supabase_client', lambda: None)
    monkeypatch.setattr(app_module, 'get_supabase_auth_client', lambda: None)
    assert app_module.validate_user('', '') is False
    assert app_module.validate_user('  ', 'secret') is False


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


def test_logout_clears_the_session():
    response = _call('logout-button-visible', logout_visible=1,
                     session={'username': 'nehal'})
    assert 'User Name' in _html(response)
    assert _session(response) == {'username': None}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_registration_stores_the_account(monkeypatch):
    saved = {}
    monkeypatch.setattr(app_module, 'user_exists', lambda user: False)
    monkeypatch.setattr(app_module, 'save_user',
                        lambda user, pw: saved.update({user: pw}) or True)
    response = _call('register-button', register=1, reg_user='jane',
                     reg_pw='pw12345', reg_pw2='pw12345')
    assert 'Account created' in _html(response)
    assert saved == {'jane': 'pw12345'}


def test_registration_rejects_mismatched_passwords(monkeypatch):
    monkeypatch.setattr(app_module, 'user_exists', lambda user: False)
    response = _call('register-button', register=1, reg_user='jane',
                     reg_pw='pw12345', reg_pw2='different')
    assert 'Passwords do not match.' in _html(response)


def test_registration_rejects_a_duplicate_username(monkeypatch):
    monkeypatch.setattr(app_module, 'user_exists', lambda user: True)
    response = _call('register-button', register=1, reg_user='nehal',
                     reg_pw='pw12345', reg_pw2='pw12345')
    assert 'That username already exists.' in _html(response)


def test_registration_failure_shows_the_technical_reason(monkeypatch):
    monkeypatch.setattr(app_module, 'user_exists', lambda user: False)
    monkeypatch.setattr(app_module, 'save_user', lambda user, pw: False)
    monkeypatch.setattr(app_module, '_consume_auth_error',
                        lambda: 'SUPABASE_SERVICE_ROLE_KEY is missing')
    response = _call('register-button', register=1, reg_user='jane',
                     reg_pw='pw12345', reg_pw2='pw12345')
    html = _html(response)
    assert 'Unable to create the account.' in html
    assert 'SUPABASE_SERVICE_ROLE_KEY is missing' in html


# ---------------------------------------------------------------------------
# Supabase is the only account store
# ---------------------------------------------------------------------------


def test_no_local_account_database_is_shipped():
    """The bundled auth_users.db was removed: Supabase holds every account."""
    assert not os.path.exists(
        os.path.join(app_module.APP_ROOT, 'data', 'auth_users.db'))
    assert not hasattr(app_module, 'AUTH_DB_PATH')
    assert not hasattr(app_module, 'initialize_auth_db')
    assert not hasattr(app_module, '_sqlite_validate')


def test_validate_user_reports_a_missing_supabase_configuration(monkeypatch):
    monkeypatch.setattr(app_module, 'get_supabase_client', lambda: None)
    app_module._auth_error = None
    assert app_module.validate_user('nehal', 'any-password') is False
    assert 'Supabase is not configured' in app_module._consume_auth_error()


def test_user_exists_reports_a_missing_supabase_configuration(monkeypatch):
    monkeypatch.setattr(app_module, 'get_supabase_client', lambda: None)
    app_module._auth_error = None
    assert app_module.user_exists('nehal') is False
    assert 'Supabase is not configured' in app_module._consume_auth_error()


def test_save_user_reports_a_missing_supabase_configuration(monkeypatch):
    monkeypatch.setattr(app_module, 'get_supabase_client', lambda: None)
    app_module._auth_error = None
    assert app_module.save_user('newbie', 'pw12345') is False
    assert 'Supabase is not configured' in app_module._consume_auth_error()


def test_health_endpoint_reports_the_supabase_backend(monkeypatch):
    """Guards against a local database file creeping back into the health check."""
    monkeypatch.setattr(app_module, '_probe_supabase_users_table',
                        lambda: (True, None))
    monkeypatch.setattr(app_module, '_count_visible_accounts', lambda: 3)

    payload = server.test_client().get('/health').get_json()

    assert payload['accounts_backend'] == 'supabase'
    assert payload['accounts_visible'] == 3
    assert payload['supabase_app_users_reachable'] is True
    assert 'auth_db_path' not in payload
    assert 'bundled_auth_db' not in payload['data_files']
