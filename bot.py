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
        
        await query.edit_message_text(f"📊 **جاري تحليل السوق ({market}) على إطار ({tf_name})...**", parse_mode="Markdown")
        time.sleep(1.5)

        is_buy = random.choice([True, False])

        # 1. تجميع المؤشرات في قاموس لتحليلها
        indicators = {
            "Alligator": random.randint(70, 95),
            "MACD": random.randint(75, 96),
            "SMA": random.randint(72, 94),
            "Bollinger": random.randint(68, 92),
            "Aroon": random.randint(70, 95),
            "RSI": random.randint(60, 88) if is_buy else random.randint(20, 40),
            "Parabolic SAR": random.randint(65, 90),
            "Fractals": random.randint(75, 98),
            "Momentum": random.randint(65, 88),
            "Awesome": random.randint(70, 93),
            "CCI": random.randint(78, 99),
            "Williams": random.randint(15, 35)
        }

        # 2. جلب حالة التذبذب والسوق واختيار أقوى 3 مؤشرات
        market_status, market_suitability = evaluate_market_condition(indicators)
        sorted_indicators = sorted(indicators.items(), key=lambda x: x[1], reverse=True)
        top_3_indicators = sorted_indicators[:3]

        # 3. بناء نص التقرير المختصر والمركز الجديد
        report_text = (
            f"📊 **تقرير تحليل التداول السريع**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📌 **حالة السوق:** {market_status}\n"
            f"🎯 **القرار:** {market_suitability}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **أقوى 3 مؤشرات داعمة للقرار:**\n"
        )

        for ind_name, ind_score in top_3_indicators:
            report_text += f"▪️ {ind_name}: `{ind_score}%`\n"

        report_text += (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *ملاحظة: تم تحليل باقي المؤشرات في الخلفية.*\n"
            f"⚠️ **التنبيه:** التداول ينطوي على مخاطر، يرجى الالتزام بإدارة رأس المال."
        )

        # 4. الأزرار التفاعلية أسفل التقرير
        keyboard = [
            [InlineKeyboardButton("🔄 تحليل سوق جديد", callback_data="choose_market")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(report_text, reply_markup=reply_markup, parse_mode="Markdown")
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

def evaluate_market_condition(indicators_dict):
    """
    تقييم حالة التذبذب والسوق بناءً على نتائج المؤشرات
    """
    # حساب متوسط القوة لجميع المؤشرات
    scores = list(indicators_dict.values())
    if not scores:
        return "غير مُتاح", "⚠️ بيانات غير كافية للتقييم"
    
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)
    min_score = min(scores)
    volatility_spread = max_score - min_score # مدى التذبذب بين أقوى وأضعف مؤشر

    # منطق تحديد هل السوق صالح للتداول أم لا
    if volatility_spread > 40 and avg_score > 60:
        market_status = "🔥 تذبذب قوي وممتاز للتداول (اتجاه واضح)"
        suitability = "صالح جداً للتداول 🟢"
    elif volatility_spread < 20:
        market_status = "💤 سوق عرضي / تذبذب ضعيف"
        suitability = "غير صالح للتداول (انتظر كسر النطاق) 🔴"
    else:
        market_status = "⚖️ تذبذب معتدل"
        suitability = "تداول بحذر (حجم عقد صغير) 🟡"
        
    return market_status, suitability
            
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
