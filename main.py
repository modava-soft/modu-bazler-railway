# -*- coding: utf-8 -*-
# Modu Bazler v5.2 – نسخه‌ی پایدار با تضمین اجرای سیکل‌ها و تنظیم کندل‌ها

import os, json, time, threading, datetime as dt
import requests, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image
import telebot
from telebot import types

# =========================
# مسیرها و کانفیگ
# =========================

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config_v5_2.json")

DEFAULT_CONFIG = {
    "symbols_1h": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT"
    ],
    "symbols_4h": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT"
    ],
    "symbols_1d": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT"
    ],
    "symbols_15m": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT","ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT",
        "OPUSDT","ARBUSDT","SUIUSDT","PEPEUSDT","TONUSDT","UNIUSDT","AAVEUSDT","INJUSDT","RNDRUSDT","FTMUSDT",
        "NEOUSDT","GALAUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","JTOUSDT","WIFUSDT","JUPUSDT","STRKUSDT","BLURUSDT",
        "RUNEUSDT","RAYUSDT","LDOUSDT","COMPUSDT","CRVUSDT","MKRUSDT","SNXUSDT","GMXUSDT","DYDXUSDT","ENSUSDT"
    ],

    # تعداد کندل نمایش (مضربی از ۲۰)
    "max_bars_1h": 80,   # پیش‌فرض ۸۰
    "max_bars_4h": 60,   # پیش‌فرض ۶۰
    "max_bars_1d": 60,   # پیش‌فرض ۶۰
    "max_bars_15m": 40,  # پیش‌فرض ۴۰

    # تعداد کندل برای محاسبات SMA/WMA/RSI/MACD (ثابت ۵۰۰)
    "calc_bars": 500,

    "alarm_wma_direction": True,
    "alarm_cross_sma20": False,
    "alarm_cross_sma100": False,
    "alarm_cross_sma200": False,
    "alarm_sma20_direction": False,
    "alarm_sma100_direction": False,
    "alarm_sma200_direction": False,

    "make_pdf_1h": True,
    "make_pdf_1d": True,
    "make_combined_15m": True,

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,

    "verbose_1h": True,
    "verbose_4h": True,
    "verbose_1d": True,
    "verbose_15m": True,

    # پیش‌فرض گزارشات
    "cycle_progress_batch": 15
}

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def reset_config():
    cfg = DEFAULT_CONFIG.copy()
    save_config(cfg)
    return cfg

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

# =========================
# توکن‌ها و ربات‌ها
# =========================

TOKEN_1H   = (os.getenv("TOKEN_1H") or "").strip()
TOKEN_4H   = (os.getenv("TOKEN_4H") or "").strip()
TOKEN_1D   = (os.getenv("TOKEN_1D") or "").strip()
TOKEN_15M  = (os.getenv("TOKEN_15M") or "").strip()
ADMIN_CHAT = (os.getenv("ADMIN_CHAT_ID") or "").strip()

def create_bot(token: str):
    if not token or not isinstance(token, str):
        return None
    if any(ch.isspace() for ch in token):
        return None
    try:
        return telebot.TeleBot(token, parse_mode="HTML")
    except:
        return None

bot_1h  = create_bot(TOKEN_1H)
bot_4h  = create_bot(TOKEN_4H)
bot_1d  = create_bot(TOKEN_1D)
bot_15m = create_bot(TOKEN_15M)

LAST_ALARMS = {
    "1h": [],
    "4h": [],
    "1d": [],
    "15m": []
}

CYCLE_LOCKS = {
    "1h": threading.Lock(),
    "4h": threading.Lock(),
    "1d": threading.Lock(),
    "15m": threading.Lock()
}

# =========================
# راهنما
# =========================

HELP_TEXT = """
Modu Bazler v5.2 – نسخه‌ی پایدار

📌 ربات‌ها:
- 1h: ربات اصلی مدیریت و منو
- 4h: ربات ۴ساعته
- 1d: ربات روزانه
- 15m: ربات ۱۵دقیقه‌ای

✅ ثبت چت هر ربات:
- در هر ربات دستور /start را بفرست تا chat_id ثبت شود.

🧭 منوی ربات 1h:
- چک یک نماد → بررسی پیشرفته یک نماد در 1h
- اجرای دستی 1h → اجرای کامل سیکل 1h
- اجرای فوری 4h / 1d / 15m → اجرای فوری سیکل هر تایم‌فریم
- اجرای چرخه‌ها → اجرای همه سیکل‌ها با فاصله ۵ دقیقه
- مدیریت نمادهای 1h / 4h / 1d / 15m → افزودن/حذف نمادها
- تنظیم آلارم‌ها → فعال/غیرفعال کردن انواع آلارم‌ها
- گزارش آلارم‌ها → نمایش آخرین آلارم‌ها
- پاک کردن آلارم‌ها → خالی کردن لیست آلارم‌ها
- تنظیمات کندل‌ها → تنظیم تعداد کندل نمایش (مضربی از ۲۰)
- وضعیت سیستم → نمایش تنظیمات و تعداد نمادها
- تنظیمات پیشرفته → کنترل PDF و verbose
- ریست برنامه → پاک‌سازی کامل و بازگشت به تنظیمات اولیه
- راهنما / رفرش منو → نمایش راهنما و منوی اصلی

🔊 حالت پردازش (verbose):
- ON → پیام‌های پردازش + نمودار همه‌ی نمادها
- OFF → فقط نمودار نمادهای دارای آلارم

📄 PDF:
- برای سیکل‌های 1h و 1d در صورت فعال بودن، یک فایل PDF از همه‌ی نمودارها ساخته و ارسال می‌شود.

⏱ اجرای چرخه‌ها:
- اجرای چرخه‌ها در منوی اصلی → اجرای 1h، سپس 4h، سپس 1d، سپس 15m با فاصله ۵ دقیقه بین هر سیکل.
"""

