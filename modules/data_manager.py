import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from functools import reduce

# Налаштування Pandas
pd.set_option('future.no_silent_downcasting', True)

# ==========================================
# 1. КОНФІГУРАЦІЯ ТА КОНСТАНТИ
# ==========================================
try:
    url_doctor = st.secrets["links"]["doktor_link"]
    url_patient = st.secrets["links"]["patient_link"]
except Exception:
    url_doctor = ""
    url_patient = ""

FORMS_CONFIG = [
    {   "id": "doctor_form",
        "name": "Лікар",
        "url": url_doctor,
        "tags": ["Findrisc", "SCORE2"],
        "identity_map": {"Name": "ПІБ", "DOB": "Дата народження"}
    },
    {   "id": "patient_form",
        "name": "Пацієнт",
        "url": url_patient,
        "tags": ["PHQ", "GAD","Паління","AUDIT"],
        "identity_map": {"Name": "ПІБ", "DOB": "Дата народження"}
    }
]

# Словники балів (Ваші словники без змін)
POINTS_MAP_GAD = {"Ніколи": 0, "Кілька днів": 1, "Понад половину часу": 2, "Майже щодня": 3}
POINTS_MAP_PHQ = {"Не турбували взагалі": 0, "Протягом декількох днів": 1, "Більше половини цього часу": 2, "Майже кожного дня": 3}
POINTS_MAP_SMOKE = {"Через 1 год.": 0, "Від 1/2 до 1 години": 1, "Від 6 до 30 хв.": 2, "5 хв або менше": 3, "Ні": 1, "Так": 2, "Будь-якої іншої": 1, "Першої вранці": 3}
POINTS_MAP_AUDIT = {"Ніколи": 0, "Один раз на місяць або рідше": 1, "2–4 рази на місяць": 2, "2–3 рази на тиждень": 3, "4 рази на тиждень або частіше": 4, "Щомісяця": 2, "Щотижня": 3, "Щодня або майже щодня": 4, "1–2 СП": 0, "3–4 СП": 1, "5–6 СП": 2, "7–9 СП": 3, "10 СП і більше": 4, "Ні": 0, "Так, більше ніж 12 місяців тому": 2, "Так, упродовж останніх 12 місяців": 4}
FINDRISC_MAPPING = {
    '[Findrisc] Чи маєте ви щодня принаймні 30 хв фізичної активності на роботі та/ або у вільний час (включно зі звичайною щоденною активністю)': {"Так": 0, "Ні": 1},
    '[Findrisc] Як часто ви їсте овочі, фрукти або ягоди?': {'Кожного дня': 0, 'Не кожного дня': 1},
    '[Findrisc] Чи приймали ви коли-небудь регулярно ліки від підвищеного тиску?': {'Ні': 0, 'Так': 2},
    '[Findrisc] Чи виявляли у вас коли-небудь підвищений рівень глюкози в крові (наприклад, під час медичного огляду, хвороби або вагітності)?': {"Так": 5, "Ні": 0},
    '[Findrisc] Чи був у когось із ваших близьких родичів або інших родичів діагностований цукровий діабет 1 або 2 типу?': {"Так: у батьків, братів, сестер або дітей": 5, "Так: тільки у дідуся/бабусі, тітки, дядька або двоюрідного брата/сестри": 3, 'Ні': 0},
}

# ==========================================
# 2. ДОПОМІЖНІ ФУНКЦІЇ (HELPERS)
# ==========================================

def calculate_age(born):
    if pd.isnull(born): return 0
    today = datetime.today()
    try:
        if isinstance(born, str): return 0
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except: return 0

def calculate_section_score(df, tag, mapping):
    cols = [c for c in df.columns if tag in c]
    if not cols: return 0
    return df[cols].apply(lambda x: x.map(mapping)).fillna(0).sum(axis=1)

# Вердикти (Ваші функції без змін)
def get_depression_verdict(s):
    if s >= 20: return "🔴 Тяжка депресія"
    if s >= 15: return "🟠 Середньої тяжкості депресія"
    if s >= 10: return "🟡 Помірної тяжкості депресія"
    if s >= 5:  return "🟢 Легка («субклінічна») депресія"
    return "⚪ Депресія відсутня"

def get_gad7_verdict(s):
    if s >= 15: return "🔴 Клінічно значимі симптоми"
    if s >= 10: return "🟠 Помірні симптоми"
    if s >= 5:  return "🟡 Легкі симптоми"
    return "🟢 Без симптомів"

def get_smoke_verdict(s):
    if s >= 8: return "🔴 Дуже високий рівень нікотинової залежності"
    if s >= 6: return "🟠 Високий рівень нікотинової залежності"
    if s >= 1: return "🟡 Низький рівень нікотинової залежності"
    return "🟢 Без нікотинової залежності"

def get_audit_verdict(s):
    if s >= 20: return "🔴 Можлива алкогольна залежність"
    if s >= 8: return "🟠 Споживання з високим ризиком"
    if s >= 1: return "🟡 Споживання з низьким ризиком" 
    return "🟢 Ймовірно пацієнт утримується від споживання"

