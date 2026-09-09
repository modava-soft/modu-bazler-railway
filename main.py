# -*- coding: utf-8 -*-
# Modu Bazler v5.2 – بازنویسی کامل با اصلاحات درخواستی

import os
import json
import time
import threading
import datetime as dt

import requests
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image

import telebot
from telebot import types

# =========================================================
# مسیرها و تنظیمات پایه
# =========================================================

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config_v5_2.json")

# =========================================================
# تنظیمات پیش‌فرض
# =========================================================
# 1) پیش‌فرض گزارشات ۱۵
# 2) پیش‌فرض کندل‌ها:
#    - روزانه (1d) و 4 ساعته (4h): 60
#    - 15 دقیقه (15m): 40
#    - 1 ساعته (1h): 80
# 3) max_bars همان 300
# =========================================================

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

    # تعداد کندل‌ها (مضربی از 20)
    "lookback_1h": 80,
    "lookback_4h": 60,
    "lookback_1d": 60,
    "lookback_15m": 40,
    "max_bars": 300,

    # آلارم‌ها
    "alarm_wma_direction": True,
    "alarm_cross_sma20": False,
    "alarm_cross_sma100": False,
    "alarm_cross_sma200": False,
    "alarm_sma20_direction": False,
    "alarm_sma100_direction": False,
    "alarm_sma200_direction": False,

    # ساخت PDF
    "make_pdf_1h": True,
    "make_pdf_1d": True,

    # ساخت چارت ترکیبی 15m
    "make_combined_15m": True,

    # chat_id ها
    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,

    # verbose
    "verbose_1h": True,
    "verbose_4h": True,
    "verbose_1d": True,
    "verbose_15m": True,

    # گزارشات – پیش‌فرض 15
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

def reset_config() -> dict:
    cfg = DEFAULT_CONFIG.copy()
    # پاک کردن همه اطلاعات و ریست کامل
    cfg["chat_id_1h"] = None
    cfg["chat_id_4h"] = None
    cfg["chat_id_1d"] = None
    cfg["chat_id_15m"] = None
    save_config(cfg)
    return cfg

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

# =========================================================
# توکن‌ها و ساخت بات‌ها
# =========================================================

TOKEN_1H  = (os.getenv("TOKEN_1H")  or "").strip()
TOKEN_4H  = (os.getenv("TOKEN_4H")  or "").strip()
TOKEN_1D  = (os.getenv("TOKEN_1D")  or "").strip()
TOKEN_15M = (os.getenv("TOKEN_15M") or "").strip()
ADMIN_CHAT = (os.getenv("ADMIN_CHAT_ID") or "").strip()

def create_bot(token: str):
    if not token or not isinstance(token, str):
        return None
    if any(ch.isspace() for ch in token):
        return None
    try:
        return telebot.TeleBot(token, parse_mode="HTML")
    except Exception:
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
    "1h":  threading.Lock(),
    "4h":  threading.Lock(),
    "1d":  threading.Lock(),
    "15m": threading.Lock()
}

# =========================================================
# متن راهنما
# =========================================================

HELP_TEXT = """
Modu Bazler v5.2

دستورات اصلی:
/start  – شروع و ثبت chat_id برای ربات 1h
/refresh – نمایش مجدد منوی اصلی

منوی اصلی شامل:
- مدیریت ارزها برای هر تایم‌فریم
- تنظیمات آلارم‌ها
- گزارش آلارم‌ها
- وضعیت سیستم
- تنظیمات پیشرفته
- اجرای چرخه‌ها
- ریست کامل برنامه

تعداد کندل‌ها (مضربی از 20):
- 1h: پیش‌فرض 80
- 4h: پیش‌فرض 60
- 1d: پیش‌فرض 60
- 15m: پیش‌فرض 40

چرخه‌ها با اختلاف 5 دقیقه بین تایم‌فریم‌ها اجرا می‌شوند.
"""

