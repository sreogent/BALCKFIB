import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import time
import random
import json
import os

# =========== ТВОИ ДАННЫЕ ===========
TOKEN = "vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg"
CREATOR_ID = 749488560
GROUP_ID = 229320501
# ===================================

# Функции загрузки/сохранения
def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Инициализация БД
bans = load_data('bans.json')
mutes = load_data('mutes.json')
warns = load_data('warns.json')
nicks = load_data('nicks.json')
roles = load_data('roles.json')
global_bans = load_data('global_bans.json') if os.path.exists('global_bans.json') else []
filter_words = load_data('filter_words.json') if os.path.exists('filter_words.json') else ['хуй', 'бля', 'сука', 'пидор', 'ебать', 'нахуй']
chat_types = load_data('chat_types.json')
quiet_modes = load_data('quiet_modes.json')
anti_flood = load_data('anti_flood.json')
welcome_texts = load_data('welcome_texts.json')
chat_binds = load_data('chat_binds.json')
bug_receivers = load_data('bug_receivers.json') if os.path.exists('bug_receivers.json') else [CREATOR_ID]

# Уровни ролей
ROLE_LEVEL = {
    'creator': 10,
    'deputy_creator': 9,
    'special_admin': 8,
    'deputy_special': 7,
    'senior_admin': 6,
    'admin': 5,
    'senior_moderator': 4,
    'moderator': 3,
    'helper': 2,
    'user': 1
}

# VK инициализация
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

def send(peer_id, text, reply=None):
    try:
        vk.messages.send(peer_id=peer_id, message=text, random_id=random.randint(1, 999999999), reply_to=reply)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_user_info(user_id):
    try:
        user = vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
        return f"{user['first_name']} {user['last_name']}"
    except:
        return f"ID{user_id}"

def get_nick(peer_id, user_id):
    p, u = str(peer_id), str(user_id)
    if p in nicks and u in nicks[p]:
        return nicks[p][u]
    return get_user_info(user_id)

def get_role(peer_id, user_id):
    if user_id == CREATOR_ID:
        return 'creator'
    p, u = str(peer_id), str(user_id)
    if p in roles and u in roles[p]:
        return roles[p][u]
    return 'user'

def has_permission(peer_id, user_id, need_role):
    role = get_role(peer_id, user_id)
    return ROLE_LEVEL.get(role, 1) >= ROLE_LEVEL.get(need_role, 1)

def is_muted(peer_id, user_id):
    p, u = str(peer_id), str(user_id)
    if p in mutes and u in mutes[p]:
        if mutes[p][u] > time.time():
            return True
        else:
            del mutes[p][u]
            save_data('mutes.json', mutes)
    return False

def is_banned(peer_id, user_id):
    p, u = str(peer_id), str(user_id)
    if p in bans and u in bans[p]:
        return True
    if user_id in global_bans:
        return True
    return False

def kick_chat(peer_id, user_id):
    try:
        vk.messages.removeChatUser(chat_id=peer_id-2000000000, user_id=user_id)
        return True
    except:
        return False

def clear_chat(peer_id, count):
    try:
        msgs = vk.messages.getHistory(peer_id=peer_id, count=min(count, 100))
        ids = [m['id'] for m in msgs['items']]
        if ids:
            vk.messages.delete(message_ids=ids, delete_for_all=1, peer_id=peer_id)
        return True
    except:
        return False

def mention_all(peer_id):
    try:
        members = vk.messages.getConversationMembers(peer_id=peer_id)
        users = []
        for m in members['items']:
            if m['member_id'] > 0:
                users.append(f"@id{m['member_id']}")
        send(peer_id, "🔔 ВНИМАНИЕ! " + " ".join(users[:50]))
    except:
        pass

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

def leave_chat(peer_id):
    try:
        vk.messages.removeChatUser(chat_id=peer_id-2000000000, user_id=-GROUP_ID)
        return True
    except:
        return False

