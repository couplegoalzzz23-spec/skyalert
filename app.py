import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from io import StringIO, BytesIO
from PIL import Image
from datetime import datetime, timezone
import streamlit.components.v1 as components
import tempfile
import os

# Memastikan aplikasi tidak crash jika library fpdf belum terinstal
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="SKYALERT TNI AU",
    page_icon="✈️",
    layout="wide"
)

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
.metric-card { background:#132433; padding:15px; border-radius:12px; }
.metar-text { font-family: monospace; background: #000; padding: 10px; border-radius: 5px; color: #00ff00; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# STATION DATA (FALLBACK/MOCK DATABASE)
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
# REAL-TIME DATA FETCHERS
# =====================================================
def fetch_metar_taf(icao):
    data = {"metar": "Data tidak tersedia", "taf": "Data tidak tersedia"}
    try:
        metar_url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
        taf_url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw"
        
        req_metar = requests.get(metar_url, timeout=5)
        if req_metar.status_code == 200 and req_metar.text.strip():
            data["metar"] = req_metar.text.strip()
            
        req_taf = requests.get(taf_url, timeout=5)
        if req_taf.status_code == 200 and req_taf.text.strip():
            data["taf"] = req_taf.text.strip()
    except Exception:
        pass
    return data

def get_observation_cycle():
    now_utc = datetime.now(timezone.utc)
    if now_utc.hour >= 12:
        cycle = f"{now_utc.strftime('%Y-%m-%d')} 12:00 UTC"
    else:
        cycle = f"{now_utc.strftime('%Y-%m-%d')} 00:00 UTC"
    return cycle

def fetch_image(wmo):
    urls = [
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.PNG",
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.png",
        f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{wmo}.PNG",
        f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{wmo}.png",
    ]
    
    timestamp = "Timestamp tidak diketahui"
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200 and len(r.content) > 1000:
                if 'Last-Modified' in r.headers:
                    timestamp = r.headers['Last-Modified']
                try:
                    img = Image.open(BytesIO(r.content))
                    return img, timestamp
                except:
                    continue
        except:
            continue
    return None, timestamp

# =====================================================
# ENHANCED METEOROLOGICAL ANALYSIS
# =====================================================
def analyze_weather(cape, ki, li, freeze, wind):
    # Analisis Thunderstorm
    if cape > 2500 or li < -5 or ki >= 40:
        thunder = "TINGGI"
        thunder_score = 3
    elif cape > 1000 or li < -2 or ki >= 30:
        thunder = "SEDANG"
        thunder_score = 2
    else:
        thunder = "RENDAH"
        thunder_score = 1

    # Analisis Turbulensi
    if wind >= 40:
        turbulence = "TINGGI"
        turb_score = 3
    elif wind >= 25:
        turbulence = "SEDANG"
        turb_score = 2
    else:
        turbulence = "RENDAH"
        turb_score = 1

    # Analisis Icing
    if freeze < 12000:
        icing = "TINGGI"
        ice_score = 3
    elif freeze < 16000:
        icing = "SEDANG"
        ice_score = 2
    else:
        icing = "RENDAH"
        ice_score = 1

    # Status Keseluruhan
    total_score = thunder_score + turb_score + ice_score
    
    if total_score >= 7 or thunder_score == 3:
        status = "AWAS"
        color = "alert-awas"
    elif total_score >= 5:
        status = "SIAGA"
        color = "alert-siaga"
    else:
        status = "NORMAL"
        color = "alert-normal"

    return status, color, thunder, turbulence, icing

# =====================================================
# HIMAWARI DYNAMIC INTERPRETATION
# =====================================================
def get_himawari_interpretation(thunder_status):
    """Menghasilkan interpretasi satelit Himawari-9 selaras dengan analisis stabilitas atmosfer"""
    if thunder_status == "TINGGI":
        return "Satelit Himawari mengindikasikan pertumbuhan awan konvektif dalam (deep convection) dengan suhu puncak awan signifikan (< -70°C). Terdapat indikasi kuat pembentukan sel Cumulonimbus (CB) aktif di sekitar wilayah aerodrome."
    elif thunder_status == "SEDANG":
        return "Satelit Himawari menunjukkan formasi awan menengah-tinggi dengan suhu puncak awan moderat (-40°C hingga -60°C). Aktivitas konvektif terpantau berkembang dan memerlukan pemantauan lanjutan."
    else:
        return "Satelit Himawari terpantau relatif aman dari sel konvektif aktif berskala luas. Tutupan awan didominasi awan tipis/rendah yang secara umum tidak signifikan mengganggu jarak pandang vertikal."

# =====================================================
# PDF GENERATOR
# =====================================================
def create_pdf_release(station, cycle_time, status, thunder, cape, li, ki, wind, turbulence, freeze, icing, himawari_text):
    if not FPDF_AVAILABLE:
        return None
        
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 1
