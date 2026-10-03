# -*- coding: utf-8 -*-
# Modu Bazler v7.9 – Multi-bot Plotly (ارتقا یافته با تجمیع آلارم‌ها)
# اصلاح‌ها:
# - جلوگیری از اجرای هم‌زمان بات با هندل 409 و فاصلهٔ زمانی بین تلاش‌ها
# - استفاده از آفست +۳:۳۰ در زمان‌ها (گزارش آلارم، سیکل‌ها، راهنما)
# - اطمینان از ارسال پیام خلاصهٔ سیکل
# - تنظیمات پیشرفته با کلید تلگرام، بدون حذف هیچ عملکردی
# - بررسی ساخت عکس و PDF و لاگ خطا در صورت مشکل
# - در پایان هر سیکل: ساخت عکس تجمیعی فقط از ارزهای آلارم‌دار (حداکثر ۱۲ در هر صفحه) و ارسال به همان ربات

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
# مسیرها و کانفیگ
# =========================

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH        = os.path.join(DATA_DIR, "config_v7_9.json")
ALARM_HISTORY_PATH = os.path.join(DATA_DIR, "alarm_history_v7_9.json")

ALL_SYMBOLS_100 = [
    "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT","TRXUSDT","LINKUSDT","MATICUSDT",
    "LTCUSDT","DOTUSDT","AVAXUSDT","UNIUSDT","ATOMUSDT","XLMUSDT","ETCUSDT","NEARUSDT","OPUSDT","ARBUSDT",
    "AAVEUSDT","ALGOUSDT","APTUSDT","AXSUSDT","BCHUSDT","CAKEUSDT","CHZUSDT","CRVUSDT","DYDXUSDT","EGLDUSDT",
    "ENSUSDT","FTMUSDT","GALAUSDT","GMTUSDT","IMXUSDT","INJUSDT","KAVAUSDT","KLAYUSDT","LDOUSDT","MANAUSDT",
    "MASKUSDT","MINAUSDT","PEPEUSDT","QNTUSDT","RNDRUSDT","ROSEUSDT","RUNEUSDT","SANDUSDT","SFPUSDT","SNXUSDT",
    "STXUSDT","SUIUSDT","THETAUSDT","TWTUSDT","VETUSDT","WOOUSDT","XECUSDT","XMRUSDT","ZECUSDT","ZILUSDT",
    "AGIXUSDT","BANDUSDT","COMPUSDT","CTSIUSDT","FLMUSDT","HFTUSDT","HOOKUSDT","ICPUSDT","LRCUSDT","MAGICUSDT",
    "MKRUSDT","NKNUSDT","OCEANUSDT","ONEUSDT","PENDLEUSDT","PYRUSDT","RLCUSDT","RSRUSDT","SKLUSDT","STORJUSDT",
    "SXPUSDT","TRBUSDT","UMAUSDT","WAVESUSDT","YFIUSDT","ZRXUSDT","BELUSDT","COTIUSDT","DODOUSDT","FETUSDT",
    "GRTUSDT","HNTUSDT","HOTUSDT","IOSTUSDT","KSMUSDT","OGNUSDT","RENUSDT","RIFUSDT","SCRTUSDT","XVGUSDT"
]

DEFAULT_CONFIG = {
    "symbols_1h":   ALL_SYMBOLS_100.copy(),
    "symbols_4h":   ALL_SYMBOLS_100.copy(),
    "symbols_1d":   ALL_SYMBOLS_100.copy(),
    "symbols_15m":  ALL_SYMBOLS_100[:75],

    "lookback_1h":  5,
    "lookback_4h":  15,
    "lookback_1d":  180,
    "lookback_15m": 3,

    "max_bars":       800,
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

    "verbose_1h":   False,
    "verbose_4h":   False,
    "verbose_1d":   False,
    "verbose_15m":  False,

    "cycle_progress_batch": 5,

    "lock_timeout_sec":      600,

    "enable_1h":   True,
    "enable_4h":   True,
    "enable_1d":   True,
    "enable_15m":  True,
}

ALARM_HISTORY = {
    "1h":  [],
    "4h":  [],
    "1d":  [],
    "15m": []
}

LAST_MSG_ID  = {}

TOKEN_1H   = (os.getenv("TOKEN_1H") or "").strip()
TOKEN_4H   = (os.getenv("TOKEN_4H") or "").strip()
TOKEN_1D   = (os.getenv("TOKEN_1D") or "").strip()
TOKEN_15M  = (os.getenv("TOKEN_15M") or "").strip()
ADMIN_CHAT = (os.getenv("ADMIN_CHAT_ID") or "").strip()

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_local():
    return now_utc() + dt.timedelta(hours=3, minutes=30)

def now_local_str():
    return now_local().strftime("%Y-%m-%d %H:%M:%S")

def debug_mark(bot, chat_id, code: int, where: str):
    msg = f"TEST#{code} @ {where}"
    try:
        if bot and chat_id:
            bot.send_message(int(chat_id), msg)
        elif ADMIN_CHAT and bot:
            bot.send_message(int(ADMIN_CHAT), msg)
    except:
        pass

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

def reset_config():
    cfg = DEFAULT_CONFIG.copy()
    save_config(cfg)
    return cfg

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
    if not token or not isinstance(token, str):
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
# SmartLock + وضعیت چرخه‌ها
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

    def force_release(self):
        try:
            if self.lock.locked():
                self.lock.release()
        except:
            pass
        self.last_acquire = None

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

def force_clear_all_locks():
    for g, lk in CYCLE_LOCKS.items():
        lk.force_release()

