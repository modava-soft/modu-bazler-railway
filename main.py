# -*- coding: utf-8 -*-
# Modu Bazler v4.0 – چهاررباته حرفه‌ای با مدیریت مرکزی، اجرای فوری، تک‌نماد، آلارم‌ها، تنظیمات پیشرفته
# زمان‌بندی بر اساس قطر (UTC+3)

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
# توکن‌ها – بعداً مقدار بده
# =========================

TOKEN_MAIN  = "6330098471:AAGHanvMEvWN-N6nh1gaKhC6uCET0kock1Q"      # ربات اصلی (مدیریت مرکزی + منوها)
TOKEN_1H    = "6771750492:AAHeldakNtSH1K9jQ3Ja-HQSelBgvWVe_cA"      # ربات سیکل 1h
TOKEN_4H    = "8288371457:AAFSNI_pAT03XDpawX_lf7qWvbTca8nXHas"      # ربات سیکل 4h
TOKEN_1D    = "7999041823:AAGsI55d2YB6qv0T6CBYsc24Dd-zilt8INU"      # ربات سیکل روزانه
TOKEN_15M   = "8884969815:AAF3OivHwJuKzA9T98Si39IMJSgtQR13a3I"      # ربات سیکل 15m

ADMIN_CHAT_ID = ""    # چت آیدی مدیر (اختیاری)

# =========================
# مسیرها و تنظیمات پایه
# =========================

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")

for d in [DATA_DIR, CHARTS_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config_v4.json")

QATAR_TZ = dt.timezone(dt.timedelta(hours=3))

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

def now_qatar():
    return dt.datetime.now(QATAR_TZ)

# =========================
# کانفیگ پیش‌فرض
# =========================

DEFAULT_CONFIG = {
    "symbols_1h": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT","ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT",
        "OPUSDT","ARBUSDT","SUIUSDT","PEPEUSDT","TONUSDT","UNIUSDT","AAVEUSDT","INJUSDT","RNDRUSDT","FTMUSDT",
        "NEOUSDT","GALAUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","JTOUSDT","WIFUSDT","JUPUSDT","STRKUSDT","BLURUSDT",
        "RUNEUSDT","RAYUSDT","LDOUSDT","COMPUSDT","CRVUSDT","MKRUSDT","SNXUSDT","GMXUSDT","DYDXUSDT","ENSUSDT"
    ],
    "symbols_4h": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT","ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT",
        "OPUSDT","ARBUSDT","SUIUSDT","PEPEUSDT","TONUSDT","UNIUSDT","AAVEUSDT","INJUSDT","RNDRUSDT","FTMUSDT",
        "NEOUSDT","GALAUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","JTOUSDT","WIFUSDT","JUPUSDT","STRKUSDT","BLURUSDT",
        "RUNEUSDT","RAYUSDT","LDOUSDT","COMPUSDT","CRVUSDT","MKRUSDT","SNXUSDT","GMXUSDT","DYDXUSDT","ENSUSDT"
    ],
    "symbols_1d": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT","ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT",
        "OPUSUSDT","ARBUSDT","SUIUSDT","PEPEUSDT","TONUSDT","UNIUSDT","AAVEUSDT","INJUSDT","RNDRUSDT","FTMUSDT",
        "NEOUSDT","GALAUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","JTOUSDT","WIFUSDT","JUPUSDT","STRKUSDT","BLURUSDT",
        "RUNEUSDT","RAYUSDT","LDOUSDT","COMPUSDT","CRVUSDT","MKRUSDT","SNXUSDT","GMXUSDT","DYDXUSDT","ENSUSDT",
        "LRCUSDT","ZILUSDT","BCHUSDT","EOSUSDT","ALGOUSDT","CHZUSDT","SANDUSDT","MANAUSDT","AXSUSDT","FLOWUSDT",
        "ROSEUSDT","KSMUSDT","CELOUSDT","1INCHUSDT","BATUSDT","ZRXUSDT","QTUMUSDT","IOSTUSDT","XEMUSDT","ZENUSDT",
        "KNCUSDT","OMGUSDT","SRMUSDT","SKLUSDT","CELRUSDT","CVCUSDT","ANKRUSDT","STORJUSDT","BANDUSDT","BALUSDT",
        "OCEANUSDT","FLMUSDT","CTSIUSDT","NKNUSDT","RLCUSDT","BELUSDT","DODOUSDT","ALPHAUSDT","LITUSDT","UNFIUSDT"
    ],
    "symbols_15m": [
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT","DOTUSDT","MATICUSDT","LTCUSDT",
        "TRXUSDT","AVAXUSDT","LINKUSDT","ATOMUSDT","XMRUSDT","ETCUSDT","XLMUSDT","FILUSDT","APTUSDT","NEARUSDT"
    ],

    "interval_1h": "1h",
    "interval_4h": "4h",
    "interval_1d": "1d",
    "interval_15m": "15m",

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

    "make_pdf": True,
    "cycle_progress_batch": 5,

    "chat_main": None,
    "chat_1h": None,
    "chat_4h": None,
    "chat_1d": None,
    "chat_15m": None
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

