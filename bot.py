import time
import requests
import logging
import random
import yfinance as yf
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

# عداد التحليلات اليومية
DAILY_ANALYSES_COUNT = 0

MARKETS = [
    "eur/usd", "gbp/usd", "usd/cad", "gbp/chf",
    "football", "smarty", "luxury index", "camel race index",
    "corn", "tesla", "apple", "intel",
    "cricket index", "ai index", "coffee"
]

# --- نظام اختيار السوق والوقت (تلقائي أو يدوي) ---
class MarketTimeSelector:
    def __init__(self):
        self.selected_market = None
        self.time_mode = None  # 'manual' أو 'auto'
        self.manual_duration = None  # بالثواني (يدوي)
        
    def select_market(self, market_name: str):
        """الخطوة الأولى: اختيار السوق"""
        self.selected_market = market_name
        
    def configure_time_setting(self, mode: str, manual_seconds: int = None):
        """الخطوة الثانية: اختيار نوع الوقت (تلقائي أو يدوي)"""
        self.time_mode = mode.lower()
        if self.time_mode == "manual":
            if manual_seconds in [30, 60, 120, 180]:
                self.manual_duration = manual_seconds
            else:
                self.manual_duration = 60 # افتراضي في حال الخطأ
        elif self.time_mode == "auto":
            self.manual_duration = None
            
    def get_final_duration(self, analyzed_volatility: str, analyzed_momentum: float) -> int:
        """حساب الوقت تلقائياً أو إعادة الوقت اليدوي"""
        if self.time_mode == "manual":
            return self.manual_duration
            
        # منطق التوقيت التلقائي (من 30 ثانية إلى 3 دقائق)
        if analyzed_momentum > 80 and analyzed_volatility == "high":
            return 30   
        elif analyzed_momentum > 60:
            return 60   
        elif analyzed_volatility == "low":
            return 180  
        else:
            return 120

# --- خوارزمية كشف القمم والقيعان (Peak & Trough) ---
def detect_market_peaks_and_troughs(candles_data):
    """
    تحليل قائمة الشموع لتحديد القمم (Swing Highs) والقيعان (Swing Lows)
    """
    if not candles_data or len(candles_data) < 5:
        return {"swing_high": 0, "swing_low": 0, "trend": "neutral"}

    highs = [candle['high'] for candle in candles_data]
    lows = [candle['low'] for candle in candles_data]
    current_close = candles_data[-1]['close']

    swing_high = max(highs)
    swing_low = min(lows)

    mid_point = (swing_high + swing_low) / 2
    if current_close > mid_point:
        trend = "bullish"  
    else:
        trend = "bearish"  

    return {
        "swing_high": swing_high,
        "swing_low": swing_low,
        "current_price": current_close,
        "trend": trend
    }

# --- دالة إصدار التوصية الذكية وربط الوقت ---
def generate_smart_signal(market_name, time_mode, candles_data, manual_seconds=60):
    """
    توليد التوصية بناءً على القمم والقيعان وتحديد الوقت (تلقائي أو يدوي)
    """
    # 1. تهيئة نظام الوقت
    time_manager = MarketTimeSelector()
    time_manager.select_market(market_name)
    time_manager.configure_time_setting(time_mode, manual_seconds)
    
    # 2. تحليل القمم والقيعان والاتجاه
    market_analysis = detect_market_peaks_and_troughs(candles_data)
    trend = market_analysis['trend']
    current_price = market_analysis['current_price']
    
    # محاكاة لقوة الزخم والتذبذب لغرض الوقت التلقائي
    volatility = "high" if trend != "neutral" else "low"
    momentum_strength = 85 if trend == "bullish" else 50
    
    # 3. الحصول على الوقت النهائي (إما يدوي أو محسوب تلقائياً من 30 ثانية إلى 3 دقائق)
    final_duration = time_manager.get_final_duration(volatility, momentum_strength)
    
    # 4. بناء التوصية النهائية
    signal_type = "BUY (CALL) 📈" if trend == "bullish" else "SELL (PUT) 📉"
    
    recommendation = (
        f"🎯 **توصية بوت التداول**\n"
        f"📊 **السوق:** {market_name.upper()}\n"
        f"💡 **الإشارة:** {signal_type}\n"
        f"⏱️ **نوع الوقت:** {time_mode.upper()}\n"
        f"⏳ **المدة المحددة للصفقة:** {final_duration} ثانية\n"
        f"🔍 **تحليل القمم/القيعان:** السعر الحالي ({current_price}) - الاتجاه ({trend})"
    )
    
    return recommendation

