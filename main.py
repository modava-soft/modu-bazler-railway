# -*- coding: utf-8 -*-
# Modu Bazler – Scheduled Edition (Fixed-Time Cycles + 15m Bot + Advanced Alarms)

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

    # 15m bot – first 50 coins (you can adjust)
    "fifteenm_symbols": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT",
        "UNIUSDT","ICPUSDT","ARBUSDT","OPUSDT","SUIUSDT",
        "PEPEUSDT","TONUSDT","SEIUSDT","INJUSDT","RUNEUSDT",
        "FTMUSDT","GALAUSDT","AAVEUSDT","SNXUSDT","NEOUSDT",
        "EGLDUSDT","KASUSDT","XECUSDT","STXUSDT","WIFUSDT",
        "JUPUSDT","PYTHUSDT","TIAUSDT","BLURUSDT","LDOUSDT",
        "RLBUSDT","COMPUSDT","ZECUSDT","CRVUSDT","SANDUSDT"
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

    # Alarm switches
    "alarm_wma_direction": True,
    "alarm_sma20_direction": False,
    "alarm_sma100_direction": False,
    "alarm_sma200_direction": False,
    "alarm_cross_sma20": True,
    "alarm_cross_sma100": True,
    "alarm_cross_sma200": True,
    "alarm_cross_sma_wma": True,

    "make_pdf": True,

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None
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

TOKEN_1H   = (os.getenv("TOKEN_1H") or "").strip()
TOKEN_4H   = (os.getenv("TOKEN_4H") or "").strip()
TOKEN_1D   = (os.getenv("TOKEN_1D") or "").strip()
TOKEN_15M  = (os.getenv("TOKEN_15M") or "").strip()
ADMIN_CHAT = (os.getenv("ADMIN_CHAT_ID") or "").strip()

bot_1h  = telebot.TeleBot(TOKEN_1H, parse_mode="HTML") if TOKEN_1H else None = telebot.TeleBot(TOKEN_1H, parse_mode="HTML") if TOKEN_1H else None
bot_4h  = telebot.TeleBot(TOKEN_4H, parse_mode="HTML") if TOKEN_4H else None
bot_1d  = telebot.TeleBot(TOKEN_1D, parse_mode="HTML") if TOKEN_1D else None
bot_15m = telebot.TeleBot(TOKEN_15M, parse_mode="HTML") if TOKEN_15M else None

# =========================================================
# MENUS / HELP
# =========================================================

HELP_TEXT = """
Modu Bazler – نسخه زمان‌بندی‌شده

دستورات و امکانات:

1) /start
   - ثبت چت فعلی برای ربات مربوطه (1h / 4h / 1d / 15m).
   - نمایش منوی اصلی.

2) منوی اصلی (ربات 1h):
   - «چک یک نماد»: دریافت نماد دلخواه (مثلاً BTCUSDT) و ارسال نمودار کامل با SMA20/50/100/200، WMA20، RSI و آلارم‌ها.
   - «اجرای دستی 1h»: اجرای یک چرخه کامل برای همه نمادهای 1h.
   - «شروع زمان‌بندی‌ها»: فعال‌سازی چرخه‌های خودکار (در این نسخه فقط پیام اطلاع‌رسانی).
   - «توقف زمان‌بندی‌ها»: توقف چرخه‌های خودکار (در این نسخه فقط پیام اطلاع‌رسانی).
   - «بازنشانی نمادها»: برگرداندن لیست نمادها به حالت پیش‌فرض.

3) آلارم‌ها:
   - تغییر جهت WMA20 (صعودی/نزولی).
   - تغییر جهت SMA20 / SMA100 / SMA200 (در صورت فعال بودن در تنظیمات).
   - برخورد WMA20 با SMA20 / SMA100 / SMA200.
   - برخورد SMAها با WMA (در صورت فعال بودن).
   - آلارم‌ها برای هر ربات (1h / 4h / 1d / 15m) جداگانه محاسبه و در صورت وقوع، همراه با عکس نمودار ارسال می‌شوند.

4) نمودارها:
   - کندل‌استیک کامل.
   - SMA20، SMA100، SMA200.
   - WMA20 با رنگ سبز در حالت صعودی و قرمز در حالت نزولی (بر اساس شیب آخر).
   - RSI (14 دوره) در پنل جداگانه.
   - خروجی PNG و HTML برای هر نماد.
   - در صورت فعال بودن make_pdf، امکان ساخت PDF از مجموعه نمودارها (در این نسخه فقط ساخت فایل، بدون ارسال).

5) ربات 15 دقیقه:
   - توکن جداگانه (TOKEN_15M).
   - محاسبه برای حدود 50 نماد اول (قابل تغییر در تنظیمات).
   - تمام آلارم‌ها و نمودارها مشابه سایر ربات‌ها.

6) تنظیمات:
   - فایل config.json در پوشه data.
   - قابل ویرایش برای:
     * لیست نمادها برای هر بازه (hourly/fourh/daily/fifteenm).
     * تعداد روزهای نگاه‌به‌عقب.
     * max_bars.
     * فعال/غیرفعال کردن انواع آلارم‌ها.

7) نکات:
   - برای کارکرد کامل ربات‌ها، حتماً توکن‌ها و ADMIN_CHAT_ID را در متغیرهای محیطی تنظیم کنید.
   - پس از اجرای برنامه، به هر چهار ربات یک پیام «ربات راه‌اندازی شد» به ADMIN_CHAT_ID ارسال می‌شود (در صورت تنظیم).
"""

