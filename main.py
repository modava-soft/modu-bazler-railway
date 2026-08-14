# -*- coding: utf-8 -*-
# Modu Bazler – Scheduled Edition (Fixed-Time Cycles + 15m Bot + RSI/MACD + Alarms)

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

# ======================================================================
# PATHS
# ======================================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
HTML_DIR   = os.path.join(DATA_DIR, "html")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, HTML_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

# ======================================================================
# DEFAULT CONFIG
# ======================================================================

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
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT",
        "UNIUSDT","SANDUSDT","AXSUSDT","AAVEUSDT","FTMUSDT",
        "GALAUSDT","ROSEUSDT","RUNEUSDT","CRVUSDT","SNXUSDT",
        "INJUSDT","OPUSDT","ARBUSDT","SEIUSDT","TIAUSDT",
        "PYTHUSDT","JTOUSDT","JUPUSDT","WIFUSDT","BONKUSDT",
        "PEPEUSDT","FLOKIUSDT","MEMEUSDT","STRKUSDT","ZROUSDT",
        "PENDLEUSDT","METISUSDT","ALTUSDT","ENAUSDT","LISTAUSDT"
    ],

    "hourly_interval": "1h",
    "fourh_interval": "4h",
    "daily_interval": "1d",
    "fifteenm_interval": "15m",

    "hourly_lookback_days": 5,
    "fourh_lookback_days": 15,
    "daily_lookback_days": 180,
    "fifteenm_lookback_days": 2,
    "max_bars": 300,

    "alarm_wma_direction": True,
    "alarm_cross_sma20": True,
    "alarm_cross_sma50": True,
    "alarm_cross_sma100": True,
    "alarm_cross_sma200": True,
    "alarm_sma_direction": False,

    "make_pdf": True,

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None
}

# ======================================================================
# CONFIG LOAD/SAVE + RESET
# ======================================================================

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

# ======================================================================
# TIME HELPERS
# ======================================================================

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

# ======================================================================
# BOT TOKENS + SAFE CREATION
# ======================================================================

TOKEN_1H  = os.getenv("TOKEN_1H")
TOKEN_4H  = os.getenv("TOKEN_4H")
TOKEN_1D  = os.getenv("TOKEN_1D")
TOKEN_15M = os.getenv("TOKEN_15M")

def safe_bot(token):
    if not token or not isinstance(token, str):
        return None
    if any(ch.isspace() for ch in token):
        return None
    if ":" not in token:
        return None
    try:
        return telebot.TeleBot(token, parse_mode="HTML")
    except Exception:
        return None

bot_1h  = safe_bot(TOKEN_1H)
bot_4h  = safe_bot(TOKEN_4H)
bot_1d  = safe_bot(TOKEN_1D)
bot_15m = safe_bot(TOKEN_15M)

# ======================================================================
# MENUS + HELP
# ======================================================================

HELP_TEXT = """مودو بازلر – نسخه زمان‌بندی‌شده

دستورات و امکانات ربات‌ها:

۱) ربات‌ها:
- ربات ۱ساعته: تحلیل دوره‌ای ۱h برای لیست ارزهای تنظیم‌شده.
- ربات ۴ساعته: تحلیل دوره‌ای ۴h.
- ربات روزانه: تحلیل دوره‌ای ۱d.
- ربات ۱۵دقیقه‌ای: تحلیل سریع 15m برای حدود ۵۰ ارز اول.

۲) نمودارها:
- نمودار اصلی: کندل‌استیک + SMA20 + SMA50 + WMA20.
- زیر نمودار: RSI و MACD در دو پنل جداگانه.
- محور عمودی (قیمت): سمت راست مدرج.
- محور افقی (زمان): برچسب‌ها یکی در میان نمایش داده می‌شوند.

۳) اندیکاتورها:
- SMA20: میانگین متحرک ساده ۲۰ کندل.
- SMA50: میانگین متحرک ساده ۵۰ کندل.
- SMA100: میانگین متحرک ساده ۱۰۰ کندل.
- SMA200: میانگین متحرک ساده ۲۰۰ کندل.
- WMA20: میانگین متحرک وزنی ۲۰ کندل با رنگ:
  - سبز: شیب مثبت (صعودی)
  - قرمز: شیب منفی (نزولی)
- RSI: شاخص قدرت نسبی (۱۴ دوره).
- MACD: مکدی کلاسیک (۱۲/۲۶/۹).

۴) آلارم‌ها (قابل تنظیم در کانفیگ):
- تغییر جهت WMA20 (از صعودی به نزولی یا برعکس).
- برخورد WMA20 با SMA20 / SMA50 / SMA100 / SMA200.
- تغییر جهت SMAها (در صورت فعال بودن گزینه alarm_sma_direction).

۵) خروجی‌ها:
- فایل PNG برای هر نمودار.
- فایل PDF تجمیعی (در صورت فعال بودن make_pdf).
- ارسال عکس نمودار + متن آلارم به ربات مربوطه.

۶) دکمه‌ها:
- دکمه شروع/منوی اصلی.
- دکمه اجرای دستی چرخه ۱ساعته.
- دکمه تنظیم/ریست لیست ارزها.
- دکمه آلارم‌ها (در نسخه فعلی آلارم‌ها از کانفیگ خوانده می‌شوند).

۷) زمان اجرا:
- ربات ۱ساعته: هر ساعت در دقیقه ۳۰.
- ربات ۴ساعته: در ساعات ۴:۳۰، ۸:۳۰، ۱۲:۳۰، ۱۶:۳۰، ۲۰:۳۰، ۲۳:۳۰، ۰:۳۰.
- ربات روزانه: هر روز ساعت ۲۳:۳۰.
- ربات ۱۵دقیقه‌ای: هر ۱۵ دقیقه (تقریباً در دقیقه ۰،۱۵،۳۰،۴۵).

برای تغییر تنظیمات، فایل config.json در پوشه data را ویرایش کنید.
"""

