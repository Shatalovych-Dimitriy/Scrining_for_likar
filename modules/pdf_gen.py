from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        # Простий заголовок на кожній сторінці
        try:
            self.set_font('CustomFont', 'I', 8)
            self.set_text_color(128, 128, 128) # Сірий колір
            self.cell(0, 10, 'HealthScreening System Report', 0, 1, 'R')
            self.ln(2)
        except:
            pass

    def footer(self):
        pass

def create_report(patient_name, date_str, verdict, score, data_dict):
    """
    Генерує стильний PDF з підтримкою кирилиці для опитувальників.
    """
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # === 1. НАЛАШТУВАННЯ ШРИФТУ ===
    font_path = 'Arial.ttf' 
    if not os.path.exists(font_path):
        font_path = 'DejaVuSans.ttf' # Запасний варіант

    if not os.path.exists(font_path):
        return b"ERROR: Font file (Arial.ttf) not found."

    # Реєструємо шрифти
    pdf.add_font('CustomFont', '', font_path, uni=True)
    pdf.add_font('CustomFont', 'B', font_path, uni=True)
    pdf.add_font('CustomFont', 'I', font_path, uni=True)
    
    # === 2. ШАПКА ЗВІТУ (БЛОК ПАЦІЄНТА) ===
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(10, 20, 190, 30, 'F')
    
    pdf.set_y(25)
    pdf.set_font('CustomFont', 'B', 18)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, f"Медичний звіт пацієнта", 0, 1, 'C')
    
    pdf.set_font('CustomFont', '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"ПІБ: {patient_name}  |  Дата: {date_str}", 0, 1, 'C')
    
    pdf.ln(15)

    # === 3. КОРОТКЕ РЕЗЮМЕ ===
    pdf.set_font('CustomFont', 'B', 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "Зведення результатів", 0, 1, 'L')
    
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y()) 
    pdf.ln(2)
    
    pdf.set_font('CustomFont', '', 11)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, verdict)
    pdf.ln(10)

    # === 4. ДЕТАЛІЗАЦІЯ (ТАБЛИЦЯ) ===
    fill_row = False 

    for key, value in data_dict.items():
        safe_key = str(key).strip()
        safe_val = str(value).strip()

        if safe_key.startswith("==="):
            pdf.ln(5) 
            clean_title = safe_key.replace("===", "").strip()
            
            pdf.set_fill_color(44, 62, 80)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('CustomFont', 'B', 12)
            pdf.cell(0, 10, f"  {clean_title}", 0, 1, 'L', fill=True)
            
            if safe_val:
                pdf.set_fill_color(230, 230, 230)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('CustomFont', 'B', 11)
                pdf.multi_cell(0, 8, f"  {safe_val}", fill=True)
            
            pdf.set_text_color(0, 0, 0)
            fill_row = False
            continue

        if safe_key == "   ":
            pdf.ln(2)
            continue

        if fill_row:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)

        w_question = 140
        w_answer = 50
        
        if pdf.get_y() > 270:
            pdf.add_page()
        
        pdf.set_font('CustomFont', '', 10)
        y_start = pdf.get_y()
        pdf.multi_cell(w_question, 6, f"  {safe_key}", border='L', align='L', fill=True)
        y_end_q = pdf.get_y()
        
        pdf.set_xy(10 + w_question, y_start)
        pdf.set_font('CustomFont', 'B', 10)
        h_block = y_end_q - y_start
        pdf.multi_cell(w_answer, h_block, safe_val, border='R', align='C', fill=True)
        
        pdf.set_y(y_end_q)
        pdf.set_draw_color(220, 220, 220)
        pdf.line(10, y_end_q, 200, y_end_q)
        fill_row = not fill_row

    return pdf.output(dest='S').encode('latin-1')


