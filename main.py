# -*- coding: utf-8 -*-
# FULL VK BOT SYSTEM
# Python 3.11+
# pip install vkbottle aiosqlite

from vkbottle.bot import Bot, Message
import aiosqlite
import asyncio
from datetime import datetime

# ================= CONFIG =================

TOKEN = "vk1.a.PNIoWwI7Erk6T7s4-9lGQAXmRLsqmDBFv1Oz_X9IkjFxuk2avaxoaKKHBxBlhfffoZf-P2EhZ2nMbzWoaZlLfk8PFBi_SafqB3QD1GS2ntswN0ig8s76KyZfpKwvNYvMNtGPRGH3v8z3CcIP-xgO8xiXGH_50kati168i6U-L1hMQDZNAiBW80XE3Ub5TGqumAOD-beIwf0cSMwL-ET8Sg"

OWNER_ID = 631833072
GROUP_ID = 229320501

PREFIX = "/"

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
        CREATE TABLE IF NOT EXISTS settings(
            chat_id INTEGER PRIMARY KEY,
            antiflood INTEGER DEFAULT 0,
            filter INTEGER DEFAULT 0,
            quiet INTEGER DEFAULT 0
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
📖 ВСЕ КОМАНДЫ

👤 Пользователь:
/help
/info
/stats
/getid

🛡 Модератор:
/kick
/mute
/unmute
/warn
/unwarn
/getwarn
/getmute
/setnick
/removenick
/getnick
/staff

⚔ Старший модератор:
/ban
/unban
/addmoder
/removerole

👑 Администратор:
/addsenmoder
/addadmin
/clear
/delete
/online

🔥 Старший администратор:
/settings
/filter
/serverinfo

🏆 Владелец:
/addsenadm
/masskick
/antiflood
/welcometext

🌍 Зам:
/gban
/gunban
/addowner

💻 Руководитель:
/addzam
/adddev
/addword
/delword
"""

# ================= BASIC =================

@bot.on.message(text="/help")
async def help_handler(message: Message):

    await message.answer(HELP)

@bot.on.message(text="/info")
async def info_handler(message: Message):

    await message.answer(
        "🤖 VK BOT SYSTEM\n"
        "👑 OWNER: vk.com/id631833072\n"
        "🏢 GROUP: club229320501"
    )

@bot.on.message(text="/stats")
async def stats_handler(message: Message):

    user = await get_user(message.from_id)

    await message.answer(
        f"📊 СТАТИСТИКА\n\n"
        f"🆔 ID: {message.from_id}\n"
        f"🎭 ROLE: {user['role']}\n"
        f"⚠ WARNS: {user['warns']}\n"
        f"🔇 MUTE: {'YES' if user['muted'] else 'NO'}\n"
        f"🚫 BAN: {'YES' if user['banned'] else 'NO'}\n"
        f"📛 NICK: {user['nick'] if user['nick'] else 'NONE'}"
    )

@bot.on.message(text="/getid")
async def getid_handler(message: Message):

    await message.answer(
        f"🆔 YOUR ID: {message.from_id}"
    )

# ================= WARN =================

@bot.on.message(text="/warn <id> <reason>")
async def warn_handler(message: Message, id: int, reason: str):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ НЕТ ДОСТУПА")

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
        f"⚠ USER {id} GOT WARN\n"
        f"📝 REASON: {reason}"
    )

@bot.on.message(text="/unwarn <id>")
async def unwarn_handler(message: Message, id: int):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET warns = CASE WHEN warns > 0 THEN warns - 1 ELSE 0 END WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(f"✅ WARN REMOVED FROM {id}")

@bot.on.message(text="/getwarn <id>")
async def getwarn_handler(message: Message, id: int):

    user = await get_user(id)

    await message.answer(
        f"⚠ WARNS: {user['warns']}"
    )

# ================= MUTE =================

@bot.on.message(text="/mute <id>")
async def mute_handler(message: Message, id: int):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET muted = 1 WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(
        f"🔇 USER {id} MUTED"
    )

@bot.on.message(text="/unmute <id>")
async def unmute_handler(message: Message, id: int):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET muted = 0 WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(
        f"🔊 USER {id} UNMUTED"
    )

@bot.on.message(text="/getmute <id>")
async def getmute_handler(message: Message, id: int):

    user = await get_user(id)

    await message.answer(
        f"🔇 MUTE: {'YES' if user['muted'] else 'NO'}"
    )

# ================= BAN =================

@bot.on.message(text="/ban <id>")
async def ban_handler(message: Message, id: int):

    if not await has_role(message.from_id, "senmoder"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET banned = 1 WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(
        f"🚫 USER {id} BANNED"
    )

@bot.on.message(text="/unban <id>")
async def unban_handler(message: Message, id: int):

    if not await has_role(message.from_id, "senmoder"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET banned = 0 WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(
        f"✅ USER {id} UNBANNED"
    )

# ================= ROLE SYSTEM =================

@bot.on.message(text="/addmoder <id>")
async def addmoder_handler(message: Message, id: int):

    if not await has_role(message.from_id, "senmoder"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    await set_role(id, "moder")

    await message.answer(
        f"✅ USER {id} IS MODERATOR"
    )

@bot.on.message(text="/addsenmoder <id>")
async def addsenmoder_handler(message: Message, id: int):

    if not await has_role(message.from_id, "admin"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    await set_role(id, "senmoder")

    await message.answer(
        f"✅ USER {id} IS SEN MODERATOR"
    )

@bot.on.message(text="/addadmin <id>")
async def addadmin_handler(message: Message, id: int):

    if not await has_role(message.from_id, "senadmin"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    await set_role(id, "admin")

    await message.answer(
        f"✅ USER {id} IS ADMIN"
    )

@bot.on.message(text="/addsenadm <id>")
async def addsenadm_handler(message: Message, id: int):

    if not await has_role(message.from_id, "owner"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    await set_role(id, "senadmin")

    await message.answer(
        f"✅ USER {id} IS SEN ADMIN"
    )

@bot.on.message(text="/addowner <id>")
async def addowner_handler(message: Message, id: int):

    if not await has_role(message.from_id, "zam"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    await set_role(id, "owner")

    await message.answer(
        f"✅ USER {id} IS OWNER"
    )

@bot.on.message(text="/addzam <id>")
async def addzam_handler(message: Message, id: int):

    if not await has_role(message.from_id, "dev"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    await set_role(id, "zam")

    await message.answer(
        f"✅ USER {id} IS ZAM"
    )

@bot.on.message(text="/adddev <id>")
async def adddev_handler(message: Message, id: int):

    if message.from_id != OWNER_ID:
        return await message.answer("❌ ONLY OWNER")

    await set_role(id, "dev")

    await message.answer(
        f"🔥 USER {id} IS DEV"
    )

# ================= NICK SYSTEM =================

@bot.on.message(text="/setnick <id> <nick>")
async def setnick_handler(message: Message, id: int, nick: str):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET nick = ? WHERE id = ?",
            (nick, id)
        )

        await db.commit()

    await message.answer(
        f"📛 USER {id} NICK -> {nick}"
    )

@bot.on.message(text="/removenick <id>")
async def removenick_handler(message: Message, id: int):

    if not await has_role(message.from_id, "moder"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "UPDATE users SET nick = '' WHERE id = ?",
            (id,)
        )

        await db.commit()

    await message.answer(
        f"✅ NICK REMOVED"
    )

@bot.on.message(text="/getnick <id>")
async def getnick_handler(message: Message, id: int):

    user = await get_user(id)

    await message.answer(
        f"📛 NICK: {user['nick'] if user['nick'] else 'NONE'}"
    )

# ================= STAFF =================

@bot.on.message(text="/staff")
async def staff_handler(message: Message):

    async with aiosqlite.connect("database.db") as db:

        async with db.execute(
            "SELECT id, role FROM users WHERE role != 'user'"
        ) as cursor:

            rows = await cursor.fetchall()

    if not rows:
        return await message.answer("❌ STAFF EMPTY")

    text = "👮 STAFF LIST\n\n"

    for row in rows:
        text += f"ID: {row[0]} | ROLE: {row[1]}\n"

    await message.answer(text)

# ================= FILTER =================

@bot.on.message(text="/addword <word>")
async def addword_handler(message: Message, word: str):

    if not await has_role(message.from_id, "dev"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "INSERT INTO banwords(word) VALUES(?)",
            (word.lower(),)
        )

        await db.commit()

    await message.answer(
        f"✅ WORD {word} ADDED"
    )

@bot.on.message(text="/delword <word>")
async def delword_handler(message: Message, word: str):

    if not await has_role(message.from_id, "dev"):
        return await message.answer("❌ НЕТ ДОСТУПА")

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "DELETE FROM banwords WHERE word = ?",
            (word.lower(),)
        )

        await db.commit()

    await message.answer(
        f"✅ WORD {word} REMOVED"
    )

# ================= MESSAGE FILTER =================

@bot.on.message()
async def filter_system(message: Message):

    if not message.text:
        return

    text = message.text.lower()

    async with aiosqlite.connect("database.db") as db:

        async with db.execute(
            "SELECT word FROM banwords"
        ) as cursor:

            rows = await cursor.fetchall()

    words = [row[0] for row in rows]

    for word in words:

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
