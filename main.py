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
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    role TEXT DEFAULT 'user',
    nick TEXT,
    warns INTEGER DEFAULT 0
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

# Роли
ROLES = {
    'user': 0, 
    'moder': 1, 
    'senmoder': 2, 
    'admin': 3, 
    'senadmin': 4, 
    'owner': 5, 
    'zam': 6, 
    'head': 7,
    'dev': 8
}

# Базовые слова для фильтра
default_words = ['хуй', 'бля', 'сука', 'пидор', 'ебать', 'нахуй', 'пизда', 'залупа', 'мудак', 'гандон']
for word in default_words:
    cur.execute("INSERT OR IGNORE INTO banwords VALUES (?)", (word,))
conn.commit()

# ==================== ФУНКЦИИ ====================
def get_role(uid):
    cur.execute("SELECT role FROM users WHERE user_id=?", (uid,))
    res = cur.fetchone()
    return res[0] if res else 'user'

def set_role(uid, role):
    cur.execute("INSERT OR REPLACE INTO users (user_id, role) VALUES (?,?)", (uid, role))
    conn.commit()

def get_nick(uid):
    cur.execute("SELECT nick FROM users WHERE user_id=?", (uid,))
    res = cur.fetchone()
    return res[0] if res and res[0] else None

def set_nick(uid, nick):
    cur.execute("UPDATE users SET nick=? WHERE user_id=?", (nick, uid))
    conn.commit()

def has_rights(uid, min_role):
    if uid == OWNER_ID:
        return True
    return ROLES.get(get_role(uid), 0) >= ROLES.get(min_role, 0)

def is_muted(uid, peer_id):
    cur.execute("SELECT until FROM mutes WHERE user_id=? AND peer_id=? AND until > ?", (uid, peer_id, int(time.time())))
    return cur.fetchone() is not None

def is_banned(uid, peer_id):
    cur.execute("SELECT 1 FROM bans WHERE user_id=? AND peer_id=?", (uid, peer_id))
    return cur.fetchone() is not None

def is_gbanned(uid):
    cur.execute("SELECT 1 FROM gban WHERE user_id=?", (uid,))
    return cur.fetchone() is not None

def get_warns(uid):
    cur.execute("SELECT warns FROM users WHERE user_id=?", (uid,))
    res = cur.fetchone()
    return res[0] if res else 0

def add_warn(uid, admin_id, peer_id, reason):
    cur.execute("UPDATE users SET warns = warns + 1 WHERE user_id=?", (uid,))
    cur.execute("INSERT INTO warn_history (user_id, peer_id, admin_id, reason, date) VALUES (?,?,?,?,?)", 
                (uid, peer_id, admin_id, reason, int(time.time())))
    conn.commit()
    return get_warns(uid)

def remove_warn(uid):
    cur.execute("UPDATE users SET warns = warns - 1 WHERE user_id=? AND warns > 0", (uid,))
    conn.commit()

def clear_user_warns(uid):
    cur.execute("UPDATE users SET warns = 0 WHERE user_id=?", (uid,))
    conn.commit()

def get_warn_history(uid):
    cur.execute("SELECT admin_id, reason, date FROM warn_history WHERE user_id=? ORDER BY date DESC LIMIT 10", (uid,))
    return cur.fetchall()

def add_mute(uid, peer_id, minutes):
    until = int(time.time()) + minutes * 60
    cur.execute("INSERT OR REPLACE INTO mutes VALUES (?,?,?)", (uid, peer_id, until))
    conn.commit()

def remove_mute(uid, peer_id):
    cur.execute("DELETE FROM mutes WHERE user_id=? AND peer_id=?", (uid, peer_id))
    conn.commit()

def add_ban(uid, peer_id, reason):
    cur.execute("INSERT OR REPLACE INTO bans VALUES (?,?,?,?)", (uid, peer_id, reason, int(time.time())))
    conn.commit()

def remove_ban(uid, peer_id):
    cur.execute("DELETE FROM bans WHERE user_id=? AND peer_id=?", (uid, peer_id))
    conn.commit()

def add_gban(uid, reason):
    cur.execute("INSERT OR REPLACE INTO gban VALUES (?,?,?)", (uid, reason, int(time.time())))
    conn.commit()

def remove_gban(uid):
    cur.execute("DELETE FROM gban WHERE user_id=?", (uid,))
    conn.commit()

def get_banwords():
    cur.execute("SELECT word FROM banwords")
    return [row[0] for row in cur.fetchall()]

def add_banword(word):
    cur.execute("INSERT OR IGNORE INTO banwords VALUES (?)", (word.lower(),))
    conn.commit()

def remove_banword(word):
    cur.execute("DELETE FROM banwords WHERE word=?", (word.lower(),))
    conn.commit()

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

def is_chat_banned(peer_id):
    cur.execute("SELECT 1 FROM chats WHERE peer_id=? AND server='banned'", (peer_id,))
    return cur.fetchone() is not None

# VK
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

def get_mention(uid):
    nick = get_nick(uid)
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

def get_all_members(peer_id):
    try:
        members = vk.messages.getConversationMembers(peer_id=peer_id)
        return [m['member_id'] for m in members['items'] if m['member_id'] > 0]
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

def get_bug_receivers():
    cur.execute("SELECT user_id FROM bug_receivers")
    return [row[0] for row in cur.fetchall()]

