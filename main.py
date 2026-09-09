# -*- coding: utf-8 -*-
# Modu Bazler v7 – main.py (بازنویسی کامل با اصلاحات درخواستی)

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
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image

import telebot
from telebot import types

# =========================================================
# مسیرها و تنظیمات پایه
# =========================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PDF_DIR = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config_v7.json")

# =========================================================
# تنظیمات پیش‌فرض
# =========================================================
# نکته:
# - پیش‌فرض گزارشات: 15 (cycle_progress_batch)
# - تعداد کندل‌ها:
#   * روزانه (1d) و 4 ساعته (4h): 60
#   * 15 دقیقه (15m): 40
#   * 1 ساعته (1h): 80
# - تعداد کندل‌ها باید مضربی از 20 باشند (در منوی تنظیمات قابل تغییر است)

DEFAULT_CONFIG = {
    "symbols_1h": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
        "SOLUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
        "TRXUSDT", "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "XMRUSDT",
        "ETCUSDT", "XLMUSDT", "FILUSDT", "APTUSDT", "NEARUSDT"
    ],
    "symbols_4h": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
        "SOLUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
        "TRXUSDT", "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "XMRUSDT",
        "ETCUSDT", "XLMUSDT", "FILUSDT", "APTUSDT", "NEARUSDT"
    ],
    "symbols_1d": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
        "SOLUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
        "TRXUSDT", "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "XMRUSDT",
        "ETCUSDT", "XLMUSDT", "FILUSDT", "APTUSDT", "NEARUSDT"
    ],
    "symbols_15m": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT",
        "DOGEUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT", "TRXUSDT", "AVAXUSDT",
        "LINKUSDT", "ATOMUSDT", "XMRUSDT", "ETCUSDT", "XLMUSDT", "FILUSDT",
        "APTUSDT", "NEARUSDT", "OPUSDT", "ARBUSDT", "SUIUSDT", "PEPEUSDT",
        "TONUSDT", "UNIUSDT", "AAVEUSDT", "INJUSDT", "RNDRUSDT", "FTMUSDT",
        "NEOUSDT", "GALAUSDT", "SEIUSDT", "TIAUSDT", "PYTHUSDT", "JTOUSDT",
        "WIFUSDT", "JUPUSDT", "STRKUSDT", "BLURUSDT", "RUNEUSDT", "RAYUSDT",
        "LDOUSDT", "COMPUSDT", "CRVUSDT", "MKRUSDT", "SNXUSDT", "GMXUSDT",
        "DYDXUSDT", "ENSUSDT"
    ],

    # تعداد کندل‌ها (مضربی از 20)
    "candles_1h": 80,
    "candles_4h": 60,
    "candles_1d": 60,
    "candles_15m": 40,

    # حداکثر بارها
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

    # حالت verbose
    "verbose_1h": True,
    "verbose_4h": True,
    "verbose_1d": True,
    "verbose_15m": True,

    # گزارشات (batch) – پیش‌فرض 15
    "cycle_progress_batch": 15,

    # تنظیمات ذخیره JPG و صفحه ترکیبی 12 تایی
    "save_jpg_enabled": True
}

# آخرین آلارم‌ها
LAST_ALARMS = {
    "1h": [],
    "4h": [],
    "1d": [],
    "15m": []
}

# لاک‌های سیکل
CYCLE_LOCKS = {
    "1h": threading.Lock(),
    "4h": threading.Lock(),
    "1d": threading.Lock(),
    "15m": threading.Lock()
}

# =========================================================
# توابع کمکی
# =========================================================

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
    # پاک کردن آلارم‌ها
    for k in LAST_ALARMS:
        LAST_ALARMS[k] = []
    save_config(cfg)
    return cfg


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")


# =========================================================
# ساخت ربات‌ها
# =========================================================

TOKEN_1H = (os.getenv("TOKEN_1H") or "").strip()
TOKEN_4H = (os.getenv("TOKEN_4H") or "").strip()
TOKEN_1D = (os.getenv("TOKEN_1D") or "").strip()
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


bot_1h = create_bot(TOKEN_1H)
bot_4h = create_bot(TOKEN_4H)
bot_1d = create_bot(TOKEN_1D)
bot_15m = create_bot(TOKEN_15M)

# =========================================================
# منوی اصلی (ربات 1h)
# =========================================================