# =========================
# ساخت ربات‌ها
# =========================

def create_bot(token: str):
    token = (token or "").strip()
    if not token:
        return None
    try:
        return telebot.TeleBot(token, parse_mode="HTML")
    except:
        return None

bot_main  = create_bot(TOKEN_MAIN)
bot_1h    = create_bot(TOKEN_1H)
bot_4h    = create_bot(TOKEN_4H)
bot_1d    = create_bot(TOKEN_1D)
bot_15m   = create_bot(TOKEN_15M)

LAST_ALARMS = {
    "main": [],
    "1h": [],
    "4h": [],
    "1d": [],
    "15m": []
}

HELP_TEXT_MAIN = """
Modu Bazler v4.0 – ربات اصلی مدیریت مرکزی

دستورات:
/start – ثبت چت و نمایش منوی اصلی
/reset_app – ریست کامل برنامه به طراحی اولیه

کلیدها:
- اجرای فوری 1h / 4h / 1d / 15m
- اجرای تک نماد (برای هر ربات)
- مدیریت نمادهای هر ربات (افزودن / حذف / نمایش)
- تنظیم آلارم‌ها
- گزارش آلارم‌ها
- تنظیمات پیشرفته
- ریست کامل برنامه
- راهنما

زمان‌بندی (قطر – UTC+3):
- 1h: هر ساعت در دقیقه 22
- 4h: 02:07، 06:07، 10:07، 14:07، 18:07، 22:07
- 1d: هر روز 01:05
- 15m: هر ۱۵ دقیقه
"""

# =========================
# ابزار داده و اندیکاتور
# =========================

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str) -> str:
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

def fetch_ohlc(symbol: str, interval: str, lookback_days: int, max_bars: int) -> pd.DataFrame:
    limit = max(200, max_bars)
    try:
        url = "https://api.binance.com/api/v3/klines"
        r = requests.get(url, params={"symbol": symbol, "interval": _binance_interval(interval), "limit": limit}, timeout=10)
        r.raise_for_status()
        data = r.json()
        rows = []
        for k in data:
            rows.append([int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])])
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
        r = requests.get(url, params={"symbol": sym, "type": _kucoin_interval(interval), "startAt": start, "endAt": end}, timeout=10)
        r.raise_for_status()
        data = r.json()["data"]
        rows = []
        for k in data:
            rows.append([int(k[0]), float(k[1]), float(k[3]), float(k[4]), float(k[2]), float(k[5])])
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

def create_plotly_chart(symbol: str, interval: str, lookback_days: int, max_bars: int, png_name: str) -> dict:
    df = fetch_ohlc(symbol, interval, lookback_days, max_bars)
    if df.empty:
        df = pd.DataFrame(columns=["o","h","l","c","v"])
        df.index = pd.to_datetime([])
    else:
        df = df[["o","h","l","c","v"]]
    df = compute_indicators(df)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6,0.2,0.2], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df["o"], high=df["h"], low=df["l"], close=df["c"], name="Price"), row=1, col=1)
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
    fig.update_layout(title=f"{symbol} – {interval}", xaxis_rangeslider_visible=False, template="plotly_white", height=1000)
    fig.add_annotation(text=f"{symbol} – {interval}", xref="paper", yref="paper", x=0.5, y=1.05, showarrow=False, font=dict(size=30, color="black"))
    fig.update_yaxes(side="right", showgrid=True)
    png_path = os.path.join(CHARTS_DIR, png_name)
    fig.write_image(png_path, width=1800, height=1100, scale=3)
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
        record = {"symbol": info["symbol"], "interval": info["interval"], "time": info["created_at"], "alarms": alarms}
        LAST_ALARMS[group] = [record]
    return alarms

