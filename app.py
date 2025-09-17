import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import BytesIO

# ------------------------------
# Helper functions
# ------------------------------

def read_csv_flexible(uploaded_file_or_path):
    """Read CSV from file uploader or local path."""
    if uploaded_file_or_path is None:
        return None
    try:
        if isinstance(uploaded_file_or_path, str):
            return pd.read_csv(uploaded_file_or_path)
        else:
            return pd.read_csv(uploaded_file_or_path)
    except Exception as e:
        st.error(f"Gagal membaca CSV: {e}")
        return None


def to_numeric_rupiah(s):
    if pd.isna(s):
        return np.nan
    if isinstance(s, (int, float, np.number)):
        return float(s)
    s = str(s)
    # Standardize negatives like "-Rp199.000" or "-199,000"
    negative = s.strip().startswith("-")
    s = s.replace("-", "").replace("Rp", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        val = float(s) if s != "" else np.nan
        return -val if negative else val
    except:
        return np.nan


def clean_september_df(df):
    # Try to standardize column names
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # Rename common columns if found
    rename_map = {
        'Unnamed: 0': 'Produk',
        'Stock Keluar': 'Stock Keluar',
        'Stock Masuk': 'Stock Masuk',
        'Stock Akhir': 'Stock Akhir',
        'Harga': 'Harga',
        'Value Total': 'Value Total',
    }
    df = df.rename(columns=rename_map)

    # Ensure numeric columns
    for col in ['Stock Keluar', 'Stock Masuk', 'Stock Akhir']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'Harga' in df.columns:
        df['Harga Num'] = df['Harga'].apply(to_numeric_rupiah)

    if 'Value Total' in df.columns:
        df['Value Num'] = df['Value Total'].apply(to_numeric_rupiah)
    else:
        # If not present, compute approx value = Stock Keluar * Harga Num (if available)
        if 'Harga Num' in df.columns:
            df['Value Num'] = df['Stock Keluar'] * df['Harga Num']

    # Product name fallback
    if 'Produk' not in df.columns:
        # try to find first object column as product name
        object_cols = [c for c in df.columns if df[c].dtype == 'object']
        if object_cols:
            df['Produk'] = df[object_cols[0]]
        else:
            df['Produk'] = np.arange(len(df))

    return df


def make_bar_chart(df, x_col, y_col, title, tooltip=None, top_n=10, sort_desc=True, format_x=None):
    if df.empty:
        return alt.Chart(pd.DataFrame({x_col: [], y_col: []})).mark_bar()
    temp = df[[x_col, y_col]].dropna().copy()
    temp = temp.groupby(x_col, as_index=False)[y_col].sum()
    temp = temp.sort_values(y_col, ascending=not sort_desc).head(top_n)

    chart = (
        alt.Chart(temp)
        .mark_bar()
        .encode(
            x=alt.X(f'{y_col}:Q', title=y_col, axis=alt.Axis(format=format_x) if format_x else alt.Axis()),
            y=alt.Y(f'{x_col}:N', sort='-x', title='Produk'),
            tooltip=tooltip or [x_col, y_col],
        )
        .properties(title=title, height=420)
    )
    return chart


def df_to_excel_download(df, filename='cleaned_september.xlsx'):
    output = BytesIO()
    try:
        import xlsxwriter  # noqa: F401
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='September')
        return output.getvalue(), filename
    except Exception:
        # Fallback to CSV bytes
        return df.to_csv(index=False).encode('utf-8'), filename.replace('.xlsx', '.csv')


# ------------------------------
# UI
# ------------------------------
st.set_page_config(page_title='September 2025 Sales Dashboard', layout='wide')

st.title('September 2025 Sales Dashboard')

st.markdown(
    """
    Upload **file September 2025** (format seperti: *So - So September 2025.csv*). App ini akan:
    - Menampilkan **Top Penjualan (Stock Keluar)**
    - **Produk dengan Value tertinggi** dan **produk minus**
    - Tabel ringkasan dan opsi unduh data yang sudah dibersihkan
    """
)

# Default path (opsional, untuk lokal). Kosongkan jika pakai uploader.
DEFAULT_LOCAL_PATH = ''  # contoh: 'So - So September 2025.csv'

col_up1, col_up2 = st.columns([2,1])
with col_up1:
    up = st.file_uploader('Upload CSV September 2025', type=['csv'])
