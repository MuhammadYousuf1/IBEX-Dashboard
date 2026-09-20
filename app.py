"""
Sales Dashboard Application
===========================
Main entry point integrating Flask with Dash for multi-page dashboard.

Run with: python app.py
"""

import hashlib
import os
import sys
from flask import Flask, render_template_string, send_from_directory
from dotenv import load_dotenv
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table, ctx, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set to True to show the registration form below the login form.
SHOW_CREATE_ACCOUNT = True

# Set to True to print the technical reason behind a failed sign-in under the
# error message. Very useful when the cloud deployment is not configured yet;
# set it to False once everything works.
SHOW_AUTH_DIAGNOSTICS = True

# Import shared data module (after Dash creation so the merged page's
# register_page/callbacks are collected by the pages plugin correctly)

# ============================================================================
# FLASK SERVER SETUP
# ============================================================================

server = Flask(__name__,
               template_folder='templates',
               static_folder='assets')
server.secret_key = os.getenv('FLASK_SECRET_KEY', 'local-development-secret-key')

# ============================================================================
# DASH APP SETUP WITH PAGES
# ============================================================================

app = dash.Dash(
    __name__,
    server=server,
    use_pages=True,
    pages_folder='pages',
    external_stylesheets=[
        dbc.themes.DARKLY,
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
        '/assets/custom.css'
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{'name': 'viewport',
                'content': 'width=device-width, initial-scale=1.0'}]
)

app.title = 'Sales Analytics Dashboard'

# Import shared data module (after Dash creation so the merged page's
# register_page/callbacks are collected by the pages plugin correctly)
from pages import sales_dashboard as sd  # noqa: E402

# ============================================================================
# SHARED NAVIGATION & LAYOUT COMPONENTS
# ============================================================================


def create_navbar():
    """Create the top navigation bar."""
    return dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand([
                html.I(className='fas fa-chart-line me-2'),
                'SOFT RAPIDO WIRELESS'
            ], href='/', className='navbar-brand-custom'),
            dbc.NavbarToggler(id='navbar-toggler'),
            dbc.Collapse(
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink([
                        html.I(className='fas fa-home me-1'),
                        'Home'
                    ], href='/', active='exact', className='nav-link-custom')),
                    dbc.NavItem(dbc.NavLink([
                        html.I(className='fas fa-chart-pie me-1'),
                        'Sales Dashboard'
                    ], href='/sales-dashboard', active='exact', className='nav-link-custom')),
                    dbc.NavItem(dbc.NavLink([
                        html.I(className='fas fa-file-invoice-dollar me-1'),
                        'Input Form'
                    ], href='/deposit-expense', active='exact', className='nav-link-custom')),
                    dbc.NavItem(dbc.NavLink([
                        html.I(className='fas fa-file-arrow-down me-1'),
                        'Reports'
                    ], href='/reports', active='exact', className='nav-link-custom')),
                ], className='ms-auto', navbar=True),
                id='navbar-collapse',
                navbar=True,
            ),
        ], fluid=True),
        color='dark',
        dark=True,
        className='navbar-custom mb-4',
        sticky='top'
    )


def create_footer():
    """Create the footer."""
    return html.Footer(
        dbc.Container(
            dbc.Row([
                dbc.Col([
                    html.P([
                        html.I(className='fas fa-copyright me-1'),
                        f' {datetime.now().year} Sales Analytics Dashboard. All rights reserved.'
                    ], className='text-center text-muted mb-0 py-3')
                ])
            ]),
            fluid=True
        ),
        className='footer-custom mt-auto'
    )

# ============================================================================
# AUTH DATABASE (Supabase only - no local account file)
# ============================================================================


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(APP_ROOT, '.env'))
# Committed credentials so the deployment works without dashboard setup.
# supabase_config.py uses os.environ.setdefault, so a local .env or any value
# configured in the Vercel dashboard always wins over the committed values.
# Delete supabase_config.py once real environment variables are configured -
# see the security warning at the top of that file.
try:
    import supabase_config  # noqa: F401
except Exception:
    pass