def send_main_menu(chat_id):
    if not bot_1h:
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("چک یک نماد", "اجرای دستی 1h")
    kb.row("شروع زمان‌بندی‌ها", "توقف زمان‌بندی‌ها")
    kb.row("بازنشانی نمادها", "راهنما")
    bot_1h.send_message(chat_id, "لطفاً گزینه مورد نظر را انتخاب کنید:", reply_markup=kb)

# =========================================================
# START COMMANDS
# =========================================================

if bot_1h:
    @bot_1h.message_handler(commands=["start"])
    def start_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, HELP_TEXT)
        send_main_menu(m.chat.id)

if bot_4h:
    @bot_4h.message_handler(commands=["start"])
    def start_4h(m):
        cfg = load_config()
        cfg["chat_id_4h"] = m.chat.id
        save_config(cfg)
        bot_4h.send_message(
            m.chat.id,
            f"ربات 4h فعال شد.\nزمان فعلی:\n# {now_utc_str()} UTC"
        )

if bot_1d:
    @bot_1d.message_handler(commands=["start"])
    def start_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        bot_1d.send_message(
            m.chat.id,
            f"ربات 1d فعال شد.\nزمان فعلی:\n# {now_utc_str()} UTC"
        )

if bot_15m:
    @bot_15m.message_handler(commands=["start"])
    def start_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        bot_15m.send_message(
            m.chat.id,
            f"ربات 15m فعال شد.\nزمان فعلی:\n# {now_utc_str()} UTC"
        )

# =========================================================
# SYMBOL CHECK (1h bot – single symbol)
# =========================================================

if bot_1h:
    @bot_1h.message_handler(func=lambda m: m.text == "چک یک نماد")
    def ask_symbol(m):
        msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید (مثلاً BTCUSDT):")
        bot_1h.register_next_step_handler(msg, do_symbol)

    def do_symbol(m):
        symbol = m.text.strip().upper()
        cfg = load_config()
        bot_1h.send_message(m.chat.id, f"در حال ساخت نمودار برای {symbol} ...")

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

# =========================================================
# DATA FETCH (BINANCE + KUCOIN)
# =========================================================

def _binance_interval(i):
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i):
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

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
        start = end - 60*60*(limit+10)
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
# INDICATORS + CHART
# =========================================================

def compute_indicators(df):
    df = df.copy()
    df["SMA20"]  = df["c"].rolling(20).mean()
    df["SMA50"]  = df["c"].rolling(50).mean()
    df["SMA100"] = df["c"].rolling(100).mean()
    df["SMA200"] = df["c"].rolling(200).mean()

    df["WMA20"] = df["c"].rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x)+1)),
        raw=True
    )
    df["WMA20_slope"] = df["WMA20"].diff()

    # RSI 14
    delta = df["c"].diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_gain = pd.Series(gain, index=df.index).rolling(14).mean()
    roll_loss = pd.Series(loss, index=df.index).rolling(14).mean()
    rs = roll_gain / (roll_loss + 1e-9)
    df["RSI14"] = 100 - (100 / (1 + rs))

    return df

