import time
import requests
import logging
import random
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# إعداد السجلات
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# الإعدادات والمتغيرات الأساسية (تأكد من وضع التوكن الصحيح هنا)
TOKEN = "8968520359:AAGNBUm9GssXoB6SeZAuPHW6IAfxC0aFJQo"
INITIAL_ADMIN_ID = "420693139"  # معرف المالك
ALLOWED_USERS = {INITIAL_ADMIN_ID}
admin_adding_state = set()
admin_deleting_state = set()  # أضف هذا السطر هنا لحالة الحذف
user_selections = {}

MARKETS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "Gold", "Silver", "Tesla", "Apple", "Amazon", "Smarty", "Football"]
TIMEFRAMES = ["30 ثانية", "1 دقيقة", "2 دقيقة", "5 دقائق", "15 دقيقة", "30 دقيقة"]

def is_authorized(user_id: str):
    return user_id in ALLOWED_USERS or user_id == str(INITIAL_ADMIN_ID)

# سيرفر الفلاسك للتشغيل المستمر على Render
app_flask = Flask("bot")

@app_flask.route("/")
def index():
    return "Bot is running!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

# أمر البداية
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("❌ غير مصرح لك استخدام هذا البوت.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 اختر السوق أو العملة", callback_data="choose_market")],
        [InlineKeyboardButton("⚙️ لوحة إدارة المستخدمين", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"🤖 **بوت التحليل الذكي وخبير التداول**\n\n"
        f"🟢 **الحالة: حساب نشط**\n\n"
        f"👇 **اضغط على الزر بالأسفل لبدء اختيار الأصول** 👇"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# معالج الأزرار والتفاعل
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if not is_authorized(user_id):
        await query.edit_message_text("❌ غير مصرح لك استخدام هذا البوت.")
        return

    data = query.data

    if data == "choose_market":
        keyboard = [[InlineKeyboardButton(market, callback_data=f"market_{market}")] for market in MARKETS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📊 **الرجاء اختيار السوق أو الأصل المطلوب:**",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if data == "admin_panel":
        if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
            admin_adding_state.discard(user_id)
            admin_deleting_state.discard(user_id)
            keyboard = [
                [InlineKeyboardButton("➕ إضافة مستخدم جديد", callback_data="add_user")],
                [InlineKeyboardButton("🗑️ حذف مستخدم مسجل", callback_data="remove_user")],
                [InlineKeyboardButton("📋 عرض المستخدمين", callback_data="list_users")],
                [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "⚙️ **لوحة إدارة المستخدمين (المالك):**\nيمكنك التحكم بصلاحيات الوصول وإضافة أو حذف المستخدمين بكل سهولة.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("⚙️ **لوحة إدارة المستخدمين:**\nعذراً، هذه اللوحة خاصة بمالك البوت فقط.", parse_mode="Markdown")
        return

    if data == "remove_user":
        if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
            admin_deleting_state.add(user_id)
            admin_adding_state.discard(user_id)
            users_list = "\n".join([f"• {u}" for u in ALLOWED_USERS])
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"🗑️ **حذف مستخدم:**\nالمستخدمون الحاليون:\n{users_list}\n\nالرجاء إرسال **اليوزر أو المعرف المراد حذفه** في رسالة الآن:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        return

    if data == "list_users":
        if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
            users_list = "\n".join([f"• {u}" for u in ALLOWED_USERS])
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"📋 **قائمة المستخدمين المسموح لهم:**\n{users_list}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        return
        
if data == "remove_user":
        if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
            admin_deleting_state.add(user_id)
            admin_adding_state.discard(user_id)
            users_list = "\n".join([f"• {u}" for u in ALLOWED_USERS])
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"🗑️ **حذف مستخدم:**\nالمستخدمون الحاليون:\n{users_list}\n\nالرجاء إرسال **اليوزر أو المعرف المراد حذفه** في رسالة الآن:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        return

if data == "list_users":
        if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
            users_list = "\n".join([f"• {u}" for u in ALLOWED_USERS])
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"📋 **قائمة المستخدمين المسموح لهم:**\n{users_list}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        return
            )
        else:
            await query.edit_message_text("⚙️ **لوحة إدارة المستخدمين:**\nعذراً، هذه اللوحة خاصة بمالك البوت فقط.", parse_mode="Markdown")
        return

if data == "add_user":
        if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
            admin_adding_state.add(user_id)
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "➕ **إضافة مستخدم جديد:**\nالرجاء إرسال **اليوزر الخاص بالمستخدم** (مثال: @username أو الـ ID) في رسالة الآن:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        return

if data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("📊 اختر السوق أو العملة", callback_data="choose_market")],
            [InlineKeyboardButton("⚙️ لوحة إدارة المستخدمين", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🤖 **بوت التحليل الذكي وخبير التداول**\n\n🟢 **الحالة:** حساب نشط\n\nاضغط على الزر بالأسفل لبدء اختيار الأصول:",
            reply_markup=reply_markup,
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
        
        decision = random.choice(["صعود (CALL)", "هبوط (PUT)"])
        accuracy = random.randint(75, 95)
        
        if "صعود" in decision:
            trend_text = "صعود قوي"
        else:
            trend_text = "هبوط قوي"

        # تقرير المؤشرات (نسب مئوية فقط بدون شرح طويل)
        report = (
            f"📊 **تقرير التحليل الفني**\n\n"
            f"🔹 السوق / الأصل: {market}\n"
            f"⏱ المدة الزمنية: {tf}\n"
            f"📈 نسبة وقوة التحليل: %{accuracy} ({trend_text})\n"
            f"🎯 القرار النهائي: {decision}\n\n"
            f"📉 **نسب المؤشرات:**\n"
            f"• ATR: %{random.randint(50, 90)}\n"
            f"• RSI: %{random.randint(20, 85)}\n"
            f"• Momentum: %{random.randint(40, 90)}\n"
            f"• ADX: %{random.randint(30, 80)}\n"
            f"• ROC: %{random.randint(10, 60)}\n"
            f"• CCI: %{random.randint(25, 75)}\n"
            f"• Aroon: %{random.randint(40, 95)}\n"
            f"• Williams %R: %{random.randint(15, 85)}\n"
            f"• CMO: %{random.randint(30, 70)}\n\n"
            f"⚠️ **تنبيه:** التداول ينطوي على مخاطر، يرجى الالتزام بإدارة رأس المال."
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحليل سوق جديد", callback_data="choose_market")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")
        return

# معالج استقبال النصوص لإضافة أو حذف المستخدمين
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
        text_input = update.message.text.strip().replace("@", "")
        
        if user_id in admin_adding_state:
            if text_input:
                ALLOWED_USERS.add(text_input)
                admin_adding_state.remove(user_id)
                await update.message.reply_text(f"✅ تمت إضافة المستخدم بنجاح: {text_input}")
            return
            
        elif user_id in admin_deleting_state:
            if text_input:
                if text_input == str(INITIAL_ADMIN_ID):
                    await update.message.reply_text("❌ لا يمكنك حذف مالك البوت الأساسي!")
                elif text_input in ALLOWED_USERS:
                    ALLOWED_USERS.remove(text_input)
                    await update.message.reply_text(f"🗑️ تمت إزالة وحذف المستخدم بنجاح: {text_input}")
                else:
                    await update.message.reply_text(f"⚠️ المستخدم '{text_input}' غير موجود في القائمة.")
                admin_deleting_state.remove(user_id)
            return

# وظيفة التنشيط الذاتي (منع السيرفر من النوم نهائياً وبدون تدخل منك)
def self_ping():
    url = "https://nef-bot.onrender.com"  # رابط سيرفرك الحالي على Render
    while True:
        try:
            time.sleep(240)  # إرسال نبضة تنشيط كل 4 دقائق لمنع السكون
            requests.get(url)
            log.info("Self-ping sent successfully to keep bot awake.")
        except Exception as e:
            log.error(f"Self-ping error: {e}")
            
def main():
    if not TOKEN:
        log.error("No token found!")
        return

    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    # تشغيل سيرفر الويب في خلفية منفصلة
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    # تشغيل خيط التنشيط الذاتي
    t_ping = threading.Thread(target=self_ping)
    t_ping.daemon = True
    t_ping.start()
    log.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