def send_main_menu(bot, chat_id):
    if bot is None or chat_id is None:
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔍 چک تک‌ارز", "▶ اجرای دستی ۱ساعته")
    kb.row("⏱ آلارم‌ها", "⚙ تنظیم/ریست ارزها")
    kb.row("ℹ راهنما", "🚀 شروع/منوی اصلی")
    bot.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

# ======================================================================
# START COMMANDS
# ======================================================================

if bot_1h:
    @bot_1h.message_handler(commands=["start"])
    def start_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, HELP_TEXT)
        send_main_menu(bot_1h, m.chat.id)

if bot_4h:
    @bot_4h.message_handler(commands=["start"])
    def start_4h(m):
        cfg = load_config()
        cfg["chat_id_4h"] = m.chat.id
        save_config(cfg)
        bot_4h.send_message(
            m.chat.id,
            f"ربات ۴ساعته فعال شد.\n#زمان‌فعلی: {now_utc_str()} UTC"
        )

if bot_1d:
    @bot_1d.message_handler(commands=["start"])
    def start_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        bot_1d.send_message(
            m.chat.id,
            f"ربات روزانه فعال شد.\n#زمان‌فعلی: {now_utc_str()} UTC"
        )

if bot_15m:
    @bot_15m.message_handler(commands=["start"])
    def start_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        bot_15m.send_message(
            m.chat.id,
            f"ربات ۱۵دقیقه‌ای فعال شد.\n#زمان‌فعلی: {now_utc_str()} UTC"
        )

# ======================================================================
# SYMBOL CHECK (SINGLE CHART)
# ======================================================================

if bot_1h:
    @bot_1h.message_handler(func=lambda m: m.text == "🔍 چک تک‌ارز")
    def ask_symbol(m):
        msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید (مثلاً BTCUSDT):")
        bot_1h.register_next_step_handler(msg, do_symbol)

    def do_symbol(m):
        symbol = m.text.strip().upper()
        cfg = load_config()
        bot_1h.send_message(m.chat.id, f"در حال تهیه نمودار برای {symbol} ...")

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

# ======================================================================
# DATA FETCH (BINANCE + KUCOIN)
# ======================================================================

def _binance_interval(i):
    return {"1h":"1h","4h":"4h","1d":"1d","15m":"15m"}[i]

def _kucoin_interval(i):
    return {"1h":"1hour","4h":"4hour","1d":"1day","15m":"15min"}[i]

def fetch_ohlc(symbol, interval, lookback_days, max_bars):
    limit = max(200, max_bars)

    # Binance
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

    # KuCoin
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

# ======================================================================
# INDICATORS + CHART
# ======================================================================

