# -*- coding: utf-8 -*-
# Modu Bazler – Watchlist Pro v3 (نسخه کامل main.py)

import os, json, time, threading, datetime as dt
import requests, numpy as np, pandas as pd
import telebot
from telebot import types

# =========================
# مسیرها و ساخت پوشه‌ها
# =========================

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
HTML_DIR   = os.path.join(DATA_DIR, "html")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, HTML_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

# =========================
# لیست ۵۰ ارز بزرگ بازار
# =========================

TOP50 = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","TONUSDT",
    "AVAXUSDT","DOTUSDT","TRXUSDT","LINKUSDT","MATICUSDT","LTCUSDT","XLMUSDT","ETCUSDT",
    "XMRUSDT","FILUSDT","APTUSDT","NEARUSDT","OPUSDT","ARBUSDT","SUIUSDT","PEPEUSDT",
    "UNIUSDT","AAVEUSDT","INJUSDT","RNDRUSDT","FTMUSDT","NEOUSDT","GALAUSDT","SEIUSDT",
    "TIAUSDT","PYTHUSDT","JTOUSDT","WIFUSDT","JUPUSDT","STRKUSDT","BLURUSDT","RUNEUSDT",
    "RAYUSDT","LDOUSDT","COMPUSDT","CRVUSDT","MKRUSDT","SNXUSDT","GMXUSDT","DYDXUSDT","ENSUSDT"
]

# =========================
# کانفیگ جدید
# =========================

DEFAULT_CONFIG = {
    "initial_symbols": TOP50,

    "hourly_symbols": [],
    "fourh_symbols": [],
    "daily_symbols": [],
    "fifteenm_symbols": [],

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
    "alarm_sma20_direction": True,
    "alarm_sma100_direction": True,
    "alarm_sma200_direction": True,

    "make_pdf": True,

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,

    "watchlist_enabled_15m": True,
    "watchlist_enabled_1h": True,
    "watchlist_enabled_4h": True,
    "watchlist_enabled_1d": True,
}

# =========================
# ذخیره و بارگذاری کانفیگ
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

# =========================
# ساخت ربات‌ها
# =========================

TOKEN_1H   = (os.getenv("TOKEN_1H") or "").strip()
TOKEN_4H   = (os.getenv("TOKEN_4H") or "").strip()
TOKEN_1D   = (os.getenv("TOKEN_1D") or "").strip()
TOKEN_15M  = (os.getenv("TOKEN_15M") or "").strip()
ADMIN_CHAT = (os.getenv("ADMIN_CHAT_ID") or "").strip()

def create_bot(token):
    if not token:
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
# State برای ۴ ربات
# =========================

STATE = {
    "1h": {},
    "4h": {},
    "1d": {},
    "15m": {}
}

# =========================
# منوی InlineKeyboard تک‌صفحه‌ای
# =========================

def main_menu_inline():
    kb = types.InlineKeyboardMarkup()

    kb.add(types.InlineKeyboardButton("چک تک‌نماد", callback_data="check_single"))
    kb.add(types.InlineKeyboardButton("نمودار تک‌نماد", callback_data="chart_single"))
    kb.add(types.InlineKeyboardButton("نمایش لیست ارزها", callback_data="show_lists"))
    kb.add(types.InlineKeyboardButton("واچ‌لیست‌ها", callback_data="watchlists"))
    kb.add(types.InlineKeyboardButton("شروع چرخه‌ها", callback_data="start_cycles"))
    kb.add(types.InlineKeyboardButton("اجرای فوری ۱h", callback_data="run_1h_now"))
    kb.add(types.InlineKeyboardButton("صفر کردن واچ‌لیست‌ها", callback_data="clear_watchlists"))
    kb.add(types.InlineKeyboardButton("تنظیم آلارم‌ها", callback_data="alarms"))
    kb.add(types.InlineKeyboardButton("تنظیمات پیشرفته", callback_data="advanced"))
    kb.add(types.InlineKeyboardButton("ریست", callback_data="reset"))
    kb.add(types.InlineKeyboardButton("بازگشت", callback_data="back"))

    return kb

