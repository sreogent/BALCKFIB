import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

TOKEN = 'vk1.a.6TizPN4pg1-Fhk95_LrCbP9i3LqBnP_J5D-Y8Us4JN-1J2NIwReHNbyTscHIRlDoTluqgMsZRrHbQvXyJqizcZGoZ-bOzUiAk8v9UMfqVesLgBo-gKM4CCHhfZcZ5AGx4kQ-gubA_Fo2ViRP6o2PK3FHZph2cefAn-4IOydOluHpvYWmqw-KKMnwDa4QYYhB7AC_TJunZ_oApcoXbexZdg'

vk = vk_api.VkApi(token=TOKEN)
longpoll = VkLongPoll(vk)

print("🤖 Простой бот запущен!")
print("Отправь ему команду /test")

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        
        if event.text == "/test":
            vk.method('messages.send', {
                'peer_id': event.peer_id,
                'message': "✅ Бот работает!",
                'random_id': get_random_id()
            })
            print(f"Ответил на команду /test от {event.user_id}")
        
        # Отвечаем на любое сообщение
        elif event.text:
            vk.method('messages.send', {
                'peer_id': event.peer_id,
                'message': f"Ты написал: {event.text}",
                'random_id': get_random_id()
            })
            print(f"Ответил пользователю {event.user_id}")