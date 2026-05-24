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
    .metric-card { background:#132433; padding:15px; border-radius:12px; }
    .metar-text { font-family: monospace; background: #000; padding: 10px; border-radius: 5px; color: #00ff00; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# DATA LOADER
# =====================================================
CSV_DATA = """icao,wmo,name,lat,lon,cape,ki,li,freeze,wind,adm4
WITT,96001,Sultan Iskandar Muda,5.523,95.420,850,37,-3,16000,35,11.71.02.2001
WIMM,96035,Kualanamu,3.642,98.885,620,35,-2,16500,28,12.07.24.2001
WIBB,96109,Sultan Syarif Kasim II,0.460,101.445,1800,38.5,-4.2,16162,28,14.71.03.1001
WIII,96749,Soekarno-Hatta,-6.125,106.655,500,35,-2,18000,25,36.71.01.1001
WARR,96933,Juanda,-7.379,112.787,1200,40,-5,15000,45,35.15.12.2001
WAAA,97180,Sultan Hasanuddin,-5.061,119.554,750,37,-3,16000,34,73.09.01.2001
"""

@st.cache_data
def load_data(): return pd.read_csv(StringIO(CSV_DATA.strip()))

def load_wilayah_data():
    if os.path.exists("kode_wilayah (1).csv"):
        df = pd.read_csv("kode_wilayah (1).csv", dtype=str)
        df['label'] = df['nama'].str.title() + " (" + df['kode'] + ")"
        return df
    return None

df = load_data()

# =====================================================
# MAIN DASHBOARD LOGIC
# =====================================================
st.title("✈️ SKYALERT TNI AU")
station = st.sidebar.selectbox("Pilih Lanud", df["name"])
row = df[df["name"] == station].iloc[0]

# Fungsi Analisis (Logic Asli)
def analyze_weather(cape, ki, li, freeze, wind):
    # Penentuan Status
    if cape > 2500 or li < -5 or ki >= 40: status, color = "AWAS", "alert-awas"
    elif cape > 1000 or li < -2 or ki >= 30: status, color = "SIAGA", "alert-siaga"
    else: status, color = "NORMAL", "alert-normal"
    
    thunder = "TINGGI" if cape > 2500 else "SEDANG" if cape > 1000 else "RENDAH"
    turb = "TINGGI" if wind >= 40 else "SEDANG" if wind >= 25 else "RENDAH"
    ice = "TINGGI" if freeze < 12000 else "SEDANG" if freeze < 16000 else "RENDAH"
    return status, color, thunder, turb, ice

status, color, thunder, turb, ice = analyze_weather(row["cape"], row["ki"], row["li"], row["freeze"], row["wind"])

st.markdown(f"<div class='{color}'>STATUS OPERASI: {status}</div>", unsafe_allow_html=True)

# BAGIAN INTERPRETASI LENGKAP (DIKEMBALIKAN)
st.subheader("💡 Interpretasi Taktis")
st.info(f"""
1. **Analisis Konvektif:** Kondisi stabilitas atmosfer saat ini menunjukkan potensi pertumbuhan awan Cumulonimbus dengan intensitas **{thunder}**. 
   Nilai CAPE ({row['cape']} J/kg) dan LI ({row['li']}) mengindikasikan tingkat labilitas yang perlu diwaspadai pada fase *approach* dan *climb*.
2. **Turbulensi & Icing:** Berdasarkan kecepatan angin atas ({row['wind']} kt) dan ketinggian Freezing Level ({row['freeze']} ft), risiko turbulensi berada pada level **{turb}** dan risiko pembentukan es (*icing*) pada level **{ice}**.
3. **Briefing Penerbang:** Sampaikan risiko Icing ({ice}) dan Turbulensi ({turb}) secara eksplisit kepada aircrew sebelum *take-off*.
""")

# =====================================================
# PENCARIAN PRESISI
# =====================================================
st.subheader("🌤️ Prakiraan Cuaca BMKG")
wil_data = load_wilayah_data()
if wil_data is not None:
    selected = st.selectbox("Cari Wilayah (Desa/Kec):", wil_data['label'])
else:
    st.write("Data wilayah default digunakan.")

#