@bot_1h.message_handler(func=lambda m: m.text == "🔴 وضعیت چرخه‌ها")
def cycles_status(m):
    txt = "وضعیت چرخه‌ها (زمان‌ها بر اساس آفست +۳:۳۰):\n"
    for g in ["1h","4h","1d","15m"]:
        lk = CYCLE_LOCKS[g]
        locked = lk.lock.locked()
        last   = lk.last_acquire
        if last:
            last_local = (last + dt.timedelta(hours=3, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            last_local = "None"
        txt += f"- {g}: locked={locked}, last_acquire={last_local}\n"
    bot_1h.send_message(m.chat.id, txt)

# =========================
# راهنما
# =========================

HELP_TEXT = """
راهنمای Modu Bazler v7.9 (چندرباته Plotly):

🔵 منوی اصلی:
- چک یک نماد
- اجرای دستی 1h / فوری 4h / فوری 1d / فوری 15m
- اجرای چرخه‌ها (همهٔ تایم‌فریم‌ها)

🟢 مدیریت نمادها:
- مدیریت نمادهای 1h / 4h / 1d / 15m
- افزودن / حذف / نمایش نمادها

🟡 آلارم‌ها:
- تنظیم آلارم‌ها (WMA و SMA)
- گزارش آلارم‌ها (تاریخچه تا ۱۹ سیکل آخر هر گروه، با زمان محلی +۳:۳۰)

🔴 تنظیمات و وضعیت:
- وضعیت سیستم
- وضعیت چرخه‌ها
- تنظیمات پیشرفته
- ریست برنامه
- رفع خطای قفل‌ها

🟣 سایر:
- راهنما
- رفرش منو

زمان‌بندی خودکار (بر اساس زمان محلی +۳:۳۰):
- سیکل 1h: هر ساعت در دقیقه 22
- سیکل 4h: ساعت‌های 2، 6، 10، 14، 18، 22 در دقیقه 7
- سیکل 1d: ساعت 1:05
- سیکل 15m: هر ۱۵ دقیقه

پایان هر سیکل، پیام خلاصهٔ سیکل حتماً به ربات ارسال می‌شود.
"""

# =========================
# منوی اصلی
# =========================

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔵 چک یک نماد", "🔵 اجرای دستی 1h")
    kb.row("🔵 اجرای فوری 4h", "🔵 اجرای فوری 1d")
    kb.row("🔵 اجرای فوری 15m")
    kb.row("🟢 مدیریت نمادهای 1h", "🟢 مدیریت نمادهای 4h")
    kb.row("🟢 مدیریت نمادهای 1d", "🟢 مدیریت نمادهای 15m")
    kb.row("🟡 تنظیم آلارم‌ها", "🟡 گزارش آلارم‌ها")
    kb.row("🔴 وضعیت سیستم", "🔴 وضعیت چرخه‌ها")
    kb.row("🔴 تنظیمات پیشرفته", "🔵 اجرای چرخه‌ها")
    kb.row("🔴 ریست برنامه", "🔴 رفع خطای قفل‌ها")
    kb.row("🟣 راهنما", "🟣 رفرش منو")
    bot_1h.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

@bot_1h.message_handler(commands=["start"])
def start_main(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    load_alarm_history()
    bot_1h.send_message(m.chat.id, HELP_TEXT)
    send_main_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "🟣 رفرش منو")
def refresh_main(m):
    send_main_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "🔴 ریست برنامه")
def reset_app(m):
    reset_config()
    for g in ["1h","4h","1d","15m"]:
        ALARM_HISTORY[g] = []
    save_alarm_history()
    bot_1h.send_message(m.chat.id, "تنظیمات و تاریخچه آلارم‌ها به حالت اولیه برگشت.")
    send_main_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "🔴 رفع خطای قفل‌ها")
def clear_locks_cmd(m):
    force_clear_all_locks()
    bot_1h.send_message(m.chat.id, "همهٔ قفل‌ها آزاد شدند.")

@bot_1h.message_handler(func=lambda m: m.text == "🟣 راهنما")
def help_menu(m):
    bot_1h.send_message(m.chat.id, HELP_TEXT)

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
    txt = f"نمادهای فعال در {group}:\n" + ", ".join(symbols)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(f"افزودن نماد به {group}", f"حذف نماد از {group}")
    kb.row(f"نمایش نمادهای {group}")
    kb.row("بازگشت به منوی اصلی")
    bot_1h.send_message(chat_id, txt, reply_markup=kb)

@bot_1h.message_handler(func=lambda m: m.text == "🟢 مدیریت نمادهای 1h")
def manage_1h(m):
    show_symbol_menu(m.chat.id, "1h")

@bot_1h.message_handler(func=lambda m: m.text == "🟢 مدیریت نمادهای 4h")
def manage_4h(m):
    show_symbol_menu(m.chat.id, "4h")

@bot_1h.message_handler(func=lambda m: m.text == "🟢 مدیریت نمادهای 1d")
def manage_1d(m):
    show_symbol_menu(m.chat.id, "1d")

@bot_1h.message_handler(func=lambda m: m.text == "🟢 مدیریت نمادهای 15m")
def manage_15m(m):
    show_symbol_menu(m.chat.id, "15m")

@bot_1h.message_handler(func=lambda m: m.text.startswith("افزودن نماد به "))
def add_symbol_any(m):
    group = m.text.split()[-1]
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید:")
    bot_1h.register_next_step_handler(msg, lambda mm: add_symbol_step(mm, group))

def add_symbol_step(m, group):
    sym = m.text.strip().upper()
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    if sym not in symbols:
        symbols.append(sym)
        set_symbols(cfg, group, symbols)
        bot_1h.send_message(m.chat.id, f"{sym} اضافه شد.")
    else:
        bot_1h.send_message(m.chat.id, f"{sym} قبلاً وجود دارد.")
    show_symbol_menu(m.chat.id, group)

