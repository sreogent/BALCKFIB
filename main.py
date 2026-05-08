import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import sqlite3
from datetime import datetime, timedelta
import re

# ============= КОНФИГ =============
TOKEN = 'vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg'
OWNER_ID = 631833072

# База данных
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()

# Создание таблиц
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    chat_id INTEGER,
    warns INTEGER DEFAULT 0,
    mute TEXT,
    ban INTEGER DEFAULT 0,
    role TEXT DEFAULT 'user',
    PRIMARY KEY (user_id, chat_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    activated INTEGER DEFAULT 0
)''')

c.execute('''CREATE TABLE IF NOT EXISTS badwords (
    word TEXT PRIMARY KEY
)''')

# Добавляем маты
bad_words = ['сука', 'блядь', 'хуй', 'пизда', 'ебать', 'жопа', 'пидор', 'мудак', 'уебан', 'долбоеб']
for w in bad_words:
    c.execute("INSERT OR IGNORE INTO badwords (word) VALUES (?)", (w,))
conn.commit()

print("БОТ ЗАПУЩЕН")
print("=" * 40)

# Подключение к ВК
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

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
    r = c.execute("SELECT role FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    return r[0] if r else 'user'

def check_perm(uid, cid, need):
    if uid == OWNER_ID:
        return True
    role = get_role(uid, cid)
    lvl = {'user':0, 'moderator':1, 'admin':2, 'owner':3}
    return lvl.get(role,0) >= lvl.get(need,0)

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

def add_warn(cid, uid, admin, reason):
    w = c.execute("SELECT warns FROM users WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
    warns = (w[0] if w else 0) + 1
    c.execute("INSERT OR REPLACE INTO users (user_id, chat_id, warns) VALUES (?,?,?)", (uid, cid, warns))
    conn.commit()
    send(2000000000 + cid, f"⚠️ {get_name(uid)} | ВАРН {warns}/3\nПричина: {reason}\nВыдал: {get_name(admin)}")
    if warns >= 3:
        c.execute("UPDATE users SET ban=1 WHERE user_id=? AND chat_id=?", (uid, cid))
        conn.commit()
        try:
            vk.messages.removeChatUser(chat_id=cid, user_id=uid)
            send(2000000000 + cid, f"🚫 {get_name(uid)} ЗАБАНЕН (3 варна)")
        except:
            pass

def mute_user(cid, uid, minutes, admin, reason):
    till = datetime.now() + timedelta(minutes=minutes)
    c.execute("UPDATE users SET mute=? WHERE user_id=? AND chat_id=?", (till.strftime('%Y-%m-%d %H:%M:%S'), uid, cid))
    conn.commit()
    send(2000000000 + cid, f"🔇 {get_name(uid)} | МУТ {minutes} мин\nПричина: {reason}\nВыдал: {get_name(admin)}")

def kick_user(cid, uid, admin, reason):
    try:
        vk.messages.removeChatUser(chat_id=cid, user_id=uid)
        send(2000000000 + cid, f"👢 {get_name(uid)} | КИК\nПричина: {reason}\nВыдал: {get_name(admin)}")
    except:
        pass

def ban_user(cid, uid, admin, reason):
    c.execute("UPDATE users SET ban=1 WHERE user_id=? AND chat_id=?", (uid, cid))
    conn.commit()
    try:
        vk.messages.removeChatUser(chat_id=cid, user_id=uid)
        send(2000000000 + cid, f"🚫 {get_name(uid)} | БАН\nПричина: {reason}\nВыдал: {get_name(admin)}")
    except:
        pass

def unban_user(cid, uid, admin):
    c.execute("UPDATE users SET ban=0 WHERE user_id=? AND chat_id=?", (uid, cid))
    conn.commit()
    send(2000000000 + cid, f"✅ {get_name(uid)} | РАЗБАНЕН\nАдмин: {get_name(admin)}")

def extract_id(text):
    ids = re.findall(r'id(\d+)', text)
    if ids:
        return int(ids[0])
    nums = re.findall(r'(\d+)', text)
    return int(nums[0]) if nums else None

print("БОТ РАБОТАЕТ, ЖДУ КОМАНД...")
print("=" * 40)

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
        
        # Регистрация
        if cid:
            c.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (cid,))
            c.execute("INSERT OR IGNORE INTO users (user_id, chat_id) VALUES (?,?)", (uid, cid))
            conn.commit()
            
            # Проверка активации бота в беседе
            activated = c.execute("SELECT activated FROM chats WHERE chat_id=?", (cid,)).fetchone()
            if not activated or activated[0] == 0:
                if msg == '/start' and uid == OWNER_ID:
                    c.execute("UPDATE chats SET activated=1 WHERE chat_id=?", (cid,))
                    conn.commit()
                    send(peer, "✅ Бот активирован в этой беседе!")
                elif msg != '/start':
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
                bad = c.execute("SELECT word FROM badwords").fetchall()
                for w in bad:
                    if w[0].lower() in msg_lower:
                        try:
                            vk.messages.delete(message_ids=[event.message_id], delete_for_all=1)
                        except:
                            pass
                        add_warn(cid, uid, 0, f"Мат: {w[0]}")
                        break
        
        # ============= КОМАНДЫ =============
        
        # 👤 ДЛЯ ВСЕХ
        if msg == '/menu':
            send(peer, "🏠 ГЛАВНОЕ МЕНЮ\n/info - информация\n/stats - статистика\n/getid - узнать ID\n/test - проверка")
        
        elif msg == '/info':
            send(peer, "🤖 BLACK FIB BOT v3.0\n👑 Разработчик: Дмитрий\n💬 /menu - меню")
        
        elif msg.startswith('/stats'):
            target = extract_id(msg) if '[' in msg else uid
            data = c.execute("SELECT warns, mute, role FROM users WHERE user_id=? AND chat_id=?", (target, cid)).fetchone()
            if data:
                muted = "НЕТ" if not data[1] else f"ДО {data[1][:16]}"
                send(peer, f"📊 {get_name(target)}\n⭐ Роль: {data[2]}\n⚠️ Варны: {data[0]}/3\n🔇 Мут: {muted}")
            else:
                send(peer, f"📊 {get_name(target)}\n⚠️ Варны: 0/3")
        
        elif msg == '/getid':
            target = extract_id(msg) if '[' in msg else uid
            send(peer, f"🆔 ID: {target}")
        
        elif msg == '/test' or msg == '/ping':
            send(peer, f"✅ Бот работает!\n👤 ID: {uid}")
        
        # 💚 ХЭЛПЕРЫ
        elif msg.startswith('/kick '):
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение"
                    kick_user(cid, target, uid, reason)
                else:
                    send(peer, "❌ /kick @user [причина]")
        
        elif msg.startswith('/mute '):
            if not check_perm(uid, cid, 'moderator'):
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
            if not check_perm(uid, cid, 'moderator'):
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
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                target = extract_id(msg)
                if target:
                    reason = msg.split(' ', 2)[2] if len(msg.split(' ', 2)) > 2 else "Нарушение"
                    add_warn(cid, target, uid, reason)
                else:
                    send(peer, "❌ /warn @user [причина]")
        
        elif msg.startswith('/unwarn '):
            if not check_perm(uid, cid, 'moderator'):
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
            if not check_perm(uid, cid, 'moderator'):
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
                admins = c.execute("SELECT user_id, role FROM users WHERE chat_id=? AND role != 'user'", (cid,)).fetchall()
                if admins:
                    txt = "👥 АДМИНИСТРАЦИЯ:\n"
                    for a in admins:
                        txt += f"• {get_name(a[0])} - {a[1]}\n"
                    send(peer, txt)
                else:
                    send(peer, "❌ Нет администрации")
        
        elif msg == '/warnlist':
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                warned = c.execute("SELECT user_id, warns FROM users WHERE chat_id=? AND warns>0 ORDER BY warns DESC", (cid,)).fetchall()
                if warned:
                    txt = "⚠️ ВАРНЫ:\n"
                    for w in warned:
                        txt += f"• {get_name(w[0])} → {w[1]}/3\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ Нет варнов")
        
        elif msg == '/mutelist':
            if not check_perm(uid, cid, 'moderator'):
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
                    txt = "🔇 МУТЫ:\n"
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
                try:
                    chat = vk.messages.getConversationMembers(peer_id=peer)
                    mentions = ' '.join([f"[id{u['member_id']}|]" for u in chat['items'] if u['member_id'] > 0][:30])
                    send(peer, mentions if mentions else "Нет пользователей")
                except:
                    send(peer, "❌ Ошибка")
        
        elif msg == '/banlist':
            if not check_perm(uid, cid, 'moderator'):
                send(peer, "❌ Нет прав!")
            else:
                bans = c.execute("SELECT user_id, date FROM bans WHERE chat_id=?", (cid,)).fetchall()
                if bans:
                    txt = "🚫 БАНЫ:\n"
                    for b in bans[:15]:
                        txt += f"• {get_name(b[0])} → {b[1][:10]}\n"
                    send(peer, txt)
                else:
                    send(peer, "✅ Нет банов")
        
        # 🟢 АДМИНИСТРАТОРЫ
        elif msg == '/filter':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                current = c.execute("SELECT filter_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET filter_on=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"📝 ФИЛЬТР МАТА {'ВКЛЮЧЕН' if new_val else 'ВЫКЛЮЧЕН'}")
        
        elif msg == '/settings':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                chat = c.execute("SELECT filter_on, quiet_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                if chat:
                    send(peer, f"⚙️ НАСТРОЙКИ\nФильтр: {'✅' if chat[0] else '❌'}\nТишина: {'✅' if chat[1] else '❌'}\n/filter - фильтр\n/quiet - тишина")
                else:
                    send(peer, "⚙️ /filter - фильтр мата\n/quiet - режим тишины")
        
        elif msg == '/quiet':
            if not check_perm(uid, cid, 'admin'):
                send(peer, "❌ Нет прав!")
            else:
                current = c.execute("SELECT quiet_on FROM chats WHERE chat_id=?", (cid,)).fetchone()
                new_val = 0 if (current and current[0] == 1) else 1
                c.execute("UPDATE chats SET quiet_on=? WHERE chat_id=?", (new_val, cid))
                conn.commit()
                send(peer, f"🔇 ТИШИНА {'ВКЛЮЧЕНА' if new_val else 'ВЫКЛЮЧЕНА'}")
        
        elif msg == '/start' and cid and uid == OWNER_ID:
            c.execute("UPDATE chats SET activated=1 WHERE chat_id=?", (cid,))
            conn.commit()
            send(peer, "✅ Бот активирован!")
        
        elif msg == '/help':
            txt = """📚 КОМАНДЫ:
━━━━━━━━━━━━━━━━━━━━
👤 ДЛЯ ВСЕХ:
/info, /stats, /getid, /test

💚 ХЭЛПЕРЫ:
/kick, /mute, /unmute, /warn, /unwarn, /clear, /staff

💙 МОДЕРАТОРЫ:
/ban, /unban, /addmoder, /removerole, /zov, /banlist

🟢 АДМИНИСТРАТОРЫ:
/filter, /quiet, /settings
━━━━━━━━━━━━━━━━━━━━
/start - активация бота в беседе"""
            send(peer, txt)
        
        # ОТВЕТ В ЛС
        elif not cid and msg and not msg.startswith('/'):
            send(peer, f"🤖 Бот работает!\nID: {uid}\nКоманды: /help")
