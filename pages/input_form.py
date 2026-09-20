"""
Store Deposit & Expense Input Form Page
=======================================
Dash port of E:\\Python\\Input_form\\input_form.py.
Schema-driven: the form fields are generated from the actual columns of the
Supabase `expenses` table (fetched live at startup), and inserts are built
dynamically — new/renamed columns in Supabase are reflected automatically
after an app restart.
"""

import base64
import os
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv

from dash import dcc, html, Input, Output, State, callback, dash_table
from dash.dash_table import FormatTemplate
import dash_bootstrap_components as dbc
from dash import register_page

# ------------------------------------------------------------------------------
# Supabase setup (loads sales_dashboard_app/.env)
# ------------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_HERE)
load_dotenv(os.path.join(_APP_DIR, ".env"))
load_dotenv()  # fallback to CWD

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
TABLE = "expenses"
BUCKET = "expense-images"

# Columns managed by the DB / UI specially — never rendered as form inputs.
_SYSTEM_COLS = {"id", "created_at"}
UPLOAD_COL = "image_url"          # handled by the image upload widget
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

_client = None


def get_supabase():
    """Return a cached Supabase client or raise if not configured."""
    from supabase import create_client
    global _client
    if _client is not None:
        return _client
    # The service-role key is preferred: the anon/publishable key is blocked by
    # row level security, which makes every read come back empty and every
    # insert/upload fail.
    api_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY")
               or os.getenv("SUPABASE_KEY")
               or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
               or "")
    if not SUPABASE_URL or not api_key:
        raise RuntimeError(
            "Missing or invalid Supabase configuration. "
            "Add SUPABASE_URL and a real JWT anon/service_role key to the app's .env file."
        )
    _client = create_client(SUPABASE_URL, api_key)
    return _client


def _pretty(name: str) -> str:
    return name.replace("_", " ").title()


def _fetch_schema():
    """Infer editable columns of the Supabase table from a real data row.

    Returns an ordered list of dicts: {name, label, kind} where kind is one of
    'text' | 'number' | 'date'. Falls back to the original known schema when
    the table is empty or unreachable.
    """
    default = [
        {"name": "entry_date",   "label": "Date",         "kind": "date"},
        {"name": "store_name",   "label": "Store Name",   "kind": "text"},
        {"name": "emp_name",     "label": "Emp Name",     "kind": "text"},
        {"name": "cash_in_hand", "label": "Cash in Hand", "kind": "number"},
        {"name": "expense_amt",  "label": "Expense Amt",  "kind": "number"},
        {"name": "expense_type", "label": "Expense Type", "kind": "text"},
        {"name": "comments",     "label": "Comments/Extra Notes", "kind": "text"},
    ]
    try:
        result = (get_supabase().table(TABLE)
                  .select("*").limit(1).execute())
        rows = result.data or []
        if not rows:
            return default
        fields = []
        for name, value in rows[0].items():
            if name in _SYSTEM_COLS or name == UPLOAD_COL:
                continue
            if isinstance(value, bool):
                kind = "text"
            elif isinstance(value, (int, float)):
                kind = "number"
            elif isinstance(value, str) and len(value) == 10 and value[4] == "-" and value[7] == "-":
                kind = "date"
            else:
                kind = "text"
            fields.append({"name": name, "label": _pretty(name), "kind": kind})
        # Keep the familiar ordering first, then any brand-new columns.
        ordered = [f for f in default if f["name"] in {x["name"] for x in fields}]
        extra = [f for f in fields if f["name"] not in {x["name"] for x in ordered}]
        return ordered + extra
    except Exception:
        return default


FIELD_DEFS = _fetch_schema()
_FIELD_NAMES = [f["name"] for f in FIELD_DEFS]
_NUMERIC_FIELDS = [f["name"] for f in FIELD_DEFS if f["kind"] == "number"]
_DATE_FIELDS = [f["name"] for f in FIELD_DEFS if f["kind"] == "date"]
UPLOAD_FIELD_LABEL = _pretty(UPLOAD_COL)