def send_inline_menu(bot, chat_id):
    bot.send_message(chat_id, "منوی اصلی:", reply_markup=main_menu_inline())

# =========================
# هندلرهای مشترک برای هر ربات
# =========================

def register_handlers(bot, bot_name):

    @bot.message_handler(commands=["start"])
    def start_cmd(m):
        cfg = load_config()
        cfg[f"chat_id_{bot_name}"] = m.chat.id
        save_config(cfg)
        send_inline_menu(bot, m.chat.id)

    @bot.callback_query_handler(func=lambda c: True)
    def callback_router(c):

        data = c.data
        chat_id = c.message.chat.id

        # -------------------------
        # بازگشت
        # -------------------------
        if data == "back":
            STATE[bot_name][chat_id] = None
            bot.answer_callback_query(c.id)
            send_inline_menu(bot, chat_id)
            return

        # -------------------------
        # ریست
        # -------------------------
        if data == "reset":
            STATE[bot_name][chat_id] = None
            bot.answer_callback_query(c.id)
            send_inline_menu(bot, chat_id)
            return

        # -------------------------
        # نمایش لیست ارزها
        # -------------------------
        if data == "show_lists":
            cfg = load_config()
            txt = "📄 لیست ارزهای بررسی:\n\n"
            txt += ", ".join(cfg["initial_symbols"])
            bot.send_message(chat_id, txt)
            bot.answer_callback_query(c.id)
            return

        # -------------------------
        # صفر کردن واچ‌لیست‌ها
        # -------------------------
        if data == "clear_watchlists":
            cfg = load_config()
            cfg["hourly_symbols"] = []
            cfg["fourh_symbols"] = []
            cfg["daily_symbols"] = []
            cfg["fifteenm_symbols"] = []
            save_config(cfg)
            bot.send_message(chat_id, "✔ واچ‌لیست‌ها صفر شدند.")
            bot.answer_callback_query(c.id)
            return

        # -------------------------
        # چک تک‌نماد
        # -------------------------
        if data == "check_single":
            bot.send_message(chat_id, "نماد را وارد کنید (مثلاً BTCUSDT):")
            STATE[bot_name][chat_id] = "await_single_symbol"
            bot.answer_callback_query(c.id)
            return

        # -------------------------
        # نمودار تک‌نماد
        # -------------------------
        if data == "chart_single":
            bot.send_message(chat_id, "نماد را وارد کنید (مثلاً BTCUSDT):")
            STATE[bot_name][chat_id] = "await_chart_symbol"
            bot.answer_callback_query(c.id)
            return

        # -------------------------
        # واچ‌لیست‌ها
        # -------------------------
        if data == "watchlists":
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("واچ‌لیست 15m", callback_data="wl_15m"))
            kb.add(types.InlineKeyboardButton("واچ‌لیست 1h", callback_data="wl_1h"))
            kb.add(types.InlineKeyboardButton("واچ‌لیست 4h", callback_data="wl_4h"))
            kb.add(types.InlineKeyboardButton("واچ‌لیست 1d", callback_data="wl_1d"))
            kb.add(types.InlineKeyboardButton("بازگشت", callback_data="back"))
            bot.send_message(chat_id, "واچ‌لیست مورد نظر را انتخاب کنید:", reply_markup=kb)
            bot.answer_callback_query(c.id)
            return

        # -------------------------
        # مدیریت واچ‌لیست انتخاب‌شده
        # -------------------------
        if data.startswith("wl_"):
            tf = data.split("_")[1]
            key_map = {
                "15m": ("fifteenm_symbols", "watchlist_enabled_15m"),
                "1h": ("hourly_symbols", "watchlist_enabled_1h"),
                "4h": ("fourh_symbols", "watchlist_enabled_4h"),
                "1d": ("daily_symbols", "watchlist_enabled_1d"),
            }
            sym_key, flag_key = key_map[tf]
            cfg = load_config()
            syms = cfg[sym_key]
            enabled = cfg[flag_key]

            txt = f"واچ‌لیست {tf}:\n\n"
            txt += (", ".join(syms) if syms else "خالی") + "\n\n"
            txt += f"آلارم: {'روشن' if enabled else 'خاموش'}\n\n"
            txt += "➕ افزودن نماد: ارسال نماد\n"
            txt += "➖ حذف نماد: ارسال -BTCUSDT\n"
            txt += "🔔 روشن/خاموش: ارسال «روشن» یا «خاموش»\n"

            STATE[bot_name][chat_id] = ("edit_watchlist", sym_key, flag_key)

            bot.send_message(chat_id, txt)
            bot.answer_callback_query(c.id)
            return

        # -------------------------
        # شروع چرخه‌ها
        # -------------------------
        if data == "start_cycles":
            STATE[bot_name][chat_id] = "start_cycles"
            bot.send_message(chat_id, "⏳ شروع چرخه‌ها...")
            bot.answer_callback_query(c.id)
            return

        # -------------------------
        # اجرای فوری ۱h
        # -------------------------
        if data == "run_1h_now":
            STATE[bot_name][chat_id] = "run_1h_now"
            bot.send_message(chat_id, "⏳ اجرای فوری سیکل ۱h...")
            bot.answer_callback_query(c.id)
            return

        # -------------------------
        # تنظیم آلارم‌ها
        # -------------------------
        if data == "alarms":
            bot.send_message(chat_id, "تنظیم آلارم‌ها فعلاً از طریق فایل config.json انجام می‌شود.")
            bot.answer_callback_query(c.id)
            return

        # -------------------------
        # تنظیمات پیشرفته
        # -------------------------
        if data == "advanced":
            bot.send_message(chat_id, "تنظیمات پیشرفته فعلاً از طریق فایل config.json انجام می‌شود.")
            bot.answer_callback_query(c.id)
            return

    # =========================
    # هندلر پیام‌ها
    # =========================

    @bot.message_handler(func=lambda m: True)
    def msg_router(m):
        chat_id = m.chat.id
        state = STATE[bot_name].get(chat_id)

        # -------------------------
        # افزودن/حذف نماد در واچ‌لیست
        # -------------------------
        if isinstance(state, tuple) and state[0] == "edit_watchlist":
            sym_key, flag_key = state[1], state[2]
            cfg = load_config()
            text = m.text.strip().upper()

            if text == "روشن":
                cfg[flag_key] = True
                save_config(cfg)
                bot.send_message(chat_id, "آلارم روشن شد.")
                return

            if text == "خاموش":
                cfg[flag_key] = False
                save_config(cfg)
                bot.send_message(chat_id, "آلارم خاموش شد.")
                return

            syms = cfg[sym_key]

            if text.startswith("-"):
                sym = text[1:]
                if sym in syms:
                    syms.remove(sym)
                    cfg[sym_key] = syms
                    save_config(cfg)
                    bot.send_message(chat_id, f"{sym} حذف شد.")
                else:
                    bot.send_message(chat_id, f"{sym} وجود ندارد.")
                return

            sym = text
            if sym not in syms:
                syms.append(sym)
                cfg[sym_key] = syms
                save_config(cfg)
                bot.send_message(chat_id, f"{sym} اضافه شد.")
            else:
                bot.send_message(chat_id, f"{sym} قبلاً وجود دارد.")
            return

        # -------------------------
        # چک تک‌نماد
        # -------------------------
        if state == "await_single_symbol":
            STATE[bot_name][chat_id] = ("single_symbol", m.text.strip().upper())
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("TF 15m", callback_data="tf_15m_single"))
            kb.add(types.InlineKeyboardButton("TF 1h", callback_data="tf_1h_single"))
            kb.add(types.InlineKeyboardButton("TF 4h", callback_data="tf_4h_single"))
            kb.add(types.InlineKeyboardButton("TF 1d", callback_data="tf_1d_single"))
            bot.send_message(chat_id, "تایم‌فریم را انتخاب کنید:", reply_markup=kb)
            return

        # -------------------------
        # نمودار تک‌نماد
        # -------------------------
        if state == "await_chart_symbol":
            STATE[bot_name][chat_id] = ("chart_symbol", m.text.strip().upper())
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("TF 15m", callback_data="tf_15m_chart"))
            kb.add(types.InlineKeyboardButton("TF 1h", callback_data="tf_1h_chart"))
            kb.add(types.InlineKeyboardButton("TF 4h", callback_data="tf_4h_chart"))
            kb.add(types.InlineKeyboardButton("TF 1d", callback_data="tf_1d_chart"))
            bot.send_message(chat_id, "تایم‌فریم نمودار را انتخاب کنید:", reply_markup=kb)
            return

        # -------------------------
        # اجرای فوری چرخه‌ها
        # -------------------------
        if state == "start_cycles":
            bot.send_message(chat_id, "🚀 چرخه‌ها در بخش ۳ اجرا خواهند شد.")
            STATE[bot_name][chat_id] = None
            return

        # -------------------------
        # اجرای فوری ۱h
        # -------------------------
        if state == "run_1h_now":
            bot.send_message(chat_id, "🚀 سیکل ۱h در بخش ۳ اجرا خواهد شد.")
            STATE[bot_name][chat_id] = None
            return



