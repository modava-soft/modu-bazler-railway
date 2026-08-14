# -*- coding: utf-8 -*-
# کد رفرنس Modu Bazler – نسخه پیشرفته و یکپارچه

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

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

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

def create_bot(token):
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

# =========================
# راهنما و منو
# =========================

HELP_TEXT = """
Modu Bazler – نسخه پیشرفته (کد رفرنس)

دستورات:
/start – ثبت چت و نمایش منو
/refresh – رفرش منو
/toggle_* – تغییر وضعیت آلارم‌ها
/start_cycle – شروع چرخه ۱ساعته
/start_cycle_4h – شروع چرخه ۴ساعته
/start_cycle_1d – شروع چرخه روزانه
/start_cycle_15m – شروع چرخه ۱۵دقیقه‌ای

منو:
- چک یک نماد: نمودار کامل + آلارم‌ها
- اجرای دستی 1h: چرخه کامل ۱ساعته
- تنظیم آلارم‌ها: نمایش و تغییر وضعیت آلارم‌ها
- بازنشانی نمادها: برگرداندن لیست‌ها به پیش‌فرض
- راهنما: همین متن
- رفرش منو: ارسال دوباره کیبورد
- شروع چرخه‌ها: شروع حرفه‌ای چرخه‌ها
- وضعیت سیستم: نمایش وضعیت ربات‌ها و تنظیمات
- گزارش آخرین آلارم‌ها: نمایش آخرین آلارم‌های ثبت‌شده
- تنظیمات پیشرفته: نمایش و تغییر پارامترهای حرفه‌ای
"""

def send_main_menu(bot, chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("چک یک نماد", "اجرای دستی 1h")
    kb.row("تنظیم آلارم‌ها", "بازنشانی نمادها")
    kb.row("راهنما", "رفرش منو")
    kb.row("شروع چرخه‌ها", "وضعیت سیستم")
    kb.row("گزارش آلارم‌ها", "تنظیمات پیشرفته")
    bot.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

def refresh_menu(bot, chat_id):
    try:
        send_main_menu(bot, chat_id)
    except:
        pass

# =========================
# هندلرهای /start و /refresh
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
    def cmd_refresh(m):
        refresh_menu(bot_1h, m.chat.id)

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
# دریافت دیتا (Binance + KuCoin)
# =========================

def _binance_interval(i):
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i):
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

def fetch_ohlc(symbol, interval, lookback_days, max_bars):
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
        start = end - 60*60*(limit+10)
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
            rows.append([int(k[0]), float(k[1]), float(k[3]), float(k[4]), float(k[2]), float(k[5])])
        df = pd.DataFrame(rows, columns=["t","o","h","l","c","v"])
        df["t"] = pd.to_datetime(df["t"], unit="s", utc=True)
        df.sort_values("t", inplace=True)
        df.set_index("t", inplace=True)
        return df
    except:
        return pd.DataFrame()

# =========================
# اندیکاتورها (SMA / WMA / RSI / MACD)
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

    # MACD
    ema12 = df["c"].ewm(span=12, adjust=False).mean()
    ema26 = df["c"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    return df

# =========================
# ساخت نمودار (Price + RSI + MACD)
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

    # Price + MA + WMA
    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df["o"], high=df["h"], low=df["l"], close=df["c"],
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
        go.Scatter(x=df.index, y=wma_up, mode="lines", name="WMA20 Up",
                   line=dict(color="green", width=2, dash="dot")),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=wma_down, mode="lines", name="WMA20 Down",
                   line=dict(color="red", width=2, dash="dot")),
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

    # MACD زیر RSI
    fig.add_trace(
        go.Scatter(x=df.index, y=df["MACD"], mode="lines", name="MACD",
                   line=dict(color="black")),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["MACD_signal"], mode="lines", name="Signal",
                   line=dict(color="magenta")),
        row=3, col=1
    )
    fig.add_trace(
        go.Bar(x=df.index, y=df["MACD_hist"], name="Hist", marker_color="gray"),
        row=3, col=1
    )

    fig.update_layout(
        title=f"{symbol} – {interval}",
        xaxis_rangeslider_visible=False,
        template="plotly_white",  # زمینه سفید
        height=1000
    )

    # محور سمت راست مدرج
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
        "last_close": float(df["c"].iloc[-1]) if len(df["c"]) else None,
        "wma": df["WMA20"].tolist() if "WMA20" in df.columns else [],
        "wma_slope": df["WMA20_slope"].tolist() if "WMA20_slope" in df.columns else [],
        "sma20": df["SMA20"].tolist() if "SMA20" in df.columns else [],
        "sma100": df["SMA100"].tolist() if "SMA100" in df.columns else [],
        "sma200": df["SMA200"].tolist() if "SMA200" in df.columns else []
    }

