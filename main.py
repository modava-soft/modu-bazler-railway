# -*- coding: utf-8 -*-
# Modu Bazler v7.5 — بخش ۱ از ۵

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
# مسیرها و فایل‌ها
# =========================

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH        = os.path.join(DATA_DIR, "config_v7_5.json")
ALARM_HISTORY_PATH = os.path.join(DATA_DIR, "alarm_history_v7_5.json")

# =========================
# کانفیگ پیش‌فرض
# =========================

DEFAULT_CONFIG = {
    "symbols_1h":   [],
    "symbols_4h":   [],
    "symbols_1d":   [],
    "symbols_15m":  [],

    "lookback_1h":  5,
    "lookback_4h":  15,
    "lookback_1d":  180,
    "lookback_15m": 3,

    "max_bars":       300,
    "bars_per_chart": 90,

    "alarm_wma_direction":   True,
    "alarm_cross_sma20":     False,
    "alarm_cross_sma100":    False,
    "alarm_cross_sma200":    False,
    "alarm_sma20_direction": False,
    "alarm_sma100_direction":False,
    "alarm_sma200_direction":False,

    "make_pdf_1h": True,
    "make_pdf_1d": True,

    "make_combined_15m": True,
    "make_combined_all": True,

    "chat_id_1h":   None,
    "chat_id_4h":   None,
    "chat_id_1d":   None,
    "chat_id_15m":  None,

    "verbose_1h":   True,
    "verbose_4h":   True,
    "verbose_1d":   True,
    "verbose_15m":  True,

    "cycle_progress_batch": 5,

    "lock_timeout_sec":      600,

    "enable_1h":   True,
    "enable_4h":   True,
    "enable_1d":   True,
    "enable_15m":  True,

    "alarm_report_enabled": False
}

# =========================
# تاریخچه آلارم‌ها
# =========================

ALARM_HISTORY = {
    "1h":  [],
    "4h":  [],
    "1d":  [],
    "15m": []
}

LAST_MSG_ID = {}

# =========================
# توکن‌ها
# =========================

TOKEN_1H   = (os.getenv("TOKEN_1H") or "").strip()
TOKEN_4H   = (os.getenv("TOKEN_4H") or "").strip()
TOKEN_1D   = (os.getenv("TOKEN_1D") or "").strip()
TOKEN_15M  = (os.getenv("TOKEN_15M") or "").strip()

# =========================
# توابع کمکی
# =========================

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG.copy()

