from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        # Логотип або назва клініки
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Медичний Портал: Результати Скринінгу', 0, 1, 'C')
        self.ln(10)

def create_report(patient_name, date_str, verdict, score, data_dict):
    # Створюємо PDF об'єкт
    pdf = PDF()
    pdf.add_page()
    
    # --- ВАЖЛИВО: Підключення кириличного шрифту ---
    # Переконайтеся, що файл 'Arial.ttf' лежить поруч зі скриптом!
    # Якщо його немає, код впаде з помилкою.
    try:
        pdf.add_font('Arial', '', 'Arial.ttf', uni=True)
        pdf.add_font('Arial', 'B', 'Arial.ttf', uni=True)
        pdf.set_font('Arial', '', 12)
    except:
        # План Б, якщо шрифту немає (будуть кракозябри, але код не впаде)
        print("⚠️ УВАГА: Файл шрифту Arial.ttf не знайдено!")
        pdf.set_font('Helvetica', '', 12)

    # 1. Інформація про пацієнта
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Пацієнт: {patient_name}", 0, 1)
    pdf.cell(0, 10, f"Дата обстеження: {date_str}", 0, 1)
    pdf.ln(5)

    # 2. Вердикт (Результат)
    pdf.set_font('Arial', 'B', 14)
    # Змінюємо колір тексту залежно від результату (просто для краси, ч/б принтер надрукує сірим)
    if "Високий" in verdict:
        pdf.set_text_color(200, 0, 0) # Червоний
    else:
        pdf.set_text_color(0, 100, 0) # Зелений
        
    pdf.cell(0, 10, f"Висновок: {verdict} ({score} балів)", 0, 1)
    pdf.set_text_color(0, 0, 0) # Повертаємо чорний колір
    pdf.ln(10)

    # 3. Таблиця відповідей
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Детальні відповіді:", 0, 1)
    
    pdf.set_font('Arial', '', 10)
    
    # Проходимося по всіх питаннях
    for question, answer in data_dict.items():
        # question - це питання, answer - відповідь
        # Використовуємо multi_cell, щоб довгий текст переносився на новий рядок
        pdf.set_font('Arial', 'B', 10)
        pdf.multi_cell(0, 6, f"Питання: {str(question)}")
        
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 6, f"Відповідь: {str(answer)}")
        pdf.ln(2) # Відступ між питаннями

    # Повертаємо готовий файл як байти (рядок)
    return pdf.output(dest='S').encode('latin-1') 
    # encode('latin-1') потрібен для fpdf версії 1.7.x, якщо у вас fpdf2 - це може бути не треба