# --- Supabase configuration -------------------------------------------------
# NOTE: .env is git-ignored, so it never reaches Vercel. The exact same three
# variables must be added in the Vercel dashboard (Project -> Settings ->
# Environment Variables) and the project redeployed:
#     SUPABASE_URL
#     SUPABASE_SERVICE_ROLE_KEY   <-- required, it is the one that bypasses RLS
#     SUPABASE_KEY                <-- optional publishable/anon key
SUPABASE_URL = (os.getenv('SUPABASE_URL')
                or os.getenv('NEXT_PUBLIC_SUPABASE_URL') or '').strip()
SUPABASE_PUBLIC_KEY = (os.getenv('SUPABASE_KEY')
                       or os.getenv('NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY') or '').strip()
# Row level security is enabled on `app_users`, so the publishable/anon key reads
# back ZERO rows and cannot insert. Only the service-role key can read/write it.
SUPABASE_ADMIN_KEY = (os.getenv('SUPABASE_SERVICE_ROLE_KEY') or '').strip()
AUTH_TABLE = 'app_users'

# There is NO local account database any more: Supabase is the single source of
# truth for logins, so the same credentials work locally and on Vercel.

# Last technical reason a Supabase call failed. Only used for the on-screen
# diagnostics while SHOW_AUTH_DIAGNOSTICS is True.
_auth_error = None
_client_cache = {}


def _set_auth_error(message):
    """Remember the technical reason behind the last failed auth operation."""
    global _auth_error
    _auth_error = message


def _consume_auth_error():
    """Return and clear the remembered auth error."""
    global _auth_error
    message, _auth_error = _auth_error, None
    return message


def _short_error(exc, limit=160):
    """One-line version of an exception, short enough for the login screen."""
    text = ' '.join(str(exc).split())
    return text if len(text) <= limit else text[:limit] + '...'


def hash_password(password):
    """Hash a password before saving it to the database."""
    return hashlib.sha256(str(password).strip().encode('utf-8')).hexdigest()


def _build_supabase_client(key):
    """Create (and cache) a Supabase client for the given API key."""
    if not SUPABASE_URL or not key:
        return None
    if key in _client_cache:
        return _client_cache[key]
    client = None
    try:
        from supabase import create_client
        client = create_client(SUPABASE_URL, key)
    except Exception as exc:
        _set_auth_error(f'Could not create the Supabase client: {_short_error(exc)}')
    _client_cache[key] = client
    return client


def get_supabase_client():
    """Client used for `app_users` reads/writes (service-role key when present)."""
    if SUPABASE_ADMIN_KEY:
        admin = _build_supabase_client(SUPABASE_ADMIN_KEY)
        if admin is not None:
            return admin
    return _build_supabase_client(SUPABASE_PUBLIC_KEY)


def get_supabase_auth_client():
    """Client used for Supabase Auth e-mail/password sign-in."""
    if SUPABASE_PUBLIC_KEY:
        public = _build_supabase_client(SUPABASE_PUBLIC_KEY)
        if public is not None:
            return public
    return get_supabase_client()


def supabase_status():
    """Secret-free summary of the Supabase wiring, exposed through /health."""
    client = get_supabase_client()
    return {
        'url_configured': bool(SUPABASE_URL),
        'publishable_key_configured': bool(SUPABASE_PUBLIC_KEY),
        'service_role_key_configured': bool(SUPABASE_ADMIN_KEY),
        'client_configured': client is not None,
        'publishable_key_is_denied_by_rls': bool(SUPABASE_URL)
        and not bool(SUPABASE_ADMIN_KEY),
    }


def _count_visible_accounts():
    """Number of `app_users` rows the configured key can actually read.

    With the service-role key this is the real number of accounts. With only the
    publishable key, row level security hides everything and this returns 0,
    which is the fastest way to spot a misconfigured deployment.
    """
    supabase = get_supabase_client()
    if supabase is None:
        return None
    try:
        result = supabase.table(AUTH_TABLE).select('username').execute()
        return len(result.data or [])
    except Exception:
        return None


