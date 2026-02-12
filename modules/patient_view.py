import streamlit as st
import pandas as pd
import base64
import urllib.parse
from modules import pdf_gen 

# ==========================================
# 🛑 НАЛАШТУВАННЯ ВАШОЇ ГУГЛ ФОРМИ
# ==========================================
FORM_BASE_URL = "https://docs.google.com/forms/d/e/ВАШ_ДОВГИЙ_ID/viewform"

ENTRY_PIB = "entry.123456789"       # Код ПІБ
ENTRY_DOB = "entry.987654321"       # Код Дати
ENTRY_CHOL = "entry.555555555"      # Код Холестерину
# ==========================================


TESTS_CONFIG = [
    {"tag": "Score2",   "name": "SCORE-2 (Серцевий ризик)", "search_key": "SCORE2", "has_score": False},
    {"tag": "FINDRISK", "name": "FINDRISK (Діабет)",       "search_key": "Findrisc", "has_score": True},
    {"tag": "PHQ",      "name": "PHQ-9 (Депресія)",        "search_key": "PHQ",      "has_score": True},
    {"tag": "GAD",      "name": "GAD-7 (Тривожність)",     "search_key": "GAD",      "has_score": True},
    {"tag": "Audit",    "name": "AUDIT (Алкоголь)",        "search_key": "AUDIT",    "has_score": True},
    {"tag": "Smoke",    "name": "Нікотинова залежність",   "search_key": "Паління",  "has_score": True}
]

def recalculate_score2_local(record, new_cholesterol):
    """Локальний перерахунок SCORE-2."""
    sex = record.get('Вкажіть стать', 'Не вказано')
    smoke = record.get('[SCORE2] Куріння тютюнових виробів', 'Ні')
    age = int(record.get('Вік', 0))
    sbp = float(record.get('[SCORE2] Систолічний артеріальний тиск', 0))
    chol = float(new_cholesterol)

    if age == 0: return "⚪ Недостатньо даних (Вік)"
    if chol <= 0: return "⚪ Введіть холестерин"

    def is_green():
        if sex == 'жінка' and smoke == 'Ні':
            if age < 45 and sbp < 120 and chol <= 5: return True
            if 49 < age < 55 and sbp < 120 and chol <= 3: return True
        return False

    def is_yellow():
        if sbp >= 180 or chol >= 8: return False
        if sex == 'жінка':
            if smoke == 'Ні':
                if age < 50: return True 
                if 50 <= age < 55: return not (sbp >= 160 or (sbp >= 140 and chol >= 6))
                if 55 <= age < 60: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 60 <= age < 70: return not (sbp >= 140 or chol >= 6)
                if 70 <= age < 90: return not (sbp >= 160 or chol >= 7)
            else: 
                if age < 50: return not (sbp >= 160 or (sbp >= 140 and chol >= 6))
                if 50 <= age < 55: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 55 <= age < 70: return not (sbp >= 140 or (sbp >= 120 and chol >= 5))
                if 70 <= age < 90: return not (sbp >= 140 or chol >= 6)
        elif sex == 'чоловік':
            if smoke == 'Ні':
                if age < 50: return not (sbp >= 160 or (sbp >= 140 and chol >= 6))
                if 50 <= age < 55: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 55 <= age < 70: return not (sbp >= 140 or chol >= 6)
                if 70 <= age < 90: return not (sbp >= 140 or chol >= 6)
            else:
                if age < 50: return not (sbp >= 160 or (sbp >= 140 and chol >= 5))
                if 50 <= age < 55: return not (sbp >= 140 or chol >= 6)
                if 55 <= age < 70: return not (sbp >= 120 or chol >= 4)
                if 70 <= age < 90: return not (sbp >= 120 or chol >= 5)
        return False

    if is_green(): return "🟢 Низький ризик"
    elif is_yellow(): return "🟡 Помірний ризик"
    else: return "🔴 Високий ризик"


def show_dashboard(df):
    """Головний екран."""
    st.header("🗂 Результати скринінгу")

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

    # === БЛОК ВВОДУ ===
    st.markdown("### 🧪 Введення аналізів")
    
    col_chol = '[SCORE2] Рівень non-HDL холестерину (ммоль/л)'
    current_val = float(record.get(col_chol, 0))

    col_in, col_action = st.columns([1, 2])
    
    with col_in:
        st.metric("Поточне значення в базі:", value=current_val)
        new_val_local = st.number_input("Нове значення:", min_value=0.0, step=0.1, key="input_chol")

    with col_action:
        st.write("")
        
        # === ПІДГОТОВКА ДАНИХ ДЛЯ URL (ВИПРАВЛЕННЯ ПОМИЛОК) ===
        
        # 1. ВИПРАВЛЕННЯ ДАТИ: Google вимагає YYYY-MM-DD
        raw_dob = record.get('Дата народження')
        try:
            # Якщо це вже Timestamp, конвертуємо в ISO
            if isinstance(raw_dob, pd.Timestamp):
                dob_for_google = raw_dob.strftime('%Y-%m-%d')
            else:
                # Якщо це рядок, пробуємо розпізнати і перевернути
                dob_for_google = pd.to_datetime(str(raw_dob), dayfirst=True).strftime('%Y-%m-%d')
        except:
            dob_for_google = str(raw_dob) # Якщо не вийшло, віддаємо як є

        # 2. ВИПРАВЛЕННЯ ХОЛЕСТЕРИНУ: Замінюємо крапку на кому
        if new_val_local > 0:
            chol_for_google = str(new_val_local).replace('.', ',')
        else:
            chol_for_google = ""

        # Формуємо параметри
        params = {
            ENTRY_PIB: record['ПІБ'],
            ENTRY_DOB: dob_for_google,
            ENTRY_CHOL: chol_for_google
        }
        
        query_string = urllib.parse.urlencode(params)
        final_link = f"{FORM_BASE_URL}?{query_string}"
        
        st.info("Натисніть кнопку, щоб відкрити Форму. Потім натисніть 'Оновити'.")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.link_button("📝 1. Відкрити Форму", final_link, type="primary")
        with col_btn2:
            if st.button("🔄 2. Оновити дані"):
                st.cache_data.clear()
                st.rerun()

    if new_val_local > 0:
        record[col_chol] = new_val_local
        record['Verdict_Score2'] = recalculate_score2_local(record, new_val_local)

    st.divider()

    st.subheader("📊 Показники здоров'я (Вердикти)")
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
            if any(x in v_str for x in ["Тяжк", "Клінічн", "Високий", "Залежність", "🔴"]):
                st.error(v_str)
            elif any(x in v_str for x in ["Помірн", "Середн", "Увага", "🟠", "🟡"]):
                st.warning(v_str)
            else:
                st.success(v_str)
            if score is not None:
                st.caption(f"Бали: {score}")


def _render_pdf_section(record, patient_name):
    st.subheader("📄 Друк результатів")
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
        st.success("✅ Звіт сформовано!")
        st.download_button(
            label="📥 Завантажити PDF-звіт",
            data=pdf_bytes,
            file_name=f"Report_{patient_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        with st.expander("👁️ Показати попередній перегляд на екрані"):
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf">'
            st.markdown(pdf_display, unsafe_allow_html=True)
            st.caption("ℹ️ Якщо документ не відображається коректно, натисніть кнопку 'Завантажити' вище.")
    except Exception as e:
        st.error(f"⚠️ Помилка генерації PDF: {e}")
