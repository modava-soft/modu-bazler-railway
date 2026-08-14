# -*- coding: utf-8 -*-
# Modu Bazler – Scheduled Edition (Fixed-Time Cycles + 4 Bots + Alarms + RSI/MACD)

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

DATA_DIR = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
HTML_DIR = os.path.join(DATA_DIR, "html")
PDF_DIR = os.path.join(DATA_DIR, "pdf")

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
    # 15m: top 50 symbols – user can adjust later
    "fifteenm_symbols": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT",
        "UNIUSDT","ICPUSDT","ARBUSDT","OPUSDT","SUIUSDT",
        "PEPEUSDT","TONUSDT","INJUSDT","RNDRUSDT","FTMUSDT",
        "GALAUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","JUPUSDT",
        "WIFUSDT","FLOKIUSDT","BONKUSDT","RUNEUSDT","BLURUSDT",
        "LDOUSDT","AAVEUSDT","CRVUSDT","COMPUSDT","SNXUSDT",
        "DYDXUSDT","GMXUSDT","CAKEUSDT","XVSUSDT","YFIUSDT"
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

    # Alarm flags – configurable
    "alarm_wma_direction": True,
    "alarm_sma_direction_20": False,
    "alarm_sma_direction_50": False,
    "alarm_sma_direction_200": False,
    "alarm_cross_sma20": True,
    "alarm_cross_sma50": True,
    "alarm_cross_sma200": True,

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

TOKEN_1H = os.getenv("TOKEN_1H")
TOKEN_4H = os.getenv("TOKEN_4H")
TOKEN_1D = os.getenv("TOKEN_1D")
TOKEN_15M = os.getenv("TOKEN_15M")

bot_1h = telebot.TeleBot(TOKEN_1H, parse_mode="HTML")
bot_4h = telebot.TeleBot(TOKEN_4H, parse_mode="HTML")
bot_1d = telebot.TeleBot(TOKEN_1D, parse_mode="HTML")
bot_15m = telebot.TeleBot(TOKEN_15M, parse_mode="HTML")

# =========================================================
# MENUS
# =========================================================

HELP_TEXT = """مودو بازلر – نسخه زمان‌بندی‌شده

دستورات و دکمه‌ها:

۱) دکمه «بررسی نماد تکی»
   - یک نماد مثل BTCUSDT وارد کنید.
   - نمودار کندل + SMA20 + SMA50 + WMA20 + RSI + MACD ساخته می‌شود.
   - خروجی به صورت PNG و PDF ذخیره و PNG برای شما ارسال می‌شود.

۲) دکمه «اجرای دستی ۱ ساعته»
   - برای همه نمادهای لیست ۱ ساعته، یک چرخه کامل اجرا می‌شود.
   - برای هر نماد، نمودار و آلارم‌ها بررسی و در صورت وجود، عکس و متن آلارم ارسال می‌شود.

۳) دکمه «تنظیم آلارم‌ها»
   - وضعیت آلارم‌ها (تغییر جهت WMA، تغییر جهت SMAها، برخورد WMA با SMAها) نمایش داده می‌شود.
   - با ارسال دستورات:
     /alarm_wma       فعال/غیرفعال کردن آلارم تغییر جهت WMA
     /alarm_sma20     فعال/غیرفعال کردن آلارم تغییر جهت SMA20
     /alarm_sma50     فعال/غیرفعال کردن آلارم تغییر جهت SMA50
     /alarm_sma200    فعال/غیرفعال کردن آلارم تغییر جهت SMA200
     /alarm_cross20   فعال/غیرفعال کردن آلارم برخورد WMA با SMA20
     /alarm_cross50   فعال/غیرفعال کردن آلارم برخورد WMA با SMA50
     /alarm_cross200  فعال/غیرفعال کردن آلارم برخورد WMA با SMA200

۴) دکمه «بازنشانی نمادها»
   - لیست نمادهای ۱ ساعته، ۴ ساعته، روزانه و ۱۵ دقیقه‌ای به حالت پیش‌فرض برمی‌گردد.

۵) دکمه «توقف خودکار»
   - فقط پیام اطلاع‌رسانی می‌فرستد (برای توقف کامل باید ربات را از هاست متوقف کنید).

ربات‌ها:
- ربات ۱ ساعته: تحلیل دوره‌ای ۱h
- ربات ۴ ساعته: تحلیل دوره‌ای 4h
- ربات روزانه: تحلیل دوره‌ای 1d
- ربات ۱۵ دقیقه‌ای: تحلیل دوره‌ای 15m برای حدود ۵۰ نماد اول

نمودارها:
- محور عمودی (قیمت) در سمت راست قرار دارد.
- محور افقی (زمان) با فواصل مناسب (یکی در میان) مدرج می‌شود.
- زیر نمودار کندل:
  * ردیف دوم: RSI (۱۴ دوره)
  * ردیف سوم: MACD (۱۲-۲۶-۹) با هیستوگرام

خروجی:
- فایل PNG در پوشه charts
- فایل PDF در پوشه pdf (تصویر نمودار در یک صفحه)
"""