def compute_indicators(df):
    df = df.copy()
    close = df["c"]

    df["SMA20"]  = close.rolling(20).mean()
    df["SMA50"]  = close.rolling(50).mean()
    df["SMA100"] = close.rolling(100).mean()
    df["SMA200"] = close.rolling(200).mean()

    df["WMA20"] = close.rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x)+1)),
        raw=True
    )
    df["WMA20_slope"] = df["WMA20"].diff()

    # RSI 14
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD (12,26,9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    df["MACD"] = macd
    df["MACD_signal"] = signal
    df["MACD_hist"] = hist

    return df

def create_plotly_chart(symbol, interval, lookback_days, max_bars, png_name, html_name):
    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)
    df.columns = ["o","h","l","c","v"]
    df = compute_indicators(df)

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03
    )

    # Candles
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["o"], high=df["h"], low=df["l"], close=df["c"],
            name="Price"
        ),
        row=1, col=1
    )

    # SMA20, SMA50, WMA20
    fig.add_trace(
        go.Scatter(x=df.index, y=df["SMA20"], mode="lines", name="SMA20", line=dict(color="blue")),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["SMA50"], mode="lines", name="SMA50", line=dict(color="orange")),
        row=1, col=1
    )

    # WMA20 رنگ بر اساس شیب آخر
    last_slope = df["WMA20_slope"].iloc[-1] if not df["WMA20_slope"].isna().all() else 0
    wma_color = "green" if last_slope > 0 else "red"
    fig.add_trace(
        go.Scatter(x=df.index, y=df["WMA20"], mode="lines", name="WMA20", line=dict(color=wma_color, dash="dot")),
        row=1, col=1
    )

    # RSI
    fig.add_trace(
        go.Scatter(x=df.index, y=df["RSI"], mode="lines", name="RSI", line=dict(color="purple")),
        row=2, col=1
    )
    fig.update_yaxes(range=[0,100], row=2, col=1)

    # MACD
    fig.add_trace(
        go.Scatter(x=df.index, y=df["MACD"], mode="lines", name="MACD", line=dict(color="cyan")),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["MACD_signal"], mode="lines", name="Signal", line=dict(color="yellow")),
        row=3, col=1
    )
    fig.add_trace(
        go.Bar(x=df.index, y=df["MACD_hist"], name="Hist", marker_color="gray"),
        row=3, col=1
    )

    # محور عمودی سمت راست
    fig.update_layout(
        yaxis=dict(side="right"),
        xaxis=dict(showgrid=True),
        xaxis2=dict(showgrid=True),
        xaxis3=dict(showgrid=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
        title=f"{symbol} – {interval} – {now_utc_str()} UTC"
    )

    # محور افقی: یکی در میان
    fig.update_xaxes(
        tickmode="auto",
        tickangle=0
    )

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
        "last_close": float(df["c"].iloc[-1]),
        "wma": df["WMA20"].tolist(),
        "wma_slope": df["WMA20_slope"].tolist(),
        "sma20": df["SMA20"].tolist(),
        "sma50": df["SMA50"].tolist(),
        "sma100": df["SMA100"].tolist(),
        "sma200": df["SMA200"].tolist()
    }

# ======================================================================
# ALARMS
# ======================================================================

def detect_alarms(cfg, info):
    alarms = []
    wma = info["wma"]
    slope = info["wma_slope"]
    sma20 = info["sma20"]
    sma50 = info["sma50"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]

    if len(wma) < 3 or len(slope) < 3:
        return alarms

    # جهت WMA
    if cfg.get("alarm_wma_direction", True):
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("تغییر جهت WMA20 به صعودی")
        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("تغییر جهت WMA20 به نزولی")

    def cross(a, b):
        if len(a) < 2 or len(b) < 2:
            return False
        return (a[-2] - b[-2]) * (a[-1] - b[-1]) < 0

    if cfg.get("alarm_cross_sma20", True) and cross(wma, sma20):
        alarms.append("برخورد WMA20 با SMA20")

    if cfg.get("alarm_cross_sma50", True) and cross(wma, sma50):
        alarms.append("برخورد WMA20 با SMA50")

    if cfg.get("alarm_cross_sma100", True) and cross(wma, sma100):
        alarms.append("برخورد WMA20 با SMA100")

    if cfg.get("alarm_cross_sma200", True) and cross(wma, sma200):
        alarms.append("برخورد WMA20 با SMA200")

    if cfg.get("alarm_sma_direction", False):
        for name, arr in [("SMA20", sma20), ("SMA50", sma50), ("SMA100", sma100), ("SMA200", sma200)]:
            if len(arr) >= 3:
                d1 = arr[-1] - arr[-2]
                d2 = arr[-2] - arr[-3]
                if d2 < 0 and d1 > 0:
                    alarms.append(f"تغییر جهت {name} به صعودی")
                if d2 > 0 and d1 < 0:
                    alarms.append(f"تغییر جهت {name} به نزولی")

    return alarms