def save_alarm_history():
    try:
        with open(ALARM_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(ALARM_HISTORY, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_alarm_history():
    global ALARM_HISTORY
    if not os.path.exists(ALARM_HISTORY_PATH):
        save_alarm_history()
        return
    try:
        with open(ALARM_HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for g in ["1h","4h","1d","15m"]:
            ALARM_HISTORY[g] = data.get(g, [])
    except:
        pass

def create_bot(token: str):
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
# SmartLock
# =========================

class SmartLock:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_acquire = None

    def acquire(self, blocking=False):
        cfg = load_config()
        timeout = cfg.get("lock_timeout_sec", 600)

        if self.lock.locked() and self.last_acquire:
            elapsed = (now_utc() - self.last_acquire).total_seconds()
            if elapsed > timeout:
                try:
                    self.lock.release()
                except:
                    pass

        ok = self.lock.acquire(blocking=blocking)
        if ok:
            self.last_acquire = now_utc()
        return ok

    def release(self):
        if self.lock.locked():
            try:
                self.lock.release()
            except:
                pass

CYCLE_LOCKS = {
    "1h":  SmartLock(),
    "4h":  SmartLock(),
    "1d":  SmartLock(),
    "15m": SmartLock()
}

# =========================
# راهنما
# =========================

HELP_TEXT = """
Modu Bazler v7.5

- گزارش آلارم‌ها با شروع/توقف
- ذخیره تا ۱۰ سیکل
- verbose واقعی
- خط افقی پایان سیکل
"""

# =========================
# منوی اصلی
# =========================

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🟡 گزارش آلارم‌ها", "🟡 تنظیم آلارم‌ها")
    kb.row("🔵 اجرای چرخه‌ها", "🟣 راهنما")
    bot_1h.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

@bot_1h.message_handler(commands=["start"])
def start_main(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    load_alarm_history()
    bot_1h.send_message(m.chat.id, HELP_TEXT)
    send_main_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "🟣 راهنما")
def help_menu(m):
    bot_1h.send_message(m.chat.id, HELP_TEXT)

# =========================
# تنظیم آلارم‌ها
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "🟡 تنظیم آلارم‌ها")
def alarm_settings(m):
    cfg = load_config()
    kb = types.InlineKeyboardMarkup()

    kb.add(types.InlineKeyboardButton(
        f"WMA جهت ({'ON' if cfg['alarm_wma_direction'] else 'OFF'})",
        callback_data="al_wma_dir"
    ))

    kb.add(types.InlineKeyboardButton(
        f"Cross SMA20 ({'ON' if cfg['alarm_cross_sma20'] else 'OFF'})",
        callback_data="al_cross_20"
    ))

    kb.add(types.InlineKeyboardButton(
        f"Cross SMA100 ({'ON' if cfg['alarm_cross_sma100'] else 'OFF'})",
        callback_data="al_cross_100"
    ))

    kb.add(types.InlineKeyboardButton(
        f"Cross SMA200 ({'ON' if cfg['alarm_cross_sma200'] else 'OFF'})",
        callback_data="al_cross_200"
    ))

    kb.add(types.InlineKeyboardButton(
        f"جهت SMA20 ({'ON' if cfg['alarm_sma20_direction'] else 'OFF'})",
        callback_data="al_dir_20"
    ))

    kb.add(types.InlineKeyboardButton(
        f"جهت SMA100 ({'ON' if cfg['alarm_sma100_direction'] else 'OFF'})",
        callback_data="al_dir_100"
    ))

    kb.add(types.InlineKeyboardButton(
        f"جهت SMA200 ({'ON' if cfg['alarm_sma200_direction'] else 'OFF'})",
        callback_data="al_dir_200"
    ))

    bot_1h.send_message(m.chat.id, "تنظیم آلارم‌ها:", reply_markup=kb)


@bot_1h.callback_query_handler(func=lambda c: c.data.startswith("al_"))
def alarm_settings_handler(c):
    cfg = load_config()

    if c.data == "al_wma_dir":
        cfg["alarm_wma_direction"] = not cfg["alarm_wma_direction"]

    elif c.data == "al_cross_20":
        cfg["alarm_cross_sma20"] = not cfg["alarm_cross_sma20"]

    elif c.data == "al_cross_100":
        cfg["alarm_cross_sma100"] = not cfg["alarm_cross_sma100"]

    elif c.data == "al_cross_200":
        cfg["alarm_cross_sma200"] = not cfg["alarm_cross_sma200"]

    elif c.data == "al_dir_20":
        cfg["alarm_sma20_direction"] = not cfg["alarm_sma20_direction"]

    elif c.data == "al_dir_100":
        cfg["alarm_sma100_direction"] = not cfg["alarm_sma100_direction"]

    elif c.data == "al_dir_200":
        cfg["alarm_sma200_direction"] = not cfg["alarm_sma200_direction"]

    save_config(cfg)
    bot_1h.answer_callback_query(c.id, "آلارم‌ها به‌روزرسانی شد.")
    alarm_settings(c.message)


# =========================
# گزارش آلارم‌ها (شروع/توقف + نمایش)
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "🟡 گزارش آلارم‌ها")
def alarms_menu(m):
    cfg = load_config()
    kb = types.InlineKeyboardMarkup()

    kb.add(types.InlineKeyboardButton(
        f"{'⏹ توقف گزارش آلارم‌ها' if cfg.get('alarm_report_enabled', False) else '▶️ شروع گزارش آلارم‌ها'}",
        callback_data="al_report_toggle"
    ))

    kb.add(types.InlineKeyboardButton(
        "📜 نمایش گزارش آلارم‌ها",
        callback_data="al_report_show"
    ))

    bot_1h.send_message(m.chat.id, "مدیریت گزارش آلارم‌ها:", reply_markup=kb)


@bot_1h.callback_query_handler(func=lambda c: c.data in ["al_report_toggle", "al_report_show"])
def alarms_menu_handler(c):
    cfg = load_config()

    # شروع / توقف ذخیره‌سازی آلارم‌ها
    if c.data == "al_report_toggle":
        cfg["alarm_report_enabled"] = not cfg.get("alarm_report_enabled", False)
        save_config(cfg)

        state = "فعال شد ✅" if cfg["alarm_report_enabled"] else "غیرفعال شد ⛔"
        bot_1h.answer_callback_query(c.id, f"گزارش آلارم‌ها {state}")

        alarms_menu(c.message)
        return

    # نمایش گزارش آلارم‌ها
    if c.data == "al_report_show":
        load_alarm_history()

        txt = "📜 گزارش آلارم‌ها (۱۰ سیکل آخر):\n\n"

        for group in ["15m", "1h", "4h", "1d"]:
            txt += f"🔹 تایم‌فریم {group}:\n"
            history = ALARM_HISTORY.get(group, [])

            if not history:
                txt += "  هیچ آلارمی ثبت نشده.\n\n"
                continue

            for idx, cycle in enumerate(history[::-1], start=1):
                txt += f"  🕒 سیکل #{idx} — زمان: {cycle['cycle_time']}\n"

                for item in cycle["items"]:
                    txt += f"    • {item['symbol']} ({item['interval']}):\n"
                    for a in item["alarms"]:
                        txt += f"      - {a}\n"
                    txt += f"      زمان آلارم: {item['time']}\n"

                txt += "\n"

            txt += "\n"

        bot_1h.send_message(c.message.chat.id, txt)
        bot_1h.answer_callback_query(c.id, "گزارش ارسال شد.")


# =========================
# تبدیل تایم‌فریم برای بایننس
# =========================

def _binance_interval(i: str) -> str:
    return {
        "1h": "1h",
        "4h": "4h",
        "1d": "1d",
        "15m": "15m"
    }[i]


# =========================
# دریافت دیتا از بایننس
# =========================

def fetch_ohlc(symbol: str, interval: str, lookback_days: int, max_bars: int) -> pd.DataFrame:
    limit = max(500, max_bars)

    try:
        url = "https://api.binance.com/api/v3/klines"
        r = requests.get(url, params={
            "symbol": symbol,
            "interval": _binance_interval(interval),
            "limit": limit
        }, timeout=10)

        r.raise_for_status()
        data = r.json()

        rows = [
            [int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])]
            for k in data
        ]

        df = pd.DataFrame(rows, columns=["t","o","h","l","c","v"])
        df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
        df.set_index("t", inplace=True)

        return df

    except Exception:
        return pd.DataFrame()


