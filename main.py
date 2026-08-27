# -*- coding: utf-8 -*-
# Modu Bazler – main.py (نسخهٔ پیشرفته با مدیریت مرکزی واچ‌لیست‌ها و تنظیمات پیشرفته)

import os, json, time, threading, datetime as dt
import requests, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import telebot
from telebot import types

# =========================
# مسیرها و تنظیمات پایه
# =========================

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
HTML_DIR   = os.path.join(DATA_DIR, "html")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, HTML_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULT_CONFIG = {
    "hourly_symbols": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT"
    ],
    "fourh_symbols": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT"
    ],
    "daily_symbols": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT"
    ],
    "fifteenm_symbols": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT","ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT",
        "OPUSDT","ARBUSDT","SUIUSDT","PEPEUSDT","TONUSDT","UNIUSDT","AAVEUSDT","INJUSDT","RNDRUSDT","FTMUSDT",
        "NEOUSDT","GALAUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","JTOUSDT","WIFUSDT","JUPUSDT","STRKUSDT","BLURUSDT",
        "RUNEUSDT","RAYUSDT","LDOUSDT","COMPUSDT","CRVUSDT","MKRUSDT","SNXUSDT","GMXUSDT","DYDXUSDT","ENSUSDT"
    ],

    "hourly_interval": "1h",
    "fourh_interval": "4h",
    "daily_interval": "1d",
    "fifteenm_interval": "15m",

    "hourly_lookback_days": 5,
    "fourh_lookback_days": 15,
    "daily_lookback_days": 180,
    "fifteenm_lookback_days": 3,

    "max_bars": 300,

    # آلارم‌ها
    "alarm_wma_direction": True,
    "alarm_cross_sma20": False,
    "alarm_cross_sma100": False,
    "alarm_cross_sma200": False,
    "alarm_sma20_direction": False,
    "alarm_sma100_direction": False,
    "alarm_sma200_direction": False,

    # PDF
    "make_pdf": True,

    # چت‌ها
    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,

    # واچ‌لیست‌ها (هر تایم‌فریم جدا، مدیریت از ربات اصلی)
    "watchlist_1h": {},
    "watchlist_4h": {},
    "watchlist_1d": {},
    "watchlist_15m": {},

    # تعداد سیکل‌هایی که وضعیت واچ‌لیست به همان ربات ارسال شود
    "watchlist_status_every_cycles": 4,

    # اندازه‌ی دسته برای پیام پیشرفت سیکل
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
# توکن‌ها و ساخت ربات‌ها
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

bot_1h  = create_bot(TOKEN_1H)   # ربات اصلی مدیریت
bot_4h  = create_bot(TOKEN_4H)
bot_1d  = create_bot(TOKEN_1D)
bot_15m = create_bot(TOKEN_15M)

# =========================
# متن راهنما
# =========================

HELP_TEXT = """
Modu Bazler – نسخه پیشرفته با سیستم آلارم و واچ‌لیست‌ها

دستورات:
/start – ثبت چت و نمایش منو در ربات اصلی
/refresh – رفرش منو
/reset_app – ریست کامل تنظیمات و واچ‌لیست‌ها

سیکل‌ها:
/start_cycle – شروع چرخه ۱ساعته (اجرای فوری)
/start_cycle_4h – شروع چرخه ۴ساعته (اجرای فوری)
/start_cycle_1d – شروع چرخه روزانه (اجرای فوری)
/start_cycle_15m – شروع چرخه ۱۵دقیقه‌ای (اجرای فوری)

زمان‌بندی خودکار:
- 1h: هر ساعت در دقیقه 30
- 4h: در ساعات 4:30، 8:30، 12:30، 16:30، 20:30، 23:30، 0:30
- 1d: هر روز ساعت 23:30
- 15m: هر 15 دقیقه (دقیقه‌های 0، 15، 30، 45)

منو اصلی ربات 1h:
- چک یک نماد (پیشرفته)
- اجرای دستی 1h
- مدیریت واچ‌لیست‌ها (1h, 4h, 1d, 15m)
- تنظیم آلارم‌ها
- بازنشانی نمادها
- راهنما
- رفرش منو
- شروع چرخه‌ها
- وضعیت سیستم
- گزارش آلارم‌ها
- تنظیمات پیشرفته
"""

# =========================
# منوها
# =========================

