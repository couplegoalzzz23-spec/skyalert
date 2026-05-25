import streamlit as st
import pandas as pd
import requests
import os
import re
from io import StringIO, BytesIO
from PIL import Image, ImageEnhance
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
    .stApp { background:#0b1120; color:white; }
    .status-card { background:#1e293b; padding:24px; border-radius:12px; border: 1px solid #334155; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .status-title { font-size:18px; font-weight:600; color:#e2e8f0; margin-bottom:12px; }
    .status-value { font-size:32px; font-weight:900; color:#f8fafc; }
    .alert-normal { color:#34d399; font-weight:bold; font-size:16px; margin-bottom:10px; }
    .alert-siaga { color:#fbbf24; font-weight:bold; font-size:16px; margin-bottom:10px; }
    .alert-awas { color:#ef4444; font-weight:bold; font-size:16px; margin-bottom:10px; }
    .metric-card { background:#1e293b; padding:15px; border-radius:12px; border: 1px solid #334155; text-align: center;}
</style>
""", unsafe_allow_html=True)

# HEADER ANTI BLOKIR
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# =====================================================
# DATA FALLBACK (Akan dipakai JIKA OCR Gagal)
# =====================================================
CSV_DATA = """
icao,wmo,name,lat,lon,cape,ki,li,freeze,wind,adm4
WITT,96001,Sultan Iskandar Muda,5.523,95.420,850,37,-3,16000,35,11.71.02.2001
WIMM,96035,Kualanamu,3.642,98.885,620,35,-2,16500,28,12.07.24.2001
WIBB,96109,Sultan Syarif Kasim II,0.460,101.445,44,32.9,-1.5,16327,44,14.71.03.1001
"""

def load_data():
    return pd.read_csv(StringIO(CSV_DATA.strip()))

df = load_data()

# =====================================================
# ENGINE PEMBACA GAMBAR SKEW-T BMKG (OCR)
# =====================================================
# TIDAK ADA CACHE DI SINI AGAR SELALU MEMBACA UPDATE TERBARU
def fetch_and_read_skewt_image(wmo):
    urls = [
        f"https://aviation.bmkg.go.id/monitoring_rason/LATEST_TEMP_{wmo}.PNG",
        f"https://aviation.bmkg.go.id/monitoring_rason/latest_temp_{wmo}.png"
    ]
    
    debug_log = ""
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            if resp.status_code == 200 and len(resp.content) > 1000:
                img = Image.open(BytesIO(resp.content))
                
                # --- PROSES MEMBACA TEKS DARI GAMBAR ---
                try:
                    import pytesseract
                    # Konfigurasi Mutlak Windows (Arahkan ke lokasi instalasi Tesseract)
                    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                    
                    # Pemotongan Gambar (Fokus ke area indeks atas agar tidak bingung membaca grafik)
                    w, h = img.size
                    cropped_img = img.crop((0, 0, w, int(h * 0.45)))
                    
                    # Pertajam kontras teks agar mudah dibaca mesin
                    gray = cropped_img.convert('L')
                    enhanced_img = ImageEnhance.Contrast(gray).enhance(2.0)
                    
                    # Eksekusi OCR
                    txt = pytesseract.image_to_string(enhanced_img, config=r'--oem 3 --psm 6')
                    
                except Exception as e:
                    return {"is_live": False, "error_msg": f"❌ Mesin OCR (Tesseract) tidak ditemukan di laptop Anda. Detail: {e}", "img": img}
                
                if txt.strip():
                    txt = txt.replace('O', '0').replace('o', '0') # Koreksi mesin
                    c = re.search(r'CAPE\s*(?:total)?\s*[:=]\s*([-\d\.]+)', txt, re.IGNORECASE)
                    k = re.search(r'(?:\bKI\b|\bK\s*[-_]?Index\b)\s*[:=]\s*([-\d\.]+)', txt, re.IGNORECASE)
                    l = re.search(r'(?:\bLI\b|\bLifted\s*[-_]?Index\b)\s*[:=]\s*([-\d\.]+)', txt, re.IGNORECASE)
                    f = re.search(r'(?:FRZG\s*Lvl|Freezing\s*Level)\s*[:=]\s*([\d\.]+)', txt, re.IGNORECASE)
                    w = re.search(r'(?:MVV|Max\s*Wind)\s*[:=]\s*([\d\.]+)', txt, re.IGNORECASE)
                    
                    if c or k or l:
                        return {
                            "cape": float(c.group(1)) if c else None,
                            "ki": float(k.group(1)) if k else None,
                            "li": float(l.group(1)) if l else None,
                            "freeze": float(f.group(1)) if f else None,
                            "wind": float(w.group(1)) if w else None,
                            "is_live": True,
                            "img": img,
                            "raw_text": txt
                        }
                    else:
                        return {"is_live": False, "error_msg": "❌ Gambar BMKG berhasil diunduh, tapi mesin gagal mengenali tulisan CAPE/LI karena resolusi buram.", "img": img}
                        
        except Exception as e:
            continue
            
    return {"is_live": False, "error_msg": "❌ Gagal mengunduh gambar dari server BMKG (Server Down/Timeout).", "img": None}


def analyze_weather(cape, ki, li, freeze, wind):
    try:
        cape, ki, li, freeze, wind = float(cape), float(ki), float(li), float(freeze), float(wind)
    except:
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
    return "AMAN", "alert-normal", thunder, turb, ice

# =====================================================
# MAIN DASHBOARD UI
# =====================================================
st.title("✈️ SKYALERT TNI AU")
st.caption("Tactical Aviation Weather & Upper Air Monitoring")

c_sel1, c_sel2 = st.columns([1, 2])
with c_sel1:
    station = st.selectbox("Pilih Lanud / Stasiun Observasi", df["name"])
row = df[df["name"] == station].iloc[0]

st.write("---")
st.subheader("☁️ Analisis Stabilitas Atmosfer (Radiosonde)")

# MENJALANKAN FUNGSI BACA GAMBAR
rason_data = fetch_and_read_skewt_image(row["wmo"])

# LOGIKA TAMPILAN JIKA GAGAL/SUKSES
if rason_data["is_live"]:
    c_val = rason_data["cape"] if rason_data["cape"] is not None else row["cape"]
    k_val = rason_data["ki"] if rason_data["ki"] is not None else row["ki"]
    l_val = rason_data["li"] if rason_data["li"] is not None else row["li"]
    f_val = rason_data["freeze"] if rason_data["freeze"] is not None else row["freeze"]
    w_val = rason_data["wind"] if rason_data["wind"] is not None else row["wind"]
    st.success(f"🟢 **Data Real-Time Sinkron:** OCR berhasil membaca gambar BMKG untuk WMO {row['wmo']}.")
else:
    c_val, k_val, l_val, f_val, w_val = row["cape"], row["ki"], row["li"], row["freeze"], row["wind"]
    st.error(rason_data.get("error_msg", "Error tidak diketahui."))
    st.warning("⚠️ **Tampilan Menggunakan Data Fallback (Statis).** Nilai di bawah ini bukan data real-time.")

status, color, thunder, turbulence, icing = analyze_weather(c_val, k_val, l_val, f_val, w_val)

# RENDER METRIK
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("CAPE (Energi Konvektif)", f"{c_val} J/kg")
c2.metric("K-Index", k_val)
c3.metric("Lifted Index", l_val)
c4.metric("Freezing Level", f"{f_val} ft")
c5.metric("Upper Wind", f"{w_val} kt")

st.write("")

# RENDER KARTU STATUS
card1, card2, card3 = st.columns(3)
with card1:
    st.markdown(f"<div class='status-card'><div class='status-title'>⛈️ Thunderstorm</div><div class='status-value'>{thunder}</div></div>", unsafe_allow_html=True)
with card2:
    st.markdown(f"<div class='status-card'><div class='status-title'>🌪️ Turbulence</div><div class='status-value'>{turbulence}</div></div>", unsafe_allow_html=True)
with card3:
    st.markdown(f"<div class='status-card'><div class='status-title'>❄️ Icing</div><div class='status-value'>{icing}</div></div>", unsafe_allow_html=True)

# INTERPRETASI TEKS
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background-color: #0f172a; padding: 24px; border-radius: 8px; border: 1px solid #1e293b;">
    <h3 style="color: #3b82f6; margin-top:0;">💡 Interpretasi Taktis & Analisis Termodinamika</h3>
    <div class="{color}">STATUS PERINGATAN UMUM: {status}</div>
    <ul style="color: #cbd5e1; font-size: 15px; line-height: 1.6;">
        <li><b>Kondisi Konvektif:</b> Dengan nilai CAPE {c_val} J/kg dan LI {l_val}, potensi pembentukan awan badai (Cumulonimbus) masuk kategori <b>{thunder}</b>.</li>
        <li><b>Kondisi Dinamis (Turbulensi):</b> Kecepatan angin lapisan atas di area {w_val} kt menciptakan potensi <i>wind shear</i> mekanis dengan risiko turbulensi <b>{turbulence}</b>.</li>
        <li><b>Kondisi Pembentukan Es:</b> <i>Freezing level</i> di ketinggian {f_val} ft menandakan risiko penumpukan es struktural (icing) pada badan pesawat tergolong <b>{icing}</b> untuk manuver taktis di level tersebut.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# SKEW T GAMBAR
st.write("---")
st.subheader("📈 Profil Radiosonde (Skew-T Log-P) Real-Time")
if rason_data.get("img") is not None:
    st.image(rason_data["img"], use_container_width=True)
else:
    st.warning("⚠️ Gagal memuat gambar dari BMKG.")

st.write("---")
st.caption("SKYALERT | Integrasi OCR Aviation Weather BMKG | Sistem Pendukung Keputusan Taktis")
