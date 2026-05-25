import streamlit as st
import pandas as pd
import requests
import os
import re
import urllib3
from io import StringIO, BytesIO
from PIL import Image
from datetime import datetime, timezone
import streamlit.components.v1 as components

# Matikan peringatan SSL (Sering bermasalah di web pemerintah)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

# HEADER BROWSER SUPER LENGKAP (Menyamar sebagai browser asli)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive'
}

# =====================================================
# STATION DATA & KODE WILAYAH LOADER
# =====================================================
CSV_DATA = """
icao,wmo,name,lat,lon,cape,ki,li,freeze,wind,adm4
WITT,96001,Sultan Iskandar Muda,5.523,95.420,850,37,-3,16000,35,11.71.02.2001
WIMM,96035,Kualanamu,3.642,98.885,620,35,-2,16500,28,12.07.24.2001
WIBB,96109,Sultan Syarif Kasim II,0.460,101.445,44,32.9,-1.5,16327,44,14.71.03.1001
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

def load_data():
    return pd.read_csv(StringIO(CSV_DATA.strip()))

@st.cache_data(ttl=3600)
def load_wilayah_data():
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
    return pd.DataFrame()

df = load_data()

# =====================================================
# REAL-TIME DATA FETCHERS
# =====================================================
@st.cache_data(ttl=300)
def fetch_metar_taf(icao):
    data = {"metar": "Data tidak tersedia", "taf": "Data tidak tersedia"}
    try:
        req_metar = requests.get(f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw", headers=HEADERS, timeout=5, verify=False)
        if req_metar.status_code == 200 and req_metar.text.strip():
            data["metar"] = req_metar.text.strip()
            
        req_taf = requests.get(f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw", headers=HEADERS, timeout=5, verify=False)
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
        response = requests.get(url, headers=HEADERS, timeout=8, verify=False)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

# FUNGSI INI DIBUANG CACHE-NYA AGAR MEMAKSA TARIK DATA BARU TERUS & ADA DEBUGGING
def fetch_rason_data(wmo):
    urls = [
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.TXT",
        f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{wmo}.TXT",
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.txt",
        f"https://aviation.bmkg.go.id/monitoring_rason/data/LATEST_TEMP_{wmo}.TXT"
    ]
    
    debug_info = "Memulai penarikan...\n"
    
    for url in urls:
        try:
            debug_info += f"Mencoba URL: {url}\n"
            resp = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            
            if resp.status_code == 200:
                txt = resp.text
                if "CAPE" in txt or "RAOB" in txt or "Station" in txt:
                    c = re.search(r'CAPE\s*(?:total)?\s*[:=]\s*([\d\.]+)', txt, re.IGNORECASE)
                    k = re.search(r'\bKI\s*[:=]\s*([-\d\.]+)', txt, re.IGNORECASE)
                    l = re.search(r'\bLI\s*[:=]\s*([-\d\.]+)', txt, re.IGNORECASE)
                    f = re.search(r'(?:FRZG\s*Lvl|Freezing\s*Level)\s*[:=]\s*([\d\.]+)', txt, re.IGNORECASE)
                    w = re.search(r'(?:MVV|Max\s*Wind)\s*[:=]\s*([\d\.]+)', txt, re.IGNORECASE)
                    
                    return {
                        "cape": float(c.group(1)) if c else None,
                        "ki": float(k.group(1)) if k else None,
                        "li": float(l.group(1)) if l else None,
                        "freeze": float(f.group(1)) if f else None,
                        "wind": float(w.group(1)) if w else None,
                        "is_live": True,
                        "debug": "Sukses"
                    }
                else:
                    debug_info += "Status 200 OK, tapi teks 'CAPE' tidak ditemukan di dalam respons BMKG.\n"
                    debug_info += f"Cuplikan Teks yang didapat: {txt[:200]}\n\n"
            else:
                debug_info += f"Gagal. Status Code: {resp.status_code}\n"
        except Exception as e:
            debug_info += f"Error: {str(e)}\n"
            
    return {"cape": None, "ki": None, "li": None, "freeze": None, "wind": None, "is_live": False, "debug": debug_info}

@st.cache_data(ttl=300)
def fetch_image(wmo):
    urls = [
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.PNG",
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.png",
    ]
    timestamp = "Timestamp tidak diketahui"
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
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
    try:
        cape, ki, li, freeze, wind = float(cape), float(ki), float(li), float(freeze), float(wind)
    except (ValueError, TypeError):
        return "TIDAK TERSEDIA", "alert-normal", "N/A", "N/A", "N/A"

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

# EKSTRAKSI DATA REAL-TIME BMKG DENGAN DETEKSI ERROR BARU
rason_live = fetch_rason_data(row["wmo"])

if rason_live["is_live"]:
    c_val = rason_live["cape"] if rason_live["cape"] is not None else row["cape"]
    k_val = rason_live["ki"] if rason_live["ki"] is not None else row["ki"]
    l_val = rason_live["li"] if rason_live["li"] is not None else row["li"]
    f_val = rason_live["freeze"] if rason_live["freeze"] is not None else row["freeze"]
    w_val = rason_live["wind"] if rason_live["wind"] is not None else row["wind"]
    data_source_msg = f"🟢 **Real-Time Data Valid:** Diekstrak langsung dari log parameter BMKG (WMO {row['wmo']})."
else:
    c_val, k_val, l_val, f_val, w_val = row["cape"], row["ki"], row["li"], row["freeze"], row["wind"]
    data_source_msg = f"🟠 **Peringatan Fallback:** Gagal mengekstrak log real-time LATEST_TEMP. Menampilkan data fallback."

# PROSES ANALISIS 
status, color, thunder, turbulence, icing = analyze_weather(c_val, k_val, l_val, f_val, w_val)

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

if not df_wilayah.empty:
    try:
        default_index = df_wilayah.index[df_wilayah['kode'] == default_adm4].tolist()[0]
    except IndexError:
        default_index = 0
        
    with c_cari1:
        selected_label = st.selectbox("📍 Pilih Wilayah Prakiraan BMKG:", df_wilayah['label'], index=default_index)
    selected_adm4 = selected_label.split("(")[-1].replace(")", "").strip()
else:
    df['label_lanud'] = df['name'] + " (" + df['adm4'] + ")"
    default_index = df.index[df['name'] == station].tolist()[0]
    
    with c_cari1:
        selected_label = st.selectbox("📍 Pilih Wilayah Prakiraan BMKG:", df['label_lanud'], index=default_index)
    selected_adm4 = selected_label.split("(")[-1].replace(")", "").strip()

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
st.caption(f"📊 Sumber Data: {data_source_msg}")

# KOTAK DEBUGGING (Akan muncul jika fallback menyala)
if not rason_live["is_live"]:
    with st.expander("🛠️ LIHAT ERROR LOG SERVER BMKG (Klik di sini)"):
        st.text(rason_live["debug"])
        st.warning("Jika terbaca 'Status 403', artinya IP Anda diblokir oleh sistem anti-DDoS BMKG. Jika terbaca 'Timeout', server BMKG sedang down.")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("CAPE (Energi Konvektif)", f"{c_val} J/kg")
c2.metric("K-Index", k_val)
c3.metric("Lifted Index", l_val)
c4.metric("Freezing Level", f"{f_val} ft")
c5.metric("Upper Wind", f"{w_val} kt")

h1, h2, h3 = st.columns(3)
h1.markdown(f"<div class='block'><h3>⛈️ Thunderstorm</h3><h1>{thunder}</h1></div>", unsafe_allow_html=True)
h2.markdown(f"<div class='block'><h3>🌪️ Turbulence</h3><h1>{turbulence}</h1></div>", unsafe_allow_html=True)
h3.markdown(f"<div class='block'><h3>❄️ Icing</h3><h1>{icing}</h1></div>", unsafe_allow_html=True)

# PENGKONDISIAN TEKS DINAMIS 
if thunder == "TINGGI":
    t_sebab = f"Nilai CAPE ekstrem ({c_val} J/kg) dipadukan dengan LI yang sangat labil ({l_val}). K-Index ({k_val}) menyuplai uap air melimpah."
    t_akibat = "Sangat mendukung formasi masif awan Cumulonimbus (CB). Waspadai hujan lebat, kilat intens, dan potensi microburst."
elif thunder == "SEDANG":
    t_sebab = f"Meskipun CAPE tercatat {c_val} J/kg, K-Index ({k_val}) mengindikasikan adanya uap air yang cukup untuk memicu ketidakstabilan parsial."
    t_akibat = "Memicu pertumbuhan awan konvektif tingkat sedang. Terdapat potensi badai petir terisolasi."
else:
    t_sebab = f"Nilai CAPE minim ({c_val} J/kg) dengan tingkat labilitas (LI {l_val}) yang tidak signifikan."
    t_akibat = "Gaya angkat vertikal (updraft) gagal terbentuk. Atmosfer stabil, membatasi pertumbuhan awan vertikal."

if turbulence == "TINGGI":
    turb_sebab = f"Kecepatan angin lapisan atas terpantau sangat kuat di angka {w_val} kt."
    turb_akibat = "Berpotensi memicu Wind Shear mekanis parah. Guncangan turbulensi dapat mengganggu kestabilan airframe."
elif turbulence == "SEDANG":
    turb_sebab = f"Angin lapisan atas terpantau berada di kecepatan moderat ({w_val} kt)."
    turb_akibat = "Terdapat gangguan pada aliran laminar. Pesawat berpotensi mengalami guncangan tingkat sedang mendadak."
else:
    turb_sebab = f"Kecepatan angin lapisan atas tergolong terkendali ({w_val} kt)."
    turb_akibat = "Aliran udara di jalur terbang cenderung laminar. Risiko wind shear dan turbulensi sangat minim."

if icing == "TINGGI":
    ice_sebab = f"Titik beku (Freezing level) turun drastis hingga elevasi {f_val} ft."
    ice_akibat = "Risiko paparan supercooled water droplets sangat kritis. Tetesan air akan membeku saat menabrak tepian sayap (structural icing)."
elif icing == "SEDANG":
    ice_sebab = f"Freezing level merambah level menengah penerbangan operasional ({f_val} ft)."
    ice_akibat = "Waspadai potensi icing moderat apabila beroperasi menembus sel awan tebal di sekitar elevasi tersebut."
else:
    ice_sebab = f"Freezing level berada di batas aman pada elevasi {f_val} ft."
    ice_akibat = "Mayoritas penerbangan taktis di level rendah terlindungi. Risiko ancaman penumpukan es sangat rendah."

st.info(f"""
### 💡 Interpretasi Taktis & Analisis Termodinamika
**STATUS PERINGATAN UMUM: {status}**

**1. Potensi Konvektif & Badai Petir (Kondisi: {thunder})**
* **Penyebab Termodinamika:** {t_sebab}
* **Akibat Meteorologi:** {t_akibat}

**2. Potensi Turbulensi Udara (Kondisi: {turbulence})**
* **Penyebab Dinamika Udara:** {turb_sebab}
* **Akibat pada Penerbangan:** {turb_akibat}

**3. Potensi Pembentukan Es / Icing (Kondisi: {icing})**
* **Penyebab Termodinamika:** {ice_sebab}
* **Akibat pada Penerbangan:** {ice_akibat}
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
