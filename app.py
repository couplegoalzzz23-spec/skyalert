import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from io import StringIO
from PIL import Image
from io import BytesIO

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
}

.metric{
    background:#132433;
    padding:16px;
    border-radius:14px;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# VALID BMKG RASON
# =====================================================

CSV_DATA = """
icao,wmo,name,lat,lon
WITT,96001,Sultan Iskandar Muda,5.523,95.420
WIMM,96035,Kualanamu,3.642,98.885
WIBB,96109,Sultan Syarif Kasim II,0.460,101.445
WIKK,96237,Depati Amir,-2.162,106.139
WIPP,96295,Sultan Mahmud Badaruddin II,-2.898,104.699
WIII,96749,Soekarno-Hatta,-6.125,106.655
WICC,96783,Husein Sastranegara,-6.900,107.575
WAHI,96747,Yogyakarta International,-7.905,110.057
WARR,96933,Juanda,-7.379,112.787
WADD,97230,I Gusti Ngurah Rai,-8.748,115.167
WAAA,97180,Sultan Hasanuddin,-5.061,119.554
WAMM,97014,Sam Ratulangi,1.549,124.926
WAPP,97724,Pattimura,-3.710,128.089
WAJJ,97690,Sentani,-2.576,140.516
"""

df = pd.read_csv(StringIO(CSV_DATA))

# =====================================================
# BMKG IMAGE FETCH
# =====================================================

def fetch_image(wmo):

    urls = [

        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.PNG",
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.png",
        f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{wmo}.PNG",
        f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{wmo}.png",
    ]

    for url in urls:

        try:
            r = requests.get(
                url,
                timeout=10
            )

            if r.status_code == 200 and len(r.content) > 1000:

                try:
                    img = Image.open(
                        BytesIO(r.content)
                    )

                    return img

                except:
                    continue

        except:
            continue

    return None

# =====================================================
# HEADER
# =====================================================

st.title("✈️ SKYALERT TNI AU")
st.caption(
    "Upper Air Radiosonde Monitoring Indonesia | BMKG Aviation"
)

# =====================================================
# SELECT
# =====================================================

station = st.selectbox(
    "Pilih Stasiun Radiosonde",
    df["name"]
)

row = df[
    df["name"] == station
].iloc[0]

# =====================================================
# MAP
# =====================================================

st.subheader(
    "Peta Radiosonde Indonesia"
)

m = folium.Map(
    location=[-2.5,118],
    zoom_start=5,
    tiles="CartoDB dark_matter"
)

for _, r in df.iterrows():

    folium.CircleMarker(
        location=[
            r["lat"],
            r["lon"]
        ],
        radius=7,
        color="#00d4ff",
        fill=True,
        fill_color="#00d4ff",
        popup=f"{r['icao']} - {r['name']}"
    ).add_to(m)

st_folium(
    m,
    width=None,
    height=420
)

# =====================================================
# INFO
# =====================================================

c1,c2,c3,c4 = st.columns(4)

c1.metric(
    "ICAO",
    row["icao"]
)

c2.metric(
    "WMO",
    row["wmo"]
)

c3.metric(
    "Lat",
    row["lat"]
)

c4.metric(
    "Lon",
    row["lon"]
)

# =====================================================
# IMAGE
# =====================================================

st.subheader(
    "Latest Radiosonde BMKG"
)

img = fetch_image(
    row["wmo"]
)

if img:

    st.image(
        img,
        use_container_width=True
    )

else:

    st.warning(
        "BMKG belum mempublikasikan sounding untuk station ini pada siklus observasi terbaru."
    )

# =====================================================
# FOOTER
# =====================================================

st.caption(
    "SKYALERT | BMKG Upper Air + Aviation Decision Support | TNI AU"
)

st.markdown(
    ":contentReference[oaicite:1]{index=1}"
)