def send_main_menu(bot, chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("چک یک نماد", "اجرای دستی 1h")
    kb.row("مدیریت واچ‌لیست‌ها", "تنظیم آلارم‌ها")
    kb.row("بازنشانی نمادها", "راهنما")
    kb.row("رفرش منو", "شروع چرخه‌ها")
    kb.row("وضعیت سیستم", "گزارش آلارم‌ها")
    kb.row("تنظیمات پیشرفته")

    bot.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

def refresh_menu(bot, chat_id):
    send_main_menu(bot, chat_id)

# =========================
# واچ‌لیست‌ها – توابع کمکی
# =========================

def get_watchlist(cfg, group: str) -> dict:
    key = f"watchlist_{group}"
    return cfg.get(key, {})

def set_watchlist(cfg, group: str, wl: dict):
    key = f"watchlist_{group}"
    cfg[key] = wl

def add_to_watchlist(cfg, group: str, symbol: str, price: float):
    wl = get_watchlist(cfg, group)
    wl[symbol] = {
        "price": float(price),
        "added_at": now_utc_str()
    }
    set_watchlist(cfg, group, wl)
    save_config(cfg)

def remove_from_watchlist(cfg, group: str, symbol: str):
    wl = get_watchlist(cfg, group)
    if symbol in wl:
        wl.pop(symbol)
        set_watchlist(cfg, group, wl)
        save_config(cfg)

def reset_watchlist_group(cfg, group: str):
    set_watchlist(cfg, group, {})
    save_config(cfg)

def reset_all_watchlists(cfg):
    for g in ["1h","4h","1d","15m"]:
        set_watchlist(cfg, g, {})
    save_config(cfg)

# =========================
# هندلرهای /start و /refresh و /reset_app (ربات اصلی)
# =========================

if bot_1h:
    @bot_1h.message_handler(commands=["start"])
    def start_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, HELP_TEXT)
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["refresh"])
    def refresh_1h(m):
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["reset_app"])
    def reset_app_1h(m):
        cfg = reset_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "برنامه و تمام واچ‌لیست‌ها ریست شدند.")
        refresh_menu(bot_1h, m.chat.id)

# سایر ربات‌ها فقط start ساده دارند
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
# هندلرهای منوی ربات اصلی (1h)
# =========================

LAST_ALARMS = []
CYCLE_COUNTERS = {
    "1h": 0,
    "4h": 0,
    "1d": 0,
    "15m": 0
}

