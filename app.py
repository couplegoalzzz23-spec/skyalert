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

# Menonaktifkan peringatan SSL yang sering muncul saat menarik data dari server pemerintah
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
# REAL-TIME DATA & IMAGE FETCHERS (FIXED)
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
        return f"{now_utc.strftime('%Y-%m-%d')} 12:00 UTC"
    else:
        return f"{now_utc.strftime('%Y-%m-%d')} 00:00 UTC"

def fetch_image_secure(url):
    """Fungsi backend untuk menarik gambar secara aman dengan bypass SSL & User-Agent"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
    }
    try:
        # verify=False penting untuk server yang SSL-nya bermasalah
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        if r.status_code == 200 and len(r.content) > 1000:
            img = Image.open(BytesIO(r.content))
            timestamp = r.headers.get('Last-Modified', 'Timestamp tidak diketahui')
            return img, timestamp
    except Exception:
        pass
    return None, None

# =====================================================
# ENHANCED METEOROLOGICAL ANALYSIS
# =====================================================
def analyze_weather(cape, ki, li, freeze, wind):
    if cape > 2500 or li < -5 or ki >= 40:
        thunder = "TINGGI"; thunder_score = 3
    elif cape > 1000 or li < -2 or ki >= 30:
        thunder = "SEDANG"; thunder_score = 2
    else:
        thunder = "RENDAH"; thunder_score = 1

    if wind >= 40:
        turbulence = "TINGGI"; turb_score = 3
    elif wind >= 25:
        turbulence = "SEDANG"; turb_score = 2
    else:
        turbulence = "RENDAH"; turb_score = 1

    if freeze < 12000:
        icing = "TINGGI"; ice_score = 3
    elif freeze < 16000:
        icing = "SEDANG"; ice_score = 2
    else:
        icing = "RENDAH"; ice_score = 1

    total_score = thunder_score + turb_score + ice_score
    if total_score >= 7 or thunder_score == 3:
        status = "AWAS"; color = "alert-awas"
    elif total_score >= 5:
        status = "SIAGA"; color = "alert-siaga"
    else:
        status = "NORMAL"; color = "alert-normal"

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

st.write("---")

# =====================================================
# UPPER AIR ANALYSIS & HAZARD
# =====================================================
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
st.subheader("🛰️ Tactical Weather Radar & Satellite")
st.caption("Peta cuaca interaktif berpusat pada koordinat Lanud.")

# 1. Radar Cuaca (Windy)
iframe_url = f"https://embed.windy.com/embed.html?type=map&location=coordinates&metricRain=mm&metricTemp=default&metricWind=kt&zoom=8&overlay=radar&product=radar&level=surface&lat={row['lat']}&lon={row['lon']}"
components.iframe(iframe_url, height=500)

# 2. Satelit Himawari-9 IR Enhanced BMKG (FIXED)
st.write("")
st.markdown("**🛰️ [Satelit Himawari-9 IR Enhanced (BMKG)](https://www.bmkg.go.id/cuaca/satelit/himawari-ir-enhanced)**")

# URL Dasar server BMKG (Ditambahkan Open Data BMKG sebagai backup stabil)
asset_base = "https://asset-mkg.bmkg.go.id/satelit/"
mews_base = "https://data.bmkg.go.id/datamkg/MEWS/satelit/"

# Pemetaan otomatis ICAO ke rute URL yang ditarik secara backend
sat_fallback_urls = []
if icao_code in ["WITT", "WIMM", "WIBB", "WIKK", "WIPP"]:
    sat_fallback_urls = [f"{asset_base}H9_EH_Sumatera_latest.png", f"{mews_base}EH_Sumatera.png"]
elif icao_code in ["WIII", "WICC", "WAHI", "WARR"]:
    sat_fallback_urls = [f"{asset_base}H9_EH_Jawa_latest.png", f"{mews_base}EH_Jawa.png"]
elif icao_code in ["WADD"]:
    sat_fallback_urls = [f"{asset_base}H9_EH_Balinusra_latest.png", f"{mews_base}EH_Indo.png"]
elif icao_code in ["WAAA", "WAMM"]:
    sat_fallback_urls = [f"{asset_base}H9_EH_Sulawesi_latest.png", f"{mews_base}EH_Sulawesi.png"]
elif icao_code in ["WAPP"]:
    sat_fallback_urls = [f"{asset_base}H9_EH_Maluku_latest.png", f"{mews_base}EH_Maluku.png"]
elif icao_code in ["WAJJ"]:
    sat_fallback_urls = [f"{asset_base}H9_EH_Papua_latest.png", f"{mews_base}EH_Papua.png"]
else:
    sat_fallback_urls = [f"{asset_base}H9_EH_Indonesia_latest.png"]

sat_fallback_urls.append(f"{mews_base}EH_Indo.png") # Ultimate fallback

sat_img = None
for url in sat_fallback_urls:
    sat_img, _ = fetch_image_secure(url)
    if sat_img:
        # Menampilkan gambar berbasis bytes, menghindari masalah CORS di browser pengguna
        st.image(sat_img, caption=f"Citra Satelit Regional Terkini - Lokasi: {station} ({icao_code})", use_container_width=True)
        break

if not sat_img:
    st.warning("⚠️ Gagal memuat citra satelit. Server BMKG sedang menolak akses, maintenance, atau down.")

# =====================================================
# SKEW-T IMAGE FETCHING (FIXED)
# =====================================================
st.write("---")
st.subheader("📈 Profil Radiosonde (Skew-T Log-P)")

# List URL Radiosonde yang ditarik via backend
rason_urls = [
    f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{row['wmo']}.PNG",
    f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{row['wmo']}.png",
    f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{row['wmo']}.PNG",
    f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{row['wmo']}.png"
]

skew_img = None
img_timestamp = "Tidak diketahui"

for url in rason_urls:
    skew_img, img_timestamp = fetch_image_secure(url)
    if skew_img:
        break

if skew_img:
    st.caption(f"Server BMKG Last-Modified: {img_timestamp}")
    st.image(skew_img, use_container_width=True)
else:
    st.warning("⚠️ BMKG belum mempublikasikan visualisasi sounding terbaru untuk stasiun ini atau server sedang down.")

# =====================================================
# FOOTER
# =====================================================
st.write("---")
st.caption("SKYALERT | Integrasi API Aviation Weather Center & BMKG Upper Air | Sistem Pendukung Keputusan Taktis")
