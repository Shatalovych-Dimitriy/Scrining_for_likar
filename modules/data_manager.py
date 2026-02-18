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
    url_corrections = st.secrets["links"]["corrections_url"]
except Exception:
    url_doctor = ""
    url_patient = ""
    url_corrections = ""

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
# 3. ФУНКЦІЇ ОБРОБКИ ДАНИХ (ВАШІ СТАРІ ПРОЦЕСОРИ)
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
         # Вік тут рахується, але для надійності будемо використовувати age з головного процесу
         pass
    
    score2_numeric_cols = ['[SCORE2] Систолічний артеріальний тиск', '[SCORE2] Рівень non-HDL холестерину (ммоль/л)']
    for col in score2_numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # FINDRISC
    df['Score_FINDRISK'] = 0
    for col_name, mapping in FINDRISC_MAPPING.items():
        if col_name in df.columns: df['Score_FINDRISK'] += df[col_name].map(mapping).fillna(0)

    if 'Вік' in df.columns:
        age_points = pd.cut(df['Вік'], bins=[0, 44, 54, 64, float('inf')], labels=[0, 2, 3, 4], include_lowest=True).fillna(0).astype(int)
        df['Score_FINDRISK'] += age_points

    col_bmi = '[Findrisc] ІМТ (кг/м2)'
    if col_bmi in df.columns:
        bmi_numeric = pd.to_numeric(df[col_bmi], errors='coerce')
        bmi_points = pd.cut(bmi_numeric, bins=[0, 25, 30, float('inf')], labels=[0, 1, 3], include_lowest=True, right=False).fillna(0).astype(int)
        df['Score_FINDRISK'] += bmi_points

    col_waist = '[Findrisc] Окружність талії, виміряна нижче ребер (см)'
    col_sex = 'Вкажіть стать'
    if col_waist in df.columns and col_sex in df.columns:
        waist_numeric = pd.to_numeric(df[col_waist], errors='coerce').fillna(0)
        is_male = df[col_sex] == 'чоловік'
        conditions = [(is_male & (waist_numeric > 102)) | (~is_male & (waist_numeric > 88)), (is_male & (waist_numeric > 94)) | (~is_male & (waist_numeric > 80))]
        waist_points = np.select(conditions, [4, 3], default=0)
        df['Score_FINDRISK'] += waist_points

    df['Verdict_FINDRISK'] = df['Score_FINDRISK'].apply(get_findrisc_verdict)
    df['Status_Doctor_Done'] = True
    return df    

