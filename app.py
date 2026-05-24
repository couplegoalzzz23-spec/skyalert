import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from io import StringIO, BytesIO
from PIL import Image
from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components

# =====================================================
# SAFE IMPORT UNTUK METPY & SIPHON (ANTI-CRASH)
# =====================================================
try:
    from siphon.simplewebservice.wyoming import WyomingUpperAir
    import metpy.calc as mpcalc
    from metpy.units import units
    import numpy as np
    ADVANCED_METEO_AVAILABLE = True
except ImportError:
    ADVANCED_METEO_AVAILABLE = False

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
.data-source { font-size: 12px; color: #88a0b9; margin-top: -10px; margin-bottom: 15px; font-style: italic;}
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
    """Aman dari error (Silent Fail) jika API AWC down"""
    data = {"metar": "Data tidak tersedia (API Timeout/Error)", "taf": "Data tidak tersedia (API Timeout/Error)"}
    try:
        req_metar = requests.get(f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw", timeout=4)
        if req_metar.status_code == 200 and req_metar.text.strip(): data["metar"] = req_metar.text.strip()
            
        req_taf = requests.get(f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw", timeout=4)
        if req_taf.status_code == 200 and req_taf.text.strip(): data["taf"] = req_taf.text.strip()
    except Exception:
        pass
    return data

def get_observation_cycle():
    now_utc = datetime.now(timezone.utc)
    target_hour = 12 if now_utc.hour >= 12 else 0
    return f"{now_utc.strftime('%Y-%m-%d')} {target_hour:02d}:00 UTC"

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
            r = requests.get(url, timeout=5)
            if r.status_code == 200 and len(r.content) > 1000:
                if 'Last-Modified' in r.headers:
                    timestamp = r.headers['Last-Modified']
                try:
                    return Image.open(BytesIO(r.content)), timestamp
                except: continue
        except: continue
    return None, timestamp

@st.cache_data(ttl=3600) # Cache data 1 jam agar tidak over-request ke Wyoming
def fetch_thermodynamic_data(wmo_id, fallback_row):
    """
    Fungsi inti DSS: Menarik RAW Data dari Wyoming dan menghitung CAPE/LI/KI dengan MetPy.
    Jika gagal (Wyoming down/MetPy error), otomatis mundur ke data CSV tanpa merusak UI.
    """
    # Nilai Default / Fallback
    cape, ki, li, freeze, wind = fallback_row['cape'], fallback_row['ki'], fallback_row['li'], fallback_row['freeze'], fallback_row['wind']
    source_msg = "🗃️ Database Lokal Statis (Fallback CSV)"

    if not ADVANCED_METEO_AVAILABLE:
        return cape, ki, li, freeze, wind, source_msg + " - Pustaka MetPy/Siphon tidak terdeteksi."

    now = datetime.now(timezone.utc)
    target_date = now.replace(hour=(12 if now.hour >= 12 else 0), minute=0, second=0, microsecond=0)
    
    df_upper = None
    # Coba tarik data cycle saat ini, jika gagal (belum rilis), coba cycle 12 jam sebelumnya
    for attempt in range(2):
        try:
            df_upper = WyomingUpperAir.request_data(target_date, wmo_id)
            source_msg = f"📡 Wyoming Upper Air (Calculated by MetPy) - Cycle: {target_date.strftime('%d %H:%M UTC')}"
            break
        except Exception:
            target_date -= timedelta(hours=12)

    if df_upper is not None:
        try:
            # Cleaning data dari NaN yang sering terjadi pada pembacaan sensor balon cuaca
            df_clean = df_upper.dropna(subset=['pressure', 'temperature', 'dewpoint', 'u_wind', 'v_wind', 'height'])
            
            p = df_clean['pressure'].values * units.hPa
            T = df_clean['temperature'].values * units.degC
            Td = df_clean['dewpoint'].values * units.degC
            u = df_clean['u_wind'].values * units.knots
            v = df_clean['v_wind'].values * units.knots
            h = df_clean['height'].values * units.meter

            # 1. Hitung CAPE
            try:
                cape_val, _ = mpcalc.surface_based_cape_cin(p, T, Td)
                if not np.isnan(cape_val.magnitude): cape = round(cape_val.magnitude, 0)
            except: pass

            # 2. Hitung Lifted Index (LI)
            try:
                li_val = mpcalc.lifted_index(p, T, Td)
                if not np.isnan(li_val.magnitude[0]): li = round(li_val.magnitude[0], 1)
            except: pass

            # 3. Hitung K-Index (KI)
            try:
                ki_val = mpcalc.k_index(p, T, Td)
                if not np.isnan(ki_val.magnitude): ki = round(ki_val.magnitude, 1)
            except: pass

            # 4. Cari Freezing Level
            try:
                T_c = T.magnitude
                freeze_idx = np.where(T_c < 0)[0]
                if len(freeze_idx) > 0:
                    freeze = round((h[freeze_idx[0]]).to('feet').magnitude, 0)
            except: pass

            # 5. Cari Upper Wind Max (Turbulence proxy)
            try:
                wind_spd = mpcalc.wind_speed(u, v)
                wind = round(np.max(wind_spd.magnitude), 0)
            except: pass

        except Exception:
            pass # Jika kalkulasi MetPy gagal karena anomali data, diam dan gunakan fallback CSV

    return cape, ki, li, freeze, wind, source_msg

# =====================================================
# ENHANCED METEOROLOGICAL ANALYSIS
# =====================================================
def analyze_weather(cape, ki, li, freeze, wind):
    if cape > 2500 or li < -5 or ki >= 40: thunder = "TINGGI"; thunder_score = 3
    elif cape > 1000 or li < -2 or ki >= 30: thunder = "SEDANG"; thunder_score = 2
    else: thunder = "RENDAH"; thunder_score = 1

    if wind >= 40: turbulence = "TINGGI"; turb_score = 3
    elif wind >= 25: turbulence = "SEDANG"; turb_score = 2
    else: turbulence = "RENDAH"; turb_score = 1

    if freeze < 12000: icing = "TINGGI"; ice_score = 3
    elif freeze < 16000: icing = "SEDANG"; ice_score = 2
    else: icing = "RENDAH"; ice_score = 1

    total_score = thunder_score + turb_score + ice_score
    if total_score >= 7 or thunder_score == 3: status = "AWAS"; color = "alert-awas"
    elif total_score >= 5: status = "SIAGA"; color = "alert-siaga"
    else: status = "NORMAL"; color = "alert-normal"

    return status, color, thunder, turbulence, icing

# =====================================================
# HEADER & UI
# =====================================================
st.title("✈️ SKYALERT TNI AU")
st.caption("Tactical Aviation Weather & Upper Air Monitoring | Sistem Pendukung Keputusan Operasional")

# =====================================================
# SELECT STATION & DATA FETCHING
# =====================================================
c_sel1, c_sel2 = st.columns([1, 2])
with c_sel1:
    station = st.selectbox("Pilih Lanud / Stasiun Observasi", df["name"])

row = df[df["name"] == station].iloc[0]
icao_code = row["icao"]
wmo_code = row["wmo"]

# Fetch semua data (Metar, Taf, dan Thermo Live via MetPy)
aviation_data = fetch_metar_taf(icao_code)
cycle_time = get_observation_cycle()
calc_cape, calc_ki, calc_li, calc_freeze, calc_wind, data_source = fetch_thermodynamic_data(wmo_code, row)

# Hitung Analisis Bahaya
status, color, thunder, turbulence, icing = analyze_weather(calc_cape, calc_ki, calc_li, calc_freeze, calc_wind)

# =====================================================
# MAIN ALERT
# =====================================================
st.markdown(
    f"""
    <div class="{color}">
    STATUS OPERASI PENERBANGAN: {status}<br>
    <span style='font-size:16px; font-weight:normal;'>{icao_code} - Target Siklus Radiosonde: {cycle_time}</span>
    </div>
    """, unsafe_allow_html=True
)
st.write("---")

# =====================================================
# METAR & TAF SECTION
# =====================================================
st.subheader(f"📡 Real-time Surface Observation ({icao_code})")
col_metar, col_taf = st.columns(2)

with col_metar:
    st.markdown("**METAR (Aktual):**")
    st.markdown(f"<div class='metar-text'>{aviation_data['metar']}</div>", unsafe_allow_html=True)

with col_taf:
    st.markdown("**TAF (Prakiraan):**")
    st.markdown(f"<div class='metar-text'>{aviation_data['taf']}</div>", unsafe_allow_html=True)

st.write("---")

# =====================================================
# UPPER AIR ANALYSIS & HAZARD
# =====================================================
st.subheader("☁️ Analisis Stabilitas Atmosfer (Radiosonde)")
st.markdown(f"<div class='data-source'>Sumber Kalkulasi Termodinamika: {data_source}</div>", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("CAPE (Energi Konvektif)", f"{calc_cape} J/kg")
c2.metric("K-Index (Potensi Badai)", calc_ki)
c3.metric("Lifted Index (LI)", calc_li)
c4.metric("Freezing Level", f"{calc_freeze} ft")
c5.metric("Upper Wind", f"{calc_wind} kt")

st.write("")
h1, h2, h3 = st.columns(3)
with h1: st.markdown(f"<div class='block'><h3>⛈️ Thunderstorm</h3><h1>{thunder}</h1></div>", unsafe_allow_html=True)
with h2: st.markdown(f"<div class='block'><h3>🌪️ Turbulence</h3><h1>{turbulence}</h1></div>", unsafe_allow_html=True)
with h3: st.markdown(f"<div class='block'><h3>❄️ Icing</h3><h1>{icing}</h1></div>", unsafe_allow_html=True)

# =====================================================
# INTERPRETATION & RECOMMENDATION
# =====================================================
summary = f"""
### 💡 Interpretasi Taktis
Data observasi permukaan (METAR) dan profil atmosfer atas menunjukkan kondisi konveksi **{thunder.lower()}**. 
* **Termodinamika:** Nilai CAPE ({calc_cape} J/kg) dan LI ({calc_li}) mengindikasikan tingkat labilitas udara saat ini. K-Index di angka {calc_ki} merepresentasikan probabilitas pertumbuhan awan Cumulonimbus (CB) di sekitar aerodrome.
* **Angin & Temperatur:** Kecepatan angin di lapisan atas ({calc_wind} kt) memicu potensi turbulensi **{turbulence.lower()}**. Waspadai level pembekuan (freezing level) pada ketinggian {calc_freeze} ft untuk risiko icing pada armada udara.

### 📋 Rekomendasi Operasional Militer
1.  **Validasi TAF:** Sinkronkan prakiraan TAF terbaru dengan pantauan radar cuaca secara berkala.
2.  **Mitigasi Rute:** Hindari area dengan sel konvektif aktif jika nilai CAPE > 1500 J/kg, terutama pada fase *approach* dan *climb*.
3.  **Briefing Penerbang:** Sampaikan risiko Icing ({icing}) dan Turbulensi ({turbulence}) secara eksplisit kepada aircrew sebelum *take-off*.
"""
st.info(summary)

# =====================================================
# RADAR & SATELLITE INTEGRATION
# =====================================================
st.write("---")
st.subheader("🛰️ Tactical Weather Radar")
st.caption("Peta cuaca interaktif berpusat pada koordinat Lanud (Windy API).")

iframe_url = f"https://embed.windy.com/embed.html?type=map&location=coordinates&metricRain=mm&metricTemp=default&metricWind=kt&zoom=8&overlay=radar&product=radar&level=surface&lat={row['lat']}&lon={row['lon']}"
components.iframe(iframe_url, height=500)

# =====================================================
# SKEW-T IMAGE FETCHING
# =====================================================
st.write("---")
st.subheader("📈 Profil Radiosonde (Skew-T Log-P)")

img, img_timestamp = fetch_image(row["wmo"])

if img:
    st.caption(f"Server BMKG Last-Modified: {img_timestamp}")
    st.image(img, use_container_width=True)
else:
    st.warning("⚠️ BMKG belum mempublikasikan visualisasi sounding terbaru untuk stasiun ini atau server sedang down.")

# =====================================================
# FOOTER
# =====================================================
st.write("---")
st.caption("SKYALERT | Integrasi API Aviation Weather Center, Wyoming Upper Air & BMKG | Sistem Pendukung Keputusan Taktis")
