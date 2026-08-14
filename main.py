# -*- coding: utf-8 -*-
# Modu Bazler – Scheduled Edition (Fixed-Time Cycles + 15m Bot + RSI + Configurable Alarms)

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

# =========================
# PATHS
# =========================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
HTML_DIR   = os.path.join(DATA_DIR, "html")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, HTML_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

# =========================
# DEFAULT CONFIG
# =========================

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

    # 15m bot – first 50 symbols (example list, can be edited in config.json)
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

    # Alarm flags (configurable)
    "alarm_wma_direction": True,
    "alarm_cross_sma20": True,
    "alarm_cross_sma100": True,
    "alarm_cross_sma200": True,
    "alarm_sma20_direction": True,
    "alarm_sma100_direction": True,
    "alarm_sma200_direction": True,

    "make_pdf": True,

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None
}

# =========================
# CONFIG LOAD/SAVE + RESET
# =========================

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

# =========================
# TIME HELPERS
# =========================

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

# =========================
# BOT TOKENS
# =========================

TOKEN_1H   = os.getenv("TOKEN_1H")
TOKEN_4H   = os.getenv("TOKEN_4H")
TOKEN_1D   = os.getenv("TOKEN_1D")
TOKEN_15M  = os.getenv("TOKEN_15M")

def create_bot(token):
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

# =========================
# MENUS & HELP
# =========================

HELP_TEXT = """
Modu Bazler – نسخه زمان‌بندی‌شده

دستورات اصلی:
/start  – ثبت چت و نمایش منو
/symbol – دریافت نمودار یک نماد (تایم‌فریم ۱ساعته)
/alarm  – تنظیم و تغییر وضعیت آلارم‌ها
/reset  – بازگردانی تنظیمات نمادها به حالت پیش‌فرض
/help   – نمایش همین راهنما

آلارم‌ها:
- تغییر جهت WMA20 (شیب مثبت به منفی یا برعکس)
- تغییر جهت SMA20 / SMA100 / SMA200
- برخورد WMA با SMA20 / SMA100 / SMA200

در هر چرخه (۱ساعته، ۴ساعته، روزانه، ۱۵دقیقه):
- برای هر نماد، نمودار کندل + SMA20/100/200 + WMA20 + RSI14 رسم می‌شود.
- در صورت وقوع آلارم، عکس نمودار به همراه لیست آلارم‌ها برای ربات مربوطه ارسال می‌شود.
- در صورت فعال بودن ساخت PDF، مجموعه نمودارها در فایل PDF ذخیره می‌گردد.

ربات‌ها:
- ربات ۱ساعته: TOKEN_1H
- ربات ۴ساعته: TOKEN_4H
- ربات روزانه: TOKEN_1D
- ربات ۱۵دقیقه: TOKEN_15M (برای ۵۰ نماد اول)

تنظیمات:
فایل config.json در پوشه data شامل:
- لیست نمادها برای هر تایم‌فریم
- تعداد روزهای نگاه‌به‌عقب
- حداکثر تعداد کندل‌ها
- وضعیت آلارم‌ها (True/False)
- chat_id هر ربات

با تغییر این مقادیر و ری‌استارت برنامه، رفتار ربات‌ها مطابق تنظیمات جدید خواهد بود.
"""

