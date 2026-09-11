# -*- coding: utf-8 -*-
# Modu Bazler v5.3 – نسخه‌ی پایدار با SmartLock، Watchdog و تست سیکل‌ها

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

CONFIG_PATH = os.path.join(DATA_DIR, "config_v5_3.json")

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

    # محاسبات روی 500 کندل، نمایش طبق max_bars
    "lookback_1h": 5,
    "lookback_4h": 15,
    "lookback_1d": 180,
    "lookback_15m": 3,
    "max_bars": 300,

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

    "cycle_progress_batch": 5,

    # تنظیمات SmartLock
    "lock_timeout_sec": 600,   # اگر قفل بیش از 10 دقیقه نگه داشته شد، آزاد شود
    "cycle_min_duration_sec": 5  # اگر سیکل کمتر از 5 ثانیه طول کشید، fallback اجرا شود
}

def save_config(cfg: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        debug_mark(None, None, 101, "save_config")

def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        debug_mark(None, None, 102, "load_config")
        return DEFAULT_CONFIG.copy()

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

def debug_mark(bot, chat_id, code: int, where: str):
    msg = f"TEST#{code} @ {where}"
    try:
        if bot and chat_id:
            bot.send_message(chat_id, msg)
        elif ADMIN_CHAT and bot:
            bot.send_message(int(ADMIN_CHAT), msg)
    except:
        pass

def create_bot(token: str):
    if not token or not isinstance(token, str):
        return None
    if any(ch.isspace() for ch in token):
        return None
    try:
        return telebot.TeleBot(token, parse_mode="HTML")
    except Exception:
        debug_mark(None, None, 103, "create_bot")
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

# SmartLock: قفل + زمان آخرین گرفتن
class SmartLock:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_acquire = None

    def acquire(self, blocking=False):
        cfg = load_config()
        timeout = cfg.get("lock_timeout_sec", 600)
        # اگر قفل قبلاً گرفته شده و خیلی طولانی شده، آزادش کن
        if self.lock.locked() and self.last_acquire:
            elapsed = (now_utc() - self.last_acquire).total_seconds()
            if elapsed > timeout:
                try:
                    self.lock.release()
                    debug_mark(bot_1h, int(ADMIN_CHAT) if ADMIN_CHAT else None, 1901, "SmartLock_force_release")
                except:
                    pass
        ok = self.lock.acquire(blocking=blocking)
        if ok:
            self.last_acquire = now_utc()
        return ok

    def release(self):
        if self.lock.locked():
            try:
                self.lock.release()
            except:
                pass

CYCLE_LOCKS = {
    "1h": SmartLock(),
    "4h": SmartLock(),
    "1d": SmartLock(),
    "15m": SmartLock()
}

# =========================
# راهنما
# =========================

HELP_TEXT = """
Modu Bazler v5.3 – نسخه‌ی پایدار با SmartLock و تست سیکل‌ها

📌 ربات‌ها:
- 1h: ربات اصلی مدیریت و منو
- 4h: ربات ۴ساعته
- 1d: ربات روزانه
- 15m: ربات ۱۵دقیقه‌ای

✅ ثبت چت هر ربات:
- در هر ربات دستور /start را بفرست تا chat_id ثبت شود.

🧭 منوی ربات 1h:
- چک یک نماد → بررسی پیشرفته یک نماد در 1h
- اجرای دستی 1h → اجرای کامل سیکل 1h (با PDF در صورت فعال بودن)
- اجرای فوری 4h / 1d / 15m → اجرای سیکل همان تایم‌فریم
- مدیریت نمادهای 1h / 4h / 1d / 15m → افزودن/حذف نمادها
- تنظیم آلارم‌ها → فعال/غیرفعال کردن انواع آلارم‌ها
- گزارش آلارم‌ها → نمایش آخرین آلارم‌های هر گروه
- وضعیت سیستم → نمایش تنظیمات و تعداد نمادها
- تنظیمات پیشرفته → کنترل PDF و verbose برای هر ربات
- اجرای چرخه‌ها → اجرای فوری همه‌ی تایم‌فریم‌ها
- ریست برنامه → بازگشت به تنظیمات اولیه

🔊 حالت پردازش (verbose):
- ON → پیام‌های پردازش + نمودار همه‌ی نمادها
- OFF → فقط نمودار نمادهای دارای آلارم، بدون پیام‌های میانی

📄 PDF:
- برای سیکل‌های 1h و 1d در صورت فعال بودن، یک فایل PDF از همه‌ی نمودارها ساخته و ارسال می‌شود.

⏱ زمان‌بندی خودکار:
- 1h: هر ساعت در دقیقه 22
- 4h: در ساعات 2، 6، 10، 14، 18، 22 (دقیقه 7)
- 1d: هر روز ساعت 1:05
- 15m: هر ۱۵ دقیقه
"""

# =========================
# منوی اصلی ربات 1h
# =========================

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("چک یک نماد", "اجرای دستی 1h")
    kb.row("اجرای فوری 4h", "اجرای فوری 1d")
    kb.row("اجرای فوری 15m")
    kb.row("مدیریت نمادهای 1h", "مدیریت نمادهای 4h")
    kb.row("مدیریت نمادهای 1d", "مدیریت نمادهای 15m")
    kb.row("تنظیم آلارم‌ها", "گزارش آلارم‌ها")
    kb.row("وضعیت سیستم", "تنظیمات پیشرفته")
    kb.row("اجرای چرخه‌ها", "ریست برنامه")
    kb.row("راهنما", "رفرش منو")
    try:
        bot_1h.send_message(chat_id, "منوی اصلی:", reply_markup=kb)
    except Exception:
        debug_mark(bot_1h, chat_id, 201, "send_main_menu")

@bot_1h.message_handler(commands=["start"])
def start_main(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    try:
        bot_1h.send_message(m.chat.id, HELP_TEXT)
        send_main_menu(m.chat.id)
    except Exception:
        debug_mark(bot_1h, m.chat.id, 202, "start_main")

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
        try:
            bot_4h.send_message(m.chat.id, "ربات ۴ساعته فعال شد.\n" + now_utc_str())
        except Exception:
            debug_mark(bot_4h, m.chat.id, 203, "start_4h")

if bot_1d:
    @bot_1d.message_handler(commands=["start"])
    def start_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        try:
            bot_1d.send_message(m.chat.id, "ربات روزانه فعال شد.\n" + now_utc_str())
        except Exception:
            debug_mark(bot_1d, m.chat.id, 204, "start_1d")

if bot_15m:
    @bot_15m.message_handler(commands=["start"])
    def start_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        try:
            bot_15m.send_message(m.chat.id, "ربات ۱۵دقیقه‌ای فعال شد.\n" + now_utc_str())
        except Exception:
            debug_mark(bot_15m, m.chat.id, 205, "start_15m")

# =========================
# ریست برنامه
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "ریست برنامه")
def reset_app(m):
    cfg = reset_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    try:
        bot_1h.send_message(m.chat.id, "برنامه و تنظیمات کامل ریست شد.")
        send_main_menu(m.chat.id)
    except Exception:
        debug_mark(bot_1h, m.chat.id, 206, "reset_app")

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
    try:
        bot_1h.send_message(chat_id, txt, reply_markup=kb)
    except Exception:
        debug_mark(bot_1h, chat_id, 301, "show_symbol_menu")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1h")
def manage_1h(m): show_symbol_menu(m.chat.id, "1h")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 4h")
def manage_4h(m): show_symbol_menu(m.chat.id, "4h")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1d")
def manage_1d(m): show_symbol_menu(m.chat.id, "1d")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 15m")
def manage_15m(m): show_symbol_menu(m.chat.id, "15m")

def add_symbol_step(m, group):
    symbol = m.text.strip().upper()
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    if symbol not in symbols:
        symbols.append(symbol)
        set_symbols(cfg, group, symbols)
        try:
            bot_1h.send_message(m.chat.id, f"{symbol} به لیست {group} اضافه شد.")
        except Exception:
            debug_mark(bot_1h, m.chat.id, 302, "add_symbol_step")
    else:
        try:
            bot_1h.send_message(m.chat.id, f"{symbol} قبلاً در لیست {group} وجود دارد.")
        except Exception:
            debug_mark(bot_1h, m.chat.id, 303, "add_symbol_step_exists")
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
        try:
            bot_1h.send_message(m.chat.id, f"{symbol} از لیست {group} حذف شد.")
        except Exception:
            debug_mark(bot_1h, m.chat.id, 304, "remove_symbol_step")
    else:
        try:
            bot_1h.send_message(m.chat.id, f"{symbol} در لیست {group} وجود ندارد.")
        except Exception:
            debug_mark(bot_1h, m.chat.id, 305, "remove_symbol_step_not_found")
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
    try:
        bot_1h.send_message(m.chat.id, txt)
    except Exception:
        debug_mark(bot_1h, m.chat.id, 306, "show_symbols_any")

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
    try:
        bot_1h.send_message(m.chat.id, "آلارم‌ها را تنظیم کنید:", reply_markup=kb)
    except Exception:
        debug_mark(bot_1h, m.chat.id, 401, "alarms_menu")

@bot_1h.callback_query_handler(func=lambda c: c.data.startswith("alarm_"))
def toggle_alarm(c):
    cfg = load_config()
    key = c.data.replace("alarm_", "")
    cfg[key] = not cfg.get(key)
    save_config(cfg)
    try:
        bot_1h.answer_callback_query(c.id, f"{key} -> {'ON' if cfg[key] else 'OFF'}")
        alarms_menu(c.message)
    except Exception:
        debug_mark(bot_1h, c.message.chat.id, 402, "toggle_alarm")

# =========================
# گزارش آلارم‌ها
# =========================

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
    try:
        bot_1h.send_message(m.chat.id, txt)
    except Exception:
        debug_mark(bot_1h, m.chat.id, 501, "alarms_report")

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
    txt += f"PDF 1h: {'ON' if cfg['make_pdf_1h'] else 'OFF'}\n"
    txt += f"PDF 1d: {'ON' if cfg['make_pdf_1d'] else 'OFF'}\n"
    txt += f"Combined 15m: {'ON' if cfg.get('make_combined_15m', True) else 'OFF'}\n"
    txt += f"verbose 1h: {'ON' if cfg['verbose_1h'] else 'OFF'}\n"
    txt += f"verbose 4h: {'ON' if cfg['verbose_4h'] else 'OFF'}\n"
    txt += f"verbose 1d: {'ON' if cfg['verbose_1d'] else 'OFF'}\n"
    txt += f"verbose 15m: {'ON' if cfg['verbose_15m'] else 'OFF'}\n"
    txt += f"lock_timeout_sec: {cfg.get('lock_timeout_sec', 600)}\n"
    txt += f"cycle_min_duration_sec: {cfg.get('cycle_min_duration_sec', 5)}\n"
    try:
        bot_1h.send_message(m.chat.id, txt)
    except Exception:
        debug_mark(bot_1h, m.chat.id, 601, "system_status")

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
    try:
        bot_1h.send_message(m.chat.id, "تنظیمات پیشرفته:", reply_markup=kb)
    except Exception:
        debug_mark(bot_1h, m.chat.id, 602, "advanced_settings")

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
    try:
        bot_1h.answer_callback_query(c.id, "تنظیمات اعمال شد.")
        advanced_settings(c.message)
    except Exception:
        debug_mark(bot_1h, c.message.chat.id, 603, "advanced_settings_handler")

# =========================
# راهنما
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "راهنما")
def help_menu(m):
    try:
        bot_1h.send_message(m.chat.id, HELP_TEXT)
    except Exception:
        debug_mark(bot_1h, m.chat.id, 701, "help_menu")