# =========================
# منوی اصلی ربات 1h
# =========================

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("چک یک نماد", "اجرای دستی 1h")
    kb.row("اجرای فوری 4h", "اجرای فوری 1d")
    kb.row("اجرای فوری 15m")
    kb.row("اجرای چرخه‌ها")
    kb.row("مدیریت نمادهای 1h", "مدیریت نمادهای 4h")
    kb.row("مدیریت نمادهای 1d", "مدیریت نمادهای 15m")
    kb.row("تنظیم آلارم‌ها", "گزارش آلارم‌ها")
    kb.row("پاک کردن آلارم‌ها")
    kb.row("تنظیمات کندل‌ها", "وضعیت سیستم")
    kb.row("تنظیمات پیشرفته", "ریست برنامه")
    kb.row("راهنما", "رفرش منو")
    bot_1h.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

@bot_1h.message_handler(commands=["start"])
def start_main(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    bot_1h.send_message(m.chat.id, HELP_TEXT)
    send_main_menu(m.chat.id)

@bot_1h.message_handler(commands=["refresh"])
@bot_1h.message_handler(func=lambda m: m.text == "رفرش منو")
def refresh_main(m):
    send_main_menu(m.chat.id)

# =========================
# استارت سایر ربات‌ها
# =========================

if bot_4h:
    @bot_4h.message_handler(commands=["start"])
    def start_4h(m):
        cfg = load_config()
        cfg["chat_id_4h"] = m.chat.id
        save_config(cfg)
        bot_4h.send_message(m.chat.id, "ربات ۴ساعته فعال شد.\n" + now_utc_str())

if bot_1d:
    @bot_1d.message_handler(commands=["start"])
    def start_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        bot_1d.send_message(m.chat.id, "ربات روزانه فعال شد.\n" + now_utc_str())

if bot_15m:
    @bot_15m.message_handler(commands=["start"])
    def start_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        bot_15m.send_message(m.chat.id, "ربات ۱۵دقیقه‌ای فعال شد.\n" + now_utc_str())

# =========================
# ریست برنامه
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "ریست برنامه")
def reset_app(m):
    cfg = reset_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    # پاک کردن آلارم‌ها
    for g in LAST_ALARMS:
        LAST_ALARMS[g] = []
    bot_1h.send_message(m.chat.id, "برنامه و تنظیمات کامل ریست شد.\nهمه آلارم‌ها پاک شدند.")
    send_main_menu(m.chat.id)

# =========================
# مدیریت نمادها
# =========================

def get_symbols(cfg, group):
    return cfg[f"symbols_{group}"]

def set_symbols(cfg, group, symbols):
    cfg[f"symbols_{group}"] = symbols
    save_config(cfg)

def show_symbol_menu(chat_id, group):
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    txt = f"نمادهای فعال در {group}:\n"
    txt += ", ".join(symbols) if symbols else "هیچ نمادی ثبت نشده است."
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(f"افزودن نماد به {group}", f"حذف نماد از {group}")
    kb.row(f"نمایش نمادهای {group}")
    kb.row("بازگشت به منوی اصلی")
    bot_1h.send_message(chat_id, txt, reply_markup=kb)

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1h")
def manage_1h(m): show_symbol_menu(m.chat.id, "1h")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 4h")
def manage_4h(m): show_symbol_menu(m.chat.id, "4h")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1d")
def manage_1d(m): show_symbol_menu(m.chat.id, "1d")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 15m")
def manage_15m(m): show_symbol_menu(m.chat.id, "15m")

@bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
def back_to_main(m):
    send_main_menu(m.chat.id)

def add_symbol_step(m, group):
    symbol = m.text.strip().upper()
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    if symbol not in symbols:
        symbols.append(symbol)
        set_symbols(cfg, group, symbols)
        bot_1h.send_message(m.chat.id, f"{symbol} به لیست {group} اضافه شد.")
    else:
        bot_1h.send_message(m.chat.id, f"{symbol} قبلاً در لیست {group} وجود دارد.")
    show_symbol_menu(m.chat.id, group)

