import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
from io import StringIO

# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="SKYALERT TNI AU",
    page_icon="✈️",
    layout="wide"
)

# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.stApp{
    background:#06101a;
    color:white;
}

.block{
    background:#112233;
    padding:15px;
    border-radius:12px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# CSV VALID BMKG RASON
# ICAO + WMO + LAT LON
# =========================================================

CSV_DATA = """
icao,wmo,name,lat,lon
WITT,96001,Sultan Iskandar Muda,5.523,-95.420
WIMM,96035,Kualanamu,3.642,98.885
WIBB,96109,Sultan Syarif Kasim II,0.460,101.445
WIKK,96237,Depati Amir,-2.162,106.139
WIPP,96295,Sultan Mahmud Badaruddin II,-2.898,104.699
WIII,96749,Soekarno-Hatta,-6.125,106.655
WICC,96783,Husein Sastranegara,-6.900,107.575
WAHI,96747,Yogyakarta Intl,-7.905,110.057
WARR,96933,Juanda,-7.379,112.787
WADD,97230,I Gusti Ngurah Rai,-8.748,115.167
WAAA,97180,Sultan Hasanuddin,-5.061,119.554
WAMM,97014,Sam Ratulangi,1.549,124.926
WAPP,97724,Pattimura,-3.710,128.089
WAJJ,97690,Sentani,-2.576,140.516
"""

df = pd.read_csv(StringIO(CSV_DATA))

# =========================================================
# BMKG IMAGE
# =========================================================

def get_image(wmo):

    urls = [
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.PNG",
        f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{wmo}.png"
    ]

    for url in urls:
        try:
            r = requests.get(url, timeout=8)

            if r.status_code == 200:
                return url

        except:
            pass

    return None

# =========================================================
# MAP
# =========================================================

st.title("✈️ SKYALERT TNI AU")
st.caption(
    "Upper Air Radiosonde Monitoring Indonesia | BMKG Aviation"
)

st.subheader("Peta Radiosonde Indonesia")

layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position='[lon, lat]',
    get_radius=30000,
    pickable=True
)

view = pdk.ViewState(
    latitude=-2,
    longitude=118,
    zoom=4
)

st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip={
            "text":"{icao}\n{name}"
        }
    )
)

# =========================================================
# SELECT
# =========================================================

selected = st.selectbox(
    "Pilih Stasiun Radiosonde",
    df["name"]
)

row = df[df["name"] == selected].iloc[0]

icao = row["icao"]
wmo = row["wmo"]

# =========================================================
# INFO
# =========================================================

a,b,c,d = st.columns(4)

a.metric("ICAO", icao)
b.metric("WMO", wmo)
c.metric("Lat", row["lat"])
d.metric("Lon", row["lon"])

# =========================================================
# BMKG
# =========================================================

st.subheader("Latest Radiosonde BMKG")

img = get_image(wmo)

if img:

    st.image(
        img,
        use_container_width=True
    )

else:

    st.warning(
        "Data/gambar radiosonde BMKG belum tersedia saat ini."
    )

# =========================================================
# LINK
# =========================================================

st.caption(
    "BMKG Monitoring Rason Indonesia"
)

st.markdown(
    "[Buka halaman resmi BMKG Aviation](https://aviation.bmkg.go.id/monitoring_rason/index)"
)
