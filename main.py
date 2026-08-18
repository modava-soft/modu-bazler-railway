# -*- coding: utf-8 -*-
# Modu Bazler – Scheduled Edition (Fixed-Time Cycles) – Layout 1 (SMA20, SMA50, WMA20)

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

import telebot
from telebot import types

# =========================================================
# PATHS
# =========================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
HTML_DIR   = os.path.join(DATA_DIR, "html")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, HTML_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

# =========================================================
# DEFAULT CONFIG
# =========================================================

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
    "alarm_cross_sma50": True,
    "alarm_cross_sma200": True,

    "make_pdf": True,

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None
}

# =========================================================
# CONFIG LOAD/SAVE + RESET
# =========================================================

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

# =========================================================
# TIME HELPERS
# =========================================================

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

# =========================================================
# BOT TOKENS
# =========================================================

TOKEN_1H = os.getenv("TOKEN_1H")
TOKEN_4H = os.getenv("TOKEN_4H")
TOKEN_1D = os.getenv("TOKEN_1D")

bot_1h = telebot.TeleBot(TOKEN_1H, parse_mode="HTML")
bot_4h = telebot.TeleBot(TOKEN_4H, parse_mode="HTML")
bot_1d = telebot.TeleBot(TOKEN_1D, parse_mode="HTML")

# =========================================================
# MENUS
# =========================================================

HELP_TEXT = """Modu Bazler – Scheduled Edition
چیدمان ۱ – SMA20, SMA50, WMA20
نمودار اصلی + RSI + MACD
PNG + PDF سه‌ردیفی
"""

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📈 تک‌نماد (۱ساعت)", "▶ اجرای دستی ۱ساعت")
    kb.row("▶ شروع چرخه‌ها", "⏹ توقف چرخه‌ها")
    kb.row("🔄 بازنشانی نمادها", "ℹ راهنما")
    bot_1h.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

# =========================================================
# START COMMANDS
# =========================================================

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
    bot_4h.send_message(
        m.chat.id,
        f"ربات ۴ساعته فعال شد.\n# {now_utc_str()} UTC"
    )

@bot_1d.message_handler(commands=["start"])
def start_1d(m):
    cfg = load_config()
    cfg["chat_id_1d"] = m.chat.id
    save_config(cfg)
    bot_1d.send_message(
        m.chat.id,
        f"ربات روزانه فعال شد.\n# {now_utc_str()} UTC"
    )

# =========================================================
# SYMBOL CHECK (SINGLE CHART)
# =========================================================

@bot_1h.message_handler(func=lambda m: m.text == "📈 تک‌نماد (۱ساعت)")
def ask_symbol(m):
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (مثلاً BTCUSDT):")
    bot_1h.register_next_step_handler(msg, do_symbol)

def do_symbol(m):
    symbol = m.text.strip().upper()
    cfg = load_config()
    bot_1h.send_message(m.chat.id, f"در حال ساخت نمودار برای {symbol} ...")

    ts = now_utc().strftime("%Y%m%d_%H%M%S")
    png_name = f"SINGLE_{symbol}_{ts}.png"
    pdf_name = f"SINGLE_{symbol}_{ts}.pdf"

    info = create_matplotlib_chart(
        symbol,
        cfg["hourly_interval"],
        cfg["hourly_lookback_days"],
        cfg["max_bars"],
        png_name,
        pdf_name
    )

    with open(info["png_path"], "rb") as f:
        bot_1h.send_photo(m.chat.id, f)

    if cfg.get("make_pdf", True):
        with open(info["pdf_path"], "rb") as f:
            bot_1h.send_document(m.chat.id, f)

# =========================================================
# DATA FETCH (BINANCE + KUCOIN)
# =========================================================

def _binance_interval(i):
    return {"1h": "1h", "4h": "4h", "1d": "1d"}[i]

def _kucoin_interval(i):
    return {"1h": "1hour", "4h": "4hour", "1d": "1day"}[i]