def create_lab_report(patient_name, dob_str, date_str, record):
    """
    Генерує PDF-звіт по лабораторних аналізах у форматі таблиці (як у Word-документі).
    """
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font_path = 'Arial.ttf' 
    if not os.path.exists(font_path): 
        font_path = 'DejaVuSans.ttf'

    pdf.add_font('CustomFont', '', font_path, uni=True)
    pdf.add_font('CustomFont', 'B', font_path, uni=True)
    pdf.add_font('CustomFont', 'I', font_path, uni=True)

    # --- ШАПКА ---
    pdf.set_font('CustomFont', 'B', 16)
    pdf.set_text_color(0, 80, 160) # Синій колір
    pdf.cell(0, 10, "Скринінг здоров’я 40+", 0, 1, 'L')
    
    pdf.set_font('CustomFont', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, f"Пацієнт: {patient_name}", 0, 1)
    pdf.cell(0, 6, f"Дата народження: {dob_str}", 0, 1)
    pdf.cell(0, 6, f"Дата проведення скринінгу: {date_str}", 0, 1)
    pdf.ln(5)

    # --- ЗАГОЛОВОК ТАБЛИЦІ ---
    pdf.set_font('CustomFont', 'B', 14)
    pdf.cell(0, 10, "Результати досліджень", 0, 1, 'C')
    
    # Шапка таблиці
    pdf.set_fill_color(220, 230, 240)
    pdf.set_font('CustomFont', 'B', 10)
    
    # Ширина колонок (разом = 190)
    w_comp = 80; w_res = 30; w_unit = 35; w_ref = 45
    
    pdf.cell(w_comp, 8, "Досліджувані компоненти", border=1, fill=True)
    pdf.cell(w_res, 8, "Результат", border=1, align='C', fill=True)
    pdf.cell(w_unit, 8, "Одиниці", border=1, align='C', fill=True)
    pdf.cell(w_ref, 8, "Референтні значення", border=1, align='C', fill=True)
    pdf.ln()

    # --- ДАНІ ТАБЛИЦІ ---
    pdf.set_font('CustomFont', '', 10)
    
    # Витягуємо дані
    col_chol = '[SCORE2] Рівень non-HDL холестерину (ммоль/л)'
    val_chol = record.get(col_chol, "")
    if pd.isna(val_chol) or val_chol == 0: 
        val_chol = "—"
    
    lab_data = [
        {"cat": "Профіль ліпідів", "items": [
            {"name": "Загальний холестерин (total-C)", "res": "—", "unit": "ммоль/л", "ref": "< 5,2"},
            {"name": "Холестерин автом. (non-HDL-C)", "res": str(val_chol), "unit": "ммоль/л", "ref": "< 4,89"},
            {"name": "ЛНПЩ (LDL-C)", "res": "—", "unit": "ммоль/л", "ref": "< 2,59"},
        ]},
        {"cat": "Глікований гемоглобін", "items": [
            {"name": "HbA1c", "res": "—", "unit": "%", "ref": "4.5 - 5.7"},
        ]}
    ]

    for category in lab_data:
        # Назва категорії (сірий фон)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font('CustomFont', 'B', 10)
        pdf.cell(190, 8, category["cat"], border=1, fill=True, ln=1)
        
        pdf.set_font('CustomFont', '', 10)
        for item in category["items"]:
            # Зберігаємо Y, щоб зробити мультисел для довгих назв
            y_before = pdf.get_y()
            
            if y_before > 260:
                pdf.add_page()
                y_before = pdf.get_y()

            pdf.multi_cell(w_comp, 8, item["name"], border=1)
            y_after = pdf.get_y()
            h_row = y_after - y_before
            
            pdf.set_xy(10 + w_comp, y_before)
            pdf.cell(w_res, h_row, item["res"], border=1, align='C')
            pdf.cell(w_unit, h_row, item["unit"], border=1, align='C')
            pdf.cell(w_ref, h_row, item["ref"], border=1, align='C')
            pdf.ln()

    # --- РЕКОМЕНДАЦІЇ ---
    pdf.add_page()
    pdf.set_font('CustomFont', 'B', 14)
    pdf.cell(0, 10, "Рекомендації", 0, 1, 'C')
    
    pdf.set_font('CustomFont', '', 10)
    recommendations_text = (
        "Що ховається за фразою «зміна способу життя»? Це комплекс заходів, "
        "що охоплює відмову від куріння, обмеження споживання алкоголю, "
        "дотримання принципів здорового харчування, регулярна фізична активність, "
        "зменшення ваги у разі її надлишку та управління стресом.\n\n"
        "Тютюнопаління: Усі види вживання тютюну є доведеним чинником серцево-судинних захворювань. "
        "Нікотин сприяє підвищенню тиску та прискоренню пульсу.\n\n"
        "Високий рівень холестерину: Якщо Вам було призначено препарати для лікування "
        "порушень ліпідного обміну (статини), обов’язково приймайте їх. Це допоможе сповільнити "
        "прогресування атеросклерозу.\n\n"
        "Вага: В ідеалі Ви маєте знати свій індекс маси тіла (норма < 25) та обвід талії "
        "(норма у жінок < 80 см, у чоловіків < 94 см).\n\n"
        "Психологічний стан: Стрес може бути пусковим механізмом підвищення АТ."
    )
    pdf.multi_cell(0, 6, recommendations_text)

    return pdf.output(dest='S').encode('latin-1')
