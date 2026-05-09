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
# Мы создаем словари для всего, чтобы бот ничего не забывал
bans = {}
mutes = {}
warns = {}
nicks = {}
roles = {}
global_bans = {}
chat_settings = {}
filter_words = ['хуй', 'бля', 'сука', 'пидор', 'ебать', 'нахуй']

def save_all():
    databases = {
        'bans': bans, 'mutes': mutes, 'warns': warns, 
        'nicks': nicks, 'roles': roles, 'global_bans': global_bans,
        'chat_settings': chat_settings
    }
    for name, data in databases.items():
        with open(f"{name}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def load_all():
    global bans, mutes, warns, nicks, roles, global_bans, chat_settings
    files = {
        'bans.json': 'bans', 'mutes.json': 'mutes', 'warns.json': 'warns',
        'nicks.json': 'nicks', 'roles.json': 'roles', 'global_bans.json': 'global_bans',
        'chat_settings.json': 'chat_settings'
    }
    for filename, var_name in files.items():
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                globals()[var_name] = json.load(f)

load_all()

# --- ИНИЦИАЛИЗАЦИЯ ВК ---
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def send(peer_id, text, reply=None):
    try:
        vk.messages.send(peer_id=peer_id, message=text, random_id=random.getrandbits(64), reply_to=reply)
    except Exception as e: print(f"Ошибка отправки: {e}")

def get_role_lvl(peer_id, user_id):
    if user_id == OWNER_ID: return 10
    p, u = str(peer_id), str(user_id)
    if p in roles and u in roles[p]:
        return roles[p][u]
    return 0

def get_nick(peer_id, user_id):
    p, u = str(peer_id), str(user_id)
    if p in nicks and u in nicks[p]:
        return nicks[p][u]
    try:
        user = vk.users.get(user_ids=user_id)[0]
        return f"{user['first_name']} {user['last_name']}"
    except: return f"id{user_id}"

def get_target_id(text, args):
    if not args: return None
    raw = args[0]
    target = raw.replace('https://vk.com/id', '').replace('[id', '').split('|')[0].replace(']', '').replace('@', '')
    try: return int(target)
    except: return None

# --- ОБРАБОТЧИК (ОСНОВНАЯ ЛОГИКА) ---
def handle(peer_id, user_id, text, msg_id):
    p_id = str(peer_id)
    u_id = str(user_id)
    
    if u_id in global_bans and user_id != OWNER_ID:
        return

    parts = text.split()
    cmd = parts[0][1:].lower()
    args = parts[1:]
    lvl = get_role_lvl(peer_id, user_id)

    # ======================================================
    # КОМАНДЫ ПОЛЬЗОВАТЕЛЕЙ (LVL 0)
    # ======================================================
    if cmd == "info":
        res = "✅ Официальные ресурсы бота:\n"
        res += "🔹 Группа: vk.com/club229320501\n"
        res += "👑 Разработчик: vk.com/id631833072"
        send(peer_id, res, msg_id)

    elif cmd == "stats":
        w = warns.get(p_id, {}).get(u_id, 0)
        role_name = {0: "Пользователь", 1: "Модератор", 2: "Ст. Модератор", 3: "Администратор", 10: "Разработчик"}.get(lvl, "Участник")
        send(peer_id, f"📊 Статистика {get_nick(peer_id, user_id)}:\n🔑 Роль: {role_name}\n⚠ Варны: {w}/3", msg_id)

    elif cmd == "getid":
        send(peer_id, f"🆔 Ваш оригинальный ID: {user_id}", msg_id)

    # ======================================================
    # КОМАНДЫ МОДЕРАТОРОВ (LVL 1)
    # ======================================================
    elif lvl >= 1 and cmd in ["kick", "mute", "unmute", "warn", "unwarn", "staff", "setnick", "removenick", "clear", "delete"]:
        target = get_target_id(text, args)
        
        if cmd == "kick":
            if not target: return send(peer_id, "⚠ Укажите пользователя!", msg_id)
            try:
                vk.messages.removeChatUser(chat_id=peer_id-2000000000, user_id=target)
                send(peer_id, f"👢 Пользователь {get_nick(peer_id, target)} исключен.")
            except: send(peer_id, "❌ Ошибка: Недостаточно прав у бота.")

        elif cmd == "warn":
            if not target: return send(peer_id, "⚠ Укажите пользователя!", msg_id)
            warns.setdefault(p_id, {})
            warns[p_id][str(target)] = warns[p_id].get(str(target), 0) + 1
            save_all()
            send(peer_id, f"⚠ {get_nick(peer_id, target)} получил варн ({warns[p_id][str(target)]}/3)")

        elif cmd == "setnick":
            if len(args) < 2: return send(peer_id, "⚠ Укажите ник!", msg_id)
            nicks.setdefault(p_id, {})[u_id] = " ".join(args)
            save_all()
            send(peer_id, f"📝 Ник изменен на: {' '.join(args)}")

        elif cmd == "clear":
            send(peer_id, "🧹 Очистка чата... Сообщения удаляются.")

    # ======================================================
    # КОМАНДЫ СТАРШИХ МОДЕРАТОРОВ (LVL 2)
    # ======================================================
    elif lvl >= 2 and cmd in ["ban", "unban", "addmoder", "removerole", "zov", "online"]:
        target = get_target_id(text, args)
        
        if cmd == "ban":
            if not target: return
            bans.setdefault(p_id, {})[str(target)] = True
            save_all()
            send(peer_id, f"🔨 {get_nick(peer_id, target)} забанен в этой беседе.")
            try: vk.messages.removeChatUser(chat_id=peer_id-2000000000, user_id=target)
            except: pass

        elif cmd == "addmoder":
            if not target: return
            roles.setdefault(p_id, {})[str(target)] = 1
            save_all()
            send(peer_id, f"🛠 {get_nick(peer_id, target)} теперь Модератор.")

        elif cmd == "zov":
            send(peer_id, "📢 Внимание! Всем участникам быть в чате!")

    # ======================================================
    # КОМАНДЫ АДМИНИСТРАТОРОВ (LVL 3)
    # ======================================================
    elif lvl >= 3 and cmd in ["skick", "quiet", "sban", "srole", "addsenmoder"]:
        if cmd == "quiet":
            chat_settings.setdefault(p_id, {})
            chat_settings[p_id]['quiet'] = not chat_settings[p_id].get('quiet', False)
            save_all()
            status = "ВКЛЮЧЕН" if chat_settings[p_id]['quiet'] else "ВЫКЛЮЧЕН"
            send(peer_id, f"🔇 Режим тишины {status}")

    # ======================================================
    # КОМАНДЫ ВЛАДЕЛЬЦА (LVL 5) И РУКОВОДИТЕЛЯ (LVL 10)
    # ======================================================
    elif lvl >= 5 and cmd in ["pin", "unpin", "antiflood", "welcometext", "news", "adddev", "gban"]:
        if cmd == "pin":
            try: vk.messages.pin(peer_id=peer_id, conversation_message_id=msg_id)
            except: send(peer_id, "❌ Не удалось закрепить.")
            
        elif cmd == "gban" and lvl >= 10:
            target = get_target_id(text, args)
            if target:
                global_bans[str(target)] = True
                save_all()
                send(peer_id, f"🌎 {target} получил ГЛОБАЛЬНЫЙ БАН.")

        elif cmd == "news" and user_id == OWNER_ID:
            send(peer_id, "🗞 Рассылка новостей запущена!")

    # ======================================================
    # HELP (ЕДИНЫЙ ИНТЕРФЕЙС)
    # ======================================================
    elif cmd == "help":
        h = "📋 [ СПИСОК КОМАНД ]\n"
        h += "👤 Юзер: /info /stats /getid\n"
        h += "🛠 Модер: /kick /mute /unmute /warn /unwarn /staff /setnick /clear /delete\n"
        h += "🛡 Ст.Модер: /ban /unban /addmoder /removerole /zov /online /banlist\n"
        h += "🏛 Админ: /skick /quiet /sban /sunban /addsenmoder /bug /srole\n"
        h += "👑 Ст.Админ: /addadmin /settings /filter /szov /serverinfo\n"
        h += "🏠 Владелец: /pin /unpin /clearwarn /masskick /welcometext\n"
        h += "🔼 Зам: /gban /gunban /sync /gbanlist /addowner\n"
        h += "💻 Руководитель: /server /news /addzam /adddev /listchats"
        send(peer_id, h, msg_id)

# --- ГЛАВНЫЙ ЦИКЛ ---
def main():
    print("--------------------------------------------------")
    print("🚀 БОТ BLACK FIB ЗАПУЩЕН!")
    print(f"👑 РАЗРАБОТЧИК: {OWNER_ID}")
    print("--------------------------------------------------")
    
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
                    msg = event.obj.message
                    text = msg.get('text', '').strip()
                    if text.startswith('/'):
                        handle(msg['peer_id'], msg['from_id'], text, msg.get('conversation_message_id'))
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
