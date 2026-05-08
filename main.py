import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
import sqlite3
from datetime import datetime, timedelta
import re
import time

# ============= КОНФИГ =============
TOKEN = 'vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg'
GROUP_ID = 229320501
OWNER_ID = 631833072

# База данных
conn = sqlite3.connect('blackfib_bot.db', check_same_thread=False)
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
    active INTEGER DEFAULT 0,
    chat_type INTEGER DEFAULT 1,
    filter_on INTEGER DEFAULT 1,
    quiet_on INTEGER DEFAULT 0,
    leave_kick INTEGER DEFAULT 0,
    antiflood INTEGER DEFAULT 0,
    welcome_text TEXT,
    welcome_on INTEGER DEFAULT 0,
    pinned_msg INTEGER DEFAULT 0
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

c.execute('''CREATE TABLE IF NOT EXISTS bug_receivers (
    user_id INTEGER PRIMARY KEY
)''')

c.execute('''CREATE TABLE IF NOT EXISTS pulls (
    name TEXT PRIMARY KEY,
    chat_id INTEGER
)''')

# Добавляем маты
bad_words = ['сука', 'блядь', 'хуй', 'пизда', 'ебать', 'жопа', 'пидор', 'мудак', 'уебан', 'долбоеб', 'хер', 'нахер', 'идиот', 'дебил', 'тупой', 'гандон', 'шлюха', 'еблан', 'лох', 'редиска']
for w in bad_words:
    c.execute("INSERT OR IGNORE INTO badwords (word) VALUES (?)", (w,))

# Добавляем владельца
c.execute("INSERT OR IGNORE INTO users (user_id, chat_id, role) VALUES (?, ?, ?)", (OWNER_ID, -1, 'glav'))
conn.commit()

print("=" * 50)
print("🤖 BLACK FIB BOT v4.0 - ПОЛНАЯ ВЕРСИЯ")
print("👑 Владелец: Дмитрий")
print("✅ Все таблицы созданы")
print("=" * 50)

# Подключение к ВК
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =============

def send(peer, text, kb=None):
    try:
        vk.messages.send(peer_id=peer, message=text, random_id=get_random_id(), keyboard=kb.get_keyboard() if kb else None)
    except Exception as e:
        print(f"Ошибка: {e}")

def get_name(uid):
    try:
        u = vk.users.get(user_ids=uid)[0]
        return f"{u['first_name']} {u['last_name']}"
    except:
        return f"id{uid}"

