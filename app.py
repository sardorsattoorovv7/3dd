import os, math, json, html, base64
from pathlib import Path
from datetime import datetime
import requests
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from dotenv import load_dotenv
from io import BytesIO
from fpdf import FPDF
import streamlit as st
import tempfile

# ========== CONSTRUCTION MODULINI ULASH ==========
CONSTRUCTION_AVAILABLE = False
try:
    from construction_module import (
        CONSTRUCTION_DEFAULTS,
        construction_types,
        wall_materials,
        floor_materials,
        roof_materials,
        calculate_construction_materials,
        create_construction_3d,
        construction_sidebar,
        construction_main
    )
    CONSTRUCTION_AVAILABLE = True
    st.success("✅ Construction moduli muvaffaqiyatli yuklandi!")
except (ImportError, ModuleNotFoundError) as e:
    CONSTRUCTION_AVAILABLE = False
    st.warning(f"⚠️ Construction moduli yuklanmadi: {e}")
    st.warning("Iltimos, construction_module.py faylini tekshiring!")
    
    # DUMMY FUNKSIYALAR - xatolik oldini olish uchun
    def construction_sidebar():
        st.error("❌ Construction moduli yuklanmagan!")
        return {}
    
    def construction_main(params):
        st.error("❌ Construction moduli yuklanmagan!")
        st.info("Iltimos, construction_module.py faylini yarating yoki tekshiring.")
    
    CONSTRUCTION_DEFAULTS = {}
    construction_types = []
    wall_materials = []
    floor_materials = []
    roof_materials = []
    calculate_construction_materials = lambda *args, **kwargs: {}
    create_construction_3d = lambda *args, **kwargs: None

except NameError as e:
    CONSTRUCTION_AVAILABLE = False
    st.warning(f"⚠️ Construction modulida funksiya topilmadi: {e}")
    
    # DUMMY FUNKSIYALAR
    def construction_sidebar():
        st.error("❌ Construction moduli to'liq emas!")
        return {}
    
    def construction_main(params):
        st.error("❌ Construction moduli to'liq emas!")
    
    CONSTRUCTION_DEFAULTS = {}
    construction_types = []
    wall_materials = []
    floor_materials = []
    roof_materials = []
    calculate_construction_materials = lambda *args, **kwargs: {}
    create_construction_3d = lambda *args, **kwargs: None
load_dotenv()

st.set_page_config(page_title="Constructor", layout="wide")

TELEGRAM_CHAT_ID = "-1002338157363"
DATA_FILE = Path("form_data.json")
DEFAULT_FORM_DATA = {
    "L_text":"5","W_text":"4","H_text":"3",
    "d_turi":"Sovutgich (PUR)","d_qalin":"100mm",
    "p_turi":"Sovutgich (PUR)","p_qalin":"80mm",
    "panel_width_m":1.16,"pol_bor":True,
    "pol_turi":"PUR (Standart)","pol_qalin":"100mm",
    "pol_material":"PUR panel",  # Yangi: "PUR panel" yoki "Beton"
    "beton_qalinligi_mm":100,     # Beton qalinligi mm da
    "eshik":"Muzlatkich eshigi","eshik_joyi":"Old",
    "eshik_pozitsiya":"O'rta","eshik_ochilish":"Ichkariga",
    "agregat":"Split-sistema (Nizkotemp)","agregat_joyi":"Old",
    "project_name":"","room_code":"EP-001",
    "mahsulot_turi":"Go'sht","saqlash_temp":"-18C",
    "ochilish_soni":"Kam","hudud":"Mo'tadil","namlik_talabi":"Standart",
    "ag_brand":"Bitzer","montaj_progress":100,"show_3d_labels":True,
    "eshik_custom_width": 900,
    "eshik_custom_height": 1900,
    "eshik_soni": 1,
    "kamera_bolish": "Yo'q",
    "kamera_bolish_nisbat": 50,
    "ikkinchi_kamera_eshik": False,
    "ikkinchi_kamera_eshik_joyi": "Old",
    "kamera_bolish_turi": "Yo'q",        # YANGI: 2-6 ta kamera uchun
    "kameralar_soni": 2,                  # YANGI: 2-6 ta kamera
    "har_bir_kamera_eshik": False,     
}
d_turi_opts      = ["Sovutgich (PUR)","Oddiy Devor","Sendvich Mineral paxta"]
d_qalin_opts     = ["50mm","80mm","100mm","150mm"]
p_turi_opts      = ["Sovutgich (PUR)","Tom uchun (Trapsiya)","Tekis panel"]
p_qalin_opts     = ["50mm","80mm","100mm","150mm"]
pw_opts          = [0.96,1.00,1.16]
pol_turi_opts    = ["PUR (Kuchaytirilgan)","PUR (Standart)"]
pol_qalin_opts   = ["50mm","80mm","100mm","150mm"]
pol_material_opts = ["PUR panel", "Beton"]  # Yangi tanlov
eshik_opts = ["Yo'q","Custom","Bir tabaqali (90x190)","Surilma (120x200)","Muzlatkich eshigi"]

eshik_joyi_opts  = ["Old","Orqa","O'ng","Chap"]
eshik_och_opts   = ["Ichkariga","Tashqariga"]
agregat_opts     = ["Yo'q","Mono-blok (Srednetemp)","Split-sistema (Nizkotemp)","Zanotti (Italiya)"]
ag_joyi_opts     = ["Old","Orqa","Chap","O'ng","O'rta (Tom)"]
mahsulot_opts    = ["Go'sht","Tovuq","Baliq","Muzqaymoq","Sut mahsulotlari","Meva-sabzavot","Gullar","Dorilar","Ichimliklar","Aralash mahsulot"]
ochilish_opts    = ["Kam","O'rtacha","Ko'p"]
hudud_opts       = ["Sovuq","Mo'tatil","Issiq"]
namlik_opts      = ["Standart","Past namlik","Yuqori namlik"]
side_pos_opts    = ["Tepa","O'rta","Past"]
tb_pos_opts      = ["Chap","O'rta","O'ng"]
ag_brand_opts    = ["Bitzer","Zanotti","Frascold","Copeland"]

MULTI_DEFAULTS = {
    "mode": "Multi-kamera",
    "multi_input_mode": "Umumiy maydon (m2)",
    "multi_area": 200.0,
    "multi_L": 20.0,
    "multi_W": 10.0,
    "n_chambers": 4,
    "height_mode": "Hammasi bir xil",
    "multi_H": 3.0,
    "has_corridor": True,
    "corridor_w": 2.5,
    "corridor_pos": "Markaz",
    "wall_mm_multi": 100,
    "door_w_multi": 0.96,
    "door_h_multi": 2.1,
    "proj_name_multi": "200m2 Sovutgich Ombori",
    "code_multi": "EP-2024-M",
    # Multi-kamera uchun pol sozlamalari
    "multi_pol_bor": True,
    "multi_pol_material": "PUR panel",
    "multi_beton_qalinligi_mm": 100,
    "multi_pol_qalin": "100mm",
}

st.markdown("""<style>
.main{background:#f0f2f5}
.block-container{padding-top:.8rem;padding-bottom:2rem;max-width:1500px}
h1,h2,h3,h4{color:#111}
.stButton>button{width:100%;border-radius:8px;height:2.8em;background:#111;color:white;font-weight:700;border:none;transition:all .25s ease;letter-spacing:.02em}
.stButton>button:hover{background:#333;transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.18)}
.stDownloadButton>button{width:100%;border-radius:8px;height:2.8em;background:#1f2937;color:white;font-weight:700;border:none}
.card{background:white;border-radius:12px;border:1px solid #e2e6ea;box-shadow:0 1px 3px rgba(0,0,0,.05);padding:18px;margin-bottom:10px}
.metric-box{background:white;border-radius:12px;border:1px solid #e2e6ea;padding:16px;text-align:center}
.metric-title{color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.metric-value{color:#111;font-size:22px;font-weight:800;margin-top:6px}
.ai-box{background:white;border-radius:12px;border:1px solid #e2e6ea;border-left:5px solid #111;padding:18px}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;background:#f3f4f6;border:1px solid #e5e7eb;font-size:12px;margin:2px 4px 4px 0}
</style>""", unsafe_allow_html=True)

# helpers
def load_form_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE,"r",encoding="utf-8") as f: data=json.load(f)
            merged=DEFAULT_FORM_DATA.copy(); merged.update(data); return merged
        except: pass
    return DEFAULT_FORM_DATA.copy()

def save_form_data():
    data={k:st.session_state.get(k,DEFAULT_FORM_DATA[k]) for k in DEFAULT_FORM_DATA}
    try:
        with open(DATA_FILE,"w",encoding="utf-8") as f: json.dump(data,f,indent=2,ensure_ascii=False)
    except Exception as e: st.warning(f"Saqlashda xatolik: {e}")

def init_state():
    for k, v in load_form_data().items():
        if k not in st.session_state:
            st.session_state[k] = v
    for k, v in MULTI_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # ===== AI_RESULT INIT =====
    if "ai_result" not in st.session_state:
        st.session_state.ai_result = None
    if "heights_list_cache" not in st.session_state:
        st.session_state.heights_list_cache = [3.0]
    
    if "multi_L_val" not in st.session_state:
        st.session_state.multi_L_val = 20.0
    if "multi_W_val" not in st.session_state:
        st.session_state.multi_W_val = 10.0
    if "multi_area_val" not in st.session_state:
        st.session_state.multi_area_val = 200.0
def parse_dim(t):
    t=(t or "").strip().replace(",",".")
    try: v=float(t); return v if v>0 else None
    except: return None

def mm_val(s): return int(str(s).replace("mm","").strip())
def m_to_mm(m): return int(round(m*1000))
def clamp(v,lo,hi): return max(lo,min(v,hi))

def door_dim(eshik):
    if eshik=="Bir tabaqali (90x190)": return 900,1900
    if eshik=="Surilma (120x200)": return 1200,2000
    if eshik=="Muzlatkich eshigi": return 960,2000
    return 0,0

# ========== SHU YERDAN KEYIN QO'SHING ==========
def door_dim_custom(eshik, custom_w=None, custom_h=None):
    """Eshik o'lchamlarini qaytaradi - custom qo'llab-quvvatlaydi"""
    if eshik == "Custom":
        return custom_w or 900, custom_h or 1900
    if eshik == "Bir tabaqali (90x190)": return 900, 1900
    if eshik == "Surilma (120x200)": return 1200, 2000
    if eshik == "Muzlatkich eshigi": return 960, 2000
    return 0, 0

def calculate_split_chambers(L, W, H, bolish_turi, kameralar_soni):
    """Kamerani 2-6 ta kameralarga bo'lish"""
    if kameralar_soni < 2:
        return [{"L": L, "W": W, "H": H, "id": 1}]
    
    chambers = []
    if bolish_turi == "Uzunlik bo'yicha":
        each_L = L / kameralar_soni
        for i in range(kameralar_soni):
            chambers.append({
                "id": i + 1,
                "L": each_L,
                "W": W,
                "H": H,
                "x": i * each_L,
                "y": 0,
                "w": each_L,
                "h": W
            })
    else:  # "Eni bo'yicha"
        each_W = W / kameralar_soni
        for i in range(kameralar_soni):
            chambers.append({
                "id": i + 1,
                "L": L,
                "W": each_W,
                "H": H,
                "x": 0,
                "y": i * each_W,
                "w": L,
                "h": each_W
            })
    
    return chambers

def panel_count(length_m,pw=1.16):
    full=int(length_m//pw); rem=round(length_m-full*pw,3)
    return {"full_panels":full,"remainder_m":rem,"total_panels":full+(1 if rem>0.01 else 0)}

def calculate_concrete_volume(area_m2, thickness_mm):
    """Beton hajmini kub metrda hisoblaydi"""
    thickness_m = thickness_mm / 1000.0
    volume_m3 = area_m2 * thickness_m
    return volume_m3

def calculate_concrete_materials(volume_m3):
    """Beton materiallarini hisoblaydi (M250 marka)"""
    # M250 beton uchun 1 m3 ga materiallar (taxminiy)
    cement_kg = volume_m3 * 350  # 350 kg/m3
    sand_m3 = volume_m3 * 0.6    # 0.6 m3 qum
    gravel_m3 = volume_m3 * 0.8  # 0.8 m3 shag'al
    return {
        "cement_kg": round(cement_kg),
        "sand_m3": round(sand_m3, 2),
        "gravel_m3": round(gravel_m3, 2),
        "total_m3": round(volume_m3, 2)
    }

def calculate_beton_cost(volume_m3, region="uzbekistan"):
    """Beton narxini hisoblaydi (taxminiy)"""
    # Taxminiy narxlar (1 m3 uchun)
    price_per_m3 = 120  # dollar yoki so'm
    return round(volume_m3 * price_per_m3, 2)

# ========== POL MATERIALI ASOSIDA QALINLIKNI OLISH ==========
def get_floor_thickness_mm(pol_material, pol_qalin=None, beton_qalinligi_mm=None):
    """Pol materialiga qarab qalinlikni qaytaradi"""
    if pol_material == "Beton":
        return beton_qalinligi_mm if beton_qalinligi_mm else 100
    else:
        # PUR panel
        if pol_qalin:
            return mm_val(pol_qalin)
        return 100

def get_floor_description(pol_material, pol_qalin_mm):
    """Pol tavsifini qaytaradi"""
    if pol_material == "Beton":
        return f"Beton {pol_qalin_mm} mm (M250)"
    else:
        return f"PUR panel {pol_qalin_mm} mm"

def calculate_multi_panels(L, W, heights_list, n_chambers, wall_mm, 
                           panel_width_m=1.16, pol_bor=True, pol_material="PUR panel",
                           beton_qalinligi_mm=100, pol_qalin="100mm",
                           has_corridor=False, corridor_w=0, corridor_pos="markaz"):
    """
    Multi-kamera uchun panel sonini hisoblaydi.
    Beton va PUR panel farqini hisobga oladi.
    """
    T = wall_mm / 1000.0
    
    # Pol qalinligini aniqlash
    floor_thickness_mm = get_floor_thickness_mm(pol_material, pol_qalin, beton_qalinligi_mm)
    floor_thickness_m = floor_thickness_mm / 1000.0
    
    # Kameralarni aniqlash
    chambers = []
    
    if has_corridor and corridor_pos == "markaz" and corridor_w > 0:
        n_left = int(math.ceil(n_chambers / 2))
        n_right = n_chambers - n_left
        cham_L = (L - corridor_w) / 2
        cham_W_left = W / n_left
        cham_W_right = W / n_right if n_right > 0 else 0
        
        for i in range(n_left):
            chambers.append({
                "id": i+1, "L": cham_L, "W": cham_W_left, 
                "H": heights_list[i] if i < len(heights_list) else heights_list[-1],
            })
        for i in range(n_right):
            chambers.append({
                "id": n_left + i + 1, "L": cham_L, "W": cham_W_right,
                "H": heights_list[n_left + i] if n_left + i < len(heights_list) else heights_list[-1],
            })
            
    elif has_corridor and corridor_w > 0 and corridor_pos in ("chap", "o'ng"):
        cham_L = L - corridor_w
        cham_W = W / n_chambers
        for i in range(n_chambers):
            chambers.append({
                "id": i+1, "L": cham_L, "W": cham_W,
                "H": heights_list[i] if i < len(heights_list) else heights_list[-1],
            })
    else:
        cham_L = L / n_chambers
        cham_W = W
        for i in range(n_chambers):
            chambers.append({
                "id": i+1, "L": cham_L, "W": cham_W,
                "H": heights_list[i] if i < len(heights_list) else heights_list[-1],
            })
    
    # Hisoblagichlar
    total_wall_panels = 0
    total_ceiling_panels = 0
    total_floor_panels = 0
    total_wall_area = 0
    total_ceiling_area = 0
    total_floor_area = 0
    chamber_stats = []
    
    for ch in chambers:
        Lc = ch["L"]
        Wc = ch["W"]
        Hc = ch["H"]
        
        # Devor panellari: 4 devor
        wall_panels = panel_count(Lc, panel_width_m)["total_panels"] * 2
        wall_panels += panel_count(Wc, panel_width_m)["total_panels"] * 2
        
        # Patalok panellari
        ceiling_panels = math.ceil(Lc / panel_width_m) * math.ceil(Wc / panel_width_m)
        
        # Pol panellari - agar PUR panel bo'lsa, panel hisoblanadi, beton bo'lsa 0
        if pol_bor and pol_material == "PUR panel":
            floor_panels = ceiling_panels
        else:
            floor_panels = 0
        
        # Maydonlar
        wall_area = 2 * (Lc + Wc) * Hc
        ceiling_area = Lc * Wc
        floor_area = Lc * Wc if pol_bor else 0
        
        chamber_stats.append({
            "id": ch["id"],
            "L": round(Lc, 2), "W": round(Wc, 2), "H": round(Hc, 2),
            "wall_panels": wall_panels,
            "ceiling_panels": ceiling_panels,
            "floor_panels": floor_panels,
            "total": wall_panels + ceiling_panels + floor_panels,
            "wall_area": round(wall_area, 1),
            "ceiling_area": round(ceiling_area, 1),
            "floor_area": round(floor_area, 1)
        })
        
        total_wall_panels += wall_panels
        total_ceiling_panels += ceiling_panels
        total_floor_panels += floor_panels
        total_wall_area += wall_area
        total_ceiling_area += ceiling_area
        total_floor_area += floor_area
    
    # Yo'lak panellari
    corridor_panels = 0
    corridor_wall_panels = 0
    corridor_ceiling_panels = 0
    corridor_floor_panels = 0
    corridor_wall_area = 0
    corridor_ceiling_area = 0
    corridor_floor_area = 0
    
    if has_corridor and corridor_w > 0:
        if corridor_pos == "markaz":
            corr_L = corridor_w
            corr_W = W
        else:
            corr_L = L
            corr_W = corridor_w
        
        corridor_wall_panels = panel_count(corr_L, panel_width_m)["total_panels"] * 2
        corridor_wall_panels += panel_count(corr_W, panel_width_m)["total_panels"] * 2
        
        # Yo'lak patalok panellari
        corridor_ceiling_panels = math.ceil(corr_L / panel_width_m) * math.ceil(corr_W / panel_width_m)
        
        # Yo'lak pol panellari - faqat PUR panel bo'lsa
        if pol_bor and pol_material == "PUR panel":
            corridor_floor_panels = corridor_ceiling_panels
        else:
            corridor_floor_panels = 0
            
        corridor_panels = corridor_wall_panels + corridor_ceiling_panels + corridor_floor_panels
        
        corridor_wall_area = 2 * (corr_L + corr_W) * max(heights_list) if heights_list else 0
        corridor_ceiling_area = corr_L * corr_W
        corridor_floor_area = corr_L * corr_W if pol_bor else 0
    
    # ===== ASOSIY JAMI PANELLAR (QO'SHIMCHALARSIZ) =====
    total_wall_panels_final = total_wall_panels + corridor_wall_panels
    total_ceiling_panels_final = total_ceiling_panels + corridor_ceiling_panels
    total_floor_panels_final = total_floor_panels + corridor_floor_panels
    
    total_panels_base = total_wall_panels_final + total_ceiling_panels_final + total_floor_panels_final
    
    # ========== BETON HAJMI (agar beton tanlangan bo'lsa) ==========
    concrete_volume_m3 = 0
    concrete_info = None
    if pol_bor and pol_material == "Beton":
        total_floor_area_m2 = total_floor_area + corridor_floor_area
        concrete_volume_m3 = calculate_concrete_volume(total_floor_area_m2, floor_thickness_mm)
        concrete_info = {
            "area_m2": round(total_floor_area_m2, 1),
            "thickness_mm": floor_thickness_mm,
            "volume_m3": round(concrete_volume_m3, 2),
            "materials": calculate_concrete_materials(concrete_volume_m3),
        }
    
    # ========== TOM QO'SHIMCHA ELEMENTLARI (ALOHIDA HISOB) ==========
    max_h = max(heights_list) if heights_list else 3.0
    
    # TOM PARAMETRLARI
    roof_ridge_H = 0.5      # Tom tizmasining balandligi (metr) - 50 sm
    roof_overhang = 0.15    # Tomning chiqindisi (metr) - 15 sm
    rib_thickness = 0.04    # Qovurga qalinligi (metr) - 40mm
    rib_width = 0.08        # Qovurga kengligi (metr) - 80mm
    
    # 1. UCHBURCHAK YON DEVORLAR (GABLE WALLS) - ALOHIDA
    gable_base = L + 2 * roof_overhang
    gable_height = roof_ridge_H
    gable_area_one = (gable_base * gable_height) / 2
    total_gable_area = gable_area_one * 2
    
    panels_per_gable = math.ceil(gable_base / panel_width_m)
    exact_gable_panels = panels_per_gable * 2
    
    # 2. TIZMA PANELI (RIDGE CAP) - ALOHIDA
    ridge_cap_length = W + 2 * roof_overhang
    ridge_cap_width = 0.30
    ridge_cap_area = ridge_cap_length * ridge_cap_width
    ridge_cap_panels = max(1, math.ceil(ridge_cap_length / panel_width_m)) if ridge_cap_length > 0 else 0
    
    # 3. FASCA PANELLARI (TOMLIK DEKOR) - ALOHIDA
    half_L = L / 2
    slope_length = math.sqrt(half_L**2 + roof_ridge_H**2) + roof_overhang
    fascia_length = slope_length * 2
    fascia_width = 0.20
    fascia_area = fascia_length * fascia_width
    fascia_panels = max(1, math.ceil(fascia_length / panel_width_m)) if fascia_length > 0 else 0
    
    # 4. TOM QOVURG'ALARI (ROOF RIBS) - METALL PROFIL
    rib_spacing = 0.25
    num_ribs_lengthwise = max(1, int(math.ceil(W / rib_spacing)))
    num_ribs_cross = max(1, int(math.ceil(L / rib_spacing)))
    
    lengthwise_ribs_length = num_ribs_lengthwise * slope_length * 2
    cross_ribs_length = num_ribs_cross * W * 2
    total_rib_length = lengthwise_ribs_length + cross_ribs_length
    total_ribs_count = (num_ribs_lengthwise + num_ribs_cross) * 2
    
    rib_volume_per_meter = rib_thickness * rib_width
    total_rib_volume = total_rib_length * rib_volume_per_meter
    rib_weight_per_meter = 2.5
    total_rib_weight = total_rib_length * rib_weight_per_meter
    
    # QO'SHIMCHA PANELLAR JAMI
    total_extra_panels = exact_gable_panels + ridge_cap_panels + fascia_panels
    total_extra_area = total_gable_area + ridge_cap_area + fascia_area
    
    # TOM QO'SHIMCHA ELEMENTLARI MA'LUMOTLARI
    roof_extra = {
        "gable_walls": {
            "count": 2,
            "area_m2": round(total_gable_area, 2),
            "panels": exact_gable_panels,
            "dimensions": f"{gable_base:.1f}m x {gable_height:.1f}m",
            "material": "PUR panel (qalinligi 80mm)",
            "description": "🏔️ Uchburchak yon devorlar"
        },
        "ridge_cap": {
            "length_m": round(ridge_cap_length, 2),
            "area_m2": round(ridge_cap_area, 2),
            "panels": ridge_cap_panels,
            "material": "Galvanizli metall (0.5mm)",
            "description": "🏠 Tizma qoplamasi"
        },
        "fascia": {
            "length_m": round(fascia_length, 2),
            "area_m2": round(fascia_area, 2),
            "panels": fascia_panels,
            "description": "🎀 Tom yonboshlari paneli (Fasça)"
        },
        "roof_ribs": {
            "total_count": total_ribs_count,
            "total_length_m": round(total_rib_length, 2),
            "total_volume_m3": round(total_rib_volume, 4),
            "total_weight_kg": round(total_rib_weight, 1),
            "rib_size": f"{rib_thickness*1000:.0f}mm x {rib_width*1000:.0f}mm",
            "spacing_cm": rib_spacing * 100,
            "slope_length_m": round(slope_length, 2),
            "description": "📏 Tom qovurg'alari (metall profil)"
        },
        "total_extra_panels": total_extra_panels,
        "total_extra_area": round(total_extra_area, 2),
        "total_rib_length_m": round(total_rib_length, 2),
        "total_rib_weight_kg": round(total_rib_weight, 1)
    }
    
    return {
        # ASOSIY HISOB (QO'SHIMCHALARSIZ)
        "total_panels": total_panels_base,
        "wall_panels": total_wall_panels_final,
        "ceiling_panels": total_ceiling_panels_final,
        "floor_panels": total_floor_panels_final,
        "corridor_panels": corridor_panels,
        "chambers": chamber_stats,
        "total_area": {
            "walls": round(total_wall_area + corridor_wall_area, 1),
            "ceiling": round(total_ceiling_area + corridor_ceiling_area, 1),
            "floor": round(total_floor_area + corridor_floor_area, 1)
        },
        # QO'SHIMCHA ELEMENTLAR (ALOHIDA)
        "roof_extra": roof_extra,
        # BETON MA'LUMOTLARI (agar beton tanlangan bo'lsa)
        "concrete": concrete_info,
        "floor_material": pol_material,
        "floor_thickness_mm": floor_thickness_mm,
        "floor_description": get_floor_description(pol_material, floor_thickness_mm)
    }

# ========== GERMITIKA HISOBI (50 m² = 24 dona) ==========
def calculate_germitika(total_area_m2):
    """
    Germitika (muhrlovchi material/lenta) miqdorini hisoblaydi
    50 m² = 24 dona asosida to'g'ri proportsiya
    
    Args:
        total_area_m2 (float): Umumiy maydon (m²) - pol maydoni
    
    Returns:
        dict: Germitika hisobi natijalari
    """
    if total_area_m2 <= 0:
        return {"germitika_soni": 0, "zaxira_bilan": 0, "hisob_metodi": "Maydon noto'g'ri"}
    
    # 50 m² ga 24 dona -> 1 m² ga 0.48 dona
    # Proportsiya: (maydon / 50) * 24
    germitika_soni = (total_area_m2 / 50) * 24
    
    # Butun songa yaxlitlash (har doim yuqoriga - yetarli bo'lishi uchun)
    germitika_soni_rounded = int(math.ceil(germitika_soni))
    
    # 15% zaxira qo'shamiz
    
    return {
        "germitika_soni": germitika_soni_rounded,
        "germitika_aniq": round(germitika_soni, 2),
        "hisob_metodi": f"{total_area_m2:.1f} m² / 50 m² × 24 = {germitika_soni:.2f} → {germitika_soni_rounded} ta",
        "asos": "50 m² = 24 dona"
    }

def create_architectural_drawing(L, W, H, wall_mm, n_chambers=4, has_corridor=True, corridor_w=2.5, corridor_pos="markaz", heights_list=None, eshiklar=None):
    """
     arxitektura chizmasini yaratadi (plan, kesim, fasad)
    AutoCAD uslubida, aniq masshtabda
    """
    import math
    from datetime import datetime
    
    # Eshiklar parametri ishlatilmasa ham funksiya ishlashi uchun
    # eshiklar parametrini qabul qiladi lekin ishlatmaydi
    
    T = wall_mm / 1000.0
    
    # Agar heights_list bo'lmasa
    if heights_list is None:
        heights_list = [H] * n_chambers
    
    # SVG o'lchamlari
    WIDTH, HEIGHT = 1400, 1000
    scale = min(550 / max(L, W), 400 / H) * 1.1
    
    # Plan pozitsiyasi
    plan_x = 80
    plan_y = 70
    plan_w = L * scale
    plan_h = W * scale
    
    # Kesim pozitsiyasi
    kesim_x = 80
    kesim_y = 500
    kesim_w = L * scale
    kesim_h = H * scale
    
    # Fasad pozitsiyasi
    fasad_x = 740
    fasad_y = 500
    fasad_w = L * scale
    fasad_h = H * scale
    
    # Kamera va yo'lakni hisoblash
    chambers = []
    if has_corridor and corridor_pos == "markaz" and corridor_w > 0:
        n_left = int(math.ceil(n_chambers / 2))
        n_right = n_chambers - n_left
        cham_L = (L - corridor_w) / 2
        cham_W_left = W / n_left
        cham_W_right = W / n_right if n_right > 0 else 0
        for i in range(n_left):
            chambers.append({"id": i+1, "x": 0, "y": i * cham_W_left, "w": cham_L, "h": cham_W_left})
        for i in range(n_right):
            chambers.append({"id": n_left+i+1, "x": cham_L + corridor_w, "y": i * cham_W_right, "w": cham_L, "h": cham_W_right})
        corridor = {"x": cham_L, "y": 0, "w": corridor_w, "h": W}
    elif has_corridor and corridor_w > 0 and corridor_pos in ("chap", "o'ng"):
        cham_L = L - corridor_w
        cham_W = W / n_chambers
        offset_x = corridor_w if corridor_pos == "chap" else 0
        for i in range(n_chambers):
            chambers.append({"id": i+1, "x": offset_x, "y": i * cham_W, "w": cham_L, "h": cham_W})
        corridor = {"x": 0 if corridor_pos == "chap" else L - corridor_w, "y": 0, "w": corridor_w, "h": W}
    else:
        cham_L = L / n_chambers
        cham_W = W
        for i in range(n_chambers):
            chambers.append({"id": i+1, "x": i * cham_L, "y": 0, "w": cham_L, "h": cham_W})
        corridor = None
    
    # Loyiha nomi (agar mavjud bo'lsa)
    try:
        proj_name = st.session_state.get('proj_name_multi', 'MULTI-KAMERA')
    except:
        proj_name = 'MULTI-KAMERA'
    
    svg = f'''<svg width="100%" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg" style="background:#ffffff;">
    <defs>
        <style>
            text {{ font-family: 'Arial', 'Segoe UI', sans-serif; }}
            .title {{ font-size: 16px; font-weight: bold; fill: #1a1a2e; }}
            .subtitle {{ font-size: 11px; fill: #666; }}
            .dim-line {{ stroke: #2563eb; stroke-width: 1; stroke-dasharray: 5,3; }}
            .dim-text {{ font-size: 9px; fill: #1e3a8a; font-family: 'Arial'; }}
            .wall-fill {{ fill: #f3f4f6; stroke: #374151; stroke-width: 2; }}
            .door-fill {{ fill: none; stroke: #059669; stroke-width: 2; }}
            .window-fill {{ fill: #bfdbfe; stroke: #3b82f6; stroke-width: 1.5; fill-opacity: 0.4; }}
            .grid-line {{ stroke: #e5e7eb; stroke-width: 0.5; }}
            .label {{ font-size: 8px; fill: #6b7280; font-family: 'Arial'; }}
            .section-line {{ stroke: #dc2626; stroke-width: 1.5; stroke-dasharray: 10,4; }}
        </style>
        <pattern id="hatch-concrete" patternUnits="userSpaceOnUse" width="6" height="6">
            <line x1="0" y1="0" x2="6" y2="6" stroke="#9ca3af" stroke-width="0.5"/>
        </pattern>
        <pattern id="hatch-insulation" patternUnits="userSpaceOnUse" width="8" height="4">
            <line x1="0" y1="0" x2="4" y2="4" stroke="#fcd34d" stroke-width="0.8"/>
            <line x1="4" y1="0" x2="8" y2="4" stroke="#fcd34d" stroke-width="0.8"/>
        </pattern>
        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563eb"/>
        </marker>
    </defs>
    
    <!-- ==================== RAMKA ==================== -->
    <rect x="20" y="20" width="{WIDTH-40}" height="{HEIGHT-40}" fill="none" stroke="#000" stroke-width="2"/>
    <rect x="25" y="25" width="{WIDTH-50}" height="{HEIGHT-50}" fill="none" stroke="#000" stroke-width="1"/>
    
    <!-- Loyiha nomi -->
    <text x="{plan_x + plan_w/2}" y="45" text-anchor="middle" font-size="16" fill="#1e293b" font-weight="bold" letter-spacing="2">ARXITEKTURA QURILISH CHIZMASI</text>
    
    <!-- ==================== 1. PLAN (REJA) ==================== -->
    <rect x="{plan_x-15}" y="{plan_y-35}" width="{plan_w+30}" height="{plan_h+50}" fill="#fafafa" rx="3" stroke="#ccc" stroke-width="1"/>
    <text x="{plan_x + plan_w/2}" y="{plan_y-12}" text-anchor="middle" class="title">REJA · 1-QAVAT</text>
    <text x="{plan_x + plan_w/2}" y="{plan_y+2}" text-anchor="middle" class="subtitle">M 1:{max(100, int(1/scale*100))}</text>
    
    <!-- Grid -->
    <g class="grid-line">
        {''.join([f'<line x1="{plan_x + i*scale}" y1="{plan_y}" x2="{plan_x + i*scale}" y2="{plan_y + plan_h}"/>' for i in range(0, int(L)+1)])}
        {''.join([f'<line x1="{plan_x}" y1="{plan_y + i*scale}" x2="{plan_x + plan_w}" y2="{plan_y + i*scale}"/>' for i in range(0, int(W)+1)])}
    </g>
    
    <!-- Tashqi devor -->
    <rect x="{plan_x}" y="{plan_y}" width="{plan_w}" height="{plan_h}" class="wall-fill" rx="2"/>
    
    <!-- Ichki devor -->
    <rect x="{plan_x + T*scale}" y="{plan_y + T*scale}" width="{plan_w - 2*T*scale}" height="{plan_h - 2*T*scale}" fill="#fff" stroke="#9ca3af" stroke-width="1"/>
    
    <!-- Devor qalinligi -->
    <rect x="{plan_x}" y="{plan_y}" width="{T*scale}" height="{plan_h}" fill="url(#hatch-concrete)" stroke="#6b7280" stroke-width="0.5"/>
    <rect x="{plan_x + plan_w - T*scale}" y="{plan_y}" width="{T*scale}" height="{plan_h}" fill="url(#hatch-concrete)" stroke="#6b7280" stroke-width="0.5"/>
    <rect x="{plan_x}" y="{plan_y}" width="{plan_w}" height="{T*scale}" fill="url(#hatch-concrete)" stroke="#6b7280" stroke-width="0.5"/>
    <rect x="{plan_x}" y="{plan_y + plan_h - T*scale}" width="{plan_w}" height="{T*scale}" fill="url(#hatch-concrete)" stroke="#6b7280" stroke-width="0.5"/>
    
    <!-- KAMERALAR -->
    {''.join([f'''
    <rect x="{plan_x + ch['x']*scale + T*scale}" y="{plan_y + ch['y']*scale + T*scale}" width="{ch['w']*scale - 2*T*scale}" height="{ch['h']*scale - 2*T*scale}" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5" stroke-dasharray="5,3"/>
    <text x="{plan_x + (ch['x'] + ch['w']/2)*scale}" y="{plan_y + (ch['y'] + ch['h']/2)*scale + 5}" text-anchor="middle" font-size="11" fill="#1e40af" font-weight="bold">KAMERA {ch['id']}</text>
    <text x="{plan_x + (ch['x'] + ch['w']/2)*scale}" y="{plan_y + (ch['y'] + ch['h']/2)*scale + 20}" text-anchor="middle" class="label">{ch['w']:.1f} x {ch['h']:.1f} m</text>
    
    <!-- Eshik -->
    <line x1="{plan_x + (ch['x'] + ch['w']/2 - 0.5)*scale}" y1="{plan_y + ch['y']*scale}" x2="{plan_x + (ch['x'] + ch['w']/2 + 0.5)*scale}" y2="{plan_y + ch['y']*scale}" stroke="#059669" stroke-width="2.5"/>
    <path d="M {plan_x + (ch['x'] + ch['w']/2 - 0.5)*scale} {plan_y + ch['y']*scale} Q {plan_x + (ch['x'] + ch['w']/2 - 0.5)*scale} {plan_y + ch['y']*scale - 15} {plan_x + (ch['x'] + ch['w']/2)*scale} {plan_y + ch['y']*scale}" fill="none" stroke="#059669" stroke-width="1.2" stroke-dasharray="3,2"/>
    ''' for ch in chambers])}
    
    <!-- YO'LAK -->
    {f'''
    <rect x="{plan_x + corridor['x']*scale}" y="{plan_y + corridor['y']*scale}" width="{corridor['w']*scale}" height="{corridor['h']*scale}" fill="#fefce8" fill-opacity="0.6" stroke="#eab308" stroke-width="2" stroke-dasharray="6,3"/>
    <text x="{plan_x + (corridor['x'] + corridor['w']/2)*scale}" y="{plan_y + corridor['h']*scale/2 + 5}" text-anchor="middle" font-size="12" fill="#ca8a04" font-weight="bold">YO'LAK</text>
    <text x="{plan_x + (corridor['x'] + corridor['w']/2)*scale}" y="{plan_y + corridor['h']*scale/2 + 22}" text-anchor="middle" class="label">B = {corridor['w']:.1f} m</text>
    ''' if corridor else ''}
    
    <!-- O'lchamlar -->
    <line x1="{plan_x}" y1="{plan_y + plan_h + 22}" x2="{plan_x + plan_w}" y2="{plan_y + plan_h + 22}" class="dim-line"/>
    <text x="{plan_x + plan_w/2}" y="{plan_y + plan_h + 38}" text-anchor="middle" class="dim-text">{L:.2f} m</text>
    
    <line x1="{plan_x - 32}" y1="{plan_y}" x2="{plan_x - 32}" y2="{plan_y + plan_h}" class="dim-line"/>
    <text x="{plan_x - 48}" y="{plan_y + plan_h/2}" text-anchor="middle" class="dim-text" transform="rotate(-90, {plan_x - 48}, {plan_y + plan_h/2})">{W:.2f} m</text>
    
    <!-- ==================== 2. KESIM ==================== -->
    <rect x="{kesim_x-15}" y="{kesim_y-35}" width="{kesim_w+30}" height="{kesim_h+50}" fill="#fafafa" rx="3" stroke="#ccc" stroke-width="1"/>
    <text x="{kesim_x + kesim_w/2}" y="{kesim_y-12}" text-anchor="middle" class="title">KESIM A-A</text>
    <text x="{kesim_x + kesim_w/2}" y="{kesim_y+2}" text-anchor="middle" class="subtitle">M 1:{max(100, int(1/scale*100))}</text>
    
    <!-- Kesim chizig'i -->
    <line x1="{plan_x}" y1="{plan_y + plan_h/2}" x2="{plan_x + plan_w}" y2="{plan_y + plan_h/2}" class="section-line"/>
    <circle cx="{plan_x}" cy="{plan_y + plan_h/2}" r="4" fill="#dc2626"/>
    <text x="{plan_x - 10}" y="{plan_y + plan_h/2 + 3}" font-size="9" fill="#dc2626" font-weight="bold">A</text>
    <circle cx="{plan_x + plan_w}" cy="{plan_y + plan_h/2}" r="4" fill="#dc2626"/>
    <text x="{plan_x + plan_w + 4}" y="{plan_y + plan_h/2 + 3}" font-size="9" fill="#dc2626" font-weight="bold">A</text>
    
    <!-- Poydevor -->
    <rect x="{kesim_x - 10}" y="{kesim_y + kesim_h - 15}" width="{kesim_w + 20}" height="15" fill="url(#hatch-concrete)" stroke="#6b7280" stroke-width="1.5"/>
    <text x="{kesim_x + kesim_w/2}" y="{kesim_y + kesim_h - 18}" text-anchor="middle" font-size="8" fill="#4b5563">BETON POYDEVOR</text>
    
    <!-- Zamin -->
    <rect x="{kesim_x}" y="{kesim_y + kesim_h - T*scale}" width="{kesim_w}" height="{T*scale}" fill="url(#hatch-concrete)" stroke="#6b7280" stroke-width="1"/>
    
    <!-- Devorlar -->
    <rect x="{kesim_x}" y="{kesim_y}" width="{T*scale}" height="{kesim_h}" fill="url(#hatch-insulation)" stroke="#6b7280" stroke-width="1"/>
    <rect x="{kesim_x + kesim_w - T*scale}" y="{kesim_y}" width="{T*scale}" height="{kesim_h}" fill="url(#hatch-insulation)" stroke="#6b7280" stroke-width="1"/>
    
    <!-- Patalok -->
    <rect x="{kesim_x}" y="{kesim_y}" width="{kesim_w}" height="{T*scale}" fill="url(#hatch-insulation)" stroke="#6b7280" stroke-width="1"/>
    
    <!-- Tom qiyaligi -->
    <polygon points="{kesim_x + kesim_w/2 - 50},{kesim_y - 35} {kesim_x + kesim_w/2},{kesim_y - 60} {kesim_x + kesim_w/2 + 50},{kesim_y - 35}" fill="#e5e7eb" stroke="#9ca3af" stroke-width="1.5"/>
    
    <!-- Ichki belgi -->
    <text x="{kesim_x + kesim_w/2}" y="{kesim_y + kesim_h/2}" text-anchor="middle" font-size="24" fill="#3b82f6"></text>
    <text x="{kesim_x + kesim_w/2}" y="{kesim_y + kesim_h/2 + 20}" text-anchor="middle" class="label">SOVUTISH KAMERASI</text>
    
    <!-- O'lchamlar -->
    <line x1="{kesim_x - 32}" y1="{kesim_y}" x2="{kesim_x - 32}" y2="{kesim_y + kesim_h}" class="dim-line"/>
    <text x="{kesim_x - 48}" y="{kesim_y + kesim_h/2}" text-anchor="middle" class="dim-text" transform="rotate(-90, {kesim_x - 48}, {kesim_y + kesim_h/2})">H = {H:.2f} m</text>
    
    <!-- ==================== 3. FASAD ==================== -->
    <rect x="{fasad_x-15}" y="{fasad_y-35}" width="{fasad_w+30}" height="{fasad_h+50}" fill="#fafafa" rx="3" stroke="#ccc" stroke-width="1"/>
    <text x="{fasad_x + fasad_w/2}" y="{fasad_y-12}" text-anchor="middle" class="title">FASAD · OLD KO'RINISH</text>
    <text x="{fasad_x + fasad_w/2}" y="{fasad_y+2}" text-anchor="middle" class="subtitle">M 1:{max(100, int(1/scale*100))}</text>
    
    <!-- Asosiy blok -->
    <rect x="{fasad_x}" y="{fasad_y}" width="{fasad_w}" height="{fasad_h}" fill="#f3f4f6" stroke="#374151" stroke-width="2.5"/>
    
    <!-- Panel chiziqlari -->
    <g stroke="#d1d5db" stroke-width="1" stroke-dasharray="4,3">
        {''.join([f'<line x1="{fasad_x + i*1.16*scale}" y1="{fasad_y}" x2="{fasad_x + i*1.16*scale}" y2="{fasad_y + fasad_h}"/>' for i in range(1, int(L/1.16)+1)])}
    </g>
    
    <!-- Eshik -->
    <rect x="{fasad_x + fasad_w*0.32}" y="{fasad_y + fasad_h*0.55}" width="{fasad_w*0.36}" height="{fasad_h*0.4}" class="door-fill" rx="2"/>
    <line x1="{fasad_x + fasad_w*0.5}" y1="{fasad_y + fasad_h*0.55}" x2="{fasad_x + fasad_w*0.5}" y2="{fasad_y + fasad_h*0.95}" stroke="#059669" stroke-width="2"/>
    <text x="{fasad_x + fasad_w/2}" y="{fasad_y + fasad_h*0.52}" text-anchor="middle" font-size="8" fill="#059669">IKKI QANOTLI ESHIK</text>
    
    <!-- Derazalar -->
    <rect x="{fasad_x + fasad_w*0.75}" y="{fasad_y + fasad_h*0.15}" width="{fasad_w*0.12}" height="{fasad_h*0.28}" class="window-fill" rx="1"/>
    <rect x="{fasad_x + fasad_w*0.88}" y="{fasad_y + fasad_h*0.15}" width="{fasad_w*0.08}" height="{fasad_h*0.28}" class="window-fill" rx="1"/>
    
    <!-- O'lchamlar -->
    <line x1="{fasad_x}" y1="{fasad_y + fasad_h + 32}" x2="{fasad_x + fasad_w}" y2="{fasad_y + fasad_h + 32}" class="dim-line"/>
    <text x="{fasad_x + fasad_w/2}" y="{fasad_y + fasad_h + 48}" text-anchor="middle" class="dim-text">L = {L:.2f} m</text>
    
    <line x1="{fasad_x - 32}" y1="{fasad_y}" x2="{fasad_x - 32}" y2="{fasad_y + fasad_h}" class="dim-line"/>
    <text x="{fasad_x - 48}" y="{fasad_y + fasad_h/2}" text-anchor="middle" class="dim-text" transform="rotate(-90, {fasad_x - 48}, {fasad_y + fasad_h/2})">H = {H:.2f} m</text>
    
    <!-- ==================== TEXNIK MA'LUMOTLAR ==================== -->
    <g transform="translate(60, {HEIGHT-180})">
        <rect x="0" y="0" width="{WIDTH-120}" height="100" fill="#fff" stroke="#ccc" stroke-width="1" rx="4"/>
        <rect x="0" y="0" width="{WIDTH-120}" height="22" fill="#1e293b" rx="4"/>
        <text x="{(WIDTH-120)/2}" y="15" text-anchor="middle" font-size="11" fill="#fff" font-weight="bold">TEXNIK MA'LUMOTLAR</text>
        
        <text x="15" y="40" font-size="9" fill="#1f2937"> Tashqi o'lcham:</text>
        <text x="120" y="40" font-size="9" fill="#4b5563">{L:.2f} x {W:.2f} x {H:.2f} m</text>
        
        <text x="320" y="40" font-size="9" fill="#1f2937"> Devor qalinligi:</text>
        <text x="420" y="40" font-size="9" fill="#4b5563">{wall_mm} mm (PUR)</text>
        
        <text x="600" y="40" font-size="9" fill="#1f2937"> Sana:</text>
        <text x="660" y="40" font-size="9" fill="#4b5563">{datetime.now().strftime("%d.%m.%Y")}</text>
        
        <text x="15" y="58" font-size="9" fill="#1f2937"> Kameralar soni:</text>
        <text x="120" y="58" font-size="9" fill="#4b5563">{n_chambers} ta</text>
        
        <text x="320" y="58" font-size="9" fill="#1f2937"> Eshiklar soni:</text>
        <text x="420" y="58" font-size="9" fill="#4b5563">{n_chambers} ta</text>
        
        <text x="600" y="58" font-size="9" fill="#1f2937"> Panel moduli:</text>
        <text x="660" y="58" font-size="9" fill="#4b5563">1.16 m</text>
        
        <text x="15" y="76" font-size="9" fill="#1f2937"> Ish harorati:</text>
        <text x="120" y="76" font-size="9" fill="#4b5563">-25°C dan +5°C gacha</text>
        
        <text x="320" y="76" font-size="9" fill="#1f2937"> Hajm:</text>
        <text x="420" y="76" font-size="9" fill="#4b5563">{L*W*H:.1f} m³</text>
        
        <text x="600" y="76" font-size="9" fill="#1f2937"> Masshtab:</text>
        <text x="660" y="76" font-size="9" fill="#4b5563">1:{max(100, int(1/scale*100))}</text>
    </g>
    
  
</svg>'''
    
    return svg

def draw_svg(svg, height=3080):
    components.html(
        f'<div style="width:100%;background:#dcdcdc;padding:16px;overflow:auto;border-radius:12px;">{svg}</div>',
        height=height, scrolling=True
    )

def svgt(x,y,text,size=10,weight="normal",anchor="middle",rotate=None,color="#111"):
    rot=f' transform="rotate({rotate} {x},{y})"' if rotate is not None else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}"{rot}>{text}</text>'
def dim_h(x1, x2, y, text, color="#222", ext=6, size=9):
    """Gorizontal o'lcham chizig'i"""
    return f"""<g stroke="{color}" fill="none" stroke-width="0.8">
  <line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"/>
  <line x1="{x1}" y1="{y-ext}" x2="{x1}" y2="{y+ext}"/>
  <line x1="{x2}" y1="{y-ext}" x2="{x2}" y2="{y+ext}"/>
  <polygon points="{x1},{y} {x1+4},{y-2} {x1+4},{y+2}" fill="{color}"/>
  <polygon points="{x2},{y} {x2-4},{y-2} {x2-4},{y+2}" fill="{color}"/>
</g><text x="{(x1+x2)/2}" y="{y-6}" font-size="{size}" text-anchor="middle" fill="{color}" font-weight="600">{text}</text>"""

def dim_v(x,y1,y2,text,color="#222",ext=6,size=9):
    cy=(y1+y2)/2
    return f"""<g stroke="{color}" fill="none" stroke-width="0.8">
  <line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}"/>
  <line x1="{x-ext}" y1="{y1}" x2="{x+ext}" y2="{y1}"/>
  <line x1="{x-ext}" y1="{y2}" x2="{x+ext}" y2="{y2}"/>
  <polygon points="{x},{y1} {x-2},{y1+4} {x+2},{y1+4}" fill="{color}"/>
  <polygon points="{x},{y2} {x-2},{y2-4} {x+2},{y2-4}" fill="{color}"/>
</g><text x="{x+12}" y="{cy}" font-size="{size}" text-anchor="middle" fill="{color}" transform="rotate(90 {x+12},{cy})">{text}</text>"""
def chain_bottom(x, y, parts, scale, color="#222", fs=6):
    """Past tomondan gorizontal o'lcham"""
    svg = ""
    total = sum(p["size"] for p in parts)
    svg += dim_h(x, x + total * scale, y + 18, str(total), color=color, size=max(fs, 8))
    cur = x
    for p in parts:
        nx = cur + p["size"] * scale
        label = f'{p["size"]} ' if p["type"] == "door" else str(p["size"])
        svg += (
            f'<line x1="{cur}" y1="{y}" x2="{cur}" y2="{y+fs}" stroke="{color}" stroke-width="0.8"/>'
            f'<line x1="{nx}" y1="{y}" x2="{nx}" y2="{y+fs}" stroke="{color}" stroke-width="0.8"/>'
            f'<line x1="{cur}" y1="{y}" x2="{nx}" y2="{y}" stroke="{color}" stroke-width="0.8"/>'
            f'<text x="{(cur+nx)/2}" y="{y+fs*1.8}" font-size="{fs}" text-anchor="middle" fill="{color}">{label}</text>'
        )
        cur = nx
    return svg
def chain_left(x, y, parts, scale, color="#222", fs=6):
    """Chap tomondan vertikal o'lcham"""
    svg = ""
    total = sum(p["size"] for p in parts)
    svg += dim_v(x - 18, y, y + total * scale, str(total), color=color, size=max(fs, 8))
    cur = y
    for p in parts:
        ny = cur + p["size"] * scale
        label = f'{p["size"]} ' if p["type"] == "door" else str(p["size"])
        mid = (cur + ny) / 2
        svg += (
            f'<line x1="{x}" y1="{cur}" x2="{x-fs}" y2="{cur}" stroke="{color}" stroke-width="0.8"/>'
            f'<line x1="{x}" y1="{ny}" x2="{x-fs}" y2="{ny}" stroke="{color}" stroke-width="0.8"/>'
            f'<line x1="{x}" y1="{cur}" x2="{x}" y2="{ny}" stroke="{color}" stroke-width="0.8"/>'
            f'<text x="{x-fs*1.8}" y="{mid}" font-size="{fs}" text-anchor="middle" fill="{color}" transform="rotate(-90, {x-fs*1.8}, {mid})">{label}</text>'
        )
        cur = ny
    return svg

def chain_top(x, y, parts, scale, color="#222", fs=6):
    svg = ""
    total = sum(p["size"] for p in parts)
    svg += dim_h(x, x + total * scale, y - 18, str(total), color=color, size=max(fs, 8))
    cur = x
    for p in parts:
        nx = cur + p["size"] * scale
        label = f'{p["size"]} ' if p["type"] == "door" else str(p["size"])
        svg += (
            f'<line x1="{cur}" y1="{y}" x2="{cur}" y2="{y-fs}" stroke="{color}" stroke-width="0.8"/>'
            f'<line x1="{nx}" y1="{y}" x2="{nx}" y2="{y-fs}" stroke="{color}" stroke-width="0.8"/>'
            f'<line x1="{cur}" y1="{y}" x2="{nx}" y2="{y}" stroke="{color}" stroke-width="0.8"/>'
            f'<text x="{(cur+nx)/2}" y="{y-fs*0.5}" font-size="{fs}" text-anchor="middle" fill="{color}">{label}</text>'
        )
        cur = nx
    return svg

def chain_right(x, y, parts, scale, color="#222", fs=6):
    svg = ""
    total = sum(p["size"] for p in parts)
    svg += dim_v(x + fs * 3, y, y + total * scale, str(total), color=color, size=max(fs, 8))
    cur = y
    for p in parts:
        ny = cur + p["size"] * scale
        label = f'{p["size"]} ' if p["type"] == "door" else str(p["size"])
        mid = (cur + ny) / 2
        svg += (
            f'<line x1="{x}" y1="{cur}" x2="{x+fs}" y2="{cur}" stroke="{color}" stroke-width="0.8"/>'
            f'<line x1="{x}" y1="{ny}" x2="{x+fs}" y2="{ny}" stroke="{color}" stroke-width="0.8"/>'
            f'<line x1="{x}" y1="{cur}" x2="{x}" y2="{ny}" stroke="{color}" stroke-width="0.8"/>'
            f'<text x="{x+fs*1.8}" y="{mid}" font-size="{fs}" text-anchor="middle" fill="{color}" '
            f'transform="rotate(90 {x+fs*1.8},{mid})">{label}</text>'
        )
        cur = ny
    return svg

def ticks_h(x,y,parts,scale,color="#111"):
    svg=""; cur=x
    for p in parts[:-1]: cur+=p["size"]*scale; svg+=f'<line x1="{cur}" y1="{y-3}" x2="{cur}" y2="{y+3}" stroke="{color}" stroke-width="0.6"/>'
    return svg

def ticks_v(x,y,parts,scale,color="#111"):
    svg=""; cur=y
    for p in parts[:-1]: cur+=p["size"]*scale; svg+=f'<line x1="{x-3}" y1="{cur}" x2="{x+3}" y2="{cur}" stroke="{color}" stroke-width="0.6"/>'
    return svg

def build_segs(total_mm,corner=480,mod=960):
    if total_mm<=0: return []
    if total_mm<=corner*2: return [total_mm]
    c=total_mm-corner*2; parts=[]
    while c>mod: parts.append(mod); c-=mod
    if c>0: parts.append(c)
    return [corner]+parts+[corner]

def seg_meta(parts,has_door=False,door_sz=960):
    res=[]; used=False
    for p in parts:
        if has_door and not used and p==door_sz: res.append({"size":p,"type":"door"}); used=True
        else: res.append({"size":p,"type":"panel"})
    return res

def room_plan(x,y,ow,oh,wt):
    ix,iy=x+wt,y+wt; iw,ih=ow-2*wt,oh-2*wt
    return (f'<rect x="{x}" y="{y}" width="{ow}" height="{oh}" fill="rgba(220,232,255,0.15)" stroke="#111" stroke-width="2"/>'
            f'<rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" fill="rgba(235,245,255,0.4)" stroke="#555" stroke-width="1" stroke-dasharray="5,3"/>')

def slab_svg(x, y, ow, oh, hmeta, vmeta, scale, label, ls=9):
    s = (f'<rect x="{x}" y="{y}" width="{ow}" height="{oh}" fill="rgba(240,246,255,0.65)" stroke="#111" stroke-width="1.4"/>')
    cx = x
    for p in hmeta[:-1]:
        cx += p["size"] * scale
        s += f'<line x1="{cx}" y1="{y}" x2="{cx}" y2="{y+oh}" stroke="#8898A8" stroke-width="0.6" stroke-dasharray="4,2"/>'
    cy = y
    for p in vmeta[:-1]:
        cy += p["size"] * scale
        s += f'<line x1="{x}" y1="{cy}" x2="{x+ow}" y2="{cy}" stroke="#8898A8" stroke-width="0.6" stroke-dasharray="4,2"/>'
    s += svgt(x + ow / 2, y - ls, label, size=ls, weight="700")
    return s
def arc_left(x, y, scale, off, dh=2000, dw=960, op="Ichkariga"):
    """Chap devorda eshik chizish"""
    top = y + off * scale
    r = dw * scale
    
    print(f"  arc_left: x={x}, y={y}, off={off}, scale={scale}")
    print(f"  top={top}, r={r}, dh={dh}")
    
    # Eshik ramkasi (ko'rinadigan qilib)
    frame = f'<rect x="{x-2}" y="{top-2}" width="4" height="{r+4}" fill="none" stroke="#1a1a2e" stroke-width="2"/>'
    
    # Eshik paneli (ochiq rang)
    door_panel = f'<rect x="{x-1}" y="{top+1}" width="2" height="{r-2}" fill="#e2e8f0" stroke="#64748b" stroke-width="1"/>'
    
    gap = f'<rect x="{x-2}" y="{top}" width="5" height="{r}" fill="white" stroke="none"/>'
    leaf = f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top+r}" stroke="#059669" stroke-width="3"/>'
    
    if op == "Ichkariga":
        arc = f'<path d="M {x} {top+r} A {r} {r} 0 0 1 {x+r} {top}" fill="none" stroke="#059669" stroke-width="2" stroke-dasharray="6,4"/>'
        oln = f'<line x1="{x}" y1="{top}" x2="{x+r}" y2="{top}" stroke="#059669" stroke-width="2"/>'
    else:
        arc = f'<path d="M {x} {top+r} A {r} {r} 0 0 0 {x-r} {top}" fill="none" stroke="#059669" stroke-width="2" stroke-dasharray="6,4"/>'
        oln = f'<line x1="{x}" y1="{top}" x2="{x-r}" y2="{top}" stroke="#059669" stroke-width="2"/>'
    
    # Eshik tutqichi
    handle = f'<circle cx="{x+2}" cy="{top + r/2}" r="3" fill="#f59e0b" stroke="#d97706" stroke-width="1"/>'
    
    return frame + door_panel + gap + leaf + arc + oln + handle

def arc_right(x, y, ow, scale, off, dh=2000, dw=960, op="Ichkariga"):
    rx = x + ow
    top = y + off * scale
    r = dw * scale
    gap = f'<rect x="{rx-3}" y="{top}" width="5" height="{r}" fill="white" stroke="none"/>'
    leaf = f'<line x1="{rx}" y1="{top}" x2="{rx}" y2="{top+r}" stroke="#111" stroke-width="2.5"/>'
    if op == "Ichkariga":
        arc = f'<path d="M {rx} {top+r} A {r} {r} 0 0 0 {rx-r} {top}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln = f'<line x1="{rx}" y1="{top}" x2="{rx-r}" y2="{top}" stroke="#111" stroke-width="1.5"/>'
    else:
        arc = f'<path d="M {rx} {top+r} A {r} {r} 0 0 1 {rx+r} {top}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln = f'<line x1="{rx}" y1="{top}" x2="{rx+r}" y2="{top}" stroke="#111" stroke-width="1.5"/>'
    return gap + leaf + arc + oln

def arc_bottom(x, y, oh, scale, off, dw=960, op="Ichkariga"):
    by = y + oh
    left = x + off * scale
    r = dw * scale
    gap = f'<rect x="{left}" y="{by-2}" width="{r}" height="5" fill="white" stroke="none"/>'
    leaf = f'<line x1="{left}" y1="{by}" x2="{left+r}" y2="{by}" stroke="#111" stroke-width="2.5"/>'
    if op == "Ichkariga":
        arc = f'<path d="M {left} {by} A {r} {r} 0 0 0 {left+r} {by-r}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln = f'<line x1="{left+r}" y1="{by}" x2="{left+r}" y2="{by-r}" stroke="#111" stroke-width="1.5"/>'
    else:
        arc = f'<path d="M {left} {by} A {r} {r} 0 0 1 {left+r} {by+r}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln = f'<line x1="{left+r}" y1="{by}" x2="{left+r}" y2="{by+r}" stroke="#111" stroke-width="1.5"/>'
    return gap + leaf + arc + oln

def arc_top(x, y, scale, off, dw=960, op="Ichkariga"):
    left = x + off * scale
    r = dw * scale
    gap = f'<rect x="{left}" y="{y-3}" width="{r}" height="5" fill="white" stroke="none"/>'
    leaf = f'<line x1="{left}" y1="{y}" x2="{left+r}" y2="{y}" stroke="#111" stroke-width="2.5"/>'
    if op == "Ichkariga":
        arc = f'<path d="M {left} {y} A {r} {r} 0 0 1 {left+r} {y+r}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln = f'<line x1="{left+r}" y1="{y}" x2="{left+r}" y2="{y+r}" stroke="#111" stroke-width="1.5"/>'
    else:
        arc = f'<path d="M {left} {y} A {r} {r} 0 0 0 {left+r} {y-r}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln = f'<line x1="{left+r}" y1="{y}" x2="{left+r}" y2="{y-r}" stroke="#111" stroke-width="1.5"/>'
    return gap + leaf + arc + oln

def title_block(x, y, w, h, proj, code, Lmm, Wmm, Hmm, wall, ceil, floor, date):
    c2, c3 = x+260, x+430
    return f"""<g>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1" rx="4"/>
    <rect x="{x}" y="{y}" width="{w}" height="24" fill="#1e293b" rx="4"/>
    <rect x="{x}" y="{y+12}" width="{w}" height="12" fill="#1e293b"/>
    <text x="{x+w/2}" y="{y+16}" font-size="11" fill="white" text-anchor="middle" font-weight="bold" font-family="Arial">ASOSIY MA'LUMOTLAR</text>
    
    <text x="{x+15}" y="{y+38}" font-size="9" fill="#1f2937" font-family="Arial">Loyiha:</text>
    <text x="{x+80}" y="{y+38}" font-size="9" fill="#0f172a" font-weight="600" font-family="Arial">{proj}</text>
    
    <text x="{x+15}" y="{y+54}" font-size="9" fill="#1f2937" font-family="Arial">Kod:</text>
    <text x="{x+80}" y="{y+54}" font-size="9" fill="#0f172a" font-weight="600" font-family="Arial">{code}</text>
    
    <text x="{x+200}" y="{y+38}" font-size="9" fill="#1f2937" font-family="Arial">Sana:</text>
    <text x="{x+260}" y="{y+38}" font-size="9" fill="#0f172a" font-weight="600" font-family="Arial">{date}</text>
    
    <text x="{x+200}" y="{y+54}" font-size="9" fill="#1f2937" font-family="Arial">Masshtab:</text>
    <text x="{x+260}" y="{y+54}" font-size="9" fill="#0f172a" font-weight="600" font-family="Arial">1:50</text>
    
    <text x="{x+400}" y="{y+38}" font-size="9" fill="#1f2937" font-family="Arial">Olcham:</text>
    <text x="{x+460}" y="{y+38}" font-size="9" fill="#0f172a" font-weight="600" font-family="Arial">{Lmm}x{Wmm}x{Hmm} mm</text>
    
    <text x="{x+400}" y="{y+54}" font-size="9" fill="#1f2937" font-family="Arial">Devor:</text>
    <text x="{x+460}" y="{y+54}" font-size="9" fill="#0f172a" font-weight="600" font-family="Arial">{wall} mm</text>
</g>"""
def arc_right(x,y,ow,scale,off,dh=2000,dw=960,op="Ichkariga"):
    rx=x+ow; top=y+off*scale; r=dw*scale
    gap=f'<rect x="{rx-3}" y="{top}" width="5" height="{r}" fill="white" stroke="none"/>'
    leaf=f'<line x1="{rx}" y1="{top}" x2="{rx}" y2="{top+r}" stroke="#111" stroke-width="2.5"/>'
    if op=="Ichkariga":
        arc=f'<path d="M {rx} {top+r} A {r} {r} 0 0 0 {rx-r} {top}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln=f'<line x1="{rx}" y1="{top}" x2="{rx-r}" y2="{top}" stroke="#111" stroke-width="1.5"/>'
    else:
        arc=f'<path d="M {rx} {top+r} A {r} {r} 0 0 1 {rx+r} {top}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln=f'<line x1="{rx}" y1="{top}" x2="{rx+r}" y2="{top}" stroke="#111" stroke-width="1.5"/>'
    return gap+leaf+arc+oln

def arc_bottom(x,y,oh,scale,off,dw=960,op="Ichkariga"):
    by=y+oh; left=x+off*scale; r=dw*scale
    gap=f'<rect x="{left}" y="{by-2}" width="{r}" height="5" fill="white" stroke="none"/>'
    leaf=f'<line x1="{left}" y1="{by}" x2="{left+r}" y2="{by}" stroke="#111" stroke-width="2.5"/>'
    if op=="Ichkariga":
        arc=f'<path d="M {left} {by} A {r} {r} 0 0 0 {left+r} {by-r}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln=f'<line x1="{left+r}" y1="{by}" x2="{left+r}" y2="{by-r}" stroke="#111" stroke-width="1.5"/>'
    else:
        arc=f'<path d="M {left} {by} A {r} {r} 0 0 1 {left+r} {by+r}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln=f'<line x1="{left+r}" y1="{by}" x2="{left+r}" y2="{by+r}" stroke="#111" stroke-width="1.5"/>'
    return gap+leaf+arc+oln

def arc_top(x,y,scale,off,dw=960,op="Ichkariga"):
    left=x+off*scale; r=dw*scale
    gap=f'<rect x="{left}" y="{y-3}" width="{r}" height="5" fill="white" stroke="none"/>'
    leaf=f'<line x1="{left}" y1="{y}" x2="{left+r}" y2="{y}" stroke="#111" stroke-width="2.5"/>'
    if op=="Ichkariga":
        arc=f'<path d="M {left} {y} A {r} {r} 0 0 1 {left+r} {y+r}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln=f'<line x1="{left+r}" y1="{y}" x2="{left+r}" y2="{y+r}" stroke="#111" stroke-width="1.5"/>'
    else:
        arc=f'<path d="M {left} {y} A {r} {r} 0 0 0 {left+r} {y-r}" fill="none" stroke="#111" stroke-width="1" stroke-dasharray="4,3"/>'
        oln=f'<line x1="{left+r}" y1="{y}" x2="{left+r}" y2="{y-r}" stroke="#111" stroke-width="1.5"/>'
    return gap+leaf+arc+oln

def title_block(x,y,w,h,proj,code,Lmm,Wmm,Hmm,wall,ceil,floor,date):
    c2,c3=x+260,x+430
    return f"""<g>

</g>"""

C = {
    "wf":"#F2F6FA","ws":"#EDF3F8","fl":"#D8E2EE","cl":"#E8F0FF",
    "sm":"#A8B8C8","eg":"#8898A8","df":"#1A202C","dl":"#2D3748",
    "dh":"#718096","ab":"#7B1C1C","ag":"#6B1515","ap":"#374151",
    "dim":"#1A202C","gm":"#D4DCE6","gM":"#BCC8D4",
    "corridor":"#F9FAFB",
    "comp_body":"#1C3557",
    "comp_panel":"#22466E",
    "comp_fan":"#2563EB",
    "comp_pipe_liq":"#DC2626",
    "comp_pipe_gas":"#2563EB",
    "comp_base":"#374151",
    "comp_logo":"#93C5FD",
    "evap":"#D1D5DB",
    "evap_fin":"#9CA3AF",
}
def door_off(parts, pos, side="vertical", dsz=960):
    """
    Eshik ofsetini hisoblaydi - 5 VARIANT BILAN
    BURCHAK PANELLARINI (480) HISOBGA OLMAYDI!
    
    parts: devor segmentlari ro'yxati (mm da)
    pos: pozitsiya ("Chap tomon burchak o'rniga", "Biroz chapga", "O'rta", "Biroz o'ngga", "O'ng tomon burchak o'rniga")
    side: "vertical" yoki "horizontal"
    dsz: eshik kengligi (mm)
    """
    if not parts:
        return 0
    
    # ===== 1. BURCHAK PANELLARINI ANIQLASH =====
    # 480 mm burchak panellarini hisobdan chiqaramiz
    main_parts = [p for p in parts if p != 480]
    
    # Agar barchasi burchak paneli bo'lsa (480)
    if not main_parts:
        # Burchak panellarining umumiy uzunligi
        total = sum(parts)
        door_width = min(dsz, total)
        if pos == "Chap tomon burchak o'rniga":
            return 0
        elif pos == "O'ng tomon burchak o'rniga":
            return total - door_width
        else:
            return (total - door_width) / 2
    
    # ===== 2. ASOSIY PANELLAR UZUNLIGI =====
    main_total = sum(main_parts)
    door_width = min(dsz, main_total)
    
    # ===== 3. BURCHAK PANELLARINING JOYLASHUVI =====
    # Chap burchak paneli borligini tekshiramiz
    has_left_corner = parts[0] == 480 if parts else False
    # O'ng burchak paneli borligini tekshiramiz
    has_right_corner = parts[-1] == 480 if parts else False
    
    # Chap burchak panelining kengligi
    left_corner_size = parts[0] if has_left_corner else 0
    # O'ng burchak panelining kengligi
    right_corner_size = parts[-1] if has_right_corner else 0
    
    # ===== 4. ESHIK OFSETINI HISOBLASH =====
    if pos == "Chap tomon burchak o'rniga":
        # Chap burchakda - chap burchak panelining oxiridan boshlab
        return left_corner_size
    
    elif pos == "Biroz chapga":
        # Chap burchakdan 300 mm keyin
        return left_corner_size + 300
    
    elif pos == "O'rta":
        # ASOSIY PANELLARNING O'RTASIDA - aniq markazda!
        # Eshik faqat asosiy panellar oralig'ida bo'ladi
        offset_in_main = (main_total - door_width) / 2
        return left_corner_size + offset_in_main
    
    elif pos == "Biroz o'ngga":
        # O'ng burchakdan 300 mm oldin
        return left_corner_size + main_total - door_width - 300
    
    elif pos == "O'ng tomon burchak o'rniga":
        # O'ng burchakda - o'ng burchak panelining boshidan
        return left_corner_size + main_total - door_width
    
    else:
        # Default: o'rta
        offset_in_main = (main_total - door_width) / 2
        return left_corner_size + offset_in_main



def box3d(fig,x,y,z,dx,dy,dz,color,name="",opacity=1.0,ec=None):
    ec=ec or C["eg"]
    vx=[x,x+dx,x+dx,x,x,x+dx,x+dx,x]
    vy=[y,y,y+dy,y+dy,y,y,y+dy,y+dy]
    vz=[z,z,z,z,z+dz,z+dz,z+dz,z+dz]
    fig.add_trace(go.Mesh3d(
        x=vx,y=vy,z=vz,
        i=[7,0,0,0,4,4,6,6,4,0,3,2],
        j=[3,4,1,2,5,6,5,2,0,1,6,3],
        k=[0,7,2,3,6,7,1,1,5,5,7,6],
        color=color,opacity=opacity,flatshading=True,
        lighting=dict(ambient=0.78,diffuse=0.58,specular=0.10,roughness=0.85),
        name=name,hoverinfo="text",text=name,showlegend=False
    ))
    edges=[(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    ex,ey,ez=[],[],[]
    for a,b in edges:
        ex+=[vx[a],vx[b],None]; ey+=[vy[a],vy[b],None]; ez+=[vz[a],vz[b],None]
    fig.add_trace(go.Scatter3d(x=ex,y=ey,z=ez,mode="lines",
        line=dict(color=ec,width=1.2),hoverinfo="skip",showlegend=False))

def ln3(fig,x1,y1,z1,x2,y2,z2,color="#555",w=1.2):
    fig.add_trace(go.Scatter3d(x=[x1,x2],y=[y1,y2],z=[z1,z2],mode="lines",
        line=dict(color=color,width=w),hoverinfo="skip",showlegend=False))

def tx3(fig,x,y,z,text,sz=10,color="#1A202C"):
    fig.add_trace(go.Scatter3d(x=[x],y=[y],z=[z],mode="text",text=[text],
        textposition="middle center",textfont=dict(size=sz,color=color,family="Arial"),
        hoverinfo="skip",showlegend=False))

def cylinder3(fig, cx, cy, z_bot, z_top, radius=0.04, color="#555", n=12):
    angles = [2*math.pi*i/n for i in range(n+1)]
    for i in range(n):
        a0, a1 = angles[i], angles[i+1]
        x0, y0 = cx+radius*math.cos(a0), cy+radius*math.sin(a0)
        x1, y1 = cx+radius*math.cos(a1), cy+radius*math.sin(a1)
        ln3(fig, x0,y0,z_bot, x1,y1,z_bot, color, 1.0)
        ln3(fig, x0,y0,z_top, x1,y1,z_top, color, 1.0)
        ln3(fig, x0,y0,z_bot, x0,y0,z_top, color, 0.8)

# COMPRESSOR / CONDENSING UNIT (outdoor unit)
def draw_compressor_unit(fig, cx, cy, cz, facing, brand="Bitzer", unit_type="split"):
    if "sanoat" in unit_type.lower() or "Copeland" in brand:
        W, D, H = 1.20, 0.60, 1.00
    elif "Zanotti" in brand:
        W, D, H = 1.05, 0.55, 0.85
    else:
        W, D, H = 0.95, 0.50, 0.80

    leg_h = 0.12
    leg_t = 0.04
    box3d(fig, cx,          cy,          cz, leg_t, D, leg_h, C["comp_base"], "Poydevor", 1.0, "#1F2937")
    box3d(fig, cx+W-leg_t,  cy,          cz, leg_t, D, leg_h, C["comp_base"], "Poydevor", 1.0, "#1F2937")
    box3d(fig, cx,          cy,          cz, W, leg_t, leg_h, C["comp_base"], "Poydevor", 1.0, "#1F2937")
    box3d(fig, cx,          cy+D-leg_t,  cz, W, leg_t, leg_h, C["comp_base"], "Poydevor", 1.0, "#1F2937")

    z0 = cz + leg_h

    box3d(fig, cx, cy, z0, W, D, H, C["comp_body"], f"Kompressor: {brand}", 1.0, "#0F2744")

    louver_c = "#152B45"
    for i in range(5):
        lz = z0 + H*0.2 + i*(H*0.55/5)
        box3d(fig, cx-0.005, cy+D*0.05, lz, 0.01, D*0.90, H*0.07, louver_c, "", 1.0, "#0A1E36")
        box3d(fig, cx+W-0.005, cy+D*0.05, lz, 0.01, D*0.90, H*0.07, louver_c, "", 1.0, "#0A1E36")

    box3d(fig, cx+W*0.05, cy-0.005, z0+H*0.55, W*0.35, 0.01, H*0.30,
          C["comp_panel"], "Kontrol panel", 1.0, "#1A3A5C")
    for li, lc in enumerate(["#22C55E","#EAB308","#EF4444"]):
        fig.add_trace(go.Scatter3d(
            x=[cx+W*0.10 + li*0.06], y=[cy-0.01], z=[z0+H*0.72],
            mode='markers', marker=dict(size=5, color=lc, symbol='circle'),
            showlegend=False, hoverinfo='skip'))

    fan_grille_t = 0.025
    box3d(fig, cx+0.03, cy+0.03, z0+H, W-0.06, D-0.06, fan_grille_t,
          "#1A3A5C", "Fan grille", 1.0, "#0F2744")
    for gi in range(4):
        gx = cx + 0.05 + gi*(W-0.10)/3
        ln3(fig, gx, cy+0.03, z0+H+fan_grille_t*0.5,
               gx, cy+D-0.03, z0+H+fan_grille_t*0.5, "#0F2744", 1.0)
    for gi in range(3):
        gy = cy + 0.05 + gi*(D-0.10)/2
        ln3(fig, cx+0.03, gy, z0+H+fan_grille_t*0.5,
               cx+W-0.03, gy, z0+H+fan_grille_t*0.5, "#0F2744", 1.0)

    n_fans = 2 if W > 0.80 else 1
    for fi in range(n_fans):
        fx = cx + W/(n_fans*2) + fi*(W/n_fans)
        fy = cy + D/2
        fz = z0 + H + fan_grille_t + 0.01
        fig.add_trace(go.Scatter3d(
            x=[fx], y=[fy], z=[fz], mode='markers',
            marker=dict(size=20, color='#1E40AF', symbol='circle',
                        line=dict(width=3, color='#93C5FD')),
            showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter3d(
            x=[fx], y=[fy], z=[fz], mode='markers',
            marker=dict(size=7, color='#DBEAFE', symbol='circle'),
            showlegend=False, hoverinfo='skip'))
        for ang in range(0, 360, 60):
            r = (min(W/n_fans, D)*0.38)
            ax = fx + r*math.cos(math.radians(ang))
            ay = fy + r*math.sin(math.radians(ang))
            ln3(fig, fx,fy,fz, ax,ay,fz, "#93C5FD", 2.0)

    comp_r = min(W, D)*0.18
    comp_x = cx + W*0.70
    comp_y = cy + D*0.50
    cylinder3(fig, comp_x, comp_y, z0+leg_h, z0+H*0.45, comp_r, "#1E3A5F", 14)
    box3d(fig, comp_x-comp_r, comp_y-comp_r, z0+H*0.45,
          comp_r*2, comp_r*2, 0.04, "#0F2744", "Kompressor silindr", 1.0, "#1E3A5F")

    pipe_x_liq = cx + W*0.15
    pipe_x_gas = cx + W*0.25
    pipe_y = cy + D*0.90
    ln3(fig, pipe_x_liq, pipe_y, z0, pipe_x_liq, pipe_y, z0-0.20, C["comp_pipe_liq"], 4.0)
    ln3(fig, pipe_x_gas, pipe_y, z0, pipe_x_gas, pipe_y, z0-0.20, C["comp_pipe_gas"], 6.0)
    tx3(fig, pipe_x_liq-0.08, pipe_y, z0+0.10, "HP", sz=7, color=C["comp_pipe_liq"])
    tx3(fig, pipe_x_gas+0.08, pipe_y, z0+0.10, "LP", sz=7, color=C["comp_pipe_gas"])

    tx3(fig, cx+W/2, cy+D/2, z0+H*0.30, brand, sz=9, color=C["comp_logo"])
    tx3(fig, cx+W/2, cy+D/2, z0+H*0.18, "KOMPRESSOR", sz=7, color="#7CB9E8")

    for vx in [cx+0.06, cx+W-0.06]:
        for vy_off in [cy+0.06, cy+D-0.06]:
            box3d(fig, vx-0.025, vy_off-0.025, cz-0.02, 0.05, 0.05, 0.04,
                  "#374151", "Vibro damper", 1.0, "#1F2937")

def draw_refrigerant_pipes(fig, room_x, room_y, room_L, room_W, room_H, T,
                            comp_cx, comp_cy, comp_cz, facing):
    pipe_wall_z = room_H * 0.85
    if facing == "Old":
        wx, wy = room_L/2, 0.0
    elif facing == "Orqa":
        wx, wy = room_L/2, room_W
    elif facing == "Chap":
        wx, wy = 0.0, room_W/2
    else:
        wx, wy = room_L, room_W/2

    ln3(fig, wx,   wy,   pipe_wall_z,
           comp_cx+0.15, comp_cy+0.45, comp_cz+0.10, C["comp_pipe_liq"], 3.5)
    ln3(fig, wx+0.05, wy+0.05, pipe_wall_z,
           comp_cx+0.25, comp_cy+0.45, comp_cz+0.10, C["comp_pipe_gas"], 5.0)

    box3d(fig, wx-0.04, wy-0.04, pipe_wall_z-0.05,
          0.08, 0.08, 0.12, "#6B7280", "Truba o'tkazgich", 1.0, "#374151")

# EVAPORATOR (indoor unit)
def draw_evaporator(fig, cx, cy, cL, cW, cH, label="", T=0.1):
    eL = min(cL * 0.55, 1.40)
    eW = 0.40; eH = 0.38
    ex = cx + T + (cL - 2*T - eL) / 2
    ey = cy + cW - T - eW - 0.04
    ez = cH - eH - 0.08

    box3d(fig, ex, ey, ez, eL, eW, eH, C["evap"], f"{label} Evaporator", 1.0, "#9CA3AF")
    box3d(fig, ex+0.03, ey-0.025, ez+0.04, eL-0.06, 0.04, eH-0.08,
          C["evap_fin"], "", 1.0, "#6B7280")
    for fi in range(8):
        fz = ez+0.06 + fi*(eH-0.12)/8
        ln3(fig, ex+0.04, ey-0.025, fz, ex+eL-0.04, ey-0.025, fz, "#B0BEC5", 0.6)

    n_evap_fans = max(1, int(eL / 0.45))
    for fi in range(n_evap_fans):
        fx = ex + eL/(n_evap_fans*2) + fi*(eL/n_evap_fans)
        fy = ey - 0.03
        fz_fan = ez + eH/2
        fig.add_trace(go.Scatter3d(
            x=[fx], y=[fy], z=[fz_fan], mode='markers',
            marker=dict(size=14, color='#1F2937', symbol='circle',
                        line=dict(width=2, color='#4B5563')),
            showlegend=False, hoverinfo='skip'))
        for ang in range(0, 360, 90):
            r = 0.08
            ax = fx + r*math.cos(math.radians(ang))
            az = fz_fan + r*math.sin(math.radians(ang))
            ln3(fig, fx, fy, fz_fan, ax, fy, az, "#6B7280", 1.5)

    box3d(fig, ex, ey, ez-0.05, eL, eW, 0.04, "#9CA3AF", "Qoplama", 1.0, "#6B7280")
    drain_x = ex + eL*0.15
    ln3(fig, drain_x, ey+eW*0.5, ez-0.05, drain_x, ey+eW*0.5, ez-0.25, "#94A3B8", 2.0)

    liq_pipe_x = ex - 0.04
    gas_pipe_x = ex - 0.04
    ln3(fig, liq_pipe_x, ey+eW*0.3, ez+0.06,
           liq_pipe_x, ey+eW*0.3, ez-0.12, C["comp_pipe_liq"], 3.5)
    ln3(fig, liq_pipe_x+0.06, ey+eW*0.3, ez+0.06,
           liq_pipe_x+0.06, ey+eW*0.3, ez-0.12, C["comp_pipe_gas"], 5.0)

# FLOOR & UTILITY
def seams_front(fig,x0,x1,yf,z0,z1,std,c):
    cx=x0+std
    while cx<x1-0.01: ln3(fig,cx,yf,z0,cx,yf,z1,c,0.8); cx+=std

def seams_side(fig,y0,y1,xf,z0,z1,std,c):
    cy=y0+std
    while cy<y1-0.01: ln3(fig,xf,cy,z0,xf,cy,z1,c,0.8); cy+=std

def floor_grid(fig,L,W,z=0):
    for xi in range(0,int(math.ceil(L))+1):
        cc=C["gM"] if xi%2==0 else C["gm"]
        ln3(fig,xi,0,z,xi,W,z,cc,0.7)
    for yi in range(0,int(math.ceil(W))+1):
        cc=C["gM"] if yi%2==0 else C["gm"]
        ln3(fig,0,yi,z,L,yi,z,cc,0.7)

def dim_arr(fig,p1,p2,offset,label):
    ox,oy,oz=offset; x1,y1,z1=p1; x2,y2,z2=p2
    fig.add_trace(go.Scatter3d(
        x=[x1,x1+ox,None,x2,x2+ox],y=[y1,y1+oy,None,y2,y2+oy],z=[z1,z1+oz,None,z2,z2+oz],
        mode="lines",line=dict(color=C["dim"],width=1.0,dash="dot"),hoverinfo="skip",showlegend=False))
    ln3(fig,x1+ox,y1+oy,z1+oz,x2+ox,y2+oy,z2+oz,C["dim"],2.2)
    tx3(fig,(x1+x2)/2+ox,(y1+y2)/2+oy,(z1+z2)/2+oz,label,sz=11,color=C["dim"])

def build_3d_single(L, W, H, wall_mm, pol_bor, eshik, ej, ep, agregat, aj, ag_brand,
                    progress=100, show_lbl=True):
    """
    Three.js (WebGL) asosidagi yagona kamerali 3D vizualizatsiya.
    BO'LINGAN KAMERALARNI HAM QO'LLAB-QUVVATLAYDI!
    Har bir kamera alohida eshik bilan!
    """
    import math
    import streamlit as st
    import json
    
    T = wall_mm / 1000.0
    eshik_turi = eshik
    
    # ===== KAMERA BO'LISH MA'LUMOTLARI =====
    kamera_bolish_turi = st.session_state.get("kamera_bolish_turi", "Yo'q")
    kameralar_soni = st.session_state.get("kameralar_soni", 2)
    har_bir_kamera_eshik = st.session_state.get("har_bir_kamera_eshik", False)
    
    # ===== ESHIK O'LCHAMLARI =====
    def get_door_dims(eshik_turi_local):
        if eshik_turi_local == "Custom":
            try:
                dwmm = st.session_state.get("eshik_custom_width", 900)
                dhmm = st.session_state.get("eshik_custom_height", 1900)
            except:
                dwmm, dhmm = 900, 1900
        else:
            try:
                dwmm, dhmm = door_dim(eshik_turi_local)
            except:
                dwmm, dhmm = 900, 1900
        return dwmm, dhmm
    
    # ===== ESHIK JOYLASHUVI (5 VARIANT) =====
    def get_door_position(door_side, door_pos, width, total_length):
        if door_pos == "Chap tomon burchak o'rniga":
            return 0.0
        elif door_pos == "Biroz chapga":
            return 0.3
        elif door_pos == "O'rta":
            return (total_length - width) / 2
        elif door_pos == "Biroz o'ngga":
            return total_length - width - 0.3
        elif door_pos == "O'ng tomon burchak o'rniga":
            return total_length - width
        else:
            return (total_length - width) / 2
    
    # ===== KAMERALARNI HISOBLASH =====
    chambers = []
    
    if kamera_bolish_turi == "Uzunlik bo'yicha" and kameralar_soni > 1:
        each_L = L / kameralar_soni
        for i in range(kameralar_soni):
            if har_bir_kamera_eshik:
                k_joyi = st.session_state.get(f"kamera_eshik_joyi_{i}", "Old")
                k_pozitsiya = st.session_state.get(f"kamera_eshik_pozitsiya_{i}", "O'rta")
                k_eshik_turi = st.session_state.get("eshik", "Yo'q")
            else:
                k_joyi = ej
                k_pozitsiya = ep
                k_eshik_turi = eshik_turi
            
            if k_eshik_turi != "Yo'q":
                dwmm_i, dhmm_i = get_door_dims(k_eshik_turi)
                dw_i = dwmm_i / 1000.0
                dh_i = dhmm_i / 1000.0
                has_door_i = True
            else:
                dw_i, dh_i = 0, 0
                has_door_i = False
            
            # Eshik pozitsiyasi - eshik joylashgan devor bo'ylab
            if k_joyi in ["Chap", "O'ng"]:
                door_offset = get_door_position(k_joyi, k_pozitsiya, dw_i, W)
            else:
                door_offset = get_door_position(k_joyi, k_pozitsiya, dw_i, each_L)
            
            chamber = {
                "id": i + 1,
                "x": i * each_L + T,           # Kamera ichki X boshlanish
                "y": T,                         # Kamera ichki Y boshlanish
                "w": each_L - 2*T,              # Kamera ichki kenglik
                "h": W - 2*T,                   # Kamera ichki balandlik
                "L": each_L,
                "W": W,
                "H": H,
                "door_side": k_joyi,
                "door_pos": k_pozitsiya,
                "has_door": has_door_i,
                "door_w": dw_i,
                "door_h": dh_i,
                "door_offset": door_offset,
                "eshik_turi": k_eshik_turi,
                "ch_x": i * each_L,             # Kamera tashqi X boshlanish
                "ch_y": 0,                      # Kamera tashqi Y boshlanish
                "ch_L": each_L,                 # Kamera tashqi uzunlik
                "ch_W": W                       # Kamera tashqi kenglik
            }
            chambers.append(chamber)
    
    elif kamera_bolish_turi == "Eni bo'yicha" and kameralar_soni > 1:
        each_W = W / kameralar_soni
        for i in range(kameralar_soni):
            if har_bir_kamera_eshik:
                k_joyi = st.session_state.get(f"kamera_eshik_joyi_{i}", "Old")
                k_pozitsiya = st.session_state.get(f"kamera_eshik_pozitsiya_{i}", "O'rta")
                k_eshik_turi = st.session_state.get("eshik", "Yo'q")
            else:
                k_joyi = ej
                k_pozitsiya = ep
                k_eshik_turi = eshik_turi
            
            if k_eshik_turi != "Yo'q":
                dwmm_i, dhmm_i = get_door_dims(k_eshik_turi)
                dw_i = dwmm_i / 1000.0
                dh_i = dhmm_i / 1000.0
                has_door_i = True
            else:
                dw_i, dh_i = 0, 0
                has_door_i = False
            
            if k_joyi in ["Chap", "O'ng"]:
                door_offset = get_door_position(k_joyi, k_pozitsiya, dw_i, L)
            else:
                door_offset = get_door_position(k_joyi, k_pozitsiya, dw_i, each_W)
            
            chamber = {
                "id": i + 1,
                "x": T,
                "y": i * each_W + T,
                "w": L - 2*T,
                "h": each_W - 2*T,
                "L": L,
                "W": each_W,
                "H": H,
                "door_side": k_joyi,
                "door_pos": k_pozitsiya,
                "has_door": has_door_i,
                "door_w": dw_i,
                "door_h": dh_i,
                "door_offset": door_offset,
                "eshik_turi": k_eshik_turi,
                "ch_x": 0,
                "ch_y": i * each_W,
                "ch_L": L,
                "ch_W": each_W
            }
            chambers.append(chamber)
    else:
        # Yagona kamera
        if eshik_turi != "Yo'q":
            dwmm, dhmm = get_door_dims(eshik_turi)
            dw_i = dwmm / 1000.0
            dh_i = dhmm / 1000.0
            has_door_i = True
            if ej in ["Chap", "O'ng"]:
                door_offset = get_door_position(ej, ep, dw_i, W)
            else:
                door_offset = get_door_position(ej, ep, dw_i, L)
        else:
            dw_i, dh_i = 0, 0
            has_door_i = False
            door_offset = 0
        
        chambers.append({
            "id": 1,
            "x": T,
            "y": T,
            "w": L - 2*T,
            "h": W - 2*T,
            "L": L,
            "W": W,
            "H": H,
            "door_side": ej,
            "door_pos": ep,
            "has_door": has_door_i,
            "door_w": dw_i,
            "door_h": dh_i,
            "door_offset": door_offset,
            "eshik_turi": eshik_turi,
            "ch_x": 0,
            "ch_y": 0,
            "ch_L": L,
            "ch_W": W
        })
    
    has_bolish = len(chambers) > 1
    has_comp = agregat != "Yo'q"
    has_door = eshik != "Yo'q"
    
    # ===== KOMPRESSOR POZITSIYASI =====
    gap = 0.55
    if "Zanotti" in ag_brand:
        cu_W, cu_D, cu_H = 1.15, 0.68, 0.88
    else:
        cu_W, cu_D, cu_H = 1.12, 0.62, 0.82
    
    zfg = -T if pol_bor else 0
    
    comp_x = 0
    comp_z = 0
    comp_y = zfg
    comp_rotation = 0
    
    if aj == "Old":
        comp_x = L / 2 - cu_W / 2
        comp_z = -cu_D - gap
        comp_rotation = 0
    elif aj == "Orqa":
        comp_x = L / 2 - cu_W / 2
        comp_z = W + gap
        comp_rotation = math.pi
    elif aj == "Chap":
        comp_x = -cu_W - gap
        comp_z = W / 2 - cu_D / 2
        comp_rotation = -math.pi/2
    elif aj == "O'ng":
        comp_x = L + gap
        comp_z = W / 2 - cu_D / 2
        comp_rotation = math.pi/2
    else:
        comp_x = L / 2 - cu_W / 2
        comp_z = W / 2 - cu_D / 2
        comp_y = H + T + 0.05
        comp_rotation = 0
    
    # ===== EVAPORATOR POZITSIYASI =====
    evap_x = L / 2
    evap_z = 0.35
    evap_y = H - 0.45
    
    if ej == "Old":
        evap_z = W - 0.35
    elif ej == "Orqa":
        evap_z = 0.35
    elif ej == "Chap":
        evap_x = L - 0.5
        evap_z = W / 2
    elif ej == "O'ng":
        evap_x = 0.5
        evap_z = W / 2
    
    # ===== JSON GA AYLANTIRISH =====
    chambers_json = json.dumps(chambers)
    has_bolish_str = str(has_bolish).lower()
    has_comp_str = str(has_comp).lower()
    T_val = T
    
    html_code = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; overflow: hidden; font-family: 'Segoe UI', 'Arial', sans-serif; background-color: #f0f4f8; }}
            #info {{ 
                position: absolute; top: 12px; left: 12px; 
                background: rgba(255,255,255,0.96); color: #0f172a; 
                padding: 10px 16px; border-radius: 10px; 
                pointer-events: none; z-index: 100; font-size: 11px; 
                backdrop-filter: blur(12px); border-left: 3px solid #0284c7; 
                box-shadow: 0 4px 15px rgba(0,0,0,0.08); 
                font-weight: 500; letter-spacing: 0.3px;
            }}
            #controls-hint {{ 
                position: absolute; bottom: 12px; left: 12px; 
                background: rgba(255,255,255,0.9); color: #475569; 
                padding: 6px 12px; border-radius: 8px; font-size: 10px; 
                pointer-events: none; backdrop-filter: blur(8px); 
                box-shadow: 0 2px 8px rgba(0,0,0,0.04); 
                font-family: monospace;
            }}
            #progress-bar {{ 
                position: absolute; bottom: 12px; right: 12px; 
                width: 180px; height: 4px; 
                background: rgba(148, 163, 184, 0.3); 
                border-radius: 4px; overflow: hidden; 
            }}
            #progress-fill {{ 
                width: {progress}%; height: 100%; 
                background: linear-gradient(90deg, #0284c7, #0ea5e9); 
            }}
            .label {{ 
                background: rgba(255, 255, 255, 0.96); padding: 4px 12px; 
                border-radius: 20px; border-left: 2px solid #0284c7; 
                font-size: 10px; font-weight: 600; white-space: nowrap; 
                font-family: 'Segoe UI', monospace; color: #0f172a; 
                backdrop-filter: blur(6px); box-shadow: 0 2px 6px rgba(0,0,0,0.06);
                pointer-events: none;
            }}
            .cold-label {{ 
                background: rgba(12, 74, 110, 0.92); border-left-color: #38bdf8; 
                color: #f0f9ff; 
            }}
        </style>
    </head>
    <body>
        <div id="info"><strong>COLD ROOM</strong> | {L:.1f}m x {W:.1f}m x {H:.1f}m | Devor: {wall_mm}mm | {ag_brand}</div>
        <div id="controls-hint">Chap tugma: Aylantirish | O'ng tugma: Surish | G'ildirak: Zoom</div>
        <div id="progress-bar"><div id="progress-fill"></div></div>
        
        <script type="importmap">
            {{
                "imports": {{
                    "three": "https://cdn.skypack.dev/three@0.128.0/build/three.module.js",
                    "three/addons/": "https://cdn.skypack.dev/three@0.128.0/examples/jsm/"
                }}
            }}
        </script>
        
        <script type="module">
            import * as THREE from 'three';
            import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
            import {{ CSS2DRenderer, CSS2DObject }} from 'three/addons/renderers/CSS2DRenderer.js';
            
            // ========== SETUP ==========
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0xf0f4f8);
            scene.fog = new THREE.FogExp2(0xf0f4f8, 0.008);
            
            const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set({L + 5:.1f}, {H + 4.5:.1f}, {W + 7:.1f});
            
            const renderer = new THREE.WebGLRenderer({{ antialias: true, powerPreference: "high-performance" }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            renderer.setPixelRatio(window.devicePixelRatio);
            document.body.appendChild(renderer.domElement);
            
            const labelRenderer = new CSS2DRenderer();
            labelRenderer.setSize(window.innerWidth, window.innerHeight);
            labelRenderer.domElement.style.position = 'absolute';
            labelRenderer.domElement.style.top = '0px';
            labelRenderer.domElement.style.left = '0px';
            labelRenderer.domElement.style.pointerEvents = 'none';
            document.body.appendChild(labelRenderer.domElement);
            
            const controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.rotateSpeed = 1.0;
            controls.zoomSpeed = 1.3;
            controls.panSpeed = 0.8;
            controls.target.set({L/2:.1f}, {H/2:.1f}, {W/2:.1f});
            
            // ========== LIGHTING ==========
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
            scene.add(ambientLight);
            
            const mainLight = new THREE.DirectionalLight(0xffffff, 1.1);
            mainLight.position.set(8, 18, 6);
            mainLight.castShadow = true;
            mainLight.shadow.mapSize.width = 1024;
            mainLight.shadow.mapSize.height = 1024;
            mainLight.shadow.camera.near = 0.5;
            mainLight.shadow.camera.far = 30;
            scene.add(mainLight);
            
            const fillLight = new THREE.PointLight(0x4488cc, 0.35);
            fillLight.position.set({L/2:.1f}, {H/2:.1f}, {W/2:.1f});
            scene.add(fillLight);
            
            const backLight = new THREE.PointLight(0xffaa66, 0.2);
            backLight.position.set({L}, {H/2}, {W});
            scene.add(backLight);
            
            const rimLight = new THREE.PointLight(0xff8866, 0.25);
            rimLight.position.set({L + 2:.1f}, {H + 1:.1f}, {W + 2:.1f});
            scene.add(rimLight);
            
            // ========== HELPER GRID ==========
            const gridHelper = new THREE.GridHelper(Math.max({L}, {W}) + 8, 24, 0x94a3b8, 0xcbd5e1);
            gridHelper.position.y = -0.05;
            scene.add(gridHelper);
            
            // ========== MATERIALS ==========
            const wallMaterial = new THREE.MeshStandardMaterial({{ color: 0xa8abae, metalness: 0.08, roughness: 0.38, transparent: true, opacity: 0.82 }});
            const edgeMaterial = new THREE.MeshStandardMaterial({{ color: 0x8e959d, metalness: 0.25, roughness: 0.28 }});
            const floorMaterial = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, roughness: 0.55, metalness: 0.08 }});
            const roofMaterial = new THREE.MeshStandardMaterial({{ color: 0xadafb0, roughness: 0.42, metalness: 0.05, transparent: true, opacity: 0.88 }});
            const panelMaterial = new THREE.MeshStandardMaterial({{ color: 0xa8abae, metalness: 0.06, roughness: 0.32, transparent: true, opacity: 0.68 }});
            
            const innerWallMat = new THREE.MeshStandardMaterial({{ 
                color: 0x64748b, 
                metalness: 0.2, 
                roughness: 0.4, 
                transparent: true, 
                opacity: 0.85,
                emissive: 0x1e293b,
                emissiveIntensity: 0.05
            }});
            
            const wallThick = {T_val:.3f};
            const wallHeight = {H:.1f};
            const panelW = {panel_width_m:.2f};
            
            // ========== FLOOR ==========
            const mainFloor = new THREE.Mesh(new THREE.BoxGeometry({L}, 0.1, {W}), floorMaterial);
            mainFloor.position.set({L/2}, -0.05, {W/2});
            mainFloor.receiveShadow = true;
            mainFloor.castShadow = true;
            scene.add(mainFloor);
            
            // ========== WALLS ==========
            const frontWall = new THREE.Mesh(new THREE.BoxGeometry({L}, wallHeight, wallThick), wallMaterial);
            frontWall.position.set({L/2}, wallHeight/2, -wallThick/2);
            frontWall.castShadow = true;
            scene.add(frontWall);
            
            const backWall = new THREE.Mesh(new THREE.BoxGeometry({L}, wallHeight, wallThick), wallMaterial);
            backWall.position.set({L/2}, wallHeight/2, {W} + wallThick/2);
            backWall.castShadow = true;
            scene.add(backWall);
            
            const leftWall = new THREE.Mesh(new THREE.BoxGeometry(wallThick, wallHeight, {W}), wallMaterial);
            leftWall.position.set(-wallThick/2, wallHeight/2, {W/2});
            leftWall.castShadow = true;
            scene.add(leftWall);
            
            const rightWall = new THREE.Mesh(new THREE.BoxGeometry(wallThick, wallHeight, {W}), wallMaterial);
            rightWall.position.set({L} + wallThick/2, wallHeight/2, {W/2});
            rightWall.castShadow = true;
            scene.add(rightWall);
            
            // ========== ROOF ==========
            const roof = new THREE.Mesh(new THREE.BoxGeometry({L} + wallThick*2, 0.1, {W} + wallThick*2), roofMaterial);
            roof.position.set({L/2}, wallHeight + 0.05, {W/2});
            roof.castShadow = true;
            scene.add(roof);
            
            // ========== ICHKI DEVORLAR ==========
            const hasBolish = {has_bolish_str};
            const chambersData = {chambers_json};
            const T2 = {T_val};
            const wallHeight2 = {H:.1f};
            
            if (hasBolish && chambersData.length > 1) {{
                for (let c = 0; c < chambersData.length - 1; c++) {{
                    const ch = chambersData[c];
                    const nextCh = chambersData[c + 1];
                    
                    if (ch.x + ch.w < nextCh.x) {{
                        const wallX = ch.x + ch.w + T2/2;
                        const wallW = T2 * 1.2;
                        const wallH = ch.h;
                        
                        const innerWall = new THREE.Mesh(
                            new THREE.BoxGeometry(wallW, wallHeight2, wallH),
                            innerWallMat
                        );
                        innerWall.position.set(wallX, wallHeight2/2, ch.y + wallH/2);
                        innerWall.castShadow = true;
                        innerWall.receiveShadow = true;
                        scene.add(innerWall);
                    }}
                    else if (ch.y + ch.h < nextCh.y) {{
                        const wallY = ch.y + ch.h + T2/2;
                        const wallW = ch.w;
                        const wallH = T2 * 1.2;
                        
                        const innerWall = new THREE.Mesh(
                            new THREE.BoxGeometry(wallW, wallHeight2, wallH),
                            innerWallMat
                        );
                        innerWall.position.set(ch.x + wallW/2, wallHeight2/2, wallY);
                        innerWall.castShadow = true;
                        innerWall.receiveShadow = true;
                        scene.add(innerWall);
                    }}
                }}
            }}
            
            // ========== ESHIKLAR (O'Z KAMERASIGA TEGISHLI) ==========
            const doorMaterial = new THREE.MeshStandardMaterial({{ color: 0x475569, metalness: 0.25, roughness: 0.55 }});
            const frameMaterial = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, metalness: 0.65, roughness: 0.28 }});
            const handleMaterial = new THREE.MeshStandardMaterial({{ color: 0xf1f5f9, metalness: 0.85, roughness: 0.15 }});
            const glassMaterial = new THREE.MeshStandardMaterial({{ color: 0x7dd3fc, metalness: 0.1, roughness: 0.2, transparent: true, opacity: 0.35 }});
            const rubberSeal = new THREE.MeshStandardMaterial({{ color: 0x1e293b, metalness: 0.02, roughness: 0.9 }});
            
            function createDoor(chamber) {{
                if (!chamber.has_door) return;
                
                const doorW = chamber.door_w;
                const doorH = chamber.door_h;
                const doorSide = chamber.door_side;
                const doorOffset = chamber.door_offset;
                const chX = chamber.ch_x;      // Kamera tashqi X boshlanish
                const chY = chamber.ch_y;      // Kamera tashqi Y boshlanish
                const chL = chamber.ch_L;      // Kamera tashqi uzunlik
                const chW = chamber.ch_W;      // Kamera tashqi kenglik
                const chId = chamber.id;
                const T_local = T2;
                
                let doorPosX = 0, doorPosZ = 0, doorRot = 0;
                let doorOffsetX = 0, doorOffsetZ = 0;
                
                // Eshik joylashuvini aniqlash - KAMERA ICHIDA
                if (doorSide === "Old") {{
                    // Old devor (Z = chY) - X o'qi bo'ylab
                    doorPosX = chX + T_local + doorOffset;
                    doorPosZ = chY - 0.025;
                    doorRot = 0;
                }} else if (doorSide === "Orqa") {{
                    // Orqa devor (Z = chY + chW) - X o'qi bo'ylab
                    doorPosX = chX + T_local + doorOffset;
                    doorPosZ = chY + chW + 0.025;
                    doorRot = Math.PI;
                }} else if (doorSide === "Chap") {{
                    // Chap devor (X = chX) - Z o'qi bo'ylab
                    doorPosX = chX - 0.025;
                    doorPosZ = chY + T_local + doorOffset;
                    doorRot = -Math.PI/2;
                }} else if (doorSide === "O'ng") {{
                    // O'ng devor (X = chX + chL) - Z o'qi bo'ylab
                    doorPosX = chX + chL + 0.025;
                    doorPosZ = chY + T_local + doorOffset;
                    doorRot = Math.PI/2;
                }} else {{
                    return;
                }}
                
                const doorGroup = new THREE.Group();
                doorGroup.position.set(doorPosX, doorH/2, doorPosZ);
                doorGroup.rotation.y = doorRot;
                
                const doorHalfWidth = doorW / 2;
                
                // Ikkala qanot
                const leftWing = new THREE.Mesh(new THREE.BoxGeometry(doorHalfWidth - 0.015, doorH, 0.055), doorMaterial);
                leftWing.position.set(-doorHalfWidth/2 - 0.01, 0, 0);
                leftWing.castShadow = true;
                doorGroup.add(leftWing);
                
                const rightWing = new THREE.Mesh(new THREE.BoxGeometry(doorHalfWidth - 0.015, doorH, 0.055), doorMaterial);
                rightWing.position.set(doorHalfWidth/2 + 0.01, 0, 0);
                rightWing.castShadow = true;
                doorGroup.add(rightWing);
                
                // Oynalar
                const windowW = doorHalfWidth * 0.6;
                const windowH = doorH * 0.35;
                const windowOffset = 0.032;
                
                const leftWindow = new THREE.Mesh(new THREE.BoxGeometry(windowW, windowH, 0.008), glassMaterial);
                leftWindow.position.set(-doorHalfWidth/2 - 0.01, doorH * 0.2, windowOffset);
                doorGroup.add(leftWindow);
                
                const rightWindow = new THREE.Mesh(new THREE.BoxGeometry(windowW, windowH, 0.008), glassMaterial);
                rightWindow.position.set(doorHalfWidth/2 + 0.01, doorH * 0.2, windowOffset);
                doorGroup.add(rightWindow);
                
                // Ramka
                const frameWidth = 0.045;
                const topFrame = new THREE.Mesh(new THREE.BoxGeometry(doorW + 0.09, frameWidth, 0.07), frameMaterial);
                topFrame.position.set(0, doorH/2 - 0.025, 0);
                doorGroup.add(topFrame);
                
                const bottomFrame = new THREE.Mesh(new THREE.BoxGeometry(doorW + 0.09, frameWidth, 0.07), frameMaterial);
                bottomFrame.position.set(0, -doorH/2 + 0.025, 0);
                doorGroup.add(bottomFrame);
                
                const leftFrame = new THREE.Mesh(new THREE.BoxGeometry(frameWidth, doorH + 0.07, 0.07), frameMaterial);
                leftFrame.position.set(-doorW/2 - 0.022, 0, 0);
                doorGroup.add(leftFrame);
                
                const rightFrame = new THREE.Mesh(new THREE.BoxGeometry(frameWidth, doorH + 0.07, 0.07), frameMaterial);
                rightFrame.position.set(doorW/2 + 0.022, 0, 0);
                doorGroup.add(rightFrame);
                
                const centerSeal = new THREE.Mesh(new THREE.BoxGeometry(0.02, doorH + 0.06, 0.08), rubberSeal);
                centerSeal.position.set(0, 0, 0);
                doorGroup.add(centerSeal);
                
                // Tutqichlar
                const leftHandle = new THREE.Mesh(new THREE.BoxGeometry(0.045, 0.14, 0.035), handleMaterial);
                leftHandle.position.set(-doorHalfWidth/2 - 0.01 + 0.22, 0.1, 0.04);
                doorGroup.add(leftHandle);
                
                const rightHandle = new THREE.Mesh(new THREE.BoxGeometry(0.045, 0.14, 0.035), handleMaterial);
                rightHandle.position.set(doorHalfWidth/2 + 0.01 - 0.22, 0.1, 0.04);
                doorGroup.add(rightHandle);
                
                // Menteshkalar
                const hingeMat = new THREE.MeshStandardMaterial({{ color: 0x64748b, metalness: 0.7, roughness: 0.25 }});
                const hingePositions = [-0.22, 0.0, 0.22];
                hingePositions.forEach(yPos => {{
                    const leftHinge = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.025, 0.04), hingeMat);
                    leftHinge.position.set(-doorW/2 + 0.015, yPos, 0.025);
                    doorGroup.add(leftHinge);
                    
                    const rightHinge = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.025, 0.04), hingeMat);
                    rightHinge.position.set(doorW/2 - 0.015, yPos, 0.025);
                    doorGroup.add(rightHinge);
                }});
                
                // Eshik yorlig'i
                const doorLabelDiv = document.createElement('div');
                doorLabelDiv.textContent = '🚪 K' + chId;
                doorLabelDiv.className = 'label';
                doorLabelDiv.style.fontSize = '9px';
                doorLabelDiv.style.padding = '2px 8px';
                const doorLabel = new CSS2DObject(doorLabelDiv);
                doorLabel.position.set(0, doorH/2 + 0.2, 0.04);
                doorGroup.add(doorLabel);
                
                scene.add(doorGroup);
            }}
            
            // Har bir kamera uchun eshik yaratish
            chambersData.forEach(ch => {{
                createDoor(ch);
            }});
            
            // ========== LABELS (KAMERA NOMLARI) ==========
            function makeLabel(text, x, y, z, isCold = false) {{
                const div = document.createElement('div');
                div.textContent = text;
                div.className = isCold ? 'label cold-label' : 'label';
                const label = new CSS2DObject(div);
                label.position.set(x, y, z);
                scene.add(label);
            }}
            
            // Har bir kamera uchun label - KAMERA ICHIDA
            chambersData.forEach((ch) => {{
                const cx = ch.x + ch.w/2;
                const cy = ch.y + ch.h/2;
                const labelText = 'KAMERA ' + ch.id + (ch.has_door ? ' 🚪' : '');
                makeLabel(labelText, cx, 0.3, cy);
            }});
            
            // ========== COMPRESSOR (AGREGAT) ==========
            const hasComp = {has_comp_str};
            const animatedFans = [];
            let particleSystem = null;
            let particleCount = 0;
            let particleVelocities = [];
            let airDirection = {{ x: 0, z: 1 }};
            let evapX = {evap_x};
            let evapY = {evap_y};
            let evapZ = {evap_z};
            
            if (hasComp) {{
                const compGroup = new THREE.Group();
                
                let compXpos = {comp_x};
                let compZpos = {comp_z};
                let compRot = {comp_rotation};
                
                if (compZpos < 0.1) {{
                    compZpos = -0.7;
                }} else if (compZpos > {W} - 0.1) {{
                    compZpos = {W} + 0.7;
                }} else if (compXpos < 0.1) {{
                    compXpos = -0.7;
                    compZpos = {W/2:.1f};
                }} else if (compXpos > {L} - 0.1) {{
                    compXpos = {L} + 0.7;
                    compZpos = {W/2:.1f};
                }}
                
                compGroup.position.set(compXpos, {comp_y}, compZpos);
                compGroup.rotation.y = compRot;
                
                const bitzerMat = new THREE.MeshStandardMaterial({{ color: 0x5a6e7a, metalness: 0.65, roughness: 0.32 }});
                const headMat = new THREE.MeshStandardMaterial({{ color: 0x4a5e6a, metalness: 0.72, roughness: 0.28 }});
                const copperMat = new THREE.MeshStandardMaterial({{ color: 0xb87333, metalness: 0.78, roughness: 0.35 }});
                const darkMat = new THREE.MeshStandardMaterial({{ color: 0x2c3e40, metalness: 0.45, roughness: 0.55 }});
                const fanMat = new THREE.MeshStandardMaterial({{ color: 0x1e2a2e, metalness: 0.35, roughness: 0.65 }});
                const coilMat = new THREE.MeshStandardMaterial({{ color: 0x8b9a6e, metalness: 0.55, roughness: 0.42 }});
                const rubberMat = new THREE.MeshStandardMaterial({{ color: 0x1a1a1a, metalness: 0.05, roughness: 0.85 }});
                const badgeMat = new THREE.MeshStandardMaterial({{ color: 0xc9a87c, metalness: 0.38, roughness: 0.48 }});
                
                // Base platform
                const basePlate = new THREE.Mesh(new THREE.BoxGeometry({cu_W} + 0.12, 0.07, {cu_D} + 0.12), bitzerMat);
                basePlate.position.y = 0.035;
                basePlate.castShadow = true;
                compGroup.add(basePlate);
                
                // Anti-vibration feet
                const footPositions = [
                    [-{cu_W}/2 + 0.15, 0, -{cu_D}/2 + 0.15],
                    [{cu_W}/2 - 0.15, 0, -{cu_D}/2 + 0.15],
                    [-{cu_W}/2 + 0.15, 0, {cu_D}/2 - 0.15],
                    [{cu_W}/2 - 0.15, 0, {cu_D}/2 - 0.15]
                ];
                footPositions.forEach(pos => {{
                    const foot = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.035, 0.1), rubberMat);
                    foot.position.set(pos[0], pos[1] + 0.02, pos[2]);
                    foot.castShadow = true;
                    compGroup.add(foot);
                }});
                
                // Main compressor body
                const compBody = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.40, 0.72, 32), bitzerMat);
                compBody.position.set(-0.38, 0.46, 0.28);
                compBody.castShadow = true;
                compGroup.add(compBody);
                
                const headCover = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.36, 0.12, 24), headMat);
                headCover.position.set(-0.38, 0.85, 0.28);
                headCover.castShadow = true;
                compGroup.add(headCover);
                
                // Condenser coil
                const condenserBlock = new THREE.Mesh(new THREE.BoxGeometry(1.05, 0.68, 0.12), coilMat);
                condenserBlock.position.set(0.08, 0.48, -0.45);
                condenserBlock.castShadow = true;
                compGroup.add(condenserBlock);
                
                // Fan
                const fanShroud = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.09, 32), bitzerMat);
                fanShroud.rotation.x = Math.PI/2;
                fanShroud.position.set(0.08, 0.52, -0.22);
                compGroup.add(fanShroud);
                
                const fanBladesGroup = new THREE.Group();
                fanBladesGroup.position.set(0.08, 0.52, -0.145);
                for (let k = 0; k < 4; k++) {{
                    const blade = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.05, 0.012), fanMat);
                    blade.rotation.z = (k * Math.PI) / 2;
                    fanBladesGroup.add(blade);
                }}
                const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.025, 12), fanMat);
                hub.position.set(0, 0, 0);
                fanBladesGroup.add(hub);
                compGroup.add(fanBladesGroup);
                animatedFans.push(fanBladesGroup);
                
                // Receiver tank
                const receiver = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.72, 24), bitzerMat);
                receiver.position.set(0.52, 0.46, 0.28);
                receiver.castShadow = true;
                compGroup.add(receiver);
                
                // BITZER badge
                const badge = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.038, 0.006), badgeMat);
                badge.position.set(-0.38, 0.22, 0.48);
                compGroup.add(badge);
                
                scene.add(compGroup);
                
                // ===== REFRIGERANT PIPES =====
                const pipeStartX = compXpos;
                const pipeStartZ = compZpos;
                const pipeEndX = {evap_x};
                const pipeEndZ = {evap_z};
                const pipeEndY = {evap_y} + 0.18;
                const wallHeightVal = wallHeight;
                
                const hpPoints = [
                    new THREE.Vector3(pipeStartX - 0.12, {comp_y} + 0.62, pipeStartZ + 0.32),
                    new THREE.Vector3(pipeStartX - 0.12, wallHeightVal - 0.18, pipeStartZ + 0.32),
                    new THREE.Vector3(pipeEndX + 0.22, wallHeightVal - 0.18, pipeEndZ + 0.28),
                    new THREE.Vector3(pipeEndX + 0.22, pipeEndY, pipeEndZ + 0.28)
                ];
                const hpCurve = new THREE.CatmullRomCurve3(hpPoints);
                const hpPipe = new THREE.Mesh(new THREE.TubeGeometry(hpCurve, 72, 0.018, 16, false), 
                    new THREE.MeshStandardMaterial({{ color: 0xc97e5a, metalness: 0.82, roughness: 0.25 }}));
                hpPipe.castShadow = true;
                scene.add(hpPipe);
                
                const llPoints = [
                    new THREE.Vector3(pipeStartX + 0.52, {comp_y} + 0.52, pipeStartZ + 0.28),
                    new THREE.Vector3(pipeStartX + 0.52, wallHeightVal - 0.18, pipeStartZ + 0.28),
                    new THREE.Vector3(pipeEndX - 0.15, wallHeightVal - 0.18, pipeEndZ - 0.18),
                    new THREE.Vector3(pipeEndX - 0.15, pipeEndY, pipeEndZ - 0.18)
                ];
                const llCurve = new THREE.CatmullRomCurve3(llPoints);
                const llPipe = new THREE.Mesh(new THREE.TubeGeometry(llCurve, 72, 0.012, 12, false),
                    new THREE.MeshStandardMaterial({{ color: 0xb87333, metalness: 0.78, roughness: 0.28 }}));
                llPipe.castShadow = true;
                scene.add(llPipe);
                
                const slPoints = [
                    new THREE.Vector3(pipeStartX - 0.45, {comp_y} + 0.38, pipeStartZ - 0.22),
                    new THREE.Vector3(pipeStartX - 0.45, wallHeightVal - 0.18, pipeStartZ - 0.22),
                    new THREE.Vector3(pipeEndX - 0.28, wallHeightVal - 0.18, pipeEndZ + 0.15),
                    new THREE.Vector3(pipeEndX - 0.28, pipeEndY, pipeEndZ + 0.15)
                ];
                const slCurve = new THREE.CatmullRomCurve3(slPoints);
                const slPipe = new THREE.Mesh(new THREE.TubeGeometry(slCurve, 72, 0.028, 16, false),
                    new THREE.MeshStandardMaterial({{ color: 0x1a1a1a, metalness: 0.02, roughness: 0.88 }}));
                slPipe.castShadow = true;
                scene.add(slPipe);
                
                // Compressor label
                makeLabel('⚙️ BITZER', compXpos, {comp_y} + 0.9, compZpos, true);
            }}
            
            // ========== EVAPORATOR ==========
            if (hasComp) {{
                const evapX = {evap_x};
                const evapY = {evap_y};
                const evapZ = {evap_z};
                const doorSide = "{ej}";
                
                const evapGroup = new THREE.Group();
                evapGroup.position.set(evapX, evapY, evapZ);
                
                let evapRotY = 0;
                if (doorSide === "Old") evapRotY = Math.PI;
                else if (doorSide === "Orqa") evapRotY = 0;
                else if (doorSide === "Chap") evapRotY = -Math.PI/2;
                else if (doorSide === "O'ng") evapRotY = Math.PI/2;
                evapGroup.rotation.y = evapRotY;
                
                const silverMat = new THREE.MeshStandardMaterial({{ color: 0xe2e8f0, metalness: 0.68, roughness: 0.18 }});
                const blackFanMat = new THREE.MeshStandardMaterial({{ color: 0x1e293b, metalness: 0.45, roughness: 0.52 }});
                const coilMatEvap = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, metalness: 0.72, roughness: 0.22 }});
                
                const evapBody = new THREE.Mesh(new THREE.BoxGeometry(1.28, 0.42, 0.46), silverMat);
                evapBody.castShadow = true;
                evapGroup.add(evapBody);
                
                // Evaporator coil fins
                for (let i = -0.55; i <= 0.55; i += 0.09) {{
                    const fin = new THREE.Mesh(new THREE.BoxGeometry(0.022, 0.34, 0.38), coilMatEvap);
                    fin.position.set(i, 0, 0);
                    evapGroup.add(fin);
                }}
                
                // Fans
                const fanPositions = [-0.42, 0, 0.42];
                for (let f = 0; f < fanPositions.length; f++) {{
                    const fanBase = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.04, 24), blackFanMat);
                    fanBase.rotation.x = Math.PI / 2;
                    fanBase.position.set(fanPositions[f], 0, 0.25);
                    evapGroup.add(fanBase);
                    
                    const fanBlades = new THREE.Group();
                    fanBlades.position.set(fanPositions[f], 0, 0.27);
                    for (let b = 0; b < 4; b++) {{
                        const blade = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.028, 0.01), blackFanMat);
                        blade.rotation.z = (b * Math.PI) / 2;
                        fanBlades.add(blade);
                    }}
                    evapGroup.add(fanBlades);
                    animatedFans.push(fanBlades);
                }}
                
                // Drain pan
                const drainPan = new THREE.Mesh(new THREE.BoxGeometry(1.35, 0.03, 0.5), new THREE.MeshStandardMaterial({{ color: 0x64748b, metalness: 0.4 }}));
                drainPan.position.set(0, -0.22, 0);
                evapGroup.add(drainPan);
                
                scene.add(evapGroup);
                
                // ===== COLD AIR PARTICLES =====
                particleCount = 800;
                const particlePositions = [];
                particleVelocities = [];
                
                if (doorSide === "Old") airDirection = {{ x: 0, z: -1 }};
                else if (doorSide === "Orqa") airDirection = {{ x: 0, z: 1 }};
                else if (doorSide === "Chap") airDirection = {{ x: 1, z: 0 }};
                else if (doorSide === "O'ng") airDirection = {{ x: -1, z: 0 }};
                
                const particleGeo = new THREE.BufferGeometry();
                for (let i = 0; i < particleCount; i++) {{
                    let px = evapX + (Math.random() - 0.5) * 1.3;
                    let py = evapY + (Math.random() - 0.5) * 0.35;
                    let pz = evapZ + (airDirection.z !== 0 ? (airDirection.z * 0.38) : (Math.random() - 0.5) * 1.3);
                    
                    if (airDirection.z !== 0) pz = evapZ + airDirection.z * 0.4;
                    if (airDirection.x !== 0) px = evapX + airDirection.x * 0.4;
                    
                    particlePositions.push(px, py, pz);
                    
                    const speed = 0.04 + Math.random() * 0.05;
                    particleVelocities.push({{
                        x: airDirection.x * speed + (Math.random() - 0.5) * 0.02,
                        y: -0.008 - Math.random() * 0.015,
                        z: airDirection.z * speed + (Math.random() - 0.5) * 0.02,
                        age: 0,
                        maxAge: 45 + Math.random() * 70
                    }});
                }}
                particleGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(particlePositions), 3));
                const particleMat = new THREE.PointsMaterial({{ color: 0x3b82f6, size: 0.028, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending }});
                particleSystem = new THREE.Points(particleGeo, particleMat);
                scene.add(particleSystem);
                
                makeLabel('❄️ EVAPORATOR', evapX, evapY + 0.5, evapZ, true);
            }}
            
            // ========== ANIMATION ==========
            function animateParticles() {{
                if (!particleSystem || particleCount === 0) return;
                const positions = particleSystem.geometry.attributes.position.array;
                for (let i = 0; i < particleCount; i++) {{
                    const idx = i * 3;
                    const v = particleVelocities[i];
                    positions[idx] += v.x;
                    positions[idx + 1] += v.y;
                    positions[idx + 2] += v.z;
                    v.age++;
                    
                    const isOut = positions[idx + 1] < 0.08 || v.age > v.maxAge ||
                                  positions[idx] < 0 || positions[idx] > {L:.1f} ||
                                  positions[idx + 2] < 0 || positions[idx + 2] > {W:.1f};
                    
                    if (isOut) {{
                        let px = evapX + (Math.random() - 0.5) * 1.3;
                        let py = evapY + (Math.random() - 0.5) * 0.35;
                        let pz = evapZ + (airDirection.z !== 0 ? (airDirection.z * 0.4) : (Math.random() - 0.5) * 1.3);
                        
                        if (airDirection.z !== 0) pz = evapZ + airDirection.z * 0.4;
                        if (airDirection.x !== 0) px = evapX + airDirection.x * 0.4;
                        
                        positions[idx] = px;
                        positions[idx + 1] = py;
                        positions[idx + 2] = pz;
                        v.age = 0;
                        v.x = airDirection.x * (0.04 + Math.random() * 0.05) + (Math.random() - 0.5) * 0.02;
                        v.y = -0.008 - Math.random() * 0.015;
                        v.z = airDirection.z * (0.04 + Math.random() * 0.05) + (Math.random() - 0.5) * 0.02;
                    }}
                }}
                particleSystem.geometry.attributes.position.needsUpdate = true;
            }}
            
            function animate() {{
                requestAnimationFrame(animate);
                
                animatedFans.forEach(fan => {{
                    fan.rotation.z += 0.25;
                }});
                
                if (particleSystem && particleCount > 0) {{
                    animateParticles();
                }}
                
                controls.update();
                renderer.render(scene, camera);
                labelRenderer.render(scene, camera);
            }}
            
            animate();
            
            window.addEventListener('resize', () => {{
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
                labelRenderer.setSize(window.innerWidth, window.innerHeight);
            }});
        </script>
    </body>
    </html>
    '''
    
    return html_code


def build_3d_multi_html(L, W, heights_list, corridor_pos, corridor_w, wall_mm,
                        door_w=0.96, door_h=2.1, n_total_arg=None,
                        comp_brand="Bitzer", comp_type="Split-sistema (Nizkotemp)",
                        comp_joyi="Orqa", door_side_multi="Old"):
    """
    EcoProm Multi-Chamber Cold Room 3D Visualization.
    - Tom va uning ikki yonboshidagi uchburchak devorlar (Gable Walls) qovurg'ali profildan shakllantirildi.
    - Ranglar palitrasi: Yashil-oq (EcoProm Factory standard) va kulrang metallik komponentlar.
    """
    import math
    import json
    
    T = wall_mm / 1000.0
    n_total = len(heights_list) if n_total_arg is None else n_total_arg

    if len(heights_list) < n_total:
        last_h = heights_list[-1] if heights_list else 3.0
        heights_list = heights_list + [last_h] * (n_total - len(heights_list))

    chambers_data = []
    
    if corridor_pos == "markaz" and corridor_w > 0:
        n_left = int(math.ceil(n_total / 2))
        n_right = n_total - n_left
        cham_L = (L - corridor_w) / 2
        cham_W_left = W / n_left
        cham_W_right = W / n_right if n_right > 0 else 0

        for i in range(n_left):
            chambers_data.append({
                "id": i + 1, "cx": 0, "cy": i * cham_W_left,
                "cL": cham_L, "cW": cham_W_left - T, "cH": heights_list[i],
                "door": "RIGHT", "wall_side": "LEFT"
            })
        for i in range(n_right):
            chambers_data.append({
                "id": n_left + i + 1, "cx": cham_L + corridor_w, "cy": i * cham_W_right,
                "cL": cham_L, "cW": cham_W_right - T, "cH": heights_list[n_left + i],
                "door": "LEFT", "wall_side": "RIGHT"
            })

    elif corridor_w > 0 and corridor_pos in ("chap", "o'ng"):
        cham_L = L - corridor_w
        cham_W = W / n_total
        offset_x = corridor_w if corridor_pos == "chap" else 0
        for i in range(n_total):
            w_side = "RIGHT" if corridor_pos == "chap" else "LEFT"
            chambers_data.append({
                "id": i + 1, "cx": offset_x, "cy": i * cham_W,
                "cL": cham_L, "cW": cham_W - T, "cH": heights_list[i],
                "door": "side", "wall_side": w_side
            })

    else:
        cham_L_each = L / n_total
        cham_W_each = W
        for i in range(n_total):
            door_side = "FRONT"
            w_side = "BACK"
            if door_side_multi == "Orqa":
                door_side = "BACK"
                w_side = "FRONT"
            elif door_side_multi == "Chap" and i == 0:
                door_side = "LEFT"
                w_side = "RIGHT"
            elif door_side_multi == "O'ng" and i == n_total - 1:
                door_side = "RIGHT"
                w_side = "LEFT"
                
            chambers_data.append({
                "id": i + 1, "cx": i * cham_L_each, "cy": 0,
                "cL": cham_L_each, "cW": cham_W_each, "cH": heights_list[i],
                "door": door_side, "wall_side": w_side
            })

    max_h = max(heights_list)
    chambers_json = json.dumps(chambers_data)
    panel_w = 0.96  

    cam_x = L * 1.6
    cam_y = max_h * 2.5
    cam_z = W * 1.9
    target_x = L / 2
    target_y = max_h / 2
    target_z = W / 2

    html_code = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ margin: 0; overflow: hidden; font-family: 'Segoe UI', system-ui, sans-serif; background-color: #f8fafc; }}
        #info {{ 
            position: absolute; top: 16px; left: 16px; 
            background: rgba(255, 255, 255, 0.98); color: #0f172a; 
            padding: 12px 20px; border-radius: 12px; font-size: 11px; 
            border: 1px solid rgba(0, 90, 54, 0.25);
            border-left: 4px solid #005a36;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06); z-index: 10; 
            font-family: monospace; line-height: 1.4;
        }}
        #controls-hint {{ 
            position: absolute; bottom: 16px; left: 16px; 
            background: rgba(255, 255, 255, 0.95); color: #475569; 
            padding: 8px 16px; border-radius: 8px; font-size: 10px; 
            z-index: 10; font-family: monospace; border: 1px solid rgba(0,0,0,0.05);
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        }}
        .label {{ 
            background: #ffffff; padding: 4px 10px; 
            border-radius: 6px; border: 1px solid #cbd5e1; border-left: 3px solid #005a36; 
            font-size: 10px; font-weight: 600; white-space: nowrap; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); color: #0f172a; 
            font-family: monospace;
        }}
        .door-label {{
            background: #ffffff; border: 1px solid #fed7aa; border-left: 3px solid #f59e0b;
            color: #b45309; font-size: 9px; padding: 3px 8px; font-family: monospace;
            border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }}
        .comp-label {{
            background: #005a36; border-left: 3px solid #38bdf8;
            color: #ffffff; font-size: 9px; padding: 4px 8px; font-weight: bold; font-family: monospace;
            border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
    </style>
</head>
<body>
    <div id="info">
        <strong style="color: #005a36;"> ECOPROM 3D PLATFORM</strong><br>
        O'lcham: {L:.1f}x{W:.1f}x{max_h:.1f}m | {wall_mm}mm panel<br>
        Konstruksiya: Qovurg'ali Sanoat Tomi va Prosedurial Fasad
    </div>


    <script type="importmap">
        {{ "imports": {{ "three": "https://unpkg.com/three@0.160.0/build/three.module.js", "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/" }} }}
    </script>

    <script type="module">
        import * as THREE from 'three';
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
        import {{ CSS2DRenderer, CSS2DObject }} from 'three/addons/renderers/CSS2DRenderer.js';

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf1f5f9);

        const camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set({cam_x:.1f}, {cam_y:.1f}, {cam_z:.1f});

        const renderer = new THREE.WebGLRenderer({{ antialias: true, powerPreference: "high-performance" }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        document.body.appendChild(renderer.domElement);

        const labelRenderer = new CSS2DRenderer();
        labelRenderer.setSize(window.innerWidth, window.innerHeight);
        labelRenderer.domElement.style.position = 'absolute';
        labelRenderer.domElement.style.top = '0px';
        labelRenderer.domElement.style.pointerEvents = 'none';
        document.body.appendChild(labelRenderer.domElement);

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.target.set({target_x:.1f}, {target_y:.1f}, {target_z:.1f});

        const chambers = {chambers_json};
        const T = {T};
        const doorW = {door_w};
        const doorH = {door_h};
        const panelWidth = {panel_w};
        const animatedFans = [];
        const particleSystems = []; 

        // ========== CHIROQLAR ==========
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
        scene.add(ambientLight);
        
        const mainLight = new THREE.DirectionalLight(0xffffff, 1.0);
        mainLight.position.set({L} * 2, {max_h} * 4, {W} * 2);
        mainLight.castShadow = true;
        mainLight.shadow.mapSize.width = 2048;
        mainLight.shadow.mapSize.height = 2048;
        mainLight.shadow.bias = -0.0001;
        scene.add(mainLight);

        // ========== MATERIALLAR ==========
        const wallMat = new THREE.MeshStandardMaterial({{ color: 0xffffff, metalness: 0.1, roughness: 0.5, transparent: true, opacity: 0.5, side: THREE.DoubleSide }});
        const roofMetalMat = new THREE.MeshStandardMaterial({{ color: 0x7e8a9b, metalness: 0.5, roughness: 0.3, side: THREE.DoubleSide }});
        const gableMetalMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, metalness: 0.4, roughness: 0.35, side: THREE.DoubleSide }});
        const doorMat = new THREE.MeshStandardMaterial({{ color: 0x1e293b, metalness: 0.3, roughness: 0.4 }});
        const gutterMat = new THREE.MeshStandardMaterial({{ color: 0x334155, metalness: 0.6, roughness: 0.3 }});
        const floorMat = new THREE.MeshStandardMaterial({{ color: 0xe2e8f0, roughness: 0.6, metalness: 0.1 }});
        const pipeRedMat = new THREE.MeshStandardMaterial({{ color: 0xdc2626, metalness: 0.6, roughness: 0.2 }});
        const pipeBlueMat = new THREE.MeshStandardMaterial({{ color: 0x0284c7, metalness: 0.6, roughness: 0.2 }});

        const totalFloor = new THREE.Mesh(new THREE.BoxGeometry({L}, 0.02, {W}), floorMat);
        totalFloor.position.set({target_x}, -0.01, {target_z});
        totalFloor.receiveShadow = true;
        scene.add(totalFloor);

        // ========== QOVURG'ALI TOM GEOMETRIYASI ==========
        const roofGroup = new THREE.Group();
        const roofRidgeH = 0.5;       
        const halfL = {L} / 2;         
        const roofWidth = {W} + 0.04;   

        const slopeLen = Math.sqrt(halfL * halfL + roofRidgeH * roofRidgeH) + 0.05;
        const pitchAngle = Math.atan2(roofRidgeH, halfL);

        // Chap va o'ng tom asosi
        const leftBase = new THREE.Mesh(new THREE.BoxGeometry(slopeLen, 0.03, roofWidth), roofMetalMat);
        leftBase.position.set(halfL / 2, {max_h} + roofRidgeH / 2, {W} / 2);
        leftBase.rotation.z = pitchAngle;
        roofGroup.add(leftBase);

        const rightBase = new THREE.Mesh(new THREE.BoxGeometry(slopeLen, 0.03, roofWidth), roofMetalMat);
        rightBase.position.set({L} - halfL / 2, {max_h} + roofRidgeH / 2, {W} / 2);
        rightBase.rotation.z = -pitchAngle;
        roofGroup.add(rightBase);

        // Tom ustiga qovurg'alar chizish (Trapeksimon relyef)
        const ribStep = 0.25; 
        const ribW = 0.04;   
        const ribH = 0.03;   

        for (let zOffset = 0.02; zOffset < roofWidth; zOffset += ribStep) {{
            const ribL = new THREE.Mesh(new THREE.BoxGeometry(slopeLen, ribH, ribW), roofMetalMat);
            ribL.position.set(halfL / 2 - Math.sin(pitchAngle)*ribH/2, {max_h} + roofRidgeH / 2 + ribH/2, zOffset);
            ribL.rotation.z = pitchAngle;
            roofGroup.add(ribL);

            const ribR = new THREE.Mesh(new THREE.BoxGeometry(slopeLen, ribH, ribW), roofMetalMat);
            ribR.position.set({L} - halfL / 2 + Math.sin(pitchAngle)*ribH/2, {max_h} + roofRidgeH / 2 + ribH/2, zOffset);
            ribR.rotation.z = -pitchAngle;
            roofGroup.add(ribR);
        }}
        
        // Ridge Cap (Tizma panel)
        const ridgeCap = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.04, roofWidth + 0.01), gutterMat);
        ridgeCap.position.set(halfL, {max_h} + roofRidgeH + 0.02, {W}/2);
        roofGroup.add(ridgeCap);
        scene.add(roofGroup);


        // ========== QOVURG'ALI YON UCHBURCHAK DEVORLAR (GABLE WALLS) ==========
        function createRibbedGableWall(zPos) {{
            const gableGroup = new THREE.Group();
            
            // Asosiy tekis uchburchak panel orqa fonni yopish uchun
            const gableShape = new THREE.Shape();
            gableShape.moveTo(0, 0);
            gableShape.lineTo({L}, 0);
            gableShape.lineTo(halfL, roofRidgeH);
            gableShape.lineTo(0, 0);
            
            const extSettings = {{ depth: 0.02, bevelEnabled: false }};
            const baseMesh = new THREE.Mesh(new THREE.ExtrudeGeometry(gableShape, extSettings), gableMetalMat);
            baseMesh.position.set(0, {max_h}, zPos);
            gableGroup.add(baseMesh);

            // Vertikal qovurg'alarni qo'shish (X o'qi bo'ylab takrorlanadi)
            const vRibDist = 0.3; 
            const vRibW = 0.04;
            const vRibD = 0.025;

            for (let x = vRibDist; x < {L}; x += vRibDist) {{
                // Har bir nuqtadagi uchburchak balandligini chiziqli tenglama bilan aniqlaymiz:
                let currentH = 0;
                if (x <= halfL) {{
                    currentH = (roofRidgeH / halfL) * x;
                }} else {{
                    currentH = roofRidgeH - ((roofRidgeH / halfL) * (x - halfL));
                }}
                
                if (currentH > 0.02) {{
                    const vRib = new THREE.Mesh(new THREE.BoxGeometry(vRibW, currentH, vRibD), gableMetalMat);
                    // Vertikal ustuncha markazini to'g'irlash
                    vRib.position.set(x, {max_h} + currentH / 2, zPos + (zPos === 0 ? -0.012 : 0.022));
                    gableGroup.add(vRib);
                }}
            }}
            scene.add(gableGroup);
        }}

        createRibbedGableWall(0);          // Old yonbosh uchburchak
        createRibbedGableWall({W} - 0.02); // Orqa yonbosh uchburchak


        // ========== TARNOV TIZIMI ==========
        function createGutterSystemX(xPos) {{
            const gutter = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.08, {W} + 0.2), gutterMat);
            gutter.position.set(xPos, {max_h} - 0.02, {W} / 2);
            scene.add(gutter);

            const pipePoints = [0.05, {W} / 2, {W} - 0.05];
            pipePoints.forEach(zP => {{
                const pipe = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, {max_h}, 12), gutterMat);
                pipe.position.set(xPos + (xPos < halfL ? -0.04 : 0.04), {max_h} / 2 - 0.02, zP);
                scene.add(pipe);
            }});
        }}
        createGutterSystemX(-0.02);         
        createGutterSystemX({L} + 0.02);    

        function createLabel(text, x, y, z, className = 'label') {{
            const div = document.createElement('div');
            div.textContent = text;
            div.className = className;
            const labelObj = new CSS2DObject(div);
            labelObj.position.set(x, y, z);
            scene.add(labelObj);
        }}

        function createRealisticDoor(x, z, width, height, rotationY, chamberId) {{
            const doorGroup = new THREE.Group();
            doorGroup.position.set(x, height/2, z);
            doorGroup.rotation.y = rotationY;
            
            const doorPanel = new THREE.Mesh(new THREE.BoxGeometry(width, height, 0.06), doorMat);
            doorGroup.add(doorPanel);
            
            const frameWidth = 0.04;
            const topFrame = new THREE.Mesh(new THREE.BoxGeometry(width + 0.08, frameWidth, 0.07), gutterMat);
            topFrame.position.set(0, height/2 - 0.02, 0);
            doorGroup.add(topFrame);
            
            const leftFrame = new THREE.Mesh(new THREE.BoxGeometry(frameWidth, height + 0.06, 0.07), gutterMat);
            leftFrame.position.set(-width/2 - 0.02, 0, 0);
            doorGroup.add(leftFrame);

            const labelDiv = document.createElement('div');
            labelDiv.textContent = '🚪 K' + chamberId;
            labelDiv.className = 'door-label';
            const doorLabel = new CSS2DObject(labelDiv);
            doorLabel.position.set(0, height/2 + 0.1, 0.045);
            doorGroup.add(doorLabel);
            
            scene.add(doorGroup);
        }}

        // ========== SHAMOL EFFEKTI ==========
        function createRealisticWindParticles(startX, startY, startZ, dir, maxLength) {{
            const pCount = 120; 
            const geometry = new THREE.BufferGeometry();
            const positions = new Float32Array(pCount * 3);
            const colors = new Float32Array(pCount * 3);
            const pData = [];
            const cStart = new THREE.Color(0x38bdf8); 
            const cEnd = new THREE.Color(0xffffff);   

            for (let i = 0; i < pCount; i++) {{
                const progress = Math.random(); 
                const currentLen = progress * maxLength;
                const angle = Math.random() * Math.PI * 2;
                const radius = 0.05 + Math.random() * 0.2; 

                let px = startX + dir.x * currentLen;
                let pz = startZ + dir.z * currentLen;
                let py = startY;

                if (dir.x !== 0) {{ pz += Math.sin(angle) * radius; py += Math.cos(angle) * radius; }}
                else {{ px += Math.sin(angle) * radius; py += Math.cos(angle) * radius; }}

                positions[i*3] = px; positions[i*3+1] = py; positions[i*3+2] = pz;

                const mixedColor = cStart.clone().lerp(cEnd, progress);
                colors[i*3] = mixedColor.r; colors[i*3+1] = mixedColor.g; colors[i*3+2] = mixedColor.b;

                pData.push({{
                    progress: progress, speed: 0.006 + Math.random() * 0.004,
                    angleOffset: Math.random() * Math.PI * 2, radius: radius, spiralSpeed: 3
                }});
            }}
            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

            const points = new THREE.Points(geometry, new THREE.PointsMaterial({{
                size: 0.035, vertexColors: true, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false
            }}));
            scene.add(points);
            particleSystems.push({{ points, pData, startX, startY, startZ, dir, maxLength, cStart, cEnd }});
        }}

        function updateWindParticles() {{
            const time = Date.now() * 0.001;
            particleSystems.forEach(sys => {{
                const posArr = sys.points.geometry.attributes.position.array;
                for (let i = 0; i < sys.pData.length; i++) {{
                    const p = sys.pData[i];
                    p.progress += p.speed;
                    if (p.progress > 1.0) p.progress = 0; 

                    const currentLen = p.progress * sys.maxLength;
                    const currentAngle = p.angleOffset + time * p.spiralSpeed;
                    const currentRadius = p.radius * (1.0 + p.progress * 0.3); 

                    let px = sys.startX + sys.dir.x * currentLen;
                    let pz = sys.startZ + sys.dir.z * currentLen;
                    let py = sys.startY + Math.cos(currentAngle) * currentRadius; 

                    if (sys.dir.x !== 0) pz += Math.sin(currentAngle) * currentRadius;
                    else px += Math.sin(currentAngle) * currentRadius;

                    posArr[i*3] = px; posArr[i*3+1] = py; posArr[i*3+2] = pz;
                }}
                sys.points.geometry.attributes.position.needsUpdate = true;
            }});
        }}

        // ========== BITZER AGREGATI ==========
        function createCompressorUnit(x, z, yBase, rotation, chamberId) {{
            const group = new THREE.Group();
            group.position.set(x, yBase, z);
            group.rotation.y = rotation;
            
            const bitzerGreen = new THREE.MeshStandardMaterial({{ color: 0x005a36, roughness: 0.25, metalness: 0.4 }}); 
            const ironMat = new THREE.MeshStandardMaterial({{ color: 0x334155, roughness: 0.4, metalness: 0.6 }});
            
            const frame = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.06, 0.8), ironMat);
            frame.position.y = 0.03;
            group.add(frame);

            const body = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.7, 16), bitzerGreen);
            body.rotation.z = Math.PI / 2;
            body.position.set(-0.1, 0.3, 0.1);
            group.add(body);

            const condenser = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.7, 0.25), ironMat);
            condenser.position.set(0, 0.38, -0.2);
            group.add(condenser);

            const shroud = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 0.06, 16), ironMat);
            shroud.rotation.x = Math.PI / 2;
            shroud.position.set(0.25, 0.38, 0.06);
            group.add(shroud);
            
            const fanBlades = new THREE.Group();
            fanBlades.position.set(0.25, 0.38, 0.09);
            for (let k = 0; k < 4; k++) {{
                const blade = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.04, 0.01), new THREE.MeshStandardMaterial({{ color: 0x0f172a }}));
                blade.rotation.z = (k * Math.PI) / 2;
                fanBlades.add(blade);
            }}
            group.add(fanBlades);
            animatedFans.push(fanBlades);

            const labelDiv = document.createElement('div');
            labelDiv.textContent = '⚙️ BITZER AGREGAT ' + chamberId;
            labelDiv.className = 'comp-label';
            const compLabel = new CSS2DObject(labelDiv);
            compLabel.position.set(0, 0.9, 0);
            group.add(compLabel);
            
            scene.add(group);
            return {{
                group,
                suctionPort: new THREE.Vector3(-0.2, 0.4, 0.15),
                dischargePort: new THREE.Vector3(0.0, 0.38, 0.15)
            }};
        }}

        function addPipe(points, colorMat, radius=0.014) {{
            const curve = new THREE.CatmullRomCurve3(points);
            const pipe = new THREE.Mesh(new THREE.TubeGeometry(curve, 25, radius, 6, false), colorMat);
            scene.add(pipe);
        }}

        // ========== KAMERALARNI QURISH ==========
        const evaporators = [];
        const compressors = [];
        
        chambers.forEach((c, idx) => {{
            const createWall = (wx, wz, ww, wd, wh) => {{
                const wall = new THREE.Mesh(new THREE.BoxGeometry(ww, wh, wd), wallMat);
                wall.position.set(wx + ww/2, wh/2, wz + wd/2);
                scene.add(wall);
            }};
            
            createWall(c.cx, c.cy + c.cW - T, c.cL, T, c.cH);   
            createWall(c.cx, c.cy, c.cL, T, c.cH);          
            createWall(c.cx, c.cy + T, T, c.cW - 2*T, c.cH);   
            createWall(c.cx + c.cL - T, c.cy + T, T, c.cW - 2*T, c.cH); 
            
            createLabel('Kamera ' + c.id, c.cx + c.cL/2, c.cH + 0.15, c.cy + c.cW/2);
            
            if (c.door && c.door !== "NONE" && c.door !== "side") {{
                let doorX = 0, doorZ = 0, doorRot = 0;
                if (c.door === "FRONT") {{ doorX = c.cL/2; doorZ = -0.01; doorRot = 0; }}
                else if (c.door === "BACK") {{ doorX = c.cL/2; doorZ = c.cW + 0.01; doorRot = Math.PI; }}
                else if (c.door === "LEFT") {{ doorX = -0.01; doorZ = c.cW/2; doorRot = -Math.PI/2; }}
                else if (c.door === "RIGHT") {{ doorX = c.cL + 0.01; doorZ = c.cW/2; doorRot = Math.PI/2; }}
                createRealisticDoor(c.cx + doorX, c.cy + doorZ, doorW, doorH, doorRot, c.id);
            }} else if (c.door === "side") {{
                let doorX = (c.wall_side === "LEFT") ? c.cL + 0.01 : -0.01;
                let doorRot = (c.wall_side === "LEFT") ? Math.PI/2 : -Math.PI/2;
                createRealisticDoor(c.cx + doorX, c.cy + c.cW/2, doorW, doorH, doorRot, c.id);
            }}
            
            // EVAPORATORLAR
            let evX = 0, evZ = c.cW / 2, evRot = 0, airDir = {{ x: 0, z: 0 }};
            if (c.wall_side === "LEFT") {{ evX = T + 0.35; evRot = Math.PI / 2; airDir = {{ x: 1, z: 0 }}; }} 
            else if (c.wall_side === "RIGHT") {{ evX = c.cL - T - 0.35; evRot = -Math.PI / 2; airDir = {{ x: -1, z: 0 }}; }} 
            else if (c.wall_side === "FRONT") {{ evX = c.cL / 2; evZ = T + 0.35; evRot = 0; airDir = {{ x: 0, z: 1 }}; }} 
            else {{ evX = c.cL / 2; evZ = c.cW - T - 0.35; evRot = Math.PI; airDir = {{ x: 0, z: -1 }}; }}
            
            const globalEvX = c.cx + evX;
            const globalEvY = c.cH - 0.45;
            const globalEvZ = c.cy + evZ;
            
            const evapGroup = new THREE.Group();
            evapGroup.position.set(globalEvX, globalEvY, globalEvZ);
            evapGroup.rotation.y = evRot;
            
            const evapBody = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.38, 0.45), floorMat);
            evapGroup.add(evapBody);
            scene.add(evapGroup);
            
            [-0.3, 0, 0.3].forEach(pos => {{
                const blades = new THREE.Group(); blades.position.set(pos, 0, 0.23);
                for (let b = 0; b < 4; b++) {{
                    const blade = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.02, 0.005), new THREE.MeshStandardMaterial({{ color: 0x334155 }}));
                    blade.rotation.z = (b * Math.PI)/2; blades.add(blade);
                }}
                evapGroup.add(blades); animatedFans.push(blades);
            }});
            
            const streamLength = (airDir.x !== 0) ? (c.cL - 0.7) : (c.cW - 0.7);
            createRealisticWindParticles(globalEvX, globalEvY, globalEvZ, airDir, streamLength);
            
            // KOMPRESSORLAR
            let compX = 0, compZ = c.cW / 2, compRot = 0;
            const outDist = T + 0.75;
            if (c.wall_side === "LEFT") {{ compX = -outDist; compRot = -Math.PI / 2; }} 
            else if (c.wall_side === "RIGHT") {{ compX = c.cL + outDist; compRot = Math.PI / 2; }} 
            else if (c.wall_side === "FRONT") {{ compX = c.cL / 2; compZ = -outDist; compRot = 0; }} 
            else {{ compX = c.cL / 2; compZ = c.cW + outDist; compRot = Math.PI; }}
            
            const compressor = createCompressorUnit(c.cx + compX, c.cy + compZ, 0, compRot, c.id);
            forwardPipes(globalEvX, globalEvY, globalEvZ, compressor);
        }});
        
        function forwardPipes(evX, evY, evZ, comp) {{
            comp.group.updateMatrixWorld(true);
            const dPort = comp.dischargePort.clone().applyMatrix4(comp.group.matrixWorld);
            const sPort = comp.suctionPort.clone().applyMatrix4(comp.group.matrixWorld);
            
            addPipe([dPort, new THREE.Vector3(dPort.x, evY + 0.18, dPort.z), new THREE.Vector3(evX, evY + 0.18, evZ), new THREE.Vector3(evX, evY, evZ)], pipeRedMat, 0.011);
            addPipe([sPort, new THREE.Vector3(sPort.x, evY + 0.10, sPort.z), new THREE.Vector3(evX, evY + 0.10, evZ), new THREE.Vector3(evX, evY, evZ)], pipeBlueMat, 0.014);
        }}
        
        createLabel("L " + {L:.1f} + "m", {target_x}, -0.2, -0.6);
        createLabel("W " + {W:.1f} + "m", {L} + 0.6, -0.2, {target_z});
        createLabel("H " + {max_h:.1f} + "m", -0.8, {target_y}, {target_z});
        
        // ========== ANIMATION LOOP ==========
        function animate() {{
            requestAnimationFrame(animate);
            animatedFans.forEach(fan => {{ fan.rotation.z += 0.22; }}); 
            updateWindParticles(); 
            controls.update();
            renderer.render(scene, camera);
            labelRenderer.render(scene, camera);
        }}
        animate();

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight); labelRenderer.setSize(window.innerWidth, window.innerHeight);
        }});
    </script>
</body>
</html>'''
    
    return html_code


def build_segs(sz):
    """
    Oddiy panel segmentlari - burchak modullarisiz.
    Patalok, tom va pol uchun ishlatiladi.
    """
    if sz <= 0:
        return []
    
    segs = []
    rem = sz
    
    while rem >= 960:
        segs.append(960)
        rem -= 960
    
    if rem > 0:
        if rem >= 300:
            segs.append(rem)
        else:
            if segs:
                segs[-1] = 960 + rem
            else:
                segs.append(rem)
    
    return segs

def build_wall_segs(sz, chap_corner=True, ong_corner=True, has_door=False):
    """
    Devor panellarini hisoblaydi
    
    Args:
        sz: Devor uzunligi (mm)
        chap_corner: Chap burchak bormi (True/False)
        ong_corner: O'ng burchak bormi (True/False)
        has_door: Eshik bormi (True/False) - YANGI!
    
    Returns:
        list: Panel segmentlari ro'yxati
        Eshik YO'Q: [480, 960, 960, 960, 960, 480]
        Eshik BOR: [480, 960, 480, 960, 960, 480, 480]
    """
    if sz <= 0:
        return []
    
    CORNER = 480
    MODULE = 960
    
    # Burchaklar
    chap = CORNER if chap_corner else 0
    ong = CORNER if ong_corner else 0
    
    # Asosiy uzunlik (burchaklarsiz)
    main_len = sz - chap - ong
    
    if main_len <= 0:
        segs = []
        if chap_corner:
            segs.append(CORNER)
        if ong_corner:
            segs.append(CORNER)
        return segs
    
    segs = []
    
    # Chap burchak
    if chap_corner:
        segs.append(CORNER)
    
    # =====================================================
    # 1. ESHIK BOR - eshikni o'rtaga joylashtiramiz
    # =====================================================
    if has_door:
        door_w = 960  # Standart eshik kengligi
        remaining = main_len - door_w
        
        if remaining <= 0:
            # Eshik butun devorni egallaydi
            segs.append(main_len)
            if ong_corner:
                segs.append(CORNER)
            return segs
        
        # Ikkiga bo'lamiz (chap va o'ng)
        side_len = remaining / 2
        
        # Chap tomon panellari
        rem = side_len
        while rem >= MODULE:
            segs.append(MODULE)
            rem -= MODULE
        if rem > 0:
            if rem < 300 and len(segs) > 0 and segs[-1] != CORNER:
                segs[-1] += rem
            else:
                segs.append(rem)
        
        # Eshik (960mm)
        segs.append(door_w)
        
        # O'ng tomon panellari (chap tomon bilan simmetrik)
        rem = side_len
        temp_segs = []
        while rem >= MODULE:
            temp_segs.append(MODULE)
            rem -= MODULE
        if rem > 0:
            if rem < 300 and len(temp_segs) > 0:
                temp_segs[-1] += rem
            else:
                temp_segs.append(rem)
        for s in temp_segs:
            segs.append(s)
    
    # =====================================================
    # 2. ESHIK YO'Q - oddiy bo'linish
    # =====================================================
    else:
        rem = main_len
        while rem >= MODULE:
            segs.append(MODULE)
            rem -= MODULE
        if rem > 0:
            if rem < 300 and len(segs) > 0:
                segs[-1] += rem
            else:
                segs.append(rem)
    
    # O'ng burchak
    if ong_corner:
        segs.append(CORNER)
    
    # ===== NATIJANI TEKSHIRISH =====
    total = sum(segs)
    if total != sz:
        diff = sz - total
        if diff != 0 and len(segs) > 1:
            if has_door:
                # Eshik bor: eshik atrofidagi panellarga qo'shamiz
                eshik_index = segs.index(door_w) if door_w in segs else -1
                if eshik_index > 0:
                    segs[eshik_index - 1] += diff / 2
                if eshik_index < len(segs) - 1:
                    segs[eshik_index + 1] += diff / 2
            else:
                # Eshik yo'q: oxirgi panelga qo'shamiz
                segs[-2] += diff
    
    print(f"🔧 build_wall_segs: sz={sz}mm, chap={chap_corner}, ong={ong_corner}, has_door={has_door}")
    print(f"  Natija: {segs} (sum={sum(segs)}mm)")
    
    return segs


def door_off(parts, pos, side="vertical", dsz=960):
    """
    Eshik ofsetini hisoblaydi - 5 VARIANT
    """
    if not parts:
        return 0.0
    
    if dsz <= 0:
        return 0.0
    
    print(f"🔍 door_off: parts={parts}, pos={pos}, side={side}, dsz={dsz}")
    
    # ===== 1. ASOSIY HISOBLAR =====
    total_length = sum(parts)
    print(f"  total_length={total_length}mm")
    
    # Burchak panellarini aniqlash
    has_left_corner = parts[0] == 480 if parts else False
    has_right_corner = parts[-1] == 480 if parts else False
    
    left_corner = parts[0] if has_left_corner else 0
    right_corner = parts[-1] if has_right_corner else 0
    
    print(f"  has_left_corner={has_left_corner}, has_right_corner={has_right_corner}")
    print(f"  left_corner={left_corner}mm, right_corner={right_corner}mm")
    
    # Burchaklarsiz asosiy panellar
    main_parts = [p for p in parts if p != 480]
    main_total = sum(main_parts) if main_parts else 0
    
    print(f"  main_parts={main_parts}")
    print(f"  main_total={main_total}mm")
    
    # Eshik kengligi
    door_w = min(dsz, main_total if main_total > 0 else dsz)
    print(f"  door_w={door_w}mm")
    
    # ===== 2. POSITSIYAGA QARAB OFSET =====
    if pos == "Chap tomon burchak o'rniga":
        # Chap burchakda - chap burchak panelining oxiridan boshlab
        result = float(left_corner)
        print(f"  ✅ Natija (Chap burchak): {result}mm")
        return result
    
    elif pos == "Biroz chapga":
        # Chap burchakdan 300 mm keyin
        result = float(left_corner + 300)
        print(f"  ✅ Natija (Biroz chapga): {result}mm")
        return result
    
    elif pos == "O'rta":
        # ===== DEVR O'RTASIDA - BUTUN DEVOR BO'YICHA =====
        # Eshikni devorning to'liq o'rtasiga joylashtiramiz
        if total_length > door_w:
            offset = (total_length - door_w) / 2
        else:
            offset = 0
        
        result = float(offset)
        print(f"  ✅ Natija (O'rta - to'liq devor): {result}mm")
        print(f"     total_length={total_length} - door_w={door_w} / 2 = {offset:.1f}")
        return result
    
    elif pos == "Biroz o'ngga":
        # O'ng burchakdan 300 mm oldin (asosiy panellar bo'yicha)
        if main_total > door_w:
            offset_in_main = main_total - door_w - 300
        else:
            offset_in_main = 0
        
        # Agar manfiy bo'lsa, o'ng burchakka yaqin joylashtiramiz
        if offset_in_main < 0:
            offset_in_main = 0
        
        result = float(left_corner + offset_in_main)
        print(f"  ✅ Natija (Biroz o'ngga): {result}mm")
        return result
    
    elif pos == "O'ng tomon burchak o'rniga":
        # O'ng burchakda - o'ng burchak panelining boshidan
        if main_total > door_w:
            offset_in_main = main_total - door_w
        else:
            offset_in_main = 0
        
        result = float(left_corner + offset_in_main)
        print(f"  ✅ Natija (O'ng burchak): {result}mm")
        return result
    
    else:
        # Default: o'rta (butun devor bo'yicha)
        if total_length > door_w:
            offset = (total_length - door_w) / 2
        else:
            offset = 0
        
        result = float(offset)
        print(f"  ✅ Natija (default): {result}mm")
        return result

def make_svg(L, W, H, wall_mm, ceil_mm, floor_mm, pol_bor, proj, code, ej, eshik, ep, eo):
    """
    Yagona kamera uchun chizma - 2-6 ta kameralarni qo'llab-quvvatlaydi
    """
    owmm = m_to_mm(L)
    ohmm = m_to_mm(W)
    ozmm = m_to_mm(H)
    
    # ========== ESHIK MA'LUMOTLARI ==========
    eshik_turi = eshik
    if eshik_turi == "Custom":
        eshik_w = st.session_state.get("eshik_custom_width", 900)
        eshik_h = st.session_state.get("eshik_custom_height", 1900)
        eshik_soni = st.session_state.get("eshik_soni", 1)
    else:
        eshik_w, eshik_h = door_dim_custom(eshik_turi)
        eshik_soni = 1
    
    # ========== KAMERA BO'LISH ==========
    kamera_bolish_turi = st.session_state.get("kamera_bolish_turi", "Yo'q")
    kameralar_soni = st.session_state.get("kameralar_soni", 2)
    
    # ========== KAMERALARNI HISOBLASH ==========
    if kamera_bolish_turi == "Uzunlik bo'yicha":
        each_L = L / kameralar_soni
        chambers = []
        for i in range(kameralar_soni):
            chambers.append({
                "id": i + 1,
                "L": each_L,
                "W": W,
                "H": H,
                "x": i * each_L,
                "y": 0,
                "w": each_L,
                "h": W
            })
        eshiklar = []
        if st.session_state.get("har_bir_kamera_eshik", False):
            for i in range(kameralar_soni):
                eshik_joyi = st.session_state.get(f"kamera_eshik_joyi_{i}", "Old")
                eshik_pozitsiya = st.session_state.get(f"kamera_eshik_pozitsiya_{i}", "O'rta")
                if eshik_turi != "Yo'q":
                    eshiklar.append({
                        "tur": eshik_turi,
                        "width": eshik_w,
                        "height": eshik_h,
                        "soni": eshik_soni,
                        "joyi": eshik_joyi,
                        "pozitsiya": eshik_pozitsiya,
                        "ochilish": "Ichkariga"
                    })
        else:
            if eshik_turi != "Yo'q":
                eshiklar.append({
                    "tur": eshik_turi,
                    "width": eshik_w,
                    "height": eshik_h,
                    "soni": eshik_soni,
                    "joyi": ej,
                    "pozitsiya": ep,
                    "ochilish": eo
                })
    
    elif kamera_bolish_turi == "Eni bo'yicha":
        each_W = W / kameralar_soni
        chambers = []
        for i in range(kameralar_soni):
            chambers.append({
                "id": i + 1,
                "L": L,
                "W": each_W,
                "H": H,
                "x": 0,
                "y": i * each_W,
                "w": L,
                "h": each_W
            })
        eshiklar = []
        if st.session_state.get("har_bir_kamera_eshik", False):
            for i in range(kameralar_soni):
                eshik_joyi = st.session_state.get(f"kamera_eshik_joyi_{i}", "Old")
                eshik_pozitsiya = st.session_state.get(f"kamera_eshik_pozitsiya_{i}", "O'rta")
                if eshik_turi != "Yo'q":
                    eshiklar.append({
                        "tur": eshik_turi,
                        "width": eshik_w,
                        "height": eshik_h,
                        "soni": eshik_soni,
                        "joyi": eshik_joyi,
                        "pozitsiya": eshik_pozitsiya,
                        "ochilish": "Ichkariga"
                    })
        else:
            if eshik_turi != "Yo'q":
                eshiklar.append({
                    "tur": eshik_turi,
                    "width": eshik_w,
                    "height": eshik_h,
                    "soni": eshik_soni,
                    "joyi": ej,
                    "pozitsiya": ep,
                    "ochilish": eo
                })
    
    else:
        chambers = [{"L": L, "W": W, "H": H, "id": 1, "x": 0, "y": 0, "w": L, "h": W}]
        eshiklar = []
        if eshik_turi != "Yo'q":
            eshiklar.append({
                "tur": eshik_turi,
                "width": eshik_w,
                "height": eshik_h,
                "soni": eshik_soni,
                "joyi": ej,
                "pozitsiya": ep,
                "ochilish": eo
            })
    
    # ========== AGAR BO'LINGAN BO'LSA ==========
    if kamera_bolish_turi != "Yo'q" and kameralar_soni > 1:
        return make_svg_split_multi(
            L, W, H, wall_mm, ceil_mm, floor_mm, pol_bor,
            proj, code, chambers, eshiklar,
            kamera_bolish_turi, kameralar_soni
        )
    
    # ========== YAGONA KAMERA ==========
    ch = chambers[0]
    Lc = ch["L"]
    Wc = ch["W"]
    Hc = ch["H"]
    
    owmm_c = m_to_mm(Lc)
    ohmm_c = m_to_mm(Wc)
    ozmm_c = m_to_mm(Hc)
    
    # ========== BURCHAK HOLATI ==========
    corners = {
        "chap_tepa": True,
        "chap_past": True,
        "ong_tepa": True,
        "ong_past": True
    }
    
    if eshik_turi != "Yo'q":
        if ej == "Chap":
            if ep == "Chap tomon burchak o'rniga":
                corners["chap_tepa"] = False
                corners["chap_past"] = False
        elif ej == "O'ng":
            if ep == "O'ng tomon burchak o'rniga":
                corners["ong_tepa"] = False
                corners["ong_past"] = False
        elif ej == "Old":
            if ep == "Chap tomon burchak o'rniga":
                corners["chap_past"] = False
            elif ep == "O'ng tomon burchak o'rniga":
                corners["ong_past"] = False
        elif ej == "Orqa":
            if ep == "Chap tomon burchak o'rniga":
                corners["chap_tepa"] = False
            elif ep == "O'ng tomon burchak o'rniga":
                corners["ong_tepa"] = False
    
    # Devor panellari
    chap_burchak_bor = corners["chap_tepa"] and corners["chap_past"]
    ong_burchak_bor = corners["ong_tepa"] and corners["ong_past"]
    
    tp = build_wall_segs(owmm_c, chap_burchak_bor, ong_burchak_bor)
    rp = build_wall_segs(ohmm_c, chap_burchak_bor, ong_burchak_bor)
    
    # Eshik
    has_door = (eshik_turi != "Yo'q")
    dwmm = eshik_w if has_door else 0
    dhmm = eshik_h if has_door else 0
    
    # ========== ESHIK OFSETINI HISOBLASH ==========
    # doff ni oldindan hisoblaymiz va keyin ishlatamiz
    doff = 0
    if has_door:
        if ej == "Chap" or ej == "O'ng":
            doff = door_off(rp, ep, "vertical", dwmm)
        elif ej == "Old" or ej == "Orqa":
            doff = door_off(tp, ep, "horizontal", dwmm)
    
    tm = seg_meta(tp, has_door=(has_door and ej in ["Old", "Orqa"]), door_sz=dwmm)
    rm = seg_meta(rp, has_door=(has_door and ej in ["Chap", "O'ng"]), door_sz=dwmm)
    
    # ========== PATALOK VA POL ==========
    tpl_segs = build_segs(owmm_c)
    rpl_segs = build_segs(ohmm_c)
    
    t_slab_meta = seg_meta(tpl_segs, has_door=False, door_sz=0)
    r_slab_meta = seg_meta(rpl_segs, has_door=False, door_sz=0)
    
    tpl = [{"size": p, "type": "panel"} for p in tpl_segs]
    rpl = [{"size": p, "type": "panel"} for p in rpl_segs]
    
    # ========== MASSHTAB ==========
    scale = min(250 / max(owmm_c, 1), 185 / max(ohmm_c, 1))
    dw = owmm_c * scale
    dh = ohmm_c * scale
    wt = max(5, wall_mm * scale)
    SW, SH = 794, 1420
    px = 390 - dw / 2
    py = 115
    my = py + dh + 92
    by = my + dh + 82
    tb = min(by + dh + 55, 978)
    
    # Ichki o'lchamlar
    iL = max(0, owmm_c - 2 * wall_mm)
    iW = max(0, ohmm_c - 2 * wall_mm)
    iH = max(0, ozmm_c - ceil_mm - (floor_mm if pol_bor else 0))
    
    # ========== PANEL JADVALI ==========
    panel_rows = build_panel_table_for_split(
        owmm, ohmm, ozmm, wall_mm, ceil_mm, floor_mm, pol_bor,
        chambers, eshiklar
    )
    
    fixed_panel_rows = []
    for row in panel_rows:
        if "Potolok/Pol paneli" in row.get("Nomi", ""):
            row["Soni"] = row["Soni"] * (len(tpl_segs) // 2 if len(tpl_segs) > 2 else 2)
            row["Maydon m²"] = (row["Uzunlik"] / 1000) * (row["Eni"] / 1000) * row["Soni"]
        fixed_panel_rows.append(row)

    table_svg = make_ecofrom_table_svg(fixed_panel_rows, x=30, y=by + dh + 110, width=730)
    
    # ========== ESHIK CHIZISH (doff dan foydalanamiz) ==========
    ds = ""
    dn = ""
    if has_door:
        if ej == "Chap":
            ds = arc_left(px, py, scale, doff, dhmm, dwmm, eo)
            dn = svgt(px - 28, py + doff * scale + dwmm * scale / 2, 
                      f"{dwmm}x{dhmm}", size=8, rotate=90, color="#333")
        elif ej == "O'ng":
            ds = arc_right(px, py, dw, scale, doff, dhmm, dwmm, eo)
            dn = svgt(px + dw + 28, py + doff * scale + dwmm * scale / 2, 
                      f"{dwmm}x{dhmm}", size=8, rotate=90, color="#333")
        elif ej == "Old":
            ds = arc_bottom(px, py, dh, scale, doff, dwmm, eo)
            dn = svgt(px + doff * scale + dwmm * scale / 2, py + dh + 14, 
                      f"{dwmm}x{dhmm}", size=8, color="#333")
        elif ej == "Orqa":
            ds = arc_top(px, py, scale, doff, dwmm, eo)
            dn = svgt(px + doff * scale + dwmm * scale / 2, py - 6, 
                      f"{dwmm}x{dhmm}", size=8, color="#333")
    
    # ========== BURCHAK CHIZIQLARI ==========
    burchak_chiziqlari = ""
    if corners["chap_tepa"]:
        burchak_chiziqlari += f'<line x1="{px}" y1="{py + 2}" x2="{px + 480 * scale}" y2="{py + 2}" stroke="#16A34A" stroke-width="2"/>'
        burchak_chiziqlari += f'<text x="{px + 240 * scale}" y="{py - 6}" font-size="7" fill="#16A34A" text-anchor="middle">480</text>'
    if corners["chap_past"]:
        burchak_chiziqlari += f'<line x1="{px}" y1="{py + dh - 2}" x2="{px + 480 * scale}" y2="{py + dh - 2}" stroke="#16A34A" stroke-width="2"/>'
        burchak_chiziqlari += f'<text x="{px + 240 * scale}" y="{py + dh + 14}" font-size="7" fill="#16A34A" text-anchor="middle">480</text>'
    if corners["ong_tepa"]:
        burchak_chiziqlari += f'<line x1="{px + dw - 480 * scale}" y1="{py + 2}" x2="{px + dw}" y2="{py + 2}" stroke="#16A34A" stroke-width="2"/>'
        burchak_chiziqlari += f'<text x="{px + dw - 240 * scale}" y="{py - 6}" font-size="7" fill="#16A34A" text-anchor="middle">480</text>'
    if corners["ong_past"]:
        burchak_chiziqlari += f'<line x1="{px + dw - 480 * scale}" y1="{py + dh - 2}" x2="{px + dw}" y2="{py + dh - 2}" stroke="#16A34A" stroke-width="2"/>'
        burchak_chiziqlari += f'<text x="{px + dw - 240 * scale}" y="{py + dh + 14}" font-size="7" fill="#16A34A" text-anchor="middle">480</text>'
    
    # ========== KOMPAS ==========
    cx_, cy_ = SW - 46, py + 18
    comp_svg = (f'<circle cx="{cx_}" cy="{cy_}" r="13" fill="none" stroke="#888" stroke-width="1"/>'
                f'<line x1="{cx_}" y1="{cy_ - 11}" x2="{cx_}" y2="{cy_ + 11}" stroke="#888" stroke-width="1"/>'
                f'<line x1="{cx_ - 11}" y1="{cy_}" x2="{cx_ + 11}" y2="{cy_}" stroke="#888" stroke-width="1"/>'
                f'<polygon points="{cx_},{cy_ - 11} {cx_ - 4},{cy_} {cx_ + 4},{cy_}" fill="#333"/>'
                + svgt(cx_, cy_ - 16, "N", size=8, weight="700", color="#333"))
    
    pol_lbl = f"Qalinligi: {floor_mm if pol_bor else 0} mm  ({'Bor' if pol_bor else 'Yoq'})"
    
    chamber_info = ""
    if len(chambers) > 1:
        chamber_info = f" | {len(chambers)} ta kamera"
        for i, ch_info in enumerate(chambers):
            chamber_info += f" | K{i+1}: {ch_info['L']:.1f}x{ch_info['W']:.1f}m"
    
    # ========== DEBUG MA'LUMOTLARI ==========
    door_segments = rp if ej in ["Chap", "O'ng"] else tp
    main_parts = [p for p in door_segments if p != 480]
    main_total = sum(main_parts) if main_parts else 0
    door_width = min(dwmm, main_total) if main_total > 0 else dwmm
    
    debug_lines = f'''
    <!-- ===== DEBUG MA'LUMOTLARI ===== -->
    <rect x="20" y="130" width="{SW-40}" height="190" fill="#FFF8E1" stroke="#FF6F00" stroke-width="2" rx="6"/>
    <text x="35" y="155" font-size="13" fill="#000000" font-weight="bold" font-family="monospace">🔍 ESHIK DEBUG MA'LUMOTLARI</text>
    <line x1="35" y1="165" x2="{SW-35}" y2="165" stroke="#FF6F00" stroke-width="0.5"/>
    
    <text x="35" y="185" font-size="11" fill="#0000FF" font-family="monospace">📌 Eshik joyi: {ej} | Pozitsiya: {ep} | Ochilish: {eo}</text>
    <text x="35" y="205" font-size="11" fill="#0000FF" font-family="monospace">📏 Eshik o'lchami: {dwmm}mm x {dhmm}mm</text>
    <text x="35" y="225" font-size="11" fill="#008000" font-family="monospace">📋 door_segments: {door_segments}</text>
    <text x="35" y="245" font-size="11" fill="#FF0000" font-family="monospace">📋 main_parts (480 larsiz): {main_parts}</text>
    <text x="35" y="265" font-size="11" fill="#8B008B" font-family="monospace">📊 main_total: {main_total}mm | door_width: {door_width}mm</text>
    <text x="35" y="285" font-size="11" fill="#D2691E" font-family="monospace">🎯 doff (door_off): {doff:.1f}mm</text>
    <text x="35" y="305" font-size="11" fill="#000000" font-family="monospace">🔲 Chap burchak: {corners['chap_tepa']} | O'ng burchak: {corners['ong_tepa']}</text>
    '''
    
    # ========== SVG ==========
    return f'''<svg width="100%" viewBox="0 0 {SW} {SH + 120}" xmlns="http://www.w3.org/2000/svg">
<rect x="20" y="20" width="{SW - 40}" height="{SH + 80}" fill="white" stroke="#111" stroke-width="1.2"/>
{svgt(390, 56, "TEXNIK CHIZMA", size=14, weight="700")}
{svgt(390, 74, (proj or "").upper() + chamber_info, size=11)}
{svgt(SW - 28, 56, code, size=10, anchor="end", color="#888")}
{comp_svg}

{debug_lines}

{svgt(px + dw / 2, py - 34, "DEVOR REJASI  (TOP VIEW)", size=10, weight="700", color="#555")}
{room_plan(px, py, dw, dh, wt)}
{ds}{dn}

<!-- O'LCHAMLAR 4 TOMONDAN -->
{chain_top(px, py, tm, scale)}
{chain_bottom(px, py+dh, tm, scale)}
{chain_left(px, py, rm, scale)}
{chain_right(px+dw, py, rm, scale)}

{ticks_h(px, py, tm, scale)}
{ticks_h(px, py+dh, tm, scale)}
{ticks_v(px, py, rm, scale)}
{ticks_v(px+dw, py, rm, scale)}

{svgt(px + dw / 2, py + dh / 2 - 6, f"Tashqi: {owmm_c}x{ohmm_c}x{ozmm_c} mm", size=8, color="#999")}
{svgt(px + dw / 2, py + dh / 2 + 8, f"Ichki:  {iL}x{iW}x{iH} mm", size=8, color="#999")}
{svgt(px + dw / 2, py + dh + 22, f"Devor qalinligi: {wall_mm} mm", size=9, color="#555")}

{burchak_chiziqlari}

{slab_svg(px, my, dw, dh, tpl, rpl, scale, "PATALOK PANELI")}
{chain_top(px, my, t_slab_meta, scale)}
{chain_bottom(px, my+dh, t_slab_meta, scale)}
{chain_left(px, my, r_slab_meta, scale)}
{chain_right(px+dw, my, r_slab_meta, scale)}
{ticks_h(px, my, t_slab_meta, scale)}
{ticks_h(px, my+dh, t_slab_meta, scale)}
{ticks_v(px, my, r_slab_meta, scale)}
{ticks_v(px+dw, my, r_slab_meta, scale)}

{slab_svg(px, by, dw, dh, tpl, rpl, scale, "POL PANELI")}
{chain_top(px, by, t_slab_meta, scale)}
{chain_bottom(px, by+dh, t_slab_meta, scale)}
{chain_left(px, by, r_slab_meta, scale)}
{chain_right(px+dw, by, r_slab_meta, scale)}
{ticks_h(px, by, t_slab_meta, scale)}
{ticks_h(px, by+dh, t_slab_meta, scale)}
{ticks_v(px, by, r_slab_meta, scale)}
{ticks_v(px+dw, by, r_slab_meta, scale)}

<rect x="30" y="{my}" width="10" height="10" fill="#16A34A"/>
{svgt(46, my + 9, "480 mm burchak moduli", size=8, anchor="start", color="#666")}
<rect x="30" y="{my + 15}" width="10" height="10" fill="none" stroke="#8898A8" stroke-width="1" stroke-dasharray="3,2"/>
{svgt(46, my + 24, "960 mm asosiy modul", size=8, anchor="start", color="#666")}

<!-- ESHIK BELGILARI -->
<rect x="200" y="{my}" width="10" height="10" fill="#059669" rx="2"/>
{svgt(216, my + 9, "Eshik ochilish chizig'i", size=8, anchor="start", color="#666")}
<rect x="200" y="{my + 15}" width="10" height="10" fill="#fef3c7" stroke="#d97706" stroke-width="1" rx="2"/>
{svgt(216, my + 24, "Eshik joylashuvi", size=8, anchor="start", color="#666")}

{table_svg}

{title_block(115, tb, 560, 110, proj or "-", code, owmm_c, ohmm_c, ozmm_c, wall_mm, ceil_mm, floor_mm if pol_bor else 0, datetime.now().strftime("%d.%m.%Y"))}
</svg>'''



def build_panel_table_for_split(owmm, ohmm, ozmm, wall_mm, ceil_mm, floor_mm, pol_bor,
                                chambers, eshiklar=None):
    """
    Bo'lingan kameralar uchun panel hisobi - 5 VARIANTLI ESHIK POZITSIYASI
    BURCHAK PANELLARI 2 GA KO'PAYTIRILADI
    """
    all_panels = []

    # ========== 1. TASHQI DEVORLAR ==========
    total_wall_panels = {}
    
    L_outer = owmm
    W_outer = ohmm
    H_outer = ozmm
    
    L_inner = max(0, L_outer - 2 * wall_mm)
    W_inner = max(0, W_outer - 2 * wall_mm)
    H_inner = max(0, H_outer - ceil_mm - (floor_mm if pol_bor else 0))
    
    # ========== BURCHAK PANELLARINI HISOBLASH ==========
    corners = {
        "chap_tepa": True,
        "chap_past": True,
        "ong_tepa": True,
        "ong_past": True
    }
    
    bolish_turi = st.session_state.get("kamera_bolish_turi", "Yo'q")
    har_bir_kamera_eshik = st.session_state.get("har_bir_kamera_eshik", False)
    
    if eshiklar:
        for idx, esh in enumerate(eshiklar):
            if esh.get("tur") != "Yo'q":
                eshik_joyi = esh.get("joyi", "Old")
                eshik_positsiya = esh.get("pozitsiya", "O'rta")
                
                if bolish_turi == "Eni bo'yicha":
                    if idx == 0:
                        if eshik_joyi == "Chap" and eshik_positsiya == "Chap tomon burchak o'rniga":
                            corners["chap_tepa"] = False
                    
                    if idx == len(chambers) - 1:
                        if eshik_joyi == "O'ng" and eshik_positsiya == "O'ng tomon burchak o'rniga":
                            corners["ong_tepa"] = False
                            corners["ong_past"] = False
                
                else:
                    if eshik_joyi == "Chap":
                        if eshik_positsiya == "Chap tomon burchak o'rniga":
                            corners["chap_tepa"] = False
                            corners["chap_past"] = False
                    elif eshik_joyi == "O'ng":
                        if eshik_positsiya == "O'ng tomon burchak o'rniga":
                            corners["ong_tepa"] = False
                            corners["ong_past"] = False
                    elif eshik_joyi == "Old":
                        if eshik_positsiya == "Chap tomon burchak o'rniga":
                            corners["chap_past"] = False
                        elif eshik_positsiya == "O'ng tomon burchak o'rniga":
                            corners["ong_past"] = False
                    elif eshik_joyi == "Orqa":
                        if eshik_positsiya == "Chap tomon burchak o'rniga":
                            corners["chap_tepa"] = False
                        elif eshik_positsiya == "O'ng tomon burchak o'rniga":
                            corners["ong_tepa"] = False
    
    # Nechta burchak paneli kerak?
    corner_count = sum(1 for v in corners.values() if v)
    
    # ========== BURCHAK PANELLARI - 2 GA KO'PAYTIRILADI ==========
    if corner_count > 0:
        # Burchak paneli eni 480 mm, lekin maydon hisobida 960 mm sifatida hisoblanadi
        # Shuning uchun 2 ga ko'paytiramiz
        corner_panel = {
            "name": "Burchak paneli",
            "length": H_outer,
            "width": 480,
            "thickness": wall_mm,
            "qty": corner_count,
            # Burchak paneli 480 mm, lekin maydon 960 mm ga teng (2 ga ko'paytiriladi)
            "total_m2": round((H_outer / 1000) * (480 / 1000) * corner_count * 2, 3)
        }
    else:
        corner_panel = None
    
    # ========== TASHQI DEVORLAR - ALOHIDA HISOB ==========
    chap_tepa_bor = corners["chap_tepa"]
    ong_tepa_bor = corners["ong_tepa"]
    chap_past_bor = corners["chap_past"]
    ong_past_bor = corners["ong_past"]
    
    # TEPA devor
    wall_segs_tepa = build_wall_segs(L_outer, chap_tepa_bor, ong_tepa_bor)
    wall_segs_tepa_no_corner = [s for s in wall_segs_tepa if s != 480]
    
    for seg in wall_segs_tepa_no_corner:
        key = f"Tashqi_Devor_TEPA_{seg}_{wall_mm}"
        if key not in total_wall_panels:
            total_wall_panels[key] = {
                "name": "Devor paneli (Tepa)",
                "length": H_outer,
                "width": seg,
                "thickness": wall_mm,
                "qty": 0,
                "total_m2": 0
            }
        total_wall_panels[key]["qty"] += 1
        total_wall_panels[key]["total_m2"] += round((H_outer / 1000) * (seg / 1000), 3)
    
    # PAST devor
    wall_segs_past = build_wall_segs(L_outer, chap_past_bor, ong_past_bor)
    wall_segs_past_no_corner = [s for s in wall_segs_past if s != 480]
    
    for seg in wall_segs_past_no_corner:
        key = f"Tashqi_Devor_PAST_{seg}_{wall_mm}"
        if key not in total_wall_panels:
            total_wall_panels[key] = {
                "name": "Devor paneli (Past)",
                "length": H_outer,
                "width": seg,
                "thickness": wall_mm,
                "qty": 0,
                "total_m2": 0
            }
        total_wall_panels[key]["qty"] += 1
        total_wall_panels[key]["total_m2"] += round((H_outer / 1000) * (seg / 1000), 3)
    
    # CHAP/O'NG devorlar
    wall_segs_short = build_wall_segs(W_outer, chap_past_bor, ong_past_bor)
    wall_segs_short_no_corner = [s for s in wall_segs_short if s != 480]
    
    for seg in wall_segs_short_no_corner:
        key = f"Tashqi_Devor_W_{seg}_{wall_mm}"
        if key not in total_wall_panels:
            total_wall_panels[key] = {
                "name": "Devor paneli",
                "length": H_outer,
                "width": seg,
                "thickness": wall_mm,
                "qty": 0,
                "total_m2": 0
            }
        total_wall_panels[key]["qty"] += 2
        total_wall_panels[key]["total_m2"] += round((H_outer / 1000) * (seg / 1000) * 2, 3)

    # ========== 2. ICHKI DEVORLAR ==========
    if len(chambers) > 1:
        inner_wall_qty = len(chambers) - 1
        inner_segs = build_segs(L_inner)
        
        for seg in inner_segs:
            key = f"Ichki_Devor_{seg}_{wall_mm}"
            if key not in total_wall_panels:
                total_wall_panels[key] = {
                    "name": "Ichki devor paneli",
                    "length": H_inner,
                    "width": seg,
                    "thickness": wall_mm,
                    "qty": 0,
                    "total_m2": 0
                }
            total_wall_panels[key]["qty"] += inner_wall_qty
            total_wall_panels[key]["total_m2"] += round((H_inner / 1000) * (seg / 1000) * inner_wall_qty, 3)

    # ========== 3. PATALOK VA POL PANELLARI ==========
    total_slab_panels = {}
    
    slab_segs = build_segs(W_outer)
    
    for seg in slab_segs:
        key = f"Slab_{seg}_{ceil_mm}"
        if key not in total_slab_panels:
            total_slab_panels[key] = {
                "name": "Potolok/Pol paneli",
                "length": L_outer,
                "width": seg,
                "thickness": ceil_mm,
                "qty": 0,
                "total_m2": 0
            }
        total_slab_panels[key]["qty"] += 1
        total_slab_panels[key]["total_m2"] += round((L_outer / 1000) * (seg / 1000), 3)
        
        if pol_bor:
            total_slab_panels[key]["qty"] += 1
            total_slab_panels[key]["total_m2"] += round((L_outer / 1000) * (seg / 1000), 3)

    # ========== 4. ESHIK USTIDAGI PANELLAR ==========
    eshik_ust_panels = {}
    
    if eshiklar:
        for esh in eshiklar:
            if esh.get("tur") != "Yo'q":
                dh = esh.get("height", 2000)
                dw = esh.get("width", 960)
                soni = esh.get("soni", 1)
                
                ust_balandlik = H_outer - dh
                
                if ust_balandlik > 0:
                    key = f"Eshik_usti_{dw}_{ust_balandlik}_{wall_mm}"
                    if key not in eshik_ust_panels:
                        eshik_ust_panels[key] = {
                            "name": "Eshik ustidagi panel",
                            "length": ust_balandlik,
                            "width": dw,
                            "thickness": wall_mm,
                            "qty": 0,
                            "total_m2": 0
                        }
                    eshik_ust_panels[key]["qty"] += soni
                    eshik_ust_panels[key]["total_m2"] += round(
                        (ust_balandlik / 1000) * (dw / 1000) * soni, 3
                    )

    # ========== 5. BARCHA PANELLARNI BIRLASHTIRISH ==========
    all_panels_list = []
    
    if corner_panel:
        all_panels_list.append(corner_panel)
    
    for key, p in total_wall_panels.items():
        all_panels_list.append({
            "name": p["name"],
            "length": p["length"],
            "width": p["width"],
            "thickness": p["thickness"],
            "qty": p["qty"],
            "total_m2": round(p["total_m2"], 3)
        })
    
    for key, p in total_slab_panels.items():
        all_panels_list.append({
            "name": p["name"],
            "length": p["length"],
            "width": p["width"],
            "thickness": p["thickness"],
            "qty": p["qty"],
            "total_m2": round(p["total_m2"], 3)
        })
    
    for key, p in eshik_ust_panels.items():
        all_panels_list.append(p)

    # ========== ESHIKLAR (FAQAT SONI) ==========
    if eshiklar:
        eshik_groups = {}
        for esh in eshiklar:
            if esh.get("tur") != "Yo'q":
                dw, dh = door_dim_custom(esh["tur"], esh.get("width"), esh.get("height"))
                key = f"Eshik_{dw}_{dh}_{wall_mm}"
                if key not in eshik_groups:
                    eshik_groups[key] = {
                        "name": "Eshik",
                        "length": dh,
                        "width": dw,
                        "thickness": wall_mm,
                        "qty": 0,
                        "total_m2": 0
                    }
                eshik_groups[key]["qty"] += esh.get("soni", 1)
        
        for key, p in eshik_groups.items():
            all_panels_list.append(p)

    # BIR XIL O'LCHAMLARNI BIRLASHTIRISH
    merged = {}
    for p in all_panels_list:
        key = f"{p['name']}_{p['length']}_{p['width']}_{p['thickness']}"
        if key in merged:
            merged[key]["qty"] += p["qty"]
            if p["name"] != "Eshik":
                merged[key]["total_m2"] = round(merged[key]["total_m2"] + p["total_m2"], 3)
        else:
            merged[key] = p.copy()

    # ROWS YARATISH
    rows = []
    for panel_id, (_, p) in enumerate(merged.items(), start=1):
        rows.append({
            "name": p["name"],
            "length": p["length"],
            "width": p["width"],
            "thickness": p["thickness"],
            "qty": p["qty"],
            "total_m2": round(p["total_m2"], 3) if p["name"] != "Eshik" else 0
        })

    def sort_key(row):
        order = {"Burchak paneli": 0, "Devor paneli (Tepa)": 1, "Devor paneli (Past)": 2, 
                 "Devor paneli": 3, "Ichki devor paneli": 4, 
                 "Potolok/Pol paneli": 5, "Eshik ustidagi panel": 6, "Eshik": 7}
        return order.get(row["name"], 99)
    
    rows.sort(key=sort_key)
    return rows







def make_ecofrom_table_svg(rows, x=30, y=420, width=900, devor_narx=0, patalok_narx=0, pol_narx=0, eshik_narx=0):
    """
    Panel spetsifikatsiya jadvali - KATTA VA ANIQ
    Narxlar avtomatik hisoblanadi
    """
    if not rows:
        return f'<svg x="{x}" y="{y}" width="{width}" height="80" xmlns="http://www.w3.org/2000/svg"><text x="10" y="40" font-size="16" fill="#888" font-weight="600">Panel ma\'lumotlari yo\'q</text></svg>'

    # ========== KATTAROQ O'LCHAMLAR ==========
    row_h = 30
    header_h = 48
    title_h = 55
    footer_h = 90
    padding = 20

    total_rows = len(rows)
    table_h = title_h + header_h + total_rows * row_h + footer_h + padding
    svg_h = table_h + 20

    # ========== JAMI HISOB ==========
    total_qty = 0
    total_m2 = 0.0
    total_price = 0.0
    
    for r in rows:
        # Eshikni hisobdan chiqaramiz (faqat Eshik, Eshik ustidagi panel emas)
        if r["name"] == "Eshik":
            continue
        
        qty_val = r["qty"]
        if isinstance(qty_val, str):
            try:
                qty_val = int(''.join(filter(str.isdigit, qty_val)))
            except:
                qty_val = 0
        elif not isinstance(qty_val, (int, float)):
            qty_val = 0
        total_qty += qty_val
        
        m2_val = r["total_m2"]
        if isinstance(m2_val, str):
            try:
                m2_val = float(m2_val.replace(',', '.'))
            except:
                m2_val = 0.0
        elif not isinstance(m2_val, (int, float)):
            m2_val = 0.0
        total_m2 += m2_val
    
    total_m2 = round(total_m2, 2)

    # ========== KENGAYTIRILGAN USTUNLAR ==========
    c = {
        "name": 230,
        "len": 70,
        "wid": 70,
        "thk": 70,
        "qty": 60,
        "m2": 80,
        "price": 90,
        "sum": 90
    }
    
    cx = {}
    cur = 0
    for k, v in c.items():
        cx[k] = cur
        cur += v
    total_w = cur

    scale = width / total_w

    def col(key):
        return cx[key] * scale

    def cw(key):
        return c[key] * scale

    def cell(x_pos, y_pos, w, h, text, bold=False, bg=None, color="#1e293b", align="middle", size=11):
        rect = f'<rect x="{x_pos:.1f}" y="{y_pos:.1f}" width="{w:.1f}" height="{h}" fill="{bg or "white"}" stroke="#cbd5e1" stroke-width="1"/>'
        tx = x_pos + w/2 if align == "middle" else x_pos + 6
        anchor = "middle" if align == "middle" else "start"
        fw = "bold" if bold else "normal"
        txt = f'<text x="{tx:.1f}" y="{y_pos + h/2 + 4:.1f}" font-size="{size}" font-weight="{fw}" fill="{color}" text-anchor="{anchor}" font-family="Arial,sans-serif">{text}</text>'
        return rect + txt

    # ========== SVG QURISH ==========
    svg = f'<svg x="{x}" y="{y}" width="{width}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">'

    # Tashqi ramka
    svg += f'<rect x="0" y="0" width="{width}" height="{svg_h}" rx="10" fill="white" stroke="#64748b" stroke-width="2"/>'

    # Sarlavha
    svg += f'<rect x="0" y="0" width="{width}" height="{title_h}" rx="10" fill="#0f172a"/>'
    svg += f'<rect x="0" y="{title_h-10}" width="{width}" height="10" fill="#0f172a"/>'
    svg += f'<text x="{width/2}" y="{title_h/2 + 7}" font-size="18" font-weight="900" fill="white" text-anchor="middle" font-family="Arial,sans-serif" letter-spacing="1">📋 PANEL SPETSIFIKATSIYASI</text>'
    svg += f'<text x="{width - 20}" y="{title_h/2 + 7}" font-size="11" fill="#94a3b8" text-anchor="end" font-family="Arial,sans-serif">v.1.0</text>'

    # Sarlavha qatori
    hy = title_h
    headers = [
        ("name", "NOMI", True),
        ("len", "UZUNLIK", True),
        ("wid", "ENI (mm)", True),
        ("thk", "QALINLIK", True),
        ("qty", "SONI", True),
        ("m2", "MAYDON m²", True),
        ("price", "NARX $/m²", True),
        ("sum", "SUMMA $", True),
    ]
    for key, label, bold in headers:
        svg += cell(col(key), hy, cw(key), header_h, label, bold=True, bg="#f1f5f9", color="#1e293b", size=12)

    # Ma'lumot qatorlari
    colors_alt = ["#ffffff", "#f8fafc"]
    total_sum = 0.0
    total_eshik_sum = 0.0
    
    for i, row in enumerate(rows):
        ry = title_h + header_h + i * row_h
        bg = colors_alt[i % 2]

        name = str(row["name"])
        
        # ===== RANGLI NOMLAR VA NARXLAR =====
        if "Burchak" in name:
            name_color = "#16a34a"
            panel_narx = devor_narx
        elif "Ichki devor" in name:
            name_color = "#8b5cf6"
            panel_narx = devor_narx
        elif "Devor" in name:
            name_color = "#1d4ed8"
            panel_narx = devor_narx
        elif "Potolok" in name or "Patalok" in name:
            name_color = "#7c3aed"
            panel_narx = patalok_narx
        elif "Pol" in name and "Potolok" not in name:
            name_color = "#059669"
            panel_narx = pol_narx
        elif "Eshik ustidagi" in name or "Eshik_usti" in name:
            name_color = "#f59e0b"  # To'q sariq rang
            panel_narx = devor_narx  # Devor narxi bilan hisoblanadi
        elif "Eshik" in name and "ustidagi" not in name:
            name_color = "#dc2626"
            panel_narx = eshik_narx
        else:
            name_color = "#1e293b"
            panel_narx = devor_narx

        qty_display = str(row["qty"])
        m2_display = f"{row['total_m2']:.2f}"
        
        # ===== NARXNI HISOBLASH =====
        if "Eshik" in name and "ustidagi" not in name:
            # Eshik (faqat eshik, ustidagi panel emas)
            eshik_soni = row["qty"]
            if isinstance(eshik_soni, str):
                try:
                    eshik_soni = int(''.join(filter(str.isdigit, eshik_soni)))
                except:
                    eshik_soni = 1
            panel_sum = eshik_soni * panel_narx
            total_eshik_sum += panel_sum
            price_display = f"{panel_narx:.0f}"
            sum_display = f"${panel_sum:,.0f}"
            m2_display = "-"
        else:
            # Barcha panellar (shu jumladan Eshik ustidagi panel)
            panel_sum = row['total_m2'] * panel_narx
            total_sum += panel_sum
            price_display = f"{panel_narx:.0f}"
            sum_display = f"${panel_sum:,.0f}"

        svg += cell(col("name"), ry, cw("name"), row_h, name, bg=bg, color=name_color, bold=True, align="start", size=10)
        svg += cell(col("len"), ry, cw("len"), row_h, str(row["length"]), bg=bg, color="#334155", size=10)
        svg += cell(col("wid"), ry, cw("wid"), row_h, str(row["width"]), bg=bg, color="#334155", size=10)
        svg += cell(col("thk"), ry, cw("thk"), row_h, str(row["thickness"]), bg=bg, color="#334155", size=10)
        svg += cell(col("qty"), ry, cw("qty"), row_h, qty_display, bg=bg, color="#1e293b", bold=True, size=11)
        svg += cell(col("m2"), ry, cw("m2"), row_h, m2_display, bg=bg, color="#334155", size=10)
        svg += cell(col("price"), ry, cw("price"), row_h, price_display, bg=bg, color="#0f172a", bold=True, size=10)
        svg += cell(col("sum"), ry, cw("sum"), row_h, sum_display, bg=bg, color="#0f172a", bold=True, size=10)

    # Footer
    fy = title_h + header_h + total_rows * row_h
    svg += f'<rect x="0" y="{fy}" width="{width}" height="{footer_h}" fill="#f0fdf4" stroke="#94a3b8" stroke-width="1"/>'
    svg += f'<line x1="0" y1="{fy}" x2="{width}" y2="{fy}" stroke="#16a34a" stroke-width="2.5"/>'

    # Jami narx (panel + eshik)
    grand_total = total_sum + total_eshik_sum

    svg += f'<text x="20" y="{fy+24}" font-size="13" font-weight="800" fill="#15803d" font-family="Arial,sans-serif">📊 JAMI:</text>'
    svg += f'<text x="20" y="{fy+48}" font-size="11" fill="#334155" font-family="Arial,sans-serif"> Panellar: <tspan font-weight="700" fill="#0f172a">{total_qty} ta</tspan></text>'
    svg += f'<text x="200" y="{fy+48}" font-size="11" fill="#334155" font-family="Arial,sans-serif"> Maydon: <tspan font-weight="700" fill="#0f172a">{total_m2:.2f} m²</tspan></text>'
    
    # Eshik narxi alohida ko'rsatiladi
    if total_eshik_sum > 0:
        svg += f'<text x="420" y="{fy+48}" font-size="11" fill="#334155" font-family="Arial,sans-serif"> Eshik: <tspan font-weight="700" fill="#dc2626">${total_eshik_sum:,.0f}</tspan></text>'
        svg += f'<text x="580" y="{fy+48}" font-size="11" fill="#334155" font-family="Arial,sans-serif"> Jami narx: <tspan font-weight="700" fill="#dc2626">${grand_total:,.0f}</tspan></text>'
    else:
        svg += f'<text x="420" y="{fy+48}" font-size="11" fill="#334155" font-family="Arial,sans-serif"> Jami narx: <tspan font-weight="700" fill="#dc2626">${total_sum:,.0f}</tspan></text>'
    

    # Pastdagi rangli chiziq
    svg += f'<rect x="0" y="{fy+footer_h-6}" width="{width}" height="6" rx="0" fill="#16a34a"/>'
    svg += f'<rect x="0" y="{fy+footer_h-6}" width="{width/3:.0f}" height="6" fill="#3b82f6"/>'
    svg += f'<rect x="{width/3:.0f}" y="{fy+footer_h-6}" width="{width/3:.0f}" height="6" fill="#8b5cf6"/>'
    svg += f'<rect x="{width*2/3:.0f}" y="{fy+footer_h-6}" width="{width/3:.0f}" height="6" fill="#16a34a"/>'

    svg += '</svg>'
    return svg





from datetime import datetime
from datetime import datetime

def make_svg_split_multi(L, W, H, wall_mm, ceil_mm, floor_mm, pol_bor, proj, code,
                         chambers, eshiklar, bolish_turi, kameralar_soni):
    """
    Bo'lingan kameralar uchun MAKSIMAL ANIQ chizma
    - Katta masshtab (4-5 barobar)
    - Katta yozuvlar
    - Qalin chiziqlar
    - Aniq o'lchamlar
    """
    owmm = m_to_mm(L)
    ohmm = m_to_mm(W)
    ozmm = m_to_mm(H)
    
    # ===================================================================
    # 1-QISM: BURCHAK HOLATINI TEKSHIRISH
    # ===================================================================
    corners = {
        "chap_tepa": True,
        "chap_past": True,
        "ong_tepa": True,
        "ong_past": True
    }
    
    har_bir_kamera_eshik = st.session_state.get("har_bir_kamera_eshik", False)
    
    for idx, ch in enumerate(chambers):
        if eshiklar:
            if har_bir_kamera_eshik and idx < len(eshiklar):
                esh = eshiklar[idx] if idx < len(eshiklar) else None
            else:
                esh = eshiklar[0] if eshiklar else None
            
            if esh and esh.get("tur") != "Yo'q":
                eshik_joyi = esh.get("joyi", "Old")
                eshik_positsiya = esh.get("pozitsiya", "O'rta")
                
                if bolish_turi == "Eni bo'yicha":
                    if idx == 0:
                        if eshik_joyi == "Chap" and eshik_positsiya == "Chap tomon burchak o'rniga":
                            corners["chap_tepa"] = False
                    
                    if idx == len(chambers) - 1:
                        if eshik_joyi == "O'ng" and eshik_positsiya == "O'ng tomon burchak o'rniga":
                            corners["ong_tepa"] = False
                            corners["ong_past"] = False
    
    # ===================================================================
    # 2-QISM: MASSHTAB VA O'LCHAMLAR (MAKSIMAL KATTA)
    # ===================================================================
    # Eski: scale = min(230 / owmm, 170 / ohmm) -> 0.039
    # Yangi: 5 barobar katta -> 0.195
    
    # Maksimal masshtab - chizma ekranga sig'ishi uchun
    MAX_SCALE = 0.25  # Maksimal ruxsat
    MIN_SCALE = 0.08  # Minimal ruxsat
    
    scale = min(1000 / owmm, 800 / ohmm)  # 4-5 barobar katta
    
    # Chegaralarni qo'llaymiz
    if scale > MAX_SCALE:
        scale = MAX_SCALE
    if scale < MIN_SCALE:
        scale = MIN_SCALE
    
    # Chizma o'lchamlari
    dw = owmm * scale
    dh = ohmm * scale
    wt = max(8, wall_mm * scale)  # Devor qalinligi - aniq ko'rinishi uchun
    
    # ===================================================================
    # 3-QISM: SVG TUZILISHI (KATTA O'LCHAMLAR)
    # ===================================================================
    # SVG o'lchamlari - ekranga sig'adigan darajada katta
    SW = max(1600, int(dw + 600))
    SH = max(3200, int(dh * 4 + 1000))
    
    # Pozitsiyalar - markazlashtirilgan
    px = (SW - dw) / 2
    py = 180
    my = py + dh + 180      # Patalok rejasi
    by = my + dh + 160      # Pol rejasi
    tb = by + dh + 160      # Jadval
    
    # ===================================================================
    # 4-QISM: YOZUV O'LCHAMLARI (KATTA VA ANIQ)
    # ===================================================================
    FONT_TITLE = 24          # Bosh sarlavha
    FONT_SUB = 16            # Ost sarlavha
    FONT_HEADER = 14         # Bo'lim sarlavhalari
    FONT_LABEL = 13          # Kamera nomlari
    FONT_DIM = 12            # O'lcham yozuvlari
    FONT_SMALL = 10          # Kichik yozuvlar
    FONT_TINY = 9            # Eng kichik yozuvlar
    
    # ===================================================================
    # 5-QISM: DEVOR SEGMENTLARI
    # ===================================================================
    chap_burchak_tepa = corners["chap_tepa"]
    chap_burchak_past = corners["chap_past"]
    ong_burchak_bor = corners["ong_tepa"] and corners["ong_past"]
    
    tp_tepa = build_wall_segs(owmm, chap_burchak_tepa, ong_burchak_bor)
    tp_past = build_wall_segs(owmm, chap_burchak_past, ong_burchak_bor)
    rp = build_wall_segs(ohmm, chap_burchak_past, ong_burchak_bor)
    
    # ===================================================================
    # 6-QISM: BURCHAK MODULI CHIZIQLARI (QALIN VA ANIQ)
    # ===================================================================
    burchak_chiziqlari = ""
    
    if chap_burchak_tepa:
        burchak_chiziqlari += f'<line x1="{px}" y1="{py+4}" x2="{px+480*scale}" y2="{py+4}" stroke="#16A34A" stroke-width="4"/>'
        burchak_chiziqlari += f'<text x="{px+240*scale}" y="{py-8}" font-size="{FONT_TINY}" fill="#16A34A" text-anchor="middle" font-weight="600">480</text>'
    
    if chap_burchak_past:
        burchak_chiziqlari += f'<line x1="{px}" y1="{py+dh-4}" x2="{px+480*scale}" y2="{py+dh-4}" stroke="#16A34A" stroke-width="4"/>'
        burchak_chiziqlari += f'<text x="{px+240*scale}" y="{py+dh+18}" font-size="{FONT_TINY}" fill="#16A34A" text-anchor="middle" font-weight="600">480</text>'
    
    if ong_burchak_bor:
        burchak_chiziqlari += f'<line x1="{px+dw-480*scale}" y1="{py+4}" x2="{px+dw}" y2="{py+4}" stroke="#16A34A" stroke-width="4"/>'
        burchak_chiziqlari += f'<text x="{px+dw-240*scale}" y="{py-8}" font-size="{FONT_TINY}" fill="#16A34A" text-anchor="middle" font-weight="600">480</text>'
        burchak_chiziqlari += f'<line x1="{px+dw-480*scale}" y1="{py+dh-4}" x2="{px+dw}" y2="{py+dh-4}" stroke="#16A34A" stroke-width="4"/>'
        burchak_chiziqlari += f'<text x="{px+dw-240*scale}" y="{py+dh+18}" font-size="{FONT_TINY}" fill="#16A34A" text-anchor="middle" font-weight="600">480</text>'
    
    # ===================================================================
    # 7-QISM: PATALOK VA POL SEGMENTLARI
    # ===================================================================
    tpl_segs = build_segs(owmm)
    rpl_segs = build_segs(ohmm)
    tpl = [{"size": p, "type": "panel"} for p in tpl_segs]
    rpl = [{"size": p, "type": "panel"} for p in rpl_segs]
    
    t_slab_meta = seg_meta(tpl_segs, has_door=False, door_sz=0)
    r_slab_meta = seg_meta(rpl_segs, has_door=False, door_sz=0)
    
    iL = max(0, owmm - 2 * wall_mm)
    iW = max(0, ohmm - 2 * wall_mm)
    iH = max(0, ozmm - ceil_mm - (floor_mm if pol_bor else 0))

    # ===================================================================
    # 8-QISM: KAMERA LABELLARI VA ICHKI DEVORLAR (ANIQ VA KATTA)
    # ===================================================================
    internal_walls_svg = ""
    chamber_labels_svg = ""
    colors = ["#eff6ff", "#f0fdf4", "#fefce8", "#fef2f2", "#f5f3ff", "#fce7f3"]
    
    for idx, ch in enumerate(chambers):
        ch_L_mm = m_to_mm(ch["L"])
        ch_W_mm = m_to_mm(ch["W"])
        
        cx_rect = px + m_to_mm(ch["x"]) * scale
        cy_rect = py + m_to_mm(ch["y"]) * scale
        cw_rect = ch_L_mm * scale
        ch_rect = ch_W_mm * scale
        
        # Kamera maydoni - aniq chegara bilan
        chamber_labels_svg += f'''
        <rect x="{cx_rect}" y="{cy_rect}" width="{cw_rect}" height="{ch_rect}" 
              fill="{colors[idx % len(colors)]}" opacity="0.6" 
              stroke="#3b82f6" stroke-width="2" rx="4"/>
        <text x="{cx_rect + cw_rect/2}" y="{cy_rect + ch_rect/2 - 12}" 
              text-anchor="middle" font-size="{FONT_LABEL + 4}" 
              font-weight="800" fill="#1e293b">KAMERA {ch["id"]}</text>
        <text x="{cx_rect + cw_rect/2}" y="{cy_rect + ch_rect/2 + 18}" 
              text-anchor="middle" font-size="{FONT_DIM}" 
              fill="#475569" font-weight="600">{ch["L"]:.2f} x {ch["W"]:.2f} m</text>
        <text x="{cx_rect + cw_rect/2}" y="{cy_rect + ch_rect/2 + 38}" 
              text-anchor="middle" font-size="{FONT_TINY}" 
              fill="#94a3b8">S = {ch["L"] * ch["W"]:.2f} m²</text>
        '''
        
        # Ichki devorlar
        if idx > 0:
            if bolish_turi == "Uzunlik bo'yicha":
                x_sep = px + m_to_mm(ch["x"]) * scale
                inner_segs = build_segs(iW)
                curr_y = py + wall_mm * scale
                for seg_w in inner_segs:
                    seg_h_scale = seg_w * scale
                    internal_walls_svg += f'''
                    <rect x="{x_sep - wt/2}" y="{curr_y}" width="{wt}" height="{seg_h_scale}" 
                          fill="#e2e8f0" stroke="#475569" stroke-width="1.5" rx="1"/>
                    <line x1="{x_sep - wt/2}" y1="{curr_y + seg_h_scale}" 
                          x2="{x_sep + wt/2}" y2="{curr_y + seg_h_scale}" 
                          stroke="#64748b" stroke-width="1.5"/>
                    '''
                    if seg_w > 100:
                        internal_walls_svg += f'''
                        <text x="{x_sep + wt/2 + 8}" y="{curr_y + seg_h_scale/2}" 
                              text-anchor="middle" font-size="{FONT_SMALL}" 
                              fill="#ef4444" font-weight="700" 
                              transform="rotate(90, {x_sep + wt/2 + 8}, {curr_y + seg_h_scale/2})">{int(seg_w)}</text>
                        '''
                    curr_y += seg_h_scale
                    
            elif bolish_turi == "Eni bo'yicha":
                y_sep = py + m_to_mm(ch["y"]) * scale
                inner_segs = build_segs(iL)
                curr_x = px + wall_mm * scale
                for seg_w in inner_segs:
                    seg_w_scale = seg_w * scale
                    internal_walls_svg += f'''
                    <rect x="{curr_x}" y="{y_sep - wt/2}" width="{seg_w_scale}" height="{wt}" 
                          fill="#e2e8f0" stroke="#475569" stroke-width="1.5" rx="1"/>
                    <line x1="{curr_x + seg_w_scale}" y1="{y_sep - wt/2}" 
                          x2="{curr_x + seg_w_scale}" y2="{y_sep + wt/2}" 
                          stroke="#64748b" stroke-width="1.5"/>
                    '''
                    if seg_w > 100:
                        internal_walls_svg += f'''
                        <text x="{curr_x + seg_w_scale/2}" y="{y_sep - wt/2 - 8}" 
                              text-anchor="middle" font-size="{FONT_SMALL}" 
                              fill="#ef4444" font-weight="700">{int(seg_w)}</text>
                        '''
                    curr_x += seg_w_scale

    # ===================================================================
    # 9-QISM: ESHIKLAR (ANIQ VA KATTA)
    # ===================================================================
    doors_svg = ""
    doors_text_svg = ""
    
    has_door_top = False
    has_door_bottom = False
    has_door_left = False
    has_door_right = False
    first_door_sz = eshiklar[0]["width"] if eshiklar else 0

    for idx, d in enumerate(eshiklar):
        if d.get("tur") == "Yo'q":
            continue
            
        dwmm = d["width"]
        dhmm = d["height"]
        e_joyi = d.get("joyi", "Old")
        e_ochilish = d.get("ochilish", "Ichkariga")
        
        if har_bir_kamera_eshik and idx < len(chambers):
            e_pozitsiya = st.session_state.get(f"kamera_eshik_pozitsiya_{idx}", "O'rta")
            ch = chambers[idx]
            ch_x = m_to_mm(ch["x"])
            ch_y = m_to_mm(ch["y"])
            ch_L = m_to_mm(ch["L"])
            ch_W = m_to_mm(ch["W"])
        else:
            e_pozitsiya = st.session_state.get("eshik_pozitsiya", "O'rta")
            ch_x, ch_y, ch_L, ch_W = 0, 0, owmm, ohmm
            
        if e_joyi in ["Chap", "O'ng"]:
            doff_local = door_off(build_wall_segs(ch_W), e_pozitsiya, "vertical", dwmm)
            absolute_offset = ch_y + doff_local
        else:
            doff_local = door_off(build_wall_segs(ch_L), e_pozitsiya, "horizontal", dwmm)
            absolute_offset = ch_x + doff_local

        # Eshik chizish - qalin va aniq
        door_color = "#059669"
        door_width_line = 3
        
        if e_joyi == "Chap":
            doors_svg += arc_left(px, py, scale, absolute_offset, dhmm, dwmm, e_ochilish)
            doors_text_svg += svgt(px - 36, py + absolute_offset * scale + dwmm * scale / 2, 
                                  f"🚪 {dwmm}x{dhmm}", size=FONT_SMALL+2, rotate=90, color="#059669", weight="700")
            has_door_left = True
        elif e_joyi == "O'ng":
            doors_svg += arc_right(px, py, dw, scale, absolute_offset, dhmm, dwmm, e_ochilish)
            doors_text_svg += svgt(px + dw + 36, py + absolute_offset * scale + dwmm * scale / 2, 
                                  f"🚪 {dwmm}x{dhmm}", size=FONT_SMALL+2, rotate=90, color="#059669", weight="700")
            has_door_right = True
        elif e_joyi == "Old":
            doors_svg += arc_bottom(px, py, dh, scale, absolute_offset, dwmm, e_ochilish)
            doors_text_svg += svgt(px + absolute_offset * scale + dwmm * scale / 2, py + dh + 22, 
                                  f"🚪 {dwmm}x{dhmm}", size=FONT_SMALL+2, color="#059669", weight="700")
            has_door_bottom = True
        elif e_joyi == "Orqa":
            doors_svg += arc_top(px, py, scale, absolute_offset, dwmm, e_ochilish)
            doors_text_svg += svgt(px + absolute_offset * scale + dwmm * scale / 2, py - 10, 
                                  f"🚪 {dwmm}x{dhmm}", size=FONT_SMALL+2, color="#059669", weight="700")
            has_door_top = True

    tm_tepa = seg_meta(tp_tepa, has_door=(has_door_top or has_door_bottom), door_sz=first_door_sz)
    tm_past = seg_meta(tp_past, has_door=(has_door_top or has_door_bottom), door_sz=first_door_sz)
    rm = seg_meta(rp, has_door=(has_door_left or has_door_right), door_sz=first_door_sz)

    # ===================================================================
    # 10-QISM: KOMPAS (KATTA VA ANIQ)
    # ===================================================================
    cx_, cy_ = SW - 70, py + 40
    comp_svg = f'''
    <circle cx="{cx_}" cy="{cy_}" r="22" fill="white" stroke="#94a3b8" stroke-width="2"/>
    <line x1="{cx_}" y1="{cy_-18}" x2="{cx_}" y2="{cy_+18}" stroke="#94a3b8" stroke-width="2"/>
    <line x1="{cx_-18}" y1="{cy_}" x2="{cx_+18}" y2="{cy_}" stroke="#94a3b8" stroke-width="2"/>
    <polygon points="{cx_},{cy_-18} {cx_-6},{cy_} {cx_+6},{cy_}" fill="#ef4444"/>
    <polygon points="{cx_},{cy_+18} {cx_-6},{cy_} {cx_+6},{cy_}" fill="#94a3b8"/>
    {svgt(cx_, cy_-28, "N", size=FONT_LABEL+2, weight="800", color="#1e293b")}
    {svgt(cx_, cy_+36, "S", size=FONT_SMALL, weight="600", color="#64748b")}
    {svgt(cx_-32, cy_, "W", size=FONT_SMALL, weight="600", color="#64748b")}
    {svgt(cx_+32, cy_, "E", size=FONT_SMALL, weight="600", color="#64748b")}
    '''
    
    pol_lbl = f"Qalinligi: {floor_mm if pol_bor else 0} mm  ({'Bor' if pol_bor else 'Yoq'})"
    
    chamber_info = f" | {kameralar_soni} ta kamera ({bolish_turi})"
    for ch_info in chambers:
        chamber_info += f" | K{ch_info['id']}:{ch_info['L']:.1f}x{ch_info['W']:.1f}m"

    # ===================================================================
    # 11-QISM: PANEL JADVALI
    # ===================================================================
    # ========== PANEL JADVALI ==========
    panel_rows = build_panel_table_for_split(
        owmm, ohmm, ozmm, wall_mm, ceil_mm, floor_mm, pol_bor,
        chambers, eshiklar
    )

    # Narxlarni olish (Sidebardan)
    devor_narx_sidebar = st.session_state.get("devor_narx", 35.0)
    patalok_narx_sidebar = st.session_state.get("patalok_narx", 45.0)
    pol_narx_sidebar = st.session_state.get("pol_narx", 40.0)

    table_svg = make_ecofrom_table_svg(
    panel_rows,  # <-- TO'G'RI
    x=30, 
    y=by + dh + 110, 
    width=730,
    devor_narx=devor_narx,
    patalok_narx=patalok_narx,
    pol_narx=pol_narx,
    eshik_narx=eshik_narx
)
    

    # ===================================================================
    # 12-QISM: YAKUNIY SVG (TO'LIQ VA ANIQ)
    # ===================================================================
    return f'''<svg width="100%" viewBox="0 0 {SW} {SH}" xmlns="http://www.w3.org/2000/svg" style="background:#ffffff;">

<!-- ========== RAMKA ========== -->
<defs>
    <filter id="shadow" x="-2%" y="-2%" width="104%" height="104%">
        <feDropShadow dx="2" dy="2" stdDeviation="3" flood-opacity="0.08"/>
    </filter>
</defs>

<rect x="20" y="20" width="{SW-40}" height="{SH-40}" fill="white" stroke="#1e293b" stroke-width="2.5" rx="10" filter="url(#shadow)"/>

<!-- ========== SARLAVHA ========== -->
{svgt(SW/2, 70, "TEXNIK CHIZMA (BO'LINGAN MULTI-KAMERA)", size=FONT_TITLE+6, weight="900", color="#0f172a")}
{svgt(SW/2, 100, (proj or "").upper() + chamber_info, size=FONT_SUB+2, color="#475569")}
{svgt(SW-50, 70, code, size=FONT_SUB+2, anchor="end", color="#64748b")}
<line x1="40" y1="115" x2="{SW-40}" y2="115" stroke="#e2e8f0" stroke-width="1.5"/>

<!-- ========== KOMPAS ========== -->
{comp_svg}

<!-- ========== 1. DEVOR REJASI ========== -->
<rect x="{px-20}" y="{py-65}" width="{dw+40}" height="{dh+85}" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1" rx="6"/>
{svgt(px+dw/2, py-48, "1. DEVOR REJASI  (TOP VIEW - MULTI)", size=FONT_HEADER+2, weight="700", color="#334155")}

{room_plan(px, py, dw, dh, wt)}
{chamber_labels_svg}
{internal_walls_svg}
{doors_svg}
{doors_text_svg}

<!-- Devor o'lchamlari -->
{chain_top(px, py, tm_tepa, scale, fs=FONT_DIM+1, color="#2563eb")}
{chain_top(px, py+dh, tm_past, scale, fs=FONT_DIM+1, color="#2563eb")}
{chain_right(px+dw+16, py, rm, scale, fs=FONT_DIM+1, color="#2563eb")}

{ticks_h(px, py, tm_tepa, scale)}
{ticks_h(px, py+dh, tm_past, scale)}
{ticks_v(px, py, rm, scale)}
{ticks_v(px+dw, py, rm, scale)}

<!-- Tashqi o'lcham -->
{svgt(px+dw/2, py+dh+38, f"L = {owmm} mm ({L:.2f} m)", size=FONT_DIM+1, color="#1e293b", weight="600")}
{svgt(px-45, py+dh/2, f"W = {ohmm} mm ({W:.2f} m)", size=FONT_DIM+1, color="#1e293b", weight="600", rotate=90)}
{svgt(px+dw/2, py+dh+55, f"Devor qalinligi: {wall_mm} mm (ichki to'siqlar tekis panellardan)", size=FONT_SMALL, color="#475569")}

<!-- ========== BURCHAK MODULLARI ========== -->
{burchak_chiziqlari}

<!-- ========== 2. PATALOK PANELI ========== -->
<rect x="{px-20}" y="{my-65}" width="{dw+40}" height="{dh+85}" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1" rx="6"/>
{svgt(px+dw/2, my-48, "2. PATALOK PANELI REJASI", size=FONT_HEADER+2, weight="700", color="#334155")}

{slab_svg(px, my, dw, dh, tpl, rpl, scale, "", ls=FONT_LABEL)}
{chain_top(px, my, t_slab_meta, scale, fs=FONT_DIM+1, color="#7c3aed")}
{chain_right(px+dw+16, my, r_slab_meta, scale, fs=FONT_DIM+1, color="#7c3aed")}
{ticks_h(px, my, t_slab_meta, scale)}
{ticks_h(px, my+dh, t_slab_meta, scale)}
{ticks_v(px, my, r_slab_meta, scale)}
{ticks_v(px+dw, my, r_slab_meta, scale)}
{svgt(px+dw/2, my+dh+38, f"Patalok qalinligi: {ceil_mm} mm", size=FONT_DIM+1, color="#1e293b", weight="600")}

<!-- ========== 3. POL PANELI ========== -->
<rect x="{px-20}" y="{by-65}" width="{dw+40}" height="{dh+85}" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1" rx="6"/>
{svgt(px+dw/2, by-48, "3. POL PANELI REJASI", size=FONT_HEADER+2, weight="700", color="#334155")}

{slab_svg(px, by, dw, dh, tpl, rpl, scale, "", ls=FONT_LABEL)}
{chain_top(px, by, t_slab_meta, scale, fs=FONT_DIM+1, color="#059669")}
{chain_right(px+dw+16, by, r_slab_meta, scale, fs=FONT_DIM+1, color="#059669")}
{ticks_h(px, by, t_slab_meta, scale)}
{ticks_h(px, by+dh, t_slab_meta, scale)}
{ticks_v(px, by, r_slab_meta, scale)}
{ticks_v(px+dw, by, r_slab_meta, scale)}
{svgt(px+dw/2, by+dh+38, pol_lbl, size=FONT_DIM+1, color="#1e293b", weight="600")}

<!-- ========== MODUL TUSHUNTIRISHLARI ========== -->
<rect x="40" y="{my-30}" width="20" height="20" fill="#16A34A" rx="4"/>
{svgt(72, my-15, "480 mm burchak moduli", size=FONT_SMALL+1, anchor="start", color="#475569")}
<rect x="40" y="{my}" width="20" height="20" fill="none" stroke="#94a3b8" stroke-width="2" stroke-dasharray="4,3" rx="4"/>
{svgt(72, my+15, "960 mm asosiy modul", size=FONT_SMALL+1, anchor="start", color="#475569")}
<rect x="40" y="{my+30}" width="20" height="20" fill="#dbeafe" stroke="#3b82f6" stroke-width="1.5" rx="4"/>
{svgt(72, my+45, "Kamera maydoni", size=FONT_SMALL+1, anchor="start", color="#475569")}
<rect x="300" y="{my-30}" width="20" height="20" fill="#fef3c7" stroke="#d97706" stroke-width="1.5" rx="4"/>
{svgt(332, my-15, "Eshik ochilish yo'nalishi", size=FONT_SMALL+1, anchor="start", color="#475569")}
<line x1="300" y1="{my+10}" x2="320" y2="{my+10}" stroke="#059669" stroke-width="3"/>
{svgt(332, my+15, "Eshik panellari", size=FONT_SMALL+1, anchor="start", color="#475569")}

<!-- ========== JADVAL ========== -->
{table_svg}

<!-- ========== SANAVIY BLOK ========== -->
{title_block(30, tb, 600, 130, proj or "-", code, owmm, ohmm, ozmm, wall_mm, ceil_mm, floor_mm if pol_bor else 0, datetime.now().strftime("%d.%m.%Y"))}

</svg>'''
def make_svg(L, W, H, wall_mm, ceil_mm, floor_mm, pol_bor, proj, code, ej, eshik, ep, eo,
             devor_narx=0, patalok_narx=0, pol_narx=0, eshik_narx=0):
    """
    Yagona kamera uchun chizma - 2-6 ta kameralarni qo'llab-quvvatlaydi
    Narxlar avtomatik ravishda Panel spetsifikatsiyasi jadvaliga qo'shiladi
    """
    owmm = m_to_mm(L)
    ohmm = m_to_mm(W)
    ozmm = m_to_mm(H)
    
    # ========== ESHIK MA'LUMOTLARI ==========
    eshik_turi = eshik
    if eshik_turi == "Custom":
        eshik_w = st.session_state.get("eshik_custom_width", 900)
        eshik_h = st.session_state.get("eshik_custom_height", 1900)
        eshik_soni = st.session_state.get("eshik_soni", 1)
    else:
        eshik_w, eshik_h = door_dim_custom(eshik_turi)
        eshik_soni = 1
    
    # ========== KAMERA BO'LISH ==========
    kamera_bolish_turi = st.session_state.get("kamera_bolish_turi", "Yo'q")
    kameralar_soni = st.session_state.get("kameralar_soni", 2)
    
    # ========== KAMERALARNI HISOBLASH ==========
    if kamera_bolish_turi == "Uzunlik bo'yicha":
        each_L = L / kameralar_soni
        chambers = []
        for i in range(kameralar_soni):
            chambers.append({
                "id": i + 1,
                "L": each_L,
                "W": W,
                "H": H,
                "x": i * each_L,
                "y": 0,
                "w": each_L,
                "h": W
            })
        eshiklar = []
        if st.session_state.get("har_bir_kamera_eshik", False):
            for i in range(kameralar_soni):
                eshik_joyi = st.session_state.get(f"kamera_eshik_joyi_{i}", "Old")
                eshik_pozitsiya = st.session_state.get(f"kamera_eshik_pozitsiya_{i}", "O'rta")
                if eshik_turi != "Yo'q":
                    eshiklar.append({
                        "tur": eshik_turi,
                        "width": eshik_w,
                        "height": eshik_h,
                        "soni": eshik_soni,
                        "joyi": eshik_joyi,
                        "pozitsiya": eshik_pozitsiya,
                        "ochilish": "Ichkariga"
                    })
        else:
            if eshik_turi != "Yo'q":
                eshiklar.append({
                    "tur": eshik_turi,
                    "width": eshik_w,
                    "height": eshik_h,
                    "soni": eshik_soni,
                    "joyi": ej,
                    "pozitsiya": ep,
                    "ochilish": eo
                })
    
    elif kamera_bolish_turi == "Eni bo'yicha":
        each_W = W / kameralar_soni
        chambers = []
        for i in range(kameralar_soni):
            chambers.append({
                "id": i + 1,
                "L": L,
                "W": each_W,
                "H": H,
                "x": 0,
                "y": i * each_W,
                "w": L,
                "h": each_W
            })
        eshiklar = []
        if st.session_state.get("har_bir_kamera_eshik", False):
            for i in range(kameralar_soni):
                eshik_joyi = st.session_state.get(f"kamera_eshik_joyi_{i}", "Old")
                eshik_pozitsiya = st.session_state.get(f"kamera_eshik_pozitsiya_{i}", "O'rta")
                if eshik_turi != "Yo'q":
                    eshiklar.append({
                        "tur": eshik_turi,
                        "width": eshik_w,
                        "height": eshik_h,
                        "soni": eshik_soni,
                        "joyi": eshik_joyi,
                        "pozitsiya": eshik_pozitsiya,
                        "ochilish": "Ichkariga"
                    })
        else:
            if eshik_turi != "Yo'q":
                eshiklar.append({
                    "tur": eshik_turi,
                    "width": eshik_w,
                    "height": eshik_h,
                    "soni": eshik_soni,
                    "joyi": ej,
                    "pozitsiya": ep,
                    "ochilish": eo
                })
    
    else:
        chambers = [{"L": L, "W": W, "H": H, "id": 1, "x": 0, "y": 0, "w": L, "h": W}]
        eshiklar = []
        if eshik_turi != "Yo'q":
            eshiklar.append({
                "tur": eshik_turi,
                "width": eshik_w,
                "height": eshik_h,
                "soni": eshik_soni,
                "joyi": ej,
                "pozitsiya": ep,
                "ochilish": eo
            })
    
    # ========== AGAR BO'LINGAN BO'LSA ==========
    if kamera_bolish_turi != "Yo'q" and kameralar_soni > 1:
        return make_svg_split_multi(
            L, W, H, wall_mm, ceil_mm, floor_mm, pol_bor,
            proj, code, chambers, eshiklar,
            kamera_bolish_turi, kameralar_soni
        )
    
    # ========== YAGONA KAMERA ==========
    ch = chambers[0]
    Lc = ch["L"]
    Wc = ch["W"]
    Hc = ch["H"]
    
    owmm_c = m_to_mm(Lc)
    ohmm_c = m_to_mm(Wc)
    ozmm_c = m_to_mm(Hc)
    
    # ========== BURCHAK HOLATI ==========
    corners = {
        "chap_tepa": True,
        "chap_past": True,
        "ong_tepa": True,
        "ong_past": True
    }
    
    if eshik_turi != "Yo'q":
        if ej == "Chap":
            if ep == "Chap tomon burchak o'rniga":
                corners["chap_tepa"] = False
                corners["chap_past"] = False
        elif ej == "O'ng":
            if ep == "O'ng tomon burchak o'rniga":
                corners["ong_tepa"] = False
                corners["ong_past"] = False
        elif ej == "Old":
            if ep == "Chap tomon burchak o'rniga":
                corners["chap_past"] = False
            elif ep == "O'ng tomon burchak o'rniga":
                corners["ong_past"] = False
        elif ej == "Orqa":
            if ep == "Chap tomon burchak o'rniga":
                corners["chap_tepa"] = False
            elif ep == "O'ng tomon burchak o'rniga":
                corners["ong_tepa"] = False
    
    # Devor panellari
    chap_burchak_bor = corners["chap_tepa"] and corners["chap_past"]
    ong_burchak_bor = corners["ong_tepa"] and corners["ong_past"]
    
    tp = build_wall_segs(owmm_c, chap_burchak_bor, ong_burchak_bor)
    rp = build_wall_segs(ohmm_c, chap_burchak_bor, ong_burchak_bor)
    
    # Eshik
    has_door = (eshik_turi != "Yo'q")
    dwmm = eshik_w if has_door else 0
    dhmm = eshik_h if has_door else 0
    
    tm = seg_meta(tp, has_door=(has_door and ej in ["Old", "Orqa"]), door_sz=dwmm)
    rm = seg_meta(rp, has_door=(has_door and ej in ["Chap", "O'ng"]), door_sz=dwmm)
    
    # ========== PATALOK VA POL ==========
    tpl_segs = build_segs(owmm_c)
    rpl_segs = build_segs(ohmm_c)
    
    t_slab_meta = seg_meta(tpl_segs, has_door=False, door_sz=0)
    r_slab_meta = seg_meta(rpl_segs, has_door=False, door_sz=0)
    
    tpl = [{"size": p, "type": "panel"} for p in tpl_segs]
    rpl = [{"size": p, "type": "panel"} for p in rpl_segs]
    
    # ========== MASSHTAB ==========
    scale = min(250 / max(owmm_c, 1), 185 / max(ohmm_c, 1))
    dw = owmm_c * scale
    dh = ohmm_c * scale
    wt = max(5, wall_mm * scale)
    SW, SH = 794, 1420
    px = 390 - dw / 2
    py = 115
    my = py + dh + 92
    by = my + dh + 82
    tb = min(by + dh + 55, 978)
    
    # Ichki o'lchamlar
    iL = max(0, owmm_c - 2 * wall_mm)
    iW = max(0, ohmm_c - 2 * wall_mm)
    iH = max(0, ozmm_c - ceil_mm - (floor_mm if pol_bor else 0))
    
    # ========== PANEL JADVALI (NARXLAR BILAN) ==========
    panel_rows = build_panel_table_for_split(
        owmm, ohmm, ozmm, wall_mm, ceil_mm, floor_mm, pol_bor,
        chambers, eshiklar
    )
    
    fixed_panel_rows = []
    for row in panel_rows:
        if "Potolok/Pol paneli" in row.get("Nomi", ""):
            row["Soni"] = row["Soni"] * (len(tpl_segs) // 2 if len(tpl_segs) > 2 else 2)
            row["Maydon m²"] = (row["Uzunlik"] / 1000) * (row["Eni"] / 1000) * row["Soni"]
        fixed_panel_rows.append(row)

    # ===== NARXLARNI JADVALGA UZATISH =====
    table_svg = make_ecofrom_table_svg(
    panel_rows,  # <-- TO'G'RI
    x=30, 
    y=by + dh + 110, 
    width=730,
    devor_narx=devor_narx,
    patalok_narx=patalok_narx,
    pol_narx=pol_narx,
    eshik_narx=eshik_narx
)
    
    # ========== ESHIK CHIZISH ==========
    ds = ""
    dn = ""
    if has_door:
        if ej == "Chap":
            doff = door_off(rp, ep, "vertical", dwmm)
            ds = arc_left(px, py, scale, doff, dhmm, dwmm, eo)
            dn = svgt(px - 28, py + doff * scale + dwmm * scale / 2, f"{dwmm}x{dhmm}", size=8, rotate=90, color="#333")
        elif ej == "O'ng":
            doff = door_off(rp, ep, "vertical", dwmm)
            ds = arc_right(px, py, dw, scale, doff, dhmm, dwmm, eo)
            dn = svgt(px + dw + 28, py + doff * scale + dwmm * scale / 2, f"{dwmm}x{dhmm}", size=8, rotate=90, color="#333")
        elif ej == "Old":
            doff = door_off(tp, ep, "horizontal", dwmm)
            ds = arc_bottom(px, py, dh, scale, doff, dwmm, eo)
            dn = svgt(px + doff * scale + dwmm * scale / 2, py + dh + 14, f"{dwmm}x{dhmm}", size=8, color="#333")
        elif ej == "Orqa":
            doff = door_off(tp, ep, "horizontal", dwmm)
            ds = arc_top(px, py, scale, doff, dwmm, eo)
            dn = svgt(px + doff * scale + dwmm * scale / 2, py - 6, f"{dwmm}x{dhmm}", size=8, color="#333")
    
    # ========== BURCHAK CHIZIQLARI ==========
    burchak_chiziqlari = ""
    if corners["chap_tepa"]:
        burchak_chiziqlari += f'<line x1="{px}" y1="{py + 2}" x2="{px + 480 * scale}" y2="{py + 2}" stroke="#16A34A" stroke-width="2"/>'
    if corners["chap_past"]:
        burchak_chiziqlari += f'<line x1="{px}" y1="{py + dh - 2}" x2="{px + 480 * scale}" y2="{py + dh - 2}" stroke="#16A34A" stroke-width="2"/>'
    if corners["ong_tepa"]:
        burchak_chiziqlari += f'<line x1="{px + dw - 480 * scale}" y1="{py + 2}" x2="{px + dw}" y2="{py + 2}" stroke="#16A34A" stroke-width="2"/>'
    if corners["ong_past"]:
        burchak_chiziqlari += f'<line x1="{px + dw - 480 * scale}" y1="{py + dh - 2}" x2="{px + dw}" y2="{py + dh - 2}" stroke="#16A34A" stroke-width="2"/>'
    
    # ========== KOMPAS ==========
    cx_, cy_ = SW - 46, py + 18
    comp_svg = (f'<circle cx="{cx_}" cy="{cy_}" r="13" fill="none" stroke="#888" stroke-width="1"/>'
                f'<line x1="{cx_}" y1="{cy_ - 11}" x2="{cx_}" y2="{cy_ + 11}" stroke="#888" stroke-width="1"/>'
                f'<line x1="{cx_ - 11}" y1="{cy_}" x2="{cx_ + 11}" y2="{cy_}" stroke="#888" stroke-width="1"/>'
                f'<polygon points="{cx_},{cy_ - 11} {cx_ - 4},{cy_} {cx_ + 4},{cy_}" fill="#333"/>'
                + svgt(cx_, cy_ - 16, "N", size=8, weight="700", color="#333"))
    
    pol_lbl = f"Qalinligi: {floor_mm if pol_bor else 0} mm  ({'Bor' if pol_bor else 'Yoq'})"
    
    chamber_info = ""
    if len(chambers) > 1:
        chamber_info = f" | {len(chambers)} ta kamera"
        for i, ch_info in enumerate(chambers):
            chamber_info += f" | K{i+1}: {ch_info['L']:.1f}x{ch_info['W']:.1f}m"
    
    # ========== SVG ==========
    return f'''<svg width="100%" viewBox="0 0 {SW} {SH + 120}" xmlns="http://www.w3.org/2000/svg">
<rect x="20" y="20" width="{SW - 40}" height="{SH + 80}" fill="white" stroke="#111" stroke-width="1.2"/>
{svgt(390, 56, "TEXNIK CHIZMA", size=14, weight="700")}
{svgt(390, 74, (proj or "").upper() + chamber_info, size=11)}
{svgt(SW - 28, 56, code, size=10, anchor="end", color="#888")}
{comp_svg}

{svgt(px + dw / 2, py - 34, "DEVOR REJASI  (TOP VIEW)", size=10, weight="700", color="#555")}
{room_plan(px, py, dw, dh, wt)}
{ds}{dn}

{chain_top(px, py, tm, scale)}
{chain_bottom(px, py + dh, tm, scale)}   # 🔽 PASTKI QO'SHILDI
{chain_left(px, py, rm, scale)}
{chain_right(px+dw, py, rm, scale)}

{ticks_h(px, py, tm, scale)}
{ticks_h(px, py+dh, tm, scale)}
{ticks_v(px, py, rm, scale)}
{ticks_v(px+dw, py, rm, scale)}

{svgt(px + dw / 2, py + dh / 2 - 6, f"Tashqi: {owmm_c}x{ohmm_c}x{ozmm_c} mm", size=8, color="#999")}
{svgt(px + dw / 2, py + dh / 2 + 8, f"Ichki:  {iL}x{iW}x{iH} mm", size=8, color="#999")}

{burchak_chiziqlari}

{slab_svg(px, my, dw, dh, tpl, rpl, scale, "PATALOK PANELI")}
{chain_top(px, my, t_slab_meta, scale)}
{chain_bottom(px, my+dh, t_slab_meta, scale)}
{chain_left(px, my, r_slab_meta, scale)}
{chain_right(px+dw, my, r_slab_meta, scale)}
{ticks_h(px, my, t_slab_meta, scale)}
{ticks_h(px, my+dh, t_slab_meta, scale)}
{ticks_v(px, my, r_slab_meta, scale)}
{ticks_v(px+dw, my, r_slab_meta, scale)}

{slab_svg(px, by, dw, dh, tpl, rpl, scale, "POL PANELI")}
{chain_top(px, by, t_slab_meta, scale)}
{chain_bottom(px, by+dh, t_slab_meta, scale)}
{chain_left(px, by, r_slab_meta, scale)}
{chain_right(px+dw, by, r_slab_meta, scale)}
{ticks_h(px, by, t_slab_meta, scale)}
{ticks_h(px, by+dh, t_slab_meta, scale)}
{ticks_v(px, by, r_slab_meta, scale)}
{ticks_v(px+dw, by, r_slab_meta, scale)}

<rect x="30" y="{my}" width="10" height="10" fill="#16A34A"/>
{svgt(46, my + 9, "480 mm burchak moduli", size=8, anchor="start", color="#666")}
<rect x="30" y="{my + 15}" width="10" height="10" fill="none" stroke="#8898A8" stroke-width="1" stroke-dasharray="3,2"/>
{svgt(46, my + 24, "960 mm asosiy modul", size=8, anchor="start", color="#666")}

{table_svg}

{title_block(115, tb, 560, 110, proj or "-", code, owmm_c, ohmm_c, ozmm_c, wall_mm, ceil_mm, floor_mm if pol_bor else 0, datetime.now().strftime("%d.%m.%Y"))}
</svg>'''

def make_svg_multi(L, W, heights_list, n_chambers, corridor_w, corridor_pos, wall_mm,
                   door_w_multi, door_h_multi, proj, code, has_corridor,
                   panel_width_m=1.16, ceil_mm=None, floor_mm=None, pol_bor=True):
    if ceil_mm is None: ceil_mm = wall_mm
    if floor_mm is None: floor_mm = wall_mm

    owmm = int(L * 1000); ohmm = int(W * 1000)
    maxHmm = int(max(heights_list) * 1000) if heights_list else 3000
    dwmm = int(door_w_multi * 1000); dhmm = int(door_h_multi * 1000)

    try:
        tp = build_segs(owmm); rp = build_segs(ohmm)
        tpl = [{"size": p, "type": "panel"} for p in tp]
        rpl = [{"size": p, "type": "panel"} for p in rp]
        wl = panel_count(L, panel_width_m); ww = panel_count(W, panel_width_m)
        dp = (wl["total_panels"] * 2) + (ww["total_panels"] * 2)
    except: tpl, rpl = [], []; dp = 0

    pw = panel_width_m
    pp = math.ceil(W / pw)
    flp = math.ceil(W / pw) if pol_bor else 0
    all_p = dp + pp + flp

    SW, SH = 2400, 3200
    max_dim = max(owmm, ohmm)
    if max_dim > 25000: scale = 800 / max_dim
    elif max_dim > 15000: scale = 1200 / max_dim
    elif max_dim > 8000:  scale = 1600 / max_dim
    else: scale = min(1900 / max(owmm, 1), 1200 / max(ohmm, 1))

    dw = owmm * scale; dh = ohmm * scale; wt = max(12, wall_mm * scale)
    px = (SW / 2) - (dw / 2); py = 250; my = py + dh + 300; by = my + dh + 250
    CHAIN_FS = max(10, int(min(dw, dh) / 55))

    n_per_side = n_chambers; n_right = 0
    if has_corridor and corridor_pos == "markaz" and corridor_w > 0:
        n_per_side = int(math.ceil(n_chambers / 2))
        n_right = n_chambers - n_per_side

    def svgt_local(x, y, text, size=16, weight="normal", color="#000", anchor="middle"):
        return (f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" '
                f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{text}</text>')

    def dim_h_local(x1, x2, y, text, color="#0f172a", size=16, ext=10):
        return (f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="2"/>'
                f'<line x1="{x1}" y1="{y-ext}" x2="{x1}" y2="{y+ext}" stroke="{color}" stroke-width="2"/>'
                f'<line x1="{x2}" y1="{y-ext}" x2="{x2}" y2="{y+ext}" stroke="{color}" stroke-width="2"/>'
                + svgt_local((x1+x2)/2, y-15, text, size=size, weight="600", color=color))

    def dim_v_local(x, y1, y2, text, color="#0f172a", size=16, ext=10):
        cy_m = (y1+y2)/2
        return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{color}" stroke-width="2"/>'
                f'<line x1="{x-ext}" y1="{y1}" x2="{x+ext}" y2="{y1}" stroke="{color}" stroke-width="2"/>'
                f'<line x1="{x-ext}" y1="{y2}" x2="{x+ext}" y2="{y2}" stroke="{color}" stroke-width="2"/>'
                f'<text x="{x+25}" y="{cy_m}" font-family="Arial" font-size="{size}" font-weight="600" '
                f'fill="{color}" transform="rotate(90, {x+25}, {cy_m})" text-anchor="middle">{text}</text>')

    svg = f'''<svg width="100%" viewBox="0 0 {SW} {SH}" xmlns="http://www.w3.org/2000/svg" style="background-color:#fcfcfc;">
<rect x="40" y="40" width="{SW-80}" height="{SH-80}" fill="white" stroke="#1e293b" stroke-width="3" rx="15"/>
{svgt_local(SW/2, 120, "MULTI-KAMERA KOMPLEKS TEXNIK CHIZMASI", size=42, weight="800", color="#0f172a")}
{svgt_local(SW/2, 175, f"LOYIHA: {(proj or '').upper()} | KOD: {code}", size=24, color="#475569")}
{svgt_local(SW-100, 120, datetime.now().strftime("%d.%m.%Y"), size=20, anchor="end", color="#94a3b8")}
<circle cx="{SW-120}" cy="{py+30}" r="24" fill="none" stroke="#94a3b8" stroke-width="2"/>
<line x1="{SW-120}" y1="{py+10}" x2="{SW-120}" y2="{py+50}" stroke="#94a3b8" stroke-width="2"/>
<polygon points="{SW-120},{py+10} {SW-112},{py+30} {SW-128},{py+30}" fill="#0f172a"/>
{svgt_local(SW-120, py+2, "N", size=16, weight="700", color="#0f172a")}
<rect x="{px}" y="{py}" width="{dw}" height="{dh}" fill="none" stroke="#334155" stroke-width="{wt}" rx="2"/>
<rect x="{px + wt}" y="{py + wt}" width="{dw - 2*wt}" height="{dh - 2*wt}" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="10,6"/>'''

    if has_corridor and corridor_w > 0:
        cor_w_s = corridor_w * scale
        if corridor_pos == "markaz":
            cor_x = px + dw/2 - cor_w_s/2; cam_w_s = (dw - cor_w_s) / 2
            cham_L_real = (L - corridor_w) / 2
            svg += (f'<rect x="{cor_x}" y="{py}" width="{cor_w_s}" height="{dh}" fill="#fef3c7" opacity="0.7"/>'
                    f'<line x1="{cor_x}" y1="{py}" x2="{cor_x}" y2="{py+dh}" stroke="#d97706" stroke-width="3" stroke-dasharray="12,8"/>'
                    f'<line x1="{cor_x+cor_w_s}" y1="{py}" x2="{cor_x+cor_w_s}" y2="{py+dh}" stroke="#d97706" stroke-width="3" stroke-dasharray="12,8"/>'
                    f'<rect x="{cor_x+cor_w_s/2-90}" y="{py+dh/2-35}" width="180" height="70" fill="white" opacity="0.95" rx="8" stroke="#d97706" stroke-width="1.5"/>'
                    + svgt_local(cor_x+cor_w_s/2, py+dh/2-5, "YO'LAK", size=24, weight="700", color="#92400e")
                    + svgt_local(cor_x+cor_w_s/2, py+dh/2+22, f"{corridor_w:.2f} m", size=18, color="#b45309"))
            svg += dim_h_local(cor_x, cor_x+cor_w_s, py-40, f"{corridor_w}m", color="#d97706", size=22, ext=8)
            if n_per_side > 0:
                cham_W_left = W / n_per_side
                for i in range(n_per_side):
                    cy2 = py + i * (dh / n_per_side); ch = dh / n_per_side
                    svg += (f'<rect x="{px}" y="{cy2}" width="{cam_w_s}" height="{ch}" fill="#eff6ff" stroke="#3b82f6" stroke-width="2.5" rx="4"/>'
                            + svgt_local(px+cam_w_s/2, cy2+ch/2-8, f"KAMERA {i+1}", size=22, weight="700", color="#1e40af")
                            + svgt_local(px+cam_w_s/2, cy2+ch/2+20, f"{cham_L_real:.1f} x {cham_W_left:.1f} m", size=16, color="#3b82f6"))
                    if i < n_per_side-1: svg += f'<line x1="{px}" y1="{cy2+ch}" x2="{px+cam_w_s}" y2="{cy2+ch}" stroke="#93c5fd" stroke-width="2" stroke-dasharray="10,5"/>'
            if n_right > 0:
                cham_W_right = W / n_right; rx2 = cor_x + cor_w_s
                for i in range(n_right):
                    idx = n_per_side+i; cy2 = py + i*(dh/n_right); ch = dh/n_right
                    svg += (f'<rect x="{rx2}" y="{cy2}" width="{cam_w_s}" height="{ch}" fill="#eff6ff" stroke="#3b82f6" stroke-width="2.5" rx="4"/>'
                            + svgt_local(rx2+cam_w_s/2, cy2+ch/2-8, f"KAMERA {idx+1}", size=22, weight="700", color="#1e40af")
                            + svgt_local(rx2+cam_w_s/2, cy2+ch/2+20, f"{cham_L_real:.1f} x {cham_W_right:.1f} m", size=16, color="#3b82f6"))
                    if i < n_right-1: svg += f'<line x1="{rx2}" y1="{cy2+ch}" x2="{rx2+cam_w_s}" y2="{cy2+ch}" stroke="#93c5fd" stroke-width="2" stroke-dasharray="10,5"/>'
        elif corridor_pos in ["chap", "o'ng"]:
            cor_x2 = px if corridor_pos == "chap" else px+dw-cor_w_s
            ox2 = cor_x2+cor_w_s if corridor_pos == "chap" else px
            cham_width = dw - cor_w_s
            cham_L_real = L - corridor_w; cham_W_real = W / n_chambers
            svg += (f'<rect x="{cor_x2}" y="{py}" width="{cor_w_s}" height="{dh}" fill="#fef3c7" opacity="0.7"/>'
                    f'<line x1="{ox2}" y1="{py}" x2="{ox2}" y2="{py+dh}" stroke="#d97706" stroke-width="3" stroke-dasharray="12,8"/>'
                    + svgt_local(cor_x2+cor_w_s/2, py+dh/2, f"YO'LAK\n{corridor_w}m", size=24, weight="700", color="#92400e"))
            svg += dim_h_local(cor_x2, cor_x2+cor_w_s, py-40, f"{corridor_w}m", color="#d97706", size=22, ext=8)
            for i in range(n_chambers):
                cy2 = py+i*(dh/n_chambers); ch = dh/n_chambers
                svg += (f'<rect x="{ox2}" y="{cy2}" width="{cham_width}" height="{ch}" fill="#eff6ff" stroke="#3b82f6" stroke-width="2.5" rx="4"/>'
                        + svgt_local(ox2+cham_width/2, cy2+ch/2-6, f"KAMERA {i+1}", size=22, weight="700", color="#1e40af")
                        + svgt_local(ox2+cham_width/2, cy2+ch/2+22, f"{cham_L_real:.1f} x {cham_W_real:.1f} m", size=16, color="#3b82f6"))
                if i < n_chambers-1: svg += f'<line x1="{ox2}" y1="{cy2+ch}" x2="{ox2+cham_width}" y2="{cy2+ch}" stroke="#93c5fd" stroke-width="2" stroke-dasharray="10,5"/>'
    else:
        cham_W_real = W / n_chambers
        for i in range(n_chambers):
            cy2 = py+i*(dh/n_chambers); ch = dh/n_chambers
            svg += (f'<rect x="{px}" y="{cy2}" width="{dw}" height="{ch}" fill="#eff6ff" stroke="#3b82f6" stroke-width="2.5" rx="4"/>'
                    + svgt_local(px+dw/2, cy2+ch/2-6, f"KAMERA {i+1}", size=24, weight="700", color="#1e40af")
                    + svgt_local(px+dw/2, cy2+ch/2+22, f"{L:.1f} x {cham_W_real:.1f} m", size=18, color="#3b82f6"))
            if i < n_chambers-1: svg += f'<line x1="{px}" y1="{cy2+ch}" x2="{px+dw}" y2="{cy2+ch}" stroke="#93c5fd" stroke-width="2" stroke-dasharray="10,5"/>'

    svg += dim_h_local(px, px+dw, py-110, f"L = {owmm} mm ({L:.2f} m)", color="#0f172a", size=24, ext=12)
    svg += dim_v_local(px+dw+110, py, py+dh, f"W = {ohmm} mm ({W:.2f} m)", color="#0f172a", size=24, ext=12)
    iL2 = max(0, owmm-2*wall_mm); iW2 = max(0, ohmm-2*wall_mm)
    svg += svgt_local(px+dw/2, py+dh/2-15, f"Tashqi: {owmm} x {ohmm} x {maxHmm} mm", size=18, color="#94a3b8")
    svg += svgt_local(px+dw/2, py+dh/2+12, f"Ichki: {iL2} x {iW2} mm", size=18, color="#94a3b8")
    svg += svgt_local(px+dw/2, py+dh+45,
        f"Devor: {wall_mm} mm | Patalok: {ceil_mm} mm | Pol: {floor_mm if pol_bor else 0} mm", size=18)

    if heights_list:
        y_off = py+dh+90
        svg += svgt_local(px+dw/2, y_off, "KAMERA BALANDLIKLARI:", size=18, weight="700", color="#475569")
        start_x2 = px+dw/2-(len(heights_list)*50)
        for i, h in enumerate(heights_list):
            svg += svgt_local(start_x2+i*100, y_off+30, f"K{i+1}: {h:.1f}m", size=15, color="#3b82f6")

    corner_s = 480*scale
    svg += (f'<line x1="{px}" y1="{py+6}" x2="{px+corner_s}" y2="{py+6}" stroke="#16a34a" stroke-width="4"/>'
            f'<line x1="{px+dw-corner_s}" y1="{py+6}" x2="{px+dw}" y2="{py+6}" stroke="#16a34a" stroke-width="4"/>'
            f'<line x1="{px}" y1="{py+dh-6}" x2="{px+corner_s}" y2="{py+dh-6}" stroke="#16a34a" stroke-width="4"/>'
            f'<line x1="{px+dw-corner_s}" y1="{py+dh-6}" x2="{px+dw}" y2="{py+dh-6}" stroke="#16a34a" stroke-width="4"/>')

    try:
        svg += (f'<g>{slab_svg(px,my,dw,dh,tpl,rpl,scale,"PATALOK PANELI REJASI",ls=CHAIN_FS+4)}'
                f'{chain_top(px,my,tpl,scale,fs=CHAIN_FS)}'
                f'{chain_right(px+dw+CHAIN_FS*5,my,rpl,scale,fs=CHAIN_FS)}'
                + svgt_local(px+dw/2, my+dh+55, f"Patalok: {ceil_mm} mm | Panel eni: {pw}m", size=20) + "</g>"
                + f'<g>{slab_svg(px,by,dw,dh,tpl,rpl,scale,"POL PANELI REJASI",ls=CHAIN_FS+4)}'
                f'{chain_top(px,by,tpl,scale,fs=CHAIN_FS)}'
                f'{chain_right(px+dw+CHAIN_FS*5,by,rpl,scale,fs=CHAIN_FS)}'
                + svgt_local(px+dw/2, by+dh+55, f"Pol: {floor_mm if pol_bor else 0} mm | Panel eni: {pw}m", size=20) + "</g>")
    except: pass

    leg_y = my-140
    svg += (f'<rect x="80" y="{leg_y}" width="20" height="20" fill="#16a34a" rx="4"/>'
            f'<text x="115" y="{leg_y+15}" font-family="Arial" font-size="18" fill="#475569">480 mm burchak moduli</text>'
            f'<rect x="80" y="{leg_y+32}" width="20" height="20" fill="none" stroke="#94a3b8" stroke-width="2" stroke-dasharray="4,3" rx="4"/>'
            f'<text x="115" y="{leg_y+47}" font-family="Arial" font-size="18" fill="#475569">960 mm asosiy modul</text>'
            f'<rect x="450" y="{leg_y}" width="20" height="20" fill="#fef3c7" stroke="#d97706" stroke-width="2" rx="4"/>'
            f'<text x="485" y="{leg_y+15}" font-family="Arial" font-size="18" fill="#475569">Yo\'lak zonasi</text>'
            f'<rect x="450" y="{leg_y+32}" width="20" height="20" fill="#eff6ff" stroke="#3b82f6" stroke-width="2" rx="4"/>'
            f'<text x="485" y="{leg_y+47}" font-family="Arial" font-size="18" fill="#475569">Sovutgich kamerasi</text>')

    svg += (f'<rect x="80" y="{SH-350}" width="{SW-160}" height="270" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2" rx="12"/>'
            f'<rect x="80" y="{SH-350}" width="{SW-160}" height="55" fill="#0f172a" rx="12"/>'
            f'<rect x="80" y="{SH-320}" width="{SW-160}" height="25" fill="#0f172a"/>'
            + svgt_local(SW/2, SH-320, "TECHNICAL DRAWING", size=26, weight="800", color="white")
          
            + svgt_local(1050, SH-275, "SANA:", size=18, anchor="start", weight="600", color="#475569")
            + svgt_local(1130, SH-275, datetime.now().strftime("%d.%m.%Y"), size=20, anchor="start", weight="700", color="#0f172a")
            + svgt_local(120, SH-225, f"O'lcham: {owmm}x{ohmm}x{maxHmm} mm | Devor: {wall_mm} mm | Patalok: {ceil_mm} mm | Pol: {floor_mm if pol_bor else 0} mm", size=18, anchor="start", color="#334155")
            + svgt_local(120, SH-185, f"Kameralar: {n_chambers} ta | Panel eni: {pw}m | Jami panel: {all_p} ta", size=18, anchor="start", color="#334155")
            + svgt_local(120, SH-145, f"Devor panellari: {dp} ta | Patalok: {pp} ta | Pol: {flp if pol_bor else 0} ta", size=16, anchor="start", color="#64748b")
            + svgt_local(SW-150, SH-110, "  Constructor", size=16, anchor="end", color="#94a3b8")
            + "</svg>")
    return svg

# PDF REPORT
# Fayl boshiga qo'shing:
def generate_pdf_report(project_name, room_code, L, W, H, wall_mm, ceil_mm, floor_mm,
                        pol_bor, d_turi, p_turi, pol_turi, eshik, agregat,
                        total_panels, hajm, inner_hajm, total_area,
                        fig_3d=None, svg_string=None):
    """
    PDF hisobot yaratish - SVG ni rasm sifatida qo'shish
    """
    try:
        from fpdf import FPDF
        import tempfile
        import os
        from datetime import datetime
        
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Sarlavha
        pdf.set_fill_color(17, 24, 39)
        pdf.rect(0, 0, 210, 25, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 16)
        pdf.cell(0, 15, 'TECHNICAL REPORT', ln=True, align='C')
        
        # Loyiha ma'lumotlari
        pdf.set_y(32)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, f'Loyiha: {project_name or "Nomalum"}', ln=True)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, f'Kod: {room_code}  |  Sana: {datetime.now().strftime("%d.%m.%Y %H:%M")}', ln=True)
        pdf.ln(4)
        
        # 1. ASOSIY PARAMETRLAR
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 8, '1. ASOSIY PARAMETRLAR', ln=True)
        pdf.ln(2)
        
        # Jadval
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font('Helvetica', 'B', 9)
        col1 = 60
        col2 = 40
        col3 = 60
        col4 = 40
        
        pdf.cell(col1, 7, 'Parametr', border=1, fill=True, align='C')
        pdf.cell(col2, 7, 'Qiymat', border=1, fill=True, align='C')
        pdf.cell(col1, 7, 'Parametr', border=1, fill=True, align='C')
        pdf.cell(col2, 7, 'Qiymat', border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_font('Helvetica', '', 9)
        data_rows = [
            ['Tashqi hajm', f'{hajm} m3', 'Ichki hajm', f'{inner_hajm} m3'],
            ['Umumiy maydon', f'{total_area} m2', 'Jami panellar', f'{total_panels} ta'],
            ['Devor qalinligi', f'{wall_mm} mm', 'Patalok qalinligi', f'{ceil_mm} mm'],
            ['Pol qalinligi', f'{floor_mm if pol_bor else 0} mm', 'Pol holati', 'Bor' if pol_bor else 'Yo\'q'],
            ['Devor turi', str(d_turi)[:15], 'Patalok turi', str(p_turi)[:15]],
            ['Pol turi', str(pol_turi or 'Mavjud emas')[:15], 'Eshik', str(eshik)[:20]],
            ['Agregat', str(agregat)[:20], 'Olcham', f'{L}x{W}x{H} m'],
        ]
        
        for row in data_rows:
            pdf.cell(col1, 6, str(row[0]), border=1, align='L')
            pdf.cell(col2, 6, str(row[1]), border=1, align='C')
            pdf.cell(col1, 6, str(row[2]), border=1, align='L')
            pdf.cell(col2, 6, str(row[3]), border=1, align='C')
            pdf.ln()
        
        pdf.ln(5)
        
        # 2. TEXNIK CHIZMA - SVG ni rasm sifatida qo'shish
        if svg_string:
            pdf.set_font('Helvetica', 'B', 11)
            pdf.cell(0, 8, '2. TEXNIK CHIZMA', ln=True)
            pdf.ln(2)
            
            img_added = False
            
            # ===== USUL 1: cairosvg =====
            try:
                import cairosvg
                png_data = cairosvg.svg2png(
                    bytestring=svg_string.encode('utf-8'),
                    output_width=2000,
                    output_height=1400,
                    scale=2.0
                )
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp.write(png_data)
                    tmp_path = tmp.name
                pdf.image(tmp_path, x=10, w=190)
                os.unlink(tmp_path)
                img_added = True
                pdf.ln(2)
            except ImportError:
                pass
            except Exception as e:
                print(f"cairosvg xatosi: {e}")
            
            # ===== USUL 2: weasyprint =====
            if not img_added:
                try:
                    from weasyprint import HTML
                    import io
                    
                    # SVG ni HTML wrapper
                    html_content = f'''
                    <html>
                        <head>
                            <style>
                                body {{ margin: 0; padding: 0; background: white; }}
                                svg {{ width: 100%; height: auto; }}
                            </style>
                        </head>
                        <body>
                            {svg_string}
                        </body>
                    </html>
                    '''
                    
                    # HTML ni PNG ga o'tkazish
                    png_bytes = HTML(string=html_content).write_png()
                    
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        tmp.write(png_bytes)
                        tmp_path = tmp.name
                    
                    pdf.image(tmp_path, x=10, w=190)
                    os.unlink(tmp_path)
                    img_added = True
                    pdf.ln(2)
                except ImportError:
                    pass
                except Exception as e:
                    print(f"weasyprint xatosi: {e}")
            
            # ===== USUL 3: imgkit =====
            if not img_added:
                try:
                    import imgkit
                    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False, mode='w', encoding='utf-8') as tmp:
                        tmp.write(svg_string)
                        svg_path = tmp.name
                    
                    png_path = svg_path.replace('.svg', '.png')
                    imgkit.from_file(svg_path, png_path, options={'width': 1800, 'height': 1200, 'quiet': ''})
                    
                    pdf.image(png_path, x=10, w=190)
                    
                    os.unlink(svg_path)
                    os.unlink(png_path)
                    img_added = True
                    pdf.ln(2)
                except ImportError:
                    pass
                except Exception as e:
                    print(f"imgkit xatosi: {e}")
            
            # ===== USUL 4: matplotlib =====
            if not img_added:
                try:
                    import matplotlib.pyplot as plt
                    import io
                    from PIL import Image
                    import xml.etree.ElementTree as ET
                    
                    # SVG ni vaqtinchalik faylga saqlash
                    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False, mode='w', encoding='utf-8') as tmp:
                        tmp.write(svg_string)
                        svg_path = tmp.name
                    
                    # Matplotlib orqali yuklash
                    fig, ax = plt.subplots(figsize=(19, 13), dpi=100)
                    ax.set_position([0, 0, 1, 1])
                    ax.axis('off')
                    
                    # SVG ni o'qish va ko'rsatish (oddiy SVG uchun)
                    try:
                        import svgutils.transform as sg
                        fig = sg.fromfile(svg_path)
                        fig.save('temp.png')
                        pdf.image('temp.png', x=10, w=190)
                        os.unlink('temp.png')
                        img_added = True
                    except:
                        plt.close()
                    
                    os.unlink(svg_path)
                    pdf.ln(2)
                except ImportError:
                    pass
                except Exception as e:
                    print(f"matplotlib xatosi: {e}")
            
            # ===== USUL 5: SVG ni matn sifatida =====
            if not img_added:
                pdf.set_font('Helvetica', '', 9)
                pdf.cell(0, 6, 'Chizma: SVG formatda', ln=True)
                pdf.cell(0, 6, f'Chizma fayli: {room_code}_drawing.svg', ln=True)
                pdf.cell(0, 6, f'Olcham: {L}x{W}x{H} m', ln=True)
                pdf.cell(0, 6, f'Panellar: {total_panels} ta', ln=True)
                
                # SVG ning qisqa ko'rinishi
                pdf.ln(2)
                pdf.set_font('Helvetica', '', 5)
                pdf.cell(0, 4, '--- SVG CHIZMA (qisqa) ---', ln=True)
                lines = svg_string.split('\n')[:15]
                for line in lines:
                    if len(line) > 100:
                        line = line[:100] + '...'
                    pdf.cell(0, 3, line, ln=True)
        
        # Footer
        pdf.set_y(270)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 5, 'Constructor | Sovutish tizimlari loyihalash', align='C')
        
        pdf_output = pdf.output(dest='S')
        
        if isinstance(pdf_output, str):
            pdf_bytes = pdf_output.encode('latin-1')
        else:
            pdf_bytes = bytes(pdf_output)
        
        return pdf_bytes
        
    except Exception as e:
        error_msg = f"PDF xatosi: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return f"PDF yaratishda xatolik: {str(e)}".encode('utf-8')




def get_groq_recommendation(mahsulot_turi, saqlash_temp, ochilish_soni,
                            hudud, namlik_talabi, L, W, H, pol_bor, mode="yagona",
                            panel_width_m=1.16, n_chambers=1, has_corridor=False,
                            corridor_w=0, corridor_pos="markaz"):
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    product_database = {
        "Go'sht": {
            "harorat_min": -22, "harorat_max": -18, "optimal_harorat": -20,
            "rejim": "Muzlatish", "namlik_min": 85, "namlik_max": 90,
            "devor_mm": 100, "patalok_mm": 80, "pol_mm": 100,
            "agregat_turi": "Past haroratli split-sistema",
            "agregat_brendi": "Bitzer yoki Frascold",
            "eshik_turi": "Muzlatkich eshigi (qalin izolyatsiyali)",
            "shamollatish": "Majburiy shamollatish (ventilyatorli)",
            "sovutish_tezligi": "4-6 soatda -20C gacha",
            "harorat_tebranishi": "1C dan oshmasligi kerak",
            "max_yuk_kg_m3": 280,
            "mahsulot_joylashuvi": "Har 1 m3 ga 250-300 kg gosht",
            "javon_oraligi": "40-50 sm",
            "eslatma": "Gosht uchun barqaror past harorat va namlik muhim."
        },
        "Tovuq": {
            "harorat_min": -22, "harorat_max": -18, "optimal_harorat": -20,
            "rejim": "Muzlatish", "namlik_min": 85, "namlik_max": 90,
            "devor_mm": 100, "patalok_mm": 80, "pol_mm": 100,
            "agregat_turi": "Past haroratli split-sistema",
            "agregat_brendi": "Bitzer yoki Zanotti",
            "eshik_turi": "Muzlatkich eshigi (qalin izolyatsiyali)",
            "shamollatish": "Majburiy shamollatish (ventilyatorli)",
            "sovutish_tezligi": "2-4 soatda -18C gacha",
            "harorat_tebranishi": "1C",
            "max_yuk_kg_m3": 220,
            "mahsulot_joylashuvi": "Har 1 m3 ga 200-250 kg tovuq goshti",
            "javon_oraligi": "35-45 sm",
            "eslatma": "Tovuq goshti tez buziladi. Tez sovutish va gigiyena muhim."
        },
        "Baliq": {
            "harorat_min": -28, "harorat_max": -22, "optimal_harorat": -25,
            "rejim": "Chuqur muzlatish", "namlik_min": 90, "namlik_max": 95,
            "devor_mm": 120, "patalok_mm": 100, "pol_mm": 120,
            "agregat_turi": "Past haroratli sanoat split-sistema",
            "agregat_brendi": "Bitzer yoki Copeland (sanoat)",
            "eshik_turi": "Muzlatkich eshigi (qalin izolyatsiyali, germetik)",
            "shamollatish": "Kuchli majburiy shamollatish",
            "sovutish_tezligi": "3-5 soatda -25C gacha",
            "harorat_tebranishi": "0.5C dan oshmasligi kerak",
            "max_yuk_kg_m3": 320,
            "mahsulot_joylashuvi": "Har 1 m3 ga 300-350 kg baliq",
            "javon_oraligi": "30-40 sm",
            "eslatma": "Baliq chuqur muzlatish talab qiladi. Harorat -22C dan yuqori bolishi mumkin emas."
        },
        "Muzqaymoq": {
            "harorat_min": -30, "harorat_max": -25, "optimal_harorat": -28,
            "rejim": "Chuqur muzlatish", "namlik_min": 80, "namlik_max": 85,
            "devor_mm": 150, "patalok_mm": 120, "pol_mm": 150,
            "agregat_turi": "Past haroratli sanoat split-sistema",
            "agregat_brendi": "Bitzer yoki Copeland (sanoat)",
            "eshik_turi": "Muzlatkich eshigi (qalin izolyatsiyali)",
            "shamollatish": "Kuchli majburiy shamollatish",
            "sovutish_tezligi": "6-8 soatda -28C gacha",
            "harorat_tebranishi": "0.5C",
            "max_yuk_kg_m3": 180,
            "mahsulot_joylashuvi": "Har 1 m3 ga 150-200 kg muzqaymoq",
            "javon_oraligi": "40-50 sm",
            "eslatma": "Eng past harorat kerak. Harorat -25C dan yuqori bolsa muzqaymoq eriydi."
        },
        "Sut mahsulotlari": {
            "harorat_min": 2, "harorat_max": 6, "optimal_harorat": 4,
            "rejim": "Sovutish", "namlik_min": 85, "namlik_max": 90,
            "devor_mm": 80, "patalok_mm": 80, "pol_mm": 80,
            "agregat_turi": "Orta haroratli split-sistema",
            "agregat_brendi": "Zanotti yoki Frascold",
            "eshik_turi": "Bir tabaqali eshik (90x190 sm)",
            "shamollatish": "Tabiiy shamollatish yetarli",
            "sovutish_tezligi": "1-2 soatda +4C gacha",
            "harorat_tebranishi": "1C",
            "max_yuk_kg_m3": 180,
            "mahsulot_joylashuvi": "Har 1 m3 ga 150-200 kg sut mahsulotlari",
            "javon_oraligi": "35-45 sm",
            "eslatma": "+2...+6C optimal harorat. Sut mahsulotlari hidni tez yutadi."
        },
        "Meva-sabzavot": {
            "harorat_min": 2, "harorat_max": 10, "optimal_harorat": 5,
            "rejim": "Sovutish", "namlik_min": 90, "namlik_max": 95,
            "devor_mm": 80, "patalok_mm": 80, "pol_mm": 80,
            "agregat_turi": "Orta haroratli split-sistema",
            "agregat_brendi": "Zanotti yoki Frascold",
            "eshik_turi": "Bir tabaqali eshik (90x190 sm)",
            "shamollatish": "Tabiiy shamollatish + namlik nazorati",
            "sovutish_tezligi": "2-4 soatda +5C gacha",
            "harorat_tebranishi": "1.5C",
            "max_yuk_kg_m3": 250,
            "mahsulot_joylashuvi": "Har 1 m3 ga 200-300 kg meva-sabzavot",
            "javon_oraligi": "40-50 sm",
            "eslatma": "Namlik 90-95% bolishi kerak. Har bir meva turi oz haroratini talab qiladi."
        },
        "Gullar": {
            "harorat_min": 3, "harorat_max": 8, "optimal_harorat": 5,
            "rejim": "Sovutish", "namlik_min": 80, "namlik_max": 90,
            "devor_mm": 80, "patalok_mm": 80, "pol_mm": 80,
            "agregat_turi": "Orta haroratli maxsus split-sistema (past shovqinli)",
            "agregat_brendi": "Zanotti yoki Frascold (maxsus seriya)",
            "eshik_turi": "Shisha eshik yoki bir tabaqali eshik",
            "shamollatish": "Yumshoq shamollatish",
            "sovutish_tezligi": "1-2 soatda +5C gacha (sekin sovutish)",
            "harorat_tebranishi": "0.5C dan oshmasligi kerak",
            "max_yuk_kg_m3": 80,
            "mahsulot_joylashuvi": "Har 1 m3 ga 50-100 kg gullar",
            "javon_oraligi": "50-60 sm",
            "eslatma": "Gullar nozik mahsulot. Harorat +3C dan past bolsa muzlaydi, +8C dan yuqori bolsa soliydi."
        },
        "Dorilar": {
            "harorat_min": 2, "harorat_max": 8, "optimal_harorat": 5,
            "rejim": "Sovutish", "namlik_min": 40, "namlik_max": 60,
            "devor_mm": 100, "patalok_mm": 80, "pol_mm": 100,
            "agregat_turi": "Orta haroratli aniq haroratli split-sistema",
            "agregat_brendi": "Zanotti yoki maxsus farmatsevtika",
            "eshik_turi": "Muzlatkich eshigi (germetik)",
            "shamollatish": "Majburiy shamollatish (HEPA filtrli)",
            "sovutish_tezligi": "2-3 soatda +5C gacha",
            "harorat_tebranishi": "0.3C",
            "max_yuk_kg_m3": 130,
            "mahsulot_joylashuvi": "Har 1 m3 ga 100-150 kg dorilar",
            "javon_oraligi": "30-40 sm",
            "eslatma": "Namlik nazorati muhim. Harorat aniq 0.3C bolishi kerak."
        },
        "Ichimliklar": {
            "harorat_min": 3, "harorat_max": 5, "optimal_harorat": 4,
            "rejim": "Sovutish", "namlik_min": 60, "namlik_max": 70,
            "devor_mm": 80, "patalok_mm": 80, "pol_mm": 80,
            "agregat_turi": "Orta haroratli split-sistema",
            "agregat_brendi": "Zanotti yoki Frascold",
            "eshik_turi": "Shisha eshik yoki bir tabaqali eshik",
            "shamollatish": "Tabiiy shamollatish",
            "sovutish_tezligi": "3-5 soatda +4C gacha",
            "harorat_tebranishi": "1C",
            "max_yuk_kg_m3": 350,
            "mahsulot_joylashuvi": "Har 1 m3 ga 300-400 kg ichimliklar",
            "javon_oraligi": "35-45 sm",
            "eslatma": "Harorat +1C dan past bolsa muzlab qolishi mumkin."
        },
        "Aralash mahsulot": {
            "harorat_min": -20, "harorat_max": 5, "optimal_harorat": -18,
            "rejim": "Aralash", "namlik_min": 70, "namlik_max": 85,
            "devor_mm": 100, "patalok_mm": 100, "pol_mm": 100,
            "agregat_turi": "Kop zonali split-sistema",
            "agregat_brendi": "Bitzer yoki Zanotti",
            "eshik_turi": "Muzlatkich eshigi",
            "shamollatish": "Majburiy shamollatish",
            "sovutish_tezligi": "4-6 soat",
            "harorat_tebranishi": "1C",
            "max_yuk_kg_m3": 250,
            "mahsulot_joylashuvi": "Har 1 m3 ga 200-300 kg",
            "javon_oraligi": "40-50 sm",
            "eslatma": "Kop zonali tizim kerak. Har bir zona oz haroratiga ega."
        },
    }

    try:
        L = float(L); W = float(W); H = float(H)
        n_chambers = int(n_chambers)
        panel_width_m = float(panel_width_m)
        corridor_w = float(corridor_w)
        if isinstance(ochilish_soni, str):
            ochilish_map = {"Kam": 2, "O'rtacha": 5, "Ko'p": 10}
            ochilish_soni = ochilish_map.get(ochilish_soni, 5)
    except:
        pass

    product_info = product_database.get(mahsulot_turi, product_database["Aralash mahsulot"])

    total_area = L * W
    total_volume = L * W * H
    wall_m = product_info["devor_mm"] / 1000.0
    ceil_m = product_info["patalok_mm"] / 1000.0
    floor_m = product_info["pol_mm"] / 1000.0 if pol_bor else 0

    inner_L = L - 2 * wall_m
    inner_W = W - 2 * wall_m
    inner_H = H - ceil_m - floor_m
    inner_area = inner_L * inner_W
    inner_volume = inner_area * inner_H

    devor_maydoni = 2 * (L + W) * H
    patalok_maydoni = L * W
    pol_maydoni = L * W if pol_bor else 0

    devor_panellar = (math.ceil(L/panel_width_m)*2) + (math.ceil(W/panel_width_m)*2)
    patalok_panellar = math.ceil(L/panel_width_m) * math.ceil(W/panel_width_m)
    pol_panellar = patalok_panellar if pol_bor else 0
    jami_panellar = devor_panellar + patalok_panellar + pol_panellar

    tashqi_harorat = {"Issiq": 45, "Mo'tadil": 30, "Sovuq": 15}.get(hudud, 30)
    harorat_farqi = abs(tashqi_harorat - product_info["optimal_harorat"])
    k_value = 0.022

    wall_heat = (devor_maydoni * k_value * harorat_farqi) / (product_info["devor_mm"]/1000) / 1000
    ceiling_heat = (patalok_maydoni * k_value * harorat_farqi) / (product_info["patalok_mm"]/1000) / 1000
    if pol_bor:
        floor_heat = (pol_maydoni * k_value * harorat_farqi * 0.7) / (product_info["pol_mm"]/1000) / 1000
    else:
        floor_heat = (pol_maydoni * 1.5 * harorat_farqi) / 0.2 / 1000

    door_heat = total_volume * 0.02 * ochilish_soni / 24
    max_yuk = product_info["max_yuk_kg_m3"]
    product_heat = inner_volume * max_yuk * 0.1 * 3.5 / 24 / 1000

    total_heat_kw = wall_heat + ceiling_heat + floor_heat + door_heat + product_heat
    safety = {"Issiq": 1.3, "Mo'tadil": 1.2, "Sovuq": 1.15}.get(hudud, 1.2)
    required_kw = total_heat_kw * safety

    required_hp = required_kw / 0.746
    hp_options = [3, 5, 7.5, 10, 15, 20, 25, 30]
    best_hp = min(hp_options, key=lambda x: abs(x - required_hp) if x >= required_hp else float('inf'))
    best_kw = best_hp * 0.746

    daily_kwh = best_kw * 16
    monthly_kwh = daily_kwh * 30
    yearly_kwh = daily_kwh * 365
    amper_380v = (best_kw * 1000) / (380 * 1.73 * 0.85) if best_kw > 0 else 0
    amper_220v = (best_kw * 1000) / 220 if best_kw > 0 else 0

    result_data = {
        "mahsulot": mahsulot_turi,
        "rejim": product_info["rejim"],
        "harorat_oraligi": f"{product_info['harorat_min']}C dan {product_info['harorat_max']}C gacha",
        "optimal_harorat": f"{product_info['optimal_harorat']}C",
        "harorat_tebranishi": product_info["harorat_tebranishi"],
        "olchamlar": {
            "tashqi": f"{L:.1f} x {W:.1f} x {H:.1f} m",
            "ichki": f"{inner_L:.2f} x {inner_W:.2f} x {inner_H:.2f} m",
            "umumiy_maydon": f"{total_area:.1f} m2",
            "ichki_maydon": f"{inner_area:.2f} m2",
            "umumiy_hajm": f"{total_volume:.1f} m3",
            "ichki_hajm": f"{inner_volume:.2f} m3",
            "foydali_hajm": f"{inner_volume * 0.7:.1f} m3"
        },
        "konstruksiya": {
            "devor_qalinligi": f"{product_info['devor_mm']} mm",
            "patalok_qalinligi": f"{product_info['patalok_mm']} mm",
            "pol_qalinligi": f"{product_info['pol_mm']} mm" if pol_bor else "Mavjud emas",
            "izolyatsiya_materiali": "PUR (Poliizosianurat)",
            "devor_panellari": f"{devor_panellar} ta",
            "patalok_panellari": f"{patalok_panellar} ta",
            "pol_panellari": f"{pol_panellar} ta" if pol_bor else "0 ta",
            "jami_panellar": f"{jami_panellar} ta",
            "panel_eni": f"{panel_width_m} m"
        },
        "agregat": {
            "turi": product_info["agregat_turi"],
            "brend_tavsiya": product_info["agregat_brendi"],
            "quvvat_hp": f"{best_hp} HP",
            "quvvat_kw": f"{best_kw:.1f} kW",
            "sovutish_quvvati": f"{required_kw:.1f} kW",
            "issiqlik_yuklamasi": f"{total_heat_kw:.2f} kW",
            "kuchlanish": "380V (3 faza)" if best_hp > 3 else "220V (1 faza)"
        },
        "energiya_sarfi": {
            "soatlik": f"{best_kw:.1f} kW/soat",
            "kundalik": f"{daily_kwh:.0f} kWh/kun",
            "oylik": f"{monthly_kwh:.0f} kWh/oy",
            "yillik": f"{yearly_kwh:.0f} kWh/yil",
            "tok_amper_380v": f"{amper_380v:.1f} A (380V)",
            "tok_amper_220v": f"{amper_220v:.1f} A (220V)" if best_hp <= 3 else "380V talab qilinadi"
        },
        "eshik": {
            "turi": product_info["eshik_turi"],
            "soni": "1 ta" if inner_area < 50 else "2 ta",
            "ochilish_soni": f"Kuniga {ochilish_soni} marta"
        },
        "shamollatish": product_info["shamollatish"],
        "namlik": f"%{product_info['namlik_min']}-{product_info['namlik_max']}",
        "mahsulot_joylashtirish": {
            "zichlik": product_info["mahsulot_joylashuvi"],
            "javon_oraligi": product_info["javon_oraligi"],
            "maksimal_yuk": f"{max_yuk} kg/m3"
        },
        "hudud": hudud,
        "tashqi_harorat": f"{tashqi_harorat}C",
        "harorat_farqi": f"{harorat_farqi}C",
        "eslatma": product_info["eslatma"],
        "xulosa": (
            f"MAHSULOT: {mahsulot_turi}\n"
            f"KAMERA: {L:.1f} x {W:.1f} x {H:.1f} m = {total_area:.1f} m2 = {total_volume:.1f} m3\n"
            f"HARORAT: {product_info['optimal_harorat']}C ({product_info['harorat_min']}C dan {product_info['harorat_max']}C gacha)\n"
            f"NAMLIK: %{product_info['namlik_min']}-{product_info['namlik_max']}\n\n"
            f"AGREGAT: {product_info['agregat_turi']}\n"
            f"Brend: {product_info['agregat_brendi']}\n"
            f"Quvvat: {best_hp} HP ({best_kw:.1f} kW)\n"
            f"Sovutish quvvati: {required_kw:.1f} kW\n"
            f"Kuchlanish: {'380V (3 faza)' if best_hp > 3 else '220V (1 faza)'}\n"
            f"Tok kuchi: {amper_380v:.1f}A (380V)\n\n"
            f"ENERGIYA SARFI:\n"
            f"Soatlik: {best_kw:.1f} kW\n"
            f"Kundalik: {daily_kwh:.0f} kWh\n"
            f"Oylik: {monthly_kwh:.0f} kWh\n"
            f"Yillik: {yearly_kwh:.0f} kWh\n\n"
            f"KONSTRUKSIYA:\n"
            f"Devor: {product_info['devor_mm']}mm PUR panel ({devor_panellar} ta)\n"
            f"Patalok: {product_info['patalok_mm']}mm PUR panel ({patalok_panellar} ta)\n"
            f"Pol: {product_info['pol_mm']}mm PUR panel ({pol_panellar} ta) if pol_bor else 'Izolyatsiyasiz'\n"
            f"Jami: {jami_panellar} ta panel ({panel_width_m}m enli)\n\n"
            f"MUHIM: {product_info['eslatma']}"
        )
    }

    if not api_key:
        return {"success": True, "data": result_data, "warning": "API kaliti yoq", "source": "offline"}

    try:
        prompt = f"""Siz sovutish tizimlari boyicha texnik ekspertsiz.
QUYIDAGI KAMERA UCHUN TEXNIK TAVSIYA BERING:
Mahsulot: {mahsulot_turi}
Kamera: {L}x{W}x{H}m = {total_area:.1f}m2
Hudud: {hudud} (tashqi harorat: {tashqi_harorat}C)
TEXNIK PARAMETRLAR: {json.dumps(result_data, indent=2, ensure_ascii=False)}
FAQAT JSON FORMATDA JAVOB BERING:
{{"agregat_tanlash_sababi":"...","energiya_tejash":"...","umumiy_xulosa":"..."}}
PUL VA NARX HAQIDA YOZMANG."""

        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.3,
                "max_tokens": 800,
                "messages": [
                    {"role": "system", "content": "Siz sovutish tizimlari boyicha texnik ekspertsiz."},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=60)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        start = content.find("{"); end = content.rfind("}")
        if start != -1 and end != -1:
            result_data["ai_professional_tavsiya"] = json.loads(content[start:end+1])
        return {"success": True, "data": result_data, "warning": None, "source": "groq_ai"}
    except Exception:
        return {"success": True, "data": result_data, "warning": "AI sorovda vaqtinchalik xatolik", "source": "offline"}

# TELEGRAM
def build_tg_msg(d):
    ai_block = ""
    if d.get("ai_data"):
        ai = d["ai_data"]
        ai_block = (f"\n\n<b>AI TAVSIYA</b>\n"
                    f"* Rejim: {html.escape(str(ai.get('rejim','-')))}\n"
                    f"* Agregat: {html.escape(str(ai.get('agregat_turi','-')))} ({html.escape(str(ai.get('agregat_quvvati','-')))})\n"
                    f"* Energiya: {html.escape(str(ai.get('energiya_kunlik','-')))}")
    return (f'<b>YANGI BUYURTMA</b>\n\n'
            f'<b>Loyiha:</b> {html.escape(str(d["project_name"]))}\n'
            f'<b>Kod:</b> {html.escape(str(d["room_code"]))}\n'
            f'<b>Sana:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}\n\n'
            f'<b>Olcham:</b> {d["L"]} x {d["W"]} x {d["H"]} m\n'
            f'<b>Hajm:</b> {d["hajm"]} m3\n'
            f'<b>Devor:</b> {d["wall_mm"]} mm  |  <b>Patalok:</b> {d["ceil_mm"]} mm\n'
            f'<b>Eshik:</b> {html.escape(str(d["eshik"]))}\n'
            f'<b>Agregat:</b> {html.escape(str(d["agregat"]))}\n'
            f'<b>Panellar:</b> {d["dp"]}+{d["pp"]}+{d["flp"]} ta'
            + ai_block).strip()

def send_tg(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    if not token: return False, "Token topilmadi"
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id":TELEGRAM_CHAT_ID,"text":msg,"parse_mode":"HTML"}, timeout=30)
        return (True,"Yuborildi") if r.status_code==200 else (False,r.text)
    except Exception as e:
        return False, str(e)

def svg_to_html_bytes(svg_string):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Texnik Chizma</title>
<style>body{{margin:0;padding:20px;background:white;}}svg{{width:100%;height:auto;}}</style></head>
<body>{svg_string}</body></html>""".encode('utf-8')

# SIDEBAR
# SIDEBAR
with st.sidebar:
    st.markdown("## Control Panel")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    
    # Asosiy rejim tanlash
    main_mode = st.radio("Asosiy rejim", ["Sovutish tizimi", "Qurilish"], key="main_mode")
    st.markdown("</div>", unsafe_allow_html=True)
    
    if main_mode == "Sovutish tizimi":
        mode = st.radio("Kamera rejimi", ["Yagona kamera", "Multi-kamera"], key="mode")
        st.markdown("</div>", unsafe_allow_html=True)
        if mode == "Yagona kamera":
            st.markdown("<div class='card'><b>Olchamlar</b>", unsafe_allow_html=True)
            st.text_input("Uzunlik (m)", key="L_text", on_change=save_form_data)
            st.text_input("Eni (m)",     key="W_text", on_change=save_form_data)
            st.text_input("Balandlik (m)", key="H_text", on_change=save_form_data)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'><b>Panel va material</b>", unsafe_allow_html=True)
            st.selectbox("Devor turi",      d_turi_opts, key="d_turi",       on_change=save_form_data)
            st.selectbox("Devor qalinligi", d_qalin_opts, key="d_qalin",     on_change=save_form_data)
            st.selectbox("Patalok turi",    p_turi_opts, key="p_turi",       on_change=save_form_data)
            st.selectbox("Patalok qalinligi", p_qalin_opts, key="p_qalin",   on_change=save_form_data)
            st.selectbox("Panel eni",       pw_opts, key="panel_width_m",    on_change=save_form_data)
            st.toggle("Pol paneli",         key="pol_bor",                   on_change=save_form_data)
            if st.session_state["pol_bor"]:
                st.selectbox("Pol materiali", pol_material_opts, key="pol_material", on_change=save_form_data)
                if st.session_state.get("pol_material", " panel") == " panel":
                    st.selectbox("Pol qalinligi", pol_qalin_opts, key="pol_qalin", on_change=save_form_data)
                else:
                    st.number_input("Beton qalinligi (mm)", min_value=50, max_value=500, value=100, step=10, key="beton_qalinligi_mm", on_change=save_form_data)
                    st.caption("Beton M250 markasi tavsiya etiladi")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'><b>Eshik va agregat</b>", unsafe_allow_html=True)

            eshik_turi = st.selectbox("Eshik turi", eshik_opts, key="eshik", on_change=save_form_data)

            # Custom eshik o'lchamlari
            if eshik_turi == "Custom":
                col_w, col_h = st.columns(2)
                with col_w:
                    st.number_input("Eshik kengligi (mm)", 600, 2000, 900, 50, key="eshik_custom_width", on_change=save_form_data)
                with col_h:
                    st.number_input("Eshik balandligi (mm)", 1500, 3000, 1900, 50, key="eshik_custom_height", on_change=save_form_data)
                
                st.number_input("Eshik soni", 1, 10, 1, key="eshik_soni", on_change=save_form_data)

            st.radio("Eshik joyi", eshik_joyi_opts, key="eshik_joyi", on_change=save_form_data)
            
            # ========== YANGI: 5 VARIANTLI ESHIK POZITSIYASI ==========
            eshik_pos_opts = [
                "Chap tomon burchak o'rniga",
                "Biroz chapga",
                "O'rta",
                "Biroz o'ngga",
                "O'ng tomon burchak o'rniga"
            ]
            
            # Eshik joyiga qarab tavsifni o'zgartirish
            joyi = st.session_state.get("eshik_joyi", "Old")
            pos_descriptions = {
                "Chap": {
                    "Chap tomon burchak o'rniga": "📍 Chap burchakda (burchak hisoblanmaydi)",
                    "Biroz chapga": "📍 Chap devorga yaqin (burchak qoladi)",
                    "O'rta": "📍 Devorning o'rtasida",
                    "Biroz o'ngga": "📍 O'ng devorga yaqin (burchak qoladi)",
                    "O'ng tomon burchak o'rniga": "📍 O'ng burchakda (burchak hisoblanmaydi)"
                },
                "O'ng": {
                    "Chap tomon burchak o'rniga": "📍 Chap burchakda (burchak hisoblanmaydi)",
                    "Biroz chapga": "📍 Chap devorga yaqin (burchak qoladi)",
                    "O'rta": "📍 Devorning o'rtasida",
                    "Biroz o'ngga": "📍 O'ng devorga yaqin (burchak qoladi)",
                    "O'ng tomon burchak o'rniga": "📍 O'ng burchakda (burchak hisoblanmaydi)"
                },
                "Old": {
                    "Chap tomon burchak o'rniga": "📍 Chap burchakda (burchak hisoblanmaydi)",
                    "Biroz chapga": "📍 Chap tomonga (burchak qoladi)",
                    "O'rta": "📍 Devorning o'rtasida",
                    "Biroz o'ngga": "📍 O'ng tomonga (burchak qoladi)",
                    "O'ng tomon burchak o'rniga": "📍 O'ng burchakda (burchak hisoblanmaydi)"
                },
                "Orqa": {
                    "Chap tomon burchak o'rniga": "📍 Chap burchakda (burchak hisoblanmaydi)",
                    "Biroz chapga": "📍 Chap tomonga (burchak qoladi)",
                    "O'rta": "📍 Devorning o'rtasida",
                    "Biroz o'ngga": "📍 O'ng tomonga (burchak qoladi)",
                    "O'ng tomon burchak o'rniga": "📍 O'ng burchakda (burchak hisoblanmaydi)"
                }
            }
            
            selected_pos = st.radio(
                "Eshik pozitsiyasi",
                eshik_pos_opts,
                key="eshik_pozitsiya",
                on_change=save_form_data,
                index=2  # Default "O'rta"
            )
            
            # Tanlangan pozitsiya uchun tavsifni ko'rsatish
            desc = pos_descriptions.get(joyi, {}).get(selected_pos, "")
            if desc:
                st.caption(desc)
            # ========== YANGI QISM TUGAYDI ==========
            
            st.radio("Ochilish", eshik_och_opts, key="eshik_ochilish", on_change=save_form_data)
            
            st.markdown("---")
            
            # ========== KAMERA BO'LISH ==========
            st.markdown("#### Kamera bo'lish")

            kamera_bolish_turi = st.radio(
                "Bo'lish turi",
                ["Yo'q", "Uzunlik bo'yicha", "Eni bo'yicha"],
                key="kamera_bolish_turi",
                on_change=save_form_data
            )

            if kamera_bolish_turi != "Yo'q":
                kameralar_soni = st.selectbox(
                    "Kameralar soni",
                    [2, 3, 4, 5, 6],
                    index=0,
                    key="kameralar_soni",
                    on_change=save_form_data
                )
                
                st.caption(f"⚠️ Kamera {kamera_bolish_turi} {kameralar_soni} ta qismga bo'linadi")
                
                # Har bir kamera uchun eshik
                st.checkbox("Har bir kamera uchun eshik", key="har_bir_kamera_eshik", on_change=save_form_data)
                if st.session_state.get("har_bir_kamera_eshik", False):
                    for i in range(kameralar_soni):
                        st.markdown(f"**Kamera {i+1}**")
                        
                        # Eshik joyi
                        joyi_kamera = st.selectbox(
                            f"Eshik joyi",
                            eshik_joyi_opts,
                            key=f"kamera_eshik_joyi_{i}",
                            on_change=save_form_data
                        )
                        
                        # ========== YANGI: HAR BIR KAMERA UCHUN 5 VARIANT ==========
                        pos_descriptions_kamera = {
                            "Chap": {
                                "Chap tomon burchak o'rniga": "📍 Chap burchakda (burchak hisoblanmaydi)",
                                "Biroz chapga": "📍 Chap devorga yaqin (burchak qoladi)",
                                "O'rta": "📍 Devorning o'rtasida",
                                "Biroz o'ngga": "📍 O'ng devorga yaqin (burchak qoladi)",
                                "O'ng tomon burchak o'rniga": "📍 O'ng burchakda (burchak hisoblanmaydi)"
                            },
                            "O'ng": {
                                "Chap tomon burchak o'rniga": "📍 Chap burchakda (burchak hisoblanmaydi)",
                                "Biroz chapga": "📍 Chap devorga yaqin (burchak qoladi)",
                                "O'rta": "📍 Devorning o'rtasida",
                                "Biroz o'ngga": "📍 O'ng devorga yaqin (burchak qoladi)",
                                "O'ng tomon burchak o'rniga": "📍 O'ng burchakda (burchak hisoblanmaydi)"
                            },
                            "Old": {
                                "Chap tomon burchak o'rniga": "📍 Chap burchakda (burchak hisoblanmaydi)",
                                "Biroz chapga": "📍 Chap tomonga (burchak qoladi)",
                                "O'rta": "📍 Devorning o'rtasida",
                                "Biroz o'ngga": "📍 O'ng tomonga (burchak qoladi)",
                                "O'ng tomon burchak o'rniga": "📍 O'ng burchakda (burchak hisoblanmaydi)"
                            },
                            "Orqa": {
                                "Chap tomon burchak o'rniga": "📍 Chap burchakda (burchak hisoblanmaydi)",
                                "Biroz chapga": "📍 Chap tomonga (burchak qoladi)",
                                "O'rta": "📍 Devorning o'rtasida",
                                "Biroz o'ngga": "📍 O'ng tomonga (burchak qoladi)",
                                "O'ng tomon burchak o'rniga": "📍 O'ng burchakda (burchak hisoblanmaydi)"
                            }
                        }
                        
                        selected_pos_kamera = st.radio(
                            f"Eshik pozitsiyasi",
                            eshik_pos_opts,
                            key=f"kamera_eshik_pozitsiya_{i}",
                            on_change=save_form_data,
                            index=2  # Default "O'rta"
                        )
                        
                        desc_kamera = pos_descriptions_kamera.get(joyi_kamera, {}).get(selected_pos_kamera, "")
                        if desc_kamera:
                            st.caption(desc_kamera)
                        # ========== YANGI QISM TUGAYDI ==========
            
            st.markdown("---")
            
            st.selectbox("Agregat turi", agregat_opts, key="agregat", on_change=save_form_data)
            st.radio("Agregat joyi", ag_joyi_opts, key="agregat_joyi", on_change=save_form_data)
            st.selectbox("Brend", ag_brand_opts, key="ag_brand")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'><b>3D sozlama</b>", unsafe_allow_html=True)
            st.slider("Montaj %", 0, 100, key="montaj_progress", on_change=save_form_data)
            st.toggle("3D yozuvlar", key="show_3d_labels")
            st.markdown("</div>", unsafe_allow_html=True)
            # ========== NARXLAR VA XARAJATLAR ==========
            st.markdown("<div class='card'><b> Narxlar va Xarajatlar</b>", unsafe_allow_html=True)

            # Materiallar narxlari
            st.markdown("####  Materiallar narxlari (1 m² uchun)")
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                devor_narx = st.number_input("Devor paneli ($/m²)", min_value=0.0, max_value=500.0, value=35.0, step=5.0, key="devor_narx", on_change=save_form_data)
            with col_m2:
                patalok_narx = st.number_input("Patalok paneli ($/m²)", min_value=0.0, max_value=500.0, value=45.0, step=5.0, key="patalok_narx", on_change=save_form_data)
            with col_m3:
                pol_narx = st.number_input("Pol paneli ($/m²)", min_value=0.0, max_value=500.0, value=40.0, step=5.0, key="pol_narx", on_change=save_form_data)

            st.markdown("---")

            # Eshik narxi
            st.markdown("####  Eshik")
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                eshik_narx = st.number_input("Eshik narxi ($/dona)", min_value=0.0, max_value=5000.0, value=280.0, step=10.0, key="eshik_narx", on_change=save_form_data)
                eshik_soni_input = st.number_input("Eshik soni", min_value=0, max_value=10, value=1, key="eshik_soni_input", on_change=save_form_data)
            with col_e2:
                eshik_ornatish = st.number_input("Eshik o'rnatish ($/dona)", min_value=0.0, max_value=1000.0, value=50.0, step=10.0, key="eshik_ornatish", on_change=save_form_data)

            st.markdown("---")

            # Agregat narxi
            st.markdown("####  Agregat (Kompressor)")
            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                agregat_narx = st.number_input("Agregat narxi ($/dona)", min_value=0.0, max_value=20000.0, value=2500.0, step=100.0, key="agregat_narx", on_change=save_form_data)
            with col_a2:
                agregat_ornatish = st.number_input("Agregat o'rnatish ($)", min_value=0.0, max_value=5000.0, value=300.0, step=50.0, key="agregat_ornatish", on_change=save_form_data)
            with col_a3:
                agregat_soni = st.number_input("Agregat soni", min_value=0, max_value=5, value=1, key="agregat_soni", on_change=save_form_data)

            st.markdown("---")

            # Qo'shimcha xarajatlar
            st.markdown("####  Qo'shimcha xarajatlar")
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1:
                transport_narx = st.number_input("Transport ($)", min_value=0.0, max_value=5000.0, value=200.0, step=50.0, key="transport_narx", on_change=save_form_data)
            with col_q2:
                montaj_ishchi = st.number_input("Montaj ishchi kuchi ($)", min_value=0.0, max_value=10000.0, value=500.0, step=50.0, key="montaj_ishchi", on_change=save_form_data)
            with col_q3:
                qoshimcha_material = st.number_input("Qo'shimcha materiallar ($)", min_value=0.0, max_value=5000.0, value=150.0, step=50.0, key="qoshimcha_material", on_change=save_form_data)

            st.markdown("---")

            # ===== XARAJATLARNI HISOBLASH =====
            def calculate_costs():
                L = parse_dim(st.session_state.get("L_text", "0"))
                W = parse_dim(st.session_state.get("W_text", "0"))
                H = parse_dim(st.session_state.get("H_text", "0"))
                
                if not L or not W or not H:
                    return None
                
                panel_width = float(st.session_state.get("panel_width_m", 1.16))
                
                # Panel miqdorlari
                wall_panels = (math.ceil(L/panel_width) * 2 + math.ceil(W/panel_width) * 2) * 2
                ceiling_panels = math.ceil(L/panel_width) * math.ceil(W/panel_width)
                floor_panels = ceiling_panels if st.session_state.get("pol_bor", False) else 0
                
                panel_area = panel_width * 1.0  # 1m balandlik
                
                # Narxlar
                devor_cost = wall_panels * panel_area * devor_narx
                patalok_cost = ceiling_panels * panel_area * patalok_narx
                pol_cost = floor_panels * panel_area * pol_narx
                panel_jami = devor_cost + patalok_cost + pol_cost
                
                eshik_jami = (eshik_narx + eshik_ornatish) * eshik_soni_input
                agregat_jami = (agregat_narx + agregat_ornatish) * agregat_soni
                qoshimcha_jami = transport_narx + montaj_ishchi + qoshimcha_material
                
                jami = panel_jami + eshik_jami + agregat_jami + qoshimcha_jami
                
                return {
                    "panel_jami": panel_jami,
                    "devor_cost": devor_cost,
                    "patalok_cost": patalok_cost,
                    "pol_cost": pol_cost,
                    "eshik_jami": eshik_jami,
                    "agregat_jami": agregat_jami,
                    "qoshimcha_jami": qoshimcha_jami,
                    "jami": jami,
                    "m2_narx": jami / (L * W) if L * W > 0 else 0,
                    "wall_panels": wall_panels,
                    "ceiling_panels": ceiling_panels,
                    "floor_panels": floor_panels,
                    "total_panels": wall_panels + ceiling_panels + floor_panels,
                }

            costs = calculate_costs()

           

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div class='card'><b>Loyiha</b>", unsafe_allow_html=True)
            st.text_input("Nomi", key="project_name", on_change=save_form_data)
            st.text_input("Kodi", key="room_code",    on_change=save_form_data)
            st.markdown("</div>", unsafe_allow_html=True)
        else:  # Multi-kamera
            st.markdown("<div class='card'><b>Olchamlar</b>", unsafe_allow_html=True)
            input_mode = st.radio("Kiritish usuli",
                ["Umumiy maydon (m2)","Uzunlik x En (qolda)"], key="multi_input_mode")
            if input_mode == "Umumiy maydon (m2)":
                st.session_state.multi_area_val = st.number_input("Maydon (m2)", 10.0, 2000.0, 200.0, 5.0, key="multi_area")
                st.session_state.multi_L_val = st.number_input("Uzunlik (m)", 3.0, 100.0, 20.0, 0.5, key="multi_L")
                st.session_state.multi_W_val = round(st.session_state.multi_area_val / max(st.session_state.multi_L_val, 0.01), 2)
                st.caption(f"En: {st.session_state.multi_W_val:.2f} m")
            else:
                st.session_state.multi_L_val = st.number_input("Uzunlik (m)", 3.0, 100.0, 20.0, 0.5, key="multi_L_qol")
                st.session_state.multi_W_val = st.number_input("En (m)", 2.0, 50.0, 10.0, 0.5, key="multi_W")
                st.session_state.multi_area_val = st.session_state.multi_L_val * st.session_state.multi_W_val
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'><b>Kameralar</b>", unsafe_allow_html=True)
            n_chambers = int(st.number_input("Kameralar soni", 1, 16, 4, key="n_chambers"))
            height_mode = st.radio("Balandlik", ["Hammasi bir xil","Har biriga alohida"], key="height_mode")
            heights_list = []
            if height_mode == "Hammasi bir xil":
                multi_H_val = st.number_input("Balandlik (m)", 2.0, 10.0, 3.0, 0.1, key="multi_H")
                heights_list = [multi_H_val] * n_chambers
            else:
                for i in range(n_chambers):
                    heights_list.append(st.number_input(f"K{i+1} balandligi (m)", 2.0, 10.0, 3.0, 0.1, key=f"multi_h_{i}"))
            st.session_state.heights_list_cache = heights_list
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'><b>Yolak</b>", unsafe_allow_html=True)
            has_corridor = st.checkbox("Yolak", value=True, key="has_corridor")
            if has_corridor:
                corridor_w   = st.number_input("Kengligi (m)", 0.5, 8.0, 2.5, 0.5, key="corridor_w")
                corridor_pos = st.radio("Joyi", ["Chap","Markaz","O'ng"], index=1, key="corridor_pos").lower()
            else:
                corridor_w, corridor_pos = 0.0, "chap"
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'><b>Qurilish</b>", unsafe_allow_html=True)
            wall_mm_multi  = st.selectbox("Devor qalinligi (mm)", [80,100,120,150], index=1, key="wall_mm_multi")
            door_w_multi   = st.number_input("Eshik kengligi (m)", 0.6, 2.5, 0.96, 0.02, key="door_w_multi")
            door_h_multi   = st.number_input("Eshik balandligi (m)", 1.6, 3.5, 2.1, 0.1, key="door_h_multi")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'><b>Pol va izolyatsiya</b>", unsafe_allow_html=True)
            multi_pol_bor = st.toggle("Pol izolyatsiyasi", value=True, key="multi_pol_bor")
            if multi_pol_bor:
                multi_pol_material = st.selectbox("Pol materiali", pol_material_opts, key="multi_pol_material")
                if multi_pol_material == " panel":
                    multi_pol_qalin = st.selectbox("Pol qalinligi", pol_qalin_opts, key="multi_pol_qalin")
                    multi_beton_qalinligi_mm = None
                else:
                    multi_beton_qalinligi_mm = st.number_input("Beton qalinligi (mm)", min_value=50, max_value=500, value=100, step=10, key="multi_beton_qalinligi_mm")
                    st.caption("Beton M250 markasi tavsiya etiladi")
                    multi_pol_qalin = f"{multi_beton_qalinligi_mm}mm"
            else:
                multi_pol_material = " panel"
                multi_pol_qalin = "0mm"
                multi_beton_qalinligi_mm = None
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'><b>Kompressor</b>", unsafe_allow_html=True)
            multi_comp_brand = st.selectbox("Kompressor brendi", ag_brand_opts, key="multi_comp_brand")
            multi_comp_type  = st.selectbox("Kompressor turi", agregat_opts[1:], key="multi_comp_type")
            multi_comp_joyi  = st.radio("Kompressor joyi", ["Old","Orqa","Chap","O'ng"],
                                        key="multi_comp_joyi", horizontal=True)
            joyi_uz = {"Old":"[Old devor (Y-)]","Orqa":"[Orqa devor (Y+)]",
                       "Chap":"[Chap devor (X-)]","O'ng":"[Ong devor (X+)]"}
            st.caption(joyi_uz.get(multi_comp_joyi,""))
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'><b>Loyiha</b>", unsafe_allow_html=True)
            proj_name_multi = st.text_input("Nomi", value="200m2 Sovutgich Ombori", key="proj_name_multi")
            code_multi      = st.text_input("Kodi", value="EP-2024-M", key="code_multi")
            st.markdown("</div>", unsafe_allow_html=True)
    
    else:  # Qurilish rejimi
        if CONSTRUCTION_AVAILABLE:
            construction_params = construction_sidebar()
        else:
            st.error("Qurilish moduli mavjud emas! Iltimos, construction_module.py faylini tekshiring.")

# MAIN AREA
st.title("Constructor")
st.write("Sovutish tizimlari va Qurilish konstruksiyalari loyihalash | 3D Vizualizatsiya | Materiallar hisobi")

st.divider()
# Rejimga qarab korsatish
main_mode = st.session_state.get("main_mode", "Sovutish tizimi")

if main_mode == "Qurilish":
    if CONSTRUCTION_AVAILABLE:
        construction_main(construction_params)
    else:
        st.error("Qurilish moduli ishga tushmadi!")
        st.info("Sababi: construction_module.py fayli topilmadi yoki undagi funksiyalar toliq emas.")
else:
    # ========== SOVUTISH TIZIMI ==========
    mode = st.session_state.get("mode", "Yagona kamera")
    
    # AI TAVSIYA
    st.subheader("AI Texnik Tavsiya")
    ai_col1,ai_col2,ai_col3,ai_col4,ai_col5 = st.columns(5)
    with ai_col1: mahsulot_turi_ai = st.selectbox("Mahsulot turi", mahsulot_opts, key="mahsulot_turi_ai")
    with ai_col2: saqlash_temp_ai  = st.text_input("Harorat", value="-18C", key="saqlash_temp_ai")
    with ai_col3: ochilish_soni_ai = st.selectbox("Ochilish soni", ochilish_opts, key="ochilish_soni_ai")
    with ai_col4: hudud_ai         = st.selectbox("Hudud", hudud_opts, key="hudud_ai")
    with ai_col5: namlik_talabi_ai = st.selectbox("Namlik", namlik_opts, key="namlik_talabi_ai")

    if st.button("AI TAVSIYA OLISH", use_container_width=True):
        if mode == "Yagona kamera":
            L_ai   = parse_dim(st.session_state.get("L_text","0"))
            W_ai   = parse_dim(st.session_state.get("W_text","0"))
            H_ai   = parse_dim(st.session_state.get("H_text","0"))
            pol_bor_ai = st.session_state.get("pol_bor", False)
            mode_ai, nc_ai, hc_ai, cw_ai, cp_ai = "yagona", 1, False, 0, "markaz"
        else:
            L_ai, W_ai = multi_L_val, multi_W_val
            H_ai = max(st.session_state.get("heights_list_cache", [3.0]))
            pol_bor_ai = st.session_state.get("multi_pol_bor", True)
            mode_ai, nc_ai, hc_ai, cw_ai, cp_ai = "multi", n_chambers, has_corridor, corridor_w, corridor_pos
        if L_ai and W_ai and H_ai:
            st.session_state.ai_result = get_groq_recommendation(
                mahsulot_turi_ai, saqlash_temp_ai, ochilish_soni_ai,
                hudud_ai, namlik_talabi_ai, L_ai, W_ai, H_ai, pol_bor_ai,
                mode=mode_ai, n_chambers=nc_ai, has_corridor=hc_ai,
                corridor_w=cw_ai, corridor_pos=cp_ai)
        else:
            st.warning("Olchamlarni kiriting!")

    if st.session_state.get("ai_result") and st.session_state.ai_result.get("success"):

        d_ai = st.session_state.ai_result["data"]
        devor_qalinligi = d_ai.get('devor_qalinligi_mm') or d_ai.get('konstruksiya', {}).get('devor_qalinligi', '-')
        patalok_qalinligi = d_ai.get('patalok_qalinligi_mm') or d_ai.get('konstruksiya', {}).get('patalok_qalinligi', '-')
        agregat_turi = d_ai.get('agregat_turi') or d_ai.get('agregat', {}).get('turi', '-')
        agregat_hp = d_ai.get('agregat', {}).get('quvvat_hp', '-')
        agregat_kw = d_ai.get('agregat', {}).get('quvvat_kw', '')
        agregat_quvvati = f"{agregat_hp} ({agregat_kw})"
        energiya = d_ai.get('energiya_sarfi', {})
        energiya_kunlik = d_ai.get('energiya_kunlik') or energiya.get('kundalik', '-')
        energiya_oylik = energiya.get('oylik', '-')
        energiya_yillik = energiya.get('yillik', '-')
        tok_amper = d_ai.get('tok_amper') or energiya.get('tok_amper_380v', '-')
        xulosa = str(d_ai.get('xulosa', d_ai.get('eslatma', '-')))[:300]

        st.markdown(f"""<div class="ai-box">
        <h3>AI Tavsiya</h3>
        <b>Rejim:</b> {d_ai.get('rejim','-')} &nbsp;|&nbsp; <b>Harorat:</b> {d_ai.get('harorat_oraligi','-')}<br>
        <b>Devor:</b> {devor_qalinligi} &nbsp;|&nbsp; <b>Patalok:</b> {patalok_qalinligi}<br>
        <b>Agregat:</b> {agregat_turi} &nbsp;(Quvvat: {agregat_quvvati})<br>
        <b>Energiya sarfi:</b><br>
        &nbsp;&nbsp;Kunlik: {energiya_kunlik} &nbsp;|&nbsp; Oylik: {energiya_oylik} &nbsp;|&nbsp; Yillik: {energiya_yillik}<br>
        <b>Tok kuchi:</b> {tok_amper}<br>
        <b>Xulosa:</b> {xulosa}
        </div>""", unsafe_allow_html=True)

        ai_prof = d_ai.get('ai_professional_tavsiya', {})
        if ai_prof:
            col1, col2 = st.columns(2)
            with col1:
                if 'agregat_tanlash_sababi' in ai_prof:
                    st.info(f"Agregat tanlash sababi: {ai_prof['agregat_tanlash_sababi']}")
                if 'energiya_tejash' in ai_prof:
                    st.info(f"Energiya tejash: {ai_prof['energiya_tejash']}")

    if mode == "Yagona kamera":
        L = parse_dim(st.session_state["L_text"])
        W = parse_dim(st.session_state["W_text"])
        H = parse_dim(st.session_state["H_text"])
        
        if not all([L, W, H]):
            st.warning("Uzunlik, eni va balandlikni kiriting.")
            st.stop()

        d_turi       = st.session_state["d_turi"]
        d_qalin      = st.session_state["d_qalin"]
        p_turi       = st.session_state["p_turi"]
        p_qalin      = st.session_state["p_qalin"]
        panel_width_m = float(st.session_state["panel_width_m"])
        pol_bor      = st.session_state["pol_bor"]
        pol_material = st.session_state.get("pol_material", "PUR panel")
        pol_qalin    = st.session_state.get("pol_qalin", "100mm") if pol_material == "PUR panel" else "0mm"
        beton_qalinligi_mm = st.session_state.get("beton_qalinligi_mm", 100) if pol_material == "Beton" else 0
        eshik        = st.session_state["eshik"]
        ej           = st.session_state["eshik_joyi"]
        ep           = st.session_state["eshik_pozitsiya"]
        eo           = st.session_state["eshik_ochilish"]
        agregat      = st.session_state["agregat"]
        aj           = st.session_state["agregat_joyi"]
        project_name = st.session_state["project_name"]
        room_code    = st.session_state["room_code"]
        ag_brand     = st.session_state["ag_brand"]
        montaj       = st.session_state["montaj_progress"]
        lbl3d        = st.session_state["show_3d_labels"]

        wall_mm  = mm_val(d_qalin)
        ceil_mm  = mm_val(p_qalin)
        
        # Pol qalinligi - materialga qarab
        if pol_bor:
            if pol_material == "Beton":
                floor_mm = beton_qalinligi_mm
            else:
                floor_mm = mm_val(pol_qalin)
        else:
            floor_mm = 0
        
        hajm       = round(L*W*H, 2)
        inner_hajm = round((max(0,m_to_mm(L)-2*wall_mm)/1000)*
                        (max(0,m_to_mm(W)-2*wall_mm)/1000)*
                        (max(0,m_to_mm(H)-ceil_mm-floor_mm)/1000), 2)
        total_area = round(2*(L+W)*H + L*W + (L*W if pol_bor else 0), 2)
        wl = panel_count(L, panel_width_m); ww = panel_count(W, panel_width_m)
        dp  = (wl["total_panels"]*2)+(ww["total_panels"]*2)
        pp  = math.ceil(W/panel_width_m)
        flp = math.ceil(W/panel_width_m) if (pol_bor and pol_material == "PUR panel") else 0
        all_p = dp+pp+flp
        
        # Beton hajmi hisobi
        beton_volume = 0
        if pol_bor and pol_material == "Beton":
            beton_area = L * W
            beton_volume = calculate_concrete_volume(beton_area, floor_mm)
            beton_materials = calculate_concrete_materials(beton_volume)
            beton_cost = calculate_beton_cost(beton_volume)
        else:
            beton_materials = None
            beton_cost = 0
        
        tp = build_segs(m_to_mm(L)); rp = build_segs(m_to_mm(W))
        tm = seg_meta(tp, has_door=(eshik!="Yo'q" and ej in ["Old","Orqa"]), door_sz=door_dim(eshik)[0])
        rm = seg_meta(rp, has_door=(eshik!="Yo'q" and ej in ["Chap","O'ng"]), door_sz=door_dim(eshik)[0])

        comp_info = f"Kompressor: {ag_brand} ({agregat}) -> {aj} tomonga" if agregat != "Yo'q" else "Agregat: Yoq"
        st.markdown(
            f'<span class="badge">Material: {d_turi}</span>'
            f'<span class="badge">Devor: {d_qalin}</span>'
            f'<span class="badge">Patalok: {p_qalin}</span>'
            f'<span class="badge">{comp_info}</span>',
            unsafe_allow_html=True)

        st.divider()
        st.subheader("1. 3D Vizualizatsiya")
        
        html_3d = build_3d_single(L, W, H, wall_mm, pol_bor, eshik, ej, ep,
                                agregat, aj, ag_brand, montaj, lbl3d)
        components.html(html_3d, height=700, scrolling=True)
        
        devor_narx_sidebar = st.session_state.get("devor_narx", 35.0)
        patalok_narx_sidebar = st.session_state.get("patalok_narx", 45.0)
        pol_narx_sidebar = st.session_state.get("pol_narx", 40.0)
        eshik_narx_sidebar = st.session_state.get("eshik_narx", 280.0)

        # ===== TEXNIK CHIZMA =====
        st.subheader("2. Texnik Chizma")
        sheet_svg = make_svg(
        L, W, H, wall_mm, ceil_mm, floor_mm, pol_bor,
        project_name, room_code, ej, eshik, ep, eo,
        devor_narx=devor_narx_sidebar,
        patalok_narx=patalok_narx_sidebar,
        pol_narx=pol_narx_sidebar,
        eshik_narx=eshik_narx_sidebar  # YANGI
    )
        draw_svg(sheet_svg, height=1100)
        
        st.subheader("3. Materiallar hisobi")
        
        # Asosiy panel kartalari
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                <div class="metric-title"><i class="fas fa-cubes"></i> JAMI PANELLAR</div>
                <div class="metric-value">{all_p} ta</div>
            </div>""", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                <div class="metric-title"><i class="fas fa-border-all"></i> DEVOR PANELLARI</div>
                <div class="metric-value">{dp} ta</div>
            </div>""", unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                <div class="metric-title"><i class="fas fa-home"></i> PATALOK PANELLARI</div>
                <div class="metric-value">{pp} ta</div>
            </div>""", unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                <div class="metric-title"><i class="fas fa-chalkboard"></i> POL PANELLARI</div>
                <div class="metric-value">{flp} ta</div>
            </div>""", unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                <div class="metric-title"><i class="fas fa-door-open"></i> ESHIK</div>
                <div class="metric-value">{'1 ta' if eshik != "Yo'q" else "Yo'q"}</div>
            </div>""", unsafe_allow_html=True)
        
        # Beton hisobi (agar tanlangan bo'lsa)
        if pol_bor and pol_material == "Beton" and beton_volume > 0:
            st.markdown("---")
            st.markdown("####  Beton poydevor hisobi")
            
            col_b1, col_b2, col_b3, col_b4 = st.columns(4)
            
            with col_b1:
                st.markdown(f"""<div class="metric-box" style="background:#fef3c7; border-top:4px solid #d97706;">
                    <div class="metric-title"><i class="fas fa-weight-hanging"></i> BETON HAJMI</div>
                    <div class="metric-value">{beton_volume:.2f} m³</div>
                    <div style="font-size:10px;">Maydon: {L*W:.1f} m²</div>
                    <div style="font-size:10px;">Qalinligi: {floor_mm} mm</div>
                </div>""", unsafe_allow_html=True)
            
            if beton_materials:
                with col_b2:
                    st.markdown(f"""<div class="metric-box" style="background:#f8fafc;">
                        <div class="metric-title"><i class="fas fa-truck"></i> SEMENT (M250)</div>
                        <div class="metric-value">{beton_materials['cement_kg']} kg</div>
                        <div style="font-size:10px;">≈ {beton_materials['cement_kg']/50:.1f} xalta</div>
                    </div>""", unsafe_allow_html=True)
                
                with col_b3:
                    st.markdown(f"""<div class="metric-box" style="background:#f8fafc;">
                        <div class="metric-title"><i class="fas fa-mountain"></i> QUM</div>
                        <div class="metric-value">{beton_materials['sand_m3']} m³</div>
                    </div>""", unsafe_allow_html=True)
                
                with col_b4:
                    st.markdown(f"""<div class="metric-box" style="background:#f8fafc;">
                        <div class="metric-title"><i class="fas fa-gem"></i> SHAG'AL</div>
                        <div class="metric-value">{beton_materials['gravel_m3']} m³</div>
                    </div>""", unsafe_allow_html=True)
            
            st.caption(f"🏗️ Beton sinfi: M250 | Taxminiy narx: ~{beton_cost} birlik (material + ishchi)")
        # ============================================================
        # ========== XARAJATLAR HISOBOTI (GERMITIKA OSTIDA) ==========
        # ============================================================
        st.subheader("Xarajatlar hisoboti")

        # Narxlarni Sidebardan olish
        devor_narx = st.session_state.get("devor_narx", 35.0)
        patalok_narx = st.session_state.get("patalok_narx", 45.0)
        pol_narx = st.session_state.get("pol_narx", 40.0)
        eshik_narx = st.session_state.get("eshik_narx", 280.0)
        eshik_ornatish = st.session_state.get("eshik_ornatish", 50.0)
        eshik_soni_input = st.session_state.get("eshik_soni_input", 1)
        agregat_narx = st.session_state.get("agregat_narx", 2500.0)
        agregat_ornatish = st.session_state.get("agregat_ornatish", 300.0)
        agregat_soni = st.session_state.get("agregat_soni", 1)
        transport_narx = st.session_state.get("transport_narx", 200.0)
        montaj_ishchi = st.session_state.get("montaj_ishchi", 500.0)
        qoshimcha_material = st.session_state.get("qoshimcha_material", 150.0)

        if L and W and H:
            panel_width = float(st.session_state.get("panel_width_m", 1.16))
            
            # Panel miqdorlari
            wall_panels = (math.ceil(L/panel_width) * 2 + math.ceil(W/panel_width) * 2) * 2
            ceiling_panels = math.ceil(L/panel_width) * math.ceil(W/panel_width)
            floor_panels = ceiling_panels if st.session_state.get("pol_bor", False) else 0
            
            panel_area = panel_width * 1.0
            
            # Narxlar
            devor_cost = wall_panels * panel_area * devor_narx
            patalok_cost = ceiling_panels * panel_area * patalok_narx
            pol_cost = floor_panels * panel_area * pol_narx
            panel_jami = devor_cost + patalok_cost + pol_cost
            
            eshik_jami = (eshik_narx + eshik_ornatish) * eshik_soni_input
            agregat_jami = (agregat_narx + agregat_ornatish) * agregat_soni
            qoshimcha_jami = transport_narx + montaj_ishchi + qoshimcha_material
            
            jami = panel_jami + eshik_jami + agregat_jami + qoshimcha_jami
            m2_narx = jami / (L * W) if L * W > 0 else 0
            
            # ===== KICHIK VA IXCHAM XARAJATLAR KARTALARI =====
            st.markdown("""
            <style>
            .cost-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 10px;
                margin: 10px 0;
            }
            .cost-item {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px 14px;
                text-align: center;
            }
            .cost-item .label {
                font-size: 11px;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .cost-item .value {
                font-size: 20px;
                font-weight: 700;
                color: #0f172a;
                margin-top: 2px;
            }
            .cost-item .sub {
                font-size: 10px;
                color: #94a3b8;
                margin-top: 2px;
            }
            .cost-total {
                background: linear-gradient(135deg, #0f172a, #1e293b);
                border-radius: 10px;
                padding: 16px 20px;
                text-align: center;
                color: white;
                margin-top: 12px;
            }
            .cost-total .label {
                font-size: 13px;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .cost-total .value {
                font-size: 32px;
                font-weight: 800;
                color: #fbbf24;
                margin: 4px 0;
            }
            .cost-total .sub {
                font-size: 12px;
                color: #94a3b8;
            }
            .cost-total .sub span {
                color: #fbbf24;
                font-weight: 600;
            }
            .cost-breakdown {
                display: flex;
                justify-content: center;
                gap: 20px;
                flex-wrap: wrap;
                font-size: 12px;
                color: #94a3b8;
                margin-top: 6px;
            }
            .cost-breakdown b {
                color: #e2e8f0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # 4 ta karta
            st.markdown(f"""
           <div class="cost-grid">
                <div class="cost-item" style="border-top: 3px solid #2563eb;">
                    <div class="label">Agregat</div>
                    <div class="value">${agregat_jami:,.0f}</div>
                    <div class="sub">{agregat_soni} ta × ${agregat_narx + agregat_ornatish:,.0f}</div>
                </div>
                <div class="cost-item" style="border-top: 3px solid #f59e0b;">
                    <div class="label">Qo'shimcha</div>
                    <div class="value">${qoshimcha_jami:,.0f}</div>
                    <div class="sub">Tr ${transport_narx:,.0f} · Ish ${montaj_ishchi:,.0f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Jami xarajat
            
            # ===== O'RNATISH NARXLARI (KICHIK) =====
            st.markdown("""
            <style>
            .install-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 8px;
                margin-top: 10px;
            }
            .install-item {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px 12px;
                text-align: center;
            }
            .install-item .label {
                font-size: 10px;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.3px;
            }
            .install-item .value {
                font-size: 16px;
                font-weight: 700;
                color: #0f172a;
            }
            .install-item .sub {
                font-size: 9px;
                color: #94a3b8;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="install-grid">
                <div class="install-item" style="border-left: 3px solid #dc2626;">
                    <div class="label">Agregat o'rnatish</div>
                    <div class="value">${agregat_ornatish:,.0f}</div>
                    <div class="sub">{agregat_soni} ta · ${agregat_narx:,.0f} + ${agregat_ornatish:,.0f}</div>
                </div>
                <div class="install-item" style="border-left: 3px solid #f59e0b;">
                    <div class="label">Montaj ishchi kuchi</div>
                    <div class="value">${montaj_ishchi:,.0f}</div>
                    <div class="sub">Ishchi xarajatlari</div>
                </div>
                <div class="install-item" style="border-left: 3px solid #16a34a;">
                    <div class="label">Transport + Material</div>
                    <div class="value">${transport_narx + qoshimcha_material:,.0f}</div>
                    <div class="sub">Tr ${transport_narx:,.0f} · Mat ${qoshimcha_material:,.0f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.info("Kamera o'lchamlarini kiriting")
        st.subheader("4. Germitika hisobi")
        
        germitika_maydoni_yagona = L * W
        germitika_yagona = calculate_germitika(germitika_maydoni_yagona)
        
        col_g1, col_g2, col_g3, col_g4 = st.columns(4)
        
        with col_g1:
            st.markdown(f"""<div class="metric-box" style="background:#f0fdf4; border-top:4px solid #16a34a;">
                <div class="metric-title"><i class="fas fa-fill-drip"></i>  GERMITIKA</div>
                <div class="metric-value">{germitika_yagona['germitika_soni']} ta</div>
                <div style="font-size:10px;">umumiy soni</div>
            </div>""", unsafe_allow_html=True)
        
        with col_g2:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #3b82f6;">
                <div class="metric-title"><i class="fas fa-calculator"></i>  HISOB</div>
                <div class="metric-value">{germitika_maydoni_yagona:.1f} m²</div>
                <div style="font-size:9px;">Pol maydoni</div>
            </div>""", unsafe_allow_html=True)
        
        with col_g3:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #8b5cf6;">
                <div class="metric-title"><i class="fas fa-info-circle"></i>  ASOS</div>
                <div class="metric-value">50 m² = 24 ta</div>
                <div style="font-size:9px;">Standart me'yor</div>
            </div>""", unsafe_allow_html=True)
        
        st.caption(f" {germitika_yagona['hisob_metodi']} ")
        
        mdata = [("Tashqi hajm",f"{hajm} m3"),("Ichki hajm",f"{inner_hajm} m3"),
                ("Devor maydoni",f"{round(2*(L+W)*H,2)} m2"),
                ("Jami maydon",f"{total_area} m2"),("Jami panellar",f"{all_p} ta")]
        
        if pol_bor and pol_material == "Beton" and beton_volume > 0:
            mdata.append(("Beton hajmi",f"{beton_volume:.2f} m3"))
        
        cols = st.columns(len(mdata))
        for col, (t, v) in zip(cols, mdata):
            with col:
                st.markdown(f'<div class="metric-box"><div class="metric-title">{t}</div>'
                            f'<div class="metric-value">{v}</div></div>', unsafe_allow_html=True)
        
        st.divider()
        st.markdown("###  Hisobot")
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        # Yagona kamera PDF chaqiruvi
        with col_btn1:
            if st.button("📄 PDF Hisobot", use_container_width=True):
                try:
                    # pol_turi ni aniqlash
                    if pol_bor:
                        if pol_material == "Beton":
                            pol_turi_value = f"Beton {beton_qalinligi_mm}mm (M250)"
                        else:
                            pol_turi_value = f"PUR panel {pol_qalin}"
                    else:
                        pol_turi_value = "Mavjud emas"
                    
                    pdf_bytes = generate_pdf_report(
                        project_name=project_name,
                        room_code=room_code,
                        L=L, W=W, H=H,
                        wall_mm=wall_mm,
                        ceil_mm=ceil_mm,
                        floor_mm=floor_mm,
                        pol_bor=pol_bor,
                        d_turi=d_turi,
                        p_turi=p_turi,
                        pol_turi=pol_turi_value,
                        eshik=eshik,
                        agregat=agregat,
                        total_panels=all_p,
                        hajm=hajm,
                        inner_hajm=inner_hajm,
                        total_area=total_area,
                        fig_3d=None,  # 3D figura bo'lmasa None
                        svg_string=sheet_svg  # SVG chizma
                    )
                    
                    st.download_button(
                        "📥 PDF Yuklab olish",
                        data=pdf_bytes,
                        file_name=f"{room_code}_report.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"PDF yaratishda xatolik: {e}")
                    st.exception(e)
       
      

    else:
        multi_L = st.session_state.multi_L_val
        multi_W = st.session_state.multi_W_val
        total_area_multi = st.session_state.multi_area_val
        comp_brand_m = st.session_state.get("multi_comp_brand","Bitzer")
        comp_type_m = st.session_state.get("multi_comp_type","Split-sistema (Nizkotemp)")
        comp_joyi_m = st.session_state.get("multi_comp_joyi","Old")
        
        # Multi-kamera pol sozlamalari
        multi_pol_bor = st.session_state.get("multi_pol_bor", True)
        multi_pol_material = st.session_state.get("multi_pol_material", "PUR panel")
        multi_pol_qalin = st.session_state.get("multi_pol_qalin", "100mm")
        multi_beton_qalinligi_mm = st.session_state.get("multi_beton_qalinligi_mm", 100)
        
        st.info(f"Maydon: {total_area_multi:.1f} m2  |  Kameralar: {n_chambers} ta  |  "
                f"Kompressor: {comp_brand_m} ({comp_type_m})  |  "
                f"Pol: {'Beton ' + str(multi_beton_qalinligi_mm) + 'mm' if multi_pol_material == 'Beton' else 'PUR panel ' + multi_pol_qalin if multi_pol_bor else 'Yo\'q'}")

        if multi_L < 1.0 or multi_W < n_chambers * 0.6:
            st.error("Olcham yetarli emas!")
            st.stop()

        st.subheader("1. 3D Vizualizatsiya (Multi-kamera)")
        
        html_3d = build_3d_multi_html(
            multi_L, multi_W, heights_list, corridor_pos,
            corridor_w if has_corridor else 0, wall_mm_multi,
            door_w_multi, door_h_multi,
            n_total_arg=n_chambers,
            comp_brand=comp_brand_m, comp_type=comp_type_m,
            comp_joyi=comp_joyi_m)
        components.html(html_3d, height=750, scrolling=True)

        n_comp_units = n_chambers
        dir_label = {"Old":"Old devor tashqarisiga (Y-)","Orqa":"Orqa devor tashqarisiga (Y+)",
                    "Chap":"Chap devor tashqarisiga (X-)","O'ng":"Ong devor tashqarisiga (X+)"}
        st.info(f"{n_comp_units} ta kompressor bloki ({comp_brand_m}) -- "
                f"{dir_label.get(comp_joyi_m, comp_joyi_m)} joylashtirilgan. "
                f"HP (qizil) va LP (kuk) quvurlar devor orqali evaporatorlarga ulanadi.")

        st.divider()
        st.subheader("2. Texnik Chizma (Multi-kamera)")
        
        # Pol qalinligini aniqlash
        if multi_pol_bor:
            if multi_pol_material == "Beton":
                floor_mm_multi = multi_beton_qalinligi_mm
            else:
                floor_mm_multi = mm_val(multi_pol_qalin)
        else:
            floor_mm_multi = 0
        
        sheet_svg_multi = make_svg_multi(
            multi_L, multi_W, heights_list, n_chambers,
            corridor_w if has_corridor else 0, corridor_pos,
            wall_mm_multi, door_w_multi, door_h_multi,
            proj_name_multi, code_multi, has_corridor,
            panel_width_m=1.16, ceil_mm=wall_mm_multi, floor_mm=floor_mm_multi, pol_bor=multi_pol_bor)
        draw_svg(sheet_svg_multi, height=3200)

        st.subheader("3. Spetsifikatsiya")
        
        # PANEL HISOBI (Multi-kamera uchun)
        panel_stats = calculate_multi_panels(
            multi_L, multi_W, heights_list, n_chambers, wall_mm_multi,
            panel_width_m=1.16, pol_bor=multi_pol_bor, pol_material=multi_pol_material,
            beton_qalinligi_mm=multi_beton_qalinligi_mm, pol_qalin=multi_pol_qalin,
            has_corridor=has_corridor, corridor_w=corridor_w, corridor_pos=corridor_pos
        )
        
        # ESHIKLAR SONI - FAQAT KAMERALAR UCHUN
        eshiklar_soni = n_chambers
        
        # ASOSIY PANELLAR KARTALARI
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                <div class="metric-title"><i class="fas fa-cubes"></i> JAMI PANELLAR</div>
                <div class="metric-value">{panel_stats['total_panels']} ta</div>
                <div style="font-size:11px; color:#666;">Asosiy panellar</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                <div class="metric-title"><i class="fas fa-border-all"></i> DEVOR PANELLARI</div>
                <div class="metric-value">{panel_stats['wall_panels']} ta</div>
                <div>{panel_stats['total_area']['walls']:.1f} m²</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                <div class="metric-title"><i class="fas fa-home"></i> PATALOK PANELLARI</div>
                <div class="metric-value">{panel_stats['ceiling_panels']} ta</div>
                <div>{panel_stats['total_area']['ceiling']:.1f} m²</div>
            </div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                <div class="metric-title"><i class="fas fa-chalkboard"></i> POL PANELLARI</div>
                <div class="metric-value">{panel_stats['floor_panels']} ta</div>
                <div>{panel_stats['total_area']['floor']:.1f} m²</div>
            </div>""", unsafe_allow_html=True)
        with col5:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                <div class="metric-title"><i class="fas fa-door-open"></i> ESHIKLAR SONI</div>
                <div class="metric-value">{eshiklar_soni} ta</div>
                <div style="font-size:11px;">{n_chambers} ta kamera</div>
            </div>""", unsafe_allow_html=True)
        
        # Beton hisobi (agar beton tanlangan bo'lsa)
        if panel_stats.get('concrete'):
            concrete = panel_stats['concrete']
            st.markdown("---")
            st.markdown("####  Beton poydevor hisobi")
            
            col_b1, col_b2, col_b3, col_b4 = st.columns(4)
            
            with col_b1:
                st.markdown(f"""<div class="metric-box" style="background:#fef3c7; border-top:4px solid #d97706;">
                    <div class="metric-title"><i class="fas fa-weight-hanging"></i> BETON HAJMI</div>
                    <div class="metric-value">{concrete['volume_m3']} m³</div>
                    <div style="font-size:10px;">Maydon: {concrete['area_m2']} m²</div>
                    <div style="font-size:10px;">Qalinligi: {concrete['thickness_mm']} mm</div>
                </div>""", unsafe_allow_html=True)
            
            if concrete.get('materials'):
                mats = concrete['materials']
                with col_b2:
                    st.markdown(f"""<div class="metric-box" style="background:#f8fafc;">
                        <div class="metric-title"><i class="fas fa-truck"></i> SEMENT (M250)</div>
                        <div class="metric-value">{mats['cement_kg']} kg</div>
                        <div style="font-size:10px;">≈ {mats['cement_kg']/50:.1f} xalta</div>
                    </div>""", unsafe_allow_html=True)
                
                with col_b3:
                    st.markdown(f"""<div class="metric-box" style="background:#f8fafc;">
                        <div class="metric-title"><i class="fas fa-mountain"></i> QUM</div>
                        <div class="metric-value">{mats['sand_m3']} m³</div>
                    </div>""", unsafe_allow_html=True)
                
                with col_b4:
                    st.markdown(f"""<div class="metric-box" style="background:#f8fafc;">
                        <div class="metric-title"><i class="fas fa-gem"></i> SHAG'AL</div>
                        <div class="metric-value">{mats['gravel_m3']} m³</div>
                    </div>""", unsafe_allow_html=True)
            
            beton_volume_multi = concrete['volume_m3']
            beton_cost_multi = calculate_beton_cost(beton_volume_multi)
            st.caption(f"🏗️ Beton sinfi: M250 | Taxminiy narx: ~{beton_cost_multi} birlik (material + ishchi)")
        
        # Qo'shimcha tom elementlari
        if 'roof_extra' in panel_stats:
            st.markdown("---")
            st.markdown("#### 🏗️ Qo'shimcha tom elementlari")
            
            re = panel_stats['roof_extra']
            
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                    <div class="metric-title"><i class="fas fa-chart-line"></i> UCHBURCHAK YON DEVORLAR</div>
                    <div class="metric-value">{re['gable_walls']['panels']} ta</div>
                    <div>{re['gable_walls']['area_m2']} m²</div>
                </div>""", unsafe_allow_html=True)
            
            with col_r2:
                st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                    <div class="metric-title"><i class="fas fa-mountain"></i> TIZMA PANELI</div>
                    <div class="metric-value">{re['ridge_cap']['panels']} ta</div>
                    <div>{re['ridge_cap']['area_m2']} m²</div>
                </div>""", unsafe_allow_html=True)
            
            with col_r3:
                st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                    <div class="metric-title"><i class="fas fa-ribbon"></i> FASCA PANELLARI</div>
                    <div class="metric-value">{re['fascia']['panels']} ta</div>
                    <div>{re['fascia']['area_m2']} m²</div>
                </div>""", unsafe_allow_html=True)
            
            st.markdown(f"""<div class="card" style="margin-top: 10px; background:#f8fafc;">
                <b><i class="fas fa-plus-circle"></i> QO'SHIMCHA ELEMENTLAR JAMI:</b><br>
                • <i class="fas fa-cubes"></i> Qo'shimcha PUR panellar: <b>{re['total_extra_panels']} ta</b> (maydon: {re['total_extra_area']} m²)<br>
                • <i class="fas fa-chart-line"></i> <b>Jami (asosiy + qo'shimcha): {panel_stats['total_panels'] + re['total_extra_panels']} ta panel</b><br>
                • <i class="fas fa-door-open"></i> <b>Jami eshiklar: {eshiklar_soni} ta</b>
            </div>""", unsafe_allow_html=True)
        
        # Har bir kamera uchun jadval
        st.markdown("#### <i class='fas fa-table'></i> Har bir kamera bo'yicha panel hisobi", unsafe_allow_html=True)
        
        chamber_table = []
        for ch in panel_stats['chambers']:
            chamber_table.append({
                "Kamera": f"K{ch['id']}",
                "O'lcham (LxWxH)": f"{ch['L']:.1f}x{ch['W']:.1f}x{ch['H']:.1f} m",
                "Devor panellari": f"{ch['wall_panels']} ta",
                "Patalok panellari": f"{ch['ceiling_panels']} ta",
                "Pol panellari": f"{ch['floor_panels']} ta",
                "Eshik": "1 ta",
                "Jami": ch['total']
            })
        
        st.dataframe(chamber_table, use_container_width=True)
            # ========== XARAJATLAR HISOBOTI (GERMITIKA OSTIDA) ==========
        # ============================================================
        st.subheader("Xarajatlar hisoboti")

        # Narxlarni Sidebardan olish
        devor_narx = st.session_state.get("devor_narx", 35.0)
        patalok_narx = st.session_state.get("patalok_narx", 45.0)
        pol_narx = st.session_state.get("pol_narx", 40.0)
        eshik_narx = st.session_state.get("eshik_narx", 280.0)
        eshik_ornatish = st.session_state.get("eshik_ornatish", 50.0)
        eshik_soni_input = st.session_state.get("eshik_soni_input", 1)
        agregat_narx = st.session_state.get("agregat_narx", 2500.0)
        agregat_ornatish = st.session_state.get("agregat_ornatish", 300.0)
        agregat_soni = st.session_state.get("agregat_soni", 1)
        transport_narx = st.session_state.get("transport_narx", 200.0)
        montaj_ishchi = st.session_state.get("montaj_ishchi", 500.0)
        qoshimcha_material = st.session_state.get("qoshimcha_material", 150.0)

        if L and W and H:
            panel_width = float(st.session_state.get("panel_width_m", 1.16))
            
            # Panel miqdorlari
            wall_panels = (math.ceil(L/panel_width) * 2 + math.ceil(W/panel_width) * 2) * 2
            ceiling_panels = math.ceil(L/panel_width) * math.ceil(W/panel_width)
            floor_panels = ceiling_panels if st.session_state.get("pol_bor", False) else 0
            
            panel_area = panel_width * 1.0
            
            # Narxlar
            devor_cost = wall_panels * panel_area * devor_narx
            patalok_cost = ceiling_panels * panel_area * patalok_narx
            pol_cost = floor_panels * panel_area * pol_narx
            panel_jami = devor_cost + patalok_cost + pol_cost
            
            eshik_jami = (eshik_narx + eshik_ornatish) * eshik_soni_input
            agregat_jami = (agregat_narx + agregat_ornatish) * agregat_soni
            qoshimcha_jami = transport_narx + montaj_ishchi + qoshimcha_material
            
            jami = panel_jami + eshik_jami + agregat_jami + qoshimcha_jami
            m2_narx = jami / (L * W) if L * W > 0 else 0
            
            # ===== XARAJATLAR KARTALARI =====
            col_x1, col_x2, col_x3, col_x4 = st.columns(4)
            
            with col_x1:
                st.markdown(f"""
                <div class="metric-box" style="background:#f8fafc; border-top:4px solid #0f172a;">
                    <div class="metric-title">PANEL NARXI</div>
                    <div class="metric-value">${panel_jami:,.0f}</div>
                    <div style="font-size:10px;">Devor: ${devor_cost:,.0f}</div>
                    <div style="font-size:10px;">Patalok: ${patalok_cost:,.0f}</div>
                    <div style="font-size:10px;">Pol: ${pol_cost:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_x2:
                st.markdown(f"""
                <div class="metric-box" style="background:#f8fafc; border-top:4px solid #dc2626;">
                    <div class="metric-title">ESHIK NARXI</div>
                    <div class="metric-value">${eshik_jami:,.0f}</div>
                    <div style="font-size:10px;">{eshik_soni_input} ta × ${eshik_narx + eshik_ornatish:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_x3:
                st.markdown(f"""
                <div class="metric-box" style="background:#f8fafc; border-top:4px solid #2563eb;">
                    <div class="metric-title">AGREGAT NARXI</div>
                    <div class="metric-value">${agregat_jami:,.0f}</div>
                    <div style="font-size:10px;">{agregat_soni} ta × ${agregat_narx + agregat_ornatish:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_x4:
                st.markdown(f"""
                <div class="metric-box" style="background:#f8fafc; border-top:4px solid #f59e0b;">
                    <div class="metric-title">QO'SHIMCHA</div>
                    <div class="metric-value">${qoshimcha_jami:,.0f}</div>
                    <div style="font-size:10px;">Transport: ${transport_narx:,.0f}</div>
                    <div style="font-size:10px;">Ishchi: ${montaj_ishchi:,.0f}</div>
                    <div style="font-size:10px;">Material: ${qoshimcha_material:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # ===== JAMI XARAJAT =====
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
                        padding: 25px; border-radius: 15px; text-align: center; color: white; margin-top: 15px;">
                <h3 style="margin: 0; color: #fbbf24;">JAMI XARAJAT</h3>
                <p style="font-size: 42px; font-weight: bold; margin: 10px 0; color: #fbbf24;">${jami:,.0f}</p>
                <hr style="border-color: #fbbf24; margin: 8px 50px;">
                <div style="display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; font-size: 14px;">
                    <span>Panel: <b>${panel_jami:,.0f}</b></span>
                    <span>Eshik: <b>${eshik_jami:,.0f}</b></span>
                    <span>Agregat: <b>${agregat_jami:,.0f}</b></span>
                    <span>Qo'shimcha: <b>${qoshimcha_jami:,.0f}</b></span>
                </div>
                <p style="margin: 10px 0; font-size: 18px; color: #fbbf24;">
                    1 m² narxi: ${m2_narx:,.0f} / m²
                </p>
                <p style="margin: 5px 0; font-size: 13px; color: #94a3b8;">
                    Jami panellar: {wall_panels + ceiling_panels + floor_panels} ta
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # ===== O'RNATISH NARXLARI (AGREGAT, ISHCHI, QO'SHIMCHA) =====
            st.markdown("---")
            st.markdown("#### O'rnatish va qo'shimcha xarajatlar")

            col_o1, col_o2, col_o3 = st.columns(3)
            
            with col_o1:
                st.markdown(f"""
                <div class="metric-box" style="background:#fef2f2; border-top:4px solid #dc2626;">
                    <div class="metric-title">AGREGAT O'RNATISH</div>
                    <div class="metric-value">${agregat_ornatish:,.0f}</div>
                    <div style="font-size:11px;">{agregat_soni} ta agregat</div>
                    <div style="font-size:10px;">${agregat_narx:,.0f} + ${agregat_ornatish:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_o2:
                st.markdown(f"""
                <div class="metric-box" style="background:#fefce8; border-top:4px solid #f59e0b;">
                    <div class="metric-title">MONTAJ ISHCHI KUCHI</div>
                    <div class="metric-value">${montaj_ishchi:,.0f}</div>
                    <div style="font-size:11px;">Ishchi xarajatlari</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_o3:
                st.markdown(f"""
                <div class="metric-box" style="background:#f0fdf4; border-top:4px solid #16a34a;">
                    <div class="metric-title">TRANSPORT + MATERIAL</div>
                    <div class="metric-value">${transport_narx + qoshimcha_material:,.0f}</div>
                    <div style="font-size:11px;">Transport: ${transport_narx:,.0f}</div>
                    <div style="font-size:10px;">Material: ${qoshimcha_material:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.info("Kamera o'lchamlarini kiriting")
        st.subheader("4. Germitika hisobi")
        
        germitika_maydoni_multi = multi_L * multi_W
        germitika_multi = calculate_germitika(germitika_maydoni_multi)
        
        col_g1, col_g2, col_g3 = st.columns(3)
        
        with col_g1:
            st.markdown(f"""<div class="metric-box" style="background:#f0fdf4; border-top:4px solid #16a34a;">
                <div class="metric-title"><i class="fas fa-fill-drip"></i> GERMITIKA</div>
                <div class="metric-value">{germitika_multi['germitika_soni']} ta</div>
            </div>""", unsafe_allow_html=True)
        
        with col_g2:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #3b82f6;">
                <div class="metric-title"><i class="fas fa-calculator"></i> HISOB</div>
                <div class="metric-value">{germitika_maydoni_multi:.1f} m²</div>
                <div style="font-size:9px;">Pol maydoni</div>
            </div>""", unsafe_allow_html=True)
        
        with col_g3:
            st.markdown(f"""<div class="metric-box" style="background:#f8fafc; border-top:4px solid #8b5cf6;">
                <div class="metric-title"><i class="fas fa-info-circle"></i> ASOS</div>
                <div class="metric-value">50 m² = 24 ta</div>
                <div style="font-size:9px;">Standart me'yor</div>
            </div>""", unsafe_allow_html=True)
        
        st.caption(f" {germitika_multi['hisob_metodi']} ")
        st.divider()

    
        st.markdown(f"""<div class='card'>
        <b>⚙️ Kompressor bloklari</b><br>
        Soni: <b>{n_comp_units} ta</b> &nbsp;|&nbsp;
        Brend: <b>{comp_brand_m}</b> &nbsp;|&nbsp;
        Tur: <b>{comp_type_m}</b><br>
        Joylashuvi: <b>{dir_label.get(comp_joyi_m, comp_joyi_m)}</b> -- beton poydevor ustiga<br>
        Ulanish: HP (qizil) + LP (kuk) refrigerant quvurlari devor orqali evaporatorlarga
        </div>""", unsafe_allow_html=True)
        
        st.divider()
        st.markdown("###  Hisobot")

        col_btn1, col_btn2, col_btn3 = st.columns(3)  # 4 ta emas, 3 ta qilib

        with col_btn1:
            st.download_button("🏗️ Chizma SVG", data=sheet_svg_multi.encode('utf-8'),
                            file_name=f"{code_multi}_drawing.svg", mime="image/svg+xml")

        with col_btn2:
            if st.button("📱 Telegramga yuborish", use_container_width=True):
                # Pol ma'lumotini aniqlash
                if multi_pol_bor:
                    if multi_pol_material == "Beton":
                        pol_info = f"Beton {floor_mm_multi}mm"
                    else:
                        pol_info = "PUR panel"
                else:
                    pol_info = "Yo'q"
                
                tg_text = (f"<b>MULTI-KAMERA</b>\n"
                        f"<b>{proj_name_multi}</b> ({code_multi})\n"
                        f"{multi_L:.1f}x{multi_W:.1f}m | {n_chambers} kamera\n"
                        f"Panellar: {panel_stats['total_panels']} ta\n"
                        f"Pol: {pol_info}\n"
                        f"Kompressor: {n_comp_units}x{comp_brand_m}")
                ok, msg = send_tg(tg_text)
                st.success(msg) if ok else st.error(msg)

        with col_btn3:
            if st.button("📄 PDF Hisobot", use_container_width=True):
                try:
                    pdf_bytes = generate_pdf_report(
                        proj_name_multi, code_multi,
                        multi_L, multi_W, max(heights_list),
                        wall_mm_multi, wall_mm_multi, floor_mm_multi if multi_pol_bor else 0,
                        multi_pol_bor, "PUR", "PUR", multi_pol_material if multi_pol_bor else "Mavjud emas",
                        "Standart", comp_type_m,
                        panel_stats['total_panels'],
                        multi_L * multi_W * max(heights_list),
                        multi_L * multi_W * max(heights_list) * 0.85,
                        multi_L * multi_W,
                        fig_3d=None,
                        ai_result=st.session_state.ai_result)
                    st.download_button("📥 Yuklab olish", data=pdf_bytes,
                                    file_name=f"{code_multi}_report.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"PDF yaratishda xatolik: {e}")
# test.py faylining eng oxiriga qo'shing
if __name__ == "__main__":
    import sys
    from streamlit.web import cli as stcli
    
    # Agar .exe sifatida ishga tushirilgan bo'lsa
    if getattr(sys, 'frozen', False):
        # .exe dan ishga tushganda
        sys.argv = ["streamlit", "run", __file__, "--server.headless", "true", "--browser.gatherUsageStats", "false"]
        sys.exit(stcli.main())