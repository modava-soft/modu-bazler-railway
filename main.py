# -*- coding: utf-8 -*-
# Modu Bazler – main.py (refreshed version)

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

# =========================================================
# مسیرها و تنظیمات پایه
# =========================================================

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
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT",
        "DOTUSDT","MATICUSDT","LTCUSDT","TRXUSDT","AVAXUSDT","LINKUSDT",
        "ATOMUSDT","XMRUSDT","ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT",
        "OPUSDT","ARBUSDT","SUIUSDT","PEPEUSDT","TONUSDT","UNIUSDT","AAVEUSDT",
        "INJUSDT","RNDRUSDT","FTMUSDT","NEOUSDT","GALAUSDT","SEIUSDT","TIAUSDT",
        "PYTHUSDT","JTOUSDT","WIFUSDT","JUPUSDT","STRKUSDT","BLURUSDT","RUNEUSDT",
        "RAYUSDT","LDOUSDT","COMPUSDT","CRVUSDT","MKRUSDT","SNXUSDT","GMXUSDT",
        "DYDXUSDT","ENSUSDT"
    ],

    "hourly_interval":   "1h",
    "fourh_interval":    "4h",
    "daily_interval":    "1d",
    "fifteenm_interval": "15m",

    "hourly_lookback_days":   5,
    "fourh_lookback_days":    15,
    "daily_lookback_days":    180,
    "fifteenm_lookback_days": 3,

    "max_bars": 300,

    "alarm_wma_direction":      True,
    "alarm_cross_sma20":        False,
    "alarm_cross_sma100":       False,
    "alarm_cross_sma200":       False,
    "alarm_sma20_direction":    False,
    "alarm_sma100_direction":   False,
    "alarm_sma200_direction":   False,

    "make_pdf": False,

    "chat_id_1h":   None,
    "chat_id_4h":   None,
    "chat_id_1d":   None,
    "chat_id_15m":  None,

    # واچ‌لیست‌ها برای هر ربات
    "watchlist_1h":   [],
    "watchlist_4h":   [],
    "watchlist_1d":   [],
    "watchlist_15m":  [],

    # چت مقصد برای ارسال آلارم واچ‌لیست (مثلاً ربات ترید)
    "watchlist_target_chat_1h":   None,
    "watchlist_target_chat_4h":   None,
    "watchlist_target_chat_1d":   None,
    "watchlist_target_chat_15m":  None
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

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

# =========================================================
# توکن‌ها و ساخت ربات‌ها
# =========================================================

TOKEN_1H   = (os.getenv("TOKEN_1H")   or "").strip()
TOKEN_4H   = (os.getenv("TOKEN_4H")   or "").strip()
TOKEN_1D   = (os.getenv("TOKEN_1D")   or "").strip()
TOKEN_15M  = (os.getenv("TOKEN_15M")  or "").strip()
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

bot_1h   = create_bot(TOKEN_1H)
bot_4h   = create_bot(TOKEN_4H)
bot_1d   = create_bot(TOKEN_1D)
bot_15m  = create_bot(TOKEN_15M)

# =========================================================
# متن راهنما
# =========================================================

HELP_TEXT = """مودو بازلر – نسخه رفرنس ارتقا یافته

دستورات:
/start          – شروع و ثبت چت اصلی
/refresh        – ریست منو و وضعیت
/start_cycle    – اجرای فوری سیکل همین تایم‌فریم
/start_cycle_4h – اجرای فوری سیکل 4h
/start_cycle_1d – اجرای فوری سیکل 1d
/start_cycle_15m – اجرای فوری سیکل 15m

دکمه‌ها:
- چک تک‌نماد
- اجرای فوری همین تایم‌فریم
- تست آلارم‌ها
- ریست منو و وضعیت
- شروع سیکل‌ها (اتوماتیک)
- وضعیت لوپ‌ها
- گزارش آلارم‌ها
- تنظیمات پیشرفته
- واچ‌لیست 15m / 1h / 4h / 1d
- بازگشت به منوی اصلی
"""

# =========================================================
# منوها
# =========================================================