def create_plotly_chart(symbol, interval, lookback_days, max_bars, png_name, html_name):
    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)
    if df.empty:
        # ایجاد یک دیتافریم خالی برای جلوگیری از کرش
        df = pd.DataFrame(columns=["o","h","l","c","v"])
        df.index = pd.to_datetime([])

    df.columns = ["o","h","l","c","v"]
    df = compute_indicators(df)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["o"], high=df["h"], low=df["l"], close=df["c"],
            name="Price"
        ),
        row=1, col=1
    )

    # SMAs
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"],  mode="lines", name="SMA20"),  row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"],  mode="lines", name="SMA50"),  row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA100"], mode="lines", name="SMA100"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], mode="lines", name="SMA200"), row=1, col=1)

    # WMA20 – رنگ بر اساس شیب آخر
    last_slope = df["WMA20_slope"].iloc[-1] if len(df["WMA20_slope"]) > 0 else 0
    wma_color = "green" if last_slope > 0 else "red"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["WMA20"],
            mode="lines",
            name="WMA20",
            line=dict(color=wma_color, dash="dot")
        ),
        row=1, col=1
    )

    # RSI
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["RSI14"],
            mode="lines",
            name="RSI14"
        ),
        row=2, col=1
    )
    fig.update_yaxes(title_text="RSI", row=2, col=1)

    fig.update_layout(
        title=f"{symbol} – {interval}",
        xaxis_rangeslider_visible=False,
        template="plotly_dark"
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
        "last_close": float(df["c"].iloc[-1]) if len(df["c"]) else None,
        "wma": df["WMA20"].tolist() if "WMA20" in df.columns else [],
        "wma_slope": df["WMA20_slope"].tolist() if "WMA20_slope" in df.columns else [],
        "sma20": df["SMA20"].tolist() if "SMA20" in df.columns else [],
        "sma50": df["SMA50"].tolist() if "SMA50" in df.columns else [],
        "sma100": df["SMA100"].tolist() if "SMA100" in df.columns else [],
        "sma200": df["SMA200"].tolist() if "SMA200" in df.columns else []
    }

# =========================================================
# ALARMS
# =========================================================

def detect_alarms(cfg, info):
    alarms = []
    wma   = info["wma"]
    slope = info["wma_slope"]
    sma20  = info["sma20"]
    sma50  = info["sma50"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]

    if len(wma) < 2:
        return alarms

    def dir_change(series):
        if len(series) < 2:
            return None
        prev = series[-2]
        curr = series[-1]
        if prev < curr:
            return "up"
        elif prev > curr:
            return "down"
        return None

    def cross(a, b):
        if len(a) < 2 or len(b) < 2:
            return False
        return (a[-2] - b[-2]) * (a[-1] - b[-1]) < 0

    # WMA direction
    if cfg.get("alarm_wma_direction", False) and len(slope) >= 2:
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("WMA20 جهت صعودی شد")
        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("WMA20 جهت نزولی شد")

    # SMA directions
    if cfg.get("alarm_sma20_direction", False) and len(sma20) >= 2:
        d = dir_change(sma20)
        if d == "up":
            alarms.append("SMA20 جهت صعودی شد")
        elif d == "down":
            alarms.append("SMA20 جهت نزولی شد")

    if cfg.get("alarm_sma100_direction", False) and len(sma100) >= 2:
        d = dir_change(sma100)
        if d == "up":
            alarms.append("SMA100 جهت صعودی شد")
        elif d == "down":
            alarms.append("SMA100 جهت نزولی شد")

    if cfg.get("alarm_sma200_direction", False) and len(sma200) >= 2:
        d = dir_change(sma200)
        if d == "up":
            alarms.append("SMA200 جهت صعودی شد")
        elif d == "down":
            alarms.append("SMA200 جهت نزولی شد")

    # Cross WMA with SMAs
    if cfg.get("alarm_cross_sma20", False) and len(sma20) >= 2 and cross(wma, sma20):
        alarms.append("WMA20 با SMA20 برخورد کرد")

    if cfg.get("alarm_cross_sma100", False) and len(sma100) >= 2 and cross(wma, sma100):
        alarms.append("WMA20 با SMA100 برخورد کرد")

    if cfg.get("alarm_cross_sma200", False) and len(sma200) >= 2 and cross(wma, sma200):
        alarms.append("WMA20 با SMA200 برخورد کرد")

    # SMA-WMA cross (generic)
    if cfg.get("alarm_cross_sma_wma", False):
        if len(sma50) >= 2 and cross(sma50, wma):
            alarms.append("SMA50 با WMA20 برخورد کرد")

    return alarms

# =========================================================
# CYCLE ENGINE
# =========================================================