# DataTable columns mirror the live Supabase schema; the image column renders
# as a clickable link. A derived "Month" column is inserted right after the
# date field and shows the entry date as MMM-YY (e.g. "Jan-26").
_MONTH_COL = 'month'
_MONEY_FIELDS = {'cash_in_hand', 'expense_amt'}
_def_cols = [{'name': f['label'], 'id': f['name'],
              'type': 'numeric' if f['kind'] == 'number' else 'text',
              **({'format': FormatTemplate.money(2)}
                 if f['name'] in _MONEY_FIELDS else {})}
             for f in FIELD_DEFS]
if _DATE_FIELDS:
    _idx = next((i for i, c in enumerate(_def_cols) if c['id'] == _DATE_FIELDS[0]), 1)
    _def_cols.insert(_idx + 1, {'name': 'Month', 'id': _MONTH_COL, 'type': 'text'})
else:
    _def_cols.append({'name': 'Month', 'id': _MONTH_COL, 'type': 'text'})
TABLE_COLUMNS = (_def_cols
                 + [{'name': UPLOAD_FIELD_LABEL, 'id': UPLOAD_COL,
                     'presentation': 'markdown'}])


def load_supabase_data() -> pd.DataFrame:
    """Fetch all expense rows from Supabase, return as DataFrame."""
    supabase = get_supabase()
    order_col = _DATE_FIELDS[0] if _DATE_FIELDS else None
    q = supabase.table(TABLE).select("*")
    if order_col:
        q = q.order(order_col, desc=True)
    rows = q.execute().data or []
    df = pd.DataFrame(rows)
    keep_order = ([f["name"] for f in FIELD_DEFS]
                  + ([UPLOAD_COL] if UPLOAD_COL in df.columns else []))
    ordered = [c for c in keep_order if c in df.columns]
    extra = [c for c in df.columns if c not in ordered]
    df = df[ordered + extra]
    return df


def parse_upload(contents):
    """Decode a dcc.Upload base64 data-URL into (bytes, mime_type)."""
    try:
        header, b64 = contents.split(",", 1)
        mime = header.split(";")[0].split(":")[1]
        return base64.b64decode(b64), mime
    except Exception:
        return None, None


def upload_image(data, filename, mimetype):
    """Upload bytes to Supabase Storage, returning its public URL."""
    supabase = get_supabase()
    ext = (filename.rsplit(".", 1)[-1] or "png").lower()
    path = f"{uuid.uuid4()}.{ext}"
    supabase.storage.from_(BUCKET).upload(
        path=path,
        file=data,
        file_options={"content-type": mimetype or "image/png"},
    )
    return supabase.storage.from_(BUCKET).get_public_url(path)


register_page(__name__, path='/deposit-expense', title='Store Deposit & Expense Details', description='Submit store deposit and expense records to the Supabase database.')


def _ctrl():
    return {'background': '#0f172a', 'color': '#e2e8f0', 'border': '1px solid #334155', 'borderRadius': '10px'}


def _field(label, control, icon='fa-pen'):
    return dbc.Col([
        html.Label([html.I(className=f'fas {icon} me-2', style={'color': '#3b82f6'}), label],
                   className='mb-2', style={'color': "#ffffff", 'fontWeight': '600'}),
        control
    ], xs=12, md=6)


def _stat_card(title, color, cid, gradient):
    return dbc.Card(dbc.CardBody([
        html.P(title, className='mb-1 text-center',
               style={'color': '#ffffff', 'fontSize': '0.8rem', 'textTransform': 'uppercase',
                      'fontWeight': '700', 'textShadow': '0 1px 3px rgba(0,0,0,0.45)'}),
        html.H3(id=cid, children='0', className='fw-bold mb-0 text-center',
                style={'color': '#ffffff', 'textShadow': '0 2px 6px rgba(0,0,0,0.5)'}),
    ]), className='gradient-stat',
      style={'--stat-grad': gradient,
             'border': '1px solid rgba(255,255,255,0.25)',
             'borderRadius': '18px',
             'boxShadow': '0 6px 18px rgba(0,0,0,0.35)'})