def get_findrisc_verdict(s):
    if s > 20: return "🔴 Дуже високий ризик: 1 із 2 (50%)"
    if s >= 15: return "🟠 Високий ризик: 1 із 3 (33%)"
    if s >= 12: return "🟡 Помірний ризик: 1 із 6 (16%)"
    if s >= 7: return "🟢 Дещо підвищений ризик: 1 із 25 (4%)"
    return "✅ Низький ризик: 1 із 100 (1%)"

def get_score2_verdict_row(row):
    sex = row.get('Вкажіть стать', 'Не вказано')
    smoke = row.get('[SCORE2] Куріння тютюнових виробів', 'Ні')
    age = int(row.get('Вік', 0))
    sbp = float(row.get('[SCORE2] Систолічний артеріальний тиск', 0))
    chol = float(row.get('[SCORE2] Рівень non-HDL холестерину (ммоль/л)', 0))

    if age == 0: return "⚪ Недостатньо даних (Вік)"
    if chol <= 0: return "⚪ Введіть холестерин"

    def is_green():
        if sex == 'жінка' and smoke == 'Ні':
            if age < 45 and sbp < 120 and chol <= 5: return True
            if 49 < age < 55 and sbp < 120 and chol <= 3: return True
        return False

    def is_yellow():
        if sbp >= 180 or chol >= 8: return False
        if sex == 'жінка':
            if smoke == 'Ні':
                if age < 50: return True 
                if 50 <= age < 55: return not (sbp >= 160 or (sbp >= 140 and chol >= 6))
                if 55 <= age < 60: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 60 <= age < 70: return not (sbp >= 140 or chol >= 6)
                if 70 <= age < 90: return not (sbp >= 160 or chol >= 7)
            else: 
                if age < 50: return not (sbp >= 160 or (sbp >= 140 and chol >= 6))
                if 50 <= age < 55: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 55 <= age < 70: return not (sbp >= 140 or (sbp >= 120 and chol >= 5))
                if 70 <= age < 90: return not (sbp >= 140 or chol >= 6)
        elif sex == 'чоловік':
            if smoke == 'Ні':
                if age < 50: return not (sbp >= 160 or (sbp >= 140 and chol >= 6))
                if 50 <= age < 55: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 55 <= age < 70: return not (sbp >= 140 or chol >= 6)
                if 70 <= age < 90: return not (sbp >= 140 or chol >= 6)
            else:
                if age < 50: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 50 <= age < 55: return not (sbp >= 140 or chol >= 6)
                if 55 <= age < 70: return not (sbp >= 120 or chol >= 4)
                if 70 <= age < 90: return not (sbp >= 120 or chol >= 5)
        return False

    if is_green(): return "🟢 Низький ризик"
    elif is_yellow(): return "🟡 Помірний ризик"
    else: return "🔴 Високий ризик"

# ==========================================
# 3. ФУНКЦІЇ ОБРОБКИ ДАНИХ
# ==========================================

def process_patient_data(df):
    df = df.copy()
    df['Score_PHQ'] = calculate_section_score(df, '[PHQ]', POINTS_MAP_PHQ)
    df['Verdict_PHQ'] = df['Score_PHQ'].apply(get_depression_verdict)
    df['Score_GAD'] = calculate_section_score(df, '[GAD]', POINTS_MAP_GAD)
    df['Verdict_GAD'] = df['Score_GAD'].apply(get_gad7_verdict)

    smoke_qty_col = '[Паління] 4. Скільки сигарет ви викурюєте на день?'
    if smoke_qty_col in df.columns:
        df[smoke_qty_col] = pd.to_numeric(df[smoke_qty_col], errors='coerce').fillna(0)
        df[smoke_qty_col] = pd.cut(df[smoke_qty_col], bins=[-1, 10, 20, 30, float('inf')], labels=[0, 1, 2, 3]).astype(int)
    
    df['Score_Smoke'] = calculate_section_score(df, '[Паління]', POINTS_MAP_SMOKE)
    df['Verdict_Smoke'] = df['Score_Smoke'].apply(get_smoke_verdict)
    df['Score_Audit'] = calculate_section_score(df, '[ AUDIT]', POINTS_MAP_AUDIT) 
    df['Verdict_Audit'] = df['Score_Audit'].apply(get_audit_verdict)
    df['Status_Patient_Done'] = True
    return df

def process_doctor_data(df):
    df = df.copy()
    if 'Вік' not in df.columns and 'Дата народження' in df.columns:
         df['Дата народження'] = pd.to_datetime(df['Дата народження'], errors='coerce')
         df['Вік'] = df['Дата народження'].apply(calculate_age)
    
    score2_numeric_cols = ['[SCORE2] Систолічний артеріальний тиск', '[SCORE2] Рівень non-HDL холестерину (ммоль/л)']
    for col in score2_numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # SCORE2 вердикт тут не рахуємо, бо холестерин ще може змінитися
    
    # FINDRISK
    df['Score_FINDRISK'] = 0
    for col_name, mapping in FINDRISC_MAPPING.items():
        if col_name in df.columns: df['Score_FINDRISK'] += df