# Обработка команд
def handle(peer_id, user_id, text, msg_id):
    # Проверки
    if is_banned(peer_id, user_id) and user_id != CREATOR_ID:
        send(peer_id, "🔒 Вы забанены в этой беседе!", msg_id)
        return
    if is_muted(peer_id, user_id) and user_id != CREATOR_ID:
        send(peer_id, "🔇 Вы замучены и не можете писать!", msg_id)
        return
    
    # Фильтр мата
    for word in filter_words:
        if word.lower() in text.lower():
            send(peer_id, f"🚫 Запрещенное слово: {word}", msg_id)
            return
    
    # ==================== ДЛЯ ВСЕХ ====================
    if text == "/info":
        send(peer_id, "📚 BLACK FIB BOT\n━━━━━━━━━━━━\n✅ Бот работает\n👑 Создатель: @id749488560\n💡 /help - список команд")
    
    elif text == "/help":
        send(peer_id, "📋 КОМАНДЫ:\n/info, /stats, /getid, /test, /ping\n/kick, /mute, /unmute, /warn, /clear\n/ban, /addmoder, /zov, /quiet\n/gban, /banwords, /pull, /pullinfo\n👉 Полный список: /fullhelp")
    
    elif text == "/fullhelp":
        send(peer_id, "📚 ВСЕ КОМАНДЫ:\n━━━━━━━━━━━━\n👤 /info /stats /getid /test /ping\n💚 /kick /mute /unmute /warn /unwarn /clear /staff /setnick /nlist /warnlist /mutelist\n💙 /ban /unban /addmoder /removerole /zov /banlist\n🔵 /quiet /addsenmoder /bug /rnickall\n🟢 /addadmin /settings /filter /serverinfo\n🟡 /type /leave /pin /unpin /antiflood /welcometext\n🔴 /gban /gunban /gbanlist /banwords /addowner /skick /sban\n🟠 /addword /delword /pull /pullinfo /delpull /srnick /ssetnick /srrole /srole /szov\n👑 /gremoverole /news /addzam\n⚜️ /banid /unbanid /clearchat /infoid /listchats /server\n👑 /adddev /addbug /delbug /sync")
    
    elif text == "/getid":
        send(peer_id, f"🆔 Ваш ID: {user_id}")
    
    elif text == "/test":
        send(peer_id, "✅ Бот работает! Комар носа не подточит!")
    
    elif text == "/ping":
        send(peer_id, "🏓 Понг! Бот активен.")
    
    elif text.startswith("/stats"):
        parts = text.split()
        target = user_id
        if len(parts) > 1:
            if parts[1].startswith("@id"):
                target = int(parts[1][3:])
            elif parts[1].isdigit():
                target = int(parts[1])
        w = warns.get(str(peer_id), {}).get(str(target), {}).get('count', 0)
        m = "Да" if is_muted(peer_id, target) else "Нет"
        send(peer_id, f"📊 Статистика {get_nick(peer_id, target)}\n⚠ Варны: {w}\n🔇 Мут: {m}\n👑 Роль: {get_role(peer_id, target)}")
    
    # ==================== АКТИВАЦИЯ ====================
    elif text == "/start":
        send(peer_id, "✅ BLACK FIB BOT АКТИВИРОВАН!\n━━━━━━━━━━━━\n📋 /help - список команд\n⚡ Бот готов к работе!")
    
    # ==================== ХЕЛПЕРЫ ====================
    elif text.startswith("/kick") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
            if kick_chat(peer_id, target):
                send(peer_id, f"👢 Кикнут {get_nick(peer_id, target)}\nПричина: {reason}")
    
    elif text.startswith("/mute") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) >= 3:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            minutes = int(parts[2])
            reason = " ".join(parts[3:]) if len(parts) > 3 else "Не указана"
            p, u = str(peer_id), str(target)
            if p not in mutes: mutes[p] = {}
            mutes[p][u] = time.time() + minutes * 60
            save_data('mutes.json', mutes)
            send(peer_id, f"🔇 Мут {minutes} мин для {get_nick(peer_id, target)}\nПричина: {reason}")
    
    elif text.startswith("/unmute") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in mutes and u in mutes[p]:
                del mutes[p][u]
                save_data('mutes.json', mutes)
                send(peer_id, f"✅ Мут снят с {get_nick(peer_id, target)}")
    
    elif text.startswith("/warn") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Нарушение"
            p, u = str(peer_id), str(target)
            if p not in warns: warns[p] = {}
            if u not in warns[p]: warns[p][u] = {'count': 0, 'reasons': []}
            warns[p][u]['count'] += 1
            warns[p][u]['reasons'].append(reason)
            save_data('warns.json', warns)
            cnt = warns[p][u]['count']
            send(peer_id, f"⚠ Варн #{cnt} для {get_nick(peer_id, target)}\nПричина: {reason}")
            if cnt >= 3:
                if p not in mutes: mutes[p] = {}
                mutes[p][u] = time.time() + 60 * 60
                save_data('mutes.json', mutes)
                send(peer_id, f"🔇 3 варна = мут 60 мин")
    
    elif text.startswith("/unwarn") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in warns and u in warns[p]:
                warns[p][u]['count'] = 0
                save_data('warns.json', warns)
                send(peer_id, f"✅ Варны сброшены для {get_nick(peer_id, target)}")
    
    elif text.startswith("/clear") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            count = int(parts[1])
            if clear_chat(peer_id, count):
                send(peer_id, f"🧹 Очищено {count} сообщений")
    
    elif text == "/staff" and has_permission(peer_id, user_id, 'helper'):
        staff = "👮 АДМИНИСТРАЦИЯ\n━━━━━━━━━━\n👑 Создатель: @id749488560\n"
        if str(peer_id) in roles:
            for uid, r in roles[str(peer_id)].items():
                staff += f"⭐ {r}: {get_nick(peer_id, int(uid))}\n"
        send(peer_id, staff[:4000])
    
    elif text.startswith("/setnick") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 2:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            nickname = " ".join(parts[2:])
            p = str(peer_id)
            if p not in nicks: nicks[p] = {}
            nicks[p][str(target)] = nickname
            save_data('nicks.json', nicks)
            send(peer_id, f"✅ Ник '{nickname}' для {get_nick(peer_id, target)}")
    
    elif text == "/nlist" and has_permission(peer_id, user_id, 'helper'):
        if str(peer_id) in nicks:
            lst = "\n".join([f"• {nick}" for nick in list(nicks[str(peer_id)].values())[:15]])
            send(peer_id, f"📝 СПИСОК НИКОВ:\n{lst}")
    
    elif text == "/warnlist" and has_permission(peer_id, user_id, 'helper'):
        if str(peer_id) in warns:
            lst = [f"• {get_nick(peer_id, int(uid))}: {w['count']}" for uid, w in warns[str(peer_id)].items()][:15]
            send(peer_id, f"⚠ СПИСОК ВАРНОВ:\n" + "\n".join(lst))
    
    elif text == "/mutelist" and has_permission(peer_id, user_id, 'helper'):
        if str(peer_id) in mutes:
            now = time.time()
            lst = []
            for uid, t in mutes[str(peer_id)].items():
                if t > now:
                    lst.append(f"• {get_nick(peer_id, int(uid))}: {int((t-now)/60)} мин")
            send(peer_id, f"🔇 АКТИВНЫЕ МУТЫ:\n" + "\n".join(lst[:15]))
    
    # ==================== МОДЕРАТОРЫ ====================
    elif text.startswith("/ban") and has_permission(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
            p = str(peer_id)
            if p not in bans: bans[p] = {}
            bans[p][str(target)] = {'reason': reason, 'time': time.time()}
            save_data('bans.json', bans)
            kick_chat(peer_id, target)
            send(peer_id, f"🔨 БАН для {get_nick(peer_id, target)}\nПричина: {reason}")
    
    elif text.startswith("/unban") and has_permission(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p in bans and str(target) in bans[p]:
                del bans[p][str(target)]
                save_data('bans.json', bans)
                send(peer_id, f"✅ Бан снят с {get_nick(peer_id, target)}")
    
    elif text.startswith("/addmoder") and has_permission(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'moderator'
            save_data('roles.json', roles)
            send(peer_id, f"✅ {get_nick(peer_id, target)} теперь МОДЕРАТОР!")
    
    elif text.startswith("/removerole") and has_permission(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p in roles and str(target) in roles[p]:
                del roles[p][str(target)]
                save_data('roles.json', roles)
                send(peer_id, f"✅ Роль снята с {get_nick(peer_id, target)}")
    
    elif text == "/zov" and has_permission(peer_id, user_id, 'moderator'):
        mention_all(peer_id)
    
    elif text == "/banlist" and has_permission(peer_id, user_id, 'moderator'):
        if str(peer_id) in bans:
            lst = [f"• {get_nick(peer_id, int(uid))}: {data.get('reason', 'Без причины')}" 
                   for uid, data in bans[str(peer_id)].items()][:15]
            send(peer_id, f"🔨 ЗАБАНЕННЫЕ:\n" + "\n".join(lst))
    
    elif text.startswith("/inactivelist") and has_permission(peer_id, user_id, 'moderator'):
        send(peer_id, "ℹ Функция в разработке")
    
    # ==================== СТАРШИЕ МОДЕРАТОРЫ ====================
    elif text == "/quiet" and has_permission(peer_id, user_id, 'senior_moderator'):
        quiet_modes[str(peer_id)] = not quiet_modes.get(str(peer_id), False)
        save_data('quiet_modes.json', quiet_modes)
        status = "ВКЛЮЧЕН" if quiet_modes[str(peer_id)] else "ВЫКЛЮЧЕН"
        send(peer_id, f"🔇 Режим тишины {status}")
    
    elif text.startswith("/addsenmoder") and has_permission(peer_id, user_id, 'senior_moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'senior_moderator'
            save_data('roles.json', roles)
            send(peer_id, f"✅ {get_nick(peer_id, target)} теперь СТАРШИЙ МОДЕРАТОР!")
    
    elif text.startswith("/bug") and has_permission(peer_id, user_id, 'senior_moderator'):
        bug_text = text[5:]
        for rec in bug_receivers:
            send(rec, f"🐛 БАГ от {get_nick(peer_id, user_id)}:\n{bug_text}")
        send(peer_id, "✅ Баг отправлен разработчику")
    
    elif text == "/rnickall" and has_permission(peer_id, user_id, 'senior_moderator'):
        if str(peer_id) in nicks:
            del nicks[str(peer_id)]
            save_data('nicks.json', nicks)
            send(peer_id, "✅ Все ники сброшены")
    
    # ==================== АДМИНИСТРАТОРЫ ====================
    elif text.startswith("/addadmin") and has_permission(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'admin'
            save_data('roles.json', roles)
            send(peer_id, f"✅ {get_nick(peer_id, target)} теперь АДМИНИСТРАТОР!")
    
    elif text == "/settings" and has_permission(peer_id, user_id, 'admin'):
        send(peer_id, "⚙ НАСТРОЙКИ БЕСЕДЫ:\n/quiet - тишина\n/filter - фильтр мата\n/antiflood - антифлуд\n/welcometext - приветствие")
    
    elif text == "/filter" and has_permission(peer_id, user_id, 'admin'):
        send(peer_id, "✅ Фильтр мата АКТИВЕН")
    
    elif text == "/serverinfo" and has_permission(peer_id, user_id, 'admin'):
        try:
            conv = vk.messages.getConversationsById(peer_ids=peer_id)
            title = conv['items'][0].get('chat_settings', {}).get('title', 'Без названия')
            send(peer_id, f"ℹ БЕСЕДА: {title}\nID: {peer_id}\nТип: Чат")
        except:
            send(peer_id, "ℹ Информация о беседе")
    
    elif text == "/rkick" and has_permission(peer_id, user_id, 'admin'):
        send(peer_id, "⚠ Функция масс-кика в разработке")
    
    # ==================== СТАРШИЕ АДМИНИСТРАТОРЫ ====================
    elif text.startswith("/type") and has_permission(peer_id, user_id, 'senior_admin'):
        parts = text.split()
        if len(parts) > 1:
            chat_types[str(peer_id)] = int(parts[1])
            save_data('chat_types.json', chat_types)
            send(peer_id, f"✅ Тип беседы: {parts[1]}")
    
    elif text == "/leave" and has_permission(peer_id, user_id, 'senior_admin'):
        send(peer_id, "👋 Бот покидает беседу...")
        time.sleep(1)
        leave_chat(peer_id)
    
    elif text.startswith("/editowner") and has_permission(peer_id, user_id, 'senior_admin'):
        parts = text.split()
        if len(parts) > 1 and user_id == CREATOR_ID:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'creator'
            save_data('roles.json', roles)
            send(peer_id, f"👑 Права владельца переданы {get_nick(peer_id, target)}")
    
    elif text.startswith("/pin") and has_permission(peer_id, user_id, 'senior_admin'):
        if pin_message(peer_id, msg_id):
            pin_text = text[5:] if len(text) > 5 else "Сообщение"
            send(peer_id, f"📌 Закреплено: {pin_text}")
    
    elif text == "/unpin" and has_permission(peer_id, user_id, 'senior_admin'):
        if unpin_message(peer_id):
            send(peer_id, "📌 Закрепление снято")
    
    elif text == "/rroleall" and has_permission(peer_id, user_id, 'senior_admin'):
        if str(peer_id) in roles:
            del roles[str(peer_id)]
            save_data('roles.json', roles)
            send(peer_id, "✅ Все роли сброшены")
    
    elif text.startswith("/addsenadm") and has_permission(peer_id, user_id, 'senior_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'senior_admin'
            save_data('roles.json', roles)
            send(peer_id, f"✅ {get_nick(peer_id, target)} теперь СТАРШИЙ АДМИНИСТРАТОР!")
    
    elif text == "/masskick" and has_permission(peer_id, user_id, 'senior_admin'):
        send(peer_id, "⚠ Функция масс-кика в разработке")
    
    elif text == "/invite" and has_permission(peer_id, user_id, 'senior_admin'):
        send(peer_id, "✅ Приглашения разрешены модераторам")
    
    elif text == "/antiflood" and has_permission(peer_id, user_id, 'senior_admin'):
        anti_flood[str(peer_id)] = not anti_flood.get(str(peer_id), False)
        save_data('anti_flood.json', anti_flood)
        status = "ВКЛЮЧЕН" if anti_flood[str(peer_id)] else "ВЫКЛЮЧЕН"
        send(peer_id, f"🌊 Антифлуд {status}")
    
    elif text.startswith("/welcometext") and has_permission(peer_id, user_id, 'senior_admin'):
        welcome_texts[str(peer_id)] = text[13:]
        save_data('welcome_texts.json', welcome_texts)
        send(peer_id, f"✅ Приветствие установлено")
    
    # ==================== СПЕЦ АДМИНИСТРАТОРЫ ====================
    elif text.startswith("/gban") and has_permission(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target not in global_bans:
                global_bans.append(target)
                save_data('global_bans.json', global_bans)
                send(peer_id, f"🌍 ГЛОБАЛЬНЫЙ БАН для ID{target}")
    
    elif text.startswith("/gunban") and has_permission(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target in global_bans:
                global_bans.remove(target)
                save_data('global_bans.json', global_bans)
                send(peer_id, f"🌍 Глобальный бан снят с ID{target}")
    
    elif text == "/gbanlist" and has_permission(peer_id, user_id, 'special_admin'):
        lst = "\n".join([f"• ID{uid}" for uid in global_bans[:20]])
        send(peer_id, f"🌍 ГЛОБАЛ БАНЫ:\n{lst}")
    
    elif text == "/banwords" and has_permission(peer_id, user_id, 'special_admin'):
        words = ", ".join(filter_words[:20])
        send(peer_id, f"🚫 ЗАПРЕЩЕННЫЕ СЛОВА:\n{words}")
    
    elif text.startswith("/addowner") and has_permission(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'creator'
            save_data('roles.json', roles)
            send(peer_id, f"👑 {get_nick(peer_id, target)} теперь ВЛАДЕЛЕЦ БЕСЕДЫ!")
    
    elif text.startswith("/skick") and has_permission(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for bind in chat_binds.values():
                kick_chat(bind, target)
            send(peer_id, f"⚡ СУПЕР КИК для ID{target}")
    
    elif text.startswith("/sban") and has_permission(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target not in global_bans:
                global_bans.append(target)
                save_data('global_bans.json', global_bans)
                for bind in chat_binds.values():
                    kick_chat(bind, target)
                send(peer_id, f"⚡ СУПЕР БАН для ID{target}")
    
    elif text.startswith("/sunban") and has_permission(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target in global_bans:
                global_bans.remove(target)
                save_data('global_bans.json', global_bans)
                send(peer_id, f"✅ СУПЕР РАЗБАН для ID{target}")
    
    # ==================== ЗАМ.СПЕЦ АДМИНА ====================
    elif text.startswith("/addword") and has_permission(peer_id, user_id, 'deputy_special'):
        word = text[8:].strip().lower()
        if word and word not in filter_words:
            filter_words.append(word)
            save_data('filter_words.json', filter_words)
            send(peer_id, f"✅ Добавлено слово: {word}")
    
    elif text.startswith("/delword") and has_permission(peer_id, user_id, 'deputy_special'):
        word = text[9:].strip().lower()
        if word in filter_words:
            filter_words.remove(word)
            save_data('filter_words.json', filter_words)
            send(peer_id, f"✅ Удалено слово: {word}")
    
    elif text.startswith("/pull") and has_permission(peer_id, user_id, 'deputy_special'):
        name = text[6:].strip()
        if name:
            chat_binds[name] = peer_id
            save_data('chat_binds.json', chat_binds)
            send(peer_id, f"✅ Привязка '{name}' создана для чата {peer_id}")
    
    elif text == "/pullinfo" and has_permission(peer_id, user_id, 'deputy_special'):
        if chat_binds:
            info = "\n".join([f"• {k}: чат {v}" for k, v in chat_binds.items()])
            send(peer_id, f"📋 ПРИВЯЗКИ ЧАТОВ:\n{info}")
        else:
            send(peer_id, "📋 Нет активных привязок")
    
    elif text.startswith("/delpull") and has_permission(peer_id, user_id, 'deputy_special'):
        name = text[9:].strip()
        if name in chat_binds:
            del chat_binds[name]
            save_data('chat_binds.json', chat_binds)
            send(peer_id, f"✅ Привязка '{name}' удалена")
    
    elif text.startswith("/srnick") and has_permission(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(nicks.keys()):
                if str(target) in nicks[p]:
                    del nicks[p][str(target)]
            save_data('nicks.json', nicks)
            send(peer_id, f"✅ Ник сброшен везде для ID{target}")
    
    elif text.startswith("/ssetnick") and has_permission(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 2:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            nickname = " ".join(parts[2:])
            for p in list(nicks.keys()):
                if p not in nicks: nicks[p] = {}
                nicks[p][str(target)] = nickname
            save_data('nicks.json', nicks)
            send(peer_id, f"✅ Ник '{nickname}' установлен везде для ID{target}")
    
    elif text.startswith("/srrole") and has_permission(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(roles.keys()):
                if str(target) in roles[p]:
                    del roles[p][str(target)]
            save_data('roles.json', roles)
            send(peer_id, f"✅ Роли сброшены везде для ID{target}")
    
    elif text.startswith("/srole") and has_permission(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 2:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            role = parts[2]
            for p in list(roles.keys()):
                if p not in roles: roles[p] = {}
                roles[p][str(target)] = role
            save_data('roles.json', roles)
            send(peer_id, f"✅ Роль '{role}' выдана везде для ID{target}")
    
    elif text.startswith("/szov") and has_permission(peer_id, user_id, 'deputy_special'):
        msg = text[6:] if len(text) > 6 else "ВНИМАНИЕ!"
        for p in chat_binds.values():
            send(p, f"🔔 СУПЕР ОПОВЕЩЕНИЕ:\n{msg}")
        send(peer_id, "✅ Супер-оповещение отправлено во все чаты")
    
    # ==================== ВЛАДЕЛЕЦ БЕСЕДЫ ====================
    elif text.startswith("/gremoverole") and has_permission(peer_id, user_id, 'creator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(roles.keys()):
                if str(target) in roles[p]:
                    del roles[p][str(target)]
            save_data('roles.json', roles)
            send(peer_id, f"✅ Все роли сброшены для ID{target}")
    
    elif text.startswith("/news") and has_permission(peer_id, user_id, 'creator'):
        news_text = text[6:]
        for p in chat_binds.values():
            send(p, f"📢 НОВОСТИ ОТ АДМИНИСТРАЦИИ:\n{news_text}")
        send(peer_id, "✅ Новости отправлены во все чаты")
    
    elif text.startswith("/addzam") and has_permission(peer_id, user_id, 'creator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'deputy_creator'
            save_data('roles.json', roles)
            send(peer_id, f"✅ {get_nick(peer_id, target)} теперь ЗАМ.СОЗДАТЕЛЯ!")
    
    # ==================== ЗАМ.СОЗДАТЕЛЯ ====================
    elif text.startswith("/banid") and has_permission(peer_id, user_id, 'deputy_creator'):
        parts = text.split()
        if len(parts) > 1:
            target_peer = int(parts[1])
            bans[str(target_peer)] = {}
            save_data('bans.json', bans)
            send(peer_id, f"✅ Беседа {target_peer} ЗАБЛОКИРОВАНА")
    
    elif text.startswith("/unbanid") and has_permission(peer_id, user_id, 'deputy_creator'):
        parts = text.split()
        if len(parts) > 1:
            target_peer = int(parts[1])
            if str(target_peer) in bans:
                del bans[str(target_peer)]
                save_data('bans.json', bans)
                send(peer_id, f"✅ Беседа {target_peer} РАЗБЛОКИРОВАНА")
    
    elif text.startswith("/clearchat") and has_permission(peer_id, user_id, 'deputy_creator'):
        parts = text.split()
        if len(parts) > 1:
            target_peer = int(parts[1])
            for db in [bans, mutes, warns, nicks, roles, quiet_modes, anti_flood, welcome_texts]:
                if str(target_peer) in db:
                    del db[str(target_peer)]
            save_data('bans.json', bans)
            save_data('mutes.json', mutes)
            save_data('warns.json', warns)
            save_data('nicks.json', nicks)
            save_data('roles.json', roles)
            send(peer_id, f"✅ Чат {target_peer} очищен из БД")
    
    elif text.startswith("/infoid") and has_permission(peer_id, user_id, 'deputy_creator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            info = f"📊 ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ ID{target}\n"
            info += f"🌍 Глобальный бан: {'ДА' if target in global_bans else 'НЕТ'}\n"
            info += f"📁 Чатов с ролью: {sum(1 for p in roles if str(target) in roles[p])}"
            send(peer_id, info)
    
    elif text == "/listchats" and has_permission(peer_id, user_id, 'deputy_creator'):
        chats = list(chat_binds.values())
        send(peer_id, f"📋 ВСЕГО ЧАТОВ: {len(chats)}\nID: {', '.join(map(str, chats[:10]))}")
    
    elif text == "/server" and has_permission(peer_id, user_id, 'deputy_creator'):
        send(peer_id, f"🖥 СЕРВЕР: OK\n📊 БД: {len(bans)} банов, {len(mutes)} мутов\n⏱ Статус: АКТИВЕН")
    
    # ==================== СОЗДАТЕЛЬ БОТА ====================
    elif text.startswith("/adddev") and user_id == CREATOR_ID:
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            send(peer_id, f"✅ Права создателя выданы ID{target}")
    
    elif text.startswith("/addbug") and user_id == CREATOR_ID:
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target not in bug_receivers:
                bug_receivers.append(target)
                save_data('bug_receivers.json', bug_receivers)
                send(peer_id, f"✅ ID{target} добавлен в получатели багов")
    
    elif text.startswith("/delbug") and user_id == CREATOR_ID:
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target in bug_receivers:
                bug_receivers.remove(target)
                save_data('bug_receivers.json', bug_receivers)
                send(peer_id, f"✅ ID{target} удален из получателей багов")
    
    elif text == "/sync" and user_id == CREATOR_ID:
        # Перезагрузка всех данных без global
        new_bans = load_data('bans.json')
        new_mutes = load_data('mutes.json')
        new_warns = load_data('warns.json')
        new_nicks = load_data('nicks.json')
        new_roles = load_data('roles.json')
        new_global_bans = load_data('global_bans.json') if os.path.exists('global_bans.json') else []
        new_filter_words = load_data('filter_words.json') if os.path.exists('filter_words.json') else filter_words
        
        # Обновляем глобальные переменные через словарь
        globals().update({
            'bans': new_bans,
            'mutes': new_mutes,
            'warns': new_warns,
            'nicks': new_nicks,
            'roles': new_roles,
            'global_bans': new_global_bans,
            'filter_words': new_filter_words
        })
        send(peer_id, "✅ База данных синхронизирована")

# Основной цикл
def main():
    print("=" * 50)
    print("🤖 BLACK FIB BOT - ПОЛНАЯ ВЕРСИЯ")
    print("=" * 50)
    print(f"👑 Создатель: @id{CREATOR_ID}")
    print(f"🆔 Группа: {GROUP_ID}")
    print("=" * 50)
    print("✅ ВСЕ КОМАНДЫ ЗАГРУЖЕНЫ")
    print("✅ Система ролей (10 уровней)")
    print("✅ Глобальные баны")
    print("✅ Привязки чатов")
    print("=" * 50)
    print("💬 Ожидание сообщений...\n")
    
    for event in longpoll.listen():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.obj.message
                peer_id = msg['peer_id']
                user_id = msg['from_id']
                text = msg.get('text', '').strip()
                msg_id = msg.get('id')
                
                if user_id > 0 and text.startswith('/'):
                    handle(peer_id, user_id, text, msg_id)
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