_HEADER = html.Div([
    html.H2([html.I(className='fas fa-money-bill-wave me-3', style={'color': '#3b82f6'}),
             'Store Deposit & Expense'], className='fw-bold mb-2', style={'color': '#f8fafc'}),
    html.P('Submit one entry per date. Records are saved permanently to the Database.',
           style={'color': '#94a3b8'}, className='mb-4'),
])

# Bright gradient backgrounds per stat card, keyed by accent colour.
_STAT_GRADIENTS = {
    '#6366f1': 'linear-gradient(135deg, #818cf8 0%, #6366f1 50%, #4f46e5 100%)',
    '#10b981': 'linear-gradient(135deg, #46ec18 0%, #10b981 50%, #059669 100%)',
    '#ef4444': 'linear-gradient(135deg, #fb7185 0%, #ef4444 50%, #dc2626 100%)',
}

_STAT_COLS = [dbc.Col(_stat_card('Total Records', '#6366f1', 'if-stats-rec',
                                 _STAT_GRADIENTS['#6366f1']), xs=12, sm=4, className='mb-3')]
for _n, _c in zip(_NUMERIC_FIELDS[:2], ['#10b981', '#ef4444']):
    _STAT_COLS.append(dbc.Col(_stat_card(_pretty(_n), _c, f'if-num-{_n}',
                                         _STAT_GRADIENTS[_c]), xs=12, sm=4, className='mb-3'))
_STATS_ROW = dbc.Row(_STAT_COLS, className='stats-row')

_ICONS = {'text': 'fa-pen', 'number': 'fa-dollar-sign', 'date': 'fa-calendar'}

_GRADIENT = 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
_FILTER_STYLE = {'background': '#1e293b', 'border': '1px solid #334155', 'borderRadius': '20px'}

DATE_RANGE_OPTIONS = [
    {'label': 'All Time', 'value': 'All Time'},
    {'label': 'Current Month', 'value': 'Current Month'},
    {'label': 'Last Month', 'value': 'Last Month'},
    {'label': 'Last 3 Months', 'value': 'Last 3 Months'},
    {'label': 'Custom Date', 'value': 'Custom Date'},
]


def _build_store_options(df):
    """Store Name dropdown options derived from the available data."""
    if df is not None and not df.empty and 'store_name' in df.columns:
        vals = [str(v) for v in pd.unique(df['store_name'].dropna())]
        return ([{'label': 'All', 'value': 'All'}]
                + [{'label': v, 'value': v} for v in sorted(set(vals))])
    return [{'label': 'All', 'value': 'All'}]


def _apply_filters(df, stores, date_range, custom_start=None, custom_end=None):
    """Filter the expense DataFrame by Store Name and Date Range (same options as other pages)."""
    if df is None or df.empty:
        return df
    result = df.copy()
    if stores and 'All' not in stores:
        col = 'store_name' if 'store_name' in result.columns else None
        if col:
            result = result[result[col].astype(str).isin(stores)]

    date_col = _DATE_FIELDS[0] if _DATE_FIELDS and _DATE_FIELDS[0] in result.columns else None
    if not date_col:
        return result
    try:
        d = pd.to_datetime(result[date_col], errors='coerce')
    except (TypeError, ValueError):
        return result

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if date_range == 'Current Month':
        start = today.replace(day=1)
        result = result[(d >= pd.Timestamp(start)) & (d < pd.Timestamp(today + timedelta(days=1)))]
    elif date_range == 'Last Month':
        first_this = today.replace(day=1)
        start = (first_this - timedelta(days=1)).replace(day=1)
        result = result[(d >= pd.Timestamp(start)) & (d < pd.Timestamp(first_this))]
    elif date_range == 'Last 3 Months':
        result = result[d >= pd.Timestamp(today - timedelta(days=90))]
    elif date_range == 'Custom Date' and custom_start and custom_end:
        try:
            cs = pd.Timestamp(custom_start)
            ce = pd.Timestamp(custom_end) + pd.Timedelta(days=1)
            result = result[(d >= cs) & (d < ce)]
        except (TypeError, ValueError):
            pass
    return result