def fetch_ohlc(symbol, interval, lookback_days, max_bars):
    limit = max(200, max_bars)

    # Binance
    try:
        url = "https://api.binance.com/api/v3/klines"
        r = requests.get(
            url,
            params={
                "symbol": symbol,
                "interval": _binance_interval(interval),
                "limit": limit
            },
            timeout=10
        )
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

    # KuCoin fallback
    try:
        sym = symbol.replace("USDT", "-USDT")
        end = int(now_utc().timestamp())
        start = end - 60 * 60 * (limit + 10)
        url = "https://api.kucoin.com/api/v1/market/candles"
        r = requests.get(
            url,
            params={
                "symbol": sym,
                "type": _kucoin_interval(interval),
                "startAt": start,
                "endAt": end
            },
            timeout=10
        )
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

# =========================================================
# INDICATORS + CHART (SMA20, SMA50, WMA20, RSI, MACD)
# =========================================================

def compute_indicators(df):
    df = df.copy()

    # SMA20, SMA50, SMA200
    df["SMA20"]  = df["c"].rolling(20).mean()
    df["SMA50"]  = df["c"].rolling(50).mean()
    df["SMA200"] = df["c"].rolling(200).mean()

    # WMA20
    df["WMA20"] = df["c"].rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x)+1)),
        raw=True
    )
    df["WMA20_slope"] = df["WMA20"].diff()

    # RSI (14)
    delta = df["c"].diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    period = 14
    roll_gain = pd.Series(gain).rolling(period).mean()
    roll_loss = pd.Series(loss).rolling(period).mean()
    rs = roll_gain / (roll_loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD (12,26,9)
    ema12 = df["c"].ewm(span=12, adjust=False).mean()
    ema26 = df["c"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    return df

def create_matplotlib_chart(symbol, interval, lookback_days, max_bars, png_name, pdf_name):
    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)
    if df.empty:
        # create empty placeholder
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.text(0.5, 0.5, f"No data for {symbol}", ha="center", va="center")
        ax.set_axis_off()
        png_path = os.path.join(CHARTS_DIR, png_name)
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        fig.savefig(png_path, dpi=200, bbox_inches="tight")
        with PdfPages(pdf_path) as pdf:
            pdf.savefig(fig)
        plt.close(fig)
        return {
            "symbol": symbol,
            "interval": interval,
            "png_path": png_path,
            "pdf_path": pdf_path,
            "created_at": now_utc_str(),
            "last_close": None,
            "wma": [],
            "wma_slope": [],
            "sma20": [],
            "sma50": [],
            "sma200": []
        }

    df.columns = ["o","h","l","c","v"]
    df = compute_indicators(df)

    # figure with 3 rows: price+SMA/WMA, RSI, MACD
    fig = plt.figure(figsize=(18, 11))
    gs = fig.add_gridspec(3, 1, height_ratios=[3, 1, 1], hspace=0.05)

    # --- Row 1: Candles + SMA20, SMA50, WMA20 (right axis) ---
    ax_price = fig.add_subplot(gs[0])
    ax_price_right = ax_price.twinx()

    x = np.arange(len(df))
    dates = df.index

    # candles (simple OHLC bars)
    for i in range(len(df)):
        color = "green" if df["c"].iloc[i] >= df["o"].iloc[i] else "red"
        ax_price.vlines(x[i], df["l"].iloc[i], df["h"].iloc[i], color=color, linewidth=1)
        ax_price.vlines(x[i], df["o"].iloc[i], df["c"].iloc[i], color=color, linewidth=4)

    # SMA/WMA on right axis
    ax_price_right.plot(x, df["SMA20"],  color="blue",  label="SMA20")
    ax_price_right.plot(x, df["SMA50"],  color="orange",label="SMA50")
    ax_price_right.plot(x, df["WMA20"],  color="magenta",label="WMA20", linestyle="--")

    ax_price.set_ylabel("Price")
    ax_price_right.set_ylabel("SMA/WMA")

    # x ticks: every other
    ax_price.set_xticks(x[::2])
    ax_price.set_xticklabels([d.strftime("%Y-%m-%d\n%H:%M") for d in dates[::2]], rotation=0, fontsize=8)

    # legend + time in legend
    run_time = now_utc_str()
    ax_price_right.legend(
        loc="upper left",
        title=f"{symbol} {interval} | Run: {run_time}"
    )

    # --- Row 2: RSI ---
    ax_rsi = fig.add_subplot(gs[1], sharex=ax_price)
    ax_rsi.plot(x, df["RSI"], color="purple", label="RSI(14)")
    ax_rsi.axhline(70, color="red", linestyle="--", linewidth=0.8)
    ax_rsi.axhline(30, color="green", linestyle="--", linewidth=0.8)
    ax_rsi.set_ylabel("RSI")
    ax_rsi.set_ylim(0, 100)
    ax_rsi.legend(loc="upper left")
    ax_rsi.grid(True, alpha=0.3)

    # --- Row 3: MACD ---
    ax_macd = fig.add_subplot(gs[2], sharex=ax_price)
    ax_macd.plot(x, df["MACD"],        color="blue",  label="MACD")
    ax_macd.plot(x, df["MACD_signal"], color="orange",label="Signal")
    ax_macd.bar(x, df["MACD_hist"],    color="gray",  label="Hist", alpha=0.5)
    ax_macd.set_ylabel("MACD")
    ax_macd.legend(loc="upper left")
    ax_macd.grid(True, alpha=0.3)

    # remove extra x labels from RSI/MACD (only top has)
    plt.setp(ax_rsi.get_xticklabels(), visible=False)
    plt.setp(ax_macd.get_xticklabels(), visible=False)

    fig.suptitle(f"{symbol} – {interval} – Layout 1 (SMA20, SMA50, WMA20)", fontsize=14)

    png_path = os.path.join(CHARTS_DIR, png_name)
    pdf_path = os.path.join(PDF_DIR, pdf_name)

    fig.savefig(png_path, dpi=300, bbox_inches="tight")

    # PDF with 3 rows (same figure, single page)
    with PdfPages(pdf_path) as pdf:
        pdf.savefig(fig)

    plt.close(fig)

    return {
        "symbol": symbol,
        "interval": interval,
        "png_path": png_path,
        "pdf_path": pdf_path,
        "created_at": now_utc_str(),
        "last_close": float(df["c"].iloc[-1]),
        "wma": df["WMA20"].tolist(),
        "wma_slope": df["WMA20_slope"].tolist(),
        "sma20": df["SMA20"].tolist(),
        "sma50": df["SMA50"].tolist(),
        "sma200": df["SMA200"].tolist()
    }

# =========================================================
# ALARMS
# =========================================================

def detect_alarms(cfg, info):
    alarms = []
    wma = info["wma"]
    slope = info["wma_slope"]
    sma20 = info["sma20"]
    sma50 = info["sma50"]
    sma200 = info["sma200"]

    if len(wma) < 3:
        return alarms

    if cfg["alarm_wma_direction"]:
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("WMA20 Up")
        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("WMA20 Down")

    def cross(a, b):
        return (a[-2] - b[-2]) * (a[-1] - b[-1]) < 0

    if cfg["alarm_cross_sma20"] and cross(wma, sma20):
        alarms.append("WMA20 Cross SMA20")

    if cfg["alarm_cross_sma50"] and cross(wma, sma50):
        alarms.append("WMA20 Cross SMA50")

    if cfg["alarm_cross_sma200"] and cross(wma, sma200):
        alarms.append("WMA20 Cross SMA200")

    return alarms

# =========================================================
# CYCLE ENGINE
# =========================================================

def run_cycle(group, bot, chat_id, symbols, interval, lookback, max_bars):
    bot.send_message(
        chat_id,
        f"شروع چرخه {group}\n# {now_utc_str()} UTC"
    )

    cfg = load_config()

    for sym in symbols:
        bot.send_message(chat_id, f"در حال پردازش: {sym}")

        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png_name = f"{group}_{sym}_{ts}.png"
        pdf_name = f"{group}_{sym}_{ts}.pdf"

        info = create_matplotlib_chart(sym, interval, lookback, max_bars, png_name, pdf_name)
        alarms = detect_alarms(cfg, info)

        caption = f"{sym}\nآخرین قیمت: {info['last_close']}"
        if alarms:
            caption += "\n" + "\n".join(alarms)

        with open(info["png_path"], "rb") as f:
            bot.send_photo(chat_id, f, caption=caption)

        if cfg.get("make_pdf", True):
            with open(info["pdf_path"], "rb") as f:
                bot.send_document(chat_id, f)

    bot.send_message(chat_id, f"پایان چرخه {group}")

# =========================================================
# FIXED-TIME SCHEDULER
# =========================================================

def wait_until(h, m):
    while True:
        now = dt.datetime.now()
        if now.hour == h and now.minute == m:
            return
        time.sleep(20)

def loop_daily():
    while True:
        cfg = load_config()
        wait_until(23, 30)
        if cfg["chat_id_1d"]:
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

def loop_4h():
    times = [(4,30),(8,30),(12,30),(16,30),(20,30),(23,30),(0,30)]
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        for h,m in times:
            if now.hour == h and now.minute == m:
                if cfg["chat_id_4h"]:
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

def loop_1h():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute == 30:
            if cfg["chat_id_1h"]:
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

# =========================================================
# START / STOP / MANUAL BUTTONS
# =========================================================

@bot_1h.message_handler(func=lambda m: m.text == "⏹ توقف چرخه‌ها")
def stop_all(m):
    bot_1h.send_message(
        m.chat.id,
        "توقف چرخه‌ها انجام شد (فقط پیام، برای توقف کامل باید سرویس را متوقف کنید)."
    )

@bot_1h.message_handler(func=lambda m: m.text == "▶ شروع چرخه‌ها")
def start_all(m):
    bot_1h.send_message(
        m.chat.id,
        "چرخه‌های ۱ساعت، ۴ساعت و روزانه در حال اجرا هستند (بر اساس زمان‌بندی)."
    )

@bot_1h.message_handler(func=lambda m: m.text == "▶ اجرای دستی ۱ساعت")
def manual_1h(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    run_cycle(
        "1h",
        bot_1h,
        m.chat.id,
        cfg["hourly_symbols"],
        "1h",
        cfg["hourly_lookback_days"],
        cfg["max_bars"]
    )

@bot_1h.message_handler(func=lambda m: m.text == "🔄 بازنشانی نمادها")
def reset_symbols(m):
    cfg = load_config()
    cfg["hourly_symbols"] = DEFAULT_CONFIG["hourly_symbols"]
    cfg["fourh_symbols"]  = DEFAULT_CONFIG["fourh_symbols"]
    cfg["daily_symbols"]  = DEFAULT_CONFIG["daily_symbols"]
    save_config(cfg)
    bot_1h.send_message(m.chat.id, "نمادها به حالت پیش‌فرض بازنشانی شدند.")

@bot_1h.message_handler(func=lambda m: m.text == "ℹ راهنما")
def show_help(m):
    bot_1h.send_message(m.chat.id, HELP_TEXT)
    send_main_menu(m.chat.id)

# =========================================================
# THREADS
# =========================================================

def start_threads():
    # scheduler threads
    t1 = threading.Thread(target=loop_1h,    daemon=True)
    t2 = threading.Thread(target=loop_4h,    daemon=True)
    t3 = threading.Thread(target=loop_daily, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    # send start message to all bots if chat ids exist
    cfg = load_config()
    if cfg["chat_id_1h"]:
        bot_1h.send_message(cfg["chat_id_1h"], f"برنامه Modu Bazler شروع شد.\n# {now_utc_str()} UTC")
    if cfg["chat_id_4h"]:
        bot_4h.send_message(cfg["chat_id_4h"], f"برنامه Modu Bazler شروع شد.\n# {now_utc_str()} UTC")
    if cfg["chat_id_1d"]:
        bot_1d.send_message(cfg["chat_id_1d"], f"برنامه Modu Bazler شروع شد.\n# {now_utc_str()} UTC")

def start_bot_polling():
    th1 = threading.Thread(target=bot_1h.infinity_polling, daemon=True)
    th2 = threading.Thread(target=bot_4h.infinity_polling, daemon=True)
    th3 = threading.Thread(target=bot_1d.infinity_polling, daemon=True)
    th1.start()
    th2.start()
    th3.start()
    # keep main thread alive
    while True:
        time.sleep(10)

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    start_threads()
    start_bot_polling()