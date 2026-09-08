# -*- coding: utf-8 -*-
# Modu Bazler v7 – نسخه‌ی حرفه‌ای با Plotly Multi‑Grid
# عکس‌های تجمیعی ۱۲تایی – بدون Matplotlib – پایدار روی Railway
# عکس تک‌نماد فقط برای نمادهای دارای آلارم
# عکس تجمیعی برای همه نمادها
# کیفیت متوسط – گزارش مرحله‌به‌مرحله ON
# پکیج‌ها از طریق requirements.txt نصب می‌شوند

import os
import json
import time
import threading
import datetime as dt
import requests
import numpy as np
import pandas as pd
import telebot
from telebot import types

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image
import base64
import io

# =========================
# مسیرها و کانفیگ
# =========================

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config_v7.json")

DEFAULT_CONFIG = {
    "symbols_1h": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT"
    ],
    "symbols_4h": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT"
    ],
    "symbols_1d": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT",
        "ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT"
    ],
    "symbols_15m": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT","ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT",
        "OPUSDT","ARBUSDT","SUIUSDT","PEPEUSDT","TONUSDT","UNIUSDT","AAVEUSDT","INJUSDT","RNDRUSDT","FTMUSDT",
        "NEOUSDT","GALAUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","JTOUSDT","WIFUSDT","JUPUSDT","STRKUSDT","BLURUSDT",
        "RUNEUSDT","RAYUSDT","LDOUSDT","COMPUSDT","CRVUSDT","MKRUSDT","SNXUSDT","GMXUSDT","DYDXUSDT","ENSUSDT"
    ],

    "lookback_1h": 5,
    "lookback_4h": 15,
    "lookback_1d": 180,
    "lookback_15m": 3,
    "max_bars": 300,

    "alarm_wma_direction": True,
    "alarm_cross_sma20": False,
    "alarm_cross_sma100": False,
    "alarm_cross_sma200": False,
    "alarm_sma20_direction": False,
    "alarm_sma100_direction": False,
    "alarm_sma200_direction": False,

    "make_pdf_1h": True,
    "make_pdf_1d": True,

    "make_combined": True,
    "report_steps": True,

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,

    "verbose_1h": True,
    "verbose_4h": True,
    "verbose_1d": True,
    "verbose_15m": True,

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
# توکن‌ها و ربات‌ها
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

LAST_ALARMS = {
    "1h": [],
    "4h": [],
    "1d": [],
    "15m": []
}

CYCLE_LOCKS = {
    "1h": threading.Lock(),
    "4h": threading.Lock(),
    "1d": threading.Lock(),
    "15m": threading.Lock()
}

# =========================
# راهنما
# =========================

HELP_TEXT = """
Modu Bazler v7 – نسخه‌ی حرفه‌ای

📌 ربات‌ها:
- 1h: ربات اصلی مدیریت و منو
- 4h: ربات ۴ساعته
- 1d: ربات روزانه
- 15m: ربات ۱۵دقیقه‌ای

🖼 عکس‌های تجمیعی:
- ساخت با Plotly Multi‑Grid
- بدون Matplotlib
- بدون RAM زیاد
- پایدار روی Railway
- ۱۲ نمودار در هر صفحه
- کیفیت متوسط (B)
- عکس تک‌نماد فقط برای نمادهای دارای آلارم
- عکس تجمیعی برای همه نمادها

🔊 گزارش مرحله‌به‌مرحله:
- فعال (ON)
- نمایش مراحل ساخت نمودارها و صفحات تجمیعی

⏱ زمان‌بندی خودکار:
- 1h: هر ساعت در دقیقه 22
- 4h: در ساعات 2، 6، 10، 14، 18، 22 (دقیقه 7)
- 1d: هر روز ساعت 1:05
- 15m: هر ۱۵ دقیقه
"""

