import streamlit as st
import pandas as pd
import requests
import folium
import re

from streamlit_folium import st_folium
from io import StringIO, BytesIO
from PIL import Image
from datetime import datetime, timezone, timedelta

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

.stApp{
    background:#06101a;
    color:white;
}

section[data-testid="stSidebar"]{
    background:#0d1826;
}

.block{
    background:#132433;
    padding:18px;
    border-radius:14px;
    margin-bottom:15px;
}

.alert-normal{
    background:#0d402c;
    padding:18px;
    border-radius:14px;
    font-size:24px;
    font-weight:bold;
    color:white;
}

.alert-siaga{
    background:#7a5a00;
    padding:18px;
    border-radius:14px;
    font-size:24px;
    font-weight:bold;
    color:white;
}

.alert-awas{
    background:#7d1010;
    padding:18px;
    border-radius:14px;
    font-size:24px;
    font-weight:bold;
    color:white;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# STATION DATA
# =====================================================

CSV_DATA = """
icao,wmo,name,lat,lon,cape,ki,li,freeze,wind
WITT,96001,Sultan Iskandar Muda,5.523,95.420,850,37,-3,16000,35
WIMM,96035,Kualanamu,3.642,98.885,620,35,-2,16500,28
WIBB,96109,Sultan Syarif Kasim II,0.460,101.445,41,36.9,0.1,16162,28
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
# HELPERS
# =====================================================

HEADERS = {
    "User-Agent":"Mozilla/5.0"
}

@st.cache_data(ttl=300)
def fetch_image(wmo):

    urls = [
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.PNG",
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.png",
    ]

    for url in urls:
        try:
            r = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

            if r.status_code == 200 and len(r.content) > 1000:
                img = Image.open(BytesIO(r.content))
                return img

        except:
            continue

    return None

@st.cache_data(ttl=300)
def fetch_metar_taf(icao):

    metar = None
    taf = None

    try:
        url = f"https://aviationweather.gov/data/metar/?ids={icao}&taf=1"
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=10
        )

        txt = r.text

        metar_match = re.search(
            rf"{icao}\s+\d{{6}}Z.*",
            txt
        )

        taf_match = re.search(
            rf"TAF\s+{icao}.*",
            txt,
            re.DOTALL
        )

        if metar_match:
            metar = metar_match.group(0)

        if taf_match:
            taf = taf_match.group(0)

    except:
        pass

    return metar, taf

# =====================================================
# ANALYSIS
# =====================================================

def analyze_weather(row, metar, taf):

    cape = row["cape"]
    ki = row["ki"]
    li = row["li"]
    freeze = row["freeze"]
    wind = row["wind"]

    score = 0

    if cape > 1000:
        score += 3
    elif cape > 500:
        score += 2

    if ki >= 38:
        score += 3
    elif ki >= 35:
        score += 2

    if li <= -4:
        score += 3
    elif li <= -2:
        score += 2

    if wind >= 40:
        score += 3
    elif wind >= 30:
        score += 2

    # METAR weather cues

    if metar:
        if "TS" in metar:
            score += 2

        if "CB" in metar:
            score += 2

    if taf:
        if "TS" in taf:
            score += 2

    # icing

    icing = "RENDAH"

    if freeze < 15000:
        icing = "TINGGI"

    elif freeze < 18000:
        icing = "SEDANG"

    # thunder

    if score >= 9:
        thunder = "TINGGI"
    elif score >= 5:
        thunder = "SEDANG"
    else:
        thunder = "RENDAH"

    # turbulence

    if wind >= 40:
        turbulence = "TINGGI"
    elif wind >= 30:
        turbulence = "SEDANG"
    else:
        turbulence = "RENDAH"

    # final

    if score >= 9:
        status = "AWAS"
        color = "alert-awas"

    elif score >= 5:
        status = "SIAGA"
        color = "alert-siaga"

    else:
        status = "NORMAL"
        color = "alert-normal"

    return status, color, thunder, turbulence, icing

# =====================================================
# HEADER
# =====================================================

st.title("✈️ SKYALERT TNI AU")
st.caption("Upper Air Radiosonde Monitoring Indonesia | BMKG Aviation")

# =====================================================
# SELECT
# =====================================================

station = st.selectbox(
    "Pilih Stasiun Radiosonde",
    df["name"]
)

row = df[df["name"] == station].iloc[0]

# =====================================================
# LIVE DATA
# =====================================================

metar, taf = fetch_metar_taf(row["icao"])

status, color, thunder, turbulence, icing = analyze_weather(
    row,
    metar,
    taf
)

# =====================================================
# TIMESTAMP
# =====================================================

utc_now = datetime.now(timezone.utc)
wib = utc_now + timedelta(hours=7)

st.caption(
    f"OBS UTC: {utc_now:%d %b %Y %H:%MZ} | WIB: {wib:%d %b %Y %H:%M}"
)

# =====================================================
# ALERT
# =====================================================

st.markdown(
    f"""
    <div class="{color}">
    STATUS OPERASI PENERBANGAN : {status}
    </div>
    """,
    unsafe_allow_html=True
)

# =====================================================
# MAP
# =====================================================

st.subheader("Peta Radiosonde Indonesia")

m = folium.Map(
    location=[-2.5,118],
    zoom_start=5,
    tiles="CartoDB dark_matter"
)

for _, r in df.iterrows():

    color_marker = "#00d4ff"

    if r["name"] == station:
        color_marker = "#ffcc00"

    folium.CircleMarker(
        location=[r["lat"], r["lon"]],
        radius=8,
        color=color_marker,
        fill=True,
        fill_color=color_marker,
        popup=f"{r['icao']} | {r['name']}"
    ).add_to(m)

st_folium(m, height=420)

# =====================================================
# METRICS
# =====================================================

st.subheader("Analisis Radiosonde")

c1,c2,c3,c4,c5 = st.columns(5)

c1.metric("ICAO", row["icao"])
c2.metric("CAPE", f"{row['cape']} J/kg")
c3.metric("KI", row["ki"])
c4.metric("LI", row["li"])
c5.metric("Wind", f"{row['wind']} kt")

# =====================================================
# HAZARD
# =====================================================

h1,h2,h3 = st.columns(3)

with h1:
    st.markdown(
        f"<div class='block'><h3>⛈ Thunderstorm</h3><h1>{thunder}</h1></div>",
        unsafe_allow_html=True
    )

with h2:
    st.markdown(
        f"<div class='block'><h3>🌪 Turbulence</h3><h1>{turbulence}</h1></div>",
        unsafe_allow_html=True
    )

with h3:
    st.markdown(
        f"<div class='block'><h3>❄ Icing</h3><h1>{icing}</h1></div>",
        unsafe_allow_html=True
    )

# =====================================================
# METAR TAF
# =====================================================

st.subheader("METAR / TAF")

if metar:
    st.code(metar)

if taf:
    st.code(taf)

# =====================================================
# SOUNDING
# =====================================================

st.subheader("Latest Radiosonde BMKG")

img = fetch_image(row["wmo"])

if img:
    st.image(
        img,
        use_container_width=True
    )
else:
    st.warning(
        "BMKG belum mempublikasikan sounding terbaru."
    )

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "SKYALERT | BMKG Upper Air + Aviation Decision Support | TNI AU"
)
