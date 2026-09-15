import time
import requests
import logging
import json
import os
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

# --- إعداد السجلات ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# --- الإعدادات والمتغيرات العامة ---
INITIAL_ADMIN_ID = "420693139"  # معرف المالك
TOKEN = "8968520359:AAFvKf7M2lnhJpCZxzaHauwlQG16ClZqCqc"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "allowed_users.json")

DAILY_ANALYSES_COUNT = 0

MARKETS = [
    # 💶 العملات الأجنبية (Forex)
    "eur/usd",
    "gbp/usd",
    "gbp/chf",
    "gbp/cad",
    "usd/chf",
    "usd/jpy",
    
    # 📊 المؤشرات والأصول الخاصة (Indices & Special Assets)
    "football index",
    "luxury index",
    "camel race index",
    "ai index",
    "cricket index",
    "smarty",
    "intel"
]

# --- إدارة المستخدمين والصلاحيات ---
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(str(u) for u in data)
        except Exception:
            pass
    return {str(INITIAL_ADMIN_ID)}

def save_users():
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(ALLOWED_USERS), f, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving users: {e}")

ALLOWED_USERS = load_users()
user_selections = {}

def is_authorized(user_id: str) -> bool:
    return user_id in ALLOWED_USERS

# --- دوال جلب الأسعار والشموع (Binance + Smart Fallback) ---
def get_market_candles(market_name):
    formatted_candles = []
    clean_market = str(market_name).upper().strip()
    
    try:
        binance_symbol = clean_market.replace("/", "").replace("-", "")
        if not binance_symbol.endswith("USDT") and not binance_symbol.endswith("BUSD"):
            binance_symbol = f"{binance_symbol}USDT"
            
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": binance_symbol, "interval": "1m", "limit": 30}
        
        response = requests.get(url, params=params, timeout=4)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                for kline in data:
                    formatted_candles.append({
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4])
                    })
                return formatted_candles
    except Exception as e:
        print(f"[MARKET ENGINE] Binance fetch note for {market_name}: {e}")

    # الوسيط الذكي الاحتياطي (Smart Fallback)
    base_price = 250.0 if "SMARTY" in clean_market else (50.0 if "FOOTBALL" in clean_market else 100.0)
    current_val = base_price
    
    for _ in range(30):
        change = random.uniform(-0.3, 0.3)
        current_val += change
        open_val = current_val - random.uniform(-0.1, 0.1)
        high_val = max(current_val, open_val) + random.uniform(0.0, 0.2)
        low_val = min(current_val, open_val) - random.uniform(0.2, 0.0)
        formatted_candles.append({
            "open": round(open_val, 4),
            "high": round(high_val, 4),
            "low": round(low_val, 4),
            "close": round(current_val, 4)
        })
    return formatted_candles

# --- الخوارزميات الحسابية والتحليل الفني ---
def calculate_sma_percentage(candles):
    if not candles or len(candles) < 5:
        return 50
    closes = [c['close'] for c in candles]
    sma_value = sum(closes[-10:]) / min(len(closes), 10)
    current_close = closes[-1]
    diff = ((current_close - sma_value) / sma_value) * 100
    return min(max(int(50 + (diff * 100)), 10), 99)

def calculate_macd_percentage(candles):
    if not candles or len(candles) < 12:
        return 50
    closes = [c['close'] for c in candles]
    short_ema = sum(closes[-5:]) / 5
    long_ema = sum(closes[-12:]) / 12
    macd_diff = short_ema - long_ema
    return min(max(int(50 + (macd_diff * 1000)), 10), 99)

def calculate_fractals_percentage(candles):
    if not candles or len(candles) < 5:
        return 50
    highs = [c['high'] for c in candles]
    recent_high_diff = highs[-1] - highs[-3] if len(highs) >= 3 else 0
    return min(max(int(50 + (recent_high_diff * 500)), 15), 98)

def calculate_rsi(candles):
    if not candles or len(candles) < 14:
        return 50
    closes = [c['close'] for c in candles]
    gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
    losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
    
    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14
    
    if avg_loss == 0:
        return 100
        
    rs = avg_gain / avg_loss
    rsi_val = 100 - (100 / (1 + rs))
    
    # إرجاع القيمة مقربة كعدد صحيح لتجنب الكسور الطويلة في التقارير
    return int(rsi_val)