HELP_TEXT = """
Modu Bazler v7

ربات چند‌تایم‌فریمی برای تحلیل بازار کریپتو.

دستورات اصلی:
/start  -> شروع و ثبت chat_id برای ربات 1h

منوی اصلی شامل:
- مدیریت ارزها برای هر تایم‌فریم
- تنظیمات آلارم‌ها
- وضعیت سیستم
- تنظیمات پیشرفته (PDF، verbose، ترکیبی 15m، تعداد کندل‌ها)
- اجرای چرخه‌ها با اختلاف ۵ دقیقه بین تایم‌فریم‌ها
- ریست کامل تنظیمات و اجرای مجدد سیکل‌ها به ترتیب
"""


def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("مدیریت ارزهای 1h", "مدیریت ارزهای 4h")
    kb.row("مدیریت ارزهای 1d", "مدیریت ارزهای 15m")

    kb.row("تنظیم آلارم‌ها", "گزارش آلارم‌ها")
    kb.row("وضعیت سیستم", "تنظیمات پیشرفته")

    kb.row("اجرای چرخه‌ها", "ریست کامل")

    bot_1h.send_message(chat_id, "منوی اصلی:", reply_markup=kb)


@bot_1h.message_handler(commands=["start"])
def start_main(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    bot_1h.send_message(m.chat.id, HELP_TEXT)
    send_main_menu(m.chat.id)


@bot_1h.message_handler(commands=["refresh"])
@bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
def refresh_main(m):
    send_main_menu(m.chat.id)


# =========================================================
# ریست کامل
# =========================================================

@bot_1h.message_handler(func=lambda m: m.text == "ریست کامل")
def reset_app(m):
    cfg = reset_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)

    # پاک کردن فایل‌های قبلی (اختیاری)
    try:
        for folder in [CHARTS_DIR, PDF_DIR]:
            for fn in os.listdir(folder):
                fp = os.path.join(folder, fn)
                if os.path.isfile(fp):
                    os.remove(fp)
    except Exception:
        pass

    bot_1h.send_message(m.chat.id, "ریست کامل انجام شد. تنظیمات به حالت پیش‌فرض برگشت.")
    send_main_menu(m.chat.id)

    # اجرای سیکل‌ها به ترتیب (1h -> 4h -> 1d -> 15m) با اختلاف ۵ دقیقه
    start_all_cycles_with_offset(m.chat.id)


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
, f"{symbol} قبلاً در لیست {group} وجود دارد.")
    show_symbol_menu(m.chat.id, group)


@bot_1h.message_handler(func=lambda m: m.text.startswith("افزودن ارز به "))
def add_symbol_any(m):
    group = m.text.split()[-1]
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (مثال: BTCUSDT):")
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


# =========================================================
# تنظیم آلارم‌ها
# =========================================================

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
        kb.add(
            types.InlineKeyboardButton(
                f"{key} ({'ON' if cfg.get(key) else 'OFF'})",
                callback_data=f"alarm_{key}"
            )
        )
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
    txt += f"تعداد کندل 1h: {cfg['candles_1h']}\n"
    txt += f"تعداد کندل 4h: {cfg['candles_4h']}\n"
    txt += f"تعداد کندل 1d: {cfg['candles_1d']}\n"
    txt += f"تعداد کندل 15m: {cfg['candles_15m']}\n"
    txt += f"گزارشات (batch): {cfg['cycle_progress_batch']}\n"
    txt += f"ذخیره JPG و صفحه ترکیبی: {'ON' if cfg['save_jpg_enabled'] else 'OFF'}\n"
    bot_1h.send_message(m.chat.id, txt)


# =========================================================
# تنظیمات پیشرفته (PDF، verbose، combined، تعداد کندل‌ها)
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

    # تنظیم تعداد کندل‌ها (مضربی از 20)
    kb.add(types.InlineKeyboardButton(
        f"کندل 1h: {cfg['candles_1h']}",
        callback_data="adv_candles_1h"
    ))
    kb.add(types.InlineKeyboardButton(
        f"کندل 4h: {cfg['candles_4h']}",
        callback_data="adv_candles_4h"
    ))
    kb.add(types.InlineKeyboardButton(
        f"کندل 1d: {cfg['candles_1d']}",
        callback_data="adv_candles_1d"
    ))
    kb.add(types.InlineKeyboardButton(
        f"کندل 15m: {cfg['candles_15m']}",
        callback_data="adv_candles_15m"
    ))

    # گزارشات batch
    kb.add(types.InlineKeyboardButton(
        f"گزارشات batch: {cfg['cycle_progress_batch']}",
        callback_data="adv_batch"
    ))

    # ذخیره JPG
    kb.add(types.InlineKeyboardButton(
        f"ذخیره JPG ({'ON' if cfg['save_jpg_enabled'] else 'OFF'})",
        callback_data="adv_save_jpg"
    ))

    # ریست از همین منو
    kb.add(types.InlineKeyboardButton(
        "ریست تنظیمات (پیش‌فرض)",
        callback_data="adv_reset_app"
    ))

    bot_1h.send_message(m.chat.id, "تنظیمات پیشرفته:", reply_markup=kb)


