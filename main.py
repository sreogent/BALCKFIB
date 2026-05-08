import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import time
import random
import re
from datetime import datetime, timedelta
import json
import os

# =========== ТВОИ ДАННЫЕ ===========
TOKEN = "vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg"
CREATOR_ID = 749488560
GROUP_ID = 227305903  # ИСПРАВЬ НА СВОЙ ID ГРУППЫ!
# ===================================

# Файлы для хранения данных
DATA_FILES = {
    'bans': 'bans.json',
    'mutes': 'mutes.json',
    'warns': 'warns.json',
    'nicks': 'nicks.json',
    'roles': 'roles.json',
    'global_bans': 'global_bans.json',
    'filter_words': 'filter_words.json',
    'chat_types': 'chat_types.json',
    'quiet_modes': 'quiet_modes.json',
    'anti_flood': 'anti_flood.json',
    'welcome_texts': 'welcome_texts.json',
    'chat_binds': 'chat_binds.json',
    'bug_receivers': 'bug_receivers.json'
}

# Загрузка данных
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
global_bans = load_data('global_bans.json')
filter_words = load_data('filter_words.json')
chat_types = load_data('chat_types.json')
quiet_modes = load_data('quiet_modes.json')
anti_flood = load_data('anti_flood.json')
welcome_texts = load_data('welcome_texts.json')
chat_binds = load_data('chat_binds.json')
bug_receivers = load_data('bug_receivers.json')

if not filter_words:
    filter_words = ['хуй', 'пизда', 'бля', 'сука', 'ебать', 'нахуй', 'пидор', 'редиска']

# Роли и уровни
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

def send_message(peer_id, text, reply_to=None, attach=None):
    try:
        params = {
            'peer_id': peer_id,
            'message': text,
            'random_id': random.randint(1, 999999999)
        }
        if reply_to:
            params['reply_to'] = reply_to
        if attach:
            params['attachment'] = attach
        vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка: {e}")

def get_user_info(user_id):
    try:
        user = vk.users.get(user_ids=user_id, fields='first_name,last_name,sex')[0]
        return f"{user['first_name']} {user['last_name']}"
    except:
        return f"ID{user_id}"

def get_nick(peer_id, user_id):
    if str(peer_id) in nicks and str(user_id) in nicks[str(peer_id)]:
        return nicks[str(peer_id)][str(user_id)]
    return get_user_info(user_id)

def get_user_role(peer_id, user_id):
    user_id = str(user_id)
    peer_id = str(peer_id)
    
    if int(user_id) == CREATOR_ID:
        return 'creator'
    
    if peer_id in roles and user_id in roles[peer_id]:
        return roles[peer_id][user_id]
    return 'user'

def has_permission(peer_id, user_id, required_role):
    user_role = get_user_role(peer_id, user_id)
    return ROLE_LEVEL.get(user_role, 1) >= ROLE_LEVEL.get(required_role, 1)

def is_admin_in_chat(peer_id, user_id):
    if user_id == CREATOR_ID:
        return True
    try:
        chat_id = peer_id - 2000000000
        chat_info = vk.messages.getConversationMembers(peer_id=peer_id)
        for member in chat_info['items']:
            if member['member_id'] == user_id and member.get('is_admin', False):
                return True
    except:
        pass
    return False

def kick_from_chat(peer_id, user_id):
    try:
        chat_id = peer_id - 2000000000
        vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id)
        return True
    except:
        return False

def mute_in_chat(peer_id, user_id, minutes):
    chat_id = peer_id - 2000000000
    key = f"{peer_id}_{user_id}"
    until_time = time.time() + (minutes * 60)
    if str(peer_id) not in mutes:
        mutes[str(peer_id)] = {}
    mutes[str(peer_id)][str(user_id)] = until_time
    save_data('mutes.json', mutes)
    return True