if bot_1h:

    # چک تک نماد
    @bot_1h.message_handler(func=lambda m: m.text == "چک یک نماد")
    def check_symbol(m):
        msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید (مثلاً BTCUSDT):")
        bot_1h.register_next_step_handler(msg, process_single_symbol)

    def process_single_symbol(m):
        symbol = m.text.strip().upper()
        cfg = load_config()
        bot_1h.send_message(m.chat.id, f"در حال بررسی پیشرفته {symbol} در تایم‌فریم 1h ...")

        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"single_1h_{symbol}_{ts}.png"
        html = f"single_1h_{symbol}_{ts}.html"

        info = create_plotly_chart(
            symbol,
            "1h",
            cfg["hourly_lookback_days"],
            cfg["max_bars"],
            png,
            html,
            watch_price=None
        )

        with open(info["png_path"], "rb") as f:
            bot_1h.send_photo(m.chat.id, f, caption=f"{symbol} – بررسی پیشرفته 1h")

        bot_1h.send_message(m.chat.id, "بررسی تک نماد پایان یافت.")

    # اجرای دستی سیکل 1h
    @bot_1h.message_handler(func=lambda m: m.text == "اجرای دستی 1h")
    def manual_1h(m):
        cfg = load_config()
        run_cycle(
            group="1h",
            bot=bot_1h,
            chat_id=cfg["chat_id_1h"],
            symbols=cfg["hourly_symbols"],
            interval="1h",
            lookback_days=cfg["hourly_lookback_days"],
            max_bars=cfg["max_bars"]
        )

    # مدیریت مرکزی واچ‌لیست‌ها
    def show_watchlist_menu(chat_id, group: str):
        cfg = load_config()
        wl = get_watchlist(cfg, group)
        txt = f"واچ‌لیست {group}:\n"
        if not wl:
            txt += "خالی است.\n"
        else:
            for s, info in wl.items():
                txt += f"- {s}: قیمت ورود {info['price']} در {info['added_at']}\n"

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row(f"افزودن نماد به واچ‌لیست {group}", f"حذف نماد از واچ‌لیست {group}")
        kb.row(f"نمایش واچ‌لیست {group}", f"ریست واچ‌لیست {group}")
        kb.row("بازگشت به منوی اصلی")
        bot_1h.send_message(chat_id, txt, reply_markup=kb)

    @bot_1h.message_handler(func=lambda m: m.text == "مدیریت واچ‌لیست‌ها")
    def manage_all_watchlists(m):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("واچ‌لیست 1h", "واچ‌لیست 4h")
        kb.row("واچ‌لیست 1d", "واچ‌لیست 15m")
        kb.row("بازگشت به منوی اصلی")
        bot_1h.send_message(m.chat.id, "انتخاب واچ‌لیست تایم‌فریم:", reply_markup=kb)

    @bot_1h.message_handler(func=lambda m: m.text == "واچ‌لیست 1h")
    def wl_1h_menu(m):
        show_watchlist_menu(m.chat.id, "1h")

    @bot_1h.message_handler(func=lambda m: m.text == "واچ‌لیست 4h")
    def wl_4h_menu(m):
        show_watchlist_menu(m.chat.id, "4h")

    @bot_1h.message_handler(func=lambda m: m.text == "واچ‌لیست 1d")
    def wl_1d_menu(m):
        show_watchlist_menu(m.chat.id, "1d")

    @bot_1h.message_handler(func=lambda m: m.text == "واچ‌لیست 15m")
    def wl_15m_menu(m):
        show_watchlist_menu(m.chat.id, "15m")

    # افزودن نماد به واچ‌لیست‌ها
    def add_wl_step(m, group: str):
        try:
            parts = m.text.strip().split()
            symbol = parts[0].upper()
            price = float(parts[1])
        except:
            bot_1h.send_message(m.chat.id, "فرمت اشتباه است. مثال: BTCUSDT 12345")
            return
        cfg = load_config()
        add_to_watchlist(cfg, group, symbol, price)
        bot_1h.send_message(m.chat.id, f"{symbol} با قیمت {price} به واچ‌لیست {group} اضافه شد.")
        show_watchlist_menu(m.chat.id, group)

    @bot_1h.message_handler(func=lambda m: m.text.startswith("افزودن نماد به واچ‌لیست "))
    def add_wl_any(m):
        text = m.text.strip()
        if "1h" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد و قیمت را به صورت BTCUSDT 12345 وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: add_wl_step(mm, "1h"))
        elif "4h" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد و قیمت را به صورت BTCUSDT 12345 وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: add_wl_step(mm, "4h"))
        elif "1d" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد و قیمت را به صورت BTCUSDT 12345 وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: add_wl_step(mm, "1d"))
        elif "15m" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد و قیمت را به صورت BTCUSDT 12345 وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: add_wl_step(mm, "15m"))

    # حذف نماد از واچ‌لیست‌ها
    def remove_wl_step(m, group: str):
        symbol = m.text.strip().upper()
        cfg = load_config()
        wl = get_watchlist(cfg, group)
        if symbol in wl:
            remove_from_watchlist(cfg, group, symbol)
            bot_1h.send_message(m.chat.id, f"{symbol} از واچ‌لیست {group} حذف شد.")
        else:
            bot_1h.send_message(m.chat.id, f"{symbol} در واچ‌لیست {group} وجود ندارد.")
        show_watchlist_menu(m.chat.id, group)

    @bot_1h.message_handler(func=lambda m: m.text.startswith("حذف نماد از واچ‌لیست "))
    def remove_wl_any(m):
        text = m.text.strip()
        if "1h" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر برای حذف را وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: remove_wl_step(mm, "1h"))
        elif "4h" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر برای حذف را وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: remove_wl_step(mm, "4h"))
        elif "1d" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر برای حذف را وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: remove_wl_step(mm, "1d"))
        elif "15m" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر برای حذف را وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: remove_wl_step(mm, "15m"))

    # نمایش واچ‌لیست‌ها
    @bot_1h.message_handler(func=lambda m: m.text.startswith("نمایش واچ‌لیست "))
    def show_wl_any(m):
        text = m.text.strip()
        cfg = load_config()
        if "1h" in text:
            wl = get_watchlist(cfg, "1h")
            group = "1h"
        elif "4h" in text:
            wl = get_watchlist(cfg, "4h")
            group = "4h"
        elif "1d" in text:
            wl = get_watchlist(cfg, "1d")
            group = "1d"
        elif "15m" in text:
            wl = get_watchlist(cfg, "15m")
            group = "15m"
        else:
            return
        txt = f"واچ‌لیست {group}:\n"
        if not wl:
            txt += "خالی است.\n"
        else:
            for s, info in wl.items():
                txt += f"- {s}: قیمت ورود {info['price']} در {info['added_at']}\n"
        bot_1h.send_message(m.chat.id, txt)

    # ریست واچ‌لیست‌ها (گروه)
    @bot_1h.message_handler(func=lambda m: m.text.startswith("ریست واچ‌لیست "))
    def reset_wl_any(m):
        text = m.text.strip()
        cfg = load_config()
        if "1h" in text:
            reset_watchlist_group(cfg, "1h")
            bot_1h.send_message(m.chat.id, "واچ‌لیست 1h پاک شد.")
            show_watchlist_menu(m.chat.id, "1h")
        elif "4h" in text:
            reset_watchlist_group(cfg, "4h")
            bot_1h.send_message(m.chat.id, "واچ‌لیست 4h پاک شد.")
            show_watchlist_menu(m.chat.id, "4h")
        elif "1d" in text:
            reset_watchlist_group(cfg, "1d")
            bot_1h.send_message(m.chat.id, "واچ‌لیست 1d پاک شد.")
            show_watchlist_menu(m.chat.id, "1d")
        elif "15m" in text:
            reset_watchlist_group(cfg, "15m")
            bot_1h.send_message(m.chat.id, "واچ‌لیست 15m پاک شد.")
            show_watchlist_menu(m.chat.id, "15m")

    # بازگشت به منوی اصلی
    @bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
    def back_to_main(m):
        refresh_menu(bot_1h, m.chat.id)

    # تنظیم آلارم‌ها (همان قبلی)
    @bot_1h.message_handler(func=lambda m: m.text == "تنظیم آلارم‌ها")
    def alarms_menu(m):
        cfg = load_config()
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                f"WMA جهت ({'ON' if cfg.get('alarm_wma_direction', True) else 'OFF'})",
                callback_data="alarm_wma_direction"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                f"Cross SMA20 ({'ON' if cfg.get('alarm_cross_sma20', False) else 'OFF'})",
                callback_data="alarm_cross_sma20"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                f"Cross SMA100 ({'ON' if cfg.get('alarm_cross_sma100', False) else 'OFF'})",
                callback_data="alarm_cross_sma100"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                f"Cross SMA200 ({'ON' if cfg.get('alarm_cross_sma200', False) else 'OFF'})",
                callback_data="alarm_cross_sma200"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                f"SMA20 جهت ({'ON' if cfg.get('alarm_sma20_direction', False) else 'OFF'})",
                callback_data="alarm_sma20_direction"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                f"SMA100 جهت ({'ON' if cfg.get('alarm_sma100_direction', False) else 'OFF'})",
                callback_data="alarm_sma100_direction"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                f"SMA200 جهت ({'ON' if cfg.get('alarm_sma200_direction', False) else 'OFF'})",
                callback_data="alarm_sma200_direction"
            )
        )
        bot_1h.send_message(m.chat.id, "آلارم‌ها را تنظیم کنید:", reply_markup=kb)

    @bot_1h.callback_query_handler(func=lambda c: c.data.startswith("alarm_"))
    def toggle_alarm(c):
        cfg = load_config()
        key = c.data
        current = cfg.get(key, False)
        cfg[key] = not current
        save_config(cfg)
        bot_1h.answer_callback_query(c.id, f"{key} -> {'ON' if cfg[key] else 'OFF'}")
        alarms_menu(c.message)

    # بازنشانی نمادهای 1h
    @bot_1h.message_handler(func=lambda m: m.text == "بازنشانی نمادها")
    def reset_symbols(m):
        cfg = load_config()
        cfg["hourly_symbols"] = DEFAULT_CONFIG["hourly_symbols"]
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "نمادهای 1h بازنشانی شدند.")

    # راهنما
    @bot_1h.message_handler(func=lambda m: m.text == "راهنما")
    def help_menu(m):
        bot_1h.send_message(m.chat.id, HELP_TEXT)

    # رفرش منو
    @bot_1h.message_handler(func=lambda m: m.text == "رفرش منو")
    def refresh_menu_btn(m):
        refresh_menu(bot_1h, m.chat.id)

    # شروع چرخه‌ها
    @bot_1h.message_handler(func=lambda m: m.text == "شروع چرخه‌ها")
    def start_cycles(m):
        bot_1h.send_message(m.chat.id, "چرخه‌ها به‌صورت خودکار طبق زمان‌بندی اجرا می‌شوند.\nبرای اجرای فوری از دستورات /start_cycle_* استفاده کنید.")

    # وضعیت سیستم
    @bot_1h.message_handler(func=lambda m: m.text == "وضعیت سیستم")
    def system_status(m):
        cfg = load_config()
        txt = "سیستم فعال است.\n" + now_utc_str()
        txt += f"\nواچ‌لیست 1h: {len(get_watchlist(cfg,'1h'))} نماد"
        txt += f"\nواچ‌لیست 4h: {len(get_watchlist(cfg,'4h'))} نماد"
        txt += f"\nواچ‌لیست 1d: {len(get_watchlist(cfg,'1d'))} نماد"
        txt += f"\nواچ‌لیست 15m: {len(get_watchlist(cfg,'15m'))} نماد"
        txt += f"\ncycle_progress_batch: {cfg.get('cycle_progress_batch',5)}"
        txt += f"\nwatchlist_status_every_cycles: {cfg.get('watchlist_status_every_cycles',4)}"
        txt += f"\nmake_pdf (روزانه): {'ON' if cfg.get('make_pdf',True) else 'OFF'}"
        bot_1h.send_message(m.chat.id, txt)

    # گزارش آلارم‌ها
    @bot_1h.message_handler(func=lambda m: m.text == "گزارش آلارم‌ها")
    def alarms_report(m):
        if not LAST_ALARMS:
            bot_1h.send_message(m.chat.id, "هیچ آلارمی ثبت نشده است.")
            return

        txt = "آخرین آلارم‌ها:\n\n"
        for item in LAST_ALARMS[-50:]:
            txt += f"{item['symbol']} ({item['interval']}):\n"
            for a in item["alarms"]:
                txt += f" - {a}\n"
            txt += f"زمان: {item['time']}\n\n"

        bot_1h.send_message(m.chat.id, txt)

    # تنظیمات پیشرفته – بدون سؤال، مستقیم قابل تنظیم
    @bot_1h.message_handler(func=lambda m: m.text == "تنظیمات پیشرفته")
    def advanced_settings(m):
        cfg = load_config()
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                f"PDF روزانه ({'ON' if cfg.get('make_pdf', True) else 'OFF'})",
                callback_data="adv_make_pdf"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                f"batch سیکل = {cfg.get('cycle_progress_batch',5)}",
                callback_data="adv_cycle_batch_toggle"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                f"ارسال وضعیت واچ‌لیست هر {cfg.get('watchlist_status_every_cycles',4)} سیکل",
                callback_data="adv_watchlist_status_toggle"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                "ریست همهٔ واچ‌لیست‌ها",
                callback_data="adv_reset_all_watchlists"
            )
        )
        kb.add(
            types.InlineKeyboardButton(
                "ریست کامل برنامه (config)",
                callback_data="adv_reset_app"
            )
        )
        bot_1h.send_message(m.chat.id, "تنظیمات پیشرفته:", reply_markup=kb)

    @bot_1h.callback_query_handler(func=lambda c: c.data.startswith("adv_"))
    def advanced_settings_handler(c):
        cfg = load_config()
        if c.data == "adv_make_pdf":
            cfg["make_pdf"] = not cfg.get("make_pdf", True)
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, f"make_pdf -> {'ON' if cfg['make_pdf'] else 'OFF'}")
        elif c.data == "adv_cycle_batch_toggle":
            current = cfg.get("cycle_progress_batch", 5)
            cfg["cycle_progress_batch"] = 10 if current == 5 else 5
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, f"cycle_progress_batch -> {cfg['cycle_progress_batch']}")
        elif c.data == "adv_watchlist_status_toggle":
            current = cfg.get("watchlist_status_every_cycles", 4)
            cfg["watchlist_status_every_cycles"] = 2 if current == 4 else 4
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, f"watchlist_status_every_cycles -> {cfg['watchlist_status_every_cycles']}")
        elif c.data == "adv_reset_all_watchlists":
            reset_all_watchlists(cfg)
            bot_1h.answer_callback_query(c.id, "تمام واچ‌لیست‌ها پاک شدند.")
        elif c.data == "adv_reset_app":
            cfg = reset_config()
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, "برنامه و تنظیمات به حالت اولیه برگشت.")
        advanced_settings(c.message)