# =========================
# محاسبه اندیکاتورها
# =========================

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if df.empty:
        return df

    # SMAها
    df["SMA20"]  = df["c"].rolling(20).mean()
    df["SMA100"] = df["c"].rolling(100).mean()
    df["SMA200"] = df["c"].rolling(200).mean()

    # WMA20
    df["WMA20"] = df["c"].rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x)+1)),
        raw=True
    )

    # شیب WMA20
    df["WMA20_slope"] = df["WMA20"].diff()

    return df


# =========================
# ساخت نمودار Plotly با خط افقی پایان سیکل
# =========================

def create_plotly_chart(symbol: str, interval: str, lookback_days: int, max_bars: int, png_name: str):

    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)

    if df.empty:
        df = pd.DataFrame(columns=["o","h","l","c","v"])
        df.index = pd.to_datetime([])
    else:
        df = df.tail(max_bars)[["o","h","l","c","v"]]

    df = compute_indicators(df)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.03
    )

    # -------------------------
    # نمودار قیمت + اندیکاتورها
    # -------------------------

    if not df.empty:

        # کندل‌ها
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

        # SMAها
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA20"], mode="lines",
            name="SMA20", line=dict(color="blue")
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA100"], mode="lines",
            name="SMA100", line=dict(color="orange")
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA200"], mode="lines",
            name="SMA200", line=dict(color="purple")
        ), row=1, col=1)

        # WMA20
        fig.add_trace(go.Scatter(
            x=df.index, y=df["WMA20"], mode="lines",
            name="WMA20", line=dict(color="green", width=2, dash="dot")
        ), row=1, col=1)

        # -------------------------
        # خط افقی پایان سیکل
        # -------------------------

        last_price = df["c"].iloc[-1]

        fig.add_hline(
            y=last_price,
            line=dict(color="purple", width=2),
            row=1, col=1
        )

    # -------------------------
    # تنظیمات نهایی نمودار
    # -------------------------

    fig.update_layout(
        title=f"{symbol} – {interval}",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=900
    )

    png_path = os.path.join(CHARTS_DIR, png_name)

    try:
        fig.write_image(png_path, width=1800, height=1100, scale=3)
    except Exception:
        png_path = None

    return {
        "symbol":    symbol,
        "interval":  interval,
        "png_path":  png_path,
        "created_at":now_utc_str(),
        "wma":       df["WMA20"].tolist()      if "WMA20"      in df.columns else [],
        "wma_slope": df["WMA20_slope"].tolist()if "WMA20_slope"in df.columns else [],
        "sma20":     df["SMA20"].tolist()      if "SMA20"      in df.columns else [],
        "sma100":    df["SMA100"].tolist()     if "SMA100"     in df.columns else [],
        "sma200":    df["SMA200"].tolist()     if "SMA200"     in df.columns else []
    }