# =========================
# اجرای سیکل‌ها برای هر ربات
# =========================

def run_cycle(bot, group: str, chat_id: int, symbols: list, interval: str, lookback_days: int, max_bars: int, make_pdf: bool):
    cfg = load_config()
    batch_size = cfg.get("cycle_progress_batch", 5)
    bot.send_message(chat_id, f"شروع چرخه {group}\n# {now_utc_str()} UTC")
    unique_symbols = list(dict.fromkeys(symbols))
    total = len(unique_symbols)
    processed = 0
    cycle_alarms = []
    pdf = None
    pdf_filename = None
    if group == "1d" and make_pdf:
        pdf_filename = os.path.join(PDF_DIR, f"{group}_{now_utc().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf = PdfPages(pdf_filename)
    for sym in unique_symbols:
        processed += 1
        if processed % batch_size == 0 or processed == 1 or processed == total:
            bot.send_message(chat_id, f"چرخه {group}: {processed} از {total} نماد پردازش شد، {total - processed} باقی مانده.")
        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"{group}_{sym}_{ts}.png"
        info = create_plotly_chart(sym, interval, lookback_days, max_bars, png)
        alarms = detect_alarms(cfg, info, group)
        if alarms:
            cycle_alarms.append({"symbol": sym, "interval": interval, "alarms": alarms})
            caption = f"{sym} ({group})\n" + "\n".join(alarms)
            with open(info["png_path"], "rb") as f:
                bot.send_photo(chat_id, f, caption=caption)
        if group == "1d" and pdf is not None:
            img = plt.imread(info["png_path"])
            fig, ax = plt.subplots(figsize=(10,6))
            ax.imshow(img); ax.axis("off"); ax.set_title(f"{sym} – {group}")
            pdf.savefig(fig); plt.close(fig)
        time.sleep(1)
    if group == "1d" and pdf is not None:
        pdf.close()
        try:
            with open(pdf_filename, "rb") as f:
                bot.send_document(chat_id, f, caption=f"گزارش کامل روزانه – چرخه {group}")
        except:
            bot.send_message(chat_id, "ارسال PDF روزانه با مشکل مواجه شد.")
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
# منوی ربات اصلی
# =========================

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("اجرای فوری 1h", "اجرای فوری 4h")
    kb.row("اجرای فوری 1d", "اجرای فوری 15m")
    kb.row("اجرای تک نماد 1h", "اجرای تک نماد 4h")
    kb.row("اجرای تک نماد 1d", "اجرای تک نماد 15m")
    kb.row("مدیریت نمادهای 1h", "مدیریت نمادهای 4h")
    kb.row("مدیریت نمادهای 1d", "مدیریت نمادهای 15m")
    kb.row("تنظیم آلارم‌ها", "گزارش آلارم‌ها")
    kb.row("تنظیمات پیشرفته", "ریست کامل برنامه")
    kb.row("راهنما")
    bot_main.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

def show_symbol_menu_main(chat_id, group: str):
    cfg = load_config()
    key = f"symbols_{group}"
    symbols = cfg.get(key, [])
    txt = f"نمادهای فعال در ربات {group}:\n"
    if not symbols:
        txt += "هیچ نمادی ثبت نشده است.\n"
    else:
        txt += ", ".join(symbols)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(f"افزودن نماد به {group}", f"حذف نماد از {group}")
    kb.row(f"نمایش نمادهای {group}")
    kb.row("بازگشت به منوی اصلی")
    bot_main.send_message(chat_id, txt, reply_markup=kb)

def add_symbol_step_main(m, group: str):
    symbol = m.text.strip().upper()
    cfg = load_config()
    key = f"symbols_{group}"
    symbols = cfg.get(key, [])
    if symbol not in symbols:
        symbols.append(symbol)
        cfg[key] = symbols
        save_config(cfg)
        bot_main.send_message(m.chat.id, f"{symbol} به لیست نمادهای {group} اضافه شد.")
    else:
        bot_main.send_message(m.chat.id, f"{symbol} قبلاً در لیست {group} وجود دارد.")
    show_symbol_menu_main(m.chat.id, group)

def remove_symbol_step_main(m, group: str):
    symbol = m.text.strip().upper()
    cfg = load_config()
    key = f"symbols_{group}"
    symbols = cfg.get(key, [])
    if symbol in symbols:
        symbols.remove(symbol)
        cfg[key] = symbols
        save_config(cfg)
        bot_main.send_message(m.chat.id, f"{symbol} از لیست نمادهای {group} حذف شد.")
    else:
        bot_main.send_message(m.chat.id, f"{symbol} در لیست {group} وجود ندارد.")
    show_symbol_menu_main(m.chat.id, group)

# =========================
# هندلرهای ربات اصلی
# =========================

if bot_main:

    @bot_main.message_handler(commands=["start"])
    def main_start(m):
        cfg = load_config()
        cfg["chat_main"] = m.chat.id
        save_config(cfg)
        bot_main.send_message(m.chat.id, HELP_TEXT_MAIN)
        send_main_menu(m.chat.id)
        threading.Thread(target=start_initial_cycles_all, daemon=True).start()

    @bot_main.message_handler(commands=["reset_app"])
    @bot_main.message_handler(func=lambda m: m.text == "ریست کامل برنامه")
    def main_reset(m):
        cfg = reset_config()
        cfg["chat_main"] = m.chat.id
        save_config(cfg)
        bot_main.send_message(m.chat.id, "برنامه به طراحی اولیه ریست شد.")
        send_main_menu(m.chat.id)

    @bot_main.message_handler(func=lambda m: m.text == "راهنما")
    def main_help(m):
        bot_main.send_message(m.chat.id, HELP_TEXT_MAIN)

    # اجرای فوری‌ها
    @bot_main.message_handler(func=lambda m: m.text == "اجرای فوری 1h")
    def main_run_1h(m):
        cfg = load_config()
        chat = cfg.get("chat_1h") or m.chat.id
        symbols = cfg["symbols_1h"][:50]
        if bot_1h:
            bot_main.send_message(m.chat.id, "اجرای فوری سیکل 1h در ربات 1h شروع شد.")
            threading.Thread(target=run_cycle, args=(bot_1h,"1h",chat,symbols,cfg["interval_1h"],cfg["lookback_1h"],cfg["max_bars"],False), daemon=True).start()
        else:
            bot_main.send_message(m.chat.id, "توکن ربات 1h تنظیم نشده است.")

    @bot_main.message_handler(func=lambda m: m.text == "اجرای فوری 4h")
    def main_run_4h(m):
        cfg = load_config()
        chat = cfg.get("chat_4h") or m.chat.id
        symbols = cfg["symbols_4h"][:50]
        if bot_4h:
            bot_main.send_message(m.chat.id, "اجرای فوری سیکل 4h در ربات 4h شروع شد.")
            threading.Thread(target=run_cycle, args=(bot_4h,"4h",chat,symbols,cfg["interval_4h"],cfg["lookback_4h"],cfg["max_bars"],False), daemon=True).start()
        else:
            bot_main.send_message(m.chat.id, "توکن ربات 4h تنظیم نشده است.")

    @bot_main.message_handler(func=lambda m: m.text == "اجرای فوری 1d")
    def main_run_1d(m):
        cfg = load_config()
        chat = cfg.get("chat_1d") or m.chat.id
        symbols = cfg["symbols_1d"][:100]
        if bot_1d:
            bot_main.send_message(m.chat.id, "اجرای فوری سیکل 1d در ربات 1d شروع شد.")
            threading.Thread(target=run_cycle, args=(bot_1d,"1d",chat,symbols,cfg["interval_1d"],cfg["lookback_1d"],cfg["max_bars"],cfg.get("make_pdf",True)), daemon=True).start()
        else:
            bot_main.send_message(m.chat.id, "توکن ربات 1d تنظیم نشده است.")

    @bot_main.message_handler(func=lambda m: m.text == "اجرای فوری 15m")
    def main_run_15m(m):
        cfg = load_config()
        chat = cfg.get("chat_15m") or m.chat.id
        symbols = cfg["symbols_15m"][:20]
        if bot_15m:
            bot_main.send_message(m.chat.id, "اجرای فوری سیکل 15m در ربات 15m شروع شد.")
            threading.Thread(target=run_cycle, args=(bot_15m,"15m",chat,symbols,cfg["interval_15m"],cfg["lookback_15m"],cfg["max_bars"],False), daemon=True).start()
        else:
            bot_main.send_message(m.chat.id, "توکن ربات 15m تنظیم نشده است.")

    # اجرای تک نماد
    @bot_main.message_handler(func=lambda m: m.text.startswith("اجرای تک نماد"))
    def main_single_symbol(m):
        text = m.text.strip()
        if "1h" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای ربات 1h را وارد کنید:")
            bot_main.register_next_step_handler(msg, lambda mm: single_symbol_run(mm,"1h"))
        elif "4h" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای ربات 4h را وارد کنید:")
            bot_main.register_next_step_handler(msg, lambda mm: single_symbol_run(mm,"4h"))
        elif "1d" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای ربات 1d را وارد کنید:")
            bot_main.register_next_step_handler(msg, lambda mm: single_symbol_run(mm,"1d"))
        elif "15m" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای ربات 15m را وارد کنید:")
            bot_main.register_next_step_handler(msg, lambda mm: single_symbol_run(mm,"15m"))

    def single_symbol_run(m, group: str):
        symbol = m.text.strip().upper()
        cfg = load_config()
        if group == "1h" and bot_1h:
            chat = cfg.get("chat_1h") or m.chat.id
            bot_main.send_message(m.chat.id, f"در حال بررسی {symbol} در ربات 1h ...")
            threading.Thread(target=run_cycle, args=(bot_1h,"1h",chat,[symbol],cfg["interval_1h"],cfg["lookback_1h"],cfg["max_bars"],False), daemon=True).start()
        elif group == "4h" and bot_4h:
            chat = cfg.get("chat_4h") or m.chat.id
            bot_main.send_message(m.chat.id, f"در حال بررسی {symbol} در ربات 4h ...")
            threading.Thread(target=run_cycle, args=(bot_4h,"4h",chat,[symbol],cfg["interval_4h"],cfg["lookback_4h"],cfg["max_bars"],False), daemon=True).start()
        elif group == "1d" and bot_1d:
            chat = cfg.get("chat_1d") or m.chat.id
            bot_main.send_message(m.chat.id, f"در حال بررسی {symbol} در ربات 1d ...")
            threading.Thread(target=run_cycle, args=(bot_1d,"1d",chat,[symbol],cfg["interval_1d"],cfg["lookback_1d"],cfg["max_bars"],cfg.get("make_pdf",True)), daemon=True).start()
        elif group == "15m" and bot_15m:
            chat = cfg.get("chat_15m") or m.chat.id
            bot_main.send_message(m.chat.id, f"در حال بررسی {symbol} در ربات 15m ...")
            threading.Thread(target=run_cycle, args=(bot_15m,"15m",chat,[symbol],cfg["interval_15m"],cfg["lookback_15m"],cfg["max_bars"],False), daemon=True).start()
        else:
            bot_main.send_message(m.chat.id, "توکن ربات مربوطه تنظیم نشده است.")

    # مدیریت نمادها
    @bot_main.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1h")
    def main_manage_1h(m):
        show_symbol_menu_main(m.chat.id, "1h")

    @bot_main.message_handler(func=lambda m: m.text == "مدیریت نمادهای 4h")
    def main_manage_4h(m):
        show_symbol_menu_main(m.chat.id, "4h")

    @bot_main.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1d")
    def main_manage_1d(m):
        show_symbol_menu_main(m.chat.id, "1d")

    @bot_main.message_handler(func=lambda m: m.text == "مدیریت نمادهای 15m")
    def main_manage_15m(m):
        show_symbol_menu_main(m.chat.id, "15m")

    @bot_main.message_handler(func=lambda m: m.text.startswith("افزودن نماد به "))
    def main_add_symbol(m):
        text = m.text.strip()
        if "1h" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای افزودن به 1h:")
            bot_main.register_next_step_handler(msg, lambda mm: add_symbol_step_main(mm,"1h"))
        elif "4h" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای افزودن به 4h:")
            bot_main.register_next_step_handler(msg, lambda mm: add_symbol_step_main(mm,"4h"))
        elif "1d" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای افزودن به 1d:")
            bot_main.register_next_step_handler(msg, lambda mm: add_symbol_step_main(mm,"1d"))
        elif "15m" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای افزودن به 15m:")
            bot_main.register_next_step_handler(msg, lambda mm: add_symbol_step_main(mm,"15m"))

    @bot_main.message_handler(func=lambda m: m.text.startswith("حذف نماد از "))
    def main_remove_symbol(m):
        text = m.text.strip()
        if "1h" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای حذف از 1h:")
            bot_main.register_next_step_handler(msg, lambda mm: remove_symbol_step_main(mm,"1h"))
        elif "4h" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای حذف از 4h:")
            bot_main.register_next_step_handler(msg, lambda mm: remove_symbol_step_main(mm,"4h"))
        elif "1d" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای حذف از 1d:")
            bot_main.register_next_step_handler(msg, lambda mm: remove_symbol_step_main(mm,"1d"))
        elif "15m" in text:
            msg = bot_main.send_message(m.chat.id, "نماد برای حذف از 15m:")
            bot_main.register_next_step_handler(msg, lambda mm: remove_symbol_step_main(mm,"15m"))

    @bot_main.message_handler(func=lambda m: m.text.startswith("نمایش نمادهای "))
    def main_show_symbols(m):
        text = m.text.strip()
        cfg = load_config()
        if "1h" in text:
            symbols = cfg.get("symbols_1h", []); group = "1h"
        elif "4h" in text:
            symbols = cfg.get("symbols_4h", []); group = "4h"
        elif "1d" in text:
            symbols = cfg.get("symbols_1d", []); group = "1d"
        elif "15m" in text:
            symbols = cfg.get("symbols_15m", []); group = "15m"
        else:
            return
        txt = f"نمادهای {group}:\n"
        if not symbols:
            txt += "هیچ نمادی ثبت نشده است."
        else:
            txt += ", ".join(symbols)
        bot_main.send_message(m.chat.id, txt)

    @bot_main.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
    def main_back(m):
        send_main_menu(m.chat.id)

    # تنظیم آلارم‌ها
    @bot_main.message_handler(func=lambda m: m.text == "تنظیم آلارم‌ها")
    def main_alarms_menu(m):
        cfg = load_config()
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(f"WMA جهت ({'ON' if cfg.get('alarm_wma_direction', True) else 'OFF'})", callback_data="alarm_wma_direction"))
        kb.add(types.InlineKeyboardButton(f"Cross SMA20 ({'ON' if cfg.get('alarm_cross_sma20', False) else 'OFF'})", callback_data="alarm_cross_sma20"))
        kb.add(types.InlineKeyboardButton(f"Cross SMA100 ({'ON' if cfg.get('alarm_cross_sma100', False) else 'OFF'})", callback_data="alarm_cross_sma100"))
        kb.add(types.InlineKeyboardButton(f"Cross SMA200 ({'ON' if cfg.get('alarm_cross_sma200', False) else 'OFF'})", callback_data="alarm_cross_sma200"))
        kb.add(types.InlineKeyboardButton(f"SMA20 جهت ({'ON' if cfg.get('alarm_sma20_direction', False) else 'OFF'})", callback_data="alarm_sma20_direction"))
        kb.add(types.InlineKeyboardButton(f"SMA100 جهت ({'ON' if cfg.get('alarm_sma100_direction', False) else 'OFF'})", callback_data="alarm_sma100_direction"))
        kb.add(types.InlineKeyboardButton(f"SMA200 جهت ({'ON' if cfg.get('alarm_sma200_direction', False) else 'OFF'})", callback_data="alarm_sma200_direction"))
        bot_main.send_message(m.chat.id, "آلارم‌ها را تنظیم کنید:", reply_markup=kb)

    @bot_main.callback_query_handler(func=lambda c: c.data.startswith("alarm_"))
    def main_toggle_alarm(c):
        cfg = load_config()
        key = c.data
        current = cfg.get(key, False)
        cfg[key] = not current
        save_config(cfg)
        bot_main.answer_callback_query(c.id, f"{key} -> {'ON' if cfg[key] else 'OFF'}")
        main_alarms_menu(c.message)

    # گزارش آلارم‌ها
    @bot_main.message_handler(func=lambda m: m.text == "گزارش آلارم‌ها")
    def main_alarms_report(m):
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
        bot_main.send_message(m.chat.id, txt)

    # تنظیمات پیشرفته
    @bot_main.message_handler(func=lambda m: m.text == "تنظیمات پیشرفته")
    def main_advanced(m):
        cfg = load_config()
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(f"PDF روزانه ({'ON' if cfg.get('make_pdf', True) else 'OFF'})", callback_data="adv_make_pdf"))
        kb.add(types.InlineKeyboardButton(f"batch سیکل = {cfg.get('cycle_progress_batch',5)}", callback_data="adv_cycle_batch"))
        kb.add(types.InlineKeyboardButton("ریست کامل برنامه", callback_data="adv_reset_app"))
        bot_main.send_message(m.chat.id, "تنظیمات پیشرفته:", reply_markup=kb)

    @bot_main.callback_query_handler(func=lambda c: c.data.startswith("adv_"))
    def main_advanced_handler(c):
        cfg = load_config()
        if c.data == "adv_make_pdf":
            cfg["make_pdf"] = not cfg.get("make_pdf", True)
            save_config(cfg)
            bot_main.answer_callback_query(c.id, f"make_pdf -> {'ON' if cfg['make_pdf'] else 'OFF'}")
        elif c.data == "adv_cycle_batch":
            current = cfg.get("cycle_progress_batch", 5)
            cfg["cycle_progress_batch"] = 10 if current == 5 else 5
            save_config(cfg)
            bot_main.answer_callback_query(c.id, f"cycle_progress_batch -> {cfg['cycle_progress_batch']}")
        elif c.data == "adv_reset_app":
            cfg = reset_config()
            cfg["chat_main"] = c.message.chat.id
            save_config(cfg)
            bot_main.answer_callback_query(c.id, "برنامه و تنظیمات به حالت اولیه برگشت.")
        main_advanced(c.message)

