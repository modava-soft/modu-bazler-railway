# -*- coding: utf-8 -*-
# Modu Bazler – main.py (نسخهٔ بازنویسی‌شده با واچ‌لیست چندرباته و منوی پیشرفته)

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

    "alarm_wma_direction": True,
    "alarm_cross_sma20": False,
    "alarm_cross_sma100": False,
    "alarm_cross_sma200": False,
    "alarm_sma20_direction": False,
    "alarm_sma100_direction": False,
    "alarm_sma200_direction": False,

    "make_pdf": False,

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,

    # واچ‌لیست‌های جدا برای هر ربات
    "watchlist_1h": [],
    "watchlist_4h": [],
    "watchlist_1d": [],
    "watchlist_15m": [],

    # تنظیمات پیام پیشرفت سیکل
    "cycle_progress_step": 5
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

bot_1h  = create_bot(TOKEN_1H)
bot_4h  = create_bot(TOKEN_4H)
bot_1d  = create_bot(TOKEN_1D)
bot_15m = create_bot(TOKEN_15M)

# برای ارسال آلارم واچ‌لیست به ربات دیگر
BOT_MAP = {
    "1h":  {"bot": lambda: bot_1h,  "chat_key": "chat_id_1h"},
    "4h":  {"bot": lambda: bot_4h,  "chat_key": "chat_id_4h"},
    "1d":  {"bot": lambda: bot_1d,  "chat_key": "chat_id_1d"},
    "15m": {"bot": lambda: bot_15m, "chat_key": "chat_id_15m"},
}

# مثال ساده برای مقصد آلارم واچ‌لیست (می‌توانی بعداً تغییرش بدهی)
WATCH_FORWARD_TARGET = {
    "1h":  "4h",
    "4h":  "1d",
    "1d":  "15m",
    "15m": "1h"
}

# =========================
# منو، راهنما، هندلرهای start
# =========================

HELP_TEXT = """
Modu Bazler – نسخه جدید با سیستم آلارم پیشرفته و واچ‌لیست چندرباته

دستورات:
/start – ثبت چت و نمایش منو
/refresh – رفرش منو
/reset – ریست تنظیمات و منو
/start_cycle_1h – شروع چرخه ۱ساعته
/start_cycle_4h – شروع چرخه ۴ساعته
/start_cycle_1d – شروع چرخه روزانه
/start_cycle_15m – شروع چرخه ۱۵دقیقه‌ای

منو:
- چک نماد پیشرفته
- اجرای فوری 1h
- اجرای سیکل 1h
- مدیریت واچ‌لیست 1h
- ریست واچ‌لیست
- بازنشانی نمادها
- راهنما
- رفرش منو
- شروع چرخه‌ها
- وضعیت سیستم
- گزارش آلارم‌ها
- ریست برنامه
"""

def send_main_menu(bot, chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("چک نماد پیشرفته", "اجرای فوری 1h")
    kb.row("اجرای سیکل 1h", "مدیریت واچ‌لیست 1h")
    kb.row("ریست واچ‌لیست", "بازنشانی نمادها")
    kb.row("راهنما", "رفرش منو")
    kb.row("شروع چرخه‌ها", "وضعیت سیستم")
    kb.row("گزارش آلارم‌ها", "ریست برنامه")
    bot.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

def refresh_menu(bot, chat_id):
    send_main_menu(bot, chat_id)

# =========================
# هندلرهای /start و /reset
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

    @bot_1h.message_handler(commands=["reset"])
    def reset_1h(m):
        cfg = reset_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "تنظیمات برنامه ریست شد و منو رفرش شد.")
        refresh_menu(bot_1h, m.chat.id)

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
# هندلرهای منوی ربات 1h (پیشرفته)
# =========================