# =========================
# تشخیص آلارم‌ها
# =========================

def detect_alarms(cfg: dict, info: dict, group: str, cycle_time: str, cycle_items: list):
    alarms = []

    wma    = info["wma"]
    slope  = info["wma_slope"]
    sma20  = info["sma20"]
    sma100 = info["sma100"]
    sma200 = info["sma200"]

    # اگر دیتا کافی نیست
    if len(wma) < 3:
        return alarms

    # -------------------------
    # جهت WMA20
    # -------------------------
    if cfg.get("alarm_wma_direction", True):
        if slope[-2] < 0 and slope[-1] > 0:
            alarms.append("WMA20 جهت رو به بالا گرفت")

        if slope[-2] > 0 and slope[-1] < 0:
            alarms.append("WMA20 جهت رو به پایین گرفت")

    # -------------------------
    # برخورد WMA با SMAها
    # -------------------------

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

    # -------------------------
    # جهت SMAها
    # -------------------------

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

    # -------------------------
    # ذخیره‌سازی آلارم‌ها در سیکل جاری
    # -------------------------

    if alarms:
        cycle_items.append({
            "symbol":  info["symbol"],
            "interval":info["interval"],
            "time":    info["created_at"],
            "alarms":  alarms
        })

    return alarms


# =========================
# ذخیره‌سازی آلارم‌ها (۱۰ سیکل آخر)
# =========================

def store_cycle_alarms(group: str, cycle_time: str, cycle_items: list):
    cfg = load_config()

    # اگر گزارش آلارم‌ها فعال نیست → ذخیره نکن
    if not cfg.get("alarm_report_enabled", False):
        return

    # اگر هیچ آلارمی نبود → ذخیره نکن
    if not cycle_items:
        return

    # اضافه کردن سیکل جدید
    ALARM_HISTORY[group].append({
        "cycle_time": cycle_time,
        "items": cycle_items
    })

    # فقط ۱۰ سیکل آخر
    if len(ALARM_HISTORY[group]) > 10:
        ALARM_HISTORY[group] = ALARM_HISTORY[group][-10:]

    save_alarm_history()


# =========================
# اجرای یک سیکل کامل
# =========================

def run_cycle_once(group: str, bot, chat_id: int, symbols: list, interval: str,
                   lookback_days: int, max_bars: int):

    cfg       = load_config()
    verbose   = cfg.get(f"verbose_{group}", True)
    batch_size= cfg.get("cycle_progress_batch", 5)
    lock      = CYCLE_LOCKS[group]

    bars_per_chart = cfg.get("bars_per_chart", max_bars)
    bars_per_chart = max(30, min(bars_per_chart, max_bars))

    cycle_time  = now_utc_str()
    cycle_items = []

    # جلوگیری از اجرای همزمان
    if not lock.acquire(blocking=False):
        return

    try:
        # شروع سیکل
        if verbose:
            bot.send_message(chat_id, f"شروع چرخه {group}\n{cycle_time} UTC")

        unique_symbols = list(dict.fromkeys(symbols))
        total     = len(unique_symbols)
        processed = 0

        for sym in unique_symbols:
            processed += 1

            # گزارش پیشرفت
            if verbose and (processed % batch_size == 0 or processed == 1 or processed == total):
                bot.send_message(chat_id, f"چرخه {group}: {processed}/{total}")

            ts  = now_utc().strftime("%Y%m%d_%H%M%S")
            png = f"{group}_{sym}_{ts}.png"

            # ساخت نمودار
            info   = create_plotly_chart(sym, interval, lookback_days, bars_per_chart, png)

            # تشخیص آلارم‌ها
            alarms = detect_alarms(cfg, info, group, cycle_time, cycle_items)

            # حالت verbose → همه نمودارها  
            # حالت غیر verbose → فقط نمودارهای آلارم‌دار
            send_this_chart = verbose or bool(alarms)

            if send_this_chart and info["png_path"]:
                caption = f"{sym} ({group})"

                if alarms:
                    caption += "\n🔔 آلارم‌ها:"
                    for a in alarms:
                        caption += f"\n - {a}"

                # ارسال نمودار
                with open(info["png_path"], "rb") as f:
                    bot.send_photo(chat_id, f, caption=caption)

            time.sleep(0.3)

        # ذخیره آلارم‌های این سیکل
        store_cycle_alarms(group, cycle_time, cycle_items)

    finally:
        lock.release()