def _filter_section(store_options):
    """Filter card with only the Date Range and Store Name fields (plus an Apply button)."""
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label([html.I(className='fas fa-store me-2', style={'color': '#6366f1'}),
                                'Store Name'], className='filter-label mb-2'),
                    dcc.Dropdown(id='if-store-filter', options=store_options, value=['All'],
                                 multi=True, placeholder='Select store...', className='dark-dropdown')
                ], xs=12, md=3, className='mb-3 mb-md-0'),
                dbc.Col([
                    html.Label([html.I(className='fas fa-calendar-alt me-2', style={'color': '#f59e0b'}),
                                'Date Range'], className='filter-label mb-2'),
                    dcc.Dropdown(id='if-date-range-filter', options=DATE_RANGE_OPTIONS,
                                 value='Current Month', placeholder='Select date range', className='dark-dropdown')
                ], xs=12, md=6, className='mb-3 mb-md-0'),
                dbc.Col([
                    html.Label([html.I(className='fas fa-sliders-h me-2', style={'color': '#06b6d4'}),
                                'Actions'], className='filter-label mb-2'),
                    dbc.Button([html.I(className='fas fa-sync-alt me-2'), 'Apply Filters'], id='if-apply-btn',
                               color='primary', className='w-100',
                               style={'borderRadius': '12px', 'fontWeight': '600', 'background': _GRADIENT, 'border': 'none'})
                ], xs=12, md=3),
            ], align='end'),
            dbc.Collapse([
                dbc.Row([
                    dbc.Col([html.Label('Start Date', className='filter-label mb-2'),
                             dcc.DatePickerSingle(id='if-custom-start', date=None,
                                                 display_format='YYYY-MM-DD', className='dark-datepicker')], xs=12, md=6),
                    dbc.Col([html.Label('End Date', className='filter-label mb-2'),
                             dcc.DatePickerSingle(id='if-custom-end', date=None,
                                                  display_format='YYYY-MM-DD', className='dark-datepicker')], xs=12, md=6)
                ], className='mt-3')
            ], id='if-custom-collapse', is_open=False),
        ], className='p-3'),
    ], className='filter-card mb-4', style=_FILTER_STYLE)


