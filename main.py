# -*- coding: utf-8 -*-
# Modu Bazler — Scheduled Edition (Fixed-Time Cycles)

import os
import json
import time
import threading
import datetime as dt

import matplotlib
matplotlib.use("Agg")

import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import telebot
from telebot import types

# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
HTML_DIR   = os.path.join(DATA_DIR, "html")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, HTML_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

# ============================================================
# DEFAULT CONFIG
# ============================================================

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

    "hourly_interval": "1h",
    "fourh_interval": "4h",
    "daily_interval": "1d",

    "hourly_lookback_days": 5,
    "fourh_lookback_days": 15,
    "daily_lookback_days": 180,
    "max_bars": 300,

    "alarm_wma_direction": True,
    "alarm_cross_sma20": True,
    "alarm_cross_sma100": True,
    "alarm_cross_sma200": True,

    "make_pdf": True,

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None
}

# ============================================================
# CONFIG LOAD/SAVE + RESET
# ============================================================

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def reset_config():
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
    save_config(DEFAULT_CONFIG.copy())

# ============================================================
# TIME HELPERS
# ============================================================

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

# ============================================================
# BOT TOKENS
# ============================================================

TOKEN_1H = os.getenv("TOKEN_1H")
TOKEN_4H = os.getenv("TOKEN_4H")
TOKEN_1D = os.getenv("TOKEN_1D")

bot_1h = telebot.TeleBot(TOKEN_1H, parse_mode="HTML")
bot_4h = telebot.TeleBot(TOKEN_4H, parse_mode="HTML")
bot_1d = telebot.TeleBot(TOKEN_1D, parse_mode="HTML")

# ============================================================
# MENUS
# ============================================================

HELP_TEXT = """
Modu Bazler — Scheduled Edition
"""

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔍 بررسی نماد", "🚀 اجرای فوری ۱ ساعته")
    kb.row("⚙️ تنظیمات", "⛔ توقف کامل")
    kb.row("▶ شروع برنامه", "🔁 ریست به ارزهای پیش‌فرض")
    bot_1h.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

# ============================================================
# START COMMANDS
# ============================================================

@bot_1h.message_handler(commands=["start"])
def start_1h(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    bot_1h.send_message(m.chat.id, HELP_TEXT)
    send_main_menu(m.chat.id)

@bot_4h.message_handler(commands=["start"])
def start_4h(m):
    cfg = load_config()
    cfg["chat_id_4h"] = m.chat.id
    save_config(cfg)
    bot_4h.send_message(m.chat.id, f"ربات ۴ ساعته فعال شد.\n⏱ {now_utc_str()} UTC")

@bot_1d.message_handler(commands=["start"])
def start_1d(m):
    cfg = load_config()
    cfg["chat_id_1d"] = m.chat.id
    save_config(cfg)
    bot_1d.send_message(m.chat.id, f"ربات روزانه فعال شد.\n⏱ {now_utc_str()} UTC")

# ============================================================
# SYMBOL CHECK
# ============================================================

@bot_1h.message_handler(func=lambda m: m.text == "🔍 بررسی نماد")
def ask_symbol(m):
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کن:")
    bot_1h.register_next_step_handler(msg, do_symbol)

def do_symbol(m):
    symbol = m.text.strip().upper()
    cfg = load_config()
    bot_1h.send_message(m.chat.id, f"⏳ ساخت چارت {symbol} ...")

    ts = now_utc().strftime("%Y%m%d_%H%M%S")
    png = f"SINGLE_{symbol}_{ts}.png"
    html = f"SINGLE_{symbol}_{ts}.html"

    info = create_plotly_chart(
        symbol,
        cfg["hourly_interval"],
        cfg["hourly_lookback_days"],
        cfg["max_bars"],
        png,
        html
    )

    with open(info["png_path"], "rb") as f:
        bot_1h.send_photo(m.chat.id, f)

# ============================================================
# DATA FETCH (BINANCE + KUCOIN)
# ============================================================

def _binance_interval(i): return {"1h":"1h","4h":"4h","1d":"1d"}[i]
def _kucoin_interval(i): return {"1h":"1hour","4h":"4hour","1d":"1day"}[i]

def fetch_ohlc(symbol, interval, lookback, max_bars):
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
                int(k[0]),
                float(k[1]), float(k[2]), float(k[3]), float(k[4]),
                float(k[5])
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
        start = end - 60*60*(limit+10)
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
                int(k[0]),
                float(k[1]), float(k[3]), float(k[4]), float(k[2]),
                float(k[5])
            ])
        df = pd.DataFrame(rows, columns=["t","o","h","l","c","v"])
        df["t"] = pd.to_datetime(df["t"], unit="s", utc=True)
        df.sort_values("t", inplace=True)
        df.set_index("t", inplace=True)
        return df
    except:
        return pd.DataFrame()

# ============================================================
# INDICATORS + CHART
# ============================================================

def compute_indicators(df):
    df = df.copy()
    df["SMA20"]  = df["c"].rolling(20).mean()
    df["SMA100"] = df["c"].rolling(100).mean()
    df["SMA200"] = df["c"].rolling(200).mean()

    df["WMA20"] = df["c"].rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x)+1)),
        raw=True
    )
    df["WMA20_slope"] = df["WMA20"].diff()

    return df

