# -*- coding: utf-8 -*-
# VK MODERATION BOT FULL SYSTEM
# Python 3.11+
# pip install vkbottle aiosqlite

from vkbottle.bot import Bot, Message
import aiosqlite
import asyncio
from datetime import datetime

TOKEN = "PASTE_NEW_TOKEN_HERE"

OWNER_ID = 631833072
GROUP_ID = 229320501

bot = Bot(token=TOKEN)

# ================= DATABASE =================

async def init_db():
    async with aiosqlite.connect("database.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'user',
            nick TEXT DEFAULT '',
            warns INTEGER DEFAULT 0,
            muted INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS warns(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reason TEXT,
            date TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS banwords(
            word TEXT
        )
        """)

        await db.commit()

asyncio.run(init_db())

# ================= ROLES =================

roles = {
    "user": 0,
    "moder": 1,
    "senmoder": 2,
    "admin": 3,
    "senadmin": 4,
    "owner": 5,
    "zam": 6,
    "dev": 7
}

# ================= FUNCTIONS =================

async def get_user(user_id):
    async with aiosqlite.connect("database.db") as db:

        async with db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ) as cursor:

            user = await cursor.fetchone()

        if not user:
            await db.execute(
                "INSERT INTO users(id) VALUES(?)",
                (user_id,)
            )

            await db.commit()

            return {
                "id": user_id,
                "role": "user",
                "nick": "",
                "warns": 0,
                "muted": 0,
                "banned": 0
            }

        return {
            "id": user[0],
            "role": user[1],
            "nick": user[2],
            "warns": user[3],
            "muted": user[4],
            "banned": user[5]
        }

async def set_role(user_id, role):
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user_id)
        )
        await db.commit()

async def has_role(user_id, role):

    if user_id == OWNER_ID:
        return True

    user = await get_user(user_id)

    return roles[user["role"]] >= roles[role]

# ================= HELP =================

HELP = """
📖 ВСЕ КОМАНДЫ БОТА

👤 Пользователь:
/info
/stats
/getid
/help

🛡 Модератор:
/kick
/mute
/unmute
/warn
/unwarn
/getban
/getwarn
/warnhistory
/staff
/setnick
/removenick
/nlist
/nonick
/getnick
/alt
/getacc
/warnlist
/clear
/getmute
/mutelist
/delete

⚔ Старший модератор:
/ban
/unban
/addmoder
/removerole
/zov
/online
/banlist
/onlinelist
/inactivelist

👑 Администратор:
/skick
/quiet
/sban
/sunban
/addsenmoder
/bug
/rnickall
/srnick
/ssetnick
/srrole
/srole

🔥 Старший администратор:
/addadmin
/settings
/filter
/szov
/serverinfo
/rkick

🏆 Владелец беседы:
/type
/leave
/editowner
/pin
/unpin
/clearwarn
/rroleall
/addsenadm
/masskick
/invite
/antiflood
/welcometext
/welcometextdelete

🌍 Зам.руководителя:
/gban
/gunban
/sync
/gbanlist
/banwords
/gbanpl
/gunbanpl
/addowner

💻 Руководитель:
/server
/addword
/delword
/gremoverole
/news
/addzam
/banid
/unbanid
/clearchat
/infoid
/addbug
/listchats
/adddev
/delbug
"""

# ================= BASIC COMMANDS =================

@bot.on.message(text="/help")
async def help_handler(message: Message):
    await message.answer(HELP)

@bot.on.message(text="/info")
async def info_handler(message: Message):
    await message.answer(
        "🤖 Официальные ресурсы бота\n\n"
        "👑 Владелец: vk.com/id631833072\n"
        "🏢 Группа: vk.com/club229320501"
    )

@bot.on.message(text="/stats")
async def stats_handler(message: Message):

    user = await get_user(message.from_id)

    await message.answer(
        f"📊 Ваша статистика\n\n"
        f"🆔 ID: {message.from_id}\n"
        f"🎭 Роль: {user['role']}\n"
        f"⚠ Варнов: {user['warns']}\n"
        f"🔇 Мут: {'Да' if user['muted'] else 'Нет'}\n"
        f"🚫 Бан: {'Да' if user['banned'] else 'Нет'}\n"
        f"📛 Ник: {user['nick'] if user['nick'] else 'Не установлен'}"
    )

@bot.on.message(text="/getid")
async def getid_handler(message: Message):
    await message.answer(f"🆔 Ваш ID: {message.from_id}")

# ================= MODERATION =================

@bot.on.message(text="/addmoder <id>")
async def addmoder_handler(message: Message, id: int):

    if not await has_role(message.from_id, "senmoder"):
        return await message.answer("❌ Нет доступа")

    await set_role(id, "moder")

    await message.answer(f"✅ Пользователь {id} назначен модератором")

@bot.on.message(text="/addsenmoder <id>")
async def addsenmoder_handler(message: Message, id: int):

    if not await has_role(message.from_id, "admin"):
        return await message.answer("❌ Нет доступа")

    await set_role(id, "senmoder")

    await message.answer(f"✅ Пользователь {id} назначен старшим модератором")

@bot.on.message(text="/addadmin <id>")
async def addadmin_handler(message: Message, id: int):

    if not await has_role(message.from_id, "senadmin"):
        return await message.answer("❌ Нет доступа")

    await set_role(id, "admin")

    await message.answer(f"✅ Пользователь {id} назначен администратором")

@bot.on.message(text="/addsenadm <id>")
async def addsenadm_handler(message: Message, id: int):

    if not await has_role(message.from_id, "owner"):
        return await message.answer("❌ Нет доступа")

    await set_role(id, "senadmin")

    await message.answer(f"✅ Пользователь {id} назначен старшим администратором")

@bot.on.message(text="/addowner <id>")
async def addowner_handler(message: Message, id: int):

    if not await has_role(message.from_id, "zam"):
        return await message.answer("❌ Нет доступа")

    await set_role(id, "owner")

    await message.answer(f"✅ Пользователь {id} назначен владельцем")

@bot.on.message(text="/addzam <id>")
async def addzam_handler(message: Message, id: int):

    if not await has_role(message.from_id, "dev"):
        return await message.answer("❌ Нет доступа")

    await set_role(id, "zam")

    await message.answer(f"✅ Пользователь {id} назначен замом")

@bot.on.message(text="/adddev <id>")
async def adddev_handler(message: Message, id: int):

    if message.from_id != OWNER_ID:
        return await message.answer("❌ Только владелец")

    await set_role(id, "dev")

    await message.answer(f"✅ Пользователь {id} назначен руководителем")

# ================= WARN SYSTEM =================

@bot.on.message(text="/warn <id> <reason>")
async def warn_handler(message: Message, id: int, reason: str):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ Нет доступа")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET warns = warns + 1 WHERE id = ?",
            (id,)
        )

        await db.execute(
            "INSERT INTO warns(user_id, reason, date) VALUES(?,?,?)",
            (
                id,
                reason,
                datetime.now().strftime("%d.%m.%Y %H:%M")
            )
        )

        await db.commit()

    await message.answer(
        f"⚠ Пользователь {id} получил предупреждение\n"
        f"📝 Причина: {reason}"
    )

@bot.on.message(text="/unwarn <id>")
async def unwarn_handler(message: Message, id: int):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ Нет доступа")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET warns = CASE WHEN warns > 0 THEN warns - 1 ELSE 0 END WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(f"✅ Варн у пользователя {id} снят")

@bot.on.message(text="/getwarn <id>")
async def getwarn_handler(message: Message, id: int):

    user = await get_user(id)

    await message.answer(
        f"⚠ Активные предупреждения пользователя {id}: {user['warns']}"
    )

# ================= MUTE SYSTEM =================

@bot.on.message(text="/mute <id>")
async def mute_handler(message: Message, id: int):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ Нет доступа")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET muted = 1 WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(f"🔇 Пользователь {id} замучен")

@bot.on.message(text="/unmute <id>")
async def unmute_handler(message: Message, id: int):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ Нет доступа")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET muted = 0 WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(f"🔊 Пользователь {id} размучен")

# ================= BAN SYSTEM =================

@bot.on.message(text="/ban <id>")
async def ban_handler(message: Message, id: int):

    if not await has_role(message.from_id, "senmoder"):
        return await message.answer("❌ Нет доступа")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET banned = 1 WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(f"🚫 Пользователь {id} заблокирован")

@bot.on.message(text="/unban <id>")
async def unban_handler(message: Message, id: int):

    if not await has_role(message.from_id, "senmoder"):
        return await message.answer("❌ Нет доступа")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET banned = 0 WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(f"✅ Пользователь {id} разблокирован")

# ================= NICK SYSTEM =================

@bot.on.message(text="/setnick <id> <nick>")
async def setnick_handler(message: Message, id: int, nick: str):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ Нет доступа")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET nick = ? WHERE id = ?",
            (nick, id)
        )

        await db.commit()

    await message.answer(f"📛 Ник пользователя {id} изменен на {nick}")

@bot.on.message(text="/removenick <id>")
async def removenick_handler(message: Message, id: int):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ Нет доступа")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET nick = '' WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(f"✅ Ник пользователя {id} удален")

# ================= STAFF =================

@bot.on.message(text="/staff")
async def staff_handler(message: Message):

    async with aiosqlite.connect("database.db") as db:

        async with db.execute(
            "SELECT id, role FROM users WHERE role != 'user'"
        ) as cursor:

            rows = await cursor.fetchall()

    if not rows:
        return await message.answer("❌ Стафф отсутствует")

    text = "👮 STAFF LIST\n\n"

    for row in rows:
        text += f"ID: {row[0]} | ROLE: {row[1]}\n"

    await message.answer(text)

# ================= FILTER =================

@bot.on.message()
async def antiflood_filter(message: Message):

    text = message.text.lower()

    async with aiosqlite.connect("database.db") as db:

        async with db.execute(
            "SELECT word FROM banwords"
        ) as cursor:

            rows = await cursor.fetchall()

    banned_words = [row[0] for row in rows]

    for word in banned_words:

        if word in text:

            try:
                await bot.api.messages.delete(
                    cmids=[message.conversation_message_id],
                    peer_id=message.peer_id,
                    delete_for_all=1
                )
            except:
                pass

            return

# ================= START =================

print("BOT STARTED")

bot.run_forever()