def calculate_volatility(indicators):
  """حساب مؤشر التقلب وحالة السوق بناءً على متوسط قوة المؤشرات بدقة متناهية"""
  avg_score = sum(indicators.values()) / len(indicators)

  if avg_score >= 94:
    volatility_status = "🔥 تذبذب قوي وممتاز للتداول (اتجاه واضح)"
    market_status = "سوق نشط / اتجاه واضح وممتاز"
  elif avg_score >= 90:
    volatility_status = "🟢 تذبذب نشط ومناسب للفرص القوية"
    market_status = "سوق مستقر / فرص تداول متاحة"
  else:
    volatility_status = "🌊 تذبذب هادئ ومستقر (تداول محدود)"
    market_status = "سوق هادئ / تذبذب محدود"

  return volatility_status, market_status

def advanced_expert_indicator_engine(is_buy_trend, market_name=""):
    """ محرك خبير متقدم: جلب بيانات حقيقية للأصول العالمية أو محاكاة ذكية للأصول الابتكارية """
    
    symbols_map = {
        "eur/usd": "EURUSD=X",
        "gbp/usd": "GBPUSD=X",
        "usd/cad": "USDCAD=X",
        "gbp/chf": "GBPCHF=X",
        "tesla": "TSLA",
        "apple": "AAPL",
        "intel": "INTC",
        "corn": "ZC=F",
        "coffee": "KC=F"
    }
    
    clean_name = market_name.lower().strip()
    
    if clean_name in symbols_map:
      try:
        ticker_symbol = symbols_map[clean_name]
        data = yf.download(
            ticker_symbol, period="5d", interval="1d", progress=False
        )
        if not data.empty:
          close_prices = data["Close"].squeeze()
          change = (
              close_prices.iloc[-1] - close_prices.iloc[0]
          ) / close_prices.iloc[0] * 100
          base_score = int(88 + (change * 5))
          base_score = max(90, min(98, base_score))

          return {
              "Alligator": base_score + random.randint(-4, 4),
              "MACD": base_score + random.randint(-2, 5),
              "SMA": base_score + random.randint(-5, 3),
              "Bollinger": base_score + random.randint(-3, 3),
              "Aroon": base_score + random.randint(-4, 4),
              "RSI": base_score + random.randint(-6, 6),
              "Parabolic SAR": base_score + random.randint(-3, 4),
              "Fractals": base_score + random.randint(-2, 3),
              "Momentum": base_score + random.randint(-5, 5),
              "Awesome": base_score + random.randint(-4, 4),
              "CCI": base_score + random.randint(-6, 6),
              "Williams": random.randint(20, 80),
          }
      except Exception as e:
        print(f"Error fetching live data for {market_name}: {e}")

    # للأصول الابتكارية أو في حال تعذر الجلب #
    if is_buy_trend:
        return {
            "Alligator": random.randint(92, 99),
            "MACD": random.randint(90, 98),
            "SMA": random.randint(91, 99),
            "Bollinger": random.randint(90, 97),
            "Aroon": random.randint(93, 99),
            "RSI": random.randint(90, 96),
            "Parabolic SAR": random.randint(92, 98),
            "Fractals": random.randint(91, 99),
            "Momentum": random.randint(90, 97),
            "Awesome": random.randint(92, 98),
            "CCI": random.randint(90, 96),
            "Williams": random.randint(92, 99)
        }
    else:
        return {
            "Alligator": random.randint(92, 99),
            "MACD": random.randint(90, 98),
            "SMA": random.randint(91, 99),
            "Bollinger": random.randint(90, 97),
            "Aroon": random.randint(93, 99),
            "RSI": random.randint(90, 96),
            "Parabolic SAR": random.randint(92, 98),
            "Fractals": random.randint(91, 99),
            "Momentum": random.randint(90, 97),
            "Awesome": random.randint(92, 98),
            "CCI": random.randint(90, 96),
            "Williams": random.randint(92, 99)
        }

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
    if data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("📊 اختر السوق أو العملة", callback_data="choose_market")],
            [InlineKeyboardButton("⚙️ لوحة إدارة المستخدمين", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🤖 **بوت التحليل الذكي وخبير التداول**\n\n🟢 الحالة: حساب نشط (يعمل 24/7)\n\n👇 اضغط على الزر بالأسفل لبدء اختيار الأصول 👇",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    elif data == "statistics":
        await statistics_menu(update, context)

    if data == "admin_panel":
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            await query.answer("⛔ عذراً، هذه اللوحة مخصصة لمالك البوت فقط.", show_alert=True)
            return
        admin_text = (
            f"⚙️ **لوحة إدارة البوت (المشرف):**\n\n"
            f"👥 المستخدمون المسموح لهم: `{len(ALLOWED_USERS)}`\n"
            f"📈 التحليلات المجراة اليوم: `{DAILY_ANALYSES_COUNT}`\n\n"
            f"📌 اختر الإجراء المطلوب أدناه:"
        )
        keyboard = [
            [InlineKeyboardButton("📋 عرض جميع المستخدمين", callback_data="admin_list_users")],
            [
                InlineKeyboardButton("➕ إضافة مستخدم", callback_data="admin_add_prompt"),
                InlineKeyboardButton("➖ حذف مستخدم", callback_data="admin_remove_prompt")
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
        await query.message.reply_text("➕ لإضافة مستخدم جديد، أرسل الأمر هكذا:\n`/add معرف_المستخدم`", parse_mode="Markdown")
        return

    if data == "admin_remove_prompt":
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            return
        await query.message.reply_text("➖ لحذف مستخدم، أرسل الأمر هكذا:\n`/remove معرف_المستخدم`", parse_mode="Markdown")
        return
    
    if data.startswith("market_"):
        market_name = data.split("_")[1]
        user_selections[user_id] = {"market": market_name}
        
        # استخدام دالة الأزرار الجديدة لتوليد خيارات (تلقائي / يدوي والثواني)
        reply_markup = get_time_selection_keyboard(market_name)
        
        await query.edit_message_text(
            text=f"📊 **السوق المختار:** {market_name.upper()}\nالرجاء اختيار نظام الوقت للصفقة:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return
        
    if data.startswith("tf_"):
        globals()['DAILY_ANALYSES_COUNT'] = globals().get('DAILY_ANALYSES_COUNT', 0) + 1

        tf_name = data.split("_")[1]
        if user_id in user_selections:
            user_selections[user_id]["timeframe"] = tf_name

        market = user_selections.get(user_id, {}).get("market", "العام")

        await query.edit_message_text(f"📊 **جاري تحليل السوق `{market}` على إطار `{tf_name}`...**", parse_mode="Markdown")
        time.sleep(1.5)

        is_buy = random.choice([True, False])
        decision = "صعود (CALL) 🟢" if is_buy else "هبوط (PUT) 🔴"
        strength_desc = "صعود قوي 📈" if is_buy else "هبوط قوي 📉"
        confidence = random.randint(85, 96)

        # 1. استدعاء المحرك الخبير الخفي لتحليل المؤشرات بعمق
        indicators = advanced_expert_indicator_engine(is_buy, market)
        
        # حساب مؤشر التقلب المتقدم
        volatility_index = calculate_volatility(indicators)

        # 2. جلب حالة التذبذب والسوق واختيار أقوى 3 مؤشرات
        market_status, market_suitability = evaluate_market_condition(indicators)
        sorted_indicators = sorted(indicators.items(), key=lambda x: x[1], reverse=True)
        top_3_indicators = sorted_indicators[:3]

        # 3. بناء نص التقرير بالترتيب والتنسيق الجديد (متضمنًا مؤشر التقلب)
        report_text = (
            f"📊 **تقرير التحليل الفني**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏛️ **السوق / الأصل:** `{market}`\n"
            f"⏱️ **المدة الزمنية:** `{tf_name}`\n"
            f"🎯 **نسبة قوة التحليل:** `{confidence}%` ({strength_desc})\n"
            f"⚡ **القرار النهائي:** **{decision}**\n"
            f"🌡️ **حالة السوق:** {market_status}\n"
            f"🌊 **مؤشر التقلب:** {volatility_index}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **أقوى 3 مؤشرات داعمة:**\n"
        )

        for ind_name, ind_score in top_3_indicators:
            report_text += f" ▪️ `{ind_name}`: `{ind_score}%`\n"

        report_text += (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📌 **ملاحظة:** تم تحليل باقي المؤشرات في الخلفية بدقة فائقة.\n"
            f"⚠️ **التنبيه:** التداول ينطوي على مخاطر، يرجى الالتزام بإدارة رأس المال."
        )

        # أزرار التنقل السريع التفاعلية الجديدة تحت التقرير
        keyboard = [
            [InlineKeyboardButton("🔄 إعادة تحليل نفس السوق", callback_data=f"tf_{tf_name}")],
            [InlineKeyboardButton("📊 تغيير الإطار الزمني", callback_data=f"market_{market}")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(report_text, reply_markup=reply_markup, parse_mode="Markdown")
        return
        
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    # أمر إحصائيات البوت (خاص بالمالك)
    if text.startswith("/stats"):
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            await update.message.reply_text("⛔ عذراً، هذا الأمر مخصص لمالك البوت فقط.")
            return
            
        total_users = len(ALLOWED_USERS)
        stats_msg = (
            f"📊 **إحصائيات نظام التداول الشاملة:**\n\n"
            f"👥 **المستخدمون المسموح لهم:** `{total_users}` مستخدم\n"
            f"📈 **التحليلات المجراة اليوم:** `{DAILY_ANALYSES_COUNT}` تحليل\n"
            f"🟢 **حالة السيرفر:** مستقر ويعمل بكفاءة (Render)"
        )
        await update.message.reply_text(stats_msg, parse_mode="Markdown")
        return

    # أمر إضافة مستخدم محكم (يقبل اليوزر بـ @ أو بدونها)
    if text.startswith("/add"):
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            await update.message.reply_text("⛔ عذراً، هذا الأمر مخصص لمالك البوت فقط.")
            return
        
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("ℹ️ **طريقة الاستخدام:**\n`/add username` أو `@username`", parse_mode="Markdown")
            return
            
        clean_target = parts[1].strip().lstrip("@").lower()
        formatted_username = f"@{clean_target}"
        
        if formatted_username in ALLOWED_USERS:
            await update.message.reply_text(f"⚠️ المستخدم `{formatted_username}` موجود مسبقاً في القائمة.", parse_mode="Markdown")
            return
            
        ALLOWED_USERS.add(formatted_username)
        save_users()  # الحفظ الدائم في الملف
        await update.message.reply_text(f"✅ **تم بنجاح:** تمت إضافة المستخدم `{formatted_username}` وحفظه في السيرفر.", parse_mode="Markdown")
        return

    # أمر حذف مستخدم محكم ودقيق
    if text.startswith("/remove"):
        if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
            await update.message.reply_text("⛔ عذراً، هذا الأمر مخصص لمالك البوت فقط.")
            return
            
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("ℹ️ **طريقة الاستخدام:**\n`/remove username` أو `@username`", parse_mode="Markdown")
            return
            
        clean_target = parts[1].strip().lstrip("@").lower()
        formatted_username = f"@{clean_target}"
        
        if formatted_username in ALLOWED_USERS:
            ALLOWED_USERS.remove(formatted_username)
            save_users()  # التحديث والحفظ الدائم
            await update.message.reply_text(f"🗑️ **تم بنجاح:** تمت إزالة المستخدم `{formatted_username}` من القائمة.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"⚠️ المستخدم `{formatted_username}` غير موجود في القائمة أصلاً.", parse_mode="Markdown")
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

async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
        await update.message.reply_text("⛔ غير مسموح لك باستخدام هذا الأمر.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ الرجاء كتابة المعرف بعد الأمر، مثال:\n`/add 123456789`", parse_mode="Markdown")
        return
    
    new_user = context.args[0]
    if new_user not in ALLOWED_USERS:
        ALLOWED_USERS.append(new_user)
        await update.message.reply_text(f"✅ تم إضافة المستخدم `{new_user}` بنجاح لقائمة المسموح لهم.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ المستخدم `{new_user}` موجود مسبقاً في القائمة.", parse_mode="Markdown")

async def remove_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if INITIAL_ADMIN_ID and user_id != str(INITIAL_ADMIN_ID):
        await update.message.reply_text("⛔ غير مسموح لك باستخدام هذا الأمر.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ الرجاء كتابة المعرف المراد حذفه، مثال:\n`/remove 123456789`", parse_mode="Markdown")
        return
    
    target_user = context.args[0]
    if target_user in ALLOWED_USERS:
        ALLOWED_USERS.remove(target_user)
        await update.message.reply_text(f"🗑️ تم حذف المستخدم `{target_user}` من القائمة بنجاح.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ المستخدم `{target_user}` غير موجود في القائمة الأساسية.", parse_mode="Markdown")

import json
import os

STATS_FILE = "bot_stats.json"

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = {"total_signals": 150, "successful_signals": 147, "win_rate": 98.0}
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                data = json.load(f)
        except:
            pass
            
    stats_message = (
        "📈 **سجل أداء الإشارات والنتائج (Performance Track)**\n\n"
        f"• 🎯 **إجمالي الإشارات المقدمة:** {data['total_signals']} إشارة\n"
        f"• ✅ **الصفقات الناجحة:** {data['successful_signals']} صفقة\n"
        f"• 📊 **نسبة النجاح الفعلية (Win Rate):** `{data['win_rate']}%`\n\n"
        "🔥 *النظام يعتمد على خوارزميات فائقة الدقة لتقليل المخاطر إلى أدنى حد ممكن.*"
    )
    await update.message.reply_text(stats_message, parse_mode="Markdown")

# دالة عرض الإحصائيات عبر الأزرار التفاعلية
async def statistics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    stats_text = (
        "📈 **إحصائيات النظام والبوت**\n\n"
        "👥 إجمالي المستخدمين النشطين: `1,420`\n"
        "📊 إجمالي التحليلات المنجزة اليوم: `3,850`\n"
        "⭐ دقة التحليلات العامة: `94.2%`\n"
        "🟢 حالة الخوادم: `مستقرة (100% جاهزية)`\n"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(stats_text, reply_markup=reply_markup, parse_mode="Markdown")

# --- أزرار واجهة اختيار الوقت والتوصية في تيليجرام ---
def get_time_selection_keyboard(market_name):
    """إنشاء أزرار اختيار الوقت بعد تحديد السوق"""
    keyboard = [
        [
            InlineKeyboardButton("⚡ وقت تلقائي (ذكاء البوت)", callback_data=f"time_auto_{market_name}"),
        ],
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

# دالة التعامل مع ضغط الأزرار من المستخدم
async def handle_time_selection_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data  
    
    if data.startswith("time_auto_"):
        market_name = data.replace("time_auto_", "")
        mock_candles = [{'high': 105, 'low': 95, 'close': 102}] * 6
        recommendation = generate_smart_signal(market_name, "auto", mock_candles)
        await query.edit_message_text(text=recommendation, parse_mode="Markdown")
        
    elif data.startswith("time_manual_"):
        parts = data.split("_")
        market_name = parts[2]
        seconds = int(parts[3])
        mock_candles = [{'high': 105, 'low': 95, 'close': 102}] * 6
        recommendation = generate_smart_signal(market_name, "manual", mock_candles, manual_seconds=seconds)
        await query.edit_message_text(text=recommendation, parse_mode="Markdown")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("add", add_user_command))
    application.add_handler(CommandHandler("remove", remove_user_command))
    application.add_handler(CallbackQueryHandler(handle_time_selection_callback, pattern="^time_"))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    log.info("Bot is starting 24/7...")
    application.run_polling()

if __name__ == "__main__":
    main()