def send_main_menu(bot, chat_id, timeframe_label: str):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("چک تک‌نماد", "اجرای فوری همین تایم‌فریم")
    kb.row("تست آلارم‌ها", "ریست منو و وضعیت")
    kb.row("شروع سیکل‌ها", "وضعیت لوپ‌ها")
    kb.row("گزارش آلارم‌ها", "تنظیمات پیشرفته")
    kb.row("واچ‌لیست 15m", "واچ‌لیست 1h")
    kb.row("واچ‌لیست 4h", "واچ‌لیست 1d")
    kb.row("بازگشت به منوی اصلی")
    bot.send_message(chat_id, f"منوی اصلی – {timeframe_label}", reply_markup=kb)

def refresh_menu(bot, chat_id, timeframe_label: str):
    send_main_menu(bot, chat_id, timeframe_label)

# =========================================================
# وضعیت‌ها برای واچ‌لیست
# =========================================================

LAST_ALARMS = []
PENDING_WATCHLIST_ACTION = {
    "1h":   {},
    "4h":   {},
    "1d":   {},
    "15m":  {}
}

def set_pending_watchlist(timeframe: str, chat_id: int):
    PENDING_WATCHLIST_ACTION[timeframe][chat_id] = True

def clear_pending_watchlist(timeframe: str, chat_id: int):
    PENDING_WATCHLIST_ACTION[timeframe].pop(chat_id, None)

def is_pending_watchlist(timeframe: str, chat_id: int) -> bool:
    return PENDING_WATCHLIST_ACTION[timeframe].get(chat_id, False)

# =========================================================
# دریافت داده‌ها
# =========================================================

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

# =========================================================
# اندیکاتورها
# =========================================================

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
    gain  = np.where(delta > 0, delta, 0.0)
    loss  = np.where(delta < 0, -delta, 0.0)
    roll_gain  = pd.Series(gain, index=df.index).rolling(14).mean()
    roll_loss  = pd.Series(loss, index=df.index).rolling(14).mean()
    rs = roll_gain / (roll_loss + 1e-9)
    df["RSI14"] = 100 - (100 / (1 + rs))

    ema12 = df["c"].ewm(span=12, adjust=False).mean()
    ema26 = df["c"].ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"]   = df["MACD"] - df["MACD_signal"]

    return df

# =========================================================
# ساخت چارت
# =========================================================

def create_plotly_chart(symbol: str, interval: str,
                        lookback_days: int, max_bars: int,
                        png_name: str, html_name: str) -> dict:

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
            open=df["o"], high=df["h"],
            low=df["l"], close=df["c"],
            name="Price"
        ),
        row=1, col=1
    )

    # SMA
    fig.add_trace(
        go.Scatter(x=df.index, y=df["SMA20"], mode="lines",
                   name="SMA20", line=dict(color="blue")),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["SMA100"], mode="lines",
                   name="SMA100", line=dict(color="orange")),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["SMA200"], mode="lines",
                   name="SMA200", line=dict(color="purple")),
        row=1, col=1
    )

    # WMA20 رنگی
    wma    = df["WMA20"]
    slope  = df["WMA20_slope"]
    wma_up   = wma.where(slope >= 0)
    wma_down = wma.where(slope < 0)

    fig.add_trace(
        go.Scatter(x=df.index, y=wma_up, mode="lines",
                   name="WMA20 Up",
                   line=dict(color="green", width=2, dash="dot")),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=wma_down, mode="lines",
                   name="WMA20 Down",
                   line=dict(color="red", width=2, dash="dot")),
        row=1, col=1
    )

    # RSI
    fig.add_trace(
        go.Scatter(x=df.index, y=df["RSI14"], mode="lines",
                   name="RSI14", line=dict(color="brown")),
        row=2, col=1
    )
    fig.add_hline(y=70, line=dict(color="red", dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="green", dash="dash"), row=2, col=1)

    # MACD
    fig.add_trace(
        go.Scatter(x=df.index, y=df["MACD"], mode="lines",
                   name="MACD", line=dict(color="black")),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["MACD_signal"], mode="lines",
                   name="Signal", line=dict(color="magenta")),
        row=3, col=1
    )
    fig.add_trace(
        go.Bar(x=df.index, y=df["MACD_hist"],
               name="Hist", marker_color="gray"),
        row=3, col=1
    )

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
        "symbol":   symbol,
        "interval": interval,
        "png_path": png_path,
        "html_path": html_path,
        "df": df
    }