# =========================
# ثبت چت‌ها در ربات‌های فرعی
# =========================

def register_chat(bot, key_chat: str):
    @bot.message_handler(commands=["start"])
    def sub_start(m):
        cfg = load_config()
        cfg[key_chat] = m.chat.id
        save_config(cfg)
        bot.send_message(m.chat.id, f"چت برای {key_chat} ثبت شد.")

if bot_1h:
    register_chat(bot_1h, "chat_1h")
if bot_4h:
    register_chat(bot_4h, "chat_4h")
if bot_1d:
    register_chat(bot_1d, "chat_1d")
if bot_15m:
    register_chat(bot_15m, "chat_15m")

# =========================
# اجرای اولیه ۴ سیکل از ربات اصلی
# =========================

def start_initial_cycles_all():
    cfg = load_config()
    if not bot_main:
        return
    chat_main = cfg.get("chat_main")
    if not chat_main:
        return
    bot_main.send_message(chat_main, "اجرای اولیه ۴ سیکل در ربات‌های مربوطه شروع شد.")
    if bot_1h:
        threading.Thread(target=run_cycle, args=(bot_1h,"1h",cfg.get("chat_1h") or chat_main,cfg["symbols_1h"][:50],cfg["interval_1h"],cfg["lookback_1h"],cfg["max_bars"],False), daemon=True).start()
    if bot_4h:
        threading.Thread(target=run_cycle, args=(bot_4h,"4h",cfg.get("chat_4h") or chat_main,cfg["symbols_4h"][:50],cfg["interval_4h"],cfg["lookback_4h"],cfg["max_bars"],False), daemon=True).start()
    if bot_1d:
        threading.Thread(target=run_cycle, args=(bot_1d,"1d",cfg.get("chat_1d") or chat_main,cfg["symbols_1d"][:100],cfg["interval_1d"],cfg["lookback_1d"],cfg["max_bars"],cfg.get("make_pdf",True)), daemon=True).start()
    if bot_15m:
        threading.Thread(target=run_cycle, args=(bot_15m,"15m",cfg.get("chat_15m") or chat_main,cfg["symbols_15m"][:20],cfg["interval_15m"],cfg["lookback_15m"],cfg["max_bars"],False), daemon=True).start()

