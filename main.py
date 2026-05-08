import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
import sqlite3
import time
from datetime import datetime, timedelta
import re
import threading

# ============= КОНФИГУРАЦИЯ =============
TOKEN = 'vk1.a.6TizPN4pg1-Fhk95_LrCbP9i3LqBnP_J5D-Y8Us4JN-1J2NIwReHNbyTscHIRlDoTluqgMsZRrHbQvXyJqizcZGoZ-bOzUiAk8v9UMfqVesLgBo-gKM4CCHhfZcZ5AGx4kQ-gubA_Fo2ViRP6o2PK3FHZph2cefAn-4IOydOluHpvYWmqw-KKMnwDa4QYYhB7AC_TJunZ_oApcoXbexZdg'
GROUP_ID = 229320501
OWNER_ID = 631833072

# Подключение к БД
conn = sqlite3.connect('admin_bot.db', check_same_thread=False)
cursor = conn.cursor()

# ============= СОЗДАНИЕ ТАБЛИЦ =============
cursor.execute('''
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    chat_type TEXT DEFAULT 'players',
    welcome_text TEXT,
    welcome_enabled INTEGER DEFAULT 0,
    filter_enabled INTEGER DEFAULT 0,
    flood_enabled INTEGER DEFAULT 0,
    quiet_mode INTEGER DEFAULT 0,
    bot_activated INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    chat_id INTEGER,
    role TEXT DEFAULT 'user',
    warns INTEGER DEFAULT 0,
    muted_until TEXT,
    banned INTEGER DEFAULT 0,
    joined_date TEXT,
    last_active TEXT,
    PRIMARY KEY (user_id, chat_id)
)
''')

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

cursor.execute('''
CREATE TABLE IF NOT EXISTS filter_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE
)
''')

conn.commit()

# Добавляем слова в фильтр
default_words = ['сука', 'блядь', 'хуй', 'пизда', 'ебать', 'жопа', 'пидор', 'мудак', 'уебан', 'долбоеб']
for word in default_words:
    cursor.execute("INSERT OR IGNORE INTO filter_words (word) VALUES (?)", (word,))
conn.commit()

print("✅ База данных готова")

# Авторизация VK
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =============