def add_bug_receiver(uid):
    cur.execute("INSERT OR IGNORE INTO bug_receivers VALUES (?)", (uid,))
    conn.commit()

def remove_bug_receiver(uid):
    cur.execute("DELETE FROM bug_receivers WHERE user_id=?", (uid,))
    conn.commit()

# Список всех чатов сервера
server_chats = []

def add_server_chat(peer_id):
    if peer_id not in server_chats:
        server_chats.append(peer_id)
        cur.execute("INSERT OR REPLACE INTO chats (peer_id, server) VALUES (?,?)", (peer_id, 'server'))
        conn.commit()

def remove_server_chat(peer_id):
    if peer_id in server_chats:
        server_chats.remove(peer_id)
        cur.execute("DELETE FROM chats WHERE peer_id=?", (peer_id,))
        conn.commit()

def get_server_chats():
    cur.execute("SELECT peer_id FROM chats WHERE server='server'")
    return [row[0] for row in cur.fetchall()]

# ==================== ГЛАВНЫЙ ОБРАБОТЧИК ====================
print("🤖 BLACK FIB BOT ЗАПУЩЕН!")
print(f"👑 Владелец: @id{OWNER_ID}")
print("✅ Все команды загружены")

def handle_message(event):
    text = event.text.strip()
    peer = event.peer_id
    uid = event.user_id
    msg_id = event.message_id
    cmd = text.split()[0].lower() if text else ''
    args = text.split()[1:] if len(text.split()) > 1 else []
    
    # Проверка на мут и бан
    if is_muted(uid, peer) and not has_rights(uid, 'moder'):
        send(peer, "🔇 Вы замучены и не можете писать!", msg_id)
        return
    if is_banned(uid, peer) and not has_rights(uid, 'moder'):
        send(peer, "🔒 Вы забанены в этой беседе!", msg_id)
        return
    if is_gbanned(uid) and not has_rights(uid, 'zam'):
        send(peer, "🌍 Вы в глобальном бане!", msg_id)
        return
    
    # Фильтр мата
    if get_setting(peer, 'filter_enabled', 1):
        banwords = get_banwords()
        for word in banwords:
            if word.lower() in text.lower():
                send(peer, f"🚫 Запрещенное слово: {word}", msg_id)
                return
    
    # ==================== START ====================
    if cmd == '/start':
        if uid == OWNER_ID:
            set_role(OWNER_ID, 'head')
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

💚 **МОДЕРАТОРЫ:**
/kick, /mute, /unmute, /warn, /unwarn, /getban, /getwarn
/warnhistory, /staff, /setnick, /removenick, /nlist, /nonick
/getnick, /alt, /getacc, /warnlist, /clear, /getmute, /mutelist, /delete

💙 **СТАРШИЕ МОДЕРАТОРЫ:**
/ban, /unban, /addmoder, /removerole, /zov, /online, /banlist, /onlinelist, /inactivelist

➡️ **ПРОДОЛЖЕНИЕ: /help2""")
        return
    
    if cmd == '/help2':
        send(peer, """📋 **BLACK FIB BOT - ПРОДОЛЖЕНИЕ**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 **АДМИНИСТРАТОРЫ:**
/skick, /quiet, /sban, /sunban, /addsenmoder, /bug
/rnickall, /srnick, /ssetnick, /srrole, /srole

🟡 **СТАРШИЕ АДМИНИСТРАТОРЫ:**
/addadmin, /settings, /filter, /szov, /serverinfo, /rkick

🔴 **ВЛАДЕЛЕЦ БЕСЕДЫ:**
/type, /leave, /editowner, /pin, /unpin, /clearwarn
/rroleall, /addsenadm, /masskick, /invite, /antiflood, /welcometext, /welcometextdelete

⚜️ **ЗАМ.РУКОВОДИТЕЛЯ:**
/gban, /gunban, /sync, /gbanlist, /banwords, /gbanpl, /gunbanpl, /addowner