# =========================================================
# منوی اصلی ربات 1h
# =========================================================

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("اجرای چرخه‌ها", "گزارش آلارم‌ها")
    kb.row("مدیریت ارزهای 1h", "مدیریت ارزهای 4h")
    kb.row("مدیریت ارزهای 1d", "مدیریت ارزهای 15m")
    kb.row("تنظیمات آلارم‌ها", "وضعیت سیستم")
    kb.row("تنظیمات پیشرفته", "ریست کامل برنامه")
    bot_1h.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

@bot_1h.message_handler(commands=["start"])
def start_main(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    bot_1h.send_message(m.chat.id, HELP_TEXT)
    send_main_menu(m.chat.id)

@bot_1h.message_handler(commands=["refresh"])
@bot_1h.message_handler(func=lambda m: m.text == "منوی اصلی")
def refresh_main(m):
    send_main_menu(m.chat.id)

# =========================================================
# ریست کامل برنامه
# =========================================================

@bot_1h.message_handler(func=lambda m: m.text == "ریست کامل برنامه")
def reset_app(m):
    cfg = reset_config()
    bot_1h.send_message(m.chat.id, "برنامه و تنظیمات به طور کامل ریست شد.")
    send_main_menu(m.chat.id)

# =========================================================
# مدیریت ارزها
# =========================================================

def get_symbols(cfg, group):
    return cfg[f"symbols_{group}"]

def set_symbols(cfg, group, symbols):
    cfg[f"symbols_{group}"] = symbols
    save_config(cfg)

def show_symbol_menu(chat_id, group):
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    txt = f"لیست ارزهای {group}:\n"
    txt += ", ".join(symbols) if symbols else "هیچ ارزی ثبت نشده است."
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(f"افزودن ارز به {group}", f"حذف ارز از {group}")
    kb.row(f"نمایش ارزهای {group}")
    kb.row("بازگشت به منوی اصلی")
    bot_1h.send_message(chat_id, txt, reply_markup=kb)

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت ارزهای 1h")
def manage_1h(m):
    show_symbol_menu(m.chat.id, "1h")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت ارزهای 4h")
def manage_4h(m):
    show_symbol_menu(m.chat.id, "4h")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت ارزهای 1d")
def manage_1d(m):
    show_symbol_menu(m.chat.id, "1d")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت ارزهای 15m")
def manage_15m(m):
    show_symbol_menu(m.chat.id, "15m")

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

@bot_1h.message_handler(func=lambda m: m.text.startswith("افزودن ارز به "))
def add_symbol_any(m):
    group = m.text.split()[-1]
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (مثلاً BTCUSDT):")
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
        bot_1h.send_message(m.chat.id, f"{symbol} در لیست {group} یافت نشد.")
    show_symbol_menu(m.chat.id, group)

@bot_1h.message_handler(func=lambda m: m.text.startswith("حذف ارز از "))
def remove_symbol_any(m):
    group = m.text.split()[-1]
    msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر برای حذف را وارد کنید:")
    bot_1h.register_next_step_handler(msg, lambda mm: remove_symbol_step(mm, group))

@bot_1h.message_handler(func=lambda m: m.text.startswith("نمایش ارزهای "))
def show_symbols_any(m):
    group = m.text.split()[-1]
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    txt = f"ارزهای {group}:\n"
    txt += ", ".join(symbols) if symbols else "هیچ ارزی ثبت نشده است."
    bot_1h.send_message(m.chat.id, txt)

@bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
def back_to_main(m):
    send_main_menu(m.chat.id)

# =========================================================
# تنظیمات آلارم‌ها
# =========================================================

@bot_1h.message_handler(func=lambda m: m.text == "تنظیمات آلارم‌ها")
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
    bot_1h.send_message(m.chat.id, "تنظیمات آلارم‌ها:", reply_markup=kb)

@bot_1h.callback_query_handler(func=lambda c: c.data.startswith("alarm_"))
def toggle_alarm(c):
    cfg = load_config()
    key = c.data.replace("alarm_", "")
    cfg[key] = not cfg.get(key)
    save_config(cfg)
    bot_1h.answer_callback_query(c.id, f"{key} -> {'ON' if cfg[key] else 'OFF'}")
    alarms_menu(c.message)

# =========================================================
# گزارش آلارم‌ها
# =========================================================

@bot_1h.message_handler(func=lambda m: m.text == "گزارش آلارم‌ها")
def alarms_report(m):
    txt = ""
    for group in ["1h", "4h", "1d", "15m"]:
        if LAST_ALARMS[group]:
            txt += f"آلارم‌های {group}:\n"
            for item in LAST_ALARMS[group]:
                txt += f"{item['symbol']} ({item['interval']}):\n"
                for a in item["alarms"]:
                    txt += f"  - {a}\n"
                txt += f"زمان: {item['time']}\n\n"
    if not txt:
        txt = "هیچ آلارمی ثبت نشده است."
    bot_1h.send_message(m.chat.id, txt)

# =========================================================
# وضعیت سیستم
# =========================================================

@bot_1h.message_handler(func=lambda m: m.text == "وضعیت سیستم")
def system_status(m):
    cfg = load_config()
    txt = "وضعیت سیستم:\n"
    txt += f"تعداد ارزهای 1h: {len(cfg['symbols_1h'])}\n"
    txt += f"تعداد ارزهای 4h: {len(cfg['symbols_4h'])}\n"
    txt += f"تعداد ارزهای 1d: {len(cfg['symbols_1d'])}\n"
    txt += f"تعداد ارزهای 15m: {len(cfg['symbols_15m'])}\n"
    txt += f"PDF 1h: {'ON' if cfg['make_pdf_1h'] else 'OFF'}\n"
    txt += f"PDF 1d: {'ON' if cfg['make_pdf_1d'] else 'OFF'}\n"
    txt += f"Combined 15m: {'ON' if cfg.get('make_combined_15m', True) else 'OFF'}\n"
    txt += f"verbose 1h: {'ON' if cfg['verbose_1h'] else 'OFF'}\n"
    txt += f"verbose 4h: {'ON' if cfg['verbose_4h'] else 'OFF'}\n"
    txt += f"verbose 1d: {'ON' if cfg['verbose_1d'] else 'OFF'}\n"
    txt += f"verbose 15m: {'ON' if cfg['verbose_15m'] else 'OFF'}\n"
    txt += f"تعداد کندل 1h: {cfg['lookback_1h']}\n"
    txt += f"تعداد کندل 4h: {cfg['lookback_4h']}\n"
    txt += f"تعداد کندل 1d: {cfg['lookback_1d']}\n"
    txt += f"تعداد کندل 15m: {cfg['lookback_15m']}\n"
    txt += f"گزارشات (batch): {cfg['cycle_progress_batch']}\n"
    bot_1h.send_message(m.chat.id, txt)

# =========================================================
# تنظیمات پیشرفته (PDF، Combined، verbose، تعداد کندل‌ها)
# =========================================================

@bot_1h.message_handler(func=lambda m: m.text == "تنظیمات پیشرفته")
def advanced_settings(m):
    cfg = load_config()
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        f"PDF 1h ({'ON' if cfg['make_pdf_1h'] else 'OFF'})",
        callback_data="adv_pdf_1h"
    ))
    kb.add(types.InlineKeyboardButton(
        f"PDF 1d ({'ON' if cfg['make_pdf_1d'] else 'OFF'})",
        callback_data="adv_pdf_1d"
    ))
    kb.add(types.InlineKeyboardButton(
        f"Combined 15m ({'ON' if cfg.get('make_combined_15m', True) else 'OFF'})",
        callback_data="adv_combined_15m"
    ))
    kb.add(types.InlineKeyboardButton(
        f"verbose 1h ({'ON' if cfg['verbose_1h'] else 'OFF'})",
        callback_data="adv_verbose_1h"
    ))
    kb.add(types.InlineKeyboardButton(
        f"verbose 4h ({'ON' if cfg['verbose_4h'] else 'OFF'})",
        callback_data="adv_verbose_4h"
    ))
    kb.add(types.InlineKeyboardButton(
        f"verbose 1d ({'ON' if cfg['verbose_1d'] else 'OFF'})",
        callback_data="adv_verbose_1d"
    ))
    kb.add(types.InlineKeyboardButton(
        f"verbose 15m ({'ON' if cfg['verbose_15m'] else 'OFF'})",
        callback_data="adv_verbose_15m"
    ))
    kb.add(types.InlineKeyboardButton(
        "تغییر تعداد کندل‌ها (مضربی از 20)",
        callback_data="adv_change_lookbacks"
    ))
    kb.add(types.InlineKeyboardButton(
        "ریست کامل برنامه",
        callback_data="adv_reset_app"
    ))
    bot_1h.send_message(m.chat.id, "تنظیمات پیشرفته:", reply_markup=kb)

