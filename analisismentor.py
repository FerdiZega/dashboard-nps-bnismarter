#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

# ==============================
# STREAMLIT CONFIG
# ==============================
st.set_page_config(
    page_title="Dashboard NPS Mentor — BNI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# HEADER
# ==============================
st.title("📊 Dashboard Analisis NPS Mentor — BNI")
st.markdown("Upload dataset NPS dalam format **Excel (.xlsx)** atau **CSV (.csv)** untuk dianalisa otomatis.")
st.markdown("---")

# ==============================
# UPLOAD DATA
# ==============================
uploaded = st.file_uploader("Upload file dataset", type=["xlsx","csv"])

if uploaded is None:
    st.warning("Silakan upload file terlebih dahulu untuk mulai analisis.")
    st.stop()

# ==============================
# LOAD DATA
# ==============================
try:
    if uploaded.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded)
    else:
        df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"Gagal membaca file: {e}")
    st.stop()

df.columns = [c.strip() for c in df.columns]

# Pastikan kolom inti ada
expected_cols = ["PERSON_ID","NAMA","kategori","skor_nps"]
missing = [c for c in expected_cols if c not in df.columns]

if missing:
    st.error(f"Kolom wajib belum lengkap. Dataset harus memiliki: {expected_cols}")
    st.stop()

# ==============================
# FILTER DATA
# ==============================
st.sidebar.header("Filter")

kategori_list = ["Semua Kategori"] + sorted(df["kategori"].unique().tolist())
kategori_selected = st.sidebar.selectbox("Pilih kategori", kategori_list)

range_min, range_max = int(df["skor_nps"].min()), int(df["skor_nps"].max())
score_range = st.sidebar.slider("Rentang skor NPS", range_min, range_max, (range_min, range_max))

search_name = st.sidebar.text_input("Cari nama mentor")

data = df.copy()
if kategori_selected != "Semua Kategori":
    data = data[data["kategori"] == kategori_selected]

data = data[(data["skor_nps"] >= score_range[0]) & (data["skor_nps"] <= score_range[1])]

if search_name:
    data = data[data["NAMA"].str.contains(search_name, case=False)]

# ==============================
# KPI CARD
# ==============================
avg_score = data["skor_nps"].mean()
total_person = data["PERSON_ID"].nunique()
total_row = len(data)
total_cat = df["kategori"].nunique()

k1,k2,k3,k4 = st.columns(4)
k1.metric("Rata-rata NPS", f"{avg_score:.2f}")
k2.metric("Jumlah baris", total_row)
k3.metric("Mentor unik", total_person)
k4.metric("Total kategori", total_cat)

# ==============================
# INSIGHTS
# ==============================
st.subheader("Insight Otomatis")
cat_summary = df.groupby("kategori")["skor_nps"].mean().reset_index()
best = cat_summary.loc[cat_summary["skor_nps"].idxmax()]
worst = cat_summary.loc[cat_summary["skor_nps"].idxmin()]

st.write(f"⭐ Kategori tertinggi: **{best['kategori']}** — {best['skor_nps']:.2f}")
st.write(f"⚠ Kategori terendah: **{worst['kategori']}** — {worst['skor_nps']:.2f}")

# ==============================
# VISUAL
# ==============================
st.subheader("Rata-rata Skor per Kategori")
fig = px.bar(cat_summary.sort_values("skor_nps"),
             x="skor_nps", y="kategori", orientation="h",
             text=cat_summary["skor_nps"].round(2))
st.plotly_chart(fig, width='stretch')

st.subheader("Distribusi Nilai NPS")
st.plotly_chart(px.histogram(data, x="skor_nps", nbins=12), width='stretch')

# ==============================
# TABLE
# ==============================
st.subheader("Tabel Data")
data_show = data.copy().reset_index(drop=True)
data_show["No"] = data_show.index + 1
st.dataframe(data_show[["No","PERSON_ID","NAMA","kategori","skor_nps"]], use_container_width=True)

# ==============================
# DOWNLOAD EXCEL
# ==============================
def save_excel(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return out.getvalue()

st.download_button("📥 Download Hasil Filter (Excel)",
                   save_excel(data_show),
                   file_name="Hasil_Filter_NPS.xlsx")