👑 **РУКОВОДИТЕЛЬ БОТА:**
/server, /addword, /delword, /gremoverole, /news, /addzam
/banid, /unbanid, /clearchat, /infoid, /addbug, /listchats, /adddev, /delbug

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ АКТИВАЦИЯ: /start
👑 ВЛАДЕЛЕЦ: https://vk.com/id631833072""")
        return
    
    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    if cmd == '/info':
        send(peer, "🔗 **Официальные ресурсы бота:**\nhttps://vk.com/club229320501\n👑 Владелец: https://vk.com/id631833072")
        return
    
    if cmd == '/stats':
        target = get_user_id(args[0]) if args else uid
        warns = get_warns(target)
        role = get_role(target)
        nick = get_nick(target) or "Не установлен"
        muted = "Да" if is_muted(target, peer) else "Нет"
        banned = "Да" if is_banned(target, peer) else "Нет"
        send(peer, f"📊 **СТАТИСТИКА** {get_user_name(target)}\n━━━━━━━━━━━━━━━━━━━━\n👑 Роль: {role}\n⚠ Варны: {warns}\n🔇 Мут: {muted}\n🔒 Бан: {banned}\n📝 Ник: {nick}")
        return
    
    if cmd == '/getid':
        target = get_user_id(args[0]) if args else uid
        send(peer, f"🆔 ID пользователя: {target}")
        return
    
    # ==================== МОДЕРАТОРЫ ====================
    if cmd == '/kick' and has_rights(uid, 'moder'):
        if not args:
            send(peer, "❌ Использование: /kick @user [причина]")
            return
        target = get_user_id(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "Не указана"
        if target and kick_chat(peer, target):
            send(peer, f"👢 **ИСКЛЮЧЕН** {get_mention(target)}\n📝 Причина: {reason}")
        else:
            send(peer, "❌ Не удалось исключить пользователя")
        return
    
    if cmd == '/mute' and has_rights(uid, 'moder'):
        if len(args) < 2:
            send(peer, "❌ Использование: /mute @user время [причина]")
            return
        target = get_user_id(args[0])
        minutes = int(args[1])
        reason = " ".join(args[2:]) if len(args) > 2 else "Не указана"
        if target:
            add_mute(target, peer, minutes)
            send(peer, f"🔇 **МУТ {minutes} МИН**\n👤 {get_mention(target)}\n📝 Причина: {reason}")
        return
    
    if cmd == '/unmute' and has_rights(uid, 'moder'):
        if not args:
            send(peer, "❌ Использование: /unmute @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_mute(target, peer)
            send(peer, f"✅ **МУТ СНЯТ** с {get_mention(target)}")
        return
    
    if cmd == '/warn' and has_rights(uid, 'moder'):
        if not args:
            send(peer, "❌ Использование: /warn @user [причина]")
            return
        target = get_user_id(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "Нарушение правил"
        if target:
            count = add_warn(target, uid, peer, reason)
            send(peer, f"⚠ **ВАРН #{count}**\n👤 {get_mention(target)}\n📝 Причина: {reason}")
            if count >= 3:
                add_mute(target, peer, 60)
                send(peer, f"🔇 3 варна = МУТ 60 МИНУТ!")
        return
    
    if cmd == '/unwarn' and has_rights(uid, 'moder'):
        if not args:
            send(peer, "❌ Использование: /unwarn @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_warn(target)
            send(peer, f"✅ **ВАРН СНЯТ** с {get_mention(target)}")
        return
    
    if cmd == '/getban' and has_rights(uid, 'moder'):
        target = get_user_id(args[0]) if args else uid
        cur.execute("SELECT reason, date FROM bans WHERE user_id=? AND peer_id=?", (target, peer))
        res = cur.fetchone()
        if res:
            send(peer, f"🔒 **ИНФО О БАНЕ** {get_mention(target)}\n📝 Причина: {res[0]}\n📅 Дата: {time.ctime(res[1])}")
        else:
            send(peer, f"✅ {get_mention(target)} не забанен")
        return
    
    if cmd == '/getwarn' and has_rights(uid, 'moder'):
        target = get_user_id(args[0]) if args else uid
        warns = get_warns(target)
        send(peer, f"⚠ **АКТИВНЫЕ ВАРНЫ** {get_mention(target)}: {warns}")
        return
    
    if cmd == '/warnhistory' and has_rights(uid, 'moder'):
        target = get_user_id(args[0]) if args else uid
        history = get_warn_history(target)
        if history:
            text = f"📜 **ИСТОРИЯ ВАРНОВ** {get_mention(target)}\n━━━━━━━━━━━━━━━━━━━━\n"
            for admin_id, reason, date in history:
                text += f"• {get_user_name(admin_id)}: {reason} ({time.ctime(date)})\n"
            send(peer, text[:4000])
        else:
            send(peer, f"📜 У {get_mention(target)} нет истории варнов")
        return
    
    if cmd == '/staff' and has_rights(uid, 'moder'):
        cur.execute("SELECT user_id, role FROM users WHERE role != 'user'")
        users = cur.fetchall()
        if users:
            text = "👮 **ПОЛЬЗОВАТЕЛИ С РОЛЯМИ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid, role in users:
                text += f"⭐ {role}: {get_user_name(uid)}\n"
            send(peer, text[:4000])
        else:
            send(peer, "👮 Нет пользователей с ролями")
        return
    
    if cmd == '/setnick' and has_rights(uid, 'moder'):
        if len(args) < 2:
            send(peer, "❌ Использование: /setnick @user ник")
            return
        target = get_user_id(args[0])
        nickname = " ".join(args[1:])
        if target:
            set_nick(target, nickname)
            send(peer, f"✅ **НИК УСТАНОВЛЕН**\n👤 {get_user_name(target)} → {nickname}")
        return
    
    if cmd == '/removenick' and has_rights(uid, 'moder'):
        if not args:
            send(peer, "❌ Использование: /removenick @user")
            return
        target = get_user_id(args[0])
        if target:
            set_nick(target, None)
            send(peer, f"✅ **НИК УДАЛЕН** у {get_mention(target)}")
        return
    
    if cmd == '/nlist' and has_rights(uid, 'moder'):
        cur.execute("SELECT user_id, nick FROM users WHERE nick IS NOT NULL")
        users = cur.fetchall()
        if users:
            text = "📝 **СПИСОК НИКОВ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid, nick in users[:20]:
                text += f"• {nick} → {get_user_name(uid)}\n"
            send(peer, text)
        else:
            send(peer, "📝 Ники не установлены")
        return
    
    if cmd == '/nonick' and has_rights(uid, 'moder'):
        cur.execute("SELECT user_id FROM users WHERE nick IS NULL")
        users = cur.fetchall()
        if users:
            text = "👤 **ПОЛЬЗОВАТЕЛИ БЕЗ НИКОВ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for (uid,) in users[:20]:
                text += f"• {get_user_name(uid)}\n"
            send(peer, text)
        else:
            send(peer, "👤 У всех пользователей есть ники!")
        return
    
    if cmd == '/getnick' and has_rights(uid, 'moder'):
        target = get_user_id(args[0]) if args else uid
        nick = get_nick(target)
        send(peer, f"🔍 **НИК** {get_mention(target)}: {nick if nick else 'Не установлен'}")
        return
    
    if cmd == '/alt' and has_rights(uid, 'moder'):
        send(peer, "🔄 **АЛЬТЕРНАТИВНЫЕ КОМАНДЫ**\n/kick, /mute, /warn, /clear, /ban, /zov")
        return
    
    if cmd == '/getacc' and has_rights(uid, 'moder'):
        if not args:
            send(peer, "❌ Использование: /getacc ник")
            return
        search = " ".join(args).lower()
        cur.execute("SELECT user_id, nick FROM users WHERE nick LIKE ?", (f"%{search}%",))
        res = cur.fetchone()
        if res:
            send(peer, f"🔍 **НАЙДЕН ПОЛЬЗОВАТЕЛЬ**\nНик: {res[1]}\nID: {res[0]}\nИмя: {get_user_name(res[0])}")
        else:
            send(peer, f"❌ Ник '{search}' не найден")
        return
    
    if cmd == '/warnlist' and has_rights(uid, 'moder'):
        cur.execute("SELECT user_id, warns FROM users WHERE warns > 0 ORDER BY warns DESC")
        users = cur.fetchall()
        if users:
            text = "⚠ **СПИСОК ВАРНОВ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid, warns in users[:20]:
                text += f"• {get_user_name(uid)}: {warns} варнов\n"
            send(peer, text)
        else:
            send(peer, "⚠ Нет активных варнов")
        return
    
    if cmd == '/clear' and has_rights(uid, 'moder'):
        count = int(args[0]) if args and args[0].isdigit() else 20
        if clear_messages(peer, count):
            send(peer, f"🧹 **ОЧИЩЕНО {count} СООБЩЕНИЙ**")
        else:
            send(peer, "❌ Ошибка очистки")
        return
    
    if cmd == '/getmute' and has_rights(uid, 'moder'):
        target = get_user_id(args[0]) if args else uid
        cur.execute("SELECT until FROM mutes WHERE user_id=? AND peer_id=?", (target, peer))
        res = cur.fetchone()
        if res and res[0] > int(time.time()):
            remaining = int((res[0] - time.time()) / 60)
            send(peer, f"🔇 **МУТ** {get_mention(target)}: осталось {remaining} мин")
        else:
            send(peer, f"✅ У {get_mention(target)} нет мута")
        return
    
    if cmd == '/mutelist' and has_rights(uid, 'moder'):
        cur.execute("SELECT user_id, until FROM mutes WHERE peer_id=? AND until > ?", (peer, int(time.time())))
        users = cur.fetchall()
        if users:
            text = "🔇 **СПИСОК МУТОВ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid, until in users[:20]:
                remaining = int((until - time.time()) / 60)
                text += f"• {get_user_name(uid)}: {remaining} мин\n"
            send(peer, text)
        else:
            send(peer, "🔇 Нет активных мутов")
        return
    
    if cmd == '/delete' and has_rights(uid, 'moder'):
        if len(args) < 2:
            send(peer, "❌ Использование: /delete @user количество")
            return
        target = get_user_id(args[0])
        count = int(args[1]) if args[1].isdigit() else 20
        if target and delete_user_messages(peer, target, count):
            send(peer, f"🗑 **УДАЛЕНО {count} СООБЩЕНИЙ** от {get_mention(target)}")
        else:
            send(peer, "❌ Ошибка удаления")
        return
    
    # ==================== СТАРШИЕ МОДЕРАТОРЫ ====================
    if cmd == '/ban' and has_rights(uid, 'senmoder'):
        if not args:
            send(peer, "❌ Использование: /ban @user [причина]")
            return
        target = get_user_id(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "Не указана"
        if target:
            add_ban(target, peer, reason)
            kick_chat(peer, target)
            send(peer, f"🔨 **БАН В БЕСЕДЕ**\n👤 {get_mention(target)}\n📝 Причина: {reason}")
        return
    
    if cmd == '/unban' and has_rights(uid, 'senmoder'):
        if not args:
            send(peer, "❌ Использование: /unban @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_ban(target, peer)
            send(peer, f"✅ **РАЗБАНЕН** {get_mention(target)}")
        return
    
    if cmd == '/addmoder' and has_rights(uid, 'senmoder'):
        if not args:
            send(peer, "❌ Использование: /addmoder @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'moder')
            send(peer, f"✅ **ВЫДАНА РОЛЬ МОДЕРАТОРА**\n👤 {get_mention(target)}")
        return
    
    if cmd == '/removerole' and has_rights(uid, 'senmoder'):
        if not args:
            send(peer, "❌ Использование: /removerole @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'user')
            send(peer, f"✅ **РОЛЬ ЗАБРАНА** у {get_mention(target)}")
        return
    
    if cmd == '/zov' and has_rights(uid, 'senmoder'):
        members = get_all_members(peer)
        mentions = [f"@id{uid}" for uid in members[:50]]
        send(peer, "🔔 **ВНИМАНИЕ! СРОЧНОЕ СООБЩЕНИЕ!**\n" + " ".join(mentions))
        return
    
    if cmd == '/online' and has_rights(uid, 'senmoder'):
        online = get_online_members(peer)
        if online:
            mentions = [f"@id{uid}" for uid in online[:30]]
            send(peer, "🟢 **ПОЛЬЗОВАТЕЛИ ОНЛАЙН**\n" + " ".join(mentions))
        else:
            send(peer, "🟢 Онлайн пользователей нет")
        return
    
    if cmd == '/banlist' and has_rights(uid, 'senmoder'):
        cur.execute("SELECT user_id, reason FROM bans WHERE peer_id=?", (peer,))
        users = cur.fetchall()
        if users:
            text = "🔨 **ЗАБАНЕННЫЕ В БЕСЕДЕ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid, reason in users[:20]:
                text += f"• {get_user_name(uid)}: {reason}\n"
            send(peer, text)
        else:
            send(peer, "🔨 В беседе нет забаненных")
        return
    
    if cmd == '/onlinelist' and has_rights(uid, 'senmoder'):
        online = get_online_members(peer)
        if online:
            names = [get_user_name(uid) for uid in online[:30]]
            text = f"🟢 **ОНЛАЙН ПОЛЬЗОВАТЕЛИ** ({len(names)})\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(names)
            send(peer, text)
        else:
            send(peer, "🟢 Онлайн пользователей нет")
        return
    
    if cmd == '/inactivelist' and has_rights(uid, 'senmoder'):
        send(peer, "📊 Функция списка неактивных в разработке")
        return
    
    # ==================== АДМИНИСТРАТОРЫ ====================
    if cmd == '/skick' and has_rights(uid, 'admin'):
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
    
    if cmd == '/quiet' and has_rights(uid, 'admin'):
        current = get_setting(peer, 'quiet', 0)
        set_setting(peer, 'quiet', 1 - current)
        status = "ВКЛЮЧЕН" if not current else "ВЫКЛЮЧЕН"
        send(peer, f"🔇 **РЕЖИМ ТИШИНЫ {status}**")
        return
    
    if cmd == '/sban' and has_rights(uid, 'admin'):
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
    
    if cmd == '/sunban' and has_rights(uid, 'admin'):
        if not args:
            send(peer, "❌ Использование: /sunban @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_gban(target)
            send(peer, f"✅ **СУПЕР РАЗБАН** для ID{target}")
        return
    
    if cmd == '/addsenmoder' and has_rights(uid, 'admin'):
        if not args:
            send(peer, "❌ Использование: /addsenmoder @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'senmoder')
            send(peer, f"✅ **ВЫДАНА РОЛЬ СТАРШЕГО МОДЕРАТОРА**\n👤 {get_mention(target)}")
        return
    
    if cmd == '/bug' and has_rights(uid, 'admin'):
        if not args:
            send(peer, "❌ Использование: /bug текст ошибки")
            return
        bug_text = " ".join(args)
        for receiver in get_bug_receivers():
            send(receiver, f"🐛 **БАГ ОТ {get_user_name(uid)}**\n📝 {bug_text}\n📌 Беседа: {peer}\n👤 Пользователь: @id{uid}")
        send(peer, "✅ **БАГ ОТПРАВЛЕН РАЗРАБОТЧИКУ**")
        return
    
    if cmd == '/rnickall' and has_rights(uid, 'admin'):
        cur.execute("UPDATE users SET nick = NULL")
        conn.commit()
        send(peer, "✅ **ВСЕ НИКИ ОЧИЩЕНЫ В БЕСЕДЕ**")
        return
    
    if cmd == '/srnick' and has_rights(uid, 'admin'):
        if not args:
            send(peer, "❌ Использование: /srnick @user")
            return
        target = get_user_id(args[0])
        if target:
            set_nick(target, None)
            send(peer, f"✅ **НИК УБРАН ВЕЗДЕ** у {get_mention(target)}")
        return
    
    if cmd == '/ssetnick' and has_rights(uid, 'admin'):
        if len(args) < 2:
            send(peer, "❌ Использование: /ssetnick @user ник")
            return
        target = get_user_id(args[0])
        nickname = " ".join(args[1:])
        if target:
            set_nick(target, nickname)
            send(peer, f"✅ **НИК УСТАНОВЛЕН ВЕЗДЕ**\n👤 {get_mention(target)} → {nickname}")
        return
    
    if cmd == '/srrole' and has_rights(uid, 'admin'):
        if not args:
            send(peer, "❌ Использование: /srrole @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'user')
            send(peer, f"✅ **РОЛИ СБРОШЕНЫ ВЕЗДЕ** у {get_mention(target)}")
        return
    
    if cmd == '/srole' and has_rights(uid, 'admin'):
        if len(args) < 2:
            send(peer, "❌ Использование: /srole @user роль")
            return
        target = get_user_id(args[0])
        role = args[1]
        if target and role in ROLES:
            set_role(target, role)
            send(peer, f"✅ **РОЛЬ ВЫДАНА ВЕЗДЕ**\n👤 {get_mention(target)} → {role}")
        return
    
    # ==================== СТАРШИЕ АДМИНИСТРАТОРЫ ====================
    if cmd == '/addadmin' and has_rights(uid, 'senadmin'):
        if not args:
            send(peer, "❌ Использование: /addadmin @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'admin')
            send(peer, f"✅ **ВЫДАНА РОЛЬ АДМИНИСТРАТОРА**\n👤 {get_mention(target)}")
        return
    
    if cmd == '/settings' and has_rights(uid, 'senadmin'):
        quiet = "ВКЛ" if get_setting(peer, 'quiet', 0) else "ВЫКЛ"
        antiflood = "ВКЛ" if get_setting(peer, 'antiflood', 0) else "ВЫКЛ"
        filter_enabled = "ВКЛ" if get_setting(peer, 'filter_enabled', 1) else "ВЫКЛ"
        invite = "ВКЛ" if get_setting(peer, 'invite_enabled', 1) else "ВЫКЛ"
        chat_type = get_setting(peer, 'type', 'players')
        send(peer, f"⚙ **НАСТРОЙКИ БЕСЕДЫ**\n━━━━━━━━━━━━━━━━━━━━\n🔇 Тишина: {quiet}\n🌊 Антифлуд: {antiflood}\n🚫 Фильтр: {filter_enabled}\n👋 Приглашения: {invite}\n📋 Тип: {chat_type}")
        return
    
    if cmd == '/filter' and has_rights(uid, 'senadmin'):
        current = get_setting(peer, 'filter_enabled', 1)
        set_setting(peer, 'filter_enabled', 1 - current)
        status = "ВКЛЮЧЕН" if not current else "ВЫКЛЮЧЕН"
        send(peer, f"🚫 **ФИЛЬТР МАТА {status}**")
        return
    
    if cmd == '/szov' and has_rights(uid, 'senadmin'):
        msg = " ".join(args) if args else "ВНИМАНИЕ! Важное объявление!"
        for chat in get_server_chats():
            send(chat, f"🔔 **ОБЪЯВЛЕНИЕ ОТ АДМИНИСТРАЦИИ**\n━━━━━━━━━━━━━━━━━━━━\n{msg}")
        send(peer, "✅ **СУПЕР-ОПОВЕЩЕНИЕ ОТПРАВЛЕНО**")
        return
    
    if cmd == '/serverinfo' and has_rights(uid, 'senadmin'):
        chats_count = len(get_server_chats())
        send(peer, f"🖥 **ИНФОРМАЦИЯ О СЕРВЕРЕ**\n━━━━━━━━━━━━━━━━━━━━\n📊 Чатов в привязке: {chats_count}\n✅ Бот активен\n👑 Владелец: https://vk.com/id631833072")
        return
    
    if cmd == '/rkick' and has_rights(uid, 'senadmin'):
        send(peer, "⚠ Функция масс-кика приглашенных в разработке")
        return
    
    # ==================== ВЛАДЕЛЕЦ БЕСЕДЫ ====================
    if cmd == '/type' and has_rights(uid, 'owner'):
        if not args:
            send(peer, "❌ Использование: /type 1-4\n1 - Игроки, 2 - Общий, 3 - VIP, 4 - Администрация")
            return
        types = {'1': 'players', '2': 'general', '3': 'vip', '4': 'admin'}
        chat_type = types.get(args[0], 'players')
        set_setting(peer, 'type', chat_type)
        send(peer, f"✅ **ТИП БЕСЕДЫ:** {chat_type}")
        return
    
    if cmd == '/leave' and has_rights(uid, 'owner'):
        current = get_setting(peer, 'leavekick', 0)
        set_setting(peer, 'leavekick', 1 - current)
        status = "ВКЛЮЧЕН" if not current else "ВЫКЛЮЧЕН"
        send(peer, f"🚪 **КИК ПРИ ВЫХОДЕ {status}**")
        return
    
    if cmd == '/editowner' and has_rights(uid, 'owner'):
        if not args:
            send(peer, "❌ Использование: /editowner @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'owner')
            send(peer, f"👑 **ПРАВА ВЛАДЕЛЬЦА ПЕРЕДАНЫ** {get_mention(target)}")
        return
    
    if cmd == '/pin' and has_rights(uid, 'owner'):
        if pin_message(peer, msg_id):
            send(peer, f"📌 **СООБЩЕНИЕ ЗАКРЕПЛЕНО**")
        else:
            send(peer, "❌ Не удалось закрепить (ответьте на сообщение, которое хотите закрепить)")
        return
    
    if cmd == '/unpin' and has_rights(uid, 'owner'):
        if unpin_message(peer):
            send(peer, "📌 **ЗАКРЕПЛЕНИЕ СНЯТО**")
        else:
            send(peer, "❌ Не удалось снять закрепление")
        return
    
    if cmd == '/clearwarn' and has_rights(uid, 'owner'):
        cur.execute("UPDATE users SET warns = 0")
        conn.commit()
        send(peer, "✅ **НАКАЗАНИЯ ВЫШЕДШИМ ПОЛЬЗОВАТЕЛЯМ ОЧИЩЕНЫ**")
        return
    
    if cmd == '/rroleall' and has_rights(uid, 'owner'):
        cur.execute("UPDATE users SET role = 'user' WHERE user_id != ?", (OWNER_ID,))
        conn.commit()
        send(peer, "✅ **ВСЕ РОЛИ В БЕСЕДЕ ОЧИЩЕНЫ**")
        return
    
    if cmd == '/addsenadm' and has_rights(uid, 'owner'):
        if not args:
            send(peer, "❌ Использование: /addsenadm @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'senadmin')
            send(peer, f"✅ **ВЫДАНА РОЛЬ СТАРШЕГО АДМИНИСТРАТОРА**\n👤 {get_mention(target)}")
        return
    
    if cmd == '/masskick' and has_rights(uid, 'owner'):
        members = get_all_members(peer)
        kicked = 0
        for uid in members:
            if get_role(uid) == 'user':
                if kick_chat(peer, uid):
                    kicked += 1
                time.sleep(0.5)
        send(peer, f"⚠️ **МАСС-КИК ВЫПОЛНЕН**\n✅ Кикнуто {kicked} пользователей без роли")
        return
    
    if cmd == '/invite' and has_rights(uid, 'owner'):
        current = get_setting(peer, 'invite_enabled', 1)
        set_setting(peer, 'invite_enabled', 1 - current)
        status = "РАЗРЕШЕНЫ" if not current else "ЗАПРЕЩЕНЫ"
        send(peer, f"👋 **ПРИГЛАШЕНИЯ МОДЕРАТОРАМИ {status}**")
        return
    
    if cmd == '/antiflood' and has_rights(uid, 'owner'):
        current = get_setting(peer, 'antiflood', 0)
        set_setting(peer, 'antiflood', 1 - current)
        status = "ВКЛЮЧЕН" if not current else "ВЫКЛЮЧЕН"
        send(peer, f"🌊 **АНТИФЛУД {status}**")
        return
    
    if cmd == '/welcometext' and has_rights(uid, 'owner'):
        if not args:
            send(peer, "❌ Использование: /welcometext текст приветствия\nИспользуйте {user} для вставки имени")
            return
        wt = " ".join(args)
        set_setting(peer, 'welcometext', wt)
        send(peer, f"✅ **ТЕКСТ ПРИВЕТСТВИЯ УСТАНОВЛЕН**")
        return
    
    if cmd == '/welcometextdelete' and has_rights(uid, 'owner'):
        set_setting(peer, 'welcometext', None)
        send(peer, "🗑 **ТЕКСТ ПРИВЕТСТВИЯ УДАЛЕН**")
        return
    
    # ==================== ЗАМ.РУКОВОДИТЕЛЯ ====================
    if cmd == '/gban' and has_rights(uid, 'zam'):
        if not args:
            send(peer, "❌ Использование: /gban @user [причина]")
            return
        target = get_user_id(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "Глобальный бан"
        if target:
            add_gban(target, reason)
            for chat in get_server_chats():
                kick_chat(chat, target)
            send(peer, f"🌍 **ГЛОБАЛЬНЫЙ БАН**\n👤 {get_mention(target)}\n📝 Причина: {reason}")
        return
    
    if cmd == '/gunban' and has_rights(uid, 'zam'):
        if not args:
            send(peer, "❌ Использование: /gunban @user")
            return
        target = get_user_id(args[0])
        if target:
            remove_gban(target)
            send(peer, f"✅ **ГЛОБАЛЬНЫЙ БАН СНЯТ** с {get_mention(target)}")
        return
    
    if cmd == '/sync' and has_rights(uid, 'zam'):
        send(peer, "✅ **БАЗА ДАННЫХ СИНХРОНИЗИРОВАНА**")
        return
    
    if cmd == '/gbanlist' and has_rights(uid, 'zam'):
        cur.execute("SELECT user_id, reason, date FROM gban")
        users = cur.fetchall()
        if users:
            text = "🌍 **ГЛОБАЛЬНЫЙ БАН-ЛИСТ**\n━━━━━━━━━━━━━━━━━━━━\n"
            for uid, reason, date in users[:20]:
                text += f"• ID{uid}: {reason} ({time.ctime(date)})\n"
            send(peer, text)
        else:
            send(peer, "🌍 Список глобальных банов пуст")
        return
    
    if cmd == '/banwords' and has_rights(uid, 'zam'):
        words = get_banwords()
        if words:
            text = "🚫 **ЗАПРЕЩЕННЫЕ СЛОВА**\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join([f"• {w}" for w in words[:20]])
            send(peer, text)
        else:
            send(peer, "🚫 Список запрещенных слов пуст")
        return
    
    if cmd == '/gbanpl' and has_rights(uid, 'zam'):
        send(peer, "🎮 **БАН В БЕСЕДАХ ИГРОКОВ** (функция в разработке)")
        return
    
    if cmd == '/gunbanpl' and has_rights(uid, 'zam'):
        send(peer, "🎮 **РАЗБАН В БЕСЕДАХ ИГРОКОВ** (функция в разработке)")
        return
    
    if cmd == '/addowner' and has_rights(uid, 'zam'):
        if not args:
            send(peer, "❌ Использование: /addowner @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'owner')
            send(peer, f"👑 **ВЫДАНЫ ПРАВА ВЛАДЕЛЬЦА БЕСЕДЫ**\n👤 {get_mention(target)}")
        return
    
    # ==================== РУКОВОДИТЕЛЬ БОТА ====================
    if cmd == '/server' and has_rights(uid, 'head'):
        add_server_chat(peer)
        send(peer, "✅ **БЕСЕДА ПРИВЯЗАНА К СЕРВЕРУ**")
        return
    
    if cmd == '/addword' and has_rights(uid, 'head'):
        if not args:
            send(peer, "❌ Использование: /addword слово")
            return
        word = args[0].lower()
        add_banword(word)
        send(peer, f"✅ **СЛОВО ДОБАВЛЕНО В ФИЛЬТР**: {word}")
        return
    
    if cmd == '/delword' and has_rights(uid, 'head'):
        if not args:
            send(peer, "❌ Использование: /delword слово")
            return
        word = args[0].lower()
        remove_banword(word)
        send(peer, f"✅ **СЛОВО УДАЛЕНО ИЗ ФИЛЬТРА**: {word}")
        return
    
    if cmd == '/gremoverole' and has_rights(uid, 'head'):
        if not args:
            send(peer, "❌ Использование: /gremoverole @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'user')
            send(peer, f"✅ **ВСЕ РОЛИ СБРОШЕНЫ** у {get_mention(target)}")
        return
    
    if cmd == '/news' and has_rights(uid, 'head'):
        if not args:
            send(peer, "❌ Использование: /news текст новости")
            return
        news = " ".join(args)
        for chat in get_server_chats():
            send(chat, f"📢 **НОВОСТИ ОТ РУКОВОДИТЕЛЯ**\n━━━━━━━━━━━━━━━━━━━━\n{news}")
        send(peer, "✅ **НОВОСТИ ОТПРАВЛЕНЫ ВО ВСЕ ЧАТЫ**")
        return
    
    if cmd == '/addzam' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /addzam @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'zam')
            send(peer, f"✅ **ВЫДАНА РОЛЬ ЗАМ.РУКОВОДИТЕЛЯ**\n👤 {get_mention(target)}")
        return
    
    if cmd == '/banid' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /banid ID_беседы")
            return
        target_peer = int(args[0])
        cur.execute("INSERT OR REPLACE INTO chats (peer_id, server) VALUES (?,?)", (target_peer, 'banned'))
        conn.commit()
        send(peer, f"✅ **БЕСЕДА {target_peer} ЗАБЛОКИРОВАНА В БОТЕ**")
        return
    
    if cmd == '/unbanid' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /unbanid ID_беседы")
            return
        target_peer = int(args[0])
        cur.execute("DELETE FROM chats WHERE peer_id=? AND server='banned'", (target_peer,))
        conn.commit()
        send(peer, f"✅ **БЕСЕДА {target_peer} РАЗБЛОКИРОВАНА**")
        return
    
    if cmd == '/clearchat' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /clearchat ID_беседы")
            return
        target_peer = int(args[0])
        cur.execute("DELETE FROM users WHERE user_id IN (SELECT user_id FROM mutes WHERE peer_id=?)", (target_peer,))
        cur.execute("DELETE FROM mutes WHERE peer_id=?", (target_peer,))
        cur.execute("DELETE FROM bans WHERE peer_id=?", (target_peer,))
        cur.execute("DELETE FROM warn_history WHERE peer_id=?", (target_peer,))
        cur.execute("DELETE FROM settings WHERE peer_id=?", (target_peer,))
        conn.commit()
        send(peer, f"✅ **ЧАТ {target_peer} УДАЛЕН ИЗ БД**")
        return
    
    if cmd == '/infoid' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /infoid @user")
            return
        target = get_user_id(args[0])
        if target:
            cur.execute("SELECT COUNT(DISTINCT peer_id) FROM mutes WHERE user_id=?", (target,))
            mutes_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT peer_id) FROM bans WHERE user_id=?", (target,))
            bans_count = cur.fetchone()[0]
            is_gb = "ДА" if is_gbanned(target) else "НЕТ"
            role = get_role(target)
            send(peer, f"📊 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ**\n━━━━━━━━━━━━━━━━━━━━\n🆔 ID: {target}\n👑 Роль: {role}\n🌍 Глобал бан: {is_gb}\n🔇 Чатов с мутом: {mutes_count}\n🔒 Чатов с баном: {bans_count}")
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
        send(peer, f"📋 **СПИСОК ЧАТОВ СЕРВЕРА**\n━━━━━━━━━━━━━━━━━━━━\nВсего: {len(chats)}\nID: {', '.join(map(str, chats[:10]))}")
        return
    
    if cmd == '/adddev' and uid == OWNER_ID:
        if not args:
            send(peer, "❌ Использование: /adddev @user")
            return
        target = get_user_id(args[0])
        if target:
            set_role(target, 'dev')
            send(peer, f"✅ **ВЫДАНЫ ПРАВА РАЗРАБОТЧИКА**\n👤 {get_mention(target)}")
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

# ==================== ЗАПУСК ====================
print("=" * 50)
print("🤖 BLACK FIB BOT ЗАПУЩЕН!")
print("=" * 50)
print(f"👑 Владелец: @id{OWNER_ID}")
print("✅ ВСЕ КОМАНДЫ ЗАГРУЖЕНЫ")
print("✅ /help - ПОЛНЫЙ СПИСОК")
print("=" * 50)
print("💬 Ожидание сообщений...\n")

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.text:
        try:
            handle_message(event)
        except Exception as e:
            print(f"Ошибка: {e}")
            send(event.peer_id, f"❌ Ошибка: {str(e)[:100]}")