def build_layout():
    """Read-only page: Recorded Data table straight from Supabase."""
    try:
        df = load_supabase_data()
        initial_data = _table_records(df)
        store_options = _build_store_options(df)
    except Exception:
        initial_data = []
        store_options = [{'label': 'All', 'value': 'All'}]

    return dbc.Container([
        dcc.Download(id='if-download'),
        dcc.Interval(id='if-refresh', interval=60_000, n_intervals=0),

        dbc.Row([dbc.Col(_HEADER, width=12)], className='mb-2'),
        _STATS_ROW,
        _filter_section(store_options),

        # --- Recorded Data (live from Supabase) ---
        dbc.Card([
            dbc.CardHeader(dbc.Row([
                dbc.Col(html.H5([html.I(className='fas fa-table me-2', style={'color': '#3b82f6'}),
                                 'Detailed Table'], className='mb-0',
                                style={'color': '#f8fafc', 'fontWeight': '700'}), xs=12, md=6),
                dbc.Col(dbc.Button([html.I(className='fas fa-download me-2'), 'Download Excel'],
                                   id='if-download-btn', color='success', outline=True,
                                   className='float-md-end', style={'borderRadius': '10px'}),
                        xs=12, md=6, className='mt-2 mt-md-0'),
            ], align='center'), style={'background': 'transparent', 'borderBottom': '1px solid #334155'}),
            dbc.CardBody([
                dcc.Loading([
                    dash_table.DataTable(
                        id='if-table',
                        columns=TABLE_COLUMNS,
                        page_size=10, page_action='native', sort_action='native', filter_action='native',
                        style_table={'overflowX': 'auto', 'borderRadius': '12px'},
                        style_cell={'textAlign': 'center', 'padding': '10px 12px', 'backgroundColor': '#0f172a',
                                    'color': '#e2e8f0', 'border': '1px solid #1e293b', 'fontSize': '14px',
                                    'whiteSpace': 'normal', 'height': 'auto'},
                        style_header={'backgroundColor': '#1e293b', 'color': '#f8fafc', 'fontWeight': '700',
                                      'border': '1px solid #334155', 'textTransform': 'uppercase', 'fontSize': '14px'},
                        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#162032'}],
                        markdown_options={'html': True, 'link_target': '_blank'},
                    )
                ], type='circle', color='#6366f1'),
            ], className='p-3'),
        ], style={'background': '#1e293b', 'border': '1px solid #334155', 'borderRadius': '20px'}),

        # --- Top 10 Stores: Cash vs Expense (custom search area) ---
        dbc.Card([
            dbc.CardHeader(dbc.Row([
                dbc.Col(html.H5([html.I(className='fas fa-ranking-star me-2', style={'color': '#f59e0b'}),
                                 'Cash vs Expense by Month'], className='mb-0',
                                style={'color': '#f8fafc', 'fontWeight': '700'}), xs=12),
            ], align='center'), style={'background': 'transparent', 'borderBottom': '1px solid #334155'}),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label([html.I(className='fas fa-store me-2', style={'color': '#6366f1'}),
                                    'Search Stores'], className='filter-label mb-2'),
                        dcc.Dropdown(id='if-ts-store-filter', options=[],
                                     value=None, multi=True, searchable=True,
                                     placeholder='Type to search stores...',
                                     className='dark-dropdown'),
                    ], xs=12, md=6, className='mb-3 mb-md-0'),
                    dbc.Col([
                        html.Label([html.I(className='fas fa-calendar-alt me-2', style={'color': '#f59e0b'}),
                                    'Month'], className='filter-label mb-2'),
                        dcc.Dropdown(id='if-ts-month-filter', options=[{'label': 'All Months', 'value': 'All'}],
                                     value=None, multi=True, placeholder='Select month...',
                                     className='dark-dropdown'),
                    ], xs=12, md=6),
                ], className='mb-3'),
                dcc.Loading(
                    dcc.Graph(id='if-ts-chart', config={'displayModeBar': True}),
                    type='circle', color='#f59e0b'),
            ], className='p-3'),
        ], className='chart-card shadow-sm mb-4'),

        # --- Cash in Hand vs Expense Amt chart (at the end of the page) ---
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5([html.I(className='fas fa-chart-bar me-2', style={'color': '#10b981'}),
                                        'Cash in Hand vs Expense Amt'], className='mb-0',
                                       style={'color': '#f8fafc', 'fontWeight': '700'}),
                               style={'background': 'transparent', 'borderBottom': '1px solid #334155'}),
                dbc.CardBody([
                    dcc.Loading(
                        dcc.Graph(id='if-chart',
                                  config={'displayModeBar': True}),
                        type='circle', color='#10b981'),
                ], className='p-3'),
            ], className='chart-card shadow-sm'), width=12),
        ], className='mb-4'),
    ], fluid=True, className='px-4 pb-5')


layout = build_layout


