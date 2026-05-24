import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="SKYALERT",
    page_icon="✈️",
    layout="wide"
)

# =====================================================
# CSS
# =====================================================

st.markdown(
    """
    <style>

    .stApp{
        background:#08111c;
        color:white;
    }

    h1,h2,h3{
        color:#00e5ff;
    }

    div[data-testid="metric-container"]{
        background:#13212f;
        border:1px solid #284154;
        padding:10px;
        border-radius:12px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =====================================================
# DATA RASON BMKG
# disesuaikan WMO + ICAO
# =====================================================

stations = [
    {
        "icao":"WIII",
        "wmo":"96749",
        "name":"Soekarno-Hatta",
        "lanud":"Jakarta"
    },
    {
        "icao":"WIBB",
        "wmo":"96109",
        "name":"Sultan Syarif Kasim II",
        "lanud":"Pekanbaru"
    },
    {
        "icao":"WICC",
        "wmo":"96783",
        "name":"Husein Sastranegara",
        "lanud":"Bandung"
    },
    {
        "icao":"WARR",
        "wmo":"96933",
        "name":"Juanda",
        "lanud":"Surabaya"
    },
    {
        "icao":"WADD",
        "wmo":"97230",
        "name":"Ngurah Rai",
        "lanud":"Bali"
    },
    {
        "icao":"WAAA",
        "wmo":"97180",
        "name":"Sultan Hasanuddin",
        "lanud":"Makassar"
    },
    {
        "icao":"WIMM",
        "wmo":"96035",
        "name":"Kualanamu",
        "lanud":"Medan"
    },
    {
        "icao":"WAPP",
        "wmo":"98433",
        "name":"Frans Kaisiepo",
        "lanud":"Biak"
    },
]

df = pd.DataFrame(stations)

# =====================================================
# BMKG RASON IMAGE URL
# =====================================================

def get_raob_url(wmo):

    candidates = [
        f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{wmo}.png",
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.PNG",
        f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{wmo}.PNG",
    ]

    for url in candidates:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return url
        except:
            pass

    return None

# =====================================================
# SAMPLE HAZARD RULE
# nanti bisa parsing otomatis
# =====================================================

def cape_status(v):

    if v < 100:
        return "LOW"

    elif v < 1000:
        return "MODERATE"

    return "HIGH"


def ki_status(v):

    if v < 25:
        return "LOW"

    elif v < 35:
        return "MODERATE"

    return "HIGH"


# =====================================================
# HEADER
# =====================================================

st.title("✈️ SKYALERT")
st.caption(
    "Aviation Upper Air Monitoring & Hazard Alert Dashboard | TNI AU"
)

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Station Selector")

selected = st.sidebar.selectbox(
    "Pilih Stasiun Radiosonde",
    df["name"].tolist()
)

row = df[df["name"] == selected].iloc[0]

icao = row["icao"]
wmo = row["wmo"]
lanud = row["lanud"]

# =====================================================
# TOP INFO
# =====================================================

a, b, c, d = st.columns(4)

with a:
    st.metric("ICAO", icao)

with b:
    st.metric("WMO", wmo)

with c:
    st.metric("LANUD", lanud)

with d:
    jakarta = timezone(timedelta(hours=7))
    now = datetime.now(jakarta)
    st.metric(
        "Update WIB",
        now.strftime("%H:%M")
    )

# =====================================================
# SAMPLE PARAMETER
# default aman
# =====================================================

cape = 41
ki = 36.9
li = 0.1
freeze = 16162

# =====================================================
# METRICS
# =====================================================

st.subheader("Atmospheric Stability")

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("CAPE", f"{cape} J/kg")

with m2:
    st.metric("KI", ki)

with m3:
    st.metric("LI", li)

with m4:
    st.metric("Freezing", f"{freeze} ft")

# =====================================================
# ALERT
# =====================================================

st.subheader("Aviation Hazard Alert")

if cape_status(cape) == "LOW":
    st.success(
        "CAPE rendah → thunderstorm minimal"
    )

elif cape_status(cape) == "MODERATE":
    st.warning(
        "CAPE sedang → convection possible"
    )

else:
    st.error(
        "CAPE tinggi → severe convection"
    )

if ki_status(ki) == "HIGH":
    st.warning(
        "K Index tinggi → pertumbuhan CB memungkinkan"
    )

if freeze < 18000:
    st.info(
        "Freezing level rendah → icing risk"
    )

# =====================================================
# IMAGE
# =====================================================

st.subheader("Latest Radiosonde BMKG")

img = get_raob_url(wmo)

if img:
    st.image(
        img,
        use_container_width=True
    )
else:
    st.warning(
        "Image radiosonde BMKG belum tersedia untuk stasiun ini."
    )

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "SKYALERT • TNI AU Aviation Meteorology • BMKG Radiosonde Monitoring"
)
