import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import sqlite3
from datetime import datetime, timedelta
import re
import time

# ============= КОНФИГ =============
TOKEN = 'vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg'
OWNER_ID = 905815597  # ТВОЙ ID

# База данных
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()

# Таблицы
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER, chat_id INTEGER, warns INTEGER DEFAULT 0,
    mute TEXT, ban INTEGER DEFAULT 0, role TEXT DEFAULT 'user',
    nick TEXT, joined TEXT, last_active TEXT, PRIMARY KEY (user_id, chat_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY, activated INTEGER DEFAULT 0
)''')

c.execute('''CREATE TABLE IF NOT EXISTS badwords (
    word TEXT PRIMARY KEY
)''')

c.execute('''CREATE TABLE IF NOT EXISTS bans (
    user_id INTEGER, chat_id INTEGER, admin_id INTEGER, reason TEXT, date TEXT,
    PRIMARY KEY (user_id, chat_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS global_bans (
    user_id INTEGER PRIMARY KEY, admin_id INTEGER, reason TEXT, date TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS warn_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, chat_id INTEGER, admin_id INTEGER, reason TEXT, date TEXT
)''')

# Добавляем маты
for w in ['сука', 'блядь', 'хуй', 'пизда', 'ебать', 'жопа', 'пидор', 'мудак']:
    c.execute("INSERT OR IGNORE INTO badwords (word) VALUES (?)", (w,))

c.execute("INSERT OR IGNORE INTO users (user_id, chat_id, role) VALUES (?, ?, ?)", (OWNER_ID, -1, 'glav'))
conn.commit()

print("БОТ ЗАПУЩЕН")
print(f"ВЛАДЕЛЕЦ: {OWNER_ID}")

# Подключение к ВК
vk = vk_api.VkApi(token=TOKEN).get_api()
longpoll = vk_api.VkLongPoll(vk_api.VkApi(token=TOKEN))

# ============= ФУНКЦИИ =============
def send(peer, text):
    try:
        vk.messages.send(peer_id=peer, message=text, random_id=get_random_id())
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
    levels = {'user':0, 'moderator':1, 'admin':2, 'owner':3, 'zamglav':6, 'glav':7}
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
            c.execute("UPDATE users SET mute=NULL WHERE user_id=? AND chat_id=?", (uid, cid))
            conn.commit()
        except:
            pass
    return False

def is_banned(uid, cid):
    r = c.execute("SELECT ban FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    return r and r[0] == 1

def is_global_banned(uid):
    return c.execute("SELECT * FROM global_bans WHERE user_id=?", (uid,)).fetchone() is not None

def register_user(uid, cid):
    c.execute("INSERT OR IGNORE INTO users (user_id, chat_id, joined, last_active) VALUES (?,?,?,?)",
              (uid, cid, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def get_chat_users(cid):
    try:
        chat = vk.messages.getConversationMembers(peer_id=2000000000 + cid)
        return [m['member_id'] for m in chat['items'] if m['member_id'] > 0]
    except:
        return []

def extract_id(text):
    ids = re.findall(r'id(\d+)', text)
    return int(ids[0]) if ids else None

def get_all_chats():
    return [row[0] for row in c.execute("SELECT chat_id FROM chats WHERE activated=1").fetchall()]

def add_warn(cid, uid, admin, reason):
    w = c.execute("SELECT warns FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    warns = (w[0] if w else 0) + 1
    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, warns) VALUES (?,?,?)", (uid, cid, warns))
    c.execute("INSERT INTO warn_history (user_id, chat_id, admin_id, reason, date) VALUES (?,?,?,?,?)",
              (uid, cid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    send(2000000000 + cid, f"⚠️ {get_name(uid)} | ВАРН {warns}/3\n📝 {reason}")
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
    send(2000000000 + cid, f"🔇 {get_name(uid)} | МУТ {minutes} мин\n📝 {reason}")

def kick_user(cid, uid, admin, reason):
    try:
        vk.messages.removeChatUser(chat_id=cid, user_id=uid)
        send(2000000000 + cid, f"👢 {get_name(uid)} | КИК\n📝 {reason}")
    except:
        pass

def ban_user(cid, uid, admin, reason):
    c.execute("INSERT OR REPLACE INTO bans (user_id, chat_id, admin_id, reason, date) VALUES (?,?,?,?,?)",
              (uid, cid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    c.execute("UPDATE users SET ban=1 WHERE user_id=? AND chat_id=?", (uid, cid))
    conn.commit()
    try:
        vk.messages.removeChatUser(chat_id=cid, user_id=uid)
        send(2000000000 + cid, f"🚫 {get_name(uid)} | БАН\n📝 {reason}")
    except:
        pass

def unban_user(cid, uid, admin):
    c.execute("DELETE FROM bans WHERE user_id=? AND chat_id=?", (uid, cid))
    c.execute("UPDATE users SET ban=0 WHERE user_id=? AND chat_id=?", (uid, cid))
    conn.commit()
    send(2000000000 + cid, f"✅ {get_name(uid)} | РАЗБАНЕН")

def global_ban(uid, admin, reason):
    c.execute("INSERT OR REPLACE INTO global_bans (user_id, admin_id, reason, date) VALUES (?,?,?,?)",
              (uid, admin, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    for chat in get_all_chats():
        try:
            vk.messages.removeChatUser(chat_id=chat, user_id=uid)
        except:
            pass
    send(OWNER_ID, f"🌐 {get_name(uid)} | ГЛОБАЛЬНЫЙ БАН\n📝 {reason}")

def global_unban(uid, admin):
    c.execute("DELETE FROM global_bans WHERE user_id=?", (uid,))
    conn.commit()
    send(OWNER_ID, f"🌐 {get_name(uid)} | ГЛОБАЛЬНЫЙ РАЗБАН")

def get_ban_info(uid, cid):
    ban = c.execute("SELECT admin_id, reason, date FROM bans WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    if ban:
        return f"Забанил: {get_name(ban[0])}\nПричина: {ban[1]}\nДата: {ban[2][:16]}"
    return "НЕ ЗАБАНЕН"

def get_global_ban_info(uid):
    ban = c.execute("SELECT admin_id, reason, date FROM global_bans WHERE user_id=?", (uid,)).fetchone()
    if ban:
        return f"Забанил: {get_name(ban[0])}\nПричина: {ban[1]}\nДата: {ban[2][:16]}"
    return "НЕ ЗАБАНЕН ГЛОБАЛЬНО"

print("БОТ РАБОТАЕТ, ЖДУ КОМАНД...")
print("=" * 50)

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
        
        if cid:
            c.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (cid,))
            register_user(uid, cid)
            c.execute("UPDATE users SET last_active=? WHERE user_id=? AND chat_id=?", 
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
            
            activated = c.execute("SELECT activated FROM chats WHERE chat_id=?", (cid,)).fetchone()
            if not activated or activated[0] == 0:
                if msg == '/start' and uid == OWNER_ID:
                    c.execute("UPDATE chats SET activated=1 WHERE chat_id=?", (cid,))
                    conn.commit()
                    send(peer, "✅ БОТ АКТИВИРОВАН!\n/help - список команд")
                continue
            
            if not msg.startswith('/'):
                for w in c.execute("SELECT word FROM badwords").fetchall():
                    if w[0].lower() in msg_lower:
                        try:
                            vk.messages.delete(message_ids=[event.message_id], delete_for_all=1)
                        except:
                            pass
                        add_warn(cid, uid, 0, f"Мат: {w[0]}")
                        break
        
        # ============= КОМАНДЫ =============
        
        if msg == '/help':
            send(peer, """📚 ВСЕ КОМАНДЫ:
━━━━━━━━━━━━━━━━━━━━
/info - информация
/stats @user - статистика
/getid - узнать ID
/test - проверка

/kick @user - кик
/mute @user 30 - мут
/unmute @user - размут
/warn @user - варн
/unwarn @user - снять варн
/clear 10 - очистка
/staff - список админов
/setnick @user ник - ник
/nlist - список ников
/warnlist - список варнов
/mutelist - список мутов

/ban @user - бан
/unban @user - разбан
/addmoder @user - дать модера
/removerole @user - забрать роль
/zov - @всех
/banlist - список банов
/getban @user - инфо о бане
/checkban @user - проверить бан
/addadmin @user - дать админа

/gban @user - глобальный бан
/gunban @user - глобальный разбан
/gbanlist - список глобальных банов
/checkgban @user - проверить глобальный бан

/addword слово - добавить слово
/delword слово - удалить слово
/banwords - список слов
/sync - синхронизация
━━━━━━━━━━━━━━━━━━━━
👑 ВЛАДЕЛЕЦ: АНДРЕЙ""")
        
        elif msg == '/info':
            send(peer, "🤖 БОТ v4.0\n👑 ВЛАДЕЛЕЦ: АНДРЕЙ\n/help - ВСЕ КОМАНДЫ")
        
        elif msg.startswith('/stats'):
            target = extract_id(msg) if '[' in msg else uid
            if target:
                data = c.execute("SELECT warns, mute, role FROM users WHERE user_id=? AND chat_id=?", (target, cid)).fetchone()
                if data:
                    muted = "НЕТ" if not data[1] else f"ДО {data[1][:16]}"
                    send(peer, f"📊 {get_name(target)}\nРоль: {data[2]}\nВарны: {data[0]}/3\nМут: {muted}")
                else:
                    send(peer, f"📊 {get_name(target)}\nВарны: 0/3")
        
        elif msg == '/getid':
            send(peer, f"🆔 ID: {uid}")
        
        elif msg == '/test':
            send(peer, f"✅ БОТ РАБОТАЕТ!\nТВОЙ ID: {uid}")
        
        elif msg.startswith('/kick '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ!")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение"
                    kick_user(cid, target, uid, reason)
                else:
                    send(peer, "❌ /kick @user [причина]")
        
        elif msg.startswith('/mute '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ!")
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
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ!")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("UPDATE users SET mute=NULL WHERE user_id=? AND chat_id=?", (target, cid))
                    conn.commit()
                    send(peer, f"🔊 {get_name(target)} РАЗМУЧЕН")
                else:
                    send(peer, "❌ /unmute @user")
        
        elif msg.startswith('/warn '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ!")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение"
                    add_warn(cid, target, uid, reason)
                else:
                    send(peer, "❌ /warn @user [причина]")
        
        elif msg.startswith('/unwarn '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ!")
            else:
                target = extract_id(msg)
                if target:
                    w = c.execute("SELECT warns FROM users WHERE user_id=? AND chat_id=?", (target, cid)).fetchone()
                    if w and w[0] > 0:
                        c.execute("UPDATE users SET warns=warns-1 WHERE user_id=? AND chat_id=?", (target, cid))
                        conn.commit()
                        send(peer, f"✅ {get_name(target)} | ВАРН СНЯТ")
                    else:
                        send(peer, "❌ НЕТ ВАРНОВ")
                else:
                    send(peer, "❌ /unwarn @user")
        
        elif msg.startswith('/clear '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ!")
            else:
                nums = re.findall(r'(\d+)', msg)
                count = int(nums[0]) if nums else 10
                if count > 100:
                    count = 100
                try:
                    history = vk.messages.getHistory(peer_id=peer, count=count)
                    ids = [m['id'] for m in history['items']]
                    vk.messages.delete(message_ids=ids, delete_for_all=1)
                    send(peer, f"✅ ОЧИЩЕНО {len(ids)} СООБЩЕНИЙ")
                except:
                    send(peer, "❌ ОШИБКА ОЧИСТКИ")
        
        elif msg == '/staff':
            if not cid:
                send(peer, "❌ ТОЛЬКО В БЕСЕДЕ")
            else:
                admins = c.execute("SELECT user_id, role FROM users WHERE chat_id=? AND role != 'user'", (cid,)).fetchall()
                if admins:
                    txt = "👥 АДМИНИСТРАЦИЯ:\n"
                    for a in admins:
                        txt += f"• {get_name(a[0])} - {a[1]}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ НЕТ АДМИНИСТРАЦИИ")
        
        elif msg.startswith('/setnick '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ!")
            else:
                target = extract_id(msg)
                if target:
                    nick = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else None
                    if nick:
                        c.execute("UPDATE users SET nick=? WHERE user_id=? AND chat_id=?", (nick, target, cid))
                        conn.commit()
                        send(peer, f"🏷 {get_name(target)} | НИК: {nick}")
                    else:
                        send(peer, "❌ /setnick @user НИК")
                else:
                    send(peer, "❌ /setnick @user НИК")
        
        elif msg == '/nlist':
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ!")
            else:
                nicks = c.execute("SELECT user_id, nick FROM users WHERE chat_id=? AND nick IS NOT NULL", (cid,)).fetchall()
                if nicks:
                    txt = "🏷 СПИСОК НИКОВ:\n"
                    for n in nicks[:20]:
                        txt += f"• {get_name(n[0])} → {n[1]}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ НЕТ НИКОВ")
        
        elif msg == '/warnlist':
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ!")
            else:
                warned = c.execute("SELECT user_id, warns FROM users WHERE chat_id=? AND warns>0 ORDER BY warns DESC", (cid,)).fetchall()
                if warned:
                    txt = "⚠️ СПИСОК ВАРНОВ:\n"
                    for w in warned:
                        txt += f"• {get_name(w[0])} → {w[1]}/3\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ НЕТ ВАРНОВ")
        
        elif msg == '/mutelist':
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ НЕТ ПРАВ!")
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
                    txt = "🔇 АКТИВНЫЕ МУТЫ:\n"
                    for a in active:
                        left = a[1] - now
                        txt += f"• {get_name(a[0])} → {left.seconds//60} МИН\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ НЕТ МУТОВ")
        
        elif msg.startswith('/ban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! ТРЕБУЕТСЯ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение"
                    ban_user(cid, target, uid, reason)
                else:
                    send(peer, "❌ /ban @user [ПРИЧИНА]")
        
        elif msg.startswith('/unban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! ТРЕБУЕТСЯ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    unban_user(cid, target, uid)
                else:
                    send(peer, "❌ /unban @user")
        
        elif msg.startswith('/addmoder '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! ТРЕБУЕТСЯ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'moderator'))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ТЕПЕРЬ МОДЕРАТОР")
                else:
                    send(peer, "❌ /addmoder @user")
        
        elif msg.startswith('/removerole '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! ТРЕБУЕТСЯ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    if target == OWNER_ID:
                        send(peer, "❌ НЕЛЬЗЯ ЗАБРАТЬ РОЛЬ У ВЛАДЕЛЬЦА БОТА!")
                        continue
                    c.execute("UPDATE users SET role='user' WHERE user_id=? AND chat_id=?", (target, cid))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | РОЛЬ ЗАБРАНА")
                else:
                    send(peer, "❌ /removerole @user")
        
        elif msg == '/zov':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! ТРЕБУЕТСЯ АДМИНИСТРАТОР")
            else:
                users = get_chat_users(cid)
                mentions = [f"[id{u}|{get_name(u)}]" for u in users if u > 0 and u != uid]
                if mentions:
                    for i in range(0, len(mentions), 10):
                        send(peer, ' '.join(mentions[i:i+10]))
                        time.sleep(0.5)
                else:
                    send(peer, "❌ НЕТ ПОЛЬЗОВАТЕЛЕЙ")
        
        elif msg == '/banlist':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! ТРЕБУЕТСЯ АДМИНИСТРАТОР")
            else:
                bans = c.execute("SELECT user_id, reason, date FROM bans WHERE chat_id=?", (cid,)).fetchall()
                if bans:
                    txt = "🚫 СПИСОК БАНОВ:\n"
                    for b in bans[:15]:
                        txt += f"• {get_name(b[0])} → {b[2][:10]}\n  {b[1][:30]}\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ НЕТ БАНОВ")
        
        elif msg.startswith('/getban '):
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ НЕТ ПРАВ! ТРЕБУЕТСЯ АДМИНИСТРАТОР")
            else:
                target = extract_id(msg)
                if target:
                    send(peer, f"🚫 ИНФО О БАНЕ {get_name(target)}:\n{get_ban_info(target, cid)}")
                else:
                    send(peer, "❌ /getban @user")
        
        elif msg.startswith('/checkban '):
            target = extract_id(msg)
            if target:
                send(peer, f"🔍 ПРОВЕРКА БАНА {get_name(target)}:\n{get_ban_info(target, cid) if cid else 'ТОЛЬКО В БЕСЕДЕ'}")
            else:
                send(peer, "❌ /checkban @user")
        
        elif msg.startswith('/addadmin '):
            if not check_perm(uid, cid, 'owner'):
                send(peer, "❌ НЕТ ПРАВ! ТРЕБУЕТСЯ ВЛАДЕЛЕЦ БЕСЕДЫ")
            else:
                target = extract_id(msg)
                if target:
                    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, role) VALUES (?,?,?)", (target, cid, 'admin'))
                    conn.commit()
                    send(peer, f"✅ {get_name(target)} | ТЕПЕРЬ АДМИНИСТРАТОР")
                else:
                    send(peer, "❌ /addadmin @user")
        
        elif msg.startswith('/gban ') or msg.startswith('/gbanpl '):
            if uid != OWNER_ID:
                send(peer, "❌ ТОЛЬКО ВЛАДЕЛЕЦ БОТА!")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Глобальное нарушение"
                    global_ban(target, uid, reason)
                    send(peer, f"🌐 {get_name(target)} | ГЛОБАЛЬНЫЙ БАН\n📝 {reason}")
                else:
                    send(peer, "❌ /gban @user [ПРИЧИНА]")
        
        elif msg.startswith('/gunban ') or msg.startswith('/gunbanpl '):
            if uid != OWNER_ID:
                send(peer, "❌ ТОЛЬКО ВЛАДЕЛЕЦ БОТА!")
            else:
                target = extract_id(msg)
                if target:
                    global_unban(target, uid)
                    send(peer, f"🌐 {get_name(target)} | ГЛОБАЛЬНЫЙ РАЗБАН")
                else:
                    send(peer, "❌ /gunban @user")
        
        elif msg == '/gbanlist':
            if uid != OWNER_ID:
                send(peer, "❌ ТОЛЬКО ВЛАДЕЛЕЦ БОТА!")
            else:
                bans = c.execute("SELECT user_id, reason, date FROM global_bans").fetchall()
                if bans:
                    txt = "🌐 ГЛОБАЛЬНЫЕ БАНЫ:\n"
                    for b in bans:
                        txt += f"• {get_name(b[0])} → {b[2][:10]}\n  {b[1][:30]}\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ НЕТ ГЛОБАЛЬНЫХ БАНОВ")
        
        elif msg.startswith('/checkgban '):
            target = extract_id(msg)
            if target:
                send(peer, f"🌐 ПРОВЕРКА ГЛОБАЛЬНОГО БАНА {get_name(target)}:\n{get_global_ban_info(target)}")
            else:
                send(peer, "❌ /checkgban @user")
        
        elif msg.startswith('/addword '):
            if uid != OWNER_ID:
                send(peer, "❌ ТОЛЬКО ВЛАДЕЛЕЦ БОТА!")
            else:
                word = msg[9:].lower()
                if word:
                    c.execute("INSERT OR IGNORE INTO badwords (word) VALUES (?)", (word,))
                    conn.commit()
                    send(peer, f"✅ СЛОВО '{word}' ДОБАВЛЕНО")
                else:
                    send(peer, "❌ /addword СЛОВО")
        
        elif msg.startswith('/delword '):
            if uid != OWNER_ID:
                send(peer, "❌ ТОЛЬКО ВЛАДЕЛЕЦ БОТА!")
            else:
                word = msg[9:].lower()
                if word:
                    c.execute("DELETE FROM badwords WHERE word=?", (word,))
                    conn.commit()
                    send(peer, f"✅ СЛОВО '{word}' УДАЛЕНО")
                else:
                    send(peer, "❌ /delword СЛОВО")
        
        elif msg == '/banwords':
            if uid != OWNER_ID:
                send(peer, "❌ ТОЛЬКО ВЛАДЕЛЕЦ БОТА!")
            else:
                words = c.execute("SELECT word FROM badwords").fetchall()
                if words:
                    send(peer, "🚫 ЗАПРЕЩЕННЫЕ СЛОВА:\n" + ', '.join([w[0] for w in words]))
                else:
                    send(peer, "✅ НЕТ ЗАПРЕЩЕННЫХ СЛОВ")
        
        elif msg == '/sync':
            if uid != OWNER_ID:
                send(peer, "❌ ТОЛЬКО ВЛАДЕЛЕЦ БОТА!")
            else:
                conn.commit()
                send(peer, "🔄 БАЗА ДАННЫХ СИНХРОНИЗИРОВАНА")
        
        elif msg == '/start' and cid and uid == OWNER_ID:
            c.execute("UPDATE chats SET activated=1 WHERE chat_id=?", (cid,))
            conn.commit()
            send(peer, "✅ БОТ АКТИВИРОВАН В ЭТОЙ БЕСЕДЕ!\n/help - ВСЕ КОМАНДЫ")
        
        elif msg == '/start' and cid and uid != OWNER_ID:
            send(peer, "❌ ТОЛЬКО ВЛАДЕЛЕЦ БОТА МОЖЕТ АКТИВИРОВАТЬ!")
        
        elif not cid and msg and not msg.startswith('/'):
            send(peer, f"🤖 БОТ РАБОТАЕТ!\nТВОЙ ID: {uid}\nКОМАНДЫ: /help\n👑 ВЛАДЕЛЕЦ: АНДРЕЙ")

print("БОТ ОСТАНОВЛЕН")