def _table_records(df):
    """DataFrame -> DataTable records with a derived Month column (MMM-YY) and
    the image column rendered as a link."""
    records = df.to_dict('records')
    date_col = _DATE_FIELDS[0] if _DATE_FIELDS and _DATE_FIELDS[0] in df.columns else None
    for row in records:
        if date_col:
            dt = pd.to_datetime(row.get(date_col), errors='coerce')
            row[_MONTH_COL] = dt.strftime('%b-%y') if not pd.isna(dt) else ''
        else:
            row[_MONTH_COL] = ''
        url = row.get(UPLOAD_COL)
        if url and str(url).startswith('http'):
            row[UPLOAD_COL] = f'[View Image]({url})'
        else:
            row[UPLOAD_COL] = 'No image'
    return records


# ------------------------------------------------------------------------------
# Chart: "Cash in Hand" vs "Expense Amt"
# ------------------------------------------------------------------------------


# Cash in Hand / Expense Amt chart fields. Each bar is a SINGLE trace (no
# stacked segments). Bar colours come from assets/bar_gradient.js (the SVG
# gradient painted client-side); the fills below are just the matching
# GRADIENTS['if-chart'] first/last stops used as the pre-JS fallback.
_CHART_FIELDS = []
for _cf_name, _cf_fill in (('cash_in_hand', "#054c76"),
                           ('expense_amt', '#d90a9b')):
    if _cf_name in _FIELD_NAMES:
        _CHART_FIELDS.append({'col': _cf_name, 'label': _pretty(_cf_name),
                              'fill': _cf_fill, 'radius': 10})
# Fallback to the first two numeric columns if the expected names are absent.
if not _CHART_FIELDS:
    _CHART_FIELDS = [
        {'col': n, 'label': _pretty(n), 'radius': 10, 'fill': c}
        for n, c in zip(_NUMERIC_FIELDS[:2], ('#054c76', '#d90a9b'))
    ]


def _build_chart(df):
    """Grouped bar chart comparing Cash in Hand vs Expense Amt for the TOP 5
    months with the maximum expense.

    Each metric is a SINGLE bar trace (no stacked segments). Bars are painted
    by the SVG gradient from assets/bar_gradient.js (GRADIENTS['if-chart']),
    with rounded corners and clean hover showing the real monthly total. Months are ordered by expense, highest
    first (5 or fewer months fall back to chronological order).
    """
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color='#e2e8f0', height=360,
        margin=dict(l=55, r=20, t=20, b=45),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(gridcolor='rgba(148,163,184,0.12)', zeroline=False,
                   type='category'),
        yaxis=dict(gridcolor='rgba(148,163,184,0.12)', zeroline=False,
                   tickprefix='$'),
    )

    if df is None or df.empty:
        fig.add_annotation(text='No data available', showarrow=False,
                           font=dict(color='#94a3b8', size=16))
        return fig

    cols = [f for f in _CHART_FIELDS if f['col'] in df.columns]
    if not cols:
        fig.add_annotation(text='Chart fields not available', showarrow=False,
                           font=dict(color='#94a3b8', size=16))
        return fig

    work = df.copy()
    for f in cols:
        work[f['col']] = pd.to_numeric(work[f['col']], errors='coerce').fillna(0)

    date_col = (_DATE_FIELDS[0]
                if _DATE_FIELDS and _DATE_FIELDS[0] in work.columns else None)
    if date_col:
        work['_month_dt'] = pd.to_datetime(work[date_col], errors='coerce')
        work = work.dropna(subset=['_month_dt'])
        # Month label as MMM-YY, sorted chronologically.
        work['_month'] = work['_month_dt'].dt.strftime('%b-%y')
        work['_month_sort'] = work['_month_dt'].dt.strftime('%Y-%m')
        chart_cols = [f['col'] for f in cols]
        monthly = (work.groupby(['_month_sort', '_month'], as_index=False)[chart_cols]
                   .sum())
        # Top 5 months by maximum expense, ordered highest expense first.
        if 'expense_amt' in monthly.columns and len(monthly) > 5:
            monthly = (monthly.sort_values('expense_amt', ascending=False)
                       .head(5)
                       .sort_values('expense_amt', ascending=False))
        else:
            monthly = monthly.sort_values('_month_sort')
        x = monthly['_month']
    else:
        x = None  # no date column -> plot row-by-row numeric values

    for f in cols:
        if x is None:
            y = work[f['col']]
            xs = list(range(1, len(y) + 1))
        else:
            y = monthly[f['col']]
            xs = x

        # Single bar trace per metric. Bar colours are painted by the SVG
        # gradient injected client-side (assets/bar_gradient.js) —
        # see GRADIENTS['if-chart'] there.
        fig.add_trace(go.Bar(
            x=xs, y=y, name=f['label'], showlegend=True,
            marker=dict(color=f.get('fill', '#1d4ed8'),
                        cornerradius=f.get('radius', 10)),
            hovertemplate='%{x}<br>%{fullData.name}: $%{y:,.2f}<extra></extra>'))

    fig.update_layout(
        barmode='group',
        bargap=0.35,
        bargroupgap=0.12,
    )
    return fig


