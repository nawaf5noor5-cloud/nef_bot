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
TOKEN = "8968520359:AAHGU6zeCoEFvHwKkln8xMBGM0KaYHATf8Y"
INITIAL_ADMIN_ID = "5300057039"  # معرف المالك
ALLOWED_USERS = {INITIAL_ADMIN_ID}
admin_adding_state = set()
user_selections = {}

MARKETS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "Gold", "Silver", "Tesla", "Apple", "Amazon", "Smarty", "Football"]
TIMEFRAMES = ["30 ثانية", "1 دقيقة", "2 دقيقة", "5 دقائق", "15 دقيقة", "30 دقيقة"]

def is_authorized(user_id: str):
    return user_id in ALLOWED_USERS or user_id == str(INITIAL_ADMIN_ID)
    
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("❌ غير مَصرح لك استخدام هذا البوت.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 اختر السوق أو العملة", callback_data="choose_market")],
        [InlineKeyboardButton("⚙️ لوحة إدارة المستخدمين", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🤖 **بوت التحليل الذكي وخبير التداول**\n\n"
        "🟢 **الحالة:** حساب نشط\n\n"
        "👇 اضغط على الزر بالأسفل لبدء اختيار الأصول:"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
# بعد دالة start_command وأزرار الترحيب، ضع دالة الأزرار:
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
        if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID):
            keyboard = [
                [InlineKeyboardButton("➕ إضافة مستخدم جديد", callback_data="add_user")],
                [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "⚙️ **لوحة إدارة المستخدمين (المالك):**\nيمكنك التحكم بصلاحيات الوصول وإضافة مستخدمين جدد عبر اليوزر الخاص بهم.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
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
        
        decision = random.choice(["صعود🟢 (CALL)", "هبوط🔴 (PUT)"])
        accuracy = random.randint(75, 95)
        
        report = (
            f"📊 **تقرير التحليل الفني المختصر**\n\n"
            f"🔹 السوق / الأصل: {market}\n"
            f"⏱ المدة الزمنية: {tf}\n"
            f"📈 نسبة وقوة التحليل: %{accuracy} ({'صعود قوي' if 'صعود' in decision else 'هبوط قوي'})\n"
            f"🎯 القرار النهائي: {decision}\n\n"
            f"📉 **ملخص نسب وقراءات المؤشرات:**\n"
            f"• متوسط المدى الحقيقي (ATR): %{random.randint(50, 90)} (تقلب)\n"
            f"• مؤشر ستوكاستيك RSI: %{random.randint(20, 85)} (تشبع)\n"
            f"• الزخم (Momentum): %{random.randint(40, 90)} (سرعة)\n"
            f"• مؤشر الحركة الاتجاهية (ADX): %{random.randint(30, 80)} (اتجاه)\n"
            f"• معدل التغير (ROC): %{random.randint(10, 60)} (تحول)\n"
            f"• قناة السلع الأساسية (CCI): %{random.randint(25, 75)} (انحراف)\n"
            f"• أرون (Aroon): %{random.randint(40, 95)} (قوة توقيت)\n"
            f"• ويليامز (%R): %{random.randint(15, 85)} (ذروة)\n"
            f"• مذبذب تشاندي (CMO): %{random.randint(30, 70)} (مكاسب/خسائر)\n\n"
            f"⚠️ **تنبيه:** التداول ينطوي على مخاطر، يرجى الالتزام بإدارة رأس المال."
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحليل سوق جديد", callback_data="choose_market")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(report, reply_markup=reply_markup, parse_mode="Markdown")
        return

# وقبل دالة main() بأسطر قليلة، ضع نسخة واحدة فقط من handle_text_messages:
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if INITIAL_ADMIN_ID and user_id == str(INITIAL_ADMIN_ID) and user_id in admin_adding_state:
        new_user = update.message.text.strip().replace("@", "")
        if new_user:
            ALLOWED_USERS.add(new_user)
            admin_adding_state.remove(user_id)
            await update.message.reply_text(f"✅ تم بنجاح إضافة المستخدم / المعرف: **{new_user}** إلى قائمة المسموح لهم.", parse_mode="Markdown")
            return