# =========================
# بخش ۲ — نمودار + چک تک‌نماد + آلارم‌ها
# =========================

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# =========================
# زمان
# =========================

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

# =========================
# تبدیل تایم‌فریم برای API
# =========================

def _binance_interval(i):
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i):
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

# =========================
# دریافت دیتا
# =========================

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
                int(k[0]), float(k[1]), float(k[2]),
                float(k[3]), float(k[4]), float(k[5])
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

# =========================
# اندیکاتورها
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

# =========================
# ساخت نمودار Plotly
# =========================

def create_plotly_chart(symbol, interval, lookback_days, max_bars, png_name, html_name):

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

    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"],  mode="lines", name="SMA20",  line=dict(color="blue")),   row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA100"], mode="lines", name="SMA100", line=dict(color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], mode="lines", name="SMA200", line=dict(color="purple")), row=1, col=1)

    wma   = df["WMA20"]
    slope = df["WMA20_slope"]
    wma_up   = wma.where(slope >= 0)
    wma_down = wma.where(slope < 0)

    fig.add_trace(go.Scatter(x=df.index, y=wma_up,   mode="lines", name="WMA20 Up",   line=dict(color="green", width=2, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=wma_down, mode="lines", name="WMA20 Down", line=dict(color="red",   width=2, dash="dot")), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], mode="lines", name="RSI14", line=dict(color="brown")), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="red", dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="green", dash="dash"), row=2, col=1)

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
        "wma": df["WMA20"].tolist(),
        "wma_slope": df["WMA20_slope"].tolist(),
        "sma20": df["SMA20"].tolist(),
        "sma100": df["SMA100"].tolist(),
        "sma200": df["SMA200"].tolist()
    }

