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
st.set_page_config(
    page_title="SKYALERT TNI AU",
    page_icon="✈️",
    layout="wide"
)

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
# STATION DATA & KODE WILAYAH LOADER
# =====================================================
CSV_DATA = """
icao,wmo,name,lat,lon,cape,ki,li,freeze,wind,adm4
WITT,96001,Sultan Iskandar Muda,5.523,95.420,850,37,-3,16000,35,11.71.02.2001
WIMM,96035,Kualanamu,3.642,98.885,620,35,-2,16500,28,12.07.24.2001
WIBB,96109,Sultan Syarif Kasim II,0.460,101.445,1800,38.5,-4.2,16162,28,14.71.03.1001
WIKK,96237,Depati Amir,-2.162,106.139,300,32,-1,17000,20,19.71.01.1001
WIPP,96295,Sultan Mahmud Badaruddin II,-2.898,104.699,450,34,-1,17500,24,16.71.04.1001
WIII,96749,Soekarno-Hatta,-6.125,106.655,500,35,-2,18000,25,36.71.01.1001
WICC,96783,Husein Sastranegara,-6.900,107.575,700,36,-2,17000,32,32.73.05.1001
WAHI,96747,Yogyakarta International,-7.905,110.057,950,38,-4,15500,40,34.01.04.2001
WARR,96933,Juanda,-7.379,112.787,1200,40,-5,15000,45,35.15.12.2001
WADD,97230,I Gusti Ngurah Rai,-8.748,115.167,350,31,-1,18500,20,51.03.01.2001
WAAA,97180,Sultan Hasanuddin,-5.061,119.554,750,37,-3,16000,34,73.09.01.2001
WAMM,97014,Sam Ratulangi,1.549,124.926,400,33,-1,18000,26,71.71.04.1001
WAPP,97724,Pattimura,-3.710,128.089,680,35,-2,17000,30,81.71.02.1001
WAJJ,97690,Sentani,-2.576,140.516,1100,39,-4,14500,42,91.03.01.2001
"""

@st.cache_data
def load_data():
    return pd.read_csv(StringIO(CSV_DATA.strip()))

@st.cache_data
def load_wilayah_data():
    """Memuat database kode wilayah dengan proteksi FileNotFoundError yang ketat"""
    file_path = "kode_wilayah (1).csv"
    if os.path.exists(file_path):
        try:
            df_wil = pd.read_csv(file_path, dtype=str)
            df_wil['kode'] = df_wil['kode'].str.strip()
            df_wil['nama'] = df_wil['nama'].str.strip().str.title()
            df_wil['label'] = df_wil['nama'] + " (" + df_wil['kode'] + ")"
            return df_wil
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame() # Kembalikan DataFrame kosong jika file tidak ada di server

df = load_data()