@bot_1h.message_handler(func=lambda m: m.text.startswith("حذف نماد از "))
def remove_symbol_any(m):
    group = m.text.split()[-1]
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید:")
    bot_1h.register_next_step_handler(msg, lambda mm: remove_symbol_step(mm, group))

def remove_symbol_step(m, group):
    sym = m.text.strip().upper()
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    if sym in symbols:
        symbols.remove(sym)
        set_symbols(cfg, group, symbols)
        bot_1h.send_message(m.chat.id, f"{sym} حذف شد.")
    else:
        bot_1h.send_message(m.chat.id, f"{sym} وجود ندارد.")
    show_symbol_menu(m.chat.id, group)

@bot_1h.message_handler(func=lambda m: m.text.startswith("نمایش نمادهای "))
def show_symbols_any(m):
    group = m.text.split()[-1]
    cfg = load_config()
    symbols = get_symbols(cfg, group)
    bot_1h.send_message(m.chat.id, ", ".join(symbols))

# =========================
# تنظیم آلارم‌ها
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "🟡 تنظیم آلارم‌ها")
def alarm_settings(m):
    cfg = load_config()
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(f"WMA جهت ({'ON' if cfg['alarm_wma_direction'] else 'OFF'})")
    kb.row(f"Cross SMA20 ({'ON' if cfg['alarm_cross_sma20'] else 'OFF'})")
    kb.row(f"Cross SMA100 ({'ON' if cfg['alarm_cross_sma100'] else 'OFF'})")
    kb.row(f"Cross SMA200 ({'ON' if cfg['alarm_cross_sma200'] else 'OFF'})")
    kb.row(f"جهت SMA20 ({'ON' if cfg['alarm_sma20_direction'] else 'OFF'})")
    kb.row(f"جهت SMA100 ({'ON' if cfg['alarm_sma100_direction'] else 'OFF'})")
    kb.row(f"جهت SMA200 ({'ON' if cfg['alarm_sma200_direction'] else 'OFF'})")
    kb.row("بازگشت به منوی اصلی")
    bot_1h.send_message(m.chat.id, "تنظیم آلارم‌ها:", reply_markup=kb)

@bot_1h.message_handler(func=lambda m: m.text.startswith("WMA جهت"))
def toggle_wma_dir(m):
    cfg = load_config()
    cfg["alarm_wma_direction"] = not cfg["alarm_wma_direction"]
    save_config(cfg)
    alarm_settings(m)

@bot_1h.message_handler(func=lambda m: m.text.startswith("Cross SMA20"))
def toggle_cross_20(m):
    cfg = load_config()
    cfg["alarm_cross_sma20"] = not cfg["alarm_cross_sma20"]
    save_config(cfg)
    alarm_settings(m)

@bot_1h.message_handler(func=lambda m: m.text.startswith("Cross SMA100"))
def toggle_cross_100(m):
    cfg = load_config()
    cfg["alarm_cross_sma100"] = not cfg["alarm_cross_sma100"]
    save_config(cfg)
    alarm_settings(m)

@bot_1h.message_handler(func=lambda m: m.text.startswith("Cross SMA200"))
def toggle_cross_200(m):
    cfg = load_config()
    cfg["alarm_cross_sma200"] = not cfg["alarm_cross_sma200"]
    save_config(cfg)
    alarm_settings(m)

@bot_1h.message_handler(func=lambda m: m.text.startswith("جهت SMA20"))
def toggle_dir_20(m):
    cfg = load_config()
    cfg["alarm_sma20_direction"] = not cfg["alarm_sma20_direction"]
    save_config(cfg)
    alarm_settings(m)

@bot_1h.message_handler(func=lambda m: m.text.startswith("جهت SMA100"))
def toggle_dir_100(m):
    cfg = load_config()
    cfg["alarm_sma100_direction"] = not cfg["alarm_sma100_direction"]
    save_config(cfg)
    alarm_settings(m)

@bot_1h.message_handler(func=lambda m: m.text.startswith("جهت SMA200"))
def toggle_dir_200(m):
    cfg = load_config()
    cfg["alarm_sma200_direction"] = not cfg["alarm_sma200_direction"]
    save_config(cfg)
    alarm_settings(m)

# =========================
# دریافت دیتا
# =========================

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str) -> str:
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