def _month_options(df):
    """Dropdown options of MMM-YY months present in the data (chronological)."""
    if df is None or df.empty or not _DATE_FIELDS or _DATE_FIELDS[0] not in df.columns:
        return [{'label': 'All Months', 'value': 'All'}]
    dt = pd.to_datetime(df[_DATE_FIELDS[0]], errors='coerce').dropna()
    months = sorted(set(dt.dt.strftime('%Y-%m|%b-%y')))
    opts = [{'label': 'All Months', 'value': 'All'}]
    opts += [{'label': lbl, 'value': key} for key, lbl in
             sorted(m.split('|') for m in months)]
    return opts


def _build_top_stores_chart(df, months=None, stores=None, top_n=10):
    """Grouped bar chart: Top-10 stores comparing Cash in Hand vs Expense Amt.

    `months` is a list of 'YYYY-MM' keys (or ['All']); `stores` a list of store
    names (or None for all). Stores are ranked by combined Cash + Expense and
    only the top `top_n` are plotted, grouped side-by-side per store.
    """
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color='#e2e8f0', height=420,
        margin=dict(l=55, r=20, t=20, b=90),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(gridcolor='rgba(148,163,184,0.12)', zeroline=False,
                   type='category', tickangle=-30),
        yaxis=dict(gridcolor='rgba(148,163,184,0.12)', zeroline=False,
                   tickprefix='$'),
    )

    if df is None or df.empty or 'store_name' not in df.columns \
            or not _NUMERIC_FIELDS:
        fig.add_annotation(text='No data available', showarrow=False,
                           font=dict(color='#94a3b8', size=16))
        return fig

    work = df.copy()
    if stores:
        work = work[work['store_name'].astype(str).isin(stores)]
    if work.empty:
        fig.add_annotation(text='No data for the selected filters', showarrow=False,
                           font=dict(color='#94a3b8', size=16))
        return fig

    cash_col, exp_col = _NUMERIC_FIELDS[0], _NUMERIC_FIELDS[1]
    work[cash_col] = pd.to_numeric(work[cash_col], errors='coerce').fillna(0)
    work[exp_col] = pd.to_numeric(work[exp_col], errors='coerce').fillna(0)

    if months and 'All' not in months and _DATE_FIELDS and _DATE_FIELDS[0] in work.columns:
        dt = pd.to_datetime(work[_DATE_FIELDS[0]], errors='coerce')
        work = work[dt.dt.strftime('%Y-%m').isin(months)]

    g = work.groupby('store_name', as_index=False)[[cash_col, exp_col]].sum()
    g['_total'] = g[cash_col] + g[exp_col]
    g = g.sort_values('_total', ascending=False).head(top_n)

    # Single bar trace per metric — NO stacked segments (no visible seams).
    # Fills match the GRADIENTS['if-ts-chart'] first/last stops in
    # assets/bar_gradient.js, which paints the real gradient client-side.
    fig.add_trace(go.Bar(x=g['store_name'], y=g[cash_col], name='Cash In Hand',
                         marker=dict(color='#e7f45c', cornerradius=10),
                         hovertemplate='%{x}<br>Cash In Hand: $%{y:,.2f}<extra></extra>'))
    fig.add_trace(go.Bar(x=g['store_name'], y=g[exp_col], name='Expense Amt',
                         marker=dict(color='#d70f19', cornerradius=10),
                         hovertemplate='%{x}<br>Expense Amt: $%{y:,.2f}<extra></extra>'))

    fig.update_layout(barmode='group', bargap=0.35, bargroupgap=0.12)
    return fig


