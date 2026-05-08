import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import time

TOKEN = 'vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg'
GROUP_ID = 229320501

print("=" * 50)
print("🚀 ЗАПУСК БОТА VK")
print("=" * 50)
print(f"Токен: {TOKEN[:30]}...")

try:
    # Подключаемся к VK
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    
    # Проверяем токен
    groups = vk.groups.getById()
    print(f"✅ Успешно! Группа: {groups[0]['name']}")
    print(f"🆔 ID группы: {groups[0]['id']}")
    
    # Подключаем LongPoll
    longpoll = VkLongPoll(vk_session)
    print("✅ LongPoll подключён")
    print("-" * 50)
    print("🤖 БОТ ЖДЁТ СООБЩЕНИЙ!")
    print("📨 Напишите боту 'Привет' в ЛС")
    print("-" * 50)
    
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            user_id = event.user_id
            message = event.text or ""
            
            # Определяем куда отвечать
            if event.from_chat:
                peer_id = 2000000000 + event.chat_id
            else:
                peer_id = user_id
            
            print(f"📨 Сообщение от {user_id}: {message[:50]}")
            
            # Отвечаем на команды
            if message.lower() == "привет":
                vk.method('messages.send', {
                    'peer_id': peer_id,
                    'message': 'Привет! Я бот Crazy RP! Напиши /help для команд',
                    'random_id': get_random_id()
                })
                print(f"✅ Ответ отправлен {user_id}")
            
            elif message.lower() == "/help" or message.lower() == "помощь":
                vk.method('messages.send', {
                    'peer_id': peer_id,
                    'message': '📚 Команды:\n/start - Начать\n/info - Информация\n/menu - Меню',
                    'random_id': get_random_id()
                })
                print(f"✅ Помощь отправлена {user_id}")
            
            elif message.lower() == "/info":
                vk.method('messages.send', {
                    'peer_id': peer_id,
                    'message': '🤖 Бот Crazy RP v1.0\n👑 Разработчик: [id631833072|Dmitriy]',
                    'random_id': get_random_id()
                })
            
            elif message.lower() == "/start":
                vk.method('messages.send', {
                    'peer_id': peer_id,
                    'message': '✅ Бот активирован!\nНапишите /help для списка команд',
                    'random_id': get_random_id()
                })
            
            else:
                # Ответ на любое сообщение (для проверки)
                vk.method('messages.send', {
                    'peer_id': peer_id,
                    'message': f'Я получил твоё сообщение: "{message[:50]}"\nНапиши /help для команд',
                    'random_id': get_random_id()
                })
                print(f"✅ Ответ на: {message[:30]}")

except Exception as e:
    print(f"❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
    print("Бот остановлен через 10 секунд...")
    time.sleep(10)
