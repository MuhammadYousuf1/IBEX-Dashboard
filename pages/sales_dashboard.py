"""
Sales Dashboard - Shared Data Module
====================================
Loads SALES UPDATE.xlsx and provides shared filtering / KPI / chart helpers
used by all dashboard pages.
"""

import dash
import sys as _sys
import json
import plotly.graph_objects as go
import plotly.express as px
from dash import dcc, html, Input, Output, State, callback, register_page
import os
from datetime import datetime, timedelta

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc

# ----------------------------------------------------------------------------
# Idempotency guard: Dash's pages plugin re-executes every page file even if
# it was already imported normally (sibling pages import this module). If a
# loaded copy already exists, re-export its contents instead of running the
# body again, which would register duplicate callbacks.
# ----------------------------------------------------------------------------
_SD_MODULE_KEY = 'pages.sales_dashboard'
_sd_cached = _sys.modules.get(_SD_MODULE_KEY)
if _sd_cached is not None and getattr(_sd_cached, '_SD_LOADED', False):
    for _sd_name in dir(_sd_cached):
        if not _sd_name.startswith('__'):
            globals()[_sd_name] = getattr(_sd_cached, _sd_name)
else:

    # Locate the SALES UPDATE.xlsx file. This module lives in the pages/
    # subfolder, so walk up until we find a 'data' directory that contains the
    # expected file. This keeps the path correct regardless of where the
    # project is installed.
    _FILE_NAME = 'SALES UPDATE.xlsx'

    def _find_data_path():
        _here = os.path.dirname(os.path.abspath(__file__))
        for _depth in range(4):
            _candidate = os.path.join(_here, 'data', _FILE_NAME)
            if os.path.exists(_candidate):
                return _candidate
            _here = os.path.dirname(_here)
        # Fall back to the root-level expected location.
        return os.path.join(_here, 'data', _FILE_NAME)

    DATA_PATH = _find_data_path()

    METRIC_COLUMNS = ['BTS', 'newact', 'totact', 'totaccessory', 'totpaymentqty',
                      'upgsor', 'upginv', 'reactact', 'newreactact', 'totaccessoryqty']

    # ------------------------------------------------------------------------
    # ActivationSheet column variables
    # Usage: df[ACT_COL_MOBILE] or df[ACT_COLUMNS]
    # ------------------------------------------------------------------------
    ACT_COL_TRANS_DATE_TIME = 'Trans Date Time'
    ACT_COL_SALESPERSON = 'Salesperson'
    ACT_COL_CONTRACT_TYPE = 'Contract Type'
    ACT_COL_TRANS_TYPE = 'Trans Type'
    ACT_COL_CUSTOMER = 'Customer'
    ACT_COL_MOBILE = 'Mobile'
    ACT_COL_SP_PO_NAME = 'SP/PO Name'
    ACT_COL_MRC = 'MRC'
    ACT_COL_DEALER_CODE = 'Dealer Code'
    ACT_COL_PRODUCT_DESC = 'Product Desc'
    ACT_COL_SERIAL = 'Serial#'
    ACT_COL_SKU = 'SKU'
    ACT_COL_SUBSCRIBER_ID = 'Subscriber ID'
    ACT_COL_UPC = 'UPC'
    ACT_COL_SP_EXP_COMM = 'SP Exp Comm'
    ACT_COL_ER_EXP_COMM = 'ER Exp Comm'
    ACT_COL_EXTERNAL_ORDER_ID = 'External Order ID'
    ACT_COL_CATEGORY = 'Category'

    # All ActivationSheet columns as a list
    ACT_COLUMNS = [
        ACT_COL_TRANS_DATE_TIME, ACT_COL_SALESPERSON, ACT_COL_CONTRACT_TYPE,
        ACT_COL_TRANS_TYPE, ACT_COL_CUSTOMER, ACT_COL_MOBILE, ACT_COL_SP_PO_NAME,
        ACT_COL_MRC, ACT_COL_DEALER_CODE, ACT_COL_PRODUCT_DESC, ACT_COL_SERIAL,
        ACT_COL_SKU, ACT_COL_SUBSCRIBER_ID, ACT_COL_UPC, ACT_COL_SP_EXP_COMM,
        ACT_COL_ER_EXP_COMM, ACT_COL_EXTERNAL_ORDER_ID, ACT_COL_CATEGORY,
    ]

    # ------------------------------------------------------------------------
    # SaledetailSheet column variables
    # Usage: df[SDT_COL_GP] or df[SDT_COLUMNS]
    # ------------------------------------------------------------------------
    SDT_COL_TRANS_DATE_TIME = 'Trans Date Time'
    SDT_COL_SALESPERSON = 'Salesperson'
    SDT_COL_CUSTOMER = 'Customer'
    SDT_COL_EMAIL = 'Email'
    SDT_COL_TRANS_TYPE = 'Trans Type'
    SDT_COL_PRODUCT_DESC = 'Product Desc'
    SDT_COL_QTY = 'Qty'
    SDT_COL_UNIT_PRICE = 'Unit Price'
    SDT_COL_UNIT_COST = 'Unit Cost'
    SDT_COL_DISCOUNTS = 'Discounts'
    SDT_COL_EXT_PRICE = 'Ext Price'
    SDT_COL_EXT_COST = 'Ext Cost'
    SDT_COL_GP = 'GP'
    SDT_COL_TAX = 'Tax'
    SDT_COL_TENDER_TYPE = 'Tender Type'
    SDT_COL_TOTAL_SALES = 'Total Sales'
    SDT_COL_VOIDED = 'Voided'
    SDT_COL_ACTIVATED_MOBILE_NUMBER = 'Activated Mobile Number'
    SDT_COL_RETURN_REASON = 'Return Reason'
    SDT_COL_UPC = 'UPC'
    SDT_COL_DEALER_CODE = 'DealerCode'
    SDT_COL_CATEGORY = 'Category'

    # All SaledetailSheet columns as a list
    SDT_COLUMNS = [
        SDT_COL_TRANS_DATE_TIME, SDT_COL_SALESPERSON, SDT_COL_CUSTOMER,
        SDT_COL_EMAIL, SDT_COL_TRANS_TYPE, SDT_COL_PRODUCT_DESC, SDT_COL_QTY,
        SDT_COL_UNIT_PRICE, SDT_COL_UNIT_COST, SDT_COL_DISCOUNTS,
        SDT_COL_EXT_PRICE, SDT_COL_EXT_COST, SDT_COL_GP, SDT_COL_TAX,
        SDT_COL_TENDER_TYPE, SDT_COL_TOTAL_SALES, SDT_COL_VOIDED,
        SDT_COL_ACTIVATED_MOBILE_NUMBER, SDT_COL_RETURN_REASON, SDT_COL_UPC,
        SDT_COL_DEALER_CODE, SDT_COL_CATEGORY,
    ]

    # ------------------------------------------------------------------------
    # Storeperf sheet column variables (store target vs achievement snapshot)
    # Usage: df[STOREPERF_COL_TARGET_ACH] or df[STOREPERF_COLUMNS]
    # NOTE: the heading row has moved around as columns were added (it sat on
    # the second row, then moved to the first once the Month column was added),
    # so _load_storeperf_data below *detects* it instead of hard-coding it.
    # ------------------------------------------------------------------------
    STOREPERF_COL_MONTH = 'Month'
    STOREPERF_COL_DEALER_CODE = 'DealerCode'
    STOREPERF_COL_STORE = 'Store Name'
    STOREPERF_COL_EMP = 'Emp Name'
    STOREPERF_COL_ACT_TARGET = 'ACT TARGET'
    STOREPERF_COL_ACTIVATION = 'ACTIVATION'
    STOREPERF_COL_REM_TARGET = 'REM TARGET'
    STOREPERF_COL_TARGET_ACH = 'TARGET ACH %'
    STOREPERF_COL_ACC_TARGET = 'ACC TARGET'
    STOREPERF_COL_ACCESSORY = 'ACCESSORY'
    STOREPERF_COL_REM_ACC = 'REM ACC'
    STOREPERF_COL_ACC_ACH = 'ACC ACH %'
    # Derived in _load_storeperf_data: the mean of TARGET ACH % and ACC ACH %.
    # This is the metric the Top Performing Stores chart is ranked by.
    STOREPERF_COL_AVG_ACH = 'ACH AVG %'

    # All Storeperf columns as a list
    STOREPERF_COLUMNS = [
        STOREPERF_COL_MONTH, STOREPERF_COL_DEALER_CODE, STOREPERF_COL_STORE,
        STOREPERF_COL_EMP, STOREPERF_COL_ACT_TARGET, STOREPERF_COL_ACTIVATION,
        STOREPERF_COL_REM_TARGET, STOREPERF_COL_TARGET_ACH,
        STOREPERF_COL_ACC_TARGET, STOREPERF_COL_ACCESSORY,
        STOREPERF_COL_REM_ACC, STOREPERF_COL_ACC_ACH, STOREPERF_COL_AVG_ACH,
    ]

    DATE_RANGE_OPTIONS = [
        {'label': 'All Time', 'value': 'All Time'},
        {'label': 'Current Month', 'value': 'Current Month'},
        {'label': 'Last Month', 'value': 'Last Month'},
        {'label': 'Last 3 Months', 'value': 'Last 3 Months'},
        {'label': 'Custom Date', 'value': 'Custom Date'},
    ]

    def _load_df():
        try:
            df = pd.read_excel(DATA_PATH)
        except Exception:
            return pd.DataFrame()
        if df.empty:
            return df
        # The updated SALES UPDATE.xlsx no longer exposes a 'DATE' column;
        # dates live in 'Trans Date Time'. Derive DATE from whichever exists.
        if 'DATE' in df.columns:
            df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
        elif ACT_COL_TRANS_DATE_TIME in df.columns:
            df['DATE'] = pd.to_datetime(df[ACT_COL_TRANS_DATE_TIME], errors='coerce')
        else:
            return df
        df['YearMonth'] = df['DATE'].dt.to_period('M').astype(str)
        return df

    DF = _load_df()

    # ------------------------------------------------------------------------
    # Device Protection data from ActivationSheet
    # ------------------------------------------------------------------------
    def _load_device_protection_data():
        """Load ActivationSheet, filter SP/PO Name = 'Device Protection',
        and return (filtered_df, count, by_district DataFrames)."""
        try:
            df = pd.read_excel(DATA_PATH, sheet_name='ActivationSheet')
        except Exception:
            return pd.DataFrame(), 0, pd.DataFrame(columns=[ACT_COL_DEALER_CODE, 'count'])
        if df.empty:
            return df, 0, pd.DataFrame(columns=[ACT_COL_DEALER_CODE, 'count'])
        # Filter for Device Protection only
        dp_df = df[df[ACT_COL_SP_PO_NAME] == 'Device Protection'].copy()
        count = len(dp_df)
        # Parse YearMonth from Trans Date Time for MoM computation
        if not dp_df.empty and ACT_COL_TRANS_DATE_TIME in dp_df.columns:
            dp_df[ACT_COL_TRANS_DATE_TIME] = pd.to_datetime(dp_df[ACT_COL_TRANS_DATE_TIME], errors='coerce')
            dp_df['YearMonth'] = dp_df[ACT_COL_TRANS_DATE_TIME].dt.to_period('M').astype(str)
        # Group by Dealer Code for district-level pie chart
        if not dp_df.empty:
            by_district = (dp_df.groupby(ACT_COL_DEALER_CODE)
                           .size()
                           .reset_index(name='count')
                           .sort_values('count', ascending=False))
        else:
            by_district = pd.DataFrame(columns=[ACT_COL_DEALER_CODE, 'count'])
        return dp_df, count, by_district

    DP_DF, DP_COUNT, DP_BY_DISTRICT = _load_device_protection_data()

    def _mom_pct_dp():
        """Return (% change vs previous month, label) for Device Protection count."""
        if DP_DF is None or DP_DF.empty:
            return None, 'no data'
        g = DP_DF.groupby('YearMonth').size()
        if len(g) < 2:
            return None, 'no prev month'
        months = sorted(g.index)
        curr = g[months[-1]]
        prev = g[months[-2]]
        if prev == 0:
            return None, 'no prev value'
        pct = ((curr - prev) / abs(prev)) * 100
        return pct, f'{months[-2]} vs {months[-1]}'

    def mom_badge_dp():
        """Build a small arrow + % badge for Device Protection month-over-month comparison."""
        pct, note = _mom_pct_dp()
        if pct is None:
            return html.Small('\u2014', className='mom-note', style={'color': '#64748b'})
        up = pct >= 0
        color = '#10b981' if up else '#ef4444'
        arrow = 'fa-arrow-up' if up else 'fa-arrow-down'
        return html.Div([
            html.Div([
                html.I(className=f'fas {arrow} mom-arrow me-1',
                       style={'color': color}),
                html.Span(f'{abs(pct):.1f}%', style={
                          'color': color, 'fontWeight': '700'})
            ]),
            html.Small('vs prev mo', className='mom-note',
                       style={'color': "#fffb04"})
        ], className='mom-badge')

    # ------------------------------------------------------------------------
    # Activations data (all SP/PO Name except Device Protection)
    # ------------------------------------------------------------------------
    def _load_activations_data():
        """Load ActivationSheet, filter out 'Device Protection',
        and return (filtered_df, count, by_district DataFrames)."""
        try:
            df = pd.read_excel(DATA_PATH, sheet_name='ActivationSheet')
        except Exception:
            return pd.DataFrame(), 0, pd.DataFrame(columns=[ACT_COL_DEALER_CODE, 'count'])
        if df.empty:
            return df, 0, pd.DataFrame(columns=[ACT_COL_DEALER_CODE, 'count'])
        # Filter out Device Protection
        act_df = df[df[ACT_COL_SP_PO_NAME] != 'Device Protection'].copy()
        count = len(act_df)
        # Parse YearMonth from Trans Date Time for MoM computation
        if not act_df.empty and ACT_COL_TRANS_DATE_TIME in act_df.columns:
            act_df[ACT_COL_TRANS_DATE_TIME] = pd.to_datetime(act_df[ACT_COL_TRANS_DATE_TIME], errors='coerce')
            act_df['YearMonth'] = act_df[ACT_COL_TRANS_DATE_TIME].dt.to_period('M').astype(str)
        # Group by Dealer Code for district-level breakdown
        if not act_df.empty:
            by_district = (act_df.groupby(ACT_COL_DEALER_CODE)
                           .size()
                           .reset_index(name='count')
                           .sort_values('count', ascending=False))
        else:
            by_district = pd.DataFrame(columns=[ACT_COL_DEALER_CODE, 'count'])
        return act_df, count, by_district

    ACT_DF, ACT_COUNT, ACT_BY_DISTRICT = _load_activations_data()

    def _mom_pct_act():
        """Return (% change vs previous month, label) for Activations count."""
        if ACT_DF is None or ACT_DF.empty:
            return None, 'no data'
        g = ACT_DF.groupby('YearMonth').size()
        if len(g) < 2:
            return None, 'no prev month'
        months = sorted(g.index)
        curr = g[months[-1]]
        prev = g[months[-2]]
        if prev == 0:
            return None, 'no prev value'
        pct = ((curr - prev) / abs(prev)) * 100
        return pct, f'{months[-2]} vs {months[-1]}'

    def mom_badge_act():
        """Build a small arrow + % badge for Activations month-over-month comparison."""
        pct, note = _mom_pct_act()
        if pct is None:
            return html.Small('\u2014', className='mom-note', style={'color': '#64748b'})
        up = pct >= 0
        color = '#10b981' if up else '#ef4444'
        arrow = 'fa-arrow-up' if up else 'fa-arrow-down'
        return html.Div([
            html.Div([
                html.I(className=f'fas {arrow} mom-arrow me-1',
                       style={'color': color}),
                html.Span(f'{abs(pct):.1f}%', style={
                          'color': color, 'fontWeight': '700'})
            ]),
            html.Small('vs prev mo', className='mom-note',
                       style={'color': '#64748b'})
        ], className='mom-badge')

    # ------------------------------------------------------------------------
    # Total SP/PO Name count (all rows in ActivationSheet)
    # ------------------------------------------------------------------------
    def _load_total_sppo_data():
        """Load ActivationSheet and return (filtered_df, count) for all SP/PO Name rows."""
        try:
            df = pd.read_excel(DATA_PATH, sheet_name='ActivationSheet')
        except Exception:
            return pd.DataFrame(), 0
        if df.empty:
            return df, 0
        count = len(df)
        # Parse YearMonth from Trans Date Time for MoM computation
        if not df.empty and ACT_COL_TRANS_DATE_TIME in df.columns:
            df[ACT_COL_TRANS_DATE_TIME] = pd.to_datetime(df[ACT_COL_TRANS_DATE_TIME], errors='coerce')
            df['YearMonth'] = df[ACT_COL_TRANS_DATE_TIME].dt.to_period('M').astype(str)
        return df, count

    TOTAL_SP_DF, TOTAL_SP_COUNT = _load_total_sppo_data()

    def _mom_pct_total_sp():
        """Return (% change vs previous month, label) for total SP/PO Name count."""
        if TOTAL_SP_DF is None or TOTAL_SP_DF.empty:
            return None, 'no data'
        g = TOTAL_SP_DF.groupby('YearMonth').size()
        if len(g) < 2:
            return None, 'no prev month'
        months = sorted(g.index)
        curr = g[months[-1]]
        prev = g[months[-2]]
        if prev == 0:
            return None, 'no prev value'
        pct = ((curr - prev) / abs(prev)) * 100
        return pct, f'{months[-2]} vs {months[-1]}'

    def mom_badge_total_sp():
        """Build a small arrow + % badge for total SP/PO Name month-over-month comparison."""
        pct, note = _mom_pct_total_sp()
        if pct is None:
            return html.Small('\u2014', className='mom-note', style={'color': '#64748b'})
        up = pct >= 0
        color = '#10b981' if up else '#ef4444'
        arrow = 'fa-arrow-up' if up else 'fa-arrow-down'
        return html.Div([
            html.Div([
                html.I(className=f'fas {arrow} mom-arrow me-1',
                       style={'color': color}),
                html.Span(f'{abs(pct):.1f}%', style={
                          'color': color, 'fontWeight': '700'})
            ]),
            html.Small('vs prev mo', className='mom-note',
                       style={'color': '#64748b'})
        ], className='mom-badge')

    # ------------------------------------------------------------------------
    # Accessories data from SaledetailSheet (Category = 'Accessories' or 'Other Accessories')
    # Sum of 'Total Sales' column
    # ------------------------------------------------------------------------
    def _load_accessories_data():
        """Load SaledetailSheet, filter Category in ('Accessories', 'Other Accessories'),
        and return (filtered_df, total_sales_sum)."""
        try:
            df = pd.read_excel(DATA_PATH, sheet_name='SaledetailSheet')
        except Exception:
            return pd.DataFrame(), 0.0
        if df.empty:
            return df, 0.0
        # Filter for Accessories categories
        mask = df[SDT_COL_CATEGORY].isin(['Accessories', 'Other Accessories'])
        acc_df = df[mask].copy()
        # Sum Total Sales
        total_sales = acc_df[SDT_COL_TOTAL_SALES].sum()
        # Parse YearMonth from Trans Date Time for MoM computation
        if not acc_df.empty and SDT_COL_TRANS_DATE_TIME in acc_df.columns:
            acc_df[SDT_COL_TRANS_DATE_TIME] = pd.to_datetime(acc_df[SDT_COL_TRANS_DATE_TIME], errors='coerce')
            acc_df['YearMonth'] = acc_df[SDT_COL_TRANS_DATE_TIME].dt.to_period('M').astype(str)
        return acc_df, total_sales

    ACC_DF, ACC_TOTAL_SALES = _load_accessories_data()

    # ------------------------------------------------------------------------
    # Bill Pay data from SaledetailSheet
    # Count of 'Product Desc' rows containing 'RTR' where 'Voided' != 'Yes'
    # ------------------------------------------------------------------------
    def _load_bill_pay_data():
        """Load SaledetailSheet, keep rows whose 'Product Desc' contains 'RTR'
        and whose 'Voided' is not 'Yes', and return (filtered_df, count)."""
        try:
            df = pd.read_excel(DATA_PATH, sheet_name='SaledetailSheet')
        except Exception:
            return pd.DataFrame(), 0
        if df.empty:
            return df, 0
        mask = (df[SDT_COL_PRODUCT_DESC].astype(str).str.contains(
            'RTR', case=False, na=False)
            & (df[SDT_COL_VOIDED] != 'Yes'))
        bp_df = df[mask].copy()
        count = len(bp_df)
        # Parse YearMonth from Trans Date Time for MoM computation
        if not bp_df.empty and SDT_COL_TRANS_DATE_TIME in bp_df.columns:
            bp_df[SDT_COL_TRANS_DATE_TIME] = pd.to_datetime(
                bp_df[SDT_COL_TRANS_DATE_TIME], errors='coerce')
            bp_df['YearMonth'] = bp_df[SDT_COL_TRANS_DATE_TIME].dt.to_period('M').astype(str)
        return bp_df, count

    BILL_PAY_DF, BILL_PAY_COUNT = _load_bill_pay_data()
    BILL_REV = float(BILL_PAY_DF[SDT_COL_TOTAL_SALES].sum()) if not BILL_PAY_DF.empty else 0.0

    # ------------------------------------------------------------------------
    # Storeperf data - store-level TARGET vs ACHIEVEMENT snapshot.
    # Feeds the 'Top Performing Stores' bar chart (TARGET ACH % / ACC ACH %).
    # ------------------------------------------------------------------------
    def _to_ratio(value):
        """Coerce a Storeperf cell to a 0-1 ratio.

        Excel percentage cells arrive as raw fractions (0.44 == 44%), so the
        value is kept as-is. A cell typed as text ('44%') is tolerated too.
        """
        if isinstance(value, str):
            text = value.strip().replace(',', '')
            if text.endswith('%'):
                num = pd.to_numeric(text[:-1].strip(), errors='coerce')
                return None if pd.isna(num) else float(num) / 100.0
            value = text
        return pd.to_numeric(value, errors='coerce')

    def _load_storeperf_data():
        """Load the 'Storeperf' sheet (store target vs achievement snapshot).

        The heading row has moved around as columns were added (it sat on the
        second row, then moved to the first once the Month column was added),
        so it is *detected*: the sheet is read raw and the first row carrying
        the expected headings is promoted to the header. 'TARGET ACH %' /
        'ACC ACH %' are coerced to numeric 0-1 ratios, a derived 'ACH AVG %'
        column (the mean of the two) is added for ranking, and rows without a
        store name are dropped.
        """
        try:
            raw = pd.read_excel(DATA_PATH, sheet_name='Storeperf', header=None)
        except Exception:
            return pd.DataFrame(columns=STOREPERF_COLUMNS)
        if raw.empty:
            return pd.DataFrame(columns=STOREPERF_COLUMNS)

        # Heading row = the first row that carries the expected labels.
        _needles = {'dealercode', 'store name', 'target ach %'}
        _header_row = None
        for _i in range(len(raw)):
            _cells = {str(c).strip().lower() for c in raw.iloc[_i].tolist()
                      if pd.notna(c)}
            if _needles.issubset(_cells):
                _header_row = _i
                break
        if _header_row is None:
            return pd.DataFrame(columns=STOREPERF_COLUMNS)

        df = raw.iloc[_header_row + 1:].copy()
        df.columns = [str(c).strip() for c in raw.iloc[_header_row].tolist()]
        df = df.reset_index(drop=True)

        for _ratio_col in (STOREPERF_COL_TARGET_ACH, STOREPERF_COL_ACC_ACH):
            if _ratio_col in df.columns:
                df[_ratio_col] = df[_ratio_col].apply(_to_ratio)
        if STOREPERF_COL_MONTH in df.columns:
            df[STOREPERF_COL_MONTH] = df[STOREPERF_COL_MONTH].map(
                lambda v: None if pd.isna(v) else str(v).strip())
        if STOREPERF_COL_STORE in df.columns:
            df = df[df[STOREPERF_COL_STORE].notna()].copy()

        # Derived ranking metric: the mean of the two achievement ratios
        # (skips a missing side, so a store with only one still ranks).
        if {STOREPERF_COL_TARGET_ACH, STOREPERF_COL_ACC_ACH}.issubset(df.columns):
            df[STOREPERF_COL_AVG_ACH] = df[[STOREPERF_COL_TARGET_ACH,
                                            STOREPERF_COL_ACC_ACH]].mean(axis=1)
        return df

    STOREPERF_DF = _load_storeperf_data()

    def _storeperf_month_options():
        """Drop-down options for the chart's Month filter ('All' first)."""
        df = STOREPERF_DF
        if df is None or df.empty or STOREPERF_COL_MONTH not in df.columns:
            return [{'label': 'All Months', 'value': 'All'}]
        months = sorted({str(m).strip() for m in df[STOREPERF_COL_MONTH].dropna()
                         if str(m).strip()})
        return ([{'label': 'All Months', 'value': 'All'}]
                + [{'label': m, 'value': m} for m in months])

    STOREPERF_MONTH_OPTIONS = _storeperf_month_options()

    def _mom_pct_acc():
        """Return (% change vs previous month, label) for Accessories Total Sales."""
        if ACC_DF is None or ACC_DF.empty:
            return None, 'no data'
        g = ACC_DF.groupby('YearMonth')[SDT_COL_TOTAL_SALES].sum()
        if len(g) < 2:
            return None, 'no prev month'
        months = sorted(g.index)
        curr = g[months[-1]]
        prev = g[months[-2]]
        if prev == 0:
            return None, 'no prev value'
        pct = ((curr - prev) / abs(prev)) * 100
        return pct, f'{months[-2]} vs {months[-1]}'

    def mom_badge_acc():
        """Build a small arrow + % badge for Accessories Total Sales month-over-month comparison."""
        pct, note = _mom_pct_acc()
        if pct is None:
            return html.Small('\u2014', className='mom-note', style={'color': '#64748b'})
        up = pct >= 0
        color = '#10b981' if up else '#ef4444'
        arrow = 'fa-arrow-up' if up else 'fa-arrow-down'
        return html.Div([
            html.Div([
                html.I(className=f'fas {arrow} mom-arrow me-1',
                       style={'color': color}),
                html.Span(f'{abs(pct):.1f}%', style={
                          'color': color, 'fontWeight': '700'})
            ]),
            html.Small('vs prev mo', className='mom-note',
                       style={'color': '#64748b'})
        ], className='mom-badge')

    def _options(values):
        opts = [{'label': 'All', 'value': 'All'}]
        opts += [{'label': str(v), 'value': str(v)}
                 for v in sorted(pd.unique(values))]
        return opts

    # ------------------------------------------------------------------------
    # Filter dropdown options derived from the CURRENT SALES UPDATE.xlsx.
    # The previous workbook exposed 'marketid' / 'company' / 'DATE' columns,
    # which no longer exist in the updated file. The updated workbook uses
    # MARKET / STORE / DM (plus 'Trans Date Time'), so build the filter
    # options straight from those columns so the drop-downs show real values.
    # ------------------------------------------------------------------------
    def _sheet_options(col_name, sheet='ActivationSheet'):
        """Return [{'label': 'All', 'value': 'All'}, ...] for a workbook column."""
        try:
            s = pd.read_excel(DATA_PATH, sheet_name=sheet)
        except Exception:
            return [{'label': 'All', 'value': 'All'}]
        if s.empty or col_name not in s.columns:
            return [{'label': 'All', 'value': 'All'}]
        opts = [{'label': 'All', 'value': 'All'}]
        opts += [{'label': str(v), 'value': str(v)}
                 for v in sorted(s[col_name].dropna().unique())]
        return opts

    def _date_bounds(sheet='ActivationSheet'):
        """Return (min_date, max_date) from the workbook's 'Trans Date Time' column."""
        try:
            s = pd.read_excel(DATA_PATH, sheet_name=sheet)
            dates = pd.to_datetime(s['Trans Date Time'], errors='coerce').dropna()
        except Exception:
            return datetime(2020, 1, 1), datetime.now()
        if dates.empty:
            return datetime(2020, 1, 1), datetime.now()
        return dates.min(), dates.max()

    MARKETID_OPTIONS = _sheet_options('MARKET')
    STORE_OPTIONS = _sheet_options('STORE')
    DM_OPTIONS = _sheet_options('DM')
    MARKET_DATE_MIN, MARKET_DATE_MAX = _date_bounds()

    # ----------------------------------------------------------------------------
    # Filtering
    # ----------------------------------------------------------------------------

    def filter_data(df, stores, DM_Name, date_range, custom_start=None, custom_end=None, markets=None):
        """Apply store / employee / market / date-range filters to the dataframe."""
        if df.empty:
            return df

        result = df

        if stores and 'All' not in stores:
            result = result[result['STORE'].astype(str).isin(stores)]

        if markets and 'All' not in markets:
            result = result[result['MARKET'].astype(str).isin(markets)]

        if DM_Name and 'All' not in DM_Name:
            emp_set = set(map(str, DM_Name))
            result = result[result['DM'].astype(str).isin(emp_set)]

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # When ``date_range`` is None but ``custom_start``/``custom_end`` are
        # provided, treat them as raw absolute bounds (used for previous-period
        # comparison frames, e.g. the equivalent of "the prior month" given the
        # active date preset).
        if date_range is None and custom_start and custom_end:
            try:
                cs = pd.Timestamp(custom_start)
                ce = pd.Timestamp(custom_end) + pd.Timedelta(days=1)
                result = result[(result['DATE'] >= cs) & (result['DATE'] < ce)]
            except (TypeError, ValueError):
                pass
        elif date_range == 'Current Month':
            start = today.replace(day=1)
            result = result[(result['DATE'] >= pd.Timestamp(start)) &
                            (result['DATE'] <= pd.Timestamp(today + timedelta(days=1)))]
        elif date_range == 'Last Month':
            first_this = today.replace(day=1)
            start = (first_this - timedelta(days=1)).replace(day=1)
            result = result[(result['DATE'] >= pd.Timestamp(start)) &
                            (result['DATE'] < pd.Timestamp(first_this))]
        elif date_range == 'Last 3 Months':
            result = result[result['DATE'] >=
                            pd.Timestamp(today - timedelta(days=90))]
        elif date_range == 'Custom Date' and custom_start and custom_end:
            try:
                cs = pd.Timestamp(custom_start)
                ce = pd.Timestamp(custom_end) + pd.Timedelta(days=1)
                result = result[(result['DATE'] >= cs) & (result['DATE'] < ce)]
            except (TypeError, ValueError):
                pass

        return result

    # ----------------------------------------------------------------------------
    # KPIs
    # ----------------------------------------------------------------------------

    def _filter_sheet(df, stores, DM_Name, date_range, custom_start=None, custom_end=None, markets=None):
        """Apply store / market / DM / date-range filters to any sheet DataFrame.

        Used so the KPI cards and the trend chart respond to the same filters
        the table/charts use. The KPI frames come from either ActivationSheet
        or SaledetailSheet, both of which expose STORE / MARKET / DM and a
        'Trans Date Time' date column (falling back to 'DATE' when present).
        """
        if df is None or df.empty:
            return df
        result = df

        if stores and 'All' not in stores and 'STORE' in result.columns:
            result = result[result['STORE'].astype(str).isin(stores)]
        if markets and 'All' not in markets and 'MARKET' in result.columns:
            result = result[result['MARKET'].astype(str).isin(markets)]
        if DM_Name and 'All' not in DM_Name and 'DM' in result.columns:
            emp_set = set(map(str, DM_Name))
            result = result[result['DM'].astype(str).isin(emp_set)]

        date_col = ('Trans Date Time' if 'Trans Date Time' in result.columns
                    else ('DATE' if 'DATE' in result.columns else None))
        if date_col is None:
            return result
        dcol = result[date_col]
        if not pd.api.types.is_datetime64_any_dtype(dcol):
            try:
                dcol = pd.to_datetime(dcol, errors='coerce')
            except Exception:
                return result

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        keep = pd.Series(True, index=result.index)

        # When ``date_range`` is None but ``custom_start``/``custom_end`` are
        # provided, treat them as raw absolute bounds (used for previous-period
        # comparison frames, e.g. the equivalent of "the prior month" given the
        # active date preset).
        if date_range is None and custom_start and custom_end:
            try:
                cs = pd.Timestamp(custom_start)
                ce = pd.Timestamp(custom_end) + pd.Timedelta(days=1)
                keep &= (dcol >= cs) & (dcol < ce)
            except (TypeError, ValueError):
                pass
        elif date_range == 'Current Month':
            start = today.replace(day=1)
            keep &= (dcol >= pd.Timestamp(start)) & (dcol <= pd.Timestamp(today + timedelta(days=1)))
        elif date_range == 'Last Month':
            first_this = today.replace(day=1)
            start = (first_this - timedelta(days=1)).replace(day=1)
            keep &= (dcol >= pd.Timestamp(start)) & (dcol < pd.Timestamp(first_this))
        elif date_range == 'Last 3 Months':
            keep &= dcol >= pd.Timestamp(today - timedelta(days=90))
        elif date_range == 'Custom Date' and custom_start and custom_end:
            try:
                cs = pd.Timestamp(custom_start)
                ce = pd.Timestamp(custom_end) + pd.Timedelta(days=1)
                keep &= (dcol >= cs) & (dcol < ce)
            except (TypeError, ValueError):
                pass

        return result[keep]

    def calculate_kpis(df):
        """Return a dict of KPI name -> {'value': number} computed over df.

        NOTE: The Sales Dashboard callback sources its KPI *card* values from
        the sheet-total globals (DP_COUNT, ACT_COUNT, TOTAL_SP_COUNT,
        ACC_TOTAL_SALES, BILL_PAY_COUNT, BILL_REV), not from this dict. This
        helper is kept for API compatibility and now works with the updated
        workbook's schema (ActivationSheet rows).
        """
        if df.empty:
            return {m: {'value': 0} for m in METRIC_COLUMNS}

        kpis = {m: {'value': 0} for m in METRIC_COLUMNS}
        # Each row in the filtered ActivationSheet is one activation.
        count = int(len(df))
        kpis['BTS'] = {'value': count}
        kpis['totact'] = {'value': count}
        return kpis

    # ----------------------------------------------------------------------------
    # Chart data
    # ----------------------------------------------------------------------------

    def get_chart_data(df):
        """Aggregate helper used by the Sales Dashboard charts.

        Updated for the current SALES UPDATE.xlsx schema. The filtered
        DataFrame holds one row per ActivationSheet rec. Aggregations:
          - by_district      : activations per DM
          - by_district_bts  : activations per DM (kept for the donut pie)
          - by_store         : activations per STORE (drives the Top Stores bar)
        """
        if df.empty:
            empty = pd.DataFrame(columns=['YearMonth', 'totact'])
            return {
                'monthly': empty,
                'by_district': pd.DataFrame(columns=['DM', 'totact']),
                'by_district_bts': pd.DataFrame(columns=['DM', 'BTS']),
                'by_store': pd.DataFrame(columns=['company', 'totaccessory', 'totact', 'store_avg']),
            }

        # Month-wise activation count (YYYY-MM from the derived DATE column).
        if 'YearMonth' in df.columns:
            monthly = (df.groupby('YearMonth').size()
                       .reset_index(name='totact')
                       .sort_values('YearMonth'))
        else:
            monthly = pd.DataFrame(columns=['YearMonth', 'totact'])

        by_district = (df.groupby('DM').size()
                       .reset_index(name='totact')
                       .sort_values('totact', ascending=False))

        by_district_bts = (by_district.copy()
                           .rename(columns={'totact': 'BTS'}))

        # Activations per store. The bar chart reads the store name from a
        # 'company' column (legacy name), so surface STORE under that key.
        by_store = (df.groupby('STORE').size()
                    .reset_index(name='totact')
                    .rename(columns={'STORE': 'company'}))
        # No accessory revenue is present on the ActivationSheet, so only
        # activation volume is used as the rank metric.
        by_store['totaccessory'] = 0
        by_store['store_avg'] = by_store['totact']
        by_store = (by_store.sort_values('store_avg', ascending=False)
                    .head(10)
                    .reset_index(drop=True))

        return {
            'monthly': monthly,
            'by_district': by_district,
            'by_district_bts': by_district_bts,
            'by_store': by_store,
        }

    # ----------------------------------------------------------------------------
    # Shared UI: filter section (used by Rebate / Spiff / Accessory GP / Sales Tax)
    # ----------------------------------------------------------------------------

    def create_filter_section(prefix, btn_gradient, employee_label='DM Name'):
        """Build the standard filter card. Component ids are '{prefix}-...'."""
        return dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label([html.I(className='fas fa-store me-2', style={
                                   'color': '#6366f1'}), 'Store Name'], className='filter-label mb-2'),
                        dcc.Dropdown(id=f'{prefix}-store-filter', options=STORE_OPTIONS, value=[
                                     'All'], multi=True, placeholder='Select stores...', className='dark-dropdown')
                    ], xs=12, md=3, className='mb-3 mb-md-0'),
                    dbc.Col([
                        html.Label([html.I(className='fas fa-user me-2', style={
                                   'color': "#820e72f5"}), employee_label], className='filter-label mb-2'),
                        dcc.Dropdown(id=f'{prefix}-employee-filter', options=DM_OPTIONS, value=[
                                     'All'], multi=True, placeholder='Select DM Name...', className='dark-dropdown')
                    ], xs=12, md=3, className='mb-3 mb-md-0'),
                    dbc.Col([
                        html.Label([html.I(className='fas fa-calendar-alt me-2', style={
                                   'color': "#29ef0a"}), 'Date Range'], className='filter-label mb-2'),
                        dcc.Dropdown(id=f'{prefix}-date-range-filter', options=DATE_RANGE_OPTIONS,
                                     value='Current Month', placeholder='Select date range...', className='dark-dropdown')
                    ], xs=12, md=3, className='mb-3 mb-md-0'),
                    dbc.Col([
                        html.Label([html.I(className='fas fa-sliders-h me-2', style={
                                   'color': '#06b6d4'}), 'Actions'], className='filter-label mb-2'),
                        dbc.Button([html.I(className='fas fa-sync-alt me-2'), 'Apply Filters'], id=f'{prefix}-apply-btn', color='primary', className='w-100',
                                   style={'borderRadius': '12px', 'fontWeight': '600', 'background': btn_gradient, 'border': 'none'})
                    ], xs=12, md=4)
                ], align='end'),
                dbc.Collapse([
                    dbc.Row([
                        dbc.Col([html.Label('Start Date', className='filter-label mb-2'), dcc.DatePickerSingle(
                            id=f'{prefix}-custom-start', date=datetime.now() - timedelta(days=30), className='dark-datepicker')], xs=12, md=6),
                        dbc.Col([html.Label('End Date', className='filter-label mb-2'), dcc.DatePickerSingle(
                            id=f'{prefix}-custom-end', date=datetime.now(), className='dark-datepicker')], xs=12, md=6)
                    ], className='mt-3')
                ], id=f'{prefix}-custom-collapse', is_open=False)
            ])
        ], className='filter-card mb-4', style={'background': '#1e293b', 'border': '1px solid #334155', 'borderRadius': '20px'})

    # ============================================================================
    # SALES DASHBOARD PAGE (merged from pages/sales_overview.py)
    # ============================================================================

    # Self-alias so merged page code can keep using `sd.` references
    sd = _sys.modules[__name__]

    # Page is registered at the bottom of this file so `layout` exists first.

    # ============================================================================
    # FILTER SECTION
    # ============================================================================

    def create_sales_filter_section():
        return dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label([
                            html.I(className='fas fa-map-marker-alt me-2',
                                   style={'color': '#8b5cf6'}),
                            'Market'
                        ], className='filter-label mb-2'),
                        dcc.Dropdown(
                            id='marketid-filter',
                            options=sd.MARKETID_OPTIONS,
                            value=['All'],
                            multi=True,
                            placeholder='Select Markets...',
                            className='dark-dropdown'
                        )
                    ], xs=12, md=3, className='mb-3 mb-md-0'),

                    dbc.Col([
                        html.Label([
                            html.I(className='fas fa-store me-2',
                                   style={'color': '#6366f1'}),
                            'Store Name'
                        ], className='filter-label mb-2'),
                        dcc.Dropdown(
                            id='store-filter',
                            options=sd.STORE_OPTIONS,
                            value=['All'],
                            multi=True,
                            placeholder='Select Stores...',
                            className='dark-dropdown'
                        )
                    ], xs=12, md=2, className='mb-3 mb-md-0'),

                    dbc.Col([
                        html.Label([
                            html.I(className='fas fa-user me-2',
                                   style={'color': '#10b981'}),
                            'DM Name'
                        ], className='filter-label mb-2'),
                        dcc.Dropdown(
                            id='employee-filter',
                            options=sd.DM_OPTIONS,
                            value=['All'],
                            multi=True,
                            placeholder='Select DM Name...',
                            className='dark-dropdown'
                        )
                    ], xs=12, md=2, className='mb-3 mb-md-0'),

                    dbc.Col([
                        html.Label([
                            html.I(className='fas fa-calendar-alt me-2',
                                   style={'color': '#f59e0b'}),
                            'Date Range'
                        ], className='filter-label mb-2'),
                        dcc.Dropdown(
                            id='date-range-filter',
                            options=sd.DATE_RANGE_OPTIONS,
                            value='Current Month',
                            placeholder='Select date range...',
                            className='dark-dropdown'
                        )
                    ], xs=12, md=2, className='mb-3 mb-md-0'),

                    dbc.Col([
                        html.Label([
                            html.I(className='fas fa-sliders-h me-2',
                                   style={'color': '#06b6d4'}),
                            'Actions'
                        ], className='filter-label mb-2'),
                        dbc.Button([
                            html.I(className='fas fa-sync-alt me-2'),
                            'Apply Filters'
                        ], id='apply-filters-btn', color='primary',
                            className='w-100', style={
                            'borderRadius': '12px',
                            'fontWeight': '600',
                            'background': 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                            'border': 'none'
                        })
                    ], xs=12, md=3)
                ], align='end'),

                # Custom Date Range (hidden by default)
                dbc.Collapse([
                    dbc.Row([
                        dbc.Col([
                            html.Label(
                                'Start Date', className='filter-label mb-2'),
                            dcc.DatePickerSingle(
                                id='custom-start-date',
                                min_date_allowed=sd.MARKET_DATE_MIN,
                                max_date_allowed=sd.MARKET_DATE_MAX,
                                date=sd.MARKET_DATE_MIN,
                                display_format='YYYY-MM-DD',
                                className='dark-datepicker'
                            )
                        ], xs=12, md=6),
                        dbc.Col([
                            html.Label(
                                'End Date', className='filter-label mb-2'),
                            dcc.DatePickerSingle(
                                id='custom-end-date',
                                min_date_allowed=sd.MARKET_DATE_MIN,
                                max_date_allowed=sd.MARKET_DATE_MAX,
                                date=sd.MARKET_DATE_MAX,
                                display_format='YYYY-MM-DD',
                                className='dark-datepicker'
                            )
                        ], xs=12, md=6)
                    ], className='mt-3')
                ], id='custom-date-collapse', is_open=False)
            ])
        ], className='filter-card mb-4', style={
            'background': '#1e293b',
            'border': '1px solid #334155',
            'borderRadius': '20px',
            'boxShadow': '0 4px 20px rgba(0,0,0,0.3)'
        })

    # ============================================================================
    # KPI CARDS
    # ============================================================================

    def create_kpi_card(kpi_id, icon, label, value, color, bg_gradient):
        return dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Div([
                            html.I(className=f'fas {icon} fa-lg')
                        ], className='kpi-icon me-3', style={
                            'width': '48px',
                            'height': '48px',
                            'borderRadius': '14px',
                            'background': bg_gradient,
                            'display': 'flex',
                            'alignItems': 'center',
                            'justifyContent': 'center',
                            'color': 'white',
                            'flexShrink': '0',
                            'boxShadow': f'0 4px 15px {color}44'
                        }),
                        html.P(label, className='kpi-label mb-0', style={
                            'color': "#ffffff", 'fontSize': '0.875rem', 'fontWeight': '600',
                            'textTransform': 'uppercase', 'letterSpacing': '0.03em'})
                    ], className='d-flex align-items-center mb-3'),
                    html.H3(id=f'sd-kpi-{kpi_id}', children=value,
                            className='mb-1 fw-bold',
                            style={'color': '#f8fafc', 'fontSize': '2rem'}),
                    html.Div(id=f'sd-kpi-{kpi_id}-mom', children='',
                             className='kpi-mom'),
                    html.Div(id=f'sd-kpi-{kpi_id}-pct', children='',
                             className='kpi-pct', style={
                                 'marginTop': '8px', 'fontSize': '0.8rem',
                                 'color': '#72f09c', 'fontWeight': '700'})
                ], className='py-4')
            ], className='kpi-card h-100', style={
                'background': '#1e293b',
                'border': f'1px solid {color}22',
                'borderRadius': '20px',
                'transition': 'all 0.3s ease',
                'boxShadow': f'0 4px 20px {color}11'
            })
        ], xs=12, sm=6, lg=4, xl=2, className='mb-3 kpi-col')

    def _mom_pct(df, column):
        """Return (% change vs previous month, label) for a KPI column.
    Compares the latest month in the data against the immediately preceding month."""
        if df is None or df.empty or column not in df.columns:
            return None, 'no data'
        g = df.groupby('YearMonth')[column].sum()
        if len(g) < 2:
            return None, 'no prev month'
        months = sorted(g.index)
        curr = g[months[-1]]
        prev = g[months[-2]]
        if prev == 0:
            return None, 'no prev value'
        pct = ((curr - prev) / abs(prev)) * 100
        return pct, f'{months[-2]} vs {months[-1]}'

    def _mom_series(df, count_only, column=None):
        """Return a sorted 'YYYY-MM' Series of counts (count_only) or column sums."""
        if df is None or df.empty or 'YearMonth' not in df.columns:
            return pd.Series(dtype=float)
        if count_only:
            s = df.groupby('YearMonth').size()
        elif column is not None and column in df.columns:
            s = df.groupby('YearMonth')[column].sum()
        else:
            return pd.Series(dtype=float)
        s.index = s.index.astype(str)
        return s.sort_index()

    def _mom_badge_from_series(g):
        """Build a small arrow + % MoM badge from a 'YYYY-MM' indexed Series."""
        if g is None or len(g) < 2:
            return html.Small('\u2014', className='mom-note', style={'color': '#64748b'})
        months = sorted(g.index)
        curr = g[months[-1]]
        prev = g[months[-2]]
        if prev == 0:
            return html.Small('\u2014', className='mom-note', style={'color': '#64748b'})
        pct = ((curr - prev) / abs(prev)) * 100
        up = pct >= 0
        color = '#10b981' if up else '#ef4444'
        arrow = 'fa-arrow-up' if up else 'fa-arrow-down'
        return html.Div([
            html.Div([
                html.I(className=f'fas {arrow} mom-arrow me-1',
                       style={'color': color}),
                html.Span(f'{abs(pct):.1f}%', style={
                          'color': color, 'fontWeight': '700'})
            ]),
            html.Small('vs prev mo', className='mom-note',
                       style={'color': "#ffe100"})
        ], className='mom-badge')

    def mom_badge(df, column):
        """Build a small arrow + % badge for month-over-month comparison."""
        s = _mom_series(df, count_only=False, column=column)
        return _mom_badge_from_series(s)

    def mom_count_badge(df):
        """Build a MoM % badge based on row count per month (e.g. # of activations)."""
        s = _mom_series(df, count_only=True)
        return _mom_badge_from_series(s)
    def _mom_two_months_prev(prev_df, curr_df, column=None):
        """Compare a previous-period frame against a current-period frame.

        ``prev_df`` and ``curr_df`` are already date-filtered to their
        respective periods. Returns (prev_sum, curr_sum, pct) computed from
        the aggregation of ``column`` (or row counts when ``column`` is None)
        over each frame.
        """
        def _agg(frame, col):
            if frame is None or frame.empty:
                return 0.0
            if col is None:
                return float(len(frame))
            if col not in frame.columns:
                return 0.0
            return float(frame[col].sum())
        prev_val = _agg(prev_df, column)
        curr_val = _agg(curr_df, column)
        if prev_val == 0:
            return None, curr_val, None
        pct = ((curr_val - prev_val) / abs(prev_val)) * 100
        return prev_val, curr_val, pct


    def _mom_two_months(df, column=None):
        """Compare the current month vs the previous month for a sheet.

        Returns (prev_val, curr_val, pct) computed from the two most recent
        'YYYY-MM' periods present in the sheet's 'YearMonth' column. Unlike the
        generic ``_mom_series`` helpers, this always compares the *most recent*
        month present in the data with the preceding month, so it produces a
        meaningful current-vs-previous-month comparison even when the active
        date-range preset (e.g. 'Current Month') would otherwise collapse the
        filtered set down to a single month.
        """
        if df is None or df.empty or 'YearMonth' not in df.columns:
            return None, None, None
        s = (df.groupby('YearMonth').size() if column is None
             else df.groupby('YearMonth')[column].sum()).sort_index()
        if len(s) < 2:
            return None, None, None
        prev_val = float(s.iloc[-2])
        curr_val = float(s.iloc[-1])
        pct = None if prev_val == 0 else ((curr_val - prev_val) / abs(prev_val)) * 100
        return prev_val, curr_val, pct
    def _previous_period_bounds(date_range, custom_start, custom_end):
        """Return (prev_start, prev_end) for the previous equivalent period.

        For 'All Time' or when the previous period cannot be determined,
        returns (None, None) to indicate that the comparison should use
        the two most recent months present in the data.
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if date_range == 'Current Month':
            first_this = today.replace(day=1)
            prev_start = (first_this - timedelta(days=1)).replace(day=1)
            prev_end = first_this - timedelta(days=1)
            return prev_start, prev_end
        elif date_range == 'Last Month':
            first_this = today.replace(day=1)
            start_last = (first_this - timedelta(days=1)).replace(day=1)
            prev_start = (start_last - timedelta(days=1)).replace(day=1)
            prev_end = start_last - timedelta(days=1)
            return prev_start, prev_end
        elif date_range == 'Last 3 Months':
            prev_start = today - timedelta(days=180)
            prev_end = today - timedelta(days=90)
            return prev_start, prev_end
        elif date_range == 'Custom Date' and custom_start and custom_end:
            try:
                cs = pd.Timestamp(custom_start)
                ce = pd.Timestamp(custom_end)
                period_days = (ce - cs).days + 1
                prev_start = cs - timedelta(days=period_days)
                prev_end = cs - timedelta(days=1)
                return prev_start, prev_end
            except (TypeError, ValueError):
                return None, None
        else:
            # 'All Time' or unknown
            return None, None



    def mom_compare_badge(df, column=None, kind='count', prev_df=None):
        """Render a badge comparing the current period to the previous period.

        When ``prev_df`` is provided, compares ``df`` (current period) with
        ``prev_df`` (previous period) directly. When omitted, falls back to
        comparing the two most recent months present in ``df`` (the legacy
        behavior), so this helper works for both date-preset-driven comparisons
        and date-preset-independent fallbacks.
        """
        if prev_df is not None and not prev_df.empty:
            prev_val, curr_val, pct = _mom_two_months_prev(
                prev_df, df, column
            )
        else:
            prev_val, curr_val, pct = _mom_two_months(df, column)
        if prev_val is None and curr_val is None:
            return html.Small('\u2014', className='mom-note',
                              style={'color': '#64748b'})
        up = (pct is not None and pct >= 0) or (prev_val == 0 and curr_val > 0)
        color = '#10b981' if up else '#ef4444'
        arrow = 'fa-arrow-up' if up else 'fa-arrow-down'
        _fmt = (lambda v: f'${v:,.0f}') if kind == 'money' else (lambda v: f'{v:,.0f}')
        pct_txt = f'{abs(pct):.1f}%' if pct is not None else 'n/a'
        return html.Div([
            html.Div([
                html.I(className=f'fas {arrow} mom-arrow me-1',
                       style={'color': color}),
                html.Span(f'{pct_txt}  ({_fmt(prev_val)} \u2192 {_fmt(curr_val)})',
                          style={'color': color, 'fontWeight': '700'})
            ]),
            html.Small('vs prev mo', className='mom-note',
                       style={'color': '#64748b'})
        ], className='mom-badge')

    # ============================================================================
    # CHARTS SECTION
    # ============================================================================

    def create_charts_section():
        return html.Div([
            dbc.Row([
                # Line Chart - Trend Analysis (full width: this "Performance
                # Metrics" card owns a whole row, and so does "KPI Breakdown"
                # below, which keeps the store-bar / market-map pair aligned)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className='fas fa-chart-line me-2',
                                       style={'color': '#6366f1'}),
                                'Monthly Performance Metrics'
                            ], className='mb-0', style={'color': '#f8fafc'})
                        ], style={'background': 'transparent', 'borderBottom': '1px solid #334155'}),
                        dbc.CardBody([
                            dcc.Graph(id='trend-chart', config={'displayModeBar': False},
                                     style={'height': '350px'})
                        ], className='p-3')
                    ], style={
                        'background': '#1e293b',
                        'border': '1px solid #334155',
                        'borderRadius': '20px'
                    })
                ], xs=12, lg=12, className='mb-4'),

                # Daily (date-wise) companion to the Performance Metrics card
                # above: the same six KPI series, but aggregated by DAY and
                # drawn as a filled gradient *area* chart - a new chart style
                # that shows the day-to-day shape instead of the monthly one.
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className='fas fa-chart-area me-2',
                                       style={'color': '#f59e0b'}),
                                'Performance Metrics - Daily Trend'
                            ], className='mb-0', style={'color': '#f8fafc'})
                        ], style={'background': 'transparent', 'borderBottom': '1px solid #334155'}),
                        dbc.CardBody([
                            dcc.Graph(id='trend-daily-chart', config={'displayModeBar': False},
                                     style={'height': '380px'})
                        ], className='p-3')
                    ], style={
                        'background': '#1e293b',
                        'border': '1px solid #334155',
                        'borderRadius': '20px'
                    })
                ], xs=12, lg=12, className='mb-4'),

                # Donut grid - the KPI cards paired by District. The former
                # "Total Act by District" card and "KPI Cards by District" card
                # are merged into this one card holding a single chart, so the
                # district breakdown for every KPI lives in exactly one place:
                # three nested donuts, each pairing two KPI cards.
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className='fas fa-chart-pie me-2',
                                       style={'color': "#00ff51"}),
                                'KPI Breakdown'
                            ], className='mb-0', style={'color': '#f8fafc'})
                        ], style={'background': 'transparent', 'borderBottom': '1px solid #334155'}),
                        dbc.CardBody([
                            dcc.Graph(id='bts-pie-chart', config={'displayModeBar': False},
                                     style={'height': '380px'})
                        ], className='p-3')
                    ], style={
                        'background': '#1e293b',
                        'border': '1px solid #334155',
                        'borderRadius': '20px'
                    })
                ], xs=12, lg=12, className='mb-4'),
            ]),

            dbc.Row([
                # Bar Chart - Top Stores
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className='fas fa-chart-bar me-2',
                                       style={'color': '#f59e0b'}),
                                'Top Performing Stores'
                            ], className='mb-0', style={'color': '#f8fafc'})
                        ], style={'background': 'transparent', 'borderBottom': '1px solid #334155'}),
                        dbc.CardBody([
                            # Chart-local filter area: search a store by name
                            # and narrow the snapshot to a single Month. Both
                            # drive the chart directly (no Apply button needed).
                            dbc.Row([
                                dbc.Col([
                                    html.Label([
                                        html.I(className='fas fa-search me-2',
                                               style={'color': '#f59e0b'}),
                                        'Store Name'
                                    ], className='filter-label mb-2'),
                                    dcc.Input(
                                        id='sp-store-search', type='search',
                                        placeholder='Search store name...',
                                        debounce=True,
                                        style={'width': '100%',
                                               'background': '#0f172a',
                                               'color': '#f8fafc',
                                               'border': '1px solid #334155',
                                               'borderRadius': '10px',
                                               'padding': '0.5rem 0.75rem'}),
                                ], xs=12, md=6, className='mb-3'),
                                dbc.Col([
                                    html.Label([
                                        html.I(className='fas fa-calendar-alt me-2',
                                               style={'color': '#29ef0a'}),
                                        'Month'
                                    ], className='filter-label mb-2'),
                                    dcc.Dropdown(
                                        id='sp-month-filter',
                                        options=STOREPERF_MONTH_OPTIONS,
                                        value='All', clearable=False,
                                        placeholder='Select month...',
                                        className='dark-dropdown'),
                                ], xs=12, md=6, className='mb-3'),
                            ], className='g-2'),
                            dcc.Graph(id='bar-chart', config={'displayModeBar': False},
                                     style={'height': '380px'})
                        ], className='p-3')
                    ], style={
                        'background': '#1e293b',
                        'border': '1px solid #334155',
                        'borderRadius': '20px'
                    })
                ], xs=12, lg=12, className='mb-4'),
            ]),
        ])

    # ============================================================================
    # PAGE LAYOUT
    # ============================================================================

    layout = dbc.Container([
        # Page Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H2([
                        html.I(className='fas fa-chart-pie me-3',
                               style={'color': '#6366f1'}),
                        'Sales Dashboard'
                    ], className='fw-bold mb-2', style={'color': '#f8fafc'}),
                    html.P('Real-time sales performance analytics and insights',
                           style={'color': '#94a3b8'})
                ], className='mb-4')
            ], width=12)
        ]),

        # Filters
        create_sales_filter_section(),

        # KPI Cards
        dbc.Row([
            create_kpi_card('DP', 'fa-tablet-screen-button', 'Device Protection', '0',
                            '#6366f1', 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)'),
            create_kpi_card('Act', 'fa-user-plus', 'Activations', '0', '#ef4444',
                            'linear-gradient(135deg, rgb(21 223 191) 0%, rgb(17 136 168) 100%)'),
            create_kpi_card('TSP', 'fa-rocket', 'Total Activations', '0', "#72f09c",
                            'linear-gradient(135deg, rgb(29 56 236) 0%, rgb(78 160 255) 100%)'),
            create_kpi_card('ACC', 'fa-hand-holding-usd', 'Total Accessories', '0',
                            "#eac34f", 'linear-gradient(135deg, rgb(210 75 231) 0%, rgb(114 12 162) 100%)'),
            create_kpi_card('totpaymentqty', 'fa-money-bill-wave', 'Bill Pay', '0', "#eac34f",
                            'linear-gradient(135deg, rgb(229 174 17) 0%, rgb(255 38 0) 100%)'),
            create_kpi_card('bill_rev', 'fa-chart-line', 'Bill Revenue', '0', "#eac34f",
                            'linear-gradient(135deg, #34ba03 0%, rgb(181 252 168) 100%)'),
        ], className='g-3 mb-4 kpi-row'),

        # Charts
        create_charts_section(),

    ], fluid=True, className='px-4 pb-5 anim-cards-page')

    # ============================================================================
    # CALLBACKS
    # ============================================================================

    @callback(
        Output('custom-date-collapse', 'is_open'),
        Input('date-range-filter', 'value')
    )
    def toggle_custom_date(date_range):
        return date_range == 'Custom Date'

    @callback(
        Output('sd-kpi-DP', 'children'),
        Output('sd-kpi-Act', 'children'),
        Output('sd-kpi-TSP', 'children'),
        Output('sd-kpi-ACC', 'children'),
        Output('sd-kpi-totpaymentqty', 'children'),
        Output('sd-kpi-bill_rev', 'children'),
        Output('sd-kpi-DP-mom', 'children'),
        Output('sd-kpi-Act-mom', 'children'),
        Output('sd-kpi-TSP-mom', 'children'),
        Output('sd-kpi-TSP-pct', 'children'),
        Output('sd-kpi-ACC-mom', 'children'),
        Output('sd-kpi-totpaymentqty-mom', 'children'),
        Output('sd-kpi-bill_rev-mom', 'children'),
        Output('trend-chart', 'figure'),
        Output('trend-daily-chart', 'figure'),
        Output('bts-pie-chart', 'figure'),
        Input('apply-filters-btn', 'n_clicks'),
        State('store-filter', 'value'),
        State('marketid-filter', 'value'),
        State('employee-filter', 'value'),
        State('date-range-filter', 'value'),
        State('custom-start-date', 'date'),
        State('custom-end-date', 'date')
    )
    def update_dashboard(n_clicks, stores, markets, employees, date_range, custom_start, custom_end):
        # Handle empty data
        if sd.DF.empty:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8'
            )
            return '0', '0', '0', '0', f'{BILL_PAY_COUNT:,}', f'${BILL_REV:,.2f}', '', '', '', 'PROT ATT% n/a', '', '', '', empty_fig, empty_fig, empty_fig

        # Apply filters
        filtered = sd.filter_data(
            sd.DF, stores, employees, date_range, custom_start, custom_end, markets=markets)

        if filtered.empty:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                annotations=[dict(text='No data available',
                                  showarrow=False, font_size=20)]
            )
            return '0', '0', '0', '0', f'{BILL_PAY_COUNT:,}', f'${BILL_REV:,.2f}', '', '', '', 'PROT ATT% n/a', '', '', '', empty_fig, empty_fig, empty_fig

        # Calculate KPIs
        kpis = sd.calculate_kpis(filtered)

        # Get chart data
        chart_data = sd.get_chart_data(filtered)

        # Filter the per-sheet KPI frames with the same selections so that the
        # KPI cards, MoM badges and the trend chart react to the filters.
        dp_f = sd._filter_sheet(DP_DF, stores, employees, date_range, custom_start, custom_end, markets=markets)
        act_f = sd._filter_sheet(ACT_DF, stores, employees, date_range, custom_start, custom_end, markets=markets)
        tsp_f = sd._filter_sheet(TOTAL_SP_DF, stores, employees, date_range, custom_start, custom_end, markets=markets)
        acc_f = sd._filter_sheet(ACC_DF, stores, employees, date_range, custom_start, custom_end, markets=markets)
        bp_f = sd._filter_sheet(BILL_PAY_DF, stores, employees, date_range, custom_start, custom_end, markets=markets)

        # --- Month-over-month comparison frames --------------------------------
        # The KPI *value* cards respect the active date-range preset. The
        # "vs prev mo" comparison should compare the selected period against the
        # previous equivalent period (e.g. this month vs last month).
        #
        # For preset ranges ('Current Month', 'Last Month', 'Last 3 Months')
        # the previous-period boundaries are computed dynamically and the
        # comparison frames are built from those bounds. For 'All Time' there
        # is no single "previous period" — fall back to comparing the two most
        # recent months present in the (store/market/DM-filtered) data, which is
        # the same behavior as the legacy badge.
        prev_start, prev_end = sd._previous_period_bounds(date_range, custom_start, custom_end)
        use_prev = prev_start is not None
        dp_prev = sd._filter_sheet(DP_DF, stores, employees, None,
                                   prev_start, prev_end, markets=markets) if use_prev else None
        act_prev = sd._filter_sheet(ACT_DF, stores, employees, None,
                                    prev_start, prev_end, markets=markets) if use_prev else None
        tsp_prev = sd._filter_sheet(TOTAL_SP_DF, stores, employees, None,
                                    prev_start, prev_end, markets=markets) if use_prev else None
        acc_prev = sd._filter_sheet(ACC_DF, stores, employees, None,
                                    prev_start, prev_end, markets=markets) if use_prev else None
        bp_prev = sd._filter_sheet(BILL_PAY_DF, stores, employees, None,
                                   prev_start, prev_end, markets=markets) if use_prev else None

        def _total_sales(frame):
            if frame is None or frame.empty or SDT_COL_TOTAL_SALES not in frame.columns:
                return 0.0
            return float(frame[SDT_COL_TOTAL_SALES].sum())

        _dp_val = f"{len(dp_f):,}"
        _act_val = f"{len(act_f):,}"
        _tsp_val = f"{len(tsp_f):,}"
        _dp_act_pct_val = (
            f"PROT ATT% {len(dp_f) / len(act_f) * 100:.2f}%"
            if len(act_f) > 0 else 'PROT ATT% n/a'
        )
        _acc_val = f"${_total_sales(acc_f):,.2f}"
        _bp_qty_val = f"{len(bp_f):,}"
        _bp_rev_val = f"${_total_sales(bp_f):,.2f}"

        # --- Trend Chart (Line) - Month-wise, mirroring the six KPI cards ---
        # Counts (left axis): Device Protection, Activations, Total Activations, Bill Pay
        # Revenue (right axis): Total Accessories ($), Bill Revenue ($)
        def _kpi_month_series(df, value_col=None):
            """Return a sorted 'YYYY-MM' indexed Series (count or sum of value_col)."""
            if df is None or df.empty or 'YearMonth' not in df.columns:
                return pd.Series(dtype=float)
            s = (df.groupby('YearMonth').size() if value_col is None
                 else df.groupby('YearMonth')[value_col].sum())
            s.index = s.index.astype(str)
            return s.sort_index()

        _MON_ABBR = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                     7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}

        def _ym_label(ym):
            try:
                y, m = ym.split('-')
                return f'{_MON_ABBR[int(m)]}-{y[2:]}'
            except Exception:
                return ym

        _dp_s = _kpi_month_series(dp_f)
        _act_s = _kpi_month_series(act_f)
        _tsp_s = _kpi_month_series(tsp_f)
        _bp_s = _kpi_month_series(bp_f)
        _acc_s = _kpi_month_series(acc_f, SDT_COL_TOTAL_SALES)
        _bp_rev_s = _kpi_month_series(bp_f, SDT_COL_TOTAL_SALES)

        _months = sorted(set(_dp_s.index) | set(_act_s.index) | set(_tsp_s.index)
                         | set(_bp_s.index) | set(_acc_s.index) | set(_bp_rev_s.index))
        _x = [_ym_label(m) for m in _months]

        def _series_vals(s):
            return [s.get(m, 0) for m in _months]

        def _trace(name, s, color, yaxis=None):
            t = dict(x=_x, y=_series_vals(s), mode='lines+markers', name=name,
                     line=dict(color=color, width=3),
                     marker=dict(size=8, color=color,
                                 line=dict(width=2, color='#1e293b')))
            if yaxis:
                t['yaxis'] = yaxis
            return go.Scatter(**t)

        trend_fig = go.Figure()
        trend_fig.add_trace(_trace('Device Protection', _dp_s, '#6366f1'))
        trend_fig.add_trace(_trace('Activations', _act_s, '#ef4444'))
        trend_fig.add_trace(_trace('Total Activations', _tsp_s, '#10b981'))
        trend_fig.add_trace(_trace('Bill Pay', _bp_s, '#eac34f'))
        trend_fig.add_trace(_trace('Total Accessories', _acc_s, '#8b5cf6', 'y2'))
        trend_fig.add_trace(_trace('Bill Revenue', _bp_rev_s, '#06b6d4', 'y2'))
        trend_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e2e8f0',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                        bgcolor='rgba(30,41,59,0.8)', bordercolor='#334155', borderwidth=1),
            margin=dict(l=40, r=60, t=60, b=40),
            xaxis=dict(gridcolor='#334155', showgrid=True,
                       zeroline=False, title='Month'),
            yaxis=dict(gridcolor='#334155', showgrid=True,
                       zeroline=False, title='Count'),
            yaxis2=dict(overlaying='y', side='right', gridcolor='#334155', showgrid=False,
                        zeroline=False, title='Revenue ($)'),
            hovermode='x unified'
        )

        # --- Daily Trend Chart (Area) - date-wise twin of the month chart -----
        # The same six KPI cards as the line chart above, but bucketed by DAY
        # instead of by month and drawn as a filled *area* chart with gradient
        # fills - a different chart style that keeps the month view above intact
        # while exposing the day-to-day shape of the business.
        # Counts (left axis): Device Protection, Activations, Total Activations,
        # Bill Pay.  Revenue (right axis): Total Accessories ($), Bill Revenue ($).
        def _kpi_day_series(df, value_col=None):
            """Return a sorted 'YYYY-MM-DD' indexed Series (count or sum)."""
            if df is None or df.empty or ACT_COL_TRANS_DATE_TIME not in df.columns:
                return pd.Series(dtype=float)
            if value_col is not None and value_col not in df.columns:
                return pd.Series(dtype=float)
            dts = pd.to_datetime(df[ACT_COL_TRANS_DATE_TIME], errors='coerce')
            ok = dts.notna()
            if not ok.any():
                return pd.Series(dtype=float)
            tmp = df.loc[ok].copy()
            tmp['_Day'] = dts[ok].dt.strftime('%Y-%m-%d').values
            s = (tmp.groupby('_Day').size() if value_col is None
                 else tmp.groupby('_Day')[value_col].sum())
            s.index = s.index.astype(str)
            return s.sort_index()

        def _rgba(color, alpha):
            """Expand a '#rrggbb' / '#rrggbbaa' colour into an rgba() string."""
            h = str(color).lstrip('#')
            try:
                return (f'rgba({int(h[0:2], 16)},{int(h[2:4], 16)},'
                        f'{int(h[4:6], 16)},{alpha})')
            except ValueError:
                return f'rgba(99,102,241,{alpha})'

        def _day_label(day, with_year=False):
            """'May 15' (or 'May 15, 26' when the range spans two years)."""
            try:
                return pd.Timestamp(day).strftime(
                    '%b %d, %y' if with_year else '%b %d')
            except Exception:
                return day

        _dp_day = _kpi_day_series(dp_f)
        _act_day = _kpi_day_series(act_f)
        _tsp_day = _kpi_day_series(tsp_f)
        _bp_day = _kpi_day_series(bp_f)
        _acc_day = _kpi_day_series(acc_f, SDT_COL_TOTAL_SALES)
        _bp_rev_day = _kpi_day_series(bp_f, SDT_COL_TOTAL_SALES)

        _day_keys = sorted(set(_dp_day.index) | set(_act_day.index)
                           | set(_tsp_day.index) | set(_bp_day.index)
                           | set(_acc_day.index) | set(_bp_rev_day.index))
        if _day_keys:
            # Walk a continuous daily range so quiet days read as zero-height
            # notches instead of silently stretching the neighbouring days.
            _day_keys = [d.strftime('%Y-%m-%d') for d in pd.date_range(
                _day_keys[0], _day_keys[-1], freq='D')]
        _multi_year = len({d[:4] for d in _day_keys}) > 1
        _day_x = [_day_label(d, _multi_year) for d in _day_keys]

        def _day_vals(s):
            return [float(s.get(d, 0)) for d in _day_keys]

        # Gradient fills need plotly >= 5.19; older versions silently fall back
        # to the flat translucent fillcolor instead of erroring out.
        _has_fill_gradient = hasattr(go.Scatter(), 'fillgradient')

        def _area_trace(name, s, color, yaxis=None, money=False):
            # hovermode='x unified' already labels every line with the trace
            # name, so the template only supplies the (optionally money) value.
            _fmt = ',.2f' if money else ',.0f'
            _prefix = '$' if money else ''
            t = dict(
                x=_day_x, y=_day_vals(s), mode='lines', name=name,
                line=dict(color=color, width=2.5),
                fill='tozeroy',
                fillcolor=_rgba(color, 0.30 if money else 0.16),
                hovertemplate=(f'{_prefix}%{{y:{_fmt}}}'
                               f'<extra></extra>'))
            if _has_fill_gradient:
                t['fillgradient'] = dict(
                    type='vertical',
                    colorscale=[(0, _rgba(color, 0.55 if money else 0.40)),
                                (1, _rgba(color, 0.0))])
            if yaxis:
                t['yaxis'] = yaxis
            return go.Scatter(**t)

        trend_daily_fig = go.Figure()
        trend_daily_fig.add_trace(_area_trace('Device Protection', _dp_day, '#6366f1'))
        trend_daily_fig.add_trace(_area_trace('Activations', _act_day, '#ef4444'))
        trend_daily_fig.add_trace(_area_trace('Total Activations', _tsp_day, '#10b981'))
        trend_daily_fig.add_trace(_area_trace('Bill Pay', _bp_day, '#eac34f'))
        trend_daily_fig.add_trace(_area_trace('Total Accessories', _acc_day,
                                              '#8b5cf6', 'y2', money=True))
        trend_daily_fig.add_trace(_area_trace('Bill Revenue', _bp_rev_day,
                                              '#06b6d4', 'y2', money=True))
        if not _day_keys:
            trend_daily_fig.update_layout(annotations=[
                dict(text='No dated records in the selected range',
                     showarrow=False, font_size=16, font_color='#94a3b8')])
        trend_daily_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e2e8f0',
            legend=dict(orientation='h', yanchor='bottom', y=1.02,
                        xanchor='right', x=1,
                        bgcolor='rgba(30,41,59,0.8)', bordercolor='#334155',
                        borderwidth=1),
            margin=dict(l=40, r=60, t=60, b=60),
            # Day labels are denser than month labels, so drop the vertical
            # gridlines and tilt the ticks to keep the axis readable.
            xaxis=dict(gridcolor='#334155', showgrid=False, zeroline=False,
                       title='Date', nticks=18, tickangle=-45,
                       automargin=True),
            yaxis=dict(gridcolor='#334155', showgrid=True, zeroline=False,
                       title='Count'),
            yaxis2=dict(overlaying='y', side='right', gridcolor='#334155',
                        showgrid=False, zeroline=False, title='Revenue ($)'),
            hovermode='x unified'
        )

        # --- Donut grid: paired KPI cards by District (nested donuts) ----------
        # Three donuts, each combining one pair of KPI cards:
        #     Device Protection + Total Accessories
        #     Activations       + Bill Pay
        #     Total Activations + Bill Revenue
        #
        # Every pair is drawn as two concentric rings: the OUTER ring is the
        # first KPI, the INNER ring the second. That keeps the units honest -
        # each ring is normalised by plotly to its own metric total, so the
        # count KPIs (Device Protection, Activations, Total Activations, Bill
        # Pay) and the dollar KPIs (Total Accessories, Bill Revenue) never have
        # to share one angle scale.
        #
        # Rings are not re-sorted (sort=False) and every ring walks the same
        # district order, so a district's outer and inner arcs line up.
        #
        # The DM (district) name itself is NOT surfaced by this chart: the
        # slices are labelled with the KPI value only and the tooltip names the
        # KPI + ring position, never the DM. The DM name still drives the slice
        # grouping/ordering below.
        #
        # Colour: every ring gets its own bright colour rather than one flat hue
        # per district, so the card reads as colourful even when the filters
        # leave a single district (the current data). Donut i takes the palette
        # entries 2i (outer) and 2i+1 (inner), and every further district steps
        # two more places, so no two rings collapse onto the same tone.
        #
        # Every KPI name is printed on the donut it belongs to: each donut gets
        # a one-line title above it - the two KPI names joined by "+", each name
        # preceded by a marker drawn in that ring's colour (first marker = outer
        # ring, second = inner ring), so the card can be read without hovering
        # an arc. The ring roles themselves are left to the tooltip and the
        # marker colours. That title band is why the rings do not use the whole
        # card height (see _title_y / _y0 / _y1 below).
        #
        # Raw values are labelled on the slices (no percentages). All six
        # frames honour the active store / market / DM / date filters.
        def _district_split(frame, value_col=None):
            """Return (labels, values, total) for ``frame`` grouped by district."""
            if frame is None or frame.empty or 'DM' not in frame.columns:
                return [], [], 0.0
            grouped = (frame.groupby('DM').size() if value_col is None
                       else frame.groupby('DM')[value_col].sum())
            grouped = grouped.sort_values(ascending=False)
            return (list(grouped.index),
                    [float(v) for v in grouped.values],
                    float(grouped.sum()))

        # Each ring is (metric, labels, values, total, number format)
        bts_pairs = [
            {
                'outer': ('Device Protection', *_district_split(dp_f), ',.0f'),
                'inner': ('Total Accessories',
                          *_district_split(acc_f, SDT_COL_TOTAL_SALES), '$,.2f'),
            },
            {
                'outer': ('Activations', *_district_split(act_f), ',.0f'),
                'inner': ('Bill Pay', *_district_split(bp_f), ',.0f'),
            },
            {
                'outer': ('Total Activations', *_district_split(tsp_f), ',.0f'),
                'inner': ('Bill Revenue',
                          *_district_split(bp_f, SDT_COL_TOTAL_SALES), '$,.2f'),
            },
        ]

        bts_rings = [pair[k] for pair in bts_pairs for k in ('outer', 'inner')]

        if not any(ring[2] for ring in bts_rings):
            bts_pie_fig = go.Figure()
            bts_pie_fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                annotations=[dict(text='No district data available',
                                  showarrow=False, font_size=16)]
            )
        else:
            # Fixed district order so the two rings of a donut line up arc for
            # arc, plus a fixed, bright palette so every ring is a strong,
            # distinct colour.
            bts_order = sorted({d for ring in bts_rings for d in ring[1]},
                               key=str)   # key=str: never compare mixed types
            _pos = {d: i for i, d in enumerate(bts_order)}

            # Vivid, high-contrast palette. Donut i takes two adjacent entries
            # (outer = even, inner = odd); each further district steps two more
            # places, so the six rings never collapse onto the same tones and
            # even a one-district selection (today's data) shows six colours.
            bts_vivid = ["#ff2600e4","#ff9900", 
                         '#00cffb','#4492ef',
                         '#6366f1',"#8e15ff"]

            def _ring_colors(donut_idx, ring_idx, count):
                """Vivid colours for one ring: donut pair + district step."""
                start = donut_idx * 2 + ring_idx
                return [bts_vivid[(start + i * 2) % len(bts_vivid)]
                        for i in range(count)]

            def _ring_slices(ring):
                """Return (labels, values, text) in the shared district order."""
                items = sorted(zip(ring[1], ring[2]), key=lambda t: _pos[t[0]])
                labels = [t[0] for t in items]
                values = [t[1] for t in items]
                text = ([f'${v:,.2f}' for v in values] if '$' in ring[4]
                        else [f'{v:,.0f}' for v in values])
                return labels, values, text

            bts_pie_fig = go.Figure()
            _n_cols = len(bts_pairs)
            _inner_scale = 0.58   # inner ring radius vs the outer one
            # Slice value-label font sizes. The original 10px labels were hard
            # to read against the arcs, so BOTH the outer and the inner ring are
            # now drawn at 2x that size (20px). They stay separate knobs because
            # the inner ring sits on much narrower arcs than the outer one and
            # may need its own tuning later.
            _label_scale = 2        # >= 2x the original 10px labels
            _outer_text_size = 10 * _label_scale
            _inner_text_size = 10 * _label_scale
            _pad = 0.015
            _title_y = 0.99       # top of each donut's KPI-name title
            _donut_titles = []    # one title annotation per donut
            for _idx, _pair in enumerate(bts_pairs):
                _x0 = _idx / _n_cols + _pad
                _x1 = (_idx + 1) / _n_cols - _pad
                # The top band of each column holds the donut's title (see
                # _donut_titles below); the rings fill everything under it.
                # The title is a single line, so the band only has to clear
                # roughly one 12px line plus a little breathing room.
                _y0, _y1 = 0.02, 0.90
                _cx, _cy = (_x0 + _x1) / 2.0, (_y0 + _y1) / 2.0
                _half_w = (_x1 - _x0) / 2.0 * _inner_scale
                _half_h = (_y1 - _y0) / 2.0 * _inner_scale

                # Title of this donut: both KPI names on one line, each preceded
                # by a marker in its ring's colour (first marker = outer ring,
                # second = inner ring). The markers use each ring's first palette
                # entry - the colour a single-district ring shows in full - so
                # the title ties straight back to the arcs. The two names are
                # separated by a space only (no '+'); the coloured markers
                # already make it clear which name belongs to which ring.
                _donut_titles.append(dict(
                    x=_cx, y=_title_y, xref='paper', yref='paper',
                    xanchor='center', yanchor='top', showarrow=False,
                    align='center',
                    text=(
                        f'<span style="color:{_ring_colors(_idx, 0, 1)[0]}">'
                        f'\u25cf <b>{_pair["outer"][0]}</b></span> '
                        f'<span style="color:{_ring_colors(_idx, 1, 1)[0]}">'
                        f'\u25cf <b>{_pair["inner"][0]}</b></span>'
                    ),
                    font=dict(size=12, color='#f8fafc'),
                ))

                # Outer ring fills the column; the inner ring is the same shape
                # scaled by _inner_scale, so it sits exactly inside the hole of
                # the outer ring (its hole is _inner_scale by definition).
                _rings = (
                    (_pair['outer'], dict(x=[_x0, _x1], y=[_y0, _y1]),
                     _inner_scale, 'outer', 0),
                    (_pair['inner'],
                     dict(x=[_cx - _half_w, _cx + _half_w],
                          y=[_cy - _half_h, _cy + _half_h]),
                     0.42, 'inner', 1),
                )

                for _ring, _domain, _hole, _where, _ring_idx in _rings:
                    _metric, _numfmt = _ring[0], _ring[4]
                    _labels, _values, _text = _ring_slices(_ring)
                    bts_pie_fig.add_trace(go.Pie(
                        labels=_labels,
                        values=_values,
                        name=f'{_metric} ({_where})',
                        domain=_domain,
                        hole=_hole,
                        sort=False,   # keep the district arcs aligned
                        marker=dict(
                            colors=_ring_colors(_idx, _ring_idx, len(_labels)),
                            # Thin dark seams so neighbouring slices of the
                            # same ring stay readable against each other.
                            line=dict(color='#1e293b', width=1.5),
                        ),
                        text=_text,
                        textposition='inside',
                        textinfo='text',
                        textfont=dict(size=(_inner_text_size if _where == 'inner'
                                            else _outer_text_size),
                                      color='#ffffff'),
                        # Tooltip shows the KPI + ring position and the value.
                        # The DM (district) name is intentionally left out so the
                        # name is not repeated on every arc of every ring.
                        hovertemplate=(f'<b>{_metric} ({_where})</b><br>'
                                       f'%{{value:{_numfmt}}}<extra></extra>')
                    ))

            bts_pie_fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#e2e8f0',
                showlegend=False,
                # KPI-name titles, one per donut (built in the loop above):
                # every KPI shown in this card is named on its own donut.
                annotations=_donut_titles,
                margin=dict(l=10, r=10, t=10, b=10),
            )

        return (
            _dp_val,
            _act_val,
            _tsp_val,
            _acc_val,
            _bp_qty_val,
            _bp_rev_val,
            sd.mom_compare_badge(dp_f, prev_df=dp_prev if use_prev else None),
            sd.mom_compare_badge(act_f, prev_df=act_prev if use_prev else None),
            sd.mom_compare_badge(tsp_f, prev_df=tsp_prev if use_prev else None),
            _dp_act_pct_val,
            sd.mom_compare_badge(acc_f, SDT_COL_TOTAL_SALES, kind='money',
                                  prev_df=acc_prev if use_prev else None),
            sd.mom_compare_badge(bp_f, prev_df=bp_prev if use_prev else None),
            sd.mom_compare_badge(bp_f, SDT_COL_TOTAL_SALES, kind='money',
                                  prev_df=bp_prev if use_prev else None),
            trend_fig,
            trend_daily_fig,
            bts_pie_fig,
        )

    @callback(
        Output('bar-chart', 'figure'),
        Input('sp-store-search', 'value'),
        Input('sp-month-filter', 'value')
    )
    def update_top_stores(store_search, selected_month):
        """Rank stores by the mean of target and accessory achievement."""
        empty_fig = go.Figure()
        empty_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94a3b8',
            annotations=[dict(text='No matching store data', showarrow=False,
                               font_size=16)]
        )

        storeperf = STOREPERF_DF.copy()
        if storeperf.empty or STOREPERF_COL_AVG_ACH not in storeperf.columns:
            return empty_fig

        if selected_month and selected_month != 'All':
            storeperf = storeperf[
                storeperf[STOREPERF_COL_MONTH].astype(str) == str(selected_month)
            ]
        if store_search:
            storeperf = storeperf[
                storeperf[STOREPERF_COL_STORE].astype(str).str.contains(
                    str(store_search).strip(), case=False, na=False)
            ]

        storeperf = storeperf.dropna(subset=[STOREPERF_COL_AVG_ACH]).sort_values(
            STOREPERF_COL_AVG_ACH, ascending=False
        ).reset_index(drop=True)
        if storeperf.empty:
            return empty_fig

        storeperf['Rank'] = storeperf.index + 1
        storeperf['Rank Label'] = storeperf.apply(
            lambda row: f"{row['Rank']}. {row[STOREPERF_COL_STORE]}", axis=1)
        store_names = storeperf[STOREPERF_COL_STORE].astype(str).tolist()
        rank_labels = storeperf['Rank Label'].tolist()
        averages = storeperf[STOREPERF_COL_AVG_ACH].astype(float).tolist()

        if len(rank_labels) == 1:
            bar_palette = ['#10b981']
        else:
            gradient_positions = [i / (len(rank_labels) - 1) for i in range(len(rank_labels))]
            bar_palette = px.colors.sample_colorscale('Sunset', gradient_positions)

        bar_fig = go.Figure(go.Bar(
            x=rank_labels,
            y=averages,
            marker=dict(
                color=bar_palette,
                line=dict(width=1.5, color='#e2e8f0'),
                opacity=0.95
            ),
            customdata=store_names,
            text=[f'{value:.1%}' for value in averages],
            texttemplate='%{text}',
            textposition='outside',
            textfont=dict(color='#f8fafc', size=11, family='Arial'),
            hovertemplate='<b>%{customdata}</b><br>Rank: %{x}<br>'
                          'Average achievement: %{y:.1%}<extra></extra>'
        ))
        bar_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e2e8f0',
            margin=dict(l=65, r=20, t=25, b=100),
            xaxis=dict(
                gridcolor='#334155', showgrid=False,
                zeroline=False,
                title=dict(text='Store / Rank', font=dict(size=12, color='#e2e8f0')),
                tickangle=-35, tickfont=dict(size=10, color='#e2e8f0')
            ),
            yaxis=dict(
                gridcolor='#334155', showgrid=True,
                zeroline=False,
                title=dict(text='Average Achievement %', font=dict(size=12, color='#e2e8f0')),
                tickformat='.0%', rangemode='tozero',
                tickfont=dict(size=10, color='#e2e8f0')
            ),
            bargap=0.35,
            showlegend=False,
            template='plotly_dark'
        )
        return bar_fig

    # ----------------------------------------------------------------------------
    # PAGE REGISTRATION (must come after `layout` is defined)
    # ----------------------------------------------------------------------------

    try:
        # Requires a Dash app to exist (app.py instantiates Dash before importing
        # this module). Skipped silently when imported outside a Dash context.
        register_page(__name__, path='/sales-dashboard', title='Sales Dashboard',
                      layout=layout)
    except Exception:
        pass

    # Mark this module as fully loaded so re-executions (Dash pages walk) skip the body.
    _SD_LOADED = True
