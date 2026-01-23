import pandas as pd
import numpy as np
from datetime import datetime
from functools import reduce  # Потрібно для злиття таблиць
import streamlit as st
# ==========================================
# 1. КОНФІГУРАЦІЯ ТА КОНСТАНТИ
# ==========================================

FORMS_CONFIG = [
    {   "id": "doctor_form",
        "name": "Лікар",
        "url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4Fkc0NoXeUR3pPuJXfJvf48jIrLPYeFiQyF7kWAT4W5ilsPddahcVjYpg15N-uJqbKzrps5nUPUiQ/pub?gid=584209057&single=true&output=csv",
        "tags": ["Findrisc", "SCORE2"],
        "identity_map": {"Name": "ПІБ", "DOB": "Дата народження"}
    },
    {   "id": "patient_form",
        "name": "Пацієнт",
        "url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSF_ZRq1NV9VwXR8PA9YPVCqIJ1MRwoZnA2Ec0Sz4CMMhU98dZIZU4BtIo4pH6oM7J4-E_VasWzCEqM/pub?gid=330455959&single=true&output=csv",
        "tags": ["PHQ", "GAD","Паління","AUDIT"],
        "identity_map": {"Name": "ПІБ", "DOB": "Дата народження"}
    }
]

# Словники балів (Винесені назовні, щоб не створювати їх щоразу при виклику функції)
POINTS_MAP_GAD = {
    "Ніколи": 0, "Кілька днів": 1, "Понад половину часу": 2, "Майже щодня": 3
}
POINTS_MAP_PHQ = {
    "Не турбували взагалі": 0, "Протягом декількох днів": 1, "Більше половини цього часу": 2, "Майже кожного дня": 3
}
POINTS_MAP_SMOKE = {
    "Через 1 год.": 0, "Від 1/2 до 1 години": 1, "Від 6 до 30 хв.": 2,
    "5 хв або менше": 3, "Ні": 1, "Так": 2,
    "Будь-якої іншої": 1, "Першої вранці": 3
}
POINTS_MAP_AUDIT = {
    "Ніколи": 0, "Один раз на місяць або рідше": 1, "2–4 рази на місяць": 2,
    "2–3 рази на тиждень": 3, "4 рази на тиждень або частіше": 4, "Щомісяця": 2,
    "Щотижня": 3, "Щодня або майже щодня": 4,
    "1–2 СП": 0, "3–4 СП": 1, "5–6 СП": 2, "7–9 СП": 3, "10 СП і більше": 4,
    "Ні": 0, "Так, більше ніж 12 місяців тому": 2, "Так, упродовж останніх 12 місяців": 4
}
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
    if pd.isnull(born):
        return 0
    today = datetime.today()
    try:
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except:
        return 0

def calculate_section_score(df, tag, mapping):
    """Універсальна функція для підрахунку балів за словником"""
    cols = [c for c in df.columns if tag in c]
    if not cols:
        print(f"⚠️ Увага: Не знайдено колонок з тегом '{tag}'")
        return 0
    # map(mapping) замінює текст на цифри, fillna(0) прибирає пропуски
    return df[cols].apply(lambda x: x.map(mapping)).fillna(0).sum(axis=1)

# --- Вердикти ---

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
    if s >= 8: return "🟡 Споживання з низьким ризиком" # Тут дублюється умова >=8, перевірте логіку
    return "🟢 Ймовірно пацієнт утримується від споживання"

def get_findrisc_verdict(s):
    if s > 20: return "🔴 Дуже високий ризик: 1 із 2 (50%)"
    if s >= 15: return "🟠 Високий ризик: 1 із 3 (33%)"
    if s >= 12: return "🟡 Помірний ризик: 1 із 6 (16%)"
    if s >= 7: return "🟢 Дещо підвищений ризик: 1 із 25 (4%)"
    return "✅ Низький ризик: 1 із 100 (1%)"

