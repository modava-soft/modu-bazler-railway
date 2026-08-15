# -*- coding: utf-8 -*-
# Modu Bazler – Watchlist Pro v3 (نسخه کامل main.py یکجا)

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
# کانفیگ جدید (واچ‌لیست‌ها خالی)
# =========================

DEFAULT_CONFIG = {
    # واچ‌لیست‌ها خالی
    "hourly_symbols": [],
    "fourh_symbols": [],
    "daily_symbols": [],
    "fifteenm_symbols": [],

    # تایم‌فریم‌ها
    "hourly_interval": "1h",
    "fourh_interval": "4h",
    "daily_interval": "1d",
    "fifteenm_interval": "15m",

    # تعداد کندل‌ها
    "hourly_lookback_days": 5,
    "fourh_lookback_days": 15,
    "daily_lookback_days": 180,
    "fifteenm_lookback_days": 3,
    "max_bars": 300,

    # آلارم‌ها
    "alarm_wma_direction": True,
    "alarm_cross_sma20": True,
    "alarm_cross_sma100": True,
    "alarm_cross_sma200": True,
    "alarm_sma20_direction": True,
    "alarm_sma100_direction": True,
    "alarm_sma200_direction": True,

    # PDF
    "make_pdf": True,

    # چت‌ها
    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,

    # واچ‌لیست روشن/خاموش
    "watchlist_enabled_15m": True,
    "watchlist_enabled_1h": True,
    "watchlist_enabled_4h": True,
    "watchlist_enabled_1d": True,

    # تنظیمات پیشرفته (اسکلت)
    "advanced": {
        "pdf_quality": "high",
        "chart_theme": "light",
        "show_rsi": True,
        "show_macd": True,
        "exchange": "binance"
    }
}

# =========================
# ذخیره و بارگذاری کانفیگ
# =========================

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# =========================
# زمان
# =========================

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

bot_1h  = create_bot(TOKEN_1H)
bot_4h  = create_bot(TOKEN_4H)
bot_1d  = create_bot(TOKEN_1D)
bot_15m = create_bot(TOKEN_15M)

# =========================
# State برای Back و Reset
# =========================

USER_STATE = {}        # وضعیت کاربر
WATCHLIST_MODE = {}    # حالت ویرایش واچ‌لیست
CHECK_STATE = {}       # بررسی تک‌نماد

# =========================
# راهنمای جدید
# =========================

HELP_TEXT = """
Modu Bazler – Watchlist Pro v3

⏱ زمان اجرای سیکل‌ها:
- سیکل 15 دقیقه‌ای: هر 15 دقیقه
- سیکل 1 ساعته: دقیقه 30 هر ساعت
- سیکل 4 ساعته: 04:30 – 08:30 – 12:30 – 16:30 – 20:30 – 23:30 – 00:30
- سیکل روزانه: 23:30

منو:
- چک تک‌نماد
- نمودار تک‌نماد
- نمایش لیست ارزها
- واچ‌لیست‌ها
- صفر کردن واچ‌لیست‌ها
- تنظیم آلارم‌ها
- تنظیمات پیشرفته
- ریست
- بازگشت
"""

# =========================
# منوی اصلی
# =========================

