import streamlit as st
import pandas as pd
import requests
import folium
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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
# LOGGING
# =====================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SKYALERT")

# =====================================================
# HTTP SESSION WITH RETRY
# =====================================================

session = requests.Session()

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry_strategy)

session.mount("https://", adapter)
session.mount("http://", adapter)

# =====================================================
# STYLE
# =====================================================

st.markdown("""
<style>
.stApp { background:#06101a; color:white; }
section[data-testid="stSidebar"] { background:#0d1826; }

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
WIII,96749,Soekarno-Hatta,-6.125,106.655,500,35,-2,18000,25,31.75.01.1001
WICC,96783,Husein Sastranegara,-6.900,107.575,700,36,-2,17000,32,32.73.01.1001
WARR,96933,Juanda,-7.379,112.787,1200,40,-5,15000,45,35.78.01.1001
"""

df = pd.read_csv(StringIO(CSV_DATA))

# =====================================================
# SAFE REQUEST
# =====================================================

def safe_get(url, timeout=10):

    try:
        response = session.get(url, timeout=timeout)

        if response.status_code == 200:
            return response

    except Exception as e:
        logger.error(f"Request error: {e}")

    return None

# =====================================================
# METAR / TAF
# =====================================================

@st.cache_data(ttl=300)

def fetch_metar_taf(icao):

    data = {
        "metar": "Data tidak tersedia",
        "taf": "Data tidak tersedia"
    }

    try:

        metar_url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
        taf_url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw"

        metar_response = safe_get(metar_url)
        taf_response = safe_get(taf_url)

        if metar_response:
            text = metar_response.text.strip()
            if text:
                data["metar"] = text

        if taf_response:
            text = taf_response.text.strip()
            if text:
                data["taf"] = text

    except Exception as e:
        logger.error(f"METAR/TAF fetch error: {e}")

    return data

# =====================================================
# BMKG FORECAST API
# =====================================================

@st.cache_data(ttl=1800)

def fetch_bmkg_forecast(adm4):

    url = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={adm4}"

    response = safe_get(url)

    if not response:
        return None

    try:

        data = response.json()

        cuaca = (
            data["data"][0]["cuaca"][0][0]
        )

        return {
            "temp": cuaca.get("t"),
            "humidity": cuaca.get("hu"),
            "weather": cuaca.get("weather_desc"),
            "wind_speed": cuaca.get("ws"),
            "wind_dir": cuaca.get("wd"),
            "visibility": cuaca.get("vs"),
            "local_datetime": cuaca.get("local_datetime")
        }

    except Exception as e:
        logger.error(f"BMKG parsing error: {e}")
        return None

# =====================================================
# OBSERVATION CYCLE
# =====================================================

def get_observation_cycle():

    now_utc = datetime.now(timezone.utc)

    if now_utc.hour >= 12:
        return f"{now_utc.strftime('%Y-%m-%d')} 12:00 UTC"

    return f"{now_utc.strftime('%Y-%m-%d')} 00:00 UTC"

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

    for url in urls:

        response = safe_get(url)

        if response and len(response.content) > 1000:

            try:
                img = Image.open(BytesIO(response.content))

                timestamp = response.headers.get(
                    "Last-Modified",
                    "Unknown"
                )

                return img, timestamp

            except Exception:
                continue

    return None, "Unknown"

# =====================================================
# HAZARD ANALYSIS
# =====================================================

def analyze_weather(cape, ki, li, freeze, wind, bmkg=None):

    thunder_score = 1
    turbulence_score = 1
    icing_score = 1

    # Thunderstorm Logic
    if cape > 2500 or li < -5 or ki >= 40:
        thunder = "TINGGI"
        thunder_score = 3

    elif cape > 1000 or li < -2 or ki >= 30:
        thunder = "SEDANG"
        thunder_score = 2

    else:
        thunder = "RENDAH"

    # Turbulence
    if wind >= 40:
        turbulence = "TINGGI"
        turbulence_score = 3

    elif wind >= 25:
        turbulence = "SEDANG"
        turbulence_score = 2

    else:
        turbulence = "RENDAH"

    # Icing
    if freeze < 12000:
        icing = "TINGGI"
        icing_score = 3

    elif freeze < 16000:
        icing = "SEDANG"
        icing_score = 2

    else:
        icing = "RENDAH"

    # BMKG Surface Weather Integration
    bmkg_modifier = 0

    if bmkg:

        weather_text = str(
            bmkg.get("weather", "")
        ).lower()

        if "hujan" in weather_text:
            bmkg_modifier += 1

        if "petir" in weather_text:
            bmkg_modifier += 2

    total_score = (
        thunder_score +
        turbulence_score +
        icing_score +
        bmkg_modifier
    )

    # Final Status
    if total_score >= 8:
        status = "AWAS"
        color = "alert-awas"

    elif total_score >= 5:
        status = "SIAGA"
        color = "alert-siaga"

    else:
        status = "NORMAL"
        color = "alert-normal"

    return (
        status,
        color,
        thunder,
        turbulence,
        icing
    )

# =====================================================
# HEADER
# =====================================================

st.title("✈️ SKYALERT TNI AU")

st.caption(
    "Tactical Aviation Weather & Upper Air Monitoring"
)

# =====================================================
# SELECT STATION
# =====================================================

station = st.selectbox(
    "Pilih Lanud / Stasiun",
    df["name"]
)

row = df[df["name"] == station].iloc[0]

icao = row["icao"]
adm4 = row["adm4"]

# =====================================================
# FETCH DATA
# =====================================================

aviation_data = fetch_metar_taf(icao)

bmkg_data = fetch_bmkg_forecast(adm4)

cycle = get_observation_cycle()

(
    status,
    color,
    thunder,
    turbulence,
    icing
) = analyze_weather(
    row["cape"],
    row["ki"],
    row["li"],
    row["freeze"],
    row["wind"],
    bmkg_data
)

# =====================================================
# MAIN STATUS
# =====================================================

st.markdown(
    f"""
    <div class="{color}">
    STATUS OPERASI PENERBANGAN: {status}<br>
    <span style='font-size:16px'>
    {icao} | Radiosonde: {cycle}
    </span>
    </div>
    """,
    unsafe_allow_html=True
)

st.write("---")

# =====================================================
# METAR / TAF
# =====================================================

st.subheader("📡 Aviation Weather")

c1, c2 = st.columns(2)

with c1:
    st.markdown("### METAR")
    st.markdown(
        f"<div class='metar-text'>{aviation_data['metar']}</div>",
        unsafe_allow_html=True
    )

with c2:
    st.markdown("### TAF")
    st.markdown(
        f"<div class='metar-text'>{aviation_data['taf']}</div>",
        unsafe_allow_html=True
    )

# =====================================================
# BMKG FORECAST
# =====================================================

st.write("---")

st.subheader("🌦️ BMKG Forecast")

if bmkg_data:

    b1, b2, b3 = st.columns(3)

    b1.metric(
        "Temperature",
        f"{bmkg_data['temp']} °C"
    )

    b2.metric(
        "Humidity",
        f"{bmkg_data['humidity']} %"
    )

    b3.metric(
        "Wind",
        f"{bmkg_data['wind_speed']} km/h"
    )

    st.info(
        f"""
        Cuaca BMKG: {bmkg_data['weather']}
        
        Visibility: {bmkg_data['visibility']}
        
        Wind Direction: {bmkg_data['wind_dir']}
        """
    )

else:

    st.warning(
        "Data prakiraan BMKG tidak tersedia."
    )

# =====================================================
# UPPER AIR ANALYSIS
# =====================================================

st.write("---")

st.subheader("☁️ Atmospheric Stability")

m1, m2, m3, m4, m5 = st.columns(5)

m1.metric("CAPE", f"{row['cape']} J/kg")
m2.metric("K-Index", row["ki"])
m3.metric("Lifted Index", row["li"])
m4.metric("Freezing Level", f"{row['freeze']} ft")
m5.metric("Upper Wind", f"{row['wind']} kt")

# =====================================================
# HAZARDS
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
# RADAR
# =====================================================

st.write("---")

st.subheader("🛰️ Tactical Radar")

iframe_url = (
    f"https://embed.windy.com/embed.html?"
    f"type=map&location=coordinates"
    f"&metricWind=kt"
    f"&zoom=8"
    f"&overlay=radar"
    f"&lat={row['lat']}"
    f"&lon={row['lon']}"
)

components.iframe(
    iframe_url,
    height=500
)

# =====================================================
# SKEW-T
# =====================================================

st.write("---")

st.subheader("📈 Radiosonde Profile")

img, ts = fetch_image(row["wmo"])

if img:

    st.caption(f"BMKG Last Update: {ts}")

    st.image(
        img,
        use_container_width=True
    )

else:

    st.warning(
        "Visualisasi sounding belum tersedia."
    )

# =====================================================
# FOOTER
# =====================================================

st.write("---")

st.caption(
    "SKYALERT TNI AU | Aviation Weather Intelligence Platform"
)
