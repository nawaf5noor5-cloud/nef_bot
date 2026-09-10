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

# الإعدادات والمتغيرات الأساسية
TOKEN = "8968520359:AAE0L8vv6NEHL6cL4hn0KSRge_an17QAoAA"
INITIAL_ADMIN_ID = "420693139"  # معرف المالك
ALLOWED_USERS = {INITIAL_ADMIN_ID}
admin_adding_state = set()
admin_deleting_state = set()
user_selections = {}

MARKETS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "Gold", "Silver", "Tesla", "Apple", "Amazon", "Smarty", "Football"]
TIMEFRAMES = ["1 دقيقة", "2 دقيقة", "5 دقائق", "15 دقيقة", "30 دقيقة", "ساعة"]

# سيرفر الفلاسك للتشغيل المستمر على Render
app_flask = Flask("bot")

@app_flask.route("/")
def index():
    return "Bot is running!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

# أداة الحماية والتحقق من صلاحية المستخدم
def is_authorized(user_id: str) -> bool:
    return user_id in ALLOWED_USERS

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

    if data.startswith("market_"):
        market_name = data.split("_")[1]
        user_selections[user_id] = {"market": market_name}
        keyboard = [[InlineKeyboardButton(tf, callback_data=f"tf_{tf}")] for tf in TIMEFRAMES]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⏱️ **الوقـت المختار:** {market_name}\nالرجاء تحديد الإطار الزمني:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if data.startswith("tf_"):
        tf_name = data.split("_")[1]
        if user_id in user_selections:
            user_selections[user_id]["timeframe"] = tf_name
        
        market = user_selections.get(user_id, {}).get("market", "العام")
        
        # رسالة جاري التحليل مع محاكاة واقعية
        await query.edit_message_text(f"🔄 **جاري تحليل السوق لـ ({market}) على إطار ({tf_name})...**", parse_mode="Markdown")
        time.sleep(1.5)
        
        # توليد نتيجة تحليل وهمية احترافية
        direction = random.choice(["🟢 شراء (CALL)", "🔴 بيع (PUT)"])
        confidence = random.randint(78, 96)
        
        analysis_text = (
            f"📈 **تقرير التحليل الفني الذكي**\n\n"
            f"📌 **الأصل:** {market}\n"
            f"⏱️ **الإطار الزمني:** {tf_name}\n\n"
            f"💡 **التوصية المقترحة:** {direction}\n"
            f"⭐ **نسبة الدقة المتوقعة:** {confidence}%\n\n"
            f"⚠️ *تنبيه: التداول ينطوي على مخاطر عالية، هذه الإشارة للاستئناس فقط.*"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحليل جديد", callback_data="choose_market")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(analysis_text, reply_markup=reply_markup, parse_mode="Markdown")
        return

    if data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("📊 اختر السوق أو العملة", callback_data="choose_market")],
            [InlineKeyboardButton("⚙️ لوحة إدارة المستخدمين", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🤖 **القائمة الرئيسية:**\nاختر من الأزرار أدناه:",
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

    if data == "add_user":
        if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
            admin_adding_state.add(user_id)
            admin_deleting_state.discard(user_id)
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "➕ **إضافة مستخدم جديد:**\nالرجاء إرسال **اليوزر أو المعرف** المراد إضافته في رسالة الآن:",
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

# معالج الرسائل النصية الموجهة لإدارة المستخدمين
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
        if user_id in admin_adding_state:
            admin_adding_state.remove(user_id)
            ALLOWED_USERS.add(text)
            await update.message.reply_text(f"✅ تم إضافة المستخدم `{text}` بنجاح إلى القائمة المسموحة.", parse_mode="Markdown")
            return

        if user_id in admin_deleting_state:
            admin_deleting_state.remove(user_id)
            if text in ALLOWED_USERS:
                if text == str(INITIAL_ADMIN_ID):
                    await update.message.reply_text("⚠️ لا يمكنك حذف المالك الأساسي للبوت.")
                    return
                ALLOWED_USERS.remove(text)
                await update.message.reply_text(f"🗑️ تم حذف المستخدم `{text}` بنجاح.", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ هذا المستخدم غير موجود في قائمة المسموح لهم.")
            return

# آلية الـ Self Ping لمنع سكون Render
def self_ping():
    while True:
        try:
            requests.get("http://localhost:8080/")
        except Exception:
            pass
        time.sleep(300)

def main():
    # تشغيل الفلاسك في مسار خلفي
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()

    # بناء وتشغيل تطبيق البوت
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    log.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