def _probe_supabase_users_table():
    """Return ``(reachable, error_message)`` without touching the global state."""
    supabase = get_supabase_client()
    if supabase is None:
        return False, 'No Supabase client could be created from the environment.'
    try:
        supabase.table(AUTH_TABLE).select('username').limit(1).execute()
        return True, None
    except Exception as exc:
        return False, f'Supabase `{AUTH_TABLE}` is not reachable: {_short_error(exc)}'


def ensure_supabase_users_table():
    """Check that the Supabase login table is reachable with the configured key."""
    reachable, error = _probe_supabase_users_table()
    if not reachable and error:
        _set_auth_error(error)
    if not SUPABASE_ADMIN_KEY:
        _set_auth_error(
            'SUPABASE_SERVICE_ROLE_KEY is not configured on this server, so row '
            'level security will hide every row of app_users.'
        )
    return reachable


def user_exists(username):
    """Check whether a username already exists in Supabase."""
    username = (username or '').strip()
    if not username:
        return False

    supabase = get_supabase_client()
    if supabase is None:
        _set_auth_error(
            'Supabase is not configured on this server: SUPABASE_URL and/or '
            'SUPABASE_SERVICE_ROLE_KEY are missing from the environment.'
        )
        return False

    try:
        result = supabase.table(AUTH_TABLE).select(
            'username').eq('username', username).limit(1).execute()
        return bool(result.data)
    except Exception as exc:
        _set_auth_error(f'Could not read `{AUTH_TABLE}`: {_short_error(exc)}')
        return False


def save_user(username, password):
    """Create or update an account in Supabase. Returns True only on success."""
    username = (username or '').strip()
    password = (password or '').strip()
    if not username or not password:
        return False

    supabase = get_supabase_client()
    if supabase is None:
        _set_auth_error(
            'Supabase is not configured on this server: SUPABASE_URL and/or '
            'SUPABASE_SERVICE_ROLE_KEY are missing from the environment.'
        )
        return False

    if not SUPABASE_ADMIN_KEY:
        _set_auth_error(
            'SUPABASE_SERVICE_ROLE_KEY is missing on this server. The '
            'publishable key cannot write to app_users because row level '
            'security is enabled.'
        )

    try:
        # `created_at` is deliberately not sent so the database default is
        # preserved instead of being rewritten on every upsert.
        supabase.table(AUTH_TABLE).upsert({
            'username': username,
            'password_hash': hash_password(password),
        }, on_conflict='username').execute()
        return True
    except Exception as exc:
        _set_auth_error(f'Supabase rejected the new account: {_short_error(exc)}')
        return False


def validate_user(username, password):
    """Validate a sign-in against Supabase Auth or the Supabase `app_users` table.

    Supabase is the only account store, so a failure here always means either a
    wrong password or a Supabase/configuration problem - never a stale local file.
    """
    username = (username or '').strip()
    password = (password or '').strip()
    if not username or not password:
        return False

    # 1) Supabase Auth (only meaningful when the user typed an e-mail address).
    if '@' in username:
        auth_client = get_supabase_auth_client()
        if auth_client is not None:
            try:
                auth_client.auth.sign_in_with_password({
                    'email': username,
                    'password': password,
                })
                return True
            except Exception as exc:
                _set_auth_error(f'Supabase Auth: {_short_error(exc)}')

    # 2) The application's own `app_users` table (sha256 hashed passwords).
    supabase = get_supabase_client()
    if supabase is None:
        _set_auth_error(
            'Supabase is not configured on this server (SUPABASE_URL and '
            'SUPABASE_SERVICE_ROLE_KEY are missing), so no account could be checked.'
        )
        return False

    expected_hash = hash_password(password)
    try:
        result = supabase.table(AUTH_TABLE).select(
            'username, password_hash').eq('username', username).execute()
        rows = result.data or []
        for row in rows:
            if row.get('password_hash') == expected_hash:
                return True
        if not rows and not SUPABASE_ADMIN_KEY:
            _set_auth_error(
                'SUPABASE_SERVICE_ROLE_KEY is missing on this server, so row '
                'level security hides every row of app_users.'
            )
    except Exception as exc:
        _set_auth_error(f'Could not read `{AUTH_TABLE}`: {_short_error(exc)}')

    return False