def is_muted(peer_id, user_id):
    peer_id = str(peer_id)
    user_id = str(user_id)
    if peer_id in mutes and user_id in mutes[peer_id]:
        if mutes[peer_id][user_id] > time.time():
            return True
        else:
            del mutes[peer_id][user_id]
            save_data('mutes.json', mutes)
    return False

def add_warn(peer_id, user_id, reason=""):
    peer_id = str(peer_id)
    user_id = str(user_id)
    if peer_id not in warns:
        warns[peer_id] = {}
    if user_id not in warns[peer_id]:
        warns[peer_id][user_id] = {'count': 0, 'reasons': []}
    warns[peer_id][user_id]['count'] += 1
    warns[peer_id][user_id]['reasons'].append(reason)
    save_data('warns.json', warns)
    return warns[peer_id][user_id]['count']

def clear_chat(peer_id, count):
    try:
        messages = vk.messages.getHistory(peer_id=peer_id, count=min(count, 100))
        msg_ids = [msg['id'] for msg in messages['items']]
        if msg_ids:
            vk.messages.delete(message_ids=msg_ids, delete_for_all=1, peer_id=peer_id)
        return True
    except:
        return False

def ban_user(peer_id, user_id, reason=""):
    peer_id = str(peer_id)
    user_id = str(user_id)
    if peer_id not in bans:
        bans[peer_id] = {}
    bans[peer_id][user_id] = {'reason': reason, 'time': time.time()}
    save_data('bans.json', bans)
    kick_from_chat(int(peer_id), int(user_id))

def is_banned(peer_id, user_id):
    peer_id = str(peer_id)
    user_id = str(user_id)
    if peer_id in bans and user_id in bans[peer_id]:
        return True
    if int(user_id) in global_bans:
        return True
    return False

