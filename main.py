import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
import sqlite3
import time
from datetime import datetime, timedelta
import re

# ============= КОНФИГУРАЦИЯ =============
TOKEN = 'vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg'
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
default_words = ['сука', 'блядь', 'хуй', 'пизда', 'ебать', 'жопа', 'пидор', 'мудак', 'уебан', 'долбоеб', 'хер', 'нахер', 'идиот', 'дебил']
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
        cursor.execute('''
            INSERT OR REPLACE INTO bans (user_id, chat_id, admin_id, reason, date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, chat_id, admin_id, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        cursor.execute('''
            UPDATE users SET banned = 1 WHERE user_id = ? AND chat_id = ?
        ''', (user_id, chat_id))
        conn.commit()
        
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
    
    if new_warns >= 3:
        ban_user(chat_id, user_id, admin_id, f"3/3 предупреждений")
        message = f"🚫 {get_user_name(user_id)} забанен за 3 предупреждения!\nПоследняя причина: {reason}"
    
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

# ============= ОБРАБОТЧИК СООБЩЕНИЙ =============

def handle_text_message(user_id, chat_id, peer_id, message):
    """Обработка текстовых сообщений (не команд)"""
    if not chat_id:
        return
    if not check_activation(chat_id):
        return
    if message.startswith('/'):
        return
    
    # Проверка фильтра мата
    cursor.execute('SELECT filter_enabled FROM chats WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    filter_enabled = result[0] if result else 0
    
    if filter_enabled:
        cursor.execute('SELECT word FROM filter_words')
        bad_words = cursor.fetchall()
        for word in bad_words:
            if word[0].lower() in message.lower():
                try:
                    vk.method('messages.delete', {
                        'message_ids': [event.message_id],
                        'delete_for_all': 1
                    })
                except:
                    pass
                warn_user(chat_id, user_id, 0, f"Мат: {word[0]}")
                break

# ============= ГЛАВНЫЙ ЦИКЛ =============

print("🤖 BLACK FIB BOT v3.0 ЗАПУЩЕН!")
print(f"👑 Владелец: [id{OWNER_ID}|Vlad]")
print("💬 Команды: /menu, /help")
print("-" * 40)

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        user_id = event.user_id
        message_text = event.text or ""
        
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
            
            cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ? AND chat_id = ?',
                         (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id, chat_id))
            conn.commit()
            
            # Проверка бана
            if check_ban(user_id, chat_id):
                kick_user(chat_id, user_id, "Вы забанены")
                continue
            
            # Проверка мута
            if check_mute(user_id, chat_id):
                try:
                    vk.method('messages.delete', {
                        'message_ids': [event.message_id],
                        'delete_for_all': 1
                    })
                except:
                    pass
                continue
            
            # Проверка текста на мат
            if message_text and not message_text.startswith('/'):
                cursor.execute('SELECT filter_enabled FROM chats WHERE chat_id = ?', (chat_id,))
                filter_res = cursor.fetchone()
                if filter_res and filter_res[0] == 1:
                    cursor.execute('SELECT word FROM filter_words')
                    bad_words = cursor.fetchall()
                    for word in bad_words:
                        if word[0].lower() in message_text.lower():
                            try:
                                vk.method('messages.delete', {
                                    'message_ids': [event.message_id],
                                    'delete_for_all': 1
                                })
                            except:
                                pass
                            warn_user(chat_id, user_id, 0, f"Мат: {word[0]}")
                            break
        
        # Обработка команд
        if message_text.startswith('/'):
            parts = message_text.split()
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            # Меню
            if cmd == '/menu' or cmd == 'меню':
                role = get_user_role(user_id, chat_id) if chat_id else 'user'
                keyboard = get_main_keyboard(role)
                send_msg(peer_id, "🏠 **Главное меню**\nВыберите действие:", keyboard)
            
            elif cmd == '/start':
                if chat_id:
                    if user_id == OWNER_ID:
                        cursor.execute('UPDATE chats SET bot_activated = 1 WHERE chat_id = ?', (chat_id,))
                        conn.commit()
                        send_msg(peer_id, "✅ Бот активирован в этой беседе!\nВведите /menu для открытия меню")
                    else:
                        send_msg(peer_id, "❌ Только владелец бота может активировать его!")
                else:
                    send_msg(peer_id, "🤖 Бот работает!\nДобавьте меня в беседу и напишите /start")
            
            # Статистика
            elif cmd == '/stats' or cmd == '📊 Статистика':
                target_id = user_id
                if args:
                    match = re.search(r'id(\d+)', args[0])
                    if match:
                        target_id = int(match.group(1))
                cursor.execute('SELECT warns, muted_until, role, joined_date FROM users WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
                data = cursor.fetchone()
                if data:
                    muted_text = "Нет" if not data[1] else f"До {data[1][:16]}"
                    msg = f"""📊 **Статистика пользователя**
━━━━━━━━━━━━━━━━━━━━
👤 Имя: {get_user_name(target_id)}
🆔 ID: {target_id}
⭐ Роль: {data[2]}
⚠️ Варны: {data[0]}/3
🔇 Мут: {muted_text}
📅 Присоединился: {data[3][:10] if data[3] else 'Неизвестно'}"""
                else:
                    msg = f"📊 Нет данных о пользователе {get_user_name(target_id)}"
                send_msg(peer_id, msg)
            
            # Информация
            elif cmd == '/info' or cmd == 'ℹ️ Информация':
                msg = """🤖 **BLACK FIB BOT v3.0**
━━━━━━━━━━━━━━━━━━━━
👑 Разработчик: [id631833072|Vlad]
📅 Создан: 2024
⚙️ Статус: 🟢 Активен
━━━━━━━━━━━━━━━━━━━━
📋 /menu - Главное меню
👥 /staff - Администрация
📜 /rules - Правила
━━━━━━━━━━━━━━━━━━━━
📢 Новости: vk.com/blackfib"""
                send_msg(peer_id, msg)
            
            # Администрация
            elif cmd == '/staff' or cmd == '👥 Администрация':
                if not chat_id:
                    send_msg(peer_id, "❌ Команда только в беседах!")
                else:
                    cursor.execute('''SELECT user_id, role FROM users WHERE chat_id = ? AND role != 'user' ORDER BY 
                        CASE role WHEN 'glav' THEN 1 WHEN 'zamglav' THEN 2 WHEN 'owner' THEN 3 WHEN 'admin' THEN 4 WHEN 'moderator' THEN 5 END''', (chat_id,))
                    staff = cursor.fetchall()
                    if staff:
                        roles_ru = {'glav': '👑 Руководитель', 'zamglav': '⚜️ Зам.руководителя', 'owner': '👑 Владелец', 'admin': '🟠 Админ', 'moderator': '🟢 Модератор'}
                        msg = "👥 **Администрация:**\n━━━━━━━━━━━━━━━━━━━━\n"
                        for s in staff:
                            msg += f"{roles_ru.get(s[1], s[1])}: {get_user_name(s[0])}\n"
                    else:
                        msg = "❌ Нет администрации"
                    send_msg(peer_id, msg)
            
            # Правила
            elif cmd == '/rules' or cmd == '📜 Правила':
                msg = """📜 **Правила беседы**
━━━━━━━━━━━━━━━━━━━━
1️⃣ Запрещён мат → предупреждение
2️⃣ Оскорбления → мут/бан
3️⃣ Флуд/Спам → предупреждение
4️⃣ Реклама → бан
5️⃣ Неадекватное поведение → мут
━━━━━━━━━━━━━━━━━━━━
⚠️ 3 предупреждения = БАН"""
                send_msg(peer_id, msg)
            
            # Модерация
            elif cmd == '/moderation' or cmd == '🛡 Модерация':
                if not check_permission(user_id, chat_id, 'moderator'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    send_msg(peer_id, "🛡 **Меню модерации**", get_moderation_keyboard())
            
            # Кик
            elif cmd == '/kick' and args:
                if not check_permission(user_id, chat_id, 'moderator'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    match = re.search(r'id(\d+)', args[0])
                    if match:
                        target_id = int(match.group(1))
                        reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
                        kick_user(chat_id, target_id, reason, user_id)
            
            # Мут
            elif cmd == '/mute' and len(args) >= 2:
                if not check_permission(user_id, chat_id, 'moderator'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    match = re.search(r'id(\d+)', args[0])
                    if match:
                        target_id = int(match.group(1))
                        try:
                            minutes = int(args[1])
                            reason = ' '.join(args[2:]) if len(args) > 2 else 'Не указана'
                            mute_user(chat_id, target_id, minutes, user_id, reason)
                        except ValueError:
                            send_msg(peer_id, "❌ Укажите корректное время в минутах!")
            
            # Размут
            elif cmd == '/unmute' and args:
                if not check_permission(user_id, chat_id, 'moderator'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    match = re.search(r'id(\d+)', args[0])
                    if match:
                        unmute_user(chat_id, int(match.group(1)))
            
            # Варн
            elif cmd == '/warn' and args:
                if not check_permission(user_id, chat_id, 'moderator'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    match = re.search(r'id(\d+)', args[0])
                    if match:
                        target_id = int(match.group(1))
                        reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
                        warn_user(chat_id, target_id, user_id, reason)
            
            # Снять варн
            elif cmd == '/unwarn' and args:
                if not check_permission(user_id, chat_id, 'moderator'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    match = re.search(r'id(\d+)', args[0])
                    if match:
                        unwarn_user(chat_id, int(match.group(1)))
            
            # Бан
            elif cmd == '/ban' and args:
                if not check_permission(user_id, chat_id, 'admin'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    match = re.search(r'id(\d+)', args[0])
                    if match:
                        target_id = int(match.group(1))
                        reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
                        ban_user(chat_id, target_id, user_id, reason)
            
            # Список варнов
            elif cmd == '/warnlist':
                if not check_permission(user_id, chat_id, 'moderator'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    cursor.execute('SELECT user_id, warns FROM users WHERE chat_id = ? AND warns > 0 ORDER BY warns DESC', (chat_id,))
                    warned = cursor.fetchall()
                    if warned:
                        msg = "⚠️ **Пользователи с варнами:**\n━━━━━━━━━━━━━━━━━━━━\n"
                        for w in warned:
                            msg += f"• {get_user_name(w[0])} – {w[1]}/3\n"
                    else:
                        msg = "✅ Нет пользователей с предупреждениями"
                    send_msg(peer_id, msg)
            
            # Список мутов
            elif cmd == '/mutelist':
                if not check_permission(user_id, chat_id, 'moderator'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
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
                        msg = "🔇 **Активные муты:**\n━━━━━━━━━━━━━━━━━━━━\n"
                        for a in active:
                            left = a[1] - now
                            msg += f"• {get_user_name(a[0])} – {left.seconds//3600}ч {(left.seconds%3600)//60}м\n"
                    else:
                        msg = "✅ Нет активных мутов"
                    send_msg(peer_id, msg)
            
            # Админ-панель
            elif cmd == '/admin' or cmd == '👑 Админ-панель':
                if not check_permission(user_id, chat_id, 'admin'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    send_msg(peer_id, "👑 **Админ-панель**", get_admin_keyboard())
            
            # Выдать модера
            elif cmd == '/addmoder' and args:
                if not check_permission(user_id, chat_id, 'admin'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    match = re.search(r'id(\d+)', args[0])
                    if match:
                        target_id = int(match.group(1))
                        cursor.execute('UPDATE users SET role = ? WHERE user_id = ? AND chat_id = ?', ('moderator', target_id, chat_id))
                        if cursor.rowcount == 0:
                            cursor.execute('INSERT INTO users (user_id, chat_id, role, joined_date) VALUES (?, ?, ?, ?)',
                                         (target_id, chat_id, 'moderator', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                        conn.commit()
                        send_msg(peer_id, f"✅ {get_user_name(target_id)} теперь модератор!")
            
            # Забрать роль
            elif cmd == '/removerole' and args:
                if not check_permission(user_id, chat_id, 'admin'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    match = re.search(r'id(\d+)', args[0])
                    if match:
                        target_id = int(match.group(1))
                        cursor.execute('UPDATE users SET role = ? WHERE user_id = ? AND chat_id = ?', ('user', target_id, chat_id))
                        conn.commit()
                        send_msg(peer_id, f"✅ У {get_user_name(target_id)} убрана роль")
            
            # Фильтр мата
            elif cmd == '/filter':
                if not check_permission(user_id, chat_id, 'admin'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    cursor.execute('SELECT filter_enabled FROM chats WHERE chat_id = ?', (chat_id,))
                    res = cursor.fetchone()
                    new_val = 0 if (res and res[0] == 1) else 1
                    cursor.execute('UPDATE chats SET filter_enabled = ? WHERE chat_id = ?', (new_val, chat_id))
                    conn.commit()
                    send_msg(peer_id, f"📝 Фильтр мата {'включён' if new_val else 'выключен'}")
            
            # Режим тишины
            elif cmd == '/quiet':
                if not check_permission(user_id, chat_id, 'admin'):
                    send_msg(peer_id, "❌ Недостаточно прав!")
                else:
                    cursor.execute('SELECT quiet_mode FROM chats WHERE chat_id = ?', (chat_id,))
                    res = cursor.fetchone()
                    new_val = 0 if (res and res[0] == 1) else 1
                    cursor.execute('UPDATE chats SET quiet_mode = ? WHERE chat_id = ?', (new_val, chat_id))
                    conn.commit()
                    send_msg(peer_id, f"🔇 Режим тишины {'включён' if new_val else 'выключен'}")
            
            # Помощь
            elif cmd == '/help':
                msg = """📚 **Доступные команды:**
━━━━━━━━━━━━━━━━━━━━
👤 **Пользователи:**
/menu - Открыть меню
/stats @user - Статистика
/staff - Администрация
/rules - Правила

🛡 **Модерация:**
/kick @user [причина]
/mute @user время [причина]
/unmute @user
/warn @user [причина]
/unwarn @user
/warnlist - Список варнов
/mutelist - Список мутов

👑 **Администрирование:**
/ban @user [причина]
/addmoder @user
/removerole @user
/filter - Вкл/Выкл фильтр
/quiet - Вкл/Выкл тишину
━━━━━━━━━━━━━━━━━━━━
💬 /menu - Открыть меню с кнопками"""
                send_msg(peer_id, msg)
            
            elif cmd == '🔙 Назад':
                role = get_user_role(user_id, chat_id) if chat_id else 'user'
                send_msg(peer_id, "🏠 Главное меню", get_main_keyboard(role))
            
            elif cmd in ['🔇 Мут', '🔊 Размут', '⚠️ Варн', '✅ Снять варн', '👢 Кик', '🚫 Бан', '📋 Список варнов', '🔇 Список мутов']:
                send_msg(peer_id, f"📝 Используйте команду: /{cmd.replace(' ', '').lower()} @user [причина]")
            
            elif cmd in ['➕ Выдать модера', '➖ Забрать роль', '📝 Фильтр мата', '🔇 Режим тишины']:
                if cmd == '➕ Выдать модера':
                    send_msg(peer_id, "📝 Используйте: /addmoder @user")
                elif cmd == '➖ Забрать роль':
                    send_msg(peer_id, "📝 Используйте: /removerole @user")
                else:
                    send_msg(peer_id, f"📝 Используйте: /{cmd.replace(' ', '').lower()}")
