 import streamlit as st 

 import pandas as pd 

 import base64 

 from modules import pdf_gen  # Ваш модуль генерації PDF 

 from streamlit_pdf_viewer import pdf_viewer 

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

    Додано кнопку завантаження, яка не блокується браузером.

    """

    st.subheader("📄 Друк результатів")


    # 1. Готуємо словник для друку

    final_print_dict = {}


    # 2. Проходимося по кожному налаштованому тесту

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


        result_header = f"ВИСНОВОК: {clean_verdict}"

        

        if test['has_score']:

            try:

                score_val = int(score) if pd.notna(score) else 0

                result_header += f" ({score_val} балів)"

            except:

                pass

        

        final_print_dict[f"=== {test['name']} ==="] = result_header


        test_questions = {}

        for col_name, val in record.items():

            if search_key in col_name and not any(x in col_name for x in ['Verdict_', 'Score_', 'Status_', 'Timestamp']):

                if pd.notna(val) and str(val) != "" and str(val) != "0":

                    test_questions[col_name] = str(val)

        

        final_print_dict.update(test_questions)

        final_print_dict[f"   "] = "   "


    # 3. Генеруємо PDF

    try:

        summary_text = "Деталізований звіт з результатами тестів та відповідями пацієнта."

        

        pdf_bytes = pdf_gen.create_report(

            patient_name=patient_name,

            date_str=str(pd.Timestamp.now().strftime('%d.%m.%Y')),

            verdict=summary_text, 

            score="", 

            data_dict=final_print_dict

        )


        # === ГОЛОВНА ЗМІНА: КНОПКА ЗАВАНТАЖЕННЯ ===

        # Це працює завжди, навіть якщо Chrome блокує попередній перегляд

        col_btn, col_preview = st.columns([1, 2])

        

        with col_btn:

            st.download_button(

                label="📥 Завантажити PDF-звіт",

                data=pdf_bytes,

                file_name=f"Screening_{patient_name.replace(' ', '_')}.pdf",

                mime="application/pdf",

                type="primary" # Робить кнопку виділеною

            )


        # === ПОПЕРЕДНІЙ ПЕРЕГЛЯД (В EXPANDER) ===

        # Ховаємо прев'ю в розгортайку. Це часто допомагає уникнути блокування,

        # бо контент не завантажується, поки користувач не клікне.

        with st.expander("👁️ Відкрити попередній перегляд"):

            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

            # Використовуємо <embed> замість <iframe> - це краще сприймається Chrome

            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf">'

            st.markdown(pdf_display, unsafe_allow_html=True)

        

    except Exception as e:

        st.error(f"⚠️ Помилка генерації PDF: {e}")