ensure_supabase_users_table()
_auth_error = None  # startup probes must not show up on the login screen

# ============================================================================
# LOGIN SCREEN + MAIN APP LAYOUT
# ============================================================================


def create_login_layout(error_message=None, success_message=None, username_value='',
                        password_value='', detail_message=None):
    """Render the initial sign-in form before the dashboard loads."""
    status = []
    if error_message:
        status.append(html.Div(error_message, className='text-danger mt-2 text-center',
                               style={'fontWeight': '600'}))
    if success_message:
        status.append(html.Div(success_message, className='text-success mt-2 text-center',
                               style={'fontWeight': '600'}))
    if detail_message and SHOW_AUTH_DIAGNOSTICS:
        # Small technical hint (missing env var, RLS denial, ...) that makes a
        # cloud configuration problem obvious instead of "invalid password".
        status.append(html.Div([
            html.I(className='fas fa-circle-info me-1'),
            detail_message,
        ], className='mt-2 text-center', style={
            'color': '#fbbf24', 'fontSize': '0.78rem', 'lineHeight': '1.35'
        }))

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div([
                        # Hidden register components so the callback's
                        # Input('register-button') / State('register-*') always
                        # resolve, even with the Create Account dialog commented out.
                        dcc.Input(id='register-username', type='text',
                                  value='', style={'display': 'none'}),
                        dcc.Input(id='register-password', type='password',
                                  value='', style={'display': 'none'}),
                        dcc.Input(id='register-confirm-password', type='password',
                                  value='', style={'display': 'none'}),
                        dbc.Button('Create Account', id='register-button',
                                   color='success', className='d-none', n_clicks=0),
                        html.H1('Welcome to IBEX-WIRELESS', className='text-center mb-3',
                                style={'fontWeight': '800', 'color': '#f8fafc'}),
                        html.P('Sign in to continue to the dashboard.',
                               className='text-center mb-4', style={'color': '#94a3b8'}),

                        dbc.Card([
                            dbc.CardBody([
                                html.H3('Login', className='mb-4 text-center',
                                        style={'color': '#f8fafc'}),
                                dbc.Label('User Name', html_for='username', style={
                                          'color': '#e2e8f0'}),
                                dbc.Input(id='username', type='text', placeholder='Enter your user name',
                                          className='mb-3', value=username_value),
                                dbc.Label('Password', html_for='password', style={
                                          'color': '#e2e8f0'}),
                                dbc.Input(id='password', type='password', placeholder='Enter your password',
                                          className='mb-3', value=password_value),
                                dbc.Button('Login', id='login-button', color='primary', className='w-100 mt-2',
                                           n_clicks=0),
                                dbc.Button('Logout', id='logout-button', color='secondary', className='d-none',
                                           n_clicks=0),
                                dbc.Button('Logout', id='logout-button-visible', color='secondary', className='d-none',
                                           n_clicks=0),
                                *status,
                            ])
                        ], style={
                            'background': '#1e293b',
                            'border': '1px solid #334155',
                            'borderRadius': '20px',
                            'maxWidth': '420px',
                            'margin': '0 auto',
                            'boxShadow': '0 20px 40px rgba(0, 0, 0, 0.35)'
                        }),

                        # --- "Create Account" dialog box (disabled/commented out) ---
                        # *([] if not SHOW_CREATE_ACCOUNT else [dbc.Card([
                        #     dbc.CardBody([
                        #         html.H4('Create Account', className='mb-3 text-center',
                        #                 style={'color': '#f8fafc'}),
                        #         dbc.Label(
                        #             'New User Name', html_for='register-username', style={'color': '#e2e8f0'}),
                        #         dbc.Input(id='register-username', type='text', placeholder='Choose a username',
                        #                   className='mb-3'),
                        #         dbc.Label(
                        #             'New Password', html_for='register-password', style={'color': '#e2e8f0'}),
                        #         dbc.Input(id='register-password', type='password', placeholder='Choose a password',
                        #                   className='mb-3'),
                        #         dbc.Label(
                        #             'Confirm Password', html_for='register-confirm-password', style={'color': '#e2e8f0'}),
                        #         dbc.Input(id='register-confirm-password', type='password', placeholder='Confirm your password',
                        #                   className='mb-3'),
                        #         dbc.Button('Create Account', id='register-button', color='success',
                        #                    className='w-100 mt-2', n_clicks=0),
                        #     ])
                        # ], style={
                        #     'background': '#111827',
                        #     'border': '1px solid #334155',
                        #     'borderRadius': '20px',
                        #     'maxWidth': '420px',
                        #     'margin': '0 auto',
                        #     'boxShadow': '0 20px 40px rgba(0, 0, 0, 0.35)'
                        # })]),


                    ], style={'paddingTop': '80px', 'paddingBottom': '80px'})
                ], style={'minHeight': '100vh', 'display': 'flex', 'alignItems': 'center',
                          'justifyContent': 'center', 'background': 'linear-gradient(135deg, #0f172a 0%, #111827 100%)'})
            ], width=12)
        ])
    ], fluid=True)


