import pandas as pd
import streamlit as st
from datetime import datetime

# === КОНФІГУРАЦІЯ ===
FORMS_CONFIG = [
    {
        "name": "Лікарі",
        "url": "https://docs.google.com/spreadsheets/d/1cWbKDyAJNjzTgb0ZsmBSXmp7v4TyzqjGAGs8mcc5n2M/viewform?embedded=true",
        "tags": ["Серце", "Неврологія"],
        # ДОДАЄМО МАПУ ІМЕН:
        # "стандартна_назва": "назва_у_вашій_гугл_формі"
        "identity_map": {
            "Name": "ПІБ",      # Як названо питання про ім'я
            "DOB": "Дата народження"     # Як названо питання про дату
        }
    },
    # Для другої форми так само:
    {
        "name": "Комплекс 2",
        "url": "hhttps://docs.google.com/spreadsheets/d/1xXjuhfnu0opui-XrAmfrr_-m0Qe_gHDBGiTMXEQaP4Y/viewform?embedded=true",
        "tags": ["Шлунок", "Зір"],
        "identity_map": {
            "Name": "ПІБ",  # Тут може бути інша назва
            "DOB": "Дата народження"
        }
    }
]

@st.cache_data(ttl=60)
def get_processed_data():
    all_data = []

    for form_conf in FORMS_CONFIG:
        try:
            df = pd.read_csv(form_conf["url"])
            
            # 1. Стандартизація Часу (автоматично)
            time_col = next((col for col in df.columns if 'time' in col.lower() or 'час' in col.lower()), None)
            if time_col:
                df.rename(columns={time_col: 'Timestamp'}, inplace=True)
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            
            # 2. === НОВЕ: Стандартизація Імені та Дати ===
            # Ми перейменовуємо колонки форми у стандартні 'Name' і 'DOB'
            # щоб програма завжди знала, де їх шукати
            id_map = form_conf.get("identity_map", {})
            
            # Перевертаємо мапу для rename (Гугл Назва -> Наша Назва)
            rename_dict = {v: k for k, v in id_map.items()} 
            df.rename(columns=rename_dict, inplace=True)

            # 3. Додаткова обробка (Вік)
            if 'DOB' in df.columns:
                # Конвертуємо у дату (Google Forms іноді дає різні формати)
                df['DOB'] = pd.to_datetime(df['DOB'], dayfirst=True, errors='coerce')
                # Рахуємо вік
                df['Age'] = df['DOB'].apply(calculate_age)

            df['Form_Source'] = form_conf["name"]
            
            # 4. Рахуємо бали (Тільки по тегах!)
            df = calculate_multi_scores(df, form_conf["tags"])
            
            all_data.append(df)
            
        except Exception as e:
            print(f"Помилка {form_conf['name']}: {e}")

    if all_data:
        # concat з'єднає колонки Name з різних таблиць в одну
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

def calculate_age(born):
    """Допоміжна функція розрахунку віку"""
    if pd.isnull(born):
        return 0
    today = datetime.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
