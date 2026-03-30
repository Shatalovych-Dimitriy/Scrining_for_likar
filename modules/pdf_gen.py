from fpdf import FPDF
import os
import pandas as pd
import textwrap
class PDF(FPDF):
    def header(self):
        try:
            self.set_font('CustomFont', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, 'HealthScreening System Report', 0, 1, 'R')
            self.ln(2)
        except: pass

    def footer(self):
        pass

def create_report(patient_name, date_str, verdict, score, data_dict):
    """Генерує PDF для опитувальників."""
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font_path = 'Arial.ttf' 
    if not os.path.exists(font_path): font_path = 'DejaVuSans.ttf'
    if not os.path.exists(font_path): return b"ERROR: Font file not found."

    pdf.add_font('CustomFont', '', font_path, uni=True)
    pdf.add_font('CustomFont', 'B', font_path, uni=True)
    pdf.add_font('CustomFont', 'I', font_path, uni=True)
    
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

        if fill_row: pdf.set_fill_color(245, 245, 245)
        else: pdf.set_fill_color(255, 255, 255)

        w_question = 140
        w_answer = 50
        
        if pdf.get_y() > 270: pdf.add_page()
        
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
    """Генерує PDF-звіт по лабораторних аналізах з кольоровою розміткою."""
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font_path = 'Arial.ttf' 
    if not os.path.exists(font_path): font_path = 'DejaVuSans.ttf'

    pdf.add_font('CustomFont', '', font_path, uni=True)
    pdf.add_font('CustomFont', 'B', font_path, uni=True)
    pdf.add_font('CustomFont', 'I', font_path, uni=True)

    # --- ШАПКА ---
    pdf.set_font('CustomFont', 'B', 16)
    pdf.set_text_color(0, 80, 160)
    pdf.cell(0, 10, "Скринінг здоров’я 40+", 0, 1, 'L')
    
    pdf.set_font('CustomFont', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, f"Пацієнт: {patient_name}", 0, 1)
    pdf.cell(0, 6, f"Дата народження: {dob_str}", 0, 1)
    pdf.cell(0, 6, f"Дата проведення скринінгу: {date_str}", 0, 1)
    pdf.ln(5)

    pdf.set_font('CustomFont', 'B', 14)
    pdf.cell(0, 10, "Результати досліджень", 0, 1, 'C')
    
    pdf.set_fill_color(220, 230, 240)
    pdf.set_font('CustomFont', 'B', 10)
    w_comp = 80; w_res = 30; w_unit = 35; w_ref = 45
    
    pdf.cell(w_comp, 8, "Досліджувані компоненти", border=1, fill=True)
    pdf.cell(w_res, 8, "Результат", border=1, align='C', fill=True)
    pdf.cell(w_unit, 8, "Одиниці", border=1, align='C', fill=True)
    pdf.cell(w_ref, 8, "Референтні значення", border=1, align='C', fill=True)
    pdf.ln()

    # --- ФУНКЦІЯ ОЦІНКИ ДЛЯ PDF ---
