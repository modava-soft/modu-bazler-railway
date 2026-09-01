# -*- coding: utf-8 -*-
# Modu Bazler v4.2 – بازنویسی نسخهٔ قبلی با:
# - ۴ ربات جداگانه (1h, 4h, 1d, 15m)
# - امکان فعال/غیرفعال کردن توضیحات اجرای برنامه (وربوز) برای هر ربات
# - اجرای صحیح سیکل‌های روزانه و ۴ساعته (بدون گیر کردن)
# - اجرای فوری ۱ساعته + تولید PDF از همه نمودارهای سیکل 1h
# - حذف واچ‌لیست‌ها و جایگزینی با «لیست نمادها» برای هر ربات (افزودن/حذف نماد)
# - منوی مرکزی در ربات 1h

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

# =========================
# مسیرها و تنظیمات پایه
# =========================

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config_v4_2.json")

DEFAULT_CONFIG = {
    # لیست نمادها برای هر ربات
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

    # آلارم‌ها
    "alarm_wma_direction": True,
    "alarm_cross_sma20": False,
    "alarm_cross_sma100": False,
    "alarm_cross_sma200": False,
    "alarm_sma20_direction": False,
    "alarm_sma100_direction": False,
    "alarm_sma200_direction": False,

    # PDF
    "make_pdf_hourly": True,   # تولید PDF برای سیکل 1h
    "make_pdf_daily": True,    # تولید PDF برای سیکل روزانه

    # چت‌ها
    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,

    # تنظیمات توضیحات (وربوز) برای هر ربات
    "verbose_1h": True,
    "verbose_4h": True,
    "verbose_1d": True,
    "verbose_15m": True,

    # اندازه‌ی دسته برای پیام پیشرفت سیکل
    "cycle_progress_batch": 5
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

bot_1h  = create_bot(TOKEN_1H)   # ربات اصلی مدیریت
bot_4h  = create_bot(TOKEN_4H)
bot_1d  = create_bot(TOKEN_1D)
bot_15m = create_bot(TOKEN_15M)

# =========================
# متن راهنما
# =========================

HELP_TEXT = """
Modu Bazler v4.2 – نسخهٔ بازنویسی شده با:
- ۴ ربات جداگانه (1h, 4h, 1d, 15m)
- امکان فعال/غیرفعال کردن توضیحات اجرای برنامه (وربوز) برای هر ربات
- اجرای صحیح سیکل‌های روزانه و ۴ساعته
- اجرای فوری ۱ساعته + تولید PDF از همه نمودارهای سیکل 1h
- مدیریت لیست نمادها برای هر ربات (افزودن/حذف)

دستورات:
/start – ثبت چت و نمایش منو در ربات اصلی (1h)
/refresh – رفرش منو
/reset_app – ریست کامل تنظیمات

منوی اصلی ربات 1h:
- چک یک نماد (1h)
- اجرای دستی 1h
- اجرای فوری 4h
- اجرای فوری 1d
- اجرای فوری 15m
- مدیریت نمادهای 1h / 4h / 1d / 15m
- تنظیم آلارم‌ها
- وضعیت سیستم
- گزارش آلارم‌ها
- تنظیمات پیشرفته
"""

# =========================
# منوها
# =========================

def send_main_menu(bot, chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("چک یک نماد", "اجرای دستی 1h")
    kb.row("اجرای فوری 4h", "اجرای فوری 1d")
    kb.row("اجرای فوری 15m")
    kb.row("مدیریت نمادهای 1h", "مدیریت نمادهای 4h")
    kb.row("مدیریت نمادهای 1d", "مدیریت نمادهای 15m")
    kb.row("تنظیم آلارم‌ها", "گزارش آلارم‌ها")
    kb.row("وضعیت سیستم", "تنظیمات پیشرفته")
    kb.row("راهنما", "رفرش منو")

    bot.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

def refresh_menu(bot, chat_id):
    send_main_menu(bot, chat_id)

# =========================
# ابزار لیست نمادها
# =========================

def get_symbols(cfg, group: str) -> list:
    key = {
        "1h": "hourly_symbols",
        "4h": "fourh_symbols",
        "1d": "daily_symbols",
        "15m": "fifteenm_symbols"
    }[group]
    return cfg.get(key, [])

def set_symbols(cfg, group: str, symbols: list):
    key = {
        "1h": "hourly_symbols",
        "4h": "fourh_symbols",
        "1d": "daily_symbols",
        "15m": "fifteenm_symbols"
    }[group]
    cfg[key] = symbols

def add_symbol(cfg, group: str, symbol: str):
    symbol = symbol.upper().strip()
    symbols = get_symbols(cfg, group)
    if symbol not in symbols:
        symbols.append(symbol)
        set_symbols(cfg, group, symbols)
        save_config(cfg)
        return True
    return False

def remove_symbol(cfg, group: str, symbol: str):
    symbol = symbol.upper().strip()
    symbols = get_symbols(cfg, group)
    if symbol in symbols:
        symbols.remove(symbol)
        set_symbols(cfg, group, symbols)
        save_config(cfg)
        return True
    return False

# =========================
# هندلرهای /start و /refresh و /reset_app (ربات اصلی)
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

    @bot_1h.message_handler(commands=["reset_app"])
    def reset_app_1h(m):
        cfg = reset_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "برنامه و تنظیمات ریست شدند.")
        refresh_menu(bot_1h, m.chat.id)

# سایر ربات‌ها فقط start ساده دارند
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
# ساختار آلارم‌ها (گزارش جداگانه)
# =========================

LAST_ALARMS = {
    "1h": [],
    "4h": [],
    "1d": [],
    "15m": []
}

# =========================
# دریافت دیتا، اندیکاتورها، نمودارها
# =========================

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str) -> str:
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