def fetch_ohlc(symbol: str, interval: str, lookback_days: int, max_bars: int) -> pd.DataFrame:
    limit = max(1000, max_bars)

    try:
        url = "https://api.binance.com/api/v3/klines"
        r = requests.get(url, params={
            "symbol": symbol,
            "interval": _binance_interval(interval),
            "limit": limit
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        rows = [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in data]
        df = pd.DataFrame(rows, columns=["t","o","h","l","c","v"])
        df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
        df.set_index("t", inplace=True)
        return df
    except Exception:
        debug_mark(bot_1h, ADMIN_CHAT, 801, "fetch_ohlc_binance")

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
        rows = [[int(k[0]), float(k[1]), float(k[3]), float(k[4]), float(k[2]), float(k[5])] for k in data]
        df = pd.DataFrame(rows, columns=["t","o","h","l","c","v"])
        df["t"] = pd.to_datetime(df["t"], unit="s", utc=True)
        df.sort_values("t", inplace=True)
        df.set_index("t", inplace=True)
        return df
    except Exception:
        debug_mark(bot_1h, ADMIN_CHAT, 802, "fetch_ohlc_kucoin")
        return pd.DataFrame()

# =========================
# اندیکاتورها
# =========================

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df

    try:
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

    except Exception:
        debug_mark(bot_1h, ADMIN_CHAT, 803, "compute_indicators")

    return df

# =========================
# نمودار Plotly
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
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03
    )

    try:
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

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=wma_up,
                mode="lines",
                name="WMA20 Up",
                line=dict(color="green", width=2)
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=wma_down,
                mode="lines",
                name="WMA20 Down",
                line=dict(color="red", width=2)
            ),
            row=1, col=1
        )

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

    except Exception:
        debug_mark(bot_1h, ADMIN_CHAT, 804, "create_plotly_chart_build")

    png_path = os.path.join(CHARTS_DIR, png_name)

    try:
        fig.write_image(png_path, width=1800, height=1100, scale=3)
    except Exception as e:
        debug_mark(bot_1h, ADMIN_CHAT, 805, f"create_plotly_chart_write_{e}")
        png_path = None

    return {
        "symbol":    symbol,
        "interval":  interval,
        "png_path":  png_path,
        "created_at":now_local_str(),
        "wma":       df["WMA20"].tolist()      if "WMA20"      in df.columns else [],
        "wma_slope": df["WMA20_slope"].tolist()if "WMA20_slope"in df.columns else [],
        "sma20":     df["SMA20"].tolist()      if "SMA20"      in df.columns else [],
        "sma100":    df["SMA100"].tolist()     if "SMA100"     in df.columns else [],
        "sma200":    df["SMA200"].tolist()     if "SMA200"     in df.columns else []
    }

# =========================
# آلارم‌ها
# =========================

def detect_alarms(cfg: dict, info: dict, group: str, cycle_time: str, cycle_items: list):
    alarms = []
    wma    = info["wma"]
    slope  = info["wma_slope"]
    sma20  = info["sma20"]
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
        cycle_items.append({
            "symbol":  info["symbol"],
            "interval":info["interval"],
            "time":    info["created_at"],
            "alarms":  alarms
        })

    return alarms

def store_cycle_alarms(group: str, cycle_time: str, cycle_items: list):
    if not cycle_items:
        return
    ALARM_HISTORY[group].append({
        "cycle_time": cycle_time,
        "items": cycle_items
    })
    if len(ALARM_HISTORY[group]) > 19:
        ALARM_HISTORY[group] = ALARM_HISTORY[group][-19:]
    save_alarm_history()

# =========================
# گزارش آلارم‌ها
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "🟡 گزارش آلارم‌ها")
def alarms_report(m):
    load_alarm_history()
    txt = "گزارش آلارم‌ها (تا ۱۹ سیکل آخر هر تایم‌فریم، زمان محلی +۳:۳۰):\n\n"

    for group in ["15m", "1h", "4h", "1d"]:
        history = ALARM_HISTORY.get(group, [])
        txt += f"🔹 تایم‌فریم {group}:\n"

        if not history:
            txt += "  هنوز آلارمی ثبت نشده است.\n\n"
            continue

        for idx, cycle in enumerate(history[::-1], start=1):
            txt += f"  🕒 سیکل #{idx} در زمان: {cycle['cycle_time']}\n"
            for item in cycle["items"]:
                txt += f"    • {item['symbol']} ({item['interval']}):\n"
                for a in item["alarms"]:
                    txt += f"      - {a}\n"
                txt += f"      زمان آلارم: {item['time']}\n"
            txt += "\n"

        txt += "\n"

    bot_1h.send_message(m.chat.id, txt)

# =========================
# چک یک نماد
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "🔵 چک یک نماد")
def check_one_symbol(m):
    msg = bot_1h.send_message(m.chat.id, "نماد را وارد کنید (مثال: BTCUSDT):")
    bot_1h.register_next_step_handler(msg, do_check_one_symbol)

def do_check_one_symbol(m):
    sym = m.text.strip().upper()
    cfg = load_config()
    bars = cfg.get("bars_per_chart", 90)
    bars = max(30, min(bars, cfg.get("max_bars", 300)))

    ts  = now_local().strftime("%Y%m%d_%H%M%S")
    png = f"check_{sym}_{ts}.png"

    info   = create_plotly_chart(sym, "1h", cfg["lookback_1h"], bars, png)
    cycle_time  = now_local_str()
    cycle_items = []
    alarms = detect_alarms(cfg, info, "1h", cycle_time, cycle_items)

    store_cycle_alarms("1h", cycle_time, cycle_items)

    caption = f"{sym} (چک 1h)"
    if alarms:
        caption += "\n🔔 آلارم‌ها:"
        for a in alarms:
            caption += f"\n - {a}"

    if sym in LAST_MSG_ID:
        caption += f"\n🔗 نمودار قبلی: https://t.me/c/{m.chat.id}/{LAST_MSG_ID[sym]}"

    if info["png_path"]:
        try:
            with open(info["png_path"], "rb") as f:
                msg = bot_1h.send_photo(m.chat.id, f, caption=caption)
            LAST_MSG_ID[sym] = msg.message_id
        except Exception as e:
            debug_mark(bot_1h, ADMIN_CHAT, 810, f"check_one_symbol_send_{e}")
            bot_1h.send_message(m.chat.id, caption + "\n⚠️ خطا در ارسال عکس.")
    else:
        bot_1h.send_message(m.chat.id, caption + "\n⚠️ عکس ساخته نشد.")

