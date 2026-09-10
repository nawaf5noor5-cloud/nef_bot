import os
import logging
import random
import asyncio
import theading

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

# الأسواق المتاحة والمدد الزمنية
MARKETS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "Gold", "Silver", "Tesla", "Apple", "Amazon", "Smarty", "Football"]
TIMEFRAMES = ["30 ثانية", "1 دقيقة", "2 دقيقة", "5 دقائق"]

user_selections = {}

# أمر البدء
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_authorized(user_id):
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "➕ **إضافة مستخدم:**\nالرجاء إرسال **User ID** الخاص بالمستخدم الجديد في رسالة الآن:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

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

# معالج الأزرار والتفاعل
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if not is_authorized(user_id):
        await query.edit_message_text("❌ غير مَصرح لك استخدام هذا البوت.")
        return

    data = query.data

    if data == "choose_market":
        keyboard = [[InlineKeyboardButton(market, callback_data=f"market_{market}")] for market in MARKETS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📊 **اختر السوق:**\nالرجاء اختيار السوق أو الأصل المطلوب:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if data == "admin_panel":
        await query.edit_message_text(
            "⚙️ **لوحة إدارة المستخدمين:**\nالمستخدمين المصرح لهم مفعلين وجاهزون.",
            parse_mode="Markdown"
        )
        return

    if data.startswith("market_"):
        market = data.split("_", 1)[1]
        user_selections[user_id] = {"market": market}
        
        keyboard = [[InlineKeyboardButton(tf, callback_data=f"tf_{tf}")] for tf in TIMEFRAMES]
        keyboard.append([InlineKeyboardButton("رجوع", callback_data="choose_market")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📈 لقد اخترت السوق: **{market}**\nالآن اختر المدة الزمنية للصفقة:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if data.startswith("tf_"):
        tf = data.split("_", 1)[1]
        if user_id in user_selections:
            user_selections[user_id]["tf"] = tf
        
        market = user_selections.get(user_id, {}).get("market", "EURUSD")
        
        # محاكاة التقرير الفني المتقدم وقراءة المؤشرات
        decision = random.choice(["صعود (CALL)", "هبوط (PUT)"])
        accuracy = random.randint(75, 95)
        
        report = (
            f"📊 **تقرير التحليل الفني المتقدم**\n\n"
            f"🔹 السوق / الأصل: {market}\n"
            f"⏱ المدة الزمنية: {tf}\n"
            f"📈 نسبة وقوة التحليل: %{accuracy} ({'صعود قوي' if 'صعود' in decision else 'هبوط قوي'})\n"
            f"🟢 القرار النهائي: {decision}\n\n"
            f"📉 **قراءة أقوى المؤشرات الفنية:**\n"
            f"• مؤشر القوة النسبية (RSI): {random.randint(40, 60)} (منطقة الحياد والسيولة)\n"
            f"• مؤشر الماكد (MACD): تقاطع إيجابي يدعم الاتجاه\n"
            f"• بولينجر باند (Bollinger Bands): ملامسة الحد وتأكيد الارتداد\n"
            f"• المتوسطات المتحركة (Moving Averages): فوق المتوسطات السريعة\n\n"
            f"⚠️ **تنبيه:** التداول ينطوي على مخاطر، يرجى الالتزام بإدارة رأس المال."
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحليل سوق جديد", callback_data="choose_market")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")
        return

# تشغيل خادم سرفر بسيط لـ Render
app_flask = Flask(__name__)
@app_flask.route("/")
def index():
    return "Bot is running!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

def main():
    if not TOKEN:
        log.error("No token found!")
        return

    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    # تشغيل سيرفر الويب في خلفية منفصلة
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    log.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