@bot_1h.callback_query_handler(func=lambda c: c.data.startswith("adv_"))
def advanced_settings_handler(c):
    cfg = load_config()
    data = c.data

    if data == "adv_pdf_1h":
        cfg["make_pdf_1h"] = not cfg["make_pdf_1h"]
        save_config(cfg)
        bot_1h.answer_callback_query(c.id, f"PDF 1h -> {'ON' if cfg['make_pdf_1h'] else 'OFF'}")
        advanced_settings(c.message)

    elif data == "adv_pdf_1d":
        cfg["make_pdf_1d"] = not cfg["make_pdf_1d"]
        save_config(cfg)
        bot_1h.answer_callback_query(c.id, f"PDF 1d -> {'ON' if cfg['make_pdf_1d'] else 'OFF'}")
        advanced_settings(c.message)

    elif data == "adv_combined_15m":
        cfg["make_combined_15m"] = not cfg.get("make_combined_15m", True)
        save_config(cfg)
        bot_1h.answer_callback_query(c.id, f"Combined 15m -> {'ON' if cfg['make_combined_15m'] else 'OFF'}")
        advanced_settings(c.message)

    elif data == "adv_verbose_1h":
        cfg["verbose_1h"] = not cfg["verbose_1h"]
        save_config(cfg)
        bot_1h.answer_callback_query(c.id, f"verbose 1h -> {'ON' if cfg['verbose_1h'] else 'OFF'}")
        advanced_settings(c.message)

    elif data == "adv_verbose_4h":
        cfg["verbose_4h"] = not cfg["verbose_4h"]
        save_config(cfg)
        bot_1h.answer_callback_query(c.id, f"verbose 4h -> {'ON' if cfg['verbose_4h'] else 'OFF'}")
        advanced_settings(c.message)

    elif data == "adv_verbose_1d":
        cfg["verbose_1d"] = not cfg["verbose_1d"]
        save_config(cfg)
        bot_1h.answer_callback_query(c.id, f"verbose 1d -> {'ON' if cfg['verbose_1d'] else 'OFF'}")
        advanced_settings(c.message)

    elif data == "adv_verbose_15m":
        cfg["verbose_15m"] = not cfg["verbose_15m"]
        save_config(cfg)
        bot_1h.answer_callback_query(c.id, f"verbose 15m -> {'ON' if cfg['verbose_15m'] else 'OFF'}")
        advanced_settings(c.message)

    elif data == "adv_change_lookbacks":
        msg = bot_1h.send_message(
            c.message.chat.id,
            "تعداد کندل‌ها را به صورت چهار عدد (1h, 4h, 1d, 15m) وارد کن.\n"
            "هر عدد باید مضربی از 20 باشد. مثال: 80 60 60 40"
        )
        bot_1h.register_next_step_handler(msg, change_lookbacks_step)
        bot_1h.answer_callback_query(c.id, "ورود مقادیر جدید تعداد کندل‌ها.")

    elif data == "adv_reset_app":
        reset_config()
        bot_1h.answer_callback_query(c.id, "برنامه ریست شد.")
        bot_1h.send_message(c.message.chat.id, "برنامه و تنظیمات به طور کامل ریست شد.")
        send_main_menu(c.message.chat.id)

