import streamlit as st
import pandas as pd

# 1. Посилання на CSV файл з логінами (Вкладка Users)
USERS_URL = st.secrets["links"]["autorize_likar"]


def login_system():
    # --- КРОК 1: Перевірка "Кишені" (Чи ми вже увійшли?) ---
    if st.session_state.get("logged_in") == True:
        return True # Пропускаємо користувача далі

    # --- КРОК 2: Малюємо форму входу ---
    st.header("🔐 Вхід у Скринінг 40+ результати")
    
    with st.form("login_form"):
        username_input = st.text_input("Логін")
        password_input = st.text_input("Пароль", type="password")
        submit_button = st.form_submit_button("Увійти")

    # --- КРОК 3: Обробка натискання кнопки ---
    if submit_button:
        try:
            # А. Скачуємо актуальний список лікарів прямо зараз
            # dtype=str важливий, щоб пароль "0000" не став числом 0
            users_df = pd.read_csv(USERS_URL, dtype=str)
            
            # Б. Шукаємо збіг
            user_match = users_df[
                (users_df['Username'] == username_input) & 
                (users_df['Password'] == password_input)
            ]

            # В. Перевіряємо результат
            if not user_match.empty:
                # Ура! Знайшли.
                user_info = user_match.iloc[0] # Беремо перший знайдений рядок
                
                # Записуємо в "кишеню" (Session State)
                st.session_state['logged_in'] = True
                st.session_state['user_name'] = user_info['Name'] # Запам'ятовуємо ім'я
                st.session_state['role'] = user_info['Role']      # Запам'ятовуємо роль
                
                st.success("Вхід успішний!")
                st.rerun() # Перезавантажуємо сторінку, щоб прибрати форму входу
            else:
                st.error("❌ Невірний логін або пароль")
                
        except Exception as e:
            st.error(f"Помилка з'єднання з базою користувачів: {e}")

    return False # Якщо ми тут - значить вхід ще не виконано


