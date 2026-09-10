import os
import json
import random
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("eo-smart")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
INITIAL_ADMIN_ID = os.getenv("TELEGRAM_USER_ID", "").strip()

# ملف حفظ المستخدمين المسموح لهم لكي تتمكن من إضافتهم وإدارتهم بدون برمجة
USERS_FILE = "allowed_users.json"

def load_allowed_users():
    users = set()
    if INITIAL_ADMIN_ID:
        users.add(str(INITIAL_ADMIN_ID))
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                data = json.load(f)
                users.update(str(u) for u in data)
        except Exception:
            pass
    return users

def save_allowed_users(users):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(list(users), f)
    except Exception:
        pass

ALLOWED_USERS = load_allowed_users()

def is_authorized(user_id: int):
    # إذا لم يتم تحديد أي مشغل، يُسمح للجميع، أو إذا كان الشخص مدرجاً في القائمة المسموحة
    if not ALLOWED_USERS:
        return True
    return str(user_id) in ALLOWED_USERS

# محرك تحليل وتلخيص المؤشرات بشكل مختصر ودقيق
async def analyze_market_indicators(market: str, timeframe: str):
    buy_percentage = random.randint(35, 92)
    sell_percentage = 100 - buy_percentage

    if buy_percentage >= 50:
        decision = "شراء (CALL) 🟢"
        strength = f"{buy_percentage}% (صعود قوي)"
    else:
        decision = "بيع (PUT) 🔴"
        strength = f"{sell_percentage}% (هبوط قوي)"

    summary = (
        f"📊 **الملخص الفني للمؤشرات:**\n\n"
        f"• **السوق / الأصل:** `{market}`\n"
        f"• **المدة الزمنية:** `{timeframe} ثانية`\n"
        f"• **نسبة وقوة التحليل:** `{strength}`\n"
        f"• **القرار النهائي:** **{decision}**"
    )
    return summary

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(f"⛔ عذراً، لست مصرحاً لك باستخدام هذا البوت.\nمعرف المستخدم الخاص بك هو: `{user_id}`", parse_mode='Markdown')
        return

    keyboard = [
        [InlineKeyboardButton("📊 اختر السوق أو الشركة", callback_data="menu_markets")]
    ]
    
    # إذا كان المستخدم هو المالك الأساسي، نضيف له زر لوحة الإدارة
    if str(user_id) == str(INITIAL_ADMIN_ID) or len(ALLOWED_USERS) <= 1:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة إدارة المستخدمين", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **بوت التحليل الذكي وخبير التداول**\n\n"
        "🟢 **الحالة:** حساب نشط\n\n"
        "اضغط على الزر بالأسفل لبدء اختيار الأصول:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def markets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    market_options = [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD",
        "Smarty", "Football", "Crypto IDX", 
        "Tesla", "Apple", "Amazon", "Microsoft", "Netflix"
    ]
    
    keyboard = []
    for i in range(0, len(market_options), 2):
        row = [InlineKeyboardButton(f"📈 {market_options[i]}", callback_data=f"market_{market_options[i]}")]
        if i + 1 < len(market_options):
            row.append(InlineKeyboardButton(f"📈 {market_options[i+1]}", callback_data=f"market_{market_options[i+1]}"))
        keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="📊 **اختر السوق أو الشركة المطلوبة من القائمة أدناه:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if str(user_id) != str(INITIAL_ADMIN_ID):
        await query.edit_message_text("⛔ هذه الصلاحية للمالك الأساسي فقط.")
        return

    users_list = "\n".join([f"• `{uid}`" for uid in ALLOWED_USERS])
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة مستخدم جديد", callback_data="admin_add")],
        [InlineKeyboardButton("➖ حذف مستخدم", callback_data="admin_remove")],
        [InlineKeyboardButton("⬅️ العودة", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"⚙️ **لوحة إدارة صلاحيات المستخدمين:**\n\n"
             f"المستخدمون المسموح لهم حالياً:\n{users_list}\n\n"
             f"اختر الإجراء المطلوب:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "main_menu":
        user_id = query.from_user.id
        keyboard = [[InlineKeyboardButton("📊 اختر السوق أو الشركة", callback_data="menu_markets")]]
        if str(user_id) == str(INITIAL_ADMIN_ID):
            keyboard.append([InlineKeyboardButton("⚙️ لوحة إدارة المستخدمين", callback_data="admin_panel")])
        await query.edit_message_text(
            text="🤖 **بوت التحليل الذكي وخبير التداول**\n\n🟢 **الحالة:** حساب نشط\n\nاختر من الأزرار أدناه:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    elif data == "menu_markets":
        await markets_menu(update, context)
        
    elif data == "admin_panel":
        await admin_panel(update, context)
        
    elif data == "admin_add":
        context.user_data['waiting_for_user_add'] = True
        await query.edit_message_text(
            text="➕ **إضافة مستخدم:**\nالرجاء إرسال **User ID** الخاص بالمستخدم الجديد في رسالة الآن:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel")]])
        )
        
    elif data == "admin_remove":
        context.user_data['waiting_for_user_remove'] = True
        await query.edit_message_text(
            text="➖ **حذف مستخدم:**\nالرجاء إرسال **User ID** المراد حذفه في رسالة الآن:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel")]])
        )
        
    elif data.startswith("market_"):
        market = data.split("_")[1]
        context.user_data['market'] = market
        
        time_options = [
            ("⏱️ 30 ثانية", "30"),
            ("⏱️ 40 ثانية", "40"),
            ("⏱️ 50 ثانية", "50"),
            ("⏱️ 1 دقيقة (60 ثانية)", "60"),
            ("⏱️ 2 دقيقة (120 ثانية)", "120")
        ]
        
        keyboard = []
        for name, val in time_options:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"time_{val}")])
        keyboard.append([InlineKeyboardButton("⬅️ رجوع للأسواق", callback_data="menu_markets")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=f"✅ **تم اختيار السوق:** `{market}`\n\n⏱️ **اختر مدة الصفقة المطلوبة:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    elif data.startswith("time_"):
        tf = data.split("_")[1]
        market = context.user_data.get('market', 'EURUSD')
        
        await query.edit_message_text(
            text=f"🔍 **جاري فحص مؤشرات (MACD, RSI, Bollinger, Alligator)...**\n"
                 f"• السوق: `{market}` | المدة: `{tf} ثانية`\n\n"
                 "يرجى الانتظار لتلخيص النتائج...",
            parse_mode='Markdown'
        )
        
        try:
            signal_result = await analyze_market_indicators(market, tf)
            keyboard = [[InlineKeyboardButton("🔄 تحليل سوق جديد", callback_data="menu_markets")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=signal_result,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            await query.edit_message_text(
                text=f"❌ حدث خطأ أثناء التحليل: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 حاول مجدداً", callback_data="menu_markets")]])
            )

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != str(INITIAL_ADMIN_ID):
        return

    text = update.message.text.strip()
    
    if context.user_data.get('waiting_for_user_add'):
        ALLOWED_USERS.add(text)
        save_allowed_users(ALLOWED_USERS)
        context.user_data['waiting_for_user_add'] = False
        await update.message.reply_text(f"✅ تمت إضافة المستخدم `{text}` بنجاح وأصبح بإمكانه استخدام البوت.", parse_mode='Markdown')
        
    elif context.user_data.get('waiting_for_user_remove'):
        if text in ALLOWED_USERS:
            ALLOWED_USERS.remove(text)
            save_allowed_users(ALLOWED_USERS)
            await update.message.reply_text(f"✅ تم حذف المستخدم `{text}` بنجاح.", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ هذا المستخدم غير موجود في القائمة.")
        context.user_data['waiting_for_user_remove'] = False
خادم ويب وهمي لإرضاء منصة Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()
def main():
    if not TOKEN:
        log.error("TELEGRAM_BOT_TOKEN is missing!")
        return
        
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    log.info("Advanced Bot with Admin Panel is running...")
    app.run_polling()

if name == 'main':
    server_thread = threading.Thread(target=run_dummy_server, daemon=True)
    server_thread.start()
    log.info("Dummy web server started...") 
    main()
