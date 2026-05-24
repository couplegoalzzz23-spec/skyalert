import streamlit as st
import pandas as pd
import requests
import os
from io import StringIO, BytesIO
from PIL import Image
from datetime import datetime, timezone
import streamlit.components.v1 as components

# =====================================================
# CONFIG & STYLE
# =====================================================
st.set_page_config(page_title="SKYALERT TNI AU", page_icon="✈️", layout="wide")

st.markdown("""
<style>
    .stApp { background:#06101a; color:white; }
    .block { background:#132433; padding:18px; border-radius:14px; margin-bottom:15px; }
    .alert-normal { background:#0d402c; padding:18px; border-radius:14px; font-size:24px; font-weight:bold; color:white; text-align:center; }
    .alert-siaga { background:#7a5a00; padding:18px; border-radius:14px; font-size:24px; font-weight:bold; color:white; text-align:center; }
    .alert-awas { background:#7d1010; padding:18px; border-radius:14px; font-size:24px; font-weight:bold; color:white; text-align:center; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# DATA & LOADER
# =====================================================
# Database internal Lanud (tidak boleh hilang)
CSV_DATA = """icao,wmo,name,lat,lon,cape,ki,li,freeze,wind,adm4
WITT,96001,Sultan Iskandar Muda,5.523,95.420,850,37,-3,16000,35,11.71.02.2001
WIMM,96035,Kualanamu,3.642,98.885,620,35,-2,16500,28,12.07.24.2001
WIBB,96109,Sultan Syarif Kasim II,0.460,101.445,1800,38.5,-4.2,16162,28,14.71.03.1001
WIII,96749,Soekarno-Hatta,-6.125,106.655,500,35,-2,18000,25,36.71.01.1001
WARR,96933,Juanda,-7.379,112.787,1200,40,-5,15000,45,35.15.12.2001
WAAA,97180,Sultan Hasanuddin,-5.061,119.554,750,37,-3,16000,34,73.09.01.2001
"""

@st.cache_data
def load_base_data(): return pd.read_csv(StringIO(CSV_DATA.strip()))

def load_wilayah():
    # Membaca CSV dengan penanganan error kolom
    if os.path.exists("kode_wilayah (1).csv"):
        try:
            df = pd.read_csv("kode_wilayah (1).csv", dtype=str)
            # Pastikan kolom 'nama' dan 'kode' ada agar tidak error saat diakses
            if 'nama' in df.columns and 'kode' in df.columns:
                df['label'] = df['nama'].str.title() + " (" + df['kode'] + ")"
                return df
        except:
            return None
    return None

df = load_base_data()
df_wil = load_wilayah()

# =====================================================
# MAIN APP
# =====================================================
st.title("✈️ SKYALERT TNI AU")
station = st.sidebar.selectbox("Pilih Lanud", df["name"])
row = df[df["name"] == station].iloc[0]

# Logika Status
def get_status(row):
    if row["cape"] > 2500 or row["li"] < -5: return "AWAS", "alert-awas"
    if row["cape"] > 1000 or row["li"] < -2: return "SIAGA", "alert-siaga"
    return "NORMAL", "alert-normal"

status, color = get_status(row)
st.markdown(f"<div class='{color}'>STATUS OPERASI: {status}</div>", unsafe_allow_html=True)

# INTERPRETASI TAKTIS (SESUAI PERMINTAAN ASLI)
st.subheader("💡 Interpretasi Taktis")
st.info(f"""
1. **Analisis Konvektif:** Kondisi stabilitas atmosfer saat ini menunjukkan potensi pertumbuhan awan Cumulonimbus dengan intensitas **{'Tinggi' if row['cape'] > 1000 else 'Rendah'}**. 
   Nilai CAPE ({row['cape']} J/kg) dan LI ({row['li']}) mengindikasikan tingkat labilitas yang perlu diwaspadai pada fase *approach* dan *climb*.
2. **Turbulensi & Icing:** Berdasarkan kecepatan angin atas ({row['wind']} kt) dan ketinggian Freezing Level ({row['freeze']} ft), risiko turbulensi berada pada level **{'Tinggi' if row['wind'] >= 40 else 'Sedang'}** dan risiko pembentukan es (*icing*) pada level **{'Tinggi' if row['freeze'] < 12000 else 'Sedang'}**.
3. **Briefing Penerbang:** Sampaikan risiko Icing dan Turbulensi secara eksplisit kepada aircrew sebelum *take-off*.
""")

# PENCARIAN PRESISI
st.subheader("📍 Presisi Wilayah BMKG")
if df_wil is not None:
    pilihan = st.selectbox("Cari Desa/Kecamatan:", df_wil['label'])
else:
    st.write("Data wilayah eksternal tidak ditemukan, menggunakan data default Lanud.")

st.write("---")
st.caption("SKYALERT TNI AU | Sistem Pendukung Keputusan Taktis")
