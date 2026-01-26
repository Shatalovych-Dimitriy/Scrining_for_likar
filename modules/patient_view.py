import streamlit as st
import pandas as pd
import base64
from modules import pdf_gen  

# === КОНФІГУРАЦІЯ ===
TESTS_CONFIG = [
    {"tag": "Score2",   "name": "SCORE-2 (Серцевий ризик)", "search_key": "SCORE2", "has_score": False},
    {"tag": "FINDRISK", "name": "FINDRISK (Діабет)",       "search_key": "Findrisc", "has_score": True},
    {"tag": "PHQ",      "name": "PHQ-9 (Депресія)",        "search_key": "PHQ",      "has_score": True},
    {"tag": "GAD",      "name": "GAD-7 (Тривожність)",     "search_key": "GAD",      "has_score": True},
    {"tag": "Audit",    "name": "AUDIT (Алкоголь)",        "search_key": "AUDIT",    "has_score": True},
    {"tag": "Smoke",    "name": "Нікотинова залежність",   "search_key": "Паління",  "has_score": True}
]

def show_dashboard(df):
    """Головний екран картки пацієнта."""
    st.header("🗂 Результати скринінгу")

    search_col = 'ПІБ'
    if search_col not in df.columns:
        st.error(f"Помилка: Відсутня колонка '{search_col}'.")
        return

    patient_list = sorted(df[search_col].unique().astype(str))
    selected_patient = st.selectbox("🔍 Пошук пацієнта:", patient_list)
    record = df[df[search_col] == selected_patient].iloc[0]

    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.caption("Пацієнт")
        st.subheader(record['ПІБ'])
    
    with col2:
        st.caption("Вік / Дата народження")
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
        elif "Очікує" in status: st.info(status)
        else: st.error(status)

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
        if pd.isna(verdict) or verdict == 0 or verdict == "":
            st.markdown("⚪ *Не пройдено*")
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
    """Блок генерації PDF."""
    st.subheader("📄 Друк результатів")

    final_print_dict = {}

    for test in TESTS_CONFIG:
        tag = test['tag']       
        search_key = test['search_key'] 
        
        verdict = record.get(f"Verdict_{tag}")
        score = record.get(f"Score_{tag}")
        
        if pd.isna(verdict) or verdict == "" or verdict == 0 or verdict == "0":
            continue

        v_str = str(verdict)
        clean_verdict = v_str.replace("🔴", "").replace("🟠", "").replace("🟡", "").replace("🟢", "").replace("✅", "").strip()
        
        if not clean_verdict:
            if "🔴" in v_str: clean_verdict = "Високий ризик / Патологія"
            elif "🟠" in v_str: clean_verdict = "Середній / Високий ризик"
            elif "🟡" in v_str: clean_verdict = "Помірний ризик / Увага"
            elif "🟢" in v_str or "✅" in v_str: clean_verdict = "Низький ризик / Норма"
            else: clean_verdict = v_str

        result_header = f"ВИСНОВОК: {clean_verdict