def create_main_layout(username=''):
    """Render the dashboard application layout after login."""
    user_label = username or 'User'
    return dbc.Container([
        dcc.Location(id='url', refresh=False),
        html.Div([
            dcc.Input(id='username', type='text',
                      value='', style={'display': 'none'}),
            dcc.Input(id='password', type='password',
                      value='', style={'display': 'none'}),
            dcc.Input(id='register-username', type='text',
                      value='', style={'display': 'none'}),
            dcc.Input(id='register-password', type='password',
                      value='', style={'display': 'none'}),
            dcc.Input(id='register-confirm-password', type='password',
                      value='', style={'display': 'none'}),
            dbc.Button('Login', id='login-button', color='primary',
                       className='d-none', n_clicks=0),
            dbc.Button('Create Account', id='register-button',
                       color='success', className='d-none', n_clicks=0),
            dbc.Button('Logout', id='logout-button',
                       color='secondary', className='d-none', n_clicks=0),
        ], style={'display': 'none'}),
        dbc.Row([
            dbc.Col(create_navbar(), width=12),
        ], className='g-0'),
        dbc.Row([
            dbc.Col(
                html.Div(
                    f'Welcome, {user_label}!',
                    className='text-light fw-bold ms-2 mt-2',
                    style={'fontSize': '1.1rem'}
                ),
                width='auto',
                className='ms-3'
            ),
            dbc.Col(
                dbc.Button(
                    'Logout',
                    id='logout-button-visible',
                    color='secondary',
                    className='mt-2',
                    n_clicks=0,
                ),
                width='auto',
                className='ms-auto me-3',
            ),
        ], className='align-items-center mb-3'),
        html.Div(id='page-content', children=dash.page_container),
        create_footer(),
        dcc.Store(id='filtered-data-store'),
        dcc.Store(id='current-filters-store'),
        dcc.Store(id='logged-in-user', data={'username': username}),
    ], fluid=True, className='main-container')


app.layout = html.Div([
    dcc.Store(id='session-user',
              data={'username': None}, storage_type='local'),
    html.Div(id='app-root', children=create_login_layout())
])


