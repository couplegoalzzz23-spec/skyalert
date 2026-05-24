import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from io import StringIO, BytesIO
from PIL import Image
from datetime import datetime, timezone
import streamlit.components.v1 as components
import json

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

section[data-testid="stSidebar"] {
    background:#0d1826;
}

.block {
    background:#132433;
    padding:18px;
    border-radius:14px;
    margin-bottom:15px;
}

.alert-normal {
    background:#0d402c;
    padding:18px;
    border-radius:14px;
    font-size:24px;
    font-weight:bold;
    color:white;
    text-align:center;
}

.alert-siaga {
    background:#7a5a00;
    padding:18px;
    border-radius:14px;
    font-size:24px;
    font-weight:bold;
    color:white;
    text-align:center;
}

.alert-awas {
    background:#7d1010;
    padding:18px;
    border-radius:14px;
    font-size:24px;
    font-weight:bold;
    color:white;
    text-align:center;
}

.metric-card {
    background:#132433;
    padding:15px;
    border-radius:12px;
}

.metar-text {
    font-family: monospace;
    background: #000;
    padding: 10px;
    border-radius: 5px;
    color: #00ff00;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# STATION DATA
# =====================================================

CSV_DATA = """
icao,wmo,name,lat,lon,cape,ki,li,freeze,wind,adm4
WITT,96001,Sultan Iskandar Muda,5.523,95.420,850,37,-3,16000,35,11.71.01.1001
WIMM,96035,Kualanamu,3.642,98.885,620,35,-2,16500,28,12.71.01.1001
WIBB,96109,Sultan Syarif Kasim II,0.460,101.445,1800,38.5,-4.2,16162,28,14.71.01.1001
WIKK,96237,Depati Amir,-2.162,106.139,300,32,-1,17000,20,19.71.01.1001
WIPP,96295,Sultan Mahmud Badaruddin II,-2.898,104.699,450,34,-1,17500,24,16.71.01.1001
WIII,96749,Soekarno-Hatta,-6.125,106.655,500,35,-2,18000,25,31.75.01.1001
WICC,96783,Husein Sastranegara,-6.900,107.575,700,36,-2,17000,32,32.73.01.1001
WAHI,96747,Yogyakarta International,-7.905,110.057,950,38,-4,15500,40,34.71.01.1001
WARR,96933,Juanda,-7.379,112.787,1200,40,-5,15000,45,35.78.01.1001
WADD,97230,I Gusti Ngurah Rai,-8.748,115.167,350,31,-1,18500,20,51.71.01.1001
WAAA,97180,Sultan Hasanuddin,-5.061,119.554,750,37,-3,16000,34,73.71.01.1001
WAMM,97014,Sam Ratulangi,1.549,124.926,400,33,-1,18000,26,71.71.01.1001
WAPP,97724,Pattimura,-3.710,128.089,680,35,-2,17000,30,81.71.01.1001
WAJJ,97690,Sentani,-2.576,140.516,1100,39,-4,14500,42,94.71.01.1001
"""

df = pd.read_csv(StringIO(CSV_DATA))

# =====================================================
# REAL-TIME DATA FETCHERS
# =====================================================

@st.cache_data(ttl=300)
def fetch_metar_taf(icao):
    """
    Mengambil data METAR dan TAF real-time
    """

    data = {
        "metar": "Data tidak tersedia",
        "taf": "Data tidak tersedia"
    }

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

# =====================================================
# BMKG FORECAST API
# =====================================================

@st.cache_data(ttl=1800)
def fetch_bmkg_forecast(adm4):
    """
    Mengambil prakiraan cuaca BMKG
    """

    url = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={adm4}"

    try:

        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()

        cuaca = data["data"][0]["cuaca"][0][0]

        return {
            "temp": cuaca.get("t"),
            "humidity": cuaca.get("hu"),
            "weather": cuaca.get("weather_desc"),
            "wind_speed": cuaca.get("ws"),
            "wind_dir": cuaca.get("wd"),
            "visibility": cuaca.get("vs"),
            "datetime": cuaca.get("local_datetime")
        }

    except Exception:
        return None

# =====================================================
# OBSERVATION CYCLE
# =====================================================

def get_observation_cycle():

    now_utc = datetime.now(timezone.utc)

    if now_utc.hour >= 12:
        cycle = f"{now_utc.strftime('%Y-%m-%d')} 12:00 UTC"
    else:
        cycle = f"{now_utc.strftime('%Y-%m-%d')} 00:00 UTC"

    return cycle

# =====================================================
# FETCH SKEW-T IMAGE
# =====================================================

@st.cache_data(ttl=3600)
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

def analyze_weather(cape, ki, li, freeze, wind, bmkg_weather=None):

    # Thunderstorm
    if cape > 2500 or li < -5 or ki >= 40:
        thunder = "TINGGI"
        thunder_score = 3

    elif cape > 1000 or li < -2 or ki >= 30:
        thunder = "SEDANG"
        thunder_score = 2

    else:
        thunder = "RENDAH"
        thunder_score = 1

    # Turbulence
    if wind >= 40:
        turbulence = "TINGGI"
        turb_score = 3

    elif wind >= 25:
        turbulence = "SEDANG"
        turb_score = 2

    else:
        turbulence = "RENDAH"
        turb_score = 1

    # Icing
    if freeze < 12000:
        icing = "TINGGI"
        ice_score = 3

    elif freeze < 16000:
        icing = "SEDANG"
        ice_score = 2

    else:
        icing = "RENDAH"
        ice_score = 1

    # BMKG Modifier
    bmkg_modifier = 0

    if bmkg_weather:

        weather_text = str(bmkg_weather).lower()

        if "hujan" in weather_text:
            bmkg_modifier += 1

        if "petir" in weather_text:
            bmkg_modifier += 2

    # Final Score
    total_score = thunder_score + turb_score + ice_score + bmkg_modifier

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

st.caption(
    "Tactical Aviation Weather & Upper Air Monitoring | Sistem Pendukung Keputusan Operasional"
)

# =====================================================
# SELECT STATION
# =====================================================

c_sel1, c_sel2 = st.columns([1, 2])

with c_sel1:
    station = st.selectbox(
        "Pilih Lanud / Stasiun Observasi",
        df["name"]
    )

row = df[df["name"] == station].iloc[0]

icao_code = row["icao"]
adm4_code = row["adm4"]

# =====================================================
# FETCH REAL-TIME DATA
# =====================================================

aviation_data = fetch_metar_taf(icao_code)

bmkg_data = fetch_bmkg_forecast(adm4_code)

cycle_time = get_observation_cycle()

status, color, thunder, turbulence, icing = analyze_weather(
    row["cape"],
    row["ki"],
    row["li"],
    row["freeze"],
    row["wind"],
    bmkg_data["weather"] if bmkg_data else None
)

# =====================================================
# MAIN ALERT
# =====================================================

st.markdown(
    f"""
    <div class="{color}">
    STATUS OPERASI PENERBANGAN: {status}<br>
    <span style='font-size:16px; font-weight:normal;'>
    {icao_code} - Siklus Radiosonde: {cycle_time}
    </span>
    </div>
    """,
    unsafe_allow_html=True
)

st.write("---")

# =====================================================
# METAR & TAF
# =====================================================

st.subheader(f"📡 Real-time Surface Observation ({icao_code})")

col_metar, col_taf = st.columns(2)

with col_metar:

    st.markdown("**METAR (Aktual):**")

    st.markdown(
        f"<div class='metar-text'>{aviation_data['metar']}</div>",
        unsafe_allow_html=True
    )

with col_taf:

    st.markdown("**TAF (Prakiraan):**")

    st.markdown(
        f"<div class='metar-text'>{aviation_data['taf']}</div>",
        unsafe_allow_html=True
    )

# =====================================================
# BMKG FORECAST
# =====================================================

st.write("---")

st.subheader("🌦️ Prakiraan Cuaca BMKG")

if bmkg_data:

    b1, b2, b3 = st.columns(3)

    with b1:
        st.metric("Temperature", f"{bmkg_data['temp']} °C")

    with b2:
        st.metric("Humidity", f"{bmkg_data['humidity']} %")

    with b3:
        st.metric("Wind", f"{bmkg_data['wind_speed']} km/h")

    st.info(
        f"""
        **Cuaca:** {bmkg_data['weather']}

        **Visibility:** {bmkg_data['visibility']}

        **Wind Direction:** {bmkg_data['wind_dir']}

        **Forecast Time:** {bmkg_data['datetime']}
        """
    )

else:

    st.warning("⚠️ Data prakiraan BMKG tidak tersedia.")

# =====================================================
# UPPER AIR ANALYSIS
# =====================================================

st.write("---")

st.subheader("☁️ Analisis Stabilitas Atmosfer (Radiosonde)")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("CAPE (Energi Konvektif)", f"{row['cape']} J/kg")
c2.metric("K-Index (Potensi Badai)", row["ki"])
c3.metric("Lifted Index (LI)", row["li"])
c4.metric("Freezing Level", f"{row['freeze']} ft")
c5.metric("Upper Wind", f"{row['wind']} kt")

# =====================================================
# HAZARD
# =====================================================

st.write("")

h1, h2, h3 = st.columns(3)

with h1:
    st.markdown(
        f"<div class='block'><h3>⛈️ Thunderstorm</h3><h1>{thunder}</h1></div>",
        unsafe_allow_html=True
    )

with h2:
    st.markdown(
        f"<div class='block'><h3>🌪️ Turbulence</h3><h1>{turbulence}</h1></div>",
        unsafe_allow_html=True
    )

with h3:
    st.markdown(
        f"<div class='block'><h3>❄️ Icing</h3><h1>{icing}</h1></div>",
        unsafe_allow_html=True
    )

# =====================================================
# INTERPRETATION & RECOMMENDATION
# =====================================================

summary = f"""
### 💡 Interpretasi Taktis

Data observasi permukaan (METAR), prakiraan BMKG, dan profil atmosfer atas menunjukkan kondisi konveksi **{thunder.lower()}**.

* **Termodinamika:** Nilai CAPE ({row['cape']} J/kg) dan LI ({row['li']}) mengindikasikan tingkat labilitas udara saat ini.

* **Konveksi:** K-Index di angka {row['ki']} merepresentasikan probabilitas pertumbuhan awan Cumulonimbus (CB).

* **Angin & Temperatur:** Kecepatan angin lapisan atas ({row['wind']} kt) memicu potensi turbulensi **{turbulence.lower()}**.

* **Icing Risk:** Waspadai level pembekuan pada {row['freeze']} ft.

* **BMKG Forecast:** Kondisi prakiraan lokal BMKG menunjukkan cuaca: **{bmkg_data['weather'] if bmkg_data else 'Tidak tersedia'}**

### 📋 Rekomendasi Operasional Militer

1. Validasi TAF dengan radar cuaca dan observasi visual.
2. Hindari area konvektif aktif saat CAPE tinggi.
3. Briefing aircrew terkait icing dan turbulence wajib dilakukan.
4. Pantau perkembangan cuaca BMKG secara periodik.
"""

st.info(summary)

# =====================================================
# RADAR & SATELLITE
# =====================================================

st.write("---")

st.subheader("🛰️ Tactical Weather Radar")

st.caption(
    "Peta cuaca interaktif berpusat pada koordinat Lanud."
)

iframe_url = f"https://embed.windy.com/embed.html?type=map&location=coordinates&metricRain=mm&metricTemp=default&metricWind=kt&zoom=8&overlay=radar&product=radar&level=surface&lat={row['lat']}&lon={row['lon']}"

components.iframe(
    iframe_url,
    height=500
)

# =====================================================
# SKEW-T IMAGE
# =====================================================

st.write("---")

st.subheader("📈 Profil Radiosonde (Skew-T Log-P)")

img, img_timestamp = fetch_image(row["wmo"])

if img:

    st.caption(
        f"Server BMKG Last-Modified: {img_timestamp}"
    )

    st.image(
        img,
        use_container_width=True
    )

else:

    st.warning(
        "⚠️ BMKG belum mempublikasikan visualisasi sounding terbaru untuk stasiun ini atau server sedang down."
    )

# =====================================================
# FOOTER
# =====================================================

st.write("---")

st.caption(
    "SKYALERT | Integrasi API Aviation Weather Center + BMKG Forecast API + BMKG Upper Air"
)