# =========================
# وضعیت سیستم
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "🔴 وضعیت سیستم")
def system_status(m):
    cfg = load_config()
    txt = "وضعیت سیستم:\n"
    txt += f"نمادهای 1h: {len(cfg['symbols_1h'])}\n"
    txt += f"نمادهای 4h: {len(cfg['symbols_4h'])}\n"
    txt += f"نمادهای 1d: {len(cfg['symbols_1d'])}\n"
    txt += f"نمادهای 15m: {len(cfg['symbols_15m'])}\n"
    txt += f"bars_per_chart: {cfg.get('bars_per_chart', 90)}\n"
    txt += f"PDF 1h: {'ON' if cfg['make_pdf_1h'] else 'OFF'}\n"
    txt += f"PDF 1d: {'ON' if cfg['make_pdf_1d'] else 'OFF'}\n"
    txt += f"Combined 15m: {'ON' if cfg.get('make_combined_15m', True) else 'OFF'}\n"
    txt += f"Combined all: {'ON' if cfg.get('make_combined_all', True) else 'OFF'}\n"
    txt += f"verbose 1h: {'ON' if cfg['verbose_1h'] else 'OFF'}\n"
    txt += f"verbose 4h: {'ON' if cfg['verbose_4h'] else 'OFF'}\n"
    txt += f"verbose 1d: {'ON' if cfg['verbose_1d'] else 'OFF'}\n"
    txt += f"verbose 15m: {'ON' if cfg['verbose_15m'] else 'OFF'}\n"
    txt += f"enable_1h: {'ON' if cfg.get('enable_1h', True) else 'OFF'}\n"
    txt += f"enable_4h: {'ON' if cfg.get('enable_4h', True) else 'OFF'}\n"
    txt += f"enable_1d: {'ON' if cfg.get('enable_1d', True) else 'OFF'}\n"
    txt += f"enable_15m: {'ON' if cfg.get('enable_15m', True) else 'OFF'}\n"
    txt += f"lock_timeout_sec: {cfg.get('lock_timeout_sec', 600)}\n"
    bot_1h.send_message(m.chat.id, txt)

# =========================
# تنظیمات پیشرفته (ReplyKeyboard)
# =========================

def send_advanced_menu(chat_id):
    cfg = load_config()
    txt = "تنظیمات پیشرفته:\n"
    txt += f"PDF 1h: {'ON' if cfg['make_pdf_1h'] else 'OFF'}\n"
    txt += f"PDF 1d: {'ON' if cfg['make_pdf_1d'] else 'OFF'}\n"
    txt += f"Combined 15m: {'ON' if cfg.get('make_combined_15m', True) else 'OFF'}\n"
    txt += f"Combined all: {'ON' if cfg.get('make_combined_all', True) else 'OFF'}\n"
    txt += f"bars_per_chart: {cfg.get('bars_per_chart', 90)}\n"
    txt += f"verbose 1h: {'ON' if cfg['verbose_1h'] else 'OFF'}\n"
    txt += f"verbose 4h: {'ON' if cfg['verbose_4h'] else 'OFF'}\n"
    txt += f"verbose 1d: {'ON' if cfg['verbose_1d'] else 'OFF'}\n"
    txt += f"verbose 15m: {'ON' if cfg['verbose_15m'] else 'OFF'}\n"
    txt += f"enable 1h: {'ON' if cfg.get('enable_1h', True) else 'OFF'}\n"
    txt += f"enable 4h: {'ON' if cfg.get('enable_4h', True) else 'OFF'}\n"
    txt += f"enable 1d: {'ON' if cfg.get('enable_1d', True) else 'OFF'}\n"
    txt += f"enable 15m: {'ON' if cfg.get('enable_15m', True) else 'OFF'}\n"

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("PDF 1h", "PDF 1d")
    kb.row("Combined 15m", "Combined all")
    kb.row("کندل +30", "کندل -30")
    kb.row("verbose 1h", "verbose 4h")
    kb.row("verbose 1d", "verbose 15m")
    kb.row("enable 1h", "enable 4h")
    kb.row("enable 1d", "enable 15m")
    kb.row("ریست کامل برنامه", "بازگشت به منوی اصلی")
    bot_1h.send_message(chat_id, txt, reply_markup=kb)

@bot_1h.message_handler(func=lambda m: m.text == "🔴 تنظیمات پیشرفته")
def advanced_settings(m):
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "PDF 1h")
def adv_pdf_1h(m):
    cfg = load_config()
    cfg["make_pdf_1h"] = not cfg["make_pdf_1h"]
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "PDF 1d")
def adv_pdf_1d(m):
    cfg = load_config()
    cfg["make_pdf_1d"] = not cfg["make_pdf_1d"]
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "Combined 15m")
def adv_combined_15m(m):
    cfg = load_config()
    cfg["make_combined_15m"] = not cfg.get("make_combined_15m", True)
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "Combined all")
def adv_combined_all(m):
    cfg = load_config()
    cfg["make_combined_all"] = not cfg.get("make_combined_all", True)
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "کندل +30")
def adv_bars_plus(m):
    cfg = load_config()
    bars = cfg.get("bars_per_chart", 90) + 30
    if bars > cfg.get("max_bars", 300):
        bars = cfg.get("max_bars", 300)
    cfg["bars_per_chart"] = max(30, bars)
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "کندل -30")
def adv_bars_minus(m):
    cfg = load_config()
    bars = cfg.get("bars_per_chart", 90) - 30
    cfg["bars_per_chart"] = max(30, bars)
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "verbose 1h")
def adv_verbose_1h(m):
    cfg = load_config()
    cfg["verbose_1h"] = not cfg["verbose_1h"]
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "verbose 4h")
def adv_verbose_4h(m):
    cfg = load_config()
    cfg["verbose_4h"] = not cfg["verbose_4h"]
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "verbose 1d")
def adv_verbose_1d(m):
    cfg = load_config()
    cfg["verbose_1d"] = not cfg["verbose_1d"]
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "verbose 15m")
def adv_verbose_15m(m):
    cfg = load_config()
    cfg["verbose_15m"] = not cfg["verbose_15m"]
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "enable 1h")
def adv_enable_1h(m):
    cfg = load_config()
    cfg["enable_1h"] = not cfg.get("enable_1h", True)
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "enable 4h")
def adv_enable_4h(m):
    cfg = load_config()
    cfg["enable_4h"] = not cfg.get("enable_4h", True)
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "enable 1d")
def adv_enable_1d(m):
    cfg = load_config()
    cfg["enable_1d"] = not cfg.get("enable_1d", True)
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "enable 15m")
def adv_enable_15m(m):
    cfg = load_config()
    cfg["enable_15m"] = not cfg.get("enable_15m", True)
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler(func=lambda m: m.text == "ریست کامل برنامه")
def adv_reset_app(m):
    cfg = reset_config()
    for g in ["1h","4h","1d","15m"]:
        ALARM_HISTORY[g] = []
    save_alarm_history()
    save_config(cfg)
    bot_1h.send_message(m.chat.id, "ریست کامل انجام شد.")
    send_advanced_menu(m.chat.id)