def change_lookbacks_step(m):
    text = m.text.strip()
    parts = text.split()
    if len(parts) != 4:
        bot_1h.send_message(m.chat.id, "فرمت اشتباه است. باید چهار عدد وارد شود. مثال: 80 60 60 40")
        return
    try:
        lb_1h, lb_4h, lb_1d, lb_15m = map(int, parts)
    except ValueError:
        bot_1h.send_message(m.chat.id, "لطفاً فقط عدد وارد کن.")
        return

    for v in [lb_1h, lb_4h, lb_1d, lb_15m]:
        if v <= 0 or v % 20 != 0:
            bot_1h.send_message(m.chat.id, "هر عدد باید مثبت و مضربی از 20 باشد.")
            return

    cfg = load_config()
    cfg["lookback_1h"] = lb_1h
    cfg["lookback_4h"] = lb_4h
    cfg["lookback_1d"] = lb_1d
    cfg["lookback_15m"] = lb_15m
    save_config(cfg)
    bot_1h.send_message(
        m.chat.id,
        f"تعداد کندل‌ها تنظیم شد:\n1h: {lb_1h}\n4h: {lb_4h}\n1d: {lb_1d}\n15m: {lb_15m}"
    )
    send_main_menu(m.chat.id)

# =========================================================
# چرخه‌ها – اجرای با اختلاف 5 دقیقه
# =========================================================

