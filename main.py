# -*- coding: utf-8 -*-
# Modu Bazler v5.2 – نسخه‌ی پایدار، کامل و بدون خطای سینتکسی

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

    # تعداد کندل‌ها (مضربی از 20) – پیش‌فرض‌ها طبق خواسته‌ی تو
    "candles_1h": 80,   # 1h → 80
    "candles_4h": 60,   # 4h → 60
    "candles_1d": 60,   # 1d → 60
    "candles_15m": 40,  # 15m → 40

    # گزارش‌ها (پیش‌فرض 15)
    "reports_default": 15,

    # حداکثر بار برای دریافت دیتا
    "max_bars": 300,

    # آلارم‌ها
    "alarm_wma_direction": True,
    "alarm_cross_sma20": False,
    "alarm_cross_sma100": False,
    "alarm_cross_sma200": False,
    "alarm_sma20_direction": False,
    "alarm_sma100_direction": False,
    "alarm_sma200_direction": False,

    # PDF و ترکیبی
    "make_pdf_1h": True,
    "make_pdf_1d": True,
    "make_combined_15m": True,

    # چت‌ها
    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,

    # verbose
    "verbose_1h": True,
    "verbose_4h": True,
    "verbose_1d": True,
    "verbose_15m": True,

    # تعداد نماد برای گزارش پیشرفت
    "cycle_progress_batch": 5
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