# =========================
# عکس تجمیعی ۱۲تایی (همهٔ نمودارهای سیکل)
# =========================

def make_combined_pages(group: str, bot, chat_id: int, image_paths):
    if not image_paths:
        return

    pages = []
    page  = []

    for img in image_paths:
        if img is None:
            continue
        page.append(img)
        if len(page) == 12:
            pages.append(page)
            page = []

    if page:
        pages.append(page)

    for idx, pg in enumerate(pages, start=1):
        fig, axes = plt.subplots(3, 4, figsize=(16, 12))
        axes = axes.flatten()

        for ax, img_path in zip(axes, pg):
            try:
                img = plt.imread(img_path)
                ax.imshow(img)
                ax.axis("off")
            except Exception as e:
                ax.text(0.5, 0.5, "خطا در عکس", ha="center")
                debug_mark(bot, chat_id, 930, f"combined_read_{group}_{e}")

        for ax in axes[len(pg):]:
            ax.axis("off")

        out_path = os.path.join(CHARTS_DIR, f"combined_{group}_{idx}.png")
        plt.tight_layout()
        plt.savefig(out_path, dpi=150)
        plt.close()

        try:
            with open(out_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"📄 صفحه {idx} – عکس تجمیعی {group}")
        except Exception as e:
            debug_mark(bot, chat_id, 931, f"combined_send_{group}_{e}")

# =========================
# عکس تجمیعی مخصوص ارزهای آلارم‌دار (حداکثر ۱۲ در هر صفحه)
# =========================

def make_alarm_combined_pages(group: str, bot, chat_id: int, alarm_images):
    if not alarm_images:
        return

    pages = []
    page  = []

    for img in alarm_images:
        if img is None:
            continue
        page.append(img)
        if len(page) == 12:
            pages.append(page)
            page = []

    if page:
        pages.append(page)

    for idx, pg in enumerate(pages, start=1):
        fig, axes = plt.subplots(3, 4, figsize=(16, 12))
        axes = axes.flatten()

        for ax, img_path in zip(axes, pg):
            try:
                img = plt.imread(img_path)
                ax.imshow(img)
                ax.axis("off")
            except Exception as e:
                ax.text(0.5, 0.5, "خطا در عکس", ha="center")
                debug_mark(bot, chat_id, 940, f"alarm_combined_read_{group}_{e}")

        for ax in axes[len(pg):]:
            ax.axis("off")

        out_path = os.path.join(CHARTS_DIR, f"alarm_combined_{group}_{idx}.png")
        plt.tight_layout()
        plt.savefig(out_path, dpi=150)
        plt.close()

        try:
            with open(out_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"📄 صفحه آلارم‌ها {idx} – {group}")
        except Exception as e:
            debug_mark(bot, chat_id, 941, f"alarm_combined_send_{group}_{e}")

# =========================
# اجرای سیکل‌ها
# =========================

