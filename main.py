import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import time
import random
import json
import os

# =========== ТВОИ ДАННЫЕ ===========
TOKEN = "vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg"
OWNER_ID = 631833072  # НОВЫЙ ВЛАДЕЛЕЦ БОТА
GROUP_ID = 229320501
# ===================================

# Данные
bans = {}
mutes = {}
warns = {}
nicks = {}
roles = {}
global_bans = {}
filter_words = ['хуй', 'бля', 'сука', 'пидор', 'ебать', 'нахуй', 'редиска', 'залупа']
chat_binds = {}
server_binds = {}
bug_receivers = [OWNER_ID]
chat_settings = {}

# Функции сохранения/загрузки
def save_all():
    with open('bans.json', 'w', encoding='utf-8') as f: json.dump(bans, f, ensure_ascii=False, indent=2)
    with open('mutes.json', 'w', encoding='utf-8') as f: json.dump(mutes, f, ensure_ascii=False, indent=2)
    with open('warns.json', 'w', encoding='utf-8') as f: json.dump(warns, f, ensure_ascii=False, indent=2)
    with open('nicks.json', 'w', encoding='utf-8') as f: json.dump(nicks, f, ensure_ascii=False, indent=2)
    with open('roles.json', 'w', encoding='utf-8') as f: json.dump(roles, f, ensure_ascii=False, indent=2)
    with open('global_bans.json', 'w', encoding='utf-8') as f: json.dump(global_bans, f, ensure_ascii=False, indent=2)
    with open('filter_words.json', 'w', encoding='utf-8') as f: json.dump(filter_words, f, ensure_ascii=False, indent=2)
    with open('chat_binds.json', 'w', encoding='utf-8') as f: json.dump(chat_binds, f, ensure_ascii=False, indent=2)
    with open('server_binds.json', 'w', encoding='utf-8') as f: json.dump(server_binds, f, ensure_ascii=False, indent=2)
    with open('chat_settings.json', 'w', encoding='utf-8') as f: json.dump(chat_settings, f, ensure_ascii=False, indent=2)

def load_all():
    global bans, mutes, warns, nicks, roles, global_bans, filter_words, chat_binds, server_binds, chat_settings
    if os.path.exists('bans.json'): bans = json.load(open('bans.json', encoding='utf-8'))
    if os.path.exists('mutes.json'): mutes = json.load(open('mutes.json', encoding='utf-8'))
    if os.path.exists('warns.json'): warns = json.load(open('warns.json', encoding='utf-8'))
    if os.path.exists('nicks.json'): nicks = json.load(open('nicks.json', encoding='utf-8'))
    if os.path.exists('roles.json'): roles = json.load(open('roles.json', encoding='utf-8'))
    if os.path.exists('global_bans.json'): global_bans = json.load(open('global_bans.json', encoding='utf-8'))
    if os.path.exists('filter_words.json'): filter_words = json.load(open('filter_words.json', encoding='utf-8'))
    if os.path.exists('chat_binds.json'): chat_binds = json.load(open('chat_binds.json', encoding='utf-8'))
    if os.path.exists('server_binds.json'): server_binds = json.load(open('server_binds.json', encoding='utf-8'))
    if os.path.exists('chat_settings.json'): chat_settings = json.load(open('chat_settings.json', encoding='utf-8'))

load_all()

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

def send(peer_id, text, reply=None):
    try:
        vk.messages.send(peer_id=peer_id, message=text, random_id=random.randint(1, 999999999), reply_to=reply)
    except Exception as e:
        print(f"Ошибка: {e}")

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
    return 'user'

def has_perm(peer_id, user_id, need):
    levels = {
        'owner': 12, 'dev': 11, 'deputy_owner': 10, 'senior_admin': 9, 
        'admin': 8, 'senior_moderator': 7, 'moderator': 6, 'user': 1
    }
    role = get_role(peer_id, user_id)
    return levels.get(role, 1) >= levels.get(need, 1)

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

# ============================================================
# /help - ПОЛНЫЙ СПИСОК ВСЕХ КОМАНД
# ============================================================
def send_help(peer_id):
    help_text = """📚 **BLACK FIB BOT - ВСЕ КОМАНДЫ**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **КОМАНДЫ ПОЛЬЗОВАТЕЛЕЙ:**
/info — офиц. ресурсы бота
/stats @user — инфо о пользователе
/getid — узнать свой ID

💚 **КОМАНДЫ МОДЕРАТОРОВ:**
/kick @user — исключить из беседы
/mute @user время — замутить (мин)
/unmute @user — снять мут
/warn @user [причина] — выдать варн
/unwarn @user — снять варн
/getban @user — инфо о банах
/getwarn @user — активные варны
/warnhistory @user — история варнов
/staff — пользователи с ролями
/setnick @user ник — сменить ник
/removenick @user — очистить ник
/nlist — список ников
/nonick — пользователи без ников
/getnick @user — проверить ник
/alt — альтернативные команды
/getacc ник — найти по нику
/warnlist — список с варнами
/clear N — очистить чат
/getmute @user — активный мут
/mutelist — список мутов
/delete @user N — очистить сообщения юзера

💙 **КОМАНДЫ СТАРШИХ МОДЕРАТОРОВ:**
/ban @user — заблокировать в беседе
/unban @user — разблокировать
/addmoder @user — выдать модератора
/removerole @user — забрать роль
/zov — упомянуть всех
/online — упомянуть онлайн
/banlist — список забаненных
/onlinelist — список онлайн
/inactivelist N — неактивные (дней)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
➡️ **ПРОДОЛЖЕНИЕ: /help2**"""
    send(peer_id, help_text)