@bot_1h.message_handler(func=lambda m: m.text.startswith("افزودن نماد به "))
def add_symbol_any(m):
    group = m.text.split()[-1]
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید:")
    bot_1h.register_next_step_handler(msg, lambda mm: add_symbol_step(mm, group))

def remove_symbol_step(m, group):
    symbol = m.text.strip().upper()
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    if symbol in symbols:
        symbols.remove(symbol)
        set_symbols(cfg, group, symbols)
        bot_1h.send_message(m.chat.id, f"{symbol} از لیست {group} حذف شد.")
    else:
        bot_1h.send_message(m.chat.id, f"{symbol} در لیست {group} وجود ندارد.")
    show_symbol_menu(m.chat.id, group)

@bot_1h.message_handler(func=lambda m: m.text.startswith("حذف نماد از "))
def remove_symbol_any(m):
    group = m.text.split()[-1]
    msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید:")
    bot_1h.register_next_step_handler(msg, lambda mm: remove_symbol_step(mm, group))

@bot_1h.message_handler(func=lambda m: m.text.startswith("نمایش نمادهای "))
def show_symbols_any(m):
    group = m.text.split()[-1]
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    txt = f"نمادهای {group}:\n"
    txt += ", ".join(symbols) if symbols else "هیچ نمادی ثبت نشده است."
    bot_1h.send_message(m.chat.id, txt)

# =========================
# تنظیم آلارم‌ها
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "تنظیم آلارم‌ها")
def alarms_menu(m):
    cfg = load_config()
    kb = types.InlineKeyboardMarkup()
    for key in [
        "alarm_wma_direction",
        "alarm_cross_sma20",
        "alarm_cross_sma100",
        "alarm_cross_sma200",
        "alarm_sma20_direction",
        "alarm_sma100_direction",
        "alarm_sma200_direction"
    ]:
        kb.add(types.InlineKeyboardButton(
            f"{key} ({'ON' if cfg.get(key) else 'OFF'})",
            callback_data=f"alarm_{key}"
        ))
    bot_1h.send_message(m.chat.id, "آلارم‌ها را تنظیم کنید:", reply_markup=kb)

@bot_1h.callback_query_handler(func=lambda c: c.data.startswith("alarm_"))
def toggle_alarm(c):
    cfg = load_config()
    key = c.data.replace("alarm_", "")
    cfg[key] = not cfg.get(key)
    save_config(cfg)
    bot_1h.answer_callback_query(c.id, f"{key} -> {'ON' if cfg[key] else 'OFF'}")
    alarms_menu(c.message)

@bot_1h.message_handler(func=lambda m: m.text == "گزارش آلارم‌ها")
def alarms_report(m):
    txt = ""
    for group in ["1h","4h","1d","15m"]:
        if LAST_ALARMS[group]:
            txt += f"آلارم‌های {group}:\n"
            for item in LAST_ALARMS[group]:
                txt += f"{item['symbol']} ({item['interval']}):\n"
                for a in item["alarms"]:
                    txt += f" - {a}\n"
                txt += f"زمان: {item['time']}\n\n"
    if not txt:
        txt = "هیچ آلارمی ثبت نشده است."
    bot_1h.send_message(m.chat.id, txt)

@bot_1h.message_handler(func=lambda m: m.text == "پاک کردن آلارم‌ها")
def clear_alarms(m):
    for g in LAST_ALARMS:
        LAST_ALARMS[g] = []
    bot_1h.send_message(m.chat.id, "همه آلارم‌ها پاک شدند.")

# =========================
# وضعیت سیستم و تنظیمات پیشرفته
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "وضعیت سیستم")
def system_status(m):
    cfg = load_config()
    txt = "وضعیت سیستم:\n"
    txt += f"نمادهای 1h: {len(cfg['symbols_1h'])}\n"
    txt += f"نمادهای 4h: {len(cfg['symbols_4h'])}\n"
    txt += f"نمادهای 1d: {len(cfg['symbols_1d'])}\n"
    txt += f"نمادهای 15m: {len(cfg['symbols_15m'])}\n"
    txt += f"max_bars_1h: {cfg['max_bars_1h']}\n"
    txt += f"max_bars_4h: {cfg['max_bars_4h']}\n"
    txt += f"max_bars_1d: {cfg['max_bars_1d']}\n"
    txt += f"max_bars_15m: {cfg['max_bars_15m']}\n"
    txt += f"calc_bars (محاسبات): {cfg['calc_bars']}\n"
    txt += f"PDF 1h: {'ON' if cfg['make_pdf_1h'] else 'OFF'}\n"
    txt += f"PDF 1d: {'ON' if cfg['make_pdf_1d'] else 'OFF'}\n"
    txt += f"Combined 15m: {'ON' if cfg.get('make_combined_15m', True) else 'OFF'}\n"
    txt += f"verbose 1h: {'ON' if cfg['verbose_1h'] else 'OFF'}\n"
    txt += f"verbose 4h: {'ON' if cfg['verbose_4h'] else 'OFF'}\n"
    txt += f"verbose 1d: {'ON' if cfg['verbose_1d'] else 'OFF'}\n"
    txt += f"verbose 15m: {'ON' if cfg['verbose_15m'] else 'OFF'}\n"
    txt += f"cycle_progress_batch: {cfg['cycle_progress_batch']}\n"
    bot_1h.send_message(m.chat.id, txt)

