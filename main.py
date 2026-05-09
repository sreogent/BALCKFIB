import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import sqlite3
import time
import re
import threading

# ==================== НАСТРОЙКИ ====================
TOKEN = "vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg"
OWNER_ID = 631833072
GROUP_ID = 229320501

# ==================== БАЗА ДАННЫХ ====================
conn = sqlite3.connect('bot.db', check_same_thread=False)
cur = conn.cursor()

cur.executescript('''
-- ГЛОБАЛЬНЫЕ РОЛИ (только для создателя и его замов)
CREATE TABLE IF NOT EXISTS global_roles (
    user_id INTEGER PRIMARY KEY,
    role TEXT DEFAULT 'user',
    date INTEGER
);

-- ЛОКАЛЬНЫЕ РОЛИ (для каждого чата отдельно)
CREATE TABLE IF NOT EXISTS local_roles (
    user_id INTEGER,
    peer_id INTEGER,
    role TEXT DEFAULT 'user',
    date INTEGER,
    PRIMARY KEY (user_id, peer_id)
);

-- НИКИ (для каждого чата отдельно)
CREATE TABLE IF NOT EXISTS nicks (
    user_id INTEGER,
    peer_id INTEGER,
    nick TEXT,
    PRIMARY KEY (user_id, peer_id)
);

-- ВАРНЫ (для каждого чата отдельно)
CREATE TABLE IF NOT EXISTS warns (
    user_id INTEGER,
    peer_id INTEGER,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, peer_id)
);

CREATE TABLE IF NOT EXISTS mutes (
    user_id INTEGER,
    peer_id INTEGER,
    until INTEGER,
    PRIMARY KEY (user_id, peer_id)
);

CREATE TABLE IF NOT EXISTS bans (
    user_id INTEGER,
    peer_id INTEGER,
    reason TEXT,
    date INTEGER,
    PRIMARY KEY (user_id, peer_id)
);

CREATE TABLE IF NOT EXISTS gban (
    user_id INTEGER PRIMARY KEY,
    reason TEXT,
    date INTEGER
);

CREATE TABLE IF NOT EXISTS warn_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    peer_id INTEGER,
    admin_id INTEGER,
    reason TEXT,
    date INTEGER
);

CREATE TABLE IF NOT EXISTS settings (
    peer_id INTEGER PRIMARY KEY,
    quiet INTEGER DEFAULT 0,
    antiflood INTEGER DEFAULT 0,
    invite_enabled INTEGER DEFAULT 1,
    welcometext TEXT,
    type TEXT DEFAULT 'players',
    leavekick INTEGER DEFAULT 0,
    filter_enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS banwords (word TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS chats (peer_id INTEGER PRIMARY KEY, server TEXT);
CREATE TABLE IF NOT EXISTS bug_receivers (user_id INTEGER PRIMARY KEY);
''')
conn.commit()

# Уровни ролей
GLOBAL_ROLES_LEVEL = {
    'owner': 100,   # Создатель бота
    'deputy': 90,   # Зам.создателя
    'dev': 85,      # Разработчик
}

LOCAL_ROLES_LEVEL = {
    'admin': 50,     # Администратор чата
    'senadmin': 45,  # Старший администратор
    'senmoder': 35,  # Старший модератор
    'moder': 30,     # Модератор
    'user': 0,       # Обычный пользователь
}

ALL_ROLES = {**GLOBAL_ROLES_LEVEL, **LOCAL_ROLES_LEVEL}

# ==================== ФУНКЦИИ ====================

# ----- ГЛОБАЛЬНЫЕ РОЛИ (видны во всех чатах) -----
def get_global_role(uid):
    cur.execute("SELECT role FROM global_roles WHERE user_id=?", (uid,))
    res = cur.fetchone()
    return res[0] if res else 'user'

def set_global_role(uid, role):
    cur.execute("INSERT OR REPLACE INTO global_roles (user_id, role, date) VALUES (?,?,?)", 
                (uid, role, int(time.time())))
    conn.commit()

def remove_global_role(uid):
    cur.execute("DELETE FROM global_roles WHERE user_id=?", (uid,))
    conn.commit()

# ----- ЛОКАЛЬНЫЕ РОЛИ (только в конкретном чате) -----
def get_local_role(uid, peer_id):
    cur.execute("SELECT role FROM local_roles WHERE user_id=? AND peer_id=?", (uid, peer_id))
    res = cur.fetchone()
    return res[0] if res else 'user'

def set_local_role(uid, peer_id, role):
    cur.execute("INSERT OR REPLACE INTO local_roles (user_id, peer_id, role, date) VALUES (?,?,?,?)", 
                (uid, peer_id, role, int(time.time())))
    conn.commit()

def remove_local_role(uid, peer_id):
    cur.execute("DELETE FROM local_roles WHERE user_id=? AND peer_id=?", (uid, peer_id))
    conn.commit()

def clear_all_local_roles(peer_id):
    cur.execute("DELETE FROM local_roles WHERE peer_id=?", (peer_id,))
    conn.commit()

# ----- ПОЛУЧЕНИЕ ИТОГОВОЙ РОЛИ -----
def get_user_role(uid, peer_id):
    # Сначала проверяем глобальную роль
    global_role = get_global_role(uid)
    if global_role != 'user':
        return global_role
    # Если нет глобальной, возвращаем локальную
    return get_local_role(uid, peer_id)

def has_rights(uid, peer_id, min_role):
    # Владелец бота имеет все права
    if uid == OWNER_ID:
        return True
    
    # Проверяем глобальную роль
    global_role = get_global_role(uid)
    if global_role != 'user':
        return ALL_ROLES.get(global_role, 0) >= ALL_ROLES.get(min_role, 0)
    
    # Проверяем локальную роль в чате
    local_role = get_local_role(uid, peer_id)
    return ALL_ROLES.get(local_role, 0) >= ALL_ROLES.get(min_role, 0)

# ----- НИКИ (локальные для каждого чата) -----
def get_nick(uid, peer_id):
    cur.execute("SELECT nick FROM nicks WHERE user_id=? AND peer_id=?", (uid, peer_id))
    res = cur.fetchone()
    return res[0] if res else None

def set_nick(uid, peer_id, nick):
    if nick is None:
        cur.execute("DELETE FROM nicks WHERE user_id=? AND peer_id=?", (uid, peer_id))
    else:
        cur.execute("INSERT OR REPLACE INTO nicks (user_id, peer_id, nick) VALUES (?,?,?)", 
                    (uid, peer_id, nick))
    conn.commit()

def clear_all_nicks(peer_id):
    cur.execute("DELETE FROM nicks WHERE peer_id=?", (peer_id,))
    conn.commit()

def clear_global_nick(uid):
    cur.execute("DELETE FROM nicks WHERE user_id=?", (uid,))
    conn.commit()

# ----- ВАРНЫ (локальные для каждого чата) -----
def get_warns(uid, peer_id):
    cur.execute("SELECT count FROM warns WHERE user_id=? AND peer_id=?", (uid, peer_id))
    res = cur.fetchone()
    return res[0] if res else 0

def add_warn(uid, peer_id, admin_id, reason):
    cur.execute("INSERT OR REPLACE INTO warns (user_id, peer_id, count) VALUES (?,?, COALESCE((SELECT count FROM warns WHERE user_id=? AND peer_id=?), 0) + 1)", 
                (uid, peer_id, uid, peer_id))
    cur.execute("INSERT INTO warn_history (user_id, peer_id, admin_id, reason, date) VALUES (?,?,?,?,?)", 
                (uid, peer_id, admin_id, reason, int(time.time())))
    conn.commit()
    return get_warns(uid, peer_id)