def send_main_menu(bot, chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("چک تک‌نماد", "نمودار تک‌نماد")
    kb.row("نمایش لیست ارزها", "واچ‌لیست‌ها")
    kb.row("صفر کردن واچ‌لیست‌ها")
    kb.row("تنظیم آلارم‌ها", "تنظیمات پیشرفته")
    kb.row("ریست", "بازگشت")
    bot.send_message(chat_id, "منوی اصلی:", reply_markup=kb)

def handle_back(bot, m):
    USER_STATE[m.chat.id] = None
    bot.send_message(m.chat.id, "بازگشت انجام شد.")
    send_main_menu(bot, m.chat.id)

def handle_reset(bot, m):
    USER_STATE[m.chat.id] = None
    WATCHLIST_MODE[m.chat.id] = None
    CHECK_STATE[m.chat.id] = None
    bot.send_message(m.chat.id, "ربات از ابتدا شروع شد.")
    send_main_menu(bot, m.chat.id)

def show_symbol_lists(bot, m):
    cfg = load_config()
    txt = "📄 لیست نمادهای هر تایم‌فریم:\n\n"
    txt += f"15m: {', '.join(cfg['fifteenm_symbols']) or 'خالی'}\n"
    txt += f"1h: {', '.join(cfg['hourly_symbols']) or 'خالی'}\n"
    txt += f"4h: {', '.join(cfg['fourh_symbols']) or 'خالی'}\n"
    txt += f"1d: {', '.join(cfg['daily_symbols']) or 'خالی'}\n"
    bot.send_message(m.chat.id, txt)

def clear_watchlists(bot, m):
    cfg = load_config()
    cfg["hourly_symbols"] = []
    cfg["fourh_symbols"] = []
    cfg["daily_symbols"] = []
    cfg["fifteenm_symbols"] = []
    save_config(cfg)
    bot.send_message(m.chat.id, "تمام واچ‌لیست‌ها صفر شدند.")

def send_watchlist_menu(bot, chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("واچ‌لیست 15m", "واچ‌لیست 1h")
    kb.row("واچ‌لیست 4h", "واچ‌لیست 1d")
    kb.row("بازگشت")
    bot.send_message(chat_id, "واچ‌لیست مورد نظر را انتخاب کنید:", reply_markup=kb)

def open_watchlist(bot, m, key, flag_key, label):
    cfg = load_config()
    syms = cfg.get(key, [])
    enabled = cfg.get(flag_key, True)

    txt = f"واچ‌لیست {label}:\n\n"
    txt += (", ".join(syms) if syms else "هیچ نمادی ثبت نشده است.") + "\n\n"
    txt += f"وضعیت آلارم: {'روشن' if enabled else 'خاموش'}\n\n"
    txt += "➕ برای افزودن نماد: نماد را ارسال کن (مثلاً BTCUSDT)\n"
    txt += "➖ برای حذف نماد: نماد را با - بفرست (مثلاً -BTCUSDT)\n"
    txt += "🔔 برای روشن/خاموش کردن آلارم: «روشن» یا «خاموش» را بفرست\n"
    txt += "↩ برای بازگشت: دکمه «بازگشت» را بزن"

    WATCHLIST_MODE[m.chat.id] = (key, flag_key, label)
    bot.send_message(m.chat.id, txt)

def edit_watchlist(bot, m):
    cfg = load_config()
    mode = WATCHLIST_MODE.get(m.chat.id)
    if not mode:
        bot.send_message(m.chat.id, "خطا: حالت واچ‌لیست فعال نیست.")
        return

    key, flag_key, label = mode
    text = m.text.strip().upper()

    if text == "روشن":
        cfg[flag_key] = True
        save_config(cfg)
        bot.send_message(m.chat.id, f"آلارم واچ‌لیست {label} روشن شد.")
        return

    if text == "خاموش":
        cfg[flag_key] = False
        save_config(cfg)
        bot.send_message(m.chat.id, f"آلارم واچ‌لیست {label} خاموش شد.")
        return

    syms = cfg.get(key, [])

    if text.startswith("-"):
        sym = text[1:].strip().upper()
        if sym in syms:
            syms.remove(sym)
            cfg[key] = syms
            save_config(cfg)
            bot.send_message(m.chat.id, f"نماد {sym} حذف شد.")
        else:
            bot.send_message(m.chat.id, f"نماد {sym} در واچ‌لیست وجود ندارد.")
        return

    sym = text
    if sym not in syms:
        syms.append(sym)
        cfg[key] = syms
        save_config(cfg)
        bot.send_message(m.chat.id, f"نماد {sym} اضافه شد.")
    else:
        bot.send_message(m.chat.id, f"نماد {sym} قبلاً وجود دارد.")

# =========================
# تبدیل تایم‌فریم برای Binance و KuCoin
# =========================

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str) -> str:
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

# =========================
# دریافت دیتا
# =========================

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

# =========================
# اندیکاتورها
# =========================

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
# ساخت نمودار
# =========================

def create_plotly_chart(
    symbol: str,
    interval: str,
    lookback_days: int,
    max_bars: int,
    png_name: str,
    html_name: str
) -> dict:

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
        "last_close": float(df["c"].iloc[-1]) if len(df["c"]) else None,
        "wma": df["WMA20"].tolist() if "WMA20" in df.columns else [],
        "wma_slope": df["WMA20_slope"].tolist() if "WMA20_slope" in df.columns else [],
        "sma20": df["SMA20"].tolist() if "SMA20" in df.columns else [],
        "sma100": df["SMA100"].tolist() if "SMA100" in df.columns else [],
        "sma200": df["SMA200"].tolist() if "SMA200" in df.columns else []
    }

# =========================
# سیستم آلارم‌ها
# =========================

LAST_ALARMS = []

def detect_alarms(cfg: dict, info: dict) -> list:
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
# چرخه‌ها (نسخه سبک)
# =========================

def run_cycle(
    group: str,
    bot,
    chat_id: int,
    symbols: list,
    interval: str,
    lookback_days: int,
    max_bars: int,
    watchlist_enabled: bool = True,
    notify_bot=None,
    notify_chat=None
):
    if not bot or not chat_id:
        return

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

    bot.send_message(
        chat_id,
        f"✅ پایان سیکل {group}\n"
        f"🔢 تعداد پردازش: {len(unique_symbols)}"
    )