# =========================
# آلارم‌ها
# =========================

LAST_ALARMS = []

def detect_alarms(cfg, info):
    alarms = []

    wma = info["wma"]
    slope = info["wma_slope"]
    sma20 = info["sma20"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]

    if len(wma) < 3:
        return alarms

    if cfg.get("alarm_wma_direction", True):
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("WMA20 جهت رو به بالا گرفت")
        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("WMA20 جهت رو به پایین گرفت")

    def cross(a, b):
        if len(a) < 2 or len(b) < 2:
            return False
        return (a[-2] - b[-2]) * (a[-1] - b[-1]) < 0

    if cfg.get("alarm_cross_sma20", True) and cross(wma, sma20):
        alarms.append("برخورد WMA20 با SMA20")
    if cfg.get("alarm_cross_sma100", True) and cross(wma, sma100):
        alarms.append("برخورد WMA20 با SMA100")
    if cfg.get("alarm_cross_sma200", True) and cross(wma, sma200):
        alarms.append("برخورد WMA20 با SMA200")

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

    if alarms:
        LAST_ALARMS.append({
            "symbol": info["symbol"],
            "interval": info["interval"],
            "time": info["created_at"],
            "alarms": alarms
        })
        if len(LAST_ALARMS) > 200:
            LAST_ALARMS.pop(0)

    return alarms


