import streamlit as st
import uuid
import sqlite3
import hashlib
from contextlib import closing

# Настройки базы данных
DATABASE = 'todo_app.db'

# Цвета для тегов
TAG_COLORS = {
    'работа': '#4A90E2',
    'учеба': '#50E3C2',
    'личное': '#BD10E0',
    'важно': '#FF0000',
    'другое': '#F8E71C'
}

DEFAULT_TAGS = list(TAG_COLORS.keys())


def create_tables():
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                tags TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()


create_tables()


def register_user(username, password):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        try:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                           (username, hashed_password))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def verify_user(username, password):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute('SELECT id FROM users WHERE username=? AND password=?',
                       (username, hashed_password))
        return cursor.fetchone()


def get_tasks(user_id):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tasks WHERE user_id=?', (user_id,))
        return [{
            'id': row[0],
            'title': row[2],
            'description': row[3],
            'status': row[4],
            'tags': row[5].split(',') if row[5] else []
        } for row in cursor.fetchall()]


def add_task(user_id, task_data):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (id, user_id, title, description, status, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            task_data['id'],
            user_id,
            task_data['title'],
            task_data['description'],
            task_data['status'],
            ','.join(task_data['tags'])
        ))
        conn.commit()

def auth_form():
    login_tab, register_tab = st.tabs(["Вход", "Регистрация"])

    with login_tab:
        with st.form("Вход"):
            username = st.text_input("Имя пользователя")
            password = st.text_input("Пароль", type="password")
            if st.form_submit_button("Войти"):
                user = verify_user(username, password)
                if user:
                    st.session_state.user = {'id': user[0], 'username': username}
                    st.rerun()
                else:
                    st.error("Неверные учетные данные")

    with register_tab:
        with st.form("Регистрация"):
            new_username = st.text_input("Новое имя пользователя")
            new_password = st.text_input("Новый пароль", type="password")
            confirm_password = st.text_input("Подтвердите пароль", type="password")
            if st.form_submit_button("Зарегистрироваться"):
                if new_password != confirm_password:
                    st.error("Пароли не совпадают")
                elif register_user(new_username, new_password):
                    st.success("Регистрация успешна! Теперь войдите")
                else:
                    st.error("Имя пользователя уже занято")

def update_task_status(task_id, new_status):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE tasks SET status=? WHERE id=?', (new_status, task_id))
        conn.commit()


def delete_task(task_id):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id=?', (task_id,))
        conn.commit()


def tag_element(tag):
    color = TAG_COLORS.get(tag, '#CCCCCC')
    return f'<span style="background-color: {color}; color: black; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">{tag}</span>'


def task_card(task):
    with st.container(border=True):
        st.markdown(f"**{task['title']}**", unsafe_allow_html=True)

        if task['description']:
            st.markdown(f"<div style='margin: 4px 0;'>{task['description']}</div>", unsafe_allow_html=True)

        if task['tags']:
            tags_html = " ".join([tag_element(tag) for tag in task['tags']])
            st.markdown(f"<div style='margin: 8px 0;'>{tags_html}</div>", unsafe_allow_html=True)

        # Компактные кнопки
        cols = st.columns([1, 1, 1, 0.5])
        with cols[0]:
            if task['status'] != 'todo':
                if st.button("◀️", help="Вернуть в 'Сделать'", key=f"todo_{task['id']}"):
                    update_task_status(task['id'], 'todo')
                    st.rerun()
        with cols[1]:
            if task['status'] != 'in_progress':
                if st.button("⏳", help="В работу", key=f"progress_{task['id']}"):
                    update_task_status(task['id'], 'in_progress')
                    st.rerun()
        with cols[2]:
            if task['status'] != 'done':
                if st.button("✅", help="Завершить", key=f"done_{task['id']}"):
                    update_task_status(task['id'], 'done')
                    st.rerun()
        with cols[3]:
            if st.button("🗑️", help="Удалить", key=f"delete_{task['id']}"):
                delete_task(task['id'])
                st.rerun()


def main_app():
    st.title("🚀 Персональный менеджер заметок")

    with st.expander("➕ Добавить новую задачу", expanded=True):
        with st.form("new_task_form"):
            title = st.text_input("Заголовок*", placeholder="Введите заголовок...")
            description = st.text_area("Описание", placeholder="Детали задачи...")
            tags = st.multiselect(
                "Теги",
                options=DEFAULT_TAGS,
                format_func=lambda x: x.capitalize(),
                placeholder="Выберите теги..."
            )

            submitted = st.form_submit_button("Добавить задачу")
            if submitted:
                if not title:
                    st.error("Заголовок обязателен!")
                else:
                    task_id = str(uuid.uuid4())
                    new_task = {
                        'id': task_id,
                        'title': title,
                        'description': description,
                        'status': 'todo',
                        'tags': tags
                    }
                    add_task(st.session_state.user['id'], new_task)
                    st.success("Задача добавлена!")

    st.subheader("Ваши задачи")
    todo_col, progress_col, done_col = st.columns(3)

    all_tasks = get_tasks(st.session_state.user['id'])

    with todo_col:
        st.markdown("### 📥 Сделать")
        for task in [t for t in all_tasks if t['status'] == 'todo']:
            task_card(task)

    with progress_col:
        st.markdown("### ⏳ В работе")
        for task in [t for t in all_tasks if t['status'] == 'in_progress']:
            task_card(task)

    with done_col:
        st.markdown("### ✅ Выполнено")
        for task in [t for t in all_tasks if t['status'] == 'done']:
            task_card(task)

    st.divider()
    st.caption(f"Всего задач: {len(all_tasks)} | "
               f"Сделать: {len([t for t in all_tasks if t['status'] == 'todo'])} | "
               f"В работе: {len([t for t in all_tasks if t['status'] == 'in_progress'])} | "
               f"Выполнено: {len([t for t in all_tasks if t['status'] == 'done'])}")

    if st.button("Выйти из аккаунта", type="primary"):
        del st.session_state.user
        st.rerun()


if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user:
    main_app()
else:
    st.markdown("## Авторизируйтесь пожалуйста!")
    auth_form()