# --- ФУНКЦІЯ ОЦІНКИ ДЛЯ PDF ---
    def get_color_rgb(test_key, val_str):
        if pd.isna(val_str) or str(val_str).strip() in ["", "nan", "—", "-"]: return (0, 0, 0)
        
        val_clean = str(val_str).replace(',', '.').strip().lower()
        
        # Перетворюємо текстові "нулі" на математичний нуль
        zero_words = ["н/в", "не виявлено", "негативний", "негативно", "відсутні", "немає", "abs", "neg"]
        
        if val_clean in zero_words:
            v = 0.0
        else:
            try: 
                v = float(val_clean)
            except: 
                return (200, 150, 0) # Жовтий для незрозумілого тексту
        
        ranges = {
            'Lab_Total_Chol': (0, 5.2), 'Lab_Non_HDL': (0, 4.89), 'Lab_LDL': (0, 2.59), 'Lab_TG': (0, 2.3),
            'Lab_WBC': (4.0, 10.0), 'Lab_LYM': (0.6, 4.1), 'Lab_MID': (0.1, 1.8), 'Lab_GRA': (2.0, 7.8),
            'Lab_LYM_perc': (20.0, 50.0), 'Lab_MID_perc': (1.0, 15.0), 'Lab_GRA_perc': (40.0, 70.0),
            'Lab_RBC': (3.8, 5.8), 'Lab_HGB': (110, 173), 'Lab_HCT': (30.0, 50.0),
            'Lab_MCV': (84, 98), 'Lab_MCH': (27.5, 32.4), 'Lab_MCHC': (317, 342),
            'Lab_PLT': (100, 300), 'Lab_PCT': (0.1, 0.5),
            'Lab_SG': (1.005, 1.025), 'Lab_pH': (5.5, 7.0), 'Lab_Protein': (0, 0.15), 'Lab_UBG': (0, 17),
            
            # ДОДАНО: Аналізи, де норма - це тільки 0
            'Lab_Glucose': (0, 0), 'Lab_Ketones': (0, 0), 'Lab_BIL': (0, 0), 
            'Lab_NIT': (0, 0), 'Lab_U_WBC': (0, 0), 'Lab_U_RBC': (0, 0)
        }
        
        c_green, c_yellow, c_red = (0, 128, 0), (200, 150, 0), (200, 0, 0)

        if test_key == 'Lab_HbA1c':
            if v <= 5.7: return c_green
            elif v <= 6.4: return c_yellow
            else: return c_red
            
        if test_key in ranges:
            min_v, max_v = ranges[test_key]
            
            if min_v <= v <= max_v: return c_green
            
            # Якщо норма = 0, будь-яке відхилення - патологія
            if max_v == 0: return c_red
            
            margin = (max_v - min_v) * 0.15 if max_v != float('inf') else min_v * 0.15
            if min_v == 0: margin = max_v * 0.15
            
            if (min_v - margin) <= v <= (max_v + margin): return c_yellow
            return c_red
            
        return (0, 0, 0)

    def get_val(key):
        val = record.get(key, "")
        if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "nan": return "—"
        return str(val)

    # --- СТРУКТУРА АНАЛІЗІВ ЯК У ДОКУМЕНТІ ---
    lab_data = [
        {"cat": "Профіль ліпідів", "items": [
            {"key": "Lab_Total_Chol", "name": "Загальний холестерин (total-C)", "unit": "ммоль/л", "ref": "< 5,2"},
            {"key": "Lab_Non_HDL", "name": "Холестерин автом. (non-HDL-C)", "unit": "ммоль/л", "ref": "< 4,89"},
            {"key": "Lab_LDL", "name": "ЛНПЩ (LDL-C)", "unit": "ммоль/л", "ref": "< 2,59"},
            {"key": "Lab_TG", "name": "Тригліцериди (TG)", "unit": "ммоль/л", "ref": "< 2,3"}
        ]},
        {"cat": "Глікований гемоглобін", "items": [
            {"key": "Lab_HbA1c", "name": "HbA1c", "unit": "%", "ref": "4.5 - 5.7"}
        ]},
        {"cat": "Загальний аналіз крові", "items": [
            {"key": "Lab_WBC", "name": "Лейкоцити (WBC)", "unit": "×10⁹/л", "ref": "4,00-10,0"},
            {"key": "Lab_LYM", "name": "Лімфоцити (LYM)", "unit": "×10⁹/л", "ref": "0,6-4,1"},
            {"key": "Lab_MID", "name": "Моноцити, еозинофіли, базофіли", "unit": "×10⁹/л", "ref": "0,1-1,8"},
            {"key": "Lab_GRA", "name": "Гранулоцити (GRA)", "unit": "×10⁹/л", "ref": "2,0-7,8"},
            {"key": "Lab_LYM_perc", "name": "LYM%", "unit": "%", "ref": "20,0-50,0"},
            {"key": "Lab_MID_perc", "name": "MID%", "unit": "%", "ref": "1,0-15,0"},
            {"key": "Lab_GRA_perc", "name": "GRA%", "unit": "%", "ref": "40,0-70,0"},
            {"key": "Lab_RBC", "name": "Еритроцити (RBC)", "unit": "×10¹²/л", "ref": "3,8-5,8"},
            {"key": "Lab_HGB", "name": "Гемоглобін (HGB)", "unit": "г/л", "ref": "110-173"},
            {"key": "Lab_HCT", "name": "Гематокрит (HCT)", "unit": "%", "ref": "30,0-50,0"},
            {"key": "Lab_MCV", "name": "MCV", "unit": "fl", "ref": "84-98"},
            {"key": "Lab_MCH", "name": "MCH", "unit": "pg", "ref": "27,5-32,4"},
            {"key": "Lab_MCHC", "name": "MCHC", "unit": "г/л", "ref": "317-342"},
            {"key": "Lab_PLT", "name": "Тромбоцити (PLT)", "unit": "×10⁹/л", "ref": "100-300"},
            {"key": "Lab_PCT", "name": "Тромбокрит (PCT)", "unit": "%", "ref": "0,1-0,5"}
        ]},
        {"cat": "Загальний аналіз сечі", "items": [
            {"key": "Lab_SG", "name": "Питома вага", "unit": "-", "ref": "1.005 - 1.025"},
            {"key": "Lab_pH", "name": "pH", "unit": "-", "ref": "5.5 - 7.0"},
            {"key": "Lab_Protein", "name": "Білок", "unit": "г/л", "ref": "< 0.15"},
            {"key": "Lab_Glucose", "name": "Глюкоза", "unit": "ммоль/л", "ref": "не виявлено"},
            {"key": "Lab_Ketones", "name": "Кетонові тіла", "unit": "ммоль/л", "ref": "не виявлено"},
            {"key": "Lab_BIL", "name": "Білірубін (BIL)", "unit": "мкмоль/л", "ref": "не виявлено"},
            {"key": "Lab_UBG", "name": "Уробіліноген (UBG)", "unit": "мкмоль/л", "ref": "0 - 17"},
            {"key": "Lab_NIT", "name": "Нітрити (NIT)", "unit": "-", "ref": "негативний"},
            {"key": "Lab_U_WBC", "name": "Лейкоцити (сеча)", "unit": "лейко/мкл", "ref": "не виявлено"},
            {"key": "Lab_U_RBC", "name": "Еритроцити (сеча)", "unit": "еритр/мкл", "ref": "не виявлено"}
        ]}
    ]

    for category in lab_data:
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font('CustomFont', 'B', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(190, 8, category["cat"], border=1, fill=True, ln=1)
        
        pdf.set_font('CustomFont', '', 10)
        for item in category["items"]:
            y_before = pdf.get_y()
            if y_before > 260:
                pdf.add_page()
                y_before = pdf.get_y()

            res_val = get_val(item["key"])
            rgb_color = get_color_rgb(item["key"], res_val)

            pdf.multi_cell(w_comp, 8, item["name"], border=1)
            y_after = pdf.get_y()
            h_row = y_after - y_before
            
            pdf.set_xy(10 + w_comp, y_before)
            
            # Друкуємо результат з кольором СВІТЛОФОРА
            pdf.set_font('CustomFont', 'B', 10)
            pdf.set_text_color(*rgb_color)
            pdf.cell(w_res, h_row, res_val, border=1, align='C')
            
            # Повертаємо чорний для одиниць та норми
            pdf.set_font('CustomFont', '', 10)
            pdf.set_text_color(0, 0, 0)
            
            pdf.cell(w_unit, h_row, item["unit"], border=1, align='C')
            pdf.cell(w_ref, h_row, item["ref"], border=1, align='C')
            pdf.ln()

    # --- РЕКОМЕНДАЦІЇ ---
    pdf.add_page()
    pdf.set_font('CustomFont', 'B', 14)
    pdf.cell(0, 10, "Рекомендації", 0, 1, 'C')
    
    pdf.set_font('CustomFont', '', 10)
    recommendations_text = textwrap.dedent("""
        Що ховається за фразою «зміна способу життя»? Це комплекс заходів, що охоплює відмову від куріння, обмеження споживання алкоголю, дотримання принципів здорового харчування, регулярна фізична активність, зменшення ваги у разі її надлишку та управління стресом. 
Тютюнопаління
Усі види вживання тютюну, перш за все куріння, є доведеним чинником не лише раку легень, а й серцево-судинних захворювань. Нікотин сприяє підвищенню тиску та прискоренню пульсу; інші сполуки, що потрапляють в організм при курінні, шкодять судинам, створюють умови для утворення та швидкого росту атеросклеротичних бляшок. Ішемічна хвороба серця в 4 рази частіше виникає у курців в порівнянні з тими, хто не палить. 
Високий рівень холестерину
Ще одним чинником виникнення та прогресування атеросклерозу, який призводить до розвитку інфаркту та інсульту, є високий рівень холестерину. Обов’язково ознайомтеся з рекомендаціями щодо здорового харчування задля зниження рівня  холестерину в крові. Якщо Вам було призначено препарати для лікування порушень ліпідного обміну, так звані статини, обов’язково приймайте їх. Це допоможе сповільнити прогресування атеросклерозу та запобігти розвитку інфаркту, інсульту, захворюванню артерій ніг.
Вага
Неодмінно слідкуйте за вагою. Надлишкова вага та ожиріння – це медична, а не естетична проблема. Вподобання щодо зовнішності можуть бути різними, а от наслідки для здоров’я зазвичай негативні. В ідеалі Ви маєте знати свій індекс маси тіла (норма < 25 кг/м2, надлишкова вага 25 – 29 кг/м2, ожиріння діагностують від 30 кг/м2) та обвід талії (норма у жінок < 80 см, у чоловіків < 94 см). Якщо Ваші показники вищі за нормативні, використовуйте поради лікаря для зниження ваги.
Фізична активність
Регулярна фізична активність сприяє зниженню АТ, зменшенню маси тіла, тренує серцево-судинну систему та м’язи, знімає стрес та психоемоційне напруження, покращує Ваш сон та самопочуття. Мета, до якої необхідно прагнути – 30-45 хвилин ходьби щодня або хоча б 5 разів на тиждень. Фізичні вправи з обтяженням (гирі, штанга, тренажери) можуть підвищувати АТ.
Здорове харчування
Базові принципи здорового харчування можна схематично представити у вигляді «Тарілки здорового харчування». Саме таке співвідношення продуктів є оптимальним з точки зору загального здоров’я та здоров’я серця та судин.
Психологічний стан 
Стрес чинить вкрай несприятливий вплив на стан здоров’я та серцево-судинні захворювання зокрема. Він може бути пусковим механізмом підвищення АТ і розвитку артеріальної гіпертензії. Доведено, що деякі психологічні практики на кшталт медитації, заняття йогою допомагають знизите емоційне напруження та знизити тиск. Якщо відчуваєте неспроможність впоратися з емоціями самотужки, відмічаєте порушення сну звертайтесь до лікаря для вчасної діагностики та лікування порушень
ментального здоров’я. 
        """).strip()

    pdf.multi_cell(0, 6, recommendations_text)

    return pdf.output(dest='S').encode('latin-1')