@bot_1h.message_handler(func=lambda m: m.text == "تنظیمات پیشرفته")
def advanced_settings(m):
    cfg = load_config()
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"PDF 1h ({'ON' if cfg['make_pdf_1h'] else 'OFF'})", callback_data="adv_pdf_1h"))
    kb.add(types.InlineKeyboardButton(f"PDF 1d ({'ON' if cfg['make_pdf_1d'] else 'OFF'})", callback_data="adv_pdf_1d"))
    kb.add(types.InlineKeyboardButton(f"Combined 15m ({'ON' if cfg.get('make_combined_15m', True) else 'OFF'})", callback_data="adv_combined_15m"))
    kb.add(types.InlineKeyboardButton(f"verbose 1h ({'ON' if cfg['verbose_1h'] else 'OFF'})", callback_data="adv_verbose_1h"))
    kb.add(types.InlineKeyboardButton(f"verbose 4h ({'ON' if cfg['verbose_4h'] else 'OFF'})", callback_data="adv_verbose_4h"))
    kb.add(types.InlineKeyboardButton(f"verbose 1d ({'ON' if cfg['verbose_1d'] else 'OFF'})", callback_data="adv_verbose_1d"))
    kb.add(types.InlineKeyboardButton(f"verbose 15m ({'ON' if cfg['verbose_15m'] else 'OFF'})", callback_data="adv_verbose_15m"))
    kb.add(types.InlineKeyboardButton("ریست کامل برنامه", callback_data="adv_reset_app"))
    bot_1h.send_message(m.chat.id, "تنظیمات پیشرفته:", reply_markup=kb)

@bot_1h.callback_query_handler(func=lambda c: c.data.startswith("adv_"))
def advanced_settings_handler(c):
    cfg = load_config()
    if c.data == "adv_pdf_1h":
        cfg["make_pdf_1h"] = not cfg["make_pdf_1h"]
    elif c.data == "adv_pdf_1d":
        cfg["make_pdf_1d"] = not cfg["make_pdf_1d"]
    elif c.data == "adv_combined_15m":
        cfg["make_combined_15m"] = not cfg.get("make_combined_15m", True)
    elif c.data == "adv_verbose_1h":
        cfg["verbose_1h"] = not cfg["verbose_1h"]
    elif c.data == "adv_verbose_4h":
        cfg["verbose_4h"] = not cfg["verbose_4h"]
    elif c.data == "adv_verbose_1d":
        cfg["verbose_1d"] = not cfg["verbose_1d"]
    elif c.data == "adv_verbose_15m":
        cfg["verbose_15m"] = not cfg["verbose_15m"]
    elif c.data == "adv_reset_app":
        cfg = reset_config()
    save_config(cfg)
    bot_1h.answer_callback_query(c.id, "تنظیمات اعمال شد.")
    advanced_settings(c.message)

# =========================
# تنظیمات کندل‌ها (مضربی از ۲۰)
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "تنظیمات کندل‌ها")
def candle_settings_menu(m):
    cfg = load_config()
    txt = "تنظیمات تعداد کندل نمایش (مضربی از ۲۰):\n"
    txt += f"1h: {cfg['max_bars_1h']}\n"
    txt += f"4h: {cfg['max_bars_4h']}\n"
    txt += f"1d: {cfg['max_bars_1d']}\n"
    txt += f"15m: {cfg['max_bars_15m']}\n\n"
    txt += "یک تایم‌فریم را انتخاب کنید:"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("کندل‌های 1h", "کندل‌های 4h")
    kb.row("کندل‌های 1d", "کندل‌های 15m")
    kb.row("بازگشت به منوی اصلی")
    bot_1h.send_message(m.chat.id, txt, reply_markup=kb)

def set_candles_for_group(m, group_key):
    msg = bot_1h.send_message(m.chat.id, "تعداد کندل را وارد کنید (مضربی از ۲۰، مثلاً ۴۰، ۶۰، ۸۰):")
    bot_1h.register_next_step_handler(msg, lambda mm: _candles_value_step(mm, group_key))

def _candles_value_step(m, group_key):
    val_text = m.text.strip()
    try:
        val = int(val_text)
        if val <= 0 or val % 20 != 0:
            raise ValueError
    except:
        bot_1h.send_message(m.chat.id, "عدد نامعتبر است. باید مضربی از ۲۰ و بزرگ‌تر از صفر باشد.")
        candle_settings_menu(m)
        return
    cfg = load_config()
    cfg[group_key] = val
    save_config(cfg)
    bot_1h.send_message(m.chat.id, f"تعداد کندل {group_key} روی {val} تنظیم شد.")
    candle_settings_menu(m)