with col_up2:
    st.write('\\n')
    use_default = st.checkbox('Pakai path lokal (developer)', value=False)
    local_path = st.text_input('Path lokal', value=DEFAULT_LOCAL_PATH)

if (up is None) and not (use_default and local_path):
    st.info('⬆️ Silakan upload file September 2025 terlebih dahulu, atau isi path lokal lalu centang opsi.')
    st.stop()

# Load data
_df = read_csv_flexible(local_path if (use_default and local_path) else up)
if _df is None or _df.empty:
    st.error('Data kosong / tidak terbaca.')
    st.stop()

# Clean
sep_df = clean_september_df(_df)

# Sidebar controls
st.sidebar.header('Filter & Opsi')
TOP_N = st.sidebar.slider('Top N', min_value=5, max_value=30, value=10, step=1)
show_tables = st.sidebar.checkbox('Tampilkan tabel detail', value=True)

# KPI Row
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    total_keluar = float(sep_df.get('Stock Keluar', pd.Series([0])).sum())
    st.metric('Total Stock Keluar', f"{int(total_keluar):,}")
with kpi2:
    total_masuk = float(sep_df.get('Stock Masuk', pd.Series([0])).sum())
    st.metric('Total Stock Masuk', f"{int(total_masuk):,}")
with kpi3:
    total_value = float(sep_df.get('Value Num', pd.Series([0])).sum())
    st.metric('Total Value (Rp)', f"Rp {int(total_value):,}")
with kpi4:
    minus_count = int((sep_df.get('Value Num', pd.Series([np.nan])).fillna(0) < 0).sum())
    st.metric('Jumlah Produk Minus', f"{minus_count}")

# Charts Row 1: Top Stock Keluar & Top Value
c1, c2 = st.columns(2)
with c1:
    chart_keluar = make_bar_chart(
        sep_df, 'Produk', 'Stock Keluar',
        title=f'Top {TOP_N} Stock Keluar - September 2025',
        tooltip=['Produk', 'Stock Keluar'],
        top_n=TOP_N,
        sort_desc=True,
    )
    st.altair_chart(chart_keluar, use_container_width=True)

with c2:
    chart_value = make_bar_chart(
        sep_df, 'Produk', 'Value Num',
        title=f'Top {TOP_N} Value (Rp) - September 2025',
        tooltip=['Produk', alt.Tooltip('Value Num:Q', format=',')],
        top_n=TOP_N,
        sort_desc=True,
        format_x=","
    )
    st.altair_chart(chart_value, use_container_width=True)

# Charts Row 2: Produk Minus & Zero-Keluar
m1, m2 = st.columns(2)
with m1:
    minus_df = sep_df[sep_df['Value Num'].fillna(0) < 0][['Produk', 'Value Num']].sort_values('Value Num')
    if minus_df.empty:
        st.success('Tidak ada produk minus berdasarkan Value Num.')
    else:
        minus_chart = (
            alt.Chart(minus_df.head(TOP_N))
            .mark_bar()
            .encode(x=alt.X('Value Num:Q', title='Value (Rp)', axis=alt.Axis(format=",")),
                    y=alt.Y('Produk:N', sort='-x', title='Produk'),
                    tooltip=['Produk', alt.Tooltip('Value Num:Q', format=',')])
            .properties(title=f'Bottom {min(TOP_N, len(minus_df))} Produk (Value Minus)')
        )
        st.altair_chart(minus_chart, use_container_width=True)

with m2:
    zero_keluar = sep_df[sep_df['Stock Keluar'] == 0][['Produk']]
    st.subheader('Produk Tidak Keluar (Stock Keluar = 0)')
    st.write(f"Jumlah: **{len(zero_keluar)}** produk")
    if show_tables and not zero_keluar.empty:
        st.dataframe(zero_keluar)

# Tables Section
if show_tables:
    st.markdown('---')
    st.subheader('Tabel Ringkasan (bersih)')
    cols_show = [c for c in ['Produk', 'Stock Keluar', 'Stock Masuk', 'Stock Akhir', 'Harga', 'Harga Num', 'Value Total', 'Value Num'] if c in sep_df.columns]
    st.dataframe(sep_df[cols_show].sort_values('Stock Keluar', ascending=False))

# Download cleaned data
clean_bytes, fname = df_to_excel_download(sep_df)
st.download_button('⬇️ Download data bersih', data=clean_bytes, file_name=fname, mime='application/octet-stream')

st.caption('© September 2025 Sales Dashboard — built with Streamlit')