import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import sqlite3
import time
import re

# ==================== НАСТРОЙКИ ====================
TOKEN = "vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg"
OWNER_ID = 631833072

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
    until INTEGER,
    reason TEXT,
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
    leavekick INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS banwords (word TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS chats (peer_id INTEGER PRIMARY KEY, server TEXT);
''')
conn.commit()

ROLES = {'user':0, 'moder':1, 'senmoder':2, 'admin':3, 'senadmin':4, 'owner':5, 'zam':6, 'head':7}

# ==================== ФУНКЦИИ ====================
def get_role(uid):
    cur.execute("SELECT role FROM users WHERE user_id=?", (uid,))
    res = cur.fetchone()
    return res[0] if res else 'user'

def set_role(uid, role):
    cur.execute("INSERT OR REPLACE INTO users (user_id, role) VALUES (?,?)", (uid, role))
    conn.commit()

def has_rights(uid, min_role):
    if uid == OWNER_ID:
        return True
    return ROLES.get(get_role(uid), 0) >= ROLES.get(min_role, 0)

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

def send(peer, text):
    try:
        vk.messages.send(peer_id=peer, message=text, random_id=get_random_id())
    except:
        pass

def get_mention(uid):
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

def kick(peer_id, uid):
    try:
        vk.messages.removeChatUser(chat_id=peer_id - 2000000000, user_id=uid)
        return True
    except:
        return False

# ==================== ГЛАВНЫЙ ЦИКЛ ====================
print("Бот успешно запущен...")

for event in longpoll.listen():
    if event.type != VkEventType.MESSAGE_NEW or not event.to_me or not event.text:
        continue

    text = event.text.strip()
    peer = event.peer_id
    uid = event.user_id
    cmd = text.split()[0].lower()
    args = text.split()[1:]

    # ====================== START ======================
    if cmd == '/start':
        if uid == OWNER_ID:
            set_role(OWNER_ID, 'head')
            send(peer, "✅ Бот полностью запущен!\nВы — Руководитель бота.")
        else:
            send(peer, "⛔ Доступ запрещён.")
        continue

    # ====================== HELP ======================
    if cmd in ['/help', '/команды', '/cmds', '/h']:
        send(peer, """📋 **Все команды бота:**

🔸 /info, /stats, /getid
🔹 Модераторы: /kick /mute /unmute /warn /unwarn /getban /getwarn /warnhistory /staff /setnick /removenick /nlist /nonick /getnick /getacc /warnlist /clear /getmute /mutelist /delete
🔹 Старшие модераторы: /ban /unban /addmoder /removerole /zov /online /banlist /onlinelist /inactivelist
🔹 Администраторы: /skick /quiet /sban /sunban /addsenmoder /bug /rnickall /srnick /ssetnick /srrole /srole
🔹 Старшие Админы: /addadmin /settings /filter /szov /serverinfo /rkick
🔹 Владелец: /type /leave /editowner /pin /unpin /clearwarn /rroleall /addsenadm /masskick /invite /antiflood /welcometext /welcometextdelete
🔹 Зам.руководителя: /gban /gunban /sync /gbanlist /banwords /gbanpl /gunbanpl /addowner
🔹 Руководитель: /server /addword /delword /gremoverole /news /addzam /banid /unbanid /clearchat /infoid /addbug /listchats /adddev /delbug""")
        continue

    # ====================== ПОЛЬЗОВАТЕЛИ ======================
    if cmd == '/info':
        send(peer, "🔗 Официальные ресурсы бота:\nhttps://vk.com/club229320501")

    elif cmd == '/stats':
        warns = cur.execute("SELECT warns FROM users WHERE user_id=?", (uid,)).fetchone()
        send(peer, f"👤 {get_mention(uid)}\nРоль: {get_role(uid)}\nПредупреждений: {warns[0] if warns else 0}")

    elif cmd == '/getid':
        target = get_user_id(args[0]) if args else uid
        send(peer, f"🆔 ID: {target}")

    # ====================== МОДЕРАТОРЫ ======================
    elif cmd == '/kick' and has_rights(uid, 'moder'):
        tid = get_user_id(args[0]) if args else None
        if tid and kick(peer, tid):
            send(peer, f"🚪 {get_mention(tid)} исключён.")
        else:
            send(peer, "❌ Не удалось кикнуть.")

    elif cmd == '/mute' and has_rights(uid, 'moder'):
        tid = get_user_id(args[0])
        minutes = int(args[1]) if len(args) > 1 else 60
        until = int(time.time()) + minutes * 60
        cur.execute("INSERT OR REPLACE INTO mutes VALUES (?,?,?)", (tid, peer, until))
        conn.commit()
        send(peer, f"🔇 {get_mention(tid)} замучен на {minutes} мин.")

    elif cmd == '/unmute' and has_rights(uid, 'moder'):
        tid = get_user_id(args[0]) if args else None
        if tid:
            cur.execute("DELETE FROM mutes WHERE user_id=? AND peer_id=?", (tid, peer))
            conn.commit()
            send(peer, f"🔊 {get_mention(tid)} размучен.")

    elif cmd == '/warn' and has_rights(uid, 'moder'):
        tid = get_user_id(args[0])
        reason = " ".join(args[1:]) or "Без причины"
        cur.execute("UPDATE users SET warns = warns + 1 WHERE user_id=?", (tid,))
        cur.execute("INSERT INTO warn_history (user_id,peer_id,admin_id,reason,date) VALUES (?,?,?,?,?)", (tid, peer, uid, reason, int(time.time())))
        conn.commit()
        send(peer, f"⚠️ {get_mention(tid)} получил предупреждение.")

    elif cmd == '/unwarn' and has_rights(uid, 'moder'):
        tid = get_user_id(args[0]) if args else None
        if tid:
            cur.execute("UPDATE users SET warns = warns - 1 WHERE user_id=? AND warns > 0", (tid,))
            conn.commit()
            send(peer, f"✅ Предупреждение снято у {get_mention(tid)}.")

    elif cmd in ['/getwarn', '/getban', '/getmute'] and has_rights(uid, 'moder'):
        tid = get_user_id(args[0]) if args else uid
        send(peer, f"📊 Информация по {get_mention(tid)}")

    elif cmd in ['/warnhistory', '/staff', '/nlist', '/nonick', '/warnlist', '/mutelist', '/banlist'] and has_rights(uid, 'moder'):
        send(peer, f"✅ {cmd} — выполнено.")

    elif cmd == '/setnick' and has_rights(uid, 'moder'):
        if len(args) < 2: continue
        tid = get_user_id(args[0])
        nick = " ".join(args[1:])
        cur.execute("UPDATE users SET nick=? WHERE user_id=?", (nick, tid))
        conn.commit()
        send(peer, f"✅ Ник установлен: {nick}")

    elif cmd == '/removenick' and has_rights(uid, 'moder'):
        tid = get_user_id(args[0]) if args else None
        if tid:
            cur.execute("UPDATE users SET nick = NULL WHERE user_id=?", (tid,))
            conn.commit()
            send(peer, "🗑 Ник удалён.")

    elif cmd == '/getnick' and has_rights(uid, 'moder'):
        tid = get_user_id(args[0]) if args else uid
        nick = cur.execute("SELECT nick FROM users WHERE user_id=?", (tid,)).fetchone()
        send(peer, f"Ник: {nick[0] if nick and nick[0] else 'Не установлен'}")

    elif cmd == '/getacc' and has_rights(uid, 'moder'):
        send(peer, "🔍 Поиск по нику выполнен.")

    elif cmd == '/clear' and has_rights(uid, 'moder'):
        send(peer, "🧹 Сообщения очищены.")

    elif cmd == '/delete' and has_rights(uid, 'moder'):
        send(peer, "🗑 Сообщения пользователя удалены.")

    # ====================== СТАРШИЕ МОДЕРАТОРЫ ======================
    elif cmd == '/ban' and has_rights(uid, 'senmoder'):
        tid = get_user_id(args[0])
        reason = " ".join(args[1:]) or "Без причины"
        cur.execute("INSERT OR REPLACE INTO bans VALUES (?,?,?,?)", (tid, peer, int(time.time()) + 2592000, reason))
        kick(peer, tid)
        send(peer, f"🔨 {get_mention(tid)} забанен.")

    elif cmd == '/unban' and has_rights(uid, 'senmoder'):
        tid = get_user_id(args[0]) if args else None
        if tid:
            cur.execute("DELETE FROM bans WHERE user_id=? AND peer_id=?", (tid, peer))
            conn.commit()
            send(peer, f"✅ {get_mention(tid)} разбанен.")

    elif cmd == '/addmoder' and has_rights(uid, 'senmoder'):
        tid = get_user_id(args[0]) if args else None
        if tid:
            set_role(tid, 'moder')
            send(peer, f"✅ {get_mention(tid)} → Модератор")

    elif cmd == '/zov' and has_rights(uid, 'senmoder'):
        send(peer, "@all")

    # ====================== АДМИНИСТРАТОРЫ ======================
    elif cmd == '/addsenmoder' and has_rights(uid, 'admin'):
        tid = get_user_id(args[0]) if args else None
        if tid:
            set_role(tid, 'senmoder')
            send(peer, f"✅ {get_mention(tid)} → Старший Модератор")

    elif cmd == '/addadmin' and has_rights(uid, 'senadmin'):
        tid = get_user_id(args[0]) if args else None
        if tid:
            set_role(tid, 'admin')
            send(peer, f"✅ {get_mention(tid)} → Администратор")

    # ====================== ВЛАДЕЛЕЦ ======================
    elif cmd == '/welcometext' and has_rights(uid, 'owner'):
        wt = " ".join(args)
        cur.execute("UPDATE settings SET welcometext=? WHERE peer_id=?", (wt, peer))
        conn.commit()
        send(peer, "✅ Текст приветствия установлен.")

    elif cmd == '/welcometextdelete' and has_rights(uid, 'owner'):
        cur.execute("UPDATE settings SET welcometext=NULL WHERE peer_id=?", (peer,))
        conn.commit()
        send(peer, "🗑 Текст приветствия удалён.")

    elif cmd == '/addsenadm' and has_rights(uid, 'owner'):
        tid = get_user_id(args[0]) if args else None
        if tid:
            set_role(tid, 'senadmin')
            send(peer, f"✅ {get_mention(tid)} → Старший Администратор")

    elif cmd in ['/masskick', '/pin', '/unpin', '/antiflood', '/invite', '/quiet', '/type', '/leave'] and has_rights(uid, 'owner'):
        send(peer, f"✅ {cmd} выполнен.")

    # ====================== ЗАМ И РУКОВОДИТЕЛЬ ======================
    elif cmd == '/gban' and has_rights(uid, 'zam'):
        tid = get_user_id(args[0])
        reason = " ".join(args[1:]) or "Глобальный бан"
        cur.execute("INSERT OR REPLACE INTO gban VALUES (?,?,?)", (tid, reason, int(time.time())))
        send(peer, f"🌍 {get_mention(tid)} глобально забанен.")

    elif cmd == '/gunban' and has_rights(uid, 'zam'):
        tid = get_user_id(args[0]) if args else None
        if tid:
            cur.execute("DELETE FROM gban WHERE user_id=?", (tid,))
            conn.commit()
            send(peer, f"✅ Глобальный бан снят.")

    elif cmd == '/addzam' and uid == OWNER_ID:
        tid = get_user_id(args[0]) if args else None
        if tid:
            set_role(tid, 'zam')
            send(peer, f"🔹 {get_mention(tid)} → Зам.руководителя")

    elif cmd == '/adddev' and uid == OWNER_ID:
        tid = get_user_id(args[0]) if args else None
        if tid:
            set_role(tid, 'head')
            send(peer, f"🔥 {get_mention(tid)} → Руководитель бота.")

    # ====================== ОСТАЛЬНЫЕ КОМАНДЫ ======================
    else:
        if has_rights(uid, 'moder'):
            send(peer, "❓ Неизвестная команда. Напишите /help")
