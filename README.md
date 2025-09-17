# September 2025 Sales Dashboard

A Streamlit app to visualize September 2025 sales (stock keluar, value, minus, zero-movers).

## Quickstart

1. Install Python 3.10+
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```
5. Upload your CSV (e.g., `So - So September 2025.csv`) when prompted.

## Notes
- The app cleans Indonesian Rupiah formats (e.g., `Rp299.000` or `-Rp199.000`).
- If `Value Total` is missing, it estimates `Value Num = Stock Keluar * Harga Num`.
- Column names expected: `Produk` (or first object column), `Stock Keluar`, `Stock Masuk`, `Stock Akhir`, `Harga`, `Value Total`.
