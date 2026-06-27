
import math
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, Polygon, Circle, Arc
import numpy as np
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union
import io
from mpl_toolkits.mplot3d import Axes3D
# ============================================================
# PROFIL MA'LUMOTLARI (GOST asosida) 
# ============================================================
LSTK_PROFILES = {
    "Ustun": "Profil 100x100x4 mm",
    "Ferma": "Profil 60x60x3 mm",
    "Progon": "Profil 80x40x3 mm",
}
# 1. Dvuhtavrlar (GOST R 57837-2017) - Ustunlar uchun
GOST_COLUMNS_KG_M = {
    "Dvuhtavr 20B1": 22.4,
    "Dvuhtavr 25B1": 25.7,
    "Dvuhtavr 30B1": 32.9,
    "Dvuhtavr 35B1": 41.4,
    "Dvuhtavr 40B1": 48.1,
    "Dvuhtavr 50B1": 64.8,
}

# 2. Kvadrat Profil Trubalar (GOST 8639-82) - Fermalar uchun
GOST_SQUARE_TRUSS_KG_M = {
    "Profil 60x60x3 mm": 5.25,
    "Profil 60x60x4 mm": 6.78,
    "Profil 80x80x3 mm": 7.13,
    "Profil 80x80x4 mm": 9.11,
    "Profil 100x100x3 mm": 9.02,
    "Profil 100x100x4 mm": 11.62,
    "Profil 120x120x4 mm": 14.13,
    "Profil 120x120x5 mm": 17.31,
    "Profil 140x140x5 mm": 20.45,
    "Profil 160x160x5 mm": 23.59,
}

# 3. Togri Tortburchak Profil Trubalar (GOST 8645-68) - Progonlar uchun
GOST_RECT_PURLIN_KG_M = {
    "Profil 80x40x3 mm": 5.02,
    "Profil 80x40x4 mm": 6.47,
    "Profil 100x50x3 mm": 6.67,
    "Profil 100x50x4 mm": 8.52,
    "Profil 120x60x3 mm": 8.05,
    "Profil 120x60x4 mm": 10.40,
    "Profil 140x60x4 mm": 11.65,
    "Profil 160x80x4 mm": 14.16,
}

# 4. Shvellerlar (GOST 8240-97) - Bog'lamalar uchun
GOST_CHANNEL_KG_M = {
    "Shveller 10P": 8.59,
    "Shveller 12P": 10.40,
    "Shveller 14P": 12.30,
    "Shveller 16P": 14.20,
    "Shveller 18P": 16.30,
    "Shveller 20P": 18.40,
    "Shveller 24P": 24.00,
}
def compute_screw_connections(metal_kg):
    """LSTK uchun vintli birikma hisobi"""
    screws_kg = metal_kg * 0.015  # 1.5% vintlar og'irligi
    screws_count = int(metal_kg / 2.5)  # Har 2.5 kg ga 1 vint
    return {
        "screws_kg": round(screws_kg, 1),
        "screws_count": screws_count,
        "screws_cost": screws_count * 0.5  # $0.5 dona
    }
def get_profile_weight(profile_type, profile_name):
    """Profil turi va nomiga qarab kg/m og'irlikni qaytaradi"""
    if profile_type == "column":
        return GOST_COLUMNS_KG_M.get(profile_name, 32.9)
    elif profile_type == "truss":
        return GOST_SQUARE_TRUSS_KG_M.get(profile_name, 11.62)
    elif profile_type == "purlin":
        return GOST_RECT_PURLIN_KG_M.get(profile_name, 8.52)
    elif profile_type == "bracing":
        return GOST_CHANNEL_KG_M.get(profile_name, 14.20)
    return 15.0

def get_profile_list(profile_type):
    """Profil turiga qarab mavjud profillar ro'yxatini qaytaradi"""
    if profile_type == "column":
        return list(GOST_COLUMNS_KG_M.keys())
    elif profile_type == "truss":
        return list(GOST_SQUARE_TRUSS_KG_M.keys())
    elif profile_type == "purlin":
        return list(GOST_RECT_PURLIN_KG_M.keys())
    elif profile_type == "bracing":
        return list(GOST_CHANNEL_KG_M.keys())
    return []
# ========== KONSTRUKSIYA MA'LUMOTLARI ==========
CONSTRUCTION_DEFAULTS = {
    "construction_type": "Angar",
    "construction_name": "Yangi Angar Loyihasi",
    "construction_code": f"ANG-{datetime.now().strftime('%Y%m%d')}",
    "construction_L": 30.0,
    "construction_W": 15.0,
    "construction_H": 7.5,
    "construction_roof_pitch": 12.0,
    "construction_floors": 1,
    "construction_wall_type": "Sendvich Panel",
    "construction_wall_thickness": 100,
    "construction_floor_type": "Sanoat Betoni",
    "construction_roof_type": "Sendvich panel",
    "construction_window_count": 6,
    "construction_window_width": 2.5,
    "construction_window_height": 2.0,
    "construction_window_spacing": 0.0,
    "construction_door_count": 1,
    "construction_door_width": 12.0,
    "construction_door_height": 6.5,
    "construction_heating": "Yoq",
    "construction_ventilation": "Tabiiy",
    "construction_electricity": "Kuchaytirilgan",
    "construction_plumbing": "Bor",
    "construction_region": "Toshkent",
    "construction_seismic_zone": 8,
    "construction_snow_load": 50.0,
    "construction_wind_load": 38.0,
}

construction_types = {
    "Angar": {
        "color": "#37474F",
        "description": "Metall karkasli angar, samolyotlar yoki katta texnika uchun",
        "base_price": 280,
        "min_span": 12,
        "max_span": 80,
        "typical_height": 8,
    },
    "Ombor": {
        "color": "#455A64",
        "description": "Ko'p maqsadli saqlash ombori",
        "base_price": 250,
        "min_span": 10,
        "max_span": 60,
        "typical_height": 6,
    },
    "Ishlab chiqarish binosi": {
        "color": "#546E7A",
        "description": "Zavod sexi yoki ishlab chiqarish maydoni",
        "base_price": 320,
        "min_span": 15,
        "max_span": 100,
        "typical_height": 10,
    },
    "Avtoservis": {
        "color": "#607D8B",
        "description": "Avtomobil diagnostikasi va ta'mirlash ustaxonasi",
        "base_price": 230,
        "min_span": 8,
        "max_span": 30,
        "typical_height": 5,
    },
    "Sport zali": {
        "color": "#78909C",
        "description": "Yopiq sport maydonchasi",
        "base_price": 350,
        "min_span": 20,
        "max_span": 60,
        "typical_height": 12,
    },
    "Savdo markazi": {
        "color": "#90A4AE",
        "description": "Kichik va o'rta savdo paviloni",
        "base_price": 400,
        "min_span": 15,
        "max_span": 50,
        "typical_height": 6,
    }
}

wall_materials = {
    "Sendvich Panel": {
        "qalinlik": [50, 80, 100, 120, 150, 200],
        "narx_m2": 35,
        "R_value": 3.5,
        "weight_kg_m2": 12,
        "fire_resistance": "B2",
        "colors": ["RAL9002", "RAL9003", "RAL5010", "RAL3000", "RAL6005"]
    },
    "Profnastil": {
        "qalinlik": [0.5, 0.7, 0.8, 1.0],
        "narx_m2": 12,
        "R_value": 0.5,
        "weight_kg_m2": 5,
        "fire_resistance": "A1",
        "colors": ["RAL9006", "RAL8017", "RAL5005"]
    },
    "SIP Panel": {
        "qalinlik": [100, 150, 200],
        "narx_m2": 55,
        "R_value": 5.2,
        "weight_kg_m2": 15,
        "fire_resistance": "B1",
        "colors": ["RAL9010", "RAL1015"]
    },
}

floor_materials = {
    "Sanoat Betoni": {"narx_m2": 45, "qalinlik": 150, "yuklama": 5000},
    "Epoksi Pol": {"narx_m2": 65, "qalinlik": 3, "yuklama": 3000},
    "Beton plita": {"narx_m2": 55, "qalinlik": 200, "yuklama": 8000},
    "Asfalt": {"narx_m2": 35, "qalinlik": 50, "yuklama": 2000},
}

roof_materials = {
    "Sendvich panel": {"narx_m2": 45, "weight_kg_m2": 13, "R_value": 4.0, "xizmat_muddati": 25},
    "Metall profil": {"narx_m2": 28, "weight_kg_m2": 5, "R_value": 0.3, "xizmat_muddati": 20},
    "Membrana tom": {"narx_m2": 55, "weight_kg_m2": 3, "R_value": 6.0, "xizmat_muddati": 35},
}

# Metall elementlarning kg/metr og'irlik standartlari (faqat og'irlik
# hisoblash uchun ishlatiladi - narxlar endi foydalanuvchi tomonidan
# input orqali kiritiladi)
METALL_STANDARDS = {
    "ustun_kg_m": 32.5,         # Ustunlar (kolonnalar) - I-bolka
    "tosin_kg_m": 24.5,         # Gorizontal tosinlar / rigellar
    "truss_kg_m": 18.5,         # Fermalar (Warren truss)
    "longitudinal_kg_m": 24.5,  # Uzunasiga tosinlar
}

SEISMIC_ZONES = {
    7: {"coefficient": 0.1, "qoshimcha_narx": 0.05},
    8: {"coefficient": 0.2, "qoshimcha_narx": 0.10},
    9: {"coefficient": 0.3, "qoshimcha_narx": 0.15},
}

WIND_LOADS = {
    "A": {"tezlik": 25, "bosim": 0.38},
    "B": {"tezlik": 30, "bosim": 0.48},
    "C": {"tezlik": 38, "bosim": 0.60},
}

# ---------------------------------------------------------------------------
# TUPROQ MA'LUMOTLARI (SNiP 2.02.01-83* "Osnovaniya zdaniy i sooruzheniy"
# asosidagi taxminiy normativ qarshilik R0 qiymatlari - bular umumiy
# ma'lumotnoma qiymatlari, ANIQ loyihalashda geologik qidiruv natijalari
# (burg'ulash, laborator tahlil) va GOST 25100 bo'yicha klassifikatsiya kerak)
# ---------------------------------------------------------------------------
SOIL_TYPES = {
    "Qoyali tog' jinsi": {
        "R0_kPa": 600, "muzlash_tasiri": False,
        "tavsif": "Amaliy deformatsiyalanmaydi - eng ishonchli tabiiy asos",
        "fundament_tavsiyasi": "Yengil lentasimon poydevor yetarli",
    },
    "Yirik shag'al / qumli-shag'al": {
        "R0_kPa": 500, "muzlash_tasiri": False,
        "tavsif": "Yuqori zichlikdagi donador tuproq, yaxshi drenaj",
        "fundament_tavsiyasi": "Standart lentasimon/ustunli poydevor",
    },
    "Zich qum": {
        "R0_kPa": 400, "muzlash_tasiri": False,
        "tavsif": "Zich joylashgan qum",
        "fundament_tavsiyasi": "Standart lentasimon/ustunli poydevor",
    },
    "O'rta zichlikdagi qum": {
        "R0_kPa": 300, "muzlash_tasiri": False,
        "tavsif": "O'rta zichlikdagi qum - eng ko'p uchraydigan holat",
        "fundament_tavsiyasi": "Standart ustunli poydevor",
    },
    "Qattiq gil": {
        "R0_kPa": 300, "muzlash_tasiri": True,
        "tavsif": "Qattiq konsistensiyali gilli tuproq",
        "fundament_tavsiyasi": "Standart ustunli poydevor, muzlash chizig'idan past",
    },
    "Yarim qattiq gil": {
        "R0_kPa": 250, "muzlash_tasiri": True,
        "tavsif": "O'rta qattiqlikdagi gil",
        "fundament_tavsiyasi": "Biroz kengaytirilgan poydevor tagligi",
    },
    "Bo'sh (govak) qum": {
        "R0_kPa": 150, "muzlash_tasiri": False,
        "tavsif": "Past zichlikdagi qum, cho'kish xavfi mavjud",
        "fundament_tavsiyasi": "Kengaytirilgan taglik yoki tuproqni zichlash tavsiya etiladi",
    },
    "Yumshoq plastik gil": {
        "R0_kPa": 120, "muzlash_tasiri": True,
        "tavsif": "Past mustahkamlikdagi yumshoq gil",
        "fundament_tavsiyasi": "Plitali poydevor yoki qoziqli fundament ko'rib chiqilsin",
    },
    "Lyoss / lyossimon (cho'kuvchan)": {
        "R0_kPa": 180, "muzlash_tasiri": False,
        "tavsif": "O'zbekistonda keng tarqalgan - suv yutganda keskin cho'kishi mumkin (просадочный grunt)",
        "fundament_tavsiyasi": "Gidroizolyatsiya SHART, tuproqni zichlash yoki qoziqli fundament",
    },
    "Torfli / botqoq tuproq": {
        "R0_kPa": 50, "muzlash_tasiri": True,
        "tavsif": "Organik tuproq, yuqori darajada deformatsiyalanuvchi",
        "fundament_tavsiyasi": "Qoziqli (svayali) fundament SHART, yuzaki poydevor tavsiya etilmaydi",
    },
}

# Qor mintaqalari - O'zbekiston sharoitiga moslashtirilgan taxminiy qiymatlar
# (SNiP 2.01.07-85* mantig'i, lekin Markaziy Osiyo iqlimiga moslashtirilgan -
# rasmiy loyihada KMK 2.01.07-96 dagi tasdiqlangan qiymatdan foydalanilsin)
SNOW_REGIONS = {
    "I - tekislik (Toshkent, Farg'ona, Buxoro, Surxon)": 0.5,
    "II - past tog' oldi (Samarqand, Jizzax)": 0.7,
    "III - tog' oldi mintaqasi": 1.0,
    "IV - tog'li hudud (Chimyon, Zomin va sh.k.)": 1.6,
}

# Seysmik statik usul koeffitsiyentlari (KMK 2.01.03-96 soddalashtirilgan
# statik usuliga asoslangan)
SEISMIC_A_COEFF = {7: 0.10, 8: 0.20, 9: 0.40}   # A - seysmik intensivlik koeffitsiyenti
SEISMIC_K1_STEEL_FRAME = 0.25                    # Bog'lovchili po'lat karkas (yuqori plastiklik)
SEISMIC_PSI_SNOW = 0.5                           # Seysmik massaga qor yukining qo'shiladigan ulushi

STEEL_GRADE = {
    "name": "C235 / St3 (oddiy konstruksiya po'lati)",
    "Ry_MPa": 230,   # hisobiy qarshilik, gamma_m material koeffitsiyenti hisobga olingan
}

FOUNDATION_FREEZING_DEPTH_M = 0.8   # Toshkent mintaqasi uchun taxminiy normativ muzlash chuqurligi


# ---------------------------------------------------------------------------
# Yordamchi: ustunlar joylashuvini hisoblash (3D va material hisob-kitobida
# bir xil natija beradigan yagona manba)
# ---------------------------------------------------------------------------
def compute_column_layout(L, W, column_spacing=8.5):
    """
    Ustunlar joylashuvini hisoblash - foydalanuvchi tomonidan kiritilgan oralig' bilan
    """
    col_spacing_x = column_spacing  # 🔽 Endi parametr sifatida qabul qiladi
    n_cols_x = max(2, int(L / col_spacing_x) + 1)
    actual_spacing_x = L / (n_cols_x - 1) if n_cols_x > 1 else L

    col_spacing_z = column_spacing  # 🔽 Kenglik bo'ylab ham
    n_cols_z = max(2, int(W / col_spacing_z) + 1)
    actual_spacing_z = W / (n_cols_z - 1) if n_cols_z > 1 else W

    return {
        "n_cols_x": n_cols_x,
        "n_cols_z": n_cols_z,
        "spacing_x": actual_spacing_x,
        "spacing_z": actual_spacing_z,
        "column_spacing": column_spacing,  # 🔽 Qo'shimcha
    }
# compute_metal_quantities funksiyasidan OLDIN qo'shing (taxminan 200-qator atrofida)

def get_construction_system_factors(system_type, L, W, H):
    if system_type == "LSTK (Yengil Po'lat)":
        return {
            "weight_multiplier": 1.0,
            "column_kg_m": 11.62,      # ← GOST 8639-82, Profil 100x100x4 mm
            "beam_kg_m": 8.52,         # ← GOST 8645-68, Profil 100x50x4 mm
            "truss_kg_m": 5.25,        # ← GOST 8639-82, Profil 60x60x3 mm
            "bracing_kg_m": 12.30,     # ← GOST 8240-97, Shveller 14P
            "connection_type": "screwed",
            "max_span": 30,
            "service_life": 35,
            "corrosion_protection": True,
        }
    else:  # LMK
        return {
            "weight_multiplier": 1.0,
            "column_kg_m": 32.5,
            "beam_kg_m": 24.5,
            "truss_kg_m": 18.5,
            "bracing_kg_m": 14.0,
            "connection_type": "welded",
            "max_span": 80,
            "service_life": 50,
            "corrosion_protection": False,
        }
def compute_metal_quantities(L, W, H, roof_pitch, column_spacing=8.5, system_type="LMK (Yengil Metall)"):
    """
    Metall miqdorlarini hisoblash - LMK/LSTK uchun
    """
    factors = get_construction_system_factors(system_type, L, W, H)
    
    pitch_rad = math.radians(roof_pitch)
    layout = compute_column_layout(L, W, column_spacing)
    n_cols_x = layout["n_cols_x"]
    n_cols_z = layout["n_cols_z"]
    prolyot = W
    
    # ===== 1) USTUNLAR =====
    total_columns = (n_cols_x * 2) + (max(0, n_cols_z - 2) * 2)
    column_meters = total_columns * H
    
    # Balandlik koeffitsiyenti
    if H <= 4:
        height_factor = 1.0
    elif H <= 6:
        height_factor = 1.05
    elif H <= 8:
        height_factor = 1.10
    elif H <= 10:
        height_factor = 1.20
    else:
        height_factor = 1.35
    
    # 🔽 TO'G'RI - factors dan to'g'ridan-to'g'ri olamiz
    base_kg_m = factors["column_kg_m"]
    column_kg_m = base_kg_m * height_factor
    column_kg = column_meters * column_kg_m
    column_qoshimcha = total_columns * 45 * height_factor * factors["weight_multiplier"]
    
    # ===== 2) TOSINLAR =====
    beam_meters = 2 * (L + W) * 1.5 * factors["weight_multiplier"]
    beam_kg_m = factors["beam_kg_m"]  # 🔽 QO'SHIMCHA KOEFFITSIYENT YO'Q
    beam_kg = beam_meters * beam_kg_m
    
    # ===== 3) FERMALAR =====
    truss_count = n_cols_x
    if roof_pitch > 0:
        slope = (W / 2) / math.cos(pitch_rad)
        truss_length = slope * 2
    else:
        truss_length = W
    
    if prolyot <= 12:
        truss_mult = 1.8
    elif prolyot <= 18:
        truss_mult = 2.0
    elif prolyot <= 25:
        truss_mult = 2.2
    elif prolyot <= 30:
        truss_mult = 2.4
    else:
        truss_mult = 2.6
    
    truss_meters = truss_count * truss_length * truss_mult
    truss_kg_m = factors["truss_kg_m"]  # 🔽 QO'SHIMCHA KOEFFITSIYENT YO'Q
    truss_kg = truss_meters * truss_kg_m
    truss_qoshimcha = truss_count * 60 * factors["weight_multiplier"]
    
    # ===== 4) PROGONLAR =====
    purlin_result = compute_purlins(L, W, H, roof_pitch, 
                                   system_type=system_type,
                                   factors=factors)
    longitudinal_meters = purlin_result["total_m"]
    longitudinal_kg = purlin_result["total_kg"]
    
    # ===== 5) BOG'LAMALAR =====
    vert_bog_m = n_cols_x * H * 0.6 * factors["weight_multiplier"]
    goriz_bog_m = (L + W) * 0.6 * factors["weight_multiplier"]
    seysmik_m = (L + W) * 0.4 * factors["weight_multiplier"]
    
    jami_boglamalar_m = vert_bog_m + goriz_bog_m + seysmik_m
    bog_kg_m = factors["bracing_kg_m"]  # 🔽 QO'SHIMCHA KOEFFITSIYENT YO'Q
    jami_boglamalar_kg = jami_boglamalar_m * bog_kg_m
    
    # ===== 6) ASOSIY METALL =====
    asosiy_metal_kg = (column_kg + column_qoshimcha + beam_kg + truss_kg + 
                        truss_qoshimcha + longitudinal_kg + jami_boglamalar_kg)
    
    # ===== 7) BIRIKMA DETALLARI =====
    if "LSTK" in system_type:
        birikma_k = 0.02
    else:
        birikma_k = 0.04
    
    birikma_kg = asosiy_metal_kg * birikma_k
    
    # ===== 8) JAMI =====
    total_metal_kg = asosiy_metal_kg + birikma_kg
    
    return {
        "total_columns": total_columns,
        "truss_count": truss_count,
        "column_meters": round(column_meters, 1),
        "column_kg": round(column_kg + column_qoshimcha, 1),
        "column_tonna": round((column_kg + column_qoshimcha) / 1000, 3),
        "beam_meters": round(beam_meters, 1),
        "beam_kg": round(beam_kg, 1),
        "beam_tonna": round(beam_kg / 1000, 3),
        "truss_meters": round(truss_meters, 1),
        "truss_kg": round(truss_kg + truss_qoshimcha, 1),
        "truss_tonna": round((truss_kg + truss_qoshimcha) / 1000, 3),
        "longitudinal_meters": round(longitudinal_meters, 1),
        "longitudinal_kg": round(longitudinal_kg, 1),
        "longitudinal_tonna": round(longitudinal_kg / 1000, 3),
        "boglamalar_kg": round(jami_boglamalar_kg, 1),
        "boglamalar_tonna": round(jami_boglamalar_kg / 1000, 3),
        "birikma_kg": round(birikma_kg, 1),
        "birikma_tonna": round(birikma_kg / 1000, 3),
        "total_metal_kg": round(total_metal_kg, 1),
        "total_metal_tonna": round(total_metal_kg / 1000, 3),
        "column_height_factor": height_factor,
        "column_base_kg_m": base_kg_m,
        "column_actual_kg_m": round(column_kg_m, 1),
        "system_type": system_type,
        "service_life": factors["service_life"],
        "connection_type": factors["connection_type"],
        "corrosion_protection": factors["corrosion_protection"],
    }
# 1. PROFIL TANLASH FUNKSIYASI - compute_metal_quantities funksiyasidan OLDIN qo'shiladi
# ============================================================

def select_optimal_profile(load_kg, span_m, height_m, profile_type="column"):
    """
    Yuk va o'lchamlarga qarab optimal metall profilni tanlaydi
    """
    profiles = {
        "column": {
            "HEA 240": {"h": 230, "bf": 240, "tw": 7.5, "tf": 12.0, "A": 76.8, "Ix": 7763, "Wx": 675, "weight": 60.3},
            "HEA 260": {"h": 250, "bf": 260, "tw": 7.5, "tf": 12.5, "A": 86.8, "Ix": 10453, "Wx": 836, "weight": 68.1},
            "IPE300": {"h": 300, "bf": 150, "tw": 7.1, "tf": 10.7, "A": 53.8, "Ix": 8356, "Wx": 557, "weight": 42.2},
            "IPE330": {"h": 330, "bf": 160, "tw": 7.5, "tf": 11.5, "A": 62.6, "Ix": 11770, "Wx": 713, "weight": 49.1},
            "HEA300": {"h": 290, "bf": 300, "tw": 8.5, "tf": 14.0, "A": 112.5, "Ix": 18263, "Wx": 1260, "weight": 88.3},
        },
        "beam": {
            "IPE 270": {"h": 270, "bf": 135, "tw": 6.6, "tf": 10.2, "A": 45.9, "Ix": 5790, "Wx": 429, "weight": 36.1},
            "IPE300": {"h": 300, "bf": 150, "tw": 7.1, "tf": 10.7, "A": 53.8, "Ix": 8356, "Wx": 557, "weight": 42.2},
            "IPE330": {"h": 330, "bf": 160, "tw": 7.5, "tf": 11.5, "A": 62.6, "Ix": 11770, "Wx": 713, "weight": 49.1},
        }
    }
    
    # Yuk va prolyotga qarab talab qilinadigan Wx ni hisoblash
    # σ = M/W ≤ Ry → W ≥ M/Ry
    # Yuk kg da berilgan, uni Nyutonga aylantiramiz va maksimal momentni hisoblaymiz
    M_max = (load_kg * 9.81 * span_m**2) / 8  # Oddiy balka uchun maksimal moment (Nm da)
    Ry = 230  # MPa - C235 po'lat uchun (hisobiy qarshilik)
    required_Wx = (M_max / Ry) * 1000  # mm³ dan sm³ ga o'tkazish uchun *1000
    
    # Profillarni talab qilingan Wx ga qarab saralash va birinchi yetarlisini tanlash
    selected = None
    # Avval kolonna profillarini tekshiramiz
    col_profiles = profiles.get(profile_type, profiles["column"])
    for name, props in col_profiles.items():
        if props["Wx"] >= required_Wx:
            selected = name
            break
    
    if not selected:
        # Hech qaysi profil yetarli bo'lmasa, eng kuchli (eng katta Wx li) profilni tanlaymiz
        selected = max(col_profiles.items(), key=lambda x: x[1]["Wx"])[0][0]
    
    return {
        "profile": selected,
        "properties": col_profiles[selected],
        "required_Wx": round(required_Wx, 1),
        "weight_kg_m": col_profiles[selected]["weight"],  # Endi 1.25 koeffitsiyent qo'llanilmaydi!
        "weight_factor": 1.0  # Zaxira koeffitsiyentini 1 ga tushirdik
    }
# ---------------------------------------------------------------------------

# ============================================================

