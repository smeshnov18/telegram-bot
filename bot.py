import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook

from config import BOT_TOKEN, MODERATOR_ID
from questions import QUESTIONS

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ===== WEBHOOK SETTINGS (Render Web Service) =====
# В Render добавь env var WEBHOOK_HOST = https://<your-service>.onrender.com
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # например: https://telegram-bot-abc123.onrender.com
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", "10000"))  # Render автоматически задаёт PORT

# ===== BOT LOGIC =====

users = {}

def moderator_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Верно", callback_data=f"ok:{user_id}"),
        types.InlineKeyboardButton("❌ Неверно", callback_data=f"no:{user_id}")
    )
    return kb

def restart_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔁 Начать заново", callback_data="restart"))
    return kb

def start_quiz(user_id: int) -> None:
    users[user_id] = {"question": 0, "waiting_review": False}

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
        "🔁 Начинаем заново!\n\n" + QUESTIONS[0]
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith(("ok", "no")))
async def review(callback: types.CallbackQuery):
    action, user_id = callback.data.split(":")
    user_id = int(user_id)

    if user_id not in users:
        await callback.answer()
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

# ===== WEBHOOK LIFECYCLE =====

async def on_startup(dp: Dispatcher):
    # Сбрасываем старые настройки и ставим webhook заново
    await bot.delete_webhook(drop_pending_updates=True)
    if not WEBHOOK_HOST:
        raise RuntimeError(
            "WEBHOOK_HOST is not set. Add it in Render env vars, e.g. https://your-service.onrender.com"
        )
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp: Dispatcher):
    await bot.delete_webhook()

if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
        skip_updates=True,
    )
