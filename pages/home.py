"""
Home Page - Main Landing Page with Navigation Cards
"""

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import register_page

register_page(__name__, path='/', title='Home - Sales Analytics')

# Page card configuration
PAGES = [
    {
        'title': 'Sales Dashboard',
        'description': 'Comprehensive sales performance metrics with KPIs, charts, and detailed analytics.',
        'icon': 'fa-chart-pie',
        'color': '#6366f1',
        'bg': 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
        'href': '/sales-dashboard',
        'stats': 'BTS • BPH • APH • APB • New Activations'
    },
    {
        'title': 'Reports Download',
        'description': 'Filter by market, store and date range, then download Activation or Sale Detail reports as Excel.',
        'icon': 'fa-file-arrow-down',
        'color': '#8b5cf6',
        'bg': 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)',
        'href': '/reports',
        'stats': 'ActivationSheet • SaledetailSheet • Excel Export'
    },
    {
        'title': 'Input Form',
        'description': 'Submit store deposit and expense entries with photo uploads, saved directly to Supabase.',
        'icon': 'fa-file-invoice-dollar',
        'color': '#3b82f6',
        'bg': 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
        'href': '/deposit-expense',
        'stats': 'Store Deposits • Expenses • Photo Uploads'
    }
]

def create_page_card(page):
    return dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(className=f'fas {page["icon"]} fa-3x mb-3')
                ], style={
                    'color': page['color'],
                    'textAlign': 'center'
                }),
                html.H4(page['title'], className='card-title text-center mb-3',
                       style={'fontWeight': '700', 'color': '#f8fafc'}),
                html.P(page['description'], className='card-text text-center mb-3',
                      style={'color': '#94a3b8', 'fontSize': '0.95rem'}),
                html.Div([
                    html.Small(page['stats'], style={'color': "#ffffff"})
                ], className='text-center mb-3'),
                dbc.Button([
                    html.I(className='fas fa-arrow-right me-2'),
                    'Open Dashboard'
                ], href=page['href'], color='light', outline=True,
                   className='w-100 mt-auto', style={
                       'borderRadius': '12px',
                       'fontWeight': '600',
                       'borderColor': page['color'],
                       'color': page['color']
                   })
            ], className='d-flex flex-column h-100')
        ], className='page-card h-100', style={
            'background': '#1e293b',
            'border': f'1px solid {page["color"]}33',
            'borderRadius': '20px',
            'transition': 'all 0.3s ease',
            'cursor': 'pointer'
        })
    ], xs=12, sm=6, lg=4, className='mb-4')

layout = dbc.Container([
    # Hero Section
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([
                    html.Span('Sales', style={'color': '#6366f1'}),
                    ' Analytics ',
                    html.Span('Hub', style={'color': '#8b5cf6'})
                ], className='display-4 fw-bold mb-3 text-center'),
                html.P('Your centralized command center for sales performance, data entry, and report downloads.',
                      className='lead text-center mb-2',
                      style={'color': '#94a3b8', 'maxWidth': '700px', 'margin': '0 auto'}),
                html.Div([
                    html.Span(className='badge bg-primary me-2', children='Real-time'),
                    html.Span(className='badge bg-success me-2', children='Interactive'),
                    html.Span(className='badge bg-info', children='Responsive'),
                ], className='text-center mb-5')
            ], className='hero-section py-5')
        ], width=12)
    ]),

    # Page Cards Grid
    dbc.Row([
        create_page_card(page) for page in PAGES
    ], className='g-4 mb-5'),

    # Quick Stats Section
    dbc.Row([
        dbc.Col([
            html.H3([
                html.I(className='fas fa-bolt me-2', style={'color': '#f59e0b'}),
                'Quick Overview'
            ], className='mb-4 text-center', style={'color': '#f8fafc'}),
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H2('4', className='fw-bold', style={'color': '#6366f1'}),
                                html.P('Active Dashboards', style={'color': '#94a3b8'})
                            ], className='text-center')
                        ], xs=6, md=3),
                        dbc.Col([
                            html.Div([
                                html.H2('117', className='fw-bold', style={'color': '#10b981'}),
                                html.P('Store Locations', style={'color': '#94a3b8'})
                            ], className='text-center')
                        ], xs=6, md=3),
                        dbc.Col([
                            html.Div([
                                html.H2('143', className='fw-bold', style={'color': '#f59e0b'}),
                                html.P('Active Employees', style={'color': '#94a3b8'})
                            ], className='text-center')
                        ], xs=6, md=3),
                        dbc.Col([
                            html.Div([
                                html.H2('12', className='fw-bold', style={'color': '#06b6d4'}),
                                html.P('State Markets', style={'color': '#94a3b8'})
                            ], className='text-center')
                        ], xs=6, md=3),
                    ])
                ])
            ], style={
                'background': '#1e293b',
                'border': '1px solid #334155',
                'borderRadius': '20px'
            })
        ], width=12)
    ], className='mb-5')

], fluid=True, className='px-4 anim-cards-page')