# =========================
# دیتا، اندیکاتورها، نمودار
# =========================

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str) -> str:
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

def fetch_ohlc(symbol: str, interval: str, lookback_days: int, max_bars: int) -> pd.DataFrame:
    limit = max(500, max_bars)
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
    except Exception:
        debug_mark(bot_1h, int(ADMIN_CHAT) if ADMIN_CHAT else None, 801, "fetch_ohlc_binance")
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
    except Exception:
        debug_mark(bot_1h, int(ADMIN_CHAT) if ADMIN_CHAT else None, 802, "fetch_ohlc_kucoin")
        return pd.DataFrame()

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df
    try:
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
    except Exception:
        debug_mark(bot_1h, int(ADMIN_CHAT) if ADMIN_CHAT else None, 803, "compute_indicators")
    return df

def create_plotly_chart(symbol: str, interval: str, lookback_days: int, max_bars: int, png_name: str):
    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)
    if df.empty:
        df = pd.DataFrame(columns=["o","h","l","c","v"])
        df.index = pd.to_datetime([])
    else:
        df = df.tail(max_bars)[["o","h","l","c","v"]]
    df = compute_indicators(df)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6,0.2,0.2], vertical_spacing=0.03)
    try:
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
    except Exception:
        debug_mark(bot_1h, int(ADMIN_CHAT) if ADMIN_CHAT else None, 804, "create_plotly_chart_build")

    png_path = os.path.join(CHARTS_DIR, png_name)
    try:
        fig.write_image(png_path, width=1800, height=1100, scale=3)
    except Exception:
        debug_mark(bot_1h, int(ADMIN_CHAT) if ADMIN_CHAT else None, 805, "create_plotly_chart_write")

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
        try:
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
        except Exception:
            debug_mark(bot_1h, int(ADMIN_CHAT) if ADMIN_CHAT else None, 806, "make_15m_combined_pages")
    return pages

