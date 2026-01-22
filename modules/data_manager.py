import pandas as pd
import streamlit as st
from datetime import datetime

# === КОНФІГУРАЦІЯ ===
FORMS_CONFIG = [
    {   "id": "doctor_form",
        "name": "Лікар",
        "url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4Fkc0NoXeUR3pPuJXfJvf48jIrLPYeFiQyF7kWAT4W5ilsPddahcVjYpg15N-uJqbKzrps5nUPUiQ/pub?gid=584209057&single=true&output=csv",
        "tags": ["Findrisc", "SCORE2"],
        # ДОДАЄМО МАПУ ІМЕН:
        # "стандартна_назва": "назва_у_вашій_гугл_формі"
        "identity_map": {
            "Name": "ПІБ",      # Як названо питання про ім'я
            "DOB": "Дата народження"     # Як названо питання про дату
        }
    },
    # Для другої форми так само:
    {   "id": "patient_form",
        "name": "Пацієнт",
        "url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSF_ZRq1NV9VwXR8PA9YPVCqIJ1MRwoZnA2Ec0Sz4CMMhU98dZIZU4BtIo4pH6oM7J4-E_VasWzCEqM/pub?gid=330455959&single=true&output=csv",
        "tags": ["SCORE2", "Зір"],
        "identity_map": {
            "Name": "ПІБ",  # Тут може бути інша назва
            "DOB": "Дата народження"
        }
    }
]
FORMS_CONFIG = [
    {
        "id": "doctor_form",
        "name": "Частина 1: Огляд лікаря",
        "url":"https://docs.google.com/spreadsheets/d/1cWbKDyAJNjzTgb0ZsmBSXmp7v4TyzqjGAGs8mcc5n2M/viewform?embedded=true",
        # 2 Тести лікаря (наприклад, Фізикальний огляд + Анамнез)
        "tags": ["Огляд", "Анамнез"], 
        "identity_map": {"Name": "ПІБ пацієнта", "DOB": "Дата народження"}
    },
    {
        "id": "patient_form",
        "name": "Частина 2: Опитувальник пацієнта",
        "url": "ПОСИЛАННЯ_НА_ФОРМУ_ПАЦІЄНТА_CSV",
        # 4 Тести пацієнта
        "tags": ["Спосіб_життя", "Скарги", "Психологія", "Спадковість"],
        "identity_map": {"Name": "Ваше Прізвище та Ім'я", "DOB": "Ваша дата народження"}
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