def fetch_klines(symbol, interval, limit):
    # نمونه ساده – می‌توانی با API واقعی جایگزین کنی
    # اینجا فقط داده‌ی ساختگی تولید می‌شود
    times = pd.date_range(end=now_utc(), periods=limit, freq="1min")
    prices = np.linspace(100, 200, limit) + np.random.randn(limit) * 5
    df = pd.DataFrame({"time": times, "close": prices})
    return df

def make_chart(symbol, interval, df, out_path):
    plt.figure(figsize=(8, 4))
    plt.plot(df["time"], df["close"], label=symbol)
    plt.title(f"{symbol} – {interval}")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

def run_cycle(group, interval, lookback, chat_id, bot, make_pdf=False, combined=False):
    if not chat_id or not bot:
        return

    cfg = load_config()
    symbols = get_symbols(cfg, group)
    if not symbols:
        bot.send_message(chat_id, f"هیچ ارزی برای {group} ثبت نشده است.")
        return

    images = []
    for symbol in symbols:
        df = fetch_klines(symbol, interval, lookback)
        img_name = f"{group}_{symbol}_{int(time.time())}.jpg"
        img_path = os.path.join(CHARTS_DIR, img_name)
        make_chart(symbol, interval, df, img_path)
        images.append(img_path)
        # ارسال هر چارت به ربات
        with open(img_path, "rb") as f:
            bot.send_photo(chat_id, f, caption=f"{symbol} – {group}")

    # ذخیره و ترکیب 12 چارت در یک صفحه (jpg)
    if images:
        page_images = []
        for i in range(0, len(images), 12):
            batch = images[i:i+12]
            page_img = combine_images_12(batch)
            page_images.append(page_img)
            with open(page_img, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"صفحه ترکیبی {group}")

    # ساخت PDF در صورت نیاز
    if make_pdf and images:
        pdf_name = f"{group}_{int(time.time())}.pdf"
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        with PdfPages(pdf_path) as pdf:
            for img in images:
                fig = plt.figure(figsize=(8, 4))
                im = Image.open(img)
                plt.imshow(im)
                plt.axis("off")
                pdf.savefig(fig)
                plt.close(fig)
        with open(pdf_path, "rb") as f:
            bot.send_document(chat_id, f, caption=f"PDF {group}")

def combine_images_12(image_paths):
    # ترکیب حداکثر 12 تصویر در یک صفحه بدون کاهش کیفیت محسوس
    # چیدمان 3x4
    imgs = [Image.open(p) for p in image_paths]
    # اندازه‌ی پایه را از اولین تصویر می‌گیریم
    w, h = imgs[0].size
    cols, rows = 3, 4
    # اگر تعداد کمتر از 12 باشد، فقط همان‌ها را می‌چینیم
    total = len(imgs)
    canvas_w = cols * w
    canvas_h = rows * h
    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")

    for idx, img in enumerate(imgs):
        r = idx // cols
        c = idx % cols
        x = c * w
        y = r * h
        canvas.paste(img, (x, y))

    out_name = f"combined_{int(time.time())}.jpg"
    out_path = os.path.join(CHARTS_DIR, out_name)
    canvas.save(out_path, "JPEG", quality=95)
    return out_path

