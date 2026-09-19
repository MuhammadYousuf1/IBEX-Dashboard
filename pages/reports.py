"""
Reports Download Page
=====================
Filter Market / Store / Date Range, pick a report name and download it.

Reports are the sheets of ``data/SALES UPDATE.xlsx``:
    - ActivationSheet
    - SaledetailSheet

The page reuses the shared data module (pages.sales_dashboard) for the
workbook path, the filter dropdown options and the common filtering logic so
its look and behaviour match the rest of the dashboard.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

import pandas as pd
from dash import dcc, html, Input, Output, State, callback, dash_table
from dash.dash_table import FormatTemplate
import dash_bootstrap_components as dbc
from dash import register_page

from pages import sales_dashboard as sd

register_page(__name__, path='/reports', title='Reports Download')

# ----------------------------------------------------------------------------
# Report catalogue -> sheet names inside SALES UPDATE.xlsx
# ----------------------------------------------------------------------------
REPORT_OPTIONS = [
    {'label': 'Activation Details', 'value': 'ActivationSheet'},
    {'label': 'Sales Detailed', 'value': 'SaledetailSheet'},
]
DEFAULT_REPORT = 'ActivationSheet'

# Money columns rendered as currency in the on-screen preview (per sheet).
_MONEY_COLS = {
    'ActivationSheet': ['MRC', 'SP Exp Comm', 'ER Exp Comm'],
    'SaledetailSheet': ['Unit Price', 'Unit Cost', 'Discounts', 'Ext Price',
                        'Ext Cost', 'GP', 'Tax', 'Total Sales'],
}

# ----------------------------------------------------------------------------
# Data helpers
# ----------------------------------------------------------------------------

def load_report(sheet_name):
    """Read one report sheet from SALES UPDATE.xlsx (empty frame on failure)."""
    try:
        return pd.read_excel(sd.DATA_PATH, sheet_name=sheet_name)
    except Exception:
        return pd.DataFrame()


def filter_report(df, markets, stores, date_range, custom_start=None, custom_end=None):
    """Apply Market / Store / Date Range filters using the shared helper."""
    return sd._filter_sheet(df, stores, None, date_range,
                            custom_start, custom_end, markets)


def _report_label(sheet_name):
    for opt in REPORT_OPTIONS:
        if opt['value'] == sheet_name:
            return opt['label']
    return sheet_name


def _scope_label(values, noun):
    """Human readable summary of a multi-select filter."""
    if not values or 'All' in values:
        return f'All {noun}'
    if len(values) == 1:
        return str(values[0])
    return f'{len(values)} {noun}'


def _period_label(date_range, custom_start, custom_end):
    if date_range == 'Custom Date' and custom_start and custom_end:
        return f'{custom_start} to {custom_end}'
    return date_range or 'All Time'


def table_columns(df, sheet_name):
    """Build DataTable columns, formatting known money columns as currency."""
    money = set(_MONEY_COLS.get(sheet_name, []))
    cols = []
    for col in df.columns:
        if col in money:
            cols.append({'name': col, 'id': col, 'type': 'numeric',
                         'format': FormatTemplate.money(2)})
        else:
            cols.append({'name': col, 'id': col})
    return cols


def table_records(df):
    """Serialize a frame for DataTable (dates -> text, NaN -> blank)."""
    if df is None or df.empty:
        return []
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    return out.where(pd.notnull(out), '').to_dict('records')


# ----------------------------------------------------------------------------
# UI: filter card (Market / Store / Date Range / Report Name)
# ----------------------------------------------------------------------------

def create_filter_section():
    """Build the inline filter card with the four report fields + Apply."""
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label([html.I(className='fas fa-map-marker-alt me-2',
                                       style={'color': '#8b5cf6'}), 'Market'],
                               className='filter-label mb-2'),
                    dcc.Dropdown(id='rpt-market-filter', options=sd.MARKETID_OPTIONS,
                                 value=['All'], multi=True, placeholder='Select markets...',
                                 className='dark-dropdown')
                ], xs=12, md=3, className='mb-3 mb-md-0'),
                dbc.Col([
                    html.Label([html.I(className='fas fa-store me-2',
                                       style={'color': '#6366f1'}), 'Store Name'],
                               className='filter-label mb-2'),
                    dcc.Dropdown(id='rpt-store-filter', options=sd.STORE_OPTIONS,
                                 value=['All'], multi=True, placeholder='Select stores...',
                                 className='dark-dropdown')
                ], xs=12, md=3, className='mb-3 mb-md-0'),
                dbc.Col([
                    html.Label([html.I(className='fas fa-calendar-alt me-2',
                                       style={'color': '#f59e0b'}), 'Date Range'],
                               className='filter-label mb-2'),
                    dcc.Dropdown(id='rpt-date-range-filter', options=sd.DATE_RANGE_OPTIONS,
                                 value='Current Month', placeholder='Select date range...',
                                 className='dark-dropdown')
                ], xs=12, md=2, className='mb-3 mb-md-0'),
                dbc.Col([
                    html.Label([html.I(className='fas fa-file-lines me-2',
                                       style={'color': '#06b6d4'}), 'Report Name'],
                               className='filter-label mb-2'),
                    dcc.Dropdown(id='rpt-report-filter', options=REPORT_OPTIONS,
                                 value=DEFAULT_REPORT, clearable=False,
                                 placeholder='Select report...', className='dark-dropdown')
                ], xs=12, md=2, className='mb-3 mb-md-0'),
                dbc.Col([
                    html.Label([html.I(className='fas fa-sliders-h me-2',
                                       style={'color': '#10b981'}), 'Actions'],
                               className='filter-label mb-2'),
                    dbc.Button([html.I(className='fas fa-sync-alt me-2'), 'Apply Filters'],
                               id='rpt-apply-btn', color='primary', className='w-100',
                               style={'borderRadius': '12px', 'fontWeight': '600', 'border': 'none',
                                      'background': 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)'})
                ], xs=12, md=2, className='mb-3 mb-md-0'),
            ], align='end', className='g-3'),
            dbc.Collapse([
                dbc.Row([
                    dbc.Col([html.Label('Start Date', className='filter-label mb-2'),
                             dcc.DatePickerSingle(id='rpt-custom-start',
                                                  min_date_allowed=sd.MARKET_DATE_MIN,
                                                  max_date_allowed=sd.MARKET_DATE_MAX,
                                                  date=sd.MARKET_DATE_MIN,
                                                  display_format='YYYY-MM-DD',
                                                  className='dark-datepicker')], xs=12, md=6),
                    dbc.Col([html.Label('End Date', className='filter-label mb-2'),
                             dcc.DatePickerSingle(id='rpt-custom-end',
                                                  min_date_allowed=sd.MARKET_DATE_MIN,
                                                  max_date_allowed=sd.MARKET_DATE_MAX,
                                                  date=sd.MARKET_DATE_MAX,
                                                  display_format='YYYY-MM-DD',
                                                  className='dark-datepicker')], xs=12, md=6),
                ], className='mt-3')
            ], id='rpt-custom-collapse', is_open=False),
        ])
    ], className='filter-card mb-4', style={'background': '#1e293b', 'border': '1px solid #334155',
                                            'borderRadius': '20px'})


# ----------------------------------------------------------------------------
# Page layout
# ----------------------------------------------------------------------------

layout = dbc.Container([
    dcc.Download(id='rpt-download'),
    dbc.Row([dbc.Col([html.Div([
        html.H2([html.I(className='fas fa-file-arrow-down me-3', style={'color': '#8b5cf6'}),
                 'Reports Download Center'], className='fw-bold mb-2', style={'color': '#f8fafc'}),
        html.P('Select Market, Store and Date Range, choose a report, then download it as Excel.',
               style={'color': '#94a3b8'})
    ], className='mb-4')], width=12)]),
    create_filter_section(),
    dbc.Row([dbc.Col([dbc.Card([
        dbc.CardHeader(dbc.Row([
            dbc.Col([html.H5([html.I(className='fas fa-table me-2', style={'color': '#8b5cf6'}),
                              'Report Preview'], className='mb-0', style={'color': '#f8fafc'})],
                    xs=12, md='auto'),
            dbc.Col([html.Span(id='rpt-summary', children='', className='table-date-badge',
                               style={'background': 'rgba(139,92,246,0.15)',
                                      'border': '1px solid rgba(139,92,246,0.35)',
                                      'color': '#c4b5fd'})],
                    xs=12, md=True, className='text-md-start'),
            dbc.Col([dbc.Button([html.I(className='fas fa-file-excel me-2'), 'Download Excel'],
                                id='rpt-download-btn', color='success', outline=True,
                                className='float-md-end', style={'borderRadius': '10px'})],
                    xs=12, md=6, className='mt-2 mt-md-0'),
        ], align='center'), style={'background': 'transparent', 'borderBottom': '1px solid #334155'}),
        dbc.CardBody([dcc.Loading([dash_table.DataTable(
            id='rpt-table',
            columns=[],
            data=[],
            page_size=20, page_action='native', sort_action='native', filter_action='native',
            style_table={'overflowX': 'auto', 'borderRadius': '12px'},
            style_cell={'textAlign': 'center', 'padding': '12px 15px', 'backgroundColor': '#0f172a',
                        'color': '#e2e8f0', 'border': '1px solid #1e293b', 'fontSize': '14px',
                        'whiteSpace': 'normal', 'height': 'auto'},
            style_header={'backgroundColor': '#1e293b', 'color': '#f8fafc', 'fontWeight': '700',
                          'border': '1px solid #334155', 'textTransform': 'uppercase', 'fontSize': '14px'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#162032'},
                {'if': {'state': 'active'}, 'backgroundColor': '#4968df', 'color': '#ffffff'}],
        )], type='circle', color='#8b5cf6')], className='p-3'),
    ], className='mb-4', style={'background': '#1e293b', 'border': '1px solid #334155',
                                'borderRadius': '20px'})], width=12)]),
], fluid=True, className='px-4 pb-5 anim-cards-page')


# ----------------------------------------------------------------------------
# Callbacks
# ----------------------------------------------------------------------------

@callback(Output('rpt-custom-collapse', 'is_open'),
          Input('rpt-date-range-filter', 'value'))
def toggle_rpt_custom(date_range):
    """Reveal the custom start/end pickers only for the 'Custom Date' preset."""
    return date_range == 'Custom Date'


@callback(
    Output('rpt-table', 'columns'),
    Output('rpt-table', 'data'),
    Output('rpt-summary', 'children'),
    Input('rpt-apply-btn', 'n_clicks'),
    Input('rpt-report-filter', 'value'),
    Input('rpt-market-filter', 'value'),
    Input('rpt-store-filter', 'value'),
    Input('rpt-date-range-filter', 'value'),
    State('rpt-custom-start', 'date'),
    State('rpt-custom-end', 'date'),
)
def update_report(n_clicks, sheet_name, markets, stores, date_range,
                  custom_start, custom_end):
    """Refresh the preview table and the summary badge for the active filters."""
    sheet_name = sheet_name or DEFAULT_REPORT
    filtered = filter_report(load_report(sheet_name), markets, stores, date_range,
                             custom_start, custom_end)
    rows = 0 if filtered is None or filtered.empty else len(filtered)

    summary = (f'{_report_label(sheet_name)} · {_scope_label(markets, "Markets")} · '
               f'{_scope_label(stores, "Stores")} · '
               f'{_period_label(date_range, custom_start, custom_end)} · {rows:,} rows')

    if rows == 0:
        return [], [], summary

    return table_columns(filtered, sheet_name), table_records(filtered), summary


@callback(
    Output('rpt-download', 'data'),
    Input('rpt-download-btn', 'n_clicks'),
    State('rpt-report-filter', 'value'),
    State('rpt-market-filter', 'value'),
    State('rpt-store-filter', 'value'),
    State('rpt-date-range-filter', 'value'),
    State('rpt-custom-start', 'date'),
    State('rpt-custom-end', 'date'),
    prevent_initial_call=True,
)
def download_report(n_clicks, sheet_name, markets, stores, date_range,
                    custom_start, custom_end):
    """Download the filtered report as an .xlsx sheet named after the report."""
    if not n_clicks:
        return None
    sheet_name = sheet_name or DEFAULT_REPORT
    filtered = filter_report(load_report(sheet_name), markets, stores, date_range,
                             custom_start, custom_end)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return dcc.send_data_frame(filtered.to_excel,
                               f'{sheet_name}_{ts}.xlsx',
                               index=False, sheet_name=sheet_name[:31])
