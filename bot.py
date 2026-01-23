from aiogram import Bot, Dispatcher, executor, types
from config import BOT_TOKEN, MODERATOR_ID
from questions import QUESTIONS

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Храним состояние пользователя
users = {}

def moderator_keyboard(user_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Верно", callback_data=f"ok:{user_id}"),
        types.InlineKeyboardButton("❌ Неверно", callback_data=f"no:{user_id}")
    )
    return kb

def restart_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔁 Начать заново, пидор!", callback_data="restart"))
    return kb

def start_quiz(user_id):
    users[user_id] = {
        "question": 0,
        "waiting_review": False
    }

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    start_quiz(message.from_user.id)
    await message.answer(QUESTIONS[0])

@dp.message_handler()
async def handle_answer(message: types.Message):
    user_id = message.from_user.id

    if user_id not in users:
        return

    if users[user_id]["waiting_review"]:
        return

    q_index = users[user_id]["question"]
    users[user_id]["waiting_review"] = True

    await bot.send_message(
        MODERATOR_ID,
        f"❓ Вопрос {q_index + 1}:\n{QUESTIONS[q_index]}\n\n✍️ Ответ:\n{message.text}",
        reply_markup=moderator_keyboard(user_id)
    )

    await message.answer("Ответ отправлен на проверку ⏳")

@dp.callback_query_handler(lambda c: c.data == "restart")
async def restart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    start_quiz(user_id)

    await bot.send_message(
        user_id,
        "🔁 Начинаем заново, пидор!\n\n" + QUESTIONS[0]
    )

    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith(("ok", "no")))
async def review(callback: types.CallbackQuery):
    action, user_id = callback.data.split(":")
    user_id = int(user_id)

    if user_id not in users:
        return

    if action == "ok":
        users[user_id]["question"] += 1
        users[user_id]["waiting_review"] = False

        if users[user_id]["question"] < len(QUESTIONS):
            await bot.send_message(
                user_id,
                "✅ Верно!\n\n" + QUESTIONS[users[user_id]["question"]]
            )
        else:
            await bot.send_message(
                user_id,
                "🎉 Все вопросы завершены!",
                reply_markup=restart_keyboard()
            )
            del users[user_id]

    else:
        users[user_id]["waiting_review"] = False
        await bot.send_message(
            user_id,
            "❌ Ответ неверный. Подумай ещё раз."
        )

    await callback.answer()

import asyncio
from aiogram.utils.exceptions import TerminatedByOtherGetUpdates

async def on_startup(dp):
    # на всякий случай отключаем webhook
    await bot.delete_webhook(drop_pending_updates=True)

async def main():
    while True:
        try:
            executor.start_polling(
                dp,
                skip_updates=True,
                on_startup=on_startup
            )
        except TerminatedByOtherGetUpdates:
            # если Telegram говорит "есть другой getUpdates"
            await asyncio.sleep(5)
        except Exception:
            # защита от бесконечных падений
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())