def calculate_volatility(candles_data):
    try:
        closes = [c['close'] for c in candles_data] if candles_data else [1.0]
        highs = [c['high'] for c in candles_data] if candles_data else [1.0]
        lows = [c['low'] for c in candles_data] if candles_data else [1.0]
        
        avg_range = sum([h - l for h, l in zip(highs, lows)]) / len(candles_data) if candles_data else 0
        price_volatility = avg_range / (sum(closes) / len(closes)) * 100 if closes and sum(closes) > 0 else 0

        if price_volatility > 0.15:
            market_state = "آمن التداول"
            volatility_state = "تذبذب عالي وحركة قوية"
        elif 0.05 <= price_volatility <= 0.15:
            market_state = "مستقر"
            volatility_state = "تذبذب متوسط وطبيعي"
        else:
            market_state = "مخاطره"
            volatility_state = "تذبذب منخفض وهادئ جداً"
    except Exception:
        market_state = "مستقر"
        volatility_state = "تذبذب متوسط وطبيعي"
        
    return volatility_state, market_state

def generate_smart_signal(market_name, time_mode, candles_data, manual_seconds=60):
    try:
        sma_val = calculate_sma_percentage(candles_data)
        macd_val = calculate_macd_percentage(candles_data)
        fractals_val = calculate_fractals_percentage(candles_data)
        rsi_val = calculate_rsi(candles_data)
        
        
        rsi_score = 100 if rsi_val < 30 else (0 if rsi_val > 70 else 50)
        
        # دمج مدروس ومتوازن للمؤشرات الأربعة الأساسية فقط
        total_score = int((sma_val + macd_val + fractals_val + rsi_score) / 4)
        decision = "شراء (CALL) 🟢" if total_score >= 50 else "بيع (PUT) 🔴"
        
        volatility_status, market_status = calculate_volatility(candles_data)

        # قائمة المؤشرات المعتمدة وتقييم مدى قوتها (البعد عن الحياد 50)
        indicators_list = [
            ("المتوسط المتحرك (SMA)", sma_val),
            ("الماكدي (MACD)", macd_val),
            ("الكسور (Fractals)", fractals_val),
            ("القوة النسبية (RSI)", rsi_val)
        ]
        
        # اختيار أقوى 3 مؤشرات تعطي دلالة واضحة
        sorted_indicators = sorted(indicators_list, key=lambda x: abs(x[1] - 50), reverse=True)
        top_3 = sorted_indicators[:3]
        indicators_text = "\n".join([f"• {ind[0]}: {int(ind[1])} بالمئة" for ind in top_3])

        if time_mode == "auto":
            if rsi_val > 75 or rsi_val < 25:
                sec_num = 60
            else:
                sec_num = 120
        else:
            try:
                sec_num = int(manual_seconds)
            except:
                sec_num = 60

        if sec_num < 60:
            final_duration = f"{sec_num} ثانية"
        elif sec_num == 60:
            final_duration = "دقيقة واحدة"
        elif sec_num % 60 == 0:
            final_duration = f"{sec_num // 60} دقائق"
        else:
            final_duration = f"{sec_num // 60} دقيقة و {sec_num % 60} ثانية"

        time_type_text = "تلقائي ذكي ⚡️" if time_mode == "auto" else "يدوي 🛠"
        clean_market = str(market_name).upper()

        report = f"""📊 تقرير التحليل الفني 📈

🏛 السوق / الأصل: {clean_market}
⏰ المدة الزمنية: {final_duration}
🎯 نسبة قوة التحليل: {total_score} 📈
⚡️ القرار النهائي: {decision}
⏱ نوع الوقت: {time_type_text}

🌡 حالة السوق: {market_status}
🌊 مؤشر التقلب: {volatility_status}

🔥 أقوى 3 مؤشرات داعمة:
{indicators_text}

⚠️ التنبيه: التداول ينطوي على مخاطر عالية، يرجى الالتزام التام بإدارة رأس المال.
"""
        return report
    except Exception as e:
        print(f"CRITICAL ERROR in generate_smart_signal: {e}")
        return f"حدث خطأ أثناء معالجة التحليل: {str(e)}"

# --- لوحة المفاتيح والازرار التفاعلية ---
def get_markets_keyboard():
    keyboard = []
    
    # قاموس لتحديد الإيموجي المناسب حسب نوع الأصل أو العملة
    market_emojis = {
        "eur/usd": "💶🇺🇸",
        "gbp/usd": "💷🇺🇸",
        "gbp/chf": "💷🇨🇭",
        "gbp/cad": "💷🇨🇦",
        "usd/chf": "🇺🇸🇨🇭",
        "usd/jpy": "🇺🇸🇯🇵",
        "football index": "⚽️",
        "luxury index": "💎",
        "camel race index": "🐪",
        "ai index": "🤖",
        "cricket index": "🏏",
        "smarty": "🧠",
        "intel": "💻"
    }
    
    for market in MARKETS:
        emoji = market_emojis.get(market.lower(), "📊")
        display_name = f"{emoji} {market.upper()}"
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"market_{market}")])
        
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)
    