# =========================
# منوی اصلی ربات 1h
# =========================

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("چک یک نماد", "اجرای دستی 1h")
    kb.row("اجرای فوری 4h", "اجرای فوری 1d")
    kb.row("اجرای فوری 15m")
    kb.row("مدیریت نمادهای 1h", "مدیریت نمادهای 4h")
    kb.row("مدیریت نمادهای 1d", "مدیریت نمادهای 15m")
    kb.row("تنظیم آلارم‌ها", "گزارش آلارم‌ها")
    kb.row("وضعیت سیستم", "تنظیمات پیشرفته")
    kb.row("اجرای چرخه‌ها", "ریست برنامه")
    kb.row("راهنما", "رفرش منو")
    bot_1h.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

@bot_1h.message_handler(commands=["start"])
def start_main(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    bot_1h.send_message(m.chat.id, HELP_TEXT)
    send_main_menu(m.chat.id)

@bot_1h.message_handler(commands=["refresh"])
@bot_1h.message_handler(func=lambda m: m.text == "رفرش منو")
def refresh_main(m):
    send_main_menu(m.chat.id)

# =========================
# استارت سایر ربات‌ها
# =========================

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
# ریست برنامه
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "ریست برنامه")
def reset_app(m):
    cfg = reset_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    bot_1h.send_message(m.chat.id, "برنامه و تنظیمات کامل ریست شد.")
    send_main_menu(m.chat.id)

# =========================
# مدیریت نمادها
# =========================

def get_symbols(cfg, group):
    return cfg[f"symbols_{group}"]

def set_symbols(cfg, group, symbols):
    cfg[f"symbols_{group}"] = symbols
    save_config(cfg)

def show_symbol_menu(chat_id, group):
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    txt = f"نمادهای فعال در {group}:\n"
    txt += ", ".join(symbols) if symbols else "هیچ نمادی ثبت نشده است."
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(f"افزودن نماد به {group}", f"حذف نماد از {group}")
    kb.row(f"نمایش نمادهای {group}")
    kb.row("بازگشت به منوی اصلی")
    bot_1h.send_message(chat_id, txt, reply_markup=kb)

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1h")
def manage_1h(m): show_symbol_menu(m.chat.id, "1h")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 4h")
def manage_4h(m): show_symbol_menu(m.chat.id, "4h")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1d")
def manage_1d(m): show_symbol_menu(m.chat.id, "1d")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 15m")
def manage_15m(m): show_symbol_menu(m.chat.id, "15m")

@bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
def back_to_main(m):
    send_main_menu(m.chat.id)

def add_symbol_step(m, group):
    symbol = m.text.strip().upper()
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    if symbol not in symbols:
        symbols.append(symbol)
        set_symbols(cfg, group, symbols)
        bot_1h.send_message(m.chat.id, f"{symbol} به لیست {group} اضافه شد.")
    else:
        bot_1h.send_message(m.chat.id, f"{symbol} قبلاً در لیست {group} وجود دارد.")
    show_symbol_menu(m.chat.id, group)

@bot_1h.message_handler(func=lambda m: m.text.startswith("افزودن نماد به "))
def add_symbol_any(m):
    group = m.text.split()[-1]
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید:")
    bot_1h.register_next_step_handler(msg, lambda mm: add_symbol_step(mm, group))

def remove_symbol_step(m, group):
    symbol = m.text.strip().upper()
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    if symbol in symbols:
        symbols.remove(symbol)
        set_symbols(cfg, group, symbols)
        bot_1h.send_message(m.chat.id, f"{symbol} از لیست {group} حذف شد.")
    else:
        bot_1h.send_message(m.chat.id, f"{symbol} در لیست {group} وجود ندارد.")
    show_symbol_menu(m.chat.id, group)

@bot_1h.message_handler(func=lambda m: m.text.startswith("حذف نماد از "))
def remove_symbol_any(m):
    group = m.text.split()[-1]
    msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید:")
    bot_1h.register_next_step_handler(msg, lambda mm: remove_symbol_step(mm, group))

