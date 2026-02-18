import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from functools import reduce

# Налаштування Pandas
pd.set_option('future.no_silent_downcasting', True)

# ==========================================
# 1. КОНФІГУРАЦІЯ
# ==========================================
try:
    url_doctor = st.secrets["links"]["doktor_link"]
    url_patient = st.secrets["links"]["patient_link"]
    url_corrections = st.secrets["links"]["hol_table_link"]
except:
    url_doctor = ""
    url_patient = ""
    url_corrections = ""

FORMS_CONFIG = [
    { "id": "doctor_form", "name": "Лікар", "url": url_doctor, "identity_map": {"Name": "ПІБ", "DOB": "Дата народження"} },
    { "id": "patient_form", "name": "Пацієнт", "url": url_patient, "identity_map": {"Name": "ПІБ", "DOB": "Дата народження"} }
]

# Словники балів (Вставте сюди ваші повні словники)
POINTS_MAP_PHQ = {"Не турбували взагалі": 0, "Протягом декількох днів": 1, "Більше половини цього часу": 2, "Майже кожного дня": 3}
# ... інші словники ...

# ==========================================
# 2. ДОПОМІЖНІ ФУНКЦІЇ
# ==========================================

def calculate_age(born):
    if pd.isnull(born): return 0
    today = datetime.today()
    try:
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except: return 0

def get_score2_verdict_row(row):
    # ВАША ФУНКЦІЯ SCORE2
    age = row.get('Вік', 0)
    chol = row.get('[SCORE2] Рівень non-HDL холестерину (ммоль/л)', 0)
    if age == 0: return "⚪ Недостатньо даних"
    if chol <= 0: return "⚪ Введіть холестерин"
    # ... тут ваша логіка ...
    return "✅ Розраховано" 

# ==========================================
# 3. ОБРОБНИКИ (PROCESSORS)
# ==========================================
def process_doctor_data(df):
    # Тут ваш код обробки лікаря (FINDRISC і т.д.)
    df['Status_Doctor_Done'] = True
    return df

def process_patient_data(df):
    # Тут ваш код обробки пацієнта (PHQ-9 і т.д.)
    df['Status_Patient_Done'] = True
    return df

# ==========================================
# 4. ГОЛОВНА ЛОГІКА (PURE PANDAS) 🐼
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
    if col_chol in full_df.columns:
         # Захист від помилок у вашій функції вердикту
         try:
            full_df['Verdict_Score2'] = full_df.apply(get_score2_verdict_row, axis=1)
         except: pass

    # Статуси
    full_df['Status_Doctor_Done'] = full_df['Status_Doctor_Done'].fillna(False)
    full_df['Status_Patient_Done'] = full_df['Status_Patient_Done'].fillna(False)
    
    def get_row_status(row):
        if row['Status_Doctor_Done'] and row['Status_Patient_Done']: return "✅ Повний комплект"
        elif row['Status_Doctor_Done']: return "⚠️ Тільки лікар"
        elif row['Status_Patient_Done']: return "⏳ Очікує огляду"
        else: return "❓ Дані відсутні"
    
    if not full_df.empty:
        full_df['Загальний статус'] = full_df.apply(get_row_status, axis=1)

    return full_df
