import sqlite3

# Твой ID ВКонтакте (ЗАМЕНИ НА СВОЙ!)
YOUR_ID = 631833072  # 👈 ВСТАВЬ СВОЙ ID!

print(f"Назначаем пользователя {YOUR_ID} администратором...")

# Подключаемся к БД
conn = sqlite3.connect('admin_bot.db')
cursor = conn.cursor()

# Назначаем глобальным администратором (во всех чатах)
cursor.execute('''
    INSERT OR REPLACE INTO users (user_id, chat_id, role, joined_date)
    VALUES (?, -1, ?, datetime('now'))
''', (YOUR_ID, 'glav'))

conn.commit()

# Проверяем
cursor.execute('SELECT * FROM users WHERE user_id = ? AND chat_id = -1', (YOUR_ID,))
user = cursor.fetchone()
if user:
    print(f"✅ Ты назначен руководителем бота!")
    print(f"   Роль: {user[3]}")
else:
    print("❌ Что-то пошло не так")

conn.close()