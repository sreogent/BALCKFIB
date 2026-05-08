import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
import sqlite3
from datetime import datetime, timedelta
import re
import time
import threading

# ============= КОНФИГ =============
TOKEN = 'vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg'
GROUP_ID = 229320501
OWNER_ID = 631833072

# База данных
conn = sqlite3.connect('blackfib_bot.db', check_same_thread=False)
c = conn.cursor()

# ============= СОЗДАНИЕ ВСЕХ ТАБЛИЦ =============
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
    active INTEGER DEFAULT 0,
    chat_type TEXT DEFAULT 'players',
    filter_on INTEGER DEFAULT 1,
    quiet_on INTEGER DEFAULT 0,
    welcome_text TEXT,
    welcome_on INTEGER DEFAULT 0
)''')

c.execute('''CREATE TABLE IF NOT EXISTS badwords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE
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

c.execute('''CREATE TABLE IF NOT EXISTS bug_receivers (
    user_id INTEGER PRIMARY KEY
)''')

# Добавляем маты
bad_words = ['сука', 'блядь', 'хуй', 'пизда', 'ебать', 'жопа', 'пидор', 'мудак', 'уебан', 'долбоеб', 'хер', 'нахер', 'идиот', 'дебил', 'тупой', 'гандон', 'шлюха', 'еблан', 'лох', 'редиска']
for w in bad_words:
    c.execute("INSERT OR IGNORE INTO badwords (word) VALUES (?)", (w,))
conn.commit()

# Добавляем владельца
c.execute("INSERT OR IGNORE INTO users (user_id, chat_id, role) VALUES (?, ?, ?)", (OWNER_ID, -1, 'glav'))
conn.commit()

print("=" * 50)
print("🤖 BLACK FIB BOT v3.0")
print("👑 Владелец: Дмитрий")
print("✅ База данных готова")
print("=" * 50)

# Подключение к ВК
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =============

