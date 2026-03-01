import os
import logging
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# ========== Render-এর জন্য Web Server (বটকে জাগিয়ে রাখতে) ==========
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    # Render সাধারণত 10000 বা নির্দিষ্ট পোর্টে রান করে
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ========== কনফিগারেশন (Environment Variable থেকে নেওয়া) ==========
# Render-এর Settings > Environment Variables-এ BOT_TOKEN নামে আপনার টোকেনটি সেভ করবেন
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE") 
CHANNEL_USERNAME = "@allVideodownloader004" 
DOWNLOAD_DIR = "downloads"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# লগিং সেটআপ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== চ্যানেল মেম্বারশিপ চেক ==========
async def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

# ========== স্টার্ট কমান্ড ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        await update.message.reply_text(
            f"📺 এই বট ব্যবহার করতে হলে আমাদের চ্যানেলে জয়েন করতে হবে:\n{CHANNEL_USERNAME}\n\nজয়েন করার পর আবার চেষ্টা করুন।"
        )
        return
    await update.message.reply_text(
        f"👋 হ্যালো {update.effective_user.first_name}!\n"
        "আমি একটি ভিডিও ডাউনলোডার বট। লিংক পাঠালে ভিডিও পাঠিয়ে দেব।"
    )

# ========== ভিডিও ডাউনলোড ফাংশন ==========
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    if not await is_member(update, context):
        await update.message.reply_text("❌ আগে চ্যানেলে জয়েন করুন!")
        return

    status_msg = await update.message.reply_text("⏳ ডাউনলোড শুরু হয়েছে...")
    file_path = None
    try:
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'format': 'best[ext=mp4]/best',
            'quiet': True,
        }
        
        loop = asyncio.get_running_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            file_path = ydl.prepare_filename(info)

            # এক্সটেনশন চেক
            if not os.path.exists(file_path):
                base, _ = os.path.splitext(file_path)
                for ext in ['.mp4', '.mkv', '.webm']:
                    if os.path.exists(base + ext):
                        file_path = base + ext
                        break

        await status_msg.edit_text("✅ ডাউনলোড শেষ! এখন পাঠানো হচ্ছে...")
        with open(file_path, 'rb') as f:
            await update.message.reply_video(f, supports_streaming=True)

        os.remove(file_path)
        await status_msg.delete()

    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text("❌ সমস্যা হয়েছে। লিংকটি সঠিক কিনা চেক করুন।")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ========== মেসেজ হ্যান্ডলার ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if url.startswith(('http://', 'https://')):
        await download_video(update, context, url)
    else:
        await update.message.reply_text("⚠️ দয়া করে সঠিক লিংক দিন।")

# ========== মেইন ফাংশন ==========
def main():
    # সার্ভার চালু করা
    keep_alive()
    
    # বট সেটআপ
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 বট এবং সার্ভার চালু হয়েছে...")
    app_bot.run_polling()

if __name__ == "__main__":
    main()
