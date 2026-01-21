import streamlit as st
import pandas as pd
import base64
from modules import printer_rez  # Імпорт нашого генератора PDF

def show_dashboard(df):
    """
    Головна функція відображення картки пацієнта.
    Приймає DataFrame з усіма пацієнтами.
    """
    
    st.header("🗂 Електронна карта пацієнта")

    # --- 1. ПОШУК ІДЕНТИФІКАТОРА (ПІБ або ID) ---
    # Шукаємо колонку, яка містить ім'я (перевірте точну назву у вашій таблиці!)
    possible_names = ['Name', 'ПІБ', 'Прізвище', 'Full Name', 'Username']
    search_col = None
    
    for col in possible_names:
        if col in df.columns:
            search_col = col
            break
            
    if not search_col:
        st.error(f"❌ Помилка: У таблиці не знайдено колонку з іменем. Доступні колонки: {list(df.columns)}")
        return

    # --- 2. ВИБІР ПАЦІЄНТА ---
    # Отримуємо унікальні імена і сортуємо їх
    patient_list = df[search_col].unique()
    selected_patient = st.selectbox("🔍 Оберіть пацієнта:", sorted(patient_list.astype(str)))

    # --- 3. ПІДГОТОВКА ДАНИХ ПАЦІЄНТА ---
    # Фільтруємо записи тільки цього пацієнта
    history = df[df[search_col] == selected_patient].copy()
    
    # Сортуємо за датою (свіжі зверху), якщо є колонка часу
    if 'Timestamp' in history.columns:
        history['Timestamp'] = pd.to_datetime(history['Timestamp'])
        history = history.sort_values(by='Timestamp', ascending=False)
    
    if history.empty:
        st.warning("Даних про цього пацієнта не знайдено.")
        return

    # Беремо найсвіжіший запис (останній скринінг)
    last_record = history.iloc[0]
    
    # Витягуємо ключові метрики (використовуємо .get, щоб не було помилок, якщо колонки немає)
    date_str = last_record['Timestamp'].strftime('%d.%m.%Y %H:%M') if 'Timestamp' in last_record else "—"
    verdict = last_record.get('Verdict', 'Не розраховано')
    score = last_record.get('Risk_Score', 0)

    st.divider()

    # --- 4. ГОЛОВНИЙ ЕКРАН (Розділяємо на дві колонки) ---
    # col_details - ліва частина (текст і таблиця)
    # col_pdf - права частина (документ для друку)
    col_details, col_pdf = st.columns([1, 1])

    # === ЛІВА КОЛОНКА: Деталі ===
    with col_details:
        st.subheader(f"Результат від {date_str}")
        
        # Відображаємо кольоровий вердикт
        if "Високий" in str(verdict) or (isinstance(score, (int, float)) and score > 8):
            st.error(f"### {verdict}\n**Сума балів ризику:** {score}")
        elif "Середній" in str(verdict) or (isinstance(score, (int, float)) and score > 5):
            st.warning(f"### {verdict}\n**Сума балів ризику:** {score}")
        else:
            st.success(f"### {verdict}\n**Сума балів ризику:** {score}")

        st.markdown("#### 📋 Відповіді пацієнта:")
        
        # Чистимо дані для красивої таблиці
        # Прибираємо технічні поля, щоб показати тільки питання-відповіді
        tech_cols = ['Timestamp', 'Date', 'Risk_Score', 'Verdict', 'Name', 'Test_Type', search_col]
        display_data = last_record.drop(labels=[c for c in tech_cols if c in last_record.index])
        
        # Транспонуємо (перевертаємо) для зручності читання
        details_df = display_data.dropna().to_frame(name="Відповідь")
        
        # Виводимо таблицю
        st.dataframe(details_df, use_container_width=True, height=500)

    # === ПРАВА КОЛОНКА: PDF Попередній перегляд ===
    with col_pdf:
        st.subheader("📄 Друкована форма")
        st.caption("Наведіть мишку на документ, щоб побачити кнопку друку (верхній правий кут).")

        # 1. Готуємо дані для PDF (словник без технічних колонок)
        clean_data_dict = display_data.to_dict()

        # 2. Генеруємо PDF (викликаємо ваш модуль pdf_gen)
        try:
            pdf_bytes = pdf_gen.create_report(
                patient_name=selected_patient,
                date_str=date_str,
                verdict=str(verdict),
                score=score,
                data_dict=clean_data_dict
            )

            # 3. Магія: Конвертуємо PDF у Base64 для відображення в браузері
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

            # 4. Створюємо HTML iframe (вбудоване вікно)
            # type="application/pdf" - це каже браузеру "включи свій PDF-рідер"
            pdf_display = f'''
                <iframe 
                    src="data:application/pdf;base64,{base64_pdf}" 
                    width="100%" 
                    height="700px" 
                    type="application/pdf"
                    style="border: 1px solid #ccc; border-radius: 5px;">
                </iframe>
            '''
            
            # Рендеримо HTML
            st.markdown(pdf_display, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Не вдалося згенерувати PDF. Перевірте файл шрифту (Arial.ttf). Помилка: {e}")

    # --- 5. ІСТОРІЯ (Знизу, якщо є старі записи) ---
    if len(history) > 1:
        st.divider()
        with st.expander(f"📚 Архів попередніх скринінгів ({len(history)-1})"):
            # Показуємо все, крім найпершого (поточного) запису
            st.dataframe(history.iloc[1:], use_container_width=True)
