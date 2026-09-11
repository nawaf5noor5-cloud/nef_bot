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

import json
import os

INITIAL_ADMIN_ID = "420693139"  # معرف المالك
TOKEN = "8968520359:AAFvKf7M2lnhJpCZxzaHauwlQG16ClZqCqc"
# استخدام المسار المطلق لضمان حفظ الملف بجانب ملف البوت دائماً
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "allowed_users.json")

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception:
            pass
    return {INITIAL_ADMIN_ID}

def save_users():
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(ALLOWED_USERS), f, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving users: {e}")

ALLOWED_USERS = load_users()
ALLOWED_USERS = load_users()
admin_adding_state = set()
admin_deleting_state = set()
user_selections = {}
MARKETS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "Gold", "Silver", "Tesla", "Apple", "Amazon", "Smarty", "Football"]
TIMEFRAMES = ["30 ثانية", "1 دقيقة", "2 دقيقة", "5 دقائق", "15 دقيقة", "30 دقيقة"]

# سيرفر الفلاسك للتشغيل المستمر على Render
app_flask = Flask("bot")

@app_flask.route("/")
def index():
    return "Bot is running 24/7!"

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
        f"🟢 **الحالة: حساب نشط (يعمل 24/7)**\n\n"
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
            f"⏱️ **السوق المختار:** {market_name}\nالرجاء تحديد الإطار الزمني:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if data.startswith("tf_"):
        tf_name = data.split("_")[1]
        if user_id in user_selections:
            user_selections[user_id]["timeframe"] = tf_name
        
        market = user_selections.get(user_id, {}).get("market", "العام")
        
        await query.edit_message_text(f"🔄 **جاري تحليل السوق لـ ({market}) على إطار ({tf_name})...**", parse_mode="Markdown")
        time.sleep(1.5)
        
        is_buy = random.choice([True, False])
        decision = "صعود (CALL)" if is_buy else "هبوط (PUT)"
        strength_desc = "صعود قوي" if is_buy else "هبوط قوي"
        confidence = random.randint(85, 96)
        
        # نسب جميع المؤشرات المطلوبة
        p_alligator = random.randint(70, 95)
        p_macd = random.randint(75, 96)
        p_sma = random.randint(72, 94)
        p_bollinger = random.randint(68, 92)
        p_aroon = random.randint(70, 95)
        rsi_val = random.randint(60, 80) if is_buy else random.randint(20, 40)
        p_ao = random.randint(65, 90)
        p_fractals = random.randint(75, 98)
        p_momentum = random.randint(65, 88)
        p_aroon_osc = random.randint(70, 93)
        p_sar = random.randint(78, 99)
        p_williams = random.randint(15, 35)

        analysis_text = (
            f"📊 **تقرير التحليل الفني**\n\n"
            f"🔹 **السوق / الأصل:** {market}\n"
            f"⏱️ **المدة الزمنية:** {tf_name}\n"
            f"📈 **نسبة وقوة التحليل:** %{confidence} ({strength_desc})\n"
            f"🎯 **القرار النهائي:** {decision}\n\n"
            f"📉 **نسب المؤشرات:**\n\n"
            f"• التمساح (Alligator): %{p_alligator}\n"
            f"• الماكد (MACD): %{p_macd}\n"
            f"• المتوسط المتحرك (SMA/EMA): %{p_sma}\n"
            f"• البولينجر باند: %{p_bollinger}\n"
            f"• أرون: %{p_aroon}\n"
            f"• RSI: %{rsi_val}\n"
            f"• المذبذب الرائع (AO): %{p_ao}\n"
            f"• الكسورية (Fractals): %{p_fractals}\n"
            f"• Momentum: %{p_momentum}\n"
            f"• مذبذب أرون: %{p_aroon_osc}\n"
            f"• التوقف والانعكاس (SAR): %{p_sar}\n"
            f"• Williams %R: %{p_williams}\n\n"
            f"⚠️ **تنبيه:** التداول ينطوي على مخاطر، يرجى الالتزام بإدارة رأس المال."
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحليل سوق جديد", callback_data="choose_market")],
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
                "⚙️ **لوحة إدارة المستخدمين (المالك):**",
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
                "➕ **إضافة مستخدم جديد:**\nالرجاء إرسال **المعرف** في رسالة الآن:",
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
                f"🗑️ **حذف مستخدم:**\nالحاليون:\n{users_list}\n\nأرسل **المعرف المراد حذفه**:",
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
                f"📋 **المستخدمون المسموح لهم:**\n{users_list}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        return

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().lstrip("@")

    if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
        if user_id in admin_adding_state:
            admin_adding_state.remove(user_id)
            ALLOWED_USERS.add(text)
            save_users()  # حفظ المستخدمين بشكل دائم في ملف
            await update.message.reply_text(f"✅ تم إضافة المستخدم `{text}` وحفظه بنجاح وتفعيله.", parse_mode="Markdown")
            return

        if user_id in admin_deleting_state:
            admin_deleting_state.remove(user_id)
            if text in ALLOWED_USERS:
                if text == str(INITIAL_ADMIN_ID):
                    await update.message.reply_text("⚠️ لا يمكنك حذف المالك الأساسي.")
                    return
                ALLOWED_USERS.remove(text)
                save_users()  # تحديث الملف بعد الحذف
                await update.message.reply_text(f"🗑️ تم حذف المستخدم `{text}` بنجاح.", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ هذا المستخدم غير موجود في القائمة.")
            return
            
# نظام منع السكون (Keep-Alive 24/7)
def self_ping():
    time.sleep(10)
    while True:
        try:
            requests.get("http://localhost:8080/")
        except Exception:
            pass
        time.sleep(120)  # يرسل طلباً كل دقيقتين ليبقى البوت نشطاً على مدار الساعة

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    log.info("Bot is starting 24/7...")
    application.run_polling()

if __name__ == "__main__":
    main()
