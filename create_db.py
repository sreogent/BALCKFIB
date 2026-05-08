import sqlite3
import os

print("Создание базы данных...")

# Проверяем, есть ли уже файл БД
if os.path.exists('admin_bot.db'):
    print("Файл admin_bot.db уже существует!")
    answer = input("Пересоздать? (да/нет): ")
    if answer.lower() != 'да':
        print("Отмена")
        exit()

# Подключаемся (файл создастся автоматически)
conn = sqlite3.connect('admin_bot.db')
cursor = conn.cursor()

print("Создание таблиц...")

# Таблица чатов
cursor.execute('''
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    chat_type TEXT DEFAULT 'players',
    welcome_text TEXT,
    welcome_enabled INTEGER DEFAULT 0,
    filter_enabled INTEGER DEFAULT 0,
    flood_enabled INTEGER DEFAULT 0,
    quiet_mode INTEGER DEFAULT 0,
    leave_kick INTEGER DEFAULT 0,
    invite_moders INTEGER DEFAULT 0,
    created_date TEXT
)
''')

# Таблица пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    chat_id INTEGER,
    nick TEXT,
    role TEXT DEFAULT 'user',
    warns INTEGER DEFAULT 0,
    muted_until TEXT,
    banned INTEGER DEFAULT 0,
    joined_date TEXT,
    last_active TEXT,
    PRIMARY KEY (user_id, chat_id)
)
''')

# Таблица истории предупреждений
cursor.execute('''
CREATE TABLE IF NOT EXISTS warn_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    chat_id INTEGER,
    admin_id INTEGER,
    reason TEXT,
    date TEXT
)
''')

# Таблица банов
cursor.execute('''
CREATE TABLE IF NOT EXISTS bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    chat_id INTEGER,
    admin_id INTEGER,
    reason TEXT,
    date TEXT,
    UNIQUE(user_id, chat_id)
)
''')

# Таблица глобальных банов
cursor.execute('''
CREATE TABLE IF NOT EXISTS global_bans (
    user_id INTEGER PRIMARY KEY,
    admin_id INTEGER,
    reason TEXT,
    date TEXT
)
''')

# Таблица фильтр-слов
cursor.execute('''
CREATE TABLE IF NOT EXISTS filter_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE
)
''')

# Таблица получателей багов
cursor.execute('''
CREATE TABLE IF NOT EXISTS bug_receivers (
    user_id INTEGER PRIMARY KEY
)
''')

# Таблица настроек
cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
''')

# Таблица ников
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_nicks (
    user_id INTEGER,
    chat_id INTEGER,
    nick TEXT,
    set_by INTEGER,
    date TEXT,
    PRIMARY KEY (user_id, chat_id)
)
''')

# Добавляем тестовые данные
print("Добавление тестовых данных...")

# Добавим пару слов в фильтр для примера
try:
    cursor.execute("INSERT INTO filter_words (word) VALUES (?)", ("мат",))
    cursor.execute("INSERT INTO filter_words (word) VALUES (?)", ("плохое_слово",))
except:
    pass

# Сохраняем изменения
conn.commit()

# Проверяем, что создалось
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("\nСозданные таблицы:")
for table in tables:
    print(f"  - {table[0]}")

# Закрываем соединение
conn.close()

print("\n✅ База данных успешно создана!")
print("Файл: admin_bot.db")
print("\nТеперь можешь запускать бота:")
print('C:\\Users\\matve\\AppData\\Local\\Programs\\Python\\Python314\\python.exe main.py')