def compute_metal_quantities_advanced(L, W, H, roof_pitch, params):
    """
    Kengaytirilgan metall hisobi - profil tanlash bilan
    """
    
    pitch_rad = math.radians(roof_pitch)
    layout = compute_column_layout(L, W)
    n_cols_x = layout["n_cols_x"]
    n_cols_z = layout["n_cols_z"]
    
    # ===== USTUNLAR =====
    # Har bir ustunga tushadigan yukni hisoblash
    floor_area = L * W
    total_columns = (n_cols_x * 2) + (max(0, n_cols_z - 2) * 2)
    
    # Tom va devor yuklari
    roof_load = params.get("roof_weight_kg_m2", 50)  # kg/m² (qor + o'lik yuk)
    wall_load = params.get("wall_weight_kg_m2", 30)  # kg/m²
    total_load = (floor_area * roof_load) + (2 * (L + W) * H * wall_load)
    load_per_column = total_load / total_columns if total_columns > 0 else 0
    
    # Optimal profilni tanlash
    column_profile = select_optimal_profile(
        load_per_column, 
        max(L, W) / n_cols_x, 
        H,
        "column"
    )
    
    column_kg_m = column_profile["weight_kg_m"] * column_profile["weight_factor"]
    column_meters = total_columns * H
    column_kg = column_meters * column_kg_m
    
    # ===== TOSINLAR =====
    beam_load = load_per_column * 0.6
    beam_profile = select_optimal_profile(
        beam_load,
        max(L, W) / n_cols_x,
        H,
        "beam"
    )
    beam_kg_m = beam_profile["weight_kg_m"] * 1.15
    beam_meters = 2 * (L + W) * 2
    beam_kg = beam_meters * beam_kg_m
    
    # ===== FERMALAR =====
    truss_load = load_per_column * 0.8
    truss_profile = select_optimal_profile(
        truss_load,
        W,
        H,
        "beam"
    )
    truss_kg_m = truss_profile["weight_kg_m"] * 1.2
    
    truss_count = n_cols_x
    if roof_pitch > 0:
        slope = (W / 2) / math.cos(pitch_rad)
        truss_length = slope * 2
    else:
        truss_length = W
    
    truss_mult = 2.2 + (W / 30) * 0.4
    truss_meters = truss_count * truss_length * truss_mult
    truss_kg = truss_meters * truss_kg_m
    
    # ===== PROGONLAR =====
    purlin_result = compute_purlins_advanced(L, W, H, roof_pitch)
    longitudinal_meters = purlin_result["total_m"]
    longitudinal_kg = purlin_result["total_kg"]
    
    # ===== BOG'LAMALAR =====
    seismic_zone = params.get("seismic_zone", 8)
    bracing_result = compute_bracing_advanced(L, W, H, seismic_zone)
    bracing_kg = bracing_result["total_kg"]
    
    # ===== UMUMIY =====
    total_metal_kg = column_kg + beam_kg + truss_kg + longitudinal_kg + bracing_kg
    
    return {
        "total_columns": total_columns,
        "truss_count": truss_count,
        "column_meters": round(column_meters, 1),
        "column_kg": round(column_kg, 1),
        "column_tonna": round(column_kg / 1000, 3),
        "beam_meters": round(beam_meters, 1),
        "beam_kg": round(beam_kg, 1),
        "beam_tonna": round(beam_kg / 1000, 3),
        "truss_meters": round(truss_meters, 1),
        "truss_kg": round(truss_kg, 1),
        "truss_tonna": round(truss_kg / 1000, 3),
        "longitudinal_meters": round(longitudinal_meters, 1),
        "longitudinal_kg": round(longitudinal_kg, 1),
        "longitudinal_tonna": round(longitudinal_kg / 1000, 3),
        "bracing_kg": round(bracing_kg, 1),
        "bracing_tonna": round(bracing_kg / 1000, 3),
        "total_metal_kg": round(total_metal_kg, 1),
        "total_metal_tonna": round(total_metal_kg / 1000, 3),
        "column_profile": column_profile["profile"],
        "column_weight_kg_m": round(column_kg_m, 1),
        "beam_profile": beam_profile["profile"],
        "beam_weight_kg_m": round(beam_kg_m, 1),
        "truss_profile": truss_profile["profile"],
        "truss_weight_kg_m": round(truss_kg_m, 1),
    }
# ---------------------------------------------------------------------------
# TUPROQ + CHIDAMLILIK MODULI (SNiP 2.01.07-85* / SNiP 2.02.01-83* / KMK
# 2.01.03-96 mantig'iga asoslangan SODDALASHTIRILGAN muhandislik tekshiruvi)
#
# DIQQAT: bu - loyihalashgacha bo'lgan (preliminary / budgetary) tekshiruv.
# Real qurilishdan oldin litsenziyalangan konstruktor muhandis tomonidan
# to'liq hisob-kitob (Lira/SAP2000/Tekla) va geologik qidiruv natijalari
# asosida tasdiqlanishi SHART. Bu modul mas'uliyatni almashtirmaydi.
# ---------------------------------------------------------------------------

def compute_section_properties(h=0.30, bf=0.20, tf=0.016, tw=0.010):
    """I-bolka ustun kesimining yuzasi, inersiya momenti va qarshilik
    momentini hisoblaydi. Standart qiymatlar 3D vizualizatsiyada
    ishlatiladigan IB_H/IB_BF/IB_TF/IB_TW bilan bir xil - ko'rinish va
    hisob bir-biriga mos keladi."""
    A = 2 * (bf * tf) + (h - 2 * tf) * tw          # m^2
    Ix = (bf * h**3) / 12 - ((bf - tw) * (h - 2*tf)**3) / 12   # m^4
    Wx = Ix / (h / 2)                               # m^3
    return {
        "A_m2": A, "Ix_m4": Ix, "Wx_m3": Wx,
        "A_cm2": A * 1e4, "Wx_cm3": Wx * 1e6,
    }


def compute_snow_load(snow_region_key, roof_pitch):
    """SNiP 2.01.07-85* mantig'i bo'yicha qor yuki: S = S0 * mu
    mu - tom qiyaligiga bog'liq shakl koeffitsiyenti"""
    S0 = SNOW_REGIONS.get(snow_region_key, 0.5)   # kPa
    if roof_pitch <= 25:
        mu = 1.0
    elif roof_pitch < 60:
        mu = (60 - roof_pitch) / 35
    else:
        mu = 0.0
    S = S0 * mu
    return {
        "S0_kPa": S0, "mu": round(mu, 2), "S_kPa": round(S, 3),
        "S_kg_m2": round(S * 1000 / 9.81, 1),
    }


def compute_wind_load(wind_region, H):
    """SNiP 2.01.07-85* mantig'i bo'yicha shamol yuki: w = w0 * k * c
    w0 - mavjud WIND_LOADS jadvalidagi normativ bosim (yagona manba)"""
    w0 = WIND_LOADS.get(wind_region, WIND_LOADS["B"])["bosim"]   # kPa
    if H <= 5:
        k = 0.5
    elif H <= 10:
        k = 0.65
    elif H <= 20:
        k = 0.85
    else:
        k = 1.0
    c_total = 1.3   # old (+0.8) va orqa (-0.5) devor koeffitsiyentlari yig'indisi
    w = w0 * k * c_total
    return {"w0_kPa": w0, "k": k, "c_total": c_total, "w_kPa": round(w, 3)}


def compute_seismic_load(seismic_zone, total_weight_kg, snow_weight_kg):
    """KMK 2.01.03-96 soddalashtirilgan statik usul: S = K1 * K2 * Q * A"""
    A = SEISMIC_A_COEFF.get(seismic_zone, 0.2)
    K1 = SEISMIC_K1_STEEL_FRAME
    K2 = 1.0
    Q = total_weight_kg + SEISMIC_PSI_SNOW * snow_weight_kg   # kg (seysmik massa)
    S_kg = K1 * K2 * Q * A
    return {"A": A, "K1": K1, "K2": K2, "Q_kg": round(Q, 1), "S_kg": round(S_kg, 1)}


def compute_resilience_report(params, materials):
    """Tuproq, qor/shamol/seysmik yuklar va ustun+fundament mustahkamligini
    bitta hisobotga birlashtiradi. `materials` - calculate_construction_materials
    natijasi (yagona manbadan metall/maydon qiymatlarini qayta ishlatish uchun)."""
    L = params.get("L", 30)
    W = params.get("W", 15)
    H = params.get("H", 7.5)
    roof_pitch = params.get("roof_pitch", 12)

    soil_key = params.get("soil_type", "O'rta zichlikdagi qum")
    snow_key = params.get("snow_region", list(SNOW_REGIONS.keys())[0])
    wind_key = params.get("wind_region", "B")
    seismic_zone = params.get("seismic_zone", 8)

    soil = SOIL_TYPES.get(soil_key, SOIL_TYPES["O'rta zichlikdagi qum"])

    n_columns = materials["total_columns"]
    floor_area = materials["floor_area_m2"]
    roof_area = materials["roof_area_m2"]
    layout = compute_column_layout(L, W)
    spacing_x = layout["spacing_x"]

    # ---- Yuklamalar ----
    snow = compute_snow_load(snow_key, roof_pitch)
    wind = compute_wind_load(wind_key, H)

    roof_panel_weight_kg_m2 = params.get("roof_weight_kg_m2", 13)
    roof_dead_kg_m2 = roof_panel_weight_kg_m2 + (materials["truss_kg"] + materials["longitudinal_kg"]) / roof_area
    snow_kg_m2 = snow["S_kg_m2"]

    wall_weight_kg_m2 = params.get("wall_weight_kg_m2", 12)
    total_wall_weight_kg = wall_weight_kg_m2 * materials["net_wall_area_m2"]
    total_dead_weight_kg = materials["metal_kg"] + roof_panel_weight_kg_m2 * roof_area + total_wall_weight_kg
    total_snow_weight_kg = snow_kg_m2 * floor_area

    seismic = compute_seismic_load(seismic_zone, total_dead_weight_kg, total_snow_weight_kg)

    # ---- Har bir ustunga to'g'ri keladigan yuklar (teng taqsimlangan, taxminiy) ----
    tributary_area = floor_area / n_columns if n_columns > 0 else floor_area
    N_vertical_kg = tributary_area * (roof_dead_kg_m2 + snow_kg_m2)
    N_vertical_N = N_vertical_kg * 9.81

    wind_force_per_col_N = wind["w_kPa"] * 1000 * spacing_x * H
    M_wind_Nm = wind_force_per_col_N * H / 2

    seismic_force_per_col_N = (seismic["S_kg"] / n_columns) * 9.81 if n_columns > 0 else 0
    M_seismic_Nm = seismic_force_per_col_N * H

    M_governing_Nm = max(M_wind_Nm, M_seismic_Nm)
    governing_case = "Shamol yuki" if M_wind_Nm >= M_seismic_Nm else "Seysmik yuk"

    # ---- Ustun kesimi tekshiruvi (kombinatsiyalangan kuchlanish) ----
    sect = compute_section_properties()
    sigma_axial = N_vertical_N / sect["A_m2"]
    sigma_bending = M_governing_Nm / sect["Wx_m3"]
    sigma_total_MPa = (sigma_axial + sigma_bending) / 1e6
    Ry = STEEL_GRADE["Ry_MPa"]
    column_utilization = round((sigma_total_MPa / Ry) * 100, 1)
    column_verdict = (
        "Yetarli" if column_utilization <= 80 else
        "Chegara holatida" if column_utilization <= 100 else
        "Yetarli emas - mustahkamlash kerak"
    )

    # ---- Fundament / tuproq tekshiruvi ----
    R0_Pa = soil["R0_kPa"] * 1000
    N_foundation_N = N_vertical_N * 1.15   # poydevor+orqa to'ldirma og'irligi uchun qo'shimcha
    A_required_m2 = N_foundation_N / R0_Pa
    standard_sizes = [0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.4, 2.8, 3.2]
    side_required = math.sqrt(A_required_m2)
    chosen_side = next((s for s in standard_sizes if s >= side_required), standard_sizes[-1])
    A_chosen_m2 = chosen_side ** 2
    pressure_Pa = N_foundation_N / A_chosen_m2
    foundation_utilization = round((pressure_Pa / R0_Pa) * 100, 1)

    if soil["R0_kPa"] < 100 or side_required > standard_sizes[-1]:
        foundation_type = "Qoziqli (svayali) fundament tavsiya etiladi"
    elif soil["R0_kPa"] < 200:
        foundation_type = "Kengaytirilgan plitali poydevor"
    else:
        foundation_type = "Standart ustunli/lentasimon poydevor"

    foundation_verdict = (
        "Yetarli" if foundation_utilization <= 80 else
        "Chegara holatida" if foundation_utilization <= 100 else
        "Yetarli emas - taglikni kattalashtirish kerak"
    )

    overall_utilization = max(column_utilization, foundation_utilization)
    if overall_utilization <= 80:
        overall_verdict, overall_color = "MOS - barqaror", "#2E7D32"
    elif overall_utilization <= 100:
        overall_verdict, overall_color = "CHEGARADA - qo'shimcha tekshiruv tavsiya etiladi", "#F9A825"
    else:
        overall_verdict, overall_color = "YETARLI EMAS - loyihani kuchaytirish kerak", "#C62828"

    return {
        "soil": soil, "soil_key": soil_key,
        "snow": snow, "wind": wind, "seismic": seismic,
        "governing_case": governing_case,
        "n_columns": n_columns, "tributary_area_m2": round(tributary_area, 2),
        "N_vertical_kg": round(N_vertical_kg, 1),
        "M_wind_kNm": round(M_wind_Nm / 1000, 2),
        "M_seismic_kNm": round(M_seismic_Nm / 1000, 2),
        "section": sect,
        "sigma_total_MPa": round(sigma_total_MPa, 1),
        "Ry_MPa": Ry,
        "column_utilization": column_utilization,
        "column_verdict": column_verdict,
        "A_required_m2": round(A_required_m2, 2),
        "chosen_footing_side_m": chosen_side,
        "foundation_pressure_kPa": round(pressure_Pa / 1000, 1),
        "foundation_utilization": foundation_utilization,
        "foundation_type": foundation_type,
        "foundation_verdict": foundation_verdict,
        "foundation_depth_m": FOUNDATION_FREEZING_DEPTH_M,
        "overall_utilization": overall_utilization,
        "overall_verdict": overall_verdict,
        "overall_color": overall_color,
    }


