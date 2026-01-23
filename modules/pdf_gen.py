from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        # Можна додати логотип або назву клініки
        try:
            # Спробуємо встановити шрифт для шапки (якщо він вже зареєстрований)
            self.set_font('CustomFont', 'B', 10)
            self.cell(0, 10, 'HealthScreening System Report', 0, 1, 'R')
            self.ln(5)
        except:
            pass

    def footer(self):
        self.set_y(-15)
        try:
            self.set_font('CustomFont', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
        except:
            pass

def create_report(patient_name, date_str, verdict, score, data_dict):
    """
    Генерує PDF з підтримкою кирилиці.
    Важливо: файл шрифту (напр. Arial.ttf) має бути в корені проекту.
    """
    pdf = PDF()
    pdf.add_page()

    # === 1. РЕЄСТРАЦІЯ ШРИФТУ (КРИТИЧНО ВАЖЛИВО) ===
    # Вибираємо шрифт. Краще покласти 'Arial.ttf' або 'DejaVuSans.ttf' у папку проекту
    font_path = 'Arial.ttf' 
    
    # Якщо Arial немає, спробуємо DejaVu (часто є на Linux серверах)
    if not os.path.exists(font_path):
        font_path = 'DejaVuSans.ttf'

    if not os.path.exists(font_path):
        # Якщо шрифту немає взагалі - повертаємо помилку, бо кирилиця не спрацює
        return b"ERROR: Font file (Arial.ttf) not found. Please upload it to the project folder."

    # uni=True вмикає підтримку Unicode (української мови)
    pdf.add_font('CustomFont', '', font_path, uni=True)
    pdf.add_font('CustomFont', 'B', font_path, uni=True) # Реєструємо жирний (хоча це той самий файл, FPDF зробить емуляцію)
    
    # === 2. ЗАГОЛОВОК ===
    pdf.set_font('CustomFont', 'B', 16)
    pdf.cell(0, 10, f"Результати скринінгу: {patient_name}", 0, 1, 'C')
    
    pdf.set_font('CustomFont', '', 10)
    pdf.cell(0, 10, f"Дата формування: {date_str}", 0, 1, 'C')
    pdf.ln(5)

    # === 3. КОРОТКЕ РЕЗЮМЕ (ВЕРДИКТИ) ===
    pdf.set_fill_color(240, 240, 240) # Сірий фон
    pdf.set_font('CustomFont', 'B', 12)
    pdf.cell(0, 10, "Загальні висновки", 0, 1, 'L', fill=True)
    
    pdf.set_font('CustomFont', '', 11)
    # verdict - це багаторядковий текст, який ми сформували в patient_view
    pdf.multi_cell(0, 7, verdict)
    pdf.ln(5)

    # === 4. ДЕТАЛЬНА ТАБЛИЦЯ (ПИТАННЯ-ВІДПОВІДІ) ===
    pdf.set_font('CustomFont', 'B', 12)
    pdf.cell(0, 10, "Деталі анкетування", 0, 1, 'L', fill=True)
    pdf.ln(2)

    pdf.set_font('CustomFont', '', 10)

    # Проходимо по словнику даних
    for key, value in data_dict.items():
        # Очистка тексту від зайвих символів, які можуть зламати PDF
        safe_key = str(key).strip()
        safe_val = str(value).strip()

        # Якщо це заголовок секції (починається з ===)
        if safe_key.startswith("==="):
            pdf.ln(3)
            pdf.set_font('CustomFont', 'B', 11) # Жирний для заголовка тесту
            # Заголовок секції малюємо на всю ширину
            # Використовуємо multi_cell, щоб не вилізло за межі
            pdf.multi_cell(0, 8, f"{safe_key}  {safe_val}", border='B')
            pdf.set_font('CustomFont', '', 10) # Повертаємо звичайний шрифт
        
        # Якщо це звичайне питання
        else:
            if safe_key == "   ": # Пустий розділювач
                pdf.ln(2)
                continue
                
            # Малюємо питання (зліва) і відповідь (справа)
            # Розрахунок висоти рядка, щоб текст не накладався
            
            # Ширина для питання (65%) і відповіді (35%)
            w_question = 130
            w_answer = 60
            
            # Зберігаємо поточну позицію
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            
            # Друкуємо питання (MultiCell дозволяє перенос слів)
            pdf.multi_cell(w_question, 6, safe_key, border='B')
            
            # Визначаємо, де закінчилося питання
            y_end = pdf.get_y()
            height = y_end - y_start
            
            # Переміщуємося вправо для друку відповіді
            pdf.set_xy(x_start + w_question, y_start)
            
            # Друкуємо відповідь (жирнішим, щоб виділялася)
            pdf.set_font('CustomFont', 'B', 10)
            
            # Відповідь теж може бути довгою, тому MultiCell
            # Але нам треба, щоб висота комірки відповіді співпадала з висотою питання
            # Хоча FPDF 1.7 це складно робить, тому просто друкуємо
            pdf.multi_cell(w_answer, 6, safe_val, border='B')
            
            # Повертаємо курсор на початок наступного рядка (під найнижчу комірку)
            y_final = pdf.get_y()
            if y_final < y_end: # Якщо питання зайняло більше місця, ніж відповідь
                pdf.set_y(y_end)
            
            pdf.set_font('CustomFont', '', 10) # Скидаємо жирність

    # Повертаємо байти PDF файлу
    return pdf.output(dest='S').encode('latin-1') # Trick: FPDF output returns latin-1 string representing bytes, we encode it back to bytes