@app.callback(
    Output('app-root', 'children'),
    Output('session-user', 'data'),
    Input('login-button', 'n_clicks'),
    Input('logout-button', 'n_clicks'),
    Input('logout-button-visible', 'n_clicks'),
    Input('register-button', 'n_clicks'),
    Input('session-user', 'data'),
    State('username', 'value'),
    State('password', 'value'),
    State('register-username', 'value'),
    State('register-password', 'value'),
    State('register-confirm-password', 'value'),
    prevent_initial_call=False
)
def authenticate_user(login_clicks, logout_clicks, logout_visible_clicks, register_clicks,
                      stored_session, username, password, register_username,
                      register_password, register_confirm_password):
    """Handle login, logout, registration and session persistence.

    Two Dash behaviours are guarded here, because together they made signing in
    impossible on the deployed app:

    * Dash fires this callback again every time the layout below is replaced,
      passing the brand new buttons with ``n_clicks == 0``. The freshly rendered
      Logout button therefore used to sign the user straight back out, so the
      login page reappeared no matter which credentials were used.
    * The very first call of the page arrives before the browser has reported
      the value saved in ``localStorage``. Returning ``{'username': None}``
      there overwrote the saved session, so a refresh never stayed signed in.

    ``session-user`` is now only written when it really changes, and ``app-root``
    always receives a value.
    """
    trigger = ctx.triggered_id
    login_clicks = login_clicks or 0
    logout_clicks = logout_clicks or 0
    logout_visible_clicks = logout_visible_clicks or 0
    register_clicks = register_clicks or 0
    stored_username = (stored_session or {}).get('username')

    # --- first paint & session restore --------------------------------------
    if trigger in (None, 'session-user'):
        if stored_username:
            return create_main_layout(username=stored_username), no_update
        return create_login_layout(), no_update  # never clear the saved session

    # --- logout -------------------------------------------------------------
    if trigger in ('logout-button', 'logout-button-visible'):
        if not logout_clicks and not logout_visible_clicks:
            return no_update, no_update  # button was rendered, not clicked
        return create_login_layout(), {'username': None}

    # --- create account -----------------------------------------------------
    if trigger == 'register-button':
        if not register_clicks:
            return no_update, no_update

        register_username = (register_username or '').strip()
        register_password = (register_password or '').strip()
        register_confirm_password = (register_confirm_password or '').strip()

        if not register_username or not register_password or not register_confirm_password:
            return create_login_layout(
                'Please complete all account fields.'), no_update
        if register_password != register_confirm_password:
            return create_login_layout(
                'Passwords do not match.', username_value=register_username), no_update
        if user_exists(register_username):
            return create_login_layout(
                'That username already exists.', username_value=register_username), no_update
        if save_user(register_username, register_password):
            return create_login_layout(
                success_message='Account created. You can now log in.',
                username_value=register_username), no_update
        return create_login_layout(
            'Unable to create the account.',
            username_value=register_username,
            detail_message=_consume_auth_error()), no_update

    # --- sign in ------------------------------------------------------------
    if not login_clicks:
        return no_update, no_update  # login button was rendered, not clicked

    username = (username or '').strip()
    password = (password or '').strip()

    if not username or not password:
        return create_login_layout(
            'Please enter both User Name and Password.',
            username_value=username, password_value=password), no_update

    if validate_user(username, password):
        return create_main_layout(username=username), {'username': username}

    return create_login_layout(
        'Invalid username or password. Please try again.',
        username_value=username, password_value=password,
        detail_message=_consume_auth_error()), no_update


# ============================================================================
# FLASK ROUTES (Non-Dash pages if needed)
# ============================================================================


@server.route('/health')
def health_check():
    """Liveness probe plus a secret-free summary of the Supabase wiring.

    Useful right after a deploy: open /health on the live site to see whether
    Supabase is configured, how many accounts are visible and whether the data
    files were bundled.
    """
    reachable, table_error = _probe_supabase_users_table()

    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'serverless': bool(os.getenv('VERCEL')),
        'python': sys.version.split()[0],
        'accounts_backend': 'supabase',
        'supabase': supabase_status(),
        'supabase_app_users_reachable': reachable,
        'supabase_error': table_error,
        'accounts_visible': _count_visible_accounts(),
        'data_files': {
            'sales_update_xlsx': os.path.exists(
                os.path.join(APP_ROOT, 'data', 'SALES UPDATE.xlsx')),
            'custom_css': os.path.exists(
                os.path.join(APP_ROOT, 'assets', 'custom.css')),
        },
    }

# ============================================================================
# RUN APPLICATION
# ============================================================================


if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Copy sample data if not exists (for first run)
    if not os.path.exists('data/SALES UPDATE.xlsx'):
        print("\n⚠️  Please place your 'SALES UPDATE.xlsx' file in the 'data/' folder")
        print("   Expected path: data/SALES UPDATE.xlsx\n")

    print("\n" + "="*60)
    print("  SALES ANALYTICS DASHBOARD")
    print("="*60)
    print("  Open your browser and navigate to:")
    print("  http://127.0.0.1:8050/")
    print("="*60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=8050)