def create_construction_3d(L, W, H, roof_pitch,
                           window_count=4, 
                           # Old devor darvozalari
                           door_front_count=1, door_front_width=12.0, door_front_height=6.5,
                           # Orqa devor darvozalari
                           door_back_count=0, door_back_width=12.0, door_back_height=6.5,
                           # Chap devor darvozalari
                           door_left_count=0, door_left_width=5.0, door_left_height=4.0,
                           # O'ng devor darvozalari
                           door_right_count=0, door_right_width=5.0, door_right_height=4.0,
                           window_width=2.5, window_height=2.0,
                           window_spacing=0.0,
                           # Ob-havo / zilzila simulyatsiyasi uchun (chidamlilik hisobidan keladi)
                           seismic_zone=8, wind_kPa=0.4, snow_kg_m2=50.0,
                           column_utilization=50.0, foundation_utilization=50.0,column_spacing=8.5):

    pitch_rad = math.radians(roof_pitch)
    ridge_height = H + (W / 2) * math.tan(pitch_rad) if roof_pitch > 0 and W > 0 else H
    pitch_rise = ridge_height - H if roof_pitch > 0 else 0.0

    layout = compute_column_layout(L, W, column_spacing)
    n_cols_x = layout["n_cols_x"]
    n_cols_z = layout["n_cols_z"]
    actual_spacing_x = layout["spacing_x"]
    actual_spacing_z = layout["spacing_z"]

    # Derazalar joylashuvi (X o'qi bo'ylab)
    win_jsons = []
    if window_count > 0 and L > 0:
        if window_spacing <= 0.01:
            total_width = window_count * window_width
            if total_width <= L:
                start = (L - total_width) / 2
                for i in range(window_count):
                    wx = start + i * window_width + window_width / 2
                    wy = H * 0.55
                    win_jsons.append((wx, wy))
            else:
                for i in range(window_count):
                    wx = (i + 0.5) * (L / window_count)
                    wy = H * 0.55
                    win_jsons.append((wx, wy))
        else:
            usable = L - 2.0
            gap = usable / (window_count + 1) if window_count > 0 else 0
            for i in range(window_count):
                wx = 1.0 + gap * (i + 1)
                wy = H * 0.55
                win_jsons.append((wx, wy))

    win_pos_js = "[" + ",".join(f"[{p[0]:.3f},{p[1]:.3f}]" for p in win_jsons) + "]"

    # ========== DARVOZALAR JOYLASHUVI ==========
    
    # Old darvozalar (Z = W)
    door_front_positions = []
    if door_front_count > 0 and L > 0:
        total_w = door_front_count * door_front_width
        if total_w < L:
            gap = (L - total_w) / (door_front_count + 1)
            for i in range(door_front_count):
                dx = gap * (i + 1) + door_front_width * (i + 0.5)
                door_front_positions.append(dx)
        else:
            seg = L / door_front_count
            for i in range(door_front_count):
                door_front_positions.append(seg * (i + 0.5))
    door_front_pos_js = "[" + ",".join(f"{p:.3f}" for p in door_front_positions) + "]"

    # Orqa darvozalar (Z = 0)
    door_back_positions = []
    if door_back_count > 0 and L > 0:
        total_w = door_back_count * door_back_width
        if total_w < L:
            gap = (L - total_w) / (door_back_count + 1)
            for i in range(door_back_count):
                dx = gap * (i + 1) + door_back_width * (i + 0.5)
                door_back_positions.append(dx)
        else:
            seg = L / door_back_count
            for i in range(door_back_count):
                door_back_positions.append(seg * (i + 0.5))
    door_back_pos_js = "[" + ",".join(f"{p:.3f}" for p in door_back_positions) + "]"

    # Chap darvozalar (X = 0) - Z o'qi bo'ylab joylashadi
    door_left_positions = []
    if door_left_count > 0 and W > 0:
        total_w = door_left_count * door_left_width
        if total_w < W:
            gap = (W - total_w) / (door_left_count + 1)
            for i in range(door_left_count):
                dz = gap * (i + 1) + door_left_width * (i + 0.5)
                door_left_positions.append(dz)
        else:
            seg = W / door_left_count
            for i in range(door_left_count):
                door_left_positions.append(seg * (i + 0.5))
    door_left_pos_js = "[" + ",".join(f"{p:.3f}" for p in door_left_positions) + "]"

    # O'ng darvozalar (X = L) - Z o'qi bo'ylab joylashadi
    door_right_positions = []
    if door_right_count > 0 and W > 0:
        total_w = door_right_count * door_right_width
        if total_w < W:
            gap = (W - total_w) / (door_right_count + 1)
            for i in range(door_right_count):
                dz = gap * (i + 1) + door_right_width * (i + 0.5)
                door_right_positions.append(dz)
        else:
            seg = W / door_right_count
            for i in range(door_right_count):
                door_right_positions.append(seg * (i + 0.5))
    door_right_pos_js = "[" + ",".join(f"{p:.3f}" for p in door_right_positions) + "]"

    # Ob-havo simulyatsiyasi uchun vizual masshtablash (haqiqiy fizik birlik
    # emas - faqat zarracha tezligi/intensivligini ko'rinishli qilish uchun)
    wind_speed_js = round(wind_kPa * 8, 2)
    snow_intensity_js = round(min(1.0, snow_kg_m2 / 150), 2)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>3D Angar Konstruktori - {L:.1f}x{W:.1f}x{H:.1f}m</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ overflow:hidden; background:#eef1f3; font-family:'Segoe UI', sans-serif; }}

  #ui-top {{
    position:absolute; top:16px; left:16px; z-index:200;
    display:flex; flex-wrap:wrap; gap:8px; align-items:center;
    background:rgba(255,255,255,0.95);
    padding:12px 16px; border-radius:8px;
    border:1px solid #e0e0e0; box-shadow:0 2px 12px rgba(0,0,0,0.06);
  }}
  #ui-top .logo {{ font-weight:700; color:#37474F; font-size:14px; margin-right:8px; }}
  .vbtn {{
    background:#fafafa; border:1px solid #d0d0d0; color:#424242;
    padding:6px 14px; border-radius:6px; cursor:pointer; font-size:12px;
    font-weight:500; transition:all .15s;
  }}
  .vbtn:hover {{ background:#e8e8e8; border-color:#b0b0b0; }}
  .vbtn.active {{ background:#37474F; color:#fff; border-color:#37474F; }}

  .sep {{ width:1px; height:24px; background:#e0e0e0; margin:0 6px; }}

  .chk-group {{ display:flex; flex-wrap:wrap; gap:8px; }}
  .chk-label {{
    display:inline-flex; align-items:center; gap:4px; font-size:11px; color:#555; cursor:pointer;
    background:#fafafa; padding:5px 10px; border-radius:6px; border:1px solid #e0e0e0;
  }}
  .chk-label input {{ accent-color:#37474F; }}

  #info-panel {{
    position:absolute; top:16px; right:0px; z-index:200;
    background:rgba(255,255,255,0.95);
    padding:16px 20px; border-radius:8px; border:1px solid #e0e0e0;
    min-width:260px; font-size:12px; color:#424242;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
  }}
  #info-panel h4 {{ color:#37474F; font-size:13px; margin-bottom:10px; border-bottom:2px solid #e0e0e0; padding-bottom:6px; }}
  #info-panel .row {{ display:flex; justify-content:space-between; margin-bottom:5px; }}
  #info-panel .val {{ font-weight:600; color:#37474F; }}

  #hint {{ position:absolute; bottom:16px; left:50%; transform:translateX(-50%); background:rgba(55,71,79,0.9); color:#fff; padding:8px 20px; border-radius:20px; font-size:11px; }}

  .sim-row {{ display:flex; align-items:center; gap:8px; margin-bottom:7px; }}
  .sim-row span:first-child {{ width:64px; flex-shrink:0; }}
  .sim-row span:last-child {{ width:38px; text-align:right; flex-shrink:0; font-weight:600; color:#37474F; }}
  .sim-row input[type=range] {{ flex:1; accent-color:#37474F; }}

  #loading {{
    position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
    background:#eef1f3; z-index:300; color:#607D8B; font-size:13px; letter-spacing:1px;
  }}
</style>
</head>
<body>

<div id="loading">3D MODEL YUKLANMOQDA...</div>

<div id="ui-top">
  <span class="logo">3D KONSTRUKTOR</span>
  <button class="vbtn active" data-v="iso">Izometrik</button>
  <button class="vbtn" data-v="front">Old fasad</button>
  <button class="vbtn" data-v="side">Yon fasad</button>
  <button class="vbtn" data-v="top">Reja</button>
  <button class="vbtn" data-v="inside">Ichkaridan</button>
  <div class="sep"></div>
  <div class="chk-group">
    <label class="chk-label"><input type="checkbox" id="chkWalls"   checked> Devorlar</label>
    <label class="chk-label"><input type="checkbox" id="chkRoof"    checked> Tom</label>
    <label class="chk-label"><input type="checkbox" id="chkColumns" checked> Ustunlar</label>
    <label class="chk-label"><input type="checkbox" id="chkTruss"   checked> Fermalar</label>
    <label class="chk-label"><input type="checkbox" id="chkWin"     checked> Derazalar</label>
    <label class="chk-label"><input type="checkbox" id="chkDoor"    checked> Darvozalar</label>
  </div>
</div>

<div id="weather-controls" style="position:absolute; bottom:16px; left:16px; z-index:200; background:rgba(255,255,255,0.95); padding:14px 16px; border-radius:8px; border:1px solid #e0e0e0; box-shadow:0 2px 12px rgba(0,0,0,0.06); font-size:11px; color:#424242; min-width:250px;">
  <div style="font-weight:700; color:#37474F; margin-bottom:8px; font-size:12px;">Simulyatsiya darajasi</div>
  <div class="sim-row"><span>Qor</span><input type="range" id="sldSnow" min="0" max="1000" step="10" value="0"><span id="valSnow">0%</span></div>
  <div class="sim-row"><span> Yomg'ir</span><input type="range" id="sldRain" min="0" max="1000" step="10" value="0"><span id="valRain">0%</span></div>
  <div class="sim-row"><span> Shamol</span><input type="range" id="sldWind" min="0" max="1000" step="10" value="0"><span id="valWind">0%</span></div>
  <div class="sim-row"><span> Zilzila</span><input type="range" id="sldQuake" min="0" max="1000" step="10" value="100"><span id="valQuake">100%</span></div>
  <button class="vbtn" id="btnQuake" style="margin-top:8px; width:100%; background:#C62828; color:#fff; border-color:#C62828;"> Zilzila testini boshlash</button>
</div>

<div id="quakeResult" style="display:none; position:absolute; top:78px; left:50%; transform:translateX(-50%); z-index:250; padding:14px 28px; border-radius:10px; color:#fff; font-weight:700; font-size:14px; box-shadow:0 4px 20px rgba(0,0,0,0.3); text-align:center; max-width:520px;"></div>

<div id="info-panel">
  <h4>Parametrlar</h4>
  <div class="row"><span>Uzunlik</span><span class="val">{L:.1f} m</span></div>
  <div class="row"><span>Kenglik</span><span class="val">{W:.1f} m</span></div>
  <div class="row"><span>Balandlik</span><span class="val">{H:.1f} m</span></div>
  <div class="row"><span>Tom qiyaligi</span><span class="val">{roof_pitch:.1f}&deg;</span></div>
  <div class="row"><span>Old darvoza</span><span class="val">{door_front_count} x {door_front_width:.1f}x{door_front_height:.1f} m</span></div>
  <div class="row"><span>Orqa darvoza</span><span class="val">{door_back_count} x {door_back_width:.1f}x{door_back_height:.1f} m</span></div>
  <div class="row"><span>Chap darvoza</span><span class="val">{door_left_count} x {door_left_width:.1f}x{door_left_height:.1f} m</span></div>
  <div class="row"><span>O'ng darvoza</span><span class="val">{door_right_count} x {door_right_width:.1f}x{door_right_height:.1f} m</span></div>
</div>

<div id="hint">Aylantirish: LMB | Surish: RMB | Zoom: Gildirak</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/renderers/CSS2DRenderer.js"></script>

<script>
const L = {L};
const W = {W};
const H = {H};
const PITCH_DEG = {roof_pitch};
const PITCH_RAD = PITCH_DEG * Math.PI / 180;
const RIDGE_H = {ridge_height};
const PITCH_RISE = {pitch_rise};
const IS_PITCHED = PITCH_DEG > 0.5;
const HALF_W = W / 2;

// Old darvozalar
const DOOR_FRONT_COUNT = {door_front_count};
const DOOR_FRONT_W = {door_front_width};
const DOOR_FRONT_H = {door_front_height};
const DOOR_FRONT_POSITIONS = {door_front_pos_js};

// Orqa darvozalar
const DOOR_BACK_COUNT = {door_back_count};
const DOOR_BACK_W = {door_back_width};
const DOOR_BACK_H = {door_back_height};
const DOOR_BACK_POSITIONS = {door_back_pos_js};

// Chap darvozalar (X = 0)
const DOOR_LEFT_COUNT = {door_left_count};
const DOOR_LEFT_W = {door_left_width};
const DOOR_LEFT_H = {door_left_height};
const DOOR_LEFT_POSITIONS = {door_left_pos_js};

// O'ng darvozalar (X = L)
const DOOR_RIGHT_COUNT = {door_right_count};
const DOOR_RIGHT_W = {door_right_width};
const DOOR_RIGHT_H = {door_right_height};
const DOOR_RIGHT_POSITIONS = {door_right_pos_js};

const WIN_W = {window_width};
const WIN_H = {window_height};
const WIN_COUNT = {window_count};
const WIN_SPACING = {window_spacing};
const WIN_POSITIONS = {win_pos_js};

const COL_STEP_X = {actual_spacing_x:.4f};
const COL_STEP_Z = {actual_spacing_z:.4f};
const N_COLS_X = {n_cols_x};
const N_COLS_Z = {n_cols_z};

const IB_H = 0.30; const IB_BF = 0.20; const IB_TF = 0.016; const IB_TW = 0.010;

// Ob-havo / zilzila simulyatsiyasi - chidamlilik hisobidan kelgan qiymatlar
const SEISMIC_ZONE_VAL = {seismic_zone};
const WIND_SPEED_BASE = {wind_speed_js};
const SNOW_INTENSITY_BASE = {snow_intensity_js};
const COLUMN_UTIL_VAL = {column_utilization};
const FOUNDATION_UTIL_VAL = {foundation_utilization};

// ============================================================
// Scene setup
// ============================================================
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef1f3);
scene.fog = new THREE.Fog(0xeef1f3, Math.max(L, W) * 2.2, Math.max(L, W) * 5);

const camera = new THREE.PerspectiveCamera(42, innerWidth/innerHeight, 0.1, 5000);
camera.position.set(Math.max(L, 20) * 1.1, Math.max(RIDGE_H, 10) * 1.5, Math.max(W, 20) * 1.6);

const renderer = new THREE.WebGLRenderer({{ antialias:true, alpha:false }});
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputEncoding = THREE.sRGBEncoding;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.physicallyCorrectLights = true;
document.body.appendChild(renderer.domElement);

const lblRen = new THREE.CSS2DRenderer();
lblRen.setSize(innerWidth, innerHeight);
lblRen.domElement.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:10;';
document.body.appendChild(lblRen.domElement);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.target.set(L/2, H/2, W/2);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.maxDistance = Math.max(L, W, H) * 6;
controls.minDistance = 2;
controls.maxPolarAngle = Math.PI * 0.495;

// ============================================================
// Lighting
// ============================================================
const hemi = new THREE.HemisphereLight(0xdfeaf2, 0xb9b0a2, 0.55);
scene.add(hemi);

const sun = new THREE.DirectionalLight(0xfff4e0, 2.4);
sun.position.set(Math.max(L, 20) * 0.9, Math.max(RIDGE_H, 10) * 2.6, Math.max(W, 20) * 0.7);
sun.castShadow = true;
sun.shadow.mapSize.width = 2048;
sun.shadow.mapSize.height = 2048;
const shadowExtent = Math.max(L, W, 20) * 0.8;
sun.shadow.camera.left = -shadowExtent;
sun.shadow.camera.right = shadowExtent;
sun.shadow.camera.top = shadowExtent;
sun.shadow.camera.bottom = -shadowExtent;
sun.shadow.camera.far = Math.max(RIDGE_H, 10) * 8;
sun.shadow.bias = -0.0003;
sun.shadow.normalBias = 0.02;
scene.add(sun);

const fillLight = new THREE.DirectionalLight(0xcfe0ff, 0.6);
fillLight.position.set(-Math.max(L, 10), H * 2.2, -Math.max(W, 10));
scene.add(fillLight);

const interiorLight = new THREE.PointLight(0xfff8ec, 3.2, Math.max(L, W, H) * 3.5, 1.4);
interiorLight.position.set(L/2, H * 0.85, W/2);
scene.add(interiorLight);

const interiorLight2 = new THREE.PointLight(0xfff4e0, 2.2, Math.max(L, W, H) * 3.0, 1.6);
interiorLight2.position.set(L * 0.25, H * 0.75, W * 0.5);
scene.add(interiorLight2);

const interiorLight3 = new THREE.PointLight(0xfff4e0, 2.2, Math.max(L, W, H) * 3.0, 1.6);
interiorLight3.position.set(L * 0.75, H * 0.75, W * 0.5);
scene.add(interiorLight3);

const interiorAmbient = new THREE.AmbientLight(0xffffff, 0.55);
scene.add(interiorAmbient);

// ============================================================
// MATERIALS
// ============================================================
const matSteel    = new THREE.MeshStandardMaterial({{ color:0x8a93a0, metalness:0.85, roughness:0.32 }});
const matBeam     = new THREE.MeshStandardMaterial({{ color:0x5c6670, metalness:0.92, roughness:0.25 }});
const matBeamWeb  = new THREE.MeshStandardMaterial({{ color:0x707a85, metalness:0.9,  roughness:0.3 }});
const matPanel    = new THREE.MeshStandardMaterial({{ color:0xe6e9eb, roughness:0.55, metalness:0.08 }});
const matPanelDouble = new THREE.MeshStandardMaterial({{ color:0xe6e9eb, roughness:0.55, metalness:0.08, side:THREE.DoubleSide }});
const matPanelTrim= new THREE.MeshStandardMaterial({{ color:0x37474F, roughness:0.4,  metalness:0.6  }});
const matRoof     = new THREE.MeshStandardMaterial({{ color:0x7c8893, metalness:0.5,  roughness:0.4, side:THREE.DoubleSide }});
const matRidge    = new THREE.MeshStandardMaterial({{ color:0x37474F, metalness:0.85, roughness:0.25 }});
const matGlass    = new THREE.MeshPhysicalMaterial({{
  color:0xffffff, transparent:true, opacity:0.08, roughness:0.0, metalness:0.0,
  transmission:1.0, ior:1.4, thickness:0.01, reflectivity:0.05, clearcoat:0.0,
  side:THREE.DoubleSide, depthWrite:false
}});
const matFrame    = new THREE.MeshStandardMaterial({{ color:0x2C3E50, roughness:0.4, metalness:0.7 }});
const matConcrete = new THREE.MeshStandardMaterial({{ color:0xc7c9cb, roughness:0.92, metalness:0.0 }});
const matDoorPanel= new THREE.MeshStandardMaterial({{ color:0x6b7785, metalness:0.6, roughness:0.35 }});
const matDoorFrame= new THREE.MeshStandardMaterial({{ color:0x808487, metalness:0.5, roughness:0.45 }});
const matGround   = new THREE.MeshStandardMaterial({{ color:0xc9cfb8, roughness:0.95, metalness:0.0 }});
const matCorrugated = new THREE.MeshStandardMaterial({{ color:0xdde1e3, roughness:0.5, metalness:0.15, side:THREE.DoubleSide }});
const matGusset   = new THREE.MeshStandardMaterial({{ color:0x4a525c, metalness:0.7, roughness:0.4 }});
const matBolt     = new THREE.MeshStandardMaterial({{ color:0x2b2f33, metalness:0.6, roughness:0.5 }});

// ============================================================
// Corrugated panel geometry
// ============================================================
function makeCorrugatedPanelGeometry(width, height, corrugateAxis) {{
  const ampl = 0.018;
  let segW, segH;
  if (corrugateAxis === 'height') {{
    segW = 1;
    segH = Math.max(8, Math.round(height / 0.18));
  }} else {{
    segW = Math.max(8, Math.round(width / 0.18));
    segH = 1;
  }}
  const geo = new THREE.PlaneGeometry(width, height, segW, segH);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {{
    let wave;
    if (corrugateAxis === 'height') {{
      const y = pos.getY(i);
      wave = Math.sin((y / height) * Math.PI * (segH / 1.6)) * ampl;
    }} else {{
      const x = pos.getX(i);
      wave = Math.sin((x / width) * Math.PI * (segW / 1.6)) * ampl;
    }}
    pos.setZ(i, pos.getZ(i) + wave);
  }}
  geo.computeVertexNormals();
  return geo;
}}

// ============================================================
// Ground
// ============================================================
const groundGeometry = new THREE.PlaneGeometry(Math.max(L, W) * 4, Math.max(L, W) * 4);
const ground = new THREE.Mesh(groundGeometry, matGround);
ground.rotation.x = -Math.PI / 2;
ground.position.set(L/2, -0.06, W/2);
ground.receiveShadow = true;
scene.add(ground);

const platform = new THREE.Mesh(new THREE.BoxGeometry(L + 1.0, 0.18, W + 1.0), matConcrete);
platform.position.set(L/2, 0.07, W/2);
platform.receiveShadow = true;
platform.castShadow = false;
scene.add(platform);

const matInteriorFloor = new THREE.MeshStandardMaterial({{ color:0xd6d2c4, roughness:0.85, metalness:0.0 }});
const interiorFloor = new THREE.Mesh(new THREE.PlaneGeometry(L - 0.05, W - 0.05), matInteriorFloor);
interiorFloor.rotation.x = -Math.PI / 2;
interiorFloor.position.set(L/2, 0.16, W/2);
interiorFloor.receiveShadow = true;
scene.add(interiorFloor);

// ============================================================
// Bino guruhi - zilzila simulyatsiyasida FAQAT shu guruh harakatlanadi,
// yer/fundament (ground, platform) o'z joyida qoladi
// ============================================================
const buildingGroup = new THREE.Group();
scene.add(buildingGroup);

// ============================================================
// Columns
// ============================================================
const colGroup = new THREE.Group();
function makeIBeamProfile() {{
  const h = IB_H, bf = IB_BF, tf = IB_TF, tw = IB_TW;
  const s = new THREE.Shape();
  s.moveTo(-bf/2, 0); s.lineTo(bf/2, 0); s.lineTo(bf/2, tf); s.lineTo(tw/2, tf);
  s.lineTo(tw/2, h-tf); s.lineTo(bf/2, h-tf); s.lineTo(bf/2, h); s.lineTo(-bf/2, h);
  s.lineTo(-bf/2, h-tf); s.lineTo(-tw/2, h-tf); s.lineTo(-tw/2, tf); s.lineTo(-bf/2, tf);
  s.lineTo(-bf/2, 0); return s;
}}
const ibeamProfile = makeIBeamProfile();
function makeIBeam(length, material) {{
  const geo = new THREE.ExtrudeGeometry(ibeamProfile, {{ steps:1, depth:length, bevelEnabled:false }});
  const mesh = new THREE.Mesh(geo, material);
  mesh.castShadow = true; mesh.receiveShadow = true;
  return mesh;
}}
function addColumn(x, z) {{
  const col = makeIBeam(H, matBeam);
  col.rotation.x = -Math.PI/2;
  col.position.set(x - IB_H/2, 0, z - IB_BF/2);
  colGroup.add(col);

  const basePlate = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.025, 0.45), matSteel);
  basePlate.position.set(x, 0.025, z);
  basePlate.castShadow = true;
  basePlate.receiveShadow = true;
  colGroup.add(basePlate);

  for (const dx of [-0.16, 0.16]) {{
    for (const dz of [-0.16, 0.16]) {{
      const bolt = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.08, 6), matSteel);
      bolt.position.set(x + dx, 0.05, z + dz);
      colGroup.add(bolt);
    }}
  }}
}}

for (let i = 0; i < N_COLS_X; i++) {{
  const x = i * COL_STEP_X;
  addColumn(x, 0);
  addColumn(x, W);
}}
for (let j = 1; j < N_COLS_Z - 1; j++) {{
  const z = j * COL_STEP_Z;
  addColumn(0, z);
  addColumn(L, z);
}}
buildingGroup.add(colGroup);

// ============================================================
// Trusses
// ============================================================
const trussGroup = new THREE.Group();

function buildWarrenTruss(xPos) {{
  const g = new THREE.Group();
  const tube_r_chord = 0.07;
  const tube_r_web   = 0.05;

  function addMember(p1, p2, radius, mat) {{
    const dir = new THREE.Vector3().subVectors(p2, p1);
    const len = dir.length();
    if (len < 0.01) return;
    const geo = new THREE.CylinderGeometry(radius, radius, len, 10);
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = true;
    m.receiveShadow = true;
    m.position.copy(new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5));
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), dir.clone().normalize());
    g.add(m);
  }}

  const halfSpanLen = IS_PITCHED ? HALF_W / Math.cos(PITCH_RAD) : HALF_W;
  const panelsPerSide = Math.max(2, Math.round(halfSpanLen / 1.8));

  function chordPoint(t, side) {{
    const z = side === 'L' ? t * HALF_W : HALF_W + t * HALF_W;
    const bottomY = H;
    const topY = side === 'L' ? H + t * PITCH_RISE : H + (1 - t) * PITCH_RISE;
    return {{
      bot: new THREE.Vector3(xPos, bottomY, z),
      top: new THREE.Vector3(xPos, topY, z)
    }};
  }}

  const nodesL = [], nodesR = [];
  for (let i = 0; i <= panelsPerSide; i++) nodesL.push(chordPoint(i / panelsPerSide, 'L'));
  for (let i = 0; i <= panelsPerSide; i++) nodesR.push(chordPoint(i / panelsPerSide, 'R'));

  for (let i = 0; i < nodesL.length - 1; i++) addMember(nodesL[i].bot, nodesL[i+1].bot, tube_r_chord, matBeam);
  addMember(nodesL[nodesL.length-1].bot, nodesR[0].bot, tube_r_chord, matBeam);
  for (let i = 0; i < nodesR.length - 1; i++) addMember(nodesR[i].bot, nodesR[i+1].bot, tube_r_chord, matBeam);

  for (let i = 0; i < nodesL.length - 1; i++) addMember(nodesL[i].top, nodesL[i+1].top, tube_r_chord, matBeam);
  addMember(nodesL[nodesL.length-1].top, nodesR[0].top, tube_r_chord, matBeam);
  for (let i = 0; i < nodesR.length - 1; i++) addMember(nodesR[i].top, nodesR[i+1].top, tube_r_chord, matBeam);

  function addWebPanels(nodes) {{
    for (let i = 0; i < nodes.length - 1; i++) {{
      addMember(nodes[i].bot, nodes[i].top, tube_r_web, matBeamWeb);
      addMember(nodes[i].bot, nodes[i+1].top, tube_r_web, matBeamWeb);
      addMember(nodes[i+1].bot, nodes[i].top, tube_r_web, matBeamWeb);
    }}
    addMember(nodes[nodes.length-1].bot, nodes[nodes.length-1].top, tube_r_web, matBeamWeb);
  }}
  addWebPanels(nodesL);
  addWebPanels(nodesR);

  addMember(nodesL[nodesL.length-1].top, nodesL[nodesL.length-1].bot, tube_r_web, matBeamWeb);

  function addGusset(p, size) {{
    const plate = new THREE.Mesh(new THREE.BoxGeometry(size, size, 0.025), matGusset);
    plate.position.copy(p);
    plate.castShadow = true;
    g.add(plate);
    const boltOffsets = [[-size*0.32, -size*0.32], [size*0.32, -size*0.32], [-size*0.32, size*0.32], [size*0.32, size*0.32]];
    boltOffsets.forEach(([dx, dy]) => {{
      const bolt = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.03, 6), matBolt);
      bolt.rotation.x = Math.PI/2;
      bolt.position.set(p.x + dx, p.y + dy, p.z);
      g.add(bolt);
    }});
  }}
  nodesL.forEach(n => {{ addGusset(n.bot, 0.22); addGusset(n.top, 0.22); }});
  nodesR.slice(1).forEach(n => {{ addGusset(n.bot, 0.22); addGusset(n.top, 0.22); }});

  const ridgeGusset = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.03), matGusset);
  ridgeGusset.position.set(xPos, H + PITCH_RISE, HALF_W);
  ridgeGusset.castShadow = true;
  g.add(ridgeGusset);

  return g;
}}

for (let i = 0; i < N_COLS_X; i++) trussGroup.add(buildWarrenTruss(i * COL_STEP_X));

for (let i = 0; i < N_COLS_X; i++) {{
  const x = i * COL_STEP_X;
  [0, W].forEach(z => {{
    const kneePlate = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.4, 0.03), matGusset);
    kneePlate.position.set(x, H, z);
    kneePlate.castShadow = true;
    trussGroup.add(kneePlate);
  }});
}}

if (IS_PITCHED) {{
  const ratios = [0.12, 0.38, 0.62, 0.88];
  ratios.forEach(r => {{
    const distZ_L = HALF_W * r;
    const distZ_R = W - distZ_L;
    const pY = H + distZ_L * Math.tan(PITCH_RAD);
    const purlinL = new THREE.Mesh(new THREE.BoxGeometry(L, 0.08, 0.06), matSteel);
    purlinL.position.set(L/2, pY - 0.02, distZ_L); purlinL.castShadow = true; purlinL.receiveShadow = true; trussGroup.add(purlinL);
    const purlinR = new THREE.Mesh(new THREE.BoxGeometry(L, 0.08, 0.06), matSteel);
    purlinR.position.set(L/2, pY - 0.02, distZ_R); purlinR.castShadow = true; purlinR.receiveShadow = true; trussGroup.add(purlinR);
  }});
}} else {{
  const ratios = [0.2, 0.5, 0.8];
  ratios.forEach(r => {{
    const purlin = new THREE.Mesh(new THREE.BoxGeometry(L, 0.08, 0.06), matSteel);
    purlin.position.set(L/2, H - 0.05, W * r); purlin.castShadow = true; purlin.receiveShadow = true; trussGroup.add(purlin);
  }});
}}

buildingGroup.add(trussGroup);

// ============================================================
// Roof
// ============================================================
const roofGroup = new THREE.Group();

function buildRoofSlope(fromZ, toZ, fromY, toY) {{
  const dz = toZ - fromZ;
  const dy = toY - fromY;
  const slopeLen = Math.sqrt(dz*dz + dy*dy);
  const geo = makeCorrugatedPanelGeometry(L, slopeLen, 'width');
  const pos = geo.attributes.position;
  const newPos = new Float32Array(pos.count * 3);
  const angle = Math.atan2(dy, dz);
  for (let i = 0; i < pos.count; i++) {{
    const lx = pos.getX(i);
    const ly = pos.getY(i);
    const lz = pos.getZ(i);
    const worldX = lx + L/2;
    const t = (ly + slopeLen/2) / slopeLen;
    const baseZ = fromZ + dz * t;
    const baseY = fromY + dy * t;
    const nz = -Math.sin(angle) * lz;
    const ny = Math.cos(angle) * lz;
    newPos[i*3]   = worldX;
    newPos[i*3+1] = baseY + ny;
    newPos[i*3+2] = baseZ + nz;
  }}
  const newGeo = new THREE.BufferGeometry();
  newGeo.setAttribute('position', new THREE.BufferAttribute(newPos, 3));
  newGeo.setIndex(geo.index);
  newGeo.computeVertexNormals();
  const finalMesh = new THREE.Mesh(newGeo, matCorrugated);
  finalMesh.castShadow = true;
  finalMesh.receiveShadow = true;
  return finalMesh;
}}

function buildFlatRoofPanel() {{
  const geo = makeCorrugatedPanelGeometry(L, W, 'width');
  const pos = geo.attributes.position;
  const newPos = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {{
    const lx = pos.getX(i);
    const ly = pos.getY(i);
    const lz = pos.getZ(i);
    newPos[i*3]   = lx + L/2;
    newPos[i*3+1] = H + 0.05 + lz;
    newPos[i*3+2] = ly + W/2;
  }}
  const newGeo = new THREE.BufferGeometry();
  newGeo.setAttribute('position', new THREE.BufferAttribute(newPos, 3));
  newGeo.setIndex(geo.index);
  newGeo.computeVertexNormals();
  const mesh = new THREE.Mesh(newGeo, matCorrugated);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}}

if (IS_PITCHED && W > 0) {{
  roofGroup.add(buildRoofSlope(0, HALF_W, H, RIDGE_H));
  roofGroup.add(buildRoofSlope(HALF_W, W, RIDGE_H, H));
  const ridgeWidth = 0.5;
  const ridgeCapMesh = new THREE.Mesh(new THREE.BoxGeometry(L + 0.2, 0.1, ridgeWidth), matRidge);
  ridgeCapMesh.position.set(L/2, RIDGE_H + 0.05, HALF_W);
  ridgeCapMesh.castShadow = true;
  ridgeCapMesh.receiveShadow = true;
  roofGroup.add(ridgeCapMesh);
  [0, W].forEach((zEdge) => {{
    const fascia = new THREE.Mesh(new THREE.BoxGeometry(L + 0.2, 0.25, 0.04), matPanelTrim);
    fascia.position.set(L/2, H - 0.05, zEdge);
    fascia.castShadow = true;
    roofGroup.add(fascia);
  }});
}} else {{
  roofGroup.add(buildFlatRoofPanel());
  const parapet = new THREE.Mesh(new THREE.BoxGeometry(L + 0.1, 0.3, 0.08), matPanelTrim);
  parapet.position.set(L/2, H + 0.2, 0.0);
  parapet.castShadow = true;
  roofGroup.add(parapet);
  const parapet2 = parapet.clone();
  parapet2.position.z = W;
  roofGroup.add(parapet2);
}}
buildingGroup.add(roofGroup);

// ============================================================
// Walls with openings
// ============================================================
const wallGroup = new THREE.Group();
const windowGroup = new THREE.Group();
const doorGroup = new THREE.Group();
const T = 0.12;

function addWallSegment(group, length, height, axis, normalSign, fixedCoord, segCenter, baseY) {{
  if (length <= 0.02 || height <= 0.02) return;
  const geo = makeCorrugatedPanelGeometry(length, height, 'width');
  const pos = geo.attributes.position;
  const newPos = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {{
    const lx = pos.getX(i);
    const ly = pos.getY(i);
    const lz = pos.getZ(i);
    let wx, wy, wz;
    if (axis === 'x') {{
      wx = segCenter + lx;
      wy = baseY + ly + height/2;
      wz = fixedCoord + lz * normalSign;
    }} else {{
      wz = segCenter + lx;
      wy = baseY + ly + height/2;
      wx = fixedCoord + lz * normalSign;
    }}
    newPos[i*3] = wx; newPos[i*3+1] = wy; newPos[i*3+2] = wz;
  }}
  const newGeo = new THREE.BufferGeometry();
  newGeo.setAttribute('position', new THREE.BufferAttribute(newPos, 3));
  newGeo.setIndex(geo.index);
  newGeo.computeVertexNormals();
  const mesh = new THREE.Mesh(newGeo, matPanelDouble);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
}}

function addWindow(axis, fixedCoord, normalSign, centerAlong, centerY) {{
  let g, f, mvv, mhh;
  if (axis === 'x') {{
    g  = new THREE.BoxGeometry(WIN_W, WIN_H, 0.03);
    f  = new THREE.BoxGeometry(WIN_W + 0.07, WIN_H + 0.07, 0.07);
    mvv = new THREE.BoxGeometry(0.03, WIN_H, 0.025);
    mhh = new THREE.BoxGeometry(WIN_W, 0.03, 0.025);
  }} else {{
    g  = new THREE.BoxGeometry(0.03, WIN_H, WIN_W);
    f  = new THREE.BoxGeometry(0.07, WIN_H + 0.07, WIN_W + 0.07);
    mvv = new THREE.BoxGeometry(0.025, WIN_H, 0.03);
    mhh = new THREE.BoxGeometry(0.025, 0.03, WIN_W);
  }}
  const glassMesh = new THREE.Mesh(g, matGlass);
  const frameMesh = new THREE.Mesh(f, matFrame);
  frameMesh.castShadow = true;
  const offset = 0.025 * normalSign;
  if (axis === 'x') {{
    glassMesh.position.set(centerAlong, centerY, fixedCoord + offset);
    frameMesh.position.set(centerAlong, centerY, fixedCoord + offset);
  }} else {{
    glassMesh.position.set(fixedCoord + offset, centerY, centerAlong);
    frameMesh.position.set(fixedCoord + offset, centerY, centerAlong);
  }}
  windowGroup.add(glassMesh);
  windowGroup.add(frameMesh);
  const mvMesh = new THREE.Mesh(mvv, matFrame);
  const mhMesh = new THREE.Mesh(mhh, matFrame);
  mvMesh.position.copy(glassMesh.position);
  mhMesh.position.copy(glassMesh.position);
  windowGroup.add(mvMesh);
  windowGroup.add(mhMesh);
}}

function buildWallWithOpenings(group, totalLength, height, axis, fixedCoord, normalSign, baseX_or_Z, openings) {{
  const sorted = openings.slice().sort((a,b) => a.center - b.center);
  let cursor = 0;
  function segCenterWorld(localStart, localLen) {{
    return baseX_or_Z + localStart + localLen/2;
  }}
  for (const op of sorted) {{
    const opStart = op.center - op.width/2 - baseX_or_Z;
    const opEnd = op.center + op.width/2 - baseX_or_Z;
    const segLen = opStart - cursor;
    if (segLen > 0.02) {{
      addWallSegment(group, segLen, height, axis, normalSign, fixedCoord, segCenterWorld(cursor, segLen), 0);
    }}
    const sill = op.sillY !== undefined ? op.sillY : 0;
    const openTop = sill + (op.openHeight !== undefined ? op.openHeight : height);
    if (sill > 0.02) {{
      addWallSegment(group, op.width, sill, axis, normalSign, fixedCoord, baseX_or_Z + op.center, 0);
    }}
    if (openTop < height - 0.02) {{
      addWallSegment(group, op.width, height - openTop, axis, normalSign, fixedCoord, baseX_or_Z + op.center, openTop);
    }}
    cursor = opEnd;
  }}
  const tailLen = totalLength - cursor;
  if (tailLen > 0.02) {{
    addWallSegment(group, tailLen, height, axis, normalSign, fixedCoord, segCenterWorld(cursor, tailLen), 0);
  }}
  if (sorted.length === 0) {{
    addWallSegment(group, totalLength, height, axis, normalSign, fixedCoord, baseX_or_Z + totalLength/2, 0);
  }}
}}

function addGirtSegments(totalLength, gh, axis, fixedCoord, normalSign, baseX_or_Z, openings) {{
  const sorted = openings.slice().sort((a,b) => a.center - b.center);
  let cursor = 0;
  const girtT = 0.05;
  function addSeg(localStart, localLen) {{
    if (localLen <= 0.02) return;
    const center = baseX_or_Z + localStart + localLen/2;
    let geo, pos;
    if (axis === 'x') {{
      geo = new THREE.BoxGeometry(localLen, girtT, girtT);
      pos = new THREE.Vector3(center, gh, fixedCoord + (girtT/2) * normalSign);
    }} else {{
      geo = new THREE.BoxGeometry(girtT, girtT, localLen);
      pos = new THREE.Vector3(fixedCoord + (girtT/2) * normalSign, gh, center);
    }}
    const mesh = new THREE.Mesh(geo, matSteel);
    mesh.position.copy(pos);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    trussGroup.add(mesh);
  }}
  for (const op of sorted) {{
    const sill = op.sillY !== undefined ? op.sillY : 0;
    const openTop = sill + (op.openHeight !== undefined ? op.openHeight : 1e9);
    if (gh > sill - 0.05 && gh < openTop + 0.05) {{
      const opStart = op.center - op.width/2 - baseX_or_Z;
      const opEnd = op.center + op.width/2 - baseX_or_Z;
      if (opStart > cursor) addSeg(cursor, opStart - cursor);
      cursor = Math.max(cursor, opEnd);
    }}
  }}
  if (totalLength - cursor > 0.02) addSeg(cursor, totalLength - cursor);
}}