def send_main_menu(chat_id, bot):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("بررسی نماد تکی", "اجرای دستی ۱ ساعته")
    kb.row("تنظیم آلارم‌ها", "بازنشانی نمادها")
    kb.row("توقف خودکار", "راهنما")
    bot.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

# =========================================================
# START COMMANDS
# =========================================================

@bot_1h.message_handler(commands=["start"])
def start_1h(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    bot_1h.send_message(m.chat.id, HELP_TEXT)
    send_main_menu(m.chat.id, bot_1h)

@bot_4h.message_handler(commands=["start"])
def start_4h(m):
    cfg = load_config()
    cfg["chat_id_4h"] = m.chat.id
    save_config(cfg)
    bot_4h.send_message(
        m.chat.id,
        f"ربات ۴ ساعته فعال شد.\nزمان فعلی:\n# {now_utc_str()} UTC"
    )

@bot_1d.message_handler(commands=["start"])
def start_1d(m):
    cfg = load_config()
    cfg["chat_id_1d"] = m.chat.id
    save_config(cfg)
    bot_1d.send_message(
        m.chat.id,
        f"ربات روزانه فعال شد.\nزمان فعلی:\n# {now_utc_str()} UTC"
    )

@bot_15m.message_handler(commands=["start"])
def start_15m(m):
    cfg = load_config()
    cfg["chat_id_15m"] = m.chat.id
    save_config(cfg)
    bot_15m.send_message(
        m.chat.id,
        f"ربات ۱۵ دقیقه‌ای فعال شد.\nزمان فعلی:\n# {now_utc_str()} UTC"
    )

# =========================================================
# SYMBOL CHECK (SINGLE)
# =========================================================

@bot_1h.message_handler(func=lambda m: m.text == "بررسی نماد تکی")
def ask_symbol(m):
    msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید (مثلاً BTCUSDT):")
    bot_1h.register_next_step_handler(msg, do_symbol)

def do_symbol(m):
    symbol = m.text.strip().upper()
    cfg = load_config()
    bot_1h.send_message(m.chat.id, f"در حال ساخت نمودار برای {symbol} ...")

    ts = now_utc().strftime("%Y%m%d_%H%M%S")
    png_name = f"SINGLE_{symbol}_{ts}.png"
    html_name = f"SINGLE_{symbol}_{ts}.html"

    info = create_plotly_chart(
        symbol,
        cfg["hourly_interval"],
        cfg["hourly_lookback_days"],
        cfg["max_bars"],
        png_name,
        html_name
    )

    with open(info["png_path"], "rb") as f:
        bot_1h.send_photo(m.chat.id, f)

# =========================================================
# DATA FETCH (BINANCE + KUCOIN)
# =========================================================

def _binance_interval(i):
    return {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}[i]

def _kucoin_interval(i):
    return {"15m": "15min", "1h": "1hour", "4h": "4hour", "1d": "1day"}[i]

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
    except Exception:
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
    except Exception:
        return pd.DataFrame()

# =========================================================
# INDICATORS + CHART
# =========================================================

def compute_indicators(df):
    df = df.copy()

    # SMA20, SMA50, SMA200
    df["SMA20"] = df["c"].rolling(20).mean()
    df["SMA50"] = df["c"].rolling(50).mean()
    df["SMA200"] = df["c"].rolling(200).mean()

    # WMA20
    df["WMA20"] = df["c"].rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x)+1)),
        raw=True
    )
    df["WMA20_slope"] = df["WMA20"].diff()

    # RSI (14)
    delta = df["c"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD (12-26-9)
    ema12 = df["c"].ewm(span=12, adjust=False).mean()
    ema26 = df["c"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    return df

def _x_dtick_ms(interval):
    if interval == "15m":
        return 30 * 60 * 1000  # 30 minutes
    if interval == "1h":
        return 2 * 60 * 60 * 1000  # 2 hours
    if interval == "4h":
        return 8 * 60 * 60 * 1000  # 8 hours
    if interval == "1d":
        return 2 * 24 * 60 * 60 * 1000  # 2 days
    return None

def create_plotly_chart(symbol, interval, lookback_days, max_bars, png_name, html_name):
    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)
    if df.empty:
        # create empty placeholder
        df = pd.DataFrame(
            columns=["o","h","l","c","v"],
            index=pd.date_range(end=now_utc(), periods=10, freq="H")
        )
        df.fillna(0, inplace=True)
    else:
        df.columns = ["o","h","l","c","v"]

    df = compute_indicators(df)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03
    )

    # Candles
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

    # SMA20, SMA50, SMA200
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA20"],
            mode="lines",
            name="SMA20",
            line=dict(color="blue", width=1.5)
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA50"],
            mode="lines",
            name="SMA50",
            line=dict(color="orange", width=1.5)
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA200"],
            mode="lines",
            name="SMA200",
            line=dict(color="purple", width=1.5)
        ),
        row=1, col=1
    )

    # WMA20 with slope-based color (up=green, down=red)
    wma = df["WMA20"]
    slope = df["WMA20_slope"]
    wma_up = wma.where(slope >= 0)
    wma_down = wma.where(slope < 0)

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=wma_up,
            mode="lines",
            name="WMA20 Up",
            line=dict(color="green", width=2, dash="dot")
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=wma_down,
            mode="lines",
            name="WMA20 Down",
            line=dict(color="red", width=2, dash="dot")
        ),
        row=1, col=1
    )

    # RSI
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["RSI"],
            mode="lines",
            name="RSI",
            line=dict(color="brown", width=1.5)
        ),
        row=2, col=1
    )
    fig.update_yaxes(range=[0, 100], row=2, col=1)

    # MACD
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MACD"],
            mode="lines",
            name="MACD",
            line=dict(color="teal", width=1.5)
        ),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MACD_signal"],
            mode="lines",
            name="Signal",
            line=dict(color="gray", width=1.0, dash="dash")
        ),
        row=3, col=1
    )
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["MACD_hist"],
            name="MACD Hist",
            marker_color="darkslateblue"
        ),
        row=3, col=1
    )

    # Layout: axes, legend, title
    dtick_ms = _x_dtick_ms(interval)

    fig.update_layout(
        title=f"{symbol} – {interval} | {now_utc_str()} UTC",
        xaxis=dict(
            showgrid=True,
            tickformat="%Y-%m-%d\n%H:%M",
            dtick=dtick_ms
        ),
        yaxis=dict(
            side="right",
            showgrid=True
        ),
        xaxis2=dict(
            showgrid=True,
            tickformat="%Y-%m-%d\n%H:%M",
            dtick=dtick_ms
        ),
        xaxis3=dict(
            showgrid=True,
            tickformat="%Y-%m-%d\n%H:%M",
            dtick=dtick_ms
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        height=900
    )

    html_path = os.path.join(HTML_DIR, html_name)
    fig.write_html(html_path)

    png_path = os.path.join(CHARTS_DIR, png_name)
    fig.write_image(png_path, width=1800, height=1100, scale=3)

    # PDF (single page with PNG)
    pdf_path = os.path.join(PDF_DIR, png_name.replace(".png", ".pdf"))
    try:
        with PdfPages(pdf_path) as pdf:
            img = plt.imread(png_path)
            fig_pdf = plt.figure(figsize=(8.27, 11.69))  # A4
            ax = fig_pdf.add_subplot(111)
            ax.imshow(img)
            ax.axis("off")
            pdf.savefig(fig_pdf)
            plt.close(fig_pdf)
    except Exception:
        pdf_path = None

    return {
        "symbol": symbol,
        "interval": interval,
        "png_path": png_path,
        "html_path": html_path,
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

    # WMA direction
    if cfg.get("alarm_wma_direction", False):
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("WMA جهت رو به بالا تغییر کرد.")
        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("WMA جهت رو به پایین تغییر کرد.")

    def cross(a, b):
        return (a[-2] - b[-2]) * (a[-1] - b[-1]) < 0

    # SMA direction (optional)
    def dir_change(series, name):
        if series[-2] < series[-1]:
            return f"{name} رو به بالا است."
        elif series[-2] > series[-1]:
            return f"{name} رو به پایین است."
        return None

    if cfg.get("alarm_sma_direction_20", False):
        msg = dir_change(sma20, "SMA20")
        if msg:
            alarms.append(msg)
    if cfg.get("alarm_sma_direction_50", False):
        msg = dir_change(sma50, "SMA50")
        if msg:
            alarms.append(msg)
    if cfg.get("alarm_sma_direction_200", False):
        msg = dir_change(sma200, "SMA200")
        if msg:
            alarms.append(msg)

    # Crosses
    if cfg.get("alarm_cross_sma20", False) and cross(wma, sma20):
        alarms.append("WMA با SMA20 برخورد کرد.")
    if cfg.get("alarm_cross_sma50", False) and cross(wma, sma50):
        alarms.append("WMA با SMA50 برخورد کرد.")
    if cfg.get("alarm_cross_sma200", False) and cross(wma, sma200):
        alarms.append("WMA با SMA200 برخورد کرد.")

    return alarms

# =========================================================
# CYCLE ENGINE
# =========================================================

def run_cycle(group, bot, chat_id, symbols, interval, lookback_days, max_bars):
    bot.send_message(
        chat_id,
        f"شروع چرخه {group}\n# {now_utc_str()} UTC"
    )

    cfg = load_config()

    for sym in symbols:
        bot.send_message(chat_id, f"در حال پردازش: {sym}")

        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"{group}_{sym}_{ts}.png"
        html = f"{group}_{sym}_{ts}.html"

        info = create_plotly_chart(sym, interval, lookback_days, max_bars, png, html)
        alarms = detect_alarms(cfg, info)

        caption = f"{sym} – {group}\nزمان: {info['created_at']} UTC"
        if alarms:
            caption += "\n" + "\n".join(alarms)

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
        for h, m in times:
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
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        # هر ۱۵ دقیقه، مثلاً در دقیقه ۵
        if now.minute % 15 == 5:
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
# START / STOP / MANUAL / HELP / ALARM CONFIG
# =========================================================

@bot_1h.message_handler(func=lambda m: m.text == "توقف خودکار")
def stop_all(m):
    bot_1h.send_message(
        m.chat.id,
        "توقف خودکار فقط با توقف سرویس هاست انجام می‌شود.\nاین پیام صرفاً اطلاع‌رسانی است."
    )

@bot_1h.message_handler(func=lambda m: m.text == "اجرای دستی ۱ ساعته")
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
    cfg["hourly_symbols"] = DEFAULT_CONFIG["hourly_symbols"]
    cfg["fourh_symbols"] = DEFAULT_CONFIG["fourh_symbols"]
    cfg["daily_symbols"] = DEFAULT_CONFIG["daily_symbols"]
    cfg["fifteenm_symbols"] = DEFAULT_CONFIG["fifteenm_symbols"]
    save_config(cfg)
    bot_1h.send_message(m.chat.id, "لیست نمادها به حالت پیش‌فرض بازنشانی شد.")

@bot_1h.message_handler(func=lambda m: m.text == "راهنما")
def show_help(m):
    bot_1h.send_message(m.chat.id, HELP_TEXT)

@bot_1h.message_handler(func=lambda m: m.text == "تنظیم آلارم‌ها")
def alarm_menu(m):
    cfg = load_config()
    lines = [
        f"alarm_wma_direction: {cfg.get('alarm_wma_direction', False)}",
        f"alarm_sma_direction_20: {cfg.get('alarm_sma_direction_20', False)}",
        f"alarm_sma_direction_50: {cfg.get('alarm_sma_direction_50', False)}",
        f"alarm_sma_direction_200: {cfg.get('alarm_sma_direction_200', False)}",
        f"alarm_cross_sma20: {cfg.get('alarm_cross_sma20', False)}",
        f"alarm_cross_sma50: {cfg.get('alarm_cross_sma50', False)}",
        f"alarm_cross_sma200: {cfg.get('alarm_cross_sma200', False)}",
        "",
        "برای تغییر هر آلارم، یکی از دستورات زیر را ارسال کنید:",
        "/alarm_wma",
        "/alarm_sma20",
        "/alarm_sma50",
        "/alarm_sma200",
        "/alarm_cross20",
        "/alarm_cross50",
        "/alarm_cross200",
    ]
    bot_1h.send_message(m.chat.id, "\n".join(lines))

# Toggle commands
@bot_1h.message_handler(commands=["alarm_wma"])
def toggle_alarm_wma(m):
    cfg = load_config()
    cfg["alarm_wma_direction"] = not cfg.get("alarm_wma_direction", False)
    save_config(cfg)
    bot_1h.send_message(m.chat.id, f"alarm_wma_direction = {cfg['alarm_wma_direction']}")

@bot_1h.message_handler(commands=["alarm_sma20"])
def toggle_alarm_sma20(m):
    cfg = load_config()
    cfg["alarm_sma_direction_20"] = not cfg.get("alarm_sma_direction_20", False)
    save_config(cfg)
    bot_1h.send_message(m.chat.id, f"alarm_sma_direction_20 = {cfg['alarm_sma_direction_20']}")

@bot_1h.message_handler(commands=["alarm_sma50"])
def toggle_alarm_sma50(m):
    cfg = load_config()
    cfg["alarm_sma_direction_50"] = not cfg.get("alarm_sma_direction_50", False)
    save_config(cfg)
    bot_1h.send_message(m.chat.id, f"alarm_sma_direction_50 = {cfg['alarm_sma_direction_50']}")

@bot_1h.message_handler(commands=["alarm_sma200"])
def toggle_alarm_sma200(m):
    cfg = load_config()
    cfg["alarm_sma_direction_200"] = not cfg.get("alarm_sma_direction_200", False)
    save_config(cfg)
    bot_1h.send_message(m.chat.id, f"alarm_sma_direction_200 = {cfg['alarm_sma_direction_200']}")

@bot_1h.message_handler(commands=["alarm_cross20"])
def toggle_alarm_cross20(m):
    cfg = load_config()
    cfg["alarm_cross_sma20"] = not cfg.get("alarm_cross_sma20", False)
    save_config(cfg)
    bot_1h.send_message(m.chat.id, f"alarm_cross_sma20 = {cfg['alarm_cross_sma20']}")

@bot_1h.message_handler(commands=["alarm_cross50"])
def toggle_alarm_cross50(m):
    cfg = load_config()
    cfg["alarm_cross_sma50"] = not cfg.get("alarm_cross_sma50", False)
    save_config(cfg)
    bot_1h.send_message(m.chat.id, f"alarm_cross_sma50 = {cfg['alarm_cross_sma50']}")

@bot_1h.message_handler(commands=["alarm_cross200"])
def toggle_alarm_cross200(m):
    cfg = load_config()
    cfg["alarm_cross_sma200"] = not cfg.get("alarm_cross_sma200", False)
    save_config(cfg)
    bot_1h.send_message(m.chat.id, f"alarm_cross_sma200 = {cfg['alarm_cross_sma200']}")

# =========================================================
# THREADS
# =========================================================

def start_threads():
    t1 = threading.Thread(target=loop_1h, daemon=True)
    t2 = threading.Thread(target=loop_4h, daemon=True)
    t3 = threading.Thread(target=loop_daily, daemon=True)
    t4 = threading.Thread(target=loop_15m, daemon=True)

    t1.start()
    t2.start()
    t3.start()
    t4.start()

def send_startup_ping():
    cfg = load_config()
    msg = f"برنامه اصلی مودو بازلر شروع شد.\n# {now_utc_str()} UTC"
    if cfg.get("chat_id_1h"):
        bot_1h.send_message(cfg["chat_id_1h"], msg)
    if cfg.get("chat_id_4h"):
        bot_4h.send_message(cfg["chat_id_4h"], msg)
    if cfg.get("chat_id_1d"):
        bot_1d.send_message(cfg["chat_id_1d"], msg)
    if cfg.get("chat_id_15m"):
        bot_15m.send_message(cfg["chat_id_15m"], msg)

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    start_threads()
    send_startup_ping()

    # polling for all bots in separate threads
    threading.Thread(target=bot_1h.infinity_polling, daemon=True).start()
    threading.Thread(target=bot_4h.infinity_polling, daemon=True).start()
    threading.Thread(target=bot_1d.infinity_polling, daemon=True).start()
    threading.Thread(target=bot_15m.infinity_polling, daemon=True).start()

    # keep main thread alive
    while True:
        time.sleep(60)