def start_all_cycles(chat_id):
    cfg = load_config()

    # ترتیب اجرای چرخه‌ها با اختلاف 5 دقیقه:
    # 1) 1h
    # 2) 4h (بعد از 5 دقیقه)
    # 3) 1d (بعد از 10 دقیقه)
    # 4) 15m (بعد از 15 دقیقه)

    def run_1h():
        with CYCLE_LOCKS["1h"]:
            run_cycle("1h", "1h", cfg["lookback_1h"], cfg["chat_id_1h"], bot_1h, make_pdf=cfg["make_pdf_1h"])

    def run_4h():
        with CYCLE_LOCKS["4h"]:
            run_cycle("4h", "4h", cfg["lookback_4h"], cfg["chat_id_4h"], bot_4h)

    def run_1d():
        with CYCLE_LOCKS["1d"]:
            run_cycle("1d", "1d", cfg["lookback_1d"], cfg["chat_id_1d"], bot_1d, make_pdf=cfg["make_pdf_1d"])

    def run_15m():
        with CYCLE_LOCKS["15m"]:
            run_cycle("15m", "15m", cfg["lookback_15m"], cfg["chat_id_15m"], bot_15m, combined=cfg.get("make_combined_15m", True))

    # اجرای 1h بلافاصله
    threading.Thread(target=run_1h, daemon=True).start()
    # اجرای 4h بعد از 5 دقیقه
    threading.Timer(5 * 60, lambda: threading.Thread(target=run_4h, daemon=True).start()).start()
    # اجرای 1d بعد از 10 دقیقه
    threading.Timer(10 * 60, lambda: threading.Thread(target=run_1d, daemon=True).start()).start()
    # اجرای 15m بعد از 15 دقیقه
    threading.Timer(15 * 60, lambda: threading.Thread(target=run_15m, daemon=True).start()).start()

    bot_1h.send_message(chat_id, "چرخه‌ها با اختلاف 5 دقیقه برای هر تایم‌فریم شروع شدند.")

@bot_1h.message_handler(func=lambda m: m.text == "اجرای چرخه‌ها")
def run_cycles_command(m):
    start_all_cycles(m.chat.id)

# =========================================================
# ثبت chat_id برای سایر ربات‌ها
# =========================================================

if bot_4h:
    @bot_4h.message_handler(commands=["start"])
    def start_4h(m):
        cfg = load_config()
        cfg["chat_id_4h"] = m.chat.id
        save_config(cfg)
        bot_4h.send_message(m.chat.id, "ربات 4h فعال شد.\n" + now_utc_str())

if bot_1d:
    @bot_1d.message_handler(commands=["start"])
    def start_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        bot_1d.send_message(m.chat.id, "ربات 1d فعال شد.\n" + now_utc_str())

if bot_15m:
    @bot_15m.message_handler(commands=["start"])
    def start_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        bot_15m.send_message(m.chat.id, "ربات 15m فعال شد.\n" + now_utc_str())

# =========================================================
# اجرای ربات‌ها
# =========================================================

def run_bot(bot):
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception:
        time.sleep(5)
        run_bot(bot)

threads = []

if bot_1h:
    t = threading.Thread(target=run_bot, args=(bot_1h,), daemon=True)
    t.start()
    threads.append(t)

if bot_4h:
    t = threading.Thread(target=run_bot, args=(bot_4h,), daemon=True)
    t.start()
    threads.append(t)

if bot_1d:
    t = threading.Thread(target=run_bot, args=(bot_1d,), daemon=True)
    t.start()
    threads.append(t)

if bot_15m:
    t = threading.Thread(target=run_bot, args=(bot_15m,), daemon=True)
    t.start()
    threads.append(t)

# نگه داشتن برنامه
while True:
    time.sleep(10)