import streamlit as st
import pandas as pd
import base64
import urllib.parse
from modules import pdf_gen 
from streamlit_pdf_viewer import pdf_viewer

# ==========================================
# 🛑 НАЛАШТУВАННЯ ВАШОЇ ГУГЛ ФОРМИ
# ==========================================
FORM_BASE_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfWddfzYXY0O1ftLHcfjaxMPyDAlB73JpSFtVRhL4i1C8mMwQ/viewform"

ENTRY_PIB = "entry.541684930"       # Код для поля ПІБ
ENTRY_DOB = "entry.376367893"       # Код для поля Дата народження
# Код для холестерину тут більше не потрібен, бо ми не передаємо його з програми у форму
# ==========================================

TESTS_CONFIG = [
    {"tag": "Score2",   "name": "SCORE-2 (Серцевий ризик)", "search_key": "SCORE2", "has_score": False},
    {"tag": "FINDRISK", "name": "FINDRISK (Діабет)",       "search_key": "Findrisc", "has_score": True},
    {"tag": "PHQ",      "name": "PHQ-9 (Депресія)",        "search_key": "PHQ",      "has_score": True},
    {"tag": "GAD",      "name": "GAD-7 (Тривожність)",     "search_key": "GAD",      "has_score": True},
    {"tag": "Audit",    "name": "AUDIT (Алкоголь)",        "search_key": "AUDIT",    "has_score": True},
    {"tag": "Smoke",    "name": "Нікотинова залежність",   "search_key": "Паління",  "has_score": True}
]

def show_dashboard(df):
    """Головний екран."""
    st.header("🗂 Картка пацієнта")

    search_col = 'ПІБ'
    if search_col not in df.columns:
        st.error(f"Помилка: Відсутня колонка '{search_col}'.")
        return

    patient_list = sorted(df[search_col].unique().astype(str))
    selected_patient = st.selectbox("🔍 Пошук пацієнта:", patient_list)
    record = df[df[search_col] == selected_patient].iloc[0].copy()

    st.divider()
    
    # --- ІНФО-ПАНЕЛЬ ---
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

    # --- КЕРУВАННЯ АНАЛІЗАМИ ---
    st.markdown("### 🧪 Внесення лабораторних даних")
    st.info("Всі результати аналізів тепер вносяться через окрему Google Форму. Програма автоматично зчитає їх після оновлення.")
    
    # Генеруємо посилання тільки з ПІБ та Датою
    raw_dob = record.get('Дата народження')
    try:
        if isinstance(raw_dob, pd.Timestamp): dob_for_google = raw_dob.strftime('%Y-%m-%d')
        else: dob_for_google = pd.to_datetime(str(raw_dob), dayfirst=True).strftime('%Y-%m-%d')
    except:
        dob_for_google = str(raw_dob)

    params = {
        ENTRY_PIB: record['ПІБ'],
        ENTRY_DOB: dob_for_google,
    }
    query_string = urllib.parse.urlencode(params)
    final_link = f"{FORM_BASE_URL}?{query_string}"
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        st.link_button("📝 1. Відкрити форму для вводу аналізів", final_link, type="primary", use_container_width=True)
    with col_btn2:
        if st.button("🔄 2. Оновити базу (Завантажити нові дані)", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # --- ВІДОБРАЖЕННЯ АНАЛІЗІВ ---
    st.subheader("🩸 Результати лабораторних аналізів")
    
    # Витягуємо холестерин з датафрейму (він туди потрапив завдяки data_manager)
    col_chol = '[SCORE2] Рівень non-HDL холестерину (ммоль/л)'
    current_chol = record.get(col_chol, 0)
    
    # Тут ви можете додати інші аналізи, якщо вони є в базі
    # наприклад: current_gl = record.get('Глюкоза', 0)
    
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        if current_chol and float(current_chol) > 0:
            st.metric("Холестерин (non-HDL)", f"{current_chol} ммоль/л")
        else:
            st.metric("Холестерин (non-HDL)", "Немає даних")
            
    # Додайте сюди інші метрики, коли вони з'являться у формі:
    # with col_a2: st.metric("Глікований гемоглобін", f"{current_hba1c} %")

    st.divider()

    # --- ОПИТУВАЛЬНИКИ ---
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
    
    tab1, tab2 = st.tabs(["Звіт по Аналізах (Новий)", "Звіт по Опитувальниках"])
    
    # ==========================================
    # ТАБ 1: НОВИЙ ЗВІТ ПО АНАЛІЗАХ (Як у Word)
    # ==========================================
    with tab1:
        st.write("Формує звіт у форматі медичного бланку з референтними значеннями.")
        
        try:
            # Викликаємо НОВУ функцію з pdf_gen.py
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
                pdf_viewer(input=pdf_bytes_lab, width=700, height=800)
                
        except Exception as e:
            st.error(f"⚠️ Помилка генерації PDF аналізів: {e}")

    # ==========================================
    # ТАБ 2: СТАРИЙ ЗВІТ ПО ОПИТУВАЛЬНИКАХ
    # ==========================================
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