# ======================================================================
# CYCLE ENGINE
# ======================================================================

def run_cycle(group, bot, chat_id, symbols, interval, lookback_days, max_bars):
    if bot is None or chat_id is None:
        return

    bot.send_message(chat_id, f"شروع چرخه {group}\n#زمان: {now_utc_str()} UTC")

    cfg = load_config()

    pdf_path = os.path.join(PDF_DIR, f"{group}_{now_utc().strftime('%Y%m%d_%H%M%S')}.pdf")
    pdf = PdfPages(pdf_path) if cfg.get("make_pdf", True) else None

    for sym in symbols:
        bot.send_message(chat_id, f"در حال پردازش: {sym}")

        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"{group}_{sym}_{ts}.png"
        html = f"{group}_{sym}_{ts}.html"

        info = create_plotly_chart(sym, interval, lookback_days, max_bars, png, html)
        alarms = detect_alarms(cfg, info)

        caption = f"{sym} – {group}\nزمان: {info['created_at']} UTC"
        if alarms:
            caption += "\nآلارم‌ها:\n" + "\n".join(f"- {a}" for a in alarms)

        with open(info["png_path"], "rb") as f:
            bot.send_photo(chat_id, f, caption=caption)

        if pdf is not None:
            img = plt.imread(info["png_path"])
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.imshow(img)
            ax.axis("off")
            pdf.savefig(fig)
            plt.close(fig)

    if pdf is not None:
        pdf.close()
        with open(pdf_path, "rb") as f:
            bot.send_document(chat_id, f, caption=f"گزارش PDF چرخه {group}")

    bot.send_message(chat_id, f"پایان چرخه {group}")

# ======================================================================
# FIXED-TIME SCHEDULER
# ======================================================================

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
        cfg = load_config()
        if bot_1d and cfg.get("chat_id_1d"):
            run_cycle(
                "1d", bot_1d, cfg["chat_id_1d"],
                cfg["daily_symbols"], "1d",
                cfg["daily_lookback_days"], cfg["max_bars"]
            )
        time.sleep(60)

def loop_4h():
    times = [(4,30),(8,30),(12,30),(16,30),(20,30),(23,30),(0,30)]
    while True:
        now = dt.datetime.now()
        cfg = load_config()
        for h,m in times:
            if now.hour == h and now.minute == m:
                if bot_4h and cfg.get("chat_id_4h"):
                    run_cycle(
                        "4h", bot_4h, cfg["chat_id_4h"],
                        cfg["fourh_symbols"], "4h",
                        cfg["fourh_lookback_days"], cfg["max_bars"]
                    )
                time.sleep(60)
        time.sleep(20)

def loop_1h():
    while True:
        now = dt.datetime.now()
        cfg = load_config()
        if now.minute == 30:
            if bot_1h and cfg.get("chat_id_1h"):
                run_cycle(
                    "1h", bot_1h, cfg["chat_id_1h"],
                    cfg["hourly_symbols"], "1h",
                    cfg["hourly_lookback_days"], cfg["max_bars"]
                )
            time.sleep(60)
        time.sleep(20)

def loop_15m():
    while True:
        now = dt.datetime.now()
        cfg = load_config()
        if now.minute % 15 == 0:
            if bot_15m and cfg.get("chat_id_15m"):
                run_cycle(
                    "15m", bot_15m, cfg["chat_id_15m"],
                    cfg["fifteenm_symbols"], "15m",
                    cfg["fifteenm_lookback_days"], cfg["max_bars"]
                )
            time.sleep(60)
        time.sleep(20)

# ======================================================================
# START / STOP / MANUAL / HELP / ALARM BUTTONS (۱ساعته)
# ======================================================================

