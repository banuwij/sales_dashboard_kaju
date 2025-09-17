import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import BytesIO

# ==============================
# Helpers
# ==============================
def to_numeric_rupiah(s):
    """Convert 'Rp239.000' / '-Rp199.000' / '239,000' → float. Keep NaN if not parseable."""
    if pd.isna(s):
        return np.nan
    if isinstance(s, (int, float, np.number)):
        return float(s)
    s = str(s)
    negative = s.strip().startswith("-")
    s = s.replace("-", "").replace("Rp", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        val = float(s) if s != "" else np.nan
        return -val if negative else val
    except Exception:
        return np.nan

def clean_september_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # Normalisasi nama kolom umum
    rename_map = {
        'Unnamed: 0': 'Produk',
        'Stock Keluar': 'Stock Keluar',
        'Stock Masuk': 'Stock Masuk',
        'Stock Akhir': 'Stock Akhir',
        'Harga': 'Harga',
        'Value Total': 'Value Total',
    }
    df = df.rename(columns=rename_map)

    # Pastikan numerik
    for col in ['Stock Keluar', 'Stock Masuk', 'Stock Akhir']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'Harga' in df.columns:
        df['Harga Num'] = df['Harga'].apply(to_numeric_rupiah)

    if 'Value Total' in df.columns:
        df['Value Num'] = df['Value Total'].apply(to_numeric_rupiah)
    elif 'Harga Num' in df.columns:
        # Estimasi kalau tidak ada Value Total
        df['Value Num'] = df['Stock Keluar'] * df['Harga Num']

    # Nama produk fallback
    if 'Produk' not in df.columns:
        object_cols = [c for c in df.columns if df[c].dtype == 'object']
        df['Produk'] = df[object_cols[0]] if object_cols else np.arange(len(df))

    return df

def fmt_rp(x):
    try:
        x = float(x)
        return 'Rp' + f"{int(round(x)): ,}".replace(',', '.')
    except Exception:
        return x

def make_bar(df, x_col, y_col, title, color="#2563EB", top_n=10, x_format=","):
    if df.empty:
        return alt.Chart(pd.DataFrame({x_col: [], y_col: []})).mark_bar()
    tmp = (
        df[[x_col, y_col]]
        .dropna()
        .groupby(x_col, as_index=False)[y_col]
        .sum()
        .sort_values(y_col, ascending=False)
        .head(top_n)
    )
    chart = (
        alt.Chart(tmp).properties(background='white')
        .mark_bar(color=color)
        .encode(
            x=alt.X(f"{y_col}:Q", axis=alt.Axis(format=x_format, labelColor="#111827", titleColor="#111827", gridColor="#E5E7EB"), title=y_col),
            y=alt.Y(f"{x_col}:N", sort='-x', title='Produk', axis=alt.Axis(labelColor="#111827", titleColor="#111827")),
            tooltip=[x_col, alt.Tooltip(f"{y_col}:Q", format=",")],
        )
        .properties(title=title, height=420)
        .configure_title(color="#111827")
        .configure_view(strokeOpacity=0)
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
        return df.to_csv(index=False).encode('utf-8'), filename.replace('.xlsx', '.csv')

# ==============================
# UI & THEME
# ==============================
st.set_page_config(page_title='Kajuaruna Dashboard', layout='wide')

# Inject CSS — dibungkus string agar tidak bikin SyntaxError
CSS = """
<style>
  html, body, [data-testid="stAppViewContainer"] { background-color: #f7f7f8 !important; }
  [data-testid="stHeader"] { background: transparent !important; }
  section[data-testid="stSidebar"] { background-color: #ffffff !important; }
  div.block-container { padding-top: 1.5rem; }

  h1, h2, h3, h4, h5, p, ul, li { color: #111827 !important; font-family: 'Helvetica Neue', Arial, sans-serif; }

  /* KPI text */
  div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] { color: #111827 !important; }

  /* Download button — teks & ikon putih */
  [data-testid="stDownloadButton"] > button {
      background-color: #111827 !important;
      color: #ffffff !important;
      border: 1px solid #111827;
      border-radius: 10px; padding: 10px 16px; font-weight: 600;
  }
  [data-testid="stDownloadButton"] > button * { color: #ffffff !important; fill: #ffffff !important; }
  [data-testid="stDownloadButton"] > button:hover { filter: brightness(1.08); }

  /* DataFrame cards */
  [data-testid="stDataFrame"] { background: #ffffff !important; border: 1px solid #E5E7EB; border-radius: 12px; padding: 6px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Palette
STK_COLOR = "#10B981"   # green (stock keluar)
VAL_COLOR = "#2563EB"   # blue (value)
MINUS_COLOR = "#EF4444" # red (minus)

# Header + logo
col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        st.image('IMG_5681.PNG', width=110)
    except Exception:
        st.write('Kajuaruna')
with col_title:
    st.title('Kajuaruna Dashboard')
    st.caption('Powered by Wijaya & Brothers')

st.markdown("""
Upload **file yang akan di olah** (mis. *So - So September 2025.csv*). App ini menampilkan:

- **Top Penjualan (Stock Keluar)**
- **Produk dengan Value tertinggi** & **produk minus**
- **Produk tidak keluar** dan **tabel ringkasan** + unduhan data bersih
""")

# ==============================
# Upload CSV (tanpa path lokal)
# ==============================
up = st.file_uploader('Upload CSV September 2025', type=['csv'])
if up is None:
    st.info('⬆️ Silakan upload file terlebih dahulu.')
    st.stop()

try:
    raw_df = pd.read_csv(up)
except Exception as e:
    st.error(f'Gagal membaca CSV: {e}')
    st.stop()

# Clean data
sep_df = clean_september_df(raw_df)

# ==============================
# Sidebar Controls
# ==============================
st.sidebar.header('Filter & Opsi')
TOP_N = st.sidebar.slider('Top N', 5, 30, 10, 1)
st.sidebar.checkbox('Tampilkan tabel detail', value=True, key='show_tables')

# ==============================
# KPI
# ==============================
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric('Total Stock Keluar', f"{int(sep_df.get('Stock Keluar', pd.Series([0])).sum()):,}".replace(',', '.'))
with k2:
    st.metric('Total Stock Masuk', f"{int(sep_df.get('Stock Masuk', pd.Series([0])).sum()):,}".replace(',', '.'))
with k3:
    st.metric('Total Value (Rp)', fmt_rp(sep_df.get('Value Num', pd.Series([0])).sum()))
with k4:
    minus_count = int((sep_df.get('Value Num', pd.Series([np.nan])).fillna(0) < 0).sum())
    st.metric('Jumlah Produk Minus', f"{minus_count}")

# ==============================
# Charts: Top Keluar & Top Value
# ==============================
c1, c2 = st.columns(2)
with c1:
    st.altair_chart(
        make_bar(sep_df, 'Produk', 'Stock Keluar', f'Top {TOP_N} Stock Keluar - September 2025', color=STK_COLOR, top_n=TOP_N, x_format=","),
        use_container_width=True
    )
with c2:
    st.altair_chart(
        make_bar(sep_df, 'Produk', 'Value Num', f'Top {TOP_N} Value (Rp) - September 2025', color=VAL_COLOR, top_n=TOP_N, x_format=","),
        use_container_width=True
    )

# ==============================
# Minus Analysis & Zero Movers
# ==============================
m1, m2 = st.columns(2)
with m1:
    minus_df = sep_df[sep_df['Value Num'].fillna(0) < 0][['Produk', 'Value Num']].sort_values('Value Num')
    if minus_df.empty:
        st.success('Tidak ada produk minus berdasarkan Value.')
    else:
        # Chart minus (merah)
        minus_chart = (
            alt.Chart(minus_df.head(TOP_N)).properties(background='white')
            .mark_bar(color=MINUS_COLOR)
            .encode(
                x=alt.X('Value Num:Q', title='Value (Rp)', axis=alt.Axis(format=",", labelColor="#111827", titleColor="#111827", gridColor="#E5E7EB")),
                y=alt.Y('Produk:N', sort='-x', title='Produk', axis=alt.Axis(labelColor="#111827", titleColor="#111827")),
                tooltip=['Produk', alt.Tooltip('Value Num:Q', format=',')]
            )
            .properties(title=f'Bottom {min(TOP_N, len(minus_df))} Produk (Value Minus)')
            .configure_title(color="#111827")
            .configure_view(strokeOpacity=0)
        )
        st.altair_chart(minus_chart, use_container_width=True)

        st.markdown('### Analisa Produk Minus')
        st.write(f'Total produk minus: **{len(minus_df)}**')
        st.markdown('- Stok keluar melebihi stok masuk (oversold)')
        st.markdown('- Kesalahan input data stok atau harga/value')
        st.markdown('- Refund/retur belum dibukukan ke stok masuk')

        minus_df_fmt = minus_df.copy()
        minus_df_fmt['Value (Rp)'] = minus_df_fmt['Value Num'].apply(fmt_rp)
        st.dataframe(minus_df_fmt[['Produk', 'Value (Rp)']].head(min(2000, len(minus_df_fmt))), height=360, use_container_width=True, hide_index=True)

with m2:
    zero_df = sep_df[sep_df['Stock Keluar'] == 0][['Produk']]
    st.subheader('Produk Tidak Keluar (Stock Keluar = 0)')
    st.write(f'Jumlah: **{len(zero_df)}** produk')
    if len(zero_df):
        st.dataframe(zero_df.rename(columns={'Produk': 'Produk'}), height=360, use_container_width=True, hide_index=True)

# ==============================
# Tabel Ringkasan (bersih) — tanpa kolom Value
# ==============================
st.markdown('---')
st.subheader('Tabel Ringkasan (bersih)')
base_cols = [c for c in ['Produk', 'Stock Keluar', 'Stock Masuk', 'Stock Akhir'] if c in sep_df.columns]
view_df = sep_df.copy()
if 'Harga Num' in view_df.columns:
    view_df['Harga (Rp)'] = view_df['Harga Num'].apply(fmt_rp)
cols_show = base_cols + (['Harga (Rp)'] if 'Harga (Rp)' in view_df.columns else [])
# format angka stok untuk tampilan
_disp = view_df[cols_show].copy()
for _c in ['Stock Keluar', 'Stock Masuk', 'Stock Akhir']:
    if _c in _disp.columns:
        try:
            _disp[_c] = _disp[_c].astype(float).round(0).astype(int).map(lambda v: f"{v:,}".replace(',', '.'))
        except Exception:
            pass
st.dataframe(_disp.sort_values('Stock Keluar', ascending=False), height=520, use_container_width=True, hide_index=True)

# ==============================
# Download cleaned data — tombol tema gelap (teks putih)
# ==============================
clean_bytes, fname = df_to_excel_download(sep_df)
st.download_button('⬇️ Download data bersih', data=clean_bytes, file_name=fname, mime='application/octet-stream')

st.caption('© Kajuaruna Dashboard — Powered by Wijaya & Brothers')