if bot_1h:

    # چک نماد پیشرفته: می‌پرسد نماد و تایم‌فریم و نوع بررسی
    @bot_1h.message_handler(func=lambda m: m.text == "چک نماد پیشرفته")
    def advanced_check_symbol(m):
        msg = bot_1h.send_message(
            m.chat.id,
            "نماد مورد نظر را وارد کنید (مثلاً BTCUSDT):"
        )
        bot_1h.register_next_step_handler(msg, advanced_check_symbol_step_symbol)

    def advanced_check_symbol_step_symbol(m):
        symbol = m.text.strip().upper()
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("1h", "4h", "1d", "15m")
        msg = bot_1h.send_message(
            m.chat.id,
            f"تایم‌فریم برای {symbol} را انتخاب کنید:",
            reply_markup=kb
        )
        bot_1h.register_next_step_handler(msg, advanced_check_symbol_step_interval, symbol)

    def advanced_check_symbol_step_interval(m, symbol):
        interval = m.text.strip()
        if interval not in ["1h","4h","1d","15m"]:
            bot_1h.send_message(m.chat.id, "تایم‌فریم نامعتبر است.")
            return

        cfg = load_config()
        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"manual_{symbol}_{interval}_{ts}.png"
        html = f"manual_{symbol}_{interval}_{ts}.html"

        info = create_plotly_chart(
            symbol,
            interval,
            cfg.get("hourly_lookback_days", 5),
            cfg.get("max_bars", 300),
            png,
            html
        )
        alarms = detect_alarms(cfg, info)

        caption = f"{symbol} ({interval})\n"
        if alarms:
            caption += "\n".join(alarms)
        else:
            caption += "در این بررسی آلارمی فعال نشد."

        with open(info["png_path"], "rb") as f:
            bot_1h.send_photo(m.chat.id, f, caption=caption)

    # اجرای فوری 1h: فقط یک بار سیکل 1h را اجرا می‌کند
    @bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 1h")
    def manual_1h(m):
        cfg = load_config()
        run_cycle(
            group="1h",
            bot=bot_1h,
            chat_id=cfg["chat_id_1h"],
            symbols=cfg["hourly_symbols"],
            interval="1h",
            lookback_days=cfg["hourly_lookback_days"],
            max_bars=cfg["max_bars"],
            is_watchlist=False
        )

    # اجرای سیکل 1h (همان لوپ زمان‌بندی، ولی دستی)
    @bot_1h.message_handler(func=lambda m: m.text == "اجرای سیکل 1h")
    def manual_cycle_1h(m):
        cfg = load_config()
        run_cycle(
            group="1h",
            bot=bot_1h,
            chat_id=cfg["chat_id_1h"],
            symbols=cfg["hourly_symbols"],
            interval="1h",
            lookback_days=cfg["hourly_lookback_days"],
            max_bars=cfg["max_bars"],
            is_watchlist=False
        )

    # مدیریت واچ‌لیست 1h: اضافه/حذف نماد
    @bot_1h.message_handler(func=lambda m: m.text == "مدیریت واچ‌لیست 1h")
    def manage_watchlist_1h(m):
        cfg = load_config()
        wl = cfg.get("watchlist_1h", [])
        txt = "واچ‌لیست 1h فعلی:\n"
        if wl:
            txt += "\n".join(wl)
        else:
            txt += "خالی است."
        txt += "\n\nنماد جدید برای اضافه کردن یا حذف کردن وارد کنید (مثلاً BTCUSDT)."
        msg = bot_1h.send_message(m.chat.id, txt)
        bot_1h.register_next_step_handler(msg, manage_watchlist_1h_step)

    def manage_watchlist_1h_step(m):
        symbol = m.text.strip().upper()
        cfg = load_config()
        wl = cfg.get("watchlist_1h", [])
        if symbol in wl:
            wl.remove(symbol)
            bot_1h.send_message(m.chat.id, f"{symbol} از واچ‌لیست 1h حذف شد.")
        else:
            wl.append(symbol)
            bot_1h.send_message(m.chat.id, f"{symbol} به واچ‌لیست 1h اضافه شد.")
        cfg["watchlist_1h"] = wl
        save_config(cfg)

    # ریست واچ‌لیست
    @bot_1h.message_handler(func=lambda m: m.text == "ریست واچ‌لیست")
    def reset_watchlist_1h(m):
        cfg = load_config()
        cfg["watchlist_1h"] = []
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "واچ‌لیست 1h پاک شد.")

    # بازنشانی نمادها
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

    # شروع چرخه‌ها (اطلاع)
    @bot_1h.message_handler(func=lambda m: m.text == "شروع چرخه‌ها")
    def start_cycles(m):
        bot_1h.send_message(m.chat.id, "چرخه‌ها به‌صورت خودکار طبق زمان‌بندی اجرا می‌شوند.")

    # وضعیت سیستم
    @bot_1h.message_handler(func=lambda m: m.text == "وضعیت سیستم")
    def system_status(m):
        bot_1h.send_message(m.chat.id, "سیستم فعال است.\n" + now_utc_str())

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
            txt += "\n"

        bot_1h.send_message(m.chat.id, txt)

    # ریست برنامه از منو
    @bot_1h.message_handler(func=lambda m: m.text == "ریست برنامه")
    def reset_program_btn(m):
        cfg = reset_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "برنامه ریست شد و تنظیمات به حالت اولیه برگشت.")
        refresh_menu(bot_1h, m.chat.id)

