import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
import sqlite3
from datetime import datetime
import re
import sys

print("=" * 50)
print("🚀 ЗАПУСК БОТА...")
print("=" * 50)

# ============= ТОКЕН (ВАШ) =============
TOKEN = 'vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg'
GROUP_ID = 229320501
OWNER_ID = 631833072

print(f"👑 Владелец: {OWNER_ID}")
print(f"📦 Токен: {TOKEN[:20]}... (обрезано)")

# ============= ПОДКЛЮЧЕНИЕ К VK =============
try:
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    
    # Проверка токена
    group_info = vk.groups.getById()
    print(f"✅ Успешно подключено к группе: {group_info[0]['name']}")
    print(f"🆔 ID группы: {group_info[0]['id']}")
    
    # Подключение LongPoll
    longpoll = VkLongPoll(vk_session)
    print("✅ LongPoll подключён")
    
except Exception as e:
    print(f"❌ ОШИБКА ПОДКЛЮЧЕНИЯ: {e}")
    sys.exit(1)

# ============= БАЗА ДАННЫХ =============
conn = sqlite3.connect('admin_bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    bot_activated INTEGER DEFAULT 0
)
''')
conn.commit()
print("✅ База данных готова")

# ============= ОТПРАВКА СООБЩЕНИЙ =============
def send_msg(peer_id, message, keyboard=None):
    try:
        params = {
            'peer_id': peer_id,
            'message': message,
            'random_id': get_random_id()
        }
        if keyboard:
            params['keyboard'] = keyboard.get_keyboard()
        vk.method('messages.send', params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# ============= КЛАВИАТУРЫ =============
def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('📊 Статистика', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('ℹ️ Информация', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('📜 Правила', color=VkKeyboardColor.SECONDARY)
    return keyboard

# ============= ГЛАВНЫЙ ЦИКЛ =============
print("-" * 50)
print("🤖 БОТ ЗАПУЩЕН И ЖДЁТ СООБЩЕНИЙ!")
print("💬 Напишите боту: /menu")
print("-" * 50)

try:
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            user_id = event.user_id
            message_text = event.text or ""
            
            if event.from_chat:
                chat_id = event.chat_id
                peer_id = 2000000000 + chat_id
            else:
                chat_id = 0
                peer_id = user_id
            
            print(f"📨 Получено сообщение от {user_id}: {message_text[:50]}")
            
            if message_text == '/menu':
                send_msg(peer_id, "🏠 **Главное меню**\nВыберите действие:", get_main_keyboard())
                print(f"✅ Отправлено меню пользователю {user_id}")
            
            elif message_text == '/info':
                send_msg(peer_id, "🤖 **BLACK FIB BOT v3.0**\n👑 Разработчик: [id631833072|Dmitriy]")
                print(f"✅ Отправлена информация пользователю {user_id}")
            
            elif message_text == '/start':
                send_msg(peer_id, "✅ Бот работает!\nВведите /menu для открытия меню")
                print(f"✅ Отправлен старт пользователю {user_id}")
            
            elif message_text == '/help':
                send_msg(peer_id, "📚 Команды:\n/menu - Главное меню\n/info - Информация\n/start - Старт")
                print(f"✅ Отправлена помощь пользователю {user_id}")

except KeyboardInterrupt:
    print("\n🛑 Бот остановлен")
except Exception as e:
    print(f"❌ ОШИБКА В ЦИКЛЕ: {e}")
    import traceback
    traceback.print_exc()