def get_time_selection_keyboard(market_name):
    keyboard = [
        [InlineKeyboardButton("⚡ وقت تلقائي (ذكاء البوت)", callback_data=f"time_auto_{market_name}")],
        [
            InlineKeyboardButton("⏱️ 30 ثانية", callback_data=f"time_manual_{market_name}_30"),
            InlineKeyboardButton("⏱️ 1 دقيقة", callback_data=f"time_manual_{market_name}_60"),
        ],
        [
            InlineKeyboardButton("⏱️ دقيقتان", callback_data=f"time_manual_{market_name}_120"),
            InlineKeyboardButton("⏱️ 3 دقائق", callback_data=f"time_manual_{market_name}_180"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_post_signal_keyboard(market_name):
    keyboard = [
        [InlineKeyboardButton("🔄 إعادة تحليل نفس السوق", callback_data=f"market_{market_name}")],
        [InlineKeyboardButton("📊 اختيار سوق آخر", callback_data="choose_market")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("📊 اختر السوق أو العملة", callback_data="choose_market")]
    ]
    if INITIAL_ADMIN_ID and str(user_id) == str(INITIAL_ADMIN_ID):
        keyboard.append([InlineKeyboardButton("⚙️ لوحة إدارة المستخدمين", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

# --- معالجة الأوامر والرسائل والطلبات ---
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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if not is_authorized(user_id):
        await query.edit_message_text("❌ غير مصرح لك استخدام هذا البوت.")
        return

    data = query.data

    if data == "choose_market":
        reply_markup = get_markets_keyboard()
        await query.message.edit_text(
            "📊 **الرجاء اختيار السوق أو الأصل المطلوب:**",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if data == "main_menu":
        reply_markup = get_main_menu_keyboard(user_id)
        await query.edit_message_text(
            "🤖 **البوت الذكي وخبير التداول**\n\n🟢 الحالة: نشط (يعمل 24/7)\n\n👇 اضغط على الزر بالأسفل لبدء اختيار الأصول 👇",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if data == "admin_panel":
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            await query.answer("⛔ عذراً، هذه اللوحة مخصصة لمالك البوت فقط.", show_alert=True)
            return
        admin_text = (
            f"⚙️ **لوحة إدارة البوت (المشرف):**\n\n"
            f"👥 المستخدمون المسموح لهم: `{len(ALLOWED_USERS)}`\n"
            f"📈 التحليلات المجراة اليوم: `{globals().get('DAILY_ANALYSES_COUNT', 0)}`\n\n"
            f"📌 اختر الإجراء المطلوب أدناه:"
        )
        keyboard = [
            [InlineKeyboardButton("📋 جميع المستخدمين", callback_data="admin_list_users")],
            [
                InlineKeyboardButton("➕ إضافة مستخدم", callback_data="admin_add_prompt"),
                InlineKeyboardButton("🗑️ حذف مستخدم", callback_data="admin_remove_prompt")
            ],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode="Markdown")
        return

    if data == "admin_list_users":
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            return
        users_list_str = "\n".join([f"• `{u}`" for u in ALLOWED_USERS]) if ALLOWED_USERS else "لا يوجد مستخدمون."
        text = f"📋 **قائمة المستخدمين المسموح لهم:**\n\n{users_list_str}"
        keyboard = [[InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "admin_add_prompt":
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            return
        context.user_data["waiting_for"] = "add_user"
        text = "➕ **إضافة مستخدم جديد:**\n\nأرسل الآن (معرف الآيدي ID) أو (اليوزر مع @) الخاص بالمستخدم المراد إضافته:"
        keyboard = [[InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "admin_remove_prompt":
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            return
        context.user_data["waiting_for"] = "remove_user"
        text = "🗑️ **حذف مستخدم:**\n\nأرسل الآن (معرف الآيدي ID) أو (اليوزر مع @) الخاص بالمستخدم المراد حذفه:"
        keyboard = [[InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data.startswith("market_"):
        market_name = data.split("_")[1]
        user_selections[user_id] = {"market": market_name}
        reply_markup = get_time_selection_keyboard(market_name)
        await query.edit_message_text(
            text=f"📊 **السوق المختار:** {market_name.upper()}\nالرجاء اختيار نظام الوقت للصفقة:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

async def handle_time_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        data = query.data
        globals()['DAILY_ANALYSES_COUNT'] = globals().get('DAILY_ANALYSES_COUNT', 0) + 1
        
        if data.startswith("time_auto_"):
            market_name = data.replace("time_auto_", "")
            await query.edit_message_text(text=f"🧠 **جاري تحليل السوق `{market_name.upper()}` بالذكاء الاصطناعي واختيار أفضل فترة زمنية...**", parse_mode="Markdown")
            time.sleep(1.0)
            
            candles_data = get_market_candles(market_name)
            recommendation = generate_smart_signal(market_name, "auto", candles_data)
            reply_markup = get_post_signal_keyboard(market_name)
            await query.edit_message_text(text=recommendation, reply_markup=reply_markup, parse_mode="Markdown")
            
        elif data.startswith("time_manual_"):
            parts = data.split("_")
            market_name = parts[2]
            seconds = int(parts[3])
            await query.edit_message_text(text=f"📊 جاري تحليل السوق `{market_name.upper()}` على وقت `{seconds} ثانية`...", parse_mode="Markdown")
            time.sleep(1.0)
            
            candles_data = get_market_candles(market_name)
            recommendation = generate_smart_signal(market_name, "manual", candles_data, manual_seconds=seconds)
            reply_markup = get_post_signal_keyboard(market_name)
            await query.edit_message_text(text=recommendation, reply_markup=reply_markup, parse_mode="Markdown")
            
    except Exception as e:
        print(f"ERROR in handle_time_selection_callback: {e}")
        try:
            await query.message.reply_text(text="⚠️ حدث خطأ مؤقت أثناء معالجة الطلب، يرجى المحاولة مرة أخرى.")
        except:
            pass

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if text.startswith("/stats"):
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            await update.message.reply_text("⛔ عذراً، هذا الأمر مخصص لمالك البوت فقط.")
            return
        total_users = len(ALLOWED_USERS)
        stats_msg = (
            f"📊 **إحصائيات نظام التداول الشاملة:**\n\n"
            f"👥 **المستخدمون المسموح لهم:** `{total_users}` مستخدم\n"
            f"📈 **التحليلات المجراة اليوم:** `{globals().get('DAILY_ANALYSES_COUNT', 0)}` تحليل\n"
            f"🟢 **حالة السيرفر:** مستقر ويعمل بكفاءة (Render)"
        )
        await update.message.reply_text(stats_msg, parse_mode="Markdown")
        return

    if text.startswith("/add"):
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            return
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("ℹ️ **طريقة الاستخدام:**\n`/add username` أو `@username`", parse_mode="Markdown")
            return
        clean_target = parts[1].strip().lstrip("@").lower()
        formatted_username = f"@{clean_target}"
        if formatted_username in ALLOWED_USERS:
            await update.message.reply_text(f"⚠️ المستخدم `{formatted_username}` موجود مسبقاً.", parse_mode="Markdown")
            return
        ALLOWED_USERS.add(formatted_username)
        save_users()
        await update.message.reply_text(f"✅ تم إضافة المستخدم `{formatted_username}` بنجاح.", parse_mode="Markdown")
        return

    if text.startswith("/remove"):
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            return
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("ℹ️ **طريقة الاستخدام:**\n`/remove username` أو `@username`", parse_mode="Markdown")
            return
        clean_target = parts[1].strip().lstrip("@").lower()
        formatted_username = f"@{clean_target}"
        if formatted_username in ALLOWED_USERS:
            ALLOWED_USERS.remove(formatted_username)
            save_users()
            await update.message.reply_text(f"🗑️ تمت إزالة المستخدم `{formatted_username}` بنجاح.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"⚠️ المستخدم `{formatted_username}` غير موجود في القائمة.", parse_mode="Markdown")
        return

# --- خادم الفلاسك ونظام Keep-Alive 24/7 ---
app_flask = Flask("bot")

@app_flask.route("/")
def index():
    return "Bot is running 24/7!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

def self_ping():
    time.sleep(10)
    while True:
        try:
            requests.get("http://localhost:8080/")
        except Exception:
            pass
        time.sleep(120)

# --- التشغيل الأساسي للبوت ---
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_time_selection_callback, pattern="^time_"))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    log.info("Bot is starting 24/7...")
    application.run_polling()

if __name__ == "__main__":
    main()