def remove_warn(uid, peer_id):
    cur.execute("UPDATE warns SET count = count - 1 WHERE user_id=? AND peer_id=? AND count > 0", (uid, peer_id))
    conn.commit()

def clear_warns(uid, peer_id):
    cur.execute("DELETE FROM warns WHERE user_id=? AND peer_id=?", (uid, peer_id))
    conn.commit()

def clear_all_warns(peer_id):
    cur.execute("DELETE FROM warns WHERE peer_id=?", (peer_id,))
    conn.commit()

def get_warn_history(uid):
    cur.execute("SELECT admin_id, reason, date, peer_id FROM warn_history WHERE user_id=? ORDER BY date DESC LIMIT 10", (uid,))
    return cur.fetchall()

# ----- МУТЫ -----
def add_mute(uid, peer_id, minutes):
    until = int(time.time()) + minutes * 60
    cur.execute("INSERT OR REPLACE INTO mutes VALUES (?,?,?)", (uid, peer_id, until))
    conn.commit()

def remove_mute(uid, peer_id):
    cur.execute("DELETE FROM mutes WHERE user_id=? AND peer_id=?", (uid, peer_id))
    conn.commit()

def is_muted(uid, peer_id):
    cur.execute("SELECT until FROM mutes WHERE user_id=? AND peer_id=? AND until > ?", (uid, peer_id, int(time.time())))
    return cur.fetchone() is not None

def get_mute_list(peer_id):
    cur.execute("SELECT user_id, until FROM mutes WHERE peer_id=? AND until > ?", (peer_id, int(time.time())))
    return cur.fetchall()

# ----- БАНЫ -----
def add_ban(uid, peer_id, reason):
    cur.execute("INSERT OR REPLACE INTO bans VALUES (?,?,?,?)", (uid, peer_id, reason, int(time.time())))
    conn.commit()

def remove_ban(uid, peer_id):
    cur.execute("DELETE FROM bans WHERE user_id=? AND peer_id=?", (uid, peer_id))
    conn.commit()

def is_banned(uid, peer_id):
    cur.execute("SELECT 1 FROM bans WHERE user_id=? AND peer_id=?", (uid, peer_id))
    return cur.fetchone() is not None

def get_ban_list(peer_id):
    cur.execute("SELECT user_id, reason, date FROM bans WHERE peer_id=?", (peer_id,))
    return cur.fetchall()

# ----- ГЛОБАЛЬНЫЕ БАНЫ -----
def add_gban(uid, reason):
    cur.execute("INSERT OR REPLACE INTO gban VALUES (?,?,?)", (uid, reason, int(time.time())))
    conn.commit()

def remove_gban(uid):
    cur.execute("DELETE FROM gban WHERE user_id=?", (uid,))
    conn.commit()

def is_gbanned(uid):
    cur.execute("SELECT 1 FROM gban WHERE user_id=?", (uid,))
    return cur.fetchone() is not None

def get_gban_list():
    cur.execute("SELECT user_id, reason, date FROM gban")
    return cur.fetchall()

# ----- ФИЛЬТР СЛОВ -----
def get_banwords():
    cur.execute("SELECT word FROM banwords")
    return [row[0] for row in cur.fetchall()]

def add_banword(word):
    cur.execute("INSERT OR IGNORE INTO banwords VALUES (?)", (word.lower(),))
    conn.commit()

def remove_banword(word):
    cur.execute("DELETE FROM banwords WHERE word=?", (word.lower(),))
    conn.commit()

# ----- НАСТРОЙКИ БЕСЕДЫ -----
def get_setting(peer_id, key, default=0):
    cur.execute(f"SELECT {key} FROM settings WHERE peer_id=?", (peer_id,))
    res = cur.fetchone()
    return res[0] if res else default

def set_setting(peer_id, key, value):
    cur.execute(f"INSERT OR REPLACE INTO settings (peer_id, {key}) VALUES (?,?)", (peer_id, value))
    conn.commit()

def get_welcometext(peer_id):
    cur.execute("SELECT welcometext FROM settings WHERE peer_id=?", (peer_id,))
    res = cur.fetchone()
    return res[0] if res else None

# ----- ЧАТЫ СЕРВЕРА -----
def add_server_chat(peer_id):
    cur.execute("INSERT OR REPLACE INTO chats (peer_id, server) VALUES (?,?)", (peer_id, 'server'))
    conn.commit()

def remove_server_chat(peer_id):
    cur.execute("DELETE FROM chats WHERE peer_id=?", (peer_id,))
    conn.commit()

def get_server_chats():
    cur.execute("SELECT peer_id FROM chats WHERE server='server'")
    return [row[0] for row in cur.fetchall()]

def is_chat_banned(peer_id):
    cur.execute("SELECT 1 FROM chats WHERE peer_id=? AND server='banned'", (peer_id,))
    return cur.fetchone() is not None

def ban_chat(peer_id):
    cur.execute("INSERT OR REPLACE INTO chats (peer_id, server) VALUES (?,?)", (peer_id, 'banned'))
    conn.commit()

def unban_chat(peer_id):
    cur.execute("DELETE FROM chats WHERE peer_id=? AND server='banned'", (peer_id,))
    conn.commit()

# ----- ПОЛУЧАТЕЛИ БАГОВ -----
def get_bug_receivers():
    cur.execute("SELECT user_id FROM bug_receivers")
    return [row[0] for row in cur.fetchall()]

def add_bug_receiver(uid):
    cur.execute("INSERT OR IGNORE INTO bug_receivers VALUES (?)", (uid,))
    conn.commit()

def remove_bug_receiver(uid):
    cur.execute("DELETE FROM bug_receivers WHERE user_id=?", (uid,))
    conn.commit()

# ==================== VK ФУНКЦИИ ====================
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

def send(peer, text, reply_to=None):
    try:
        vk.messages.send(peer_id=peer, message=text, random_id=get_random_id(), reply_to=reply_to)
    except Exception as e:
        print(f"Send error: {e}")

def get_user_name(uid):
    try:
        u = vk.users.get(user_ids=uid)[0]
        return f"{u['first_name']} {u['last_name']}"
    except:
        return f"ID{uid}"

def get_mention(uid, peer_id=None):
    nick = get_nick(uid, peer_id) if peer_id else None
    if nick:
        return f"@{nick}"
    try:
        u = vk.users.get(user_ids=uid)[0]
        return f"@id{uid} ({u['first_name']} {u['last_name']})"
    except:
        return f"@id{uid}"

def get_user_id(arg):
    if not arg:
        return None
    arg = re.sub(r'[^0-9]', '', str(arg))
    try:
        return int(arg)
    except:
        return None

def kick_chat(peer_id, uid):
    try:
        vk.messages.removeChatUser(chat_id=peer_id - 2000000000, user_id=uid)
        return True
    except:
        return False

def clear_messages(peer_id, count=20):
    try:
        msgs = vk.messages.getHistory(peer_id=peer_id, count=min(count, 100))
        msg_ids = [m['id'] for m in msgs['items']]
        if msg_ids:
            vk.messages.delete(message_ids=msg_ids, delete_for_all=1, peer_id=peer_id)
        return True
    except:
        return False

