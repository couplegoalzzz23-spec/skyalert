import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from io import StringIO, BytesIO
from PIL import Image
from datetime import datetime, timezone
import streamlit.components.v1 as components

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
    """Mengambil data METAR dan TAF secara real-time dari Aviation Weather Center API"""
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
    """Menentukan cycle observasi Radiosonde (00Z atau 12Z) menggunakan module bawaan"""
    now_utc = datetime.now(timezone.utc)
    if now_utc.hour >= 12:
        cycle = f"{now_utc.strftime('%Y-%m-%d')} 12:00 UTC"
    else:
        cycle = f"{now_utc.strftime('%Y-%m-%d')} 00:00 UTC"
    return cycle

def fetch_image(wmo):
    """Menarik gambar Skew-T BMKG beserta timestamp dari HTTP header"""
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

def fetch_bmkg_public_weather():
    """Mengambil data prakiraan cuaca publik area spesifik dari API BMKG"""
    url = "https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4=31.71.03.1001"
    try:
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

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
# HEADER & UI
# =====================================================
st.title("✈️ SKYALERT TNI AU")
st.caption("Tactical Aviation Weather & Upper Air Monitoring | Sistem Pendukung Keputusan Operasional")

# =====================================================
# SELECT STATION & REAL-TIME FETCH
# =====================================================
c_sel1, c_sel2 = st.columns([1, 2])
with c_sel1:
    station = st.selectbox("Pilih Lanud / Stasiun Observasi", df["name"])

row = df[df["name"] == station].iloc[0]
icao_code = row["icao"]

# Fetch Real-time data
aviation_data = fetch_metar_taf(icao_code)
cycle_time = get_observation_cycle()
status, color, thunder, turbulence, icing = analyze_weather(row["cape"], row["ki"], row["li"], row["freeze"], row["wind"])

# =====================================================
# MAIN ALERT
# =====================================================
st.markdown(
    f"""
    <div class="{color}">
    STATUS OPERASI PENERBANGAN: {status}<br>
    <span style='font-size:16px; font-weight:normal;'>{icao_code} - Siklus Radiosonde: {cycle_time}</span>
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

# =====================================================
# PUBLIC BMKG WEATHER INTEGRATION
# =====================================================
st.write("---")
st.subheader("🌤️ Prakiraan Cuaca Publik BMKG (Referensi Tambahan)")
st.caption("Sumber Data Aktual API: Prakiraan berbasis koordinat wilayah administratif")

bmkg_data = fetch_bmkg_public_weather()
if bmkg_data and "data" in bmkg_data and len(bmkg_data["data"]) > 0:
    lokasi = bmkg_data["data"][0].get("lokasi", {})
    nama_daerah = f"{lokasi.get('desa', '')}, Kec. {lokasi.get('kecamatan', '')}, {lokasi.get('kota', '')}"
    st.markdown(f"**Lokasi Prakiraan Terbaca:** {nama_daerah}")
    
    cuaca_list = bmkg_data["data"][0].get("cuaca", [])
    if cuaca_list and len(cuaca_list) > 0:
        # Mengambil array sekuensial waktu cuaca pertama
        forecasts = cuaca_list[0]
        
        # Menampilkan hingga 6 titik prakiraan waktu ke depan
        display_count = min(6, len(forecasts))
        cols_bmkg = st.columns(display_count)
        
        for i in range(display_count):
            fc = forecasts[i]
            waktu = fc.get("local_datetime", fc.get("datetime", "-"))
            kondisi = fc.get("weather_desc", "-")
            suhu = fc.get("t", "-")
            ws = fc.get("ws", "0") # Kecepatan angin
            wd = fc.get("wd", "-") # Arah angin
            
            # Format parsing agar ringkas
            waktu_jam = waktu.split(" ")[-1] if " " in waktu else waktu
            
            with cols_bmkg[i]:
                st.markdown(f"""
                <div class='metric-card' style='text-align:center;'>
                    <div style='font-size:16px; color:#a2b1c6;'>{waktu_jam}</div>
                    <div style='font-size:14px; margin:8px 0; min-height:40px; display:flex; align-items:center; justify-content:center;'>{kondisi}</div>
                    <div style='font-size:22px; font-weight:bold; color:#00ff00;'>{suhu}°C</div>
                    <div style='font-size:12px; color:#888; margin-top:5px;'>🌬️ {wd} {ws} km/h</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Rincian urutan waktu cuaca belum tersedia di respons saat ini.")
else:
    st.warning("⚠️ Data prakiraan cuaca publik BMKG tidak dapat diambil untuk saat ini.")

# =====================================================
# UPPER AIR ANALYSIS & HAZARD
# =====================================================
st.write("---")
st.subheader("☁️ Analisis Stabilitas Atmosfer (Radiosonde)")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("CAPE (Energi Konvektif)", f"{row['cape']} J/kg")
c2.metric("K-Index (Potensi Badai)", row["ki"])
c3.metric("Lifted Index (LI)", row["li"])
c4.metric("Freezing Level", f"{row['freeze']} ft")
c5.metric("Upper Wind", f"{row['wind']} kt")

st.write("")
h1, h2, h3 = st.columns(3)
with h1:
    st.markdown(f"<div class='block'><h3>⛈️ Thunderstorm</h3><h1>{thunder}</h1></div>", unsafe_allow_html=True)
with h2:
    st.markdown(f"<div class='block'><h3>🌪️ Turbulence</h3><h1>{turbulence}</h1></div>", unsafe_allow_html=True)
with h3:
    st.markdown(f"<div class='block'><h3>❄️ Icing</h3><h1>{icing}</h1></div>", unsafe_allow_html=True)

# =====================================================
# INTERPRETATION & RECOMMENDATION
# =====================================================
summary = f"""
### 💡 Interpretasi Taktis
Data observasi permukaan (METAR) dan profil atmosfer atas menunjukkan kondisi konveksi **{thunder.lower()}**. 
* **Termodinamika:** Nilai CAPE ({row['cape']} J/kg) dan LI ({row['li']}) mengindikasikan tingkat labilitas udara saat ini. K-Index di angka {row['ki']} merepresentasikan probabilitas pertumbuhan awan Cumulonimbus (CB) di sekitar aerodrome.
* **Angin & Temperatur:** Kecepatan angin di lapisan atas ({row['wind']} kt) memicu potensi turbulensi **{turbulence.lower()}**. Waspadai level pembekuan (freezing level) pada ketinggian {row['freeze']} ft untuk risiko icing pada armada udara.

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
st.caption("Peta cuaca interaktif berpusat pada koordinat Lanud.")

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
st.caption("SKYALERT | Integrasi API Aviation Weather Center & BMKG Upper Air | Sistem Pendukung Keputusan Taktis")
