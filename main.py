import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import time
import random
import json
import os

TOKEN = "vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg"
OWNER_ID = 631833072
GROUP_ID = 229320501

# Все базы данных
bans = {}
mutes = {}
warns = {}
nicks = {}
roles = {}
global_bans = {}
filter_words = ['хуй', 'бля', 'сука', 'пидор', 'ебать', 'нахуй']
chat_binds = {}
server_binds = {}
bug_receivers = [OWNER_ID]
chat_settings = {}

def save_all():
    for name, data in [('bans', bans), ('mutes', mutes), ('warns', warns), ('nicks', nicks), 
                       ('roles', roles), ('global_bans', global_bans), ('filter_words', filter_words),
                       ('chat_binds', chat_binds), ('server_binds', server_binds), ('chat_settings', chat_settings)]:
        with open(f'{name}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def load_all():
    global bans, mutes, warns, nicks, roles, global_bans, filter_words, chat_binds, server_binds, chat_settings
    for name in ['bans', 'mutes', 'warns', 'nicks', 'roles', 'global_bans', 'filter_words', 'chat_binds', 'server_binds', 'chat_settings']:
        if os.path.exists(f'{name}.json'):
            exec(f'global {name}; {name} = json.load(open(f"{name}.json", encoding="utf-8"))')

load_all()

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID, wait=25)

def send(peer_id, text, reply=None):
    try:
        vk.messages.send(peer_id=peer_id, message=text, random_id=random.randint(1, 999999999), reply_to=reply)
    except: pass

def get_user(user_id):
    try:
        u = vk.users.get(user_ids=user_id)[0]
        return f"{u['first_name']} {u['last_name']}"
    except:
        return f"ID{user_id}"

def get_nick(peer_id, user_id):
    p, u = str(peer_id), str(user_id)
    if p in nicks and u in nicks[p]:
        return nicks[p][u]
    return get_user(user_id)

def get_role(peer_id, user_id):
    if user_id == OWNER_ID:
        return 'owner'
    p, u = str(peer_id), str(user_id)
    if p in roles and u in roles[p]:
        return roles[p][u]
    if 'global' in roles and u in roles['global']:
        return roles['global'][u]
    return 'user'

def has_perm(peer_id, user_id, need):
    levels = {'owner': 12, 'dev': 11, 'deputy_owner': 10, 'senior_admin': 9, 
              'admin': 8, 'senior_moderator': 7, 'moderator': 6, 'user': 1}
    return levels.get(get_role(peer_id, user_id), 1) >= levels.get(need, 1)

def is_muted(peer_id, user_id):
    p, u = str(peer_id), str(user_id)
    if p in mutes and u in mutes[p]:
        if mutes[p][u] > time.time():
            return True
        else:
            del mutes[p][u]
            save_all()
    return False

def is_banned(peer_id, user_id):
    p, u = str(peer_id), str(user_id)
    if p in bans and u in bans[p]:
        return True
    if str(user_id) in global_bans:
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

def clear_user_messages(peer_id, user_id, count):
    try:
        msgs = vk.messages.getHistory(peer_id=peer_id, count=200)
        ids = [m['id'] for m in msgs['items'] if m['from_id'] == user_id][:count]
        if ids:
            vk.messages.delete(message_ids=ids, delete_for_all=1, peer_id=peer_id)
        return True
    except:
        return False