# =========================
# اجرای چرخه‌ها از منوی اصلی
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "🔵 اجرای چرخه‌ها")
def run_cycles_menu(m):
    kb = types.InlineKeyboardMarkup()

    kb.add(types.InlineKeyboardButton("اجرای چرخه 1h",  callback_data="run_1h"))
    kb.add(types.InlineKeyboardButton("اجرای چرخه 4h",  callback_data="run_4h"))
    kb.add(types.InlineKeyboardButton("اجرای چرخه 1d",  callback_data="run_1d"))
    kb.add(types.InlineKeyboardButton("اجرای چرخه 15m", callback_data="run_15m"))

    bot_1h.send_message(m.chat.id, "انتخاب چرخه:", reply_markup=kb)


@bot_1h.callback_query_handler(func=lambda c: c.data.startswith("run_"))
def run_cycles_handler(c):
    cfg = load_config()
    chat_id = c.message.chat.id

    if c.data == "run_1h":
        run_cycle_once("1h", bot_1h, chat_id, cfg["symbols_1h"], "1h", cfg["lookback_1h"], cfg["max_bars"])

    elif c.data == "run_4h":
        run_cycle_once("4h", bot_4h, chat_id, cfg["symbols_4h"], "4h", cfg["lookback_4h"], cfg["max_bars"])

    elif c.data == "run_1d":
        run_cycle_once("1d", bot_1d, chat_id, cfg["symbols_1d"], "1d", cfg["lookback_1d"], cfg["max_bars"])

    elif c.data == "run_15m":
        run_cycle_once("15m", bot_15m, chat_id, cfg["symbols_15m"], "15m", cfg["lookback_15m"], cfg["max_bars"])

    bot_1h.answer_callback_query(c.id, "چرخه اجرا شد.")

# =========================
# اجرای خودکار چرخه‌ها (Loop اصلی)
# =========================

def auto_cycle_loop(group: str, bot, interval: str, get_symbols, get_lookback):
    while True:
        try:
            cfg = load_config()

            # اگر این تایم‌فریم غیرفعال شده باشد → رد شو
            if not cfg.get(f"enable_{group}", True):
                time.sleep(5)
                continue

            chat_id = cfg.get(f"chat_id_{group}", None)
            if not chat_id:
                time.sleep(5)
                continue

            symbols  = cfg.get(get_symbols, [])
            lookback = cfg.get(get_lookback, 5)
            max_bars = cfg.get("max_bars", 300)

            run_cycle_once(group, bot, chat_id, symbols, interval, lookback, max_bars)

        except Exception as e:
            print(f"[ERROR auto_cycle_loop {group}] {e}")

        # فاصله زمانی اجرای خودکار
        if group == "15m":
            time.sleep(15 * 60)
        elif group == "1h":
            time.sleep(60 * 60)
        elif group == "4h":
            time.sleep(4 * 60 * 60)
        elif group == "1d":
            time.sleep(24 * 60 * 60)


# =========================
# ساخت Thread برای هر تایم‌فریم
# =========================

def start_auto_threads():
    threads = []

    if bot_15m:
        t15 = threading.Thread(
            target=auto_cycle_loop,
            args=("15m", bot_15m, "15m", "symbols_15m", "lookback_15m"),
            daemon=True
        )
        threads.append(t15)

    if bot_1h:
        t1h = threading.Thread(
            target=auto_cycle_loop,
            args=("1h", bot_1h, "1h", "symbols_1h", "lookback_1h"),
            daemon=True
        )
        threads.append(t1h)

    if bot_4h:
        t4h = threading.Thread(
            target=auto_cycle_loop,
            args=("4h", bot_4h, "4h", "symbols_4h", "lookback_4h"),
            daemon=True
        )
        threads.append(t4h)

    if bot_1d:
        t1d = threading.Thread(
            target=auto_cycle_loop,
            args=("1d", bot_1d, "1d", "symbols_1d", "lookback_1d"),
            daemon=True
        )
        threads.append(t1d)

    # شروع همه Threadها
    for t in threads:
        t.start()


# =========================
# شروع ربات‌ها
# =========================

if __name__ == "__main__":
    load_alarm_history()
    start_auto_threads()

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
        time.sleep(1)