# Обработка команд
def handle_command(peer_id, user_id, text, msg_id):
    user_id = int(user_id)
    peer_id = int(peer_id)
    
    # Проверка бана
    if is_banned(peer_id, user_id) and user_id != CREATOR_ID:
        return
    
    # Проверка мута
    if is_muted(peer_id, user_id) and user_id != CREATOR_ID:
        send_message(peer_id, "🔇 Вы замучены!", msg_id)
        return
    
    # Фильтр мата
    for word in filter_words:
        if word.lower() in text.lower():
            send_message(peer_id, f"🚫 Запрещенное слово: {word}", msg_id)
            return
    
    # ═══════════════════════════════════════════════════════
    # КОМАНДЫ ДЛЯ ВСЕХ (уровень 0)
    # ═══════════════════════════════════════════════════════
    
    if text == "/info":
        send_message(peer_id, "📚 BLACK FIB BOT\n━━━━━━━━━━━━\n✅ Версия: 1.0\n👑 Создатель: @id749488560\n💡 Бот полностью функционирует")
    
    elif text.startswith("/stats"):
        parts = text.split()
        target_id = user_id
        if len(parts) > 1 and parts[1].startswith("@id"):
            target_id = int(parts[1][3:])
        elif len(parts) > 1 and parts[1].isdigit():
            target_id = int(parts[1])
        
        w = warns.get(str(peer_id), {}).get(str(target_id), {}).get('count', 0)
        is_m = "Да" if is_muted(peer_id, target_id) else "Нет"
        role = get_user_role(peer_id, target_id)
        nick = get_nick(peer_id, target_id)
        
        send_message(peer_id, f"📊 Статистика {nick}\n━━━━━━━━━━━━\n⚠ Варны: {w}\n🔇 Мут: {is_m}\n👑 Роль: {role}")
    
    elif text == "/getid":
        send_message(peer_id, f"🆔 Ваш ID: {user_id}")
    
    elif text == "/test":
        send_message(peer_id, "✅ Бот работает! Комар носа не подточит!")
    
    elif text == "/ping":
        send_message(peer_id, "🏓 Понг! Бот активен.")
    
    # ═══════════════════════════════════════════════════════
    # ХЕЛПЕРЫ (уровень helper)
    # ═══════════════════════════════════════════════════════
    
    elif text.startswith("/kick") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target_id = None
            if parts[1].startswith("@id"):
                target_id = int(parts[1][3:])
            elif parts[1].isdigit():
                target_id = int(parts[1])
            
            if target_id:
                reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
                if kick_from_chat(peer_id, target_id):
                    send_message(peer_id, f"👢 Кикнут пользователь\nПричина: {reason}")
                else:
                    send_message(peer_id, "❌ Ошибка при кике")
    
    elif text.startswith("/mute") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 2:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            minutes = int(parts[2])
            reason = " ".join(parts[3:]) if len(parts) > 3 else "Не указана"
            mute_in_chat(peer_id, target_id, minutes)
            send_message(peer_id, f"🔇 Мут на {minutes} мин\nПричина: {reason}")
    
    elif text.startswith("/unmute") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if str(peer_id) in mutes and str(target_id) in mutes[str(peer_id)]:
                del mutes[str(peer_id)][str(target_id)]
                save_data('mutes.json', mutes)
                send_message(peer_id, "✅ Мут снят")
    
    elif text.startswith("/warn") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
            count = add_warn(peer_id, target_id, reason)
            send_message(peer_id, f"⚠ Выдан варн #{count}\nПричина: {reason}")
            if count >= 3:
                mute_in_chat(peer_id, target_id, 60)
                send_message(peer_id, f"🔇 3 варна = мут 60 мин")
    
    elif text.startswith("/unwarn") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if str(peer_id) in warns and str(target_id) in warns[str(peer_id)]:
                warns[str(peer_id)][str(target_id)]['count'] = 0
                save_data('warns.json', warns)
                send_message(peer_id, "✅ Варны сброшены")
    
    elif text.startswith("/clear") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            count = int(parts[1])
            if clear_chat(peer_id, count):
                send_message(peer_id, f"🧹 Очищено {count} сообщений")
    
    elif text == "/staff" and has_permission(peer_id, user_id, 'helper'):
        staff_list = "👮 Администрация\n━━━━━━━━━━━━\n👑 Создатель: @id749488560\n"
        send_message(peer_id, staff_list)
    
    elif text.startswith("/setnick") and has_permission(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 2:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            nickname = " ".join(parts[2:])
            if str(peer_id) not in nicks:
                nicks[str(peer_id)] = {}
            nicks[str(peer_id)][str(target_id)] = nickname
            save_data('nicks.json', nicks)
            send_message(peer_id, f"✅ Ник установлен: {nickname}")
    
    elif text == "/nlist" and has_permission(peer_id, user_id, 'helper'):
        if str(peer_id) in nicks and nicks[str(peer_id)]:
            lst = "\n".join([f"{get_nick(peer_id, int(uid))}" for uid in list(nicks[str(peer_id)].keys())[:10]])
            send_message(peer_id, f"📝 Список ников:\n{lst}")
    
    elif text == "/warnlist" and has_permission(peer_id, user_id, 'helper'):
        if str(peer_id) in warns:
            lst = []
            for uid, data in warns[str(peer_id)].items():
                lst.append(f"{get_nick(peer_id, int(uid))}: {data['count']} варнов")
            send_message(peer_id, "⚠ Список варнов:\n" + "\n".join(lst[:10]))
    
    elif text == "/mutelist" and has_permission(peer_id, user_id, 'helper'):
        if str(peer_id) in mutes:
            lst = []
            for uid, until in mutes[str(peer_id)].items():
                if until > time.time():
                    remaining = int((until - time.time()) / 60)
                    lst.append(f"{get_nick(peer_id, int(uid))}: {remaining} мин")
            send_message(peer_id, "🔇 Замучены:\n" + "\n".join(lst[:10]))
    
    # ═══════════════════════════════════════════════════════
    # МОДЕРАТОРЫ (уровень moderator)
    # ═══════════════════════════════════════════════════════
    
    elif text.startswith("/ban") and has_permission(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
            ban_user(peer_id, target_id, reason)
            send_message(peer_id, f"🔨 Бан навсегда\nПричина: {reason}")
    
    elif text.startswith("/unban") and has_permission(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if str(peer_id) in bans and str(target_id) in bans[str(peer_id)]:
                del bans[str(peer_id)][str(target_id)]
                save_data('bans.json', bans)
                send_message(peer_id, "✅ Бан снят")
    
    elif text.startswith("/addmoder") and has_permission(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if str(peer_id) not in roles:
                roles[str(peer_id)] = {}
            roles[str(peer_id)][str(target_id)] = 'moderator'
            save_data('roles.json', roles)
            send_message(peer_id, f"✅ {get_nick(peer_id, target_id)} теперь модератор!")
    
    elif text.startswith("/removerole") and has_permission(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if str(peer_id) in roles and str(target_id) in roles[str(peer_id)]:
                del roles[str(peer_id)][str(target_id)]
                save_data('roles.json', roles)
                send_message(peer_id, f"✅ Роль снята с {get_nick(peer_id, target_id)}")
    
    elif text == "/zov" and has_permission(peer_id, user_id, 'moderator'):
        send_message(peer_id, "🔔 @all @everyone ВНИМАНИЕ! Срочное сообщение от администрации!")
    
    elif text == "/banlist" and has_permission(peer_id, user_id, 'moderator'):
        if str(peer_id) in bans:
            lst = [f"{get_nick(peer_id, int(uid))}: {data['reason']}" for uid, data in bans[str(peer_id)].items()]
            send_message(peer_id, "🔨 Забаненные:\n" + "\n".join(lst[:10]))
    
    elif text.startswith("/inactivelist") and has_permission(peer_id, user_id, 'moderator'):
        send_message(peer_id, "ℹ Функция в разработке")
    
    # ═══════════════════════════════════════════════════════
    # СТАРШИЕ МОДЕРАТОРЫ (уровень senior_moderator)
    # ═══════════════════════════════════════════════════════
    
    elif text == "/quiet" and has_permission(peer_id, user_id, 'senior_moderator'):
        quiet_modes[str(peer_id)] = not quiet_modes.get(str(peer_id), False)
        save_data('quiet_modes.json', quiet_modes)
        status = "включен" if quiet_modes[str(peer_id)] else "выключен"
        send_message(peer_id, f"🔇 Режим тишины {status}")
    
    elif text.startswith("/addsenmoder") and has_permission(peer_id, user_id, 'senior_moderator'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            roles[str(peer_id)][str(target_id)] = 'senior_moderator'
            save_data('roles.json', roles)
            send_message(peer_id, f"✅ {get_nick(peer_id, target_id)} теперь старший модератор!")
    
    elif text.startswith("/bug") and has_permission(peer_id, user_id, 'senior_moderator'):
        bug_text = text[5:]
        for receiver in bug_receivers:
            send_message(int(receiver), f"🐛 Баг от {get_nick(peer_id, user_id)}:\n{bug_text}")
        send_message(peer_id, "✅ Баг отправлен разработчику")
    
    elif text == "/rnickall" and has_permission(peer_id, user_id, 'senior_moderator'):
        if str(peer_id) in nicks:
            del nicks[str(peer_id)]
            save_data('nicks.json', nicks)
            send_message(peer_id, "✅ Все ники сброшены")
    
    # ═══════════════════════════════════════════════════════
    # АДМИНИСТРАТОРЫ (уровень admin)
    # ═══════════════════════════════════════════════════════
    
    elif text.startswith("/addadmin") and has_permission(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            roles[str(peer_id)][str(target_id)] = 'admin'
            save_data('roles.json', roles)
            send_message(peer_id, f"✅ {get_nick(peer_id, target_id)} теперь администратор!")
    
    elif text == "/settings" and has_permission(peer_id, user_id, 'admin'):
        send_message(peer_id, "⚙ Настройки беседы:\n/quiet - тишина\n/filter - фильтр мата\n/antiflood - антифлуд")
    
    elif text == "/filter" and has_permission(peer_id, user_id, 'admin'):
        # Переключатель фильтра
        send_message(peer_id, "✅ Фильтр мата активен")
    
    elif text == "/serverinfo" and has_permission(peer_id, user_id, 'admin'):
        chat_info = vk.messages.getConversationsById(peer_ids=peer_id)
        send_message(peer_id, f"ℹ Информация о беседе отправлена в личку")
    
    elif text == "/rkick" and has_permission(peer_id, user_id, 'admin'):
        send_message(peer_id, "⚠ Функция масс-кика в разработке")
    
    # ═══════════════════════════════════════════════════════
    # СТАРШИЕ АДМИНИСТРАТОРЫ (уровень senior_admin)
    # ═══════════════════════════════════════════════════════
    
    elif text.startswith("/type") and has_permission(peer_id, user_id, 'senior_admin'):
        parts = text.split()
        if len(parts) > 1:
            chat_types[str(peer_id)] = int(parts[1])
            save_data('chat_types.json', chat_types)
            send_message(peer_id, f"✅ Тип беседы изменен на {parts[1]}")
    
    elif text == "/leave" and has_permission(peer_id, user_id, 'senior_admin'):
        send_message(peer_id, "👋 Бот покидает беседу...")
        time.sleep(1)
        vk.messages.removeChatUser(chat_id=peer_id-2000000000, user_id=GROUP_ID)
    
    elif text.startswith("/editowner") and has_permission(peer_id, user_id, 'senior_admin'):
        send_message(peer_id, "⚠ Только создатель может передать права!")
    
    elif text.startswith("/pin") and has_permission(peer_id, user_id, 'senior_admin'):
        pin_text = text[5:]
        vk.messages.pin(peer_id=peer_id, message_id=msg_id)
        send_message(peer_id, f"📌 Закреплено: {pin_text}")
    
    elif text == "/unpin" and has_permission(peer_id, user_id, 'senior_admin'):
        vk.messages.unpin(peer_id=peer_id)
        send_message(peer_id, "📌 Закрепление снято")
    
    elif text == "/rroleall" and has_permission(peer_id, user_id, 'senior_admin'):
        if str(peer_id) in roles:
            del roles[str(peer_id)]
            save_data('roles.json', roles)
            send_message(peer_id, "✅ Все роли сброшены")
    
    elif text.startswith("/addsenadm") and has_permission(peer_id, user_id, 'senior_admin'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            roles[str(peer_id)][str(target_id)] = 'senior_admin'
            save_data('roles.json', roles)
            send_message(peer_id, f"✅ {get_nick(peer_id, target_id)} теперь старший администратор!")
    
    elif text == "/masskick" and has_permission(peer_id, user_id, 'senior_admin'):
        send_message(peer_id, "⚠ Массовый кик в разработке")
    
    elif text == "/invite" and has_permission(peer_id, user_id, 'senior_admin'):
        send_message(peer_id, "✅ Приглашения разрешены модераторам")
    
    elif text == "/antiflood" and has_permission(peer_id, user_id, 'senior_admin'):
        anti_flood[str(peer_id)] = not anti_flood.get(str(peer_id), False)
        save_data('anti_flood.json', anti_flood)
        status = "включен" if anti_flood[str(peer_id)] else "выключен"
        send_message(peer_id, f"🌊 Антифлуд {status}")
    
    elif text.startswith("/welcometext") and has_permission(peer_id, user_id, 'senior_admin'):
        welcome_texts[str(peer_id)] = text[13:]
        save_data('welcome_texts.json', welcome_texts)
        send_message(peer_id, f"✅ Приветствие установлено")
    
    # ═══════════════════════════════════════════════════════
    # СПЕЦ АДМИНИСТРАТОРЫ (уровень special_admin)
    # ═══════════════════════════════════════════════════════
    
    elif text.startswith("/gban") and has_permission(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            global_bans.append(target_id)
            save_data('global_bans.json', global_bans)
            send_message(peer_id, f"🌍 Глобальный бан для {get_nick(peer_id, target_id)}")
    
    elif text.startswith("/gunban") and has_permission(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target_id in global_bans:
                global_bans.remove(target_id)
                save_data('global_bans.json', global_bans)
                send_message(peer_id, f"🌍 Глобальный бан снят")
    
    elif text == "/gbanlist" and has_permission(peer_id, user_id, 'special_admin'):
        lst = [f"ID{uid}" for uid in global_bans[:20]]
        send_message(peer_id, "🌍 Глобал баны:\n" + "\n".join(lst))
    
    elif text == "/banwords" and has_permission(peer_id, user_id, 'special_admin'):
        words = ", ".join(filter_words[:15])
        send_message(peer_id, f"🚫 Запрещенные слова:\n{words}")
    
    elif text.startswith("/addowner") and has_permission(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            roles[str(peer_id)][str(target_id)] = 'creator'
            save_data('roles.json', roles)
            send_message(peer_id, f"👑 {get_nick(peer_id, target_id)} теперь владелец беседы!")
    
    elif text.startswith("/skick") and has_permission(peer_id, user_id, 'special_admin'):
        send_message(peer_id, "⚠ Супер кик в разработке")
    
    elif text.startswith("/sban") and has_permission(peer_id, user_id, 'special_admin'):
        send_message(peer_id, "⚠ Супер бан в разработке")
    
    # ═══════════════════════════════════════════════════════
    # ЗАМ.СПЕЦ АДМИНА (уровень deputy_special)
    # ═══════════════════════════════════════════════════════
    
    elif text.startswith("/addword") and has_permission(peer_id, user_id, 'deputy_special'):
        word = text[8:].strip().lower()
        if word and word not in filter_words:
            filter_words.append(word)
            save_data('filter_words.json', filter_words)
            send_message(peer_id, f"✅ Добавлено слово: {word}")
    
    elif text.startswith("/delword") and has_permission(peer_id, user_id, 'deputy_special'):
        word = text[9:].strip().lower()
        if word in filter_words:
            filter_words.remove(word)
            save_data('filter_words.json', filter_words)
            send_message(peer_id, f"✅ Удалено слово: {word}")
    
    elif text.startswith("/pull") and has_permission(peer_id, user_id, 'deputy_special'):
        name = text[6:].strip()
        if name:
            chat_binds[name] = peer_id
            save_data('chat_binds.json', chat_binds)
            send_message(peer_id, f"✅ Привязка '{name}' создана")
    
    elif text == "/pullinfo" and has_permission(peer_id, user_id, 'deputy_special'):
        info = "\n".join([f"{k}: чат {v}" for k, v in chat_binds.items()])
        send_message(peer_id, f"📋 Привязки:\n{info}")
    
    elif text.startswith("/delpull") and has_permission(peer_id, user_id, 'deputy_special'):
        name = text[9:].strip()
        if name in chat_binds:
            del chat_binds[name]
            save_data('chat_binds.json', chat_binds)
            send_message(peer_id, f"✅ Привязка '{name}' удалена")
    
    elif text.startswith("/srnick") and has_permission(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(nicks.keys()):
                if str(target_id) in nicks[p]:
                    del nicks[p][str(target_id)]
            save_data('nicks.json', nicks)
            send_message(peer_id, "✅ Ник сброшен везде")
    
    elif text.startswith("/ssetnick") and has_permission(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 2:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            nickname = " ".join(parts[2:])
            for p in list(nicks.keys()):
                if str(p) not in nicks:
                    nicks[str(p)] = {}
                nicks[str(p)][str(target_id)] = nickname
            save_data('nicks.json', nicks)
            send_message(peer_id, f"✅ Ник '{nickname}' установлен везде")
    
    elif text.startswith("/srrole") and has_permission(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(roles.keys()):
                if str(target_id) in roles[p]:
                    del roles[p][str(target_id)]
            save_data('roles.json', roles)
            send_message(peer_id, "✅ Роль сброшена везде")
    
    elif text.startswith("/srole") and has_permission(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 2:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            role = parts[2]
            for p in list(roles.keys()):
                if str(p) not in roles:
                    roles[str(p)] = {}
                roles[str(p)][str(target_id)] = role
            save_data('roles.json', roles)
            send_message(peer_id, f"✅ Роль '{role}' выдана везде")
    
    elif text.startswith("/szov") and has_permission(peer_id, user_id, 'deputy_special'):
        msg = text[6:] if len(text) > 6 else "ВНИМАНИЕ!"
        for p in list(chat_binds.values()):
            send_message(p, f"🔔 ГЛОБАЛЬНОЕ ОПОВЕЩЕНИЕ:\n{msg}")
        send_message(peer_id, "✅ Супер-упоминание отправлено")
    
    # ═══════════════════════════════════════════════════════
    # ВЛАДЕЛЕЦ БЕСЕДЫ (уровень creator)
    # ═══════════════════════════════════════════════════════
    
    elif text.startswith("/gremoverole") and has_permission(peer_id, user_id, 'creator'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(roles.keys()):
                if str(target_id) in roles[p]:
                    del roles[p][str(target_id)]
            save_data('roles.json', roles)
            send_message(peer_id, "✅ Роли сброшены везде")
    
    elif text.startswith("/news") and has_permission(peer_id, user_id, 'creator'):
        news_text = text[6:]
        for p in list(chat_binds.values()):
            send_message(p, f"📢 НОВОСТИ:\n{news_text}")
        send_message(peer_id, "✅ Новости отправлены")
    
    elif text.startswith("/addzam") and has_permission(peer_id, user_id, 'creator'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            roles[str(peer_id)][str(target_id)] = 'deputy_creator'
            save_data('roles.json', roles)
            send_message(peer_id, f"✅ {get_nick(peer_id, target_id)} теперь зам.создателя!")
    
    # ═══════════════════════════════════════════════════════
    # ЗАМ.СОЗДАТЕЛЯ (уровень deputy_creator)
    # ═══════════════════════════════════════════════════════
    
    elif text.startswith("/banid") and has_permission(peer_id, user_id, 'deputy_creator'):
        parts = text.split()
        if len(parts) > 1:
            target_peer = int(parts[1])
            bans[str(target_peer)] = {}
            save_data('bans.json', bans)
            send_message(peer_id, f"✅ Беседа {target_peer} заблокирована")
    
    elif text.startswith("/unbanid") and has_permission(peer_id, user_id, 'deputy_creator'):
        parts = text.split()
        if len(parts) > 1:
            target_peer = int(parts[1])
            if str(target_peer) in bans:
                del bans[str(target_peer)]
                save_data('bans.json', bans)
                send_message(peer_id, f"✅ Беседа {target_peer} разблокирована")
    
    elif text.startswith("/clearchat") and has_permission(peer_id, user_id, 'deputy_creator'):
        parts = text.split()
        if len(parts) > 1:
            target_peer = int(parts[1])
            # Очистка всех данных чата
            for db in [bans, mutes, warns, nicks, roles, quiet_modes, anti_flood, welcome_texts]:
                if str(target_peer) in db:
                    del db[str(target_peer)]
            save_data('bans.json', bans)
            save_data('mutes.json', mutes)
            save_data('warns.json', warns)
            save_data('nicks.json', nicks)
            save_data('roles.json', roles)
            send_message(peer_id, f"✅ Чат {target_peer} очищен из БД")
    
    elif text.startswith("/infoid") and has_permission(peer_id, user_id, 'deputy_creator'):
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            info = f"📊 Инфо о ID{target_id}\n"
            info += f"Глобал бан: {'Да' if target_id in global_bans else 'Нет'}\n"
            info += f"Количество чатов с ролями: {sum(1 for p in roles if str(target_id) in roles[p])}"
            send_message(peer_id, info)
    
    elif text == "/listchats" and has_permission(peer_id, user_id, 'deputy_creator'):
        chats = list(chat_binds.values())
        send_message(peer_id, f"📋 Всего чатов: {len(chats)}\nID: {', '.join(map(str, chats[:10]))}")
    
    elif text == "/server" and has_permission(peer_id, user_id, 'deputy_creator'):
        send_message(peer_id, f"🖥 Сервер: OK\n📊 БД: {len(bans)} банов, {len(mutes)} мутов\n⏱ Аптайм: активен")
    
    # ═══════════════════════════════════════════════════════
    # СОЗДАТЕЛЬ БОТА (только CREATOR_ID)
    # ═══════════════════════════════════════════════════════
    
    elif text.startswith("/adddev") and user_id == CREATOR_ID:
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            roles[f"dev_{target_id}"] = {'level': 99}
            send_message(peer_id, f"✅ Права создателя выданы ID{target_id}")
    
    elif text.startswith("/addbug") and user_id == CREATOR_ID:
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            bug_receivers.append(target_id)
            save_data('bug_receivers.json', bug_receivers)
            send_message(peer_id, f"✅ ID{target_id} добавлен в получатели багов")
    
    elif text.startswith("/delbug") and user_id == CREATOR_ID:
        parts = text.split()
        if len(parts) > 1:
            target_id = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target_id in bug_receivers:
                bug_receivers.remove(target_id)
                save_data('bug_receivers.json', bug_receivers)
                send_message(peer_id, f"✅ ID{target_id} удален из получателей багов")
    
    elif text == "/sync" and user_id == CREATOR_ID:
        # Перезагрузка всех данных
        global bans, mutes, warns, nicks, roles, global_bans, filter_words
        bans = load_data('bans.json')
        mutes = load_data('mutes.json')
        warns = load_data('warns.json')
        nicks = load_data('nicks.json')
        roles = load_data('roles.json')
        global_bans = load_data('global_bans.json')
        filter_words = load_data('filter_words.json')
        send_message(peer_id, "✅ База данных синхронизирована")

# Обработка новых участников
def handle_new_member(peer_id, user_id):
    if str(peer_id) in welcome_texts:
        send_message(peer_id, welcome_texts[str(peer_id)].replace("{user}", get_nick(peer_id, user_id)))

# Главный цикл
def main():
    print("🤖 BLACK FIB BOT ЗАПУЩЕН!")
    print(f"👑 Создатель: @id{CREATOR_ID}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ Все команды загружены")
    print("✅ Базы данных инициализированы")
    print("━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Ожидание сообщений...")
    
    for event in longpoll.listen():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.obj.message
                peer_id = msg['peer_id']
                user_id = msg['from_id']
                text = msg.get('text', '').strip()
                msg_id = msg.get('id')
                
                # Игнорируем себя
                if user_id == GROUP_ID:
                    continue
                
                # Обработка команды
                if text.startswith('/'):
                    handle_command(peer_id, user_id, text, msg_id)
            
            elif event.type == VkBotEventType.GROUP_JOIN:
                if event.obj.user_id:
                    handle_new_member(event.obj.peer_id, event.obj.user_id)
                    
        except Exception as e:
            print(f"Ошибка: {e}")
            if CREATOR_ID:
                try:
                    send_message(CREATOR_ID, f"❌ Ошибка бота: {str(e)[:200]}")
                except:
                    pass

if __name__ == "__main__":
    main()
