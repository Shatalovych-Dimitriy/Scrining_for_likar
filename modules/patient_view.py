import streamlit as st
import pandas as pd
import base64
import urllib.parse
from modules import pdf_gen 

# ==========================================
# 🛑 НАЛАШТУВАННЯ ВАШОЇ ГУГЛ ФОРМИ
# ==========================================
FORM_BASE_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfWddfzYXY0O1ftLHcfjaxMPyDAlB73JpSFtVRhL4i1C8mMwQ/viewform"

ENTRY_PIB = "entry.541684930"       
ENTRY_DOB = "entry.376367893"       

TESTS_CONFIG = [
    {"tag": "Score2",   "name": "SCORE-2 (Серцевий ризик)", "search_key": "SCORE2", "has_score": False},
    {"tag": "FINDRISK", "name": "FINDRISK (Діабет)",       "search_key": "Findrisc", "has_score": True},
    {"tag": "PHQ",      "name": "PHQ-9 (Депресія)",        "search_key": "PHQ",      "has_score": True},
    {"tag": "GAD",      "name": "GAD-7 (Тривожність)",     "search_key": "GAD",      "has_score": True},
    {"tag": "Audit",    "name": "AUDIT (Алкоголь)",        "search_key": "AUDIT",    "has_score": True},
    {"tag": "Smoke",    "name": "Нікотинова залежність",   "search_key": "Паління",  "has_score": True}
]

# --- ЛОГІКА СВІТЛОФОРА ДЛЯ АНАЛІЗІВ ---
def get_lab_status(test_key, val_str):
    if pd.isna(val_str) or str(val_str).strip() in ["", "nan", "—", "-"]:
        return "—", "⚪"
    
    val_clean = str(val_str).replace(',', '.').strip().lower()
    
    # 1. Перетворюємо текстові "нулі" на математичний нуль
    zero_words = ["н/в", "не виявлено", "негативний", "негативно", "відсутні", "немає", "abs", "neg"]
    
    if val_clean in zero_words:
        v = 0.0
    else:
        try: 
            v = float(val_clean)
        except: 
            return str(val_str), "🟡" # Якщо ввели незрозумілий текст, підсвічуємо жовтим для уваги

    # 2. Референтні значення (min, max)
    ranges = {
        'Lab_Total_Chol': (0, 5.2), 'Lab_Non_HDL': (0, 4.89), 'Lab_LDL': (0, 2.59), 'Lab_TG': (0, 2.3),
        'Lab_WBC': (4.0, 10.0), 'Lab_LYM': (0.6, 4.1), 'Lab_MID': (0.1, 1.8), 'Lab_GRA': (2.0, 7.8),
        'Lab_LYM_perc': (20.0, 50.0), 'Lab_MID_perc': (1.0, 15.0), 'Lab_GRA_perc': (40.0, 70.0),
        'Lab_RBC': (3.8, 5.8), 'Lab_HGB': (110, 173), 'Lab_HCT': (30.0, 50.0),
        'Lab_MCV': (84, 98), 'Lab_MCH': (27.5, 32.4), 'Lab_MCHC': (317, 342),
        'Lab_PLT': (100, 300), 'Lab_PCT': (0.1, 0.5),
        'Lab_SG': (1.005, 1.025), 'Lab_pH': (5.5, 7.0), 'Lab_Protein': (0, 0.15), 'Lab_UBG': (0, 17),
        
        # ДОДАНО: Аналізи, де норма - це тільки 0 (або "не виявлено")
        'Lab_Glucose': (0, 0), 'Lab_Ketones': (0, 0), 'Lab_BIL': (0, 0), 
        'Lab_NIT': (0, 0), 'Lab_U_WBC': (0, 0), 'Lab_U_RBC': (0, 0)
    }

    # Специфічне правило для Глікованого гемоглобіну
    if test_key == 'Lab_HbA1c':
        if v <= 5.7: return str(val_str), "🟢"
        elif v <= 6.4: return str(val_str), "🟡"
        else: return str(val_str), "🔴"

    # Перевірка для інших аналізів
    if test_key in ranges:
        min_v, max_v = ranges[test_key]
        
        # Якщо вписується в норму
        if min_v <= v <= max_v: return str(val_str), "🟢"
        
        # Якщо норма - це тільки 0, то будь-яке число більше нуля - це патологія (Червоний)
        if max_v == 0:
            return str(val_str), "🔴"
        
        # Відхилення 15% - це Жовта зона (Межовий стан)
        margin = (max_v - min_v) * 0.15 if max_v != float('inf') else min_v * 0.15
        if min_v == 0: margin = max_v * 0.15
        
        if (min_v - margin) <= v <= (max_v + margin): return str(val_str), "🟡"
        
        # Все інше - Червона зона
        return str(val_str), "🔴"
        
    return str(val_str), "⚪"

