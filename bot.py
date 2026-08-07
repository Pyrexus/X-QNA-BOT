"""
QNA Counter Bot
---------------
Single-file Telegram bot (python-telegram-bot 22.8, polling).

What it does:
1. Owner sends /live in bot DM.
2. Bot posts a formatted "NGL x SHIP SESSION" message to CHANNEL_1
   with two link buttons, ending in a "Number Of QNA Answered ➜ 00" line.
3. Every time a new message/post appears in CHANNEL_2 (the QNA answers
   channel), the bot bumps the counter by +1 and edits the live post
   in CHANNEL_1 to show the new number.

No database — just a small local JSON file (data.json) that stores the
current count and the message_id of the active live post, so the count
survives restarts on Railway.
"""

import json
import logging
import os
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# --------------------------------------------------------------------------
# CONFIG — set these as environment variables (e.g. on Railway).
# --------------------------------------------------------------------------
BOT_TOKEN = "8834146619:AAHjkjw0Rbu_0bYAoeewtT0hGr4f7Y2eZ-E"
OWNER_ID = 6798950954
CHANNEL_1_ID = -1003973011793  # main channel, gets the /live post
CHANNEL_2_ID = -1004436301107  # QNA answers channel, triggers the +1

NGL_LINK = "https://ngl.link/lilesh"
QNA_ANS_LINK = "https://t.me/QNAZENITH"

DATA_FILE = Path(__file__).parent / "data.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("qna-bot")

# --------------------------------------------------------------------------
# Tiny JSON-file "storage"
# --------------------------------------------------------------------------
def load_data() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            log.warning("data.json unreadable, starting fresh")
    return {"count": 0, "live_message_id": None}


def save_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data))


# --------------------------------------------------------------------------
# Bold-digit formatting: 0-9 -> 𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵
# --------------------------------------------------------------------------
BOLD_DIGIT_BASE = ord("𝟬")  # Mathematical Bold Digit Zero, U+1D7CE


def bold_number(n: int) -> str:
    s = str(n).zfill(2)  # always at least 2 digits: 00, 01 ... 10, 11 ... 100
    return "".join(chr(BOLD_DIGIT_BASE + int(d)) for d in s)