def fetch_ohlc(symbol: str, interval: str, lookback_days: int, max_bars: int) -> pd.DataFrame:
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
                int(k[0]), float(k[1]), float(k[2]),
                float(k[3]), float(k[4]), float(k[5])
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
    if df.empty:
        return df
    df["SMA20"]  = df["c"].rolling(20).mean()
    df["SMA100"] = df["c"].rolling(100).mean()
    df["SMA200"] = df["c"].rolling(200).mean()
    df["WMA20"] = df["c"].rolling(20).apply(lambda x: np.average(x, weights=np.arange(1, len(x)+1)), raw=True)
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

def create_plotly_chart(symbol: str, interval: str, lookback_days: int, max_bars: int, png_name: str):
    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)
    if df.empty:
        df = pd.DataFrame(columns=["o","h","l","c","v"])
        df.index = pd.to_datetime([])
    else:
        df = df[["o","h","l","c","v"]]
    df = compute_indicators(df)

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.6,0.2,0.2],
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

    png_path = os.path.join(CHARTS_DIR, png_name)
    try:
        fig.write_image(png_path, width=1800, height=1100, scale=3)
    except:
        pass

    return {
        "symbol": symbol,
        "interval": interval,
        "png_path": png_path,
        "created_at": now_utc_str(),
        "last_close": float(df["c"].iloc[-1]) if len(df["c"]) else None,
        "wma": df["WMA20"].tolist() if "WMA20" in df.columns else [],
        "wma_slope": df["WMA20_slope"].tolist() if "WMA20_slope" in df.columns else [],
        "sma20": df["SMA20"].tolist() if "SMA20" in df.columns else [],
        "sma100": df["SMA100"].tolist() if "SMA100" in df.columns else [],
        "sma200": df["SMA200"].tolist() if "SMA200" in df.columns else []
    }