@bot_1h.message_handler(func=lambda m: m.text == "کندل‌های 1h")
def set_candles_1h(m):
    set_candles_for_group(m, "max_bars_1h")

@bot_1h.message_handler(func=lambda m: m.text == "کندل‌های 4h")
def set_candles_4h(m):
    set_candles_for_group(m, "max_bars_4h")

@bot_1h.message_handler(func=lambda m: m.text == "کندل‌های 1d")
def set_candles_1d(m):
    set_candles_for_group(m, "max_bars_1d")

@bot_1h.message_handler(func=lambda m: m.text == "کندل‌های 15m")
def set_candles_15m(m):
    set_candles_for_group(m, "max_bars_15m")

# =========================
# راهنما
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "راهنما")
def help_menu(m):
    bot_1h.send_message(m.chat.id, HELP_TEXT)

# =========================
# دیتا، اندیکاتورها، نمودار
# =========================

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str) -> str:
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

def fetch_ohlc(symbol: str, interval: str, calc_bars: int) -> pd.DataFrame:
    limit = max(500, calc_bars)  # حداقل ۵۰۰ کندل برای محاسبات
    try:
        url = "https://api.binance.com/api/v3/klines"
        r = requests.get(url, params={
            "symbol": symbol,
            "interval": _binance_interval(interval),
            "limit": limit
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        rows = [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in data]
        df = pd.DataFrame(rows, columns=["t","o","h","l","c","v"])
        df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
        df.set_index("t", inplace=True)
        return df
    except:
        pass
    try:
        sym = symbol.replace("USDT", "-USDT")
        end = int(now_utc().timestamp())
        start = end - 60 * 60 * (limit + 10)
        url = "https://api.kucoin.com/api/v1/market/candles"
        r = requests.get(url, params={
            "symbol": sym,
            "type": _kucoin_interval(interval),
            "startAt": start,
            "endAt": end
        }, timeout=10)
        r.raise_for_status()
        data = r.json()["data"]
        rows = [[int(k[0]), float(k[1]), float(k[3]), float(k[4]), float(k[2]), float(k[5])] for k in data]
        df = pd.DataFrame(rows, columns=["t","o","h","l","c","v"])
        df["t"] = pd.to_datetime(df["t"], unit="s", utc=True)
        df.sort_values("t", inplace=True)
        df.set_index("t", inplace=True)
        return df
    except:
        return pd.DataFrame()

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df
    df["SMA20"]  = df["c"].rolling(20).mean()
    df["SMA100"] = df["c"].rolling(100).mean()
    df["SMA200"] = df["c"].rolling(200).mean()
    df["WMA20"] = df["c"].rolling(20).apply(lambda x: np.average(x, weights=np.arange(1, len(x)+1)), raw=True)
    df["WMA20_slope"] = df["WMA20"].diff()
    delta = df["c"].diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_gain = pd.Series(gain, index=df.index).rolling(14).mean()
    roll_loss = pd.Series(loss, index=df.index).rolling(14).mean()
    rs = roll_gain / (roll_loss + 1e-9)
    df["RSI14"] = 100 - (100 / (1 + rs))
    ema12 = df["c"].ewm(span=12, adjust=False).mean()
    ema26 = df["c"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    return df

def create_plotly_chart(symbol: str, interval: str, max_bars: int, calc_bars: int, png_name: str):
    df_raw = fetch_ohlc(symbol, interval, calc_bars)
    if df_raw.empty:
        df_raw = pd.DataFrame(columns=["o","h","l","c","v"])
        df_raw.index = pd.to_datetime([])
    df_ind = compute_indicators(df_raw)
    # نمایش فقط آخرین max_bars کندل، محاسبات روی کل df_ind (حداقل ۵۰۰)
    df_plot = df_ind.tail(max_bars)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6,0.2,0.2], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot["o"], high=df_plot["h"], low=df_plot["l"], close=df_plot["c"], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["SMA20"],  mode="lines", name="SMA20",  line=dict(color="blue")),   row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["SMA100"], mode="lines", name="SMA100", line=dict(color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["SMA200"], mode="lines", name="SMA200", line=dict(color="purple")), row=1, col=1)

    wma   = df_plot["WMA20"]
    slope = df_plot["WMA20_slope"]
    wma_up   = wma.where(slope >= 0)
    wma_down = wma.where(slope < 0)
    fig.add_trace(go.Scatter(x=df_plot.index, y=wma_up,   mode="lines", name="WMA20 Up",   line=dict(color="green", width=2, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=wma_down, mode="lines", name="WMA20 Down", line=dict(color="red",   width=2, dash="dot")), row=1, col=1)

    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["RSI14"], mode="lines", name="RSI14", line=dict(color="brown")), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="red", dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="green", dash="dash"), row=2, col=1)

    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["MACD"],        mode="lines", name="MACD",   line=dict(color="black")),   row=3, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["MACD_signal"], mode="lines", name="Signal", line=dict(color="magenta")), row=3, col=1)
    fig.add_trace(go.Bar(x=df_plot.index, y=df_plot["MACD_hist"], name="Hist", marker_color="gray"), row=3, col=1)

    fig.update_layout(title=f"{symbol} – {interval}", xaxis_rangeslider_visible=False, template="plotly_white", height=1000)
    fig.add_annotation(text=f"{symbol} – {interval}", xref="paper", yref="paper", x=0.5, y=1.05, showarrow=False, font=dict(size=30, color="black"))
    fig.update_yaxes(side="right", showgrid=True)

    png_path = os.path.join(CHARTS_DIR, png_name)
    try:
        fig.write_image(png_path, width=1800, height=1100, scale=3)
    except:
        pass

    # برای آلارم‌ها از کل df_ind استفاده می‌کنیم (نه فقط df_plot)
    return {
        "symbol": symbol,
        "interval": interval,
        "png_path": png_path,
        "created_at": now_utc_str(),
        "wma": df_ind["WMA20"].tolist() if "WMA20" in df_ind.columns else [],
        "wma_slope": df_ind["WMA20_slope"].tolist() if "WMA20_slope" in df_ind.columns else [],
        "sma20": df_ind["SMA20"].tolist() if "SMA20" in df_ind.columns else [],
        "sma100": df_ind["SMA100"].tolist() if "SMA100" in df_ind.columns else [],
        "sma200": df_ind["SMA200"].tolist() if "SMA200" in df_ind.columns else []
    }

