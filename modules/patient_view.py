import streamlit as st
import pandas as pd
import base64
from modules import pdf_gen  # Ваш модуль генерації PDF

# === КОНФІГУРАЦІЯ ВІДОБРАЖЕННЯ ===
# tag: частина назви колонки після "Verdict_" або "Score_"
# name: Заголовок картки
# has_score: Чи є у цього тесту числові бали (SCORE2 не має Score_Score2, тільки Verdict)
TESTS_CONFIG = [
    {"tag": "Score2",   "name": "🫀 SCORE-2 (Серцевий ризик)", "has_score": False},
    {"tag": "FINDRISK", "name": "🍬 FINDRISK (Діабет)",       "has_score": True},
    {"tag": "PHQ",      "name": "😞 PHQ-9 (Депресія)",        "has_score": True},
    {"tag": "GAD",      "name": "😰 GAD-7 (Тривожність)",     "has_score": True},
    {"tag": "Audit",    "name": "🍷 AUDIT (Алкоголь)",        "has_score": True},
    {"tag": "Smoke",    "name": "🚬 Нікотинова залежність",   "has_score": True}
]

def show_dashboard(df):
    """
    Головний екран картки пацієнта.
    """
    st.header("🗂 Результати скринінгу")

    # --- 1. ПОШУК ПАЦІЄНТА (По ПІБ, а не Name) ---
    search_col = 'ПІБ'
    
    if search_col not in df.columns:
        st.error(f"Помилка: Відсутня колонка '{search_col}'. Перевірте data_manager.")
        return

    # Сортуємо список пацієнтів
    patient_list = sorted(df[search_col].unique().astype(str))
    selected_patient = st.selectbox("🔍 Пошук пацієнта:", patient_list)

    # Отримуємо запис пацієнта
    record = df[df[search_col] == selected_patient].iloc[0]

    # --- 2. ІНФО-ПАНЕЛЬ ---
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.caption("Пацієнт")
        st.subheader(record['ПІБ'])
    
    with col2:
        st.caption("Вік / Дата народження")
        dob = record.get('Дата народження', '—')
        if isinstance(dob, pd.Timestamp): 
            dob = dob.strftime('%d.%m.%Y')
        
        age = int(record.get('Вік', 0))
        st.subheader(f"{age} років")
        st.text(f"({dob})")

    with col3:
        st.caption("Стать")
        # Шукаємо колонку статі (вона може бути з різних форм, тому шукаємо схожу)
        sex_col = next((c for c in record.index if 'стать' in c.lower()), None)
        sex = record.get(sex_col, "Не вказано") if sex_col else "—"
        st.subheader(sex)

    with col4:
        st.caption("Статус заповнення")
        status = record.get('Загальний статус', 'Невідомо')
        
        if "Повний" in status:
            st.success(status)
        elif "Тільки лікар" in status:
            st.warning(status)
        elif "Очікує" in status:
            st.info(status)
        else:
            st.error(status)

    st.divider()

    # --- 3. СІТКА РЕЗУЛЬТАТІВ (GRID LAYOUT) ---
    st.subheader("📊 Показники здоров'я")
    
    cols = st.columns(3) # 3 колонки для карток

    for index, test in enumerate(TESTS_CONFIG):
        current_col = cols[index % 3]
        with current_col:
            _draw_test_card(record, test)

    st.divider()

    # --- 4. ПДФ ТА ДРУК ---
    _render_pdf_section(record, selected_patient)


def _draw_test_card(record, test_conf):
    """Малює одну картку тесту."""
    tag = test_conf["tag"]
    title = test_conf["name"]
    has_score = test_conf["has_score"]

    # Формуємо назви колонок, які згенерував data_manager
    verdict_col = f"Verdict_{tag}"
    score_col = f"Score_{tag}"

    verdict = record.get(verdict_col)
    
    # Отримуємо бали тільки якщо вони передбачені тестом
    score = record.get(score_col, 0) if has_score else None

    # Контейнер картки
    with st.container(border=True):
        st.markdown(f"**{title}**")
        
        # Перевірка на пустоту (NaN або пустий рядок)
        if pd.isna(verdict) or verdict == "" or verdict is None or verdict == 0:
            st.markdown("⚪ *Не пройдено*")
        else:
            verdict_str = str(verdict)
            
            # --- Логіка кольорів ---
            # Червоний (тригери небезпеки)
            if any(x in verdict_str for x in ["Тяжк", "Клінічн", "Високий", "Залежність", "🔴"]):
                st.error(f"{verdict_str}")
            # Помаранчевий/Жовтий (тригери уваги)
            elif any(x in verdict_str for x in ["Помірн", "Середн", "Увага", "🟠", "🟡"]):
                st.warning(f"{verdict_str}")
            # Зелений (все ок)
            else:
                st.success(f"{verdict_str}")
            
            # Виводимо бали, якщо вони є
            if has_score:
                st.caption(f"Бали: {score}")


def _render_pdf_section(record, patient_name):
    """Блок генерації PDF"""
    st.subheader("📄 Друк результатів")
    
    # 1. Формуємо текстове резюме для шапки
    summary_text = ""
    for test in TESTS_CONFIG:
        v = record.get(f"Verdict_{test['tag']}")
        if pd.notna(v) and v != 0:
            # Очищаємо смайлики для PDF (бо можуть не відобразитись)
            clean_v = str(v).replace("🔴", "").replace("🟠", "").replace("🟡", "").replace("🟢", "").replace("✅", "").strip()
            summary_text += f"• {test['name']}: {clean_v}\n"

    # 2. Очищаємо дані для детальної таблиці (прибираємо технічні поля)
    # Прибираємо всі колонки, які ми створили програмно (Score_, Verdict_, Status_...)
    tech_keywords = ['Score_', 'Verdict_', 'Status_', 'Загальний статус', 'Вік']
    tech_cols = [c for c in record.index if any(x in c for x in tech_keywords)]
    
    # Також можна прибрати ідентифікатори, бо вони вже в шапці
    tech_cols.extend(['ПІБ', 'Дата народження', 'Позначка часу_doc', 'Позначка часу_pat'])
    
    print_data = record.drop(labels=tech_cols, errors='ignore').dropna()

    try:
        # Викликаємо генератор (переконайтесь, що pdf_gen.py існує)
        pdf_bytes = pdf_gen.create_report(
            patient_name=patient_name,
            date_str=str(pd.Timestamp.now().strftime('%d.%m.%Y')),
            verdict=summary_text, 
            score="", # Загальний бал не потрібен, бо у нас резюме
            data_dict=print_data.to_dict()
        )

        # Відображення
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        
    except Exception as e:
        st.warning("⚠️ Попередній перегляд PDF недоступний (перевірте наявність шрифтів).")
        with st.expander("Показати сирі дані для друку"):
            st.dataframe(print_data)
