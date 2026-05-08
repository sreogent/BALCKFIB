import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import sqlite3
from datetime import datetime, timedelta
import re

# Токен сообщества
TOKEN = 'vk1.a.6TizPN4pg1-Fhk95_LrCbP9i3LqBnP_J5D-Y8Us4JN-1J2NIwReHNbyTscHIRlDoTluqgMsZRrHbQvXyJqizcZGoZ-bOzUiAk8v9UMfqVesLgBo-gKM4CCHhfZcZ5AGx4kQ-gubA_Fo2ViRP6o2PK3FHZph2cefAn-4IOydOluHpvYWmqw-KKMnwDa4QYYhB7AC_TJunZ_oApcoXbexZdg'
GROUP_ID = 229320501

# ТВОЙ ID ВК
OWNER_ID = 631833072

# Авторизация
vk = vk_api.VkApi(token=TOKEN)
longpoll = VkLongPoll(vk)

# Подключение к БД
conn = sqlite3.connect('admin_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    chat_type TEXT DEFAULT 'players',
    welcome_text TEXT,
    welcome_enabled INTEGER DEFAULT 0,
    filter_enabled INTEGER DEFAULT 0,
    flood_enabled INTEGER DEFAULT 0,
    quiet_mode INTEGER DEFAULT 0,
    leave_kick INTEGER DEFAULT 0,
    invite_moders INTEGER DEFAULT 0,
    created_date TEXT,
    bot_activated INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    chat_id INTEGER,
    nick TEXT,
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
CREATE TABLE IF NOT EXISTS global_bans (
    user_id INTEGER PRIMARY KEY,
    admin_id INTEGER,
    reason TEXT,
    date TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS filter_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS bug_receivers (
    user_id INTEGER PRIMARY KEY
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_nicks (
    user_id INTEGER,
    chat_id INTEGER,
    nick TEXT,
    set_by INTEGER,
    date TEXT,
    PRIMARY KEY (user_id, chat_id)
)
''')

# Добавляем тебя как владельца бота
cursor.execute('''
    INSERT OR IGNORE INTO users (user_id, chat_id, role, joined_date)
    VALUES (?, ?, ?, ?)
''', (OWNER_ID, -1, 'glav', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

# Добавляем слова в фильтр
words = ["сука", "блядь", "хуй", "пизда", "ебать", "мат"]
for word in words:
    cursor.execute("INSERT OR IGNORE INTO filter_words (word) VALUES (?)", (word,))

conn.commit()

print("✅ База данных готова")
print(f"👑 Владелец бота: [id{OWNER_ID}|Vlad]")
print("🤖 БОТ ЗАПУЩЕН")

# Роли
ROLES = {
    'user': 0, 'moderator': 1, 'seniormoderator': 2, 'admin': 3,
    'senioradmin': 4, 'owner': 5, 'zamglav': 6, 'glav': 7
}

class AdminBot:
    def __init__(self):
        self.commands = {
            '/start': self.cmd_start, '/help': self.cmd_help, '/info': self.cmd_info,
            '/stats': self.cmd_stats, '/getid': self.cmd_getid, '/test': self.cmd_test,
            '/kick': self.cmd_kick, '/mute': self.cmd_mute, '/unmute': self.cmd_unmute,
            '/warn': self.cmd_warn, '/unwarn': self.cmd_unwarn, '/staff': self.cmd_staff,
            '/setnick': self.cmd_setnick, '/nlist': self.cmd_nlist, '/warnlist': self.cmd_warnlist,
            '/mutelist': self.cmd_mutelist, '/clear': self.cmd_clear, '/ban': self.cmd_ban,
            '/unban': self.cmd_unban, '/addmoder': self.cmd_addmoder, '/removerole': self.cmd_removerole,
            '/zov': self.cmd_zov, '/banlist': self.cmd_banlist, '/addadmin': self.cmd_addadmin,
            '/filter': self.cmd_filter, '/quiet': self.cmd_quiet, '/settings': self.cmd_settings,
            '/gban': self.cmd_gban, '/gunban': self.cmd_gunban, '/gbanlist': self.cmd_gbanlist,
            '/addword': self.cmd_addword, '/delword': self.cmd_delword, '/sync': self.cmd_sync
        }
        
    def send_msg(self, peer_id, message):
        try:
            vk.method('messages.send', {'peer_id': peer_id, 'message': message, 'random_id': get_random_id()})
        except Exception as e:
            print(f"Ошибка: {e}")
    
    def get_user_name(self, user_id):
        try:
            user = vk.method('users.get', {'user_ids': user_id})
            return f"{user[0]['first_name']} {user[0]['last_name']}"
        except:
            return f"id{user_id}"
    
    def get_chat_users(self, chat_id):
        try:
            chat = vk.method('messages.getConversationMembers', {'peer_id': 2000000000 + chat_id})
            return [user['member_id'] for user in chat['items'] if user['member_id'] > 0]
        except:
            return []
    
    def get_user_role(self, user_id, chat_id):
        cursor.execute('SELECT role FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        result = cursor.fetchone()
        return result[0] if result else 'user'
    
    def check_permission(self, user_id, chat_id, required_role):
        if user_id == OWNER_ID:
            return True
        role = self.get_user_role(user_id, chat_id)
        return ROLES.get(role, 0) >= ROLES.get(required_role, 0)
    
    def is_global_admin(self, user_id):
        if user_id == OWNER_ID:
            return True
        cursor.execute('SELECT role FROM users WHERE user_id = ? AND chat_id = -1', (user_id,))
        result = cursor.fetchone()
        return result and result[0] in ['zamglav', 'glav']
    
    def register_chat(self, chat_id):
        cursor.execute('INSERT OR IGNORE INTO chats (chat_id, created_date, bot_activated) VALUES (?, ?, ?)',
                      (chat_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0))
        conn.commit()
    
    def register_user(self, user_id, chat_id):
        cursor.execute('INSERT OR IGNORE INTO users (user_id, chat_id, joined_date, last_active) VALUES (?, ?, ?, ?)',
                      (user_id, chat_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    
    def check_activation(self, chat_id):
        cursor.execute('SELECT bot_activated FROM chats WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        return result and result[0] == 1
    
    def check_mute(self, user_id, chat_id):
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
    
    def check_ban(self, user_id, chat_id):
        cursor.execute('SELECT banned FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        result = cursor.fetchone()
        return result and result[0] == 1
    
    def check_global_ban(self, user_id):
        cursor.execute('SELECT * FROM global_bans WHERE user_id = ?', (user_id,))
        return cursor.fetchone() is not None
    
    # ============= КОМАНДЫ =============
    
    def cmd_start(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Только владелец бота!")
            return
        if self.check_activation(chat_id):
            self.send_msg(peer_id, "✅ Бот уже активирован!")
            return
        cursor.execute('UPDATE chats SET bot_activated = 1 WHERE chat_id = ?', (chat_id,))
        conn.commit()
        self.send_msg(peer_id, "✅ Бот активирован!\n/help - список команд")
    
    def cmd_help(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        help_text = """📚 **КОМАНДЫ:**
━━━━━━━━━━━━━━━━━━━━
👤 **ВСЕМ:**
/info - инфо о боте
/stats @user - статистика
/getid - узнать ID
/test - проверка

🟢 **МОДЕРАТОРЫ:**
/kick @user - кик
/mute @user 30 - мут
/unmute @user - размут
/warn @user - варн
/unwarn @user - снять варн
/clear 10 - очистка
/staff - админы
/setnick @user ник - ник
/nlist - список ников
/warnlist - список варнов
/mutelist - список мутов

🟠 **АДМИНИСТРАТОРЫ:**
/ban @user - бан
/unban - разбан
/addmoder @user - дать модера
/removerole @user - забрать роль
/zov - @всех
/banlist - список банов
/addadmin @user - дать админа
/filter - фильтр
/quiet - тишина
/settings - настройки

🔴 **ГЛОБАЛКА:**
/gban @user - глобальный бан
/gunban @user - глобальный разбан
/gbanlist - список гл.банов
/addword слово - добавить слово
/delword слово - удалить слово
/sync - синхронизация
━━━━━━━━━━━━━━━━━━━━
👑 Владелец: Дмитрий"""
        self.send_msg(peer_id, help_text)
    
    def cmd_info(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        self.send_msg(peer_id, "🤖 BLACK FIB BOT v3.0\n👑 Дмитрий\n💬 /help")
    
    def cmd_stats(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        target_id = user_id
        if args and args[0].startswith('[id'):
            try:
                target_id = int(re.findall(r'id(\d+)', args[0])[0])
            except:
                pass
        cursor.execute('SELECT warns, muted_until, role FROM users WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
        user = cursor.fetchone()
        if user:
            muted = "НЕТ" if not user[1] else f"ДО {user[1][:16]}"
            self.send_msg(peer_id, f"📊 {self.get_user_name(target_id)}\n⭐ Роль: {user[2]}\n⚠️ Варны: {user[0]}/3\n🔇 Мут: {muted}")
        else:
            self.send_msg(peer_id, f"📊 {self.get_user_name(target_id)}\n⚠️ Варны: 0/3")
    
    def cmd_getid(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        self.send_msg(peer_id, f"🆔 ID: {user_id}")
    
    def cmd_test(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        self.send_msg(peer_id, f"✅ Бот работает!\n👤 ID: {user_id}")
    
    def cmd_kick(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'moderator'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /kick @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Нарушение'
            vk.method('messages.removeChatUser', {'chat_id': chat_id, 'user_id': target_id})
            self.send_msg(peer_id, f"👢 {self.get_user_name(target_id)} кикнут\nПричина: {reason}")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_mute(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'moderator'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if len(args) < 2:
            self.send_msg(peer_id, "❌ /mute @user 30")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            minutes = int(args[1])
            muted_until = datetime.now() + timedelta(minutes=minutes)
            cursor.execute('UPDATE users SET muted_until = ? WHERE user_id = ? AND chat_id = ?', (muted_until.strftime('%Y-%m-%d %H:%M:%S'), target_id, chat_id))
            conn.commit()
            self.send_msg(peer_id, f"🔇 {self.get_user_name(target_id)} замучен на {minutes} мин")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_unmute(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'moderator'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /unmute @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            cursor.execute('UPDATE users SET muted_until = NULL WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            conn.commit()
            self.send_msg(peer_id, f"🔊 {self.get_user_name(target_id)} размучен")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_warn(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'moderator'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /warn @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Нарушение'
            cursor.execute('SELECT warns FROM users WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            warns = cursor.fetchone()
            new_warns = (warns[0] if warns else 0) + 1
            cursor.execute('UPDATE users SET warns = ? WHERE user_id = ? AND chat_id = ?', (new_warns, target_id, chat_id))
            conn.commit()
            self.send_msg(peer_id, f"⚠️ {self.get_user_name(target_id)} | ВАРН {new_warns}/3\nПричина: {reason}")
            if new_warns >= 3:
                cursor.execute('UPDATE users SET banned = 1 WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
                conn.commit()
                try:
                    vk.method('messages.removeChatUser', {'chat_id': chat_id, 'user_id': target_id})
                    self.send_msg(peer_id, f"🚫 {self.get_user_name(target_id)} забанен (3 варна)")
                except:
                    pass
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_unwarn(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'moderator'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /unwarn @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            cursor.execute('UPDATE users SET warns = warns - 1 WHERE user_id = ? AND chat_id = ? AND warns > 0', (target_id, chat_id))
            conn.commit()
            self.send_msg(peer_id, f"✅ {self.get_user_name(target_id)} варн снят")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_staff(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        cursor.execute('SELECT user_id, role FROM users WHERE chat_id = ? AND role != "user"', (chat_id,))
        staff = cursor.fetchall()
        if staff:
            msg = "👥 АДМИНИСТРАЦИЯ:\n"
            for s in staff:
                msg += f"• {self.get_user_name(s[0])} - {s[1]}\n"
            self.send_msg(peer_id, msg)
        else:
            self.send_msg(peer_id, "❌ Нет администрации")
    
    def cmd_setnick(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'moderator'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if len(args) < 2:
            self.send_msg(peer_id, "❌ /setnick @user ник")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            nick = ' '.join(args[1:])
            cursor.execute('INSERT OR REPLACE INTO user_nicks (user_id, chat_id, nick, set_by, date) VALUES (?, ?, ?, ?, ?)',
                          (target_id, chat_id, nick, user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            self.send_msg(peer_id, f"🏷 Ник для {self.get_user_name(target_id)}: {nick}")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_nlist(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        cursor.execute('SELECT user_id, nick FROM user_nicks WHERE chat_id = ?', (chat_id,))
        nicks = cursor.fetchall()
        if nicks:
            msg = "📋 СПИСОК НИКОВ:\n"
            for n in nicks:
                msg += f"• {self.get_user_name(n[0])} - {n[1]}\n"
            self.send_msg(peer_id, msg)
        else:
            self.send_msg(peer_id, "❌ Нет ников")
    
    def cmd_warnlist(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'moderator'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        cursor.execute('SELECT user_id, warns FROM users WHERE chat_id = ? AND warns > 0', (chat_id,))
        warned = cursor.fetchall()
        if warned:
            msg = "⚠️ ВАРНЫ:\n"
            for w in warned:
                msg += f"• {self.get_user_name(w[0])} - {w[1]}/3\n"
            self.send_msg(peer_id, msg)
        else:
            self.send_msg(peer_id, "✅ Нет варнов")
    
    def cmd_mutelist(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'moderator'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        cursor.execute('SELECT user_id, muted_until FROM users WHERE chat_id = ? AND muted_until IS NOT NULL', (chat_id,))
        muted = cursor.fetchall()
        now = datetime.now()
        active = []
        for m in muted:
            try:
                till = datetime.strptime(m[1], '%Y-%m-%d %H:%M:%S')
                if till > now:
                    active.append((m[0], till))
            except:
                pass
        if active:
            msg = "🔇 МУТЫ:\n"
            for a in active:
                left = a[1] - now
                msg += f"• {self.get_user_name(a[0])} - {left.seconds//60} мин\n"
            self.send_msg(peer_id, msg)
        else:
            self.send_msg(peer_id, "✅ Нет мутов")
    
    def cmd_clear(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'moderator'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /clear 10")
            return
        try:
            count = int(args[0])
            if count > 100:
                count = 100
            history = vk.method('messages.getHistory', {'peer_id': peer_id, 'count': count})
            ids = [msg['id'] for msg in history['items']]
            vk.method('messages.delete', {'message_ids': ids, 'delete_for_all': 1})
            self.send_msg(peer_id, f"✅ Удалено {count} сообщений")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_ban(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'admin'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /ban @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Нарушение'
            cursor.execute('INSERT OR REPLACE INTO bans (user_id, chat_id, admin_id, reason, date) VALUES (?, ?, ?, ?, ?)',
                          (target_id, chat_id, user_id, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            cursor.execute('UPDATE users SET banned = 1 WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            conn.commit()
            try:
                vk.method('messages.removeChatUser', {'chat_id': chat_id, 'user_id': target_id})
                self.send_msg(peer_id, f"🚫 {self.get_user_name(target_id)} забанен\nПричина: {reason}")
            except:
                pass
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_unban(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'admin'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /unban @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            cursor.execute('DELETE FROM bans WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            cursor.execute('UPDATE users SET banned = 0 WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            conn.commit()
            self.send_msg(peer_id, f"✅ {self.get_user_name(target_id)} разбанен")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_addmoder(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'admin'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /addmoder @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            cursor.execute('UPDATE users SET role = "moderator" WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            if cursor.rowcount == 0:
                cursor.execute('INSERT INTO users (user_id, chat_id, role, joined_date) VALUES (?, ?, ?, ?)',
                              (target_id, chat_id, 'moderator', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            self.send_msg(peer_id, f"✅ {self.get_user_name(target_id)} теперь модератор")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_removerole(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'admin'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /removerole @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            cursor.execute('UPDATE users SET role = "user" WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            conn.commit()
            self.send_msg(peer_id, f"✅ У {self.get_user_name(target_id)} роль забрана")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_zov(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'admin'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        users = self.get_chat_users(chat_id)
        mentions = [f"[id{u}|{self.get_user_name(u)}]" for u in users[:50]]
        self.send_msg(peer_id, ' '.join(mentions) if mentions else "Нет пользователей")
    
    def cmd_banlist(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'admin'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        cursor.execute('SELECT user_id FROM bans WHERE chat_id = ?', (chat_id,))
        bans = cursor.fetchall()
        if bans:
            msg = "🚫 БАНЫ:\n"
            for b in bans:
                msg += f"• {self.get_user_name(b[0])}\n"
            self.send_msg(peer_id, msg)
        else:
            self.send_msg(peer_id, "✅ Нет банов")
    
    def cmd_addadmin(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'senioradmin'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /addadmin @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            cursor.execute('UPDATE users SET role = "admin" WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            if cursor.rowcount == 0:
                cursor.execute('INSERT INTO users (user_id, chat_id, role, joined_date) VALUES (?, ?, ?, ?)',
                              (target_id, chat_id, 'admin', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            self.send_msg(peer_id, f"✅ {self.get_user_name(target_id)} теперь администратор")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_filter(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'admin'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        cursor.execute('SELECT filter_enabled FROM chats WHERE chat_id = ?', (chat_id,))
        current = cursor.fetchone()
        new_val = 0 if (current and current[0] == 1) else 1
        cursor.execute('UPDATE chats SET filter_enabled = ? WHERE chat_id = ?', (new_val, chat_id))
        conn.commit()
        self.send_msg(peer_id, f"📝 Фильтр {'ВКЛ' if new_val else 'ВЫКЛ'}")
    
    def cmd_quiet(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'admin'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        cursor.execute('SELECT quiet_mode FROM chats WHERE chat_id = ?', (chat_id,))
        current = cursor.fetchone()
        new_val = 0 if (current and current[0] == 1) else 1
        cursor.execute('UPDATE chats SET quiet_mode = ? WHERE chat_id = ?', (new_val, chat_id))
        conn.commit()
        self.send_msg(peer_id, f"🔇 Тишина {'ВКЛ' if new_val else 'ВЫКЛ'}")
    
    def cmd_settings(self, user_id, chat_id, args):
        if not chat_id:
            self.send_msg(user_id, "❌ Только в беседах!")
            return
        peer_id = 2000000000 + chat_id
        if not self.check_permission(user_id, chat_id, 'admin'):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        cursor.execute('SELECT filter_enabled, quiet_mode FROM chats WHERE chat_id = ?', (chat_id,))
        settings = cursor.fetchone()
        if settings:
            self.send_msg(peer_id, f"⚙️ НАСТРОЙКИ:\n📝 Фильтр: {'✅' if settings[0] else '❌'}\n🔇 Тишина: {'✅' if settings[1] else '❌'}")
    
    def cmd_gban(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        if not self.is_global_admin(user_id):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /gban @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Глобальный бан'
            cursor.execute('INSERT OR REPLACE INTO global_bans (user_id, admin_id, reason, date) VALUES (?, ?, ?, ?)',
                          (target_id, user_id, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            self.send_msg(peer_id, f"🌐 {self.get_user_name(target_id)} глобально забанен\nПричина: {reason}")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_gunban(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        if not self.is_global_admin(user_id):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /gunban @user")
            return
        try:
            target_id = int(re.findall(r'id(\d+)', args[0])[0])
            cursor.execute('DELETE FROM global_bans WHERE user_id = ?', (target_id,))
            conn.commit()
            self.send_msg(peer_id, f"🌐 {self.get_user_name(target_id)} глобально разбанен")
        except:
            self.send_msg(peer_id, "❌ Ошибка!")
    
    def cmd_gbanlist(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        if not self.is_global_admin(user_id):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        cursor.execute('SELECT user_id FROM global_bans')
        bans = cursor.fetchall()
        if bans:
            msg = "🌐 ГЛОБАЛЬНЫЕ БАНЫ:\n"
            for b in bans:
                msg += f"• {self.get_user_name(b[0])}\n"
            self.send_msg(peer_id, msg)
        else:
            self.send_msg(peer_id, "✅ Нет глобальных банов")
    
    def cmd_addword(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        if not self.is_global_admin(user_id):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /addword слово")
            return
        word = args[0].lower()
        cursor.execute('INSERT OR IGNORE INTO filter_words (word) VALUES (?)', (word,))
        conn.commit()
        self.send_msg(peer_id, f"✅ Слово '{word}' добавлено")
    
    def cmd_delword(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        if not self.is_global_admin(user_id):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_msg(peer_id, "❌ /delword слово")
            return
        word = args[0].lower()
        cursor.execute('DELETE FROM filter_words WHERE word = ?', (word,))
        conn.commit()
        self.send_msg(peer_id, f"✅ Слово '{word}' удалено")
    
    def cmd_sync(self, user_id, chat_id, args):
        peer_id = 2000000000 + chat_id if chat_id else user_id
        if not self.is_global_admin(user_id):
            self.send_msg(peer_id, "❌ Нет прав!")
            return
        conn.commit()
        self.send_msg(peer_id, "🔄 База синхронизирована")
    
    def process_message(self, event):
        user_id = event.user_id
        if event.from_chat:
            chat_id = event.chat_id
            peer_id = 2000000000 + chat_id
        else:
            chat_id = 0
            peer_id = user_id
        message = event.text

        if chat_id:
            self.register_chat(chat_id)
            self.register_user(user_id, chat_id)
            cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ? AND chat_id = ?',
                         (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id, chat_id))
            conn.commit()
            
            if self.check_global_ban(user_id):
                try:
                    vk.method('messages.removeChatUser', {'chat_id': chat_id, 'user_id': user_id})
                except:
                    pass
                return
            
            if self.check_ban(user_id, chat_id):
                try:
                    vk.method('messages.removeChatUser', {'chat_id': chat_id, 'user_id': user_id})
                except:
                    pass
                return
            
            if self.check_mute(user_id, chat_id):
                return
            
            if not self.check_activation(chat_id) and user_id != OWNER_ID:
                if message and message.startswith('/start'):
                    pass
                else:
                    return
            
            # Фильтр мата
            if message and not message.startswith('/') and self.check_activation(chat_id):
                cursor.execute('SELECT filter_enabled FROM chats WHERE chat_id = ?', (chat_id,))
                res = cursor.fetchone()
                if res and res[0] == 1:
                    cursor.execute('SELECT word FROM filter_words')
                    bad = cursor.fetchall()
                    for w in bad:
                        if w[0].lower() in message.lower():
                            try:
                                vk.method('messages.delete', {'message_ids': [event.message_id], 'delete_for_all': 1})
                            except:
                                pass
                            cursor.execute('SELECT warns FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
                            warns = cursor.fetchone()
                            new_warns = (warns[0] if warns else 0) + 1
                            cursor.execute('UPDATE users SET warns = ? WHERE user_id = ? AND chat_id = ?', (new_warns, user_id, chat_id))
                            conn.commit()
                            if new_warns >= 3:
                                cursor.execute('UPDATE users SET banned = 1 WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
                                conn.commit()
                            break
        
        if message and message.startswith('/'):
            parts = message.split()
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            if cmd in self.commands:
                try:
                    self.commands[cmd](user_id, chat_id, args)
                except Exception as e:
                    print(f"Ошибка: {e}")
                    self.send_msg(peer_id, f"❌ Ошибка")
    
    def run(self):
        print("-" * 40)
        print("💬 Команды: /help")
        print("-" * 40)
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                self.process_message(event)

if __name__ == '__main__':
    bot = AdminBot()
    bot.run()