def run_cycle_once(group: str, bot, chat_id: int, symbols: list, interval: str,
                   lookback_days: int, max_bars: int, make_pdf: bool):

    cfg       = load_config()
    verbose   = cfg.get(f"verbose_{group}", True)
    batch_size= cfg.get("cycle_progress_batch", 5)
    lock      = CYCLE_LOCKS[group]

    bars_per_chart = cfg.get("bars_per_chart", max_bars)
    bars_per_chart = max(30, min(bars_per_chart, max_bars))

    cycle_time  = now_local_str()
    cycle_items = []

    if not lock.acquire(blocking=False):
        debug_mark(bot, chat_id, 902, f"run_cycle_lock_busy_{group}")
        return [], [], 0, cycle_time, cycle_items

    pdf          = None
    pdf_filename = None

    if make_pdf and group in ["1h", "1d"]:
        pdf_filename = os.path.join(PDF_DIR, f"{group}_{now_local().strftime('%Y%m%d_%H%M%S')}.pdf")
        try:
            pdf = PdfPages(pdf_filename)
        except Exception as e:
            debug_mark(bot, chat_id, 905, f"run_cycle_pdf_init_{group}_{e}")
            pdf = None
            bot.send_message(chat_id, f"⚠️ PDF {group} ساخته نشد.")

    all_images   = []
    alarm_images = []
    alarms_count = 0

    try:
        if verbose:
            bot.send_message(chat_id, f"شروع چرخه {group}\n{cycle_time} (محلی +۳:۳۰)")

        unique_symbols = list(dict.fromkeys(symbols))
        total     = len(unique_symbols)
        processed = 0

        for sym in unique_symbols:
            processed += 1

            if verbose and (processed % batch_size == 0 or processed == 1 or processed == total):
                bot.send_message(chat_id, f"چرخه {group}: {processed}/{total}")

            ts  = now_local().strftime("%Y%m%d_%H%M%S")
            png = f"{group}_{sym}_{ts}.png"

            info   = create_plotly_chart(sym, interval, lookback_days, bars_per_chart, png)
            alarms = detect_alarms(cfg, info, group, cycle_time, cycle_items)

            if info["png_path"]:
                all_images.append(info["png_path"])

            if alarms:
                alarms_count += len(alarms)
                if info["png_path"]:
                    alarm_images.append(info["png_path"])

            send_this_chart = False
            if verbose:
                send_this_chart = True
            else:
                if alarms:
                    send_this_chart = True

            if send_this_chart and info["png_path"]:
                caption = f"{sym} ({group})"
                if alarms:
                    caption += "\n🔔 آلارم‌ها:"
                    for a in alarms:
                        caption += f"\n - {a}"

                if sym in LAST_MSG_ID:
                    caption += f"\n🔗 نمودار قبلی: https://t.me/c/{chat_id}/{LAST_MSG_ID[sym]}"

                try:
                    with open(info["png_path"], "rb") as f:
                        msg = bot.send_photo(chat_id, f, caption=caption)
                    LAST_MSG_ID[sym] = msg.message_id
                except Exception as e:
                    debug_mark(bot, chat_id, 906, f"cycle_send_chart_{group}_{e}")

            if pdf is not None and info["png_path"]:
                try:
                    img = plt.imread(info["png_path"])
                    fig_pdf, ax_pdf = plt.subplots(figsize=(10, 6))
                    ax_pdf.imshow(img)
                    ax_pdf.axis("off")
                    pdf.savefig(fig_pdf)
                    plt.close(fig_pdf)
                except Exception as e:
                    debug_mark(bot, chat_id, 907, f"pdf_add_{group}_{e}")

            time.sleep(0.3)

        if pdf is not None:
            try:
                pdf.close()
                with open(pdf_filename, "rb") as f:
                    bot.send_document(chat_id, f, caption=f"گزارش PDF کامل سیکل {group}")
            except Exception as e:
                debug_mark(bot, chat_id, 908, f"pdf_send_{group}_{e}")
                bot.send_message(chat_id, f"⚠️ ارسال PDF {group} با خطا مواجه شد.")

        return all_images, alarm_images, alarms_count, cycle_time, cycle_items

    finally:
        lock.release()

def run_cycle(group: str, bot, chat_id: int, symbols: list, interval: str,
              lookback_days: int, max_bars: int, make_pdf: bool):

    cfg = load_config()

    if group == "1h"  and not cfg.get("enable_1h",  True): return
    if group == "4h"  and not cfg.get("enable_4h",  True): return
    if group == "1d"  and not cfg.get("enable_1d",  True): return
    if group == "15m" and not cfg.get("enable_15m", True): return

    all_images, alarm_images, alarms_count, cycle_time, cycle_items = run_cycle_once(
        group, bot, chat_id, symbols, interval, lookback_days, max_bars, make_pdf
    )

    store_cycle_alarms(group, cycle_time, cycle_items)

    if cfg.get("make_combined_all", True):
        make_combined_pages(group, bot, chat_id, all_images)

    total_symbols      = len(list(dict.fromkeys(symbols)))
    alarm_symbols      = len(cycle_items)
    total_alarms       = alarms_count

    summary = (
        f"📊 خلاصهٔ سیکل {group}\n"
        f"🕒 زمان سیکل (محلی +۳:۳۰): {cycle_time}\n"
        f"🔢 تعداد نمادها: {total_symbols}\n"
        f"🔔 نمادهای آلارم‌دار: {alarm_symbols}\n"
        f"📣 تعداد کل آلارم‌ها: {total_alarms}"
    )

    try:
        bot.send_message(chat_id, summary)
    except Exception as e:
        debug_mark(bot, chat_id, 909, f"cycle_summary_send_{group}_{e}")

    # ارسال عکس‌های تجمیعی مخصوص ارزهای آلارم‌دار
    if alarm_images:
        make_alarm_combined_pages(group, bot, chat_id, alarm_images)

# =========================
# اجرای دستی
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "🔵 اجرای دستی 1h")
def manual_1h(m):
    cfg = load_config()
    if not cfg.get("enable_1h", True):
        bot_1h.send_message(m.chat.id, "ربات 1h غیرفعال است.")
        return

    threading.Thread(
        target=lambda: run_cycle(
            "1h",
            bot_1h,
            m.chat.id,
            cfg["symbols_1h"],
            "1h",
            cfg["lookback_1h"],
            cfg["max_bars"],
            cfg["make_pdf_1h"]
        ),
        daemon=True
    ).start()

@bot_1h.message_handler(func=lambda m: m.text == "🔵 اجرای فوری 4h")
def manual_4h(m):
    cfg = load_config()
    if not cfg.get("enable_4h", True):
        bot_1h.send_message(m.chat.id, "ربات 4h غیرفعال است.")
        return

    threading.Thread(
        target=lambda: run_cycle(
            "4h",
            bot_4h or bot_1h,
            m.chat.id,
            cfg["symbols_4h"],
            "4h",
            cfg["lookback_4h"],
            cfg["max_bars"],
            False
        ),
        daemon=True
    ).start()

@bot_1h.message_handler(func=lambda m: m.text == "🔵 اجرای فوری 1d")
def manual_1d(m):
    cfg = load_config()
    if not cfg.get("enable_1d", True):
        bot_1h.send_message(m.chat.id, "ربات 1d غیرفعال است.")
        return

    threading.Thread(
        target=lambda: run_cycle(
            "1d",
            bot_1d or bot_1h,
            m.chat.id,
            cfg["symbols_1d"],
            "1d",
            cfg["lookback_1d"],
            cfg["max_bars"],
            cfg["make_pdf_1d"]
        ),
        daemon=True
    ).start()

