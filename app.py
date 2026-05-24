import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from io import StringIO, BytesIO
from PIL import Image

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="SKYALERT TNI AU",
    page_icon="✈️",
    layout="wide"
)

# =====================================================
# STYLE (Mempertahankan Desain Asli Anda)
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
.metric-card{
    background:#132433;
    padding:15px;
    border-radius:12px;
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
# IMAGE FETCH (KOKOH & AMAN)
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
            r = requests.get(url, timeout=10)
            # Memastikan response sukses dan data yang diterima benar-benar file gambar (bukan teks error)
            if r.status_code == 200 and len(r.content) > 1000:
                try:
                    img = Image.open(BytesIO(r.content))
                    return img
                except:
                    continue
        except:
            continue
    return None

# =====================================================
# ANALYSIS LOGIC (Sesuai Rumus Klasifikasi Anda)
# =====================================================
def analyze_weather(cape, ki, li, freeze, wind):
    score = 0

    # CAPE
    if cape > 1000: score += 3
    elif cape > 500: score += 2
    elif cape > 100: score += 1

    # KI
    if ki >= 38: score += 3
    elif ki >= 35: score += 2
    elif ki >= 30: score += 1

    # LI
    if li <= -4: score += 3
    elif li <= -2: score += 2
    elif li < 0: score += 1

    # WIND
    if wind >= 40: score += 3
    elif wind >= 30: score += 2
    elif wind >= 20: score += 1

    # FREEZING (ICING)
    if freeze < 15000:
        icing = "TINGGI"
    elif freeze < 18000:
        icing = "SEDANG"
    else:
        icing = "RENDAH"

    # FINAL STATUS
    if score >= 9:
        status = "AWAS"
        color = "alert-awas"
    elif score >= 5:
        status = "SIAGA"
        color = "alert-siaga"
    else:
        status = "NORMAL"
        color = "alert-normal"

    # THUNDERSTORM
    if cape > 1000 or ki > 38: 
        thunder = "TINGGI"
    elif cape > 500: 
        thunder = "SEDANG"
    else: 
        thunder = "RENDAH"

    # TURBULENCE
    if wind >= 40: 
        turbulence = "TINGGI"
    elif wind >= 30: 
        turbulence = "SEDANG"
    else: 
        turbulence = "RENDAH"

    return status, color, thunder, turbulence, icing

# =====================================================
# HEADER
# =====================================================
st.title("✈️ SKYALERT TNI AU")
st.caption("Upper Air Radiosonde Monitoring Indonesia | BMKG Aviation")

# =====================================================
# SELECT STATION
# =====================================================
station = st.selectbox("Pilih Stasiun Radiosonde", df["name"])
row = df[df["name"] == station].iloc[0]

# =====================================================
# EXECUTE ANALYSIS
# =====================================================
status, color, thunder, turbulence, icing = analyze_weather(
    row["cape"], row["ki"], row["li"], row["freeze"], row["wind"]
)

# =====================================================
# MAIN ALERT
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
# MAP (Peta Folium Asli Dipertahankan)
# =====================================================
st.subheader("Peta Radiosonde Indonesia")

m = folium.Map(
    location=[-2.5, 118],
    zoom_start=5,
    tiles="CartoDB dark_matter"
)

for _, r in df.iterrows():
    marker_color = "#00d4ff"
    if r["name"] == station:
        marker_color = "#ffcc00"

    folium.CircleMarker(
        location=[r["lat"], r["lon"]],
        radius=8,
        color=marker_color,
        fill=True,
        fill_color=marker_color,
        popup=f"{r['icao']} - {r['name']}"
    ).add_to(m)

st_folium(m, width=None, height=420)

# =====================================================
# STATION INFO
# =====================================================
st.subheader("Analisis Radiosonde")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("ICAO", row["icao"])
c2.metric("CAPE", f"{row['cape']} J/kg")
c3.metric("KI", row["ki"])
c4.metric("LI", row["li"])
c5.metric("Wind", f"{row['wind']} kt")

# =====================================================
# HAZARD
# =====================================================
h1, h2, h3 = st.columns(3)

with h1:
    st.markdown(f"""
    <div class="block">
    <h3>⛈ Thunderstorm</h3>
    <h1>{thunder}</h1>
    </div>
    """, unsafe_allow_html=True)

with h2:
    st.markdown(f"""
    <div class="block">
    <h3>🌪 Turbulence</h3>
    <h1>{turbulence}</h1>
    </div>
    """, unsafe_allow_html=True)

with h3:
    st.markdown(f"""
    <div class="block">
    <h3>❄ Icing</h3>
    <h1>{icing}</h1>
    </div>
    """, unsafe_allow_html=True)

# =====================================================
# INTERPRETASI
# =====================================================
st.subheader("Kesimpulan Data Radiosonde")

summary = f"""
### {station} ({row['icao']})

- Potensi thunderstorm : **{thunder}**
- Risiko turbulensi : **{turbulence}**
- Risiko icing : **{icing}**
- Status operasional penerbangan : **{status}**

### Interpretasi
Data radiosonde menunjukkan kondisi atmosfer dengan potensi konveksi {thunder.lower()}.
Nilai CAPE sebesar {row['cape']} J/kg menunjukkan tingkat energi konvektif atmosfer.
Nilai KI sebesar {row['ki']} menunjukkan potensi pertumbuhan awan Cumulonimbus.
Nilai LI sebesar {row['li']} menunjukkan tingkat ketidakstabilan atmosfer.
Kecepatan angin lapisan atas mencapai {row['wind']} knot sehingga potensi turbulensi berada pada kategori {turbulence.lower()}.

### Rekomendasi Operasional
- Laksanakan monitoring cuaca lanjutan sebelum penerbangan.
- Waspadai pertumbuhan awan CB di sekitar jalur penerbangan.
- Perhatikan potensi icing dan turbulensi pada fase climb dan descent.
"""
st.markdown(summary)

# =====================================================
# IMAGE SKEW-T
# =====================================================
st.subheader("Latest Radiosonde BMKG")

img = fetch_image(row["wmo"])

if img:
    # Menggunakan fungsi modern masa depan Streamlit yang didukung penuh
    st.image(img, use_container_width=True)
else:
    st.warning("BMKG belum mempublikasikan sounding terbaru untuk stasiun ini.")

# =====================================================
# FOOTER
# =====================================================
st.caption("SKYALERT | BMKG Upper Air + Aviation Decision Support | TNI AU")
