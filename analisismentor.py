#!/usr/bin/env python
# coding: utf-8

import os
import pandas as pd
import numpy as np
from tqdm import tqdm
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt
import webbrowser
from io import BytesIO

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Dashboard NPS Mentor — BNI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- FOLDER CSV ----------------
csv_folder = "csv_output"
os.makedirs(csv_folder, exist_ok=True)

# ---------------- LOAD EXCEL ----------------
excel_file = "dummy_dataset_full.xlsx"
if os.path.exists(excel_file):
    xls = pd.ExcelFile(excel_file)
    print(f"Converting Excel to CSV in folder '{csv_folder}'...")
    for sheet in tqdm(xls.sheet_names, desc="Converting sheets"):
        df = pd.read_excel(xls, sheet_name=sheet)
        df.to_csv(os.path.join(csv_folder, f"{sheet}.csv"), index=False)
    print("Conversion complete!")
else:
    print("File dummy_dataset_full.xlsx tidak ditemukan. Menggunakan dummy data.")
    # buat dummy CSV minimal agar dashboard jalan
    cats = ["Fasilitator Internal","Fasilitator Eksternal","Mentor Lapangan",
            "Buddy Lapangan","Coach Lapangan","Pensiunan Observer"]
    rows = []
    pid = 1000
    for cat in cats:
        for i in range(50):
            pid += 1
            rows.append({
                "PERSON_ID": pid,
                "NAMA": f"Nama {pid}",
                "kategori": cat,
                "skor_nps": int(np.clip(np.random.normal(75,10),40,100))
            })
    master_nps = pd.DataFrame(rows)

# ---------------- LOAD CSV ----------------
def load_csv(name):
    path = os.path.join(csv_folder, name)
    if os.path.exists(path):
        return pd.read_csv(path)
    else:
        return pd.DataFrame()

if 'master_nps' not in locals():
    # Load CSV dari folder
    m_biodata       = load_csv("m_biodata.csv")
    mentor_lapangan = load_csv("mentor_lapangan.csv")
    fasil_internal  = load_csv("fasil_internal.csv")
    fasil_eksternal = load_csv("fasil_eksternal.csv")
    buddy           = load_csv("buddy_lapangan.csv")
    coach           = load_csv("coach_lapangan.csv")
    observer        = load_csv("observer_pensiun.csv")

    nps_mentor      = load_csv("nps_mentor_lapangan.csv")
    nps_fi          = load_csv("nps_fasil_internal.csv")
    nps_fe          = load_csv("nps_fasil_eksternal.csv")
    nps_buddy       = load_csv("nps_buddy.csv")
    nps_coach       = load_csv("nps_coach.csv")
    nps_observer    = load_csv("nps_pensiunan_observer.csv")

    # ---------------- NORMALISASI ----------------
    def normalize_person_col(df):
        for c in df.columns:
            if c.upper().strip() in ["PERSON_ID","PERSONID","PERSON"]:
                df = df.rename(columns={c: "PERSON_ID"})
                return df
        return df

    nps_tables = [
        (nps_mentor, "Mentor Lapangan"),
        (nps_fi, "Fasilitator Internal"),
        (nps_fe, "Fasilitator Eksternal"),
        (nps_buddy, "Buddy Lapangan"),
        (nps_coach, "Coach Lapangan"),
        (nps_observer, "Pensiunan Observer")
    ]

    normalized = []
    for df, cat in nps_tables:
        df = normalize_person_col(df)
        if "PERSON_ID" not in df.columns and not m_biodata.empty:
            possible = [c for c in df.columns if df[c].isin(m_biodata["person_id"]).any()]
            if possible:
                df = df.rename(columns={possible[0]: "PERSON_ID"})
        df["kategori"] = cat
        if "skor_nps" not in df.columns:
            for alt in ["skor","score","nps","skor_nps"]:
                if alt in df.columns:
                    df = df.rename(columns={alt:"skor_nps"})
        if all(col in df.columns for col in ["PERSON_ID","skor_nps","kategori"]):
            normalized.append(df[["PERSON_ID","skor_nps","kategori"]])

    master_nps = pd.concat(normalized, ignore_index=True, sort=False)

    if not m_biodata.empty:
        m_biodata_renamed = m_biodata.rename(columns={"person_id":"PERSON_ID","nama":"NAMA"})
        master_nps = master_nps.merge(m_biodata_renamed[["PERSON_ID","NAMA","UNIT","GRADE","JABATAN","TGL_MASUK"]],
                                      on="PERSON_ID", how="left")

