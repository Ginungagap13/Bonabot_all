import re
import random
from pathlib import Path
from typing import Optional, Tuple

from telegram import (
    Update,
    InputFile,
    MessageEntity,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

import settings
import db

# Инициализируем БД
db.init_db()

# Регулярка: ровно 6 символов, A‑Z и 0‑9
CODE_RE = re.compile(r"^[A-Z0-9]{6}$")

async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь фото + ID (6 символов.) в одном сообщении."
    )

# ===================== 1️⃣ Обработка сообщения с фото+кодом =====================
async def photo_with_code_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # 1. Проверяем, есть ли фотография
    if not msg.photo:
        await msg.reply_text("❌ В сообщении должна быть фотография.")
        return

    # 2. Берём последний вариант фото (максимальное разрешение)
    photo_file_id = msg.photo[-1].file_id

    # 3. Извлекаем текстовое сообщение (непосредственно после фото)
    if not msg.caption:
        await msg.reply_text("❌ В сообщении должен быть код.")
        return
    caption = msg.caption.strip().upper()

    # 4. Проверяем формат кода
    if not CODE_RE.fullmatch(caption):
        await msg.reply_text(
            "❌ Код должен состоять ровно из 6 символов: A‑Z и цифры 0‑9."
        )
        return

    # 5. Сохраняем в БД
    db.add_message(
        chat_id=msg.chat.id,
        user_id=msg.from_user.id,
        username=msg.from_user.username or "",
        photo_file_id=photo_file_id,
        code=caption,
    )

    await msg.reply_text("✅ Сообщение принято!")

# ===================== 2️⃣ Владелец: просмотр всех сообщений =====================
async def list_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.OWNER_ID:
        return

    rows = db.list_messages()
    if not rows:
        await update.message.reply_text("📭 Нет записей.")
        return

    for r in rows[:20]:  # лимитируем на 20 для читаемости
        txt = f"🆔 {r['id']} | 👤 @{r['username']} | 📅 {r['ts']}\n"
        txt += f"🔢 Код: *{r['code']}*\n"
        await update.message.reply_text(txt, parse_mode="Markdown")

# ===================== 3️⃣ Владелец: выбор победителя (рандомайзер) =====================
async def draw_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.OWNER_ID:
        return

    # Формат команды: /draw <число_победителей> <ID сообщения>
    args = update.message.text.split()
    if len(args) != 3:
        await update.message.reply_text("⚠️ Пример: /draw 3 42")
        return
    try:
        count = int(args[1])
        msg_id = int(args[2])
    except ValueError:
        await update.message.reply_text("❌ Неверный формат чисел.")
        return

    # Получаем всех пользователей, которые отправили фото к этому сообщению
    with db.get_conn() as conn:
        rows = list(conn.execute(
            "SELECT DISTINCT user_id, username FROM messages WHERE id = ?", (msg_id,)
        ))

    if not rows:
        await update.message.reply_text("❌ Ничего не найдено.")
        return

    users = [(r["user_id"], r["username"]) for r in rows]
    winners = random.sample(users, min(count, len(users)))

    txt = f"🏆 Результат розыгрыша (ID сообщения {msg_id})\n"
    for i, (uid, uname) in enumerate(winners, 1):
        txt += f"{i}. @{uname} (ID: {uid})\n"
        db.add_winner(msg_id, uid, uname)

    await update.message.reply_text(txt)

# ===================== 4️⃣ Владелец: ответы пользователям =====================
async def reply_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings.OWNER_ID:
        return

    # /reply <user_id> <текст>
    args = update.message.text.split(maxsplit=2)
    if len(args) != 3:
        await update.message.reply_text("⚠️ Пример: /reply 123456 Hello!")
        return
    try:
        target_user = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Неверный ID пользователя.")
        return

    text = args[2]
    await update.effective_chat.send_message(text, reply_to_message_id=None,
                                             parse_mode="Markdown")
    await update.message.reply_text(f"✅ Ответ отправлен пользователю {target_user}")

# ===================== Запуск ==========================================
if __name__ == "__main__":
    app = ApplicationBuilder().token(settings.TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("draw", draw_cmd))
    app.add_handler(CommandHandler("reply", reply_cmd))

    # Обработка фото+код
    photo_filter = (
        filters.PHOTO & ~filters.COMMAND & filters.Caption
    )
    app.add_handler(MessageHandler(photo_filter, photo_with_code_handler))

    print("🚀 Бот запущен. Ожидание сообщений...")
    app.run_polling()