# =========================
# دریافت دیتا، اندیکاتورها، نمودارها
# =========================

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str) -> str:
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

def fetch_ohlc(symbol: str, interval: str, lookback_days: int, max_bars: int) -> pd.DataFrame:
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
        rows = []
        for k in data:
            rows.append([
                int(k[0]), float(k[1]), float(k[2]),
                float(k[3]), float(k[4]), float(k[5])
            ])
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
        rows = []
        for k in data:
            rows.append([
                int(k[0]), float(k[1]), float(k[3]),
                float(k[4]), float(k[2]), float(k[5])
            ])
        df = pd.DataFrame(rows, columns=["t","o","h","l","c","v"])
        df["t"] = pd.to_datetime(df["t"], unit="s", utc=True)
        df.sort_values("t", inplace=True)
        df.set_index("t", inplace=True)
        return df
    except:
        return pd.DataFrame()

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["SMA20"]  = df["c"].rolling(20).mean()
    df["SMA100"] = df["c"].rolling(100).mean()
    df["SMA200"] = df["c"].rolling(200).mean()

    df["WMA20"] = df["c"].rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x)+1)),
        raw=True
    )
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

def create_plotly_chart(
    symbol: str,
    interval: str,
    lookback_days: int,
    max_bars: int,
    png_name: str,
    html_name: str,
    watch_price: float = None
) -> dict:

    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)
    if df.empty:
        df = pd.DataFrame(columns=["o","h","l","c","v"])
        df.index = pd.to_datetime([])
    else:
        df = df[["o","h","l","c","v"]]

    df = compute_indicators(df)

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["o"],
            high=df["h"],
            low=df["l"],
            close=df["c"],
            name="Price"
        ),
        row=1, col=1
    )

    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"],  mode="lines", name="SMA20",  line=dict(color="blue")),   row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA100"], mode="lines", name="SMA100", line=dict(color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], mode="lines", name="SMA200", line=dict(color="purple")), row=1, col=1)

    wma   = df["WMA20"]
    slope = df["WMA20_slope"]
    wma_up   = wma.where(slope >= 0)
    wma_down = wma.where(slope < 0)

    fig.add_trace(go.Scatter(x=df.index, y=wma_up,   mode="lines", name="WMA20 Up",   line=dict(color="green", width=2, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=wma_down, mode="lines", name="WMA20 Down", line=dict(color="red",   width=2, dash="dot")), row=1, col=1)

    if watch_price is not None:
        fig.add_hline(
            y=watch_price,
            line=dict(color="purple", dash="dash"),
            annotation_text=f"Watch {symbol} @ {watch_price}",
            annotation_position="top left",
            row=1, col=1
        )

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], mode="lines", name="RSI14", line=dict(color="brown")), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="red", dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="green", dash="dash"), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"],        mode="lines", name="MACD",   line=dict(color="black")),   row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], mode="lines", name="Signal", line=dict(color="magenta")), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="Hist", marker_color="gray"), row=3, col=1)

    fig.update_layout(
        title=f"{symbol} – {interval}",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=1000
    )

    fig.add_annotation(
        text=f"{symbol} – {interval}",
        xref="paper", yref="paper",
        x=0.5, y=1.05,
        showarrow=False,
        font=dict(size=30, color="black")
    )

    fig.update_yaxes(side="right", showgrid=True)

    html_path = os.path.join(HTML_DIR, html_name)
    fig.write_html(html_path)

    png_path = os.path.join(CHARTS_DIR, png_name)
    fig.write_image(png_path, width=1800, height=1100, scale=3)

    return {
        "symbol": symbol,
        "interval": interval,
        "png_path": png_path,
        "html_path": html_path,
        "created_at": now_utc_str(),
        "last_close": float(df["c"].iloc[-1]) if len(df["c"]) else None,
        "wma": df["WMA20"].tolist() if "WMA20" in df.columns else [],
        "wma_slope": df["WMA20_slope"].tolist() if "WMA20_slope" in df.columns else [],
        "sma20": df["SMA20"].tolist() if "SMA20" in df.columns else [],
        "sma100": df["SMA100"].tolist() if "SMA100" in df.columns else [],
        "sma200": df["SMA200"].tolist() if "SMA200" in df.columns else []
    }