def get_score2_verdict_row(row):
    """Логіка SCORE2 (оптимізована)"""
    sex = row['Вкажіть стать']
    smoke = row['[SCORE2] Куріння тютюнових виробів']
    age = row['Вік']
    sbp = row['[SCORE2] Систолічний артеріальний тиск']
    chol = row['[SCORE2] Рівень non-HDL холестерину (ммоль/л)']

    def is_green():
        if sex == 'жінка' and smoke == 'Ні':
            if age < 45 and sbp < 120 and chol <= 5: return True
            if 49 < age < 55 and sbp < 120 and chol <= 3: return True
        return False

    def is_yellow():
        if sbp >= 180 or chol >= 8: return False
        
        # ЖІНКИ
        if sex == 'жінка':
            if smoke == 'Ні':
                if age < 50: return True 
                if 50 <= age < 55: return not (sbp >= 160 or (sbp >= 140 and chol >= 6))
                if 55 <= age < 60: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 60 <= age < 70: return not (sbp >= 140 or chol >= 6)
                if 70 <= age < 90: return not (sbp >= 160 or chol >= 7)
            else: # Палять
                if age < 50: return not (sbp >= 160 or (sbp >= 140 and chol >= 6))
                if 50 <= age < 55: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 55 <= age < 70: return not (sbp >= 140 or (sbp >= 120 and chol >= 5))
                if 70 <= age < 90: return not (sbp >= 140 or chol >= 6)
        
        # ЧОЛОВІКИ
        elif sex == 'чоловік':
            if smoke == 'Ні':
                if age < 50: return not (sbp >= 160 or (sbp >= 140 and chol >= 6))
                if 50 <= age < 55: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 55 <= age < 70: return not (sbp >= 140 or chol >= 6)
                if 70 <= age < 90: return not (sbp >= 140 or chol >= 6)
            else: # Палять
                if age < 50: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 50 <= age < 55: return not (sbp >= 140 or chol >= 6)
                if 55 <= age < 70: return not (sbp >= 120 or chol >= 4)
                if 70 <= age < 90: return not (sbp >= 120 or chol >= 5)
        return False

    if is_green(): return "🟢"
    elif is_yellow(): return "🟡"
    else: return "🔴"

# ==========================================
# 3. ФУНКЦІЇ ОБРОБКИ ДАНИХ
# ==========================================

def process_patient_data(df):
    df = df.copy()
    
    # PHQ-9
    df['Score_PHQ'] = calculate_section_score(df, '[PHQ]', POINTS_MAP_PHQ)
    df['Verdict_PHQ'] = df['Score_PHQ'].apply(get_depression_verdict)
    
    # GAD-7
    df['Score_GAD'] = calculate_section_score(df, '[GAD]', POINTS_MAP_GAD)
    df['Verdict_GAD'] = df['Score_GAD'].apply(get_gad7_verdict)

    # Smoke
    smoke_qty_col = '[Паління] 4. Скільки сигарет ви викурюєте на день?'
    if smoke_qty_col in df.columns:
         # Заповнюємо нулями пропуски перед cut, щоб уникнути помилок
        df[smoke_qty_col] = df[smoke_qty_col].fillna(0)
        df[smoke_qty_col] = pd.cut(
            df[smoke_qty_col], 
            bins=[-1, 10, 20, 30, float('inf')], 
            labels=[0, 1, 2, 3]
        ).astype(int)
    
    df['Score_Smoke'] = calculate_section_score(df, '[Паління]', POINTS_MAP_SMOKE)
    df['Verdict_Smoke'] = df['Score_Smoke'].apply(get_smoke_verdict)

    # AUDIT
    df['Score_Audit'] = calculate_section_score(df, '[ AUDIT]', POINTS_MAP_AUDIT) # Перевірте пробіл у тезі
    df['Verdict_Audit'] = df['Score_Audit'].apply(get_audit_verdict)

    df['Status_Patient_Done'] = True
    return df


