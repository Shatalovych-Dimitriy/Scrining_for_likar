import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def save_correction_safe(patient_name, dob_str, cholesterol_val):
    """
    Зберігає холестерин у окрему таблицю.
    Шукає збіг за ПІБ та Датою народження.
    """
    try:
        # Авторизація
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Відкриття таблиці виправлень
        sheet = client.open_by_url(st.secrets["links"]["corrections_url"]).sheet1
        
        records = sheet.get_all_records()
        row_number = None
        
        # Приведення до рядків та нижнього регістру для точного пошуку
        target_name = str(patient_name).strip().lower()
        target_dob = str(dob_str).strip()
        
        for i, row in enumerate(records):
            row_name = str(row.get('ПІБ', '')).strip().lower()
            row_dob = str(row.get('Дата народження', '')).strip()
            
            # Перевіряємо і Ім'я, і Дату
            if row_name == target_name and row_dob == target_dob:
                row_number = i + 2  # +2 (бо індексація з 0 + рядок заголовка)
                break
        
        if row_number:
            # Оновлюємо існуючого (Колонка 3 - це Холестерин)
            sheet.update_cell(row_number, 3, cholesterol_val)
        else:
            # Додаємо нового
            sheet.append_row([patient_name, dob_str, cholesterol_val])
            
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False