def send_main_menu(bot, chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("✅ بررسی نماد", "📊 اجرای دستی ۱ساعته")
    kb.row("🔔 تنظیم آلارم‌ها", "🛑 توقف (نمادها تغییری نمی‌کنند)")
    kb.row("♻️ بازگردانی نمادها", "ℹ️ راهنما")
    bot.send_message(chat_id, "لطفاً گزینه مورد نظر را انتخاب کنید:", reply_markup=kb)

# =========================
# START COMMANDS
# =========================

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
        bot_4h.send_message(m.chat.id, f"ربات ۴ساعته فعال شد.\n# {now_utc_str()} UTC")

if bot_1d:
   @bot_1d.message_handler(commands=["start"])
    def start_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        bot_1d.send_message(m.chat.id, f"ربات روزانه فعال شد.\n# {now_utc_str()} UTC")

if bot_15m:
    @bot_15m.message_handler(commands=["start"])
    def start_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        bot_15m.send_message(m.chat.id, f"ربات ۱۵دقیقه‌ای فعال شد.\n# {now_utc_str()} UTC")

def refresh_menu_if_needed(bot, chat_id):
    try:
        send_main_menu(bot, chat_id)
    except:
        pass
@bot_1h.message_handler(commands=["start"])
def start_1h(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)

    bot_1h.send_message(m.chat.id, HELP_TEXT)

    refresh_menu_if_needed(bot_1h, m.chat.id)

@bot_1h.message_handler(commands=["toggle_wma_dir"])
def toggle_wma_dir(m):
    cfg = load_config()
    cfg["alarm_wma_direction"] = not cfg["alarm_wma_direction"]
    save_config(cfg)

    bot_1h.send_message(m.chat.id, f"alarm_wma_direction = {cfg['alarm_wma_direction']}")

    refresh_menu_if_needed(bot_1h, m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "بازنشانی نمادها")
def reset_symbols(m):
    cfg = load_config()
    cfg["hourly_symbols"] = DEFAULT_CONFIG["hourly_symbols"]
    cfg["fourh_symbols"]  = DEFAULT_CONFIG["fourh_symbols"]
    cfg["daily_symbols"]  = DEFAULT_CONFIG["daily_symbols"]
    cfg["fifteenm_symbols"] = DEFAULT_CONFIG["fifteenm_symbols"]
    save_config(cfg)

    bot_1h.send_message(m.chat.id, "نمادها ریست شدند.")

    refresh_menu_if_needed(bot_1h, m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای دستی 1h")
def manual_1h(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)

    run_cycle("1h", bot_1h, m.chat.id,
              cfg["hourly_symbols"], "1h",
              cfg["hourly_lookback_days"], cfg["max_bars"])

    refresh_menu_if_needed(bot_1h, m.chat.id)



# =========================
# SYMBOL CHECK (1h)
# =========================

if bot_1h:
    @bot_1h.message_handler(func=lambda m: m.text == "✅ بررسی نماد")
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

        alarms = detect_alarms(cfg, info)
        caption = f"نمودار {symbol}\nآخرین قیمت: {info['last_close']}\n"
        if alarms:
            caption += "آلارم‌ها:\n" + "\n".join(alarms)

        with open(info["png_path"], "rb") as f:
            bot_1h.send_photo(m.chat.id, f, caption=caption)

# =========================
# DATA FETCH (BINANCE + KUCOIN)
# =========================

def _binance_interval(i):
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i):
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

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
    except Exception:
        pass

    # KuCoin fallback
    try:
        sym = symbol.replace("USDT", "-USDT")
        end = int(now_utc().timestamp())
        start = end - 60*60*(limit + 10)
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
    except Exception:
        return pd.DataFrame()

# =========================
# INDICATORS + CHART
# =========================

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

    # RSI14
    delta = df["c"].diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_gain = pd.Series(gain).rolling(14).mean()
    roll_loss = pd.Series(loss).rolling(14).mean()
    rs = roll_gain / roll_loss
    rsi = 100 - (100 / (1 + rs))
    df["RSI14"] = rsi

    return df

def create_plotly_chart(symbol, interval, lookback_days, max_bars, png_name, html_name):
    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)
    df.columns = ["o","h","l","c","v"]
    df = compute_indicators(df)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3],
                        vertical_spacing=0.03)

    # Candles
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["o"], high=df["h"], low=df["l"], close=df["c"],
            name="Price"
        ),
        row=1, col=1
    )

    # SMAs
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"],  mode="lines", name="SMA20",  line=dict(color="blue")),  row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA100"], mode="lines", name="SMA100", line=dict(color="orange")),row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], mode="lines", name="SMA200", line=dict(color="purple")),row=1, col=1)

    # WMA20 with slope-based color
    wma = df["WMA20"]
    slope = df["WMA20_slope"]
    wma_up   = wma.where(slope >= 0)
    wma_down = wma.where(slope < 0)

    fig.add_trace(
        go.Scatter(x=df.index, y=wma_up, mode="lines", name="WMA20 Up",
                   line=dict(color="green", width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=wma_down, mode="lines", name="WMA20 Down",
                   line=dict(color="red", width=2)),
        row=1, col=1
    )

    # RSI
    fig.add_trace(
        go.Scatter(x=df.index, y=df["RSI14"], mode="lines", name="RSI14",
                   line=dict(color="brown")),
        row=2, col=1
    )
    fig.add_hline(y=70, line=dict(color="red", dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="green", dash="dash"), row=2, col=1)

    fig.update_layout(
        title=f"{symbol} – {interval}",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=900
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
        "sma100": df["SMA100"].tolist(),
        "sma200": df["SMA200"].tolist()
    }

# =========================
# ALARMS
# =========================

def detect_alarms(cfg, info):
    alarms = []
    wma    = info["wma"]
    slope  = info["wma_slope"]
    sma20  = info["sma20"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]

    if len(wma) < 3 or len(slope) < 3:
        return alarms

    # WMA direction change
    if cfg.get("alarm_wma_direction", True):
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("WMA20 جهت رو به بالا گرفت")
        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("WMA20 جهت رو به پایین گرفت")

    def cross(a, b):
        return (a[-2] - b[-2]) * (a[-1] - b[-1]) < 0

    # Crosses
    if cfg.get("alarm_cross_sma20", True) and cross(wma, sma20):
        alarms.append("برخورد WMA20 با SMA20")
    if cfg.get("alarm_cross_sma100", True) and cross(wma, sma100):
        alarms.append("برخورد WMA20 با SMA100")
    if cfg.get("alarm_cross_sma200", True) and cross(wma, sma200):
        alarms.append("برخورد WMA20 با SMA200")

    # SMA direction changes
    def dir_change(arr, name):
        if len(arr) < 3:
            return
        d1 = arr[-1] - arr[-2]
        d2 = arr[-2] - arr[-3]
        if d2 < 0 and d1 > 0:
            alarms.append(f"{name} جهت رو به بالا گرفت")
        if d2 > 0 and d1 < 0:
            alarms.append(f"{name} جهت رو به پایین گرفت")

    if cfg.get("alarm_sma20_direction", True):
        dir_change(sma20, "SMA20")
    if cfg.get("alarm_sma100_direction", True):
        dir_change(sma100, "SMA100")
    if cfg.get("alarm_sma200_direction", True):
        dir_change(sma200, "SMA200")

    return alarms

# =========================
# CYCLE ENGINE
# =========================

def run_cycle(group, bot, chat_id, symbols, interval, lookback_days, max_bars):
    if not bot or not chat_id:
        return

    bot.send_message(chat_id, f"شروع چرخه {group}\n# {now_utc_str()} UTC")

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

        if alarms:
            caption = f"آلارم برای {sym} ({group})\n" + "\n".join(alarms)
            with open(info["png_path"], "rb") as f:
                bot.send_photo(chat_id, f, caption=caption)

        # اضافه به PDF
        if pdf is not None:
            img = plt.imread(info["png_path"])
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.imshow(img)
            ax.axis("off")
            ax.set_title(f"{sym} – {group}")
            pdf.savefig(fig)
            plt.close(fig)

    if pdf is not None:
        pdf.close()
        bot.send_message(chat_id, f"فایل PDF چرخه {group} ذخیره شد.")

    bot.send_message(chat_id, f"پایان چرخه {group}")

# =========================
# FIXED-TIME SCHEDULER
# =========================

def loop_daily():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.hour == 23 and now.minute == 30:
            if cfg.get("chat_id_1d") and bot_1d:
                run_cycle(
                    "1d", bot_1d, cfg["chat_id_1d"],
                    cfg["daily_symbols"], "1d",
                    cfg["daily_lookback_days"], cfg["max_bars"]
                )
            time.sleep(60)
        time.sleep(20)

def loop_4h():
    times = [(4,30),(8,30),(12,30),(16,30),(20,30),(23,30),(0,30)]
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        for h,m in times:
            if now.hour == h and now.minute == m:
                if cfg.get("chat_id_4h") and bot_4h:
                    run_cycle(
                        "4h", bot_4h, cfg["chat_id_4h"],
                        cfg["fourh_symbols"], "4h",
                        cfg["fourh_lookback_days"], cfg["max_bars"]
                    )
                time.sleep(60)
        time.sleep(20)

def loop_1h():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute == 30:
            if cfg.get("chat_id_1h") and bot_1h:
                run_cycle(
                    "1h", bot_1h, cfg["chat_id_1h"],
                    cfg["hourly_symbols"], "1h",
                    cfg["hourly_lookback_days"], cfg["max_bars"]
                )
            time.sleep(60)
        time.sleep(20)

def loop_15m():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute % 15 == 0:
            if cfg.get("chat_id_15m") and bot_15m:
                run_cycle(
                    "15m", bot_15m, cfg["chat_id_15m"],
                    cfg["fifteenm_symbols"], "15m",
                    cfg["fifteenm_lookback_days"], cfg["max_bars"]
                )
            time.sleep(60)
        time.sleep(20)

# =========================
# START / STOP / MANUAL / HELP / RESET (1h bot)
# =========================

if bot_1h:
    @bot_1h.message_handler(func=lambda m: m.text == "🛑 توقف (نمادها تغییری نمی‌کنند)")
    def stop_all(m):
        bot_1h.send_message(m.chat.id, "چرخه‌ها متوقف نمی‌شوند از اینجا؛ برای توقف کامل، سرویس را در هاست خاموش کنید.")

    @bot_1h.message_handler(func=lambda m: m.text == "📊 اجرای دستی ۱ساعته")
    def manual_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        run_cycle(
            "1h", bot_1h, m.chat.id,
            cfg["hourly_symbols"], "1h",
            cfg["hourly_lookback_days"], cfg["max_bars"]
        )

    @bot_1h.message_handler(func=lambda m: m.text == "♻️ بازگردانی نمادها")
    def reset_symbols(m):
        cfg = load_config()
        cfg["hourly_symbols"] = DEFAULT_CONFIG["hourly_symbols"]
        cfg["fourh_symbols"]  = DEFAULT_CONFIG["fourh_symbols"]
        cfg["daily_symbols"]  = DEFAULT_CONFIG["daily_symbols"]
        cfg["fifteenm_symbols"] = DEFAULT_CONFIG["fifteenm_symbols"]
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "نمادها به حالت پیش‌فرض بازگردانده شدند.")

    @bot_1h.message_handler(func=lambda m: m.text == "ℹ️ راهنما")
    def show_help(m):
        bot_1h.send_message(m.chat.id, HELP_TEXT)

    @bot_1h.message_handler(func=lambda m: m.text == "🔔 تنظیم آلارم‌ها")
    def alarm_menu(m):
        cfg = load_config()
        text = "وضعیت فعلی آلارم‌ها:\n"
        text += f"WMA جهت: {cfg.get('alarm_wma_direction', True)}\n"
        text += f"Cross SMA20: {cfg.get('alarm_cross_sma20', True)}\n"
        text += f"Cross SMA100: {cfg.get('alarm_cross_sma100', True)}\n"
        text += f"Cross SMA200: {cfg.get('alarm_cross_sma200', True)}\n"
        text += f"SMA20 جهت: {cfg.get('alarm_sma20_direction', True)}\n"
        text += f"SMA100 جهت: {cfg.get('alarm_sma100_direction', True)}\n"
        text += f"SMA200 جهت: {cfg.get('alarm_sma200_direction', True)}\n\n"
        text += "برای تغییر، یکی از دستورات زیر را ارسال کنید:\n"
        text += "/toggle_wma_dir\n/toggle_cross_sma20\n/toggle_cross_sma100\n/toggle_cross_sma200\n"
        text += "/toggle_sma20_dir\n/toggle_sma100_dir\n/toggle_sma200_dir\n"
        bot_1h.send_message(m.chat.id, text)

    @bot_1h.message_handler(commands=["toggle_wma_dir"])
    def toggle_wma_dir(m):
        cfg = load_config()
        cfg["alarm_wma_direction"] = not cfg.get("alarm_wma_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_wma_direction = {cfg['alarm_wma_direction']}")

    @bot_1h.message_handler(commands=["toggle_cross_sma20"])
    def toggle_cross_sma20(m):
        cfg = load_config()
        cfg["alarm_cross_sma20"] = not cfg.get("alarm_cross_sma20", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_cross_sma20 = {cfg['alarm_cross_sma20']}")

    @bot_1h.message_handler(commands=["toggle_cross_sma100"])
    def toggle_cross_sma100(m):
        cfg = load_config()
        cfg["alarm_cross_sma100"] = not cfg.get("alarm_cross_sma100", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_cross_sma100 = {cfg['alarm_cross_sma100']}")

    @bot_1h.message_handler(commands=["toggle_cross_sma200"])
    def toggle_cross_sma200(m):
        cfg = load_config()
        cfg["alarm_cross_sma200"] = not cfg.get("alarm_cross_sma200", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_cross_sma200 = {cfg['alarm_cross_sma200']}")

    @bot_1h.message_handler(commands=["toggle_sma20_dir"])
    def toggle_sma20_dir(m):
        cfg = load_config()
        cfg["alarm_sma20_direction"] = not cfg.get("alarm_sma20_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_sma20_direction = {cfg['alarm_sma20_direction']}")

    @bot_1h.message_handler(commands=["toggle_sma100_dir"])
    def toggle_sma100_dir(m):
        cfg = load_config()
        cfg["alarm_sma100_direction"] = not cfg.get("alarm_sma100_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_sma100_direction = {cfg['alarm_sma100_direction']}")

    @bot_1h.message_handler(commands=["toggle_sma200_dir"])
    def toggle_sma200_dir(m):
        cfg = load_config()
        cfg["alarm_sma200_direction"] = not cfg.get("alarm_sma200_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_sma200_direction = {cfg['alarm_sma200_direction']}")

# =========================
# THREADS
# =========================

def start_threads():
    t1 = threading.Thread(target=loop_1h,    daemon=True)
    t2 = threading.Thread(target=loop_4h,    daemon=True)
    t3 = threading.Thread(target=loop_daily, daemon=True)
    t4 = threading.Thread(target=loop_15m,   daemon=True)

    t1.start()
    t2.start()
    t3.start()
    t4.start()

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    # شروع برنامه – پیام به هر ربات (در صورت داشتن chat_id)
    cfg = load_config()
    if bot_1h and cfg.get("chat_id_1h"):
        bot_1h.send_message(cfg["chat_id_1h"], f"برنامه اصلی Modu Bazler شروع شد.\n# {now_utc_str()} UTC")
    if bot_4h and cfg.get("chat_id_4h"):
        bot_4h.send_message(cfg["chat_id_4h"], f"برنامه اصلی Modu Bazler شروع شد.\n# {now_utc_str()} UTC")
    if bot_1d and cfg.get("chat_id_1d"):
        bot_1d.send_message(cfg["chat_id_1d"], f"برنامه اصلی Modu Bazler شروع شد.\n# {now_utc_str()} UTC")
    if bot_15m and cfg.get("chat_id_15m"):
        bot_15m.send_message(cfg["chat_id_15m"], f"برنامه اصلی Modu Bazler شروع شد.\n# {now_utc_str()} UTC")

    start_threads()

    # polling برای هر ربات موجود
    if bot_1h:
        threading.Thread(target=lambda: bot_1h.infinity_polling(), daemon=True).start()
    if bot_4h:
        threading.Thread(target=lambda: bot_4h.infinity_polling(), daemon=True).start()
    if bot_1d:
        threading.Thread(target=lambda: bot_1d.infinity_polling(), daemon=True).start()
    if bot_15m:
        threading.Thread(target=lambda: bot_15m.infinity_polling(), daemon=True).start()

    # نگه داشتن برنامه
    while True:
        time.sleep(60)