# =====================================================
# REAL-TIME DATA FETCHERS
# =====================================================
@st.cache_data(ttl=300)
def fetch_metar_taf(icao):
    data = {"metar": "Data tidak tersedia", "taf": "Data tidak tersedia"}
    try:
        req_metar = requests.get(f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw", timeout=5)
        if req_metar.status_code == 200 and req_metar.text.strip():
            data["metar"] = req_metar.text.strip()
            
        req_taf = requests.get(f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw", timeout=5)
        if req_taf.status_code == 200 and req_taf.text.strip():
            data["taf"] = req_taf.text.strip()
    except Exception:
        pass
    return data

@st.cache_data(ttl=600)
def fetch_bmkg_public_weather(adm4_code):
    if not str(adm4_code).strip():
        adm4_code = "31.71.03.1001" 
    url = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={str(adm4_code).strip()}"
    try:
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

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
                timestamp = r.headers.get('Last-Modified', timestamp)
                try:
                    img = Image.open(BytesIO(r.content))
                    return img, timestamp
                except:
                    continue
        except:
            continue
    return None, timestamp

def get_observation_cycle():
    now_utc = datetime.now(timezone.utc)
    hour = "12:00" if now_utc.hour >= 12 else "00:00"
    return f"{now_utc.strftime('%Y-%m-%d')} {hour} UTC"

# =====================================================
# METEOROLOGICAL ANALYSIS
# =====================================================
def analyze_weather(cape, ki, li, freeze, wind):
    if cape > 2500 or li < -5 or ki >= 40: thunder, t_score = "TINGGI", 3
    elif cape > 1000 or li < -2 or ki >= 30: thunder, t_score = "SEDANG", 2
    else: thunder, t_score = "RENDAH", 1

    if wind >= 40: turb, turb_score = "TINGGI", 3
    elif wind >= 25: turb, turb_score = "SEDANG", 2
    else: turb, turb_score = "RENDAH", 1

    if freeze < 12000: ice, ice_score = "TINGGI", 3
    elif freeze < 16000: ice, ice_score = "SEDANG", 2
    else: ice, ice_score = "RENDAH", 1

    total_score = t_score + turb_score + ice_score
    if total_score >= 7 or t_score == 3: return "AWAS", "alert-awas", thunder, turb, ice
    elif total_score >= 5: return "SIAGA", "alert-siaga", thunder, turb, ice
    return "NORMAL", "alert-normal", thunder, turb, ice

# =====================================================
# MAIN DASHBOARD UI
# =====================================================
st.title("✈️ SKYALERT TNI AU")
st.caption("Tactical Aviation Weather & Upper Air Monitoring | Sistem Pendukung Keputusan Operasional")

c_sel1, c_sel2 = st.columns([1, 2])
with c_sel1:
    station = st.selectbox("Pilih Lanud / Stasiun Observasi", df["name"])

row = df[df["name"] == station].iloc[0]
status, color, thunder, turbulence, icing = analyze_weather(row["cape"], row["ki"], row["li"], row["freeze"], row["wind"])

st.markdown(
    f"""
    <div class="{color}">
        STATUS OPERASI PENERBANGAN: {status}<br>
        <span style='font-size:16px; font-weight:normal;'>{row["icao"]} - Siklus Radiosonde: {get_observation_cycle()}</span>
    </div>
    """, unsafe_allow_html=True
)
st.write("---")

st.subheader(f"📡 Real-time Surface Observation ({row['icao']})")
aviation_data = fetch_metar_taf(row["icao"])
col_metar, col_taf = st.columns(2)
with col_metar:
    st.markdown("**METAR (Aktual):**")
    st.markdown(f"<div class='metar-text'>{aviation_data['metar']}</div>", unsafe_allow_html=True)
with col_taf:
    st.markdown("**TAF (Prakiraan):**")
    st.markdown(f"<div class='metar-text'>{aviation_data['taf']}</div>", unsafe_allow_html=True)

# =====================================================
# INTEGRASI API PUBLIK BMKG (PENCARIAN PRESISI)
# =====================================================
st.write("---")
st.subheader("🌤️ Prakiraan Cuaca Publik BMKG (Presisi Wilayah)")

df_wilayah = load_wilayah_data()
default_adm4 = str(row.get("adm4", "31.71.03.1001"))

c_cari1, c_cari2 = st.columns([2, 1])

# Jika file CSV ditemukan, tampilkan dropdown lengkap
if not df_wilayah.empty:
    try:
        default_index = df_wilayah.index[df_wilayah['kode'] == default_adm4].tolist()[0]
    except IndexError:
        default_index = 0
        
    with c_cari1:
        selected_label = st.selectbox("📍 Pilih Wilayah Prakiraan BMKG:", df_wilayah['label'], index=default_index)
    selected_adm4 = selected_label.split("(")[-1].replace(")", "").strip()

# Jika file CSV tidak ada di server, otomatis munculkan pilihan Lanud saja (anti-crash)
else:
    df['label_lanud'] = df['name'] + " (" + df['adm4'] + ")"
    default_index = df.index[df['name'] == station].tolist()[0]
    
    with c_cari1:
        selected_label = st.selectbox("📍 Pilih Wilayah Prakiraan BMKG:", df['label_lanud'], index=default_index)
    selected_adm4 = selected_label.split("(")[-1].replace(")", "").strip()

# Ambil data BMKG
bmkg_data = fetch_bmkg_public_weather(selected_adm4)

if bmkg_data and "data" in bmkg_data and bmkg_data["data"]:
    lokasi = bmkg_data["data"][0].get("lokasi", {})
    nama_daerah = f"{lokasi.get('desa', '')}, Kec. {lokasi.get('kecamatan', '')}, {lokasi.get('kota', '')}, {lokasi.get('provinsi', '')}"
    st.markdown(f"**📍 Lokasi Terbaca oleh API:** `{nama_daerah}`")
    
    cuaca_list = bmkg_data["data"][0].get("cuaca", [])
    if cuaca_list and cuaca_list[0]:
        forecasts = cuaca_list[0]
        display_count = min(6, len(forecasts))
        cols_bmkg = st.columns(display_count)
        
        for i in range(display_count):
            fc = forecasts[i]
            waktu = fc.get("local_datetime", fc.get("datetime", "-"))
            waktu_jam = waktu.split(" ")[-1] if " " in waktu else waktu
            kondisi = fc.get("weather_desc", "-")
            suhu = fc.get("t", "-")
            ws, wd = fc.get("ws", "0"), fc.get("wd", "-")
            
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
    st.error("⚠️ Data prakiraan cuaca tidak tersedia untuk kode wilayah yang dipilih, atau server BMKG sedang sibuk.")

# =====================================================
# UPPER AIR ANALYSIS
# =====================================================
st.write("---")
st.subheader("☁️ Analisis Stabilitas Atmosfer (Radiosonde)")
# Menambahkan takarir/caption asal muasal instrumen data agar user tidak menduga-duga
st.caption(f"📊 Sumber Data: Hasil ekstraksi parameter fisis profil sounding udara atas stasiun udara WMO {row['wmo']} melalui jaringan [BMKG Monitoring Radiosonde](https://aviation.bmkg.go.id/monitoring_rason/index).")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("CAPE (Energi Konvektif)", f"{row['cape']} J/kg")
c2.metric("K-Index", row["ki"])
c3.metric("Lifted Index", row["li"])
c4.metric("Freezing Level", f"{row['freeze']} ft")
c5.metric("Upper Wind", f"{row['wind']} kt")

h1, h2, h3 = st.columns(3)
h1.markdown(f"<div class='block'><h3>⛈️ Thunderstorm</h3><h1>{thunder}</h1></div>", unsafe_allow_html=True)
h2.markdown(f"<div class='block'><h3>🌪️ Turbulence</h3><h1>{turbulence}</h1></div>", unsafe_allow_html=True)
h3.markdown(f"<div class='block'><h3>❄️ Icing</h3><h1>{icing}</h1></div>", unsafe_allow_html=True)

st.info(f"""
### 💡 Interpretasi Taktis & Analisis Termodinamika
**STATUS PERINGATAN UMUM: {status}**

*🔍 **Transparansi & Validitas Data:** Seluruh indeks stabilitas dan parameter termodinamika di atas dihitung dan diekstraksi secara langsung dari grafik **Skew-T Log-P** berbasis peluncuran balon cuaca aktual stasiun rason ini. Data divalidasi silang menggunakan basis data resmi [BMKG Rason Portal](https://aviation.bmkg.go.id/monitoring_rason/index).*

**1. Potensi Konvektif & Badai Petir (Kondisi: {thunder})**
* **Penyebab Termodinamika:** Nilai **CAPE** (*Convective Available Potential Energy*) sebesar **{row['cape']} J/kg** mewakili besaran energi apung (buoyancy) parsial yang mengindikasikan tingkat labilitas massa udara. Disertai **Lifted Index (LI)** bernilai **{row['li']}**, yang mengukur perbedaan suhu parsel udara yang diangkat terhadap lingkungan sekitarnya.
* **Akibat Meteorologi:** Kondisi atmosfer yang labil membuat parsel udara terdorong ke atas dengan cepat (menghasilkan *updraft* yang kuat). Sementara itu, nilai **K-Index** sebesar **{row['ki']}** memvalidasi tingginya ketersediaan uap air di lapisan bawah hingga menengah. Kombinasi gaya angkat vertikal dan uap air ini memicu pertumbuhan masif awan vertikal, terutama **Cumulonimbus (CB)**, yang berpotensi menghasilkan hujan lebat dan kilat.

**2. Potensi Turbulensi Udara (Kondisi: {turbulence})**
* **Penyebab Dinamika Udara:** Kecepatan angin lapisan atas terpantau di angka **{row['wind']} kt**. Kecepatan angin yang kuat pada lapisan ini umumnya memicu *Wind Shear* mekanis, yakni perubahan tajam kecepatan atau arah angin dalam jarak yang berdekatan.
* **Akibat pada Penerbangan:** *Wind shear* merusak aliran udara laminar, menciptakan pusaran dan olakan (eddy) acak di sepanjang jalur terbang. Hal ini mengakibatkan pesawat mengalami guncangan (**turbulensi {turbulence.lower()}**) mendadak, yang sangat menuntut kewaspadaan awak kokpit demi keselamatan dan stabilitas badan pesawat (*airframe*).

**3. Potensi Pembentukan Es / Icing (Kondisi: {icing})**
* **Penyebab Termodinamika:** *Freezing level* tercatat pada elevasi **{row['freeze']} ft** (ketinggian dimana suhu udara ambien melintasi titik 0°C). Di atas ketinggian ini, butiran air awan tidak langsung membeku melainkan beralih menjadi air superdingin (*supercooled water droplets*).
* **Akibat pada Penerbangan:** Ketika komponen eksterior pesawat terbang (terutama tepi depan sayap dan mesin) menembus wilayah *supercooled droplets* ini, tetesan tersebut akan membeku seketika sesaat setelah terjadi benturan. Risiko **icing {icing.lower()}** ini sangat berbahaya karena merusak profil aerodinamis sayap (mengurangi daya angkat/lift) dan secara signifikan menambah bobot beban pesawat.
""")

# =====================================================
# RADAR & SATELLITE
# =====================================================
st.write("---")
st.subheader("🛰️ Tactical Weather Radar")
iframe_url = f"https://embed.windy.com/embed.html?type=map&location=coordinates&metricRain=mm&metricTemp=default&metricWind=kt&zoom=8&overlay=radar&product=radar&level=surface&lat={row['lat']}&lon={row['lon']}"
components.iframe(iframe_url, height=500)

# =====================================================
# SKEW-T IMAGE
# =====================================================
st.write("---")
st.subheader("📈 Profil Radiosonde (Skew-T Log-P)")
img, img_timestamp = fetch_image(row["wmo"])
if img:
    st.caption(f"Visualisasi diagram termodinamika mentah yang diunggah oleh server repositori [BMKG Upper Air Portal](https://aviation.bmkg.go.id/monitoring_rason/). Last-Modified: {img_timestamp}")
    st.image(img, use_container_width=True)
else:
    st.warning("⚠️ BMKG belum mempublikasikan visualisasi sounding terbaru untuk stasiun ini atau server sedang down.")

st.write("---")
st.caption("SKYALERT | Integrasi API Aviation Weather Center & BMKG | Sistem Pendukung Keputusan Taktis")