def send_msg(peer_id, message, keyboard=None):
    """Отправка сообщения"""
    try:
        params = {
            'peer_id': peer_id,
            'message': message,
            'random_id': get_random_id()
        }
        if keyboard:
            params['keyboard'] = keyboard.get_keyboard()
        vk.method('messages.send', params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_user_name(user_id):
    """Получить имя пользователя"""
    try:
        user = vk.method('users.get', {'user_ids': user_id})
        return f"{user[0]['first_name']} {user[0]['last_name']}"
    except:
        return f"id{user_id}"

def get_chat_users(chat_id):
    """Получить список участников чата"""
    try:
        chat = vk.method('messages.getConversationMembers', {'peer_id': 2000000000 + chat_id})
        return [user['member_id'] for user in chat['items'] if user['member_id'] > 0]
    except:
        return []

def get_user_role(user_id, chat_id):
    """Получить роль пользователя"""
    cursor.execute('SELECT role FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    result = cursor.fetchone()
    return result[0] if result else 'user'

def check_permission(user_id, chat_id, required_role):
    """Проверка прав"""
    if user_id == OWNER_ID:
        return True
    role = get_user_role(user_id, chat_id)
    roles_order = {'user': 0, 'moderator': 1, 'admin': 2, 'owner': 3, 'zamglav': 4, 'glav': 5}
    return roles_order.get(role, 0) >= roles_order.get(required_role, 0)

def is_global_admin(user_id):
    """Проверка глобального админа"""
    if user_id == OWNER_ID:
        return True
    cursor.execute('SELECT role FROM users WHERE user_id = ? AND chat_id = -1', (user_id,))
    result = cursor.fetchone()
    return result and result[0] in ['zamglav', 'glav']

def check_mute(user_id, chat_id):
    """Проверка мута"""
    cursor.execute('SELECT muted_until FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    result = cursor.fetchone()
    if result and result[0]:
        try:
            muted_until = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
            if muted_until > datetime.now():
                return True
            else:
                cursor.execute('UPDATE users SET muted_until = NULL WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
                conn.commit()
        except:
            pass
    return False

def check_ban(user_id, chat_id):
    """Проверка бана"""
    cursor.execute('SELECT banned FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    result = cursor.fetchone()
    return result and result[0] == 1

def check_activation(chat_id):
    """Проверка активации бота"""
    cursor.execute('SELECT bot_activated FROM chats WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    return result and result[0] == 1

def register_chat(chat_id):
    """Регистрация чата"""
    cursor.execute('INSERT OR IGNORE INTO chats (chat_id, bot_activated) VALUES (?, 0)', (chat_id,))
    conn.commit()

def register_user(user_id, chat_id):
    """Регистрация пользователя"""
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, chat_id, joined_date, last_active) 
        VALUES (?, ?, ?, ?)
    ''', (user_id, chat_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

# ============= КЛАВИАТУРЫ =============

def get_main_keyboard(role='user'):
    """Главное меню"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('📊 Статистика', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('ℹ️ Информация', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('👥 Администрация', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('📜 Правила', color=VkKeyboardColor.SECONDARY)
    
    if role in ['moderator', 'admin', 'owner', 'zamglav', 'glav']:
        keyboard.add_line()
        keyboard.add_button('🛡 Модерация', color=VkKeyboardColor.NEGATIVE)
        keyboard.add_button('⚙️ Настройки', color=VkKeyboardColor.PRIMARY)
    
    if role in ['admin', 'owner', 'zamglav', 'glav']:
        keyboard.add_line()
        keyboard.add_button('👑 Админ-панель', color=VkKeyboardColor.NEGATIVE)
    
    return keyboard

def get_moderation_keyboard():
    """Меню модерации"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('🔇 Мут', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button('🔊 Размут', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('⚠️ Варн', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button('✅ Снять варн', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('👢 Кик', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button('🚫 Бан', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('📋 Список варнов', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('🔇 Список мутов', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('🔙 Назад', color=VkKeyboardColor.SECONDARY)
    return keyboard

def get_admin_keyboard():
    """Админ-панель"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('➕ Выдать модера', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('➖ Забрать роль', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('📝 Фильтр мата', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('🔇 Режим тишины', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('🔙 Назад', color=VkKeyboardColor.SECONDARY)
    return keyboard

# ============= ОСНОВНЫЕ ФУНКЦИИ =============

def kick_user(chat_id, user_id, reason="Не указана", admin_id=None):
    """Исключить пользователя из беседы"""
    try:
        vk.method('messages.removeChatUser', {
            'chat_id': chat_id,
            'user_id': user_id
        })
        if admin_id:
            send_msg(2000000000 + chat_id, f"👢 Пользователь {get_user_name(user_id)} исключён.\nПричина: {reason}")
        return True
    except Exception as e:
        print(f"Ошибка кика: {e}")
        return False

def ban_user(chat_id, user_id, admin_id, reason="Не указана"):
    """Забанить пользователя"""
    try:
        # Добавляем в БД банов
        cursor.execute('''
            INSERT OR REPLACE INTO bans (user_id, chat_id, admin_id, reason, date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, chat_id, admin_id, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Обновляем статус бана в таблице users
        cursor.execute('''
            UPDATE users SET banned = 1 WHERE user_id = ? AND chat_id = ?
        ''', (user_id, chat_id))
        conn.commit()
        
        # Кикаем пользователя
        kick_user(chat_id, user_id, reason, admin_id)
        return True
    except Exception as e:
        print(f"Ошибка бана: {e}")
        return False

def unban_user(chat_id, user_id):
    """Разбанить пользователя"""
    cursor.execute('DELETE FROM bans WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    cursor.execute('UPDATE users SET banned = 0 WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    conn.commit()
    send_msg(2000000000 + chat_id, f"✅ Пользователь {get_user_name(user_id)} разбанен")

def mute_user(chat_id, user_id, minutes, admin_id, reason="Не указана"):
    """Замутить пользователя"""
    muted_until = datetime.now() + timedelta(minutes=minutes)
    cursor.execute('''
        UPDATE users SET muted_until = ? WHERE user_id = ? AND chat_id = ?
    ''', (muted_until.strftime('%Y-%m-%d %H:%M:%S'), user_id, chat_id))
    conn.commit()
    send_msg(2000000000 + chat_id, f"🔇 {get_user_name(user_id)} замучен на {minutes} мин.\nПричина: {reason}")

def unmute_user(chat_id, user_id):
    """Размутить пользователя"""
    cursor.execute('UPDATE users SET muted_until = NULL WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    conn.commit()
    send_msg(2000000000 + chat_id, f"🔊 {get_user_name(user_id)} размучен")

def warn_user(chat_id, user_id, admin_id, reason="Не указана"):
    """Выдать предупреждение"""
    cursor.execute('SELECT warns FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    result = cursor.fetchone()
    warns = result[0] if result else 0
    new_warns = warns + 1
    
    cursor.execute('''
        UPDATE users SET warns = ? WHERE user_id = ? AND chat_id = ?
    ''', (new_warns, user_id, chat_id))
    
    cursor.execute('''
        INSERT INTO warn_history (user_id, chat_id, admin_id, reason, date)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, chat_id, admin_id, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    
    message = f"⚠️ {get_user_name(user_id)} получил предупреждение ({new_warns}/3)\nПричина: {reason}"
    
    # Если 3 варна - бан
    if new_warns >= 3:
        ban_user(chat_id, user_id, admin_id, f"Превышение лимита предупреждений (3/3)")
        message = f"🚫 {get_user_name(user_id)} забанен за 3 предупреждения!\nПоследняя причина: {reason}"
    else:
        send_msg(2000000000 + chat_id, message)
        return
    
    send_msg(2000000000 + chat_id, message)

def unwarn_user(chat_id, user_id):
    """Снять предупреждение"""
    cursor.execute('SELECT warns FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    result = cursor.fetchone()
    warns = result[0] if result else 0
    
    if warns > 0:
        cursor.execute('UPDATE users SET warns = warns - 1 WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        conn.commit()
        send_msg(2000000000 + chat_id, f"✅ Снято предупреждение у {get_user_name(user_id)}")
    else:
        send_msg(2000000000 + chat_id, f"❌ У {get_user_name(user_id)} нет предупреждений")

# ============= ОБРАБОТЧИК КОМАНД =============

def handle_command(user_id, chat_id, cmd, args, peer_id):
    """Обработка команд"""
    
    # ===== ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ =====
    if cmd == 'меню' or cmd == '/menu':
        role = get_user_role(user_id, chat_id) if chat_id else 'user'
        keyboard = get_main_keyboard(role)
        send_msg(peer_id, "🏠 **Главное меню**\nВыберите действие:", keyboard)
        return
    
    elif cmd == '📊 Статистика' or cmd == '/stats':
        target_id = user_id
        if args and args[0].startswith('[id'):
            match = re.search(r'id(\d+)', args[0])
            if match:
                target_id = int(match.group(1))
        
        cursor.execute('SELECT warns, muted_until, role, joined_date FROM users WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
        user_data = cursor.fetchone()
        
        if user_data:
            muted_text = "Нет" if not user_data[1] else f"До {user_data[1][:16]}"
            message = f"""📊 **Статистика пользователя**
━━━━━━━━━━━━━━━━━━━━
👤 Имя: {get_user_name(target_id)}
🆔 ID: {target_id}
⭐ Роль: {user_data[2]}
⚠️ Варны: {user_data[0]}/3
🔇 Мут: {muted_text}
📅 Присоединился: {user_data[3][:10] if user_data[3] else 'Неизвестно'}
━━━━━━━━━━━━━━━━━━━━"""
        else:
            message = f"📊 **Статистика пользователя {get_user_name(target_id)}**\nНет данных"
        send_msg(peer_id, message)
        return
    
    elif cmd == 'ℹ️ Информация' or cmd == '/info':
        message = """🤖 **BLACK FIB BOT v3.0**
━━━━━━━━━━━━━━━━━━━━
👑 Разработчик: [id631833072|Vlad]
📅 Создан: 2024
⚙️ Статус: 🟢 Активен
━━━━━━━━━━━━━━━━━━━━
📋 **Команды:**
• /menu - Главное меню
• /stats @user - Статистика
• /staff - Администрация
• /rules - Правила
━━━━━━━━━━━━━━━━━━━━
📢 Новости: vk.com/blackfib
🆘 Поддержка: vk.me/blackfib"""
        send_msg(peer_id, message)
        return
    
    elif cmd == '👥 Администрация' or cmd == '/staff':
        if not chat_id:
            send_msg(peer_id, "❌ Команда только в беседах!")
            return
        cursor.execute('''
            SELECT user_id, role FROM users 
            WHERE chat_id = ? AND role != 'user'
            ORDER BY 
                CASE role
                    WHEN 'glav' THEN 1
                    WHEN 'zamglav' THEN 2
                    WHEN 'owner' THEN 3
                    WHEN 'admin' THEN 4
                    WHEN 'moderator' THEN 5
                END
        ''', (chat_id,))
        staff = cursor.fetchall()
        if staff:
            roles_ru = {'glav': '👑 Руководитель', 'zamglav': '⚜️ Зам.руководителя', 'owner': '👑 Владелец', 'admin': '🟠 Админ', 'moderator': '🟢 Модератор'}
            message = "👥 **Администрация беседы:**\n━━━━━━━━━━━━━━━━━━━━\n"
            for s in staff:
                message += f"{roles_ru.get(s[1], s[1])}: {get_user_name(s[0])}\n"
        else:
            message = "❌ Нет администрации в беседе"
        send_msg(peer_id, message)
        return
    
    elif cmd == '📜 Правила' or cmd == '/rules':
        message = """📜 **Правила беседы**
━━━━━━━━━━━━━━━━━━━━
1️⃣ **Запрещён мат** - предупреждение
2️⃣ **Оскорбления участников** - мут/бан
3️⃣ **Флуд/Спам** - предупреждение
4️⃣ **Реклама без разрешения** - бан
5️⃣ **Неадекватное поведение** - мут
━━━━━━━━━━━━━━━━━━━━
⚠️ 3 предупреждения = БАН
━━━━━━━━━━━━━━━━━━━━
Нарушение правил = наказание по усмотрению администрации."""
        send_msg(peer_id, message)
        return
    
    # ===== МОДЕРАЦИЯ =====
    elif cmd == '🛡 Модерация' or cmd == '/moderation':
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        keyboard = get_moderation_keyboard()
        send_msg(peer_id, "🛡 **Меню модерации**\nВыберите действие:", keyboard)
        return
    
    elif cmd == '🔇 Мут' or cmd == '/mute':
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        send_msg(peer_id, "📝 **Мут пользователя**\nОтветьте на сообщение пользователя или введите:\n/mute @user время_в_минутах причина")
        return
    
    elif cmd == '🔊 Размут' or cmd == '/unmute':
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        send_msg(peer_id, "📝 **Размут пользователя**\nОтветьте на сообщение пользователя или введите:\n/unmute @user")
        return
    
    elif cmd == '⚠️ Варн' or cmd == '/warn':
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        send_msg(peer_id, "📝 **Выдача варна**\nОтветьте на сообщение пользователя или введите:\n/warn @user причина")
        return
    
    elif cmd == '✅ Снять варн' or cmd == '/unwarn':
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        send_msg(peer_id, "📝 **Снятие варна**\nОтветьте на сообщение пользователя или введите:\n/unwarn @user")
        return
    
    elif cmd == '👢 Кик' or cmd == '/kick':
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        send_msg(peer_id, "📝 **Кик пользователя**\nОтветьте на сообщение пользователя или введите:\n/kick @user причина")
        return
    
    elif cmd == '🚫 Бан' or cmd == '/ban':
        if not check_permission(user_id, chat_id, 'admin'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        send_msg(peer_id, "📝 **Бан пользователя**\nОтветьте на сообщение пользователя или введите:\n/ban @user причина")
        return
    
    elif cmd == '📋 Список варнов' or cmd == '/warnlist':
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        cursor.execute('SELECT user_id, warns FROM users WHERE chat_id = ? AND warns > 0 ORDER BY warns DESC', (chat_id,))
        warned = cursor.fetchall()
        if warned:
            message = "⚠️ **Пользователи с предупреждениями:**\n━━━━━━━━━━━━━━━━━━━━\n"
            for w in warned:
                message += f"• {get_user_name(w[0])} – {w[1]}/3\n"
        else:
            message = "✅ Нет пользователей с предупреждениями"
        send_msg(peer_id, message)
        return
    
    elif cmd == '🔇 Список мутов' or cmd == '/mutelist':
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        cursor.execute('SELECT user_id, muted_until FROM users WHERE chat_id = ? AND muted_until IS NOT NULL', (chat_id,))
        muted_list = cursor.fetchall()
        now = datetime.now()
        active = []
        for m in muted_list:
            try:
                until = datetime.strptime(m[1], '%Y-%m-%d %H:%M:%S')
                if until > now:
                    active.append((m[0], until))
            except:
                pass
        if active:
            message = "🔇 **Активные муты:**\n━━━━━━━━━━━━━━━━━━━━\n"
            for a in active:
                time_left = a[1] - now
                hours = time_left.seconds // 3600
                mins = (time_left.seconds % 3600) // 60
                message += f"• {get_user_name(a[0])} – {hours}ч {mins}м\n"
        else:
            message = "✅ Нет активных мутов"
        send_msg(peer_id, message)
        return
    
    # ===== АДМИН-ПАНЕЛЬ =====
    elif cmd == '👑 Админ-панель' or cmd == '/admin':
        if not check_permission(user_id, chat_id, 'admin'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        keyboard = get_admin_keyboard()
        send_msg(peer_id, "👑 **Админ-панель**\nВыберите действие:", keyboard)
        return
    
    elif cmd == '➕ Выдать модера' or cmd == '/addmoder':
        if not check_permission(user_id, chat_id, 'admin'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        send_msg(peer_id, "📝 **Выдача модератора**\nОтветьте на сообщение пользователя или введите:\n/addmoder @user")
        return
    
    elif cmd == '➖ Забрать роль' or cmd == '/removerole':
        if not check_permission(user_id, chat_id, 'admin'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        send_msg(peer_id, "📝 **Снятие роли**\nОтветьте на сообщение пользователя или введите:\n/removerole @user")
        return
    
    elif cmd == '📝 Фильтр мата' or cmd == '/filter':
        if not check_permission(user_id, chat_id, 'admin'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        cursor.execute('SELECT filter_enabled FROM chats WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        current = result[0] if result else 0
        new_value = 0 if current else 1
        cursor.execute('UPDATE chats SET filter_enabled = ? WHERE chat_id = ?', (new_value, chat_id))
        conn.commit()
        status = "включён" if new_value else "выключен"
        send_msg(peer_id, f"📝 **Фильтр мата {status}**")
        return
    
    elif cmd == '🔇 Режим тишины' or cmd == '/quiet':
        if not check_permission(user_id, chat_id, 'admin'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        cursor.execute('SELECT quiet_mode FROM chats WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        current = result[0] if result else 0
        new_value = 0 if current else 1
        cursor.execute('UPDATE chats SET quiet_mode = ? WHERE chat_id = ?', (new_value, chat_id))
        conn.commit()
        status = "включён" if new_value else "выключен"
        send_msg(peer_id, f"🔇 **Режим тишины {status}**")
        return
    
    elif cmd == '🔙 Назад':
        role = get_user_role(user_id, chat_id) if chat_id else 'user'
        keyboard = get_main_keyboard(role)
        send_msg(peer_id, "🏠 **Главное меню**", keyboard)
        return
    
    # ===== ОБРАБОТКА КОМАНД С АРГУМЕНТАМИ =====
    # Разбор команд типа /kick @user причина
    if cmd == '/kick' and len(args) >= 1:
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        match = re.search(r'id(\d+)', args[0])
        if match:
            target_id = int(match.group(1))
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
            kick_user(chat_id, target_id, reason, user_id)
        return
    
    elif cmd == '/mute' and len(args) >= 2:
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        match = re.search(r'id(\d+)', args[0])
        if match:
            target_id = int(match.group(1))
            try:
                minutes = int(args[1])
                reason = ' '.join(args[2:]) if len(args) > 2 else 'Не указана'
                mute_user(chat_id, target_id, minutes, user_id, reason)
            except ValueError:
                send_msg(peer_id, "❌ Укажите корректное время в минутах!")
        return
    
    elif cmd == '/unmute' and len(args) >= 1:
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        match = re.search(r'id(\d+)', args[0])
        if match:
            target_id = int(match.group(1))
            unmute_user(chat_id, target_id)
        return
    
    elif cmd == '/warn' and len(args) >= 1:
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        match = re.search(r'id(\d+)', args[0])
        if match:
            target_id = int(match.group(1))
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
            warn_user(chat_id, target_id, user_id, reason)
        return
    
    elif cmd == '/unwarn' and len(args) >= 1:
        if not check_permission(user_id, chat_id, 'moderator'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        match = re.search(r'id(\d+)', args[0])
        if match:
            target_id = int(match.group(1))
            unwarn_user(chat_id, target_id)
        return
    
    elif cmd == '/ban' and len(args) >= 1:
        if not check_permission(user_id, chat_id, 'admin'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        match = re.search(r'id(\d+)', args[0])
        if match:
            target_id = int(match.group(1))
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
            ban_user(chat_id, target_id, user_id, reason)
        return
    
    elif cmd == '/addmoder' and len(args) >= 1:
        if not check_permission(user_id, chat_id, 'admin'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        match = re.search(r'id(\d+)', args[0])
        if match:
            target_id = int(match.group(1))
            cursor.execute('UPDATE users SET role = ? WHERE user_id = ? AND chat_id = ?', ('moderator', target_id, chat_id))
            if cursor.rowcount == 0:
                cursor.execute('INSERT INTO users (user_id, chat_id, role, joined_date) VALUES (?, ?, ?, ?)',
                             (target_id, chat_id, 'moderator', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            send_msg(peer_id, f"✅ {get_user_name(target_id)} теперь модератор!")
        return
    
    elif cmd == '/removerole' and len(args) >= 1:
        if not check_permission(user_id, chat_id, 'admin'):
            send_msg(peer_id, "❌ Недостаточно прав!")
            return
        match = re.search(r'id(\d+)', args[0])
        if match:
            target_id = int(match.group(1))
            cursor.execute('UPDATE users SET role = ? WHERE user_id = ? AND chat_id = ?', ('user', target_id, chat_id))
            conn.commit()
            send_msg(peer_id, f"✅ У {get_user_name(target_id)} убрана роль")
        return

# ============= ГЛАВНЫЙ ЦИКЛ =============

print("🤖 BLACK FIB BOT v3.0 ЗАПУЩЕН!")
print(f"👑 Владелец: [id{OWNER_ID}|Vlad]")
print("💬 Команды: /menu, /help")
print("-" * 40)

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        user_id = event.user_id
        message = event.text or ""
        
        if event.from_chat:
            chat_id = event.chat_id
            peer_id = 2000000000 + chat_id
        else:
            chat_id = 0
            peer_id = user_id
        
        # Регистрация чата и пользователя
        if chat_id:
            register_chat(chat_id)
            register_user(user_id, chat_id)
            
            # Обновляем активность
            cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ? AND chat_id = ?',
                         (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id, chat_id))
            conn.commit()
            
            # Проверка бана
            if check_ban(user_id, chat_id):
                kick_user(chat_id, user_id, "Вы забанены на этом сервере")
                continue
            
            # Проверка мута
            if check_mute(user_id, chat_id):
                # Замученный пользователь не может писать
                try:
                    vk.method('messages.delete', {
                        'message_ids': [event.message_id],
                        'delete_for_all': 1
                    })
                except:
                    pass
                continue
            
            # Фильтр мата
            if message and not message.startswith('/'):
               