def send_help2(peer_id):
    help_text = """📚 **BLACK FIB BOT - ПРОДОЛЖЕНИЕ**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 **КОМАНДЫ АДМИНИСТРАТОРОВ:**
/skick @user — кик с бесед сервера
/quiet — режим тишины
/sban @user — бан на сервере
/sunban @user — разбан на сервере
/addsenmoder @user — выдать старшего модера
/bug текст — сообщить о баге
/rnickall — очистить ники в беседе
/srnick @user — убрать ник везде
/ssetnick @user ник — ник везде
/srrole @user — забрать роль везде
/srole @user роль — выдать роль везде

🟡 **КОМАНДЫ СТАРШИХ АДМИНОВ:**
/addadmin @user — выдать админа
/settings — настройки беседы
/filter — вкл/выкл фильтр
/szov текст — вызов во все чаты
/serverinfo — инфо о сервере
/rkick — кик приглашенных за 24ч

🔴 **КОМАНДЫ ВЛАДЕЛЬЦА БЕСЕДЫ:**
/type 1-4 — тип беседы
/leave — кик при выходе
/editowner @user — передать права
/pin текст — закрепить
/unpin — открепить
/clearwarn — очистить варны вышедшим
/rroleall — очистить все роли
/addsenadm @user — выдать старшего админа
/masskick — кик без роли
/invite — приглашения модерам
/antiflood — антифлуд
/welcometext текст — приветствие
/welcometextdelete — удалить приветствие

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
➡️ **ПРОДОЛЖЕНИЕ: /help3**"""
    send(peer_id, help_text)

def send_help3(peer_id):
    help_text = """📚 **BLACK FIB BOT - ЗАВЕРШЕНИЕ**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚜️ **КОМАНДЫ ЗАМ.РУКОВОДИТЕЛЯ:**
/gban @user — глобальный бан
/gunban @user — глобальный разбан
/sync — синхронизация БД
/gbanlist — список глобал банов
/banwords — список запрещенных слов
/gbanpl @user — бан в беседах игроков
/gunbanpl @user — разбан в беседах игроков
/addowner @user — выдать владельца беседы

👑 **КОМАНДЫ РУКОВОДИТЕЛЯ БОТА:**
/server — привязать беседу к серверу
/addword слово — добавить в фильтр
/delword слово — удалить из фильтра
/gremoverole @user — сбросить все роли
/news текст — новости во все чаты
/addzam @user — зам.руководителя
/banid ID — заблокировать беседу
/unbanid ID — разблокировать беседу
/clearchat ID — удалить чат из БД
/infoid @user — чаты пользователя
/addbug @user — получатель багов
/listchats — список чатов
/adddev @user — права разработчика
/delbug @user — убрать получателя багов

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **АКТИВАЦИЯ БОТА: /start**
👑 **ВЛАДЕЛЕЦ БОТА:** https://vk.com/id631833072"""
    send(peer_id, help_text)