def detect_alarms(cfg: dict, info: dict, group: str):
    alarms = []
    wma    = info["wma"]
    slope  = info["wma_slope"]
    sma20  = info["sma20"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]

    if len(wma) < 3 or len(slope) < 3:
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

    if cfg.get("alarm_cross_sma20", False) and cross(wma, sma20):
        alarms.append("برخورد WMA20 با SMA20")
    if cfg.get("alarm_cross_sma100", False) and cross(wma, sma100):
        alarms.append("برخورد WMA20 با SMA100")
    if cfg.get("alarm_cross_sma200", False) and cross(wma, sma200):
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

    if cfg.get("alarm_sma20_direction", False):
        dir_change(sma20, "SMA20")
    if cfg.get("alarm_sma100_direction", False):
        dir_change(sma100, "SMA100")
    if cfg.get("alarm_sma200_direction", False):
        dir_change(sma200, "SMA200")

    if alarms:
        LAST_ALARMS[group] = [{
            "symbol": info["symbol"],
            "interval": info["interval"],
            "time": info["created_at"],
            "alarms": alarms
        }]

    return alarms

# =========================
# اجرای سیکل‌ها
# =========================

def run_cycle(group: str, bot, chat_id: int, symbols: list, interval: str, lookback_days: int, max_bars: int, make_pdf: bool):
    cfg = load_config()
    verbose_key = {
        "1h": "verbose_1h",
        "4h": "verbose_4h",
        "1d": "verbose_1d",
        "15m": "verbose_15m"
    }[group]
    verbose = cfg.get(verbose_key, True)

    if chat_id is None:
        return

    if verbose:
        bot.send_message(chat_id, f"شروع چرخه {group}\n# {now_utc_str()} UTC")

    unique_symbols = list(dict.fromkeys(symbols))
    total = len(unique_symbols)
    processed = 0
    batch_size = cfg.get("cycle_progress_batch", 5)

    pdf = None
    pdf_filename = None
    if make_pdf and group in ["1h","1d"]:
        pdf_filename = os.path.join(PDF_DIR, f"{group}_{now_utc().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf = PdfPages(pdf_filename)

    for sym in unique_symbols:
        processed += 1
        if verbose and (processed % batch_size == 0 or processed == 1 or processed == total):
            bot.send_message(chat_id, f"چرخه {group}: {processed} از {total} نماد پردازش شد، {total - processed} باقی مانده.")

        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"{group}_{sym}_{ts}.png"
        info = create_plotly_chart(sym, interval, lookback_days, max_bars, png)
        alarms = detect_alarms(cfg, info, group)

        if alarms:
            caption = f"{sym} ({group})\n" + "\n".join(alarms)
        else:
            caption = f"{sym} ({group}) – بدون آلارم خاص"

        try:
            with open(info["png_path"], "rb") as f:
                bot.send_photo(chat_id, f, caption=caption)
        except:
            pass

        if pdf is not None:
            try:
                img = plt.imread(info["png_path"])
                fig, ax = plt.subplots(figsize=(10,6))
                ax.imshow(img); ax.axis("off"); ax.set_title(f"{sym} – {group}")
                pdf.savefig(fig); plt.close(fig)
            except:
                pass

        time.sleep(1)

    if pdf is not None:
        try:
            pdf.close()
            with open(pdf_filename, "rb") as f:
                bot.send_document(chat_id, f, caption=f"گزارش PDF کامل سیکل {group}")
        except:
            pass

    if verbose:
        bot.send_message(chat_id, f"پایان چرخه {group}")

# =========================
# هندلرهای منوی ربات اصلی (1h)
# =========================

if bot_1h:

    # چک تک نماد در 1h
    @bot_1h.message_handler(func=lambda m: m.text == "چک یک نماد")
    def check_symbol(m):
        msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید (مثلاً BTCUSDT):")
        bot_1h.register_next_step_handler(msg, process_single_symbol)

    def process_single_symbol(m):
        symbol = m.text.strip().upper()
        cfg = load_config()
        bot_1h.send_message(m.chat.id, f"در حال بررسی {symbol} در تایم‌فریم 1h ...")

        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"single_1h_{symbol}_{ts}.png"

        info = create_plotly_chart(
            symbol,
            "1h",
            cfg["hourly_lookback_days"],
            cfg["max_bars"],
            png
        )

        try:
            with open(info["png_path"], "rb") as f:
                bot_1h.send_photo(m.chat.id, f, caption=f"{symbol} – بررسی 1h")
        except:
            pass

        bot_1h.send_message(m.chat.id, "بررسی تک نماد پایان یافت.")

    # اجرای دستی سیکل 1h
    @bot_1h.message_handler(func=lambda m: m.text == "اجرای دستی 1h")
    def manual_1h(m):
        cfg = load_config()
        chat = cfg.get("chat_id_1h") or m.chat.id
        symbols = cfg["hourly_symbols"]
        run_cycle(
            group="1h",
            bot=bot_1h,
            chat_id=chat,
            symbols=symbols,
            interval="1h",
            lookback_days=cfg["hourly_lookback_days"],
            max_bars=cfg["max_bars"],
            make_pdf=cfg.get("make_pdf_hourly", True)
        )

    # اجرای فوری 4h
    @bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 4h")
    def manual_4h_btn(m):
        cfg = load_config()
        if bot_4h and cfg.get("chat_id_4h"):
            run_cycle(
                "4h",
                bot_4h,
                cfg["chat_id_4h"],
                cfg["fourh_symbols"],
                "4h",
                cfg["fourh_lookback_days"],
                cfg["max_bars"],
                make_pdf=False
            )
        else:
            bot_1h.send_message(m.chat.id, "ربات 4h یا چت آن ثبت نشده است.")

    # اجرای فوری 1d
    @bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 1d")
    def manual_1d_btn(m):
        cfg = load_config()
        if bot_1d and cfg.get("chat_id_1d"):
            run_cycle(
                "1d",
                bot_1d,
                cfg["chat_id_1d"],
                cfg["daily_symbols"],
                "1d",
                cfg["daily_lookback_days"],
                cfg["max_bars"],
                make_pdf=cfg.get("make_pdf_daily", True)
            )
        else:
            bot_1h.send_message(m.chat.id, "ربات 1d یا چت آن ثبت نشده است.")

    # اجرای فوری 15m
    @bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 15m")
    def manual_15m_btn(m):
        cfg = load_config()
        if bot_15m and cfg.get("chat_id_15m"):
            run_cycle(
                "15m",
                bot_15m,
                cfg["chat_id_15m"],
                cfg["fifteenm_symbols"],
                "15m",
                cfg["fifteenm_lookback_days"],
                cfg["max_bars"],
                make_pdf=False
            )
        else:
            bot_1h.send_message(m.chat.id, "ربات 15m یا چت آن ثبت نشده است.")

    # مدیریت نمادها
    def show_symbol_menu(chat_id, group: str):
        cfg = load_config()
        symbols = get_symbols(cfg, group)
        txt = f"نمادهای فعال در {group}:\n"
        if not symbols:
            txt += "هیچ نمادی ثبت نشده است.\n"
        else:
            txt += ", ".join(symbols)

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row(f"افزودن نماد به {group}", f"حذف نماد از {group}")
        kb.row(f"نمایش نمادهای {group}")
        kb.row("بازگشت به منوی اصلی")
        bot_1h.send_message(chat_id, txt, reply_markup=kb)

    @bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1h")
    def manage_1h_symbols(m):
        show_symbol_menu(m.chat.id, "1h")

    @bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 4h")
    def manage_4h_symbols(m):
        show_symbol_menu(m.chat.id, "4h")

    @bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1d")
    def manage_1d_symbols(m):
        show_symbol_menu(m.chat.id, "1d")

    @bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 15m")
    def manage_15m_symbols(m):
        show_symbol_menu(m.chat.id, "15m")

    @bot_1h.message_handler(func=lambda m: m.text.startswith("افزودن نماد به "))
    def add_symbol_any(m):
        text = m.text.strip()
        if "1h" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (مثلاً BTCUSDT):")
            bot_1h.register_next_step_handler(msg, lambda mm: add_symbol_step(mm,"1h"))
        elif "4h" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (مثلاً BTCUSDT):")
            bot_1h.register_next_step_handler(msg, lambda mm: add_symbol_step(mm,"4h"))
        elif "1d" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (مثلاً BTCUSDT):")
            bot_1h.register_next_step_handler(msg, lambda mm: add_symbol_step(mm,"1d"))
        elif "15m" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (مثلاً BTCUSDT):")
            bot_1h.register_next_step_handler(msg, lambda mm: add_symbol_step(mm,"15m"))

    def add_symbol_step(m, group: str):
        symbol = m.text.strip().upper()
        cfg = load_config()
        if add_symbol(cfg, group, symbol):
            bot_1h.send_message(m.chat.id, f"{symbol} به لیست نمادهای {group} اضافه شد.")
        else:
            bot_1h.send_message(m.chat.id, f"{symbol} قبلاً در لیست {group} وجود دارد.")
        show_symbol_menu(m.chat.id, group)

    @bot_1h.message_handler(func=lambda m: m.text.startswith("حذف نماد از "))
    def remove_symbol_any(m):
        text = m.text.strip()
        if "1h" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر برای حذف را وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: remove_symbol_step(mm,"1h"))
        elif "4h" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر برای حذف را وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: remove_symbol_step(mm,"4h"))
        elif "1d" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر برای حذف را وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: remove_symbol_step(mm,"1d"))
        elif "15m" in text:
            msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر برای حذف را وارد کنید:")
            bot_1h.register_next_step_handler(msg, lambda mm: remove_symbol_step(mm,"15m"))

    def remove_symbol_step(m, group: str):
        symbol = m.text.strip().upper()
        cfg = load_config()
        if remove_symbol(cfg, group, symbol):
            bot_1h.send_message(m.chat.id, f"{symbol} از لیست نمادهای {group} حذف شد.")
        else:
            bot_1h.send_message(m.chat.id, f"{symbol} در لیست {group} وجود ندارد.")
        show_symbol_menu(m.chat.id, group)

    @bot_1h.message_handler(func=lambda m: m.text.startswith("نمایش نمادهای "))
    def show_symbols_any(m):
        text = m.text.strip()
        cfg = load_config()
        if "1h" in text:
            symbols = get_symbols(cfg, "1h"); group = "1h"
        elif "4h" in text:
            symbols = get_symbols(cfg, "4h"); group = "4h"
        elif "1d" in text:
            symbols = get_symbols(cfg, "1d"); group = "1d"
        elif "15m" in text:
            symbols = get_symbols(cfg, "15m"); group = "15m"
        else:
            return
        txt = f"نمادهای {group}:\n"
        if not symbols:
            txt += "هیچ نمادی ثبت نشده است."
        else:
            txt += ", ".join(symbols)
        bot_1h.send_message(m.chat.id, txt)

    @bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
    def back_to_main(m):
        refresh_menu(bot_1h, m.chat.id)

    # تنظیم آلارم‌ها
    @bot_1h.message_handler(func=lambda m: m.text == "تنظیم آلارم‌ها")
    def alarms_menu(m):
        cfg = load_config()
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(f"WMA جهت ({'ON' if cfg.get('alarm_wma_direction', True) else 'OFF'})", callback_data="alarm_wma_direction"))
        kb.add(types.InlineKeyboardButton(f"Cross SMA20 ({'ON' if cfg.get('alarm_cross_sma20', False) else 'OFF'})", callback_data="alarm_cross_sma20"))
        kb.add(types.InlineKeyboardButton(f"Cross SMA100 ({'ON' if cfg.get('alarm_cross_sma100', False) else 'OFF'})", callback_data="alarm_cross_sma100"))
        kb.add(types.InlineKeyboardButton(f"Cross SMA200 ({'ON' if cfg.get('alarm_cross_sma200', False) else 'OFF'})", callback_data="alarm_cross_sma200"))
        kb.add(types.InlineKeyboardButton(f"SMA20 جهت ({'ON' if cfg.get('alarm_sma20_direction', False) else 'OFF'})", callback_data="alarm_sma20_direction"))
        kb.add(types.InlineKeyboardButton(f"SMA100 جهت ({'ON' if cfg.get('alarm_sma100_direction', False) else 'OFF'})", callback_data="alarm_sma100_direction"))
        kb.add(types.InlineKeyboardButton(f"SMA200 جهت ({'ON' if cfg.get('alarm_sma200_direction', False) else 'OFF'})", callback_data="alarm_sma200_direction"))
        bot_1h.send_message(m.chat.id, "آلارم‌ها را تنظیم کنید:", reply_markup=kb)

    @bot_1h.callback_query_handler(func=lambda c: c.data.startswith("alarm_"))
    def toggle_alarm(c):
        cfg = load_config()
        key = c.data
        current = cfg.get(key, False)
        cfg[key] = not current
        save_config(cfg)
        bot_1h.answer_callback_query(c.id, f"{key} -> {'ON' if cfg[key] else 'OFF'}")
        alarms_menu(c.message)

    # گزارش آلارم‌ها
    @bot_1h.message_handler(func=lambda m: m.text == "گزارش آلارم‌ها")
    def alarms_report(m):
        txt = ""
        for group in ["1h","4h","1d","15m"]:
            if LAST_ALARMS[group]:
                if group == "1h": title = "⏱ آلارم‌های 1h"
                elif group == "4h": title = "⏱ آلارم‌های 4h"
                elif group == "1d": title = "📅 آلارم‌های روزانه"
                else: title = "🔁 آلارم‌های 15m"
                txt += title + ":\n"
                for item in LAST_ALARMS[group]:
                    txt += f"{item['symbol']} ({item['interval']}):\n"
                    for a in item["alarms"]:
                        txt += f" - {a}\n"
                    txt += f"زمان: {item['time']}\n\n"
        if not txt:
            txt = "هیچ آلارمی ثبت نشده است."
        bot_1h.send_message(m.chat.id, txt)

    # وضعیت سیستم
    @bot_1h.message_handler(func=lambda m: m.text == "وضعیت سیستم")
    def system_status(m):
        cfg = load_config()
        txt = "سیستم فعال است.\n" + now_utc_str()
        txt += f"\nنمادهای 1h: {len(get_symbols(cfg,'1h'))}"
        txt += f"\nنمادهای 4h: {len(get_symbols(cfg,'4h'))}"
        txt += f"\نمادهای 1d: {len(get_symbols(cfg,'1d'))}"
        txt += f"\نمادهای 15m: {len(get_symbols(cfg,'15m'))}"
        txt += f"\ncycle_progress_batch: {cfg.get('cycle_progress_batch',5)}"
        txt += f"\nmake_pdf_hourly: {'ON' if cfg.get('make_pdf_hourly',True) else 'OFF'}"
        txt += f"\nmake_pdf_daily: {'ON' if cfg.get('make_pdf_daily',True) else 'OFF'}"
        txt += f"\nverbose_1h: {'ON' if cfg.get('verbose_1h',True) else 'OFF'}"
        txt += f"\nverbose_4h: {'ON' if cfg.get('verbose_4h',True) else 'OFF'}"
        txt += f"\nverbose_1d: {'ON' if cfg.get('verbose_1d',True) else 'OFF'}"
        txt += f"\nverbose_15m: {'ON' if cfg.get('verbose_15m',True) else 'OFF'}"
        bot_1h.send_message(m.chat.id, txt)

    # تنظیمات پیشرفته
    @bot_1h.message_handler(func=lambda m: m.text == "تنظیمات پیشرفته")
    def advanced_settings(m):
        cfg = load_config()
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(f"PDF 1h ({'ON' if cfg.get('make_pdf_hourly', True) else 'OFF'})", callback_data="adv_make_pdf_hourly"))
        kb.add(types.InlineKeyboardButton(f"PDF 1d ({'ON' if cfg.get('make_pdf_daily', True) else 'OFF'})", callback_data="adv_make_pdf_daily"))
        kb.add(types.InlineKeyboardButton(f"batch سیکل = {cfg.get('cycle_progress_batch',5)}", callback_data="adv_cycle_batch_toggle"))
        kb.add(types.InlineKeyboardButton(f"verbose 1h ({'ON' if cfg.get('verbose_1h',True) else 'OFF'})", callback_data="adv_verbose_1h"))
        kb.add(types.InlineKeyboardButton(f"verbose 4h ({'ON' if cfg.get('verbose_4h',True) else 'OFF'})", callback_data="adv_verbose_4h"))
        kb.add(types.InlineKeyboardButton(f"verbose 1d ({'ON' if cfg.get('verbose_1d',True) else 'OFF'})", callback_data="adv_verbose_1d"))
        kb.add(types.InlineKeyboardButton(f"verbose 15m ({'ON' if cfg.get('verbose_15m',True) else 'OFF'})", callback_data="adv_verbose_15m"))
        kb.add(types.InlineKeyboardButton("ریست کامل برنامه (config)", callback_data="adv_reset_app"))
        bot_1h.send_message(m.chat.id, "تنظیمات پیشرفته:", reply_markup=kb)

    @bot_1h.callback_query_handler(func=lambda c: c.data.startswith("adv_"))
    def advanced_settings_handler(c):
        cfg = load_config()
        if c.data == "adv_make_pdf_hourly":
            cfg["make_pdf_hourly"] = not cfg.get("make_pdf_hourly", True)
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, f"make_pdf_hourly -> {'ON' if cfg['make_pdf_hourly'] else 'OFF'}")
        elif c.data == "adv_make_pdf_daily":
            cfg["make_pdf_daily"] = not cfg.get("make_pdf_daily", True)
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, f"make_pdf_daily -> {'ON' if cfg['make_pdf_daily'] else 'OFF'}")
        elif c.data == "adv_cycle_batch_toggle":
            current = cfg.get("cycle_progress_batch", 5)
            cfg["cycle_progress_batch"] = 10 if current == 5 else 5
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, f"cycle_progress_batch -> {cfg['cycle_progress_batch']}")
        elif c.data == "adv_verbose_1h":
            cfg["verbose_1h"] = not cfg.get("verbose_1h", True)
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, f"verbose_1h -> {'ON' if cfg['verbose_1h'] else 'OFF'}")
        elif c.data == "adv_verbose_4h":
            cfg["verbose_4h"] = not cfg.get("verbose_4h", True)
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, f"verbose_4h -> {'ON' if cfg['verbose_4h'] else 'OFF'}")
        elif c.data == "adv_verbose_1d":
            cfg["verbose_1d"] = not cfg.get("verbose_1d", True)
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, f"verbose_1d -> {'ON' if cfg['verbose_1d'] else 'OFF'}")
        elif c.data == "adv_verbose_15m":
            cfg["verbose_15m"] = not cfg.get("verbose_15m", True)
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, f"verbose_15m -> {'ON' if cfg['verbose_15m'] else 'OFF'}")
        elif c.data == "adv_reset_app":
            cfg = reset_config()
            save_config(cfg)
            bot_1h.answer_callback_query(c.id, "برنامه و تنظیمات به حالت اولیه برگشت.")
        advanced_settings(c.message)

    # راهنما
    @bot_1h.message_handler(func=lambda m: m.text == "راهنما")
    def help_menu(m):
        bot_1h.send_message(m.chat.id, HELP_TEXT)

    # رفرش منو
    @bot_1h.message_handler(func=lambda m: m.text == "رفرش منو")
    def refresh_menu_btn(m):
        refresh_menu(bot_1h, m.chat.id)