def create_plotly_chart(symbol, interval, lookback, max_bars, png_name, html_name):
    df = fetch_ohlc(symbol, interval, lookback, max_bars)
    df.columns = ["o","h","l","c","v"]
    df = compute_indicators(df)

    fig = make_subplots(rows=1, cols=1)
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["o"], high=df["h"], low=df["l"], close=df["c"]
    ))

    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], mode="lines"))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA100"], mode="lines"))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], mode="lines"))

    fig.add_trace(go.Scatter(x=df.index, y=df["WMA20"], mode="lines"))

    html_path = os.path.join(HTML_DIR, html_name)
    fig.write_html(html_path)

    png_path = os.path.join(CHARTS_DIR, png_name)
    fig.write_image(png_path, width=1800, .height=1100, scale=3)

    return {
        "symbol": symbol,
        "interval": interval,
        "png_path": png_path,
        "html_path": html_path,
        "created_at": now_utc_str(),
        "last_close": float(df["c"].iloc[-1]),
        "wma": df["WMA20"].tolist(),
        "wma_slope": df["WMA20_slope"].tolist(),
        "sma20": df["SMA20"].tolist(),
        "sma100": df["SMA100"].tolist(),
        "sma200": df["SMA200"].tolist()
    }

# ============================================================
# ALARMS
# ============================================================

def detect_alarms(cfg, info):
    alarms = []
    wma = info["wma"]
    slope = info["wma_slope"]
    sma20 = info["sma20"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]

    if cfg["alarm_wma_direction"]:
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("WMA Up")
        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("WMA Down")

    def cross(a, b):
        return (a[-2]-b[-2])*(a[-1]-b[-1]) < 0

    if cfg["alarm_cross_sma20"] and cross(wma, sma20):
        alarms.append("WMA Cross SMA20")

    if cfg["alarm_cross_sma100"] and cross(wma, sma100):
        alarms.append("WMA Cross SMA100")

    if cfg["alarm_cross_sma200"] and cross(wma, sma200):
        alarms.append("WMA Cross SMA200")

    return alarms

# ============================================================
# CYCLE ENGINE
# ============================================================

def run_cycle(group, bot, chat_id, symbols, interval, lookback, max_bars):
    bot.send_message(chat_id, f"🟦 شروع سیکل {group}\n⏱ {now_utc_str()} UTC")

    cfg = load_config()

    for sym in symbols:
        bot.send_message(chat_id, f"🔄 در حال پردازش: {sym}")

        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"{group}_{sym}_{ts}.png"
        html = f"{group}_{sym}_{ts}.html"

        info = create_plotly_chart(sym, interval, lookback, max_bars, png, html)

        alarms = detect_alarms(cfg, info)

        if alarms:
            caption = f"🚨 {sym}\n" + "\n".join(alarms)
            with open(info["png_path"], "rb") as f:
                bot.send_photo(chat_id, f, caption=caption)

    bot.send_message(chat_id, f"✅ پایان سیکل {group}")

# ============================================================
# FIXED-TIME SCHEDULER
# ============================================================

def wait_until(h, m):
    while True:
        now = dt.datetime.now()
        if now.hour == h and now.minute == m:
            return
        time.sleep(20)

def loop_daily():
    cfg = load_config()
    while True:
        wait_until(23, 30)
        if cfg["chat_id_1d"]:
            run_cycle("1d", bot_1d, cfg["chat_id_1d"],
                      cfg["daily_symbols"], "1d",
                      cfg["daily_lookback_days"], cfg["max_bars"])
        time.sleep(60)

def loop_4h():
    times = [(4,30),(8,30),(12,30),(16,30),(20,30),(23,30),(0,30)]
    cfg = load_config()
    while True:
        now = dt.datetime.now()
        for h,m in times:
            if now.hour == h and now.minute == m:
                if cfg["chat_id_4h"]:
                    run_cycle("4h", bot_4h, cfg["chat_id_4h"],
                              cfg["fourh_symbols"], "4h",
                              cfg["fourh_lookback_days"], cfg["max_bars"])
                time.sleep(60)
        time.sleep(20)

def loop_1h():
    cfg = load_config()
    while True:
        now = dt.datetime.now()
        if now.minute == 30:
            if cfg["chat_id_1h"]:
                run_cycle("1h", bot_1h, cfg["chat_id_1h"],
                          cfg["hourly_symbols"], "1h",
                          cfg["hourly_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

# ============================================================
# START / STOP / MANUAL
# ============================================================

@bot_1h.message_handler(func=lambda m: m.text == "⛔ توقف کامل")
def stop_all(m):
    bot_1h.send_message(m.chat.id, "⛔ توقف فعال شد (اما زمان‌بندی ثابت ادامه دارد).")

@bot_1h.message_handler(func=lambda m: m.text == "▶ شروع برنامه")
def start_all(m):
    bot_1h.send_message(m.chat.id, "▶ برنامه شروع شد.")

@bot_1h.message_handler(func=lambda m: m.text == "🚀 اجرای فوری ۱ ساعته")
def manual_1h(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    run_cycle("1h", bot_1h, m.chat.id,
              cfg["hourly_symbols"], "1h",
              cfg["hourly_lookback_days"], cfg["max_bars"])

@bot_1h.message_handler(func=lambda m: m.text == "🔁 ریست به ارزهای پیش‌فرض")
def reset_symbols(m):
    cfg = load_config()
    cfg["hourly_symbols"] = DEFAULT_CONFIG["hourly_symbols"]
    cfg["fourh_symbols"]  = DEFAULT_CONFIG["fourh_symbols"]
    cfg["daily_symbols"]  = DEFAULT_CONFIG["daily_symbols"]
    save_config(cfg)
    bot_1h.send_message(m.chat.id, "نمادها به حالت پیش‌فرض ریست شدند.")

# ============================================================
# THREADS
# ============================================================

def start_threads():
    t1 = threading.Thread(target=loop_1h, daemon=True)
    t2 = threading.Thread(target=loop_4h, daemon=True)
    t3 = threading.Thread(target=loop_daily, daemon=True)

    t1.start()
    t2.start()
    t3.start()

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    start_threads()
    bot_1h.infinity_polling()
    bot_4h.infinity_polling()
    bot_1d.infinity_polling()