# =========================
# دریافت دیتا، اندیکاتورها، نمودارها
# =========================

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str) -> str:
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

def fetch_ohlc(symbol: str, interval: str, lookback_days: int, max_bars: int) -> pd.DataFrame:
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
                int(k[0]), float(k[1]), float(k[2]),
                float(k[3]), float(k[4]), float(k[5])
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
    html_name: str
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

    # Price
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

    # SMA
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"],  mode="lines", name="SMA20",  line=dict(color="blue")),   row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA100"], mode="lines", name="SMA100", line=dict(color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], mode="lines", name="SMA200", line=dict(color="purple")), row=1, col=1)

    # WMA20 با رنگ شیب
    wma   = df["WMA20"]
    slope = df["WMA20_slope"]
    wma_up   = wma.where(slope >= 0)
    wma_down = wma.where(slope < 0)

    fig.add_trace(go.Scatter(x=df.index, y=wma_up,   mode="lines", name="WMA20 Up",   line=dict(color="green", width=2, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=wma_down, mode="lines", name="WMA20 Down", line=dict(color="red",   width=2, dash="dot")), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], mode="lines", name="RSI14", line=dict(color="brown")), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="red", dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="green", dash="dash"), row=2, col=1)

    # MACD
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

LAST_ALARMS = []

def detect_alarms(cfg: dict, info: dict) -> list:
    alarms = []

    wma    = info["wma"]
    slope  = info["wma_slope"]
    sma20  = info["sma20"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]

    if len(wma) < 3 or len(slope) < 3:
        return alarms

    # آلارم تغییر جهت WMA20
    if cfg.get("alarm_wma_direction", True):
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("WMA20 جهت رو به بالا گرفت")
        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("WMA20 جهت رو به پایین گرفت")

    # برخورد WMA با SMAها
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

    # تغییر جهت SMAها
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
# چرخه‌ها با پیام پیشرفت و واچ‌لیست
# =========================

def forward_watchlist_alarms(group: str, cfg: dict, symbol: str, interval: str, alarms: list):
    target_group = WATCH_FORWARD_TARGET.get(group)
    if not target_group:
        return

    target_info = BOT_MAP.get(target_group)
    if not target_info:
        return

    target_bot = target_info["bot"]()
    target_chat_id = cfg.get(target_info["chat_key"])
    if not target_bot or not target_chat_id:
        return

    txt = f"آلارم واچ‌لیست از سیکل {group} برای {symbol} ({interval}):\n"
    for a in alarms:
        txt += f" - {a}\n"
    target_bot.send_message(target_chat_id, txt)

def run_cycle(
    group: str,
    bot,
    chat_id: int,
    symbols: list,
    interval: str,
    lookback_days: int,
    max_bars: int,
    is_watchlist: bool = False
):
    if not bot or not chat_id:
        return

    cfg = load_config()
    progress_step = cfg.get("cycle_progress_step", 5)

    total = len(symbols) if isinstance(symbols, list) else 1
    bot.send_message(chat_id, f"شروع چرخه {group} ({'واچ‌لیست' if is_watchlist else 'نمادهای اصلی'})\nتعداد نمادها: {total}\n# {now_utc_str()} UTC")

    if isinstance(symbols, str):
        symbols = [symbols]

    unique_symbols = list(dict.fromkeys(symbols))

    cycle_alarms = []

    pdf = None
    if cfg.get("make_pdf", False):
        pdf = PdfPages(os.path.join(PDF_DIR, f"{group}_{now_utc().strftime('%Y%m%d_%H%M%S')}.pdf"))

    for idx, sym in enumerate(unique_symbols, start=1):
        # پیام پیشرفت هر N نماد
        if idx == 1 or idx % progress_step == 0 or idx == total:
            bot.send_message(
                chat_id,
                f"پیشرفت سیکل {group}: {idx}/{total} نماد بررسی شده، {total - idx} باقی مانده."
            )

        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"{group}_{sym}_{ts}.png"
        html = f"{group}_{sym}_{ts}.html"

        info = create_plotly_chart(sym, interval, lookback_days, max_bars, png, html)
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

            if pdf is not None:
                img = plt.imread(info["png_path"])
                fig, ax = plt.subplots(figsize=(10,6))
                ax.imshow(img)
                ax.axis("off")
                ax.set_title(f"{sym} – {group}")
                pdf.savefig(fig)
                plt.close(fig)

            # اگر این سیکل روی واچ‌لیست است، آلارم را به ربات مقصد بفرست
            if is_watchlist:
                forward_watchlist_alarms(group, cfg, sym, interval, alarms)

        time.sleep(1)

    if pdf is not None:
        pdf.close()
        bot.send_message(chat_id, f"فایل PDF چرخه {group} ذخیره شد.")

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
# لوپ‌های زمان‌بندی (نمادهای اصلی + واچ‌لیست)
# =========================

