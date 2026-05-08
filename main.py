import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import sqlite3
import time
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

# Создание таблиц с правильной структурой
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
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
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

# Проверяем и добавляем колонку bot_activated если её нет
try:
    cursor.execute("SELECT bot_activated FROM chats LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE chats ADD COLUMN bot_activated INTEGER DEFAULT 0")
    print("✅ Добавлена колонка bot_activated в таблицу chats")

# Добавляем тебя как владельца бота (глобально)
cursor.execute('''
    INSERT OR IGNORE INTO users (user_id, chat_id, role, joined_date)
    VALUES (?, ?, ?, ?)
''', (OWNER_ID, -1, 'glav', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

# Добавляем несколько слов в фильтр для примера
try:
    words = ["сука", "блядь", "хуй", "пизда", "ебать", "мат", "плохое_слово"]
    for word in words:
        cursor.execute("INSERT OR IGNORE INTO filter_words (word) VALUES (?)", (word,))
except Exception as e:
    print(f"Ошибка при добавлении слов: {e}")

conn.commit()

print("✅ База данных подготовлена")
print(f"👑 Владелец бота: [id{OWNER_ID}|Vlad]")

# Роли и их уровень доступа
ROLES = {
    'user': 0,
    'moderator': 1,
    'seniormoderator': 2,
    'admin': 3,
    'senioradmin': 4,
    'owner': 5,
    'zamglav': 6,
    'glav': 7
}

class AdminBot:
    def __init__(self):
        self.commands = {
            # Команды пользователей
            '/start': self.cmd_start,
            '/help': self.cmd_help,
            '/info': self.cmd_info,
            '/stats': self.cmd_stats,
            '/getid': self.cmd_getid,
            '/test': self.cmd_test,
            
            # Команды модераторов
            '/kick': self.cmd_kick,
            '/mute': self.cmd_mute,
            '/unmute': self.cmd_unmute,
            '/warn': self.cmd_warn,
            '/unwarn': self.cmd_unwarn,
            '/getban': self.cmd_getban,
            '/getwarn': self.cmd_getwarn,
            '/warnhistory': self.cmd_warnhistory,
            '/staff': self.cmd_staff,
            '/setnick': self.cmd_setnick,
            '/removenick': self.cmd_removenick,
            '/nlist': self.cmd_nlist,
            '/nonick': self.cmd_nonick,
            '/getnick': self.cmd_getnick,
            '/alt': self.cmd_alt,
            '/getacc': self.cmd_getacc,
            '/warnlist': self.cmd_warnlist,
            '/clear': self.cmd_clear,
            '/getmute': self.cmd_getmute,
            '/mutelist': self.cmd_mutelist,
            '/delete': self.cmd_delete,
            
            # Команды старших модераторов
            '/ban': self.cmd_ban,
            '/unban': self.cmd_unban,
            '/addmoder': self.cmd_addmoder,
            '/removerole': self.cmd_removerole,
            '/zov': self.cmd_zov,
            '/online': self.cmd_online,
            '/banlist': self.cmd_banlist,
            '/onlinelist': self.cmd_onlinelist,
            '/inactivelist': self.cmd_inactivelist,
            
            # Команды администраторов
            '/skick': self.cmd_skick,
            '/quiet': self.cmd_quiet,
            '/sban': self.cmd_sban,
            '/sunban': self.cmd_sunban,
            '/addsenmoder': self.cmd_addsenmoder,
            '/bug': self.cmd_bug,
            '/rnickall': self.cmd_rnickall,
            '/srnick': self.cmd_srnick,
            '/ssetnick': self.cmd_ssetnick,
            '/srrole': self.cmd_srrole,
            '/srole': self.cmd_srole,
            
            # Команды старших администраторов
            '/addadmin': self.cmd_addadmin,
            '/settings': self.cmd_settings,
            '/filter': self.cmd_filter,
            '/szov': self.cmd_szov,
            '/serverinfo': self.cmd_serverinfo,
            '/rkick': self.cmd_rkick,
            
            # Команды владельца беседы
            '/type': self.cmd_type,
            '/leave': self.cmd_leave,
            '/editowner': self.cmd_editowner,
            '/pin': self.cmd_pin,
            '/unpin': self.cmd_unpin,
            '/clearwarn': self.cmd_clearwarn,
            '/rroleall': self.cmd_rroleall,
            '/addsenadm': self.cmd_addsenadm,
            '/masskick': self.cmd_masskick,
            '/invite': self.cmd_invite,
            '/antiflood': self.cmd_antiflood,
            '/welcometext': self.cmd_welcometext,
            '/welcometextdelete': self.cmd_welcometextdelete,
            
            # Команды зам.руководителя
            '/gban': self.cmd_gban,
            '/gunban': self.cmd_gunban,
            '/sync': self.cmd_sync,
            '/gbanlist': self.cmd_gbanlist,
            '/banwords': self.cmd_banwords,
            '/gbanpl': self.cmd_gbanpl,
            '/gunbanpl': self.cmd_gunbanpl,
            '/addowner': self.cmd_addowner,
            
            # Команды руководителя
            '/server': self.cmd_server,
            '/addword': self.cmd_addword,
            '/delword': self.cmd_delword,
            '/gremoverole': self.cmd_gremoverole,
            '/news': self.cmd_news,
            '/addzam': self.cmd_addzam,
            '/banid': self.cmd_banid,
            '/unbanid': self.cmd_unbanid,
            '/clearchat': self.cmd_clearchat,
            '/infoid': self.cmd_infoid,
            '/addbug': self.cmd_addbug,
            '/listchats': self.cmd_listchats,
            '/adddev': self.cmd_adddev,
            '/delbug': self.cmd_delbug,
        }
        
    def send_msg(self, peer_id, message, attachment=None):
        """Универсальная отправка сообщений"""
        try:
            vk.method('messages.send', {
                'peer_id': peer_id,
                'message': message,
                'random_id': get_random_id(),
                'attachment': attachment
            })
        except Exception as e:
            print(f"Ошибка отправки: {e}")
    
    def get_user_name(self, user_id):
        """Получение имени пользователя"""
        try:
            user = vk.method('users.get', {'user_ids': user_id})
            return f"{user[0]['first_name']} {user[0]['last_name']}"
        except:
            return f"id{user_id}"
    
    def get_chat_users(self, chat_id):
        """Получение списка пользователей в чате"""
        try:
            chat = vk.method('messages.getConversationMembers', {'peer_id': 2000000000 + chat_id})
            return [user['member_id'] for user in chat['items'] if user['member_id'] > 0]
        except:
            return []
    
    def get_user_role(self, user_id, chat_id):
        """Получение роли пользователя"""
        cursor.execute('SELECT role FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        result = cursor.fetchone()
        return result[0] if result else 'user'
    
    def check_permission(self, user_id, chat_id, required_role):
        """Проверка прав пользователя"""
        # Владелец бота имеет все права
        if user_id == OWNER_ID:
            return True
            
        role = self.get_user_role(user_id, chat_id)
        return ROLES.get(role, 0) >= ROLES.get(required_role, 0)
    
    def is_global_admin(self, user_id):
        """Проверка глобальных прав"""
        if user_id == OWNER_ID:
            return True
            
        cursor.execute('SELECT role FROM users WHERE user_id = ? AND chat_id = -1', (user_id,))
        result = cursor.fetchone()
        return result and result[0] in ['zamglav', 'glav']
    
    def register_chat(self, chat_id):
        """Регистрация чата"""
        cursor.execute('INSERT OR IGNORE INTO chats (chat_id, created_date, bot_activated) VALUES (?, ?, ?)',
                      (chat_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0))
        conn.commit()
    
    def register_user(self, user_id, chat_id):
        """Регистрация пользователя в чате"""
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, chat_id, joined_date, last_active) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, chat_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    
    def check_activation(self, chat_id):
        """Проверка активации бота в чате"""
        try:
            cursor.execute('SELECT bot_activated FROM chats WHERE chat_id = ?', (chat_id,))
            result = cursor.fetchone()
            return result and result[0] == 1
        except:
            # Если колонки нет, возвращаем False
            return False
    
    # ============= ОСНОВНЫЕ КОМАНДЫ =============
    
    def cmd_start(self, user_id, chat_id, args):
        """Активация бота в чате (только для владельца)"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        # Проверяем, что активирует владелец бота
        if user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Только владелец бота может активировать его!")
            return
        
        # Проверяем, не активирован ли уже бот
        if self.check_activation(chat_id):
            self.send_msg(peer_id, "✅ Бот уже активирован в этой беседе!")
            return
        
        # Активируем бота
        cursor.execute('UPDATE chats SET bot_activated = 1 WHERE chat_id = ?', (chat_id,))
        conn.commit()
        
        # Отправляем приветственное сообщение
        welcome_text = (
            "🤖 **BLACK FIB BOT**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ Бот успешно активирован!\n\n"
            "📋 **Основные команды:**\n"
            "• /help - список всех команд\n"
            "• /info - информация о боте\n"
            "• /stats @user - статистика\n"
            "• /staff - список администрации\n\n"
            "🛡 **Модерация:**\n"
            "• /kick @user - исключить\n"
            "• /mute @user 30 - замутить\n"
            "• /warn @user - предупреждение\n"
            "• /ban @user - заблокировать\n\n"
            "⚙️ **Настройки:**\n"
            "• /filter - включить фильтр\n"
            "• /antiflood - антифлуд\n"
            "• /type players - тип беседы\n\n"
            "👑 Разработчик: [id631833072|Vlad]\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        self.send_msg(peer_id, welcome_text)
    
    def cmd_help(self, user_id, chat_id, args):
        """Справка по командам"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        # Проверяем активацию для чатов
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе! Ожидайте активации владельцем.")
            return
        
        role = self.get_user_role(user_id, chat_id) if chat_id else 'user'
        if user_id == OWNER_ID:
            role = 'glav'
        
        help_text = (
            "📚 **BLACK FIB BOT - СПРАВКА**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 **Команды пользователей:**\n"
            "• /info - информация о боте\n"
            "• /stats @user - статистика\n"
            "• /getid - узнать ID пользователя\n"
            "• /test - проверка работы\n\n"
        )
        
        if ROLES.get(role, 0) >= 1:  # Модератор и выше
            help_text += (
                "🟢 **Модераторы:**\n"
                "• /kick @user - исключить\n"
                "• /mute @user 30 - замутить\n"
                "• /unmute @user - размутить\n"
                "• /warn @user - предупреждение\n"
                "• /unwarn @user - снять варн\n"
                "• /clear 10 - очистить чат\n"
                "• /staff - список администрации\n"
                "• /setnick @user ник - установить ник\n"
                "• /nlist - список ников\n"
                "• /warnlist - список варнов\n"
                "• /mutelist - список мутов\n\n"
            )
        
        if ROLES.get(role, 0) >= 2:  # Старший модератор и выше
            help_text += (
                "🟡 **Ст.Модераторы:**\n"
                "• /ban @user - заблокировать\n"
                "• /unban @user - разблокировать\n"
                "• /addmoder @user - дать модератора\n"
                "• /removerole @user - забрать роль\n"
                "• /zov - упомянуть всех\n"
                "• /banlist - список банов\n"
                "• /inactivelist - неактивные\n\n"
            )
        
        if ROLES.get(role, 0) >= 3:  # Администратор и выше
            help_text += (
                "🟠 **Администраторы:**\n"
                "• /quiet - режим тишины\n"
                "• /addsenmoder @user - ст.модера\n"
                "• /bug - сообщить о баге\n"
                "• /rnickall - сбросить ники\n\n"
            )
        
        if ROLES.get(role, 0) >= 4:  # Старший администратор и выше
            help_text += (
                "🔴 **Ст.Администраторы:**\n"
                "• /addadmin @user - дать админа\n"
                "• /settings - настройки беседы\n"
                "• /filter - вкл/выкл фильтр\n"
                "• /serverinfo - инфо о беседе\n"
                "• /rkick - кик новых\n\n"
            )
        
        if ROLES.get(role, 0) >= 5:  # Владелец беседы
            help_text += (
                "👑 **Владелец беседы:**\n"
                "• /type players/server - тип беседы\n"
                "• /leave - кик при выходе\n"
                "• /editowner @user - передать права\n"
                "• /pin текст - закрепить\n"
                "• /unpin - открепить\n"
                "• /rroleall - сбросить роли\n"
                "• /addsenadm @user - ст.админа\n"
                "• /masskick - кик без роли\n"
                "• /invite - приглашение модерами\n"
                "• /antiflood - вкл/выкл антифлуд\n"
                "• /welcometext текст - приветствие\n\n"
            )
        
        if ROLES.get(role, 0) >= 6:  # Зам.руководителя
            help_text += (
                "⚜️ **Зам.руководителя:**\n"
                "• /gban @user - глобальный бан\n"
                "• /gunban @user - глобальный разбан\n"
                "• /gbanlist - список гл.банов\n"
                "• /banwords - список запрещенных слов\n"
                "• /addowner @user - дать владельца\n\n"
            )
        
        if ROLES.get(role, 0) >= 7 or user_id == OWNER_ID:  # Руководитель
            help_text += (
                "👑 **Руководитель бота:**\n"
                "• /addword слово - добавить в фильтр\n"
                "• /delword слово - удалить из фильтра\n"
                "• /gremoverole @user - сброс ролей\n"
                "• /news текст - новости во все чаты\n"
                "• /addzam @user - зам.руководителя\n"
                "• /banid id - заблокировать беседу\n"
                "• /unbanid id - разблокировать\n"
                "• /clearchat id - удалить чат из бд\n"
                "• /infoid @user - инфо о пользователе\n"
                "• /listchats - список чатов\n"
                "• /adddev @user - дать права рук-ля\n"
            )
        
        help_text += "\n━━━━━━━━━━━━━━━━━━━━"
        self.send_msg(peer_id, help_text)
    
    def cmd_info(self, user_id, chat_id, args):
        """Информация о боте"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе! Ожидайте активации владельцем.")
            return
        
        message = (
            "🤖 **BLACK FIB BOT**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 Версия: 2.0\n"
            "👑 Разработчик: [id631833072|Vlad]\n"
            "📅 Дата создания: 2024\n"
            "⚙️ Статус: Активен\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📋 Команды: /help\n"
            "📢 Новости: https://vk.com/blackfib\n"
            "🆘 Поддержка: https://vk.me/blackfib"
        )
        self.send_msg(peer_id, message)
    
    def cmd_test(self, user_id, chat_id, args):
        """Тестовая команда"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе! Ожидайте активации владельцем.")
            return
        
        if chat_id:
            status = f"✅ Бот работает в беседе!\n👤 Твой ID: {user_id}\n💬 ID чата: {chat_id}"
            if user_id == OWNER_ID:
                status += "\n👑 Ты владелец бота"
        else:
            status = f"✅ Бот работает в ЛС!\n👤 Твой ID: {user_id}"
            if user_id == OWNER_ID:
                status += "\n👑 Ты владелец бота"
        
        self.send_msg(peer_id, status)
    
    def cmd_stats(self, user_id, chat_id, args):
        """Информация о пользователе"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        target_id = user_id
        if args and args[0].startswith('[id'):
            try:
                target_id = int(re.findall(r'id(\d+)', args[0])[0])
            except:
                pass
        
        cursor.execute('SELECT * FROM users WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
        user = cursor.fetchone()
        
        if not user:
            self.register_user(target_id, chat_id)
            cursor.execute('SELECT * FROM users WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            user = cursor.fetchone()
        
        muted_info = ""
        if user and user[5]:
            try:
                muted_until = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
                if muted_until > datetime.now():
                    muted_info = f"🔇 Мут до: {muted_until.strftime('%d.%m.%Y %H:%M')}\n"
            except:
                pass
        
        role_emoji = {
            'user': '👤',
            'moderator': '🟢',
            'seniormoderator': '🟡',
            'admin': '🟠',
            'senioradmin': '🔴',
            'owner': '👑',
            'zamglav': '⚜️',
            'glav': '👑'
        }
        
        role = user[3] if user else 'user'
        emoji = role_emoji.get(role, '👤')
        
        message = (
            f"📊 Статистика пользователя:\n"
            f"{emoji} Имя: {self.get_user_name(target_id)}\n"
            f"🆔 ID: {target_id}\n"
            f"⭐ Роль: {role}\n"
            f"⚠️ Предупреждений: {user[4] if user else 0}/3\n"
            f"{muted_info}"
            f"📅 Присоединился: {user[7] if user else 'Неизвестно'}\n"
            f"⏰ Последняя активность: {user[8] if user else 'Неизвестно'}"
        )
        
        if target_id == OWNER_ID:
            message += "\n👑 Владелец бота"
        
        self.send_msg(peer_id, message)
    
    def cmd_getid(self, user_id, chat_id, args):
        """Узнать ID пользователя"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if args and args[0].startswith('[id'):
            try:
                target_id = int(re.findall(r'id(\d+)', args[0])[0])
            except:
                target_id = user_id
        else:
            target_id = user_id
        
        self.send_msg(peer_id, f"🆔 ID пользователя: {target_id}")
    
    # ============= КОМАНДЫ МОДЕРАТОРОВ =============
    
    def cmd_kick(self, user_id, chat_id, args):
        """Исключить пользователя из беседы"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя! Пример: /kick @user")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
            
            vk.method('messages.removeChatUser', {
                'chat_id': chat_id,
                'user_id': target_id
            })
            
            self.send_msg(peer_id, f"✅ Пользователь [id{target_id}|] исключён.\nПричина: {reason}")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_mute(self, user_id, chat_id, args):
        """Замутить пользователя"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if len(args) < 2:
            self.send_msg(peer_id, "❌ Пример: /mute @user 30 (минут)")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            minutes = int(args[1])
            reason = ' '.join(args[2:]) if len(args) > 2 else 'Не указана'
            
            muted_until = datetime.now() + timedelta(minutes=minutes)
            
            cursor.execute('''
                UPDATE users SET muted_until = ? 
                WHERE user_id = ? AND chat_id = ?
            ''', (muted_until.strftime('%Y-%m-%d %H:%M:%S'), target_id, chat_id))
            conn.commit()
            
            self.send_msg(peer_id, 
                         f"🔇 Пользователь [id{target_id}|] замучен на {minutes} мин.\nПричина: {reason}")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_unmute(self, user_id, chat_id, args):
        """Размутить пользователя"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('''
                UPDATE users SET muted_until = NULL 
                WHERE user_id = ? AND chat_id = ?
            ''', (target_id, chat_id))
            conn.commit()
            
            self.send_msg(peer_id, f"🔊 Пользователь [id{target_id}|] размучен!")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_warn(self, user_id, chat_id, args):
        """Выдать предупреждение"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Пример: /warn @user Причина")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
            
            cursor.execute('SELECT warns FROM users WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            result = cursor.fetchone()
            warns = result[0] if result else 0
            new_warns = warns + 1
            
            cursor.execute('''
                UPDATE users SET warns = ? 
                WHERE user_id = ? AND chat_id = ?
            ''', (new_warns, target_id, chat_id))
            
            cursor.execute('''
                INSERT INTO warn_history (user_id, chat_id, admin_id, reason, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (target_id, chat_id, user_id, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            
            message = f"⚠️ Пользователь [id{target_id}|] получил предупреждение ({new_warns}/3)\nПричина: {reason}"
            
            if new_warns >= 3:
                muted_until = datetime.now() + timedelta(hours=24)
                cursor.execute('''
                    UPDATE users SET muted_until = ?, warns = 0 
                    WHERE user_id = ? AND chat_id = ?
                ''', (muted_until.strftime('%Y-%m-%d %H:%M:%S'), target_id, chat_id))
                conn.commit()
                message += "\n🔇 Достигнут лимит предупреждений! Мут на 24 часа."
            
            self.send_msg(peer_id, message)
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_unwarn(self, user_id, chat_id, args):
        """Снять предупреждение"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('SELECT warns FROM users WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            result = cursor.fetchone()
            warns = result[0] if result else 0
            
            if warns > 0:
                cursor.execute('''
                    UPDATE users SET warns = warns - 1 
                    WHERE user_id = ? AND chat_id = ?
                ''', (target_id, chat_id))
                conn.commit()
                self.send_msg(peer_id, f"✅ Снято предупреждение у [id{target_id}|]")
            else:
                self.send_msg(peer_id, f"❌ У пользователя нет предупреждений!")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_getban(self, user_id, chat_id, args):
        """Информация о банах пользователя"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('''
                SELECT * FROM bans 
                WHERE user_id = ? AND chat_id = ?
            ''', (target_id, chat_id))
            ban = cursor.fetchone()
            
            if ban:
                admin_name = self.get_user_name(ban[3])
                self.send_msg(peer_id,
                            f"🚫 Информация о бане:\n"
                            f"👤 Пользователь: [id{target_id}|]\n"
                            f"👮 Забанил: {admin_name}\n"
                            f"📝 Причина: {ban[4]}\n"
                            f"📅 Дата: {ban[5]}")
            else:
                self.send_msg(peer_id, "✅ Пользователь не забанен")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_getwarn(self, user_id, chat_id, args):
        """Информация о предупреждениях"""
        self.cmd_stats(user_id, chat_id, args)
    
    def cmd_warnhistory(self, user_id, chat_id, args):
        """История предупреждений"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('''
                SELECT * FROM warn_history 
                WHERE user_id = ? AND chat_id = ?
                ORDER BY date DESC LIMIT 10
            ''', (target_id, chat_id))
            warns = cursor.fetchall()
            
            if warns:
                message = f"📜 История предупреждений [id{target_id}|]:\n"
                for warn in warns:
                    admin_name = self.get_user_name(warn[3])
                    message += f"• {warn[5][:10]}: {warn[4]} (от {admin_name})\n"
                self.send_msg(peer_id, message)
            else:
                self.send_msg(peer_id, "✅ Нет истории предупреждений")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_staff(self, user_id, chat_id, args):
        """Список пользователей с ролями"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('''
            SELECT user_id, role FROM users 
            WHERE chat_id = ? AND role != 'user'
            ORDER BY 
                CASE role
                    WHEN 'glav' THEN 1
                    WHEN 'zamglav' THEN 2
                    WHEN 'owner' THEN 3
                    WHEN 'senioradmin' THEN 4
                    WHEN 'admin' THEN 5
                    WHEN 'seniormoderator' THEN 6
                    WHEN 'moderator' THEN 7
                END
        ''', (chat_id,))
        staff = cursor.fetchall()
        
        if staff:
            message = "👥 Администрация:\n"
            roles_ru = {
                'glav': '👑 Руководитель',
                'zamglav': '⚜️ Зам.руководителя',
                'owner': '👤 Владелец беседы',
                'senioradmin': '🔴 Ст.Админ',
                'admin': '🟠 Админ',
                'seniormoderator': '🟡 Ст.Модер',
                'moderator': '🟢 Модератор'
            }
            
            for s in staff:
                name = self.get_user_name(s[0])
                role = roles_ru.get(s[1], s[1])
                message += f"{role} – {name}\n"
            
            self.send_msg(peer_id, message)
        else:
            self.send_msg(peer_id, "❌ Нет администрации в чате")
    
    def cmd_setnick(self, user_id, chat_id, args):
        """Установить ник пользователю"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if len(args) < 2:
            self.send_msg(peer_id, "❌ Пример: /setnick @user Новый ник")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                target_id = int(numbers[0]) if numbers else user_id
            
            nick = ' '.join(args[1:])
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_nicks (user_id, chat_id, nick, set_by, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (target_id, chat_id, nick, user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            
            self.send_msg(peer_id, f"✅ Ник для [id{target_id}|] установлен: {nick}")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_removenick(self, user_id, chat_id, args):
        """Удалить ник"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    target_id = user_id
            
            cursor.execute('DELETE FROM user_nicks WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            conn.commit()
            
            self.send_msg(peer_id, f"✅ Ник удалён у [id{target_id}|]")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_nlist(self, user_id, chat_id, args):
        """Список ников"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT user_id, nick FROM user_nicks WHERE chat_id = ?', (chat_id,))
        nicks = cursor.fetchall()
        
        if nicks:
            message = "📋 Список ников:\n"
            for nick in nicks:
                name = self.get_user_name(nick[0])
                message += f"• {name} – {nick[1]}\n"
            self.send_msg(peer_id, message)
        else:
            self.send_msg(peer_id, "❌ Ники не найдены")
    
    def cmd_nonick(self, user_id, chat_id, args):
        """Пользователи без ников"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        chat_users = self.get_chat_users(chat_id)
        cursor.execute('SELECT user_id FROM user_nicks WHERE chat_id = ?', (chat_id,))
        users_with_nicks = [u[0] for u in cursor.fetchall()]
        
        users_without_nicks = [u for u in chat_users if u not in users_with_nicks and u > 0]
        
        if users_without_nicks:
            message = "👤 Пользователи без ников:\n"
            for user in users_without_nicks[:20]:
                name = self.get_user_name(user)
                message += f"• {name}\n"
            self.send_msg(peer_id, message)
        else:
            self.send_msg(peer_id, "✅ У всех есть ники!")
    
    def cmd_getnick(self, user_id, chat_id, args):
        """Получить ник"""
        self.cmd_stats(user_id, chat_id, args)
    
    def cmd_alt(self, user_id, chat_id, args):
        """Альтернативные команды"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /alt в разработке")
    
    def cmd_getacc(self, user_id, chat_id, args):
        """Получить аккаунт"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /getacc в разработке")
    
    def cmd_warnlist(self, user_id, chat_id, args):
        """Список пользователей с предупреждениями"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT user_id, warns FROM users WHERE chat_id = ? AND warns > 0 ORDER BY warns DESC', (chat_id,))
        warned_users = cursor.fetchall()
        
        if warned_users:
            message = "⚠️ Пользователи с предупреждениями:\n"
            for user in warned_users:
                name = self.get_user_name(user[0])
                message += f"• {name} – {user[1]}/3\n"
            self.send_msg(peer_id, message)
        else:
            self.send_msg(peer_id, "✅ Нет пользователей с предупреждениями")
    
    def cmd_clear(self, user_id, chat_id, args):
        """Очистить сообщения"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите количество сообщений!")
            return
        
        try:
            count = int(args[0])
            if count > 100:
                count = 100
            
            history = vk.method('messages.getHistory', {
                'peer_id': 2000000000 + chat_id,
                'count': count
            })
            
            message_ids = [msg['id'] for msg in history['items']]
            
            vk.method('messages.delete', {
                'message_ids': message_ids,
                'delete_for_all': 1
            })
            
            self.send_msg(peer_id, f"✅ Удалено {count} сообщений")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_getmute(self, user_id, chat_id, args):
        """Получить информацию о муте"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /getmute в разработке")
    
    def cmd_mutelist(self, user_id, chat_id, args):
        """Список мутов"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'moderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT user_id, muted_until FROM users WHERE chat_id = ? AND muted_until IS NOT NULL', (chat_id,))
        muted_users = cursor.fetchall()
        
        now = datetime.now()
        active_mutes = []
        
        for user in muted_users:
            try:
                muted_until = datetime.strptime(user[1], '%Y-%m-%d %H:%M:%S')
                if muted_until > now:
                    active_mutes.append((user[0], muted_until))
            except:
                pass
        
        if active_mutes:
            message = "🔇 Активные муты:\n"
            for user in active_mutes:
                name = self.get_user_name(user[0])
                time_left = user[1] - now
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                message += f"• {name} – ещё {hours}ч {minutes}м\n"
            self.send_msg(peer_id, message)
        else:
            self.send_msg(peer_id, "✅ Нет активных мутов")
    
    def cmd_delete(self, user_id, chat_id, args):
        """Удалить сообщения"""
        self.cmd_clear(user_id, chat_id, args)
    
    # ============= КОМАНДЫ СТАРШИХ МОДЕРАТОРОВ =============
    
    def cmd_ban(self, user_id, chat_id, args):
        """Заблокировать пользователя в беседе"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'seniormoderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Пример: /ban @user Причина")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
            
            cursor.execute('''
                INSERT OR REPLACE INTO bans (user_id, chat_id, admin_id, reason, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (target_id, chat_id, user_id, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            cursor.execute('UPDATE users SET banned = 1 WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            conn.commit()
            
            try:
                vk.method('messages.removeChatUser', {
                    'chat_id': chat_id,
                    'user_id': target_id
                })
            except:
                pass
            
            self.send_msg(peer_id, f"🚫 Пользователь [id{target_id}|] забанен.\nПричина: {reason}")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_unban(self, user_id, chat_id, args):
        """Разблокировать пользователя в беседе"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'seniormoderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('DELETE FROM bans WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            cursor.execute('UPDATE users SET banned = 0 WHERE user_id = ? AND chat_id = ?', (target_id, chat_id))
            conn.commit()
            
            self.send_msg(peer_id, f"✅ Пользователь [id{target_id}|] разбанен")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_addmoder(self, user_id, chat_id, args):
        """Выдать модератора"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'seniormoderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('''
                UPDATE users SET role = 'moderator' 
                WHERE user_id = ? AND chat_id = ?
            ''', (target_id, chat_id))
            
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO users (user_id, chat_id, role, joined_date)
                    VALUES (?, ?, ?, ?)
                ''', (target_id, chat_id, 'moderator', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            
            self.send_msg(peer_id, f"✅ Пользователь [id{target_id}|] теперь модератор")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_removerole(self, user_id, chat_id, args):
        """Забрать роль у пользователя"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'seniormoderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            # Получаем текущую роль
            current_role = self.get_user_role(target_id, chat_id)
            
            # Нельзя забрать роль у владельца бота
            if target_id == OWNER_ID:
                self.send_msg(peer_id, "❌ Нельзя забрать роль у владельца бота!")
                return
            
            # Нельзя забрать роль у владельца беседы (если это не владелец бота)
            if current_role == 'owner' and user_id != OWNER_ID:
                self.send_msg(peer_id, "❌ Нельзя забрать роль у владельца беседы!")
                return
            
            cursor.execute('''
                UPDATE users SET role = 'user' 
                WHERE user_id = ? AND chat_id = ?
            ''', (target_id, chat_id))
            conn.commit()
            
            self.send_msg(peer_id, f"✅ У пользователя [id{target_id}|] убрана роль")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_zov(self, user_id, chat_id, args):
        """Упомянуть всех пользователей"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'seniormoderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        users = self.get_chat_users(chat_id)
        mentions = []
        for user in users[:50]:
            name = self.get_user_name(user)
            mentions.append(f"[id{user}|{name}]")
        
        message = ' '.join(mentions) if mentions else "Нет пользователей"
        self.send_msg(peer_id, message)
    
    def cmd_online(self, user_id, chat_id, args):
        """Информация о онлайн пользователях"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        self.send_msg(peer_id, "📱 Функция /online в разработке")
    
    def cmd_banlist(self, user_id, chat_id, args):
        """Список забаненных"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'seniormoderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT user_id, reason, date FROM bans WHERE chat_id = ?', (chat_id,))
        bans = cursor.fetchall()
        
        if bans:
            message = "🚫 Забаненные пользователи:\n"
            for ban in bans:
                name = self.get_user_name(ban[0])
                message += f"• {name} – {ban[2][:10]}: {ban[1][:30]}\n"
            self.send_msg(peer_id, message)
        else:
            self.send_msg(peer_id, "✅ Нет забаненных пользователей")
    
    def cmd_onlinelist(self, user_id, chat_id, args):
        """Список онлайн пользователей"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if chat_id and not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        self.send_msg(peer_id, "📱 Функция /onlinelist в разработке")
    
    def cmd_inactivelist(self, user_id, chat_id, args):
        """Список неактивных пользователей"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'seniormoderator') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        days = 30
        if args and args[0].isdigit():
            days = int(args[0])
        
        threshold = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT user_id, last_active FROM users 
            WHERE chat_id = ? AND last_active < ?
        ''', (chat_id, threshold.strftime('%Y-%m-%d %H:%M:%S')))
        
        inactive = cursor.fetchall()
        
        if inactive:
            message = f"💤 Неактивные (> {days} дней):\n"
            for user in inactive:
                name = self.get_user_name(user[0])
                message += f"• {name}\n"
            self.send_msg(peer_id, message)
        else:
            self.send_msg(peer_id, f"✅ Нет неактивных пользователей")
    
    # ============= КОМАНДЫ АДМИНИСТРАТОРОВ =============
    
    def cmd_skick(self, user_id, chat_id, args):
        """Супер кик (кик из всех бесед)"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.check_permission(user_id, chat_id, 'admin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /skick в разработке")
    
    def cmd_quiet(self, user_id, chat_id, args):
        """Режим тишины"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'admin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT quiet_mode FROM chats WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        current = result[0] if result else 0
        
        new_value = 0 if current else 1
        cursor.execute('UPDATE chats SET quiet_mode = ? WHERE chat_id = ?', (new_value, chat_id))
        conn.commit()
        
        status = "включён" if new_value else "выключен"
        self.send_msg(peer_id, f"🔇 Режим тишины {status}")
    
    def cmd_sban(self, user_id, chat_id, args):
        """Супер бан"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.check_permission(user_id, chat_id, 'admin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /sban в разработке")
    
    def cmd_sunban(self, user_id, chat_id, args):
        """Супер разбан"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.check_permission(user_id, chat_id, 'admin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /sunban в разработке")
    
    def cmd_addsenmoder(self, user_id, chat_id, args):
        """Добавить старшего модератора"""
        self.cmd_addmoder(user_id, chat_id, args)
    
    def cmd_bug(self, user_id, chat_id, args):
        """Сообщить о баге"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.check_activation(chat_id) and chat_id and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'admin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Опишите баг!")
            return
        
        bug_text = ' '.join(args)
        
        cursor.execute('SELECT user_id FROM bug_receivers')
        receivers = cursor.fetchall()
        
        # Отправляем владельцу
        try:
            self.send_msg(OWNER_ID, 
                        f"🐛 Баг от {self.get_user_name(user_id)}:\n"
                        f"📍 Чат: {chat_id if chat_id else 'ЛС'}\n"
                        f"📝 Текст: {bug_text}")
        except:
            pass
        
        # Отправляем другим получателям
        for receiver in receivers:
            try:
                self.send_msg(receiver[0], 
                            f"🐛 Баг от {self.get_user_name(user_id)}:\n"
                            f"📍 Чат: {chat_id if chat_id else 'ЛС'}\n"
                            f"📝 Текст: {bug_text}")
            except:
                pass
        
        self.send_msg(peer_id, "✅ Баг отправлен разработчикам")
    
    def cmd_rnickall(self, user_id, chat_id, args):
        """Сбросить все ники в беседе"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_permission(user_id, chat_id, 'admin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('DELETE FROM user_nicks WHERE chat_id = ?', (chat_id,))
        conn.commit()
        
        self.send_msg(peer_id, "✅ Все ники в беседе сброшены")
    
    def cmd_srnick(self, user_id, chat_id, args):
        """Супер сброс ника"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.check_permission(user_id, chat_id, 'admin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /srnick в разработке")
    
    def cmd_ssetnick(self, user_id, chat_id, args):
        """Супер установка ника"""
        self.cmd_setnick(user_id, chat_id, args)
    
    def cmd_srrole(self, user_id, chat_id, args):
        """Супер сброс роли"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.check_permission(user_id, chat_id, 'admin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /srrole в разработке")
    
    def cmd_srole(self, user_id, chat_id, args):
        """Супер выдача роли"""
        self.cmd_addmoder(user_id, chat_id, args)
    
    # ============= КОМАНДЫ СТАРШИХ АДМИНИСТРАТОРОВ =============
    
    def cmd_addadmin(self, user_id, chat_id, args):
        """Выдать администратора"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_permission(user_id, chat_id, 'senioradmin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('''
                UPDATE users SET role = 'admin' 
                WHERE user_id = ? AND chat_id = ?
            ''', (target_id, chat_id))
            
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO users (user_id, chat_id, role, joined_date)
                    VALUES (?, ?, ?, ?)
                ''', (target_id, chat_id, 'admin', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            
            self.send_msg(peer_id, f"✅ Пользователь [id{target_id}|] теперь администратор")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_settings(self, user_id, chat_id, args):
        """Настройки беседы"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'senioradmin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT * FROM chats WHERE chat_id = ?', (chat_id,))
        chat = cursor.fetchone()
        
        if not chat:
            self.register_chat(chat_id)
            cursor.execute('SELECT * FROM chats WHERE chat_id = ?', (chat_id,))
            chat = cursor.fetchone()
        
        settings_ru = {
            'chat_type': 'Тип беседы',
            'welcome_enabled': 'Приветствие',
            'filter_enabled': 'Фильтр',
            'flood_enabled': 'Антифлуд',
            'quiet_mode': 'Режим тишины',
            'leave_kick': 'Кик при выходе',
            'invite_moders': 'Приглашение модерами',
            'bot_activated': 'Бот активирован'
        }
        
        message = "⚙️ Настройки беседы:\n"
        for i, key in enumerate(['chat_type', 'welcome_enabled', 'filter_enabled', 
                                 'flood_enabled', 'quiet_mode', 'leave_kick', 'invite_moders', 'bot_activated']):
            if i < len(chat) - 1:
                value = chat[i+1] if i+1 < len(chat) else 'не задано'
                if key in settings_ru:
                    if key == 'chat_type':
                        status = "👥 Игроков" if value == 'players' else "🖥️ Серверная" if value == 'server' else value
                    else:
                        status = "✅ Да" if value == 1 else "❌ Нет"
                    message += f"{settings_ru[key]}: {status}\n"
        
        self.send_msg(peer_id, message)
    
    def cmd_filter(self, user_id, chat_id, args):
        """Включить/выключить фильтр"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'senioradmin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT filter_enabled FROM chats WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        current = result[0] if result else 0
        
        new_value = 0 if current else 1
        cursor.execute('UPDATE chats SET filter_enabled = ? WHERE chat_id = ?', (new_value, chat_id))
        conn.commit()
        
        status = "включён" if new_value else "выключен"
        self.send_msg(peer_id, f"📝 Фильтр {status}")
    
    def cmd_szov(self, user_id, chat_id, args):
        """Супер упоминание"""
        self.cmd_zov(user_id, chat_id, args)
    
    def cmd_serverinfo(self, user_id, chat_id, args):
        """Информация о беседе"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'senioradmin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        users_count = len(self.get_chat_users(chat_id))
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE chat_id = ?', (chat_id,))
        registered = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bans WHERE chat_id = ?', (chat_id,))
        bans = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE chat_id = ? AND warns > 0', (chat_id,))
        warned = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE chat_id = ? AND muted_until IS NOT NULL', (chat_id,))
        muted = cursor.fetchone()[0]
        
        message = (
            f"📊 Информация о беседе:\n"
            f"🆔 ID: {chat_id}\n"
            f"👥 Участников: {users_count}\n"
            f"📝 Зарегистрировано: {registered}\n"
            f"⚠️ С варнами: {warned}\n"
            f"🔇 Замучено: {muted}\n"
            f"🚫 Банов: {bans}"
        )
        
        self.send_msg(peer_id, message)
    
    def cmd_rkick(self, user_id, chat_id, args):
        """Массовый кик"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.check_permission(user_id, chat_id, 'senioradmin') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /rkick в разработке")
    
    # ============= КОМАНДЫ ВЛАДЕЛЬЦА БЕСЕДЫ =============
    
    def cmd_type(self, user_id, chat_id, args):
        """Выбрать тип беседы"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите тип: players или server")
            return
        
        chat_type = args[0].lower()
        if chat_type not in ['players', 'server']:
            self.send_msg(peer_id, "❌ Неверный тип! Доступно: players, server")
            return
        
        cursor.execute('UPDATE chats SET chat_type = ? WHERE chat_id = ?', (chat_type, chat_id))
        conn.commit()
        
        type_ru = "игроков" if chat_type == 'players' else "серверная"
        self.send_msg(peer_id, f"✅ Тип беседы изменён на: {type_ru}")
    
    def cmd_leave(self, user_id, chat_id, args):
        """Кик при выходе"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT leave_kick FROM chats WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        current = result[0] if result else 0
        
        new_value = 0 if current else 1
        cursor.execute('UPDATE chats SET leave_kick = ? WHERE chat_id = ?', (new_value, chat_id))
        conn.commit()
        
        status = "включён" if new_value else "выключен"
        self.send_msg(peer_id, f"🚪 Кик при выходе {status}")
    
    def cmd_editowner(self, user_id, chat_id, args):
        """Редактировать владельца"""
        self.cmd_addowner(user_id, chat_id, args)
    
    def cmd_pin(self, user_id, chat_id, args):
        """Закрепить сообщение"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите текст для закрепления!")
            return
        
        text = ' '.join(args)
        
        try:
            msg = vk.method('messages.send', {
                'peer_id': 2000000000 + chat_id,
                'message': text,
                'random_id': get_random_id()
            })
            
            vk.method('messages.pin', {
                'peer_id': 2000000000 + chat_id,
                'message_id': msg
            })
            
            self.send_msg(peer_id, "✅ Сообщение закреплено")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_unpin(self, user_id, chat_id, args):
        """Открепить сообщение"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        try:
            vk.method('messages.unpin', {
                'peer_id': 2000000000 + chat_id
            })
            self.send_msg(peer_id, "✅ Сообщение откреплено")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_clearwarn(self, user_id, chat_id, args):
        """Очистить предупреждения"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('UPDATE users SET warns = 0 WHERE chat_id = ?', (chat_id,))
        cursor.execute('DELETE FROM warn_history WHERE chat_id = ?', (chat_id,))
        conn.commit()
        
        self.send_msg(peer_id, "✅ Все предупреждения в беседе очищены")
    
    def cmd_rroleall(self, user_id, chat_id, args):
        """Сбросить все роли"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('''
            UPDATE users SET role = 'user' 
            WHERE chat_id = ? AND role NOT IN ('owner') AND user_id != ?
        ''', (chat_id, OWNER_ID))
        conn.commit()
        
        self.send_msg(peer_id, "✅ Все роли в беседе сброшены")
    
    def cmd_addsenadm(self, user_id, chat_id, args):
        """Добавить старшего администратора"""
        self.cmd_addadmin(user_id, chat_id, args)
    
    def cmd_masskick(self, user_id, chat_id, args):
        """Массовый кик"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /masskick в разработке")
    
    def cmd_invite(self, user_id, chat_id, args):
        """Приглашение"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /invite в разработке")
    
    def cmd_antiflood(self, user_id, chat_id, args):
        """Антифлуд"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_activation(chat_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Бот ещё не активирован в этой беседе!")
            return
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT flood_enabled FROM chats WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        current = result[0] if result else 0
        
        new_value = 0 if current else 1
        cursor.execute('UPDATE chats SET flood_enabled = ? WHERE chat_id = ?', (new_value, chat_id))
        conn.commit()
        
        status = "включён" if new_value else "выключен"
        self.send_msg(peer_id, f"🌊 Антифлуд {status}")
    
    def cmd_welcometext(self, user_id, chat_id, args):
        """Текст приветствия"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите текст приветствия!")
            return
        
        text = ' '.join(args)
        cursor.execute('UPDATE chats SET welcome_text = ?, welcome_enabled = 1 WHERE chat_id = ?', (text, chat_id))
        conn.commit()
        
        self.send_msg(peer_id, "✅ Текст приветствия установлен")
    
    def cmd_welcometextdelete(self, user_id, chat_id, args):
        """Удалить текст приветствия"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_permission(user_id, chat_id, 'owner') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('UPDATE chats SET welcome_text = NULL, welcome_enabled = 0 WHERE chat_id = ?', (chat_id,))
        conn.commit()
        
        self.send_msg(peer_id, "✅ Текст приветствия удалён")
    
    # ============= КОМАНДЫ ЗАМ.РУКОВОДИТЕЛЯ =============
    
    def cmd_gban(self, user_id, chat_id, args):
        """Глобальный бан"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Пример: /gban @user Причина")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            elif target_text.isdigit():
                target_id = int(target_text)
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            reason = ' '.join(args[1:]) if len(args) > 1 else 'Не указана'
            
            cursor.execute('''
                INSERT OR REPLACE INTO global_bans (user_id, admin_id, reason, date)
                VALUES (?, ?, ?, ?)
            ''', (target_id, user_id, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            
            cursor.execute('SELECT chat_id FROM users WHERE user_id = ?', (target_id,))
            chats = cursor.fetchall()
            
            for chat in chats:
                try:
                    vk.method('messages.removeChatUser', {
                        'chat_id': chat[0],
                        'user_id': target_id
                    })
                except:
                    pass
            
            self.send_msg(peer_id, 
                         f"🌐 Пользователь [id{target_id}|] забанен глобально.\nПричина: {reason}")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_gunban(self, user_id, chat_id, args):
        """Глобальный разбан"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            elif target_text.isdigit():
                target_id = int(target_text)
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('DELETE FROM global_bans WHERE user_id = ?', (target_id,))
            conn.commit()
            
            self.send_msg(peer_id, f"🌐 Пользователь [id{target_id}|] разбанен глобально")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_sync(self, user_id, chat_id, args):
        """Синхронизация"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        conn.commit()
        self.send_msg(peer_id, "🔄 База данных синхронизирована")
    
    def cmd_gbanlist(self, user_id, chat_id, args):
        """Список глобальных банов"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT user_id, reason, date FROM global_bans')
        bans = cursor.fetchall()
        
        if bans:
            message = "🌐 Глобальные баны:\n"
            for ban in bans:
                name = self.get_user_name(ban[0])
                message += f"• {name} – {ban[2][:10]}: {ban[1][:30]}\n"
            self.send_msg(peer_id, message)
        else:
            self.send_msg(peer_id, "✅ Нет глобальных банов")
    
    def cmd_banwords(self, user_id, chat_id, args):
        """Запрещенные слова"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT word FROM filter_words')
        words = cursor.fetchall()
        
        if words:
            message = "🚫 Запрещённые слова:\n"
            message += ', '.join([w[0] for w in words])
            self.send_msg(peer_id, message)
        else:
            self.send_msg(peer_id, "✅ Нет запрещённых слов")
    
    def cmd_gbanpl(self, user_id, chat_id, args):
        """Глобальный бан в беседах игроков"""
        self.cmd_gban(user_id, chat_id, args)
    
    def cmd_gunbanpl(self, user_id, chat_id, args):
        """Глобальный разбан в беседах игроков"""
        self.cmd_gunban(user_id, chat_id, args)
    
    def cmd_addowner(self, user_id, chat_id, args):
        """Выдать права владельца беседы"""
        if not chat_id:
            self.send_msg(user_id, "❌ Эта команда работает только в беседах!")
            return
            
        peer_id = 2000000000 + chat_id
        
        if not self.check_permission(user_id, chat_id, 'zamglav') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя! Пример: /addowner @user")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            elif target_text.isdigit():
                target_id = int(target_text)
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            # Сначала сбрасываем роль владельца у текущего владельца
            cursor.execute('''
                UPDATE users SET role = 'user' 
                WHERE chat_id = ? AND role = 'owner'
            ''', (chat_id,))
            
            # Назначаем нового владельца
            cursor.execute('''
                UPDATE users SET role = 'owner' 
                WHERE user_id = ? AND chat_id = ?
            ''', (target_id, chat_id))
            
            # Если пользователь не найден, создаем запись
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO users (user_id, chat_id, role, joined_date)
                    VALUES (?, ?, ?, ?)
                ''', (target_id, chat_id, 'owner', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            
            self.send_msg(peer_id, f"👑 Пользователь [id{target_id}|] теперь владелец беседы!")
            
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    # ============= КОМАНДЫ РУКОВОДИТЕЛЯ =============
    
    def cmd_server(self, user_id, chat_id, args):
        """Информация о сервере"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /server в разработке")
    
    def cmd_addword(self, user_id, chat_id, args):
        """Добавить слово в фильтр"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите слово!")
            return
        
        word = args[0].lower()
        
        try:
            cursor.execute('INSERT INTO filter_words (word) VALUES (?)', (word,))
            conn.commit()
            self.send_msg(peer_id, f"✅ Слово '{word}' добавлено в фильтр")
        except sqlite3.IntegrityError:
            self.send_msg(peer_id, f"❌ Слово уже в фильтре!")
    
    def cmd_delword(self, user_id, chat_id, args):
        """Удалить слово из фильтра"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите слово!")
            return
        
        word = args[0].lower()
        
        cursor.execute('DELETE FROM filter_words WHERE word = ?', (word,))
        conn.commit()
        
        self.send_msg(peer_id, f"✅ Слово '{word}' удалено из фильтра")
    
    def cmd_gremoverole(self, user_id, chat_id, args):
        """Глобальное снятие роли"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /gremoverole в разработке")
    
    def cmd_news(self, user_id, chat_id, args):
        """Новости"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /news в разработке")
    
    def cmd_addzam(self, user_id, chat_id, args):
        """Назначить зам.руководителя"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.check_permission(user_id, chat_id, 'glav') and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            elif target_text.isdigit():
                target_id = int(target_text)
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, chat_id, role, joined_date)
                VALUES (?, -1, ?, ?)
            ''', (target_id, 'zamglav', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            
            self.send_msg(peer_id, f"⚜️ Пользователь [id{target_id}|] теперь зам.руководителя бота!")
            
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_banid(self, user_id, chat_id, args):
        """Бан по ID"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /banid в разработке")
    
    def cmd_unbanid(self, user_id, chat_id, args):
        """Разбан по ID"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /unbanid в разработке")
    
    def cmd_clearchat(self, user_id, chat_id, args):
        """Очистить чат"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        self.send_msg(peer_id, "🔧 Функция /clearchat в разработке")
    
    def cmd_infoid(self, user_id, chat_id, args):
        """Информация по ID"""
        self.cmd_stats(user_id, chat_id, args)
    
    def cmd_addbug(self, user_id, chat_id, args):
        """Добавить получателя багов"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            elif target_text.isdigit():
                target_id = int(target_text)
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('INSERT OR IGNORE INTO bug_receivers (user_id) VALUES (?)', (target_id,))
            conn.commit()
            
            self.send_msg(peer_id, f"✅ Пользователь [id{target_id}|] добавлен в получатели багов")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    def cmd_listchats(self, user_id, chat_id, args):
        """Список чатов"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        cursor.execute('SELECT chat_id, chat_type, bot_activated FROM chats')
        chats = cursor.fetchall()
        
        if chats:
            message = "📋 Список чатов:\n"
            for chat in chats:
                status = "✅" if chat[2] == 1 else "❌"
                message += f"{status} Чат {chat[0]} ({chat[1]})\n"
            self.send_msg(peer_id, message)
        else:
            self.send_msg(peer_id, "❌ Нет чатов в базе")
    
    def cmd_adddev(self, user_id, chat_id, args):
        """Добавить разработчика"""
        self.cmd_addzam(user_id, chat_id, args)
    
    def cmd_delbug(self, user_id, chat_id, args):
        """Удалить получателя багов"""
        peer_id = 2000000000 + chat_id if chat_id else user_id
        
        if not self.is_global_admin(user_id) and user_id != OWNER_ID:
            self.send_msg(peer_id, "❌ Недостаточно прав!")
            return
        
        if not args:
            self.send_msg(peer_id, "❌ Укажите пользователя!")
            return
        
        try:
            target_text = args[0]
            if target_text.startswith('[id') and '|' in target_text:
                target_id = int(target_text.split('[id')[1].split('|')[0])
            elif target_text.isdigit():
                target_id = int(target_text)
            else:
                numbers = re.findall(r'\d+', target_text)
                if numbers:
                    target_id = int(numbers[0])
                else:
                    self.send_msg(peer_id, "❌ Не удалось определить ID пользователя!")
                    return
            
            cursor.execute('DELETE FROM bug_receivers WHERE user_id = ?', (target_id,))
            conn.commit()
            
            self.send_msg(peer_id, f"✅ Пользователь [id{target_id}|] удалён из получателей багов")
        except Exception as e:
            self.send_msg(peer_id, f"❌ Ошибка: {e}")
    
    # ============= ПРОВЕРКИ =============
    
    def check_mute(self, user_id, chat_id):
        """Проверка мута"""
        cursor.execute('SELECT muted_until FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        result = cursor.fetchone()
        
        if result and result[0]:
            try:
                muted_until = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                if muted_until > datetime.now():
                    return True
                else:
                    cursor.execute('UPDATE users SET muted_until = NULL WHERE user_id = ? AND chat_id = ?', 
                                 (user_id, chat_id))
                    conn.commit()
            except:
                pass
        return False
    
    def check_ban(self, user_id, chat_id):
        """Проверка бана"""
        cursor.execute('SELECT banned FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        result = cursor.fetchone()
        return result and result[0] == 1
    
    def check_global_ban(self, user_id):
        """Проверка глобального бана"""
        cursor.execute('SELECT * FROM global_bans WHERE user_id = ?', (user_id,))
        return cursor.fetchone() is not None
    
    def process_message(self, event):
        """Обработка сообщения"""
        user_id = event.user_id
        
        # Получаем ID чата правильно
        if event.from_chat:
            chat_id = event.chat_id
            peer_id = 2000000000 + chat_id
        else:
            chat_id = 0
            peer_id = event.user_id
            
        message = event.text

        # Регистрируем чат и пользователя
        if chat_id:
            self.register_chat(chat_id)
            self.register_user(user_id, chat_id)
            
            # Обновляем последнюю активность
            cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ? AND chat_id = ?',
                         (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id, chat_id))
            conn.commit()
            
            # Проверяем глобальный бан
            if self.check_global_ban(user_id):
                try:
                    vk.method('messages.removeChatUser', {
                        'chat_id': chat_id,
                        'user_id': user_id
                    })
                except:
                    pass
                return
            
            # Проверяем бан в чате
            if self.check_ban(user_id, chat_id):
                try:
                    vk.method('messages.removeChatUser', {
                        'chat_id': chat_id,
                        'user_id': user_id
                    })
                except:
                    pass
                return
            
            # Проверяем мут
            if self.check_mute(user_id, chat_id):
                # Не обрабатываем команды от замученных
                return
            
            # Проверяем активацию бота (только для чатов)
            if not self.check_activation(chat_id) and user_id != OWNER_ID:
                # Если бот не активирован, разрешаем только /start
                if message and message.startswith('/start'):
                    pass  # Пропускаем для обработки
                else:
                    # Игнорируем все остальные сообщения
                    return
            
            # Проверяем фильтр (только если бот активирован)
            if message and not message.startswith('/') and self.check_activation(chat_id):
                cursor.execute('SELECT filter_enabled FROM chats WHERE chat_id = ?', (chat_id,))
                result = cursor.fetchone()
                if result and result[0] == 1:
                    cursor.execute('SELECT word FROM filter_words')
                    bad_words = cursor.fetchall()
                    for word in bad_words:
                        if word[0].lower() in message.lower():
                            # Удаляем сообщение
                            try:
                                vk.method('messages.delete', {
                                    'message_ids': [event.message_id],
                                    'delete_for_all': 1
                                })
                            except:
                                pass
                            
                            # Выдаем предупреждение
                            cursor.execute('SELECT warns FROM users WHERE user_id = ? AND chat_id = ?', 
                                         (user_id, chat_id))
                            result = cursor.fetchone()
                            warns = result[0] if result else 0
                            new_warns = warns + 1
                            
                            cursor.execute('UPDATE users SET warns = ? WHERE user_id = ? AND chat_id = ?',
                                         (new_warns, user_id, chat_id))
                            
                            cursor.execute('''
                                INSERT INTO warn_history (user_id, chat_id, admin_id, reason, date)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (user_id, chat_id, 0, 'Мат (автоматически)', 
                                 datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                            conn.commit()
                            
                            if new_warns >= 3:
                                muted_until = datetime.now() + timedelta(hours=24)
                                cursor.execute('''
                                    UPDATE users SET muted_until = ?, warns = 0 
                                    WHERE user_id = ? AND chat_id = ?
                                ''', (muted_until.strftime('%Y-%m-%d %H:%M:%S'), user_id, chat_id))
                                conn.commit()
                            break
    
        # Обрабатываем команды
        if message and message.startswith('/'):
            parts = message.split()
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            if cmd in self.commands:
                try:
                    self.commands[cmd](user_id, chat_id, args)
                except Exception as e:
                    print(f"Ошибка в команде {cmd}: {e}")
                    self.send_msg(peer_id, f"❌ Произошла ошибка: {e}")
    
    def run(self):
        """Запуск бота"""
        print("🤖 BLACK FIB BOT ЗАПУЩЕН!")
        print(f"👑 Владелец: [id{OWNER_ID}|Vlad]")
        print("📱 Режим: Ожидание сообщений")
        print("💬 Команды: /help")
        print("-" * 40)
        
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                # Обрабатываем все сообщения
                self.process_message(event)

if __name__ == '__main__':
    bot = AdminBot()
    bot.run()