# =========================
# آلارم‌ها
# =========================

def detect_alarms(cfg: dict, info: dict) -> list:
    alarms = []

    wma    = info["wma"]
    slope  = info["wma_slope"]
    sma20  = info["sma20"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]

    if len(wma) < 3 or len(slope) < 3:
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
        LAST_ALARMS.append({
            "symbol": info["symbol"],
            "interval": info["interval"],
            "time": info["created_at"],
            "alarms": alarms
        })
        if len(LAST_ALARMS) > 500:
            LAST_ALARMS.pop(0)

    return alarms

# =========================
# چرخه‌ها
# =========================

def run_cycle(group: str, bot, chat_id: int, symbols: list, interval: str, lookback_days: int, max_bars: int):
    if not bot or not chat_id:
        return

    cfg = load_config()
    batch_size = cfg.get("cycle_progress_batch", 5)

    bot.send_message(chat_id, f"شروع چرخه {group}\n# {now_utc_str()} UTC")

    if isinstance(symbols, str):
        symbols = [symbols]
    unique_symbols = list(dict.fromkeys(symbols))

    total = len(unique_symbols)
    processed = 0

    cycle_alarms = []

    pdf = None
    pdf_filename = None
    if group == "1d" and cfg.get("make_pdf", True):
        pdf_filename = os.path.join(PDF_DIR, f"{group}_{now_utc().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf = PdfPages(pdf_filename)

    CYCLE_COUNTERS[group] = CYCLE_COUNTERS.get(group, 0) + 1
    send_watch_status = (CYCLE_COUNTERS[group] % cfg.get("watchlist_status_every_cycles", 4) == 0)

    wl_group = get_watchlist(cfg, group)

    for sym in unique_symbols:
        processed += 1

        if processed % batch_size == 0 or processed == 1 or processed == total:
            bot.send_message(
                chat_id,
                f"چرخه {group}: {processed} از {total} نماد پردازش شد، {total - processed} باقی مانده."
            )

        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"{group}_{sym}_{ts}.png"
        html = f"{group}_{sym}_{ts}.html"

        watch_price = None
        if sym in wl_group:
            watch_price = wl_group[sym]["price"]

        info = create_plotly_chart(sym, interval, lookback_days, max_bars, png, html, watch_price=watch_price)
        alarms = detect_alarms(cfg, info)

        if alarms:
            cycle_alarms.append({
                "symbol": sym,
                "interval": interval,
                "alarms": alarms
            })

            caption = f"{sym} ({group})\n" + "\n".join(alarms)

            with open(info["png_path"], "rb") as f:
                bot.send_photo(chat_id, f, caption=caption)

        if send_watch_status and sym in wl_group:
            caption = f"وضعیت واچ‌لیست {group} – {sym}\nقیمت ورود: {wl_group[sym]['price']}\nزمان ورود: {wl_group[sym]['added_at']}"
            with open(info["png_path"], "rb") as f:
                bot.send_photo(chat_id, f, caption=caption)

        if group == "1d" and pdf is not None:
            img = plt.imread(info["png_path"])
            fig, ax = plt.subplots(figsize=(10,6))
            ax.imshow(img)
            ax.axis("off")
            ax.set_title(f"{sym} – {group}")
            pdf.savefig(fig)
            plt.close(fig)

        time.sleep(1)

    if group == "1d" and pdf is not None:
        pdf.close()
        try:
            with open(pdf_filename, "rb") as f:
                bot.send_document(chat_id, f, caption=f"گزارش کامل روزانه – چرخه {group}")
        except:
            bot.send_message(chat_id, "ارسال PDF روزانه با مشکل مواجه شد.")

    if cycle_alarms:
        table = "جدول آلارم‌های این سیکل:\n\n"
        for item in cycle_alarms:
            table += f"{item['symbol']} ({item['interval']}):\n"
            for a in item["alarms"]:
                table += f" - {a}\n"
            table += "\n"
        bot.send_message(chat_id, table)
    else:
        bot.send_message(chat_id, "در این سیکل هیچ آلارمی فعال نشد.")

    bot.send_message(chat_id, f"پایان چرخه {group}")

# =========================
# لوپ‌های زمان‌بندی و اجرای فوری
# =========================

def loop_1h():
    while True:
        cfg = load_config()
        now = dt.datetime.now()

        if now.minute == 30 and bot_1h and cfg.get("chat_id_1h"):
            run_cycle(
                "1h",
                bot_1h,
                cfg["chat_id_1h"],
                cfg["hourly_symbols"],
                "1h",
                cfg["hourly_lookback_days"],
                cfg["max_bars"]
            )
            time.sleep(60)

        time.sleep(20)

def loop_4h():
    times = [(4,30),(8,30),(12,30),(16,30),(20,30),(23,30),(0,30)]
    while True:
        cfg = load_config()
        now = dt.datetime.now()

        for h, m in times:
            if now.hour == h and now.minute == m and bot_4h and cfg.get("chat_id_4h"):
                run_cycle(
                    "4h",
                    bot_4h,
                    cfg["chat_id_4h"],
                    cfg["fourh_symbols"],
                    "4h",
                    cfg["fourh_lookback_days"],
                    cfg["max_bars"]
                )
                time.sleep(60)

        time.sleep(20)

def loop_1d():
    while True:
        cfg = load_config()
        now = dt.datetime.now()

        if now.hour == 23 and now.minute == 30 and bot_1d and cfg.get("chat_id_1d"):
            run_cycle(
                "1d",
                bot_1d,
                cfg["chat_id_1d"],
                cfg["daily_symbols"],
                "1d",
                cfg["daily_lookback_days"],
                cfg["max_bars"]
            )
            time.sleep(60)

        time.sleep(20)

def loop_15m():
    while True:
        cfg = load_config()
        now = dt.datetime.now()

        if now.minute % 15 == 0 and bot_15m and cfg.get("chat_id_15m"):

            symbols = cfg["fifteenm_symbols"]
            if isinstance(symbols, str):
                symbols = [symbols]

            run_cycle(
                "15m",
                bot_15m,
                cfg["chat_id_15m"],
                symbols,
                "15m",
                cfg["fifteenm_lookback_days"],
                cfg["max_bars"]
            )

            time.sleep(60)

        time.sleep(20)

# اجرای فوری سیکل‌ها از ربات اصلی
if bot_1h:
    @bot_1h.message_handler(commands=["start_cycle"])
    def cmd_cycle_1h(m):
        cfg = load_config()
        run_cycle(
            "1h",
            bot_1h,
            cfg["chat_id_1h"],
            cfg["hourly_symbols"],
            "1h",
            cfg["hourly_lookback_days"],
            cfg["max_bars"]
        )

if bot_4h:
    @bot_4h.message_handler(commands=["start_cycle_4h"])
    def cmd_cycle_4h(m):
        cfg = load_config()
        run_cycle(
            "4h",
            bot_4h,
            cfg["chat_id_4h"],
            cfg["fourh_symbols"],
            "4h",
            cfg["fourh_lookback_days"],
            cfg["max_bars"]
        )

if bot_1d:
    @bot_1d.message_handler(commands=["start_cycle_1d"])
    def cmd_cycle_1d(m):
        cfg = load_config()
        run_cycle(
            "1d",
            bot_1d,
            cfg["chat_id_1d"],
            cfg["daily_symbols"],
            "1d",
            cfg["daily_lookback_days"],
            cfg["max_bars"]
        )

if bot_15m:
    @bot_15m.message_handler(commands=["start_cycle_15m"])
    def cmd_cycle_15m(m):
        cfg = load_config()
        symbols = cfg["fifteenm_symbols"]
        if isinstance(symbols, str):
            symbols = [symbols]
        run_cycle(
            "15m",
            bot_15m,
            cfg["chat_id_15m"],
            symbols,
            "15m",
            cfg["fifteenm_lookback_days"],
            cfg["max_bars"]
        )

# =========================
# اجرای نهایی main
# =========================

if __name__ == "__main__":

    if ADMIN_CHAT:
        if bot_1h:
            bot_1h.send_message(ADMIN_CHAT, "ربات اصلی 1h راه‌اندازی شد.")
        if bot_4h:
            bot_4h.send_message(ADMIN_CHAT, "ربات 4h راه‌اندازی شد.")
        if bot_1d:
            bot_1d.send_message(ADMIN_CHAT, "ربات 1d راه‌اندازی شد.")
        if bot_15m:
            bot_15m.send_message(ADMIN_CHAT, "ربات 15m راه‌اندازی شد.")

    if bot_1h:
        threading.Thread(target=bot_1h.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_1h, daemon=True).start()

    if bot_4h:
        threading.Thread(target=bot_4h.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_4h, daemon=True).start()

    if bot_1d:
        threading.Thread(target=bot_1d.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_1d, daemon=True).start()

    if bot_15m:
        threading.Thread(target=bot_15m.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_15m, daemon=True).start()

    while True:
        time.sleep(60)