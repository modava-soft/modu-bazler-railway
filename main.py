# =========================
# SECTION 1 — CONFIG & BOTS
# =========================

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

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
HTML_DIR   = os.path.join(DATA_DIR, "html")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, HTML_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULT_CONFIG = {
    "hourly_symbols": ["BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT"],
    "fourh_symbols":  ["BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT"],
    "daily_symbols":  ["BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT"],
    "fifteenm_symbols": ["BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT"],

    "hourly_interval": "1h",
    "fourh_interval": "4h",
    "daily_interval": "1d",
    "fifteenm_interval": "15m",

    "hourly_lookback_days": 5,
    "fourh_lookback_days": 15,
    "daily_lookback_days": 180,
    "fifteenm_lookback_days": 3,

    "max_bars": 300,

    "alarm_wma_direction": True,
    "alarm_cross_sma20": True,
    "alarm_cross_sma100": True,
    "alarm_cross_sma200": True,

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None
}

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

TOKEN_1H  = (os.getenv("TOKEN_1H") or "").strip()
TOKEN_4H  = (os.getenv("TOKEN_4H") or "").strip()
TOKEN_1D  = (os.getenv("TOKEN_1D") or "").strip()
TOKEN_15M = (os.getenv("TOKEN_15M") or "").strip()

def create_bot(token):
    if not token or " " in token or ":" not in token:
        return None
    try:
        return telebot.TeleBot(token, parse_mode="HTML")
    except:
        return None

bot_1h  = create_bot(TOKEN_1H)
bot_4h  = create_bot(TOKEN_4H)
bot_1d  = create_bot(TOKEN_1D)
bot_15m = create_bot(TOKEN_15M)

# =========================
# SECTION 2 — MENUS & START
# =========================

HELP_TEXT = """
Modu Bazler – راهنمای کامل
(این متن را می‌توانی کامل‌تر کنی)
"""

def send_main_menu(bot, chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("چک یک نماد", "اجرای دستی 1h")
    kb.row("تنظیم آلارم‌ها", "بازنشانی نمادها")
    kb.row("راهنما", "رفرش منو")
    bot.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

def refresh_menu(bot, chat_id):
    try:
        send_main_menu(bot, chat_id)
    except:
        pass

# ---- START COMMANDS ----

if bot_1h:
    @bot_1h.message_handler(commands=["start"])
    def start_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)

        bot_1h.send_message(m.chat.id, HELP_TEXT)
        refresh_menu(bot_1h, m.chat.id)

if bot_4h:
    @bot_4h.message_handler(commands=["start"])
    def start_4h(m):
        cfg = load_config()
        cfg["chat_id_4h"] = m.chat.id
        save_config(cfg)
        bot_4h.send_message(m.chat.id, "ربات ۴ساعته فعال شد.")

if bot_1d:
    @bot_1d.message_handler(commands=["start"])
    def start_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        bot_1d.send_message(m.chat.id, "ربات روزانه فعال شد.")

if bot_15m:
    @bot_15m.message_handler(commands=["start"])
    def start_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        bot_15m.send_message(m.chat.id, "ربات ۱۵دقیقه‌ای فعال شد.")

# =========================
# SECTION 3 — DATA & CHART
# =========================

def fetch_ohlc(symbol, interval, lookback_days, max_bars):
    try:
        url = "https://api.binance.com/api/v3/klines"
        r = requests.get(url, params={
            "symbol": symbol,
            "interval": interval,
            "limit": max_bars
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        rows = []
        for k in data:
            rows.append([int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4])])
        df = pd.DataFrame(rows, columns=["t","o","h","l","c"])
        df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
        df.set_index("t", inplace=True)
        return df
    except:
        return pd.DataFrame()