# ---------------- DASHBOARD ----------------
st.title("📊 Dashboard Analisis NPS Mentor — BNI")
st.markdown("Dashboard menampilkan ringkasan kinerja mentor berdasarkan nilai NPS.")
st.markdown("---")

# Sidebar filter
st.sidebar.header("Filter Data")
kategori_list = ["Semua Kategori"] + sorted(master_nps["kategori"].unique().tolist())
kategori_selected = st.sidebar.selectbox("Pilih Kategori", kategori_list)

score_min, score_max = int(master_nps["skor_nps"].min()), int(master_nps["skor_nps"].max())
score_range = st.sidebar.slider("Rentang NPS", score_min, score_max, (score_min, score_max))

search_name = st.sidebar.text_input("Cari nama mentor")

# Filter data
df_filtered = master_nps.copy()
if kategori_selected != "Semua Kategori":
    df_filtered = df_filtered[df_filtered["kategori"]==kategori_selected]
df_filtered = df_filtered[(df_filtered["skor_nps"]>=score_range[0]) & (df_filtered["skor_nps"]<=score_range[1])]
if search_name.strip():
    df_filtered = df_filtered[df_filtered["NAMA"].str.contains(search_name, case=False, na=False)]

# KPI
avg_nps = df_filtered["skor_nps"].mean()
total_mentor = df_filtered["PERSON_ID"].nunique()
total_cat = master_nps["kategori"].nunique()
total_rows = len(df_filtered)

k1,k2,k3,k4 = st.columns(4)
k1.metric("Rata-rata NPS", f"{avg_nps:.2f}")
k2.metric("Jumlah baris", total_rows)
k3.metric("Jumlah mentor unik", total_mentor)
k4.metric("Jumlah kategori total", total_cat)

# Insight otomatis
avg_by_cat = master_nps.groupby("kategori")["skor_nps"].mean().reset_index()
best_cat = avg_by_cat.loc[avg_by_cat["skor_nps"].idxmax()]
worst_cat = avg_by_cat.loc[avg_by_cat["skor_nps"].idxmin()]

st.subheader("Insight Otomatis")
st.write(f"- Kategori terbaik: **{best_cat['kategori']}** ({best_cat['skor_nps']:.2f})")
st.write(f"- Kategori terendah: **{worst_cat['kategori']}** ({worst_cat['skor_nps']:.2f})")

# Charts
st.subheader("Rata-rata NPS per Kategori")
fig_cat = px.bar(avg_by_cat.sort_values("skor_nps"), x="skor_nps", y="kategori",
                 orientation="h", text=avg_by_cat["skor_nps"].round(2))
st.plotly_chart(fig_cat, use_container_width=True)

st.subheader("Distribusi Nilai NPS")
fig_hist = px.histogram(df_filtered, x="skor_nps", nbins=12)
st.plotly_chart(fig_hist, use_container_width=True)

# Tabel data
st.subheader("Tabel Data (Filtered)")
df_display = df_filtered.copy().reset_index(drop=True)
df_display["no"] = df_display.index+1
cols_order = ["no","PERSON_ID","NAMA","kategori","skor_nps"]
st.dataframe(df_display[cols_order])

# Download Excel
def to_excel(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="nps_filtered")
    return buf.getvalue()

st.download_button("📥 Download Excel", to_excel(df_display), file_name="nps_filtered.xlsx")

# ---------------- AUTO OPEN BROWSER ----------------
try:
    webbrowser.open("http://localhost:8501")
except:
    pass
