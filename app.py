import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from io import StringIO, BytesIO
from PIL import Image
from datetime import datetime, timezone
import streamlit.components.v1 as components
import urllib3
import json

# Mengabaikan peringatan SSL agar koneksi ke server pemerintah lebih stabil
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="SKYALERT TNI AU", page_icon="✈️", layout="wide")

# =====================================================
# STYLE
# =====================================================
st.markdown("""
<style>
.stApp { background:#06101a; color:white; }
section[data-testid="stSidebar"] { background:#0d1826; }
.block { background:#132433; padding:18px; border-radius:14px; margin-bottom:15px; }
.alert-normal { background:#0d402c; padding:18px; border-radius:14px; font-size:24px; font-weight:bold; color:white; text-align:center; }
.alert-siaga { background:#7a5a00; padding:18px; border-radius:14px; font-size:24px; font-weight:bold; color:white; text-align:center; }
.alert-awas { background:#7d1010; padding:18px; border-radius:14px; font-size:24px; font-weight:bold; color:white; text-align:center; }
.metar-text { font-family: monospace; background: #000; padding: 10px; border-radius: 5px; color: #00ff00; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# STATION DATA
# =====================================================
CSV_DATA = """
icao,wmo,name,lat,lon,cape,ki,li,freeze,wind
WITT,96001,Sultan Iskandar Muda,5.523,95.420,850,37,-3,16000,35
WIMM,96035,Kualanamu,3.642,98.885,620,35,-2,16500,28
WIBB,96109,Sultan Syarif Kasim II,0.460,101.445,1800,38.5,-4.2,16162,28
WIKK,96237,Depati Amir,-2.162,106.139,300,32,-1,17000,20
WIPP,96295,Sultan Mahmud Badaruddin II,-2.898,104.699,450,34,-1,17500,24
WIII,96749,Soekarno-Hatta,-6.125,106.655,500,35,-2,18000,25
WICC,96783,Husein Sastranegara,-6.900,107.575,700,36,-2,17000,32
WAHI,96747,Yogyakarta International,-7.905,110.057,950,38,-4,15500,40
WARR,96933,Juanda,-7.379,112.787,1200,40,-5,15000,45
WADD,97230,I Gusti Ngurah Rai,-8.748,115.167,350,31,-1,18500,20
WAAA,97180,Sultan Hasanuddin,-5.061,119.554,750,37,-3,16000,34
WAMM,97014,Sam Ratulangi,1.549,124.926,400,33,-1,18000,26
WAPP,97724,Pattimura,-3.710,128.089,680,35,-2,17000,30
WAJJ,97690,Sentani,-2.576,140.516,1100,39,-4,14500,42
"""
df = pd.read_csv(StringIO(CSV_DATA))

# =====================================================
# DATA FETCHERS
# =====================================================
def fetch_bmkg_forecast(adm4_code="31.71.03.1001"):
    """Mengambil data prakiraan cuaca dari API BMKG"""
    url = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={adm4_code}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None

def fetch_image_secure(url):
    """Menarik gambar dengan bypass SSL & User-Agent"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content)), r.headers.get('Last-Modified')
    except:
        return None, None
    return None, None

# =====================================================
# UI START
# =====================================================
st.title("✈️ SKYALERT TNI AU")
st.caption("Tactical Aviation Weather & Upper Air Monitoring")

station = st.selectbox("Pilih Lanud / Stasiun Observasi", df["name"])
row = df[df["name"] == station].iloc[0]

# --- BMKG Forecast Section ---
st.subheader("🗓️ Prakiraan Cuaca BMKG (Publik)")
with st.spinner("Mengambil data prakiraan..."):
    forecast_data = fetch_bmkg_forecast()
    if forecast_data and "data" in forecast_data:
        try:
            # Mengambil list prakiraan
            cuaca = forecast_data["data"][0]["cuaca"][0]
            # Menampilkan summary sederhana
            col1, col2, col3 = st.columns(3)
            col1.metric("Lokasi", forecast_data["data"][0]["lokasi"]["kecamatan"])
            col2.metric("Suhu", f"{cuaca[0]['t']}°C")
            col3.metric("Kondisi", cuaca[0]["weather_desc"])
            st.caption("Data diperbarui secara real-time dari server BMKG Publik.")
        except:
            st.error("Format data BMKG tidak sesuai.")
    else:
        st.warning("Data prakiraan saat ini tidak tersedia.")

st.write("---")

# --- METAR & TAF ---
st.subheader(f"📡 Surface Observation ({row['icao']})")
# (Fungsi fetch_metar_taf tetap sama seperti script awal Anda)
# ... [Sisipkan fungsi fetch_metar_taf di sini] ...

# --- Upper Air ---
st.subheader("☁️ Analisis Stabilitas Atmosfer (Radiosonde)")
# ... [Sisipkan logika analisis seperti script awal] ...

# --- Satellite & Radar ---
st.write("---")
st.subheader("🛰️ Tactical Weather Radar & Satellite")
# (Gunakan logika fetch_image_secure untuk Satelit)
# ... [Sisipkan iframe Windy dan logic image satelit] ...

# --- Footer ---
st.write("---")
st.caption("SKYALERT | Integrasi API Aviation Weather & BMKG Publik")
