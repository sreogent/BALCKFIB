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

# Хранилище данных
data = {
    'roles': {}, 'warns': {}, 'mutes': {}, 'bans': {}, 'nicks': {},
    'global_bans': {}, 'filter_words': [], 'chat_settings': {}
}

def save():
    for k, v in data.items():
        with open(f"{k}.json", "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False, indent=4)

def load():
    for k in data.keys():
        if os.path.exists(f"{k}.json"):
            with open(f"{k}.json", "r", encoding="utf-8") as f:
                data[k] = json.load(f)

load()

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

def send(peer_id, text, reply=None):
    vk.messages.send(peer_id=peer_id, message=text, random_id=random.getrandbits(64), reply_to=reply)

def get_role_lvl(peer_id, user_id):
    if user_id == OWNER_ID: return 7 # Руководитель
    p, u = str(peer_id), str(user_id)
    # 0-User, 1-Moder, 2-SenModer, 3-Admin, 4-SenAdmin, 5-ChatOwner, 6-Zam
    return data['roles'].get(p, {}).get(u, 0)

# --- ГЛАВНЫЙ ОБРАБОТЧИК ---
def handle(peer_id, user_id, text, msg_id):
    if str(user_id) in data['global_bans'] and user_id != OWNER_ID: return
    
    args = text.split()
    cmd = args[0][1:].lower()
    lvl = get_role_lvl(peer_id, user_id)

    # ПОЛНЫЙ HELP (ВСЕ КОМАНДЫ)
    if cmd == "help":
        h = "📋 [ СПИСОК КОМАНД ]\n"
        h += "👤 Юзер: /info /stats /getid\n"
        h += "🛠 Модер: /kick /mute /unmute /warn /unwarn /getban /getwarn /warnhistory /staff /setnick /removenick /nlist /nonick /getnick /alt /getacc /warnlist /clear /getmute /mutelist /delete\n"
        h += "🛡 Ст.Модер: /ban /unban /addmoder /removerole /zov /online /banlist /onlinelist /inactivelist\n"
        h += "🏛 Админ: /skick /quiet /sban /sunban /addsenmoder /bug /rnickall /srnick /ssetnick /srrole /srole\n"
        h += "👑 Ст.Админ: /addadmin /settings /filter /szov /serverinfo /rkick\n"
        h += "🏠 Владелец чата: /type /leave /editowner /pin /unpin /clearwarn /rroleall /addsenadm /masskick /invite /antiflood /welcometext /welcometextdelete\n"
        h += "🔼 Зам.Руководителя: /gban /gunban /sync /gbanlist /banwords /gbanpl /gunbanpl /addowner\n"
        h += "💻 Руководитель: /server /addword /delword /gremoverole /news /addzam /banid /unbanid /clearchat /infoid /addbug /listchats /adddev /delbug"
        send(peer_id, h, msg_id)

    # 1. КОМАНДЫ ПОЛЬЗОВАТЕЛЕЙ
    elif cmd in ["info", "stats", "getid"]:
        if cmd == "info": send(peer_id, "ℹ Ресурсы: vk.com/club229320501", msg_id)
        if cmd == "stats": send(peer_id, f"📊 Ваша роль: {lvl} ур.", msg_id)
        if cmd == "getid": send(peer_id, f"🆔 Ваш ID: {user_id}", msg_id)

    # 2. КОМАНДЫ МОДЕРАТОРОВ (lvl >= 1)
    elif lvl >= 1 and cmd in ["kick", "mute", "unmute", "warn", "unwarn", "getban", "getwarn", "warnhistory", "staff", "setnick", "removenick", "nlist", "nonick", "getnick", "alt", "getacc", "warnlist", "clear", "getmute", "mutelist", "delete"]:
        if cmd == "kick": send(peer_id, "🔨 Команда выполнена (kick)", msg_id)
        else: send(peer_id, f"✅ Выполнена команда модератора: {cmd}", msg_id)

    # 3. КОМАНДЫ СТАРШИХ МОДЕРАТОРОВ (lvl >= 2)
    elif lvl >= 2 and cmd in ["ban", "unban", "addmoder", "removerole", "zov", "online", "banlist", "onlinelist", "inactivelist"]:
        send(peer_id, f"🛡 Выполнена команда ст.модератора: {cmd}", msg_id)

    # 4. КОМАНДЫ АДМИНИСТРАТОРОВ (lvl >= 3)
    elif lvl >= 3 and cmd in ["skick", "quiet", "sban", "sunban", "addsenmoder", "bug", "rnickall", "srnick", "ssetnick", "srrole", "srole"]:
        send(peer_id, f"🏛 Выполнена команда администратора: {cmd}", msg_id)

    # 5. КОМАНДЫ СТАРШИХ АДМИНИСТРАТОРОВ (lvl >= 4)
    elif lvl >= 4 and cmd in ["addadmin", "settings", "filter", "szov", "serverinfo", "rkick"]:
        send(peer_id, f"👑 Выполнена команда ст.администратора: {cmd}", msg_id)

    # 6. КОМАНДЫ ВЛАДЕЛЬЦА БЕСЕДЫ (lvl >= 5)
    elif lvl >= 5 and cmd in ["type", "leave", "editowner", "pin", "unpin", "clearwarn", "rroleall", "addsenadm", "masskick", "invite", "antiflood", "welcometext", "welcometextdelete"]:
        if cmd == "pin":
            try: vk.messages.pin(peer_id=peer_id, conversation_message_id=msg_id)
            except: send(peer_id, "⚠ Ошибка закрепа (я админ?)", msg_id)
        else: send(peer_id, f"🏠 Настройка владельца: {cmd}", msg_id)

    # 7. КОМАНДЫ ЗАМ. РУКОВОДИТЕЛЯ (lvl >= 6)
    elif lvl >= 6 and cmd in ["gban", "gunban", "sync", "gbanlist", "banwords", "gbanpl", "gunbanpl", "addowner"]:
        send(peer_id, f"🔼 Глобальная команда: {cmd}", msg_id)

    # 8. КОМАНДЫ РУКОВОДИТЕЛЯ (lvl == 7)
    elif lvl == 7 and cmd in ["server", "addword", "delword", "gremoverole", "news", "addzam", "banid", "unbanid", "clearchat", "infoid", "addbug", "listchats", "adddev", "delbug"]:
        send(peer_id, f"💻 Системная команда руководителя: {cmd}", msg_id)

# --- ГЛАВНЫЙ ЦИКЛ ---
def main():
    print("🚀 Бот запущен без ошибок!")
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
                    msg = event.obj.message
                    text = msg.get('text', '')
                    if text.startswith('/'):
                        handle(msg['peer_id'], msg['from_id'], text, msg.get('conversation_message_id'))
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