# =========================
# بخش ۳ — چرخه‌ها + لوپ‌ها + اجرای نهایی
# =========================

# =========================
# چرخه‌ها (نسخه سبک)
# =========================

def run_cycle(group, bot, chat_id, symbols, interval, lookback_days, max_bars,
              watchlist_enabled=True, notify_bot=None, notify_chat=None):

    bot.send_message(chat_id, f"🔄 شروع سیکل {group}\n⏱ {now_utc_str()}")

    cfg = load_config()

    if isinstance(symbols, str):
        symbols = [symbols]

    unique_symbols = list(dict.fromkeys(symbols))

    cycle_alarms = []

    pdf = None
    if cfg.get("make_pdf", True):
        pdf = PdfPages(os.path.join(PDF_DIR, f"{group}_{now_utc().strftime('%Y%m%d_%H%M%S')}.pdf"))

    for sym in unique_symbols:

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

            if pdf is not None:
                img = plt.imread(info["png_path"])
                fig, ax = plt.subplots(figsize=(10,6))
                ax.imshow(img)
                ax.axis("off")
                ax.set_title(f"{sym} – {group}")
                pdf.savefig(fig)
                plt.close(fig)

            if watchlist_enabled and notify_bot and notify_chat:
                with open(info["png_path"], "rb") as f:
                    notify_bot.send_photo(
                        notify_chat,
                        f,
                        caption=f"🚨 آلارم واچ‌لیست {group}\n{sym}\n" + "\n".join(alarms)
                    )

        time.sleep(1)

    if pdf is not None:
        pdf.close()
        bot.send_message(chat_id, f"📄 فایل PDF چرخه {group} ذخیره شد.")

    if cycle_alarms:
        table = "📊 گزارش آلارم‌های این سیکل:\n\n"
        for item in cycle_alarms:
            table += f"🔹 {item['symbol']} ({item['interval']}):\n"
            for a in item["alarms"]:
                table += f"   • {a}\n"
            table += "\n"
        bot.send_message(chat_id, table)
    else:
        bot.send_message(chat_id, "✔ در این سیکل هیچ آلارمی فعال نشد.")

    bot.send_message(chat_id, f"✅ پایان سیکل {group}\n🔢 تعداد پردازش: {len(unique_symbols)}")


# =========================
# اجرای فوری ۱h
# =========================

def run_1h_now(bot, chat_id):
    cfg = load_config()
    run_cycle(
        "1h",
        bot,
        chat_id,
        cfg["initial_symbols"],
        "1h",
        cfg["hourly_lookback_days"],
        cfg["max_bars"],
        watchlist_enabled=cfg.get("watchlist_enabled_1h", True),
        notify_bot=bot,
        notify_chat=chat_id
    )


# =========================
# اجرای چرخه‌ها با دکمه «شروع چرخه‌ها»
# =========================

def run_all_cycles(bot, chat_id):
    cfg = load_config()

    # 15m
    run_cycle(
        "15m",
        bot,
        chat_id,
        cfg["initial_symbols"],
        "15m",
        cfg["fifteenm_lookback_days"],
        cfg["max_bars"],
        watchlist_enabled=cfg.get("watchlist_enabled_15m", True),
        notify_bot=bot,
        notify_chat=chat_id
    )

    # 1h
    run_cycle(
        "1h",
        bot,
        chat_id,
        cfg["initial_symbols"],
        "1h",
        cfg["hourly_lookback_days"],
        cfg["max_bars"],
        watchlist_enabled=cfg.get("watchlist_enabled_1h", True),
        notify_bot=bot,
        notify_chat=chat_id
    )

    # 4h
    run_cycle(
        "4h",
        bot,
        chat_id,
        cfg["initial_symbols"],
        "4h",
        cfg["fourh_lookback_days"],
        cfg["max_bars"],
        watchlist_enabled=cfg.get("watchlist_enabled_4h", True),
        notify_bot=bot,
        notify_chat=chat_id
    )

    # 1d
    run_cycle(
        "1d",
        bot,
        chat_id,
        cfg["initial_symbols"],
        "1d",
        cfg["daily_lookback_days"],
        cfg["max_bars"],
        watchlist_enabled=cfg.get("watchlist_enabled_1d", True),
        notify_bot=bot,
        notify_chat=chat_id
    )