# =========================
# آلارم‌ها
# =========================

LAST_ALARMS = []

def detect_alarms(cfg, info):
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

    # ذخیره آخرین آلارم‌ها
    if alarms:
        LAST_ALARMS.append({
            "symbol": info["symbol"],
            "interval": info["interval"],
            "time": info["created_at"],
            "alarms": alarms
        })
        if len(LAST_ALARMS) > 100:
            LAST_ALARMS.pop(0)

    return alarms

# =========================
# چرخه پردازش
# =========================

def run_cycle(group, bot, chat_id, symbols, interval, lookback_days, max_bars):
    if not bot or not chat_id:
        return
    bot.send_message(chat_id, f"شروع چرخه {group}\n# {now_utc_str()} UTC")

    cfg = load_config()
    pdf = PdfPages(os.path.join(PDF_DIR, f"{group}_{now_utc().strftime('%Y%m%d_%H%M%S')}.pdf")) if cfg.get("make_pdf", True) else None

    # جلوگیری از تکرار نمادها در ۱۵ دقیقه
    unique_symbols = list(dict.fromkeys(symbols))

    for sym in unique_symbols:
        bot.send_message(chat_id, f"در حال پردازش: {sym}")
        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"{group}_{sym}_{ts}.png"
        html = f"{group}_{sym}_{ts}.html"
        info = create_plotly_chart(sym, interval, lookback_days, max_bars, png, html)
        alarms = detect_alarms(cfg, info)
        caption = f"{sym} ({group})"
        if alarms:
            caption += "\n" + "\n".join(alarms)
        with open(info["png_path"], "rb") as f:
            bot.send_photo(chat_id, f, caption=caption)
        if pdf is not None:
            img = plt.imread(info["png_path"])
            fig, ax = plt.subplots(figsize=(10,6))
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
# هندلرهای منو (۱ساعته)
# =========================