# =========================
# اجرای سیکل‌ها با SmartLock و Watchdog
# =========================

def run_cycle_once(group: str, bot, chat_id: int, symbols: list, interval: str, lookback_days: int, max_bars: int, make_pdf: bool):
    lock = CYCLE_LOCKS.get(group)
    if lock is None:
        debug_mark(bot, chat_id, 901, f"run_cycle_no_lock_{group}")
        return

    if not lock.acquire(blocking=False):
        debug_mark(bot, chat_id, 902, f"run_cycle_lock_busy_{group}")
        return

    combined_jpgs = []
    try:
        cfg = load_config()
        verbose = cfg.get(f"verbose_{group}", True)

        if chat_id is None:
            debug_mark(bot, chat_id, 903, f"run_cycle_no_chat_{group}")
            return

        if verbose:
            try:
                bot.send_message(chat_id, f"شروع چرخه {group}\n{now_utc_str()} UTC")
            except Exception:
                debug_mark(bot, chat_id, 904, f"run_cycle_start_msg_{group}")

        unique_symbols = list(dict.fromkeys(symbols))
        total = len(unique_symbols)
        processed = 0
        batch_size = cfg.get("cycle_progress_batch", 5)

        pdf = None
        pdf_filename = None

        if make_pdf and group in ["1h", "1d"]:
            pdf_filename = os.path.join(PDF_DIR, f"{group}_{now_utc().strftime('%Y%m%d_%H%M%S')}.pdf")
            try:
                pdf = PdfPages(pdf_filename)
            except Exception:
                debug_mark(bot, chat_id, 905, f"run_cycle_pdf_init_{group}")
                pdf = None

        for sym in unique_symbols:
            processed += 1

            if verbose and (processed % batch_size == 0 or processed == 1 or processed == total):
                try:
                    bot.send_message(chat_id, f"چرخه {group}: {processed}/{total} نماد، {total - processed} باقی مانده.")
                except Exception:
                    debug_mark(bot, chat_id, 906, f"run_cycle_progress_{group}")

            ts = now_utc().strftime("%Y%m%d_%H%M%S")
            png = f"{group}_{sym}_{ts}.png"

            info = create_plotly_chart(sym, interval, lookback_days, max_bars, png)
            alarms = detect_alarms(cfg, info, group)

            if group == "15m":
                try:
                    img = Image.open(info["png_path"]).convert("RGB")
                    jpg_name = os.path.splitext(os.path.basename(info["png_path"]))[0] + ".jpg"
                    jpg_path = os.path.join(CHARTS_DIR, jpg_name)
                    img.save(jpg_path, format="JPEG", quality=95)
                    combined_jpgs.append(jpg_path)
                except Exception:
                    debug_mark(bot, chat_id, 907, f"run_cycle_15m_jpg_{group}")

            if verbose or alarms:
                caption = f"{sym} ({group})"
                if alarms:
                    caption += "\n" + "\n".join(alarms)
                else:
                    caption += " – بدون آلارم"

                try:
                    with open(info["png_path"], "rb") as f:
                        bot.send_photo(chat_id, f, caption=caption)
                except Exception:
                    debug_mark(bot, chat_id, 908, f"run_cycle_send_photo_{group}")

            if pdf is not None:
                try:
                    img = plt.imread(info["png_path"])
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.imshow(img)
                    ax.axis("off")
                    ax.set_title(f"{sym} – {group}")
                    pdf.savefig(fig)
                    plt.close(fig)
                except Exception:
                    debug_mark(bot, chat_id, 909, f"run_cycle_pdf_add_{group}")

            time.sleep(0.3)

        if pdf is not None:
            try:
                pdf.close()
                with open(pdf_filename, "rb") as f:
                    bot.send_document(chat_id, f, caption=f"گزارش PDF کامل سیکل {group}")
            except Exception:
                debug_mark(bot, chat_id, 910, f"run_cycle_pdf_send_{group}")

        if group == "15m":
            cfg = load_config()
            if cfg.get("make_combined_15m", True) and combined_jpgs:
                pages = make_15m_combined_pages(combined_jpgs)
                for p in pages:
                    try:
                        with open(p, "rb") as f:
                            bot.send_photo(chat_id, f, caption="صفحهٔ ترکیبی 15m")
                    except Exception:
                        debug_mark(bot, chat_id, 911, f"run_cycle_15m_pages_{group}")

    finally:
        lock.release()