# =========================================================
# تشخیص آلارم‌ها
# =========================================================

def detect_alarms(cfg: dict, symbol: str, interval: str, df: pd.DataFrame) -> list:
    alarms = []
    if df.empty or len(df) < 5:
        return alarms

    last = df.iloc[-1]

    if cfg.get("alarm_wma_direction", False):
        slope = last.get("WMA20_slope", 0)
        if slope > 0:
            alarms.append("WMA20 رو به بالا")
        elif slope < 0:
            alarms.append("WMA20 رو به پایین")

    if cfg.get("alarm_cross_sma20", False):
        if not pd.isna(last["WMA20"]) and not pd.isna(last["SMA20"]):
            if last["WMA20"] > last["SMA20"]:
                alarms.append("برخورد WMA20 به بالای SMA20")
            elif last["WMA20"] < last["SMA20"]:
                alarms.append("برخورد WMA20 به پایین SMA20")

    if cfg.get("alarm_cross_sma100", False):
        if not pd.isna(last["WMA20"]) and not pd.isna(last["SMA100"]):
            if last["WMA20"] > last["SMA100"]:
                alarms.append("برخورد WMA20 به بالای SMA100")
            elif last["WMA20"] < last["SMA100"]:
                alarms.append("برخورد WMA20 به پایین SMA100")

    if cfg.get("alarm_cross_sma200", False):
        if not pd.isna(last["WMA20"]) and not pd.isna(last["SMA200"]):
            if last["WMA20"] > last["SMA200"]:
                alarms.append("برخورد WMA20 به بالای SMA200")
            elif last["WMA20"] < last["SMA200"]:
                alarms.append("برخورد WMA20 به پایین SMA200")

    if cfg.get("alarm_sma20_direction", False):
        if not pd.isna(last["SMA20"]):
            prev = df.iloc[-2]
            if last["SMA20"] > prev["SMA20"]:
                alarms.append("شیب SMA20 رو به بالا")
            elif last["SMA20"] < prev["SMA20"]:
                alarms.append("شیب SMA20 رو به پایین")

    if cfg.get("alarm_sma100_direction", False):
        if not pd.isna(last["SMA100"]):
            prev = df.iloc[-2]
            if last["SMA100"] > prev["SMA100"]:
                alarms.append("شیب SMA100 رو به بالا")
            elif last["SMA100"] < prev["SMA100"]:
                alarms.append("شیب SMA100 رو به پایین")

    if cfg.get("alarm_sma200_direction", False):
        if not pd.isna(last["SMA200"]):
            prev = df.iloc[-2]
            if last["SMA200"] > prev["SMA200"]:
                alarms.append("شیب SMA200 رو به بالا")
            elif last["SMA200"] < prev["SMA200"]:
                alarms.append("شیب SMA200 رو به پایین")

    return alarms

# =========================================================
# اجرای سیکل
# =========================================================

def run_cycle(timeframe_key: str, bot, chat_id: int,
              symbols: list, interval: str,
              lookback_days: int, max_bars: int,
              cfg: dict):

    if not bot or not chat_id:
        return

    start_time = now_utc()
    bot.send_message(
        chat_id,
        f"لوپ {interval}: شروع سیکل خودکار.\n"
        f"زمان شروع: 🕰 {start_time.strftime('%H:%M:%S %d-%m-%Y')}\n"
        f"زمان تقریبی پردازش: ⏳ حدود {len(symbols)*6} ثانیه\n"
        f"تعداد نمادها: 📅 {len(symbols)}"
    )

    global LAST_ALARMS
    cycle_alarms = []

    for idx, sym in enumerate(symbols, start=1):
        bot.send_message(
            chat_id,
            f"در حال بررسی 🔍 {sym} ({idx}/{len(symbols)}) در سیکل {interval}..."
        )

        png_name  = f"{sym}_{interval}.png"
        html_name = f"{sym}_{interval}.html"

        try:
            chart_info = create_plotly_chart(
                sym, interval, lookback_days, max_bars,
                png_name, html_name
            )
            df = chart_info["df"]
            alarms = detect_alarms(cfg, sym, interval, df)

            if alarms:
                cycle_alarms.append({
                    "symbol": sym,
                    "interval": interval,
                    "alarms": alarms
                })

                caption = f"{sym} – {interval}\n" + "\n".join(f"- {a}" for a in alarms)
            else:
                caption = f"{sym} – {interval}\nبدون آلارم خاص."

            with open(chart_info["png_path"], "rb") as f:
                bot.send_photo(chat_id, f, caption=caption)

            # اگر در واچ‌لیست است و آلارم دارد، به ربات دیگر پیام بده
            wl_key = f"watchlist_{timeframe_key}"
            target_key = f"watchlist_target_chat_{timeframe_key}"
            watchlist = cfg.get(wl_key, [])
            target_chat = cfg.get(target_key)

            if alarms and sym in watchlist and target_chat:
                text = f"آلارم واچ‌لیست {interval} برای {sym}:\n" + "\n".join(f"- {a}" for a in alarms)
                try:
                    bot.send_message(int(target_chat), text)
                except:
                    pass

        except Exception as e:
            bot.send_message(chat_id, f"خطا در پردازش {sym}: {e}")

    LAST_ALARMS = cycle_alarms[-50:]

    bot.send_message(
        chat_id,
        f"سیکل {interval} پایان یافت. زمان پایان: {now_utc_str()}"
    )