def run_cycle(group, bot, chat_id, symbols, interval, lookback_days, max_bars):
    if not bot or not chat_id:
        return

    bot.send_message(chat_id, f"شروع چرخه {group}\n# {now_utc_str()} UTC")

    cfg = load_config()

    for sym in symbols:
        bot.send_message(chat_id, f"در حال پردازش: {sym}")

        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"{group}_{sym}_{ts}.png"
        html = f"{group}_{sym}_{ts}.html"

        info = create_plotly_chart(sym, interval, lookback_days, max_bars, png, html)
        alarms = detect_alarms(cfg, info)

        if alarms:
            caption = f"آلارم برای {sym} ({group})\n" + "\n".join(alarms)
            with open(info["png_path"], "rb") as f:
                bot.send_photo(chat_id, f, caption=caption)

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
        if cfg.get("chat_id_1d"):
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
                if cfg.get("chat_id_4h"):
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
            if cfg.get("chat_id_1h"):
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

def loop_15m():
    # هر 15 دقیقه در دقیقه 0،15،30،45
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute in [0,15,30,45]:
            if cfg.get("chat_id_15m"):
                run_cycle(
                    "15m",
                    bot_15m,
                    cfg["chat_id_15m"],
                    cfg["fifteenm_symbols"],
                    "15m",
                    cfg["fifteenm_lookback_days"],
                    cfg["max_bars"]
                )
            time.sleep(60)
        time.sleep(20)

# =========================================================
# START / STOP / MANUAL (1h bot)
# =========================================================

if bot_1h:
    @bot_1h.message_handler(func=lambda m: m.text == "توقف زمان‌بندی‌ها")
    def stop_all(m):
        bot_1h.send_message(
            m.chat.id,
            "در این نسخه، زمان‌بندی‌ها به‌صورت دستی کنترل می‌شوند.\n(پیام اطلاع‌رسانی توقف زمان‌بندی‌ها)"
        )

    @bot_1h.message_handler(func=lambda m: m.text == "شروع زمان‌بندی‌ها")
    def start_all(m):
        bot_1h.send_message(
            m.chat.id,
            "در این نسخه، زمان‌بندی‌ها به‌صورت خودکار در پس‌زمینه اجرا می‌شوند.\n(پیام اطلاع‌رسانی شروع زمان‌بندی‌ها)"
        )

    @bot_1h.message_handler(func=lambda m: m.text == "اجرای دستی 1h")
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

    @bot_1h.message_handler(func=lambda m: m.text == "بازنشانی نمادها")
    def reset_symbols(m):
        cfg = load_config()
        cfg["hourly_symbols"]  = DEFAULT_CONFIG["hourly_symbols"]
        cfg["fourh_symbols"]   = DEFAULT_CONFIG["fourh_symbols"]
        cfg["daily_symbols"]   = DEFAULT_CONFIG["daily_symbols"]
        cfg["fifteenm_symbols"] = DEFAULT_CONFIG["fifteenm_symbols"]
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "لیست نمادها به حالت پیش‌فرض بازنشانی شد.")

    @bot_1h.message_handler(func=lambda m: m.text == "راهنما")
    def show_help(m):
        bot_1h.send_message(m.chat.id, HELP_TEXT)

# =========================================================
# THREADS
# =========================================================

def start_threads():
    if bot_1h:
        t1 = threading.Thread(target=loop_1h, daemon=True)
        t1.start()
    if bot_4h:
        t2 = threading.Thread(target=loop_4h, daemon=True)
        t2.start()
    if bot_1d:
        t3 = threading.Thread(target=loop_daily, daemon=True)
        t3.start()
    if bot_15m:
        t4 = threading.Thread(target=loop_15m, daemon=True)
        t4.start()

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    # پیام شروع به چهار ربات (در صورت وجود ADMIN_CHAT_ID)
    if ADMIN_CHAT:
        if bot_1h:
            bot_1h.send_message(ADMIN_CHAT, "ربات 1h راه‌اندازی شد.")
        if bot_4h:
            bot_4h.send_message(ADMIN_CHAT, "ربات 4h راه‌اندازی شد.")
        if bot_1d:
            bot_1d.send_message(ADMIN_CHAT, "ربات 1d راه‌اندازی شد.")
        if bot_15m:
            bot_15m.send_message(ADMIN_CHAT, "ربات 15m راه‌اندازی شد.")

    start_threads()

    # infinity_polling فقط برای ربات‌هایی که توکن دارند
    threads = []
    if bot_1h:
        threads.append(threading.Thread(target=bot_1h.infinity_polling, daemon=True))
    if bot_4h:
        threads.append(threading.Thread(target=bot_4h.infinity_polling, daemon=True))
    if bot_1d:
        threads.append(threading.Thread(target=bot_1d.infinity_polling, daemon=True))
    if bot_15m:
        threads.append(threading.Thread(target=bot_15m.infinity_polling, daemon=True))

    for t in threads:
        t.start()

    # نگه داشتن برنامه
    while True:
        time.sleep(10)