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
        "tags": ["PHQ", "GAD","Паління","AUDIT"],
        "identity_map": {
            "Name": "ПІБ",  # Тут може бути інша назва
            "DOB": "Дата народження"
        }
    }
]
def process_doctor_data(df):
    
    """Обробка 2 тестів лікаря"""
    # Тут ваша логіка для тегів [Огляд] і [Анамнез]
    # Наприклад:
    # df['Score_Огляд'] = ...
    # df['Verdict_Огляд'] = ...
    
    # === ВАЖЛИВО: Ставимо "печатку", що лікар роботу зробив ===
    df['Status_Doctor_Done'] = True
    return df

def process_patient_data(df):
    points_map_GAD = {
        "Ніколи": 0, "Кілька днів": 1, "Понад половину часу": 2, 
        "Майже щодня": 3
    }
        points_map_PHQ = {
        "Не турбували взагалі": 0, "Протягом декількох днів": 1, "Більше половини цього часу": 2, 
        "Майже кожного дня": 3
    }
    def calculate_pyl_score(row,teg, map):
        score = 0
        for question, answer in row.items():
            # Перевіряємо, чи питання належить до Огляду
            if teg in str(question):
                # Шукаємо відповідь у нашому словнику балів
                # str(answer) потрібно, щоб не впало, якщо там число
                if str(answer) in map:
                    score += points_map[str(answer)]
        return score

    #PHQ
    df['Score_PHQ']=df.apply(
        calculate_pyl_score, 
        axis=1, 
        teg=['PHQ'],  # Передаємо значення
        map=points_map_PHQ        # Передаємо значення
        )
    # 1. Визначаємо функцію вердикту згідно з таблицею
    def get_depression_verdict(s):
        # Перевіряємо від найвищого до найнижчого
        if s >= 20: return "🔴 Тяжка депресія"
        if s >= 15: return "🟠 Середньої тяжкості депресія"
        if s >= 10: return "🟡 Помірної тяжкості депресія"
        if s >= 5:  return "🟢 Легка («субклінічна») депресія"
        return "⚪ Депресія відсутня" # 0-4 бали

    # 2. Застосовуємо її (замість лямбди)
    # Припускаємо, що колонка з балами називається 'Score_PHQ9' (або ваша назва)
    df['Verdict_PHQ'] = df['Score_PHQ'].apply(get_depression_verdict)
    
    df['Status_Patient_Done'] = True
    return df
    
def calculate_age(born):
    """Допоміжна функція розрахунку віку"""
    if pd.isnull(born):
        return 0
    today = datetime.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    
# === 3. ГОЛОВНИЙ МЕРДЖЕР (ОБ'ЄДНУВАЧ) ===
@st.cache_data(ttl=60)
def get_processed_data():
    dfs_to_merge = []

    for conf in FORMS_CONFIG:
        try:
            df = pd.read_csv(conf["url"])
            
            # Стандартизація (Ім'я, Час, Дата) - код із попередніх прикладів
            df = _standardize_columns(df, conf) 
            
            # Видаляємо дублікати (беремо найсвіжіший запис)
            if 'Timestamp' in df.columns:
                df = df.sort_values('Timestamp', ascending=False)
            df = df.drop_duplicates(subset=['Name', 'DOB'], keep='first')

            # Викликаємо відповідну обробку
            # Для цього ми використовуємо функцію calculate_multi_scores (універсальну)
            # або ваші специфічні, якщо логіка складна.
            # Для прикладу тут виклик універсальної з тегами:
            df = calculate_multi_scores(df, conf["tags"])
            
            # Додаємо статус
            if conf["id"] == "doctor_form":
                df['Status_Doctor_Done'] = True
            elif conf["id"] == "patient_form":
                df['Status_Patient_Done'] = True

            dfs_to_merge.append(df)
            
        except Exception as e:
            print(f"Помилка {conf['name']}: {e}")

    if not dfs_to_merge:
        return pd.DataFrame()

    # === ЗШИВАННЯ (OUTER JOIN) ===
    # how='outer' гарантує: якщо є тільки форма лікаря - рядок буде.
    # якщо є тільки форма пацієнта - рядок теж буде.
    # якщо є обидві - вони з'єднаються.
    try:
        full_df = reduce(
            lambda left, right: pd.merge(
                left, right, 
                on=['Name', 'DOB'], 
                how='outer', 
                suffixes=('_doc', '_pat')
            ), 
            dfs_to_merge
        )
        
        # Об'єднуємо Timestamp і Age з різних таблиць, щоб не було дірок
        # (код очистки Timestamp і Age такий самий, як я писав раніше)
        
        return full_df
    except Exception as e:
        st.error(f"Помилка злиття даних: {e}")
        return pd.DataFrame()