def run_cycle(group: str, bot, chat_id: int, symbols: list, interval: str, lookback_days: int, max_bars: int, make_pdf: bool):
    """
    اجرای سیکل با Watchdog و fallback:
    - اگر سیکل خیلی سریع (کمتر از cycle_min_duration_sec) تمام شد، یک بار دیگر اجرا می‌شود.
    """
    cfg = load_config()
    min_dur = cfg.get("cycle_min_duration_sec", 5)

    start = now_utc()
    run_cycle_once(group, bot, chat_id, symbols, interval, lookback_days, max_bars, make_pdf)
    end = now_utc()

    elapsed = (end - start).total_seconds()
    if elapsed < min_dur:
        debug_mark(bot, chat_id, 2001, f"run_cycle_fallback_{group}")
        run_cycle_once(group, bot, chat_id, symbols, interval, lookback_days, max_bars, make_pdf)

# =========================
# اجرای دستی و فوری سیکل‌ها
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "اجرای دستی 1h")
def manual_1h(m):
    cfg = load_config()
    symbols = cfg["symbols_1h"]
    run_cycle("1h", bot_1h, m.chat.id, symbols, "1h", cfg["lookback_1h"], cfg["max_bars"], cfg["make_pdf_1h"])

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 4h")
def manual_4h(m):
    cfg = load_config()
    symbols = cfg["symbols_4h"]
    run_cycle("4h", bot_4h or bot_1h, m.chat.id, symbols, "4h", cfg["lookback_4h"], cfg["max_bars"], False)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 1d")
