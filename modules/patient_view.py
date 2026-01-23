import streamlit as st
import pandas as pd
import base64
from modules import pdf_gen  # Ваш модуль генерації PDF

# === КОНФІГУРАЦІЯ ВІДОБРАЖЕННЯ ===
TESTS_CONFIG = [
    {"tag": "Score2",   "name": "🫀 SCORE-2 (Серцевий ризик)", "has_score": False},
    {"tag": "FINDRISK", "name": "🍬 FINDRISK (Діабет)",       "has_score": True},
    {"tag": "PHQ",      "name": "😞 PHQ-9 (Депресія)",        "has_score": True},
    {"tag": "GAD",      "name": "😰 GAD-7 (Тривожність)",     "has_score": True},
    {"tag": "Audit",    "name": "🍷 AUDIT (Алкоголь)",        "has_score": True},
    {"tag": "Smoke",    "name": "🚬 Нікотинова залежність",   "has_score": True}
]

def show_dashboard(df):
    """Головний екран картки пацієнта."""
    st.header("🗂 Результати скринінгу")

    # --- 1. ПОШУК ПАЦІЄНТА ---
    search_col = 'ПІБ'
    if search_col not in df.columns:
        st.error(f"Помилка: Відсутня колонка '{search_col}'.")
        return

    patient_list = sorted(df[search_col].unique().astype(str))
    selected_patient = st.selectbox("🔍 Пошук пацієнта:", patient_list)
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

    # --- 3. СІТКА РЕЗУЛЬТАТІВ ---
    st.subheader("📊 Показники здоров'я (Вердикти)")
    cols = st.columns(3)
    for index, test in enumerate(TESTS_CONFIG):
        with cols[index % 3]:
            _draw_test_card(record, test)

    st.divider()

    # --- 4. ПДФ ТА ДРУК ---
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
    """
    Блок генерації PDF.
    Фільтрує дані так, щоб у таблицю потрапили лише ПОЧАТКОВІ питання та відповіді.
    """
    st.subheader("📄 Друк результатів")

    # 1. Формуємо "шапку" з вердиктами (коротке резюме)
    summary_text = "ВИСНОВКИ СИСТЕМИ:\n"
    for test in TESTS_CONFIG:
        v = record.get(f"Verdict_{test['tag']}")
        if pd.notna(v) and v != 0 and v != "":
            # Чистимо смайлики для PDF
            clean_v = str(v).replace("🔴", "").replace("🟠", "").replace("🟡", "").replace("🟢", "").replace("✅", "").strip()
            summary_text += f"- {test['name']}: {clean_v}\n"

    # 2. === ГОЛОВНА ЗМІНА: Фільтруємо "сирі" дані для таблиці ===
    # Ми хочемо бачити питання (наприклад "[PHQ] Як часто...") і відповідь ("Кілька днів")
    
    raw_data_dict = {}
    
    # Список слів-маркерів, які ми НЕ хочемо бачити у друці (технічні поля)
    system_markers = [
        'Score_', 'Verdict_', 'Status_', 'Загальний статус', 
        'Позначка часу', 'Timestamp', 'Form_Source', 
        'Вік_doc', 'Вік_pat'
    ]
    # Поля, які вже є в шапці, тому дублювати їх не треба
    header_fields = ['ПІБ', 'Name', 'Дата народження', 'DOB', 'Вік']

    for col_name, value in record.items():
        # 1. Пропускаємо системні розрахунки (Score_PHQ, Verdict_GAD...)
        if any(marker in col_name for marker in system_markers):
            continue
            
        # 2. Пропускаємо поля шапки (Ім'я, Вік)
        if col_name in header_fields:
            continue
            
        # 3. Пропускаємо пусті значення (щоб не засмічувати звіт)
        if pd.isna(value) or value == "" or value == 0 or value == "0":
            continue

        # Якщо пройшли всі перевірки — це оригінальне питання!
        # Конвертуємо значення в рядок для краси
        raw_data_dict[col_name] = str(value)

    # 3. Генеруємо PDF
    try:
        pdf_bytes = pdf_gen.create_report(
            patient_name=patient_name,
            date_str=str(pd.Timestamp.now().strftime('%d.%m.%Y')),
            verdict=summary_text, 
            score="", 
            data_dict=raw_data_dict  # <--- Передаємо відфільтровані сирі дані
        )

        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        
    except Exception as e:
        st.warning("⚠️ Попередній перегляд недоступний (перевірте шрифт Arial.ttf).")
        # Для налагодження покажемо, що ми намагалися надрукувати
        with st.expander("Переглянути дані, що йдуть на друк"):
            st.write(raw_data_dict)