# =========================================================
# هندلرهای ربات 1h
# =========================================================

if bot_1h:

    @bot_1h.message_handler(commands=["start"])
    def start_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, HELP_TEXT)
        refresh_menu(bot_1h, m.chat.id, "1h")

    @bot_1h.message_handler(commands=["refresh"])
    def refresh_1h_cmd(m):
        refresh_menu(bot_1h, m.chat.id, "1h")

    @bot_1h.message_handler(commands=["start_cycle"])
    def start_cycle_1h_cmd(m):
        cfg = load_config()
        run_cycle(
            "1h",
            bot_1h,
            cfg.get("chat_id_1h") or m.chat.id,
            cfg["hourly_symbols"],
            cfg["hourly_interval"],
            cfg["hourly_lookback_days"],
            cfg["max_bars"],
            cfg
        )

    @bot_1h.message_handler(func=lambda m: m.text == "چک تک‌نماد")
    def check_symbol_1h(m):
        bot_1h.send_message(m.chat.id, "نماد را ارسال کنید (مثال: BTCUSDT):")

    @bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری همین تایم‌فریم")
    def manual_1h(m):
        cfg = load_config()
        run_cycle(
            "1h",
            bot_1h,
            cfg.get("chat_id_1h") or m.chat.id,
            cfg["hourly_symbols"],
            cfg["hourly_interval"],
            cfg["hourly_lookback_days"],
            cfg["max_bars"],
            cfg
        )

    @bot_1h.message_handler(func=lambda m: m.text == "تست آلارم‌ها")
    def alarms_menu_1h(m):
        bot_1h.send_message(m.chat.id, "تست آلارم‌ها در این نسخه فقط در سیکل‌ها انجام می‌شود.")

    @bot_1h.message_handler(func=lambda m: m.text == "ریست منو و وضعیت")
    def reset_menu_1h(m):
        cfg = load_config()
        cfg["hourly_symbols"] = DEFAULT_CONFIG["hourly_symbols"]
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "لیست نمادهای 1h به حالت پیش‌فرض ریست شد.")
        refresh_menu(bot_1h, m.chat.id, "1h")

    @bot_1h.message_handler(func=lambda m: m.text == "شروع سیکل‌ها")
    def start_cycles_1h(m):
        cfg = load_config()
        bot_1h.send_message(m.chat.id, "سیکل خودکار 1h به صورت دستی اجرا می‌شود.")
        run_cycle(
            "1h",
            bot_1h,
            cfg.get("chat_id_1h") or m.chat.id,
            cfg["hourly_symbols"],
            cfg["hourly_interval"],
            cfg["hourly_lookback_days"],
            cfg["max_bars"],
            cfg
        )

    @bot_1h.message_handler(func=lambda m: m.text == "وضعیت لوپ‌ها")
    def system_status_1h(m):
        bot_1h.send_message(m.chat.id, f"لوپ 1h آماده اجرا است.\nزمان فعلی: {now_utc_str()}")

    @bot_1h.message_handler(func=lambda m: m.text == "گزارش آلارم‌ها")
    def alarms_report_1h(m):
        if not LAST_ALARMS:
            bot_1h.send_message(m.chat.id, "فعلاً آلارمی ثبت نشده است.")
            return
        txt = "آخرین آلارم‌ها:\n\n"
        for item in LAST_ALARMS[-20:]:
            txt += f"{item['symbol']} ({item['interval']}):\n"
            for a in item["alarms"]:
                txt += f"  - {a}\n"
            txt += "\n"
        bot_1h.send_message(m.chat.id, txt)

    @bot_1h.message_handler(func=lambda m: m.text == "تنظیمات پیشرفته")
    def advanced_settings_1h(m):
        bot_1h.send_message(m.chat.id, "تنظیمات پیشرفته در این نسخه به صورت دستی در فایل config.json قابل ویرایش است.")

    @bot_1h.message_handler(func=lambda m: m.text == "واچ‌لیست 1h")
    def watchlist_1h_btn(m):
        cfg = load_config()
        wl = cfg.get("watchlist_1h", [])
        bot_1h.send_message(
            m.chat.id,
            "نماد را برای اضافه شدن به واچ‌لیست 1h ارسال کنید.\n"
            f"لیست فعلی: {', '.join(wl) if wl else 'خالی'}"
        )
        set_pending_watchlist("1h", m.chat.id)

    @bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
    def back_to_main_1h(m):
        refresh_menu(bot_1h, m.chat.id, "1h")

    @bot_1h.message_handler(func=lambda m: True)
    def generic_1h(m):
        cfg = load_config()
        chat_id = m.chat.id

        if is_pending_watchlist("1h", chat_id):
            sym = m.text.strip().upper()
            wl = cfg.get("watchlist_1h", [])
            if sym not in wl:
                wl.append(sym)
                cfg["watchlist_1h"] = wl
                save_config(cfg)
                bot_1h.send_message(chat_id, f"{sym} به واچ‌لیست 1h اضافه شد.")
            else:
                bot_1h.send_message(chat_id, f"{sym} قبلاً در واچ‌لیست 1h بوده است.")
            clear_pending_watchlist("1h", chat_id)
            return

        # اگر متن نماد باشد، چارت تک‌نماد
        if len(m.text.strip()) >= 6 and m.text.strip().isalpha():
            sym = m.text.strip().upper()
            png_name  = f"{sym}_1h_single.png"
            html_name = f"{sym}_1h_single.html"
            try:
                chart_info = create_plotly_chart(
                    sym, cfg["hourly_interval"],
                    cfg["hourly_lookback_days"],
                    cfg["max_bars"],
                    png_name, html_name
                )
                with open(chart_info["png_path"], "rb") as f:
                    bot_1h.send_photo(chat_id, f, caption=f"نمودار 1h – {sym}")
            except Exception as e:
                bot_1h.send_message(chat_id, f"خطا در ساخت نمودار {sym}: {e}")