def delete_user_messages(peer_id, uid, count=20):
    try:
        msgs = vk.messages.getHistory(peer_id=peer_id, count=200)
        msg_ids = [m['id'] for m in msgs['items'] if m['from_id'] == uid][:count]
        if msg_ids:
            vk.messages.delete(message_ids=msg_ids, delete_for_all=1, peer_id=peer_id)
        return True
    except:
        return False

def get_all_members(peer_id):
    try:
        members = vk.messages.getConversationMembers(peer_id=peer_id)
        return [m['member_id'] for m in members['items'] if m['member_id'] > 0]
    except:
        return []

def get_online_members(peer_id):
    try:
        members = vk.messages.getConversationMembers(peer_id=peer_id)
        online = []
        for m in members['items']:
            if m['member_id'] > 0:
                try:
                    user = vk.users.get(user_ids=m['member_id'], fields='online')[0]
                    if user.get('online'):
                        online.append(m['member_id'])
                except:
                    pass
        return online
    except:
        return []

def pin_message(peer_id, msg_id):
    try:
        vk.messages.pin(peer_id=peer_id, message_id=msg_id)
        return True
    except:
        return False

def unpin_message(peer_id):
    try:
        vk.messages.unpin(peer_id=peer_id)
        return True
    except:
        return False

# ==================== ГЛАВНЫЙ ОБРАБОТЧИК ====================
print("=" * 50)
print("🤖 BLACK FIB BOT ЗАПУЩЕН!")
print("=" * 50)
print(f"👑 Владелец бота: @id{OWNER_ID}")
print("✅ Система ролей: ГЛОБАЛЬНЫЕ (owner/deputy/dev) + ЛОКАЛЬНЫЕ (admin/senadmin/moder/senmoder)")
print("✅ Ники: для каждого чата отдельно")
print("✅ Варны: для каждого чата отдельно")
print("=" * 50)
print("💬 Ожидание сообщений...\n")