@bot_1h.callback_query_handler(func=lambda c: c.data.startswith("adv_"))
def advanced_settings_handler(c):
    cfg = load_config()
    data = c.data

    if data == "adv_pdf_1h":
        cfg["make_pdf_1h"] = not cfg["make_pdf_1h"]
        bot_1h.answer_callback_query(c.id, f"PDF 1h -> {'ON' if cfg['make_pdf_1h'] else 'OFF'}")

    elif data == "adv_pdf_1d":
        cfg["make_pdf_1d"] = not cfg["make_pdf_1d"]
        bot_1h.answer_callback_query(c.id, f"PDF 1d -> {'ON' if cfg['make_pdf_1d'] else 'OFF'}")

    elif data == "adv_combined_15m":
        cfg["make_combined_15m"] = not cfg.get("make_combined_15m", True)
        bot_1h.answer_callback_query(c.id, f"Combined 15m -> {'ON' if cfg['make_combined_15m'] else 'OFF'}")

    elif data == "adv_verbose_1h":
        cfg["verbose_1h"] = not cfg["verbose_1h"]
        bot_1h.answer_callback_query(c.id, f"verbose 1h -> {'ON' if cfg['verbose_1h'] else 'OFF'}")

    elif data == "adv_verbose_4h":
        cfg["verbose_4h"] = not cfg["verbose_4h"]
        bot_1h.answer_callback_query(c.id, f"verbose 4h -> {'ON' if cfg['verbose_4h'] else 'OFF'}")

    elif data == "adv_verbose_1d":
        cfg["verbose_1d"] = not cfg["verbose_1d"]
        bot_1h.answer_callback_query(c.id, f"verbose 1d -> {'ON' if cfg['verbose_1d'] else 'OFF'}")

    elif data == "adv_verbose_15m":
        cfg["verbose_15m"] = not cfg["verbose_15m"]
        bot_1h.answer_callback_query(c.id, f"verbose 15m -> {'ON' if cfg['verbose_15m'] else 'OFF'}")

    elif data.startswith("adv_candles_"):
        tf = data.split("_")[-1]  # 1h / 4h / 1d / 15m
        key = f"candles_{tf}"
        current = cfg[key]
        # افزایش یا کاهش مضربی از 20 (بین 20 و 400 مثلاً)
        new_val = current + 20
        if new_val > 400:
            new_val = 20
        cfg[key] = new_val
        bot_1h.answer_callback_query(c.id, f"{key} -> {new_val}")

    elif data == "adv_batch":
        current = cfg["cycle_progress_batch"]
        new_val = current + 5
        if new_val > 60:
            new_val = 15
        cfg["cycle_progress_batch"] = new_val
        bot_1h.answer_callback_query(c.id, f"batch -> {new_val}")

    elif data == "adv_save_jpg":
        cfg["save_jpg_enabled"] = not cfg["save_jpg_enabled"]
        bot_1h.answer_callback_query(c.id, f"save_jpg -> {'ON' if cfg['save_jpg_enabled'] else 'OFF'}")

    elif data == "adv_reset_app":
        cfg = reset_config()
        bot_1h.answer_callback_query(c.id, "تنظیمات به حالت پیش‌فرض برگشت.")
        cfg["chat_id_1h"] = c.message.chat.id

    save_config(cfg)
    advanced_settings(c.message)


# =========================================================
# اجرای چرخه‌ها با اختلاف ۵ دقیقه
# =========================================================

