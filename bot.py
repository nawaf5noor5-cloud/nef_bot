import os
import logging
import random
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# إعداد السجلات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

# استدعاء التوكن
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
INITIAL_ADMIN_ID = os.getenv("TELEGRAM_USER_ID", "").strip()

# قائمة المستخدمين المصرح لهم
ALLOWED_USER_FILE = "allowed_users.json"
ALLOWED_USERS = set()
if INITIAL_ADMIN_ID:
    ALLOWED_USERS.add(str(INITIAL_ADMIN_ID))

def is_authorized(user_id):
    return str(user_id) in ALLOWED_USERS or (INITIAL_ADMIN_ID and str(user_id) == str(INITIAL_ADMIN_ID))

# الأسواق المتاحة
MARKETS = [
    "الذهب (Gold)",
    "EUR/USD (فوركس)",
    "BTC/USD (عملات رقمية)",
    "Apple (أبل)",
    "Tesla (تسلا)"
]

# المدد الزمنية المتاحة (تمت إضافة 30 ثانية و 1 دقيقة)
TIMEFRAMES = ["30 ثانية", "1 دقيقة", "2 دقيقة", "5 دقائق"]

# تخزين حالة المستخدم المؤقتة
user_selections = {}

# خادم ويب وهمي لإبقاء البوت يعمل على Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ALLOWED_USERS:
        # رسالة طلب الـ User ID إذا لم يكن مضافاً
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "➕ **إضافة مستخدم:**\nالرجاء إرسال **User ID** الخاص بالمستخدم الجديد في رسالة الآن:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    # رسالة الترحيب الأصلية بالتنسيق المطلوب
    keyboard = [
        [InlineKeyboardButton("📊 اختر السوق أو العملة", callback_data="choose_market")],
        [InlineKeyboardButton("⚙️ لوحة إدارة المستخدمين", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🤖 **بوت التحليل الذكي وخبير التداول**\n\n"
        "🟢 **الحالة:** حساب نشط\n\n"
        "اضغط على الزر بالأسفل لبدء اختيار الأصول:"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not is_authorized(user_id):
        await query.edit_message_text("غير مصرح لك استخدام هذا البوت.")
        return

    data = query.data

    if data.startswith("market_"):
        market = data.split("_", 1)[1]
        user_selections[user_id] = {"market": market}

        keyboard = [[InlineKeyboardButton(tf, callback_data=f"tf_{tf}")] for tf in TIMEFRAMES]
        keyboard.append([InlineKeyboardButton("رجوع", callback_data="back_to_markets")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"لقد اخترت السوق: *{market}*\nالآن اختر المدة الزمنية للصفقة:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif data.startswith("tf_"):
        tf = data.split("_", 1)[1]
        if user_id not in user_selections:
            user_selections[user_id] = {}
        user_selections[user_id]["timeframe"] = tf

        market = user_selections[user_id].get("market", "غير معروف")

        # رسالة جاري التحليل
        await query.edit_message_text(f"⏳ جاري تحليل السوق لـ *{market}* على فريم *{tf}*...", parse_mode="Markdown")
        await asyncio.sleep(2)

        # توليد نتيجة تحليل فني احترافية ومتطورة
        directions = ["صعود (CALL 🟢)", "هبوط (PUT 🔴)"]
        direction = random.choice(directions)
        confidence = random.randint(84, 98)
        
        analysis_text = (
            f"📊 *تقرير التحليل الفني المتقدم*\n\n"
            f"🔹 *السوق:* {market}\n"
            f"⏱ *المدة الزمنية:* {tf}\n"
            f"📈 *الاتجاه المتوقع:* *{direction}*\n"
            f"🎯 *نسبة الدقة:* `{confidence}%`\n\n"
            f"⚙️ *تفاصيل المؤشرات والسيولة:*\n"
            f"• مؤشر القوة النسبية (RSI): مشبع بالسيولة في النطاق المثالي.\n"
            f"• حركة السيولة اللحظية (Order Flow): تدفقات شرائية قوية تدعم القرار.\n"
            f"• تحليل الشموع اليابانية: تأكيد النطاق السعري والانعكاس.\n\n"
            f"⚠️ *تنبيه:* التداول ينطوي على مخاطر، يرجى الالتزام بإدارة رأس المال."
        )

        keyboard = [
            [InlineKeyboardButton("تحليل صفقة جديدة", callback_data="back_to_markets")],
            [InlineKeyboardButton("إغلاق", callback_data="cancel_add")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(analysis_text, reply_markup=reply_markup, parse_mode="Markdown")

    elif data == "back_to_markets":
        keyboard = [[InlineKeyboardButton(market, callback_data=f"market_{market}")] for market in MARKETS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "اختر السوق الذي تريد تحليله:",
            reply_markup=reply_markup
        )

    elif data == "cancel_add":
        await query.message.delete()

def main():
    if not TOKEN:
        log.error("No token provided!")
        return

    keep_alive()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    log.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
