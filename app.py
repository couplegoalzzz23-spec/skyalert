import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

# =====================================================
# PAGE
# =====================================================

st.set_page_config(
    page_title="SKYALERT",
    page_icon="✈️",
    layout="wide"
)

# =====================================================
# CSS
# =====================================================

st.markdown("""
<style>

.stApp{
    background:#06101a;
    color:white;
}

.alert-green{
    background:#0d402c;
    padding:15px;
    border-radius:12px;
    font-size:20px;
    font-weight:bold;
}

.alert-yellow{
    background:#5c4c00;
    padding:15px;
    border-radius:12px;
    font-size:20px;
    font-weight:bold;
}

.alert-red{
    background:#5d1717;
    padding:15px;
    border-radius:12px;
    font-size:20px;
    font-weight:bold;
}

.briefing{
    background:#132433;
    padding:18px;
    border-radius:12px;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# STATION DATA
# =====================================================

stations = [

    {
        "icao":"WIBB",
        "wmo":"96109",
        "name":"Sultan Syarif Kasim II",
        "lanud":"Pekanbaru",

        # valid screenshot BMKG
        "cape":41,
        "ki":36.9,
        "li":0.1,
        "freeze":16162,
        "wind":28
    },

    {
        "icao":"WIII",
        "wmo":"96749",
        "name":"Soekarno-Hatta",
        "lanud":"Jakarta",
        "cape":120,
        "ki":31,
        "li":-1,
        "freeze":17000,
        "wind":22
    },

    {
        "icao":"WARR",
        "wmo":"96933",
        "name":"Juanda",
        "lanud":"Surabaya",
        "cape":800,
        "ki":38,
        "li":-3,
        "freeze":17500,
        "wind":35
    }
]

df = pd.DataFrame(stations)

# =====================================================
# BMKG IMAGE
# =====================================================

def get_raob_url(wmo):

    urls = [
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.PNG",
        f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{wmo}.png",
    ]

    for url in urls:
        try:
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                return url
        except:
            pass

    return None

# =====================================================
# ANALYSIS
# =====================================================

def thunderstorm_risk(cape, ki, li):

    score = 0

    if cape > 500:
        score += 2

    elif cape > 100:
        score += 1

    if ki >= 35:
        score += 2

    elif ki >= 30:
        score += 1

    if li < -2:
        score += 2

    elif li < 0:
        score += 1

    if score <= 2:
        return "LOW"

    elif score <= 4:
        return "MODERATE"

    return "HIGH"


def icing_risk(freeze):

    if freeze < 15000:
        return "HIGH"

    elif freeze < 18000:
        return "MODERATE"

    return "LOW"


def turbulence_risk(wind):

    if wind >= 35:
        return "HIGH"

    elif wind >= 20:
        return "MODERATE"

    return "LOW"


def flight_status(ts, icing, turb):

    levels = [ts, icing, turb]

    if "HIGH" in levels:
        return "WARNING"

    elif "MODERATE" in levels:
        return "CAUTION"

    return "NORMAL"

# =====================================================
# HEADER
# =====================================================

st.title("✈️ SKYALERT")
st.caption(
    "Aviation Upper Air Early Warning Dashboard | TNI AU"
)

# =====================================================
# SIDEBAR
# =====================================================

selected = st.sidebar.selectbox(
    "Pilih Stasiun Radiosonde",
    df["name"]
)

row = df[df["name"] == selected].iloc[0]

# =====================================================
# VALUES
# =====================================================

cape = row["cape"]
ki = row["ki"]
li = row["li"]
freeze = row["freeze"]
wind = row["wind"]

ts = thunderstorm_risk(cape, ki, li)
ice = icing_risk(freeze)
turb = turbulence_risk(wind)

status = flight_status(ts, ice, turb)

# =====================================================
# MAIN ALARM
# =====================================================

if status == "NORMAL":
    st.markdown(
        '<div class="alert-green">🟢 FLIGHT STATUS NORMAL — aman untuk operasi penerbangan</div>',
        unsafe_allow_html=True
    )

elif status == "CAUTION":
    st.markdown(
        '<div class="alert-yellow">🟡 FLIGHT STATUS CAUTION — perlu kewaspadaan penerbangan</div>',
        unsafe_allow_html=True
    )

else:
    st.markdown(
        '<div class="alert-red">🔴 FLIGHT STATUS WARNING — hazard signifikan terdeteksi</div>',
        unsafe_allow_html=True
    )

# =====================================================
# METRICS
# =====================================================

a,b,c,d,e = st.columns(5)

a.metric("CAPE", f"{cape} J/kg")
b.metric("KI", ki)
c.metric("LI", li)
d.metric("Freezing", f"{freeze} ft")
e.metric("Wind", f"{wind} kt")

# =====================================================
# RISK
# =====================================================

x,y,z = st.columns(3)

x.metric("Thunderstorm Risk", ts)
y.metric("Icing Risk", ice)
z.metric("Turbulence Risk", turb)

# =====================================================
# BRIEFING
# =====================================================

st.subheader("Pilot Briefing Summary")

brief = f"""

Station : {row['name']} ({row['icao']})

• Thunderstorm : {ts}

• Icing : {ice}

• Turbulence : {turb}

• Operational Status : {status}

Kesimpulan:

Atmosfer menunjukkan potensi konveksi {ts.lower()}.
Risiko icing berada pada kategori {ice.lower()}.
Potensi turbulensi {turb.lower()}.

Rekomendasi:
Laksanakan monitoring lanjutan sebelum departure / training flight.
"""

st.markdown(
    f'<div class="briefing">{brief}</div>',
    unsafe_allow_html=True
)

# =====================================================
# IMAGE
# =====================================================

st.subheader("Latest Radiosonde BMKG")

img = get_raob_url(row["wmo"])

if img:
    st.image(
        img,
        use_container_width=True
    )
else:
    st.info(
        "Gambar radiosonde BMKG belum tersedia."
    )

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "SKYALERT | BMKG Upper Air + Aviation Hazard Decision Support"
)