def loop_1h():
    while True:
        cfg = load_config()
        now = dt.datetime.now()

        if now.minute == 30 and bot_1h and cfg.get("chat_id_1h"):
            # نمادهای اصلی
            run_cycle(
                group="1h",
                bot=bot_1h,
                chat_id=cfg["chat_id_1h"],
                symbols=cfg["hourly_symbols"],
                interval="1h",
                lookback_days=cfg["hourly_lookback_days"],
                max_bars=cfg["max_bars"],
                is_watchlist=False
            )
            # واچ‌لیست 1h
            wl = cfg.get("watchlist_1h", [])
            if wl:
                run_cycle(
                    group="1h",
                    bot=bot_1h,
                    chat_id=cfg["chat_id_1h"],
                    symbols=wl,
                    interval="1h",
                    lookback_days=cfg["hourly_lookback_days"],
                    max_bars=cfg["max_bars"],
                    is_watchlist=True
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
                    group="4h",
                    bot=bot_4h,
                    chat_id=cfg["chat_id_4h"],
                    symbols=cfg["fourh_symbols"],
                    interval="4h",
                    lookback_days=cfg["fourh_lookback_days"],
                    max_bars=cfg["max_bars"],
                    is_watchlist=False
                )
                wl = cfg.get("watchlist_4h", [])
                if wl:
                    run_cycle(
                        group="4h",
                        bot=bot_4h,
                        chat_id=cfg["chat_id_4h"],
                        symbols=wl,
                        interval="4h",
                        lookback_days=cfg["fourh_lookback_days"],
                        max_bars=cfg["max_bars"],
                        is_watchlist=True
                    )
                time.sleep(60)

        time.sleep(20)

def loop_1d():
    while True:
        cfg = load_config()
        now = dt.datetime.now()

        if now.hour == 23 and now.minute == 30 and bot_1d and cfg.get("chat_id_1d"):
            run_cycle(
                group="1d",
                bot=bot_1d,
                chat_id=cfg["chat_id_1d"],
                symbols=cfg["daily_symbols"],
                interval="1d",
                lookback_days=cfg["daily_lookback_days"],
                max_bars=cfg["max_bars"],
                is_watchlist=False
            )
            wl = cfg.get("watchlist_1d", [])
            if wl:
                run_cycle(
                    group="1d",
                    bot=bot_1d,
                    chat_id=cfg["chat_id_1d"],
                    symbols=wl,
                    interval="1d",
                    lookback_days=cfg["daily_lookback_days"],
                    max_bars=cfg["max_bars"],
                    is_watchlist=True
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
                group="15m",
                bot=bot_15m,
                chat_id=cfg["chat_id_15m"],
                symbols=symbols,
                interval="15m",
                lookback_days=cfg["fifteenm_lookback_days"],
                max_bars=cfg["max_bars"],
                is_watchlist=False
            )

            wl = cfg.get("watchlist_15m", [])
            if wl:
                run_cycle(
                    group="15m",
                    bot=bot_15m,
                    chat_id=cfg["chat_id_15m"],
                    symbols=wl,
                    interval="15m",
                    lookback_days=cfg["fifteenm_lookback_days"],
                    max_bars=cfg["max_bars"],
                    is_watchlist=True
                )

            time.sleep(60)

        time.sleep(20)

# =========================
# اجرای نهایی main
# =========================

if __name__ == "__main__":

    if ADMIN_CHAT:
        if bot_1h:
            bot_1h.send_message(ADMIN_CHAT, "ربات 1h راه‌اندازی شد.")
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