def run_cycle(group: str):
    """
    اجرای سیکل برای تایم‌فریم مشخص.
    اینجا فقط اسکلت کار را می‌گذاریم؛
    فرض می‌کنیم تابعی مثل fetch_data_and_make_charts وجود دارد.
    """
    cfg = load_config()
    candles_key = f"candles_{group}"
    candles = cfg.get(candles_key, 60)
    symbols = cfg.get(f"symbols_{group}", [])
    chat_id_key = f"chat_id_{group}"
    chat_id = cfg.get(chat_id_key)

    if not chat_id:
        return

    with CYCLE_LOCKS[group]:
        # اینجا باید داده‌ها را از صرافی بگیریم و چارت بسازیم
        # برای سادگی، فقط یک پیام تست می‌فرستیم
        bot_1h.send_message(
            chat_id,
            f"شروع سیکل {group} با {len(symbols)} ارز و {candles} کندل.\nزمان: {now_utc_str()}")

        # مثال: ساخت چارت‌ها و ذخیره JPG
        if cfg["save_jpg_enabled"]:
            # فرض: برای هر نماد یک تصویر ساخته می‌شود
            # اینجا فقط شبیه‌سازی می‌کنیم
            for i, sym in enumerate(symbols[:12]):  # حداکثر 12 تا برای صفحه ترکیبی
                img_path = os.path.join(CHARTS_DIR, f"{group}_{sym}.jpg")
                fig = plt.figure(figsize=(4, 3))
                plt.title(f"{group} - {sym}")
                plt.plot(np.random.randn(50).cumsum())
                plt.tight_layout()
                fig.savefig(img_path, dpi=150)
                plt.close(fig)

            # ساخت صفحه ترکیبی 12 تایی
            combined_path = os.path.join(CHARTS_DIR, f"{group}_combined_12.jpg")
            make_combined_page(group, symbols[:12], combined_path)

            # ارسال صفحه ترکیبی به ربات
            with open(combined_path, "rb") as f:
                bot_1h.send_photo(chat_id, f, caption=f"صفحه ترکیبی 12 چارت ({group})")


def make_combined_page(group: str, symbols, output_path: str):
    """
    چیدمان 12 تصویر روی یک صفحه بدون افت کیفیت محسوس.
    فرض: قبلاً برای هر نماد فایل JPG ساخته شده است.
    """
    images = []
    for sym in symbols:
        img_path = os.path.join(CHARTS_DIR, f"{group}_{sym}.jpg")
        if os.path.exists(img_path):
            images.append(Image.open(img_path))

    if not images:
        return

    # همه را به اندازه یکسان تبدیل می‌کنیم
    # مثلاً 600x400 برای هر چارت
    w, h = 600, 400
    resized = [img.resize((w, h), Image.LANCZOS) for img in images]

    # چیدمان 3x4 (12 تصویر)
    cols = 3
    rows = 4
    page_w = cols * w
    page_h = rows * h

    page = Image.new("RGB", (page_w, page_h), (255, 255, 255))

    for idx, img in enumerate(resized):
        r = idx // cols
        c = idx % cols
        x = c * w
        y = r * h
        page.paste(img, (x, y))

    page.save(output_path, "JPEG", quality=90)


def start_all_cycles_with_offset(chat_id_1h: int):
    """
    اجرای سیکل‌ها با اختلاف ۵ دقیقه:
    - 1h: بلافاصله
    - 4h: بعد از 5 دقیقه
    - 1d: بعد از 10 دقیقه
    - 15m: بعد از 15 دقیقه
    """
    cfg = load_config()
    cfg["chat_id_1h"] = chat_id_1h
    save_config(cfg)

    def delayed_run(group, delay_min):
        time.sleep(delay_min * 60)
        run_cycle(group)

    threading.Thread(target=delayed_run, args=("1h", 0), daemon=True).start()
    threading.Thread(target=delayed_run, args=("4h", 5), daemon=True).start()
    threading.Thread(target=delayed_run, args=("1d", 10), daemon=True).start()
    threading.Thread(target=delayed_run, args=("15m", 15), daemon=True).start()

    bot_1h.send_message(chat_id_1h, "اجرای چرخه‌ها با اختلاف ۵ دقیقه بین تایم‌فریم‌ها شروع شد.")


@bot_1h.message_handler(func=lambda m: m.text == "اجرای چرخه‌ها")
def run_cycles_command(m):
    start_all_cycles_with_offset(m.chat.id)


# =========================================================
# ربات‌های دیگر (ثبت chat_id و پیام شروع)
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

def main():
    threads = []

    if bot_1h:
        t1 = threading.Thread(target=bot_1h.infinity_polling, daemon=True)
        threads.append(t1)

    if bot_4h:
        t2 = threading.Thread(target=bot_4h.infinity_polling, daemon=True)
        threads.append(t2)

    if bot_1d:
        t3 = threading.Thread(target=bot_1d.infinity_polling, daemon=True)
        threads.append(t3)

    if bot_15m:
        t4 = threading.Thread(target=bot_15m.infinity_polling, daemon=True)
        threads.append(t4)

    for t in threads:
        t.start()

    # نگه داشتن برنامه
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()