# =========================
# لوپ‌های زمان‌بندی (قطر)
# =========================

def loop_1h():
    while True:
        cfg = load_config()
        chat = cfg.get("chat_1h")
        if not bot_1h or not chat:
            time.sleep(10); continue
        now = now_qatar()
        if now.minute == 22:
            symbols = cfg["symbols_1h"][:50]
            threading.Thread(target=run_cycle, args=(bot_1h,"1h",chat,symbols,cfg["interval_1h"],cfg["lookback_1h"],cfg["max_bars"],False), daemon=True).start()
            time.sleep(60)
        time.sleep(20)

def loop_4h():
    times = [(2,7),(6,7),(10,7),(14,7),(18,7),(22,7)]
    while True:
        cfg = load_config()
        chat = cfg.get("chat_4h")
        if not bot_4h or not chat:
            time.sleep(10); continue
        now = now_qatar()
        for h,m in times:
            if now.hour == h and now.minute == m:
                symbols = cfg["symbols_4h"][:50]
                threading.Thread(target=run_cycle, args=(bot_4h,"4h",chat,symbols,cfg["interval_4h"],cfg["lookback_4h"],cfg["max_bars"],False), daemon=True).start()
                time.sleep(60)
        time.sleep(20)

def loop_1d():
    while True:
        cfg = load_config()
        chat = cfg.get("chat_1d")
        if not bot_1d or not chat:
            time.sleep(10); continue
        now = now_qatar()
        if now.hour == 1 and now.minute == 5:
            symbols = cfg["symbols_1d"][:100]
            threading.Thread(target=run_cycle, args=(bot_1d,"1d",chat,symbols,cfg["interval_1d"],cfg["lookback_1d"],cfg["max_bars"],cfg.get("make_pdf",True)), daemon=True).start()
            time.sleep(60)
        time.sleep(20)

