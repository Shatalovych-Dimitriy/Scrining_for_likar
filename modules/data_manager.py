import pandas as pd
import numpy as np
from datetime import datetime
from functools import reduce
import streamlit as st

# Налаштування Pandas, щоб прибрати warning про downcasting
pd.set_option('future.no_silent_downcasting', True)

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

# Словники балів
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
        if isinstance(born, str): return 0 # Якщо раптом прийшов рядок
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except:
        return 0

def calculate_section_score(df, tag, mapping):
    cols = [c for c in df.columns if tag in c]
    if not cols:
        # print(f"⚠️ Увага: Не знайдено колонок з тегом '{tag}'")
        return 0
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
    # Виправив дублювання умови:
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
    age = row.get('Вік', 0)
    sbp = row.get('[SCORE2] Систолічний артеріальний тиск', 0)
    chol = row.get('[SCORE2] Рівень non-HDL холестерину (ммоль/л)', 0)

    # Захист від помилок, якщо вік не пораховано
    if age == 0: return "⚪ Недостатньо даних (Вік)"

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

    if is_green(): return "🟢 Зелений"
    elif is_yellow(): return "🟡 Жовтий"
    else: return "🔴 червоний"

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
        # Безпечна обробка
        df[smoke_qty_col] = pd.to_numeric(df[smoke_qty_col], errors='coerce').fillna(0)
        df[smoke_qty_col] = pd.cut(
            df[smoke_qty_col], 
            bins=[-1, 10, 20, 30, float('inf')], 
            labels=[0, 1, 2, 3]
        ).astype(int)
    
    df['Score_Smoke'] = calculate_section_score(df, '[Паління]', POINTS_MAP_SMOKE)
    df['Verdict_Smoke'] = df['Score_Smoke'].apply(get_smoke_verdict)

    # AUDIT
    df['Score_Audit'] = calculate_section_score(df, '[ AUDIT]', POINTS_MAP_AUDIT) 
    df['Verdict_Audit'] = df['Score_Audit'].apply(get_audit_verdict)

    df['Status_Patient_Done'] = True
    return df