if bot_1h:
    @bot_1h.message_handler(func=lambda m: m.text == "چک یک نماد")
    def ask_symbol(m):
        msg = bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید (مثلاً BTCUSDT):")
        bot_1h.register_next_step_handler(msg, do_symbol)

    def do_symbol(m):
        try:
            symbol = m.text.strip().upper()
        except:
            bot_1h.send_message(m.chat.id, "نماد نامعتبر است.")
            return
        cfg = load_config()
        bot_1h.send_message(m.chat.id, f"در حال تهیه نمودار برای {symbol} ...")
        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"SINGLE_{symbol}_{ts}.png"
        html = f"SINGLE_{symbol}_{ts}.html"
        info = create_plotly_chart(symbol, cfg["hourly_interval"], cfg["hourly_lookback_days"], cfg["max_bars"], png, html)
        alarms = detect_alarms(cfg, info)
        caption = f"نمودار {symbol}\nآخرین قیمت: {info['last_close']}\n"
        if alarms:
            caption += "آلارم‌ها:\n" + "\n".join(alarms)
        with open(info["png_path"], "rb") as f:
            bot_1h.send_photo(m.chat.id, f, caption=caption)
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(func=lambda m: m.text == "اجرای دستی 1h")
    def manual_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        run_cycle("1h", bot_1h, m.chat.id, cfg["hourly_symbols"], "1h", cfg["hourly_lookback_days"], cfg["max_bars"])
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(func=lambda m: m.text == "بازنشانی نمادها")
    def reset_symbols(m):
        cfg = load_config()
        cfg["hourly_symbols"]   = DEFAULT_CONFIG["hourly_symbols"]
        cfg["fourh_symbols"]    = DEFAULT_CONFIG["fourh_symbols"]
        cfg["daily_symbols"]    = DEFAULT_CONFIG["daily_symbols"]
        cfg["fifteenm_symbols"] = DEFAULT_CONFIG["fifteenm_symbols"]
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "نمادها به حالت پیش‌فرض بازگردانده شدند.")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(func=lambda m: m.text == "راهنما")
    def show_help(m):
        bot_1h.send_message(m.chat.id, HELP_TEXT)

    @bot_1h.message_handler(func=lambda m: m.text == "رفرش منو")
    def btn_refresh(m):
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(func=lambda m: m.text == "تنظیم آلارم‌ها")
    def alarm_menu(m):
        cfg = load_config()
        text = "وضعیت آلارم‌ها:\n"
        text += f"WMA جهت: {cfg.get('alarm_wma_direction', True)}\n"
        text += f"Cross SMA20: {cfg.get('alarm_cross_sma20', True)}\n"
        text += f"Cross SMA100: {cfg.get('alarm_cross_sma100', True)}\n"
        text += f"Cross SMA200: {cfg.get('alarm_cross_sma200', True)}\n"
        text += f"SMA20 جهت: {cfg.get('alarm_sma20_direction', True)}\n"
        text += f"SMA100 جهت: {cfg.get('alarm_sma100_direction', True)}\n"
        text += f"SMA200 جهت: {cfg.get('alarm_sma200_direction', True)}\n"
        text += "\nدستورات:\n/toggle_wma_dir\n/toggle_cross_sma20\n/toggle_cross_sma100\n/toggle_cross_sma200\n/toggle_sma20_dir\n/toggle_sma100_dir\n/toggle_sma200_dir"
        bot_1h.send_message(m.chat.id, text)

    @bot_1h.message_handler(func=lambda m: m.text == "شروع چرخه‌ها")
    def start_cycles_menu(m):
        text = "شروع چرخه‌ها:\n"
        text += "/start_cycle – چرخه ۱ساعته\n"
        text += "/start_cycle_4h – چرخه ۴ساعته\n"
        text += "/start_cycle_1d – چرخه روزانه\n"
        text += "/start_cycle_15m – چرخه ۱۵دقیقه‌ای\n"
        bot_1h.send_message(m.chat.id, text)

    @bot_1h.message_handler(func=lambda m: m.text == "وضعیت سیستم")
    def system_status(m):
        cfg = load_config()
        text = "وضعیت سیستم:\n"
        text += f"chat_id_1h: {cfg.get('chat_id_1h')}\n"
        text += f"chat_id_4h: {cfg.get('chat_id_4h')}\n"
        text += f"chat_id_1d: {cfg.get('chat_id_1d')}\n"
        text += f"chat_id_15m: {cfg.get('chat_id_15m')}\n"
        text += f"تعداد آخرین آلارم‌ها: {len(LAST_ALARMS)}\n"
        bot_1h.send_message(m.chat.id, text)

    @bot_1h.message_handler(func=lambda m: m.text == "گزارش آلارم‌ها")
    def alarms_report(m):
        if not LAST_ALARMS:
            bot_1h.send_message(m.chat.id, "آلارمی ثبت نشده است.")
            return
        text = "آخرین آلارم‌ها:\n"
        for a in LAST_ALARMS[-10:]:
            text += f"{a['time']} | {a['symbol']} ({a['interval']}):\n"
            for ln in a["alarms"]:
                text += f" - {ln}\n"
        bot_1h.send_message(m.chat.id, text)

    @bot_1h.message_handler(func=lambda m: m.text == "تنظیمات پیشرفته")
    def advanced_settings(m):
        cfg = load_config()
        text = "تنظیمات پیشرفته:\n"
        text += f"max_bars: {cfg.get('max_bars')}\n"
        text += f"make_pdf: {cfg.get('make_pdf')}\n"
        text += f"hourly_lookback_days: {cfg.get('hourly_lookback_days')}\n"
        text += f"fourh_lookback_days: {cfg.get('fourh_lookback_days')}\n"
        text += f"daily_lookback_days: {cfg.get('daily_lookback_days')}\n"
        text += f"fifteenm_lookback_days: {cfg.get('fifteenm_lookback_days')}\n"
        bot_1h.send_message(m.chat.id, text)

    # toggle commands (کلید تنظیم آلارم‌ها)
    @bot_1h.message_handler(commands=["toggle_wma_dir"])
    def toggle_wma_dir(m):
        cfg = load_config()
        cfg["alarm_wma_direction"] = not cfg.get("alarm_wma_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_wma_direction = {cfg['alarm_wma_direction']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_cross_sma20"])
    def toggle_cross_sma20(m):
        cfg = load_config()
        cfg["alarm_cross_sma20"] = not cfg.get("alarm_cross_sma20", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_cross_sma20 = {cfg['alarm_cross_sma20']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_cross_sma100"])
    def toggle_cross_sma100(m):
        cfg = load_config()
        cfg["alarm_cross_sma100"] = not cfg.get("alarm_cross_sma100", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_cross_sma100 = {cfg['alarm_cross_sma100']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_cross_sma200"])
    def toggle_cross_sma200(m):
        cfg = load_config()
        cfg["alarm_cross_sma200"] = not cfg.get("alarm_cross_sma200", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_cross_sma200 = {cfg['alarm_cross_sma200']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_sma20_dir"])
    def toggle_sma20_dir(m):
        cfg = load_config()
        cfg["alarm_sma20_direction"] = not cfg.get("alarm_sma20_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_sma20_direction = {cfg['alarm_sma20_direction']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_sma100_dir"])
    def toggle_sma100_dir(m):
        cfg = load_config()
        cfg["alarm_sma100_direction"] = not cfg.get("alarm_sma100_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_sma100_direction = {cfg['alarm_sma100_direction']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_sma200_dir"])
    def toggle_sma200_dir(m):
        cfg = load_config()
        cfg["alarm_sma200_direction"] = not cfg.get("alarm_sma200_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_sma200_direction = {cfg['alarm_sma200_direction']}")
        refresh_menu(bot_1h, m.chat.id)

    # کلید شروع چرخه‌ها (دستورات حرفه‌ای)
    @bot_1h.message_handler(commands=["start_cycle"])
    def cmd_start_cycle_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        run_cycle("1h", bot_1h, m.chat.id, cfg["hourly_symbols"], "1h", cfg["hourly_lookback_days"], cfg["max_bars"])

    @bot_1h.message_handler(commands=["start_cycle_4h"])
    def cmd_start_cycle_4h(m):
        cfg = load_config()
        cfg["chat_id_4h"] = m.chat.id
        save_config(cfg)
        if bot_4h:
            run_cycle("4h", bot_4h, m.chat.id, cfg["fourh_symbols"], "4h", cfg["fourh_lookback_days"], cfg["max_bars"])

    @bot_1h.message_handler(commands=["start_cycle_1d"])
    def cmd_start_cycle_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        if bot_1d:
            run_cycle("1d", bot_1d, m.chat.id, cfg["daily_symbols"], "1d", cfg["daily_lookback_days"], cfg["max_bars"])

    @bot_1h.message_handler(commands=["start_cycle_15m"])
    def cmd_start_cycle_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        if bot_15m:
            run_cycle("15m", bot_15m, m.chat.id, cfg["fifteenm_symbols"], "15m", cfg["fifteenm_lookback_days"], cfg["max_bars"])

# =========================
# لوپ‌های زمان‌بندی
# =========================

def loop_1h():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute == 30 and bot_1h and cfg.get("chat_id_1h"):
            run_cycle("1h", bot_1h, cfg["chat_id_1h"], cfg["hourly_symbols"], "1h", cfg["hourly_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

def loop_4h():
    times = [(4,30),(8,30),(12,30),(16,30),(20,30),(23,30),(0,30)]
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        for h,m in times:
            if now.hour == h and now.minute == m and bot_4h and cfg.get("chat_id_4h"):
                run_cycle("4h", bot_4h, cfg["chat_id_4h"], cfg["fourh_symbols"], "4h", cfg["fourh_lookback_days"], cfg["max_bars"])
                time.sleep(60)
        time.sleep(20)

def loop_1d():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.hour == 23 and now.minute == 30 and bot_1d and cfg.get("chat_id_1d"):
            run_cycle("1d", bot_1d, cfg["chat_id_1d"], cfg["daily_symbols"], "1d", cfg["daily_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

def loop_15m():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute % 15 == 0 and bot_15m and cfg.get("chat_id_15m"):
            run_cycle("15m", bot_15m, cfg["chat_id_15m"], cfg["fifteenm_symbols"], "15m", cfg["fifteenm_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    if ADMIN_CHAT:
        if bot_1h:  bot_1h.send_message(ADMIN_CHAT, "ربات 1h راه‌اندازی شد.")
        if bot_4h:  bot_4h.send_message(ADMIN_CHAT, "ربات 4h راه‌اندازی شد.")
        if bot_1d:  bot_1d.send_message(ADMIN_CHAT, "ربات 1d راه‌اندازی شد.")
        if bot_15m: bot_15m.send_message(ADMIN_CHAT, "ربات 15m راه‌اندازی شد.")

    if bot_1h:
        threading.Thread(target=bot_1h.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_1h, daemon=True).start()
    if bot_4h:
        threading.Thread(target=bot_4h.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_4h, daemon=True).start()
    if bot_1d:
        threading.Thread(target=bot_1d.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_1d, daemon=True).start()
    if bot_15m:
        threading.Thread(target=bot_15m.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_15m, daemon=True).start()

    while True:
        time.sleep(60)
```chat_id_15m')}\n"
        text += f"تعداد آخرین آلارم‌ها: {len(LAST_ALARMS)}\n"
        bot_1h.send_message(m.chat.id, text)

    @bot_1h.message_handler(func=lambda m: m.text == "گزارش آلارم‌ها")
    def alarms_report(m):
        if not LAST_ALARMS:
            bot_1h.send_message(m.chat.id, "آلارمی ثبت نشده است.")
            return
        text = "آخرین آلارم‌ها:\n"
        for a in LAST_ALARMS[-10:]:
            text += f"{a['time']} | {a['symbol']} ({a['interval']}):\n"
            for ln in a["alarms"]:
                text += f" - {ln}\n"
        bot_1h.send_message(m.chat.id, text)

    @bot_1h.message_handler(func=lambda m: m.text == "تنظیمات پیشرفته")
    def advanced_settings(m):
        cfg = load_config()
        text = "تنظیمات پیشرفته:\n"
        text += f"max_bars: {cfg.get('max_bars')}\n"
        text += f"make_pdf: {cfg.get('make_pdf')}\n"
        text += f"hourly_lookback_days: {cfg.get('hourly_lookback_days')}\n"
        text += f"fourh_lookback_days: {cfg.get('fourh_lookback_days')}\n"
        text += f"daily_lookback_days: {cfg.get('daily_lookback_days')}\n"
        text += f"fifteenm_lookback_days: {cfg.get('fifteenm_lookback_days')}\n"
        bot_1h.send_message(m.chat.id, text)

    # toggle commands (کلید تنظیم آلارم‌ها)
    @bot_1h.message_handler(commands=["toggle_wma_dir"])
    def toggle_wma_dir(m):
        cfg = load_config()
        cfg["alarm_wma_direction"] = not cfg.get("alarm_wma_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_wma_direction = {cfg['alarm_wma_direction']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_cross_sma20"])
    def toggle_cross_sma20(m):
        cfg = load_config()
        cfg["alarm_cross_sma20"] = not cfg.get("alarm_cross_sma20", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_cross_sma20 = {cfg['alarm_cross_sma20']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_cross_sma100"])
    def toggle_cross_sma100(m):
        cfg = load_config()
        cfg["alarm_cross_sma100"] = not cfg.get("alarm_cross_sma100", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_cross_sma100 = {cfg['alarm_cross_sma100']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_cross_sma200"])
    def toggle_cross_sma200(m):
        cfg = load_config()
        cfg["alarm_cross_sma200"] = not cfg.get("alarm_cross_sma200", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_cross_sma200 = {cfg['alarm_cross_sma200']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_sma20_dir"])
    def toggle_sma20_dir(m):
        cfg = load_config()
        cfg["alarm_sma20_direction"] = not cfg.get("alarm_sma20_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_sma20_direction = {cfg['alarm_sma20_direction']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_sma100_dir"])
    def toggle_sma100_dir(m):
        cfg = load_config()
        cfg["alarm_sma100_direction"] = not cfg.get("alarm_sma100_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_sma100_direction = {cfg['alarm_sma100_direction']}")
        refresh_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(commands=["toggle_sma200_dir"])
    def toggle_sma200_dir(m):
        cfg = load_config()
        cfg["alarm_sma200_direction"] = not cfg.get("alarm_sma200_direction", True)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"alarm_sma200_direction = {cfg['alarm_sma200_direction']}")
        refresh_menu(bot_1h, m.chat.id)

    # کلید شروع چرخه‌ها (دستورات حرفه‌ای)
    @bot_1h.message_handler(commands=["start_cycle"])
    def cmd_start_cycle_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        run_cycle("1h", bot_1h, m.chat.id, cfg["hourly_symbols"], "1h", cfg["hourly_lookback_days"], cfg["max_bars"])

    @bot_1h.message_handler(commands=["start_cycle_4h"])
    def cmd_start_cycle_4h(m):
        cfg = load_config()
        cfg["chat_id_4h"] = m.chat.id
        save_config(cfg)
        if bot_4h:
            run_cycle("4h", bot_4h, m.chat.id, cfg["fourh_symbols"], "4h", cfg["fourh_lookback_days"], cfg["max_bars"])

    @bot_1h.message_handler(commands=["start_cycle_1d"])
    def cmd_start_cycle_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        if bot_1d:
            run_cycle("1d", bot_1d, m.chat.id, cfg["daily_symbols"], "1d", cfg["daily_lookback_days"], cfg["max_bars"])

    @bot_1h.message_handler(commands=["start_cycle_15m"])
    def cmd_start_cycle_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        if bot_15m:
            run_cycle("15m", bot_15m, m.chat.id, cfg["fifteenm_symbols"], "15m", cfg["fifteenm_lookback_days"], cfg["max_bars"])

# =========================
# لوپ‌های زمان‌بندی
# =========================

def loop_1h():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute == 30 and bot_1h and cfg.get("chat_id_1h"):
            run_cycle("1h", bot_1h, cfg["chat_id_1h"], cfg["hourly_symbols"], "1h", cfg["hourly_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

def loop_4h():
    times = [(4,30),(8,30),(12,30),(16,30),(20,30),(23,30),(0,30)]
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        for h,m in times:
            if now.hour == h and now.minute == m and bot_4h and cfg.get("chat_id_4h"):
                run_cycle("4h", bot_4h, cfg["chat_id_4h"], cfg["fourh_symbols"], "4h", cfg["fourh_lookback_days"], cfg["max_bars"])
                time.sleep(60)
        time.sleep(20)

def loop_1d():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.hour == 23 and now.minute == 30 and bot_1d and cfg.get("chat_id_1d"):
            run_cycle("1d", bot_1d, cfg["chat_id_1d"], cfg["daily_symbols"], "1d", cfg["daily_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

def loop_15m():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute % 15 == 0 and bot_15m and cfg.get("chat_id_15m"):
            run_cycle("15m", bot_15m, cfg["chat_id_15m"], cfg["fifteenm_symbols"], "15m", cfg["fifteenm_lookback_days"], cfg["max_bars"])
            time.sleep(60)
        time.sleep(20)

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    if ADMIN_CHAT:
        if bot_1h:  bot_1h.send_message(ADMIN_CHAT, "ربات 1h راه‌اندازی شد.")
        if bot_4h:  bot_4h.send_message(ADMIN_CHAT, "ربات 4h راه‌اندازی شد.")
        if bot_1d:  bot_1d.send_message(ADMIN_CHAT, "ربات 1d راه‌اندازی شد.")
        if bot_15m: bot_15m.send_message(ADMIN_CHAT, "ربات 15m راه‌اندازی شد.")

    if bot_1h:
        threading.Thread(target=bot_1h.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_1h, daemon=True).start()
    if bot_4h:
        threading.Thread(target=bot_4h.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_4h, daemon=True).start()
    if bot_1d:
        threading.Thread(target=bot_1d.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_1d, daemon=True).start()
    if bot_15m:
        threading.Thread(target=bot_15m.infinity_polling, daemon=True).start()
        threading.Thread(target=loop_15m, daemon=True).start()

    while True:
        time.sleep(60)