def handle_message(event):
    text = event.text.strip()
    peer = event.peer_id
    uid = event.user_id
    msg_id = event.message_id
    cmd = text.split()[0].lower() if text else ''
    args = text.split()[1:] if len(text.split()) > 1 else []
    
    # Проверка на мут и бан
    if is_muted(uid, peer) and not has_rights(uid, peer, 'moder'):
        send(peer, "🔇 Вы замучены!", msg_id)
        return
    if is_banned(uid, peer) and not has_rights(uid, peer, 'moder'):
        send(peer, "🔒 Вы забанены в этой беседе!", msg_id)
        return
    if is_gbanned(uid) and not has_rights(uid, peer, 'deputy'):
        send(peer, "🌍 Вы в глобальном бане!", msg_id)
        return
    
    # Фильтр мата
    if get_setting(peer, 'filter_enabled', 1):
        for word in get_banwords():
            if word.lower() in text.lower():
                send(peer, f"🚫 Запрещенное слово: {word}", msg_id)
                return
    
    # ==================== START ====================
    if cmd == '/start':
        if uid == OWNER_ID:
            set_global_role(OWNER_ID, 'owner')
            send(peer, "✅ BLACK FIB БОТ АКТИВИРОВАН!\n👑 Владелец: https://vk.com/id631833072\n📋 /help - все команды")
        else:
            send(peer, "⛔ Только владелец может активировать бота")
        return
    
    # ==================== HELP ====================
    if cmd in ['/help', '/команды', '/cmds']:
        send(peer, """📋 **BLACK FIB BOT - ВСЕ КОМАНДЫ**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **ПОЛЬЗОВАТЕЛИ:**
/info, /stats, /getid

💚 **МОДЕРАТОРЫ (локальные):**
/kick, /mute, /unmute, /warn, /unwarn, /getban, /getwarn
/warnhistory, /staff, /setnick, /removenick, /nlist, /nonick
/getnick, /alt, /getacc, /warnlist, /clear, /getmute, /mutelist, /delete

💙 **СТАРШИЕ МОДЕРАТОРЫ (локальные):**
/ban, /unban, /addmoder, /removerole, /zov, /online, /banlist, /onlinelist, /inactivelist

➡️ **ПРОДОЛЖЕНИЕ: /help2""")
        return
    
    if cmd == '/help2':
        send(peer, """📋 **BLACK FIB BOT - ПРОДОЛЖЕНИЕ**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 **АДМИНИСТРАТОРЫ (локальные):**
/skick, /quiet, /sban, /sunban, /addsenmoder, /bug
/rnickall, /srnick, /ssetnick, /srrole, /srole

🟡 **СТАРШИЕ АДМИНИСТРАТОРЫ (локальные):**
/addadmin, /settings, /filter, /szov, /serverinfo, /rkick

🔴 **ВЛАДЕЛЕЦ БЕСЕДЫ (локальный):**
/type, /leave, /editowner, /pin, /unpin, /clearwarn
/rroleall, /addsenadm, /masskick, /invite, /antiflood, /welcometext, /welcometextdelete

⚜️ **ЗАМ.РУКОВОДИТЕЛЯ (глобальный):**
/gban, /gunban, /sync, /gbanlist, /banwords, /gbanpl, /gunbanpl, /addowner

👑 **РУКОВОДИТЕЛЬ БОТА (глобальный):**
/server, /addword, /delword, /gremoverole, /news, /addzam
/banid, /unbanid, /clearchat, /infoid, /addbug, /listchats, /adddev, /delbug

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 Глобальные роли: owner, deputy, dev
📍 Локальные роли: admin, senadmin, moder, senmoder""")
        return
    
    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    if cmd == '/info':
        send(peer, "🔗 **Официальные ресурсы бота:**\nhttps://vk.com/club229320501\n👑 Владелец: https://vk.com/id631833072")
        return
    
    if cmd == '/stats':
        target = get_user_id(args[0]) if args else uid
        warns = get_warns(target, peer)
        role = get_user_role(target, peer)
        nick = get_nick(target, peer) or "Не установлен"
        muted = "Да" if is_muted(target, peer) else "Нет"
        banned = "Да" if is_banned(target, peer) else "Нет"
        global_role = get_global_role(target)
        
        text = f"📊 **СТАТИСТИКА** {get_user_name(target)}\n━━━━━━━━━━━━━━━━━━━━\n"
        text += f"👑 Роль в этом чате: {role}\n"
        if global_role != 'user':
            text += f"🌍 Глобальная роль: {global_role}\n"
        text += f"⚠ Варны: {warns}\n🔇 Мут: {muted}\n🔒 Бан: {banned}\n📝 Ник: {nick}"
        send(peer, text)
        return
    
    if cmd == '/getid':
        target = get_user_id(args[0]) if args else uid
        send(peer, f"🆔 ID пользователя: {target}")
        return
    
    # ==================== МОДЕРАТОРЫ (локальные роли) ====================
    if cmd == '/kick' and has_rights(uid, peer, 'moder'):
        if not args:
            send(peer, "❌ Использование: /kick @user [причина]")
            return
        target = get_user_id(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "Не указана"
        if target and kick_chat(peer, target):
            send(peer, f"👢 **ИСКЛЮЧЕН** {get_mention(target, peer)}\n📝 Причина: {reason}")
        else:
            send(peer, "❌ Не удалось исключить")
        return
    
    if cmd == '/mute' and has_rights(uid, peer, 'moder'):
        if len(args) < 2:
            send(peer, "❌ Использование: /mute @user время [причина]")
            return
        target = get_user_id(args[0])
        minutes = int(args[1])
        reason = " ".join(args[2:]) if len(args) > 2 else "Не указана"
        if target:
            add_mute(target, peer, minutes)
            send(peer, f"🔇 **МУТ {minutes} МИН**\n👤 {get_mention(target, peer)}\n📝 Причина: {reason}")
        return
    
    if cmd == '/unmute' and has_rights(uid, peer, 'moder'):
        if not args:
            send(peer, "❌ Использование: /unmute @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_mute(target, peer)
            send(peer, f"✅ **МУТ СНЯТ** с {get_mention(target, peer)}")
        return
    
    if cmd == '/warn' and has_rights(uid, peer, 'moder'):
        if not args:
            send(peer, "❌ Использование: /warn @user [причина]")
            return
        target = get_user_id(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "Нарушение правил"
        if target:
            count = add_warn(target, peer, uid, reason)
            send(peer, f"⚠ **ВАРН #{count}**\n👤 {get_mention(target, peer)}\n📝 Причина: {reason}")
            if count >= 3:
                add_mute(target, peer, 60)
                send(peer, f"🔇 3 варна = МУТ 60 МИНУТ!")
        return
    
    if cmd == '/unwarn' and has_rights(uid, peer, 'moder'):
        if not args:
            send(peer, "❌ Использование: /unwarn @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_warn(target, peer)
            send(peer, f"✅ **ВАРН СНЯТ** с {get_mention(target, peer)}")
        return
    
    if cmd == '/getban' and has_rights(uid, peer, 'moder'):
        target = get_user_id(args[0]) if args else uid
        res = cur.execute("SELECT reason, date FROM bans WHERE user_id=? AND peer_id=?", (target, peer)).fetchone()
        if res:
            send(peer, f"🔒 **ИНФО О БАНЕ** {get_mention(target, peer)}\n📝 Причина: {res[0]}\n📅 Дата: {time.ctime(res[1])}")
        else:
            send(peer, f"✅ {get_mention(target, peer)} не забанен")
        return
    
    if cmd == '/getwarn' and has_rights(uid, peer, 'moder'):
        target = get_user_id(args[0]) if args else uid
        warns = get_warns(target, peer)
        send(peer, f"⚠ **АКТИВНЫЕ ВАРНЫ** {get_mention(target, peer)}: {warns}")
        return
    
    if cmd == '/warnhistory' and has_rights(uid, peer, 'moder'):
        target = get_user_id(args[0]) if args else uid
        history = get_warn_history(target)
        if history:
            text = f"📜 **ИСТОРИЯ ВАРНОВ** {get_mention(target, peer)}\n━━━━━━━━━━━━━━━━━━━━\n"
            for admin_id, reason, date, peer_id in history:
                text += f"• {get_user_name(admin_id)}: {reason} (в чате {peer_id}) - {time.ctime(date)}\n"
            send(peer, text[:4000])
        else:
            send(peer, f"📜 У {get_mention(target, peer)} нет истории варнов")
        return
    
    if cmd == '/staff' and has_rights(uid, peer, 'moder'):
        text = "👮 **ПОЛЬЗОВАТЕЛИ С РОЛЯМИ**\n━━━━━━━━━━━━━━━━━━━━\n"
        
        # Глобальные роли
        cur.execute("SELECT user_id, role FROM global_roles WHERE role != 'user'")
        for uid2, role in cur.fetchall():
            text += f"🌍 {role} (глобал): {get_user_name(uid2)}\n"
        
        # Локальные роли в этом чате
        cur.execute("SELECT user_id, role FROM local_roles WHERE peer_id=? AND role != 'user'", (peer,))
        for uid2, role in cur.fetchall():
            if get_global_role(uid2) == 'user':
                text += f"📍 {role} (локал): {get_user_name(uid2)}\n"
        
        send(peer, text[:4000] if len(text) > 4000 else text)
        return
    
    if cmd == '/setnick' and has_rights(uid, peer, 'moder'):
        if len(args) < 2:
            send(peer, "❌ Использование: /setnick @user ник")
            return
        target = get_user_id(args[0])
        nickname = " ".join(args[1:])
        if target:
            set_nick(target, peer, nickname)
            send(peer, f"✅ **НИК УСТАНОВЛЕН**\n👤 {get_user_name(target)} → {nickname} (только в этом чате)")
        return
    
    if cmd == '/removenick' and has_rights(uid, peer, 'moder'):
        if not args:
            send(peer, "❌ Использование: /removenick @user")
            return
        target = get_user_id(args[0])
        if target:
            set_nick(target, peer, None)
            send(peer, f"✅ **НИК УДАЛЕН** у {get_mention(target, peer)}")
        return
    
    if cmd == '/nlist' and has_rights(uid, peer, 'moder'):
        cur.execute("SELECT user_id, nick FROM nicks WHERE peer_id=?", (peer,))
        users = cur.fetchall()
        if users:
            text = "📝 **СПИСОК НИКОВ В ЭТОМ ЧАТЕ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid2, nick in users[:20]:
                text += f"• {nick} → {get_user_name(uid2)}\n"
            send(peer, text)
        else:
            send(peer, "📝 Ники не установлены в этом чате")
        return
    
    if cmd == '/nonick' and has_rights(uid, peer, 'moder'):
        all_members = get_all_members(peer)
        users_with_nick = [row[0] for row in cur.execute("SELECT user_id FROM nicks WHERE peer_id=?", (peer,)).fetchall()]
        no_nick = [uid2 for uid2 in all_members if uid2 not in users_with_nick][:20]
        if no_nick:
            text = "👤 **ПОЛЬЗОВАТЕЛИ БЕЗ НИКОВ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid2 in no_nick:
                text += f"• {get_user_name(uid2)}\n"
            send(peer, text)
        else:
            send(peer, "👤 У всех пользователей есть ники!")
        return
    
    if cmd == '/getnick' and has_rights(uid, peer, 'moder'):
        target = get_user_id(args[0]) if args else uid
        nick = get_nick(target, peer)
        send(peer, f"🔍 **НИК** {get_mention(target, peer)}: {nick if nick else 'Не установлен'}")
        return
    
    if cmd == '/alt' and has_rights(uid, peer, 'moder'):
        send(peer, "🔄 **АЛЬТЕРНАТИВНЫЕ КОМАНДЫ**\n/kick, /mute, /warn, /clear, /ban, /zov")
        return
    
    if cmd == '/getacc' and has_rights(uid, peer, 'moder'):
        if not args:
            send(peer, "❌ Использование: /getacc ник")
            return
        search = " ".join(args).lower()
        cur.execute("SELECT user_id, nick FROM nicks WHERE peer_id=? AND nick LIKE ?", (peer, f"%{search}%"))
        res = cur.fetchone()
        if res:
            send(peer, f"🔍 **НАЙДЕН ПОЛЬЗОВАТЕЛЬ**\nНик: {res[1]}\nID: {res[0]}\nИмя: {get_user_name(res[0])}")
        else:
            send(peer, f"❌ Ник '{search}' не найден в этом чате")
        return
    
    if cmd == '/warnlist' and has_rights(uid, peer, 'moder'):
        cur.execute("SELECT user_id, count FROM warns WHERE peer_id=? AND count > 0 ORDER BY count DESC", (peer,))
        users = cur.fetchall()
        if users:
            text = "⚠ **СПИСОК ВАРНОВ В ЭТОМ ЧАТЕ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid2, count in users[:20]:
                text += f"• {get_user_name(uid2)}: {count} варнов\n"
            send(peer, text)
        else:
            send(peer, "⚠ Нет активных варнов в этом чате")
        return
    
    if cmd == '/clear' and has_rights(uid, peer, 'moder'):
        count = int(args[0]) if args and args[0].isdigit() else 20
        if clear_messages(peer, count):
            send(peer, f"🧹 **ОЧИЩЕНО {count} СООБЩЕНИЙ**")
        else:
            send(peer, "❌ Ошибка очистки")
        return
    
    if cmd == '/getmute' and has_rights(uid, peer, 'moder'):
        target = get_user_id(args[0]) if args else uid
        cur.execute("SELECT until FROM mutes WHERE user_id=? AND peer_id=?", (target, peer))
        res = cur.fetchone()
        if res and res[0] > int(time.time()):
            remaining = int((res[0] - time.time()) / 60)
            send(peer, f"🔇 **МУТ** {get_mention(target, peer)}: осталось {remaining} мин")
        else:
            send(peer, f"✅ У {get_mention(target, peer)} нет мута")
        return
    
    if cmd == '/mutelist' and has_rights(uid, peer, 'moder'):
        mutes_list = get_mute_list(peer)
        if mutes_list:
            text = "🔇 **СПИСОК МУТОВ В ЭТОМ ЧАТЕ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid2, until in mutes_list[:20]:
                remaining = int((until - time.time()) / 60)
                text += f"• {get_user_name(uid2)}: {remaining} мин\n"
            send(peer, text)
        else:
            send(peer, "🔇 Нет активных мутов")
        return
    
    if cmd == '/delete' and has_rights(uid, peer, 'moder'):
        if len(args) < 2:
            send(peer, "❌ Использование: /delete @user количество")
            return
        target = get_user_id(args[0])
        count = int(args[1]) if args[1].isdigit() else 20
        if target and delete_user_messages(peer, target, count):
            send(peer, f"🗑 **УДАЛЕНО {count} СООБЩЕНИЙ** от {get_mention(target, peer)}")
        else:
            send(peer, "❌ Ошибка удаления")
        return
    
    # ==================== СТАРШИЕ МОДЕРАТОРЫ (локальные) ====================
    if cmd == '/ban' and has_rights(uid, peer, 'senmoder'):
        if not args:
            send(peer, "❌ Использование: /ban @user [причина]")
            return
        target = get_user_id(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "Не указана"
        if target:
            add_ban(target, peer, reason)
            kick_chat(peer, target)
            send(peer, f"🔨 **БАН В БЕСЕДЕ**\n👤 {get_mention(target, peer)}\n📝 Причина: {reason}")
        return
    
    if cmd == '/unban' and has_rights(uid, peer, 'senmoder'):
        if not args:
            send(peer, "❌ Использование: /unban @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_ban(target, peer)
            send(peer, f"✅ **РАЗБАНЕН** {get_mention(target, peer)}")
        return
    
    if cmd == '/addmoder' and has_rights(uid, peer, 'senmoder'):
        if not args:
            send(peer, "❌ Использование: /addmoder @user")
            return
        target = get_user_id(args[0])
        if target:
            set_local_role(target, peer, 'moder')
            send(peer, f"✅ **ВЫДАНА РОЛЬ МОДЕРАТОРА** (только в этом чате)\n👤 {get_mention(target, peer)}")
        return
    
    if cmd == '/removerole' and has_rights(uid, peer, 'senmoder'):
        if not args:
            send(peer, "❌ Использование: /removerole @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_local_role(target, peer)
            send(peer, f"✅ **РОЛЬ ЗАБРАНА** у {get_mention(target, peer)}")
        return
    
    if cmd == '/zov' and has_rights(uid, peer, 'senmoder'):
        members = get_all_members(peer)
        mentions = [f"@id{uid}" for uid in members[:50]]
        send(peer, "🔔 **ВНИМАНИЕ! СРОЧНОЕ СООБЩЕНИЕ!**\n" + " ".join(mentions))
        return
    
    if cmd == '/online' and has_rights(uid, peer, 'senmoder'):
        online = get_online_members(peer)
        if online:
            mentions = [f"@id{uid}" for uid in online[:30]]
            send(peer, "🟢 **ПОЛЬЗОВАТЕЛИ ОНЛАЙН**\n" + " ".join(mentions))
        else:
            send(peer, "🟢 Онлайн пользователей нет")
        return
    
    if cmd == '/banlist' and has_rights(uid, peer, 'senmoder'):
        ban_list = get_ban_list(peer)
        if ban_list:
            text = "🔨 **ЗАБАНЕННЫЕ В ЭТОЙ БЕСЕДЕ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid2, reason, date in ban_list[:20]:
                text += f"• {get_user_name(uid2)}: {reason} ({time.ctime(date)})\n"
            send(peer, text)
        else:
            send(peer, "🔨 В этой беседе нет забаненных")
        return
    
    if cmd == '/onlinelist' and has_rights(uid, peer, 'senmoder'):
        online = get_online_members(peer)
        if online:
            names = [get_user_name(uid) for uid in online[:30]]
            text = f"🟢 **ОНЛАЙН ПОЛЬЗОВАТЕЛИ** ({len(names)})\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(names)
            send(peer, text)
        else:
            send(peer, "🟢 Онлайн пользователей нет")
        return
    
    if cmd == '/inactivelist' and has_rights(uid, peer, 'senmoder'):
        send(peer, "📊 Функция списка неактивных в разработке")
        return
    
    # ==================== АДМИНИСТРАТОРЫ (локальные) ====================
    if cmd == '/skick' and has_rights(uid, peer, 'admin'):
        if not args:
            send(peer, "❌ Использование: /skick @user")
            return
        target = get_user_id(args[0])
        if target:
            count = 0
            for chat in get_server_chats():
                if kick_chat(chat, target):
                    count += 1
            send(peer, f"⚡ **СУПЕР КИК** для ID{target}\n✅ Кикнут в {count} чатах")
        return
    
    if cmd == '/quiet' and has_rights(uid, peer, 'admin'):
        current = get_setting(peer, 'quiet', 0)
        set_setting(peer, 'quiet', 1 - current)
        status = "ВКЛЮЧЕН" if not current else "ВЫКЛЮЧЕН"
        send(peer, f"🔇 **РЕЖИМ ТИШИНЫ {status}**")
        return
    
    if cmd == '/sban' and has_rights(uid, peer, 'admin'):
        if not args:
            send(peer, "❌ Использование: /sban @user [причина]")
            return
        target = get_user_id(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "Нарушение правил сервера"
        if target:
            add_gban(target, reason)
            for chat in get_server_chats():
                kick_chat(chat, target)
            send(peer, f"🌍 **СУПЕР БАН** для ID{target}\n📝 Причина: {reason}")
        return
    
    if cmd == '/sunban' and has_rights(uid, peer, 'admin'):
        if not args:
            send(peer, "❌ Использование: /sunban @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_gban(target)
            send(peer, f"✅ **СУПЕР РАЗБАН** для ID{target}")
        return
    
    if cmd == '/addsenmoder' and has_rights(uid, peer, 'admin'):
        if not args:
            send(peer, "❌ Использование: /addsenmoder @user")
            return
        target = get_user_id(args[0])
        if target:
            set_local_role(target, peer, 'senmoder')
            send(peer, f"✅ **ВЫДАНА РОЛЬ СТАРШЕГО МОДЕРАТОРА** (только в этом чате)\n👤 {get_mention(target, peer)}")
        return
    
    if cmd == '/bug' and has_rights(uid, peer, 'admin'):
        if not args:
            send(peer, "❌ Использование: /bug текст ошибки")
            return
        bug_text = " ".join(args)
        for receiver in get_bug_receivers():
            send(receiver, f"🐛 **БАГ ОТ {get_user_name(uid)}**\n📝 {bug_text}\n📌 Беседа: {peer}\n👤 Пользователь: @id{uid}")
        send(peer, "✅ **БАГ ОТПРАВЛЕН РАЗРАБОТЧИКУ**")
        return
    
    if cmd == '/rnickall' and has_rights(uid, peer, 'admin'):
        clear_all_nicks(peer)
        send(peer, "✅ **ВСЕ НИКИ ОЧИЩЕНЫ В ЭТОЙ БЕСЕДЕ**")
        return
    
    if cmd == '/srnick' and has_rights(uid, peer, 'admin'):
        if not args:
            send(peer, "❌ Использование: /srnick @user")
            return
        target = get_user_id(args[0])
        if target:
            clear_global_nick(target)
            send(peer, f"✅ **НИК УБРАН ВО ВСЕХ ЧАТАХ** у {get_mention(target, peer)}")
        return
    
    if cmd == '/ssetnick' and has_rights(uid, peer, 'admin'):
        if len(args) < 2:
            send(peer, "❌ Использование: /ssetnick @user ник")
            return
        target = get_user_id(args[0])
        nickname = " ".join(args[1:])
        if target:
            for chat in get_server_chats():
                set_nick(target, chat, nickname)
            set_nick(target, peer, nickname)
            send(peer, f"✅ **НИК УСТАНОВЛЕН ВО ВСЕХ ЧАТАХ**\n👤 {get_mention(target, peer)} → {nickname}")
        return
    
    if cmd == '/srrole' and has_rights(uid, peer, 'admin'):
        if not args:
            send(peer, "❌ Использование: /srrole @user")
            return
        target = get_user_id(args[0])
        if target:
            for chat in get_server_chats():
                remove_local_role(target, chat)
            remove_local_role(target, peer)
            send(peer, f"✅ **РОЛИ СБРОШЕНЫ ВО ВСЕХ ЧАТАХ** у {get_mention(target, peer)}")
        return
    
    if cmd == '/srole' and has_rights(uid, peer, 'admin'):
        if len(args) < 2:
            send(peer, "❌ Использование: /srole @user роль")
            return
        target = get_user_id(args[0])
        role = args[1]
        if target and role in LOCAL_ROLES_LEVEL:
            for chat in get_server_chats():
                set_local_role(target, chat, role)
            set_local_role(target, peer, role)
            send(peer, f"✅ **РОЛЬ ВЫДАНА ВО ВСЕХ ЧАТАХ**\n👤 {get_mention(target, peer)} → {role}")
        else:
            send(peer, f"❌ Неверная роль. Доступные: {', '.join(LOCAL_ROLES_LEVEL.keys())}")
        return
    
    # ==================== СТАРШИЕ АДМИНИСТРАТОРЫ (локальные) ====================
    if cmd == '/addadmin' and has_rights(uid, peer, 'senadmin'):
        if not args:
            send(peer, "❌ Использование: /addadmin @user")
            return
        target = get_user_id(args[0])
        if target:
            set_local_role(target, peer, 'admin')
            send(peer, f"✅ **ВЫДАНА РОЛЬ АДМИНИСТРАТОРА** (только в этом чате)\n👤 {get_mention(target, peer)}")
        return
    
    if cmd == '/settings' and has_rights(uid, peer, 'senadmin'):
        quiet = "ВКЛ" if get_setting(peer, 'quiet', 0) else "ВЫКЛ"
        antiflood = "ВКЛ" if get_setting(peer, 'antiflood', 0) else "ВЫКЛ"
        filter_enabled = "ВКЛ" if get_setting(peer, 'filter_enabled', 1) else "ВЫКЛ"
        invite = "ВКЛ" if get_setting(peer, 'invite_enabled', 1) else "ВЫКЛ"
        chat_type = get_setting(peer, 'type', 'players')
        send(peer, f"⚙ **НАСТРОЙКИ ЭТОЙ БЕСЕДЫ**\n━━━━━━━━━━━━━━━━━━━━\n🔇 Тишина: {quiet}\n🌊 Антифлуд: {antiflood}\n🚫 Фильтр: {filter_enabled}\n👋 Приглашения: {invite}\n📋 Тип: {chat_type}")
        return
    
    if cmd == '/filter' and has_rights(uid, peer, 'senadmin'):
        current = get_setting(peer, 'filter_enabled', 1)
        set_setting(peer, 'filter_enabled', 1 - current)
        status = "ВКЛЮЧЕН" if not current else "ВЫКЛЮЧЕН"
        send(peer, f"🚫 **ФИЛЬТР МАТА В ЭТОЙ БЕСЕДЕ {status}**")
        return
    
    if cmd == '/szov' and has_rights(uid, peer, 'senadmin'):
        msg = " ".join(args) if args else "ВНИМАНИЕ! Важное объявление!"
        for chat in get_server_chats():
            send(chat, f"🔔 **ОБЪЯВЛЕНИЕ ОТ АДМИНИСТРАЦИИ**\n━━━━━━━━━━━━━━━━━━━━\n{msg}")
        send(peer, "✅ **СУПЕР-ОПОВЕЩЕНИЕ ОТПРАВЛЕНО ВО ВСЕ ЧАТЫ СЕРВЕРА**")
        return
    
    if cmd == '/serverinfo' and has_rights(uid, peer, 'senadmin'):
        chats_count = len(get_server_chats())
        send(peer, f"🖥 **ИНФОРМАЦИЯ О СЕРВЕРЕ**\n━━━━━━━━━━━━━━━━━━━━\n📊 Чатов в привязке: {chats_count}\n✅ Бот активен\n👑 Владелец бота: https://vk.com/id{OWNER_ID}")
        return
    
    if cmd == '/rkick' and has_rights(uid, peer, 'senadmin'):
        send(peer, "⚠ Функция масс-кика приглашенных за 24 часа в разработке")
        return
    
    # ==================== ВЛАДЕЛЕЦ БЕСЕДЫ (локальный) ====================
    if cmd == '/type' and has_rights(uid, peer, 'owner'):
        if not args:
            send(peer, "❌ Использование: /type 1-4\n1 - Игроки, 2 - Общий, 3 - VIP, 4 - Администрация")
            return
        types = {'1': 'players', '2': 'general', '3': 'vip', '4': 'admin'}
        chat_type = types.get(args[0], 'players')
        set_setting(peer, 'type', chat_type)
        send(peer, f"✅ **ТИП БЕСЕДЫ УСТАНОВЛЕН:** {chat_type}")
        return
    
    if cmd == '/leave' and has_rights(uid, peer, 'owner'):
        current = get_setting(peer, 'leavekick', 0)
        set_setting(peer, 'leavekick', 1 - current)
        status = "ВКЛЮЧЕН" if not current else "ВЫКЛЮЧЕН"
        send(peer, f"🚪 **КИК ПОЛЬЗОВАТЕЛЯ ПРИ ВЫХОДЕ {status}**")
        return
    
    if cmd == '/editowner' and has_rights(uid, peer, 'owner'):
        if not args:
            send(peer, "❌ Использование: /editowner @user")
            return
        target = get_user_id(args[0])
        if target:
            set_local_role(target, peer, 'owner')
            send(peer, f"👑 **ПРАВА ВЛАДЕЛЬЦА БЕСЕДЫ ПЕРЕДАНЫ** {get_mention(target, peer)}")
        return
    
    if cmd == '/pin' and has_rights(uid, peer, 'owner'):
        if pin_message(peer, msg_id):
            send(peer, f"📌 **СООБЩЕНИЕ ЗАКРЕПЛЕНО**")
        else:
            send(peer, "❌ Не удалось закрепить (ответьте на сообщение, которое хотите закрепить)")
        return
    
    if cmd == '/unpin' and has_rights(uid, peer, 'owner'):
        if unpin_message(peer):
            send(peer, "📌 **ЗАКРЕПЛЕНИЕ СНЯТО**")
        else:
            send(peer, "❌ Не удалось снять закрепление")
        return
    
    if cmd == '/clearwarn' and has_rights(uid, peer, 'owner'):
        clear_all_warns(peer)
        send(peer, "✅ **НАКАЗАНИЯ ВЫШЕДШИМ ПОЛЬЗОВАТЕЛЯМ ОЧИЩЕНЫ**")
        return
    
    if cmd == '/rroleall' and has_rights(uid, peer, 'owner'):
        clear_all_local_roles(peer)
        send(peer, "✅ **ВСЕ ЛОКАЛЬНЫЕ РОЛИ В ЭТОЙ БЕСЕДЕ ОЧИЩЕНЫ**")
        return
    
    if cmd == '/addsenadm' and has_rights(uid, peer, 'owner'):
        if not args:
            send(peer, "❌ Использование: /addsenadm @user")
            return
        target = get_user_id(args[0])
        if target:
            set_local_role(target, peer, 'senadmin')
            send(peer, f"✅ **ВЫДАНА РОЛЬ СТАРШЕГО АДМИНИСТРАТОРА** (только в этом чате)\n👤 {get_mention(target, peer)}")
        return
    
    if cmd == '/masskick' and has_rights(uid, peer, 'owner'):
        members = get_all_members(peer)
        kicked = 0
        for member_uid in members:
            if get_user_role(member_uid, peer) == 'user' and member_uid != OWNER_ID:
                if kick_chat(peer, member_uid):
                    kicked += 1
                time.sleep(0.3)
        send(peer, f"⚠️ **МАСС-КИК ВЫПОЛНЕН**\n✅ Кикнуто {kicked} пользователей без роли")
        return
    
    if cmd == '/invite' and has_rights(uid, peer, 'owner'):
        current = get_setting(peer, 'invite_enabled', 1)
        set_setting(peer, 'invite_enabled', 1 - current)
        status = "РАЗРЕШЕНЫ" if not current else "ЗАПРЕЩЕНЫ"
        send(peer, f"👋 **ПРИГЛАШЕНИЯ МОДЕРАТОРАМИ {status}**")
        return
    
    if cmd == '/antiflood' and has_rights(uid, peer, 'owner'):
        current = get_setting(peer, 'antiflood', 0)
        set_setting(peer, 'antiflood', 1 - current)
        status = "ВКЛЮЧЕН" if not current else "ВЫКЛЮЧЕН"
        send(peer, f"🌊 **АНТИФЛУД {status}**")
        return
    
    if cmd == '/welcometext' and has_rights(uid, peer, 'owner'):
        if not args:
            send(peer, "❌ Использование: /welcometext текст приветствия\nИспользуйте {user} для вставки имени нового участника")
            return
        wt = " ".join(args)
        set_setting(peer, 'welcometext', wt)
        send(peer, f"✅ **ТЕКСТ ПРИВЕТСТВИЯ УСТАНОВЛЕН**\n📝 {wt[:50]}...")
        return
    
    if cmd == '/welcometextdelete' and has_rights(uid, peer, 'owner'):
        set_setting(peer, 'welcometext', None)
        send(peer, "🗑 **ТЕКСТ ПРИВЕТСТВИЯ УДАЛЕН**")
        return
    
    # ==================== ЗАМ.РУКОВОДИТЕЛЯ (глобальный) ====================
    if cmd == '/gban' and has_rights(uid, peer, 'deputy'):
        if not args:
            send(peer, "❌ Использование: /gban @user [причина]")
            return
        target = get_user_id(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "Глобальный бан"
        if target:
            add_gban(target, reason)
            for chat in get_server_chats():
                kick_chat(chat, target)
            send(peer, f"🌍 **ГЛОБАЛЬНЫЙ БАН** (действует во всех чатах)\n👤 {get_mention(target, peer)}\n📝 Причина: {reason}")
        return
    
    if cmd == '/gunban' and has_rights(uid, peer, 'deputy'):
        if not args:
            send(peer, "❌ Использование: /gunban @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_gban(target)
            send(peer, f"✅ **ГЛОБАЛЬНЫЙ БАН СНЯТ** с {get_mention(target, peer)}")
        return
    
    if cmd == '/sync' and has_rights(uid, peer, 'deputy'):
        send(peer, "✅ **БАЗА ДАННЫХ СИНХРОНИЗИРОВАНА**")
        return
    
    if cmd == '/gbanlist' and has_rights(uid, peer, 'deputy'):
        gbans = get_gban_list()
        if gbans:
            text = "🌍 **ГЛОБАЛЬНЫЙ БАН-ЛИСТ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid2, reason, date in gbans[:20]:
                text += f"• ID{uid2}: {reason} ({time.ctime(date)})\n"
            send(peer, text)
        else:
            send(peer, "🌍 Список глобальных банов пуст")
        return
    
    if cmd == '/banwords' and has_rights(uid, peer, 'deputy'):
        words = get_banwords()
        if words:
            text = "🚫 **ЗАПРЕЩЕННЫЕ СЛОВА В ФИЛЬТРЕ**\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join([f"• {w}" for w in words[:20]])
            send(peer, text)
        else:
            send(peer, "🚫 Список запрещенных слов пуст")
        return
    
    if cmd == '/gbanpl' and has_rights(uid, peer, 'deputy'):
        send(peer, "🎮 **БАН В БЕСЕДАХ ИГРОКОВ** (функция в разработке)")
        return
    
    if cmd == '/gunbanpl' and has_rights(uid, peer, 'deputy'):
        send(peer, "🎮 **РАЗБАН В БЕСЕДАХ ИГРОКОВ** (функция в разработке)")
        return
    
    if cmd == '/addowner' and has_rights(uid, peer, 'deputy'):
        if not args:
            send(peer, "❌ Использование: /addowner @user")
            return
        target = get_user_id(args[0])
        if target:
            set_local_role(target, peer, 'owner')
            send(peer, f"👑 **ВЫДАНЫ ПРАВА ВЛАДЕЛЬЦА ЭТОЙ БЕСЕДЫ**\n👤 {get_mention(target, peer)}")
        return
    
    # ==================== РУКОВОДИТЕЛЬ БОТА (глобальный) ====================
    if cmd == '/server' and has_rights(uid, peer, 'head'):
        add_server_chat(peer)
        send(peer, "✅ **ЭТА БЕСЕДА ПРИВЯЗАНА К СЕРВЕРУ**\nТеперь доступны команды: /szov, /news, /skick, /sban и другие глобальные команды")
        return
    
    if cmd == '/addword' and has_rights(uid, peer, 'head'):
        if not args:
            send(peer, "❌ Использование: /addword слово")
            return
        word = args[0].lower()
        add_banword(word)
        send(peer, f"✅ **СЛОВО ДОБАВЛЕНО В ГЛОБАЛЬНЫЙ ФИЛЬТР**: {word}")
        return
    
    if cmd == '/delword' and has_rights(uid, peer, 'head'):
        if not args:
            send(peer, "❌ Использование: /delword слово")
            return
        word = args[0].lower()
        remove_banword(word)
        send(peer, f"✅ **СЛОВО УДАЛЕНО ИЗ ГЛОБАЛЬНОГО ФИЛЬТРА**: {word}")
        return
    
    if cmd == '/gremoverole' and has_rights(uid, peer, 'head'):
        if not args:
            send(peer, "❌ Использование: /gremoverole @user")
            return
        target = get_user_id(args[0])
        if target:
            # Удаляем глобальную роль
            remove_global_role(target)
            # Удаляем все локальные роли
            for chat in get_server_chats():
                remove_local_role(target, chat)
            remove_local_role(target, peer)
            send(peer, f"✅ **ВСЕ РОЛИ СБРОШЕНЫ** у {get_mention(target, peer)} (и глобальные, и локальные)")
        return
    
    if cmd == '/news' and has_rights(uid, peer, 'head'):
        if not args:
            send(peer, "❌ Использование: /news текст новости")
            return
        news = " ".join(args)
        for chat in get_server_chats():
            send(chat, f"📢 **НОВОСТИ ОТ РУКОВОДИТЕЛЯ БОТА**\n━━━━━━━━━━━━━━━━━━━━\n{news}")
        send(peer, "✅ **НОВОСТИ ОТПРАВЛЕНЫ ВО ВСЕ ЧАТЫ СЕРВЕРА**")
        return
    
    if cmd == '/addzam' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /addzam @user")
            return
        target = get_user_id(args[0])
        if target:
            set_global_role(target, 'deputy')
            send(peer, f"✅ **ВЫДАНА ГЛОБАЛЬНАЯ РОЛЬ ЗАМ.РУКОВОДИТЕЛЯ**\n👤 {get_mention(target, peer)}\n🌍 Эта роль действует ВО ВСЕХ ЧАТАХ!")
        return
    
    if cmd == '/banid' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /banid ID_беседы")
            return
        target_peer = int(args[0])
        ban_chat(target_peer)
        send(peer, f"✅ **БЕСЕДА {target_peer} ЗАБЛОКИРОВАНА В БОТЕ**")
        return
    
    if cmd == '/unbanid' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /unbanid ID_беседы")
            return
        target_peer = int(args[0])
        unban_chat(target_peer)
        send(peer, f"✅ **БЕСЕДА {target_peer} РАЗБЛОКИРОВАНА В БОТЕ**")
        return
    
    if cmd == '/clearchat' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /clearchat ID_беседы")
            return
        target_peer = int(args[0])
        # Удаляем все данные чата
        cur.execute("DELETE FROM local_roles WHERE peer_id=?", (target_peer,))
        cur.execute("DELETE FROM nicks WHERE peer_id=?", (target_peer,))
        cur.execute("DELETE FROM warns WHERE peer_id=?", (target_peer,))
        cur.execute("DELETE FROM mutes WHERE peer_id=?", (target_peer,))
        cur.execute("DELETE FROM bans WHERE peer_id=?", (target_peer,))
        cur.execute("DELETE FROM warn_history WHERE peer_id=?", (target_peer,))
        cur.execute("DELETE FROM settings WHERE peer_id=?", (target_peer,))
        conn.commit()
        send(peer, f"✅ **ЧАТ {target_peer} ПОЛНОСТЬЮ УДАЛЕН ИЗ БАЗЫ ДАННЫХ**")
        return
    
    if cmd == '/infoid' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /infoid @user")
            return
        target = get_user_id(args[0])
        if target:
            cur.execute("SELECT COUNT(DISTINCT peer_id) FROM local_roles WHERE user_id=?", (target,))
            roles_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT peer_id) FROM mutes WHERE user_id=?", (target,))
            mutes_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT peer_id) FROM bans WHERE user_id=?", (target,))
            bans_count = cur.fetchone()[0]
            is_gb = "ДА" if is_gbanned(target) else "НЕТ"
            global_role = get_global_role(target)
            
            send(peer, f"📊 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ ID{target}**\n━━━━━━━━━━━━━━━━━━━━\n🌍 Глобальная роль: {global_role}\n🔒 Глобальный бан: {is_gb}\n📁 Чатов с ролью: {roles_count}\n🔇 Чатов с мутом: {mutes_count}\n🔨 Чатов с баном: {bans_count}")
        return
    
    if cmd == '/addbug' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /addbug @user")
            return
        target = get_user_id(args[0])
        if target:
            add_bug_receiver(target)
            send(peer, f"✅ **ID{target} ДОБАВЛЕН В ПОЛУЧАТЕЛИ БАГОВ**")
        return
    
    if cmd == '/listchats' and uid == OWNER_ID:
        chats = get_server_chats()
        if chats:
            send(peer, f"📋 **СПИСОК ЧАТОВ, ПРИВЯЗАННЫХ К СЕРВЕРУ**\n━━━━━━━━━━━━━━━━━━━━\nВсего: {len(chats)}\nID: {', '.join(map(str, chats[:15]))}")
        else:
            send(peer, "📋 Нет чатов, привязанных к серверу")
        return
    
    if cmd == '/adddev' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /adddev @user")
            return
        target = get_user_id(args[0])
        if target:
            set_global_role(target, 'dev')
            send(peer, f"✅ **ВЫДАНЫ ГЛОБАЛЬНЫЕ ПРАВА РАЗРАБОТЧИКА**\n👤 {get_mention(target, peer)}\n🌍 Эта роль действует ВО ВСЕХ ЧАТАХ!")
        return
    
    if cmd == '/delbug' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /delbug @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_bug_receiver(target)
            send(peer, f"✅ **ID{target} УДАЛЕН ИЗ ПОЛУЧАТЕЛЕЙ БАГОВ**")
        return
    
    # Если команда не распознана
    if cmd.startswith('/') and has_rights(uid, peer, 'moder'):
        send(peer, f"❓ Неизвестная команда. Напиши /help для списка всех команд")
        return

# ==================== ОБРАБОТКА НОВЫХ УЧАСТНИКОВ ====================
print("💬 Ожидание сообщений...\n")

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.text:
        try:
            # Проверка на бан чата
            if is_chat_banned(event.peer_id) and event.user_id != OWNER_ID:
                continue
            handle_message(event)
        except Exception as e:
            print(f"Ошибка: {e}")
            try:
                send(event.peer_id, f"❌ Ошибка: {str(e)[:100]}")
            except:
                pass
    
    # Приветствие новых участников
    elif event.type == VkEventType.GROUP_JOIN and event.user_id:
        try:
            welcome = get_welcometext(event.peer_id)
            if welcome:
                welcome = welcome.replace("{user}", get_mention(event.user_id, event.peer_id))
                send(event.peer_id, welcome)
        except:
            pass