def send(peer, text, kb=None):
    try:
        vk.messages.send(
            peer_id=peer,
            message=text,
            random_id=get_random_id(),
            keyboard=kb.get_keyboard() if kb else None
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_name(uid):
    try:
        u = vk.users.get(user_ids=uid)[0]
        return f"{u['first_name']} {u['last_name']}"
    except:
        return f"id{uid}"

def get_role(uid, cid):
    r = c.execute("SELECT role FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    if r:
        return r[0]
    if uid == OWNER_ID:
        return 'glav'
    return 'user'

def check_perm(uid, cid, need):
    if uid == OWNER_ID:
        return True
    role = get_role(uid, cid)
    lvl = {'user':0, 'moderator':1, 'seniormoderator':2, 'admin':3, 'senioradmin':4, 'owner':5, 'zamglav':6, 'glav':7}
    return lvl.get(role, 0) >= lvl.get(need, 0)

def is_muted(uid, cid):
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
    r = c.execute("SELECT ban FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    return r and r[0] == 1

def is_global_banned(uid):
    r = c.execute("SELECT * FROM global_bans WHERE user_id=?", (uid,)).fetchone()
    return r is not None

def register_user(uid, cid):
    c.execute("INSERT OR IGNORE INTO users (user_id, chat_id, joined, last_active) VALUES (?, ?, ?, ?)",
              (uid, cid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def get_chat_users(cid):
    try:
        chat = vk.messages.getConversationMembers(peer_id=2000000000 + cid)
        return [m['member_id'] for m in chat['items'] if m['member_id'] > 0]
    except:
        return []

# ============= КРАСИВЫЕ КЛАВИАТУРЫ =============

def main_kb(role):
    kb = VkKeyboard(one_time=False)
    kb.add_button("📊 СТАТИСТИКА", VkKeyboardColor.PRIMARY)
    kb.add_button("ℹ️ ИНФО", VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("👥 АДМИНЫ", VkKeyboardColor.PRIMARY)
    kb.add_button("📜 ПРАВИЛА", VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("🆔 GETID", VkKeyboardColor.PRIMARY)
    kb.add_button("🧪 ТЕСТ", VkKeyboardColor.SECONDARY)
    
    if role in ['moderator', 'seniormoderator', 'admin', 'senioradmin', 'owner', 'zamglav', 'glav']:
        kb.add_line()
        kb.add_button("🛡 МОДЕРАЦИЯ", VkKeyboardColor.NEGATIVE)
    
    if role in ['admin', 'senioradmin', 'owner', 'zamglav', 'glav']:
        kb.add_line()
        kb.add_button("⚙️ НАСТРОЙКИ", VkKeyboardColor.PRIMARY)
    
    if role in ['owner', 'zamglav', 'glav']:
        kb.add_line()
        kb.add_button("👑 ГЛОБАЛКА", VkKeyboardColor.NEGATIVE)
    
    return kb

def moder_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button("🔇 МУТ", VkKeyboardColor.NEGATIVE)
    kb.add_button("🔊 РАЗМУТ", VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("⚠️ ВАРН", VkKeyboardColor.NEGATIVE)
    kb.add_button("✅ СНЯТЬ ВАРН", VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("👢 КИК", VkKeyboardColor.NEGATIVE)
    kb.add_button("🚫 БАН", VkKeyboardColor.NEGATIVE)
    kb.add_line()
    kb.add_button("📋 ВАРНЫ", VkKeyboardColor.PRIMARY)
    kb.add_button("🔇 МУТЫ", VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("📜 ИСТОРИЯ", VkKeyboardColor.PRIMARY)
    kb.add_button("🏷 NICK", VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🔙 НАЗАД", VkKeyboardColor.SECONDARY)
    return kb

def admin_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button("➕ МОДЕРАТОР", VkKeyboardColor.POSITIVE)
    kb.add_button("➕ СТ.МОДЕР", VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("➕ АДМИН", VkKeyboardColor.POSITIVE)
    kb.add_button("➕ СТ.АДМИН", VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("➖ ЗАБРАТЬ РОЛЬ", VkKeyboardColor.NEGATIVE)
    kb.add_button("📝 ФИЛЬТР", VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🔇 ТИШИНА", VkKeyboardColor.PRIMARY)
    kb.add_button("🏷 NICKALL", VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🐛 БАГ", VkKeyboardColor.NEGATIVE)
    kb.add_button("📊 СЕРВЕР", VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🔙 НАЗАД", VkKeyboardColor.SECONDARY)
    return kb

def global_kb():
    kb = VkKeyboard(one_time=False)
    kb.add_button("🌐 ГЛОБАЛ БАН", VkKeyboardColor.NEGATIVE)
    kb.add_button("🌐 ГЛОБАЛ АНБАН", VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("📋 ГЛОБАЛ БАНЫ", VkKeyboardColor.PRIMARY)
    kb.add_button("➕ ЗАМ.ГЛАВЫ", VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("🗑 ОЧИСТИТЬ ЧАТ", VkKeyboardColor.NEGATIVE)
    kb.add_button("📢 НОВОСТИ", VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🔙 НАЗАД", VkKeyboardColor.SECONDARY)
    return kb

# ============= ОСНОВНЫЕ ДЕЙСТВИЯ =============

def add_warn(cid, uid, admin, reason):
    w = c.execute("SELECT warns FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    warns = (w[0] if w else 0) + 1
    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, warns) VALUES (?,?,?)", (uid, cid, warns))
    c.execute("INSERT INTO warn_history (user_id, chat_id, admin_id, reason, date) VALUES (?,?,?,?,?)",
              (uid, cid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    send(2000000000 + cid, f"⚠️ {get_name(uid)} | ВАРН {warns}/3\n📝 {reason}\n👮 {get_name(admin)}")
    if warns >= 3:
        c.execute("UPDATE users SET ban=1 WHERE user_id=? AND chat_id=?", (uid, cid))
        conn.commit()
        try:
            vk.messages.removeChatUser(chat_id=cid, user_id=uid)
            send(2000000000 + cid, f"🚫 {get_name(uid)} ЗАБАНЕН (3/3 варнов)")
        except:
            pass

def mute_user(cid, uid, minutes, admin, reason):
    till = datetime.now() + timedelta(minutes=minutes)
    c.execute("UPDATE users SET mute=? WHERE user_id=? AND chat_id=?", (till.strftime('%Y-%m-%d %H:%M:%S'), uid, cid))
    conn.commit()
    send(2000000000 + cid, f"🔇 {get_name(uid)} | МУТ {minutes} мин\n📝 {reason}\n👮 {get_name(admin)}")

def kick_user(cid, uid, admin, reason):
    try:
        vk.messages.removeChatUser(chat_id=cid, user_id=uid)
        send(2000000000 + cid, f"👢 {get_name(uid)} | КИК\n📝 {reason}\n👮 {get_name(admin)}")
    except:
        pass

def ban_user(cid, uid, admin, reason):
    c.execute("UPDATE users SET ban=1 WHERE user_id=? AND chat_id=?", (uid, cid))
    c.execute("INSERT INTO bans (user_id, chat_id, admin_id, reason, date) VALUES (?,?,?,?,?)",
              (uid, cid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    try:
        vk.messages.removeChatUser(chat_id=cid, user_id=uid)
        send(2000000000 + cid, f"🚫 {get_name(uid)} | БАН\n📝 {reason}\n👮 {get_name(admin)}")
    except:
        pass

def set_nick(cid, uid, admin, nick):
    c.execute("UPDATE users SET nick=? WHERE user_id=? AND chat_id=?", (nick, uid, cid))
    conn.commit()
    send(2000000000 + cid, f"🏷 {get_name(uid)} | НИК: {nick}\n👮 {get_name(admin)}")

# ============= ГЛАВНЫЙ ЦИКЛ =============

print("🤖 БОТ ЗАПУЩЕН И ЖДЁТ СООБЩЕНИЙ!")
print("💬 НАПИШИТЕ /menu В ЛС ИЛИ БЕСЕДЕ")
print("=" * 50)

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        uid = event.user_id
        msg = event.text or ""
        
        if event.from_chat:
            cid = event.chat_id
            peer = 2000000000 + cid
        else:
            cid = 0
            peer = uid
        
        # Регистрация
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
            
            # Фильтр мата
            if not msg.startswith('/'):
                filter_on = c.execute("SELECT filter_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                if not filter_on or filter_on[0] == 1:
                    bad = c.execute("SELECT word FROM badwords").fetchall()
                    for w in bad:
                        if w[0].lower() in msg.lower():
                            try:
                                vk.messages.delete(message_ids=[event.message_id], delete_for_all=1)
                            except:
                                pass
                            add_warn(cid, uid, 0, f"Мат: {w[0]}")
                            break
        
        # ============= ОБРАБОТКА КОМАНД =============
        
        # ГЛАВНОЕ МЕНЮ
        if msg == '/menu':
            role = get_role(uid, cid)
            send(peer, "🏠 ГЛАВНОЕ МЕНЮ", main_kb(role))
        
        # СТАТИСТИКА
        elif msg == '📊 СТАТИСТИКА' or msg.startswith('/stats'):
            target = uid
            if '[' in msg:
                ids = re.findall(r'id(\d+)', msg)
                if ids:
                    target = int(ids[0])
            data = c.execute("SELECT warns, mute, role, nick, joined, messages FROM users WHERE user_id=? AND chat_id=?", (target, cid)).fetchone()
            if data:
                muted = "НЕТ" if not data[1] else f"ДО {data[1][:16]}"
                nick = data[3] if data[3] else "НЕТ"
                send(peer, f"📊 СТАТИСТИКА {get_name(target)}\n"
                           f"━━━━━━━━━━━━━━━━━━━━\n"
                           f"⭐ РОЛЬ: {data[2]}\n"
                           f"🏷 НИК: {nick}\n"
                           f"⚠️ ВАРНЫ: {data[0]}/3\n"
                           f"🔇 МУТ: {muted}\n"
                           f"📨 СООБЩЕНИЙ: {data[5]}\n"
                           f"📅 ПРИСОЕДИНИЛСЯ: {data[4][:10] if data[4] else '???'}")
            else:
                send(peer, f"📊 {get_name(target)}\n⚠️ ВАРНЫ: 0/3")
        
        # ИНФО
        elif msg == 'ℹ️ ИНФО' or msg == '/info':
            send(peer, "🤖 BLACK FIB BOT v3.0\n━━━━━━━━━━━━━━━━━━━━\n👑 DMITRIY\n📅 2024-2025\n💬 /menu - ГЛАВНОЕ МЕНЮ\n📢 @blackfib")
        
        # АДМИНЫ
        elif msg == '👥 АДМИНЫ' or msg == '/staff':
            if not cid:
                send(peer, "❌ ТОЛЬКО В БЕСЕДЕ")
            else:
                admins = c.execute("SELECT user_id, role FROM users WHERE chat_id=? AND role IN ('moderator','seniormoderator','admin','senioradmin','owner','zamglav','glav')", (cid,)).fetchall()
                if admins:
                    txt = "👥 АДМИНИСТРАЦИЯ:\n━━━━━━━━━━━━━━━━━━━━\n"
                    r_ru = {'moderator':'🟢 МОДЕРАТОР', 'seniormoderator':'🟡 СТ.МОДЕРАТОР', 'admin':'🟠 АДМИН', 'senioradmin':'🔴 СТ.АДМИН', 'owner':'👑 ВЛАДЕЛЕЦ', 'zamglav':'⚜️ ЗАМ.ГЛАВЫ', 'glav':'👑 ГЛАВА'}
                    for a in admins:
                        txt += f"{r_ru.get(a[1], a[1])}: {get_name(a[0])}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ НЕТ АДМИНОВ")
        
        # ПРАВИЛА
        elif msg == '📜 ПРАВИЛА' or msg == '/rules':
            send(peer, "📜 ПРАВИЛА:\n━━━━━━━━━━━━━━━━━━━━\n1️⃣ МАТ → ВАРН\n2️⃣ ОСКОРБЛЕНИЯ → МУТ/БАН\n3️⃣ ФЛУД → ПРЕДУПРЕЖДЕНИЕ\n4️⃣ РЕКЛАМА → БАН\n5️⃣ НЕАДЕКВАТ → МУТ\n━━━━━━━━━━━━━━━━━━━━\n⚠️ 3 ВАРНА = БАН")
        
        # GETID
        elif msg == '🆔 GETID' or msg.startswith('/getid'):
            target = uid
            if '[' in msg:
                ids = re.findall(r'id(\d+)', msg)
                if ids:
                    target = int(ids[0])
            send(peer, f"🆔 ID: {target}")
        
        # ТЕСТ
        elif msg == '🧪 ТЕСТ' or msg == '/test':
            send(peer, f"✅ БОТ РАБОТАЕТ!\n👤 ТВОЙ ID: {uid}\n💬 ЧАТ ID: {cid if cid else 'ЛС'}")
        
        # МОДЕРАЦИЯ
        elif msg == '🛡 МОДЕРАЦИЯ' or msg == '/moder':
            if check_perm(uid, cid, 'moderator'):
                send(peer, "🛡 МЕНЮ МОДЕРАЦИИ", moder_kb())
            else:
                send(peer, "❌ НЕТ ПРАВ")
        
        # НАСТРОЙКИ
        elif msg == '⚙️ НАСТРОЙКИ' or msg == '/settings':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ")
            else:
                chat = c.execute("SELECT filter_on, quiet_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                filter_st = "✅ ВКЛ" if (chat and chat[0] == 1) else "❌ ВЫКЛ"
                quiet_st = "✅ ВКЛ" if (chat and chat[1] == 1) else "❌ ВЫКЛ"
                send(peer, f"⚙️ НАСТРОЙКИ БЕСЕДЫ\n━━━━━━━━━━━━━━━━━━━━\n📝 ФИЛЬТР МАТА: {filter_st}\n🔇 РЕЖИМ ТИШИНЫ: {quiet_st}\n\n/filter - ВКЛ/ВЫКЛ ФИЛЬТР\n/quiet - ВКЛ/ВЫКЛ ТИШИНУ")
        
        # ГЛОБАЛКА
        elif msg == '👑 ГЛОБАЛКА' or msg == '/global':
            if check_perm(uid, cid, 'owner'):
                send(peer, "👑 ГЛОБАЛЬНОЕ МЕНЮ", global_kb())
            else:
                send(peer, "❌ НЕТ ПРАВ")
        
        # НАЗАД
        elif msg == '🔙 НАЗАД':
            role = get_role(uid, cid)
            send(peer, "🏠 ГЛАВНОЕ МЕНЮ", main_kb(role))
        
        # ============= МОДЕРАТОРСКИЕ КОМАНДЫ =============
        
        elif msg == '🔇 МУТ' or msg.startswith('/mute '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ")
            else:
                ids = re.findall(r'id(\d+)', msg)
                if ids:
                    target = int(ids[0])
                    nums = re.findall(r'(\d+)', msg)
                    mins = int(nums[1]) if len(nums) > 1 else 5
                    reason = msg.split(' ', 3)[3] if len(msg.split(' ', 3)) > 3 else "Нарушение"
                    mute_user(cid, target, mins, uid, reason)
                else:
                    send(peer, "❌ /mute @user 5 [ПРИЧИНА]")
        
        elif msg == '🔊 РАЗМУТ' or msg.startswith('/unmute '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ")
            else:
                ids = re.findall(r'id(\d+)', msg)
                if ids:
                    target = int(ids[0])
                    c.execute("UPDATE users SET mute=NULL WHERE user_id=? AND chat_id=?", (target, cid))
                    conn.commit()
                    send(peer, f"🔊 {get_name(target)} РАЗМУЧЕН")
                else:
                    send(peer, "❌ /unmute @user")
        
        elif msg == '⚠️ ВАРН' or msg.startswith('/warn '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ")
            else:
                ids = re.findall(r'id(\d+)', msg)
                if ids:
                    target = int(ids[0])
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение"
                    add_warn(cid, target, uid, reason)
                else:
                    send(peer, "❌ /warn @user [ПРИЧИНА]")
        
        elif msg == '✅ СНЯТЬ ВАРН' or msg.startswith('/unwarn '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ")
            else:
                ids = re.findall(r'id(\d+)', msg)
                if ids:
                    target = int(ids[0])
                    w = c.execute("SELECT warns FROM users WHERE user_id=? AND chat_id=?", (target, cid)).fetchone()
                    if w and w[0] > 0:
                        c.execute("UPDATE users SET warns=warns-1 WHERE user_id=? AND chat_id=?", (target, cid))
                        conn.commit()
                        send(peer, f"✅ {get_name(target)} | ВАРН СНЯТ")
                    else:
                        send(peer, "❌ НЕТ ВАРНОВ")
                else:
                    send(peer, "❌ /unwarn @user")
        
        elif msg == '👢 КИК' or msg.startswith('/kick '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ")
            else:
                ids = re.findall(r'id(\d+)', msg)
                if ids:
                    target = int(ids[0])
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение"
                    kick_user(cid, target, uid, reason)
                else:
                    send(peer, "❌ /kick @user [ПРИЧИНА]")
        
        elif msg == '🚫 БАН' or msg.startswith('/ban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ")
            else:
                ids = re.findall(r'id(\d+)', msg)
                if ids:
                    target = int(ids[0])
