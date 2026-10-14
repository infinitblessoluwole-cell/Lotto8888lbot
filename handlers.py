import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import (
    get_or_create_user, get_favorites, add_favorite,
    add_learned, get_learned, get_daily_word
)
from words_data import WORDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id)
    
    await update.message.reply_text(
        f"👋 *Welcome, {user.first_name}!*\n\n"
        "I'm your vocabulary learning assistant.\n\n"
        "*Available Commands:*\n"
        "• /today — Get your daily word\n"
        "• /favorite `<word>` — Save a word with translation\n"
        "• /favorites — View saved words\n"
        "• /quiz — Take a vocabulary quiz\n"
        "• /review — Review previously learned words\n"
        "• /help — Show this message",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word, idx = get_daily_word(user_id, WORDS)
    
    text = (
        f"📖 *Word of the Day*\n\n"
        f"*{word['word']}*\n"
        f"_{word['translation']}_"
    )
    
    keyboard = [[
        InlineKeyboardButton("✅ Mark as Learned", callback_data=f"learn:{word['word']}"),
    ]]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/favorite word - translation`\n"
            "Example: `/favorite lucid - easy to understand`",
            parse_mode="Markdown"
        )
        return
    
    raw = " ".join(context.args)
    if " - " not in raw:
        await update.message.reply_text(
            "Please use format: `/favorite word - translation`",
            parse_mode="Markdown"
        )
        return
    
    word, translation = raw.split(" - ", 1)
    word = word.strip()
    translation = translation.strip()
    
    if add_favorite(user_id, word, translation):
        await update.message.reply_text(f"⭐ Saved: *{word}*\n_{translation}_", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ *{word}* is already in your favorites.")


async def favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    favs = get_favorites(user_id)
    
    if not favs:
        await update.message.reply_text("You haven't saved any words yet. Use `/favorite word - translation`", parse_mode="Markdown")
        return
    
    lines = [f"⭐ *Your Favorites* ({len(favs)} words)\n"]
    for i, f in enumerate(favs[:15], 1):
        lines.append(f"{i}. *{f['word']}* — _{f['translation']}_")
    
    if len(favs) > 15:
        lines.append(f"\n...and {len(favs) - 15} more.")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a multiple-choice quiz from the word pool."""
    user_id = update.effective_user.id
    get_or_create_user(user_id)
    
    # Pick 1 correct word + 3 distractors
    correct = random.choice(WORDS)
    others = [w for w in WORDS if w["word"] != correct["word"]]
    distractors = random.sample(others, min(3, len(others)))
    
    options = [correct["translation"]] + [d["translation"] for d in distractors]
    random.shuffle(options)
    
    # Store correct answer in context for callback validation
    context.user_data["quiz_answer"] = correct["translation"]
    context.user_data["quiz_word"] = correct["word"]
    
    keyboard = []
    for opt in options:
        keyboard.append([InlineKeyboardButton(opt[:50], callback_data=f"quiz:{opt}")])
    
    await update.message.reply_text(
        f"🧠 *Quiz Time*\n\nWhat does *{correct['word']}* mean?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    learned = get_learned(user_id, limit=10)
    
    if not learned:
        await update.message.reply_text(
            "You haven't marked any words as learned yet. "
            "Use `/today` and tap ✅ to track progress.",
            parse_mode="Markdown"
        )
        return
    
    lines = [f"📚 *Review ({len(learned)} words)*\n"]
    for w in learned:
        lines.append(f"• *{w['word']}* — _{w['translation']}_")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data.startswith("learn:"):
        word_str = data.split(":", 1)[1]
        # Find translation in pool
        match = next((w for w in WORDS if w["word"] == word_str), None)
        if match:
            add_learned(user_id, match["word"], match["translation"])
            await query.edit_message_text(
                f"✅ *{match['word']}* marked as learned!\n"
                f"_{match['translation']}_",
                parse_mode="Markdown"
            )
    
    elif data.startswith("quiz:"):
        answer = data.split(":", 1)[1]
        correct = context.user_data.get("quiz_answer")
        word = context.user_data.get("quiz_word", "the word")
        
        if answer == correct:
            # Add to learned automatically
            match = next((w for w in WORDS if w["word"] == word), None)
            if match:
                add_learned(user_id, match["word"], match["translation"])
            await query.edit_message_text(f"🎉 Correct! *{word}* means _{correct}_", parse_mode="Markdown")
        else:
            await query.edit_message_text(
                f"❌ Not quite. *{word}* means _{correct}_.",
                parse_mode="Markdown"
            )