if bot_1h:
    @bot_1h.message_handler(func=lambda m: m.text == "⚙ تنظیم/ریست ارزها")
    def reset_symbols(m):
        cfg = load_config()
        cfg["hourly_symbols"]  = DEFAULT_CONFIG["hourly_symbols"]
        cfg["fourh_symbols"]   = DEFAULT_CONFIG["fourh_symbols"]
        cfg["daily_symbols"]   = DEFAULT_CONFIG["daily_symbols"]
        cfg["fifteenm_symbols"] = DEFAULT_CONFIG["fifteenm_symbols"]
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "لیست ارزها به حالت پیش‌فرض بازنشانی شد.")

    @bot_1h.message_handler(func=lambda m: m.text == "▶ اجرای دستی ۱ساعته")
    def manual_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        run_cycle(
            "1h", bot_1h, m.chat.id,
            cfg["hourly_symbols"], "1h",
            cfg["hourly_lookback_days"], cfg["max_bars"]
        )

    @bot_1h.message_handler(func=lambda m: m.text == "ℹ راهنما")
    def show_help(m):
        bot_1h.send_message(m.chat.id, HELP_TEXT)

    @bot_1h.message_handler(func=lambda m: m.text == "🚀 شروع/منوی اصلی")
    def show_menu(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        send_main_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(func=lambda m: m.text == "⏱ آلارم‌ها")
    def alarms_info(m):
        cfg = load_config()
        txt = "تنظیمات آلارم فعلی:\n"
        txt += f"- تغییر جهت WMA20: {'فعال' if cfg.get('alarm_wma_direction', True) else 'غیرفعال'}\n"
        txt += f"- برخورد WMA20 با SMA20: {'فعال' if cfg.get('alarm_cross_sma20', True) else 'غیرفعال'}\n"
        txt += f"- برخورد WMA20 با SMA50: {'فعال' if cfg.get('alarm_cross_sma50', True) else 'غیرفعال'}\n"
        txt += f"- برخورد WMA20 با SMA100: {'فعال' if cfg.get('alarm_cross_sma100', True) else 'غیرفعال'}\n"
        txt += f"- برخورد WMA20 با SMA200: {'فعال' if cfg.get('alarm_cross_sma200', True) else 'غیرفعال'}\n"
        txt += f"- تغییر جهت SMAها: {'فعال' if cfg.get('alarm_sma_direction', False) else 'غیرفعال'}\n"
        txt += "\nبرای تغییر این مقادیر، فایل config.json را ویرایش کنید."
        bot_1h.send_message(m.chat.id, txt)

# ======================================================================
# THREADS
# ======================================================================

def start_threads():
    t1 = threading.Thread(target=loop_1h,    daemon=True)
    t2 = threading.Thread(target=loop_4h,    daemon=True)
    t3 = threading.Thread(target=loop_daily, daemon=True)
    t4 = threading.Thread(target=loop_15m,   daemon=True)

    t1.start()
    t2.start()
    t3.start()
    t4.start()

# ======================================================================
# MAIN
# ======================================================================

if __name__ == "__main__":
    # شروع برنامه: ارسال پیام به هر رباتی که توکن معتبر دارد
    cfg = load_config()
    if bot_1h and cfg.get("chat_id_1h"):
        bot_1h.send_message(cfg["chat_id_1h"], f"برنامه اصلی مودو بازلر اجرا شد.\n#زمان: {now_utc_str()} UTC")
        send_main_menu(bot_1h, cfg["chat_id_1h"])
    if bot_4h and cfg.get("chat_id_4h"):
        bot_4h.send_message(cfg["chat_id_4h"], f"برنامه اصلی مودو بازلر اجرا شد (۴ساعته).\n#زمان: {now_utc_str()} UTC")
    if bot_1d and cfg.get("chat_id_1d"):
        bot_1d.send_message(cfg["chat_id_1d"], f"برنامه اصلی مودو بازلر اجرا شد (روزانه).\n#زمان: {now_utc_str()} UTC")
    if bot_15m and cfg.get("chat_id_15m"):
        bot_15m.send_message(cfg["chat_id_15m"], f"برنامه اصلی مودو بازلر اجرا شد (۱۵دقیقه‌ای).\n#زمان: {now_utc_str()} UTC")

    start_threads()

    # polling برای هر رباتی که ساخته شده
    if bot_1h:
        threading.Thread(target=bot_1h.infinity_polling, daemon=True).start()
    if bot_4h:
        threading.Thread(target=bot_4h.infinity_polling, daemon=True).start()
    if bot_1d:
        threading.Thread(target=bot_1d.infinity_polling, daemon=True).start()
    if bot_15m:
        threading.Thread(target=bot_15m.infinity_polling, daemon=True).start()

    # نگه داشتن برنامه
    while True:
        time.sleep(60)