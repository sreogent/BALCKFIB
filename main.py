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

# Данные
bans = {}
mutes = {}
warns = {}
nicks = {}
roles = {}
global_bans = []
filter_words = ['хуй', 'бля', 'сука', 'пидор', 'ебать', 'нахуй']
chat_binds = {}
bug_receivers = [CREATOR_ID]

# Функции
def save_data():
    with open('bans.json', 'w') as f: json.dump(bans, f)
    with open('mutes.json', 'w') as f: json.dump(mutes, f)
    with open('warns.json', 'w') as f: json.dump(warns, f)
    with open('nicks.json', 'w') as f: json.dump(nicks, f)
    with open('roles.json', 'w') as f: json.dump(roles, f)
    with open('global_bans.json', 'w') as f: json.dump(global_bans, f)
    with open('filter_words.json', 'w') as f: json.dump(filter_words, f)

def load_data():
    global bans, mutes, warns, nicks, roles, global_bans, filter_words, chat_binds
    if os.path.exists('bans.json'): bans = json.load(open('bans.json'))
    if os.path.exists('mutes.json'): mutes = json.load(open('mutes.json'))
    if os.path.exists('warns.json'): warns = json.load(open('warns.json'))
    if os.path.exists('nicks.json'): nicks = json.load(open('nicks.json'))
    if os.path.exists('roles.json'): roles = json.load(open('roles.json'))
    if os.path.exists('global_bans.json'): global_bans = json.load(open('global_bans.json'))
    if os.path.exists('filter_words.json'): filter_words = json.load(open('filter_words.json'))
    if os.path.exists('chat_binds.json'): chat_binds = json.load(open('chat_binds.json'))

load_data()

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

def send(peer_id, text, reply=None):
    try:
        vk.messages.send(peer_id=peer_id, message=text, random_id=random.randint(1, 999999999), reply_to=reply)
    except: pass

def get_nick(peer_id, user_id):
    p, u = str(peer_id), str(user_id)
    if p in nicks and u in nicks[p]:
        return nicks[p][u]
    try:
        user = vk.users.get(user_ids=user_id)[0]
        return f"{user['first_name']} {user['last_name']}"
    except:
        return f"ID{user_id}"

def get_role(peer_id, user_id):
    if user_id == CREATOR_ID:
        return 'creator'
    p, u = str(peer_id), str(user_id)
    if p in roles and u in roles[p]:
        return roles[p][u]
    return 'user'

def has_perm(peer_id, user_id, need):
    levels = {'creator':10, 'deputy_creator':9, 'special_admin':8, 'deputy_special':7, 
              'senior_admin':6, 'admin':5, 'senior_moderator':4, 'moderator':3, 'helper':2, 'user':1}
    role = get_role(peer_id, user_id)
    return levels.get(role, 1) >= levels.get(need, 1)

def is_muted(peer_id, user_id):
    p, u = str(peer_id), str(user_id)
    if p in mutes and u in mutes[p]:
        if mutes[p][u] > time.time():
            return True
        else:
            del mutes[p][u]
            save_data()
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

