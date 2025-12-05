# dashboard.py
import os
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

# ---------- Config ----------
st.set_page_config(page_title="Dashboard NPS Mentor — BNI", layout="wide")

DB_CONN = os.getenv("DB_CONN")  # postgres connection string (server side)
if not DB_CONN:
    st.error("DB_CONN environment variable belum di-set. Isi DB_CONN di .env atau secret.")
    st.stop()

# create SQLAlchemy engine (pooling default)
engine = create_engine(DB_CONN, pool_pre_ping=True)

st.title("📊 Dashboard Analisis NPS Mentor — BNI")
st.markdown("Dashboard membaca data langsung dari database. Upload lewat halaman upload (uploader).")
st.markdown("---")

# ---------- Sidebar: filter ----------
with engine.connect() as conn:
    # ambil daftar kategori dari DB (limit kecil)
    q = text("SELECT DISTINCT kategori FROM nps_data ORDER BY kategori")
    categories = [r[0] for r in conn.execute(q).fetchall()]

kategori_list = ["Semua Kategori"] + categories
kategori_selected = st.sidebar.selectbox("Pilih Kategori", kategori_list)

# date / optional filters
min_score, max_score = st.sidebar.slider("Rentang skor NPS", 0, 100, (0, 100))
search_name = st.sidebar.text_input("Cari nama (substring)")

# ---------- Aggregate query (server side) ----------
# rata-rata per kategori
with engine.connect() as conn:
    q_cat = text("""
        SELECT kategori, ROUND(AVG(skor_nps)::numeric,2) AS mean_nps, COUNT(*) AS n
        FROM nps_data
        GROUP BY kategori
        ORDER BY mean_nps DESC
    """)
    df_cat = pd.read_sql(q_cat, conn)

st.subheader("Rata-rata NPS per Kategori")
if df_cat.empty:
    st.info("Belum ada data di tabel nps_data.")
else:
    fig = px.bar(df_cat.sort_values("mean_nps"), x="mean_nps", y="kategori", orientation="h",
                 labels={"mean_nps":"Rata-rata NPS","kategori":"Kategori"}, text="mean_nps")
    st.plotly_chart(fig, use_container_width=True)

# ---------- Build filtered result (limited rows) ----------
where_clauses = []
params = {}

if kategori_selected != "Semua Kategori":
    where_clauses.append("kategori = :kategori")
    params["kategori"] = kategori_selected

where_clauses.append("skor_nps BETWEEN :min_s AND :max_s")
params["min_s"] = int(min_score)
params["max_s"] = int(max_score)

if search_name:
    where_clauses.append("LOWER(nama) LIKE :name")
    params["name"] = f"%{search_name.lower()}%"

where_sql = " AND ".join(where_clauses)
base_q = f"""
    SELECT person_id, nama, kategori, skor_nps, id_nps, created_at
    FROM nps_data
    WHERE {where_sql}
    ORDER BY skor_nps DESC
    LIMIT 1000
"""

with engine.connect() as conn:
    df_sample = pd.read_sql(text(base_q), conn, params=params)

st.subheader("Sample Data (max 1000 rows)")
st.write(f"Menampilkan sampai 1.000 baris — gunakan filter untuk mempersempit hasil.")
st.dataframe(df_sample)

# ---------- KPI ----------
with engine.connect() as conn:
    q_kpi = text(f"""
        SELECT
          COUNT(*) FILTER (WHERE skor_nps BETWEEN :min_s AND :max_s) as rows_filtered,
          COUNT(DISTINCT person_id) FILTER (WHERE skor_nps BETWEEN :min_s AND :max_s) as unique_persons,
          ROUND(AVG(skor_nps) FILTER (WHERE skor_nps BETWEEN :min_s AND :max_s)::numeric,2) as avg_nps
        FROM nps_data
    """)
    kpi = conn.execute(q_kpi, {"min_s": params["min_s"], "max_s": params["max_s"]}).fetchone()

k1,k2,k3 = st.columns(3)
k1.metric("Rata-rata NPS (filter)", f"{kpi['avg_nps'] if kpi['avg_nps'] is not None else 0}")
k2.metric("Jumlah baris (filter)", f"{kpi['rows_filtered']}")
k3.metric("Jumlah mentor unik (filter)", f"{kpi['unique_persons']}")

# ---------- Download sample ----------
def to_excel_bytes(df):
    import io
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return buf

if not df_sample.empty:
    st.download_button("📥 Download Sample (Excel)", to_excel_bytes(df_sample), file_name="nps_sample.xlsx")

st.info("Catatan: Dashboard ini melakukan agregasi di database — cocok untuk dataset besar.")
