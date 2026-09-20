"""
Sales Dashboard Application
===========================
Main entry point integrating Flask with Dash for multi-page dashboard.

Run with: python app.py
"""

import hashlib
import os
import sqlite3
import sys
from flask import Flask, render_template_string, send_from_directory
from dotenv import load_dotenv
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table, ctx
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
# AUTH DATABASE (SQLite fallback + optional Supabase support)
# ============================================================================


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(APP_ROOT, '.env'))
AUTH_DB_PATH = os.path.join(APP_ROOT, 'data', 'auth_users.db')


def hash_password(password):
    """Hash a password before saving it to the database."""
    return hashlib.sha256(str(password).strip().encode('utf-8')).hexdigest()


def get_supabase_client():
    """Return a Supabase client using the configured server-side or public env values."""
    supabase_url = (
        os.getenv('SUPABASE_URL')
        or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    )
    supabase_key = (
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        or os.getenv('SUPABASE_KEY')
        or os.getenv('NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY')
    )
    if not supabase_url or not supabase_key:
        return None

    try:
        from supabase import create_client
        return create_client(supabase_url, supabase_key)
    except Exception:
        return None


def initialize_auth_db():
    """Create the local fallback auth table without creating any default account."""
    os.makedirs(os.path.dirname(AUTH_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS app_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.commit()
    conn.close()


def ensure_supabase_users_table():
    """Try to ensure the login table exists in Supabase when configured."""
    supabase = get_supabase_client()
    if not supabase:
        return False

    try:
        supabase.table('app_users').select('username').limit(1).execute()
        return True
    except Exception:
        return False


def user_exists(username):
    """Check whether a username already exists in the configured database."""
    username = (username or '').strip()
    if not username:
        return False

    supabase = get_supabase_client()
    if supabase:
        try:
            result = supabase.table('app_users').select(
                'username').eq('username', username).limit(1).execute()
            rows = result.data or []
            if rows:
                return True
        except Exception:
            pass

    conn = sqlite3.connect(AUTH_DB_PATH)
    row = conn.execute(
        'SELECT 1 FROM app_users WHERE username = ?', (username,)
    ).fetchone()
    conn.close()
    return row is not None


def save_user(username, password):
    """Save a username/password pair directly to Supabase, with SQLite as fallback."""
    username = (username or '').strip()
    password = (password or '').strip()
    if not username or not password:
        return False

    hashed_password = hash_password(password)

    supabase = get_supabase_client()
    if supabase:
        try:
            supabase.table('app_users').upsert({
                'username': username,
                'password_hash': hashed_password,
                'created_at': datetime.utcnow().isoformat()
            }, on_conflict='username').execute()
            # Keep local DB synced for fallback, but do not block Supabase success.
            conn = sqlite3.connect(AUTH_DB_PATH)
            conn.execute(
                'INSERT OR IGNORE INTO app_users (username, password_hash) VALUES (?, ?)',
                (username, hashed_password),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            pass

    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.execute(
        'INSERT OR IGNORE INTO app_users (username, password_hash) VALUES (?, ?)',
        (username, hashed_password),
    )
    conn.commit()
    conn.close()
    return True


def validate_user(username, password):
    """Check custom app users and Supabase Auth credentials."""
    username = (username or '').strip()
    password = (password or '').strip()
    if not username or not password:
        return False

    expected_hash = hash_password(password)

    supabase = get_supabase_client()
    if supabase:
        # Support users created in Supabase Authentication as well as the
        # application's legacy app_users table.
        try:
            supabase.auth.sign_in_with_password({
                'email': username,
                'password': password,
            })
            return True
        except Exception:
            pass

        try:
            result = supabase.table('app_users').select(
                '*').eq('username', username).execute()
            rows = result.data or []
            for row in rows:
                if row.get('password_hash') == expected_hash:
                    return True
            # If Supabase is reachable but username wasn't found, do not immediately fail if
            # there is a local fallback row; this helps keep a backup working when syncing is delayed.
        except Exception:
            pass

    conn = sqlite3.connect(AUTH_DB_PATH)
    row = conn.execute(
        'SELECT 1 FROM app_users WHERE username = ? AND password_hash = ?',
        (username, expected_hash),
    ).fetchone()
    conn.close()
    return row is not None


initialize_auth_db()


def sync_local_auth_to_supabase():
    """Mirror the local auth database into Supabase if credentials are configured."""
    supabase = get_supabase_client()
    if not supabase:
        return False

    try:
        conn = sqlite3.connect(AUTH_DB_PATH)
        rows = conn.execute(
            'SELECT username, password_hash FROM app_users ORDER BY id'
        ).fetchall()
        conn.close()

        for username, password_hash in rows:
            supabase.table('app_users').upsert({
                'username': username,
                'password_hash': password_hash,
                'created_at': datetime.utcnow().isoformat()
            }, on_conflict='username').execute()
        return True
    except Exception:
        return False


ensure_supabase_users_table()
sync_local_auth_to_supabase()

# ============================================================================
# LOGIN SCREEN + MAIN APP LAYOUT
# ============================================================================


def create_login_layout(error_message=None, success_message=None, username_value='', password_value=''):
    """Render the initial sign-in form before the dashboard loads."""
    status = []
    if error_message:
        status.append(html.Div(error_message, className='text-danger mt-2 text-center',
                               style={'fontWeight': '600'}))
    if success_message:
        status.append(html.Div(success_message, className='text-success mt-2 text-center',
                               style={'fontWeight': '600'}))

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div([
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

                        *([] if not SHOW_CREATE_ACCOUNT else [dbc.Card([
                            dbc.CardBody([
                                html.H4('Create Account', className='mb-3 text-center',
                                        style={'color': '#f8fafc'}),
                                dbc.Label(
                                    'New User Name', html_for='register-username', style={'color': '#e2e8f0'}),
                                dbc.Input(id='register-username', type='text', placeholder='Choose a username',
                                          className='mb-3'),
                                dbc.Label(
                                    'New Password', html_for='register-password', style={'color': '#e2e8f0'}),
                                dbc.Input(id='register-password', type='password', placeholder='Choose a password',
                                          className='mb-3'),
                                dbc.Label(
                                    'Confirm Password', html_for='register-confirm-password', style={'color': '#e2e8f0'}),
                                dbc.Input(id='register-confirm-password', type='password', placeholder='Confirm your password',
                                          className='mb-3'),
                                dbc.Button('Create Account', id='register-button', color='success',
                                           className='w-100 mt-2', n_clicks=0),
                            ])
                        ], style={
                            'background': '#111827',
                            'border': '1px solid #334155',
                            'borderRadius': '20px',
                            'maxWidth': '420px',
                            'margin': '0 auto',
                            'boxShadow': '0 20px 40px rgba(0, 0, 0, 0.35)'
                        })]),

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
    """Handle login, logout, and session persistence for the current login-only layout."""
    trigger = ctx.triggered_id if ctx.triggered_id else None

    if trigger == 'session-user':
        stored_username = (stored_session or {}).get('username')
        if stored_username:
            return create_main_layout(username=stored_username), {'username': stored_username}
        return create_login_layout(), {'username': None}

    if trigger in ('logout-button', 'logout-button-visible'):
        return create_login_layout(), {'username': None}

    if trigger == 'register-button':
        register_username = (register_username or '').strip()
        register_password = (register_password or '').strip()
        register_confirm_password = (register_confirm_password or '').strip()

        if not register_username or not register_password or not register_confirm_password:
            return create_login_layout(
                'Please complete all account fields.'), {'username': None}
        if register_password != register_confirm_password:
            return create_login_layout(
                'Passwords do not match.', username_value=register_username), {'username': None}
        if user_exists(register_username):
            return create_login_layout(
                'That username already exists.', username_value=register_username), {'username': None}
        if save_user(register_username, register_password):
            return create_login_layout(
                success_message='Account created. You can now log in.',
                username_value=register_username), {'username': None}
        return create_login_layout(
            'Unable to create the account. Please try again.',
            username_value=register_username), {'username': None}

    username = (username or '').strip()
    password = (password or '').strip()

    if not username or not password:
        return create_login_layout('Please enter both User Name and Password.', username_value=username, password_value=password), {'username': None}

    if validate_user(username, password):
        return create_main_layout(username=username), {'username': username}

    return create_login_layout('Invalid username or password. Please try again.', username_value=username, password_value=password), {'username': None}


# ============================================================================
# FLASK ROUTES (Non-Dash pages if needed)
# ============================================================================


@server.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

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