# ОБРАБОТКА КОМАНД
def handle(peer_id, user_id, text, msg_id):
    if is_banned(peer_id, user_id) and user_id != CREATOR_ID:
        send(peer_id, "🔒 Вы забанены", msg_id)
        return
    if is_muted(peer_id, user_id) and user_id != CREATOR_ID:
        send(peer_id, "🔇 Вы замучены", msg_id)
        return
    
    for word in filter_words:
        if word in text.lower():
            send(peer_id, f"🚫 Запрещено: {word}", msg_id)
            return
    
    # ========== /help - НОРМАЛЬНЫЙ ПОЛНЫЙ СПИСОК ==========
    if text == "/help":
        help_text = """📚 **BLACK FIB BOT - ВСЕ КОМАНДЫ**
━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **ДЛЯ ВСЕХ:**
/info - инфо о боте
/stats @user - статистика
/getid - свой ID
/test - проверка
/ping - пинг

💚 **ХЕЛПЕРЫ:**
/kick @user [причина]
/mute @user время [причина]
/unmute @user
/warn @user [причина]
/unwarn @user
/clear 10
/staff
/setnick @user ник
/nlist
/warnlist
/mutelist

💙 **МОДЕРАТОРЫ:**
/ban @user [причина]
/unban @user
/addmoder @user
/removerole @user
/zov
/banlist

🔵 **СТАРШИЕ МОДЕРАТОРЫ:**
/quiet
/addsenmoder @user
/bug текст
/rnickall

🟢 **АДМИНИСТРАТОРЫ:**
/addadmin @user
/settings
/filter
/serverinfo

━━━━━━━━━━━━━━━━━━━━━━━━━
➡️ ПРОДОЛЖЕНИЕ: /help2"""
        send(peer_id, help_text)
    
    elif text == "/help2":
        help_text = """📚 **BLACK FIB BOT - ПРОДОЛЖЕНИЕ**
━━━━━━━━━━━━━━━━━━━━━━━━━

🟡 **СТАРШИЕ АДМИНЫ:**
/type 1-4
/leave
/editowner @user
/pin текст
/unpin
/rroleall
/addsenadm @user
/antiflood
/welcometext текст

🔴 **СПЕЦ АДМИНЫ:**
/gban @user
/gunban @user
/gbanlist
/banwords
/addowner @user
/skick @user
/sban @user

🟠 **ЗАМ.СПЕЦ АДМИНА:**
/addword слово
/delword слово
/pull название
/pullinfo
/delpull название
/srnick @user
/ssetnick @user ник
/szov текст

👑 **ВЛАДЕЛЕЦ:**
/news текст
/addzam @user

⚜️ **ЗАМ.СОЗДАТЕЛЯ:**
/banid id
/unbanid id
/clearchat id
/listchats
/server

━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Для активации в беседе: /start"""
        send(peer_id, help_text)
    
    # ========== ОСНОВНЫЕ КОМАНДЫ ==========
    elif text == "/info":
        send(peer_id, "📚 BLACK FIB BOT\n✅ Работает!\n👑 Создатель: @id749488560\n💡 /help - все команды")
    
    elif text == "/getid":
        send(peer_id, f"🆔 Ваш ID: {user_id}")
    
    elif text == "/test":
        send(peer_id, "✅ Бот работает! Комар носа не подточит!")
    
    elif text == "/ping":
        send(peer_id, "🏓 Понг!")
    
    elif text.startswith("/stats"):
        parts = text.split()
        target = user_id
        if len(parts) > 1:
            if parts[1].startswith("@id"):
                target = int(parts[1][3:])
            elif parts[1].isdigit():
                target = int(parts[1])
        p, u = str(peer_id), str(target)
        w = warns.get(p, {}).get(u, {}).get('count', 0)
        m = "Да" if is_muted(peer_id, target) else "Нет"
        send(peer_id, f"📊 Статистика {get_nick(peer_id, target)}\n⚠ Варны: {w}\n🔇 Мут: {m}\n👑 Роль: {get_role(peer_id, target)}")
    
    # ========== АКТИВАЦИЯ ==========
    elif text == "/start":
        send(peer_id, "✅ BLACK FIB БОТ АКТИВИРОВАН!\n📋 /help - список команд\n👑 @id749488560")
    
    # ========== ХЕЛПЕРЫ ==========
    elif text.startswith("/kick") and has_perm(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
            if kick_chat(peer_id, target):
                send(peer_id, f"👢 Кикнут {get_nick(peer_id, target)}\nПричина: {reason}")
    
    elif text.startswith("/mute") and has_perm(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) >= 3:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            minutes = int(parts[2])
            reason = " ".join(parts[3:]) if len(parts) > 3 else "Не указана"
            p, u = str(peer_id), str(target)
            if p not in mutes: mutes[p] = {}
            mutes[p][u] = time.time() + minutes * 60
            save_data()
            send(peer_id, f"🔇 Мут {minutes} мин для {get_nick(peer_id, target)}\nПричина: {reason}")
    
    elif text.startswith("/unmute") and has_perm(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in mutes and u in mutes[p]:
                del mutes[p][u]
                save_data()
                send(peer_id, f"✅ Мут снят с {get_nick(peer_id, target)}")
    
    elif text.startswith("/warn") and has_perm(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Нарушение"
            p, u = str(peer_id), str(target)
            if p not in warns: warns[p] = {}
            if u not in warns[p]: warns[p][u] = {'count': 0, 'reasons': []}
            warns[p][u]['count'] += 1
            warns[p][u]['reasons'].append(reason)
            save_data()
            cnt = warns[p][u]['count']
            send(peer_id, f"⚠ Варн #{cnt} для {get_nick(peer_id, target)}\nПричина: {reason}")
            if cnt >= 3:
                if p not in mutes: mutes[p] = {}
                mutes[p][u] = time.time() + 3600
                save_data()
                send(peer_id, f"🔇 3 варна = мут 60 мин")
    
    elif text.startswith("/unwarn") and has_perm(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in warns and u in warns[p]:
                warns[p][u]['count'] = 0
                save_data()
                send(peer_id, f"✅ Варны сброшены для {get_nick(peer_id, target)}")
    
    elif text.startswith("/clear") and has_perm(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 1:
            if clear_chat(peer_id, int(parts[1])):
                send(peer_id, f"🧹 Очищено {parts[1]} сообщений")
    
    elif text == "/staff" and has_perm(peer_id, user_id, 'helper'):
        staff = "👮 АДМИНИСТРАЦИЯ\n━━━━━━━━━━\n👑 Создатель: @id749488560\n"
        if str(peer_id) in roles:
            for uid, r in roles[str(peer_id)].items():
                staff += f"⭐ {r}: {get_nick(peer_id, int(uid))}\n"
        send(peer_id, staff[:4000])
    
    elif text.startswith("/setnick") and has_perm(peer_id, user_id, 'helper'):
        parts = text.split()
        if len(parts) > 2:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            nickname = " ".join(parts[2:])
            p = str(peer_id)
            if p not in nicks: nicks[p] = {}
            nicks[p][str(target)] = nickname
            save_data()
            send(peer_id, f"✅ Ник установлен: {nickname}")
    
    elif text == "/nlist" and has_perm(peer_id, user_id, 'helper'):
        if str(peer_id) in nicks:
            lst = "\n".join([f"• {nick}" for nick in list(nicks[str(peer_id)].values())[:15]])
            send(peer_id, f"📝 СПИСОК НИКОВ:\n{lst}")
    
    elif text == "/warnlist" and has_perm(peer_id, user_id, 'helper'):
        if str(peer_id) in warns:
            lst = [f"• {get_nick(peer_id, int(uid))}: {w['count']}" for uid, w in warns[str(peer_id)].items()][:15]
            send(peer_id, f"⚠ СПИСОК ВАРНОВ:\n" + "\n".join(lst))
    
    elif text == "/mutelist" and has_perm(peer_id, user_id, 'helper'):
        if str(peer_id) in mutes:
            now = time.time()
            lst = [f"• {get_nick(peer_id, int(uid))}: {int((t-now)/60)} мин" 
                   for uid, t in mutes[str(peer_id)].items() if t > now][:15]
            send(peer_id, f"🔇 АКТИВНЫЕ МУТЫ:\n" + "\n".join(lst))
    
    # ========== МОДЕРАТОРЫ ==========
    elif text.startswith("/ban") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
            p = str(peer_id)
            if p not in bans: bans[p] = {}
            bans[p][str(target)] = reason
            save_data()
            kick_chat(peer_id, target)
            send(peer_id, f"🔨 БАН для {get_nick(peer_id, target)}\nПричина: {reason}")
    
    elif text.startswith("/unban") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p in bans and str(target) in bans[p]:
                del bans[p][str(target)]
                save_data()
                send(peer_id, f"✅ Бан снят с {get_nick(peer_id, target)}")
    
    elif text.startswith("/addmoder") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'moderator'
            save_data()
            send(peer_id, f"✅ {get_nick(peer_id, target)} теперь МОДЕРАТОР!")
    
    elif text.startswith("/removerole") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p in roles and str(target) in roles[p]:
                del roles[p][str(target)]
                save_data()
                send(peer_id, f"✅ Роль снята с {get_nick(peer_id, target)}")
    
    elif text == "/zov" and has_perm(peer_id, user_id, 'moderator'):
        try:
            members = vk.messages.getConversationMembers(peer_id=peer_id)
            users = [f"@id{m['member_id']}" for m in members['items'] if m['member_id'] > 0][:50]
            send(peer_id, "🔔 ВНИМАНИЕ! " + " ".join(users))
        except: pass
    
    elif text == "/banlist" and has_perm(peer_id, user_id, 'moderator'):
        if str(peer_id) in bans:
            lst = [f"• {get_nick(peer_id, int(uid))}: {reason}" for uid, reason in bans[str(peer_id)].items()][:15]
            send(peer_id, f"🔨 ЗАБАНЕННЫЕ:\n" + "\n".join(lst))
    
    # ========== СТАРШИЕ МОДЕРАТОРЫ ==========
    elif text == "/quiet" and has_perm(peer_id, user_id, 'senior_moderator'):
        send(peer_id, "🔇 Режим тишины (функция в разработке)")
    
    elif text.startswith("/addsenmoder") and has_perm(peer_id, user_id, 'senior_moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'senior_moderator'
            save_data()
            send(peer_id, f"✅ {get_nick(peer_id, target)} теперь СТАРШИЙ МОДЕРАТОР!")
    
    elif text.startswith("/bug") and has_perm(peer_id, user_id, 'senior_moderator'):
        bug_text = text[5:]
        for rec in bug_receivers:
            send(rec, f"🐛 БАГ от {get_nick(peer_id, user_id)}:\n{bug_text}")
        send(peer_id, "✅ Баг отправлен создателю")
    
    elif text == "/rnickall" and has_perm(peer_id, user_id, 'senior_moderator'):
        if str(peer_id) in nicks:
            del nicks[str(peer_id)]
            save_data()
            send(peer_id, "✅ Все ники сброшены")
    
    # ========== АДМИНИСТРАТОРЫ ==========
    elif text.startswith("/addadmin") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'admin'
            save_data()
            send(peer_id, f"✅ {get_nick(peer_id, target)} теперь АДМИНИСТРАТОР!")
    
    elif text == "/settings" and has_perm(peer_id, user_id, 'admin'):
        send(peer_id, "⚙ НАСТРОЙКИ:\n/quiet - тишина\n/filter - фильтр мата\n/antiflood - антифлуд")
    
    elif text == "/filter" and has_perm(peer_id, user_id, 'admin'):
        send(peer_id, "✅ Фильтр мата АКТИВЕН")
    
    elif text == "/serverinfo" and has_perm(peer_id, user_id, 'admin'):
        send(peer_id, f"ℹ БЕСЕДА ID: {peer_id}\nБот: BLACK FIB")
    
    # ========== СТАРШИЕ АДМИНЫ ==========
    elif text.startswith("/type") and has_perm(peer_id, user_id, 'senior_admin'):
        send(peer_id, "✅ Тип беседы установлен")
    
    elif text == "/leave" and has_perm(peer_id, user_id, 'senior_admin'):
        send(peer_id, "👋 Бот покидает беседу...")
        time.sleep(1)
        try:
            vk.messages.removeChatUser(chat_id=peer_id-2000000000, user_id=-GROUP_ID)
        except: pass
    
    elif text.startswith("/pin") and has_perm(peer_id, user_id, 'senior_admin'):
        try:
            vk.messages.pin(peer_id=peer_id, message_id=msg_id)
            send(peer_id, f"📌 Закреплено")
        except: pass
    
    elif text == "/unpin" and has_perm(peer_id, user_id, 'senior_admin'):
        try:
            vk.messages.unpin(peer_id=peer_id)
            send(peer_id, "📌 Закрепление снято")
        except: pass
    
    elif text == "/rroleall" and has_perm(peer_id, user_id, 'senior_admin'):
        if str(peer_id) in roles:
            del roles[str(peer_id)]
            save_data()
            send(peer_id, "✅ Все роли сброшены")
    
    elif text.startswith("/addsenadm") and has_perm(peer_id, user_id, 'senior_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'senior_admin'
            save_data()
            send(peer_id, f"✅ {get_nick(peer_id, target)} теперь СТАРШИЙ АДМИН!")
    
    elif text == "/antiflood" and has_perm(peer_id, user_id, 'senior_admin'):
        send(peer_id, "🌊 Антифлуд включен")
    
    elif text.startswith("/welcometext") and has_perm(peer_id, user_id, 'senior_admin'):
        send(peer_id, f"✅ Приветствие установлено")
    
    # ========== СПЕЦ АДМИНЫ ==========
    elif text.startswith("/gban") and has_perm(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target not in global_bans:
                global_bans.append(target)
                save_data()
                send(peer_id, f"🌍 ГЛОБАЛЬНЫЙ БАН для ID{target}")
    
    elif text.startswith("/gunban") and has_perm(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target in global_bans:
                global_bans.remove(target)
                save_data()
                send(peer_id, f"🌍 Глобальный бан снят")
    
    elif text == "/gbanlist" and has_perm(peer_id, user_id, 'special_admin'):
        lst = "\n".join([f"• ID{uid}" for uid in global_bans[:20]])
        send(peer_id, f"🌍 ГЛОБАЛ БАНЫ:\n{lst}" if lst else "🌍 Список пуст")
    
    elif text == "/banwords" and has_perm(peer_id, user_id, 'special_admin'):
        send(peer_id, f"🚫 ЗАПРЕЩЕННЫЕ СЛОВА:\n{', '.join(filter_words)}")
    
    elif text.startswith("/addowner") and has_perm(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'creator'
            save_data()
            send(peer_id, f"👑 {get_nick(peer_id, target)} теперь ВЛАДЕЛЕЦ!")
    
    elif text.startswith("/skick") and has_perm(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for bind in chat_binds.values():
                kick_chat(bind, target)
            send(peer_id, f"⚡ Супер кик для ID{target}")
    
    elif text.startswith("/sban") and has_perm(peer_id, user_id, 'special_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target not in global_bans:
                global_bans.append(target)
                save_data()
                send(peer_id, f"⚡ Супер бан для ID{target}")
    
    # ========== ЗАМ.СПЕЦ АДМИНА ==========
    elif text.startswith("/addword") and has_perm(peer_id, user_id, 'deputy_special'):
        word = text[8:].strip().lower()
        if word and word not in filter_words:
            filter_words.append(word)
            save_data()
            send(peer_id, f"✅ Добавлено слово: {word}")
    
    elif text.startswith("/delword") and has_perm(peer_id, user_id, 'deputy_special'):
        word = text[9:].strip().lower()
        if word in filter_words:
            filter_words.remove(word)
            save_data()
            send(peer_id, f"✅ Удалено слово: {word}")
    
    elif text.startswith("/pull") and has_perm(peer_id, user_id, 'deputy_special'):
        name = text[6:].strip()
        if name:
            chat_binds[name] = peer_id
            save_data()
            send(peer_id, f"✅ Привязка '{name}' создана")
    
    elif text == "/pullinfo" and has_perm(peer_id, user_id, 'deputy_special'):
        if chat_binds:
            info = "\n".join([f"• {k}: чат {v}" for k, v in chat_binds.items()])
            send(peer_id, f"📋 ПРИВЯЗКИ:\n{info}")
    
    elif text.startswith("/delpull") and has_perm(peer_id, user_id, 'deputy_special'):
        name = text[9:].strip()
        if name in chat_binds:
            del chat_binds[name]
            save_data()
            send(peer_id, f"✅ Привязка '{name}' удалена")
    
    elif text.startswith("/srnick") and has_perm(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(nicks.keys()):
                if str(target) in nicks[p]:
                    del nicks[p][str(target)]
            save_data()
            send(peer_id, f"✅ Ник сброшен везде")
    
    elif text.startswith("/ssetnick") and has_perm(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 2:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            nickname = " ".join(parts[2:])
            for p in list(nicks.keys()):
                if p not in nicks: nicks[p] = {}
                nicks[p][str(target)] = nickname
            save_data()
            send(peer_id, f"✅ Ник '{nickname}' везде")
    
    elif text.startswith("/srrole") and has_perm(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(roles.keys()):
                if str(target) in roles[p]:
                    del roles[p][str(target)]
            save_data()
            send(peer_id, f"✅ Роли сброшены везде")
    
    elif text.startswith("/srole") and has_perm(peer_id, user_id, 'deputy_special'):
        parts = text.split()
        if len(parts) > 2:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            role = parts[2]
            for p in list(roles.keys()):
                if p not in roles: roles[p] = {}
                roles[p][str(target)] = role
            save_data()
            send(peer_id, f"✅ Роль '{role}' везде")
    
    elif text.startswith("/szov") and has_perm(peer_id, user_id, 'deputy_special'):
        msg = text[6:] if len(text) > 6 else "ВНИМАНИЕ!"
        for p in chat_binds.values():
            send(p, f"🔔 СУПЕР ОПОВЕЩЕНИЕ:\n{msg}")
        send(peer_id, "✅ Супер-оповещение отправлено")
    
    # ========== ВЛАДЕЛЕЦ БЕСЕДЫ ==========
    elif text.startswith("/news") and has_perm(peer_id, user_id, 'creator'):
        news_text = text[6:]
        for p in chat_binds.values():
            send(p, f"📢 НОВОСТЬ:\n{news_text}")
        send(peer_id, "✅ Новости отправлены")
    
    elif text.startswith("/addzam") and has_perm(peer_id, user_id, 'creator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'deputy_creator'
            save_data()
            send(peer_id, f"✅ {get_nick(peer_id, target)} теперь ЗАМ.СОЗДАТЕЛЯ!")
    
    # ========== ЗАМ.СОЗДАТЕЛЯ ==========
    elif text.startswith("/banid") and has_perm(peer_id, user_id, 'deputy_creator'):
        parts = text.split()
        if len(parts) > 1:
            bans[str(parts[1])] = {}
            save_data()
            send(peer_id, f"✅ Беседа {parts[1]} заблокирована")
    
    elif text.startswith("/unbanid") and has_perm(peer_id, user_id, 'deputy_creator'):
        parts = text.split()
        if len(parts) > 1:
            if str(parts[1]) in bans:
                del bans[str(parts[1])]
                save_data()
                send(peer_id, f"✅ Беседа {parts[1]} разблокирована")
    
    elif text == "/listchats" and has_perm(peer_id, user_id, 'deputy_creator'):
        send(peer_id, f"📋 Чатов в привязке: {len(chat_binds)}")
    
    elif text == "/server" and has_perm(peer_id, user_id, 'deputy_creator'):
        send(peer_id, f"🖥 СЕРВЕР: OK\nБД загружена\nБот активен")
    
    # ========== СОЗДАТЕЛЬ БОТА ==========
    elif text == "/sync" and user_id == CREATOR_ID:
        load_data()
        send(peer_id, "✅ БД синхронизирована")

# ЗАПУСК
def main():
    print("=" * 50)
    print("🤖 BLACK FIB BOT ЗАПУЩЕН!")
    print("=" * 50)
    print(f"👑 Создатель: @id{CREATOR_ID}")
    print(f"🆔 Группа: {GROUP_ID}")
    print("=" * 50)
    print("✅ /help - ВСЕ КОМАНДЫ")
    print("✅ /help2 - ПРОДОЛЖЕНИЕ")
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
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