def detect_alarms(cfg: dict, info: dict, group: str):
    alarms = []
    wma    = info["wma"]
    slope  = info["wma_slope"]
    sma20  = info["sma20"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]
    if len(wma) < 3:
        return alarms
    if cfg.get("alarm_wma_direction", True):
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("WMA20 جهت رو به بالا گرفت")
        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("WMA20 جهت رو به پایین گرفت")
    def cross(a, b):
        if len(a) < 2 or len(b) < 2:
            return False
        return (a[-2] - b[-2]) * (a[-1] - b[-1]) < 0
    if cfg.get("alarm_cross_sma20", False) and cross(wma, sma20):
        alarms.append("برخورد WMA20 با SMA20")
    if cfg.get("alarm_cross_sma100", False) and cross(wma, sma100):
        alarms.append("برخورد WMA20 با SMA100")
    if cfg.get("alarm_cross_sma200", False) and cross(wma, sma200):
        alarms.append("برخورد WMA20 با SMA200")
    def dir_change(arr, name):
        if len(arr) < 3:
            return
        d1 = arr[-1] - arr[-2]
        d2 = arr[-2] - arr[-3]
        if d2 < 0 and d1 > 0:
            alarms.append(f"{name} جهت رو به بالا گرفت")
        if d2 > 0 and d1 < 0:
            alarms.append(f"{name} جهت رو به پایین گرفت")
    if cfg.get("alarm_sma20_direction", False):
        dir_change(sma20, "SMA20")
    if cfg.get("alarm_sma100_direction", False):
        dir_change(sma100, "SMA100")
    if cfg.get("alarm_sma200_direction", False):
        dir_change(sma200, "SMA200")
    if alarms:
        LAST_ALARMS[group] = [{
            "symbol": info["symbol"],
            "interval": info["interval"],
            "time": info["created_at"],
            "alarms": alarms
        }]
    return alarms

def make_15m_combined_pages(jpg_paths: list) -> list:
    pages = []
    page_w, page_h = 1800, 1400
    cell_w, cell_h = page_w // 4, page_h // 3

    for i in range(0, len(jpg_paths), 12):
        chunk = jpg_paths[i:i+12]
        page = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        idx = 0
        for r in range(3):
            for c in range(4):
                if idx < len(chunk):
                    img = Image.open(chunk[idx]).convert("RGB")
                    img = img.resize((cell_w, cell_h), Image.LANCZOS)
                    x = c * cell_w
                    y = r * cell_h
                    page.paste(img, (x, y))
                    idx += 1
        out_name = f"15m_combined_{i//12 + 1}.jpg"
        out_path = os.path.join(CHARTS_DIR, out_name)
        page.save(out_path, format="JPEG", quality=95)
        pages.append(out_path)

    return pages

# =========================
# اجرای سیکل‌ها با قفل (دو روش: معمولی و اجباری)
# =========================

