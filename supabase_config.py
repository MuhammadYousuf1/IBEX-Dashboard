"""Committed Supabase credentials for the IBEX Dashboard deployment.

!! SECURITY WARNING !!
This file is PUBLIC in the GitHub repository. It contains the project's
service-role key, which bypasses row level security on the whole Supabase
project (read and write every row, including the app_users password hashes).

This exists only because the Vercel project has no environment variables
configured. Once SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_KEY are
set in the Vercel dashboard, DELETE this file and rotate the service key in
Supabase -> Settings -> API (a key that has been public must not be reused).

Values are applied with os.environ.setdefault, so any real environment
variable - a local .env or a value configured in the Vercel dashboard -
always wins over the values below.
"""

import os

VALUES = {
    'SUPABASE_URL': 'https://iobhyhbbooxinrhomlvv.supabase.co',
    'SUPABASE_KEY': 'sb_publishable_nMEhwybJZRNL7Rb50qes9g_6v1jMqA6',
    'SUPABASE_SERVICE_ROLE_KEY': (
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
        'eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlvYmh5aGJib294aW5yaG9tbHZ2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzI4MDkwNCwiZXhwIjoyMDk4ODU2OTA0fQ.'
        'Vlf8aVnz-GSErldUt84UsdcpBdb1Spah098kVO6uHNI'
    ),
}


def apply():
    """Copy the committed values into os.environ without overriding real ones."""
    for name, value in VALUES.items():
        os.environ.setdefault(name, value)


apply()