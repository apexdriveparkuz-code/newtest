import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "taxi_bot.db"

DRIVERS, LICENSES, CALLS, COMMENT = range(4)

MAIN_MENU = ReplyKeyboardMarkup(
    [["Natija kiritish"], ["Bugungi hisobot", "Umumiy hisobot"]],
    resize_keyboard=True,
)


def get_admin_ids() -> set[int]:
    raw_ids = os.getenv("ADMIN_IDS", "")
    admin_ids = set()
    for raw_id in raw_ids.split(","):
        raw_id = raw_id.strip()
        if raw_id.isdigit():
            admin_ids.add(int(raw_id))
    return admin_ids


def is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids()


def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                drivers_connected INTEGER NOT NULL,
                licenses_done INTEGER NOT NULL,
                calls_made INTEGER NOT NULL,
                comment TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_report(
    user_id: int,
    full_name: str,
    drivers_connected: int,
    licenses_done: int,
    calls_made: int,
    comment: str,
) -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            INSERT INTO reports (
                user_id,
                full_name,
                drivers_connected,
                licenses_done,
                calls_made,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                full_name,
                drivers_connected,
                licenses_done,
                calls_made,
                comment,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def fetch_today_rows() -> list[tuple]:
    today = datetime.now().date().isoformat()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return conn.execute(
            """
            SELECT full_name, drivers_connected, licenses_done, calls_made, comment, created_at
            FROM reports
            WHERE date(created_at) = ?
            ORDER BY created_at DESC
            """,
            (today,),
        ).fetchall()


def fetch_total_rows() -> list[tuple]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return conn.execute(
            """
            SELECT
                full_name,
                SUM(drivers_connected),
                SUM(licenses_done),
                SUM(calls_made),
                COUNT(*)
            FROM reports
            GROUP BY user_id, full_name
            ORDER BY SUM(drivers_connected) DESC, SUM(calls_made) DESC
            """
        ).fetchall()


def parse_number(text: str) -> int | None:
    text = text.strip()
    if not text.isdigit():
        return None
    return int(text)


def full_name(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "Noma'lum hodim"
    name_parts = [user.first_name, user.last_name]
    name = " ".join(part for part in name_parts if part)
    return name or user.username or str(user.id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Assalomu alaykum.\n\n"
        "Natijani kiritish uchun tugmani bosing. Admin bo'lsangiz, hisobotlarni ham shu yerdan ko'rasiz."
    )
    await update.message.reply_text(text, reply_markup=MAIN_MENU)


async def begin_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "Bugun nechta haydovchi ulandingiz? Faqat raqam yuboring.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DRIVERS


async def receive_drivers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = parse_number(update.message.text)
    if value is None:
        await update.message.reply_text("Iltimos, faqat raqam yuboring. Masalan: 5")
        return DRIVERS

    context.user_data["drivers_connected"] = value
    await update.message.reply_text("Nechta litsenziya qildingiz? Faqat raqam yuboring.")
    return LICENSES


async def receive_licenses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = parse_number(update.message.text)
    if value is None:
        await update.message.reply_text("Iltimos, faqat raqam yuboring. Masalan: 2")
        return LICENSES

    context.user_data["licenses_done"] = value
    await update.message.reply_text("Nechta odamga qo'ng'iroq qildingiz? Faqat raqam yuboring.")
    return CALLS


async def receive_calls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = parse_number(update.message.text)
    if value is None:
        await update.message.reply_text("Iltimos, faqat raqam yuboring. Masalan: 30")
        return CALLS

    context.user_data["calls_made"] = value
    await update.message.reply_text(
        "Izoh yozing. Agar izoh yo'q bo'lsa, `yo'q` deb yuboring.",
        parse_mode="Markdown",
    )
    return COMMENT


async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    comment = update.message.text.strip()
    user = update.effective_user

    save_report(
        user_id=user.id,
        full_name=full_name(update),
        drivers_connected=context.user_data["drivers_connected"],
        licenses_done=context.user_data["licenses_done"],
        calls_made=context.user_data["calls_made"],
        comment="" if comment.lower() in {"yo'q", "yoq", "yuq", "-"} else comment,
    )

    await update.message.reply_text(
        "Natija saqlandi. Rahmat.",
        reply_markup=MAIN_MENU,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Kiritish bekor qilindi.", reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def today_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Bu bo'lim faqat admin uchun.")
        return

    rows = fetch_today_rows()
    if not rows:
        await update.message.reply_text("Bugun hali natija kiritilmagan.")
        return

    total_drivers = sum(row[1] for row in rows)
    total_licenses = sum(row[2] for row in rows)
    total_calls = sum(row[3] for row in rows)

    lines = [
        "Bugungi hisobot",
        "",
        f"Ulangan haydovchilar: {total_drivers}",
        f"Litsenziyalar: {total_licenses}",
        f"Qo'ng'iroqlar: {total_calls}",
        "",
        "Hodimlar bo'yicha:",
    ]

    for name, drivers, licenses, calls, comment, created_at in rows:
        time_part = created_at[11:16]
        comment_part = f"\nIzoh: {comment}" if comment else ""
        lines.append(
            f"\n{name} ({time_part})\n"
            f"Haydovchi: {drivers} | Litsenziya: {licenses} | Qo'ng'iroq: {calls}"
            f"{comment_part}"
        )

    await update.message.reply_text("\n".join(lines))


async def total_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("Bu bo'lim faqat admin uchun.")
        return

    rows = fetch_total_rows()
    if not rows:
        await update.message.reply_text("Hali natija kiritilmagan.")
        return

    lines = ["Umumiy hisobot", ""]
    for name, drivers, licenses, calls, count in rows:
        lines.append(
            f"{name}\n"
            f"Haydovchi: {drivers} | Litsenziya: {licenses} | Qo'ng'iroq: {calls} | Hisobotlar: {count}\n"
        )

    await update.message.reply_text("\n".join(lines))


def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(".env faylida BOT_TOKEN yozilmagan.")

    init_db()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    app = Application.builder().token(token).build()

    conversation = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Natija kiritish$"), begin_report)],
        states={
            DRIVERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_drivers)],
            LICENSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_licenses)],
            CALLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_calls)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hisobot", today_report))
    app.add_handler(CommandHandler("umumiy", total_report))
    app.add_handler(conversation)
    app.add_handler(MessageHandler(filters.Regex("^Bugungi hisobot$"), today_report))
    app.add_handler(MessageHandler(filters.Regex("^Umumiy hisobot$"), total_report))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