# Read-only refresh: stats + table data, auto-refreshing every 60 seconds.
_OUTPUTS = ([Output('if-stats-rec', 'children')]
            + [Output(f'if-num-{n}', 'children') for n in _NUMERIC_FIELDS[:2]]
            + [Output('if-chart', 'figure')]
            + [Output('if-table', 'data')]
            + [Output('if-store-filter', 'options')])


@callback(
    *_OUTPUTS,
    Input('if-refresh', 'n_intervals'),
    Input('if-apply-btn', 'n_clicks'),
    State('if-store-filter', 'value'),
    State('if-date-range-filter', 'value'),
    State('if-custom-start', 'date'),
    State('if-custom-end', 'date'),
)
def refresh_records(n_intervals, n_clicks, stores, date_range, custom_start, custom_end):
    try:
        df = load_supabase_data()
    except Exception:
        ef = _build_chart(None)
        return ['0'] + ['$0.00'] * min(2, len(_NUMERIC_FIELDS)) \
            + [ef] + [[]] + [[{'label': 'All', 'value': 'All'}]]

    store_options = _build_store_options(df)
    filtered = _apply_filters(df, stores, date_range, custom_start, custom_end)

    def _fmt(col):
        if col in filtered.columns:
            total = float(pd.to_numeric(filtered[col], errors='coerce').fillna(0).sum())
            return f'${total:,.2f}'
        return '$0.00'

    stats = [str(len(filtered))] + [_fmt(n) for n in _NUMERIC_FIELDS[:2]]
    return (*stats, _build_chart(filtered), _table_records(filtered), store_options)


@callback(
    Output('if-custom-collapse', 'is_open'),
    Input('if-date-range-filter', 'value'),
)
def toggle_if_custom(date_range):
    return date_range == 'Custom Date'


# Top-10 Stores chart: search area (store search + month) drives the figure.
@callback(
    Output('if-ts-chart', 'figure'),
    Output('if-ts-store-filter', 'options'),
    Output('if-ts-month-filter', 'options'),
    Input('if-refresh', 'n_intervals'),
    Input('if-ts-store-filter', 'value'),
    Input('if-ts-month-filter', 'value'),
)
def refresh_top_stores(n_intervals, sel_stores, sel_months):
    try:
        df = load_supabase_data()
    except Exception:
        df = None
    store_opts = _build_store_options(df)
    month_opts = _month_options(df)
    stores = list(sel_stores) if sel_stores else None
    months = list(sel_months) if sel_months else None
    return _build_top_stores_chart(df, months=months, stores=stores), store_opts, month_opts


@callback(
    Output('if-download', 'data'),
    Input('if-download-btn', 'n_clicks'),
    State('if-store-filter', 'value'),
    State('if-date-range-filter', 'value'),
    State('if-custom-start', 'date'),
    State('if-custom-end', 'date'),
    prevent_initial_call=True,
)
def download_excel(n_clicks, stores, date_range, custom_start, custom_end):
    if not n_clicks:
        return None
    df = _apply_filters(load_supabase_data(), stores, date_range, custom_start, custom_end)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return dcc.send_data_frame(df.to_excel,
                               f'deposit_maintenance_data_{ts}.xlsx',
                               index=False, sheet_name='Deposit_Data')