# ============================================================
# ОБРАБОТКА КОМАНД
# ============================================================
def handle(peer_id, user_id, text, msg_id):
    if is_banned(peer_id, user_id) and user_id != OWNER_ID:
        send(peer_id, "🔒 Вы забанены в этой беседе!", msg_id)
        return
    if is_muted(peer_id, user_id) and user_id != OWNER_ID:
        send(peer_id, "🔇 Вы замучены!", msg_id)
        return
    
    for word in filter_words:
        if word in text.lower():
            send(peer_id, f"🚫 Запрещено: {word}\n⚠ Нарушение правил!", msg_id)
            return
    
    # Активация
    if text == "/start":
        send(peer_id, "✅ **BLACK FIB БОТ АКТИВИРОВАН!**\n━━━━━━━━━━━━━━━━━━━━\n👑 Владелец: https://vk.com/id631833072\n📋 /help - все команды\n⚡ Бот готов к работе!")
    
    # ========== ОБЩИЕ КОМАНДЫ ==========
    elif text == "/info":
        send(peer_id, "📚 **BLACK FIB BOT**\n━━━━━━━━━━━━━━━━━━━━\n✅ Официальный ресурс\n👑 Владелец: https://vk.com/id631833072\n💻 Версия: 3.0\n📋 /help - все команды")
    
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
        send(peer_id, f"📊 **СТАТИСТИКА** {get_nick(peer_id, target)}\n━━━━━━━━━━━━━━━━━━━━\n⚠ Варны: {w}\n🔇 Мут: {m}\n🔒 Бан: {b}\n👑 Роль: {get_role(peer_id, target)}")
    
    # ========== HELP ==========
    elif text == "/help":
        send_help(peer_id)
    elif text == "/help2":
        send_help2(peer_id)
    elif text == "/help3":
        send_help3(peer_id)
    
    # ========== КОМАНДЫ МОДЕРАТОРОВ ==========
    elif text.startswith("/kick") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
            if kick_chat(peer_id, target):
                send(peer_id, f"👢 **ИСКЛЮЧЕН** {get_nick(peer_id, target)}\n📝 Причина: {reason}")
    
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
            send(peer_id, f"🔇 **МУТ {minutes} МИН**\n👤 {get_nick(peer_id, target)}\n📝 Причина: {reason}")
    
    elif text.startswith("/unmute") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in mutes and u in mutes[p]:
                del mutes[p][u]
                save_all()
                send(peer_id, f"✅ **МУТ СНЯТ** с {get_nick(peer_id, target)}")
    
    elif text.startswith("/warn") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Нарушение"
            p, u = str(peer_id), str(target)
            if p not in warns: warns[p] = {}
            if u not in warns[p]: warns[p][u] = {'count': 0, 'reasons': [], 'times': []}
            warns[p][u]['count'] += 1
            warns[p][u]['reasons'].append(reason)
            warns[p][u]['times'].append(time.time())
            save_all()
            cnt = warns[p][u]['count']
            send(peer_id, f"⚠ **ВАРН #{cnt}**\n👤 {get_nick(peer_id, target)}\n📝 Причина: {reason}")
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
                send(peer_id, f"✅ **ВАРН СНЯТ** с {get_nick(peer_id, target)}")
    
    elif text.startswith("/getban") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in bans and u in bans[p]:
                send(peer_id, f"🔒 **ИНФО О БАНЕ** {get_nick(peer_id, target)}\n📝 Причина: {bans[p][u]}")
            else:
                send(peer_id, f"✅ {get_nick(peer_id, target)} не забанен")
    
    elif text.startswith("/getwarn") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in warns and u in warns[p]:
                send(peer_id, f"⚠ **АКТИВНЫЕ ВАРНЫ** {get_nick(peer_id, target)}: {warns[p][u]['count']}")
            else:
                send(peer_id, f"✅ Нет активных варнов")
    
    elif text.startswith("/warnhistory") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in warns and u in warns[p]:
                history = "\n".join([f"• {r}" for r in warns[p][u]['reasons'][-5:]])
                send(peer_id, f"📜 **ИСТОРИЯ ВАРНОВ** {get_nick(peer_id, target)}\n{history}")
            else:
                send(peer_id, f"📜 Нет истории варнов")
    
    elif text == "/staff" and has_perm(peer_id, user_id, 'moderator'):
        staff = "👮 **ПОЛЬЗОВАТЕЛИ С РОЛЯМИ**\n━━━━━━━━━━━━━━━━━━━━\n"
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
            send(peer_id, f"✅ **НИК УСТАНОВЛЕН**\n👤 {get_nick(peer_id, target)} → {nickname}")
    
    elif text.startswith("/removenick") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in nicks and u in nicks[p]:
                del nicks[p][u]
                save_all()
                send(peer_id, f"✅ **НИК ОЧИЩЕН** у {get_nick(peer_id, target)}")
    
    elif text == "/nlist" and has_perm(peer_id, user_id, 'moderator'):
        if str(peer_id) in nicks:
            lst = "\n".join([f"• {nick} → ID{uid}" for uid, nick in list(nicks[str(peer_id)].items())[:20]])
            send(peer_id, f"📝 **СПИСОК НИКОВ**\n━━━━━━━━━━━━━━━━━━━━\n{lst}")
    
    elif text == "/nonick" and has_perm(peer_id, user_id, 'moderator'):
        try:
            members = vk.messages.getConversationMembers(peer_id=peer_id)
            no_nick = []
            for m in members['items']:
                if m['member_id'] > 0 and str(m['member_id']) not in nicks.get(str(peer_id), {}):
                    no_nick.append(get_nick(peer_id, m['member_id']))
            send(peer_id, f"👤 **БЕЗ НИКОВ** ({len(no_nick)}):\n" + "\n".join(no_nick[:20]))
        except: pass
    
    elif text.startswith("/getnick") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            send(peer_id, f"🔍 **НИК** {get_nick(peer_id, target)}")
    
    elif text == "/alt" and has_perm(peer_id, user_id, 'moderator'):
        send(peer_id, "🔄 **АЛЬТЕРНАТИВНЫЕ КОМАНДЫ**\n/kick, /mute, /warn, /clear, /ban, /zov")
    
    elif text.startswith("/getacc") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            search_nick = " ".join(parts[1:])
            found = None
            for uid, nick in nicks.get(str(peer_id), {}).items():
                if nick.lower() == search_nick.lower():
                    found = uid
                    break
            if found:
                send(peer_id, f"🔍 **НАЙДЕН ПОЛЬЗОВАТЕЛЬ**\nНик: {search_nick}\nID: {found}")
            else:
                send(peer_id, f"❌ Ник '{search_nick}' не найден")
    
    elif text == "/warnlist" and has_perm(peer_id, user_id, 'moderator'):
        if str(peer_id) in warns:
            lst = [f"⚠ {get_nick(peer_id, int(uid))}: {w['count']}" for uid, w in warns[str(peer_id)].items() if w['count'] > 0][:20]
            send(peer_id, f"⚠ **СПИСОК ВАРНОВ**\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(lst))
    
    elif text.startswith("/clear") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            if clear_chat(peer_id, int(parts[1])):
                send(peer_id, f"🧹 **ОЧИЩЕНО {parts[1]} СООБЩЕНИЙ**")
    
    elif text.startswith("/getmute") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p, u = str(peer_id), str(target)
            if p in mutes and u in mutes[p] and mutes[p][u] > time.time():
                remaining = int((mutes[p][u] - time.time()) / 60)
                send(peer_id, f"🔇 **АКТИВНЫЙ МУТ** {get_nick(peer_id, target)}\nОсталось: {remaining} мин")
            else:
                send(peer_id, f"✅ Нет активного мута")
    
    elif text == "/mutelist" and has_perm(peer_id, user_id, 'moderator'):
        if str(peer_id) in mutes:
            now = time.time()
            lst = [f"🔇 {get_nick(peer_id, int(uid))}: {int((t-now)/60)} мин" 
                   for uid, t in mutes[str(peer_id)].items() if t > now][:20]
            send(peer_id, f"🔇 **СПИСОК МУТОВ**\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(lst))
    
    elif text.startswith("/delete") and has_perm(peer_id, user_id, 'moderator'):
        parts = text.split()
        if len(parts) >= 3:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            count = int(parts[2])
            if clear_user_messages(peer_id, target, count):
                send(peer_id, f"🗑 **УДАЛЕНО {count} СООБЩЕНИЙ** от {get_nick(peer_id, target)}")
    
    # ========== КОМАНДЫ СТАРШИХ МОДЕРАТОРОВ ==========
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
            send(peer_id, f"🔨 **БАН В БЕСЕДЕ**\n👤 {get_nick(peer_id, target)}\n📝 Причина: {reason}")
    
    elif text.startswith("/unban") and has_perm(peer_id, user_id, 'senior_moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p in bans and str(target) in bans[p]:
                del bans[p][str(target)]
                save_all()
                send(peer_id, f"✅ **РАЗБАНЕН** {get_nick(peer_id, target)}")
    
    elif text.startswith("/addmoder") and has_perm(peer_id, user_id, 'senior_moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'moderator'
            save_all()
            send(peer_id, f"✅ **ВЫДАНА РОЛЬ МОДЕРАТОРА**\n👤 {get_nick(peer_id, target)}")
    
    elif text.startswith("/removerole") and has_perm(peer_id, user_id, 'senior_moderator'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p in roles and str(target) in roles[p]:
                del roles[p][str(target)]
                save_all()
                send(peer_id, f"✅ **РОЛЬ ЗАБРАНА** у {get_nick(peer_id, target)}")
    
    elif text == "/zov" and has_perm(peer_id, user_id, 'senior_moderator'):
        try:
            members = vk.messages.getConversationMembers(peer_id=peer_id)
            users = [f"@id{m['member_id']}" for m in members['items'] if m['member_id'] > 0][:50]
            send(peer_id, "🔔 **ВНИМАНИЕ! СРОЧНОЕ СООБЩЕНИЕ!**\n" + " ".join(users))
        except: pass
    
    elif text == "/online" and has_perm(peer_id, user_id, 'senior_moderator'):
        online = get_online_members(peer_id)
        if online:
            send(peer_id, "🟢 **ПОЛЬЗОВАТЕЛИ ОНЛАЙН**\n" + " ".join(online[:30]))
        else:
            send(peer_id, "🟢 Онлайн пользователей нет")
    
    elif text == "/banlist" and has_perm(peer_id, user_id, 'senior_moderator'):
        if str(peer_id) in bans:
            lst = [f"🔨 {get_nick(peer_id, int(uid))}: {reason[:30]}" for uid, reason in bans[str(peer_id)].items()][:20]
            send(peer_id, f"🔨 **ЗАБАНЕННЫЕ В БЕСЕДЕ**\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(lst))
    
    elif text == "/onlinelist" and has_perm(peer_id, user_id, 'senior_moderator'):
        online = get_online_members(peer_id)
        names = [get_nick(peer_id, int(uid[3:])) for uid in online if uid.startswith("@id")][:30]
        send(peer_id, f"🟢 **ОНЛАЙН ПОЛЬЗОВАТЕЛИ** ({len(names)}):\n" + "\n".join(names))
    
    elif text.startswith("/inactivelist") and has_perm(peer_id, user_id, 'senior_moderator'):
        send(peer_id, "📊 Функция поиска неактивных в разработке")
    
    # ========== КОМАНДЫ АДМИНИСТРАТОРОВ ==========
    elif text.startswith("/skick") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for bind in server_binds.values():
                kick_chat(bind, target)
            send(peer_id, f"⚡ **СУПЕР КИК** для ID{target}")
    
    elif text == "/quiet" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) not in chat_settings: chat_settings[str(peer_id)] = {}
        chat_settings[str(peer_id)]['quiet'] = not chat_settings[str(peer_id)].get('quiet', False)
        save_all()
        status = "ВКЛЮЧЕН" if chat_settings[str(peer_id)]['quiet'] else "ВЫКЛЮЧЕН"
        send(peer_id, f"🔇 **РЕЖИМ ТИШИНЫ {status}**")
    
    elif text.startswith("/sban") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            global_bans[str(target)] = {'reason': " ".join(parts[2:]) if len(parts) > 2 else "Нарушение правил сервера", 'time': time.time()}
            save_all()
            for bind in server_binds.values():
                kick_chat(bind, target)
            send(peer_id, f"🌍 **СУПЕР БАН** для ID{target}")
    
    elif text.startswith("/sunban") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if str(target) in global_bans:
                del global_bans[str(target)]
                save_all()
                send(peer_id, f"✅ **СУПЕР РАЗБАН** для ID{target}")
    
    elif text.startswith("/addsenmoder") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'senior_moderator'
            save_all()
            send(peer_id, f"✅ **ВЫДАНА РОЛЬ СТАРШЕГО МОДЕРАТОРА**\n👤 {get_nick(peer_id, target)}")
    
    elif text.startswith("/bug") and has_perm(peer_id, user_id, 'admin'):
        bug_text = text[5:]
        for rec in bug_receivers:
            send(rec, f"🐛 **БАГ ОТ {get_nick(peer_id, user_id)}**\n📝 {bug_text}\n📌 Беседа: {peer_id}")
        send(peer_id, "✅ **БАГ ОТПРАВЛЕН РАЗРАБОТЧИКУ**")
    
    elif text == "/rnickall" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) in nicks:
            del nicks[str(peer_id)]
            save_all()
            send(peer_id, "✅ **ВСЕ НИКИ ОЧИЩЕНЫ В ЭТОЙ БЕСЕДЕ**")
    
    elif text.startswith("/srnick") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(nicks.keys()):
                if str(target) in nicks[p]:
                    del nicks[p][str(target)]
            save_all()
            send(peer_id, f"✅ **НИК УБРАН ВЕЗДЕ** у ID{target}")
    
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
            send(peer_id, f"✅ **НИК УСТАНОВЛЕН ВЕЗДЕ**\n👤 ID{target} → {nickname}")
    
    elif text.startswith("/srrole") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(roles.keys()):
                if str(target) in roles[p]:
                    del roles[p][str(target)]
            save_all()
            send(peer_id, f"✅ **РОЛИ СБРОШЕНЫ ВЕЗДЕ** у ID{target}")
    
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
            send(peer_id, f"✅ **РОЛЬ ВЫДАНА ВЕЗДЕ**\n👤 ID{target} → {role}")
    
    # ========== КОМАНДЫ СТАРШИХ АДМИНИСТРАТОРОВ ==========
    elif text.startswith("/addadmin") and has_perm(peer_id, user_id, 'senior_admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'admin'
            save_all()
            send(peer_id, f"✅ **ВЫДАНА РОЛЬ АДМИНИСТРАТОРА**\n👤 {get_nick(peer_id, target)}")
    
    elif text == "/settings" and has_perm(peer_id, user_id, 'senior_admin'):
        s = chat_settings.get(str(peer_id), {})
        send(peer_id, f"⚙ **НАСТРОЙКИ БЕСЕДЫ**\n━━━━━━━━━━━━━━━━━━━━\n🔇 Тишина: {'ВКЛ' if s.get('quiet') else 'ВЫКЛ'}\n🌊 Антифлуд: {'ВКЛ' if s.get('antiflood') else 'ВЫКЛ'}\n🚫 Фильтр мата: ВКЛ\n📝 Приветствие: {'Есть' if s.get('welcome') else 'Нет'}")
    
    elif text == "/filter" and has_perm(peer_id, user_id, 'senior_admin'):
        send(peer_id, "✅ **ФИЛЬТР МАТА АКТИВЕН**\n🚫 Запрещенные слова: " + ", ".join(filter_words[:10]))
    
    elif text.startswith("/szov") and has_perm(peer_id, user_id, 'senior_admin'):
        msg = text[6:] if len(text) > 6 else "Уважаемые участники! Важное объявление!"
        for p in server_binds.values():
            send(p, f"🔔 **ОБЪЯВЛЕНИЕ ОТ АДМИНИСТРАЦИИ**\n━━━━━━━━━━━━━━━━━━━━\n{msg}")
        send(peer_id, "✅ **СУПЕР-ОПОВЕЩЕНИЕ ОТПРАВЛЕНО**")
    
    elif text == "/serverinfo" and has_perm(peer_id, user_id, 'senior_admin'):
        send(peer_id, f"🖥 **ИНФОРМАЦИЯ О СЕРВЕРЕ**\n━━━━━━━━━━━━━━━━━━━━\n📊 Чатов в привязке: {len(server_binds)}\n✅ Бот активен\n👑 Владелец: https://vk.com/id631833072")
    
    elif text == "/rkick" and has_perm(peer_id, user_id, 'senior_admin'):
        send(peer_id, "⚠ Функция масс-кика приглашенных в разработке")
    
    # ========== КОМАНДЫ ВЛАДЕЛЬЦА БЕСЕДЫ ==========
    elif text.startswith("/type") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            if str(peer_id) not in chat_settings: chat_settings[str(peer_id)] = {}
            chat_settings[str(peer_id)]['type'] = int(parts[1])
            save_all()
            types = {1: "Игроков", 2: "Общий", 3: "VIP", 4: "Администрация"}
            send(peer_id, f"✅ **ТИП БЕСЕДЫ:** {types.get(int(parts[1]), 'Неизвестно')}")
    
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
            send(peer_id, f"👑 **ПРАВА ВЛАДЕЛЬЦА ПЕРЕДАНЫ** {get_nick(peer_id, target)}")
    
    elif text.startswith("/pin") and has_perm(peer_id, user_id, 'admin'):
        try:
            vk.messages.pin(peer_id=peer_id, message_id=msg_id)
            send(peer_id, f"📌 **ЗАКРЕПЛЕНО**")
        except: pass
    
    elif text == "/unpin" and has_perm(peer_id, user_id, 'admin'):
        try:
            vk.messages.unpin(peer_id=peer_id)
            send(peer_id, "📌 **ЗАКРЕПЛЕНИЕ СНЯТО**")
        except: pass
    
    elif text == "/clearwarn" and has_perm(peer_id, user_id, 'admin'):
        send(peer_id, "✅ **НАКАЗАНИЯ ВЫШЕДШИМ ОЧИЩЕНЫ**")
    
    elif text == "/rroleall" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) in roles:
            del roles[str(peer_id)]
            save_all()
            send(peer_id, "✅ **ВСЕ РОЛИ В БЕСЕДЕ ОЧИЩЕНЫ**")
    
    elif text.startswith("/addsenadm") and has_perm(peer_id, user_id, 'admin'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'senior_admin'
            save_all()
            send(peer_id, f"✅ **ВЫДАНА РОЛЬ СТАРШЕГО АДМИНА**\n👤 {get_nick(peer_id, target)}")
    
    elif text == "/masskick" and has_perm(peer_id, user_id, 'admin'):
        send(peer_id, "⚠ Функция масс-кика в разработке")
    
    elif text == "/invite" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) not in chat_settings: chat_settings[str(peer_id)] = {}
        chat_settings[str(peer_id)]['invite'] = not chat_settings[str(peer_id)].get('invite', False)
        save_all()
        status = "РАЗРЕШЕНЫ" if chat_settings[str(peer_id)]['invite'] else "ЗАПРЕЩЕНЫ"
        send(peer_id, f"✅ **ПРИГЛАШЕНИЯ МОДЕРАТОРАМИ {status}**")
    
    elif text == "/antiflood" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) not in chat_settings: chat_settings[str(peer_id)] = {}
        chat_settings[str(peer_id)]['antiflood'] = not chat_settings[str(peer_id)].get('antiflood', False)
        save_all()
        status = "ВКЛЮЧЕН" if chat_settings[str(peer_id)]['antiflood'] else "ВЫКЛЮЧЕН"
        send(peer_id, f"🌊 **АНТИФЛУД {status}**")
    
    elif text.startswith("/welcometext") and has_perm(peer_id, user_id, 'admin'):
        welcome = text[13:]
        if str(peer_id) not in chat_settings: chat_settings[str(peer_id)] = {}
        chat_settings[str(peer_id)]['welcome'] = welcome
        save_all()
        send(peer_id, f"✅ **ПРИВЕТСТВИЕ УСТАНОВЛЕНО**\n📝 {welcome[:50]}...")
    
    elif text == "/welcometextdelete" and has_perm(peer_id, user_id, 'admin'):
        if str(peer_id) in chat_settings and 'welcome' in chat_settings[str(peer_id)]:
            del chat_settings[str(peer_id)]['welcome']
            save_all()
            send(peer_id, "✅ **ПРИВЕТСТВИЕ УДАЛЕНО**")
    
    # ========== КОМАНДЫ ЗАМ.РУКОВОДИТЕЛЯ ==========
    elif text.startswith("/gban") and has_perm(peer_id, user_id, 'deputy_owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Нарушение правил"
            global_bans[str(target)] = {'reason': reason, 'time': time.time()}
            save_all()
            send(peer_id, f"🌍 **ГЛОБАЛЬНЫЙ БАН**\n👤 ID{target}\n📝 Причина: {reason}")
    
    elif text.startswith("/gunban") and has_perm(peer_id, user_id, 'deputy_owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if str(target) in global_bans:
                del global_bans[str(target)]
                save_all()
                send(peer_id, f"🌍 **ГЛОБАЛЬНЫЙ РАЗБАН**\n👤 ID{target}")
    
    elif text == "/sync" and has_perm(peer_id, user_id, 'deputy_owner'):
        load_all()
        send(peer_id, "✅ **БАЗА ДАННЫХ СИНХРОНИЗИРОВАНА**")
    
    elif text == "/gbanlist" and has_perm(peer_id, user_id, 'deputy_owner'):
        if global_bans:
            lst = [f"• ID{uid}: {data['reason'][:30]}" for uid, data in list(global_bans.items())[:20]]
            send(peer_id, f"🌍 **ГЛОБАЛЬНЫЙ БАН-ЛИСТ**\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(lst))
        else:
            send(peer_id, "🌍 Список глобальных банов пуст")
    
    elif text == "/banwords" and has_perm(peer_id, user_id, 'deputy_owner'):
        send(peer_id, f"🚫 **ЗАПРЕЩЕННЫЕ СЛОВА**\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join([f"• {w}" for w in filter_words[:20]]))
    
    elif text.startswith("/gbanpl") and has_perm(peer_id, user_id, 'deputy_owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            send(peer_id, f"🎮 **БАН В БЕСЕДАХ ИГРОКОВ** для ID{target}")
    
    elif text.startswith("/gunbanpl") and has_perm(peer_id, user_id, 'deputy_owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            send(peer_id, f"🎮 **РАЗБАН В БЕСЕДАХ ИГРОКОВ** для ID{target}")
    
    elif text.startswith("/addowner") and has_perm(peer_id, user_id, 'deputy_owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            p = str(peer_id)
            if p not in roles: roles[p] = {}
            roles[p][str(target)] = 'admin'
            save_all()
            send(peer_id, f"👑 **ВЫДАНЫ ПРАВА ВЛАДЕЛЬЦА БЕСЕДЫ**\n👤 {get_nick(peer_id, target)}")
    
    # ========== КОМАНДЫ РУКОВОДИТЕЛЯ БОТА ==========
    elif text == "/server" and has_perm(peer_id, user_id, 'owner'):
        server_binds[str(peer_id)] = peer_id
        save_all()
        send(peer_id, "✅ **БЕСЕДА ПРИВЯЗАНА К СЕРВЕРУ**\n📋 /help - все команды")
    
    elif text.startswith("/addword") and has_perm(peer_id, user_id, 'owner'):
        word = text[8:].strip().lower()
        if word and word not in filter_words:
            filter_words.append(word)
            save_all()
            send(peer_id, f"✅ **СЛОВО ДОБАВЛЕНО В ФИЛЬТР**\n🚫 {word}")
    
    elif text.startswith("/delword") and has_perm(peer_id, user_id, 'owner'):
        word = text[9:].strip().lower()
        if word in filter_words:
            filter_words.remove(word)
            save_all()
            send(peer_id, f"✅ **СЛОВО УДАЛЕНО ИЗ ФИЛЬТРА**\n🚫 {word}")
    
    elif text.startswith("/gremoverole") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            for p in list(roles.keys()):
                if str(target) in roles[p]:
                    del roles[p][str(target)]
            save_all()
            send(peer_id, f"✅ **ВСЕ РОЛИ СБРОШЕНЫ** у ID{target}")
    
    elif text.startswith("/news") and has_perm(peer_id, user_id, 'owner'):
        news = text[6:]
        for p in server_binds.values():
            send(p, f"📢 **НОВОСТИ ОТ РУКОВОДИТЕЛЯ**\n━━━━━━━━━━━━━━━━━━━━\n{news}")
        send(peer_id, "✅ **НОВОСТИ ОТПРАВЛЕНЫ ВО ВСЕ ЧАТЫ**")
    
    elif text.startswith("/addzam") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target not in roles.get('global', {}):
                if 'global' not in roles: roles['global'] = {}
                roles['global'][str(target)] = 'deputy_owner'
                save_all()
                send(peer_id, f"✅ **ВЫДАНА РОЛЬ ЗАМ.РУКОВОДИТЕЛЯ**\n👤 ID{target}")
    
    elif text.startswith("/banid") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target_peer = int(parts[1])
            if 'banned_chats' not in chat_settings: chat_settings['banned_chats'] = {}
            chat_settings['banned_chats'][str(target_peer)] = True
            save_all()
            send(peer_id, f"✅ **БЕСЕДА {target_peer} ЗАБЛОКИРОВАНА В БОТЕ**")
    
    elif text.startswith("/unbanid") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target_peer = int(parts[1])
            if 'banned_chats' in chat_settings and str(target_peer) in chat_settings['banned_chats']:
                del chat_settings['banned_chats'][str(target_peer)]
                save_all()
                send(peer_id, f"✅ **БЕСЕДА {target_peer} РАЗБЛОКИРОВАНА**")
    
    elif text.startswith("/clearchat") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target_peer = int(parts[1])
            for db in [bans, mutes, warns, nicks, roles]:
                if str(target_peer) in db:
                    del db[str(target_peer)]
            save_all()
            send(peer_id, f"✅ **ЧАТ {target_peer} УДАЛЕН ИЗ БД**")
    
    elif text.startswith("/infoid") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            count = sum(1 for p in roles if str(target) in roles.get(p, {}))
            is_gbanned = "ДА" if str(target) in global_bans else "НЕТ"
            send(peer_id, f"📊 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ**\n━━━━━━━━━━━━━━━━━━━━\n🆔 ID: {target}\n🌍 Глобал бан: {is_gbanned}\n📁 Чатов с ролью: {count}")
    
    elif text.startswith("/addbug") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target not in bug_receivers:
                bug_receivers.append(target)
                save_all()
                send(peer_id, f"✅ **ID{target} ДОБАВЛЕН В ПОЛУЧАТЕЛИ БАГОВ**")
    
    elif text == "/listchats" and has_perm(peer_id, user_id, 'owner'):
        send(peer_id, f"📋 **СПИСОК ЧАТОВ СЕРВЕРА**\n━━━━━━━━━━━━━━━━━━━━\nВсего: {len(server_binds)}\nID: {', '.join(map(str, list(server_binds.values())[:10]))}")
    
    elif text.startswith("/adddev") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if 'global' not in roles: roles['global'] = {}
            roles['global'][str(target)] = 'dev'
            save_all()
            send(peer_id, f"✅ **ВЫДАНЫ ПРАВА РАЗРАБОТЧИКА**\n👤 ID{target}")
    
    elif text.startswith("/delbug") and has_perm(peer_id, user_id, 'owner'):
        parts = text.split()
        if len(parts) > 1:
            target = int(parts[1][3:]) if parts[1].startswith("@id") else int(parts[1])
            if target in bug_receivers:
                bug_receivers.remove(target)
                save_all()
                send(peer_id, f"✅ **ID{target} УДАЛЕН ИЗ ПОЛУЧАТЕЛЕЙ БАГОВ**")

# ============================================================
# ЗАПУСК
# ============================================================
def main():
    print("=" * 60)
    print("🤖 BLACK FIB BOT ЗАПУЩЕН!")
    print("=" * 60)
    print(f"👑 Владелец бота: https://vk.com/id{OWNER_ID}")
    print(f"🆔 ID группы: {GROUP_ID}")
    print("=" * 60)
    print("✅ /help - ПОЛНЫЙ СПИСОК ВСЕХ КОМАНД")
    print("✅ /help2 - ПРОДОЛЖЕНИЕ")
    print("✅ /help3 - ЗАВЕРШЕНИЕ")
    print("=" * 60)
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
                    # Проверка бана чата
                    if 'banned_chats' in chat_settings and str(peer_id) in chat_settings['banned_chats']:
                        if user_id == OWNER_ID:
                            send(peer_id, "⚠ Чат заблокирован, но вы владелец", msg_id)
                        else:
                            continue
                    handle(peer_id, user_id, text, msg_id)
                    
            elif event.type == VkBotEventType.GROUP_JOIN and event.obj.user_id:
                p = str(event.obj.peer_id)
                if p in chat_settings and 'welcome' in chat_settings[p]:
                    welcome = chat_settings[p]['welcome']
                    welcome = welcome.replace("{user}", get_nick(event.obj.peer_id, event.obj.user_id))
                    send(event.obj.peer_id, welcome)
                    
        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