# =========================================================
# هندلرهای ربات 4h
# =========================================================

if bot_4h:

    @bot_4h.message_handler(commands=["start"])
    def start_4h(m):
        cfg = load_config()
        cfg["chat_id_4h"] = m.chat.id
        save_config(cfg)
        bot_4h.send_message(m.chat.id, "ربات 4h فعال شد و این چت بعنوان چت اصلی سیکل 4h ثبت شد.")
        refresh_menu(bot_4h, m.chat.id, "4h")

    @bot_4h.message_handler(commands=["start_cycle_4h"])
    def start_cycle_4h_cmd(m):
        cfg = load_config()
        run_cycle(
            "4h",
            bot_4h,
            cfg.get("chat_id_4h") or m.chat.id,
            cfg["fourh_symbols"],
            cfg["fourh_interval"],
            cfg["fourh_lookback_days"],
            cfg["max_bars"],
            cfg
        )

    @bot_4h.message_handler(func=lambda m: m.text == "ریست منو و وضعیت")
    def reset_menu_4h(m):
        cfg = load_config()
        cfg["fourh_symbols"] = DEFAULT_CONFIG["fourh_symbols"]
        save_config(cfg)
        bot_4h.send_message(m.chat.id, "لیست نمادهای 4h به حالت پیش‌فرض ریست شد.")
        refresh_menu(bot_4h, m.chat.id, "4h")

    @bot_4h.message_handler(func=lambda m: m.text == "اجرای فوری همین تایم‌فریم")
    def manual_4h(m):
        cfg = load_config()
        run_cycle(
            "4h",
            bot_4h,
            cfg.get("chat_id_4h") or m.chat.id,
            cfg["fourh_symbols"],
            cfg["fourh_interval"],
            cfg["fourh_lookback_days"],
            cfg["max_bars"],
            cfg
        )

    @bot_4h.message_handler(func=lambda m: m.text == "واچ‌لیست 4h")
    def watchlist_4h_btn(m):
        cfg = load_config()
        wl = cfg.get("watchlist_4h", [])
        bot_4h.send_message(
            m.chat.id,
            "نماد را برای اضافه شدن به واچ‌لیست 4h ارسال کنید.\n"
            f"لیست فعلی: {', '.join(wl) if wl else 'خالی'}"
        )
        set_pending_watchlist("4h", m.chat.id)

    @bot_4h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
    def back_to_main_4h(m):
        refresh_menu(bot_4h, m.chat.id, "4h")

    @bot_4h.message_handler(func=lambda m: True)
    def generic_4h(m):
        cfg = load_config()
        chat_id = m.chat.id

        if is_pending_watchlist("4h", chat_id):
            sym = m.text.strip().upper()
            wl = cfg.get("watchlist_4h", [])
            if sym not in wl:
                wl.append(sym)
                cfg["watchlist_4h"] = wl
                save_config(cfg)
                bot_4h.send_message(chat_id, f"{sym} به واچ‌لیست 4h اضافه شد.")
            else:
                bot_4h.send_message(chat_id, f"{sym} قبلاً در واچ‌لیست 4h بوده است.")
            clear_pending_watchlist("4h", chat_id)
            return