def process_doctor_data(df):
    df = df.copy()

    # 1. Дата та Вік
    df['Дата народження'] = pd.to_datetime(df['Дата народження'], errors='coerce')
    df['Вік'] = df['Дата народження'].apply(calculate_age)
    
    # 2. SCORE2
    score2_numeric_cols = [
        '[SCORE2] Систолічний артеріальний тиск', 
        '[SCORE2] Рівень non-HDL холестерину (ммоль/л)'
    ]
    # Конвертуємо в числа для безпеки
    for col in score2_numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    if all(col in df.columns for col in score2_numeric_cols):
        df['Verdict_Score2'] = df.apply(get_score2_verdict_row, axis=1)

    # 3. FINDRISC
    df = df.replace(FINDRISC_MAPPING) # Важливо: зберегли результат

    # Age Score
    df['[Findrisc] Вік'] = pd.cut(
        df['Вік'], bins=[0, 44, 54, 64, float('inf')], labels=[0, 2, 3, 4], include_lowest=True
    ).fillna(0).astype(int)

    # BMI Score
    col_bmi = '[Findrisc] ІМТ (кг/м2)'
    if col_bmi in df.columns:
        df[col_bmi] = pd.to_numeric(df[col_bmi], errors='coerce')
        df[col_bmi] = pd.cut(
            df[col_bmi], bins=[0, 24, 30, float('inf')], labels=[0, 1, 3], include_lowest=True
        ).fillna(0).astype(int)

    # Waist Score
    col_waist = '[Findrisc] Окружність талії, виміряна нижче ребер (см)'
    if col_waist in df.columns:
        df[col_waist] = pd.to_numeric(df[col_waist], errors='coerce').fillna(0)
        limit_high = np.where(df['Вкажіть стать'] == 'чоловік', 102, 88)
        limit_mid  = np.where(df['Вкажіть стать'] == 'чоловік', 93, 79)
        conditions = [df[col_waist] > limit_high, df[col_waist] > limit_mid]
        df[col_waist] = np.select(conditions, [4, 3], default=0)

    # Sum Score
    findrisc_cols = [c for c in df.columns if '[Findrisc]' in c]
    df[findrisc_cols] = df[findrisc_cols].apply(pd.to_numeric, errors='coerce')
    df['Score_FINDRISC'] = df[findrisc_cols].fillna(0).sum(axis=1)
    df['Verdict_FINDRISC'] = df['Score_FINDRISC'].apply(get_findrisc_verdict)
    
    df['Status_Doctor_Done'] = True
    return df

# ==========================================
# 4. ГОЛОВНИЙ МЕРДЖЕР (ОБ'ЄДНУВАЧ)
# ==========================================
@st.cache_data(ttl=60)
def get_processed_data():
    dfs_to_merge = []

    for conf in FORMS_CONFIG:
        try:
            print(f"Завантаження: {conf['name']}...")
            df = pd.read_csv(conf["url"])
            # --- ТИМЧАСОВА ВСТАВКА ДЛЯ ДІАГНОСТИКИ ---
            st.write(f"📂 Форма: {conf['name']}")
            st.write("Знайдені колонки:", df.columns.tolist())
            # -----------------------------------------
            # Базова очистка
            df = df.fillna(0)
            
            # Перейменування колонок (ідентифікаторів)
            # Припускаємо, що у конфізі identity_map правильний для кожної форми
            # Але краще робити rename тут, якщо імена в csv відрізняються
            # df = df.rename(columns=conf["identity_map"]) 

            # Сортування та видалення дублікатів
            if 'Позначка часу' in df.columns:
                df = df.sort_values('Позначка часу', ascending=False)
            
            # Видалення дублікатів по ключових полях
            # Переконаємось, що поля існують
            key_cols = list(conf["identity_map"].values()) # ['ПІБ', 'Дата народження']
            
            # Тимчасово перейменуємо для уніфікації перед злиттям, якщо вони ще не перейменовані
            df = df.rename(columns={k: v for k,v in conf["identity_map"].items() if k in df.columns})
            
            # Видаляємо дублікати
            if all(col in df.columns for col in key_cols):
                 df = df.drop_duplicates(subset=key_cols, keep='first')
            
            # Обробка специфічних даних
            if conf["id"] == "doctor_form":
                df = process_doctor_data(df)
            elif conf["id"] == "patient_form":
                df = process_patient_data(df)

            dfs_to_merge.append(df)
            
        except Exception as e:
            print(f"Помилка при обробці форми {conf['name']}: {e}")

    if not dfs_to_merge:
        return pd.DataFrame()

    # ЗШИВАННЯ (OUTER JOIN)
    try:
        # Для злиття нам треба, щоб ключові колонки називалися однаково у всіх DF
        # У FORMS_CONFIG ми вказали: "Name" -> "ПІБ", "DOB" -> "Дата народження"
        # Тому зливаємо по 'ПІБ' та 'Дата народження'
        
        full_df = reduce(
            lambda left, right: pd.merge(
                left, right, 
                on=['ПІБ', 'Дата народження'],  # Зливаємо по уніфікованих іменах
                how='outer', 
                suffixes=('_doc', '_pat')
            ), 
            dfs_to_merge
        )
        return full_df
    except Exception as e:
        print(f"Помилка злиття даних: {e}")
        return pd.DataFrame()

# ==========================================
# ЗАПУСК
# ==========================================
# final_df = get_processed_data()
# print(final_df.head())