@bot_1h.message_handler(func=lambda m: m.text.startswith("نمایش نمادهای "))
def show_symbols_any(m):
    group = m.text.split()[-1]
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    txt = f"نمادهای {group}:\n"
    txt += ", ".join(symbols) if symbols else "هیچ نمادی ثبت نشده است."
    bot_1h.send_message(m.chat.id, txt)

# =========================
# تنظیم آلارم‌ها
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "تنظیم آلارم‌ها")
def alarms_menu(m):
    cfg = load_config()
    kb = types.InlineKeyboardMarkup()
    for key in [
        "alarm_wma_direction",
        "alarm_cross_sma20",
        "alarm_cross_sma100",
        "alarm_cross_sma200",
        "alarm_sma20_direction",
        "alarm_sma100_direction",
        "alarm_sma200_direction"
    ]:
        kb.add(types.InlineKeyboardButton(
            f"{key} ({'ON' if cfg.get(key) else 'OFF'})",
            callback_data=f"alarm_{key}"
        ))
    bot_1h.send_message(m.chat.id, "آلارم‌ها را تنظیم کنید:", reply_markup=kb)

@bot_1h.callback_query_handler(func=lambda c: c.data.startswith("alarm_"))
def toggle_alarm(c):
    cfg = load_config()
    key = c.data.replace("alarm_", "")
    cfg[key] = not cfg.get(key)
    save_config(cfg)
    bot_1h.answer_callback_query(c.id, f"{key} -> {'ON' if cfg[key] else 'OFF'}")
    alarms_menu(c.message)

# =========================
# گزارش آلارم‌ها
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "گزارش آلارم‌ها")
def alarms_report(m):
    txt = ""
    for group in ["1h","4h","1d","15m"]:
        if LAST_ALARMS[group]:
            txt += f"آلارم‌های {group}:\n"
            for item in LAST_ALARMS[group]:
                txt += f"{item['symbol']} ({item['interval']}):\n"
                for a in item["alarms"]:
                    txt += f" - {a}\n"
                txt += f"زمان: {item['time']}\n\n"
    if not txt:
        txt = "هیچ آلارمی ثبت نشده است."
    bot_1h.send_message(m.chat.id, txt)

# =========================
# دریافت دیتا از بایننس
# =========================

def get_klines(symbol, interval, limit=300):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data, columns=[
            "open_time","open","high","low","close","volume",
            "close_time","qav","trades","tbbav","tbqav","ignore"
        ])
        df["open"]  = df["open"].astype(float)
        df["high"]  = df["high"].astype(float)
        df["low"]   = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"]= df["volume"].astype(float)
        return df
    except Exception as e:
        return None

# =========================
# محاسبهٔ اندیکاتورها
# =========================

def calc_indicators(df):
    df["sma20"]  = df["close"].rolling(20).mean()
    df["sma100"] = df["close"].rolling(100).mean()
    df["sma200"] = df["close"].rolling(200).mean()

    df["wma20"] = df["close"].rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, 21)), raw=True
    )

    df["wma_dir"] = df["wma20"].diff()

    df["cross_sma20"]  = df["close"] - df["sma20"]
    df["cross_sma100"] = df["close"] - df["sma100"]
    df["cross_sma200"] = df["close"] - df["sma200"]

    return df

# =========================
# سیستم آلارم‌ها
# =========================