# =========================================================
# هندلرهای ربات 1d
# =========================================================

if bot_1d:

    @bot_1d.message_handler(commands=["start"])
    def start_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        bot_1d.send_message(m.chat.id, "ربات 1d فعال شد و این چت بعنوان چت اصلی سیکل 1d ثبت شد.")
        refresh_menu(bot_1d, m.chat.id, "1d")

    @bot_1d.message_handler(commands=["start_cycle_1d"])
    def start_cycle_1d_cmd(m):
        cfg = load_config()
        run_cycle(
            "1d",
            bot_1d,
            cfg.get("chat_id_1d") or m.chat.id,
            cfg["daily_symbols"],
            cfg["daily_interval"],
            cfg["daily_lookback_days"],
            cfg["max_bars"],
            cfg
        )

    @bot_1d.message_handler(func=lambda m: m.text == "ریست منو و وضعیت")
    def reset_menu_1d(m):
        cfg = load_config()
        cfg["daily_symbols"] = DEFAULT_CONFIG["daily_symbols"]
        save_config(cfg)
        bot_1d.send_message(m.chat.id, "لیست نمادهای 1d به حالت پیش‌فرض ریست شد.")
        refresh_menu(bot_1d, m.chat.id, "1d")

    @bot_1d.message_handler(func=lambda m: m.text == "اجرای فوری همین تایم‌فریم")
    def manual_1d(m):
        cfg = load_config()
        run_cycle(
            "1d",
            bot_1d,
            cfg.get("chat_id_1d") or m.chat.id,
            cfg["daily_symbols"],
            cfg["daily_interval"],
            cfg["daily_lookback_days"],
            cfg["max_bars"],
            cfg
        )

    @bot_1d.message_handler(func=lambda m: m.text == "واچ‌لیست 1d")
    def watchlist_1d_btn(m):
        cfg = load_config()
        wl = cfg.get("watchlist_1d", [])
        bot_1d.send_message(
            m.chat.id,
            "نماد را برای اضافه شدن به واچ‌لیست 1d ارسال کنید.\n"
            f"لیست فعلی: {', '.join(wl) if wl else 'خالی'}"
        )
        set_pending_watchlist("1d", m.chat.id)

    @bot_1d.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
    def back_to_main_1d(m):
        refresh_menu(bot_1d, m.chat.id, "1d")

    @bot_1d.message_handler(func=lambda m: True)
    def generic_1d(m):
        cfg = load_config()
        chat_id = m.chat.id

        if is_pending_watchlist("1d", chat_id):
            sym = m.text.strip().upper()
            wl = cfg.get("watchlist_1d", [])
            if sym not in wl:
                wl.append(sym)
                cfg["watchlist_1d"] = wl
                save_config(cfg)
                bot_1d.send_message(chat_id, f"{sym} به واچ‌لیست 1d اضافه شد.")
            else:
                bot_1d.send_message(chat_id, f"{sym} قبلاً در واچ‌لیست 1d بوده است.")
            clear_pending_watchlist("1d", chat_id)
            return