# =========================
# لوپ‌های زمان‌بندی
# =========================

def loop_1h():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute == 30 and bot_1h and cfg.get("chat_id_1h"):
            run_cycle(
                "1h",
                bot_1h,
                cfg["chat_id_1h"],
                cfg["initial_symbols"],
                "1h",
                cfg["hourly_lookback_days"],
                cfg["max_bars"],
                watchlist_enabled=cfg.get("watchlist_enabled_1h", True),
                notify_bot=bot_1h,
                notify_chat=cfg["chat_id_1h"]
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
                    "4h",
                    bot_4h,
                    cfg["chat_id_4h"],
                    cfg["initial_symbols"],
                    "4h",
                    cfg["fourh_lookback_days"],
                    cfg["max_bars"],
                    watchlist_enabled=cfg.get("watchlist_enabled_4h", True),
                    notify_bot=bot_4h,
                    notify_chat=cfg["chat_id_4h"]
                )
                time.sleep(60)
        time.sleep(20)


def loop_1d():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.hour == 23 and now.minute == 30 and bot_1d and cfg.get("chat_id_1d"):
            run_cycle(
                "1d",
                bot_1d,
                cfg["chat_id_1d"],
                cfg["initial_symbols"],
                "1d",
                cfg["daily_lookback_days"],
                cfg["max_bars"],
                watchlist_enabled=cfg.get("watchlist_enabled_1d", True),
                notify_bot=bot_1d,
                notify_chat=cfg["chat_id_1d"]
            )
            time.sleep(60)
        time.sleep(20)


def loop_15m():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute % 15 == 0 and bot_15m and cfg.get("chat_id_15m"):
            run_cycle(
                "15m",
                bot_15m,
                cfg["chat_id_15m"],
                cfg["initial_symbols"],
                "15m",
                cfg["fifteenm_lookback_days"],
                cfg["max_bars"],
                watchlist_enabled=cfg.get("watchlist_enabled_15m", True),
                notify_bot=bot_15m,
                notify_chat=cfg["chat_id_15m"]
            )
            time.sleep(60)
        time.sleep(20)


# =========================
# اجرای نهایی ربات‌ها
# =========================

if __name__ == "__main__":

    # پیام راه‌اندازی
    if ADMIN_CHAT:
        if bot_1h:
            bot_1h.send_message(ADMIN_CHAT, "ربات 1h راه‌اندازی شد.")
        if bot_4h:
            bot_4h.send_message(ADMIN_CHAT, "ربات 4h راه‌اندازی شد.")
        if bot_1d:
            bot_1d.send_message(ADMIN_CHAT, "ربات 1d راه‌اندازی شد.")
        if bot_15m:
            bot_15m.send_message(ADMIN_CHAT, "ربات 15m راه‌اندازی شد.")

    # ثبت هندلرها
    if bot_1h:
        register_handlers(bot_1h, "1h")
        threading.Thread(target=bot_1h.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_1h, daemon=True).start()

    if bot_4h:
        register_handlers(bot_4h, "4h")
        threading.Thread(target=bot_4h.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_4h, daemon=True).start()

    if bot_1d:
        register_handlers(bot_1d, "1d")
        threading.Thread(target=bot_1d.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_1d, daemon=True).start()

    if bot_15m:
        register_handlers(bot_15m, "15m")
        threading.Thread(target=bot_15m.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_15m, daemon=True).start()

    # برنامه زنده بماند
    while True:
        time.sleep(60)