def check_alarms(df, cfg):
    alarms = []

    last = df.iloc[-1]

    if cfg["alarm_wma_direction"]:
        if last["wma_dir"] > 0:
            alarms.append("WMA20 صعودی")
        elif last["wma_dir"] < 0:
            alarms.append("WMA20 نزولی")

    if cfg["alarm_cross_sma20"]:
        if last["cross_sma20"] > 0:
            alarms.append("قیمت بالای SMA20")
        else:
            alarms.append("قیمت زیر SMA20")

    if cfg["alarm_cross_sma100"]:
        if last["cross_sma100"] > 0:
            alarms.append("قیمت بالای SMA100")
        else:
            alarms.append("قیمت زیر SMA100")

    if cfg["alarm_cross_sma200"]:
        if last["cross_sma200"] > 0:
            alarms.append("قیمت بالای SMA200")
        else:
            alarms.append("قیمت زیر SMA200")

    if cfg["alarm_sma20_direction"]:
        if df["sma20"].diff().iloc[-1] > 0:
            alarms.append("SMA20 صعودی")
        else:
            alarms.append("SMA20 نزولی")

    if cfg["alarm_sma100_direction"]:
        if df["sma100"].diff().iloc[-1] > 0:
            alarms.append("SMA100 صعودی")
        else:
            alarms.append("SMA100 نزولی")

    if cfg["alarm_sma200_direction"]:
        if df["sma200"].diff().iloc[-1] > 0:
            alarms.append("SMA200 صعودی")
        else:
            alarms.append("SMA200 نزولی")

    return alarms

# =========================
# ثبت آلارم‌ها
# =========================

def record_alarm(group, symbol, interval, alarms):
    LAST_ALARMS[group].append({
        "symbol": symbol,
        "interval": interval,
        "alarms": alarms,
        "time": now_utc_str()
    })

# =========================
# ساخت نمودار تک‌نماد با Plotly
# =========================

def make_single_chart(symbol, df, interval, quality="B"):
    """
    ساخت نمودار تک‌نماد با Plotly
    خروجی: فایل PNG در پوشه charts
    """

    # کیفیت خروجی
    if quality == "A":
        width, height, scale = 2000, 1500, 3
    elif quality == "B":
        width, height, scale = 1800, 1400, 2
    else:
        width, height, scale = 1500, 1200, 2

    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"type": "xy"}]],
        horizontal_spacing=0.02,
        vertical_spacing=0.02
    )

    # کندل‌ها
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price"
        ),
        row=1, col=1
    )

    # SMAها
    fig.add_trace(go.Scatter(
        x=df.index, y=df["sma20"], name="SMA20", line=dict(color="orange", width=2)
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["sma100"], name="SMA100", line=dict(color="blue", width=2)
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["sma200"], name="SMA200", line=dict(color="purple", width=2)
    ), row=1, col=1)

    # WMA20
    fig.add_trace(go.Scatter(
        x=df.index, y=df["wma20"], name="WMA20", line=dict(color="green", width=2)
    ), row=1, col=1)

    fig.update_layout(
        title=f"{symbol} – {interval}",
        template="plotly_dark",
        width=width,
        height=height,
        margin=dict(l=40, r=40, t=60, b=40)
    )

    # ذخیرهٔ فایل
    out_path = os.path.join(CHARTS_DIR, f"{symbol}_{interval}.png")
    fig.write_image(out_path, scale=scale)

    return out_path


# =========================
# ساخت عکس‌های تجمیعی ۱۲تایی با Plotly Multi‑Grid
# =========================