# =========================================================
# هندلرهای ربات 15m
# =========================================================

if bot_15m:

    @bot_15m.message_handler(commands=["start"])
    def start_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        bot_15m.send_message(m.chat.id, "ربات 15m فعال شد و این چت بعنوان چت اصلی سیکل 15m ثبت شد.")
        refresh_menu(bot_15m, m.chat.id, "15m")

    @bot_15m.message_handler(commands=["start_cycle_15m"])
    def start_cycle_15m_cmd(m):
        cfg = load_config()
        run_cycle(
            "15m",
            bot_15m,
            cfg.get("chat_id_15m") or m.chat.id,
            cfg["fifteenm_symbols"],
            cfg["fifteenm_interval"],
            cfg["fifteenm_lookback_days"],
            cfg["max_bars"],
            cfg
        )

    @bot_15m.message_handler(func=lambda m: m.text == "ریست منو و وضعیت")
    def reset_menu_15m(m):
        cfg = load_config()
        cfg["fifteenm_symbols"] = DEFAULT_CONFIG["fifteenm_symbols"]
        save_config(cfg)
        bot_15m.send_message(m.chat.id, "لیست نمادهای 15m به حالت پیش‌فرض ریست شد.")
        refresh_menu(bot_15m, m.chat.id, "15m")

    @bot_15m.message_handler(func=lambda m: m.text == "اجرای فوری همین تایم‌فریم")
    def manual_15m(m):
        cfg = load_config()
        run_cycle(
            "15m",
            bot_15m,
            cfg.get("chat_id_15m") or m.chat.id,
            cfg["fifteenm_symbols"],
            cfg["fifteenm_interval"],
            cfg["fifteenm_lookback_days"],
            cfg["max_bars"],
            cfg
        )

    @bot_15m.message_handler(func=lambda m: m.text == "واچ‌لیست 15m")
    def watchlist_15m_btn(m):
        cfg = load_config()
        wl = cfg.get("watchlist_15m", [])
        bot_15m.send_message(
            m.chat.id,
            "نماد را برای اضافه شدن به واچ‌لیست 15m ارسال کنید.\n"
            f"لیست فعلی: {', '.join(wl) if wl else 'خالی'}"
        )
        set_pending_watchlist("15m", m.chat.id)

    @bot_15m.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
    def back_to_main_15m(m):
        refresh_menu(bot_15m, m.chat.id, "15m")

    @bot_15m.message_handler(func=lambda m: True)
    def generic_15m(m):
        cfg = load_config()
        chat_id = m.chat.id

        if is_pending_watchlist("15m", chat_id):
            sym = m.text.strip().upper()
            wl = cfg.get("watchlist_15m", [])
            if sym not in wl:
                wl.append(sym)
                cfg["watchlist_15m"] = wl
                save_config(cfg)
                bot_15m.send_message(chat_id, f"{sym} به واچ‌لیست 15m اضافه شد.")
            else:
                bot_15m.send_message(chat_id, f"{sym} قبلاً در واچ‌لیست 15m بوده است.")
            clear_pending_watchlist("15m", chat_id)
            return

# =========================================================
# اجرای ربات‌ها
# =========================================================

def run_all_bots():
    threads = []
    if bot_1h:
        threads.append(threading.Thread(target=bot_1h.infinity_polling, name="bot_1h"))
    if bot_4h:
        threads.append(threading.Thread(target=bot_4h.infinity_polling, name="bot_4h"))
    if bot_1d:
        threads.append(threading.Thread(target=bot_1d.infinity_polling, name="bot_1d"))
    if bot_15m:
        threads.append(threading.Thread(target=bot_15m.infinity_polling, name="bot_15m"))

    for t in threads:
        t.daemon = True
        t.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    run_all_bots()