def manual_1d(m):
    cfg = load_config()
    symbols = cfg["symbols_1d"]
    run_cycle("1d", bot_1d or bot_1h, m.chat.id, symbols, "1d", cfg["lookback_1d"], cfg["max_bars"], cfg["make_pdf_1d"])

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 15m")
def manual_15m(m):
    cfg = load_config()
    symbols = cfg["symbols_15m"]
    run_cycle("15m", bot_15m or bot_1h, m.chat.id, symbols, "15m", cfg["lookback_15m"], cfg["max_bars"], False)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای چرخه‌ها")
def run_all_cycles(m):
    cfg = load_config()
    try:
        bot_1h.send_message(m.chat.id, "اجرای همهٔ سیکل‌ها شروع شد.")
    except Exception:
        debug_mark(bot_1h, m.chat.id, 1001, "run_all_cycles_msg")

    threading.Thread(target=lambda: run_cycle("1h", bot_1h, m.chat.id, cfg["symbols_1h"], "1h", cfg["lookback_1h"], cfg["max_bars"], cfg["make_pdf_1h"]), daemon=True).start()
    threading.Thread(target=lambda: run_cycle("4h", bot_4h or bot_1h, m.chat.id, cfg["symbols_4h"], "4h", cfg["lookback_4h"], cfg["max_bars"], False), daemon=True).start()
    threading.Thread(target=lambda: run_cycle("1d", bot_1d or bot_1h, m.chat.id, cfg["symbols_1d"], "1d", cfg["lookback_1d"], cfg["max_bars"], cfg["make_pdf_1d"]), daemon=True).start()
    threading.Thread(target=lambda: run_cycle("15m", bot_15m or bot_1h, m.chat.id, cfg["symbols_15m"], "15m", cfg["lookback_15m"], cfg["max_bars"], False), daemon=True).start()

# =========================
# چک یک نماد (اجرای تک نماد)
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "چک یک نماد")
def check_one_symbol_start(m):
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (مثلاً BTCUSDT):")
    bot_1h.register_next_step_handler(msg, check_one_symbol_do)