# =========================
# زمان‌بندی خودکار سیکل‌ها (اجرای صحیح روزانه و ۴ساعته)
# =========================

def scheduler_loop():
    while True:
        try:
            cfg = load_config()
            now = now_utc()

            # 1h – هر ساعت در دقیقه 22 (UTC)
            if now.minute == 22 and now.second < 5:
                if bot_1h and cfg.get("chat_id_1h"):
                    threading.Thread(
                        target=run_cycle,
                        args=(
                            "1h",
                            bot_1h,
                            cfg["chat_id_1h"],
                            cfg["hourly_symbols"],
                            "1h",
                            cfg["hourly_lookback_days"],
                            cfg["max_bars"],
                            cfg.get("make_pdf_hourly", True)
                        ),
                        daemon=True
                    ).start()
                    time.sleep(10)

            # 4h – در ساعات 2:07، 6:07، 10:07، 14:07، 18:07، 22:07 (UTC)
            if now.minute == 7 and now.second < 5 and now.hour in [2,6,10,14,18,22]:
                if bot_4h and cfg.get("chat_id_4h"):
                    threading.Thread(
                        target=run_cycle,
                        args=(
                            "4h",
                            bot_4h,
                            cfg["chat_id_4h"],
                            cfg["fourh_symbols"],
                            "4h",
                            cfg["fourh_lookback_days"],
                            cfg["max_bars"],
                            False
                        ),
                        daemon=True
                    ).start()
                    time.sleep(10)

            # 1d – هر روز ساعت 1:05 (UTC)
            if now.hour == 1 and now.minute == 5 and now.second < 5:
                if bot_1d and cfg.get("chat_id_1d"):
                    threading.Thread(
                        target=run_cycle,
                        args=(
                            "1d",
                            bot_1d,
                            cfg["chat_id_1d"],
                            cfg["daily_symbols"],
                            "1d",
                            cfg["daily_lookback_days"],
                            cfg["max_bars"],
                            cfg.get("make_pdf_daily", True)
                        ),
                        daemon=True
                    ).start()
                    time.sleep(10)

            # 15m – هر ۱۵ دقیقه
            if now.minute % 15 == 0 and now.second < 5:
                if bot_15m and cfg.get("chat_id_15m"):
                    threading.Thread(
                        target=run_cycle,
                        args=(
                            "15m",
                            bot_15m,
                            cfg["chat_id_15m"],
                            cfg["fifteenm_symbols"],
                            "15m",
                            cfg["fifteenm_lookback_days"],
                            cfg["max_bars"],
                            False
                        ),
                        daemon=True
                    ).start()
                    time.sleep(10)

            time.sleep(3)
        except:
            time.sleep(10)

# =========================
# راه‌اندازی
# =========================

if __name__ == "__main__":
    if ADMIN_CHAT and bot_1h:
        try:
            bot_1h.send_message(ADMIN_CHAT, "Modu Bazler v4.2 – ربات اصلی راه‌اندازی شد.")
        except:
            pass

    if bot_1h:
        threading.Thread(target=bot_1h.infinity_polling, daemon=True).start()
    if bot_4h:
        threading.Thread(target=bot_4h.infinity_polling, daemon=True).start()
    if bot_1d:
        threading.Thread(target=bot_1d.infinity_polling, daemon=True).start()
    if bot_15m:
        threading.Thread(target=bot_15m.infinity_polling, daemon=True).start()

    threading.Thread(target=scheduler_loop, daemon=True).start()

    while True:
        time.sleep(60)