# ==========================================
# 4. ГОЛОВНИЙ МЕРДЖЕР (ОНОВЛЕНИЙ ЧЕРЕЗ PANDAS MERGE) 🚀
# ==========================================
@st.cache_data(ttl=60)
def get_processed_data():
    dfs_to_merge = []

    # --- ЕТАП 1: ЗАВАНТАЖЕННЯ ОСНОВНИХ ДАНИХ ---
    for conf in FORMS_CONFIG:
        try:
            if not conf["url"]: continue
            df = pd.read_csv(conf["url"]).fillna(0)
            
            # Перейменування
            target_pib = conf["identity_map"]["Name"]
            target_dob = conf["identity_map"]["DOB"]
            if target_pib not in df.columns: continue
            df = df.rename(columns={target_pib: 'ПІБ', target_dob: 'Дата народження'})
            
            # === PANDAS МАГІЯ ДАТ ===
            # errors='coerce' перетворить сміття на NaT (Not a Time), програма не впаде
            # dayfirst=True важливий для наших форматів 25.01.2000
            df['Дата народження'] = pd.to_datetime(df['Дата народження'], dayfirst=True, errors='coerce')
            
            # Чистка ПІБ
            df['ПІБ'] = df['ПІБ'].astype(str).str.strip()
            
            # Видаляємо тих, у кого крива дата або немає імені
            df = df.dropna(subset=['ПІБ', 'Дата народження'])
            
            # Сортуємо і лишаємо свіжі
            if 'Позначка часу' in df.columns: df = df.sort_values('Позначка часу', ascending=False)
            df = df.drop_duplicates(subset=['ПІБ', 'Дата народження'], keep='first')
            
            df['Вік'] = df['Дата народження'].apply(calculate_age)

            if conf["id"] == "doctor_form": df = process_doctor_data(df)
            elif conf["id"] == "patient_form": df = process_patient_data(df)
            
            dfs_to_merge.append(df)
        except Exception as e:
            print(f"Error loading {conf['name']}: {e}")

    if not dfs_to_merge: return pd.DataFrame()

    # Злиття Лікаря і Пацієнта
    full_df = reduce(lambda l, r: pd.merge(l, r, on=['ПІБ', 'Дата народження'], how='outer', suffixes=('_doc', '_pat')), dfs_to_merge)
    
    # Об'єднання віку
    if 'Вік_doc' in full_df.columns: full_df['Вік'] = full_df['Вік_doc'].combine_first(full_df.get('Вік_pat'))
    
    # Виправляємо проблему з типами після merge (щоб не було NaN у булевих колонках)
    full_df['Status_Doctor_Done'] = full_df['Status_Doctor_Done'].fillna(False).astype(bool)
    full_df['Status_Patient_Done'] = full_df['Status_Patient_Done'].fillna(False).astype(bool)

    # --- ЕТАП 2: ЗАВАНТАЖЕННЯ ТА ЗЛИТТЯ ВИПРАВЛЕНЬ (MERGE) ---
    col_chol = '[SCORE2] Рівень non-HDL холестерину (ммоль/л)'
    
    if url_corrections:
        try:
            # 1. Читаємо виправлення
            corr_df = pd.read_csv(url_corrections).fillna("")
            
            # 2. Знаходимо колонки (шукаємо "схожі" назви)
            c_pib = next((c for c in corr_df.columns if "піб" in c.lower() or "name" in c.lower()), None)
            c_dob = next((c for c in corr_df.columns if "дат" in c.lower() or "dob" in c.lower()), None)
            c_val = next((c for c in corr_df.columns if "chol" in c.lower() or "холест" in c.lower()), None)

            if c_pib and c_dob and c_val:
                # 3. Готуємо таблицю виправлень до формату основної
                corr_clean = pd.DataFrame()
                corr_clean['ПІБ'] = corr_df[c_pib].astype(str).str.strip()
                
                # Та сама МАГІЯ ДАТ: Pandas сам розбереться з 1980-01-25 vs 25.01.1980
                corr_clean['Дата народження'] = pd.to_datetime(corr_df[c_dob], dayfirst=True, errors='coerce')
                
                # Чистимо числа (заміна коми на крапку)
                corr_clean['Chol_New'] = corr_df[c_val].astype(str).str.replace(',', '.', regex=False)
                corr_clean['Chol_New'] = pd.to_numeric(corr_clean['Chol_New'], errors='coerce')
                
                # Прибираємо пусті дати/числа
                corr_clean = corr_clean.dropna(subset=['ПІБ', 'Дата народження', 'Chol_New'])
                
                # Лишаємо тільки останнє виправлення для пацієнта
                corr_clean = corr_clean.drop_duplicates(subset=['ПІБ', 'Дата народження'], keep='last')

                # 4. РОБИМО MERGE (ЛІВЕ З'ЄДНАННЯ)
                # Ми приєднуємо виправлення до основної таблиці по ПІБ і Даті
                full_df = pd.merge(full_df, corr_clean, on=['ПІБ', 'Дата народження'], how='left')
                
                # 5. ПІДМІНА ДАНИХ (COMBINE_FIRST)
                # Якщо є Chol_New -> беремо його. Якщо немає -> залишаємо старе.
                if col_chol not in full_df.columns: full_df[col_chol] = 0.0
                
                # combine_first працює навпаки: заповнює пропуски в першому аргументі другим
                # Тому ми беремо Chol_New і заповнюємо його пропуски старим значенням
                full_df[col_chol] = full_df['Chol_New'].combine_first(full_df[col_chol])
                
                # Прибираємо технічну колонку
                full_df = full_df.drop(columns=['Chol_New'])
                
                print("✅ Виправлення успішно застосовані через Merge")

        except Exception as e:
            print(f"❌ Помилка Merge виправлень: {e}")

    # --- ЕТАП 3: ФІНАЛІЗАЦІЯ ---
    
    # Перерахунок SCORE2 вже з новими даними
    # Важливо: ми запускаємо це ТУТ, а не в process_doctor_data, бо холестерин міг змінитися
    if col_chol in full_df.columns:
         try:
            full_df['Verdict_Score2'] = full_df.apply(get_score2_verdict_row, axis=1)
         except: pass

    # Статуси
    def get_row_status(row):
        if row['Status_Doctor_Done'] and row['Status_Patient_Done']: return "✅ Повний комплект"
        elif row['Status_Doctor_Done']: return "⚠️ Тільки лікар"
        elif row['Status_Patient_Done']: return "⏳ Очікує огляду"
        else: return "❓ Дані відсутні"
    
    if not full_df.empty:
        full_df['Загальний статус'] = full_df.apply(get_row_status, axis=1)

    return full_df