def run_cycle(group: str, bot, chat_id: int, symbols: list, interval: str, max_bars: int, make_pdf: bool, force_lock: bool = False):
    """
    اگر force_lock=True باشد، قفل به صورت blocking گرفته می‌شود تا حتماً سیکل اجرا شود.
    اگر False باشد، در صورت مشغول بودن قفل، سیکل اجرا نمی‌شود (برای زمان‌بندی خودکار).
    """
    lock = CYCLE_LOCKS.get(group)
    if lock is None:
        return

    if force_lock:
        lock.acquire(blocking=True)
    else:
        if not lock.acquire(blocking=False):
            # اگر قفل مشغول است، برای اطمینان یک بار دیگر با تاخیر تلاش می‌کنیم
            time.sleep(2)
            if not lock.acquire(blocking=False):
                return

    combined_jpgs = []

    try:
        cfg = load_config()
        verbose = cfg.get(f"verbose_{group}", True)
        calc_bars = cfg.get("calc_bars", 500)

        if chat_id is None:
            return

        if verbose:
            bot.send_message(chat_id, f"شروع چرخه {group}\n{now_utc_str()} UTC")

        unique_symbols = list(dict.fromkeys(symbols))
        total = len(unique_symbols)
        processed = 0
        batch_size = cfg.get("cycle_progress_batch", 15)

        pdf = None
        pdf_filename = None

        if make_pdf and group in ["1h", "1d"]:
            pdf_filename = os.path.join(PDF_DIR, f"{group}_{now_utc().strftime('%Y%m%d_%H%M%S')}.pdf")
            pdf = PdfPages(pdf_filename)

        for sym in unique_symbols:
            processed += 1

            if verbose and (processed % batch_size == 0 or processed == 1 or processed == total):
                bot.send_message(chat_id, f"چرخه {group}: {processed}/{total} نماد، {total - processed} باقی مانده.")

            ts = now_utc().strftime("%Y%m%d_%H%M%S")
            png = f"{group}_{sym}_{ts}.png"

            info = create_plotly_chart(sym, interval, max_bars, calc_bars, png)
            alarms = detect_alarms(cfg, info, group)

            if group == "15m":
                try:
                    img = Image.open(info["png_path"]).convert("RGB")
                    jpg_name = os.path.splitext(os.path.basename(info["png_path"]))[0] + ".jpg"
                    jpg_path = os.path.join(CHARTS_DIR, jpg_name)
                    img.save(jpg_path, format="JPEG", quality=95)
                    combined_jpgs.append(jpg_path)
                except:
                    pass

            if verbose or alarms:
                caption = f"{sym} ({group})"
                if alarms:
                    caption += "\n" + "\n".join(alarms)
                else:
                    caption += " – بدون آلارم"

                try:
                    with open(info["png_path"], "rb") as f:
                        bot.send_photo(chat_id, f, caption=caption)
                except:
                    pass

            if pdf is not None:
                try:
                    img = plt.imread(info["png_path"])
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.imshow(img)
                    ax.axis("off")
                    ax.set_title(f"{sym} – {group}")
                    pdf.savefig(fig)
                    plt.close(fig)
                except:
                    pass

            time.sleep(0.3)

        if pdf is not None:
            try:
                pdf.close()
                with open(pdf_filename, "rb") as f:
                    bot.send_document(chat_id, f, caption=f"گزارش PDF کامل سیکل {group}")
            except:
                pass

        if group == "15m":
            cfg = load_config()
            if cfg.get("make_combined_15m", True) and combined_jpgs:
                pages = make_15m_combined_pages(combined_jpgs)
                for p in pages:
                    try:
                        with open(p, "rb") as f:
                            bot.send_photo(chat_id, f, caption="صفحهٔ ترکیبی ۱۵دقیقه‌ای")
                    except:
                        pass

        if verbose:
            bot.send_message(chat_id, f"پایان چرخه {group}\n{now_utc_str()} UTC")

    finally:
        lock.release()

# =========================
# اجرای فوری و اجرای چرخه‌ها
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "اجرای دستی 1h")
def manual_1h(m):
    cfg = load_config()
    chat_id = cfg.get("chat_id_1h") or m.chat.id
    symbols = cfg["symbols_1h"]
    max_bars = cfg["max_bars_1h"]
    run_cycle("1h", bot_1h, chat_id, symbols, "1h", max_bars, cfg["make_pdf_1h"], force_lock=True)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 4h")
def manual_4h(m):
    cfg = load_config()
    chat_id = cfg.get("chat_id_4h") or cfg.get("chat_id_1h") or m.chat.id
    symbols = cfg["symbols_4h"]
    max_bars = cfg["max_bars_4h"]
    run_cycle("4h", bot_4h or bot_1h, chat_id, symbols, "4h", max_bars, False, force_lock=True)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 1d")
def manual_1d(m):
    cfg = load_config()
    chat_id = cfg.get("chat_id_1d") or cfg.get("chat_id_1h") or m.chat.id
    symbols = cfg["symbols_1d"]
    max_bars = cfg["max_bars_1d"]
    run_cycle("1d", bot_1d or bot_1h, chat_id, symbols, "1d", max_bars, cfg["make_pdf_1d"], force_lock=True)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 15m")
