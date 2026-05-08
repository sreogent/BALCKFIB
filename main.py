import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import sqlite3
from datetime import datetime, timedelta
import re
import time

# ============= КОНФИГ =============
TOKEN = 'vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg'
OWNER_ID = 631833072

# Подключение к БД
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()

# ============= СОЗДАНИЕ ТАБЛИЦ =============
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    chat_id INTEGER,
    warns INTEGER DEFAULT 0,
    mute TEXT,
    ban INTEGER DEFAULT 0,
    role TEXT DEFAULT 'user',
    nick TEXT,
    joined TEXT,
    last_active TEXT,
    messages INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, chat_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    activated INTEGER DEFAULT 0,
    filter_on INTEGER DEFAULT 1,
    quiet_on INTEGER DEFAULT 0,
    welcome_text TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS badwords (
    word TEXT PRIMARY KEY
)''')

c.execute('''CREATE TABLE IF NOT EXISTS warn_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    chat_id INTEGER,
    admin_id INTEGER,
    reason TEXT,
    date TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    chat_id INTEGER,
    admin_id INTEGER,
    reason TEXT,
    date TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS global_bans (
    user_id INTEGER PRIMARY KEY,
    admin_id INTEGER,
    reason TEXT,
    date TEXT
)''')

# Добавляем маты
bad_words = ['сука', 'блядь', 'хуй', 'пизда', 'ебать', 'жопа', 'пидор', 'мудак', 'уебан', 'долбоеб', 'хер', 'нахер', 'идиот', 'дебил', 'тупой']
for w in bad_words:
    c.execute("INSERT OR IGNORE INTO badwords (word) VALUES (?)", (w,))
conn.commit()

print("БОТ ЗАПУЩЕН")
print("=" * 60)

# Подключение к ВК
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =============

def send(peer, text):
    """Отправка сообщения"""
    try:
        vk.messages.send(peer_id=peer, message=text, random_id=get_random_id())
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_name(uid):
    """Получить имя пользователя по ID"""
    try:
        u = vk.users.get(user_ids=uid)[0]
        return f"{u['first_name']} {u['last_name']}"
    except:
        return f"id{uid}"

def get_nick(uid, cid):
    """Получить ник пользователя в чате"""
    r = c.execute("SELECT nick FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    return r[0] if r and r[0] else get_name(uid)

def get_role(uid, cid):
    """Получить роль пользователя"""
    if uid == OWNER_ID:
        return 'glav'
    r = c.execute("SELECT role FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    return r[0] if r else 'user'

def get_role_level(role):
    """Уровень роли для проверки прав"""
    levels = {
        'user': 0, 'helper': 1, 'moderator': 2, 'seniormoderator': 3,
        'admin': 4, 'senioradmin': 5, 'owner': 6, 'zamglav': 7, 'glav': 8
    }
    return levels.get(role, 0)

def check_perm(uid, cid, need):
    """Проверка прав пользователя"""
    if uid == OWNER_ID:
        return True
    return get_role_level(get_role(uid, cid)) >= get_role_level(need)

def is_muted(uid, cid):
    """Проверка мута"""
    r = c.execute("SELECT mute FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    if r and r[0]:
        try:
            till = datetime.strptime(r[0], '%Y-%m-%d %H:%M:%S')
            if till > datetime.now():
                return True
            else:
                c.execute("UPDATE users SET mute=NULL WHERE user_id=? AND chat_id=?", (uid, cid))
                conn.commit()
        except:
            pass
    return False

def is_banned(uid, cid):
    """Проверка бана в конкретном чате"""
    r = c.execute("SELECT ban FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    return r and r[0] == 1

def is_global_banned(uid):
    """Проверка глобального бана"""
    r = c.execute("SELECT * FROM global_bans WHERE user_id=?", (uid,)).fetchone()
    return r is not None

def register_user(uid, cid):
    """Регистрация пользователя в чате"""
    c.execute("INSERT OR IGNORE INTO users (user_id, chat_id, joined, last_active) VALUES (?, ?, ?, ?)",
              (uid, cid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def get_chat_users(cid):
    """Получить список участников чата"""
    try:
        chat = vk.messages.getConversationMembers(peer_id=2000000000 + cid)
        return [m['member_id'] for m in chat['items'] if m['member_id'] > 0]
    except:
        return []

def extract_id(text):
    """Извлечь ID пользователя из текста (@user)"""
    ids = re.findall(r'id(\d+)', text)
    if ids:
        return int(ids[0])
    nums = re.findall(r'(\d+)', text)
    return int(nums[0]) if nums else None

def get_all_chats():
    """Получить список всех активированных чатов"""
    return [row[0] for row in c.execute("SELECT chat_id FROM chats WHERE activated=1").fetchall()]

# ============= ОСНОВНЫЕ ДЕЙСТВИЯ =============

def add_warn(cid, uid, admin, reason):
    """Выдать предупреждение"""
    w = c.execute("SELECT warns FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    warns = (w[0] if w else 0) + 1
    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, warns) VALUES (?,?,?)", (uid, cid, warns))
    c.execute("INSERT INTO warn_history (user_id, chat_id, admin_id, reason, date) VALUES (?,?,?,?,?)",
              (uid, cid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    send(2000000000 + cid, f"⚠️ {get_nick(uid, cid)} | ВАРН {warns}/3\n📝 {reason}\n👮 {get_nick(admin, cid)}")
    if warns >= 3:
        c.execute("UPDATE users SET ban=1 WHERE user_id=? AND chat_id=?", (uid, cid))
        conn.commit()
        try:
            vk.messages.removeChatUser(chat_id=cid, user_id=uid)
            send(2000000000 + cid, f"🚫 {get_nick(uid, cid)} ЗАБАНЕН (3/3 варнов)")
        except:
            pass

def mute_user(cid, uid, minutes, admin, reason):
    """Замутить пользователя"""
    till = datetime.now() + timedelta(minutes=minutes)
    c.execute("UPDATE users SET mute=? WHERE user_id=? AND chat_id=?", (till.strftime('%Y-%m-%d %H:%M:%S'), uid, cid))
    conn.commit()
    send(2000000000 + cid, f"🔇 {get_nick(uid, cid)} | МУТ {minutes} мин\n📝 {reason}\n👮 {get_nick(admin, cid)}")

def kick_user(cid, uid, admin, reason):
    """Исключить пользователя из чата"""
    try:
        vk.messages.removeChatUser(chat_id=cid, user_id=uid)
        send(2000000000 + cid, f"👢 {get_nick(uid, cid)} | КИК\n📝 {reason}\n👮 {get_nick(admin, cid)}")
    except:
        pass

def ban_user(cid, uid, admin, reason):
    """Забанить пользователя в чате"""
    c.execute("UPDATE users SET ban=1 WHERE user_id=? AND chat_id=?", (uid, cid))
    c.execute("INSERT INTO bans (user_id, chat_id, admin_id, reason, date) VALUES (?,?,?,?,?)",
              (uid, cid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    try:
        vk.messages.removeChatUser(chat_id=cid, user_id=uid)
        send(2000000000 + cid, f"🚫 {get_nick(uid, cid)} | БАН\n📝 {reason}\n👮 {get_nick(admin, cid)}")
    except:
        pass

def unban_user(cid, uid, admin):
    """Разбанить пользователя"""
    c.execute("UPDATE users SET ban=0 WHERE user_id=? AND chat_id=?", (uid, cid))
    c.execute("DELETE FROM bans WHERE user_id=? AND chat_id=?", (uid, cid))
    conn.commit()
    send(2000000000 + cid, f"✅ {get_nick(uid, cid)} | РАЗБАНЕН\n👮 {get_nick(admin, cid)}")

def set_nick(cid, uid, admin, nick):
    """Установить ник"""
    c.execute("UPDATE users SET nick=? WHERE user_id=? AND chat_id=?", (nick, uid, cid))
    conn.commit()
    send(2000000000 + cid, f"🏷 {get_nick(uid, cid)} | НИК: {nick}\n👮 {get_nick(admin, cid)}")

def global_ban(uid, admin, reason):
    """Глобальный бан (во всех чатах)"""
    c.execute("INSERT OR REPLACE INTO global_bans (user_id, admin_id, reason, date) VALUES (?,?,?,?)",
              (uid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    for chat in get_all_chats():
        try:
            vk.messages.removeChatUser(chat_id=chat, user_id=uid)
        except:
            pass
    send(OWNER_ID, f"🌐 {get_name(uid)} | ГЛОБАЛЬНЫЙ БАН\n📝 {reason}\n👮 {get_name(admin)}")

def global_unban(uid, admin):
    """Глобальный разбан"""
    c.execute("DELETE FROM global_bans WHERE user_id=?", (uid,))
    conn.commit()
    send(OWNER_ID, f"🌐 {get_name(uid)} | ГЛОБАЛЬНЫЙ РАЗБАН\n👮 {get_name(admin)}")

def clear_chat_messages(peer, count):
    """Очистить сообщения в чате"""
    try:
        history = vk.messages.getHistory(peer_id=peer, count=count)
        ids = [m['id'] for m in history['items']]
        vk.messages.delete(message_ids=ids, delete_for_all=1)
        return len(ids)
    except:
        return 0

def send_to_all_chats(text):
    """Отправить сообщение во все чаты"""
    for chat in get_all_chats():
        try:
            send(2000000000 + chat, text)
        except:
            pass

def convert_role_name(role):
    """Конвертировать роль в читаемый вид"""
    roles = {
        'helper': '💚 ХЭЛПЕР', 'moderator': '💙 МОДЕРАТОР', 'seniormoderator': '🔵 СТ.МОДЕРАТОР',
        'admin': '🟢 АДМИН', 'senioradmin': '🟡 СТ.АДМИН', 'owner': '👑 ВЛАДЕЛЕЦ',
        'zamglav': '⚜️ ЗАМ.ГЛАВЫ', 'glav': '👑 ГЛАВА'
    }
    return roles.get(role, role)

print("БОТ РАБОТАЕТ, ЖДУ КОМАНД...")
print("=" * 60)

# ============= ГЛАВНЫЙ ЦИКЛ =============
for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        uid = event.user_id
        msg = event.text or ""
        msg_lower = msg.lower()
        
        if event.from_chat:
            cid = event.chat_id
            peer = 2000000000 + cid
        else:
            cid = 0
            peer = uid
        
        # Регистрация чата и пользователя
        if cid:
            c.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (cid,))
            register_user(uid, cid)
            c.execute("UPDATE users SET last_active=?, messages=messages+1 WHERE user_id=? AND chat_id=?", 
                     (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), uid, cid))
            conn.commit()
            
            # Проверка глобального бана
            if is_global_banned(uid):
                try:
                    vk.messages.removeChatUser(chat_id=cid, user_id=uid)
                except:
                    pass
                continue
            
            # Проверка бана
            if is_banned(uid, cid):
                try:
                    vk.messages.removeChatUser(chat_id=cid, user_id=uid)
                except:
                    pass
                continue
            
            # Проверка мута
            if is_muted(uid, cid):
                continue
            
            # Проверка активации бота
            activated = c.execute("SELECT activated FROM chats WHERE chat_id=?", (cid,)).fetchone()
            if not activated or activated[0] == 0:
                if msg == '/start' and uid == OWNER_ID:
                    c.execute("UPDATE chats SET activated=1 WHERE chat_id=?", (cid,))
                    conn.commit()
                    send(peer, "✅ БОТ АКТИВИРОВАН В ЭТОЙ БЕСЕДЕ!\n📋 Напиши /help для списка команд")
                continue
            
            # Фильтр мата
            if not msg.startswith('/'):
                filter_on = c.execute("SELECT filter_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                if not filter_on or filter_on[0] == 1:
                    bad = c.execute("SELECT word FROM badwords").fetchall()
                    for w in bad:
                        if w[0].lower() in msg_lower:
                            try:
                                vk.messages.delete(message_ids=[event.message_id], delete_for_all=1)
                            except:
                                pass
                            add_warn(cid, uid, 0, f"МАТ: {w[0]}")
                            break
        
        # ============= КОМАНДЫ ДЛЯ ВСЕХ =============
        
        if msg == '/help':
            txt = """📚 **BLACK FIB BOT - ПОЛНАЯ СПРАВКА**
━━━━━━━━━━━━━━━━━━━━

👤 **КОМАНДЫ ДЛЯ ВСЕХ:**
/info - информация о боте
/stats @user - статистика пользователя
/getid - узнать свой ID
/test - проверка работы бота
/ping - пинг бота

💚 **ХЭЛПЕРЫ:**
/kick @user [причина] - исключить из беседы
/mute @user время [причина] - замутить (в минутах)
/unmute @user - снять мут
/warn @user [причина] - выдать предупреждение
/unwarn @user - снять предупреждение
/clear 10 - очистить чат
/staff - список администрации
/setnick @user ник - установить ник
/nlist - список всех ников
/warnlist - список пользователей с варнами
/mutelist - список активных мутов

💙 **МОДЕРАТОРЫ:**
/ban @user [причина] - заблокировать в чате
/unban @user - разблокировать
/addmoder @user - выдать модератора
/removerole @user - забрать роль
/zov - упомянуть всех участников
/banlist - список забаненных
/inactivelist 30 - список неактивных (дней)

🔵 **СТАРШИЕ МОДЕРАТОРЫ:**
/quiet - включить/выключить режим тишины
/addsenmoder @user - выдать старшего модератора
/bug текст - сообщить о баге
/rnickall - сбросить все ники в беседе

🟢 **АДМИНИСТРАТОРЫ:**
/addadmin @user - выдать администратора
/settings - настройки беседы
/filter - включить/выключить фильтр мата
/serverinfo - информация о беседе
/rkick - кик всех новых участников

🟡 **СТАРШИЕ АДМИНИСТРАТОРЫ:**
/type 1-4 - тип беседы
/leave - кик при выходе участника
/editowner @user - передать права владельца
/pin текст - закрепить сообщение
/unpin - открепить сообщение
/rroleall - сбросить все роли
/addsenadm @user - выдать старшего админа
/masskick - кик всех без роли
/invite - разрешить приглашения модерам
/antiflood - включить/выключить антифлуд
/welcometext текст - установить приветствие

🔴 **СПЕЦ АДМИНИСТРАТОРЫ:**
/gban @user [причина] - глобальный бан
/gunban @user - глобальный разбан
/gbanlist - список глобальных банов
/banwords - список запрещенных слов
/addowner @user - выдать владельца беседы
/skick @user - супер кик (из всех бесед)
/sban @user - супер бан
/sunban @user - супер разбан

🟠 **ЗАМ.СПЕЦ АДМИНА:**
/addword слово - добавить слово в фильтр
/delword слово - удалить слово из фильтра
/pull название - создать привязку чата
/pullinfo - информация о привязках
/delpull название - удалить привязку
/srnick @user - сбросить ник везде
/ssetnick @user ник - установить ник везде
/srrole @user - сбросить роль везде
/srole @user роль - выдать роль везде
/szov текст - супер упоминание во все чаты

👑 **ВЛАДЕЛЕЦ БЕСЕДЫ:**
/gremoverole @user - сбросить все роли пользователя
/news текст - отправить новости во все чаты
/addzam @user - выдать зам.создателя

⚜️ **ЗАМ.СОЗДАТЕЛЯ:**
/banid id - заблокировать беседу по ID
/unbanid id - разблокировать беседу
/clearchat id - удалить чат из БД
/infoid @user - информация о пользователе
/listchats - список всех чатов
/server - информация о сервере

👑 **СОЗДАТЕЛЬ БОТА:**
/adddev @user - выдать права создателя
/addbug @user - добавить получателя багов
/delbug @user - удалить получателя багов
/sync - синхронизировать БД
━━━━━━━━━━━━━━━━━━━━
💡 Для активации бота в беседе напиши /start"""
            send(peer, txt)
        
        elif msg == '/info':
            send(peer, "🤖 **BLACK FIB BOT v4.0**\n━━━━━━━━━━━━━━━━━━━━\n👑 Разработчик: Дмитрий\n📅 Дата создания: 2024\n⚙️ Статус: 🟢 АКТИВЕН\n📋 /help - все команды")
        
        elif msg.startswith('/stats'):
            target = extract_id(msg) if '[' in msg else uid
            if target:
                data = c.execute("SELECT warns, mute, role, nick, joined, messages FROM users WHERE user_id=? AND chat_id=?", (target, cid)).fetchone()
                if data:
                    muted = "НЕТ" if not data[1] else f"ДО {data[1][:16]}"
                    nick = data[3] if data[3] else "НЕТ"
                    send(peer, f"📊 **СТАТИСТИКА {get_name(target)}**\n━━━━━━━━━━━━━━━━━━━━\n⭐ Роль: {data[2]}\n🏷 Ник: {nick}\n⚠️ Варны: {data[0]}/3\n🔇 Мут: {muted}\n📨 Сообщений: {data[5]}\n📅 Присоединился: {data[4][:10] if data[4] else 'Неизвестно'}")
                else:
                    send(peer, f"📊 {get_name(target)}\n⚠️ Варны: 0/3")
            else:
                send(peer, "❌ /stats @user")
        
        elif msg == '/getid':
            send(peer, f"🆔 **ТВОЙ ID:** {uid}")
        
        elif msg == '/test' or msg == '/ping':
            send(peer, f"✅ **БОТ РАБОТАЕТ!**\n━━━━━━━━━━━━━━━━━━━━\n👤 Твой ID: {uid}\n💬 Чат: {cid if cid else 'ЛИЧНЫЕ СООБЩЕНИЯ'}\n🕐 Время: {datetime.now().strftime('%H:%M:%S')}")
        
        # ============= КОМАНДЫ ХЭЛПЕРОВ =============
        
        elif msg.startswith('/kick '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ХЭЛПЕР")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение правил"
                    kick_user(cid, target, uid, reason)
                else:
                    send(peer, "❌ /kick @user [причина]")
        
        elif msg.startswith('/mute '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ХЭЛПЕР")
            else:
                target = extract_id(msg)
                if target:
                    nums = re.findall(r'(\d+)', msg)
                    mins = int(nums[1]) if len(nums) > 1 else 30
                    reason = msg.split(' ', 3)[3] if len(msg.split(' ', 3)) > 3 else "Нарушение правил"
                    mute_user(cid, target, mins, uid, reason)
                else:
                    send(peer, "❌ /mute @user 30 [причина]")
        
        elif msg.startswith('/unmute '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ХЭЛПЕР")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET mute=NULL WHERE user_id=? AND chat_id=?", (target, cid))
                    conn.commit()
                    send(peer, f"🔊 {get_nick(target, cid)} РАЗМУЧЕН\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /unmute @user")
        
        elif msg.startswith('/warn '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ХЭЛПЕР")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение правил"
                    add_warn(cid, target, uid, reason)
                else:
                    send(peer, "❌ /warn @user [причина]")
        
        elif msg.startswith('/unwarn '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ХЭЛПЕР")
            else:
                target = extract_id(msg)
                if target:
                    w = c.execute("SELECT warns FROM users WHERE user_id=? AND chat_id=?", (target, cid)).fetchone()
                    if w and w[0] > 0:
                        c.execute("UPDATE users SET warns=warns-1 WHERE user_id=? AND chat_id=?", (target, cid))
                        conn.commit()
                        send(peer, f"✅ {get_nick(target, cid)} | ВАРН СНЯТ\n👮 {get_nick(uid, cid)}")
                    else:
                        send(peer, "❌ У ПОЛЬЗОВАТЕЛЯ НЕТ ВАРНОВ")
                else:
                    send(peer, "❌ /unwarn @user")
        
        elif msg.startswith('/clear '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ХЭЛПЕР")
            else:
                nums = re.findall(r'(\d+)', msg)
                count = int(nums[0]) if nums else 10
                if count > 100:
                    count = 100
                deleted = clear_chat_messages(peer, count)
                send(peer, f"✅ ОЧИЩЕНО {deleted} СООБЩЕНИЙ\n👮 {get_nick(uid, cid)}")
        
        elif msg == '/staff':
            if not cid:
                send(peer, "❌ КОМАНДА ТОЛЬКО В БЕСЕДАХ!")
            else:
                admins = c.execute("SELECT user_id, role FROM users WHERE chat_id=? AND role != 'user'", (cid,)).fetchall()
                if admins:
                    txt = "👥 **АДМИНИСТРАЦИЯ БЕСЕДЫ**\n━━━━━━━━━━━━━━━━━━━━\n"
                    for a in admins:
                        txt += f"{convert_role_name(a[1])}: {get_name(a[0])}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ НЕТ АДМИНИСТРАЦИИ В ЭТОЙ БЕСЕДЕ")
        
        elif msg.startswith('/setnick '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ХЭЛПЕР")
            else:
                target = extract_id(msg)
                if target:
                    nick = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else None
                    if nick:
                        set_nick(cid, target, uid, nick)
                    else:
                        send(peer, "❌ /setnick @user НИК")
                else:
                    send(peer, "❌ /setnick @user НИК")
        
        elif msg == '/nlist':
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ХЭЛПЕР")
            else:
                nicks = c.execute("SELECT user_id, nick FROM users WHERE chat_id=? AND nick IS NOT NULL", (cid,)).fetchall()
                if nicks:
                    txt = "🏷 **СПИСОК НИКОВ**\n━━━━━━━━━━━━━━━━━━━━\n"
                    for n in nicks[:20]:
                        txt += f"• {get_name(n[0])} → {n[1]}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ НЕТ НИКОВ В ЭТОЙ БЕСЕДЕ")
        
        elif msg == '/warnlist':
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ХЭЛПЕР")
            else:
                warned = c.execute("SELECT user_id, warns FROM users WHERE chat_id=? AND warns>0 ORDER BY warns DESC", (cid,)).fetchall()
                if warned:
                    txt = "⚠️ **ПОЛЬЗОВАТЕЛИ С ВАРНАМИ**\n━━━━━━━━━━━━━━━━━━━━\n"
                    for w in warned:
                        txt += f"• {get_name(w[0])} → {w[1]}/3\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ НЕТ ПОЛЬЗОВАТЕЛЕЙ С ВАРНАМИ")
        
        elif msg == '/mutelist':
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ХЭЛПЕР")
            else:
                now = datetime.now()
                muted = c.execute("SELECT user_id, mute FROM users WHERE chat_id=? AND mute IS NOT NULL", (cid,)).fetchall()
                active = []
                for m in muted:
                    try:
                        till = datetime.strptime(m[1], '%Y-%m-%d %H:%M:%S')
                        if till > now:
                            active.append((m[0], till))
                    except:
                        pass
                if active:
                    txt = "🔇 **АКТИВНЫЕ МУТЫ**\n━━━━━━━━━━━━━━━━━━━━\n"
                    for a in active:
                        left = a[1] - now
                        txt += f"• {get_name(a[0])} → {left.seconds//60} мин\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ НЕТ АКТИВНЫХ МУТОВ")
        
        # ============= КОМАНДЫ МОДЕРАТОРОВ =============
        
        elif msg.startswith('/ban '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: МОДЕРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение правил"
                    ban_user(cid, target, uid, reason)
                else:
                    send(peer, "❌ /ban @user [причина]")
        
        elif msg.startswith('/unban '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: МОДЕРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    unban_user(cid, target, uid)
                else:
                    send(peer, "❌ /unban @user")
        
        elif msg.startswith('/addmoder '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: МОДЕРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'moderator'))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ТЕПЕРЬ МОДЕРАТОР\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /addmoder @user")
        
        elif msg.startswith('/removerole '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: МОДЕРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET role='user' WHERE user_id=? AND chat_id=?", (target, cid))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | РОЛЬ ЗАБРАНА\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /removerole @user")
        
        elif msg == '/zov':
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: МОДЕРАТОР")
            else:
                users = get_chat_users(cid)
                mentions = []
                for u in users:
                    if u > 0 and u != uid:
                        mentions.append(f"[id{u}|{get_name(u)}]")
                if mentions:
                    for i in range(0, len(mentions), 10):
                        send(peer, ' '.join(mentions[i:i+10]))
                        time.sleep(0.5)
                else:
                    send(peer, "❌ НЕТ ПОЛЬЗОВАТЕЛЕЙ ДЛЯ УПОМИНАНИЯ")
        
        elif msg == '/banlist':
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: МОДЕРАТОР")
            else:
                bans = c.execute("SELECT user_id, reason, date FROM bans WHERE chat_id=?", (cid,)).fetchall()
                if bans:
                    txt = "🚫 **ЗАБАНЕННЫЕ ПОЛЬЗОВАТЕЛИ**\n━━━━━━━━━━━━━━━━━━━━\n"
                    for b in bans[:15]:
                        txt += f"• {get_name(b[0])} → {b[2][:10]}\n📝 {b[1][:30]}\n\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ НЕТ ЗАБАНЕННЫХ ПОЛЬЗОВАТЕЛЕЙ")
        
        elif msg.startswith('/inactivelist'):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: МОДЕРАТОР")
            else:
                days = int(re.findall(r'(\d+)', msg)[0]) if re.findall(r'(\d+)', msg) else 30
                threshold = datetime.now() - timedelta(days=days)
                inactive = c.execute("SELECT user_id FROM users WHERE chat_id=? AND last_active < ?", (cid, threshold.strftime('%Y-%m-%d %H:%M:%S'))).fetchall()
                if inactive:
                    txt = f"💤 **НЕАКТИВНЫЕ ({days} ДНЕЙ)**\n━━━━━━━━━━━━━━━━━━━━\n"
                    for i in inactive[:15]:
                        txt += f"• {get_name(i[0])}\n"
                    send(peer, txt)
                else:
                    send(peer, f"✅ НЕТ НЕАКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ ({days} ДНЕЙ)")
        
        # ============= КОМАНДЫ СТАРШИХ МОДЕРАТОРОВ =============
        
        elif msg == '/quiet':
            if not check_perm(uid, cid, 'seniormoderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ МОДЕРАТОР")
            else:
                current = c.execute("SELECT quiet_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET quiet_on=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"🔇 **РЕЖИМ ТИШИНЫ {'ВКЛЮЧЕН' if new_val else 'ВЫКЛЮЧЕН'}**\n👮 {get_nick(uid, cid)}")
        
        elif msg.startswith('/addsenmoder '):
            if not check_perm(uid, cid, 'seniormoderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ МОДЕРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'seniormoderator'))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ТЕПЕРЬ СТАРШИЙ МОДЕРАТОР\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /addsenmoder @user")
        
        elif msg.startswith('/bug '):
            if not check_perm(uid, cid, 'seniormoderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ МОДЕРАТОР")
            else:
                bug_text = msg[5:]
                send(OWNER_ID, f"🐛 **БАГ ОТ {get_name(uid)}**\n━━━━━━━━━━━━━━━━━━━━\n📝 {bug_text}\n📍 ЧАТ: {cid}\n👤 ID: {uid}")
                send(peer, f"✅ БАГ ОТПРАВЛЕН РАЗРАБОТЧИКАМ\n📝 {bug_text}")
        
        elif msg == '/rnickall':
            if not check_perm(uid, cid, 'seniormoderator'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ МОДЕРАТОР")
            else:
                c.execute("UPDATE users SET nick=NULL WHERE chat_id=?", (cid,))
                conn.commit()
                send(peer, f"✅ **ВСЕ НИКИ В БЕСЕДЕ СБРОШЕНЫ**\n👮 {get_nick(uid, cid)}")
        
        # ============= КОМАНДЫ АДМИНИСТРАТОРОВ =============
        
        elif msg.startswith('/addadmin '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'admin'))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ТЕПЕРЬ АДМИНИСТРАТОР\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /addadmin @user")
        
        elif msg == '/settings':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: АДМИНИСТРАТОР")
            else:
                chat = c.execute("SELECT filter_on, quiet_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                if chat:
                    send(peer, f"⚙️ **НАСТРОЙКИ БЕСЕДЫ**\n━━━━━━━━━━━━━━━━━━━━\n📝 ФИЛЬТР МАТА: {'✅ ВКЛЮЧЕН' if chat[0] else '❌ ВЫКЛЮЧЕН'}\n🔇 РЕЖИМ ТИШИНЫ: {'✅ ВКЛЮЧЕН' if chat[1] else '❌ ВЫКЛЮЧЕН'}\n━━━━━━━━━━━━━━━━━━━━\n/filter - вкл/выкл фильтр\n/quiet - вкл/выкл тишину")
                else:
                    send(peer, "⚙️ НАСТРОЙКИ БЕСЕДЫ\n/filter - фильтр мата\n/quiet - режим тишины")
        
        elif msg == '/filter':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: АДМИНИСТРАТОР")
            else:
                current = c.execute("SELECT filter_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET filter_on=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"📝 **ФИЛЬТР МАТА {'ВКЛЮЧЕН' if new_val else 'ВЫКЛЮЧЕН'}**\n👮 {get_nick(uid, cid)}")
        
        elif msg == '/serverinfo':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: АДМИНИСТРАТОР")
            else:
                users_count = len(get_chat_users(cid))
                registered = c.execute("SELECT COUNT(*) FROM users WHERE chat_id=?", (cid,)).fetchone()[0]
                banned = c.execute("SELECT COUNT(*) FROM bans WHERE chat_id=?", (cid,)).fetchone()[0]
                warned = c.execute("SELECT COUNT(*) FROM users WHERE chat_id=? AND warns>0", (cid,)).fetchone()[0]
                muted = c.execute("SELECT COUNT(*) FROM users WHERE chat_id=? AND mute IS NOT NULL", (cid,)).fetchone()[0]
                send(peer, f"📊 **ИНФОРМАЦИЯ О БЕСЕДЕ**\n━━━━━━━━━━━━━━━━━━━━\n🆔 ID БЕСЕДЫ: {cid}\n👥 ВСЕГО УЧАСТНИКОВ: {users_count}\n📝 ЗАРЕГИСТРИРОВАНО: {registered}\n⚠️ С ВАРНАМИ: {warned}\n🔇 ЗАМУЧЕНО: {muted}\n🚫 ЗАБАНЕНО: {banned}")
        
        elif msg == '/rkick':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: АДМИНИСТРАТОР")
            else:
                users = get_chat_users(cid)
                kicked = 0
                for u in users:
                    role = get_role(u, cid)
                    if role == 'user':
                        try:
                            vk.messages.removeChatUser(chat_id=cid, user_id=u)
                            kicked += 1
                            time.sleep(0.3)
                        except:
                            pass
                send(peer, f"✅ **КИКНУТО {kicked} НОВЫХ ПОЛЬЗОВАТЕЛЕЙ**\n👮 {get_nick(uid, cid)}")
        
        # ============= КОМАНДЫ СТАРШИХ АДМИНИСТРАТОРОВ =============
        
        elif msg.startswith('/type '):
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                nums = re.findall(r'(\d+)', msg)
                if nums:
                    t = int(nums[0])
                    c.execute("UPDATE chats SET chat_type=? WHERE chat_id=?", (t, cid))
                    conn.commit()
                    send(peer, f"✅ **ТИП БЕСЕДЫ ИЗМЕНЁН НА {t}**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /type 1-4")
        
        elif msg == '/leave':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                current = c.execute("SELECT leave_kick FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET leave_kick=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"🚪 **КИК ПРИ ВЫХОДЕ {'ВКЛЮЧЕН' if new_val else 'ВЫКЛЮЧЕН'}**\n👮 {get_nick(uid, cid)}")
        
        elif msg.startswith('/editowner '):
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET role='owner' WHERE user_id=? AND chat_id=?", (target, cid))
                    c.execute("UPDATE users SET role='user' WHERE user_id=? AND chat_id=?", (uid, cid))
                    conn.commit()
                    send(peer, f"👑 {get_name(target)} | ТЕПЕРЬ ВЛАДЕЛЕЦ БЕСЕДЫ\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /editowner @user")
        
        elif msg.startswith('/pin '):
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                text = msg[5:]
                if text:
                    msg_id = vk.messages.send(peer_id=peer, message=text, random_id=get_random_id())
                    vk.messages.pin(peer_id=peer, message_id=msg_id)
                    send(peer, f"✅ **СООБЩЕНИЕ ЗАКРЕПЛЕНО**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /pin ТЕКСТ")
        
        elif msg == '/unpin':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                vk.messages.unpin(peer_id=peer)
                send(peer, f"✅ **СООБЩЕНИЕ ОТКРЕПЛЕНО**\n👮 {get_nick(uid, cid)}")
        
        elif msg == '/rroleall':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                c.execute("UPDATE users SET role='user' WHERE chat_id=? AND role != 'owner'", (cid,))
                conn.commit()
                send(peer, f"✅ **ВСЕ РОЛИ В БЕСЕДЕ СБРОШЕНЫ**\n👮 {get_nick(uid, cid)}")
        
        elif msg.startswith('/addsenadm '):
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'senioradmin'))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ТЕПЕРЬ СТАРШИЙ АДМИНИСТРАТОР\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /addsenadm @user")
        
        elif msg == '/masskick':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                users = get_chat_users(cid)
                kicked = 0
                for u in users:
                    role = get_role(u, cid)
                    if role == 'user':
                        try:
                            vk.messages.removeChatUser(chat_id=cid, user_id=u)
                            kicked += 1
                            time.sleep(0.3)
                        except:
                            pass
                send(peer, f"✅ **КИКНУТО {kicked} ПОЛЬЗОВАТЕЛЕЙ БЕЗ РОЛИ**\n👮 {get_nick(uid, cid)}")
        
        elif msg == '/invite':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                current = c.execute("SELECT invite_moders FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET invite_moders=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"👥 **ПРИГЛАШЕНИЕ МОДЕРАМИ {'РАЗРЕШЕНО' if new_val else 'ЗАПРЕЩЕНО'}**\n👮 {get_nick(uid, cid)}")
        
        elif msg == '/antiflood':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                current = c.execute("SELECT antiflood FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET antiflood=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"🌊 **АНТИФЛУД {'ВКЛЮЧЕН' if new_val else 'ВЫКЛЮЧЕН'}**\n👮 {get_nick(uid, cid)}")
        
        elif msg.startswith('/welcometext '):
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СТАРШИЙ АДМИНИСТРАТОР")
            else:
                text = msg[13:]
                if text:
                    c.execute("UPDATE chats SET welcome_text=? WHERE chat_id=?", (text, cid))
                    conn.commit()
                    send(peer, f"👋 **ПРИВЕТСТВИЕ УСТАНОВЛЕНО**\n📝 {text}\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /welcometext ТЕКСТ")
        
        # ============= КОМАНДЫ СПЕЦ АДМИНИСТРАТОРОВ =============
        
        elif msg.startswith('/gban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СПЕЦ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Глобальное нарушение"
                    global_ban(target, uid, reason)
                    send(peer, f"🌐 {get_name(target)} | ГЛОБАЛЬНЫЙ БАН\n📝 {reason}\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /gban @user [причина]")
        
        elif msg.startswith('/gunban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СПЕЦ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    global_unban(target, uid)
                    send(peer, f"🌐 {get_name(target)} | ГЛОБАЛЬНЫЙ РАЗБАН\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /gunban @user")
        
        elif msg == '/gbanlist':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СПЕЦ АДМИНИСТРАТОР")
            else:
                bans = c.execute("SELECT user_id, reason, date FROM global_bans").fetchall()
                if bans:
                    txt = "🌐 **ГЛОБАЛЬНЫЕ БАНЫ**\n━━━━━━━━━━━━━━━━━━━━\n"
                    for b in bans:
                        txt += f"• {get_name(b[0])} → {b[2][:10]}\n📝 {b[1][:30]}\n\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ НЕТ ГЛОБАЛЬНЫХ БАНОВ")
        
        elif msg == '/banwords':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СПЕЦ АДМИНИСТРАТОР")
            else:
                words = c.execute("SELECT word FROM badwords").fetchall()
                if words:
                    txt = "🚫 **ЗАПРЕЩЕННЫЕ СЛОВА**\n━━━━━━━━━━━━━━━━━━━━\n"
                    txt += ', '.join([w[0] for w in words])
                    send(peer, txt)
                else:
                    send(peer, "✅ НЕТ ЗАПРЕЩЕННЫХ СЛОВ")
        
        elif msg.startswith('/addowner '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СПЕЦ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'owner'))
                    conn.commit()
                    send(peer, f"👑 {get_name(target)} | ТЕПЕРЬ ВЛАДЕЛЕЦ БЕСЕДЫ\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /addowner @user")
        
        elif msg.startswith('/skick '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СПЕЦ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    for chat in get_all_chats():
                        try:
                            vk.messages.removeChatUser(chat_id=chat, user_id=target)
                        except:
                            pass
                    send(peer, f"👢 {get_name(target)} | СУПЕР КИК (ИЗ ВСЕХ ЧАТОВ)\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /skick @user")
        
        elif msg.startswith('/sban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СПЕЦ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Супер бан"
                    global_ban(target, uid, reason)
                    send(peer, f"💀 {get_name(target)} | СУПЕР БАН\n📝 {reason}\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /sban @user [причина]")
        
        elif msg.startswith('/sunban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: СПЕЦ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    global_unban(target, uid)
                    send(peer, f"💀 {get_name(target)} | СУПЕР РАЗБАН\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /sunban @user")
        
        # ============= КОМАНДЫ ЗАМ.СПЕЦ АДМИНА =============
        
        elif msg.startswith('/addword '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СПЕЦ АДМИНА")
            else:
                word = msg[9:].lower()
                if word and len(word) > 0:
                    c.execute("INSERT OR IGNORE INTO badwords (word) VALUES (?)", (word,))
                    conn.commit()
                    send(peer, f"✅ **СЛОВО '{word}' ДОБАВЛЕНО В ФИЛЬТР**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /addword СЛОВО")
        
        elif msg.startswith('/delword '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СПЕЦ АДМИНА")
            else:
                word = msg[9:].lower()
                if word:
                    c.execute("DELETE FROM badwords WHERE word=?", (word,))
                    conn.commit()
                    send(peer, f"✅ **СЛОВО '{word}' УДАЛЕНО ИЗ ФИЛЬТРА**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /delword СЛОВО")
        
        elif msg.startswith('/pull '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СПЕЦ АДМИНА")
            else:
                name = msg[6:].strip()
                if name:
                    c.execute("INSERT OR REPLACE INTO pulls (name, chat_id) VALUES (?,?)", (name, cid))
                    conn.commit()
                    send(peer, f"✅ **ПРИВЯЗКА '{name}' СОЗДАНА**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /pull НАЗВАНИЕ")
        
        elif msg == '/pullinfo':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СПЕЦ АДМИНА")
            else:
                pulls = c.execute("SELECT name, chat_id FROM pulls").fetchall()
                if pulls:
                    txt = "📋 **СПИСОК ПРИВЯЗОК**\n━━━━━━━━━━━━━━━━━━━━\n"
                    for p in pulls:
                        txt += f"• {p[0]} → ЧАТ {p[1]}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ НЕТ ПРИВЯЗОК")
        
        elif msg.startswith('/delpull '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СПЕЦ АДМИНА")
            else:
                name = msg[9:].strip()
                if name:
                    c.execute("DELETE FROM pulls WHERE name=?", (name,))
                    conn.commit()
                    send(peer, f"✅ **ПРИВЯЗКА '{name}' УДАЛЕНА**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /delpull НАЗВАНИЕ")
        
        elif msg.startswith('/srnick '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СПЕЦ АДМИНА")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET nick=NULL WHERE user_id=?", (target,))
                    conn.commit()
                    send(peer, f"✅ **НИК {get_name(target)} СБРОШЕН ВЕЗДЕ**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /srnick @user")
        
        elif msg.startswith('/ssetnick '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СПЕЦ АДМИНА")
            else:
                target = extract_id(msg)
                if target:
                    parts = msg.split(' ', 2)
                    if len(parts) > 2:
                        nick = parts[2]
                        c.execute("UPDATE users SET nick=? WHERE user_id=?", (nick, target))
                        conn.commit()
                        send(peer, f"✅ **НИК {get_name(target)} УСТАНОВЛЕН ВЕЗДЕ: {nick}**\n👮 {get_nick(uid, cid)}")
                    else:
                        send(peer, "❌ /ssetnick @user НИК")
                else:
                    send(peer, "❌ /ssetnick @user НИК")
        
        elif msg.startswith('/srrole '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СПЕЦ АДМИНА")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET role='user' WHERE user_id=? AND chat_id!=-1", (target,))
                    conn.commit()
                    send(peer, f"✅ **РОЛЬ {get_name(target)} СБРОШЕНА ВЕЗДЕ**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /srrole @user")
        
        elif msg.startswith('/srole '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СПЕЦ АДМИНА")
            else:
                target = extract_id(msg)
                if target:
                    parts = msg.split(' ', 2)
                    if len(parts) > 2:
                        role = parts[2]
                        if role in ['helper', 'moderator', 'seniormoderator', 'admin', 'senioradmin']:
                            c.execute("UPDATE users SET role=? WHERE user_id=? AND chat_id!=-1", (role, target))
                            conn.commit()
                            send(peer, f"✅ **РОЛЬ '{role}' ВЫДАНА {get_name(target)} ВЕЗДЕ**\n👮 {get_nick(uid, cid)}")
                        else:
                            send(peer, "❌ ДОСТУПНЫЕ РОЛИ: helper, moderator, seniormoderator, admin, senioradmin")
                    else:
                        send(peer, "❌ /srole @user РОЛЬ")
                else:
                    send(peer, "❌ /srole @user РОЛЬ")
        
        elif msg.startswith('/szov '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СПЕЦ АДМИНА")
            else:
                text = msg[6:]
                if text:
                    send_to_all_chats(f"📢 **СУПЕР УПОМИНАНИЕ ОТ {get_name(uid)}**\n━━━━━━━━━━━━━━━━━━━━\n{text}")
                    send(peer, f"✅ **СООБЩЕНИЕ ОТПРАВЛЕНО ВО ВСЕ ЧАТЫ**\n📝 {text}\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /szov ТЕКСТ")
        
        # ============= КОМАНДЫ ВЛАДЕЛЬЦА БЕСЕДЫ =============
        
        elif msg.startswith('/gremoverole '):
            if not check_perm(uid, cid, 'owner'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ВЛАДЕЛЕЦ БЕСЕДЫ")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET role='user' WHERE user_id=? AND chat_id=?", (target, cid))
                    conn.commit()
                    send(peer, f"✅ **ВСЕ РОЛИ {get_name(target)} СБРОШЕНЫ**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /gremoverole @user")
        
        elif msg.startswith('/news '):
            if not check_perm(uid, cid, 'owner'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ВЛАДЕЛЕЦ БЕСЕДЫ")
            else:
                news_text = msg[6:]
                if news_text:
                    send_to_all_chats(f"📢 **НОВОСТИ ОТ АДМИНИСТРАЦИИ**\n━━━━━━━━━━━━━━━━━━━━\n{news_text}\n━━━━━━━━━━━━━━━━━━━━\n👮 ОТ: {get_name(uid)}")
                    send(peer, f"✅ **НОВОСТИ ОТПРАВЛЕНЫ ВО ВСЕ ЧАТЫ**\n📝 {news_text}")
                else:
                    send(peer, "❌ /news ТЕКСТ")
        
        elif msg.startswith('/addzam '):
            if not check_perm(uid, cid, 'owner'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ВЛАДЕЛЕЦ БЕСЕДЫ")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, -1, 'zamglav'))
                    conn.commit()
                    send(peer, f"⚜️ {get_name(target)} | ТЕПЕРЬ ЗАМ.СОЗДАТЕЛЯ\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /addzam @user")
        
        # ============= КОМАНДЫ ЗАМ.СОЗДАТЕЛЯ =============
        
        elif msg.startswith('/banid '):
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СОЗДАТЕЛЯ")
            else:
                nums = re.findall(r'(\d+)', msg)
                if nums:
                    target_chat = int(nums[0])
                    c.execute("UPDATE chats SET activated=0 WHERE chat_id=?", (target_chat,))
                    conn.commit()
                    send(peer, f"🚫 **ЧАТ {target_chat} ЗАБЛОКИРОВАН**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /banid ID_ЧАТА")
        
        elif msg.startswith('/unbanid '):
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СОЗДАТЕЛЯ")
            else:
                nums = re.findall(r'(\d+)', msg)
                if nums:
                    target_chat = int(nums[0])
                    c.execute("UPDATE chats SET activated=1 WHERE chat_id=?", (target_chat,))
                    conn.commit()
                    send(peer, f"✅ **ЧАТ {target_chat} РАЗБЛОКИРОВАН**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /unbanid ID_ЧАТА")
        
        elif msg.startswith('/clearchat '):
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СОЗДАТЕЛЯ")
            else:
                nums = re.findall(r'(\d+)', msg)
                if nums:
                    target_chat = int(nums[0])
                    c.execute("DELETE FROM chats WHERE chat_id=?", (target_chat,))
                    c.execute("DELETE FROM users WHERE chat_id=?", (target_chat,))
                    c.execute("DELETE FROM bans WHERE chat_id=?", (target_chat,))
                    conn.commit()
                    send(peer, f"🗑 **ЧАТ {target_chat} УДАЛЁН ИЗ БД**\n👮 {get_nick(uid, cid)}")
                else:
                    send(peer, "❌ /clearchat ID_ЧАТА")
        
        elif msg.startswith('/infoid '):
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СОЗДАТЕЛЯ")
            else:
                target = extract_id(msg)
                if target:
                    data = c.execute("SELECT role, warns, last_active, messages FROM users WHERE user_id=? AND chat_id!=-1", (target,)).fetchone()
                    if data:
                        send(peer, f"📊 **ИНФОРМАЦИЯ О {get_name(target)}**\n━━━━━━━━━━━━━━━━━━━━\n⭐ ГЛОБАЛЬНАЯ РОЛЬ: {data[0]}\n⚠️ ВСЕГО ВАРНОВ: {data[1]}\n📨 ВСЕГО СООБЩЕНИЙ: {data[3]}\n📅 ПОСЛЕДНЯЯ АКТИВНОСТЬ: {data[2][:16] if data[2] else 'НЕИЗВЕСТНО'}")
                    else:
                        send(peer, f"📊 НЕТ ДАННЫХ О {get_name(target)}")
                else:
                    send(peer, "❌ /infoid @user")
        
        elif msg == '/listchats':
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СОЗДАТЕЛЯ")
            else:
                chats = c.execute("SELECT chat_id, activated FROM chats").fetchall()
                if chats:
                    txt = "📋 **СПИСОК ЧАТОВ**\n━━━━━━━━━━━━━━━━━━━━\n"
                    for ch in chats[:20]:
                        txt += f"• {ch[0]} - {'✅ АКТИВЕН' if ch[1] else '❌ ЗАБЛОКИРОВАН'}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ НЕТ ЧАТОВ В БАЗЕ ДАННЫХ")
        
        elif msg == '/server':
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ НЕТ ПРАВ! Требуется роль: ЗАМ.СОЗДАТЕЛЯ")
            else:
                total_chats = len(get_all_chats())
                total_users = c.execute("SELECT COUNT(DISTINCT user_id) FROM users WHERE chat_id!=-1").fetchone()[0]
                total_bans = c.execute("SELECT COUNT(*) FROM global_bans").fetchone()[0]
                total_messages = c.execute("SELECT SUM(messages) FROM users WHERE chat_id!=-1").fetchone()[0] or 0
                send(peer, f"🖥️ **ИНФОРМАЦИЯ О СЕРВЕРЕ**\n━━━━━━━━━━━━━━━━━━━━\n📊 АКТИВНЫХ ЧАТОВ: {total_chats}\n👥 ВСЕГО ПОЛЬЗОВАТЕЛЕЙ: {total_users}\n🌐 ГЛОБАЛЬНЫХ БАНОВ: {total_bans}\n📨 ВСЕГО СООБЩЕНИЙ: {total_messages}")
        
        # ============= КОМАНДЫ СОЗДАТЕЛЯ БОТА =============
        
        elif uid == OWNER_ID:
            if msg.startswith('/adddev '):
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, -1, 'glav'))
                    conn.commit()
                    send(peer, f"👑 {get_name(target)} | ТЕПЕРЬ СОЗДАТЕЛЬ БОТА")
                else:
                    send(peer, "❌ /adddev @user")
            
            elif msg.startswith('/addbug '):
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR IGNORE INTO bug_receivers (user_id) VALUES (?)", (target,))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ДОБАВЛЕН В ПОЛУЧАТЕЛИ БАГОВ")
                else:
                    send(peer, "❌ /addbug @user")
            
            elif msg.startswith('/delbug '):
                target = extract_id(msg)
                if target:
                    c.execute("DELETE FROM bug_receivers WHERE user_id=?", (target,))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | УДАЛЁН ИЗ ПОЛУЧАТЕЛЕЙ БАГОВ")
                else:
                    send(peer, "❌ /delbug @user")
            
            elif msg == '/sync':
                conn.commit()
                send(peer, "✅ **БАЗА ДАННЫХ СИНХРОНИЗИРОВАНА**")
        
        # ============= АКТИВАЦИЯ БОТА =============
        
        elif msg == '/start' and cid and uid == OWNER_ID:
            c.execute("UPDATE chats SET activated=1 WHERE chat_id=?", (cid,))
            conn.commit()
            send(peer, "✅ **БОТ АКТИВИРОВАН В ЭТОЙ БЕСЕДЕ!**\n📋 Напиши /help для списка всех команд")
        
        elif msg == '/start' and cid and uid != OWNER_ID:
            send(peer, "❌ **ТОЛЬКО ВЛАДЕЛЕЦ БОТА МОЖЕТ АКТИВИРОВАТЬ ЕГО!**")
        
        # ============= ОТВЕТ В ЛИЧНЫХ СООБЩЕНИЯХ =============
        
        elif not cid and msg and not msg.startswith('/'):
            send(peer, f"🤖 **BLACK FIB BOT v4.0**\n━━━━━━━━━━━━━━━━━━━━\n👤 ТВОЙ ID: {uid}\n📋 КОМАНДЫ: /help\n👑 ВЛАДЕЛЕЦ: Дмитрий")

print("Бот остановлен")
