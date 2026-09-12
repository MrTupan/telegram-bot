import os
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------- CONFIGURATION -----------------
BOT_TOKEN = "8713395098:AAHIb6JVL5IjKtcEDmAt_j-lucnZoIH__7c"

# Numerical IDs usually start with -100 for supergroups and channels
CHANNEL_ID = -1001771046909   # Replace with your Channel ID
GROUP_ID = -1001790217091     # Replace with your Group ID

CHANNEL_LINK = "https://t.me/Tupan_Bypass"
GROUP_LINK = "https://t.me/TUPAN_FEEDBACKS"

REQUIRED_INVITES = 5
FILE_PATH = "potato_graphics.zip"  # Path to the file you want to send
ACTIVATION_TEXT = (
    "🎉 **Congratulations! You have completed all steps.**\n\n"
    "Here is your file. Follow these steps to activate:\n"
    "1. Extract the archive.\n"
    "2. Run the installer.\n"
    "3. Use activation key: `XXXX-YYYY-ZZZZ`"
)
# --------------------------------------------------

DB_NAME = "bot_data.db"


async def init_db():
    """Initialize the SQLite database to store user invites."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                user_id INTEGER PRIMARY KEY,
                invite_count INTEGER DEFAULT 0
            )
        """)
        await db.commit()


async def is_member(bot, chat_id: int, user_id: int) -> bool:
    """Check if the user is a member/admin of a chat."""
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


async def get_invite_count(user_id: int) -> int:
    """Get the number of friends added by the user."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT invite_count FROM invites WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# 1. Start Command Handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    invites = await get_invite_count(user_id)

    welcome_text = (
        f"👋 Hello {update.effective_user.first_name}!\n\n"
        "To receive your download and activation guide, please complete these steps:\n\n"
        f"1️⃣ Join our **Channel**\n"
        f"2️⃣ Join our **Group**\n"
        f"3️⃣ Add **{REQUIRED_INVITES} friends** directly into the group\n\n"
        f"📊 **Your progress:** {invites}/{REQUIRED_INVITES} friends added.\n\n"
        "Click the buttons below to join, and then click **Verify** when done."
    )

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("👥 Join Group", url=GROUP_LINK)],
        [InlineKeyboardButton("🔄 Verify & Claim File", callback_data="verify_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")


# 2. Tracking Added Members in Group
async def track_group_adds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detects when someone manually adds users to the group."""
    message = update.message
    if not message or not message.new_chat_members:
        return

    # Ensure this update is coming from your specific group
    if message.chat.id != GROUP_ID:
        return

    inviter = message.from_user
    # Count how many members were added (excluding bot accounts)
    added_count = sum(1 for m in message.new_chat_members if not m.is_bot and m.id != inviter.id)

    if added_count > 0:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
                INSERT INTO invites (user_id, invite_count) 
                VALUES (?, ?) 
                ON CONFLICT(user_id) DO UPDATE SET invite_count = invite_count + ?
            """, (inviter.id, added_count, added_count))
            await db.commit()


# 3. Verification Handler
async def verify_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    bot = context.bot

    # Step-by-step checks
    joined_channel = await is_member(bot, CHANNEL_ID, user_id)
    joined_group = await is_member(bot, GROUP_ID, user_id)
    invites = await get_invite_count(user_id)

    missing = []
    if not joined_channel:
        missing.append("❌ You haven't joined the **Channel** yet.")
    if not joined_group:
        missing.append("❌ You haven't joined the **Group** yet.")
    if invites < REQUIRED_INVITES:
        missing.append(f"❌ You have added **{invites}/{REQUIRED_INVITES}** friends to the group.")

    if missing:
        msg = "⚠️ **Requirements not met:**\n\n" + "\n".join(missing)
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("👥 Join Group", url=GROUP_LINK)],
            [InlineKeyboardButton("🔄 Check Again", callback_data="verify_tasks")]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        # User passed all requirements
        await query.edit_message_text("✅ All steps completed! Sending your file now...")
        
        # Send the file
        if os.path.exists(FILE_PATH):
            with open(FILE_PATH, "rb") as f:
                await bot.send_document(
                    chat_id=user_id,
                    document=f,
                    caption=ACTIVATION_TEXT,
                    parse_mode="Markdown"
                )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=ACTIVATION_TEXT,
                parse_mode="Markdown"
            )


def main():
    import asyncio
    asyncio.run(init_db())

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$"))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_group_adds))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