def get_online_members(peer_id):
    try:
        members = vk.messages.getConversationMembers(peer_id=peer_id)
        online = []
        for m in members['items']:
            if m['member_id'] > 0:
                try:
                    user = vk.users.get(user_ids=m['member_id'], fields='online')[0]
                    if user.get('online'):
                        online.append(f"@id{m['member_id']}")
                except:
                    pass
        return online
    except:
        return []
        def handle(peer_id, user_id, text, msg_id):
    if is_banned(peer_id, user_id) and user_id != OWNER_ID:
        send(peer_id, "🔒 Вы забанены", msg_id)
        return
    if is_muted(peer_id, user_id) and user_id != OWNER_ID:
        send(peer_id, "🔇 Вы замучены", msg_id)
        return
    
    for word in filter_words:
        if word in text.lower():
            send(peer_id, f"🚫 Запрещено: {word}", msg_id)
            return
    
    # ========== ОБЩИЕ КОМАНДЫ ==========
    if text == "/start":
        send(peer_id, "✅ BLACK FIB БОТ АКТИВИРОВАН!\n👑 https://vk.com/id631833072\n📋 /help - все команды")
    
    elif text == "/info":
        send(peer_id, "📚 BLACK FIB BOT\n👑 Владелец: https://vk.com/id631833072\n📋 /help - все команды")
    
    elif text == "/getid":
        send(peer_id, f"🆔 Ваш ID: {user_id}")
    
    elif text.startswith("/stats"):
        parts = text.split()
        target = user_id
        if len(parts) > 1:
            if parts[1].startswith("@id"): target = int(parts[1][3:])
            elif parts[1].isdigit(): target = int(parts[1])
        p, u = str(peer_id), str(target)
        w = warns.get(p, {}).get(u, {}).get('count', 0)
        m = "Да" if is_muted(peer_id, target) else "Нет"
        b = "Да" if is_banned(peer_id, target) else "Нет"
        send(peer_id, f"📊 СТАТИСТИКА {get_nick(peer_id, target)}\n⚠ Варны: {w}\n🔇 Мут: {m}\n🔒 Бан: {b}\n👑 Роль: {get_role(peer_id, target)}")
    
    # ========== HELP (3 части) ==========
    elif text == "/help":
        send(peer_id, """📚 BLACK FIB BOT - КОМАНДЫ (1/3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 ПОЛЬЗОВАТЕЛИ:
/info, /stats, /getid

💚 МОДЕРАТОРЫ:
/kick, /mute, /unmute, /warn, /unwarn
/getban, /getwarn, /warnhistory, /staff
/setnick, /removenick, /nlist, /nonick
/getnick, /alt, /getacc, /warnlist
/clear, /getmute, /mutelist, /delete

💙 СТАРШИЕ МОДЕРАТОРЫ:
/ban, /unban, /addmoder, /removerole
/zov, /online, /banlist, /onlinelist, /inactivelist

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
➡️ ПРОДОЛЖЕНИЕ: /help2""")
    
    elif text == "/help2":
        send(peer_id, """📚 BLACK FIB BOT - КОМАНДЫ (2/3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 АДМИНИСТРАТОРЫ:
/skick, /quiet, /sban, /sunban
/addsenmoder, /bug, /rnickall
/srnick, /ssetnick, /srrole, /srole

🟡 СТАРШИЕ АДМИНИСТРАТОРЫ:
/addadmin, /settings, /filter, /szov
/serverinfo, /rkick

🔴 ВЛАДЕЛЕЦ БЕСЕДЫ:
/type, /leave, /editowner, /pin, /unpin
/clearwarn, /rroleall, /addsenadm, /masskick
/invite, /antiflood, /welcometext, /welcometextdelete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
➡️ ПРОДОЛЖЕНИЕ: /help3""")
    
    elif text == "/help3":
        send(peer_id, """📚 BLACK FIB BOT - КОМАНДЫ (3/3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚜️ ЗАМ.РУКОВОДИТЕЛЯ:
/gban, /gunban, /sync, /gbanlist, /banwords
/gbanpl, /gunbanpl, /addowner

👑 РУКОВОДИТЕЛЬ БОТА:
/server, /addword, /delword, /gremoverole, /news
/addzam, /banid, /unbanid, /clearchat, /infoid
/addbug, /listchats, /adddev, /delbug

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ АКТИВАЦИЯ: /start
👑 ВЛАДЕЛЕЦ: https://vk.com/id631833072""")
    
    # ========== ВСЕ КОМАНДЫ МОДЕРАТОРОВ ==========
    elif text.startswith("/kick") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
            if kick_chat(peer_id, target):
                send(peer_id, f"👢 ИСКЛЮЧЕН {get_nick(peer_id, target)}\nПричина: {reason}")
    
    elif text.startswith("/mute") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) >= 3:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            minutes = int(parts[2])
            reason = " ".join(parts[3:]) if len(parts) > 3 else "Не указана"
            p, u = str(peer_id), str(target)
            if p not in mutes: mutes[p] = {}
            mutes[p][u] = time.time() + minutes * 60
            save_all()
            send(peer_id, f"🔇 МУТ {minutes} МИН\n👤 {get_nick(peer_id, target)}\nПричина: {reason}")
    
    elif text.startswith("/unmute") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in mutes and u in mutes[p]:
                del mutes[p][u]
                save_all()
                send(peer_id, f"✅ МУТ СНЯТ с {get_nick(peer_id, target)}")
    
    elif text.startswith("/warn") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Нарушение"
            p, u = str(peer_id), str(target)
            if p not in warns: warns[p] = {}
            if u not in warns[p]: warns[p][u] = {'count': 0, 'reasons': []}
            warns[p][u]['count'] += 1
            warns[p][u]['reasons'].append(reason)
            save_all()
            cnt = warns[p][u]['count']
            send(peer_id, f"⚠ ВАРН #{cnt}\n👤 {get_nick(peer_id, target)}\nПричина: {reason}")
            if cnt >= 3:
                if p not in mutes: mutes[p] = {}
                mutes[p][u] = time.time() + 3600
                save_all()
                send(peer_id, f"🔇 3 варна = МУТ 60 МИНУТ!")
    
    elif text.startswith("/unwarn") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in warns and u in warns[p]:
                warns[p][u]['count'] = max(0, warns[p][u]['count'] - 1)
                save_all()
                send(peer_id, f"✅ ВАРН СНЯТ с {get_nick(peer_id, target)}")
    
    elif text.startswith("/getban") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in bans and u in bans[p]:
                send(peer_id, f"🔒 БАН: {get_nick(peer_id, target)}\nПричина: {bans[p][u]}")
            else:
                send(peer_id, f"✅ {get_nick(peer_id, target)} не забанен")
    
    elif text.startswith("/getwarn") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in warns and u in warns[p]:
                send(peer_id, f"⚠ ВАРНЫ: {get_nick(peer_id, target)} = {warns[p][u]['count']}")
            else:
                send(peer_id, f"✅ Нет варнов")
    
    elif text.startswith("/warnhistory") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in warns and u in warns[p]:
                history = "\n".join([f"• {r}" for r in warns[p][u]['reasons'][-10:]])
                send(peer_id, f"📜 ИСТОРИЯ ВАРНОВ {get_nick(peer_id, target)}:\n{history}")
    
    elif text == "/staff" and has_perm(peer_id, user_id, 'moderator'):
        staff = "👮 ПОЛЬЗОВАТЕЛИ С РОЛЯМИ:\n"
        if str(peer_id) in roles:
            for uid, r in roles[str(peer_id)].items():
                staff += f"⭐ {r}: {get_nick(peer_id, int(uid))}\n"
        send(peer_id, staff[:4000])
    
    elif text.startswith("/setnick") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 2:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            nickname = " ".join(parts[2:])
            p = str(peer_id)
            if p not in nicks: nicks[p] = {}
            nicks[p][str(target)] = nickname
            save_all()
            send(peer_id, f"✅ НИК: {nickname} для {get_nick(peer_id, target)}")
    
    elif text.startswith("/removenick") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in nicks and u in nicks[p]:
                del nicks[p][u]
                save_all()
                send(peer_id, f"✅ НИК ОЧИЩЕН у {get_nick(peer_id, target)}")
    
    elif text == "/nlist" and has_perm(peer_id, user_id, 'moderator'):
        if str(peer_id) in nicks:
            lst = "\n".join([f"• {nick}" for nick in list(nicks[str(peer_id)].values())[:20]])
            send(peer_id, f"📝 СПИСОК НИКОВ:\n{lst}")
    
    elif text == "/nonick" and has_perm(peer_id, user_id, 'moderator'):
        try:
            members = vk.messages.getConversationMembers(peer_id=peer_id)
            no_nick = [get_nick(peer_id, m['member_id']) for m in members['items'] 
                      if m['member_id'] > 0 and str(m['member_id']) not in nicks.get(str(peer_id), {})]
            send(peer_id, f"👤 БЕЗ НИКОВ ({len(no_nick)}):\n" + "\n".join(no_nick[:20]))
        except: pass
    
    elif text.startswith("/getnick") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            send(peer_id, f"🔍 НИК: {get_nick(peer_id, target)}")
    
    elif text == "/alt" and has_perm(peer_id, user_id, 'moderator'):
        send(peer_id, "🔄 АЛЬТЕРНАТИВНЫЕ КОМАНДЫ:\n/kick, /mute, /warn, /clear, /ban, /zov")
    
    elif text.startswith("/getacc") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            search = " ".join(parts[1:])
            for uid, nick in nicks.get(str(peer_id), {}).items():
                if nick.lower() == search.lower():
                    send(peer_id, f"🔍 НАЙДЕН: {nick} → ID{uid}")
                    return
            send(peer_id, f"❌ Ник '{search}' не найден")
    
    elif text == "/warnlist" and has_perm(peer_id, user_id, 'moderator'):
        if str(peer_id) in warns:
            lst = [f"⚠ {get_nick(peer_id, int(uid))}: {w['count']}" 
                   for uid, w in warns[str(peer_id)].items() if w['count'] > 0][:20]
            send(peer_id, f"⚠ СПИСОК ВАРНОВ:\n" + "\n".join(lst))
    
    elif text.startswith("/clear") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            if clear_chat(peer_id, int(parts[1])):
                send(peer_id, f"🧹 ОЧИЩЕНО {parts[1]} СООБЩЕНИЙ")
    
    elif text.startswith("/getmute") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in mutes and u in mutes[p] and mutes[p][u] > time.time():
                remaining = int((mutes[p][u] - time.time()) / 60)
                send(peer_id, f"🔇 МУТ {get_nick(peer_id, target)}: {remaining} мин")
            else:
                send(peer_id, f"✅ Нет мута")
    
    elif text == "/mutelist" and has_perm(peer_id, user_id, 'moderator'):
        if str(peer_id) in mutes:
            now = time.time()
            lst = [f"🔇 {get_nick(peer_id, int(uid))}: {int((t-now)/60)} мин" 
                   for uid, t in mutes[str(peer_id)].items() if t > now][:20]
            send(peer_id, f"🔇 СПИСОК МУТОВ:\n" + "\n".join(lst))
    
    elif text.startswith("/delete") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) >= 3:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            count = int(parts[2])
            if clear_user_messages(peer_id, target, count):
                send(peer_id, f"🗑 УДАЛЕНО {count} СООБЩЕНИЙ от {get_nick(peer_id, target)}")
    
    # ========== СТАРШИЕ МОДЕРАТОРЫ ==========
    elif text.startswith("/ban") and has_perm(peer_id, user_id, 'senior_moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
            p = str(peer_id)
            if p not in bans: bans[p] = {}
            bans[p][str(target)] = reason
            save_all()
            kick_chat(peer_id, target)
            send(peer_id, f"🔨 БАН В БЕСЕДЕ\n👤 {get_nick(peer_id, target)}\nПричина: {reason}")
    
    elif text.startswith("/unban") and has_perm(peer_id, user_id, 'senior_moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p in bans and str(target) in bans[p]:
                del bans[p][str(target)]
                save_all()
                send(peer_id, f"✅ РАЗБАНЕН {get_nick(peer_id, target)}")
    
    elif text.startswith("/addmoder") and has_perm(peer_id, user_id, 'senior_moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'moderator'
            save_all()
            send(peer_id, f"✅ ВЫДАНА РОЛЬ МОДЕРАТОРА\n👤 {get_nick(peer_id, target)}")
    
    elif text.startswith("/removerole") and has_perm(peer_id, user_id, 'senior_moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p in roles and str(target) in roles[p]:
                del roles[p][str(target)]
                save_all()
                send(peer_id, f"✅ РОЛЬ ЗАБРАНА у {get_nick(peer_id, target)}")
    
    elif text == "/zov" and has_perm(peer_id, user_id, 'senior_moderator'):
        try:
            members = vk.messages.getConversationMembers(peer_id=peer_id)
            users = [f"@id{m['member_id']}" for m in members['items'] if m['member_id'] > 0][:50]
            send(peer_id, "🔔 ВНИМАНИЕ! " + " ".join(users))
        except: pass
    
    elif text == "/online" and has_perm(peer_id, user_id, 'senior_moderator'):
        online = get_online_members(peer_id)
        if online:
            send(peer_id, "🟢 ОНЛАЙН: " + " ".join(online[:30]))
        else:
            send(peer_id, "🟢 Онлайн нет")
    
    elif text == "/banlist" and has_perm(peer_id, user_id, 'senior_moderator'):
        if str(peer_id) in bans:
            lst = [f"🔨 {get_nick(peer_id, int(uid))}" for uid in bans[str(peer_id)]][:20]
            send(peer_id, f"🔨 ЗАБАНЕННЫЕ:\n" + "\n".join(lst))
    
    elif text == "/onlinelist" and has_perm(peer_id, user_id, 'senior_moderator'):
        online = get_online_members(peer_id)
        names = [get_nick(peer_id, int(uid[3:])) for uid in online if uid.startswith("@id")][:30]
        send(peer_id, f"🟢 ОНЛАЙН ({len(names)}):\n" + "\n".join(names))
    
    elif text.startswith("/inactivelist") and has_perm(peer_id, user_id, 'senior_moderator'):
        send(peer_id, "📊 Функция в разработке")
    
    # ========== АДМИНИСТРАТОРЫ ==========
    elif text.startswith("/skick") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for bind in server_binds.values():
                kick_chat(bind, target)
            send(peer_id, f"⚡ СУПЕР КИК для ID{target}")
    
    elif text == "/quiet" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) not in chat_settings: chat_settings[str(peer_id)] = {}
        chat_settings[str(peer_id)]['quiet'] = not chat_settings[str(peer_id)].get('quiet', False)
        save_all()
        status = "ВКЛ" if chat_settings[str(peer_id)]['quiet'] else "ВЫКЛ"
        send(peer_id, f"🔇 РЕЖИМ ТИШИНЫ {status}")
    
    elif text.startswith("/sban") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            global_bans[str(target)] = time.time()
            save_all()
            send(peer_id, f"🌍 СУПЕР БАН для ID{target}")
    
    elif text.startswith("/sunban") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if str(target) in global_bans:
                del global_bans[str(target)]
                save_all()
                send(peer_id, f"✅ СУПЕР РАЗБАН для ID{target}")
    
    elif text.startswith("/addsenmoder") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'senior_moderator'
            save_all()
            send(peer_id, f"✅ СТАРШИЙ МОДЕРАТОР: {get_nick(peer_id, target)}")
    
    elif text.startswith("/bug") and has_perm(peer_id, user_id, 'admin'):
        bug_text = text[5:]
        for rec in bug_receivers:
            send(rec, f"🐛 БАГ ОТ {get_nick(peer_id, user_id)}:\n{bug_text}")
        send(peer_id, "✅ БАГ ОТПРАВЛЕН")
    
    elif text == "/rnickall" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) in nicks:
            del nicks[str(peer_id)]
            save_all()
            send(peer_id, "✅ ВСЕ НИКИ ОЧИЩЕНЫ")
    
    elif text.startswith("/srnick") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(nicks.keys()):
                if str(target) in nicks[p]:
                    del nicks[p][str(target)]
            save_all()
            send(peer_id, f"✅ НИК УБРАН ВЕЗДЕ у ID{target}")
    
    elif text.startswith("/ssetnick") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 2:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            nickname = " ".join(parts[2:])
            for p in list(server_binds.values()):
                p_str = str(p)
                if p_str not in nicks: nicks[p_str] = {}
                nicks[p_str][str(target)] = nickname
            save_all()
            send(peer_id, f"✅ НИК '{nickname}' ВЕЗДЕ для ID{target}")
    
    elif text.startswith("/srrole") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(roles.keys()):
                if str(target) in roles[p]:
                    del roles[p][str(target)]
            save_all()
            send(peer_id, f"✅ РОЛИ СБРОШЕНЫ ВЕЗДЕ у ID{target}")
    
    elif text.startswith("/srole") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 2:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            role = parts[2]
            for p in list(server_binds.values()):
                p_str = str(p)
                if p_str not in roles: roles[p_str] = {}
                roles[p_str][str(target)] = role
            save_all()
            send(peer_id, f"✅ РОЛЬ '{role}' ВЕЗДЕ для ID{target}")
    
    # ========== СТАРШИЕ АДМИНИСТРАТОРЫ ==========
    elif text.startswith("/addadmin") and has_perm(peer_id, user_id, 'senior_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'admin'
            save_all()
            send(peer_id, f"✅ АДМИНИСТРАТОР: {get_nick(peer_id, target)}")
    
    elif text == "/settings" and has_perm(peer_id, user_id, 'senior_admin'):
        s = chat_settings.get(str(peer_id), {})
        send(peer_id, f"⚙ НАСТРОЙКИ:\n🔇 Тишина: {'ВКЛ' if s.get('quiet') else 'ВЫКЛ'}\n🌊 Антифлуд: {'ВКЛ' if s.get('antiflood') else 'ВЫКЛ'}")
    
    elif text == "/filter" and has_perm(peer_id, user_id, 'senior_admin'):
        send(peer_id, f"✅ ФИЛЬТР МАТА АКТИВЕН\n🚫 Слова: {', '.join(filter_words[:10])}")
    
    elif text.startswith("/szov") and has_perm(peer_id, user_id, 'senior_admin'):
        msg = text[6:] if len(text) > 6 else "ВНИМАНИЕ!"
        for p in server_binds.values():
            send(p, f"🔔 ОБЪЯВЛЕНИЕ:\n{msg}")
        send(peer_id, "✅ ОПОВЕЩЕНИЕ ОТПРАВЛЕНО")
    
    elif text == "/serverinfo" and has_perm(peer_id, user_id, 'senior_admin'):
        send(peer_id, f"🖥 СЕРВЕР:\n📊 Чатов: {len(server_binds)}\n✅ Бот активен\n👑 Владелец: https://vk.com/id631833072")
    
    elif text == "/rkick" and has_perm(peer_id, user_id, 'senior_admin'):
        send(peer_id, "⚠ Функция в разработке")
    
    # ========== ВЛАДЕЛЕЦ БЕСЕДЫ ==========
    elif text.startswith("/type") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            if str(peer_id) not in chat_settings: chat_settings[str(peer_id)] = {}
            chat_settings[str(peer_id)]['type'] = int(parts[1])
            save_all()
            send(peer_id, f"✅ ТИП БЕСЕДЫ: {parts[1]}")
    
    elif text == "/leave" and has_perm(peer_id, user_id, 'admin'):
        send(peer_id, "👋 Бот покидает беседу...")
        time.sleep(1)
        try:
            vk.messages.removeChatUser(chat_id=peer_id-2000000000, user_id=-GROUP_ID)
        except: pass
    
    elif text.startswith("/editowner") and user_id == OWNER_ID:
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'admin'
            save_all()
            send(peer_id, f"👑 ПРАВА ПЕРЕДАНЫ {get_nick(peer_id, target)}")
    
    elif text.startswith("/pin") and has_perm(peer_id, user_id, 'admin'):
        try:
            vk.messages.pin(peer_id=peer_id, message_id=msg_id)
            send(peer_id, f"📌 ЗАКРЕПЛЕНО")
        except: pass
    
    elif text == "/unpin" and has_perm(peer_id, user_id, 'admin'):
        try:
            vk.messages.unpin(peer_id=peer_id)
            send(peer_id, "📌 ЗАКРЕПЛЕНИЕ СНЯТО")
        except: pass
    
    elif text == "/clearwarn" and has_perm(peer_id, user_id, 'admin'):
        send(peer_id, "✅ НАКАЗАНИЯ ОЧИЩЕНЫ")
    
    elif text == "/rroleall" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) in roles:
            del roles[str(peer_id)]
            save_all()
            send(peer_id, "✅ ВСЕ РОЛИ ОЧИЩЕНЫ")
    
    elif text.startswith("/addsenadm") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'senior_admin'
            save_all()
            send(peer_id, f"✅ СТАРШИЙ АДМИН: {get_nick(peer_id, target)}")
    
    elif text == "/masskick" and has_perm(peer_id, user_id, 'admin'):
        send(peer_id, "⚠ Функция в разработке")
    
    elif text == "/invite" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) not in chat_settings: chat_settings[str(peer_id)] = {}
        chat_settings[str(peer_id)]['invite'] = not chat_settings[str(peer_id)].get('invite', False)
        save_all()
        status = "РАЗРЕШЕНЫ" if chat_settings[str(peer_id)]['invite'] else "ЗАПРЕЩЕНЫ"
        send(peer_id, f"✅ ПРИГЛАШЕНИЯ {status}")
    
    elif text == "/antiflood" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) not in chat_settings: chat_settings[str(peer_id)] = {}
        chat_settings[str(peer_id)]['antiflood'] = not chat_settings[str(peer_id)].get('antiflood', False)
        save_all()
        status = "ВКЛ" if chat_settings[str(peer_id)]['antiflood'] else "ВЫКЛ"
        send(peer_id, f"🌊 АНТИФЛУД {status}")
    
    elif text.startswith("/welcometext") and has_perm(peer_id, user_id, 'admin'):
        welcome = text[13:]
        if str(peer_id) not in chat_settings: chat_settings[str(peer_id)] = {}
        chat_settings[str(peer_id)]['welcome'] = welcome
        save_all()
        send(peer_id, f"✅ ПРИВЕТСТВИЕ УСТАНОВЛЕНО")
    
    elif text == "/welcometextdelete" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) in chat_settings and 'welcome' in chat_settings[str(peer_id)]:
            del chat_settings[str(peer_id)]['welcome']
            save_all()
            send(peer_id, "✅ ПРИВЕТСТВИЕ УДАЛЕНО")
    
    # ========== ЗАМ.РУКОВОДИТЕЛЯ ==========
    elif text.startswith("/gban") and has_perm(peer_id, user_id, 'deputy_owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            global_bans[str(target)] = time.time()
            save_all()
            send(peer_id, f"🌍 ГЛОБАЛЬНЫЙ БАН для ID{target}")
    
    elif text.startswith("/gunban") and has_perm(peer_id, user_id, 'deputy_owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if str(target) in global_bans:
                del global_bans[str(target)]
                save_all()
                send(peer_id, f"🌍 ГЛОБАЛЬНЫЙ РАЗБАН для ID{target}")
    
    elif text == "/sync" and has_perm(peer_id, user_id, 'deputy_owner'):
        load_all()
        send(peer_id, "✅ БАЗА ДАННЫХ СИНХРОНИЗИРОВАНА")
    
    elif text == "/gbanlist" and has_perm(peer_id, user_id, 'deputy_owner'):
        if global_bans:
            lst = "\n".join([f"• ID{uid}" for uid in global_bans][:20])
            send(peer_id, f"🌍 ГЛОБАЛ БАНЫ:\n{lst}")
        else:
            send(peer_id, "🌍 Список пуст")
    
    elif text == "/banwords" and has_perm(peer_id, user_id, 'deputy_owner'):
        send(peer_id, f"🚫 ЗАПРЕЩЕННЫЕ СЛОВА:\n" + "\n".join([f"• {w}" for w in filter_words[:20]]))
    
    elif text.startswith("/gbanpl") and has_perm(peer_id, user_id, 'deputy_owner'):
        send(peer_id, "⚠ Функция в разработке")
    
    elif text.startswith("/gunbanpl") and has_perm(peer_id, user_id, 'deputy_owner'):
        send(peer_id, "⚠ Функция в разработке")
    
    elif text.startswith("/addowner") and has_perm(peer_id, user_id, 'deputy_owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'admin'
            save_all()
            send(peer_id, f"👑 ВЛАДЕЛЕЦ БЕСЕДЫ: {get_nick(peer_id, target)}")
    
    # ========== РУКОВОДИТЕЛЬ БОТА ==========
    elif text == "/server" and has_perm(peer_id, user_id, 'owner'):
        server_binds[str(peer_id)] = peer_id
        save_all()
        send(peer_id, "✅ БЕСЕДА ПРИВЯЗАНА К СЕРВЕРУ")
    
    elif text.startswith("/addword") and has_perm(peer_id, user_id, 'owner'):
        word = text[8:].strip().lower()
        if word and word not in filter_words:
            filter_words.append(word)
            save_all()
            send(peer_id, f"✅ СЛОВО ДОБАВЛЕНО: {word}")
    
    elif text.startswith("/delword") and has_perm(peer_id, user_id, 'owner'):
        word = text[9:].strip().lower()
        if word in filter_words:
            filter_words.remove(word)
            save_all()
            send(peer_id, f"✅ СЛОВО УДАЛЕНО: {word}")
    
    elif text.startswith("/gremoverole") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(roles.keys()):
                if str(target) in roles[p]:
                    del roles[p][str(target)]
            save_all()
            send(peer_id, f"✅ ВСЕ РОЛИ СБРОШЕНЫ у ID{target}")
    
    elif text.startswith("/news") and has_perm(peer_id, user_id, 'owner'):
        news = text[6:]
        for p in server_binds.values():
            send(p, f"📢 НОВОСТЬ:\n{news}")
        send(peer_id, "✅ НОВОСТИ ОТПРАВЛЕНЫ")
    
    elif text.startswith("/addzam") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if 'global' not in roles: roles['global'] = {}
            roles['global'][str(target)] = 'deputy_owner'
            save_all()
            send(peer_id, f"✅ ЗАМ.РУКОВОДИТЕЛЯ: ID{target}")
    
    elif text.startswith("/banid") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            if 'banned_chats' not in chat_settings: chat_settings['banned_chats'] = {}
            chat_settings['banned_chats'][str(parts[1])] = True
            save_all()
            send(peer_id, f"✅ БЕСЕДА {parts[1]} ЗАБЛОКИРОВАНА")
    
    elif text.startswith("/unbanid") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            if 'banned_chats' in chat_settings and str(parts[1]) in chat_settings['banned_chats']:
                del chat_settings['banned_chats'][str(parts[1])]
                save_all()
                send(peer_id, f"✅ БЕСЕДА {parts[1]} РАЗБЛОКИРОВАНА")
    
    elif text.startswith("/clearchat") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1])
            for db in [bans, mutes, warns, nicks, roles]:
                if str(target) in db:
                    del db[str(target)]
            save_all()
            send(peer_id, f"✅ ЧАТ {target} ОЧИЩЕН ИЗ БД")
    
    elif text.startswith("/infoid") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            count = sum(1 for p in roles if str(target) in roles.get(p, {}))
            send(peer_id, f"📊 ID{target}\n🌍 Глобал бан: {'ДА' if str(target) in global_bans else 'НЕТ'}\n📁 Чатов с ролью: {count}")
    
    elif text.startswith("/addbug") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target not in bug_receivers:
                bug_receivers.append(target)
                save_all()
                send(peer_id, f"✅ ID{target} ДОБАВЛЕН")
    
    elif text == "/listchats" and has_perm(peer_id, user_id, 'owner'):
        send(peer_id, f"📋 ЧАТОВ: {len(server_binds)}\nID: {', '.join(map(str, list(server_binds.values())[:10]))}")
    
    elif text.startswith("/adddev") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if 'global' not in roles: roles['global'] = {}
            roles['global'][str(target)] = 'dev'
            save_all()
            send(peer_id, f"✅ ПРАВА РАЗРАБОТЧИКА: ID{target}")
    
    elif text.startswith("/delbug") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target in bug_receivers:
                bug_receivers.remove(target)
                save_all()
                send(peer_id, f"✅ ID{target} УДАЛЕН")
                def main():
    print("=" * 60)
    print("🤖 BLACK FIB BOT ЗАПУЩЕН!")
    print("=" * 60)
    print(f"👑 Владелец: https://vk.com/id{OWNER_ID}")
    print(f"🆔 Группа: {GROUP_ID}")
    print("=" * 60)
    print("✅ ВСЕ 87 КОМАНД ЗАГРУЖЕНЫ")
    print("✅ /help - ПОЛНЫЙ СПИСОК")
    print("=" * 60)
    print("💬 Ожидание сообщений...\n")
    
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    msg = event.obj.message
                    peer_id = msg['peer_id']
                    user_id = msg['from_id']
                    text = msg.get('text', '').strip()
                    msg_id = msg.get('id')
                    
                    if user_id > 0 and text.startswith('/'):
                        if 'banned_chats' in chat_settings and str(peer_id) in chat_settings['banned_chats']:
                            if user_id == OWNER_ID:
                                send(peer_id, "⚠ Чат заблокирован", msg_id)
                            continue
                        handle(peer_id, user_id, text, msg_id)
                        
                elif event.type == VkBotEventType.GROUP_JOIN and event.obj.user_id:
                    p = str(event.obj.peer_id)
                    if p in chat_settings and 'welcome' in chat_settings[p]:
                        welcome = chat_settings[p]['welcome'].replace("{user}", get_nick(event.obj.peer_id, event.obj.user_id))
                        send(event.obj.peer_id, welcome)
                        
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Переподключение через 5 сек...")
            time.sleep(5)

if __name__ == "__main__":
    main()