def check_one_symbol_do(m):
    symbol = m.text.strip().upper()
    cfg = load_config()
    try:
        bot_1h.send_message(m.chat.id, f"در حال بررسی {symbol} در تایم 1h ...")
    except Exception:
        debug_mark(bot_1h, m.chat.id, 1101, "check_one_symbol_msg")

    ts = now_utc().strftime("%Y%m%d_%H%M%S")
    png = f"1h_single_{symbol}_{ts}.png"
    info = create_plotly_chart(symbol, "1h", cfg["lookback_1h"], cfg["max_bars"], png)
    alarms = detect_alarms(cfg, info, "1h")
    caption = f"{symbol} (1h)"
    if alarms:
        caption += "\n" + "\n".join(alarms)
    try:
        with open(info["png_path"], "rb") as f:
            bot_1h.send_photo(m.chat.id, f, caption=caption)
    except Exception:
        debug_mark(bot_1h, m.chat.id, 1102, "check_one_symbol_send")

# =========================
# زمان‌بندی خودکار سیکل‌ها
# =========================

def scheduler_loop():
    while True:
        try:
            now = now_utc()
            minute = now.minute
            hour = now.hour

            cfg = load_config()

            # 1h: هر ساعت در دقیقه 22
            if minute == 22:
                if cfg.get("chat_id_1h"):
                    threading.Thread(
                        target=lambda: run_cycle("1h", bot_1h, cfg["chat_id_1h"], cfg["symbols_1h"], "1h", cfg["lookback_1h"], cfg["max_bars"], cfg["make_pdf_1h"]),
                        daemon=True
                    ).start()

            # 4h: در ساعات 2، 6، 10، 14، 18، 22 (دقیقه 7)
            if minute == 7 and hour in [2,6,10,14,18,22]:
                if cfg.get("chat_id_4h") or cfg.get("chat_id_1h"):
                    ch = cfg.get("chat_id_4h") or cfg.get("chat_id_1h")
                    threading.Thread(
                        target=lambda: run_cycle("4h", bot_4h or bot_1h, ch, cfg["symbols_4h"], "4h", cfg["lookback_4h"], cfg["max_bars"], False),
                        daemon=True
                    ).start()

            # 1d: هر روز ساعت 1:05
            if hour == 1 and minute == 5:
                if cfg.get("chat_id_1d") or cfg.get("chat_id_1h"):
                    ch = cfg.get("chat_id_1d") or cfg.get("chat_id_1h")
                    threading.Thread(
                        target=lambda: run_cycle("1d", bot_1d or bot_1h, ch, cfg["symbols_1d"], "1d", cfg["lookback_1d"], cfg["max_bars"], cfg["make_pdf_1d"]),
                        daemon=True
                    ).start()

            # 15m: هر 15 دقیقه
            if minute % 15 == 0:
                if cfg.get("chat_id_15m") or cfg.get("chat_id_1h"):
                    ch = cfg.get("chat_id_15m") or cfg.get("chat_id_1h")
                    threading.Thread(
                        target=lambda: run_cycle("15m", bot_15m or bot_1h, ch, cfg["symbols_15m"], "15m", cfg["lookback_15m"], cfg["max_bars"], False),
                        daemon=True
                    ).start()

        except Exception:
            debug_mark(bot_1h, int(ADMIN_CHAT) if ADMIN_CHAT else None, 1201, "scheduler_loop")

        time.sleep(60)

# =========================
# راه‌اندازی زمان‌بند و polling
# =========================

def start_scheduler_thread():
    try:
        t = threading.Thread(target=scheduler_loop, daemon=True)
        t.start()
    except Exception:
        debug_mark(bot_1h, int(ADMIN_CHAT) if ADMIN_CHAT else None, 1301, "start_scheduler_thread")

def main():
    start_scheduler_thread()
    try:
        if bot_1h:
            bot_1h.polling(none_stop=True, interval=0, timeout=20)
        if bot_4h:
            bot_4h.polling(none_stop=True, interval=0, timeout=20)
        if bot_1d:
            bot_1d.polling(none_stop=True, interval=0, timeout=20)
        if bot_15m:
            bot_15m.polling(none_stop=True, interval=0, timeout=20)
    except Exception:
        debug_mark(bot_1h, int(ADMIN_CHAT) if ADMIN_CHAT else None, 1401, "main_polling")

if __name__ == "__main__":
    main()