# =========================
# هندلرهای ربات 1h
# =========================

if bot_1h:

    @bot_1h.message_handler(commands=["start"])
    def start_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, HELP_TEXT)
        send_main_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(func=lambda m: m.text == "بازگشت")
    def back_1h(m):
        handle_back(bot_1h, m)

    @bot_1h.message_handler(func=lambda m: m.text == "ریست")
    def reset_1h(m):
        handle_reset(bot_1h, m)

    @bot_1h.message_handler(func=lambda m: m.text == "نمایش لیست ارزها")
    def show_list_1h(m):
        show_symbol_lists(bot_1h, m)

    @bot_1h.message_handler(func=lambda m: m.text == "صفر کردن واچ‌لیست‌ها")
    def clear_watch_1h(m):
        clear_watchlists(bot_1h, m)

    @bot_1h.message_handler(func=lambda m: m.text == "واچ‌لیست‌ها")
    def wl_menu_1h(m):
        send_watchlist_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(func=lambda m: m.text in ["واچ‌لیست 15m","واچ‌لیست 1h","واچ‌لیست 4h","واچ‌لیست 1d"])
    def wl_open_1h(m):
        cfg = load_config()
        key_map = {
            "واچ‌لیست 15m": ("fifteenm_symbols", "watchlist_enabled_15m", "15m"),
            "واچ‌لیست 1h": ("hourly_symbols", "watchlist_enabled_1h", "1h"),
            "واچ‌لیست 4h": ("fourh_symbols", "watchlist_enabled_4h", "4h"),
            "واچ‌لیست 1d": ("daily_symbols", "watchlist_enabled_1d", "1d")
        }
        sym_key, flag_key, label = key_map[m.text]
        open_watchlist(bot_1h, m, sym_key, flag_key, label)

    @bot_1h.message_handler(func=lambda m: m.chat.id in WATCHLIST_MODE)
    def wl_edit_1h(m):
        edit_watchlist(bot_1h, m)

    @bot_1h.message_handler(func=lambda m: m.text == "چک تک‌نماد")
    def check_symbol_1h(m):
        bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید (مثلاً BTCUSDT):")
        bot_1h.register_next_step_handler(m, ask_tf_check_1h)

    def ask_tf_check_1h(m):
        sym = m.text.strip().upper()
        CHECK_STATE[m.chat.id] = sym
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("TF 15m", "TF 1h")
        kb.row("TF 4h", "TF 1d")
        kb.row("بازگشت")
        bot_1h.send_message(m.chat.id, "تایم‌فریم را انتخاب کنید:", reply_markup=kb)
        bot_1h.register_next_step_handler(m, do_single_check_1h)

    def do_single_check_1h(m):
        if m.text == "بازگشت":
            handle_back(bot_1h, m)
            return
        sym = CHECK_STATE.get(m.chat.id)
        if not sym:
            bot_1h.send_message(m.chat.id, "نماد نامشخص است.")
            send_main_menu(bot_1h, m.chat.id)
            return
        tf_map = {
            "TF 15m": ("15m", "fifteenm_lookback_days"),
            "TF 1h": ("1h", "hourly_lookback_days"),
            "TF 4h": ("4h", "fourh_lookback_days"),
            "TF 1d": ("1d", "daily_lookback_days")
        }
        choice = m.text.strip()
        cfg = load_config()
        if choice not in tf_map:
            bot_1h.send_message(m.chat.id, "تایم‌فریم نامعتبر است.")
            send_main_menu(bot_1h, m.chat.id)
            return
        interval, lb_key = tf_map[choice]
        lookback = cfg[lb_key]
        max_bars = cfg["max_bars"]
        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"single_{sym}_{interval}_{ts}.png"
        html = f"single_{sym}_{interval}_{ts}.html"
        info = create_plotly_chart(sym, interval, lookback, max_bars, png, html)
        caption = f"بررسی تک‌نماد: {sym} ({interval})"
        with open(info["png_path"], "rb") as f:
            bot_1h.send_photo(m.chat.id, f, caption=caption)
        send_main_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(func=lambda m: m.text == "نمودار تک‌نماد")
    def chart_single_1h(m):
        bot_1h.send_message(m.chat.id, "نماد مورد نظر را وارد کنید (مثلاً BTCUSDT):")
        bot_1h.register_next_step_handler(m, chart_tf_1h)

    def chart_tf_1h(m):
        sym = m.text.strip().upper()
        CHECK_STATE[m.chat.id] = sym
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("TF 15m", "TF 1h")
        kb.row("TF 4h", "TF 1d")
        kb.row("بازگشت")
        bot_1h.send_message(m.chat.id, "تایم‌فریم نمودار را انتخاب کنید:", reply_markup=kb)
        bot_1h.register_next_step_handler(m, chart_do_1h)

    def chart_do_1h(m):
        if m.text == "بازگشت":
            handle_back(bot_1h, m)
            return
        sym = CHECK_STATE.get(m.chat.id)
        if not sym:
            bot_1h.send_message(m.chat.id, "نماد نامشخص است.")
            send_main_menu(bot_1h, m.chat.id)
            return
        tf_map = {
            "TF 15m": ("15m", "fifteenm_lookback_days"),
            "TF 1h": ("1h", "hourly_lookback_days"),
            "TF 4h": ("4h", "fourh_lookback_days"),
            "TF 1d": ("1d", "daily_lookback_days")
        }
        choice = m.text.strip()
        cfg = load_config()
        if choice not in tf_map:
            bot_1h.send_message(m.chat.id, "تایم‌فریم نامعتبر است.")
            send_main_menu(bot_1h, m.chat.id)
            return
        interval, lb_key = tf_map[choice]
        lookback = cfg[lb_key]
        max_bars = cfg["max_bars"]
        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"chart_{sym}_{interval}_{ts}.png"
        html = f"chart_{sym}_{interval}_{ts}.html"
        info = create_plotly_chart(sym, interval, lookback, max_bars, png, html)
        caption = f"نمودار تک‌نماد: {sym} ({interval})"
        with open(info["png_path"], "rb") as f:
            bot_1h.send_photo(m.chat.id, f, caption=caption)
        send_main_menu(bot_1h, m.chat.id)

    @bot_1h.message_handler(func=lambda m: m.text == "تنظیم آلارم‌ها")
    def alarms_menu_1h(m):
        bot_1h.send_message(m.chat.id, "تنظیم آلارم‌ها فعلاً از طریق فایل config.json انجام می‌شود.")

    @bot_1h.message_handler(func=lambda m: m.text == "تنظیمات پیشرفته")
    def advanced_menu_1h(m):
        bot_1h.send_message(m.chat.id, "تنظیمات پیشرفته فعلاً به‌صورت دستی در config.json قابل تغییر است.")