def show_dashboard(df):
    st.header("🗂 Картка пацієнта")

    search_col = 'ПІБ'
    if search_col not in df.columns:
        st.error(f"Помилка: Відсутня колонка '{search_col}'.")
        return

    patient_list = sorted(df[search_col].unique().astype(str))
    selected_patient = st.selectbox("🔍 Пошук пацієнта:", patient_list)
    record = df[df[search_col] == selected_patient].iloc[0].copy()

    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.caption("Пацієнт")
        st.subheader(record['ПІБ'])
    with col2:
        st.caption("Вік / Дата")
        dob = record.get('Дата народження', '—')
        if isinstance(dob, pd.Timestamp): dob = dob.strftime('%d.%m.%Y')
        age = int(record.get('Вік', 0))
        st.subheader(f"{age} років")
        st.text(f"({dob})")
    with col3:
        st.caption("Стать")
        sex_col = next((c for c in record.index if 'стать' in c.lower()), None)
        sex = record.get(sex_col, "—") if sex_col else "—"
        st.subheader(sex)
    with col4:
        st.caption("Статус")
        status = record.get('Загальний статус', 'Невідомо')
        if "Повний" in status: st.success(status)
        elif "Тільки лікар" in status: st.warning(status)
        else: st.info(status)

    st.divider()

    st.markdown("### 🧪 Внесення лабораторних даних")
    st.info("Всі результати аналізів тепер вносяться через окрему Google Форму. Програма автоматично зчитає їх після оновлення.")
    
    raw_dob = record.get('Дата народження')
    try:
        if isinstance(raw_dob, pd.Timestamp): dob_for_google = raw_dob.strftime('%Y-%m-%d')
        else: dob_for_google = pd.to_datetime(str(raw_dob), dayfirst=True).strftime('%Y-%m-%d')
    except: dob_for_google = str(raw_dob)

    params = { ENTRY_PIB: record['ПІБ'], ENTRY_DOB: dob_for_google }
    query_string = urllib.parse.urlencode(params)
    final_link = f"{FORM_BASE_URL}?{query_string}"
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1: st.link_button("📝 1. Відкрити форму для вводу аналізів", final_link, type="primary", use_container_width=True)
    with col_btn2:
        if st.button("🔄 2. Оновити базу (Завантажити нові дані)", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # --- ВІДОБРАЖЕННЯ АНАЛІЗІВ НА ЕКРАНІ ЗІ СВІТЛОФОРОМ ---
    st.subheader("🩸 Результати лабораторних аналізів")
    
    def render_lab(title, key):
        val, emoji = get_lab_status(key, record.get(key, ""))
        st.write(f"{title}: {emoji} **{val}**")

    with st.expander("🔬 Переглянути внесені аналізи (Розгорнути)", expanded=True):
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1:
            st.markdown("**(1) Ліпіди та Цукор**")
            render_lab("Загальний хол.", "Lab_Total_Chol")
            render_lab("non-HDL (SCORE2)", "Lab_Non_HDL")
            render_lab("ЛНПЩ", "Lab_LDL")
            render_lab("Тригліцериди", "Lab_TG")
            render_lab("HbA1c", "Lab_HbA1c")
        with col_l2:
            st.markdown("**(2) Загальний крові**")
            render_lab("Гемоглобін (HGB)", "Lab_HGB")
            render_lab("Еритроцити (RBC)", "Lab_RBC")
            render_lab("Лейкоцити (WBC)", "Lab_WBC")
            render_lab("Тромбоцити (PLT)", "Lab_PLT")
            render_lab("ШОЕ / Гематокрит", "Lab_HCT")
        with col_l3:
            st.markdown("**(3) Загальний сечі**")
            render_lab("Білок", "Lab_Protein")
            render_lab("Глюкоза", "Lab_Glucose")
            render_lab("Кетони", "Lab_Ketones")
            render_lab("Лейкоцити", "Lab_U_WBC")
            render_lab("Еритроцити", "Lab_U_RBC")

    st.divider()

    st.subheader("📊 Показники здоров'я (Опитувальники)")
    cols = st.columns(3)
    for index, test in enumerate(TESTS_CONFIG):
        with cols[index % 3]:
            _draw_test_card(record, test)

    st.divider()
    _render_pdf_section(record, selected_patient)

def _draw_test_card(record, test_conf):
    tag = test_conf["tag"]
    title = test_conf["name"]
    verdict = record.get(f"Verdict_{tag}")
    score = record.get(f"Score_{tag}", 0) if test_conf["has_score"] else None

    with st.container(border=True):
        st.markdown(f"**{title}**")
        if tag == "Score2" and ("холестерин" in str(verdict).lower() or "Введіть" in str(verdict)):
             st.info(str(verdict)) 
        elif pd.isna(verdict) or verdict == 0 or verdict == "":
            st.markdown("⚪ *Не пройдено / Немає даних*")
        else:
            v_str = str(verdict)
            if any(x in v_str for x in ["Тяжк", "Клінічн", "Високий", "Залежність", "🔴"]): st.error(v_str)
            elif any(x in v_str for x in ["Помірн", "Середн", "Увага", "🟠", "🟡"]): st.warning(v_str)
            else: st.success(v_str)
            if score is not None: st.caption(f"Бали: {score}")

def _render_pdf_section(record, patient_name):
    st.subheader("📄 Друк результатів")
    tab1, tab2 = st.tabs(["Звіт по Аналізах (Новий)", "Звіт по Опитувальниках"])
    
    with tab1:
        st.write("Формує звіт у форматі медичного бланку з референтними значеннями та підсвіткою результатів.")
        try:
            pdf_bytes_lab = pdf_gen.create_lab_report(
                patient_name=patient_name,
                dob_str=str(record.get('Дата народження', '—')).split()[0],
                date_str=str(pd.Timestamp.now().strftime('%d.%m.%Y')),
                record=record
            )
            
            st.download_button(
                label="📥 Завантажити PDF Аналізів",
                data=pdf_bytes_lab,
                file_name=f"Lab_Report_{patient_name.replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            
            with st.expander("👁️ Попередній перегляд (Аналізи)"):
                base64_pdf = base64.b64encode(pdf_bytes_lab).decode('utf-8')
                pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf">'
                st.markdown(pdf_display, unsafe_allow_html=True)
                st.caption("ℹ️ Якщо документ не відображається коректно, натисніть кнопку 'Завантажити' вище.")
                
        except Exception as e:
            st.error(f"⚠️ Помилка генерації PDF аналізів: {e}")

    with tab2:
        final_print_dict = {}
        for test in TESTS_CONFIG:
            tag = test['tag']       
            search_key = test['search_key'] 
            verdict = record.get(f"Verdict_{tag}")
            score = record.get(f"Score_{tag}")
            if pd.isna(verdict) or verdict == "" or verdict == 0 or verdict == "0": continue
            v_str = str(verdict)
            clean_verdict = v_str.replace("🔴", "").replace("🟠", "").replace("🟡", "").replace("🟢", "").replace("✅", "").strip()
            if not clean_verdict:
                if "🔴" in v_str: clean_verdict = "Високий ризик / Патологія"
                elif "🟠" in v_str: clean_verdict = "Середній / Високий ризик"
                elif "🟡" in v_str: clean_verdict = "Помірний ризик / Увага"
                elif "🟢" in v_str or "✅" in v_str: clean_verdict = "Низький ризик / Норма"
                else: clean_verdict = v_str
            result_header = f"ВИСНОВОК: {clean_verdict}"
            if test['has_score']:
                try:
                    score_val = int(score) if pd.notna(score) else 0
                    result_header += f" ({score_val} балів)"
                except: pass
            final_print_dict[f"=== {test['name']} ==="] = result_header
            test_questions = {}
            for col_name, val in record.items():
                if search_key in col_name and not any(x in col_name for x in ['Verdict_', 'Score_', 'Status_', 'Timestamp']):
                    if pd.notna(val) and str(val) != "" and str(val) != "0":
                        test_questions[col_name] = str(val)
            final_print_dict.update(test_questions)
            final_print_dict[f"   "] = "   "

        try:
            summary_text = "Деталізований звіт з результатами тестів та відповідями пацієнта."
            pdf_bytes = pdf_gen.create_report(
                patient_name=patient_name,
                date_str=str(pd.Timestamp.now().strftime('%d.%m.%Y')),
                verdict=summary_text, 
                score="", 
                data_dict=final_print_dict
            )
            
            st.download_button(
                label="📥 Завантажити PDF Опитувальників",
                data=pdf_bytes,
                file_name=f"Questionnaire_{patient_name.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"⚠️ Помилка: {e}")