def get_role(uid, cid):
    if uid == OWNER_ID:
        return 'glav'
    r = c.execute("SELECT role FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    return r[0] if r else 'user'

def get_role_level(role):
    levels = {
        'user': 0, 'helper': 1, 'moderator': 2, 'seniormoderator': 3,
        'admin': 4, 'senioradmin': 5, 'owner': 6, 'zamglav': 7, 'glav': 8
    }
    return levels.get(role, 0)

def check_perm(uid, cid, need):
    if uid == OWNER_ID:
        return True
    return get_role_level(get_role(uid, cid)) >= get_role_level(need)

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

def get_user_nick(uid, cid):
    r = c.execute("SELECT nick FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    return r[0] if r and r[0] else get_name(uid)

def extract_id(text):
    ids = re.findall(r'id(\d+)', text)
    if ids:
        return int(ids[0])
    nums = re.findall(r'(\d+)', text)
    return int(nums[0]) if nums else None

def get_all_chats():
    return [row[0] for row in c.execute("SELECT chat_id FROM chats WHERE active=1").fetchall()]

# ============= ОСНОВНЫЕ ДЕЙСТВИЯ =============

def add_warn(cid, uid, admin, reason):
    w = c.execute("SELECT warns FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    warns = (w[0] if w else 0) + 1
    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, warns) VALUES (?,?,?)", (uid, cid, warns))
    c.execute("INSERT INTO warn_history (user_id, chat_id, admin_id, reason, date) VALUES (?,?,?,?,?)",
              (uid, cid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    send(2000000000 + cid, f"⚠️ {get_user_nick(uid, cid)} | ВАРН {warns}/3\n📝 {reason}\n👮 {get_user_nick(admin, cid)}")
    if warns >= 3:
        c.execute("UPDATE users SET ban=1 WHERE user_id=? AND chat_id=?", (uid, cid))
        conn.commit()
        try:
            vk.messages.removeChatUser(chat_id=cid, user_id=uid)
            send(2000000000 + cid, f"🚫 {get_user_nick(uid, cid)} ЗАБАНЕН (3/3 варнов)")
        except:
            pass

def mute_user(cid, uid, minutes, admin, reason):
    till = datetime.now() + timedelta(minutes=minutes)
    c.execute("UPDATE users SET mute=? WHERE user_id=? AND chat_id=?", (till.strftime('%Y-%m-%d %H:%M:%S'), uid, cid))
    conn.commit()
    send(2000000000 + cid, f"🔇 {get_user_nick(uid, cid)} | МУТ {minutes} мин\n📝 {reason}\n👮 {get_user_nick(admin, cid)}")

def kick_user(cid, uid, admin, reason):
    try:
        vk.messages.removeChatUser(chat_id=cid, user_id=uid)
        send(2000000000 + cid, f"👢 {get_user_nick(uid, cid)} | КИК\n📝 {reason}\n👮 {get_user_nick(admin, cid)}")
    except:
        pass

def ban_user(cid, uid, admin, reason):
    c.execute("UPDATE users SET ban=1 WHERE user_id=? AND chat_id=?", (uid, cid))
    c.execute("INSERT INTO bans (user_id, chat_id, admin_id, reason, date) VALUES (?,?,?,?,?)",
              (uid, cid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    try:
        vk.messages.removeChatUser(chat_id=cid, user_id=uid)
        send(2000000000 + cid, f"🚫 {get_user_nick(uid, cid)} | БАН\n📝 {reason}\n👮 {get_user_nick(admin, cid)}")
    except:
        pass

def unban_user(cid, uid, admin):
    c.execute("UPDATE users SET ban=0 WHERE user_id=? AND chat_id=?", (uid, cid))
    c.execute("DELETE FROM bans WHERE user_id=? AND chat_id=?", (uid, cid))
    conn.commit()
    send(2000000000 + cid, f"✅ {get_user_nick(uid, cid)} | РАЗБАНЕН\n👮 {get_user_nick(admin, cid)}")

def set_nick(cid, uid, admin, nick):
    c.execute("UPDATE users SET nick=? WHERE user_id=? AND chat_id=?", (nick, uid, cid))
    conn.commit()
    send(2000000000 + cid, f"🏷 {get_user_nick(uid, cid)} | НИК: {nick}\n👮 {get_user_nick(admin, cid)}")

def global_ban(uid, admin, reason):
    c.execute("INSERT OR REPLACE INTO global_bans (user_id, admin_id, reason, date) VALUES (?,?,?,?)",
              (uid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    for chat in get_all_chats():
        try:
            vk.messages.removeChatUser(chat_id=chat, user_id=uid)
        except:
            pass
    send(OWNER_ID, f"🌐 {get_name(uid)} | ГЛОБАЛЬНЫЙ БАН\n📝 {reason}\n👮 {get_name(admin)}")

# ============= КЛАВИАТУРЫ =============

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
    if get_role_level(role) >= 1:
        kb.add_line()
        kb.add_button("🛡 МОДЕРАЦИЯ", VkKeyboardColor.NEGATIVE)
    if get_role_level(role) >= 4:
        kb.add_line()
        kb.add_button("⚙️ НАСТРОЙКИ", VkKeyboardColor.PRIMARY)
    if get_role_level(role) >= 6:
        kb.add_line()
        kb.add_button("👑 ГЛОБАЛКА", VkKeyboardColor.NEGATIVE)
    return kb

# ============= ГЛАВНЫЙ ЦИКЛ =============

print("🤖 БОТ ЗАПУЩЕН! ЖДУ КОМАНД...")
print("=" * 50)

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
        
        if cid:
            c.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (cid,))
            register_user(uid, cid)
            c.execute("UPDATE users SET last_active=?, messages=messages+1 WHERE user_id=? AND chat_id=?", 
                     (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), uid, cid))
            conn.commit()
            
            if is_global_banned(uid):
                try:
                    vk.messages.removeChatUser(chat_id=cid, user_id=uid)
                except:
                    pass
                continue
            
            if is_banned(uid, cid):
                try:
                    vk.messages.removeChatUser(chat_id=cid, user_id=uid)
                except:
                    pass
                continue
            
            if is_muted(uid, cid):
                continue
            
            if not msg.startswith('/'):
                chat = c.execute("SELECT filter_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                if not chat or chat[0] == 1:
                    bad = c.execute("SELECT word FROM badwords").fetchall()
                    for w in bad:
                        if w[0].lower() in msg_lower:
                            try:
                                vk.messages.delete(message_ids=[event.message_id], delete_for_all=1)
                            except:
                                pass
                            add_warn(cid, uid, 0, f"Мат: {w[0]}")
                            break
        
        # ============= ВСЕ КОМАНДЫ =============
        
        # 👤 КОМАНДЫ ДЛЯ ВСЕХ
        if msg == '/menu':
            send(peer, "🏠 ГЛАВНОЕ МЕНЮ", main_kb(get_role(uid, cid) if cid else 'user'))
        
        elif msg == '/info':
            send(peer, "🤖 BLACK FIB BOT v4.0\n━━━━━━━━━━━━━━━━━━━━\n👑 Разработчик: Дмитрий\n📅 2024-2025\n💬 /menu - главное меню")
        
        elif msg.startswith('/stats'):
            target = extract_id(msg) if '[' in msg else uid
            data = c.execute("SELECT warns, mute, role, nick, joined, messages FROM users WHERE user_id=? AND chat_id=?", (target, cid)).fetchone()
            if data:
                muted = "НЕТ" if not data[1] else f"ДО {data[1][:16]}"
                nick = data[3] if data[3] else "НЕТ"
                send(peer, f"📊 {get_name(target)}\n⭐ Роль: {data[2]}\n🏷 Ник: {nick}\n⚠️ Варны: {data[0]}/3\n🔇 Мут: {muted}\n📨 Сообщений: {data[5]}")
            else:
                send(peer, f"📊 {get_name(target)}\n⚠️ Варны: 0/3")
        
        elif msg == '/getid' or msg.startswith('/getid '):
            target = extract_id(msg) if '[' in msg else uid
            send(peer, f"🆔 ID: {target}")
        
        elif msg == '/test' or msg == '/ping':
            send(peer, f"✅ Бот работает!\n👤 ID: {uid}\n💬 Чат: {cid if cid else 'ЛС'}")
        
        # 💚 ХЭЛПЕРЫ
        elif msg.startswith('/kick '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение"
                    kick_user(cid, target, uid, reason)
                else:
                    send(peer, "❌ /kick @user [причина]")
        
        elif msg.startswith('/mute '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    nums = re.findall(r'(\d+)', msg)
                    mins = int(nums[1]) if len(nums) > 1 else 30
                    reason = msg.split(' ', 3)[3] if len(msg.split(' ', 3)) > 3 else "Нарушение"
                    mute_user(cid, target, mins, uid, reason)
                else:
                    send(peer, "❌ /mute @user 30 [причина]")
        
        elif msg.startswith('/unmute '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET mute=NULL WHERE user_id=? AND chat_id=?", (target, cid))
                    conn.commit()
                    send(peer, f"🔊 {get_name(target)} размучен")
                else:
                    send(peer, "❌ /unmute @user")
        
        elif msg.startswith('/warn '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение"
                    add_warn(cid, target, uid, reason)
                else:
                    send(peer, "❌ /warn @user [причина]")
        
        elif msg.startswith('/unwarn '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    w = c.execute("SELECT warns FROM users WHERE user_id=? AND chat_id=?", (target, cid)).fetchone()
                    if w and w[0] > 0:
                        c.execute("UPDATE users SET warns=warns-1 WHERE user_id=? AND chat_id=?", (target, cid))
                        conn.commit()
                        send(peer, f"✅ {get_name(target)} | Варн снят")
                    else:
                        send(peer, "❌ Нет варнов")
                else:
                    send(peer, "❌ /unwarn @user")
        
        elif msg.startswith('/clear '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ Нет прав!")
            else:
                nums = re.findall(r'(\d+)', msg)
                count = int(nums[0]) if nums else 10
                if count > 100:
                    count = 100
                history = vk.messages.getHistory(peer_id=peer, count=count)
                ids = [m['id'] for m in history['items']]
                vk.messages.delete(message_ids=ids, delete_for_all=1)
                send(peer, f"✅ Очищено {len(ids)} сообщений")
        
        elif msg == '/staff':
            if not cid:
                send(peer, "❌ Только в беседе")
            else:
                admins = c.execute("SELECT user_id, role FROM users WHERE chat_id=? AND role NOT IN ('user')", (cid,)).fetchall()
                if admins:
                    txt = "👥 АДМИНИСТРАЦИЯ:\n━━━━━━━━━━━━━━━━━━━━\n"
                    r_ru = {'helper':'💚 ХЭЛПЕР', 'moderator':'💙 МОДЕРАТОР', 'seniormoderator':'🔵 СТ.МОДЕРАТОР', 'admin':'🟢 АДМИН', 'senioradmin':'🟡 СТ.АДМИН', 'owner':'👑 ВЛАДЕЛЕЦ'}
                    for a in admins:
                        txt += f"{r_ru.get(a[1], a[1])}: {get_name(a[0])}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ Нет администрации")
        
        elif msg.startswith('/setnick '):
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    nick = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else None
                    if nick:
                        set_nick(cid, target, uid, nick)
                    else:
                        send(peer, "❌ /setnick @user ник")
                else:
                    send(peer, "❌ /setnick @user ник")
        
        elif msg == '/nlist':
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ Нет прав!")
            else:
                nicks = c.execute("SELECT user_id, nick FROM users WHERE chat_id=? AND nick IS NOT NULL", (cid,)).fetchall()
                if nicks:
                    txt = "🏷 СПИСОК НИКОВ:\n━━━━━━━━━━━━━━━━━━━━\n"
                    for n in nicks[:20]:
                        txt += f"• {get_name(n[0])} → {n[1]}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ Нет ников")
        
        elif msg == '/warnlist':
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ Нет прав!")
            else:
                warned = c.execute("SELECT user_id, warns FROM users WHERE chat_id=? AND warns>0 ORDER BY warns DESC", (cid,)).fetchall()
                if warned:
                    txt = "⚠️ ВАРНЫ:\n━━━━━━━━━━━━━━━━━━━━\n"
                    for w in warned:
                        txt += f"• {get_name(w[0])} → {w[1]}/3\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ Нет варнов")
        
        elif msg == '/mutelist':
            if not check_perm(uid, cid, 'helper'):
                send(peer, "❌ Нет прав!")
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
                    txt = "🔇 МУТЫ:\n━━━━━━━━━━━━━━━━━━━━\n"
                    for a in active:
                        left = a[1] - now
                        txt += f"• {get_name(a[0])} → {left.seconds//60} мин\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ Нет мутов")
        
        # 💙 МОДЕРАТОРЫ
        elif msg.startswith('/ban '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение"
                    ban_user(cid, target, uid, reason)
                else:
                    send(peer, "❌ /ban @user [причина]")
        
        elif msg.startswith('/unban '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    unban_user(cid, target, uid)
                else:
                    send(peer, "❌ /unban @user")
        
        elif msg.startswith('/addmoder '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'moderator'))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ТЕПЕРЬ МОДЕРАТОР")
                else:
                    send(peer, "❌ /addmoder @user")
        
        elif msg.startswith('/removerole '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET role='user' WHERE user_id=? AND chat_id=?", (target, cid))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | РОЛЬ ЗАБРАНА")
                else:
                    send(peer, "❌ /removerole @user")
        
        elif msg == '/zov':
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                users = get_chat_users(cid)
                mentions = ' '.join([f"[id{u}|]" for u in users[:30]])
                send(peer, mentions if mentions else "Нет пользователей")
        
        elif msg == '/banlist':
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                bans = c.execute("SELECT user_id, reason, date FROM bans WHERE chat_id=?", (cid,)).fetchall()
                if bans:
                    txt = "🚫 БАНЫ:\n━━━━━━━━━━━━━━━━━━━━\n"
                    for b in bans[:15]:
                        txt += f"• {get_name(b[0])} → {b[2][:10]}\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ Нет банов")
        
        elif msg.startswith('/inactivelist'):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                days = int(re.findall(r'(\d+)', msg)[0]) if re.findall(r'(\d+)', msg) else 30
                threshold = datetime.now() - timedelta(days=days)
                inactive = c.execute("SELECT user_id FROM users WHERE chat_id=? AND last_active < ?", (cid, threshold.strftime('%Y-%m-%d %H:%M:%S'))).fetchall()
                if inactive:
                    txt = f"💤 НЕАКТИВНЫЕ ({days} дней):\n━━━━━━━━━━━━━━━━━━━━\n"
                    for i in inactive[:15]:
                        txt += f"• {get_name(i[0])}\n"
                    send(peer, txt)
                else:
                    send(peer, f"✅ Нет неактивных ({days} дней)")
        
        # 🔵 СТАРШИЕ МОДЕРАТОРЫ
        elif msg == '/quiet':
            if not check_perm(uid, cid, 'seniormoderator'):
                send(peer, "❌ Нет прав!")
            else:
                current = c.execute("SELECT quiet_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET quiet_on=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"🔇 РЕЖИМ ТИШИНЫ {'ВКЛЮЧЕН' if new_val else 'ВЫКЛЮЧЕН'}")
        
        elif msg.startswith('/addsenmoder '):
            if not check_perm(uid, cid, 'seniormoderator'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'seniormoderator'))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ТЕПЕРЬ СТАРШИЙ МОДЕРАТОР")
                else:
                    send(peer, "❌ /addsenmoder @user")
        
        elif msg.startswith('/bug '):
            if not check_perm(uid, cid, 'seniormoderator'):
                send(peer, "❌ Нет прав!")
            else:
                bug_text = msg[5:]
                receivers = c.execute("SELECT user_id FROM bug_receivers").fetchall()
                for r in receivers:
                    try:
                        send(r[0], f"🐛 БАГ ОТ {get_name(uid)}:\n📝 {bug_text}\n📍 Чат: {cid}")
                    except:
                        pass
                send(peer, "✅ Баг отправлен разработчикам")
        
        elif msg == '/rnickall':
            if not check_perm(uid, cid, 'seniormoderator'):
                send(peer, "❌ Нет прав!")
            else:
                c.execute("UPDATE users SET nick=NULL WHERE chat_id=?", (cid,))
                conn.commit()
                send(peer, "✅ ВСЕ НИКИ СБРОШЕНЫ")
        
        # 🟢 АДМИНИСТРАТОРЫ
        elif msg.startswith('/addadmin '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'admin'))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ТЕПЕРЬ АДМИНИСТРАТОР")
                else:
                    send(peer, "❌ /addadmin @user")
        
        elif msg == '/settings':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                chat = c.execute("SELECT filter_on, quiet_on, antiflood, welcome_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                if chat:
                    send(peer, f"⚙️ НАСТРОЙКИ БЕСЕДЫ\n━━━━━━━━━━━━━━━━━━━━\n📝 ФИЛЬТР: {'✅' if chat[0] else '❌'}\n🔇 ТИШИНА: {'✅' if chat[1] else '❌'}\n🌊 АНТИФЛУД: {'✅' if chat[2] else '❌'}\n👋 ПРИВЕТСТВИЕ: {'✅' if chat[3] else '❌'}")
                else:
                    send(peer, "⚙️ НАСТРОЙКИ БЕСЕДЫ\n/filter - фильтр мата\n/quiet - режим тишины\n/antiflood - антифлуд\n/welcometext - приветствие")
        
        elif msg == '/filter':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                current = c.execute("SELECT filter_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET filter_on=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"📝 ФИЛЬТР МАТА {'ВКЛЮЧЕН' if new_val else 'ВЫКЛЮЧЕН'}")
        
        elif msg == '/serverinfo':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                users_count = len(get_chat_users(cid))
                registered = c.execute("SELECT COUNT(*) FROM users WHERE chat_id=?", (cid,)).fetchone()[0]
                banned = c.execute("SELECT COUNT(*) FROM bans WHERE chat_id=?", (cid,)).fetchone()[0]
                warned = c.execute("SELECT COUNT(*) FROM users WHERE chat_id=? AND warns>0", (cid,)).fetchone()[0]
                send(peer, f"📊 ИНФОРМАЦИЯ О БЕСЕДЕ\n━━━━━━━━━━━━━━━━━━━━\n👥 Участников: {users_count}\n📝 Зарегистрировано: {registered}\n⚠️ С варнами: {warned}\n🚫 Забанено: {banned}")
        
        elif msg == '/rkick':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                users = get_chat_users(cid)
                kicked = 0
                for u in users:
                    role = get_role(u, cid)
                    if role == 'user':
                        try:
                            vk.messages.removeChatUser(chat_id=cid, user_id=u)
                            kicked += 1
                            time.sleep(0.5)
                        except:
                            pass
                send(peer, f"✅ Кикнуто {kicked} новых пользователей")
        
        # 🟡 СТАРШИЕ АДМИНИСТРАТОРЫ
        elif msg.startswith('/type '):
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                nums = re.findall(r'(\d+)', msg)
                if nums:
                    t = int(nums[0])
                    c.execute("UPDATE chats SET chat_type=? WHERE chat_id=?", (t, cid))
                    conn.commit()
                    send(peer, f"✅ Тип беседы изменён на {t}")
                else:
                    send(peer, "❌ /type 1-4")
        
        elif msg == '/leave':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                current = c.execute("SELECT leave_kick FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET leave_kick=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"🚪 КИК ПРИ ВЫХОДЕ {'ВКЛЮЧЕН' if new_val else 'ВЫКЛЮЧЕН'}")
        
        elif msg.startswith('/editowner '):
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET role='owner' WHERE user_id=? AND chat_id=?", (target, cid))
                    c.execute("UPDATE users SET role='user' WHERE user_id=? AND chat_id=? AND role='owner'", (uid, cid))
                    conn.commit()
                    send(peer, f"👑 {get_name(target)} | ТЕПЕРЬ ВЛАДЕЛЕЦ БЕСЕДЫ")
                else:
                    send(peer, "❌ /editowner @user")
        
        elif msg.startswith('/pin '):
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                text = msg[5:]
                msg_id = vk.messages.send(peer_id=peer, message=text, random_id=get_random_id())
                vk.messages.pin(peer_id=peer, message_id=msg_id)
                send(peer, "✅ Сообщение закреплено")
        
        elif msg == '/unpin':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                vk.messages.unpin(peer_id=peer)
                send(peer, "✅ Сообщение откреплено")
        
        elif msg == '/rroleall':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                c.execute("UPDATE users SET role='user' WHERE chat_id=? AND role NOT IN ('owner')", (cid,))
                conn.commit()
                send(peer, "✅ ВСЕ РОЛИ СБРОШЕНЫ")
        
        elif msg.startswith('/addsenadm '):
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'senioradmin'))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ТЕПЕРЬ СТАРШИЙ АДМИНИСТРАТОР")
                else:
                    send(peer, "❌ /addsenadm @user")
        
        elif msg == '/masskick':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                users = get_chat_users(cid)
                kicked = 0
                for u in users:
                    role = get_role(u, cid)
                    if role == 'user':
                        try:
                            vk.messages.removeChatUser(chat_id=cid, user_id=u)
                            kicked += 1
                        except:
                            pass
                send(peer, f"✅ Кикнуто {kicked} пользователей без роли")
        
        elif msg == '/invite':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                current = c.execute("SELECT invite_moders FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET invite_moders=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"👥 ПРИГЛАШЕНИЕ МОДЕРАМИ {'РАЗРЕШЕНО' if new_val else 'ЗАПРЕЩЕНО'}")
        
        elif msg == '/antiflood':
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                current = c.execute("SELECT antiflood FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET antiflood=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"🌊 АНТИФЛУД {'ВКЛЮЧЕН' if new_val else 'ВЫКЛЮЧЕН'}")
        
        elif msg.startswith('/welcometext '):
            if not check_perm(uid, cid, 'senioradmin'):
                send(peer, "❌ Нет прав!")
            else:
                text = msg[13:]
                c.execute("UPDATE chats SET welcome_text=?, welcome_on=1 WHERE chat_id=?", (text, cid))
                conn.commit()
                send(peer, f"👋 ПРИВЕТСТВИЕ УСТАНОВЛЕНО\n{text}")
        
        # 🔴 СПЕЦ АДМИНИСТРАТОРЫ
        elif msg.startswith('/gban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Глобальное нарушение"
                    global_ban(target, uid, reason)
                    send(peer, f"🌐 {get_name(target)} | ГЛОБАЛЬНЫЙ БАН\n📝 {reason}")
                else:
                    send(peer, "❌ /gban @user [причина]")
        
        elif msg.startswith('/gunban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("DELETE FROM global_bans WHERE user_id=?", (target,))
                    conn.commit()
                    send(peer, f"🌐 {get_name(target)} | ГЛОБАЛЬНЫЙ РАЗБАН")
                else:
                    send(peer, "❌ /gunban @user")
        
        elif msg == '/gbanlist':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                bans = c.execute("SELECT user_id, reason, date FROM global_bans").fetchall()
                if bans:
                    txt = "🌐 ГЛОБАЛЬНЫЕ БАНЫ:\n━━━━━━━━━━━━━━━━━━━━\n"
                    for b in bans:
                        txt += f"• {get_name(b[0])} → {b[2][:10]}\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ Нет глобальных банов")
        
        elif msg == '/banwords':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                words = c.execute("SELECT word FROM badwords").fetchall()
                if words:
                    txt = "🚫 ЗАПРЕЩЕННЫЕ СЛОВА:\n━━━━━━━━━━━━━━━━━━━━\n"
                    txt += ', '.join([w[0] for w in words])
                    send(peer, txt)
                else:
                    send(peer, "✅ Нет запрещенных слов")
        
        elif msg.startswith('/addowner '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'owner'))
                    conn.commit()
                    send(peer, f"👑 {get_name(target)} | ТЕПЕРЬ ВЛАДЕЛЕЦ БЕСЕДЫ")
                else:
                    send(peer, "❌ /addowner @user")
        
        elif msg.startswith('/skick '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    for chat in get_all_chats():
                        try:
                            vk.messages.removeChatUser(chat_id=chat, user_id=target)
                        except:
                            pass
                    send(peer, f"👢 {get_name(target)} | СУПЕР КИК")
                else:
                    send(peer, "❌ /skick @user")
        
        elif msg.startswith('/sban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Супер бан"
                    global_ban(target, uid, reason)
                    send(peer, f"💀 {get_name(target)} | СУПЕР БАН\n📝 {reason}")
                else:
                    send(peer, "❌ /sban @user")
        
        elif msg.startswith('/sunban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("DELETE FROM global_bans WHERE user_id=?", (target,))
                    conn.commit()
                    send(peer, f"💀 {get_name(target)} | СУПЕР РАЗБАН")
                else:
                    send(peer, "❌ /sunban @user")
        
        # 👑 ВЛАДЕЛЕЦ БЕСЕДЫ
        elif msg.startswith('/gremoverole '):
            if not check_perm(uid, cid, 'owner'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET role='user' WHERE user_id=? AND chat_id=?", (target, cid))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ВСЕ РОЛИ СБРОШЕНЫ")
                else:
                    send(peer, "❌ /gremoverole @user")
        
        elif msg.startswith('/news '):
            if not check_perm(uid, cid, 'owner'):
                send(peer, "❌ Нет прав!")
            else:
                news_text = msg[6:]
                for chat in get_all_chats():
                    try:
                        send(2000000000 + chat, f"📢 НОВОСТИ ОТ АДМИНИСТРАЦИИ\n━━━━━━━━━━━━━━━━━━━━\n{news_text}")
                    except:
                        pass
                send(peer, "✅ Новости отправлены во все чаты")
        
        elif msg.startswith('/addzam '):
            if not check_perm(uid, cid, 'owner'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, -1, 'zamglav'))
                    conn.commit()
                    send(peer, f"⚜️ {get_name(target)} | ТЕПЕРЬ ЗАМ.СОЗДАТЕЛЯ")
                else:
                    send(peer, "❌ /addzam @user")
        
        # ⚜️ ЗАМ.СОЗДАТЕЛЯ
        elif msg.startswith('/banid '):
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ Нет прав!")
            else:
                nums = re.findall(r'(\d+)', msg)
                if nums:
                    target_chat = int(nums[0])
                    c.execute("UPDATE chats SET active=0 WHERE chat_id=?", (target_chat,))
                    conn.commit()
                    send(peer, f"🚫 Чат {target_chat} заблокирован")
                else:
                    send(peer, "❌ /banid 123456789")
        
        elif msg.startswith('/unbanid '):
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ Нет прав!")
            else:
                nums = re.findall(r'(\d+)', msg)
                if nums:
                    target_chat = int(nums[0])
                    c.execute("UPDATE chats SET active=1 WHERE chat_id=?", (target_chat,))
                    conn.commit()
                    send(peer, f"✅ Чат {target_chat} разблокирован")
                else:
                    send(peer, "❌ /unbanid 123456789")
        
        elif msg.startswith('/clearchat '):
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ Нет прав!")
            else:
                nums = re.findall(r'(\d+)', msg)
                if nums:
                    target_chat = int(nums[0])
                    c.execute("DELETE FROM chats WHERE chat_id=?", (target_chat,))
                    c.execute("DELETE FROM users WHERE chat_id=?", (target_chat,))
                    c.execute("DELETE FROM bans WHERE chat_id=?", (target_chat,))
                    conn.commit()
                    send(peer, f"🗑 Чат {target_chat} удалён из БД")
                else:
                    send(peer, "❌ /clearchat 123456789")
        
        elif msg.startswith('/infoid '):
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    data = c.execute("SELECT role, warns, last_active FROM users WHERE user_id=? AND chat_id!=-1", (target,)).fetchone()
                    if data:
                        send(peer, f"📊 ИНФО О {get_name(target)}\n⭐ Роль: {data[0]}\n⚠️ Варны: {data[1]}\n📅 Последняя активность: {data[2][:16] if data[2] else 'Неизвестно'}")
                    else:
                        send(peer, f"📊 Нет данных о {get_name(target)}")
                else:
                    send(peer, "❌ /infoid @user")
        
        elif msg == '/listchats':
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ Нет прав!")
            else:
                chats = c.execute("SELECT chat_id, active FROM chats").fetchall()
                if chats:
                    txt = "📋 СПИСОК ЧАТОВ:\n━━━━━━━━━━━━━━━━━━━━\n"
                    for ch in chats[:20]:
                        txt += f"• {ch[0]} - {'✅' if ch[1] else '❌'}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ Нет чатов")
        
        elif msg == '/server':
            if not check_perm(uid, cid, 'zamglav'):
                send(peer, "❌ Нет прав!")
            else:
                total_chats = len(get_all_chats())
                total_users = c.execute("SELECT COUNT(DISTINCT user_id) FROM users WHERE chat_id!=-1").fetchone()[0]
                total_bans = c.execute("SELECT COUNT(*) FROM global_bans").fetchone()[0]
                send(peer, f"🖥️ ИНФОРМАЦИЯ О СЕРВЕРЕ\n━━━━━━━━━━━━━━━━━━━━\n📊 Всего чатов: {total_chats}\n👥 Всего пользователей: {total_users}\n🌐 Глобальных банов: {total_bans}")
        
        # 👑 СОЗДАТЕЛЬ БОТА (FC4096)
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
                    send(peer, f"✅ {get_name(target)} | УДАЛЕН ИЗ ПОЛУЧАТЕЛЕЙ БАГОВ")
                else:
                    send(peer, "❌ /delbug @user")
            
            elif msg == '/sync':
                conn.commit()
                send(peer, "✅ БАЗА ДАННЫХ СИНХРОНИЗИРОВАНА")
        
        # ОТВЕТ НА ЛЮБОЕ СООБЩЕНИЕ В ЛС
        elif not cid and msg and not msg.startswith('/'):
            send(peer, "🤖 BLACK FIB BOT v4.0\n📋 Напиши /menu для списка команд\n👑 Владелец: Дмитрий")

print("Бот остановлен")