def make_combined_page(images, page_number, quality="B"):
    """
    ساخت یک صفحه تجمیعی شامل ۱۲ عکس
    images: لیست مسیر عکس‌ها
    page_number: شماره صفحه
    """

    # کیفیت خروجی
    if quality == "A":
        width, height, scale = 2000, 1500, 3
    elif quality == "B":
        width, height, scale = 1800, 1400, 2
    else:
        width, height, scale = 1500, 1200, 2

    # تعداد عکس‌ها در هر صفحه
    ROWS = 3
    COLS = 4

    fig = make_subplots(
        rows=ROWS,
        cols=COLS,
        specs=[[{"type": "domain"} for _ in range(COLS)] for _ in range(ROWS)],
        horizontal_spacing=0.01,
        vertical_spacing=0.01
    )

    # قرار دادن عکس‌ها در ساب‌پلات‌ها
    idx = 0
    for r in range(1, ROWS + 1):
        for c in range(1, COLS + 1):
            if idx < len(images):
                img_path = images[idx]
                try:
                    img = Image.open(img_path)
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    encoded = base64.b64encode(buf.getvalue()).decode()

                    fig.add_trace(
                        go.Image(source=f"data:image/png;base64,{encoded}"),
                        row=r, col=c
                    )
                except Exception as e:
                    print("خطا در بارگذاری عکس:", e)
            idx += 1

    fig.update_layout(
        title=f"Combined Page {page_number}",
        template="plotly_dark",
        width=width,
        height=height,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    out_path = os.path.join(CHARTS_DIR, f"combined_page_{page_number}.png")
    fig.write_image(out_path, scale=scale)

    return out_path


def make_all_combined(symbols, interval, quality="B"):
    """
    ساخت تمام صفحات تجمیعی برای یک گروه زمانی
    """

    # ساخت عکس‌های تک‌نماد
    image_paths = []
    for sym in symbols:
        df = get_klines(sym, interval, 300)
        if df is None:
            continue

        df = calc_indicators(df)
        img_path = make_single_chart(sym, df, interval, quality)
        image_paths.append(img_path)

    # تقسیم عکس‌ها به صفحات ۱۲تایی
    pages = []
    for i in range(0, len(image_paths), 12):
        chunk = image_paths[i:i+12]
        page_num = (i // 12) + 1
        page_path = make_combined_page(chunk, page_num, quality)
        pages.append(page_path)

    return pages


# =========================
# ارسال عکس به ربات‌ها
# =========================

def send_photo(bot, chat_id, photo_path, caption=None):
    """
    ارسال عکس به ربات تلگرام
    """
    if bot is None or chat_id is None:
        return False

    try:
        with open(photo_path, "rb") as f:
            bot.send_photo(chat_id, f, caption=caption)
        return True
    except Exception as e:
        print("خطا در ارسال عکس:", e)
        return False


# =========================
# گزارش مرحله‌به‌مرحله
# =========================

def report_step(bot, chat_id, text, cfg):
    """
    اگر report_steps فعال باشد، پیام مرحله‌به‌مرحله ارسال می‌شود
    """
    if cfg.get("report_steps", True):
        try:
            bot.send_message(chat_id, f"🔹 {text}")
        except:
            pass


# =========================
# اجرای کامل یک چرخه
# =========================

def run_cycle(group, bot, interval, cfg):
    """
    اجرای کامل چرخه برای یک گروه زمانی
    شامل:
    - دریافت دیتا
    - ساخت نمودار تک‌نماد
    - ساخت صفحات تجمیعی
    - ارسال عکس‌ها
    - ثبت آلارم‌ها
    """

    symbols = cfg[f"symbols_{group}"]
    chat_id = cfg.get(f"chat_id_{group}")

    if bot is None or chat_id is None:
        return

    report_step(bot, chat_id, f"شروع چرخه {group}", cfg)

    single_images = []
    alarms_detected = []

    # دریافت دیتا و ساخت نمودار تک‌نماد
    for sym in symbols:
        report_step(bot, chat_id, f"دریافت دیتا برای {sym}", cfg)

        df = get_klines(sym, interval, cfg["max_bars"])
        if df is None:
            report_step(bot, chat_id, f"❌ خطا در دریافت دیتا {sym}", cfg)
            continue

        df = calc_indicators(df)

        # بررسی آلارم‌ها
        alarms = check_alarms(df, cfg)
        if alarms:
            record_alarm(group, sym, interval, alarms)
            alarms_detected.append((sym, alarms))

        # ساخت نمودار تک‌نماد
        report_step(bot, chat_id, f"ساخت نمودار {sym}", cfg)
        img_path = make_single_chart(sym, df, interval, "B")
        single_images.append((sym, img_path))

    # ارسال عکس‌های تک‌نماد فقط برای نمادهای دارای آلارم
    for sym, alarms in alarms_detected:
        for s, img in single_images:
            if s == sym:
                caption = f"{sym} – آلارم‌ها:\n" + "\n".join(alarms)
                send_photo(bot, chat_id, img, caption)
                report_step(bot, chat_id, f"ارسال عکس آلارم {sym}", cfg)

    # ساخت صفحات تجمیعی
    report_step(bot, chat_id, "ساخت صفحات تجمیعی…", cfg)

    all_imgs = [img for _, img in single_images]
    pages = []

    for i in range(0, len(all_imgs), 12):
        chunk = all_imgs[i:i+12]
        page_num = (i // 12) + 1
        report_step(bot, chat_id, f"ساخت صفحه {page_num}", cfg)
        page_path = make_combined_page(chunk, page_num, "B")
        pages.append(page_path)

    # ارسال صفحات تجمیعی
    for p in pages:
        send_photo(bot, chat_id, p, caption="صفحه تجمیعی")
        report_step(bot, chat_id, f"ارسال صفحه تجمیعی", cfg)

    report_step(bot, chat_id, f"پایان چرخه {group}", cfg)

# =========================
# زمان‌بندی خودکار چرخه‌ها
# =========================

def scheduler_loop():
    """
    زمان‌بندی خودکار برای 1h، 4h، 1d، 15m
    """

    while True:
        now = dt.datetime.utcnow()
        minute = now.minute
        hour = now.hour

        cfg = load_config()

        # 1h → هر ساعت دقیقه 22
        if minute == 22:
            if bot_1h:
                run_cycle("1h", bot_1h, "1h", cfg)

        # 4h → ساعت‌های 2، 6، 10، 14، 18، 22 دقیقه 7
        if minute == 7 and hour in [2, 6, 10, 14, 18, 22]:
            if bot_4h:
                run_cycle("4h", bot_4h, "4h", cfg)

        # 1d → هر روز ساعت 1:05
        if hour == 1 and minute == 5:
            if bot_1d:
                run_cycle("1d", bot_1d, "1d", cfg)

        # 15m → هر ۱۵ دقیقه
        if minute % 15 == 0:
            if bot_15m:
                run_cycle("15m", bot_15m, "15m", cfg)

        time.sleep(30)


# =========================
# اجرای دستی چرخه‌ها از ربات 1h
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "اجرای دستی 1h")
def manual_1h(m):
    cfg = load_config()
    run_cycle("1h", bot_1h, "1h", cfg)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 4h")
def manual_4h(m):
    cfg = load_config()
    run_cycle("4h", bot_4h, "4h", cfg)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 1d")
def manual_1d(m):
    cfg = load_config()
    run_cycle("1d", bot_1d, "1d", cfg)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری 15m")
def manual_15m(m):
    cfg = load_config()
    run_cycle("15m", bot_15m, "15m", cfg)


# =========================
# اجرای چرخه‌ها (منوی اصلی)
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "اجرای چرخه‌ها")
def run_all_cycles(m):
    cfg = load_config()

    if bot_1h:
        run_cycle("1h", bot_1h, "1h", cfg)

    if bot_4h:
        run_cycle("4h", bot_4h, "4h", cfg)

    if bot_1d:
        run_cycle("1d", bot_1d, "1d", cfg)

    if bot_15m:
        run_cycle("15m", bot_15m, "15m", cfg)


# =========================
# حلقهٔ اصلی اجرای ربات‌ها
# =========================

def start_bots():
    """
    اجرای هم‌زمان ربات‌ها + زمان‌بندی
    """

    # زمان‌بندی در یک Thread جدا
    threading.Thread(target=scheduler_loop, daemon=True).start()

    # اجرای ربات‌ها
    if bot_1h:
        threading.Thread(target=bot_1h.infinity_polling, daemon=True).start()

    if bot_4h:
        threading.Thread(target=bot_4h.infinity_polling, daemon=True).start()

    if bot_1d:
        threading.Thread(target=bot_1d.infinity_polling, daemon=True).start()

    if bot_15m:
        threading.Thread(target=bot_15m.infinity_polling, daemon=True).start()

    # نگه‌داشتن برنامه
    while True:
        time.sleep(1)


# =========================
# اجرای برنامه
# =========================

if __name__ == "__main__":
    print("Modu Bazler v7 started.")
    start_bots()