// ========== DEVORLAR ==========

// Old devor (Z = W) - old darvozalar
{{
  const frontOpenings = DOOR_FRONT_POSITIONS.map(dx => ({{
    center: dx, width: DOOR_FRONT_W, sillY: 0, openHeight: DOOR_FRONT_H
  }}));
  buildWallWithOpenings(wallGroup, L, H, 'x', W, 1, 0, frontOpenings);
  const wallGirtHeights = [H * 0.18, H * 0.5, H * 0.82];
  wallGirtHeights.forEach(gh => addGirtSegments(L, gh, 'x', W, 1, 0, frontOpenings));
}}

// Orqa devor (Z = 0) - orqa darvozalar
{{
  const backOpenings = DOOR_BACK_POSITIONS.map(dx => ({{
    center: dx, width: DOOR_BACK_W, sillY: 0, openHeight: DOOR_BACK_H
  }}));
  // Derazalarni ham qo'shamiz
  for (let wi = 0; wi < WIN_COUNT; wi++) {{
    const wx = WIN_POSITIONS[wi][0];
    const wy = WIN_POSITIONS[wi][1];
    backOpenings.push({{ center: wx, width: WIN_W, sillY: wy - WIN_H/2, openHeight: WIN_H }});
    addWindow('x', 0, -1, wx, wy);
  }}
  buildWallWithOpenings(wallGroup, L, H, 'x', 0, -1, 0, backOpenings);
  const wallGirtHeightsBack = [H * 0.18, H * 0.5, H * 0.82];
  wallGirtHeightsBack.forEach(gh => addGirtSegments(L, gh, 'x', 0, -1, 0, backOpenings));
}}

// Chap devor (X = 0) - chap darvozalar
{{
  const leftOpenings = DOOR_LEFT_POSITIONS.map(dz => ({{
    center: dz, width: DOOR_LEFT_W, sillY: 0, openHeight: DOOR_LEFT_H
  }}));
  buildWallWithOpenings(wallGroup, W, H, 'z', 0, -1, 0, leftOpenings);
  const wallGirtHeightsLeft = [H * 0.18, H * 0.5, H * 0.82];
  wallGirtHeightsLeft.forEach(gh => addGirtSegments(W, gh, 'z', 0, -1, 0, leftOpenings));
}}

// O'ng devor (X = L) - o'ng darvozalar
{{
  const rightOpenings = DOOR_RIGHT_POSITIONS.map(dz => ({{
    center: dz, width: DOOR_RIGHT_W, sillY: 0, openHeight: DOOR_RIGHT_H
  }}));
  buildWallWithOpenings(wallGroup, W, H, 'z', L, 1, 0, rightOpenings);
  const wallGirtHeightsRight = [H * 0.18, H * 0.5, H * 0.82];
  wallGirtHeightsRight.forEach(gh => addGirtSegments(W, gh, 'z', L, 1, 0, rightOpenings));
}}

buildingGroup.add(wallGroup);
buildingGroup.add(windowGroup);

// ============================================================
// DOORS (3D models)
// ============================================================

// Old darvozalar (Z = W)
const doorZ_front = W + T/2 + 0.04;
DOOR_FRONT_POSITIONS.forEach((doorX) => {{
  const dw = Math.max(1.0, DOOR_FRONT_W);
  const dh = Math.max(1.0, DOOR_FRONT_H);
  const panelWidth = dw;
  const panelHeight = dh / 4;
  const panelThick = 0.05;
  for (let i = 0; i < 4; i++) {{
    const panel = new THREE.Mesh(new THREE.BoxGeometry(panelWidth - 0.1, panelHeight - 0.02, panelThick), matDoorPanel);
    panel.position.set(doorX, (i + 0.5) * panelHeight, doorZ_front);
    panel.castShadow = true;
    doorGroup.add(panel);
    for (let v = 0; v < 4; v++) {{
      const vertLine = new THREE.Mesh(new THREE.BoxGeometry(0.012, panelHeight - 0.04, panelThick + 0.01), matSteel);
      vertLine.position.set(doorX - panelWidth/2 + 0.15 + v * (panelWidth - 0.3)/3, (i + 0.5) * panelHeight, doorZ_front);
      doorGroup.add(vertLine);
    }}
  }}
  const doorFrameOuter = new THREE.Mesh(new THREE.BoxGeometry(dw + 0.15, dh + 0.15, 0.08), matDoorFrame);
  doorFrameOuter.position.set(doorX, dh/2, W + T/2 + 0.01);
  doorGroup.add(doorFrameOuter);
  const doorFrameInner = new THREE.Mesh(new THREE.BoxGeometry(dw - 0.02, dh - 0.02, 0.06), matSteel);
  doorFrameInner.position.set(doorX, dh/2, W + T/2 + 0.03);
  doorGroup.add(doorFrameInner);
}});

// Orqa darvozalar (Z = 0)
const doorZ_back = -T/2 - 0.04;
DOOR_BACK_POSITIONS.forEach((doorX) => {{
  const dw = Math.max(1.0, DOOR_BACK_W);
  const dh = Math.max(1.0, DOOR_BACK_H);
  const panelWidth = dw;
  const panelHeight = dh / 4;
  const panelThick = 0.05;
  for (let i = 0; i < 4; i++) {{
    const panel = new THREE.Mesh(new THREE.BoxGeometry(panelWidth - 0.1, panelHeight - 0.02, panelThick), matDoorPanel);
    panel.position.set(doorX, (i + 0.5) * panelHeight, doorZ_back);
    panel.castShadow = true;
    doorGroup.add(panel);
  }}
  const doorFrameOuter = new THREE.Mesh(new THREE.BoxGeometry(dw + 0.15, dh + 0.15, 0.08), matDoorFrame);
  doorFrameOuter.position.set(doorX, dh/2, -T/2 - 0.01);
  doorGroup.add(doorFrameOuter);
}});

// Chap darvozalar (X = 0)
const doorX_left = -T/2 - 0.04;
DOOR_LEFT_POSITIONS.forEach((doorZ) => {{
  const dw = Math.max(1.0, DOOR_LEFT_W);
  const dh = Math.max(1.0, DOOR_LEFT_H);
  const panelHeight = dh / 4;
  const panelThick = 0.05;
  for (let i = 0; i < 4; i++) {{
    const panel = new THREE.Mesh(new THREE.BoxGeometry(panelThick, panelHeight - 0.02, dw - 0.1), matDoorPanel);
    panel.position.set(doorX_left, (i + 0.5) * panelHeight, doorZ);
    panel.castShadow = true;
    doorGroup.add(panel);
  }}
  const doorFrameOuter = new THREE.Mesh(new THREE.BoxGeometry(0.08, dh + 0.15, dw + 0.15), matDoorFrame);
  doorFrameOuter.position.set(-T/2 - 0.01, dh/2, doorZ);
  doorGroup.add(doorFrameOuter);
}});

// O'ng darvozalar (X = L)
const doorX_right = L + T/2 + 0.04;
DOOR_RIGHT_POSITIONS.forEach((doorZ) => {{
  const dw = Math.max(1.0, DOOR_RIGHT_W);
  const dh = Math.max(1.0, DOOR_RIGHT_H);
  const panelHeight = dh / 4;
  const panelThick = 0.05;
  for (let i = 0; i < 4; i++) {{
    const panel = new THREE.Mesh(new THREE.BoxGeometry(panelThick, panelHeight - 0.02, dw - 0.1), matDoorPanel);
    panel.position.set(doorX_right, (i + 0.5) * panelHeight, doorZ);
    panel.castShadow = true;
    doorGroup.add(panel);
  }}
  const doorFrameOuter = new THREE.Mesh(new THREE.BoxGeometry(0.08, dh + 0.15, dw + 0.15), matDoorFrame);
  doorFrameOuter.position.set(L + T/2 + 0.01, dh/2, doorZ);
  doorGroup.add(doorFrameOuter);
}});

buildingGroup.add(doorGroup);

// ============================================================
// OB-HAVO VA ZILZILA SIMULYATSIYASI
// ============================================================
const WEATHER = {{
  snowOn: false, rainOn: false, windOn: false,
  windSpeed: WIND_SPEED_BASE,
  snowIntensity: SNOW_INTENSITY_BASE,
  snowFallMult: 0.4,
}};

function makeCircleTexture() {{
  const c = document.createElement('canvas');
  c.width = 32; c.height = 32;
  const ctx = c.getContext('2d');
  const grad = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 32, 32);
  return new THREE.CanvasTexture(c);
}}
const circleTex = makeCircleTexture();

const WX_MIN = -8, WX_MAX = L + 8, WZ_MIN = -8, WZ_MAX = W + 8;
const WX_TOP = RIDGE_H + 12;

// ============================================================
// PARTICLE COUNT UPDATE FUNCTION
// ============================================================
function updateParticleCount(geometry, targetCount) {{
  const currentCount = geometry.attributes.position.count;
  if (currentCount === targetCount) return;
  
  const stride = geometry.attributes.position.itemSize || 3;
  const newPos = new Float32Array(targetCount * stride);
  const oldPos = geometry.attributes.position.array;
  
  for (let i = 0; i < targetCount; i++) {{
    if (i < currentCount && i * stride < oldPos.length) {{
      for (let j = 0; j < stride; j++) {{
        newPos[i*stride + j] = oldPos[i*stride + j];
      }}
    }} else {{
      newPos[i*stride] = WX_MIN + Math.random() * (WX_MAX - WX_MIN);
      newPos[i*stride+1] = Math.random() * WX_TOP;
      if (stride > 2) newPos[i*stride+2] = WZ_MIN + Math.random() * (WZ_MAX - WZ_MIN);
    }}
  }}
  
  geometry.setAttribute('position', new THREE.BufferAttribute(newPos, stride));
  geometry.attributes.position.needsUpdate = true;
}}

// ---- QOR (1500 ta zarracha) ----
let SNOW_COUNT = 1500;
const snowGeo = new THREE.BufferGeometry();
const snowPosArr = new Float32Array(SNOW_COUNT * 3);
const snowVelArr = new Float32Array(SNOW_COUNT);
for (let i = 0; i < SNOW_COUNT; i++) {{
  snowPosArr[i*3]   = WX_MIN + Math.random() * (WX_MAX - WX_MIN);
  snowPosArr[i*3+1] = Math.random() * WX_TOP;
  snowPosArr[i*3+2] = WZ_MIN + Math.random() * (WZ_MAX - WZ_MIN);
  snowVelArr[i] = 0.6 + Math.random() * 0.8;
}}
snowGeo.setAttribute('position', new THREE.BufferAttribute(snowPosArr, 3));
const snowMat = new THREE.PointsMaterial({{ 
  size:0.22, map:circleTex, transparent:true, opacity:0.9, 
  color:0xffffff, depthWrite:false, blending:THREE.NormalBlending 
}});
const snowPoints = new THREE.Points(snowGeo, snowMat);
snowPoints.visible = false;
scene.add(snowPoints);

function updateSnow(dt) {{
  const fallMult = WEATHER.snowFallMult || 1;
  const pos = snowGeo.attributes.position.array;
  const count = snowGeo.attributes.position.count;
  for (let i = 0; i < count; i++) {{
    pos[i*3+1] -= snowVelArr[i % snowVelArr.length] * dt * 6 * fallMult;
    pos[i*3]   += Math.sin(performance.now()*0.0005 + i) * 0.015 + WEATHER.windSpeed * dt * 0.25;
    if (pos[i*3+1] < 0) {{
      pos[i*3+1] = WX_TOP;
      pos[i*3]   = WX_MIN + Math.random() * (WX_MAX - WX_MIN);
      pos[i*3+2] = WZ_MIN + Math.random() * (WZ_MAX - WZ_MIN);
    }}
  }}
  snowGeo.attributes.position.needsUpdate = true;
}}

// Tom ustidagi qor qoplami
const snowCapMat = new THREE.MeshStandardMaterial({{ 
  color:0xffffff, roughness:0.85, metalness:0.0, 
  transparent:true, opacity:0.0, depthWrite:false, side:THREE.DoubleSide 
}});


// ---- YOMG'IR (750 ta chiziq) ----
let RAIN_COUNT = 750;
const rainGeo = new THREE.BufferGeometry();
const rainPosArr = new Float32Array(RAIN_COUNT * 6);
for (let i = 0; i < RAIN_COUNT; i++) {{
  const x = WX_MIN + Math.random() * (WX_MAX - WX_MIN);
  const y = Math.random() * WX_TOP;
  const z = WZ_MIN + Math.random() * (WZ_MAX - WZ_MIN);
  rainPosArr[i*6]   = x; rainPosArr[i*6+1] = y;        rainPosArr[i*6+2] = z;
  rainPosArr[i*6+3] = x; rainPosArr[i*6+4] = y - 0.35;  rainPosArr[i*6+5] = z;
}}
rainGeo.setAttribute('position', new THREE.BufferAttribute(rainPosArr, 3));
const rainMat = new THREE.LineBasicMaterial({{ color:0x9fc4e0, transparent:true, opacity:0.7 }});
const rainLines = new THREE.LineSegments(rainGeo, rainMat);
rainLines.visible = false;
scene.add(rainLines);

function updateRain(dt) {{
  const fall = dt * 9 * (0.6 + (WEATHER.rainIntensity || 0) * 1.5);
  const pos = rainGeo.attributes.position.array;
  const count = rainGeo.attributes.position.count;
  for (let i = 0; i < count; i++) {{
    pos[i*6+1] -= fall; pos[i*6+4] -= fall;
    pos[i*6]   += WEATHER.windSpeed * dt * 0.5;
    pos[i*6+3] += WEATHER.windSpeed * dt * 0.5;
    if (pos[i*6+1] < 0) {{
      const x = WX_MIN + Math.random() * (WX_MAX - WX_MIN);
      const z = WZ_MIN + Math.random() * (WZ_MAX - WZ_MIN);
      pos[i*6]=x; pos[i*6+1]=WX_TOP;        pos[i*6+2]=z;
      pos[i*6+3]=x; pos[i*6+4]=WX_TOP-0.35; pos[i*6+5]=z;
    }}
  }}
  rainGeo.attributes.position.needsUpdate = true;
}}

// ---- SHAMOL (250 ta zarracha) ----
let WIND_COUNT = 250;
const windGeo = new THREE.BufferGeometry();
const windPosArr = new Float32Array(WIND_COUNT * 3);
for (let i = 0; i < WIND_COUNT; i++) {{
  windPosArr[i*3]   = WX_MIN + Math.random() * (WX_MAX - WX_MIN);
  windPosArr[i*3+1] = 0.3 + Math.random() * (RIDGE_H + 4);
  windPosArr[i*3+2] = WZ_MIN + Math.random() * (WZ_MAX - WZ_MIN);
}}
windGeo.setAttribute('position', new THREE.BufferAttribute(windPosArr, 3));
const windMat = new THREE.PointsMaterial({{ 
  size:0.18, map:circleTex, transparent:true, opacity:0.6, 
  color:0xb0c4de, depthWrite:false, blending:THREE.NormalBlending 
}});
const windPoints = new THREE.Points(windGeo, windMat);
windPoints.visible = false;
scene.add(windPoints);

function updateWind(dt) {{
  const pos = windGeo.attributes.position.array;
  const count = windGeo.attributes.position.count;
  const speed = 3 + WEATHER.windSpeed * 2;
  for (let i = 0; i < count; i++) {{
    pos[i*3] += speed * dt;
    pos[i*3+1] += Math.sin(performance.now()*0.001 + i*0.5) * 0.005;
    if (pos[i*3] > WX_MAX) pos[i*3] = WX_MIN;
  }}
  windGeo.attributes.position.needsUpdate = true;
}}

// ---- ZILZILA ----
const quakeAmplitudeMap = {{7:0.05, 8:0.12, 9:0.25}};
const quakeBaseAmplitude = (quakeAmplitudeMap[SEISMIC_ZONE_VAL] || 0.12) * Math.max(0.6, H / 7.5);
const quakeFreq = 2.2;
const quakeDurationSec = 7.0;
let quakeActive = false;
let quakeStartTime = 0;
let quakeCurrentAmplitude = quakeBaseAmplitude;
let quakeCurrentMagnitudePct = 100;

function tintMembers(hexColor) {{
  [colGroup, trussGroup].forEach(g => {{
    g.traverse(obj => {{
      if (obj.isMesh && obj.material && obj.material.color) {{
        if (!obj.userData.origColor) obj.userData.origColor = obj.material.color.clone();
        obj.material.color.set(hexColor);
      }}
    }});
  }});
}}
function resetMemberColors() {{
  [colGroup, trussGroup].forEach(g => {{
    g.traverse(obj => {{
      if (obj.isMesh && obj.userData.origColor) obj.material.color.copy(obj.userData.origColor);
    }});
  }});
}}

function startEarthquake() {{
  resetMemberColors();
  document.getElementById('quakeResult').style.display = 'none';
  quakeCurrentMagnitudePct = parseInt(document.getElementById('sldQuake').value, 10);
  quakeCurrentAmplitude = quakeBaseAmplitude * (quakeCurrentMagnitudePct / 100);
  quakeActive = true;
  quakeStartTime = performance.now();
}}

function updateEarthquake() {{
  if (!quakeActive) return;
  const t = (performance.now() - quakeStartTime) / 1000;
  if (t > quakeDurationSec) {{
    quakeActive = false;
    buildingGroup.position.x = 0;
    buildingGroup.rotation.z = 0;
    showQuakeResult();
    return;
  }}
  const decay = Math.exp(-0.45 * t);
  const offset = quakeCurrentAmplitude * decay * Math.sin(quakeFreq * 2 * Math.PI * t);
  buildingGroup.position.x = offset;
  buildingGroup.rotation.z = offset * 0.012;
  buildingGroup.position.y = Math.abs(offset) * 0.003;
}}

function showQuakeResult() {{
  const el = document.getElementById('quakeResult');
  const baseWorstUtil = Math.max(COLUMN_UTIL_VAL, FOUNDATION_UTIL_VAL);
  const magMult = quakeCurrentMagnitudePct / 100;
  const effectiveUtil = baseWorstUtil * magMult;
  const failed = effectiveUtil > 100;
  if (failed) {{
    tintMembers(0xb71c1c);
    el.innerHTML = '&#9888;&#65039; STRUKTURA YETARLI EMAS &mdash; effektiv band qilinish: ' + effectiveUtil.toFixed(0) + '% (zilzila kuchi: ' + quakeCurrentMagnitudePct + '%)';
    el.style.background = 'rgba(198,40,40,0.95)';
  }} else {{
    el.innerHTML = '&#9989; BARDOSH BERDI &mdash; effektiv band qilinish: ' + effectiveUtil.toFixed(0) + '% (zilzila kuchi: ' + quakeCurrentMagnitudePct + '%, zona ' + SEISMIC_ZONE_VAL + ')';
    el.style.background = 'rgba(46,125,50,0.95)';
  }}
  el.style.display = 'block';
}}

// ============================================================
// Grid
// ============================================================
const grid = new THREE.GridHelper(Math.max(L, W) * 3, 40, 0xb8c2c8, 0xd6dde1);
grid.position.set(L/2, 0.001, W/2);
grid.material.transparent = true;
grid.material.opacity = 0.4;
scene.add(grid);

// ============================================================
// Labels
// ============================================================
function addLabel(txt, x, y, z, color) {{
  const d = document.createElement('div');
  d.textContent = txt;
  d.style.cssText = `background:rgba(255,255,255,0.92); color:${{color}}; padding:3px 10px; border-radius:4px; font-size:10px; font-family:monospace; white-space:nowrap; pointer-events:none; border:1px solid #e0e0e0;`;
  const lbl = new THREE.CSS2DObject(d);
  lbl.position.set(x, y, z);
  scene.add(lbl);
}}

addLabel(`Uzunlik: {L:.1f} m`, L/2, -0.3, -1.0, '#37474F');
addLabel(`Kenglik: {W:.1f} m`, L + 1.5, -0.3, W/2, '#455A64');
addLabel(`Balandlik: {H:.1f} m`, -1.5, H/2, W/2, '#546E7A');
if (IS_PITCHED) addLabel(`Tizma: {ridge_height:.2f} m`, L/2, RIDGE_H + 0.5, HALF_W, '#607D8B');

// ============================================================
// Camera views
// ============================================================
const VIEWS = {{
  iso:   {{ p:[Math.max(L, 20)*1.1, Math.max(RIDGE_H, 10)*1.5, Math.max(W, 20)*1.6], t:[L/2, H/2, W/2] }},
  front: {{ p:[L/2, H*0.8, W + Math.max(W, 20)*1.2], t:[L/2, H/2, W/2] }},
  side:  {{ p:[-Math.max(L, 20)*1.2, H*0.8, W/2], t:[L/2, H/2, W/2] }},
  top:   {{ p:[L/2, Math.max(RIDGE_H, 10)*2.5, W/2], t:[L/2, 0, W/2] }},
  inside:{{ p:[L/2, H*0.5, W*0.3], t:[L/2, H*0.5, W*0.8] }}
}};

document.querySelectorAll('.vbtn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.vbtn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const v = VIEWS[btn.dataset.v];
    if (v) {{
      const startPos = camera.position.clone();
      const endPos = new THREE.Vector3(...v.p);
      const startTarget = controls.target.clone();
      const endTarget = new THREE.Vector3(...v.t);
      const duration = 800;
      const startTime = Date.now();
      function animateView() {{
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        camera.position.lerpVectors(startPos, endPos, ease);
        controls.target.lerpVectors(startTarget, endTarget, ease);
        controls.update();
        if (progress < 1) requestAnimationFrame(animateView);
      }}
      animateView();
    }}
  }});
}});

document.getElementById('chkWalls').addEventListener('change', e => wallGroup.visible = e.target.checked);
document.getElementById('chkRoof').addEventListener('change', e => roofGroup.visible = e.target.checked);
document.getElementById('chkColumns').addEventListener('change', e => colGroup.visible = e.target.checked);
document.getElementById('chkTruss').addEventListener('change', e => trussGroup.visible = e.target.checked);
document.getElementById('chkWin').addEventListener('change', e => windowGroup.visible = e.target.checked);
document.getElementById('chkDoor').addEventListener('change', e => doorGroup.visible = e.target.checked);

// ============================================================
// WEATHER UPDATE FUNCTIONS (with particle density control)
// ============================================================
function updateSnowVisual() {{
  const pct = parseInt(document.getElementById('sldSnow').value, 10);
  document.getElementById('valSnow').textContent = pct + '%';
  WEATHER.snowOn = pct > 0;
  WEATHER.snowIntensity = SNOW_INTENSITY_BASE * (pct / 100);
  WEATHER.snowFallMult = 0.4 + (pct / 100) * 1.6;
  
  // Dynamic particle count: 200 at 0%, up to 3000 at 100%
  const targetCount = Math.round(200 + (pct / 100) * 2800);
  updateParticleCount(snowGeo, targetCount);
  
  snowPoints.visible = WEATHER.snowOn;
  snowMat.opacity = WEATHER.snowOn ? Math.min(1.0, 0.3 + WEATHER.snowIntensity * 0.7) : 0.0;
  snowMat.size = 0.15 + (pct / 100) * 0.25;
  snowCapMat.opacity = WEATHER.snowOn ? Math.min(0.95, 0.1 + WEATHER.snowIntensity * 0.65) : 0.0;
}}

function updateRainVisual() {{
  const pct = parseInt(document.getElementById('sldRain').value, 10);
  document.getElementById('valRain').textContent = pct + '%';
  WEATHER.rainOn = pct > 0;
  WEATHER.rainIntensity = pct / 100;
  
  const targetCount = Math.round(100 + (pct / 100) * 1400);
  updateParticleCount(rainGeo, targetCount);
  
  rainLines.visible = WEATHER.rainOn;
  rainMat.opacity = WEATHER.rainOn ? Math.min(1.0, 0.2 + WEATHER.rainIntensity * 0.6) : 0.0;
}}

function updateWindVisual() {{
  const pct = parseInt(document.getElementById('sldWind').value, 10);
  document.getElementById('valWind').textContent = pct + '%';
  WEATHER.windOn = pct > 0;
  WEATHER.windSpeed = Math.max(WIND_SPEED_BASE, 0.4) * (pct / 100);
  
  const targetCount = Math.round(30 + (pct / 100) * 270);
  updateParticleCount(windGeo, targetCount);
  
  windPoints.visible = WEATHER.windOn;
  windMat.opacity = WEATHER.windOn ? Math.min(0.8, 0.2 + (pct / 100) * 0.5) : 0.0;
  windMat.size = 0.10 + (pct / 100) * 0.25;
}}

function updateQuakeSliderLabel() {{
  const pct = parseInt(document.getElementById('sldQuake').value, 10);
  document.getElementById('valQuake').textContent = pct + '%';
}}

document.getElementById('sldSnow').addEventListener('input', updateSnowVisual);
document.getElementById('sldRain').addEventListener('input', updateRainVisual);
document.getElementById('sldWind').addEventListener('input', updateWindVisual);
document.getElementById('sldQuake').addEventListener('input', updateQuakeSliderLabel);
updateSnowVisual(); updateRainVisual(); updateWindVisual(); updateQuakeSliderLabel();

document.getElementById('btnQuake').addEventListener('click', () => {{
  startEarthquake();
}});

let __lastFrameTime = performance.now();
(function animate() {{
  requestAnimationFrame(animate);
  const __now = performance.now();
  const dt = Math.min((__now - __lastFrameTime) / 1000, 0.05);
  __lastFrameTime = __now;
  if (WEATHER.snowOn) updateSnow(dt);
  if (WEATHER.rainOn) updateRain(dt);
  if (WEATHER.windOn) updateWind(dt);
  updateEarthquake();
  controls.update();
  renderer.render(scene, camera);
  lblRen.render(scene, camera);
}})();

window.addEventListener('resize', () => {{
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  lblRen.setSize(innerWidth, innerHeight);
}});