def manual_15m(m):
    cfg = load_config()
    chat_id = cfg.get("chat_id_15m") or cfg.get("chat_id_1h") or m.chat.id
    symbols = cfg["symbols_15m"]
    max_bars = cfg["max_bars_15m"]
    run_cycle("15m", bot_15m or bot_1h, chat_id, symbols, "15m", max_bars, False, force_lock=True)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای چرخه‌ها")
def run_all_cycles(m):
    """
    اجرای همه سیکل‌ها با فاصله ۵ دقیقه بین هر سیکل.
    برای اطمینان از اجرای حتمی، از force_lock=True استفاده می‌کنیم.
    """
    cfg = load_config()
    chat_1h  = cfg.get("chat_id_1h")  or m.chat.id
    chat_4h  = cfg.get("chat_id_4h")  or chat_1h
    chat_1d  = cfg.get("chat_id_1d")  or chat_1h
    chat_15m = cfg.get("chat_id_15m") or chat_1h

    bot_1h.send_message(chat_1h, "اجرای چرخه‌ها آغاز شد.\n1h → 4h → 1d → 15m با فاصله ۵ دقیقه.")

    def _run_seq():
        try:
            # 1h
            run_cycle("1h", bot_1h, chat_1h, cfg["symbols_1h"], "1h", cfg["max_bars_1h"], cfg["make_pdf_1h"], force_lock=True)
            time.sleep(5 * 60)

            # 4h
            run_cycle("4h", bot_4h or bot_1h, chat_4h, cfg["symbols_4h"], "4h", cfg["max_bars_4h"], False, force_lock=True)
            time.sleep(5 * 60)

            # 1d
            run_cycle("1d", bot_1d or bot_1h, chat_1d, cfg["symbols_1d"], "1d", cfg["max_bars_1d"], cfg["make_pdf_1d"], force_lock=True)
            time.sleep(5 * 60)

            # 15m
            run_cycle("15m", bot_15m or bot_1h, chat_15m, cfg["symbols_15m"], "15m", cfg["max_bars_15m"], False, force_lock=True)

            bot_1h.send_message(chat_1h, "اجرای چرخه‌ها به‌صورت کامل انجام شد.")
        except Exception as e:
            try:
                bot_1h.send_message(chat_1h, f"خطا در اجرای چرخه‌ها: {e}")
            except:
                pass

    threading.Thread(target=_run_seq, daemon=True).start()

# =========================
# چک یک نماد (اجرای تک نماد)
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "چک یک نماد")
def check_one_symbol(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("تایم‌فریم 1h", "تایم‌فریم 4h")
    kb.row("تایم‌فریم 1d", "تایم‌فریم 15m")
    kb.row("بازگشت به منوی اصلی")
    msg = bot_1h.send_message(m.chat.id, "تایم‌فریم را انتخاب کنید:", reply_markup=kb)
    bot_1h.register_next_step_handler(msg, _check_symbol_interval_step)

def _check_symbol_interval_step(m):
    tf_map = {
        "تایم‌فریم 1h": "1h",
        "تایم‌فریم 4h": "4h",
        "تایم‌فریم 1d": "1d",
        "تایم‌فریم 15m": "15m"
    }
    if m.text not in tf_map:
        send_main_menu(m.chat.id)
        return
    interval = tf_map[m.text]
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (مثلاً BTCUSDT):")
    bot_1h.register_next_step_handler(msg, lambda mm: _check_symbol_run(mm, interval))

def _check_symbol_run(m, interval):
    symbol = m.text.strip().upper()
    cfg = load_config()
    calc_bars = cfg.get("calc_bars", 500)
    max_bars_key = {
        "1h": "max_bars_1h",
        "4h": "max_bars_4h",
        "1d": "max_bars_1d",
        "15m": "max_bars_15m"
    }[interval]
    max_bars = cfg.get(max_bars_key, 80)
    ts = now_utc().strftime("%Y%m%d_%H%M%S")
    png = f"single_{interval}_{symbol}_{ts}.png"
    info = create_plotly_chart(symbol, interval, max_bars, calc_bars, png)
    alarms = detect_alarms(cfg, info, interval)
    caption = f"{symbol} ({interval})"
    if alarms:
        caption += "\n" + "\n".join(alarms)
    else:
        caption += " – بدون آلارم"
    try:
        with open(info["png_path"], "rb") as f:
            bot_1h.send_photo(m.chat.id, f, caption=caption)
    except:
        bot_1h.send_message(m.chat.id, "خطا در ارسال نمودار.")
    send_main_menu(m.chat.id)

# =========================
# حلقه‌های ربات‌ها
# =========================

def _run_bot(bot):
    if bot:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except:
            time.sleep(5)
            _run_bot(bot)

threads = []
for b in [bot_1h, bot_4h, bot_1d, bot_15m]:
    if b:
        t = threading.Thread(target=_run_bot, args=(b,), daemon=True)
        t.start()
        threads.append(t)

# نگه داشتن برنامه
while True:
    time.sleep(10)