@bot_1h.message_handler(func=lambda m: m.text == "🔵 اجرای فوری 15m")
def manual_15m(m):
    cfg = load_config()
    if not cfg.get("enable_15m", True):
        bot_1h.send_message(m.chat.id, "ربات 15m غیرفعال است.")
        return

    threading.Thread(
        target=lambda: run_cycle(
            "15m",
            bot_15m or bot_1h,
            m.chat.id,
            cfg["symbols_15m"],
            "15m",
            cfg["lookback_15m"],
            cfg["max_bars"],
            False
        ),
        daemon=True
    ).start()

@bot_1h.message_handler(func=lambda m: m.text == "🔵 اجرای چرخه‌ها")
def run_all_cycles(m):
    cfg = load_config()

    bot_1h.send_message(m.chat.id, "اجرای همهٔ سیکل‌ها شروع شد.")

    if cfg.get("enable_1h", True):
        threading.Thread(
            target=lambda: run_cycle(
                "1h",
                bot_1h,
                m.chat.id,
                cfg["symbols_1h"],
                "1h",
                cfg["lookback_1h"],
                cfg["max_bars"],
                cfg["make_pdf_1h"]
            ),
            daemon=True
        ).start()

    if cfg.get("enable_4h", True):
        threading.Thread(
            target=lambda: run_cycle(
                "4h",
                bot_4h or bot_1h,
                m.chat.id,
                cfg["symbols_4h"],
                "4h",
                cfg["lookback_4h"],
                cfg["max_bars"],
                False
            ),
            daemon=True
        ).start()

    if cfg.get("enable_1d", True):
        threading.Thread(
            target=lambda: run_cycle(
                "1d",
                bot_1d or bot_1h,
                m.chat.id,
                cfg["symbols_1d"],
                "1d",
                cfg["lookback_1d"],
                cfg["max_bars"],
                cfg["make_pdf_1d"]
            ),
            daemon=True
        ).start()

    if cfg.get("enable_15m", True):
        threading.Thread(
            target=lambda: run_cycle(
                "15m",
                bot_15m or bot_1h,
                m.chat.id,
                cfg["symbols_15m"],
                "15m",
                cfg["lookback_15m"],
                cfg["max_bars"],
                False
            ),
            daemon=True
        ).start()

# =========================
# زمان‌بندی خودکار (بر اساس زمان محلی +۳:۳۰)
# =========================

def scheduler_loop():
    while True:
        try:
            local  = now_local()
            minute = local.minute
            hour   = local.hour

            cfg = load_config()

            if minute == 22 and cfg.get("enable_1h", True) and cfg.get("chat_id_1h"):
                threading.Thread(
                    target=lambda: run_cycle(
                        "1h",
                        bot_1h,
                        cfg["chat_id_1h"],
                        cfg["symbols_1h"],
                        "1h",
                        cfg["lookback_1h"],
                        cfg["max_bars"],
                        cfg["make_pdf_1h"]
                    ),
                    daemon=True
                ).start()

            if minute == 7 and hour in [2,6,10,14,18,22] and cfg.get("enable_4h", True):
                ch = cfg.get("chat_id_4h") or cfg.get("chat_id_1h")
                if ch:
                    threading.Thread(
                        target=lambda: run_cycle(
                            "4h",
                            bot_4h or bot_1h,
                            ch,
                            cfg["symbols_4h"],
                            "4h",
                            cfg["lookback_4h"],
                            cfg["max_bars"],
                            False
                        ),
                        daemon=True
                    ).start()

            if hour == 1 and minute == 5 and cfg.get("enable_1d", True):
                ch = cfg.get("chat_id_1d") or cfg.get("chat_id_1h")
                if ch:
                    threading.Thread(
                        target=lambda: run_cycle(
                            "1d",
                            bot_1d or bot_1h,
                            ch,
                            cfg["symbols_1d"],
                            "1d",
                            cfg["lookback_1d"],
                            cfg["max_bars"],
                            cfg["make_pdf_1d"]
                        ),
                        daemon=True
                    ).start()

            if minute % 15 == 0 and cfg.get("enable_15m", True):
                ch = cfg.get("chat_id_15m") or cfg.get("chat_id_1h")
                if ch:
                    threading.Thread(
                        target=lambda: run_cycle(
                            "15m",
                            bot_15m or bot_1h,
                            ch,
                            cfg["symbols_15m"],
                            "15m",
                            cfg["lookback_15m"],
                            cfg["max_bars"],
                            False
                        ),
                        daemon=True
                    ).start()

        except Exception as e:
            debug_mark(bot_1h, ADMIN_CHAT, 1201, f"scheduler_loop_{e}")

        time.sleep(60)

# =========================
# main (هندل 409 و جلوگیری از چند اینستنس)
# =========================

def main():
    load_alarm_history()
    threading.Thread(target=scheduler_loop, daemon=True).start()

    if bot_1h:
        while True:
            try:
                bot_1h.infinity_polling(timeout=60)
            except telebot.apihelper.ApiTelegramException as e:
                err_code = getattr(e, "error_code", None)
                debug_mark(bot_1h, ADMIN_CHAT, 1409, f"polling_error_{e}")
                print("ApiTelegramException:", e)
                if err_code == 409:
                    time.sleep(15)
                    continue
                else:
                    break
            except Exception as e:
                debug_mark(bot_1h, ADMIN_CHAT, 1410, f"polling_generic_{e}")
                print("Polling crashed:", e)
                time.sleep(15)
                continue
    else:
        print("توکن ربات 1h تنظیم نشده است.")

if __name__ == "__main__":
    main()