def process_doctor_data(df):
    df = df.copy()

    # Вік тут вже повинен бути порахований в головній функції, але для перестраховки:
    if 'Вік' not in df.columns:
         if 'Дата народження' in df.columns:
             # Переконуємось, що дата у форматі datetime
             df['Дата народження'] = pd.to_datetime(df['Дата народження'], errors='coerce')
             df['Вік'] = df['Дата народження'].apply(calculate_age)
    
    # SCORE2
    score2_numeric_cols = [
        '[SCORE2] Систолічний артеріальний тиск', 
        '[SCORE2] Рівень non-HDL холестерину (ммоль/л)'
    ]
    for col in score2_numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    if all(col in df.columns for col in score2_numeric_cols):
        df['Verdict_Score2'] = df.apply(get_score2_verdict_row, axis=1)

    # FINDRISC
    # Використовуємо infer_objects для уникнення warning
    df = df.replace(FINDRISC_MAPPING).infer_objects(copy=False)

    # Age Score
    if 'Вік' in df.columns:
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
    col_sex = 'Вкажіть стать'
    
    if col_waist in df.columns and col_sex in df.columns:
        df[col_waist] = pd.to_numeric(df[col_waist], errors='coerce').fillna(0)
        
        # Векторизована логіка через numpy select
        is_male = df[col_sex] == 'чоловік'
        waist = df[col_waist]
        
        conditions = [
            (is_male & (waist > 102)) | (~is_male & (waist > 88)), # Високий ризик (4 бали)
            (is_male & (waist > 94) & (waist <= 102)) | (~is_male & (waist > 80) & (waist <= 88)) # Середній ризик (3 бали)
        ]
        
        # Якщо нічого не підійшло - 0 балів. 
        # (У вашому попередньому коді були інші межі, я поставив стандартні Findrisk, але перевірте їх)
        df[col_waist] = np.select(conditions, [4, 3], default=0)

    # Sum Score
    findrisc_cols = [c for c in df.columns if '[Findrisc]' in c]
    # Перетворюємо все у числа
    for c in findrisc_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
    df['Score_FINDRISC'] = df[findrisc_cols].sum(axis=1)
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
            df = df.fillna(0)
            
            # --- 1. УНІФІКАЦІЯ НАЗВ ---
            # Перейменовуємо "ПІБ" (з identity_map) в "ПІБ" (для злиття)
            # Якщо у csv назва інша - перейменовуємо. Якщо така сама - залишаємо.
            rename_dict = {v: k for k,v in conf["identity_map"].items() if v in df.columns}
            # У нашому випадку "ПІБ"->"Name", але ми хочемо залишити українські назви для зручності
            # Тому зробимо навпаки: перейменуємо так, щоб скрізь було ['ПІБ', 'Дата народження']
            
            # Оскільки ми в конфізі пишемо "Name": "ПІБ", це значить, що ми очікуємо колонку "ПІБ" в CSV.
            # І для merge нам треба колонка "ПІБ". Тобто перейменовувати нічого не треба, 
            # ЯКЩО в усіх CSV колонки називаються однаково.
            
            # АЛЕ, щоб злиття працювало гарантовано, треба переконатись, що колонки є.
            target_pib = conf["identity_map"]["Name"]
            target_dob = conf["identity_map"]["DOB"]
            
            if target_pib not in df.columns or target_dob not in df.columns:
                print(f"Помилка: Не знайдено ключових колонок у {conf['name']}")
                continue
                
            # Перейменуємо в стандартні для програми ключі (на всяк випадок)
            df = df.rename(columns={target_pib: 'ПІБ', target_dob: 'Дата народження'})
            
            # --- 2. ОБРОБКА ТИПІВ ДАНИХ (ВИРІШЕННЯ ПОМИЛКИ MERGE) ---
            # Конвертуємо Дату народження у datetime, щоб merge не ламався
            df['Дата народження'] = pd.to_datetime(df['Дата народження'], errors='coerce', dayfirst=True)
            # Конвертуємо ПІБ у рядок і прибираємо зайві пробіли
            df['ПІБ'] = df['ПІБ'].astype(str).str.strip()

            # --- 3. ЧИСТКА ---
            if 'Позначка часу' in df.columns:
                df = df.sort_values('Позначка часу', ascending=False)
            
            # Видаляємо дублікати (залишаємо найсвіжіший запис)
            # Важливо: dropna subset, щоб не зливати пусті рядки
            df = df.dropna(subset=['ПІБ', 'Дата народження'])
            df = df.drop_duplicates(subset=['ПІБ', 'Дата народження'], keep='first')
            
            # Розрахунок віку (бо він потрібен і там і там)
            df['Вік'] = df['Дата народження'].apply(calculate_age)

            # --- 4. РОЗРАХУНКИ ---
            if conf["id"] == "doctor_form":
                df = process_doctor_data(df)
            elif conf["id"] == "patient_form":
                df = process_patient_data(df)

            dfs_to_merge.append(df)
            
        except Exception as e:
            print(f"Помилка при обробці форми {conf['name']}: {e}")

    if not dfs_to_merge:
        return pd.DataFrame()

    # --- 5. ЗШИВАННЯ ---
    try:
        full_df = reduce(
            lambda left, right: pd.merge(
                left, right, 
                on=['ПІБ', 'Дата народження'], 
                how='outer', 
                suffixes=('_doc', '_pat')
            ), 
            dfs_to_merge
        )
        
        # --- 6. ОБ'ЄДНАННЯ ДУБЛЬОВАНИХ КОЛОНОК ---
        # Після merge можуть з'явитися Вік_doc, Вік_pat. Об'єднаємо їх.
        if 'Вік_doc' in full_df.columns and 'Вік_pat' in full_df.columns:
            full_df['Вік'] = full_df['Вік_doc'].combine_first(full_df['Вік_pat'])
        elif 'Вік_doc' in full_df.columns:
            full_df['Вік'] = full_df['Вік_doc']
            
        # --- 7. ФІНАЛІЗАЦІЯ СТАТУСІВ ---
        
        # 1. Заповнюємо False там, де форми не було
        full_df['Status_Doctor_Done'] = full_df['Status_Doctor_Done'].fillna(False)
        full_df['Status_Patient_Done'] = full_df['Status_Patient_Done'].fillna(False)

        # 2. Функція для текстового статусу
        def get_row_status(row):
            if row['Status_Doctor_Done'] and row['Status_Patient_Done']:
                return "✅ Повний комплект"
            elif row['Status_Doctor_Done']:
                return "⚠️ Тільки лікар (пацієнт не заповнив)"
            elif row['Status_Patient_Done']:
                return "⏳ Очікує огляду лікаря"
            else:
                return "❓ Дані відсутні"

        # 3. Застосовуємо статус
        if not full_df.empty:
            full_df['Загальний статус'] = full_df.apply(get_row_status, axis=1)

        return full_df

    except Exception as e:
        st.error(f"Помилка злиття даних: {e}") # Виводимо на екран
        print(f"Помилка злиття: {e}")
        return pd.DataFrame()