# =========================
# لوپ‌ها
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
                cfg["hourly_symbols"],
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
                    cfg["fourh_symbols"],
                    "4h",
                    cfg["fourh_lookback_days"],
                    cfg["max_bars"],
                    watchlist_enabled=cfg.get("watchlist_enabled_4h", True),
                    notify_bot=bot_1h if bot_1h else bot_4h,
                    notify_chat=cfg.get("chat_id_1h") or cfg["chat_id_4h"]
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
                cfg["daily_symbols"],
                "1d",
                cfg["daily_lookback_days"],
                cfg["max_bars"],
                watchlist_enabled=cfg.get("watchlist_enabled_1d", True),
                notify_bot=bot_1h if bot_1h else bot_1d,
                notify_chat=cfg.get("chat_id_1h") or cfg["chat_id_1d"]
            )
            time.sleep(60)
        time.sleep(20)

def loop_15m():
    while True:
        cfg = load_config()
        now = dt.datetime.now()
        if now.minute % 15 == 0 and bot_15m and cfg.get("chat_id_15m"):
            symbols = cfg["fifteenm_symbols"]
            if isinstance(symbols, str):
                symbols = [symbols]
            run_cycle(
                "15m",
                bot_15m,
                cfg["chat_id_15m"],
                symbols,
                "15m",
                cfg["fifteenm_lookback_days"],
                cfg["max_bars"],
                watchlist_enabled=cfg.get("watchlist_enabled_15m", True),
                notify_bot=bot_1h if bot_1h else bot_15m,
                notify_chat=cfg.get("chat_id_1h") or cfg["chat_id_15m"]
            )
            time.sleep(60)
        time.sleep(20)

# =========================
# اجرای نهایی main.py
# =========================

if __name__ == "__main__":

    if ADMIN_CHAT:
        if bot_1h:
            bot_1h.send_message(ADMIN_CHAT, "ربات 1h راه‌اندازی شد.")
        if bot_4h:
            bot_4h.send_message(ADMIN_CHAT, "ربات 4h راه‌اندازی شد.")
        if bot_1d:
            bot_1d.send_message(ADMIN_CHAT, "ربات 1d راه‌اندازی شد.")
        if bot_15m:
            bot_15m.send_message(ADMIN_CHAT, "ربات 15m راه‌اندازی شد.")

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