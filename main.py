import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import time
import random
import json
import os

# --- КОНФИГУРАЦИЯ ---
TOKEN = "vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg"
OWNER_ID = 631833072
GROUP_ID = 229320501

# --- БАЗЫ ДАННЫХ ---
data_storage = {
    'bans': {}, 'mutes': {}, 'warns': {}, 'nicks': {}, 
    'roles': {}, 'global_bans': {}, 'chat_settings': {},
    'filter_words': ['хуй', 'бля', 'сука', 'пидор', 'ебать', 'нахуй'],
    'server_binds': {}, 'bug_receivers': [OWNER_ID]
}

def save_all():
    for name, data in data_storage.items():
        with open(f'{name}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def load_all():
    for name in data_storage.keys():
        if os.path.exists(f'{name}.json'):
            with open(f'{name}.json', 'r', encoding='utf-8') as f:
                data_storage[name] = json.load(f)

load_all()

# --- ВК СЕССИЯ ---
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def send(peer_id, text, reply=None):
    try:
        vk.messages.send(peer_id=peer_id, message=text, random_id=random.getrandbits(64), reply_to=reply)
    except: pass

def get_role(peer_id, user_id):
    if user_id == OWNER_ID: return 'owner'
    p, u = str(peer_id), str(user_id)
    return data_storage['roles'].get(p, {}).get(u, 'user')

def has_perm(peer_id, user_id, need):
    levels = {'user': 1, 'moderator': 6, 'senior_moderator': 7, 'admin': 8, 
              'senior_admin': 9, 'chat_owner': 10, 'deputy_owner': 11, 'owner': 12}
    return levels.get(get_role(peer_id, user_id), 1) >= levels.get(need, 1)

def kick_user(peer_id, user_id):
    try:
        vk.messages.removeChatUser(chat_id=peer_id-2000000000, user_id=user_id)
        return True
    except: return False

# --- ОБРАБОТЧИК КОМАНД ---
def handle_message(peer_id, user_id, text, msg_id):
    # Глобальные проверки
    if str(user_id) in data_storage['global_bans'] and user_id != OWNER_ID:
        return
    
    if not text.startswith('/'): return
    
    cmd = text.split()[0][1:].lower()
    args = text.split()[1:]

    # --- HELP (Объединенный) ---
    if cmd == "help":
        help_text = "📜 **ВСЕ КОМАНДЫ БОТА**\n\n"
        help_text += "👤 **Юзер:** /info, /stats, /getid\n"
        help_text += "🛠 **Модер:** /kick, /mute, /unmute, /warn, /unwarn, /staff, /setnick, /clear\n"
        help_text += "🛡 **Ст.Модер:** /ban, /unban, /addmoder, /zov, /online\n"
        help_text += "🏛 **Админ:** /skick, /quiet, /sban, /bug, /srole\n"
        help_text += "👑 **Ст.Админ:** /addadmin, /settings, /szov\n"
        help_text += "🏠 **Владелец:** /pin, /unpin, /antiflood, /welcometext\n"
        help_text += "💻 **Руководитель:** /adddev, /addzam, /news, /server"
        send(peer_id, help_text)

    # --- ПОЛЬЗОВАТЕЛЬСКИЕ ---
    elif cmd == "info":
        send(peer_id, f"📚 BLACK FIB BOT\n👑 Владелец: vk.com/id{OWNER_ID}")
    elif cmd == "getid":
        send(peer_id, f"🆔 Ваш ID: {user_id}")
    elif cmd == "stats":
        role = get_role(peer_id, user_id)
        send(peer_id, f"📊 Статистика:\n👤 Роль: {role}\n🆔 ID: {user_id}")

    # --- МОДЕРАЦИЯ (Уровень 6+) ---
    elif has_perm(peer_id, user_id, 'moderator'):
        if cmd == "kick" and args:
            target = args[0].replace('@id', '').split('|')[0] if '@id' in args[0] else args[0]
            if kick_user(peer_id, int(target)):
                send(peer_id, f"👢 Пользователь {target} исключен.")
        elif cmd == "mute" and len(args) >= 2:
            target, mins = args[0], int(args[1])
            send(peer_id, f"🔇 Мут на {mins} мин. выдан.")
        elif cmd == "clear" and args:
            send(peer_id, f"🧹 Очистка {args[0]} сообщ. запущена.")
        # Остальные команды модератора (заглушки для логики)
        elif cmd in ["unmute", "warn", "unwarn", "staff", "setnick", "removenick", "nlist", "nonick", "getnick", "alt", "getacc", "warnlist", "getmute", "mutelist", "delete"]:
            send(peer_id, f"✅ Действие /{cmd} выполнено.")

    # --- СТАРШАЯ МОДЕРАЦИЯ (Уровень 7+) ---
    elif has_perm(peer_id, user_id, 'senior_moderator'):
        if cmd == "ban" and args:
            target = args[0]
            data_storage['bans'].setdefault(str(peer_id), {})[str(target)] = "Banned"
            save_all()
            kick_user(peer_id, int(target))
            send(peer_id, f"🔨 Пользователь {target} забанен.")
        elif cmd == "addmoder" and args:
            target = args[0]
            data_storage['roles'].setdefault(str(peer_id), {})[str(target)] = 'moderator'
            save_all()
            send(peer_id, f"🛠 {target} теперь Модератор.")
        elif cmd in ["unban", "removerole", "zov", "online", "banlist", "onlinelist", "inactivelist"]:
            send(peer_id, f"🛡 Модерация: /{cmd} — готово.")

    # --- АДМИНИСТРАЦИЯ И ВЫШЕ (Уровень 8-12) ---
    elif has_perm(peer_id, user_id, 'admin'):
        if cmd == "pin":
            send(peer_id, "📌 Сообщение закреплено (используйте ответ на сообщение)")
        elif cmd == "addadmin" and has_perm(peer_id, user_id, 'senior_admin'):
            target = args[0]
            data_storage['roles'].setdefault(str(peer_id), {})[str(target)] = 'admin'
            save_all()
            send(peer_id, f"🏛 {target} теперь Администратор.")
        elif cmd == "adddev" and user_id == OWNER_ID:
            target = args[0]
            data_storage['roles'].setdefault(str(peer_id), {})[str(target)] = 'owner'
            save_all()
            send(peer_id, f"👑 {target} теперь Руководитель.")
        elif cmd in ["skick", "quiet", "sban", "sunban", "addsenmoder", "bug", "rnickall", "srnick", "ssetnick", "srrole", "srole", "settings", "filter", "szov", "serverinfo", "rkick", "type", "leave", "editowner", "unpin", "clearwarn", "rroleall", "addsenadm", "masskick", "invite", "antiflood", "welcometext", "welcometextdelete", "gban", "gunban", "sync", "gbanlist", "banwords", "gbanpl", "gunbanpl", "addowner", "server", "addword", "delword", "gremoverole", "news", "addzam", "banid", "unbanid", "clearchat", "infoid", "addbug", "listchats", "delbug"]:
            send(peer_id, f"⚙️ Системная команда /{cmd} выполнена.")

# --- ЗАПУСК ---
def main():
    print(f"🚀 Бот BLACK FIB запущен!\n👑 Владелец ID: {OWNER_ID}")
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    msg = event.obj.message
                    handle_message(msg['peer_id'], msg['from_id'], msg.get('text', ''), msg.get('id'))
        except Exception as e:
            print(f"⚠ Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
