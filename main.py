# -*- coding: utf-8 -*-
# Modu Bazler v7.9 – Multi-bot Plotly (ارتقا یافته)
# رفع‌ها:
# - ساخت و ارسال درست عکس ۱۲ نموداری (JPG/PNG) در صفحات ۳×۴
# - پیام شروع و پایان برای اجرای سیکل‌ها و ساخت عکس ۱۲تایی هر ربات
# - جلوگیری از اجرای هم‌زمان با SmartLock
# - تنظیمات پیشرفته برای نمایش/عدم‌نمایش نمودار ارزهای آلارم‌دار و عکس تجمیعی آلارم‌ها

import os, json, time, threading, datetime as dt
import requests, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import telebot
from telebot import types

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

    "show_alarm_charts":      True,
    "make_alarm_combined":    True,
    "alarm_combined_message": True,
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

HELP_TEXT = """
Modu Bazler v7.9 – راهنما:

- چک یک نماد
- اجرای دستی 1h / فوری 4h / فوری 1d / فوری 15m
- اجرای چرخه‌ها (همهٔ تایم‌فریم‌ها)
- عکس ۱۲تایی 1h / 4h / 1d / 15m
- مدیریت نمادها
- تنظیم آلارم‌ها و گزارش آلارم‌ها (با فلش رنگی برای آخرین آلارم‌ها)
- تنظیمات پیشرفته (PDF، Combined، نمایش نمودار آلارم‌دار، عکس تجمیعی آلارم‌ها)
- وضعیت سیستم و وضعیت چرخه‌ها
- ریست برنامه و رفع خطای قفل‌ها

زمان‌ها بر اساس زمان محلی +۳:۳۰:
- 1h: هر ساعت دقیقه 22
- 4h: ساعت‌های 2، 6، 10، 14، 18، 22 دقیقه 7
- 1d: ساعت 1:05
- 15m: هر ۱۵ دقیقه
"""

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔵 چک یک نماد", "🔵 اجرای دستی 1h")
    kb.row("🔵 اجرای فوری 4h", "🔵 اجرای فوری 1d")
    kb.row("🔵 اجرای فوری 15m")
    kb.row("📸 عکس ۱۲تایی 1h", "📸 عکس ۱۲تایی 4h")
    kb.row("📸 عکس ۱۲تایی 1d", "📸 عکس ۱۲تایی 15m")
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

@bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
def back_to_main(m):
    send_main_menu(m.chat.id)

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
               ```python
# -*- coding: utf-8 -*-
# Modu Bazler v7.9 – Multi-bot Plotly (ارتقا یافته)
# رفع‌ها:
# - ساخت و ارسال درست عکس ۱۲ نموداری (JPG/PNG) در صفحات ۳×۴
# - پیام شروع و پایان برای اجرای سیکل‌ها و ساخت عکس ۱۲تایی هر ربات
# - جلوگیری از اجرای هم‌زمان با SmartLock
# - تنظیمات پیشرفته برای نمایش/عدم‌نمایش نمودار ارزهای آلارم‌دار و عکس تجمیعی آلارم‌ها

import os, json, time, threading, datetime as dt
import requests, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import telebot
from telebot import types

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

    "show_alarm_charts":      True,
    "make_alarm_combined":    True,
    "alarm_combined_message": True,
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

HELP_TEXT = """
Modu Bazler v7.9 – راهنما:

- چک یک نماد
- اجرای دستی 1h / فوری 4h / فوری 1d / فوری 15m
- اجرای چرخه‌ها (همهٔ تایم‌فریم‌ها)
- عکس ۱۲تایی 1h / 4h / 1d / 15m
- مدیریت نمادها
- تنظیم آلارم‌ها و گزارش آلارم‌ها (با فلش رنگی برای آخرین آلارم‌ها)
- تنظیمات پیشرفته (PDF، Combined، نمایش نمودار آلارم‌دار، عکس تجمیعی آلارم‌ها)
- وضعیت سیستم و وضعیت چرخه‌ها
- ریست برنامه و رفع خطای قفل‌ها

زمان‌ها بر اساس زمان محلی +۳:۳۰:
- 1h: هر ساعت دقیقه 22
- 4h: ساعت‌های 2، 6، 10، 14، 18، 22 دقیقه 7
- 1d: ساعت 1:05
- 15m: هر ۱۵ دقیقه
"""

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔵 چک یک نماد", "🔵 اجرای دستی 1h")
    kb.row("🔵 اجرای فوری 4h", "🔵 اجرای فوری 1d")
    kb.row("🔵 اجرای فوری 15m")
    kb.row("📸 عکس ۱۲تایی 1h", "📸 عکس ۱۲تایی 4h")
    kb.row("📸 عکس ۱۲تایی 1d", "📸 عکس ۱۲تایی 15m")
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

@bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
def back_to_main(m):
    send_main_menu(m.chat.id)

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

@bot_1h.message_handler.text.startswithdef show_symbols[-1]
    cfg = load = get_symbols(cfg(func=lambda m: m.text == "🟡 تنظیم آلارم‌ها")
def alarm_settings(m):
    cfg = load_config()
    kb = types.ReplyKeyboardMarkup(resize_keyboard' if cfg['alarm_wma_direction'] else.row(f"Cross SMA20 ({'ON' if cfg20'] else 'OFF'})")
    kb.row(f"ON' if cfg['alarm.row(f"Cross SMA200 ({'ON' if cfg['alarm_cross_sma200'] else 'OFF'})جهت SMA20 ({'ON' if cfg['alarm_sma20_direction'] cfg['alarm_sma100 toggle_wma_dir(m(m)

@bot_1h.message_handler(func=lambda m: m.text.startswith = load_config()
["alarm_cross_sma100"]
    save_config(cfg)
    alarm_settings("Cross SMA200"))
_200(m):
    cfg    cfg["alarm_cross(cfg)
    alarm_settings(m)

@bot_1h.message m: m.text.startswith("جهت SMA20"))
def_config()
    cfg"] = not cfg["alarm"]
    save_config(cfg)
    alarm_settings(m)

@bot_1h.message m: m.text.startswithdef toggle_dir_100_config()
    cfg"] = not cfg["alarm_sma100_direction"]
    save_config(cfg)
    alarm_settings m: m.text.startswith(m):
    cfg = load_config()
    cfg"] = not cfg["alarm_sma200_direction"]
    save_config(cfg)
    alarm_settings(m)

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str {"1h": "1hour",m": "15min"}[i]

def fetch_ohlc(symbol: str, interval: str, lookback_days_bars)
    try:
        url = "https://api.binance.com        r = requests.get(url, params={
            "symbol": symbol,
            "interval": _binance_interval "limit": limit
_for_status()
               rows = [[int(k[0]), float(k[1]), float(k[2]), float(k[3]),(k[5])] for k inv"])
        df["(df["t"], unit="
    except Exception:
        debug_mark(bot_1h, ADMIN_CHAT, 801, "fetch_ohl("USDT", "-USDT")
(now_utc().timestamp        url = "https/api/v1/market/candles"
        r = requests.get(url, params={
            "symbol": sym,
            "type": _kucoin_interval(interval),
           ,
            "endAt": end
       data"]
        rows = [[int(k[0]), float(k[1]), float(k[3]), float(k[4]), float(k[2]), float data]
        df = pd.DataFrame(rows, columns=["t","v"])
        df["t"] = pd.to_datetime(df["t"], unit="s", utc=True)
        df.sort_values("t", inplace=True=True)
        return:
        debug_mark(bot_1h, ADMIN_CHAT, 802, "fetch_ohlc_kucoin")
        return pd.DataFrame()

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df df
    try:
        df["SMA20"]  = df["c"].rolling(20).mean()
        df["SMA100"] = df["c"].rolling(100).mean()
        df["SMA200"] = df["c"].rolling(200).mean()

        df["WMA20"] = df["c"].rolling(20).apply(
           (1, len(x)+1)),

        )
       diff()

        delta = df["c"].diff()
.where(delta > 0, delta, 0.0)
       (delta < 0, -delta, 0.0)
        roll_gain = pd.Series(gain, index=df.index).rolling(14).mean()
        rs = roll + 1e-9)
       =False).mean()
       (bot_1h, ADMIN_CHATicators")
    return df = pd.DataFrame        df.indexights=[0.6, 0.2,            go.C   row=1, col=1)
 fig.add_trace(go, y=df["SMA200"], mode="lines", name(color="purple")),        wma   = df wma_up   = wma.where wma_down = wma.where(slope < 0)

                   go.Scatter(
                y=wma_up,
               ", width=2)
            go.Scatter(
                y=wma_down,
                name="WMA20 Down="red", width=2)
 row=1, col=1
        )

        fig.add(x=df.index, y=df["RSI14"], mode="I14", line=dict(color2, col=1)
       =70, line=dict(color"), row=2, col=1)
        fig.add=dict(color="green", dash="dash"), row=2, col=1)

(go.Scatter(x=dfD"],        mode="lines", name="   row=3, col=1)
        fig.add_trace(go.Scatter(x=df="lines", name="(color="magenta")), row=3, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist_rangeslider_visible template="plotly x=0.5, y=1.05,
1h, ADMIN_CHAT, ly_chart_build")

    png_path = osS_DIR, png_name)
0, scale=3)
           except Exception as e:
        debug_mark(bot_1h, ADMIN_CHAT, 805, f"create "symbol":    symbol":  interval,
        "png_path":  png_path,
        "_str(),
        "      in df.columns"     in df.columns else []
    }

: dict, group: str, cycle_items: list["wma"]
    slope"]
    sma200 = infoalarm_wma_direction if slope[-2] < 0 and slope[-1] > 0:
            alarms رو به بالا گرفت[-2] > 0 and slope[-1] < 0:
            alarms.append(" گرفت")

    def cross(a, b):
                   return (a[-2] - b[-2])_sma20", False) and):
        alarms.append("برخورد W    if cfg.get("", False) and cross(wma, sma100):
       برخورد WMA20 با SMA_sma200", False)200):
        alarms.append("برخورد W    def dir_change if len(arr) < 3:

        d1 = arr d2 = arr[-2] - arr2 < 0 and d1 > 0:
            alarms جهت رو به بالا گرفت > 0 and d1 < 0:
 جهت رو به پایین گرفت")

    if cfg.get("alarm_sma20_direction", False):
        dir_change(sma20, "SMA20")
    if cfg.get(", "SMA100")
    if cfg.get("alarm_sma200_direction", False):
        dir_change(sma200, "SMA200")

    if alarms:
       ["interval"],
           ["created_at"],
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

@bot_1h.message گزارش آلارم‌ها")
 = "گزارش آلارم‌ها هر تایم‌فریم، زمان محلی +۳:۳۰):\n\n"
    for group in ["15m", "1h", "4h", "1d"]:
        history = ALARM_HISTORY.get(group, [])
        txt += f"🔹 تایم‌فریم {group}:\n"
                   continue = history[-1]
        last_symbols = {item["symbol"] for["items"]}
        enumerate(history[::-1], start=1):
 f"  🕒 سیکل #{idx} در زمان: {cycle item in cycle[""]
                else ""
                txt += f"    • {['interval']}):\ for a in item[" txt += f"      - {a}\n"
                txt += f"      زمان txt += "\n"
        txt += "\n"
    bot_1h.send_message(m.chat.id, txt)

.text == "🔵 چک یک نماد")
def check    msg = bot_1h.id, "نماد را وارد کنید (مثال: BTCUSDT):")
    bot_1h.register_next_symbol(m):
    sym bars = cfg.get(" 300)))
    ts  =_{sym}_{ts}.png"
    info   = create_plotly_chart(sym, "1h", cfg["lookback_1h"], bars,  = now_local_str = []
    alarms_items)
    storeh", cycle_time, cycle_items)
    caption:
        caption:"
        for a in alarms:
            - {a}"
    if sym in LAST_MSG_ID:
        caption += f"\n🔗 نمودار قبلی: https://t.meLAST_MSG_ID[sym]}"
 with open(info[" msg = bot_1h.send_MSG_ID[sym] = msg except Exception as e:
           1h, ADMIN_CHAT, _symbol_send_{e}")
1h.send_message(m عکس.")
    else:
        bot_1hn⚠️ عکس ساخته نشد.")

@bot_1h.message_handler(func=lambda m: m.text == "🔴 system_status(m_config()
    txt = "وضعیت سیستم:\n"
    txt += f"نمادهای 1h: {len(cfg['symbols_1h'])}\n"
    txt += f"نمادهای 4h: {len(cfg['symbols += f"نمادهای 1d_1d'])}\n"
    txt += f"نمادهای 15_15m'])}\n"
    txt: {cfg.get('bars_per_chart', 90)}\n"
    txt += f cfg['make_pdf_1h'] else 'OFF'}\n"
    txt += f"PDF 1d: {'ON' if cfg['make_pdf_1d'] else 'OFF'}\n"
    txt += f"Combined 15m: {'ON' if cfg.get('OFF'}\n"
    txt: {'ON' if cfg.get f"show_alarm_ch.get('show_alarm_charts', True) else_alarm_combined', True) else 'OFF f"alarm_combined_message: {'ON' ifined_message', True) else 'OFF'}\n"
 1h: {'ON' if cfg['verbose_1h'] else 'OFF'}\n"
    txt: {'ON' if cfg[' 'OFF'}\n"
    txt += f"verbose 15verbose_15m'] else 'OFF'}\n"
    txt {'ON' if cfg.get    txt += f"enable_4h: {'ON' if cfg True) else 'OFF'}\n"
    txt += f"enable_1d: {'ON' if cfg.get('enable_1d', True) else 'OFF'}\n"
_15m: {'ON' if cfg'}\n"
    txt += f"lock_timeout_sec_timeout_sec', 600.send_message(m.chat.id, txt)

def send_advanced_menu(chat = "تنظیمات پیشرفته cfg['make_pdf_1h'] else 'OFF'}\d'] else 'OFF'}\make_combined_15OFF'}\n"
    txt', True) else 'OFF: {cfg.get('bars' if cfg['verbose_1h'] else 'OFF'}"verbose 4h: {'ON' if cfg['verbose' if cfg['verboseON' if cfg['verbose    txt += f"enable True) else 'OFF) else 'OFF'}\n"
    txt += f"enable 15m: {'ON' if cfg.get('enable_15m', True) else 'OFFarts: {'ON' if cfg_charts', True) else 'OFF'}\n"
    txt_combined: {'ON' True) else 'OFFined_message', True=True)
    kb.rowCombined 15m", "Combined all")
    kb.row("کندل +30 1h", "verbose 4 15m")
    kb.rowined")
    kb.row("alarm_combined کامل برنامه")
   _1h.message_handler(func=lambda m: m")
def adv_pdf_1h(m):
    cfg = load(cfg)
    send_advanced@bot_1h.message_handler.text == "Combined 15m")
def adv_combined_15m(m):
    cfg = load_config not cfg.get("make(func=lambda m: m all")
def adv_comb()
    cfg["make(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler_plus(m):
    cfg("bars_per_chart        bars = cfg(30, bars)
    save_config(cfg)
    send_advanced_menu(m.chat.id)

@bot_1h.message_handler_minus(m):
    cfg["bars_per_chart_menu(m.chat.id)

(func=lambda m: m load_config()
   @bot_1h.message_handler(func=lambda m: m.text == "verbose 4h")
def adv_verbose_4h(m):
    cfg = cfg["verbose_4h_4h"]
    save_config_menu(m.chat.id)

.text == "verbose_1d(m):
    cfg = load_config()
   _1d"]
    save_config@bot_1h.message_handler.text == "verbose_15m(m):
    cfg_15m"] = not cfg    save_config(cfg_menu(m.chat.id)

(func=lambda m: m.text == "enable load_config()
    = not cfg.get("enable_1h", True)
    save_config_menu(m.chat.id)

(func=lambda m: m cfg["enable_4h"])
    save_config(cfg)
    send_advanced.text == "enable load_config()
   )
    save_config = load_config()
(cfg)
    send_advanced(func=lambda m: m.text == "show_alarm(m):
    cfg = load_config()
    cfg["show_alarm_charts("show_alarm_charts_combined")
def adv(cfg)
    send_advanced@bot_1h.message_handler.text == "alarm_comb adv_alarm_combined_message(m):
   ()
    cfg["alarm_combined_message("alarm_combined_menu(m.chat.id)

 برنامه")
def adv_HISTORY[g] = []
(cfg)
    bot_1h.send_message(m.chatadvanced_menu(m.chat_id: int, image_paths):
    if not image
    try:
        ساخت عکس ۱۲تایی except:
        pass

    pages []
    for img in
        if not os
        page.append len(page) == 12:
            pages page:
        pages.append(page)

   (pages, start=1):
 = plt.subplots(3, 12))
        axes        for ax, img try:
                im = Image.open(img_path)
                im = im.resize((800, 500))
                ax.imshow(im)
                ax.axis("off")
            except Exception as e:
                ax.text(0.5, 0.5, "خطا در عکس", ha="center")
                debug_mark(bot, chat_id, 930, f"combined_read_{group}_{e}")
        for ax in axes[len(pg):]:
            ax.axis("off")
        out_path = os.path.join(CHARTS_DIR, f"combined_{group}_{idx}.jpg")
        plt.tight_layout()
        plt.savefig(out_path, dpi=120, format="jpg")
        plt.close()
        try:
            with open(out_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"📄 صفحه {idx} – عکس ۱۲تایی {group}")
        except Exception as e:
            debug_mark(bot, chat_id, 931, f"combined_send_{group}_{e}")

    try:
        bot.send_message(chat_id, f"✅ ساخت و ارسال عکس‌های ۱۲تایی {group} پایان یافت.")
    except:
        pass

def make_alarm_combined_pages(group: str, bot, chat_id: int, alarm_images):
    if not alarm_images:
        return
    cfg = load_config()
    if not cfg.get("make_alarm_combined", True):
        return
    try:
        bot.send_message(chat_id, f"📸 شروع ساخت عکس ۱۲تایی آلارم‌ها {group}...")
    except:
        pass

    pages = []
    page  = []
    for img in alarm_images:
        if img is None:
            continue
        if not os.path.exists(img):
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
                im = Image.open(img_path)
                im = im.resize((800, 500))
                ax.imshow(im)
                ax.axis("off")
            except Exception as e:
                ax.text(0.5, 0.5, "خطا در عکس", ha="center")
                debug_mark(bot, chat_id, 940, f"alarm_combined_read_{group}_{e}")
        for ax in axes[len(pg):]:
            ax.axis("off")
        out_path = os.path.join(CHARTS_DIR, f"alarm_combined_{group}_{idx}.jpg")
        plt.tight_layout()
        plt.savefig(out_path, dpi=120, format="jpg")
        plt.close()
        try:
            with open(out_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"📄 صفحه آلارم‌ها {idx} – {group}")
        except Exception as e:
            debug_mark(bot, chat_id, 941, f"alarm_combined_send_{group}_{e}")

    if cfg.get("alarm_combined_message", True):
        try:
            bot.send_message(chat_id, f"✅ عکس‌های تجمیعی آلارم‌های سیکل {group} ارسال شد.")
        except Exception as e:
            debug_mark(bot, chat_id, 942, f"alarm_combined_msg_{group}_{e}")

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
        try:
            bot.send_message(chat_id, f"⚠️ چرخه {group} در حال اجراست، اجرای جدید انجام نشد.")
        except:
            pass
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
        bot.send_message(chat_id, f"🚀 شروع اجرای چرخه {group} در {cycle_time} (محلی +۳:۳۰)")
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

            if alarms and not cfg.get("show_alarm_charts", True):
                send_this_chart = False
                try:
                    txt = f"{sym} ({group}) – آلارم‌ها:\n"
                    for a in alarms:
                        txt += f"- {a}\n"
                    bot.send_message(chat_id, txt)
                except Exception as e:
                    debug_mark(bot, chat_id, 913, f"alarm_text_only_{group}_{e}")

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
                    im = Image.open(info["png_path"])
                    fig_pdf, ax_pdf = plt.subplots(figsize=(10, 6))
                    ax_pdf.imshow(im)
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
        try:
            bot.send_message(chat_id, f"✅ پایان اجرای چرخه {group} در {cycle_time}")
        except:
            pass

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

    if alarm_images:
        make_alarm_combined_pages(group, bot, chat_id, alarm_images)

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

def quick_combined(group: str, bot, chat_id: int):
    cfg = load_config()
    symbols = cfg[f"symbols_{group}"]
    interval = group
    lookback = cfg[f"lookback_{group}"] if f"lookback_{group}" in cfg else 5
    max_bars = cfg["max_bars"]
    try:
        bot.send_message(chat_id, f"📸 شروع ساخت عکس ۱۲تایی فوری {group}...")
    except:
        pass
    all_images, _, _, cycle_time, _ = run_cycle_once(
        group, bot, chat_id, symbols, interval, lookback, max_bars, False
    )
    if not all_images:
        try:
            bot.send_message(chat_id, f"⚠️ برای {group} عکس ساخته نشد.")
        except:
            pass
        return
    make_combined_pages(group, bot, chat_id, all_images)
    try:
        bot.send_message(chat_id, f"✅ عکس‌های ۱۲تایی فوری {group} بر اساس اجرای در زمان {cycle_time} ارسال شد.")
    except:
        pass

@bot_1h.message_handler(func=lambda m: m.text == "📸 عکس ۱۲تایی 1h")
def quick_1h(m):
    threading.Thread(
        target=lambda: quick_combined("1h", bot_1h, m.chat.id),
        daemon=True
    ).start()

@bot_1h.message_handler(func=lambda m: m.text == "📸 عکس ۱۲تایی 4h")
def quick_4h(m):
    threading.Thread(
        target=lambda: quick_combined("4h", bot_4h or bot_1h, m.chat.id),
        daemon=True
    ).start()

@bot_1h.message_handler(func=lambda m: m.text == "📸 عکس ۱۲تایی 1d")
def quick_1d(m):
    threading.Thread(
        target=lambda: quick_combined("1d", bot_1d or bot_1h, m.chat.id),
        daemon=True
    ).start()

@bot_1h.message_handler(func=lambda m: m.text == "📸 عکس ۱۲تایی 15m")
def quick_15m(m):
    threading.Thread(
        target=lambda: quick_combined("15m", bot_15m or bot_1h, m.chat.id),
        daemon=True
    ).start()

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