def compute_indicators(df):
    df["SMA20"]  = df["c"].rolling(20).mean()
    df["SMA100"] = df["c"].rolling(100).mean()
    df["SMA200"] = df["c"].rolling(200).mean()

    df["WMA20"] = df["c"].rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x)+1)),
        raw=True
    )
    df["WMA20_slope"] = df["WMA20"].diff()

    delta = df["c"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    roll_gain = pd.Series(gain).rolling(14).mean()
    roll_loss = pd.Series(loss).rolling(14).mean()
    rs = roll_gain / roll_loss
    df["RSI14"] = 100 - (100 / (1 + rs))

    return df

def create_chart(symbol, interval, lookback_days, max_bars, png_name):
    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)
    df = compute_indicators(df)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["o"], high=df["h"], low=df["l"], close=df["c"]
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA100"], name="SMA100"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], name="SMA200"), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], name="RSI14"), row=2, col=1)

    png_path = os.path.join(CHARTS_DIR, png_name)
    fig.write_image(png_path, width=1600, height=900)

    return {
        "png_path": png_path,
        "wma": df["WMA20"].tolist(),
        "wma_slope": df["WMA20_slope"].tolist(),
        "sma20": df["SMA20"].tolist(),
        "sma100": df["SMA100"].tolist(),
        "sma200": df["SMA200"].tolist()
    }


# =========================
# SECTION 4 — ALARMS & CYCLE
# =========================

def detect_alarms(cfg, info):
    alarms = []
    wma = info["wma"]
    slope = info["wma_slope"]
    sma20 = info["sma20"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]

    def cross(a, b):
        return (a[-2] - b[-2]) * (a[-1] - b[-1]) < 0

    if cfg["alarm_wma_direction"]:
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("WMA20 صعودی شد")
        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("WMA20 نزولی شد")

    if cfg["alarm_cross_sma20"] and cross(wma, sma20):
        alarms.append("WMA20 با SMA20 برخورد کرد")

    if cfg["alarm_cross_sma100"] and cross(wma, sma100):
        alarms.append("WMA20 با SMA100 برخورد کرد")

    if cfg["alarm_cross_sma200"] and cross(wma, sma200):
        alarms.append("WMA20 با SMA200 برخورد کرد")

    return alarms

def run_cycle(group, bot, chat_id, symbols, interval, lookback_days, max_bars):
    bot.send_message(chat_id, f"شروع چرخه {group}")

    cfg = load_config()

    for sym in symbols:
        bot.send_message(chat_id, f"در حال پردازش: {sym}")

        png_name = f"{group}_{sym}_{now_utc().strftime('%Y%m%d_%H%M%S')}.png"
        info = create_chart(sym, interval, lookback_days, max_bars, png_name)
        alarms = detect_alarms(cfg, info)

        with open(info["png_path"], "rb") as f:
            bot.send_photo(chat_id, f, caption="\n".join(alarms) if alarms else sym)

    bot.send_message(chat_id, f"پایان چرخه {group}")

# =========================
# SECTION 5 — SCHEDULER & MAIN
# =========================

def loop_1h():
    while True:
        now = dt.datetime.now()
        if now.minute == 30:
            cfg = load_config()
            if cfg["chat_id_1h"]:
                run_cycle("1h", bot_1h, cfg["chat_id_1h"],
                          cfg["hourly_symbols"], "1h",
                          cfg["hourly_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

def loop_4h():
    while True:
        now = dt.datetime.now()
        if now.hour in [4,8,12,16,20,23] and now.minute == 30:
            cfg = load_config()
            if cfg["chat_id_4h"]:
                run_cycle("4h", bot_4h, cfg["chat_id_4h"],
                          cfg["fourh_symbols"], "4h",
                          cfg["fourh_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

def loop_1d():
    while True:
        now = dt.datetime.now()
        if now.hour == 23 and now.minute == 30:
            cfg = load_config()
            if cfg["chat_id_1d"]:
                run_cycle("1d", bot_1d, cfg["chat_id_1d"],
                          cfg["daily_symbols"], "1d",
                          cfg["daily_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

def loop_15m():
    while True:
        now = dt.datetime.now()
        if now.minute % 15 == 0:
            cfg = load_config()
            if cfg["chat_id_15m"]:
                run_cycle("15m", bot_15m, cfg["chat_id_15m"],
                          cfg["fifteenm_symbols"], "15m",
                          cfg["fifteenm_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

if __name__ == "__main__":
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
        time.sleep(10)