window.addEventListener('load', () => {{
  const l = document.getElementById('loading');
  if (l) l.style.display = 'none';
}});
setTimeout(() => {{
  const l = document.getElementById('loading');
  if (l) l.style.display = 'none';
}}, 1200);
</script>
</body>
</html>"""
    return html


def calculate_construction_materials(params):
    """Bitta params dict qabul qiladigan versiya - LMK/LSTK bilan"""
    
    # Parametrlarni olish
    L = params.get("L", 30)
    W = params.get("W", 15)
    H = params.get("H", 7.5)
    roof_pitch = params.get("roof_pitch", 12)
    column_spacing = params.get("column_spacing", 8.5)
    system_type = params.get("construction_system", "LMK (Yengil Metall)")
    wall_type = params.get("wall_type", "Sendvich Panel")
    roof_type = params.get("roof_type", "Sendvich panel")
    floor_type = params.get("floor_type", "Sanoat Betoni")
    floor_panel_mode = params.get("floor_panel_mode", False)
    
    window_count_front = params.get("window_count_front", 3)
    window_count_back = params.get("window_count_back", 3)
    window_count_left = params.get("window_count_left", 0)
    window_count_right = params.get("window_count_right", 0)
    
    door_front_count = params.get("door_front_count", 1)
    door_front_width = params.get("door_front_width", 12.0)
    door_front_height = params.get("door_front_height", 6.5)
    
    door_back_count = params.get("door_back_count", 0)
    door_back_width = params.get("door_back_width", 12.0)
    door_back_height = params.get("door_back_height", 6.5)
    
    door_left_count = params.get("door_left_count", 0)
    door_left_width = params.get("door_left_width", 5.0)
    door_left_height = params.get("door_left_height", 4.0)
    
    door_right_count = params.get("door_right_count", 0)
    door_right_width = params.get("door_right_width", 5.0)
    door_right_height = params.get("door_right_height", 4.0)
    
    window_width = params.get("window_width", 2.5)
    window_height = params.get("window_height", 2.0)
    
    wall_price = params.get("wall_price", 35)
    roof_price = params.get("roof_price", 45)
    floor_price = params.get("floor_price", 45)
    window_price = params.get("window_price", 45)
    door_price = params.get("door_price", 28)
    
    price_column = params.get("price_metal_column", 950)
    price_beam = params.get("price_metal_beam", 950)
    price_truss = params.get("price_metal_truss", 950)
    price_longitudinal = params.get("price_metal_longitudinal", 950)
    
    concrete_price = params.get("price_concrete", 85)
    cement_price = params.get("price_cement", 0.09)
    sand_price = params.get("price_sand", 35)
    gravel_price = params.get("price_gravel", 40)
    rebar_price = params.get("price_rebar", 0.85)
    shipyak_price = params.get("price_shipyak", 30)
    labor_percent = params.get("labor_percent", 32)
    
    pitch_rad = math.radians(roof_pitch)
    roof_multiplier = 1 / math.cos(pitch_rad) if roof_pitch > 0 else 1.0
    
    # ============================================================
    # 1. PANEL O'LCHAMLARI - BALANDLIKKA QARAB
    # ============================================================
    MAX_PANEL_HEIGHT = 12.0  # Standart panel uzunligi
    
    if H > MAX_PANEL_HEIGHT:
        panel_sections = math.ceil(H / MAX_PANEL_HEIGHT)
        panel_height = H / panel_sections
        panel_note = f"{panel_sections} qismga bo'linadi"
    else:
        panel_sections = 1
        panel_height = H
        panel_note = "Standart panel"
    
    PANEL_WIDTH = 1.0
    
    # ============================================================
    # 2. DEVOR MAYDONLARI
    # ============================================================
    front_wall_area = L * H
    front_door_area = door_front_count * (door_front_width * door_front_height)
    front_window_area = window_count_front * (window_width * window_height)
    front_net = max(0, front_wall_area - front_door_area - front_window_area)
    front_panels = math.ceil(front_net / (PANEL_WIDTH * panel_height)) * panel_sections
    
    back_wall_area = L * H
    back_door_area = door_back_count * (door_back_width * door_back_height)
    back_window_area = window_count_back * (window_width * window_height)
    back_net = max(0, back_wall_area - back_door_area - back_window_area)
    back_panels = math.ceil(back_net / (PANEL_WIDTH * panel_height)) * panel_sections
    
    left_wall_area = W * H
    left_door_area = door_left_count * (door_left_width * door_left_height)
    left_window_area = window_count_left * (window_width * window_height)
    left_net = max(0, left_wall_area - left_door_area - left_window_area)
    left_panels = math.ceil(left_net / (PANEL_WIDTH * panel_height)) * panel_sections
    
    right_wall_area = W * H
    right_door_area = door_right_count * (door_right_width * door_right_height)
    right_window_area = window_count_right * (window_width * window_height)
    right_net = max(0, right_wall_area - right_door_area - right_window_area)
    right_panels = math.ceil(right_net / (PANEL_WIDTH * panel_height)) * panel_sections
    
    net_wall_area = front_net + back_net + left_net + right_net
    total_wall_panels = front_panels + back_panels + left_panels + right_panels
    
    # ============================================================
    # 3. FRONTON
    # ============================================================
    if roof_pitch > 0 and W > 0:
        ridge_rise = (W / 2) * math.tan(pitch_rad)
        gable_area = 2 * (0.5 * W * ridge_rise)
    else:
        ridge_rise = 0.0
        gable_area = 0.0
    
    gable_panels = math.ceil(gable_area / (PANEL_WIDTH * ridge_rise)) if gable_area > 0 and ridge_rise > 0 else 0
    
    floor_area = L * W
    roof_area = L * W * roof_multiplier
    
    # ============================================================
    # 4. TOM PANELLARI
    # ============================================================
    if roof_pitch > 0 and W > 0:
        roof_panels = math.ceil(L / PANEL_WIDTH) * 2
    else:
        roof_panels = math.ceil(L / PANEL_WIDTH) * math.ceil(W / PANEL_WIDTH)
    
    # ============================================================
    # 5. POL PANELLARI
    # ============================================================
    if floor_panel_mode:
        floor_panels = math.ceil(L / PANEL_WIDTH) * math.ceil(W / PANEL_WIDTH)
    else:
        floor_panels = 0
    
    # ============================================================
    # 6. METALL HISOBI
    # ============================================================
    metal = compute_metal_quantities(L, W, H, roof_pitch, column_spacing, system_type)


    
    # ============================================================
    # 7. NARXLAR
    # ============================================================
    column_cost = metal["column_tonna"] * price_column
    beam_cost = metal["beam_tonna"] * price_beam
    truss_cost = metal["truss_tonna"] * price_truss
    longitudinal_cost = metal["longitudinal_tonna"] * price_longitudinal
    metal_karkas_cost = column_cost + beam_cost + truss_cost + longitudinal_cost
    
    wall_cost = net_wall_area * wall_price
    gable_wall_cost = gable_area * wall_price
    roof_cost = roof_area * roof_price
    floor_cost = floor_area * floor_price
    
    total_windows = window_count_front + window_count_back + window_count_left + window_count_right
    total_doors = door_front_count + door_back_count + door_left_count + door_right_count
    
    total_window_area = total_windows * (window_width * window_height)
    window_cost_total = total_window_area * window_price
    
    total_door_area = (
        door_front_count * (door_front_width * door_front_height) +
        door_back_count * (door_back_width * door_back_height) +
        door_left_count * (door_left_width * door_left_height) +
        door_right_count * (door_right_width * door_right_height)
    )
    door_cost_total = total_door_area * door_price
    
    foundation_concrete = metal["total_columns"] * 1.0 * (1 + (H - 7.5) * 0.02 if H > 7.5 else 1.0)
    floor_concrete = floor_area * 0.15
    total_concrete = foundation_concrete + floor_concrete
    
    concrete_cost = total_concrete * concrete_price
    rebar_kg = total_concrete * 55
    rebar_cost = rebar_kg * rebar_price
    sand_m3 = total_concrete * 0.55
    gravel_m3 = total_concrete * 0.75
    sand_cost = sand_m3 * sand_price
    gravel_cost = gravel_m3 * gravel_price
    cement_kg = total_concrete * 320
    cement_cost = cement_kg * cement_price
    shipyak_cost = floor_area * shipyak_price
    
    material_total = (
        metal_karkas_cost + wall_cost + gable_wall_cost + roof_cost + floor_cost +
        concrete_cost + rebar_cost + window_cost_total + door_cost_total +
        sand_cost + gravel_cost + cement_cost + shipyak_cost
    )
    labor_cost = material_total * (labor_percent / 100)
    total_cost = material_total + labor_cost
    
    return {
        "floor_area_m2": round(floor_area, 1),
        "wall_area_m2": round(2 * (L + W) * H, 1),
        "roof_area_m2": round(roof_area, 1),
        "gable_area_m2": round(gable_area, 1),
        "net_wall_area_m2": round(net_wall_area, 1),
        "total_volume_m3": round(L * W * H, 1),
        
        "panel_width_m": PANEL_WIDTH,
        "panel_height_m": panel_height,
        "panel_sections": panel_sections,
        "panel_note": panel_note,
        
        "gable_panels": gable_panels,
        "front_panels": front_panels,
        "back_panels": back_panels,
        "left_panels": left_panels,
        "right_panels": right_panels,
        "total_wall_panels": total_wall_panels,
        "roof_panels": roof_panels,
        "floor_panels": floor_panels,
        "floor_panel_mode": floor_panel_mode,
        
        "front_wall_net": round(front_net, 1),
        "back_wall_net": round(back_net, 1),
        "left_wall_net": round(left_net, 1),
        "right_wall_net": round(right_net, 1),
        
        "window_count": total_windows,
        "door_count": total_doors,
        "window_area_m2": round(total_window_area, 1),
        "door_area_m2": round(total_door_area, 1),
        
        "concrete_volume_m3": round(total_concrete, 1),
        "sand_m3": round(sand_m3, 1),
        "gravel_m3": round(gravel_m3, 1),
        "cement_kg": round(cement_kg),
        "rebar_kg": round(rebar_kg),
        
        "total_columns": metal["total_columns"],
        "truss_count": metal["truss_count"],
        "column_meters": metal["column_meters"],
        "column_kg": metal["column_kg"],
        "column_tonna": metal["column_tonna"],
        "beam_meters": metal["beam_meters"],
        "beam_kg": metal["beam_kg"],
        "beam_tonna": metal["beam_tonna"],
        "truss_meters": metal["truss_meters"],
        "truss_kg": metal["truss_kg"],
        "truss_tonna": metal["truss_tonna"],
        "longitudinal_meters": metal["longitudinal_meters"],
        "longitudinal_kg": metal["longitudinal_kg"],
        "longitudinal_tonna": metal["longitudinal_tonna"],
        "metal_tonna": metal["total_metal_tonna"],
        "metal_kg": metal["total_metal_kg"],
        "column_height_factor": metal.get("column_height_factor", 1.0),
        "column_actual_kg_m": metal.get("column_actual_kg_m", 32.0),
        
        "metal_karkas_cost": round(metal_karkas_cost),
        "column_cost": round(column_cost),
        "beam_cost": round(beam_cost),
        "truss_cost": round(truss_cost),
        "longitudinal_cost": round(longitudinal_cost),
        "wall_cost": round(wall_cost),
        "gable_wall_cost": round(gable_wall_cost),
        "roof_cost": round(roof_cost),
        "floor_cost": round(floor_cost),
        "window_cost": round(window_cost_total),
        "door_cost": round(door_cost_total),
        "concrete_cost": round(concrete_cost),
        "rebar_cost": round(rebar_cost),
        "cement_cost": round(cement_cost),
        "sand_cost": round(sand_cost),
        "gravel_cost": round(gravel_cost),
        "shipyak_cost": round(shipyak_cost),
        "labor_cost": round(labor_cost),
        "material_total": round(material_total),
        "total_cost": round(total_cost),
        
        "wall_price": wall_price,
        "roof_price": roof_price,
        "floor_price": floor_price,
        "window_price": window_price,
        "door_price": door_price,
        "labor_percent": labor_percent,
        "construction_system": system_type,
        "connection_type": metal.get("connection_type", "welded"),
        "service_life": metal.get("service_life", 50),
        "corrosion_protection": metal.get("corrosion_protection", False),
    }

# ============================================================
# ========== YANGI QO'SHILADIGAN FUNKSIYALAR ==========
def compute_purlins(L, W, H, roof_pitch, purlin_profile="Profil 120x60x4 mm", 
                    wall_purlin_profile="Profil 100x50x4 mm", 
                    bracing_profile="Shveller 14P", panel_width=1.0,
                    system_type="LMK (Yengil Metall)", factors=None):
    """
    Progonlar (purlins) hisobi - LMK/LSTK uchun
    """
    if factors is None:
        factors = get_construction_system_factors(system_type, L, W, H)
    
    pitch_rad = math.radians(roof_pitch)
    
    # Progonlarning kg/m og'irliklari
    purlin_kg_m = get_profile_weight("purlin", purlin_profile) * factors["weight_multiplier"]
    wall_purlin_kg_m = get_profile_weight("purlin", wall_purlin_profile) * factors["weight_multiplier"]
    bracing_kg_m = get_profile_weight("bracing", bracing_profile) * factors["weight_multiplier"]
    
    # ===== 1. DEVOR PROGONLARI =====
    if H <= 4:
        wall_rows = 2
    elif H <= 6:
        wall_rows = 3
    elif H <= 8:
        wall_rows = 4
    elif H <= 10:
        wall_rows = 5
    elif H <= 12:
        wall_rows = 6
    elif H <= 14:
        wall_rows = 7
    elif H <= 16:
        wall_rows = 8
    elif H <= 18:
        wall_rows = 9
    else:
        wall_rows = 10
    
    # 🔽 LSTK uchun progonlar oralig'i kichikroq
    if "LSTK" in system_type:
        wall_rows = min(wall_rows + 2, 12)  # Ko'proq progon
    
    wall_purlins_m = wall_rows * 2 * (L + W)
    wall_purlins_kg = wall_purlins_m * wall_purlin_kg_m
    
    # ===== 2. TOM PROGONLARI =====
    if roof_pitch <= 5:
        roof_rows = 3
    elif roof_pitch <= 15:
        roof_rows = 4
    elif roof_pitch <= 25:
        roof_rows = 5
    else:
        roof_rows = 6
    
    # 🔽 LSTK uchun ko'proq progon
    if "LSTK" in system_type:
        roof_rows += 1
    
    slope_length = W / (2 * math.cos(pitch_rad)) if roof_pitch > 0 else W / 2
    roof_purlins_m = roof_rows * 2 * slope_length * 2
    roof_purlins_kg = roof_purlins_m * purlin_kg_m
    
    # ===== 3. QOSHIMCHA =====
    wind_braces_m = 0
    extra_braces_m = 0
    if H > 15:
        wind_braces_m = int(H / 5) * (L + W) * 0.5
        extra_braces_m = (H - 15) * 2 * (L + W) * 0.2
    
    wind_braces_kg = wind_braces_m * bracing_kg_m
    extra_braces_kg = extra_braces_m * bracing_kg_m
    
    # ===== 4. QOSHIMCHA OGIRLIK =====
    additional = (wall_purlins_kg + roof_purlins_kg) * 0.08 * factors["weight_multiplier"]
    
    # ===== 5. JAMI =====
    total_kg = wall_purlins_kg + roof_purlins_kg + wind_braces_kg + extra_braces_kg + additional
    total_m = wall_purlins_m + roof_purlins_m + wind_braces_m + extra_braces_m
    
    return {
        "wall_rows": wall_rows,
        "roof_rows": roof_rows,
        "wall_purlins_m": round(wall_purlins_m, 1),
        "roof_purlins_m": round(roof_purlins_m, 1),
        "wind_braces_m": round(wind_braces_m, 1),
        "extra_braces_m": round(extra_braces_m, 1),
        "total_m": round(total_m, 1),
        "wall_purlins_kg": round(wall_purlins_kg, 1),
        "roof_purlins_kg": round(roof_purlins_kg, 1),
        "wind_braces_kg": round(wind_braces_kg, 1),
        "extra_braces_kg": round(extra_braces_kg, 1),
        "additional_kg": round(additional, 1),
        "total_kg": round(total_kg, 1),
        "total_tonna": round(total_kg / 1000, 3),
        "purlin_profile": purlin_profile,
        "purlin_kg_m": round(purlin_kg_m, 2),
        "wall_purlin_profile": wall_purlin_profile,
        "wall_purlin_kg_m": round(wall_purlin_kg_m, 2),
        "bracing_profile": bracing_profile,
        "bracing_kg_m": round(bracing_kg_m, 2),
    }
def compute_bracing(L, W, H, seismic_zone, wind_region="B"):
    """
    SNiP II-23-81 bo'yicha bog'lamalar hisobi
    """
    horizontal_spacing = 6.0
    n_horizontal = int(math.ceil(max(L, W) / horizontal_spacing))
    horizontal_m = n_horizontal * (L + W) * 0.3
    
    vertical_spacing = 6.0
    n_vertical_x = int(math.ceil(L / vertical_spacing))
    n_vertical_z = int(math.ceil(W / vertical_spacing))
    vertical_m = (n_vertical_x + n_vertical_z) * H * 0.5
    
    seismic_coeff = 1.0
    seismic_m = (L + W) * 0.3 * seismic_coeff
    
    diagonal_m = math.sqrt(L**2 + W**2) * 0.5 
    
    total_m = horizontal_m + vertical_m + seismic_m + diagonal_m
    weight_per_m = 15.0
    total_kg = total_m * weight_per_m
    
    return {
        "horizontal_m": round(horizontal_m, 1),
        "vertical_m": round(vertical_m, 1),
        "seismic_m": round(seismic_m, 1),
        "diagonal_m": round(diagonal_m, 1),
        "total_m": round(total_m, 1),
        "weight_per_m": weight_per_m,
        "total_kg": round(total_kg, 1),
        "total_tonna": round(total_kg / 1000, 3)
    }


def compute_connections(metal_kg, connection_type="mixed"):
    """
    SNiP II-23-81 bo'yicha birikma detallari
    """
    coefficients = {
        "bolted": {"default": 0.065},
        "welded": {"default": 0.05},
        "mixed": {"default": 0.08}
    }
    
    coeff = coefficients.get(connection_type, coefficients["mixed"])
    weight_kg = metal_kg * coeff["default"]
    
    details_count = {
        "bolts": int(metal_kg / 500),
        "plates": int(metal_kg / 1000) + 1,
        "welds_m": int(metal_kg / 200)
    }
    
    return {
        "type": connection_type,
        "coefficient": coeff["default"],
        "weight_kg": round(weight_kg, 1),
        "weight_tonna": round(weight_kg / 1000, 3),
        "details": details_count
    }

def calculate_advanced_materials(params):
    """Qo'shimcha hisob-kitoblar bilan (seysmik, muhandislik, progonlar, bog'lamalar, birikmalar)"""
    materials = calculate_construction_materials(params)
    
    # ===== 1. PROGONLAR (PURLINS) HISOBI =====
    L = params.get("L", 30)
    W = params.get("W", 15)
    H = params.get("H", 7.5)
    roof_pitch = params.get("roof_pitch", 12)
    column_spacing = params.get("column_spacing", 8.5)
    
    # Profil ma'lumotlarini olish
    purlin_profile = params.get("purlin_profile", "Profil 120x60x4 mm")
    wall_purlin_profile = params.get("wall_purlin_profile", "Profil 100x50x4 mm")
    bracing_profile = params.get("bracing_profile", "Shveller 14P")
    
    # Profillarni uzatish
    purlins = compute_purlins(
        L, W, H, roof_pitch,
        purlin_profile=purlin_profile,
        wall_purlin_profile=wall_purlin_profile,
        bracing_profile=bracing_profile
    )
    
    # Progon ma'lumotlarini materials ga qo'shish
    materials["purlins_wall_m"] = purlins["wall_purlins_m"]
    materials["purlins_roof_m"] = purlins["roof_purlins_m"]
    materials["purlins_total_m"] = purlins["total_m"]
    materials["purlins_wall_kg"] = purlins["wall_purlins_kg"]
    materials["purlins_roof_kg"] = purlins["roof_purlins_kg"]
    materials["purlins_total_kg"] = purlins["total_kg"]
    materials["purlins_total_tonna"] = purlins["total_tonna"]
    
    # Profil ma'lumotlari
    materials["purlin_profile"] = purlin_profile
    materials["purlin_kg_m"] = purlins["purlin_kg_m"]
    materials["wall_purlin_profile"] = wall_purlin_profile
    materials["wall_purlin_kg_m"] = purlins["wall_purlin_kg_m"]
    materials["bracing_profile"] = bracing_profile
    materials["bracing_kg_m"] = purlins["bracing_kg_m"]
    
    # Progonlar narxi (1 tonna uchun)
    purlin_price_per_ton = params.get("price_metal_purlins", 950)
    purlins_cost = purlins["total_tonna"] * purlin_price_per_ton
    materials["purlins_cost"] = round(purlins_cost)
    
    # ===== 2. BOG'LAMALAR (BRACING) HISOBI =====
    seismic_zone = params.get("seismic_zone", 8)
    wind_region = params.get("wind_region", "B")
    
    bracing = compute_bracing(L, W, H, seismic_zone, wind_region)
    materials["bracing_horizontal_m"] = bracing["horizontal_m"]
    materials["bracing_vertical_m"] = bracing["vertical_m"]
    materials["bracing_seismic_m"] = bracing["seismic_m"]
    materials["bracing_diagonal_m"] = bracing["diagonal_m"]
    materials["bracing_total_m"] = bracing["total_m"]
    materials["bracing_kg"] = bracing["total_kg"]
    materials["bracing_tonna"] = bracing["total_tonna"]
    
    # Bog'lamalar narxi (1 tonna uchun)
    bracing_price_per_ton = params.get("price_metal_bracing", 950)
    bracing_cost = bracing["total_tonna"] * bracing_price_per_ton
    materials["bracing_cost"] = round(bracing_cost)
    
    # ===== 3. ORIGINAL METALLNI SAQLASH =====
    # Asosiy metall (progonsiz) ni saqlab qolamiz
    materials["metal_tonna_original"] = materials.get("metal_tonna_original", materials["metal_tonna"])
    materials["metal_kg_original"] = materials.get("metal_kg_original", materials["metal_kg"])
    
    # ===== 4. BIRIKMA DETALLARI (CONNECTIONS) HISOBI =====
    # 🔽 ORIGINAL METALL + PROGONLAR + BOG'LAMALAR (YANGI MATERIALS["METAL_KG"] EMAS!)
    total_metal_for_connections = (
        materials["metal_kg_original"] +   # 🔽 ORIGINAL (progonsiz)
        purlins["total_kg"] + 
        bracing["total_kg"]
    )
    
    connection_type = params.get("connection_type", "mixed")
    connections = compute_connections(total_metal_for_connections, connection_type)
    materials["connection_type"] = connection_type
    materials["connection_coefficient"] = connections["coefficient"]
    materials["connection_kg"] = connections["weight_kg"]
    materials["connection_tonna"] = connections["weight_tonna"]
    materials["connection_bolts"] = connections["details"]["bolts"]
    materials["connection_plates"] = connections["details"]["plates"]
    materials["connection_welds_m"] = connections["details"]["welds_m"]
    
    # Birikma detallari narxi (1 tonna uchun)
    connection_price_per_ton = params.get("price_metal_connection", 950)
    connection_cost = connections["weight_tonna"] * connection_price_per_ton
    materials["connection_cost"] = round(connection_cost)
    
    # ===== 5. JAMI METALL (PROGONLAR BILAN BIRGA) =====
    # 🔽 MUHIM: ORIGINAL + PROGONLAR + BOG'LAMALAR + BIRIKMALAR
    materials["metal_kg_with_purlins"] = (
        materials["metal_kg_original"] + 
        purlins["total_kg"] + 
        bracing["total_kg"] + 
        connections["weight_kg"]
    )
    materials["metal_tonna_with_purlins"] = round(
        materials["metal_kg_with_purlins"] / 1000, 3
    )
    
    # 🔽 Asosiy ko'rsatkichda ko'rsatiladigan metall tonnaji (YANGILANDI)
    materials["metal_kg"] = materials["metal_kg_with_purlins"]
    materials["metal_tonna"] = materials["metal_tonna_with_purlins"]
    
    # ===== 6. YANGILANGAN METALL KARKAS NARXI =====
    # Eski metall narxiga progonlar, bog'lamalar va birikmalarni qo'shamiz
    updated_metal_karkas_cost = (
        materials["metal_karkas_cost"] + 
        materials["purlins_cost"] + 
        materials["bracing_cost"] + 
        materials["connection_cost"]
    )
    materials["updated_metal_karkas_cost"] = round(updated_metal_karkas_cost)
    materials["metal_karkas_cost"] = round(updated_metal_karkas_cost)
    
    # ===== 7. SEYSiMIK QO'SHIMCHA =====
    seismic_factors = {7: 0.1, 8: 0.2, 9: 0.3}
    seismic_factor = seismic_factors.get(seismic_zone, 0.15)
    seismic_extra_cost = materials["metal_karkas_cost"] * seismic_factor
    materials["seismic_extra_cost"] = round(seismic_extra_cost)
    materials["seismic_factor"] = seismic_factor
    
    # ===== 8. MUHANDISLIK TIZIMLARI =====
    engineering_cost = 0
    engineering_details = {}
    
    if params.get("heating") != "Yoq":
        heating_cost = materials["floor_area_m2"] * 25
        engineering_cost += heating_cost
        engineering_details["heating"] = round(heating_cost)
    
    if params.get("ventilation") != "Tabiiy":
        ventilation_cost = materials["floor_area_m2"] * 15
        engineering_cost += ventilation_cost
        engineering_details["ventilation"] = round(ventilation_cost)
    
    if params.get("electricity") != "Standart":
        electricity_cost = materials["floor_area_m2"] * 20
        engineering_cost += electricity_cost
        engineering_details["electricity"] = round(electricity_cost)
    
    if params.get("plumbing") != "Yoq":
        plumbing_cost = materials["floor_area_m2"] * 18
        engineering_cost += plumbing_cost
        engineering_details["plumbing"] = round(plumbing_cost)
    
    materials["engineering_systems_cost"] = round(engineering_cost)
    materials["engineering_details"] = engineering_details
    
    # ===== 9. YANGILANGAN MATERIAL TOTAL =====
    updated_material_total = (
        materials["material_total"] + 
        materials["purlins_cost"] + 
        materials["bracing_cost"] + 
        materials["connection_cost"]
    )
    materials["updated_material_total"] = round(updated_material_total)
    materials["material_total"] = round(updated_material_total)
    
    # ===== 10. JAMI HISOB =====
    optimized_total = (
        materials["material_total"] + 
        materials["labor_cost"] + 
        seismic_extra_cost + 
        engineering_cost
    )
    materials["optimized_total"] = round(optimized_total)
    materials["cost_per_m2"] = round(
        optimized_total / materials["floor_area_m2"], 1
    ) if materials["floor_area_m2"] > 0 else 0
    
    # ===== 11. QO'SHIMCHA METRIK MA'LUMOTLAR =====
    materials["total_metal_with_purlins_kg"] = materials["metal_kg_with_purlins"]
    materials["total_metal_with_purlins_tonna"] = materials["metal_tonna_with_purlins"]
    
    # ===== 12. XULOSA MA'LUMOTLARI =====
    materials["summary"] = {
        "asosiy_metall_tonna": materials["metal_tonna_original"],
        "progonlar_tonna": purlins["total_tonna"],
        "boglamalar_tonna": bracing["total_tonna"],
        "birikmalar_tonna": connections["weight_tonna"],
        "jami_metall_tonna": materials["metal_tonna"],
        "materiallar_narxi": materials["material_total"],
        "ishchi_kuchi_narxi": materials["labor_cost"],
        "seysmik_qoshimcha": seismic_extra_cost,
        "muhandislik_narxi": engineering_cost,
        "jami_narx": optimized_total,
        "1m2_narxi": materials["cost_per_m2"]
    }
    
    return materials







def draw_sheet_layout(ax, title_text, detail_num, scale="1:10", doc_code="EP-001-KM"):
    """
    Draws a standard O'zDSt / GOST border and stamp (title block) on the drawing sheet.
    The sheet canvas dimensions are standard: x in [-2.0, 10.0], y in [-2.0, 8.0].
    """
    # Outer frame
    frame = patches.Rectangle((-1.9, -1.9), 11.8, 9.8, linewidth=1.5, edgecolor='#0F172A', facecolor='none', zorder=1)
    ax.add_patch(frame)
    
    # Inner border (5mm from top/right/bottom, 20mm from left for binding)
    border = patches.Rectangle((-1.5, -1.75), 11.2, 9.5, linewidth=1, edgecolor='#0F172A', facecolor='none', zorder=1)
    ax.add_patch(border)
    
    # Grid background (subtle CAD grid)
    ax.grid(True, which='both', color='#F1F5F9', linestyle='-', linewidth=0.5, zorder=0)
    
    # Stamp (Title Block) in the bottom right corner
    stamp_x, stamp_y = 5.2, -1.75
    stamp_w, stamp_h = 4.5, 1.3
    
    stamp_border = patches.Rectangle((stamp_x, stamp_y), stamp_w, stamp_h, linewidth=1.5, edgecolor='#0F172A', facecolor='#F8FAFC', zorder=10)
    ax.add_patch(stamp_border)
    
    # Stamp internal line grid (4 rows, 2 columns)
    for ry in [0.325, 0.65, 0.975]:
        ax.plot([stamp_x, stamp_x + stamp_w], [stamp_y + ry, stamp_y + ry], color='#0F172A', linewidth=0.8, zorder=11)
        
    # Vertical line dividing left names from right details
    ax.plot([stamp_x + 1.8, stamp_x + 1.8], [stamp_y, stamp_y + stamp_h], color='#0F172A', linewidth=0.8, zorder=11)
    
    # Left Column (x in [5.2, 7.0]): Names and roles
    ax.text(stamp_x + 0.08, stamp_y + 1.10, "Loyiha / Project: Cold Room", fontsize=6, color='#0F172A', fontweight='bold', va='center', zorder=12)
    ax.text(stamp_x + 0.08, stamp_y + 0.78, "Chizdi / Drawn: Antigravity AI", fontsize=6, color='#0F172A', va='center', zorder=12)
    ax.text(stamp_x + 0.08, stamp_y + 0.46, "Tekshirdi / Checked: Arch Dept", fontsize=6, color='#0F172A', va='center', zorder=12)
    ax.text(stamp_x + 0.08, stamp_y + 0.14, f"Sana / Date: {datetime.now().strftime('%m.%Y')}", fontsize=6, color='#0F172A', va='center', zorder=12)
    
    # Right Column (x in [7.0, 9.7]): Project/sheet details
    disp_title = title_text.split('/')[0].strip() if '/' in title_text else title_text
    if len(disp_title) > 28:
        disp_title = disp_title[:26] + "..."
    ax.text(stamp_x + 1.88, stamp_y + 1.10, f"Mavzu / Title: {disp_title}", fontsize=6, color='#0F172A', fontweight='bold', va='center', zorder=12)
    ax.text(stamp_x + 1.88, stamp_y + 0.78, f"Hujjat / Doc: {doc_code}", fontsize=6, color='#1E3A8A', fontweight='bold', va='center', zorder=12)
    ax.text(stamp_x + 1.88, stamp_y + 0.46, f"Masshtab / Scale: {scale}", fontsize=6, color='#0F172A', va='center', zorder=12)
    ax.text(stamp_x + 1.88, stamp_y + 0.14, f"Varaq / Sheet: {detail_num}", fontsize=6.5, color='#0F172A', fontweight='bold', va='center', zorder=12)
    
    # Sheet Main Title
    ax.text(3.5, 7.3, title_text, fontsize=11, color='#0F172A', fontweight='bold', ha='center', zorder=12)
    ax.text(3.5, 6.9, f"KONSTRUKTIV DETAL / CONSTRUCTION DETAIL {detail_num}", fontsize=7.5, color='#475569', fontweight='bold', ha='center', zorder=12)
    ax.text(3.5, 6.6, "O'zDSt / GOST standartlari asosida chizilgan", fontsize=6.5, color='#94A3B8', style='italic', ha='center', zorder=12)

def draw_dimension_h(ax, x1, x2, y, val_mm, text_y_offset=0.15, tick_size=0.12, color='#1E3A8A'):
    """
    Draws a horizontal dimension line with standard 45-degree slashes/ticks at the ends.
    """
    # Main dimension line
    ax.plot([x1, x2], [y, y], color=color, linewidth=0.9, zorder=15)
    
    # Extension lines
    ax.plot([x1, x1], [y - 0.25, y + 0.25], color=color, linewidth=0.6, zorder=15)
    ax.plot([x2, x2], [y - 0.25, y + 0.25], color=color, linewidth=0.6, zorder=15)
    
    # 45-degree slash ticks
    ax.plot([x1 - tick_size, x1 + tick_size], [y - tick_size, y + tick_size], color=color, linewidth=1.5, zorder=16)
    ax.plot([x2 - tick_size, x2 + tick_size], [y - tick_size, y + tick_size], color=color, linewidth=1.5, zorder=16)
    
    # Value text placed above the line
    ax.text((x1 + x2) / 2, y + text_y_offset, str(val_mm), fontsize=7.5, color=color, fontweight='bold', ha='center', va='bottom', zorder=17)

def draw_dimension_v(ax, x, y1, y2, val_mm, text_x_offset=-0.15, tick_size=0.12, color='#1E3A8A'):
    """
    Draws a vertical dimension line with standard 45-degree slashes/ticks at the ends.
    """
    # Main dimension line
    ax.plot([x, x], [y1, y2], color=color, linewidth=0.9, zorder=15)
    
    # Extension lines
    ax.plot([x - 0.25, x + 0.25], [y1, y1], color=color, linewidth=0.6, zorder=15)
    ax.plot([x - 0.25, x + 0.25], [y2, y2], color=color, linewidth=0.6, zorder=15)
    
    # 45-degree slash ticks
    ax.plot([x - tick_size, x + tick_size], [y1 - tick_size, y1 + tick_size], color=color, linewidth=1.5, zorder=16)
    ax.plot([x - tick_size, x + tick_size], [y2 - tick_size, y2 + tick_size], color=color, linewidth=1.5, zorder=16)
    
    # Value text (rotated) placed to the left of the line
    ax.text(x + text_x_offset, (y1 + y2) / 2, str(val_mm), fontsize=7.5, color=color, fontweight='bold', ha='right', va='center', rotation=90, zorder=17)

def draw_leader(ax, x_start, y_start, x_end, y_end, text, shelf_w=0.8, color='#334155'):
    """
    Draws a construction detail leader (annotative pointer) pointing to a specific layer/material.
    """
    # Connection dot at the target point
    dot = plt.Circle((x_start, y_start), 0.04, color=color, fill=True, zorder=20)
    ax.add_patch(dot)
    
    # Diagonal leader line
    ax.plot([x_start, x_end], [y_start, y_end], color=color, linewidth=0.8, zorder=20)
    
    # Horizontal shelf line
    shelf_end_x = x_end + shelf_w if x_end >= x_start else x_end - shelf_w
    ax.plot([x_end, shelf_end_x], [y_end, y_end], color=color, linewidth=0.8, zorder=20)
    
    # Descriptive text placed above the shelf
    ha_align = 'left' if x_end >= x_start else 'right'
    text_x = x_end + 0.05 if x_end >= x_start else x_end - 0.05
    ax.text(text_x, y_end + 0.05, text, fontsize=7, color='#0F172A', fontweight='medium', ha=ha_align, va='bottom', zorder=21)

def create_architectural_drawings(params, materials=None):
    """
    Generates extremely detailed and professional structural detail drawings for Streamlit application.
    Returns a dictionary of Matplotlib Figure objects.
    
    Scale: 1:10 / 1:5, complying with O'zDSt standard drawings.
    """
    drawings = {}
    
    # Retrieve dynamic dimensions from params
    d_qalin_str = params.get("d_qalin", "100mm")
    try:
        wall_t_mm = int(d_qalin_str.replace("mm", "").strip())
    except:
        wall_t_mm = 100
        
    pol_qalin_str = params.get("pol_qalin", "100mm")
    try:
        floor_t_mm = int(pol_qalin_str.replace("mm", "").strip())
    except:
        floor_t_mm = 100
        
    p_qalin_str = params.get("p_qalin", "100mm")
    try:
        roof_t_mm = int(p_qalin_str.replace("mm", "").strip())
    except:
        roof_t_mm = 100
        
    project_name = params.get("project_name", "EP-001 Warehouse")
    if not project_name:
        project_name = "EP-001 Warehouse"
    room_code = params.get("room_code", "EP-001")
    
    # ============================================================
    # ASOSIY CHIZMALAR (REJA, FASAD, KESIM, IZOMETRIK)
    # ============================================================
    
    # ---- REJA (TOP VIEW) ----
    def create_floor_plan():
        L = params.get("L", 30)
        W = params.get("W", 15)
        
        fig, ax = plt.subplots(figsize=(16, 11), dpi=120)
        ax.set_facecolor('white')
        fig.patch.set_facecolor('white')
        ax.set_aspect('equal')
        
        # ASOSIY BINO
        rect = patches.Rectangle((0, 0), L, W, linewidth=2.5, edgecolor='#000000', facecolor='none', zorder=1)
        ax.add_patch(rect)
        
        # USTUNLAR
        layout = compute_column_layout(L, W)
        for i in range(layout["n_cols_x"]):
            for j in range(layout["n_cols_z"]):
                x = i * layout["spacing_x"]
                z = j * layout["spacing_z"]
                size = 0.3
                col = patches.Rectangle((x - size/2, z - size/2), size, size,
                                       linewidth=1.5, edgecolor='#FF0000',
                                       facecolor='none', zorder=2)
                ax.add_patch(col)
                ax.plot([x - size/2.5, x + size/2.5], [z, z], color='#FF0000', linewidth=1.5, zorder=3)
                ax.plot([x, x], [z - size/2.5, z + size/2.5], color='#FF0000', linewidth=1.5, zorder=3)
                ax.text(x, z - 0.4, f'C{layout["n_cols_x"] * j + i + 1}',
                       ha='center', va='center', fontsize=7, color='#FF0000')
        
        # DARVOZALAR
        door_front_count = params.get("door_front_count", 1)
        door_front_width = params.get("door_front_width", 12.0)
        if door_front_count > 0:
            total_w = door_front_count * door_front_width
            gap = (L - total_w) / (door_front_count + 1) if total_w < L else 0
            for i in range(door_front_count):
                dx = gap * (i + 1) + door_front_width * i
                door = patches.Rectangle((dx, W - 0.15), door_front_width, 0.3,
                                        linewidth=2, edgecolor='#00FFFF',
                                        facecolor='none', zorder=2)
                ax.add_patch(door)
                arc = patches.Arc((dx + door_front_width/2, W), door_front_width/2.5, door_front_width/2.5,
                                 theta1=0, theta2=90, linewidth=1.5, edgecolor='#00FFFF', linestyle='--', zorder=2)
                ax.add_patch(arc)
                ax.text(dx + door_front_width/2, W + 0.5, f'D-{i+1}', ha='center', va='center', fontsize=9, color='#00FFFF', fontweight='bold')
        
        # DERAZALAR
        w_front = params.get("window_count_front", 3)
        window_width = params.get("window_width", 2.5)
        if w_front > 0:
            total_w = w_front * window_width
            gap = (L - total_w) / (w_front + 1) if total_w < L else 0
            for i in range(w_front):
                dx = gap * (i + 1) + window_width * i
                win = patches.Rectangle((dx, W - 0.15), window_width, 0.3,
                                       linewidth=1.5, edgecolor='#00FF00',
                                       facecolor='none', zorder=1)
                ax.add_patch(win)
                ax.plot([dx + window_width/2, dx + window_width/2], [W - 0.15, W + 0.15], color='#00FF00', linewidth=1, zorder=2)
                ax.plot([dx, dx + window_width], [W, W], color='#00FF00', linewidth=1, zorder=2)
        
        # O'LCHAMLAR
        ax.plot([0.3, L-0.3], [-0.7, -0.7], color='#FF0000', linewidth=1.5)
        ax.plot([0.3, 0.3], [-0.6, -0.8], color='#FF0000', linewidth=1.5)
        ax.plot([L-0.3, L-0.3], [-0.6, -0.8], color='#FF0000', linewidth=1.5)
        ax.plot([0.3, 0.1], [-0.7, -0.7], color='#FF0000', linewidth=1.5)
        ax.plot([L-0.3, L-0.1], [-0.7, -0.7], color='#FF0000', linewidth=1.5)
        ax.text(L/2, -0.9, f'{L:.1f} m', ha='center', va='center', color='#FF0000', fontsize=12, fontweight='bold')
        
        ax.plot([-0.7, -0.7], [0.3, W-0.3], color='#FF0000', linewidth=1.5)
        ax.plot([-0.6, -0.8], [0.3, 0.3], color='#FF0000', linewidth=1.5)
        ax.plot([-0.6, -0.8], [W-0.3, W-0.3], color='#FF0000', linewidth=1.5)
        ax.plot([-0.7, -0.7], [0.3, 0.1], color='#FF0000', linewidth=1.5)
        ax.plot([-0.7, -0.7], [W-0.3, W-0.1], color='#FF0000', linewidth=1.5)
        ax.text(-0.9, W/2, f'{W:.1f} m', ha='center', va='center', color='#FF0000', fontsize=12, fontweight='bold', rotation=90)
        
        ax.annotate('X', xy=(L + 0.5, -0.3), color='#FF0000', fontsize=14, fontweight='bold')
        ax.annotate('Z', xy=(-0.3, W + 0.5), color='#FF0000', fontsize=14, fontweight='bold')
        
        ax.set_xlim(-2, L + 2)
        ax.set_ylim(-2, W + 2)
        ax.axis('off')
        
        title = f'REJA (TOP VIEW)  |  {L:.1f} x {W:.1f} m  |  Masshtab: 1:{int(max(L,W)/2)}'
        ax.text(L/2, W + 1.5, title, ha='center', va='center', fontsize=14, fontweight='bold', color='#333333')
        
        scale_bar_len = min(L/4, 5)
        ax.plot([0.5, 0.5 + scale_bar_len], [-1.2, -1.2], color='black', linewidth=2)
        ax.plot([0.5, 0.5], [-1.1, -1.3], color='black', linewidth=2)
        ax.plot([0.5 + scale_bar_len, 0.5 + scale_bar_len], [-1.1, -1.3], color='black', linewidth=2)
        ax.text(0.5 + scale_bar_len/2, -1.4, f'{scale_bar_len:.0f} m', ha='center', va='center', fontsize=8)
        
        return fig
    
    # ---- FASAD (FRONT ELEVATION) ----
    def create_front_elevation():
        L = params.get("L", 30)
        H = params.get("H", 7.5)
        W = params.get("W", 15)
        roof_pitch = params.get("roof_pitch", 12)
        
        fig, ax = plt.subplots(figsize=(16, 10), dpi=120)
        ax.set_facecolor('white')
        fig.patch.set_facecolor('white')
        ax.set_aspect('equal')
        
        rect = patches.Rectangle((0, 0), L, H, linewidth=2.5, edgecolor='#000000', facecolor='none', zorder=1)
        ax.add_patch(rect)
        
        ridge_H = H
        if roof_pitch > 0:
            ridge_H = H + (W/2) * np.tan(np.radians(roof_pitch))
            roof = patches.Polygon([(0, H), (L/2, ridge_H), (L, H)], linewidth=2.5, edgecolor='#000000', facecolor='none', zorder=1)
            ax.add_patch(roof)
            for x in np.linspace(0.5, L-0.5, 8):
                y = H + (ridge_H - H) * (1 - abs(x - L/2) / (L/2))
                ax.plot([x, x], [0, y], color='#DDDDDD', linewidth=0.5, zorder=0)
        
        door_front_count = params.get("door_front_count", 1)
        door_front_width = params.get("door_front_width", 12.0)
        door_front_height = params.get("door_front_height", 6.5)
        if door_front_count > 0:
            total_w = door_front_count * door_front_width
            gap = (L - total_w) / (door_front_count + 1) if total_w < L else 0
            for i in range(door_front_count):
                dx = gap * (i + 1) + door_front_width * i
                door = patches.Rectangle((dx, 0), door_front_width, door_front_height,
                                        linewidth=2.5, edgecolor='#00FFFF', facecolor='none', zorder=2)
                ax.add_patch(door)
                mid = dx + door_front_width/2
                ax.plot([mid, mid], [0, door_front_height], color='#00FFFF', linewidth=1.5, zorder=3)
                for j in range(4):
                    y = j * door_front_height/4
                    ax.plot([dx + 0.1, dx + door_front_width - 0.1], [y + door_front_height/8, y + door_front_height/8],
                           color='#00FFFF', linewidth=0.8, alpha=0.5, zorder=3)
                ax.text(dx + door_front_width/2, -0.5, f'D-{i+1}\n{door_front_width:.1f}x{door_front_height:.1f}',
                       ha='center', va='center', fontsize=8, color='#00FFFF', fontweight='bold')
        
        w_front = params.get("window_count_front", 3)
        window_width = params.get("window_width", 2.5)
        window_height = params.get("window_height", 2.0)
        if w_front > 0:
            total_w = w_front * window_width
            gap = (L - total_w) / (w_front + 1) if total_w < L else 0
            for i in range(w_front):
                dx = gap * (i + 1) + window_width * i
                wy = H * 0.55
                win = patches.Rectangle((dx, wy - window_height/2), window_width, window_height,
                                       linewidth=2, edgecolor='#00FF00', facecolor='none', zorder=2)
                ax.add_patch(win)
                ax.plot([dx + window_width/2, dx + window_width/2], [wy - window_height/2, wy + window_height/2],
                       color='#00FF00', linewidth=1, zorder=3)
                ax.plot([dx, dx + window_width], [wy, wy], color='#00FF00', linewidth=1, zorder=3)
                ax.text(dx + window_width/2, wy + window_height/2 + 0.3, f'W-{i+1}',
                       ha='center', va='center', fontsize=7, color='#00FF00')
        
        ax.plot([-0.5, -0.5], [0.3, H-0.3], color='#FF0000', linewidth=1.5)
        ax.plot([-0.4, -0.6], [0.3, 0.3], color='#FF0000', linewidth=1.5)
        ax.plot([-0.4, -0.6], [H-0.3, H-0.3], color='#FF0000', linewidth=1.5)
        ax.plot([-0.5, -0.5], [0.3, 0.1], color='#FF0000', linewidth=1.5)
        ax.plot([-0.5, -0.5], [H-0.3, H-0.1], color='#FF0000', linewidth=1.5)
        ax.text(-0.8, H/2, f'{H:.1f} m', ha='center', va='center', color='#FF0000', fontsize=12, fontweight='bold', rotation=90)
        
        if roof_pitch > 0:
            ax.plot([L/2, L/2], [ridge_H + 0.3, ridge_H - 0.3], color='#FF0000', linewidth=1.5, linestyle='--')
            ax.text(L/2, ridge_H + 0.7, f'{ridge_H:.1f} m', ha='center', va='center', color='#FF0000', fontsize=10, fontweight='bold')
        
        ax.annotate('A', xy=(L + 1.5, -0.3), color='#FF0000', fontsize=14, fontweight='bold')
        ax.annotate('A', xy=(L + 1.5, H + 0.3), color='#FF0000', fontsize=14, fontweight='bold')
        ax.plot([L + 1, L + 1], [-0.3, H + 0.3], color='#FF0000', linewidth=1.5, linestyle='--')
        
        ax.set_xlim(-2, L + 3)
        ax.set_ylim(-2, max(H, ridge_H) + 2)
        ax.axis('off')
        
        title = f'OLD FASAD (FRONT ELEVATION)  |  L={L:.1f} m, H={H:.1f} m'
        ax.text(L/2, max(H, ridge_H) + 1.5, title, ha='center', va='center', fontsize=14, fontweight='bold', color='#333333')
        
        return fig
    
    # ---- KESIM (SECTION A-A) ----
    def create_section_view():
        L = params.get("L", 30)
        H = params.get("H", 7.5)
        W = params.get("W", 15)
        roof_pitch = params.get("roof_pitch", 12)
        
        fig, ax = plt.subplots(figsize=(16, 10), dpi=120)
        ax.set_facecolor('white')
        fig.patch.set_facecolor('white')
        ax.set_aspect('equal')
        
        rect = patches.Rectangle((0, 0), L, H, linewidth=2.5, edgecolor='#000000', facecolor='#F5F5F5', zorder=1)
        ax.add_patch(rect)
        
        for x in np.arange(0, L, 0.3):
            for y in np.arange(0, H, 0.3):
                if (x + y) % 0.5 < 0.25:
                    ax.scatter(x, y, color='#CCCCCC', s=2, alpha=0.3, zorder=0)
        
        ridge_H = H
        if roof_pitch > 0:
            ridge_H = H + (W/2) * np.tan(np.radians(roof_pitch))
            roof = patches.Polygon([(0, H), (L/2, ridge_H), (L, H)], linewidth=2.5, edgecolor='#000000', facecolor='#F0F0F0', zorder=1)
            ax.add_patch(roof)
            for x in np.arange(0, L, 0.3):
                y_top = H + (ridge_H - H) * (1 - abs(x - L/2) / (L/2))
                for y in np.arange(H, y_top, 0.3):
                    if (x + y) % 0.5 < 0.25:
                        ax.scatter(x, y, color='#CCCCCC', s=2, alpha=0.3, zorder=0)
        
        layout = compute_column_layout(L, W)
        for i in range(layout["n_cols_x"]):
            x = i * layout["spacing_x"]
            col = patches.Rectangle((x - 0.15, 0), 0.3, H, linewidth=2, edgecolor='#FF0000', facecolor='none', zorder=2)
            ax.add_patch(col)
            ax.plot([x - 0.2, x + 0.2], [0.05, 0.05], color='#FF0000', linewidth=3, zorder=3)
            ax.plot([x - 0.2, x + 0.2], [H-0.05, H-0.05], color='#FF0000', linewidth=3, zorder=3)
            ax.text(x, H/2, f'C{i+1}', ha='center', va='center', fontsize=8, color='#FF0000', fontweight='bold')
            ax.scatter(x, H/2, color='#FF0000', s=30, marker='+', zorder=3)
        
        floor = patches.Rectangle((0, -0.15), L, 0.3, linewidth=2, edgecolor='#444444', facecolor='#D3D3D3', zorder=2)
        ax.add_patch(floor)
        foundation = patches.Rectangle((0.2, -0.55), L-0.4, 0.4, linewidth=2, edgecolor='#444444', facecolor='#D3D3D3', zorder=2)
        ax.add_patch(foundation)
        
        ax.plot([-0.5, -0.5], [0.3, H-0.3], color='#FF0000', linewidth=1.5)
        ax.plot([-0.4, -0.6], [0.3, 0.3], color='#FF0000', linewidth=1.5)
        ax.plot([-0.4, -0.6], [H-0.3, H-0.3], color='#FF0000', linewidth=1.5)
        ax.text(-0.8, H/2, f'{H:.1f} m', ha='center', va='center', color='#FF0000', fontsize=12, fontweight='bold', rotation=90)
        
        if roof_pitch > 0:
            ax.text(L/2, ridge_H + 0.7, f'{ridge_H:.1f} m', ha='center', va='center', color='#FF0000', fontsize=10, fontweight='bold')
            ax.plot([L/2, L/2], [ridge_H + 0.3, ridge_H - 0.3], color='#FF0000', linewidth=1.5, linestyle='--')
        
        ax.annotate('A', xy=(L + 1.5, -0.3), color='#FF0000', fontsize=14, fontweight='bold')
        ax.annotate('A', xy=(L + 1.5, H + 0.3), color='#FF0000', fontsize=14, fontweight='bold')
        ax.annotate('A-A', xy=(L + 1.5, H/2), color='#FF0000', ha='center', va='center', fontsize=12, fontweight='bold')
        ax.plot([L + 1, L + 1], [-0.3, H + 0.3], color='#FF0000', linewidth=1.5, linestyle='--')
        
        ax.set_xlim(-2, L + 3)
        ax.set_ylim(-1.5, max(H, ridge_H) + 2)
        ax.axis('off')
        
        title = f'KESIM A-A (SECTION A-A)  |  L={L:.1f} m, H={H:.1f} m'
        ax.text(L/2, max(H, ridge_H) + 1.5, title, ha='center', va='center', fontsize=14, fontweight='bold', color='#333333')
        
        return fig
    
    # ---- IZOMETRIK (3D VIEW) ----
    def create_isometric_view():
        from mpl_toolkits.mplot3d import Axes3D
        L = params.get("L", 30)
        W = params.get("W", 15)
        H = params.get("H", 7.5)
        roof_pitch = params.get("roof_pitch", 12)
        
        fig = plt.figure(figsize=(16, 11), dpi=120)
        ax = fig.add_subplot(111, projection='3d')
        ax.set_facecolor('white')
        fig.patch.set_facecolor('white')
        
        x = [0, L, L, 0, 0]
        y = [0, 0, W, W, 0]
        z = [0, 0, 0, 0, 0]
        ax.plot3D(x, y, z, color='black', linewidth=2.5, zorder=1)
        
        z_top = [H, H, H, H, H]
        ax.plot3D(x, y, z_top, color='black', linewidth=2.5, zorder=1)
        
        for i in range(4):
            ax.plot3D([x[i], x[i]], [y[i], y[i]], [0, H], color='black', linewidth=2, zorder=1)
        
        ridge_H = H
        if roof_pitch > 0:
            ridge_H = H + (W/2) * np.tan(np.radians(roof_pitch))
            roof1 = [(0, 0, H), (L, 0, H), (L, W/2, ridge_H), (0, W/2, ridge_H)]
            rx, ry, rz = zip(*roof1)
            ax.plot3D(rx, ry, rz, color='black', linewidth=2.5, zorder=1)
            roof2 = [(0, W, H), (L, W, H), (L, W/2, ridge_H), (0, W/2, ridge_H)]
            rx2, ry2, rz2 = zip(*roof2)
            ax.plot3D(rx2, ry2, rz2, color='black', linewidth=2.5, zorder=1)
            ax.plot3D([0, L], [W/2, W/2], [ridge_H, ridge_H], color='#FF0000', linewidth=2.5, linestyle='--', zorder=2)
        
        layout = compute_column_layout(L, W)
        for i in range(layout["n_cols_x"]):
            for j in range(layout["n_cols_z"]):
                cx = i * layout["spacing_x"]
                cz = j * layout["spacing_z"]
                ax.plot3D([cx, cx], [cz, cz], [0, H], color='#FF0000', linewidth=2, zorder=2)
                ax.scatter(cx, cz, 0, color='#FF0000', s=40, marker='o', zorder=3)
                ax.scatter(cx, cz, H, color='#FF0000', s=40, marker='o', zorder=3)
        
        w_front = params.get("window_count_front", 3)
        window_width = params.get("window_width", 2.5)
        window_height = params.get("window_height", 2.0)
        if w_front > 0:
            total_w = w_front * window_width
            gap = (L - total_w) / (w_front + 1) if total_w < L else 0
            for i in range(w_front):
                dx = gap * (i + 1) + window_width * i
                wy = H * 0.55
                xw = [dx, dx + window_width, dx + window_width, dx, dx]
                yw = [W, W, W, W, W]
                zw = [wy - window_height/2, wy - window_height/2, wy + window_height/2, wy + window_height/2, wy - window_height/2]
                ax.plot3D(xw, yw, zw, color='#00FF00', linewidth=1.5, zorder=2)
        
        door_front_count = params.get("door_front_count", 1)
        door_front_width = params.get("door_front_width", 12.0)
        door_front_height = params.get("door_front_height", 6.5)
        if door_front_count > 0:
            total_w = door_front_count * door_front_width
            gap = (L - total_w) / (door_front_count + 1) if total_w < L else 0
            for i in range(door_front_count):
                dx = gap * (i + 1) + door_front_width * i
                xd = [dx, dx + door_front_width, dx + door_front_width, dx, dx]
                yd = [W, W, W, W, W]
                zd = [0, 0, door_front_height, door_front_height, 0]
                ax.plot3D(xd, yd, zd, color='#00FFFF', linewidth=2.5, zorder=2)
                mid = dx + door_front_width/2
                ax.plot3D([mid, mid], [W, W], [0, door_front_height], color='#00FFFF', linewidth=1.5, linestyle='--', zorder=3)
        
        ax.text3D(L/2, -0.8, -0.5, f'{L:.1f} m', color='#FF0000', fontsize=12, fontweight='bold')
        ax.text3D(-0.8, W/2, -0.5, f'{W:.1f} m', color='#FF0000', fontsize=12, fontweight='bold')
        ax.text3D(-0.8, -0.8, H/2, f'{H:.1f} m', color='#FF0000', fontsize=12, fontweight='bold')
        
        ax.set_xlabel('X', color='#333333', fontsize=12, fontweight='bold')
        ax.set_ylabel('Z', color='#333333', fontsize=12, fontweight='bold')
        ax.set_zlabel('Y (Balandlik)', color='#333333', fontsize=12, fontweight='bold')
        
        ax.view_init(elev=25, azim=-135)
        ax.grid(True, alpha=0.1)
        
        title = f'3D IZOMETRIK KO\'RINISH  |  {L:.1f}x{W:.1f}x{H:.1f} m'
        ax.set_title(title, color='#333333', fontsize=14, fontweight='bold', pad=30)
        
        return fig
    
    # ============================================================
    # ASOSIY CHIZMALAR (KEYINGI DETAIL CHIZMALAR)
    # ============================================================
    
    # ---- DETAIL 1: Ustun - poydevor birikmasi ----
    def detail_1():
        fig, ax = plt.subplots(figsize=(10, 8), dpi=120)
        ax.set_aspect('equal')
        draw_sheet_layout(ax, "USTUN - POYDEVOR BIRIKMASI / COLUMN - FOUNDATION JOINT", "01", "1:10", room_code)
        
        ground = patches.Rectangle((-1.5, -1.5), 10.0, 1.0, facecolor='#E2E8F0', hatch='...', edgecolor='#94A3B8', linewidth=0.5)
        ax.add_patch(ground)
        
        footing = patches.Rectangle((1.5, -0.5), 4.0, 3.0, facecolor='#E2E8F0', hatch='//.', edgecolor='#0F172A', linewidth=1.5, zorder=2)
        ax.add_patch(footing)
        
        grout = patches.Rectangle((2.2, 2.5), 2.6, 0.1, facecolor='#94A3B8', hatch='xx', edgecolor='#475569', linewidth=0.8, zorder=3)
        ax.add_patch(grout)
        
        base_plate = patches.Rectangle((2.0, 2.6), 3.0, 0.15, facecolor='#334155', edgecolor='#0F172A', linewidth=1.2, zorder=4)
        ax.add_patch(base_plate)
        
        column = patches.Rectangle((3.1, 2.75), 0.8, 3.45, facecolor='#475569', edgecolor='#0F172A', linewidth=1.5, zorder=5)
        ax.add_patch(column)
        
        rib_l = patches.Polygon([(2.0, 2.75), (3.1, 2.75), (3.1, 4.0)], facecolor='#334155', edgecolor='#0F172A', linewidth=1, zorder=6)
        rib_r = patches.Polygon([(5.0, 2.75), (3.9, 2.75), (3.9, 4.0)], facecolor='#334155', edgecolor='#0F172A', linewidth=1, zorder=6)
        ax.add_patch(rib_l)
        ax.add_patch(rib_r)
        
        for bx in [2.4, 4.6]:
            ax.plot([bx, bx], [0.3, 2.8], color='#0F172A', linewidth=2.0, zorder=7)
            ax.plot([bx, bx + 0.3], [0.3, 0.3], color='#0F172A', linewidth=2.0, zorder=7)
            nut = patches.Rectangle((bx - 0.15, 2.75), 0.3, 0.12, facecolor='#94A3B8', edgecolor='#0F172A', linewidth=0.8, zorder=8)
            washer = patches.Rectangle((bx - 0.2, 2.75), 0.4, 0.03, facecolor='#475569', edgecolor='#0F172A', linewidth=0.5, zorder=8)
            ax.add_patch(nut)
            ax.add_patch(washer)
            
        ax.plot([1.7, 5.3], [0.0, 0.0], color='#1E293B', linewidth=1.2, linestyle='--', zorder=3)
        ax.plot([1.7, 5.3], [2.0, 2.0], color='#1E293B', linewidth=1.2, linestyle='--', zorder=3)
        for rx in np.arange(1.9, 5.3, 0.5):
            ax.plot([rx, rx], [-0.3, 2.3], color='#1E293B', linewidth=0.8, linestyle=':', zorder=3)
            
        draw_leader(ax, 3.5, 5.0, 1.0, 5.5, "Chelik tayanch ustuni / Steel column box (400x400)")
        draw_leader(ax, 2.8, 3.5, 0.5, 4.5, "Kuchaytiruvchi kosinka / Stiffening rib (t=10 mm)")
        draw_leader(ax, 2.1, 2.68, 0.2, 3.5, "Tayanch plitasi / Base plate (t=20 mm)")
        draw_leader(ax, 2.4, 2.85, 0.4, 2.0, "Anker bolti yong'og'i / Anchor nut M24")
        draw_leader(ax, 3.5, 2.55, 0.8, 1.2, "Sementli to'ldiruvchi podlivka / Non-shrink grout (t=50 mm)")
        draw_leader(ax, 4.0, 1.0, 5.2, 0.5, "Beton poydevor / Concrete footing B20 (M250)")
        draw_leader(ax, 4.6, 0.4, 5.5, -0.2, "Anker bolti M24 / Anchor bolt L=800mm")
        draw_leader(ax, 2.5, -1.0, 1.0, -1.2, "Zichlashtirilgan shag'al to'shama / Compacted gravel cushion")
        
        draw_dimension_h(ax, 1.5, 5.5, -0.8, "1600")
        draw_dimension_h(ax, 2.0, 5.0, 2.2, "600")
        draw_dimension_h(ax, 3.1, 3.9, 6.3, "400")
        draw_dimension_v(ax, 1.2, -0.5, 2.5, "1200")
        draw_dimension_v(ax, 1.8, 2.6, 2.75, "40")
        
        ax.set_xlim(-2.0, 10.0)
        ax.set_ylim(-2.0, 8.0)
        ax.axis('off')
        return fig
    
    # ============================================================
    # QOLGAN DETAIL 2-10 CHIZMALAR (qisqartirilgan holda)
    # ============================================================
    def detail_2():
        fig, ax = plt.subplots(figsize=(10, 8), dpi=120)
        ax.set_aspect('equal')
        draw_sheet_layout(ax, "USTUN VA TOSIN BIRIKMASI / COLUMN - BEAM CONNECTION", "02", "1:10", room_code)
        
        ax.fill([2.5, 2.7, 2.7, 3.3, 3.3, 3.5, 3.5, 2.5], 
                [-1.5, -1.5, 5.0, 5.0, -1.5, -1.5, 5.0, 5.0], 
                facecolor='#475569', edgecolor='#0F172A', linewidth=1.2, zorder=2)
        ax.plot([3.0, 3.0], [-1.5, 5.0], color='#0F172A', linestyle='-.', linewidth=0.8, zorder=3)
        
        bracket = patches.Polygon([(2.5, 3.0), (2.0, 3.0), (2.5, 4.0)], facecolor='#334155', edgecolor='#0F172A', linewidth=1.2, zorder=3)
        ax.add_patch(bracket)
        
        ax.fill([-1.5, 2.5, 2.5, -1.5], [4.0, 4.0, 4.2, 4.2], facecolor='#334155', edgecolor='#0F172A', linewidth=1, zorder=4)
        ax.fill([-1.5, 2.5, 2.5, -1.5], [5.3, 5.3, 5.5, 5.5], facecolor='#334155', edgecolor='#0F172A', linewidth=1, zorder=4)
        ax.fill([-1.5, 2.5, 2.5, -1.5], [4.2, 4.2, 5.3, 5.3], facecolor='#475569', edgecolor='#0F172A', linewidth=0.8, zorder=3)
        
        end_plate = patches.Rectangle((2.45, 3.9), 0.1, 1.7, facecolor='#1E293B', edgecolor='#0F172A', linewidth=1, zorder=5)
        ax.add_patch(end_plate)
        
        for by in [4.1, 4.5, 4.9, 5.3]:
            ax.plot([2.35, 2.75], [by, by], color='#EF4444', linewidth=2.0, zorder=6)
            bolt_head = patches.Rectangle((2.3, by-0.08), 0.1, 0.16, facecolor='#94A3B8', edgecolor='#0F172A', linewidth=0.8, zorder=7)
            nut = patches.Rectangle((2.6, by-0.08), 0.1, 0.16, facecolor='#94A3B8', edgecolor='#0F172A', linewidth=0.8, zorder=7)
            ax.add_patch(bolt_head)
            ax.add_patch(nut)
            
        ax.plot([2.5, 2.5], [3.0, 4.0], color='#0F172A', linewidth=1.5, linestyle=':', zorder=8)
        
        draw_leader(ax, 3.0, 2.0, 4.5, 2.5, "Chelik ustun / Steel column (I-beam H-200)")
        draw_leader(ax, -0.5, 4.8, -1.2, 5.8, "Asosiy yopgich tosin / Main beam (I-beam H-300)")
        draw_leader(ax, 2.5, 5.4, 1.5, 6.2, "Mustahkamlovchi metall plita / Connection plate (t=12 mm)")
        draw_leader(ax, 2.3, 3.0, 1.0, 2.2, "Tayanch stoligi / Support bracket (t=10 mm)")
        draw_leader(ax, 2.65, 4.5, 4.2, 4.8, "Yuqori mustahkamlikdagi boltlar M20 (k. 8.8)")
        draw_leader(ax, 2.5, 3.5, 3.8, 3.6, "Zavod payvand choki / Factory weld joint (h=6 mm)")
        
        draw_dimension_h(ax, 2.5, 3.5, -0.5, "200")
        draw_dimension_v(ax, -1.3, 4.0, 5.5, "300")
        draw_dimension_v(ax, 3.7, 3.9, 5.6, "340")
        draw_dimension_h(ax, 2.0, 2.5, 2.8, "50")
        
        ax.set_xlim(-2.0, 10.0)
        ax.set_ylim(-2.0, 8.0)
        ax.axis('off')
        return fig
    
    # ============================================================
    # CHIZMALARNI YIG'ISH
    # ============================================================
    drawings['reja'] = create_floor_plan()
    drawings['fasad'] = create_front_elevation()
    drawings['kesim'] = create_section_view()
    drawings['izometrik'] = create_isometric_view()
    drawings['detail_1'] = detail_1()
    drawings['detail_2'] = detail_2()
    # detail_3 dan detail_10 gacha sizda mavjud, ularni ham qo'shing
    
    return drawings
def construction_sidebar():
    st.sidebar.title("Qurilish Konfiguratori")

    with st.sidebar.expander("Loyiha malumotlari", expanded=True):
        construction_type = st.selectbox("Bino turi", list(construction_types.keys()), key="construction_type")
        name = st.text_input("Loyiha nomi", value="Yangi Angar Loyihasi", key="cons_name")
        code = st.text_input("Loyiha kodi", value=f"ANG-{datetime.now().strftime('%Y%m%d')}-001", key="cons_code")

    with st.sidebar.expander("Asosiy olchamlar", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            L = st.number_input("Uzunlik (m)", min_value=5.0, value=30.0, step=1.0, key="cons_L")
            H = st.number_input("Balandlik (m)", min_value=3.0, value=7.5, step=0.5, key="cons_H")
        with col2:
            W = st.number_input("Kenglik (m)", min_value=5.0, value=15.0, step=1.0, key="cons_W")
            roof_pitch = st.slider("Tom qiyaligi (gradus)", 0.0, 45.0, 12.0, 1.0, key="cons_roof_pitch")
        column_spacing = st.slider(
            "Ustunlar oralig'i (m)", 
            min_value=3.0, 
            max_value=12.0, 
            value=8.5, 
            step=0.250, 
            key="cons_column_spacing",
            help="Ustunlar orasidagi masofa. Kichik qiymat - ko'proq ustun, katta qiymat - kamroq ustun"
        )
    
        with st.sidebar.expander("Materiallar", expanded=True):
            wall_type = st.selectbox("Devor turi", list(wall_materials.keys()), key="cons_wall")
            wall_thickness = st.selectbox("Devor qalinligi", wall_materials[wall_type]["qalinlik"], key="cons_thick")
            floor_type = st.selectbox("Pol turi", list(floor_materials.keys()), key="cons_floor")
            roof_type = st.selectbox("Tom turi", list(roof_materials.keys()), key="cons_roof")
            floor_panel_mode = st.checkbox(
                "Pol panel sifatida hisobla", 
                value=False,  # ✅ Default False
                key="cons_floor_panel"
            )
    # ===== YANGI: PROFIL TANLASH =====
            st.divider()
            st.markdown("#### Progonlar profillari")
            
            # Tom progonlari
            purlin_profile = st.selectbox(
                "Tom progonlari (GOST 8645-68)",
                options=get_profile_list("purlin"),
                index=3,  # "Profil 120x60x4 mm" indeksi
                key="purlin_profile_select"
            )
            
            # Devor progonlari
            wall_purlin_profile = st.selectbox(
                "Devor progonlari (GOST 8645-68)",
                options=get_profile_list("purlin"),
                index=2,  # "Profil 100x50x4 mm" indeksi
                key="wall_purlin_profile_select"
            )
            
            # Bog'lamalar profili
            bracing_profile = st.selectbox(
                "Bog'lamalar (Shveller GOST 8240-97)",
                options=get_profile_list("bracing"),
                index=2,  # "Shveller 14P" indeksi
                key="bracing_profile_select"
            )
            
            # Tanlangan profillarning og'irliklarini ko'rsatish
            st.caption(f"Tom progonlari: {purlin_profile} ({get_profile_weight('purlin', purlin_profile)} kg/m)")
            st.caption(f"Devor progonlari: {wall_purlin_profile} ({get_profile_weight('purlin', wall_purlin_profile)} kg/m)")
            st.caption(f"Bog'lamalar: {bracing_profile} ({get_profile_weight('bracing', bracing_profile)} kg/m)")
        # construction_sidebar() funksiyasiga qo'shing (taxminan 2200-qator atrofida)

        with st.sidebar.expander("Konstruksiya turi", expanded=True):
            construction_system = st.radio(
                "Metall karkas turi",
                options=["LMK (Yengil Metall)", "LSTK (Yengil Po'lat)"],
                index=0,
                key="construction_system",
                help="""
                **LMK**: Qalin metall (8-40mm), payvandlash/boltlar, katta oraliqli binolar
                **LSTK**: Yupqa sinklangan po'lat (0.7-4mm), vintli birikma, angar/omborlar
                """
            )
            
            # 🔽 BU QISMNI QO'SHING - tanlangan variantni ko'rsatish
            st.write(f"Tanlangan: **{construction_system}**")
         
    with st.sidebar.expander("Derazalar (har devor uchun)", expanded=False):
        st.caption("Old fasad (darvozalar tomon)")
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            w_front = st.number_input("Old deraza soni", min_value=0, max_value=20, value=3, key="win_front")
        with col_w2:
            w_back = st.number_input("Orqa deraza soni", min_value=0, max_value=20, value=3, key="win_back")
        col_w3, col_w4 = st.columns(2)
        with col_w3:
            w_left = st.number_input("Chap deraza soni", min_value=0, max_value=20, value=0, key="win_left")
        with col_w4:
            w_right = st.number_input("O'ng deraza soni", min_value=0, max_value=20, value=0, key="win_right")
        
        col_ws1, col_ws2 = st.columns(2)
        with col_ws1:
            window_width = st.number_input("Deraza eni (m)", min_value=0.5, max_value=5.0, value=2.5, step=0.1, key="cons_win_w")
        with col_ws2:
            window_height = st.number_input("Deraza boyi (m)", min_value=0.5, max_value=4.0, value=2.0, step=0.1, key="cons_win_h")

    with st.sidebar.expander("Darvozalar", expanded=False):
        st.markdown("#### Old devor (Z=W)")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            door_front_count = st.number_input("Old darvoza soni", min_value=0, max_value=20, value=1, key="door_front")
        with col_d2:
            door_front_width = st.number_input("Old darvoza eni (m)", min_value=2.0, max_value=20.0, value=12.0, step=1.0, key="door_front_w")
            door_front_height = st.number_input("Old darvoza boyi (m)", min_value=2.0, max_value=10.0, value=6.5, step=0.5, key="door_front_h")

        st.markdown("#### Orqa devor (Z=0)")
        col_d3, col_d4 = st.columns(2)
        with col_d3:
            door_back_count = st.number_input("Orqa darvoza soni", min_value=0, max_value=20, value=0, key="door_back")
        with col_d4:
            door_back_width = st.number_input("Orqa darvoza eni (m)", min_value=2.0, max_value=20.0, value=12.0, step=1.0, key="door_back_w")
            door_back_height = st.number_input("Orqa darvoza boyi (m)", min_value=2.0, max_value=10.0, value=6.5, step=0.5, key="door_back_h")

        st.markdown("#### Chap devor (X=0)")
        col_d5, col_d6 = st.columns(2)
        with col_d5:
            door_left_count = st.number_input("Chap darvoza soni", min_value=0, max_value=20, value=0, key="door_left")
        with col_d6:
            door_left_width = st.number_input("Chap darvoza eni (m)", min_value=0.0, max_value=20.0, value=5.0, step=1.0, key="door_left_w")
            door_left_height = st.number_input("Chap darvoza boyi (m)", min_value=0.0, max_value=10.0, value=4.0, step=0.5, key="door_left_h")

        st.markdown("#### O'ng devor (X=L)")
        col_d7, col_d8 = st.columns(2)
        with col_d7:
            door_right_count = st.number_input("O'ng darvoza soni", min_value=0, max_value=20, value=0, key="door_right")
        with col_d8:
            door_right_width = st.number_input("O'ng darvoza eni (m)", min_value=0.0, max_value=20.0, value=5.0, step=1.0, key="door_right_w")
            door_right_height = st.number_input("O'ng darvoza boyi (m)", min_value=0.0, max_value=10.0, value=4.0, step=0.5, key="door_right_h")

    with st.sidebar.expander("NARXLAR (1 tonna/$)", expanded=True):
        st.markdown("#### Metall narxlari")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            price_column = st.number_input("Ustunlar", min_value=0.0, max_value=5000.0, value=950.0, step=50.0, key="price_metal_column")
            price_truss = st.number_input("Fermalar", min_value=0.0, max_value=5000.0, value=950.0, step=50.0, key="price_metal_truss")
            # 🔽 YANGI: Progonlar narxi
            price_purlins = st.number_input("Progonlar", min_value=0.0, max_value=5000.0, value=950.0, step=50.0, key="price_metal_purlins")
        with col_m2:
            price_beam = st.number_input("Tosinlar", min_value=0.0, max_value=5000.0, value=950.0, step=50.0, key="price_metal_beam")
            price_longitudinal = st.number_input("Uzunasiga", min_value=0.0, max_value=5000.0, value=950.0, step=50.0, key="price_metal_longitudinal")
            # 🔽 YANGI: Bog'lamalar narxi
            price_bracing = st.number_input("Bog'lamalar", min_value=0.0, max_value=5000.0, value=950.0, step=50.0, key="price_metal_bracing")
        
        # 🔽 YANGI: Birikma turi va narxi
        st.markdown("#### Birikma detallari")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            connection_type = st.selectbox(
                "Birikma turi", 
                ["bolted", "welded", "mixed"], 
                index=2, 
                key="connection_type"
            )
        with col_c2:
            price_connection = st.number_input(
                "Birikmalar narxi (1 tonna)", 
                min_value=0.0, 
                max_value=5000.0, 
                value=950.0, 
                step=50.0, 
                key="price_metal_connection"
            )
        
        st.markdown("#### Qurilish materiallari (1 m²/$)")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            wall_price = st.number_input("Devor paneli", min_value=0.0, max_value=500.0, value=35.0, step=5.0, key="price_wall")
            roof_price = st.number_input("Tom qoplamasi", min_value=0.0, max_value=500.0, value=45.0, step=5.0, key="price_roof")
        with col_p2:
            floor_price = st.number_input("Pol qoplamasi", min_value=0.0, max_value=500.0, value=45.0, step=5.0, key="price_floor")
            window_price = st.number_input("Deraza (1 m²)", min_value=0.0, max_value=200.0, value=45.0, step=5.0, key="price_window")
            door_price = st.number_input("Darvoza (1 m²)", min_value=0.0, max_value=200.0, value=28.0, step=5.0, key="price_door")
        
        st.markdown("#### Beton va materiallar")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            concrete_price = st.number_input("Beton (1 m³)", min_value=0.0, max_value=500.0, value=85.0, step=5.0, key="price_concrete")
            cement_price = st.number_input("Sement (1 kg)", min_value=0.0, max_value=1.0, value=0.09, step=0.01, key="price_cement")
            sand_price = st.number_input("Qum (1 m³)", min_value=0.0, max_value=200.0, value=35.0, step=5.0, key="price_sand")
        with col_b2:
            rebar_price = st.number_input("Armatura (1 kg)", min_value=0.0, max_value=2.0, value=0.85, step=0.05, key="price_rebar")
            gravel_price = st.number_input("Shag'al (1 m³)", min_value=0.0, max_value=200.0, value=40.0, step=5.0, key="price_gravel")
            shipyak_price = st.number_input("Shipyak (1 m²)", min_value=0.0, max_value=100.0, value=30.0, step=5.0, key="price_shipyak")
        
        st.markdown("#### Ishchi kuchi")
        labor_percent = st.slider("Ishchi kuchi foizi (%)", 0, 100, 32, 1, key="labor_percent")
    
    with st.sidebar.expander("Muhandislik va iqlim", expanded=False):
        heating = st.selectbox("Isitish", ["Yoq", "Gazli", "Elektr", "Infraqizil"], key="cons_heating")
        ventilation = st.selectbox("Shamollatish", ["Tabiiy", "Majburiy", "Rekuperatsiya"], key="cons_vent")
        electricity = st.selectbox("Elektr", ["Standart", "Kuchaytirilgan", "Sanoat"], key="cons_elec")
        plumbing = st.selectbox("Suv taminoti", ["Yoq", "Bor", "Sanoat"], key="cons_plumb")
        seismic_zone = st.selectbox("Seysmik zona", [7, 8, 9], index=1, key="cons_seismic")
        wind_region = st.selectbox("Shamol hududi", ["A", "B", "C"], index=1, key="cons_wind")
        st.divider()
        st.markdown("#### Tuproq va qor (chidamlilik hisobi uchun)")
        soil_type = st.selectbox("Tuproq turi", list(SOIL_TYPES.keys()), index=3, key="cons_soil")
        st.caption(SOIL_TYPES[soil_type]["tavsif"])
        snow_region = st.selectbox("Qor mintaqasi", list(SNOW_REGIONS.keys()), index=0, key="cons_snow_region")
    
    return {
        "construction_type": construction_type,
        "construction_name": name,
        "construction_code": code,
        "L": L, "W": W, "H": H, "roof_pitch": roof_pitch, "floors": 1,
        "column_spacing": column_spacing, 
        "wall_type": wall_type, "wall_thickness": wall_thickness,
        "floor_type": floor_type, "roof_type": roof_type,
        "window_count_front": w_front, "window_count_back": w_back,
        "window_count_left": w_left, "window_count_right": w_right,
        "window_width": window_width, "window_height": window_height,
        "door_front_count": door_front_count, 
        "door_front_width": door_front_width, 
        "door_front_height": door_front_height,
        "door_back_count": door_back_count, 
        "door_back_width": door_back_width, 
        "door_back_height": door_back_height,
        "door_left_count": door_left_count, 
        "door_left_width": door_left_width, 
        "door_left_height": door_left_height,
        "door_right_count": door_right_count, 
        "door_right_width": door_right_width, 
        "door_right_height": door_right_height,
        "floor_panel_mode": floor_panel_mode,
        # Metall narxlari
        "price_metal_column": price_column,
        "price_metal_beam": price_beam,
        "price_metal_truss": price_truss,
        "price_metal_longitudinal": price_longitudinal,
        "price_metal_purlins": price_purlins,      # 🔽 YANGI
        "price_metal_bracing": price_bracing,      # 🔽 YANGI
        "price_metal_connection": price_connection, # 🔽 YANGI
        "connection_type": connection_type,        # 🔽 YANGI
        # Qurilish materiallari
        "wall_price": wall_price,
        "roof_price": roof_price,
        "floor_price": floor_price,
        "window_price": window_price,
        "door_price": door_price,
        "price_concrete": concrete_price,
        "price_cement": cement_price,
        "price_sand": sand_price,
        "price_gravel": gravel_price,
        "price_rebar": rebar_price,
        "price_shipyak": shipyak_price,
        "labor_percent": labor_percent,
        # Muhandislik
        "heating": heating, "ventilation": ventilation,
        "electricity": electricity, "plumbing": plumbing,
        "seismic_zone": seismic_zone, "wind_region": wind_region,
        "soil_type": soil_type, "snow_region": snow_region,
         "purlin_profile": purlin_profile,
        "wall_purlin_profile": wall_purlin_profile,
        "bracing_profile": bracing_profile,
        "construction_system": construction_system,
    }





def construction_main(params):
    """Asosiy kontent - 3D vizualizatsiya va materiallar hisobi"""
    
    construction_type = params["construction_type"]
    const_info = construction_types[construction_type]

    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: {const_info['color']}; margin-bottom: 5px;">{construction_type}</h2>
        <p style="color: #666;">{params['construction_name']} | Kod: {params['construction_code']}</p>
    </div>
    """, unsafe_allow_html=True)

    materials = calculate_advanced_materials(params) 
    resilience = compute_resilience_report(params, materials)
  

    st.markdown("### 3D Vizualizatsiya")
    st.caption("Sichqoncha bilan aylantiring | Kamera tugmalarini bosing | Elementlarni yoqing/ochiring")

    total_windows = params['window_count_front'] + params['window_count_back'] + params['window_count_left'] + params['window_count_right']
    
    # Yangi darvoza parametrlari
    door_front_count = params.get("door_front_count", 1)
    door_front_width = params.get("door_front_width", 12.0)
    door_front_height = params.get("door_front_height", 6.5)
    door_back_count = params.get("door_back_count", 0)
    door_back_width = params.get("door_back_width", 12.0)
    door_back_height = params.get("door_back_height", 6.5)
    door_left_count = params.get("door_left_count", 0)
    door_left_width = params.get("door_left_width", 5.0)
    door_left_height = params.get("door_left_height", 4.0)
    door_right_count = params.get("door_right_count", 0)
    door_right_width = params.get("door_right_width", 5.0)
    door_right_height = params.get("door_right_height", 4.0)
    
    total_doors = door_front_count + door_back_count + door_left_count + door_right_count
    
    # 🔽 MUHIM: column_spacing ni olamiz
    column_spacing = params.get("column_spacing", 8.5)
    
    # 🔽 Ustunlar haqida ma'lumot qo'shamiz
    layout = compute_column_layout(params["L"], params["W"], column_spacing)
    st.info(f"""
    🏗 **Ustunlar joylashuvi:**
    - Oraliq: {column_spacing:.1f} m
    - Uzunlik bo'ylab: {layout['n_cols_x']} ta
    - Kenglik bo'ylab: {layout['n_cols_z']} ta
    - Fermalar: {layout['n_cols_x']} ta
    """)
    
    # 🔽 MUHIM: column_spacing ni uzatamiz!
    html_3d = create_construction_3d(
        params["L"], params["W"], params["H"], params["roof_pitch"],
        window_count=total_windows,
        door_front_count=door_front_count,
        door_front_width=door_front_width,
        door_front_height=door_front_height,
        door_back_count=door_back_count,
        door_back_width=door_back_width,
        door_back_height=door_back_height,
        door_left_count=door_left_count,
        door_left_width=door_left_width,
        door_left_height=door_left_height,
        door_right_count=door_right_count,
        door_right_width=door_right_width,
        door_right_height=door_right_height,
        window_width=params["window_width"],
        window_height=params["window_height"],
        window_spacing=0.0,
        seismic_zone=params.get("seismic_zone", 8),
        wind_kPa=resilience["wind"]["w_kPa"],
        snow_kg_m2=resilience["snow"]["S_kg_m2"],
        column_utilization=resilience["column_utilization"],
        foundation_utilization=resilience["foundation_utilization"],
        column_spacing=column_spacing
    )
    
    st.caption("Yuqoridagi panelda Qor / Yomg'ir / Shamol effektlarini yoqib ko'ring, yoki Zilzila testi bilan tanlangan seysmik zona va chidamlilik hisobiga mos tebranishni sinab ko'ring.")
    
    # 🔽 Unique key - Streamlit caching muammosini hal qiladi
    components.html(html_3d, height=650, scrolling=False)

    st.markdown("### Asosiy Ko'rsatkichlar")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Maydon", f"{materials['floor_area_m2']:,.0f} m²")
    with col2:
        st.metric("Metall konstruksiya", f"{materials['metal_tonna']:.2f} t")
    with col3:
        st.metric("Jami narx", f"${materials['optimized_total']:,.0f}")
    with col4:
        st.metric("1 m² narxi", f"${materials['cost_per_m2']:,.1f}")

    # ========== TABLAR ==========
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        " O'lchamlar", 
        " Materiallar", 
        " Xarajatlar", 
        " Metall tahlili", 
        " Chidamlilik",
        " Chizmalar"
    ])

    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Devor maydoni", f"{materials['wall_area_m2']:,.1f} m²")
            st.metric("Tom maydoni", f"{materials['roof_area_m2']:,.1f} m²")
            st.metric("Umumiy hajm", f"{materials['total_volume_m3']:,.1f} m³")
        with col_b:
            st.metric("Ustunlar soni", f"{materials['total_columns']} ta")
            st.metric("Fermalar soni", f"{materials['truss_count']} ta")
            total_w = params['window_count_front'] + params['window_count_back'] + params['window_count_left'] + params['window_count_right']
            st.metric("Deraza/Darvoza", f"{total_w}/{total_doors} ta")

    with tab2:
        st.markdown("####  Devor konstruksiyasi")
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        with col_w1:
            st.metric("Devor turi", params['wall_type'])
        with col_w2:
            st.metric("Qalinligi", f"{params['wall_thickness']} mm")
        with col_w3:
            st.metric("Balandligi", f"{params['H']:.1f} m")
        with col_w4:
            st.metric("Jami panellar", f"{materials['total_wall_panels']} dona")
        
        st.write(f"**Old fasad:** {materials['front_wall_net']:,.1f} m² | {materials['front_panels']} dona panel")
        st.write(f"**Orqa fasad:** {materials['back_wall_net']:,.1f} m² | {materials['back_panels']} dona panel")
        st.write(f"**Chap devor:** {materials['left_wall_net']:,.1f} m² | {materials['left_panels']} dona panel")
        st.write(f"**O'ng devor:** {materials['right_wall_net']:,.1f} m² | {materials['right_panels']} dona panel")
        st.write(f"**Fronton devori:** {materials['gable_area_m2']:,.1f} m² | {materials['gable_panels']} dona panel")
        st.divider()
        
        st.markdown("####  Darvozalar ma'lumotlari")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.write(f"**Old darvoza:** {door_front_count} ta x {door_front_width:.1f}x{door_front_height:.1f} m")
            st.write(f"**Orqa darvoza:** {door_back_count} ta x {door_back_width:.1f}x{door_back_height:.1f} m")
        with col_d2:
            st.write(f"**Chap darvoza:** {door_left_count} ta x {door_left_width:.1f}x{door_left_height:.1f} m")
            st.write(f"**O'ng darvoza:** {door_right_count} ta x {door_right_width:.1f}x{door_right_height:.1f} m")
        st.divider()
        
        st.markdown("####  Tom konstruksiyasi")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric("Tom turi", params['roof_type'])
        with col_r2:
            st.metric("Qiyaligi", f"{params['roof_pitch']:.1f}°")
        with col_r3:
            st.metric("Tom panellari", f"{materials['roof_panels']} dona")
        st.write(f"**Jami tom maydoni:** {materials['roof_area_m2']:,.1f} m²")
        st.divider()
        
        st.markdown("####  Pol konstruksiyasi")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            st.metric("Pol turi", params['floor_type'])
        with col_f2:
            st.metric("Pol maydoni", f"{materials['floor_area_m2']:,.1f} m²")
        with col_f3:
            st.metric("Pol panellari", f"{materials['floor_panels']} dona" if materials['floor_panel_mode'] else "Panel emas")
        st.divider()
        
        st.markdown("####  Beton va materiallar")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.write(f" Beton: {materials['concrete_volume_m3']:.1f} m³")
            st.write(f"🪨 Shag'al: {materials['gravel_m3']:.1f} m³")
            st.write(f" Qum: {materials['sand_m3']:.1f} m³")
        with col_b2:
            st.write(f" Sement: {materials['cement_kg']:,.0f} kg")
            st.write(f" Armatura: {materials['rebar_kg']:,.0f} kg")
        
        st.divider()
        
        # Umumiy panel hisobi
        total_kvadrat = materials['net_wall_area_m2'] + materials['roof_area_m2'] + materials['floor_area_m2']
        total_dona = materials['total_wall_panels'] + materials['roof_panels'] + materials['floor_panels']
        
        st.markdown("####  Umumiy panel hisobi")
        col_u1, col_u2, col_u3 = st.columns(3)
        with col_u1:
            st.metric("Jami kvadrat", f"{total_kvadrat:,.1f} m²")
        with col_u2:
            st.metric("Jami panellar", f"{total_dona} dona")
        with col_u3:
            st.metric("Panel kengligi", "1.0 m (standart)")

    with tab3:
        st.markdown("####  Xarajatlar tahlili")
        
        col_e1, col_e2 = st.columns(2)
        
        with col_e1:
            st.markdown("** Konstruktiv elementlar**")
            st.write(f"Metall karkas: ${materials['metal_karkas_cost']:,.0f}")
            st.write(f"Devor panellari: ${materials['wall_cost']:,.0f}")
            st.write(f"Fronton devori: ${materials['gable_wall_cost']:,.0f}")
            st.write(f"Tom qoplamasi: ${materials['roof_cost']:,.0f}")
            st.write(f"Pol qoplamasi: ${materials['floor_cost']:,.0f}")
            st.write(f"Derazalar: ${materials['window_cost']:,.0f}")
            st.write(f"Darvozalar: ${materials['door_cost']:,.0f}")
            
        with col_e2:
            st.markdown("** Beton ishlari**")
            st.write(f"Beton: ${materials['concrete_cost']:,.0f}")
            st.write(f"Armatura: ${materials['rebar_cost']:,.0f}")
            st.write(f"Sement: ${materials['cement_cost']:,.0f}")
            st.write(f"Qum: ${materials['sand_cost']:,.0f}")
            st.write(f"Shag'al: ${materials['gravel_cost']:,.0f}")
            st.write(f"Shipyak: ${materials.get('shipyak_cost', 0):,.0f}")
        
        st.divider()
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("** Umumiy xarajatlar**")
            st.write(f"Materiallar jami: ${materials['material_total']:,.0f}")
            st.write(f"Ishchi kuchi ({params.get('labor_percent', 32)}%): ${materials['labor_cost']:,.0f}")
            st.write(f"Seysmik qo'shimcha: ${materials['seismic_extra_cost']:,.0f}")
            st.write(f"Muhandislik tizimlari: ${materials['engineering_systems_cost']:,.0f}")
            
        with col_t2:
            st.markdown("** Yakuniy summa**")
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a472a 0%, #2d5a3f 100%); 
                        padding: 25px; border-radius: 15px; text-align: center; color: white;">
                <h3 style="margin: 0; color: #ffd700;">UMUMIY NARX</h3>
                <p style="font-size: 32px; font-weight: bold; margin: 10px 0;">${materials['optimized_total']:,.0f}</p>
                <hr style="border-color: #ffd700;">
                <p style="margin: 5px 0;">1 m² narxi: ${materials['cost_per_m2']:,.1f}</p>
                <p style="margin: 5px 0; font-size: 12px;">Qurilish maydoni: {materials['floor_area_m2']:.0f} m²</p>
            </div>
            """, unsafe_allow_html=True)

    # ========== TAB 4: METALL TAHLILI (TO'LIQ YANGILANGAN) ==========
    # ========== TAB 4: METALL TAHLILI ==========
    with tab4:
        st.markdown("#### Metall karkas detallari")
        
        # Hozirgi tanlangan sistemani olish
        current_system = params.get("construction_system", "LMK (Yengil Metall)")
        
        # ===== LMK va LSTK solishtirma jadvali =====
        st.markdown("### LMK va LSTK konstruksiya turlari")
        st.caption("Quyidagi jadvalda ikkala konstruksiya turining xususiyatlari ko'rsatilgan")
        
        # Jadval ma'lumotlari
        comparison_data = {
            "Xususiyat": [
                "Konstruksiya turi",
                "Material qalinligi",
                "Birikma usuli",
                "Xizmat muddati",
                "Korroziya himoyasi",
                "Maksimal oraliq",
                "Qo'llanilishi",
                "Afzalliklari",
                "Kamchiliklari"
            ],
            "LMK (Yengil Metall)": [
                "LMK",
                "8-40 mm",
                "Payvandlash yoki boltli",
                "50+ yil",
                "Qo'shimcha ishlov kerak",
                "80 metrgacha",
                "Katta oraliqli binolar, ko'p qavatli inshootlar, yirik savdo markazlari, ishlab chiqarish sexlari",
                "Yuqori mustahkamlik, katta oraliqlar, ko'p qavatli qurilish, yong'inga chidamlilik",
                "Metall sarfi yuqori, o'rnatish vaqti uzoq, korroziyaga qarshi ishlov kerak"
            ],
            "LSTK (Yengil Po'lat)": [
                "LSTK",
                "0.7-4 mm",
                "Vintli (samorezlar)",
                "35-40 yil",
                "Sinklangan (qo'shimcha ishlovsiz)",
                "30 metrgacha",
                "Qishloq xo'jaligi inshootlari, angarlar, omborlar, kichik savdo maydonlari, kam qavatli qurilish",
                "Korroziyaga chidamli, tez o'rnatiladi, yengil, transport arzon, ekologik toza",
                "Xizmat muddati qisqaroq, katta oraliqlar uchun mos emas, ko'p qavatli qurilish uchun emas"
            ]
        }
        
        # DataFrame yaratish
        df_compare = pd.DataFrame(comparison_data)
        df_compare = df_compare.set_index('Xususiyat')
        
        # Tanlangan variantni rang bilan belgilash (applymap -> map)
        def highlight_current(val):
            if current_system in str(val):
                return 'background-color: #2E7D32; color: white; font-weight: bold'
            return ''
        
        # Jadvalni ko'rsatish - map() ishlatamiz
        styled_df = df_compare.style.map(highlight_current)
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        st.divider()
        
        # ===== TANLANGAN VARIANT HAQIDA QISQA MA'LUMOT =====
        st.markdown(f"#### Tanlangan: {current_system}")
        
        if current_system == "LMK (Yengil Metall)":
            st.info("""
            **LMK** - qalin metall prokatdan tayyorlangan konstruksiya.
            
            Asosiy xususiyatlar:
            - Material: 8-40 mm
            - Birikma: Payvandlash/Bolt
            - Xizmat muddati: 50+ yil
            - Maksimal oraliq: 80 m
            - Qo'llanilishi: Katta oraliqli binolar, ko'p qavatli inshootlar
            """)
        else:
            st.info("""
            **LSTK** - yupqa sinklangan po'lat profillardan tayyorlangan konstruksiya.
            
            Asosiy xususiyatlar:
            - Material: 0.7-4 mm
            - Birikma: Vintli (samorezlar)
            - Xizmat muddati: 35-40 yil
            - Maksimal oraliq: 30 m
            - Qo'llanilishi: Angarlar, omborlar, qishloq xo'jaligi inshootlari
            """)
        
        st.divider()
        
        # ===== METALL KARKAS DETALLARI =====
        st.markdown("#### Metall karkas detallari")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        with col_m1:
            st.markdown("**Ustunlar (kolonnalar)**")
            st.metric("Soni", f"{materials['total_columns']} ta")
            st.metric("Metr", f"{materials['column_meters']:.1f} m")
            st.metric("Og'irlik", f"{materials['column_kg']:.0f} kg")
            st.metric("Tonna", f"{materials['column_tonna']:.3f} t")
            
        with col_m2:
            st.markdown("**Tosinlar (rigellar)**")
            st.metric("Metr", f"{materials['beam_meters']:.1f} m")
            st.metric("Og'irlik", f"{materials['beam_kg']:.0f} kg")
            st.metric("Tonna", f"{materials['beam_tonna']:.3f} t")
            
        with col_m3:
            st.markdown("**Fermalar**")
            st.metric("Soni", f"{materials['truss_count']} ta")
            st.metric("Metr", f"{materials['truss_meters']:.1f} m")
            st.metric("Og'irlik", f"{materials['truss_kg']:.0f} kg")
            st.metric("Tonna", f"{materials['truss_tonna']:.3f} t")
            
        with col_m4:
            st.markdown("**Uzunasiga tosinlar**")
            st.metric("Metr", f"{materials['longitudinal_meters']:.1f} m")
            st.metric("Og'irlik", f"{materials['longitudinal_kg']:.0f} kg")
            st.metric("Tonna", f"{materials['longitudinal_tonna']:.3f} t")
        
        st.divider()
        
        col_total1, col_total2, col_total3 = st.columns(3)
        with col_total1:
            st.metric("Jami metall", f"{materials['metal_tonna']:.3f} t")
        with col_total2:
            st.metric("Karkas narxi", f"${materials['metal_karkas_cost']:,.0f}")
        with col_total3:
            avg_price = materials['metal_karkas_cost'] / materials['metal_tonna'] if materials['metal_tonna'] > 0 else 0
            st.metric("1 tonna o'rtacha narxi", f"${avg_price:.0f}")
        
        # Grafik: metall tarkibi
        metal_df = pd.DataFrame({
            'Element': ['Ustunlar', 'Tosinlar', 'Fermalar', 'Uzunasiga'],
            'Og\'irlik (kg)': [
                materials['column_kg'],
                materials['beam_kg'],
                materials['truss_kg'],
                materials['longitudinal_kg']
            ],
            'Narx ($)': [
                materials['column_cost'],
                materials['beam_cost'],
                materials['truss_cost'],
                materials['longitudinal_cost']
            ]
        })
        
        col_ch1, col_ch2 = st.columns(2)
        with col_ch1:
            fig_kg = px.pie(metal_df, values='Og\'irlik (kg)', names='Element', 
                           title='Metall og\'irlik bo\'yicha taqsimot',
                           color_discrete_sequence=['#37474F', '#455A64', '#546E7A', '#607D8B'])
            fig_kg.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_kg, use_container_width=True)
            
        with col_ch2:
            fig_price = px.pie(metal_df, values='Narx ($)', names='Element',
                              title='Metall narx bo\'yicha taqsimot',
                              color_discrete_sequence=['#1B5E20', '#2E7D32', '#388E3C', '#43A047'])
            fig_price.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_price, use_container_width=True)
    with tab5:
        st.markdown("####  Tuproq, yuklamalar va konstruktiv chidamlilik")
        st.caption(
            "SNiP 2.01.07-85* / SNiP 2.02.01-83* / KMK 2.01.03-96 mantig'iga asoslangan "
            "SODDALASHTIRILGAN, loyihalashgacha bo'lgan (preliminary) tekshiruv. "
            "Real qurilishdan oldin litsenziyalangan konstruktor muhandis tomonidan "
            "to'liq hisob-kitob (Lira/SAP2000/Tekla) va geologik qidiruv natijalari "
            "asosida tasdiqlanishi SHART - bu hisob mas'uliyatni almashtirmaydi."
        )

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Tuproq turi", resilience["soil_key"])
            st.metric("Normativ qarshilik R0", f"{resilience['soil']['R0_kPa']} kPa")
        with col_s2:
            st.metric("Qor yuki", f"{resilience['snow']['S_kg_m2']:.0f} kg/m²")
            st.metric("Shamol bosimi", f"{resilience['wind']['w_kPa']*1000:.0f} Pa")
        with col_s3:
            st.metric("Seysmik bazaviy kuch", f"{resilience['seismic']['S_kg']:.0f} kg")
            st.metric("Hal qiluvchi yon yuk", resilience['governing_case'])

        st.write(f"**Tuproq tavsifi:** {resilience['soil']['tavsif']}")
        st.write(f"**Fundament tavsiyasi:** {resilience['soil']['fundament_tavsiyasi']}")

        if resilience['soil']['muzlash_tasiri']:
            st.info(f"ℹ️ Fundament chuqurligi muzlash chizig'idan ({resilience['foundation_depth_m']:.1f} m) past bo'lishi tavsiya etiladi.")
        if "cho'kuvchan" in resilience['soil_key'].lower() or "lyoss" in resilience['soil_key'].lower():
            st.warning("⚠️ Lyossimon tuproqlar suv yutganda keskin cho'kishi mumkin (просадочный grunt). Gidroizolyatsiya va suvni fundamentdan uzoqlashtirish shart.")

        st.divider()
        st.markdown("####  Ustun (kolonna) tekshiruvi")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.metric("Vertikal yuk (1 ustun)", f"{resilience['N_vertical_kg']:,.0f} kg")
            st.metric("Moment - shamol", f"{resilience['M_wind_kNm']:.1f} kNm")
            st.metric("Moment - seysmika", f"{resilience['M_seismic_kNm']:.1f} kNm")
        with col_c2:
            st.metric("Kesim yuzasi", f"{resilience['section']['A_cm2']:.0f} cm²")
            st.metric("Qarshilik momenti Wx", f"{resilience['section']['Wx_cm3']:.0f} cm³")
            st.metric("Umumiy kuchlanish σ", f"{resilience['sigma_total_MPa']:.1f} MPa")
        with col_c3:
            st.metric("Po'lat hisobiy qarshiligi Ry", f"{resilience['Ry_MPa']} MPa")
            st.progress(min(resilience['column_utilization'] / 100, 1.0))
            st.metric("Band qilinish darajasi", f"{resilience['column_utilization']:.1f}%")
        st.write(f"**Xulosa (ustun):** {resilience['column_verdict']}")

        st.divider()
        st.markdown("####  Fundament tekshiruvi")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            st.metric("Talab qilingan taglik", f"{resilience['A_required_m2']:.2f} m²")
            st.metric("Tanlangan taglik tomoni", f"{resilience['chosen_footing_side_m']:.1f} m")
        with col_f2:
            st.metric("Taglik bosimi", f"{resilience['foundation_pressure_kPa']:.1f} kPa")
            st.metric("Fundament chuqurligi", f"{resilience['foundation_depth_m']:.1f} m")
        with col_f3:
            st.progress(min(resilience['foundation_utilization'] / 100, 1.0))
            st.metric("Band qilinish darajasi", f"{resilience['foundation_utilization']:.1f}%")
        st.write(f"**Fundament turi:** {resilience['foundation_type']}")
        st.write(f"**Xulosa (fundament):** {resilience['foundation_verdict']}")

        st.divider()
        st.markdown(f"""
        <div style="background: {resilience['overall_color']}; padding: 25px; border-radius: 15px; text-align: center; color: white;">
            <h3 style="margin: 0; color: #ffffff;">UMUMIY XULOSA</h3>
            <p style="font-size: 26px; font-weight: bold; margin: 10px 0;">{resilience['overall_verdict']}</p>
            <p style="margin: 5px 0;">Eng yuqori band qilinish darajasi: {resilience['overall_utilization']:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)

    # ===== 6-TAB: ARXITEKTURA CHIZMALARI =====
    with tab6:
        st.markdown("### 🏗️ Arxitektura Chizmalari (AutoCAD uslubida)")
        st.caption("Quyidagi chizmalar professional loyiha hujjatlari uchun asos bo'lib xizmat qiladi")
        
        # Chizmalarni yaratish
        drawings = create_architectural_drawings(params, materials)
        
        # 4 ta chizmani gridda ko'rsatish
        col1, col2 = st.columns(2)
        
        with col1:
            st.pyplot(drawings['reja'], use_container_width=True)
            st.caption("📐 REJA (Top View) - AutoCAD uslubida")
        
        with col2:
            st.pyplot(drawings['fasad'], use_container_width=True)
            st.caption("📐 OLD FASAD (Front Elevation) - AutoCAD uslubida")
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.pyplot(drawings['kesim'], use_container_width=True)
            st.caption("📐 KESIM A-A (Section A-A) - AutoCAD uslubida")
        
        with col4:
            st.pyplot(drawings['izometrik'], use_container_width=True)
            st.caption("📐 3D IZOMETRIK KO'RINISH - AutoCAD uslubida")
        
        # Chizmalarni yuklab olish
        st.divider()
        st.markdown("#### 📥 Chizmalarni Yuklab Olish")
        
        col_btns = st.columns(4)

        for idx, (name, fig) in enumerate(drawings.items()):
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', 
                        facecolor=fig.get_facecolor(), edgecolor='none')
            buf.seek(0)
            
            with col_btns[idx % 4]:
                st.download_button(
                    f"📥 {name.upper()}",
                    data=buf,
                    file_name=f"{params['construction_code']}_{name}.png",
                    mime="image/png",
                    use_container_width=True
                )

    # ========== EKSPORT TUGMALARI ==========
    st.divider()
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        export_data = {
            "loyiha": {
                "nomi": params['construction_name'],
                "kodi": params['construction_code'],
                "turi": construction_type,
                "sana": datetime.now().isoformat()
            },
            "parametrlar": {k: v for k, v in params.items() if not k.startswith('_')},
            "materiallar": materials,
            "chidamlilik": resilience,
            "jami_sum": materials["optimized_total"]
        }
        st.download_button(
            "📄 JSON yuklash",
            data=json.dumps(export_data, indent=2, ensure_ascii=False),
            file_name=f"{params['construction_code']}_data.json",
            mime="application/json",
            use_container_width=True
        )

    with col_btn2:
        try:
            from io import BytesIO
            
            df_export = pd.DataFrame([materials])
            excel_buffer = BytesIO()
            
            try:
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df_export.to_excel(writer, sheet_name='Materiallar hisobi', index=False)
                    pd.DataFrame([params]).to_excel(writer, sheet_name='Loyiha parametrlari', index=False)
                excel_buffer.seek(0)
                st.download_button(
                    "📊 Excel yuklash",
                    data=excel_buffer,
                    file_name=f"{params['construction_code']}_hisobot.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except ImportError:
                st.warning("⚠️ Excel yaratish uchun 'openpyxl' kutubxonasi kerak. O'rnatish: pip install openpyxl")
        except Exception as e:
            st.warning(f"Excel yaratishda xatolik: {e}")
    