HELP_TEXT = """
Modu Bazler v5.2 – نسخه‌ی پایدار و کامل

📌 ربات‌ها:
- 1h: ربات اصلی مدیریت و منو
- 4h: ربات ۴ساعته
- 1d: ربات روزانه
- 15m: ربات ۱۵دقیقه‌ای

✅ ثبت چت هر ربات:
- در هر ربات دستور /start را بفرست تا chat_id ثبت شود.

🧭 منوی ربات 1h:
- چک یک نماد → بررسی پیشرفته یک نماد در 1h (اجرای فوری تک نماد)
- اجرای دستی 1h → اجرای کامل سیکل 1h
- اجرای فوری 4h / 1d / 15m → اجرای فوری سیکل همان تایم‌فریم
- اجرای چرخه‌ها → اجرای فوری همه‌ی تایم‌فریم‌ها با فاصله‌ی ۵ دقیقه
- مدیریت نمادهای 1h / 4h / 1d / 15m → افزودن/حذف/نمایش نمادها
- تنظیم آلارم‌ها → فعال/غیرفعال کردن انواع آلارم‌ها
- پاک کردن آلارم‌ها → پاک کردن لیست آلارم‌های ذخیره شده
- گزارش آلارم‌ها → نمایش آخرین آلارم‌های هر گروه
- وضعیت سیستم → نمایش تنظیمات و تعداد نمادها
- تنظیمات پیشرفته → کنترل PDF، verbose و تعداد کندل‌ها (مضربی از ۲۰)
- ریست برنامه → پاک کردن همه تنظیمات و آلارم‌ها و بازگشت به پیش‌فرض‌ها

🔊 حالت پردازش (verbose):
- ON → پیام‌های پردازش + نمودار همه‌ی نمادها
- OFF → فقط نمودار نمادهای دارای آلارم، بدون پیام‌های میانی

📄 PDF:
- برای سیکل‌های 1h و 1d در صورت فعال بودن، یک فایل PDF از همه‌ی نمودارها ساخته و ارسال می‌شود.
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
    kb.row("تنظیم آلارم‌ها", "پاک کردن آلارم‌ها")
    kb.row("گزارش آلارم‌ها", "وضعیت سیستم")
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
# ریست برنامه (پاک کردن همه چیز)
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "ریست برنامه")
def reset_app(m):
    cfg = reset_config()
    cfg["chat_id_1h"] = m.chat.id
    cfg["chat_id_4h"] = None
    cfg["chat_id_1d"] = None
    cfg["chat_id_15m"] = None
    save_config(cfg)
    for k in LAST_ALARMS:
        LAST_ALARMS[k] = []
    bot_1h.send_message(m.chat.id, "برنامه و تنظیمات کامل ریست شد. همه آلارم‌ها پاک شدند.")
    send_main_menu(m.chat.id)

# =========================
# مدیریت نمادها
# =========================

def get_symbols(cfg, group):
    return cfg.get(f"symbols_{group}", [])

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
    if symbol == "بازگشت به منوی اصلی":
        send_main_menu(m.chat.id)
        return
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
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (یا 'بازگشت به منوی اصلی'):")
    bot_1h.register_next_step_handler(msg, lambda mm: add_symbol_step(mm, group))

def remove_symbol_step(m, group):
    symbol = m.text.strip().upper()
    if symbol == "بازگشت به منوی اصلی":
        send_main_menu(m.chat.id)
        return
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
    msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید (یا 'بازگشت به منوی اصلی'):")
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
# تنظیم آلارم‌ها و پاک کردن آلارم‌ها
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

@bot_1h.message_handler(func=lambda m: m.text == "پاک کردن آلارم‌ها")
def clear_alarms(m):
    for k in LAST_ALARMS:
        LAST_ALARMS[k] = []
    bot_1h.send_message(m.chat.id, "همه آلارم‌ها پاک شدند.")

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

# =========================
# وضعیت سیستم و تنظیمات پیشرفته (شامل کندل‌ها)
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "وضعیت سیستم")
def system_status(m):
    cfg = load_config()
    txt = "وضعیت سیستم:\n"
    txt += f"نمادهای 1h: {len(cfg['symbols_1h'])}\n"
    txt += f"نمادهای 4h: {len(cfg['symbols_4h'])}\n"
    txt += f"نمادهای 1d: {len(cfg['symbols_1d'])}\n"
    txt += f"نمادهای 15m: {len(cfg['symbols_15m'])}\n"
    txt += f"PDF 1h: {'ON' if cfg['make_pdf_1h'] else 'OFF'}\n"
    txt += f"PDF 1d: {'ON' if cfg['make_pdf_1d'] else 'OFF'}\n"
    txt += f"Combined 15m: {'ON' if cfg.get('make_combined_15m', True) else 'OFF'}\n"
    txt += f"verbose 1h: {'ON' if cfg['verbose_1h'] else 'OFF'}\n"
    txt += f"verbose 4h: {'ON' if cfg['verbose_4h'] else 'OFF'}\n"
    txt += f"verbose 1d: {'ON' if cfg['verbose_1d'] else 'OFF'}\n"
    txt += f"verbose 15m: {'ON' if cfg['verbose_15m'] else 'OFF'}\n"
    txt += f"candles 1h: {cfg['candles_1h']}\n"
    txt += f"candles 4h: {cfg['candles_4h']}\n"
    txt += f"candles 1d: {cfg['candles_1d']}\n"
    txt += f"candles 15m: {cfg['candles_15m']}\n"
    txt += f"reports_default: {cfg['reports_default']}\n"
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
    kb.add(types.InlineKeyboardButton(f"candles 1h ({cfg['candles_1h']})", callback_data="adv_candles_1h"))
    kb.add(types.InlineKeyboardButton(f"candles 4h ({cfg['candles_4h']})", callback_data="adv_candles_4h"))
    kb.add(types.InlineKeyboardButton(f"candles 1d ({cfg['candles_1d']})", callback_data="adv_candles_1d"))
    kb.add(types.InlineKeyboardButton(f"candles 15m ({cfg['candles_15m']})", callback_data="adv_candles_15m"))
    kb.add(types.InlineKeyboardButton(f"reports ({cfg['reports_default']})", callback_data="adv_reports"))
    kb.add(types.InlineKeyboardButton("ریست کامل برنامه", callback_data="adv_reset_app"))
    bot_1h.send_message(m.chat.id, "تنظیمات پیشرفته:", reply_markup=kb)

def _set_candles_multiple(cfg, key, value):
    try:
        v = int(value)
        if v <= 0 or v % 20 != 0:
            return False
        cfg[key] = v
        save_config(cfg)
        return True
    except:
        return False

@bot_1h.callback_query_handler(func=lambda c: c.data.startswith("adv_"))
def advanced_settings_handler(c):
    cfg = load_config()
    data = c.data
    if data == "adv_pdf_1h":
        cfg["make_pdf_1h"] = not cfg["make_pdf_1h"]
        save_config(cfg)
    elif data == "adv_pdf_1d":
        cfg["make_pdf_1d"] = not cfg["make_pdf_1d"]
        save_config(cfg)
    elif data == "adv_combined_15m":
        cfg["make_combined_15m"] = not cfg.get("make_combined_15m", True)
        save_config(cfg)
    elif data == "adv_verbose_1h":
        cfg["verbose_1h"] = not cfg["verbose_1h"]
        save_config(cfg)
    elif data == "adv_verbose_4h":
        cfg["verbose_4h"] = not cfg["verbose_4h"]
        save_config(cfg)
    elif data == "adv_verbose_1d":
        cfg["verbose_1d"] = not cfg["verbose_1d"]
        save_config(cfg)
    elif data == "adv_verbose_15m":
        cfg["verbose_15m"] = not cfg["verbose_15m"]
        save_config(cfg)
    elif data == "adv_reset_app":
        cfg = reset_config()
        for k in LAST_ALARMS:
            LAST_ALARMS[k] = []
        save_config(cfg)
    elif data in ["adv_candles_1h","adv_candles_4h","adv_candles_1d","adv_candles_15m","adv_reports"]:
        key_map = {
            "adv_candles_1h": "candles_1h",
            "adv_candles_4h": "candles_4h",
            "adv_candles_1d": "candles_1d",
            "adv_candles_15m": "candles_15m",
            "adv_reports": "reports_default"
        }
        key = key_map[data]
        msg = bot_1h.send_message(c.message.chat.id, f"مقدار جدید برای {key} را وارد کن (مضربی از 20 برای candles):")
        def _handler(mm):
            val = mm.text.strip()
            if key.startswith("candles_"):
                ok = _set_candles_multiple(cfg, key, val)
                if ok:
                    bot_1h.send_message(mm.chat.id, f"{key} به {val} تغییر کرد.")
                else:
                    bot_1h.send_message(mm.chat.id, "مقدار نامعتبر است. باید مضربی از ۲۰ و بزرگ‌تر از صفر باشد.")
            else:
                try:
                    v = int(val)
                    if v <= 0:
                        raise ValueError
                    cfg[key] = v
                    save_config(cfg)
                    bot_1h.send_message(mm.chat.id, f"{key} به {v} تغییر کرد.")
                except:
                    bot_1h.send_message(mm.chat.id, "مقدار نامعتبر است.")
            advanced_settings(mm)
        bot_1h.register_next_step_handler(msg, _handler)
        bot_1h.answer_callback_query(c.id, "در حال تنظیم مقدار جدید...")
        return
    bot_1h.answer_callback_query(c.id, "تنظیمات اعمال شد.")
    advanced_settings(c.message)

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

def fetch_ohlc(symbol: str, interval: str, max_bars: int) -> pd.DataFrame:
    limit = max(200, max_bars)
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

def create_plotly_chart(symbol: str, interval: str, candles: int, max_bars: int, png_name: str):
    df = fetch_ohlc(symbol, interval, max_bars)
    if df.empty:
        df = pd.DataFrame(columns=["o","h","l","c","v"])
        df.index = pd.to_datetime([])
    else:
        df = df[["o","h","l","c","v"]]
        if len(df) > candles:
            df = df.iloc[-candles:]
    df = compute_indicators(df)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6,0.2,0.2], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df["o"], high=df["h"], low=df["l"], close=df["c"], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"],  mode="lines", name="SMA20",  line=dict(color="blue")),   row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA100"], mode="lines", name="SMA100", line=dict(color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], mode="lines", name="SMA200", line=dict(color="purple")), row=1, col=1)
    wma   = df["WMA20"]
    slope = df["WMA20_slope"]
    wma_up   = wma.where(slope >= 0)
    wma_down = wma.where(slope < 0)
    fig.add_trace(go.Scatter(x=df.index, y=wma_up,   mode="lines", name="WMA20 Up",   line=dict(color="green", width=2, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=wma_down, mode="lines", name="WMA20 Down", line=dict(color="red",   width=2, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], mode="lines", name="RSI14", line=dict(color="brown")), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="red", dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="green", dash="dash"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"],        mode="lines", name="MACD",   line=dict(color="black")),   row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], mode="lines", name="Signal", line=dict(color="magenta")), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="Hist", marker_color="gray"), row=3, col=1)
    fig.update_layout(title=f"{symbol} – {interval}", xaxis_rangeslider_visible=False, template="plotly_white", height=1000)
    fig.add_annotation(text=f"{symbol} – {interval}", xref="paper", yref="paper", x=0.5, y=1.05, showarrow=False, font=dict(size=30, color="black"))
    fig.update_yaxes(side="right", showgrid=True)
    png_path = os.path.join(CHARTS_DIR, png_name)
    try:
        fig.write_image(png_path, width=1800, height=1100, scale=3)
    except:
        pass
    return {
        "symbol": symbol,
        "interval": interval,
        "png_path": png_path,
        "created_at": now_utc_str(),
        "wma": df["WMA20"].tolist() if "WMA20" in df.columns else [],
        "wma_slope": df["WMA20_slope"].tolist() if "WMA20_slope" in df.columns else [],
        "sma20": df["SMA20"].tolist() if "SMA20" in df.columns else [],
        "sma100": df["SMA100"].tolist() if "SMA100" in df.columns else [],
        "sma200": df["SMA200"].tolist() if "SMA200" in df.columns else []
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
# اجرای سیکل‌ها
# =========================

def run_cycle(group: str, bot, chat_id: int, symbols: list, interval: str, candles: int, max_bars: int, make_pdf: bool):
    lock = CYCLE_LOCKS.get(group)
    if lock is None:
        return
    if not lock.acquire(blocking=False):
        return
    combined_jpgs = []
    try:
        cfg = load_config()
        verbose = cfg.get(f"verbose_{group}", True)
        if chat_id is None:
            return
        if verbose:
            bot.send_message(chat_id, f"شروع چرخه {group}\n{now_utc_str()} UTC")
        unique_symbols = list(dict.fromkeys(symbols))
        total = len(unique_symbols)
        processed = 0
        batch_size = cfg.get("cycle_progress_batch", 5)
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
            info = create_plotly_chart(sym, interval, candles, max_bars, png)
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
# اجرای فوری چرخه‌ها و تک نماد
# =========================

def _run_group_cycle(group: str):
    cfg = load_config()
    if group == "1h":
        bot = bot_1h
        chat_id = cfg.get("chat_id_1h")
        symbols = cfg.get("symbols_1h", [])
        interval = "1h"
        candles = cfg.get("candles_1h", 80)
        make_pdf = cfg.get("make_pdf_1h", True)
    elif group == "4h":
        bot = bot_4h or bot_1h
        chat_id = cfg.get("chat_id_4h") or cfg.get("chat_id_1h")
        symbols = cfg.get("symbols_4h", [])
        interval = "4h"
        candles = cfg.get("candles_4h", 60)
        make_pdf = False
    elif group == "1d":
        bot = bot_1d or bot_1h
        chat_id = cfg.get("chat_id_1d") or cfg.get("chat_id_1h")
        symbols = cfg.get("symbols_1d", [])
        interval = "1d"
        candles = cfg.get("candles_1d", 60)
        make_pdf = cfg.get("make_pdf_1d", True)
    elif group == "15m":
        bot = bot_15m or bot_1h
        chat_id = cfg.get("chat_id_15m") or cfg.get("chat_id_1h")
        symbols = cfg.get("symbols_15m", [])
        interval = "15m"
        candles = cfg.get("candles_15m", 40)
        make_pdf = False
    else:
        return
    max_bars = cfg.get("max_bars", 300)
    if not symbols:
        if bot and chat_id:
            bot.send_message(chat_id, f"هیچ نمادی برای {group} ثبت نشده است.")
        return
    threading.Thread(target=run_cycle, args=(group, bot, chat_id, symbols, interval, candles, max_bars, make_pdf), daemon=True).start()

@bot_1h.message_handler(func=lambda m: m.text == "اجرای دستی 1h")
def manual_1h(m):
    _run_group_cycle("1h")

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 4h")
def manual_4h(m):
    _run_group_cycle("4h")

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 1d")
def manual_1d(m):
    _run_group_cycle("1d")

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 15m")
def manual_15m(m):
    _run_group_cycle("15m")

@bot_1h.message_handler(func=lambda m: m.text == "اجرای چرخه‌ها")
def run_all_cycles(m):
    cfg = load_config()
    chat_id = m.chat.id
    bot_1h.send_message(chat_id, "اجرای چرخه‌ها برای همه تایم‌فریم‌ها با فاصله‌ی ۵ دقیقه شروع شد.")
    def _runner():
        _run_group_cycle("1h")
        time.sleep(5 * 60)
        _run_group_cycle("4h")
        time.sleep(5 * 60)
        _run_group_cycle("1d")
        time.sleep(5 * 60)
        _run_group_cycle("15m")
    threading.Thread(target=_runner, daemon=True).start()

# =========================
# چک یک نماد (اجرای فوری تک نماد در 1h)
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "چک یک نماد")
def check_one_symbol(m):
    msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کن (مثلاً BTCUSDT):")
    def _handler(mm):
        symbol = mm.text.strip().upper()
        cfg = load_config()
        candles = cfg.get("candles_1h", 80)
        max_bars = cfg.get("max_bars", 300)
        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"check_1h_{symbol}_{ts}.png"
        info = create_plotly_chart(symbol, "1h", candles, max_bars, png)
        alarms = detect_alarms(cfg, info, "1h")
        caption = f"{symbol} (1h)"
        if alarms:
            caption += "\n" + "\n".join(alarms)
        else:
            caption += " – بدون آلارم"
        try:
            with open(info["png_path"], "rb") as f:
                bot_1h.send_photo(mm.chat.id, f, caption=caption)
        except:
            bot_1h.send_message(mm.chat.id, "خطا در ارسال نمودار.")
    bot_1h.register_next_step_handler(msg, _handler)

# =========================
# اجرای ربات‌ها
# =========================

def _start_bot(bot):
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except:
        time.sleep(5)
        _start_bot(bot)

threads = []
if bot_1h:
    t = threading.Thread(target=_start_bot, args=(bot_1h,), daemon=True)
    threads.append(t)
    t.start()
if bot_4h:
    t = threading.Thread(target=_start_bot, args=(bot_4h,), daemon=True)
    threads.append(t)
    t.start()
if bot_1d:
    t = threading.Thread(target=_start_bot, args=(bot_1d,), daemon=True)
    threads.append(t)
    t.start()
if bot_15m:
    t = threading.Thread(target=_start_bot, args=(bot_15m,), daemon=True)
    threads.append(t)
    t.start()

while True:
    time.sleep(10)