# --------------------------------------------------------------------------
# Message text builder
# --------------------------------------------------------------------------
def build_message(count: int) -> str:
    return (
        "╭━━━〔 🔥 𝗡𝗚𝗟 × 𝗦𝗛𝗜𝗣 𝗦𝗘𝗦𝗦𝗜𝗢𝗡 🔥 〕━━━╮\n\n"
        "<b>𝗢𝗰𝗮𝘆 𝘀𝗼 𝗜𝘁'𝘀 𝗳𝗶𝗻𝗮𝗹𝗹𝘆 𝘁𝗶𝗺𝗲 𝗳𝗼𝗿 𝗤𝗡𝗔... 😈</b>\n"
        "<blockquote>𝗚𝗼𝘁 𝘀𝗼𝗺𝗲𝘁𝗵𝗶𝗻𝗴 𝘆𝗼𝘂'𝘃𝗲 𝗮𝗹𝘄𝗮𝘆𝘀 𝘄𝗮𝗻𝘁𝗲𝗱 𝘁𝗼 𝗮𝘀𝗸? 👀</blockquote>\n"
        "<blockquote>💌 𝗣𝗲𝗿𝘀𝗼𝗻𝗮𝗹 𝗤𝘂𝗲𝘀𝘁𝗶𝗼𝗻𝘀?\n"
        "❤️ 𝗦𝗵𝗶𝗽 𝗺𝗲 𝘄𝗶𝘁𝗵 𝘀𝗼𝗺𝗲𝗼𝗻𝗲?\n"
        "🤫 𝗦𝗲𝗰𝗿𝗲𝘁𝘀?\n"
        "😂 𝗥𝗼𝗮𝘀𝘁𝘀?\n"
        "💭 𝗢𝗿 𝗷𝘂𝘀𝘁 𝗿𝗮𝗻𝗱𝗼𝗺 𝗰𝗵𝗮𝗼𝘀?</blockquote>\n"
        "<blockquote>𝗡𝗼 𝗹𝗶𝗺𝗶𝘁𝘀. 𝗔𝘀𝗸 𝗮𝗻𝘆𝘁𝗵𝗶𝗻𝗴. 😌</blockquote>\n"
        "<b>⏳ 𝗧𝗵𝗲 𝗹𝗶𝗻𝗸 𝘄𝗶𝗹𝗹 𝗯𝗲 𝗼𝗽𝗲𝗻 𝗳𝗼𝗿 𝗮 𝗹𝗶𝗺𝗶𝘁𝗲𝗱 𝘁𝗶𝗺𝗲, 𝘀𝗼 𝗱𝗼𝗻'𝘁 𝗺𝗶𝘀𝘀 𝗶𝘁!</b>\n"
        "╭──〔 💌 〕──╮ \n"
        f'    <a href="{NGL_LINK}">𝗡𝗚𝗟 𝗟𝗜𝗡𝗞</a>\n'
        "╰──〔 💌 〕──╯\n\n"
        "<blockquote>📢 𝗔𝗹𝗹 𝗿𝗲𝗽𝗹𝗶𝗲𝘀, 𝘀𝗵𝗶𝗽𝘀 &amp; 𝗿𝗲𝗮𝗰𝘁𝗶𝗼𝗻𝘀 𝘄𝗶𝗹𝗹 𝗯𝗲 𝗽𝗼𝘀𝘁𝗲𝗱 𝗶𝗻 𝘁𝗵𝗲 𝘀𝗽𝗲𝗰𝗶𝗮𝗹 𝗴𝗿𝗼𝘂𝗽👇👇</blockquote>\n\n"
        "╭──〔 🚀 〕──╮\n"
        f'   <a href="{QNA_ANS_LINK}">𝗝𝗢𝗜𝗡 𝗡𝗢𝗪</a>\n'
        "╰──〔 💌 〕──╯\n"
        "<b>𝗟𝗲𝘁'𝘀 𝘀𝗲𝗲 𝘄𝗵𝗼 𝘀𝗲𝗻𝗱𝘀 𝘁𝗵𝗲 𝗰𝗿𝗮𝘇𝗶𝗲𝘀𝘁 𝗺𝗲𝘀𝘀𝗮𝗴𝗲... 😈❤️‍🔥</b>\n"
        f"<blockquote><b>𝐍𝐮𝐦𝐛𝐞𝐫 𝐎𝐟 𝐐𝐍𝐀 𝐀𝐧𝐬𝐰𝐞𝐫𝐞𝐝 ➜ {bold_number(count)}</b></blockquote>\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    )


def build_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("𝗡𝗚𝗟 𝗟𝗶𝗻𝗸 🌚", url=NGL_LINK, style="primary"),
                InlineKeyboardButton("𝗤𝗡𝗔 𝗔𝗻𝘀 🌝", url=QNA_ANS_LINK, style="success"),
            ]
        ]
    )


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------
async def live_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user

    # owner-only, DM-only
    if msg.chat.type != "private" or user is None or user.id != OWNER_ID:
        return

    data = load_data()
    text = build_message(data["count"])
    
    try:
        sent = await context.bot.send_message(
            chat_id=CHANNEL_1_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_keyboard(),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
        
        data["live_message_id"] = sent.message_id
        save_data(data)
        await update.effective_message.reply_text(
            f"✅ Live post sent to channel 1. Current count: {data['count']:02d}"
        )
        
    except BadRequest as e:
        # This will tell you EXACTLY why Telegram is rejecting the message!
        await update.effective_message.reply_text(
            f"❌ Telegram rejected the message!\n\nReason: <code>{e.message}</code>",
            parse_mode=ParseMode.HTML
        )
        log.error("Telegram API BadRequest: %s", e.message)


async def on_channel_2_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    post = update.channel_post
    if post is None or post.chat.id != CHANNEL_2_ID:
        return

    data = load_data()
    data["count"] += 1

    if data.get("live_message_id"):
        try:
            await context.bot.edit_message_text(
                chat_id=CHANNEL_1_ID,
                message_id=data["live_message_id"],
                text=build_message(data["count"]),
                parse_mode=ParseMode.HTML,
                reply_markup=build_keyboard(),
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
        except Exception as e:  # message deleted, not modified, etc.
            log.warning("Could not edit live post: %s", e)

    save_data(data)
    log.info("Count bumped to %s", data["count"])


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Unhandled error", exc_info=context.error)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def main() -> None:
    if not BOT_TOKEN or not OWNER_ID or not CHANNEL_1_ID or not CHANNEL_2_ID:
        raise SystemExit(
            "Missing config. Set BOT_TOKEN, OWNER_ID, CHANNEL_1_ID, CHANNEL_2_ID env vars."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    # /live — owner-only, DM-only (check is done inside live_cmd)
    app.add_handler(CommandHandler("live", live_cmd))

    # Any new post in channel 2 -> bump counter
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, on_channel_2_post))

    app.add_error_handler(on_error)

    log.info("Bot starting (polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