def loop_15m():
    while True:
        cfg = load_config()
        chat = cfg.get("chat_15m")
        if not bot_15m or not chat:
            time.sleep(10); continue
        now = now_qatar()
        if now.minute % 15 == 0:
            symbols = cfg["symbols_15m"][:20]
            threading.Thread(target=run_cycle, args=(bot_15m,"15m",chat,symbols,cfg["interval_15m"],cfg["lookback_15m"],cfg["max_bars"],False), daemon=True).start()
            time.sleep(60)
        time.sleep(20)

# =========================
# راه‌اندازی
# =========================

if __name__ == "__main__":
    if ADMIN_CHAT_ID and bot_main:
        bot_main.send_message(ADMIN_CHAT_ID, "Modu Bazler v4.0 – ربات اصلی راه‌اندازی شد.")

    if bot_main:
        threading.Thread(target=bot_main.infinity_polling, daemon=True).start()
    if bot_1h:
        threading.Thread(target=bot_1h.infinity_polling, daemon=True).start()
    if bot_4h:
        threading.Thread(target=bot_4h.infinity_polling, daemon=True).start()
    if bot_1d:
        threading.Thread(target=bot_1d.infinity_polling, daemon=True).start()
    if bot_15m:
        threading.Thread(target=bot_15m.infinity_polling, daemon=True).start()

    threading.Thread(target=loop_1h, daemon=True).start()
    threading.Thread(target=loop_4h, daemon=True).start()
    threading.Thread(target=loop_1d, daemon=True).start()
    threading.Thread(target=loop_15m, daemon=True).start()

    while True:
        time.sleep(60)