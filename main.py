# -*- coding: utf-8 -*-
# Modu Bazler – Single Bot, Multi Cycles v10
# یک ربات – چهار سیکل – منوی چندصفحه‌ای – واچ‌لیست امن – پیام پردازش هر ارز

import os, json, time, threading, datetime as dt, re
import requests, numpy as np, pandas as pd
import telebot
from telebot import types
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# =========================
# مسیرها و پوشه‌ها
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
# لیست ۵۰ ارز بزرگ
# =========================

TOP50 = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","TONUSDT",
    "AVAXUSDT","DOTUSDT","TRXUSDT","LINKUSDT","MATICUSDT","LTCUSDT","XLMUSDT","ETCUSDT",
    "XMRUSDT","FILUSDT","APTUSDT","NEARUSDT","OPUSUSDT","ARBUSDT","SUIUSDT","PEPEUSDT",
    "UNIUSDT","AAVEUSDT","INJUSDT","RNDRUSDT","FTMUSDT","NEOUSDT","GALAUSDT","SEIUSDT",
    "TIAUSDT","PYTHUSDT","JTOUSDT","WIFUSDT","JUPUSDT","STRKUSDT","BLURUSDT","RUNEUSDT",
    "RAYUSDT","LDOUSDT","COMPUSDT","CRVUSDT","MKRUSDT","SNXUSDT","GMXUSDT","DYDXUSDT","ENSUSDT"
]

# =========================
# کانفیگ
# =========================

DEFAULT_CONFIG = {
    "initial_symbols": TOP50,

    "wl_15m": [],
    "wl_1h": [],
    "wl_4h": [],
    "wl_1d": [],

    "interval_15m": "15m",
    "interval_1h": "1h",
    "interval_4h": "4h",
    "interval_1d": "1d",

    "lookback_15m_days": 3,
    "lookback_1h_days": 5,
    "lookback_4h_days": 15,
    "lookback_1d_days": 180,
    "max_bars": 300,

    "alarm_wma_direction": True,
    "alarm_cross_sma20": True,
    "alarm_cross_sma100": True,
    "alarm_cross_sma200": True,
    "alarm_sma20_direction": True,
    "alarm_sma100_direction": True,
    "alarm_sma200_direction": True,

    "make_pdf": True,

    "chat_id_cycle": None,

    "watchlist_enabled_15m": True,
    "watchlist_enabled_1h": True,
    "watchlist_enabled_4h": True,
    "watchlist_enabled_1d": True,

    "menu_version": 1
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

# =========================
# توکن و ربات
# =========================

TOKEN       = (os.getenv("TELEGRAM_TOKEN") or "").strip()
ADMIN_CHAT  = (os.getenv("ADMIN_CHAT_ID") or "").strip()

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

STATE = {}

# =========================
# منوهای ReplyKeyboardMarkup
# =========================

MAIN_PAGE_1 = "📊 نمودار + آلارم تک‌نماد"
MAIN_PAGE_1_LIST = "📋 لیست ارزهای بررسی"
MAIN_PAGE_1_WL = "👁 واچ‌لیست‌ها"
MAIN_PAGE_1_START_ALL = "🚀 شروع چرخه‌های کامل"
MAIN_PAGE_1_RUN_15M = "⚡ اجرای فوری 15m"
MAIN_PAGE_1_RUN_1H = "⚡ اجرای فوری 1h"
MAIN_PAGE_1_RUN_4H = "⚡ اجرای فوری 4h"
MAIN_PAGE_1_RUN_1D = "⚡ اجرای فوری 1d"
MAIN_PAGE_1_LOOPS = "⏱ وضعیت لوپ‌ها"
MAIN_PAGE_1_NEXT = "➡️ صفحه ۲"

MAIN_PAGE_2_CLEAR_WL = "🧹 صفر کردن واچ‌لیست‌ها"
MAIN_PAGE_2_ALARMS = "🔔 تنظیم آلارم‌ها"
MAIN_PAGE_2_ADV = "⚙ تنظیمات پیشرفته"
MAIN_PAGE_2_LAST = "📑 آخرین آلارم‌ها"
MAIN_PAGE_2_PDF = "📄 وضعیت PDF"
MAIN_PAGE_2_CFG = "📦 وضعیت کانفیگ"
MAIN_PAGE_2_PREV = "⬅️ صفحه ۱"
MAIN_PAGE_2_NEXT = "➡️ صفحه ۳"

MAIN_PAGE_3_HELP = "❓ راهنما"
MAIN_PAGE_3_RESET = "🔄 ریست منو و وضعیت"
MAIN_PAGE_3_TEST_CHART = "📈 تست نمودار BTCUSDT"
MAIN_PAGE_3_TEST_ALARMS = "🧪 تست آلارم‌ها"
MAIN_PAGE_3_PREV = "⬅️ صفحه ۲"

WL_15M = "👁 واچ‌لیست 15m"
WL_1H  = "👁 واچ‌لیست 1h"
WL_4H  = "👁 واچ‌لیست 4h"
WL_1D  = "👁 واچ‌لیست 1d"
WL_BACK = "⬅️ بازگشت به منوی اصلی"

TF_15M = "15m"
TF_1H  = "1h"
TF_4H  = "4h"
TF_1D  = "1d"
TF_BACK = "⬅️ انصراف"

ALL_MENU_TEXTS = {
    MAIN_PAGE_1, MAIN_PAGE_1_LIST, MAIN_PAGE_1_WL, MAIN_PAGE_1_START_ALL,
    MAIN_PAGE_1_RUN_15M, MAIN_PAGE_1_RUN_1H, MAIN_PAGE_1_RUN_4H, MAIN_PAGE_1_RUN_1D,
    MAIN_PAGE_1_LOOPS, MAIN_PAGE_1_NEXT,
    MAIN_PAGE_2_CLEAR_WL, MAIN_PAGE_2_ALARMS, MAIN_PAGE_2_ADV,
    MAIN_PAGE_2_LAST, MAIN_PAGE_2_PDF, MAIN_PAGE_2_CFG,
    MAIN_PAGE_2_PREV, MAIN_PAGE_2_NEXT,
    MAIN_PAGE_3_HELP, MAIN_PAGE_3_RESET, MAIN_PAGE_3_TEST_CHART,
    MAIN_PAGE_3_TEST_ALARMS, MAIN_PAGE_3_PREV,
    WL_15M, WL_1H, WL_4H, WL_1D, WL_BACK,
    TF_15M, TF_1H, TF_4H, TF_1D, TF_BACK
}

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{2,}USDT$")

def build_main_menu_page1():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(MAIN_PAGE_1, MAIN_PAGE_1_LIST)
    kb.row(MAIN_PAGE_1_WL, MAIN_PAGE_1_START_ALL)
    kb.row(MAIN_PAGE_1_RUN_15M, MAIN_PAGE_1_RUN_1H)
    kb.row(MAIN_PAGE_1_RUN_4H, MAIN_PAGE_1_RUN_1D)
    kb.row(MAIN_PAGE_1_LOOPS)
    kb.row(MAIN_PAGE_1_NEXT)
    return kb

def build_main_menu_page2():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(MAIN_PAGE_2_CLEAR_WL, MAIN_PAGE_2_ALARMS)
    kb.row(MAIN_PAGE_2_ADV, MAIN_PAGE_2_LAST)
    kb.row(MAIN_PAGE_2_PDF, MAIN_PAGE_2_CFG)
    kb.row(MAIN_PAGE_2_PREV, MAIN_PAGE_2_NEXT)
    return kb

def build_main_menu_page3():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(MAIN_PAGE_3_HELP, MAIN_PAGE_3_RESET)
    kb.row(MAIN_PAGE_3_TEST_CHART, MAIN_PAGE_3_TEST_ALARMS)
    kb.row(MAIN_PAGE_3_PREV)
    return kb

def build_watchlist_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(WL_15M, WL_1H)
    kb.row(WL_4H, WL_1D)
    kb.row(WL_BACK)
    return kb

def build_tf_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(TF_15M, TF_1H)
    kb.row(TF_4H, TF_1D)
    kb.row(TF_BACK)
    return kb

def send_main_menu(chat_id, page=1):
    if page == 1:
        bot.send_message(chat_id, "🧭 منوی اصلی – صفحه ۱:", reply_markup=build_main_menu_page1())
    elif page == 2:
        bot.send_message(chat_id, "🧭 منوی اصلی – صفحه ۲:", reply_markup=build_main_menu_page2())
    else:
        bot.send_message(chat_id, "🧭 منوی اصلی – صفحه ۳:", reply_markup=build_main_menu_page3())

# =========================
# زمان و تبدیل تایم‌فریم
# =========================

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def now_utc_str():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S")

def _binance_interval(i):
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i):
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

# =========================
# دریافت دیتا
# =========================

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
            rows.append([
                int(k[0]), float(k[1]), float(k[2]),
                float(k[3]), float(k[4]), float(k[5])
            ])

        df = pd.DataFrame(rows, columns=["t","o","h","l","c","v"])
        df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
        df.set_index("t", inplace=True)
        return df

    except Exception:
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

    except Exception:
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
# چرخه‌ها با پیام هر ارز
# =========================

def run_cycle(group, chat_id, symbols, interval, lookback_days, max_bars,
              watchlist_enabled=True, use_watchlist=False):
    try:
        cfg = load_config()

        if use_watchlist:
            wl_map = {
                "15m": "wl_15m",
                "1h": "wl_1h",
                "4h": "wl_4h",
                "1d": "wl_1d"
            }
            wl_key = wl_map[interval]
            symbols = cfg.get(wl_key, []) or symbols

        if isinstance(symbols, str):
            symbols = [symbols]
        unique_symbols = list(dict.fromkeys(symbols))

        total = len(unique_symbols)
        approx_sec = total * 6

        bot.send_message(
            chat_id,
            f"🔄 شروع سیکل {group}\n"
            f"⏱ زمان شروع: {now_utc_str()}\n"
            f"⏳ زمان تقریبی پردازش: حدود {approx_sec} ثانیه\n"
            f"🔢 تعداد نمادها: {total}"
        )

        cycle_alarms = []

        pdf = None
        if cfg.get("make_pdf", True):
            pdf = PdfPages(
                os.path.join(PDF_DIR, f"{group}_{now_utc().strftime('%Y%m%d_%H%M%S')}.pdf")
            )

        step = 10 if total >= 20 else max(5, total // 3) if total > 3 else total

        for idx, sym in enumerate(unique_symbols, start=1):
            try:
                bot.send_message(
                    chat_id,
                    f"🔍 در حال بررسی {sym} ({idx}/{total}) در سیکل {group}..."
                )

                ts = now_utc().strftime("%Y%m%d_%H%M%S")
                png = f"{group}_{sym}_{ts}.png"
                html = f"{group}_{sym}_{ts}.html"

                info = create_plotly_chart(sym, interval, lookback_days, max_bars, png, html)
                alarms = detect_alarms(cfg, info)

                caption = f"📊 {sym} – {interval} – سیکل {group}\n"
                if alarms:
                    caption += "🔔 آلارم‌ها:\n" + "\n".join(f"• {a}" for a in alarms)
                    cycle_alarms.append({
                        "symbol": sym,
                        "interval": interval,
                        "alarms": alarms
                    })
                else:
                    caption += "✅ در این لحظه آلارمی فعال نشد."

                with open(info["png_path"], "rb") as f:
                    bot.send_photo(chat_id, f, caption=caption)

                if pdf is not None and alarms:
                    img = plt.imread(info["png_path"])
                    fig, ax = plt.subplots(figsize=(10,6))
                    ax.imshow(img)
                    ax.axis("off")
                    ax.set_title(f"{sym} – {group}")
                    pdf.savefig(fig)
                    plt.close(fig)

                if idx % step == 0 or idx == total:
                    bot.send_message(
                        chat_id,
                        f"🔄 پیشرفت سیکل {group}: {idx} از {total} نماد بررسی شد."
                    )

                time.sleep(2)

            except Exception as e_sym:
                bot.send_message(
                    chat_id,
                    f"⚠ خطا در پردازش نماد {sym} در سیکل {group}:\n{e_sym}"
                )

        if pdf is not None:
            pdf.close()
            bot.send_message(chat_id, f"📄 فایل PDF چرخه {group} ذخیره شد.")

        if cycle_alarms:
            table = f"📊 گزارش آلارم‌های سیکل {group}:\n\n"
            for item in cycle_alarms:
                table += f"🔹 {item['symbol']} ({item['interval']}):\n"
                for a in item["alarms"]:
                    table += f"   • {a}\n"
                table += "\n"
            bot.send_message(chat_id, table)
        else:
            bot.send_message(chat_id, f"✔ در سیکل {group} هیچ آلارمی فعال نشد.")

        bot.send_message(
            chat_id,
            f"✅ پایان سیکل {group}\n🔢 تعداد پردازش: {total}"
        )

    except Exception as e:
        bot.send_message(
            chat_id,
            f"❌ خطای کلی در اجرای سیکل {group}:\n{e}"
        )

def run_cycle_15m(chat_id):
    cfg = load_config()
    run_cycle(
        "15m",
        chat_id,
        cfg["initial_symbols"],
        "15m",
        cfg["lookback_15m_days"],
        cfg["max_bars"],
        watchlist_enabled=cfg.get("watchlist_enabled_15m", True),
        use_watchlist=True
    )

def run_cycle_1h(chat_id):
    cfg = load_config()
    run_cycle(
        "1h",
        chat_id,
        cfg["initial_symbols"],
        "1h",
        cfg["lookback_1h_days"],
        cfg["max_bars"],
        watchlist_enabled=cfg.get("watchlist_enabled_1h", True),
        use_watchlist=True
    )

def run_cycle_4h(chat_id):
    cfg = load_config()
    run_cycle(
        "4h",
        chat_id,
        cfg["initial_symbols"],
        "4h",
        cfg["lookback_4h_days"],
        cfg["max_bars"],
        watchlist_enabled=cfg.get("watchlist_enabled_4h", True),
        use_watchlist=True
    )

def run_cycle_1d(chat_id):
    cfg = load_config()
    run_cycle(
        "1d",
        chat_id,
        cfg["initial_symbols"],
        "1d",
        cfg["lookback_1d_days"],
        cfg["max_bars"],
        watchlist_enabled=cfg.get("watchlist_enabled_1d", True),
        use_watchlist=True
    )

def run_all_cycles(chat_id):
    run_cycle_15m(chat_id)
    run_cycle_1h(chat_id)
    run_cycle_4h(chat_id)
    run_cycle_1d(chat_id)

# =========================
# لوپ‌های زمانی
# =========================

def safe_sleep(sec):
    try:
        time.sleep(sec)
    except Exception:
        pass

def loop_15m():
    while True:
        try:
            cfg = load_config()
            chat_id = cfg.get("chat_id_cycle")
            if not chat_id:
                safe_sleep(30)
                continue

            now = dt.datetime.now()
            if now.minute % 15 == 0:
                bot.send_message(chat_id, "⏱ لوپ 15m: شروع سیکل خودکار.")
                run_cycle_15m(chat_id)
                safe_sleep(60)
            safe_sleep(20)
        except Exception as e:
            if ADMIN_CHAT:
                bot.send_message(ADMIN_CHAT, f"❌ خطا در لوپ 15m:\n{e}")
            safe_sleep(60)

def loop_1h():
    while True:
        try:
            cfg = load_config()
            chat_id = cfg.get("chat_id_cycle")
            if not chat_id:
                safe_sleep(30)
                continue

            now = dt.datetime.now()
            if now.minute == 30:
                bot.send_message(chat_id, "⏱ لوپ 1h: شروع سیکل خودکار.")
                run_cycle_1h(chat_id)
                safe_sleep(60)
            safe_sleep(20)
        except Exception as e:
            if ADMIN_CHAT:
                bot.send_message(ADMIN_CHAT, f"❌ خطا در لوپ 1h:\n{e}")
            safe_sleep(60)

def loop_4h():
    times = [(4,30),(8,30),(12,30),(16,30),(20,30),(0,30)]
    while True:
        try:
            cfg = load_config()
            chat_id = cfg.get("chat_id_cycle")
            if not chat_id:
                safe_sleep(30)
                continue

            now = dt.datetime.now()
            for h, m in times:
                if now.hour == h and now.minute == m:
                    bot.send_message(chat_id, "⏱ لوپ 4h: شروع سیکل خودکار.")
                    run_cycle_4h(chat_id)
                    safe_sleep(60)
            safe_sleep(20)
        except Exception as e:
            if ADMIN_CHAT:
                bot.send_message(ADMIN_CHAT, f"❌ خطا در لوپ 4h:\n{e}")
            safe_sleep(60)

def loop_1d():
    while True:
        try:
            cfg = load_config()
            chat_id = cfg.get("chat_id_cycle")
            if not chat_id:
                safe_sleep(30)
                continue

            now = dt.datetime.now()
            if now.hour == 23 and now.minute == 30:
                bot.send_message(chat_id, "⏱ لوپ 1d: شروع سیکل خودکار.")
                run_cycle_1d(chat_id)
                safe_sleep(60)
            safe_sleep(20)
        except Exception as e:
            if ADMIN_CHAT:
                bot.send_message(ADMIN_CHAT, f"❌ خطا در لوپ 1d:\n{e}")
            safe_sleep(60)

# =========================
# نمودار + آلارم تک‌نماد
# =========================

def process_single_symbol(chat_id, symbol, interval):
    try:
        cfg = load_config()
        bot.send_message(
            chat_id,
            f"📊 در حال آماده‌سازی نمودار {symbol} – {interval}...\n⏳ زمان تقریبی: حدود ۵ تا ۱۰ ثانیه"
        )
        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"single_{symbol}_{interval}_{ts}.png"
        html = f"single_{symbol}_{interval}_{ts}.html"

        lookback_map = {
            "15m": cfg["lookback_15m_days"],
            "1h":  cfg["lookback_1h_days"],
            "4h":  cfg["lookback_4h_days"],
            "1d":  cfg["lookback_1d_days"]
        }

        info = create_plotly_chart(symbol, interval, lookback_map[interval], cfg["max_bars"], png, html)
        alarms = detect_alarms(cfg, info)

        caption = f"📊 نمودار {symbol} – {interval}\n"
        if alarms:
            caption += "🔔 آلارم‌ها:\n" + "\n".join(f"• {a}" for a in alarms)
        else:
            caption += "✅ در این لحظه آلارمی فعال نشد."

        with open(info["png_path"], "rb") as f:
            bot.send_photo(chat_id, f, caption=caption)

    except Exception as e:
        bot.send_message(
            chat_id,
            f"❌ خطا در پردازش نمودار تک‌نماد {symbol} – {interval}:\n{e}"
        )

# =========================
# هندلرها
# =========================

@bot.message_handler(commands=["start"])
def start_cmd(m):
    cfg = load_config()
    cfg["chat_id_cycle"] = m.chat.id
    cfg["menu_version"] = 2
    save_config(cfg)
    STATE[m.chat.id] = None
    bot.send_message(m.chat.id, "✅ ربات فعال شد و این چت به‌عنوان چت اصلی سیکل‌ها ثبت شد.")
    send_main_menu(m.chat.id, page=1)

@bot.message_handler(func=lambda m: True)
def msg_router(m):
    chat_id = m.chat.id
    text = (m.text or "").strip()
    state = STATE.get(chat_id)

    if text == MAIN_PAGE_1_NEXT:
        send_main_menu(chat_id, page=2)
        STATE[chat_id] = None
        return
    if text == MAIN_PAGE_2_PREV:
        send_main_menu(chat_id, page=1)
        STATE[chat_id] = None
        return
    if text == MAIN_PAGE_2_NEXT:
        send_main_menu(chat_id, page=3)
        STATE[chat_id] = None
        return
    if text == MAIN_PAGE_3_PREV:
        send_main_menu(chat_id, page=2)
        STATE[chat_id] = None
        return

    if text == MAIN_PAGE_3_RESET:
        STATE[chat_id] = None
        send_main_menu(chat_id, page=1)
        return

    if text == MAIN_PAGE_1_LIST:
        cfg = load_config()
        txt = "📋 لیست ارزهای بررسی:\n\n" + ", ".join(cfg["initial_symbols"])
        bot.send_message(chat_id, txt)
        return

    if text == MAIN_PAGE_2_CLEAR_WL:
        cfg = load_config()
        cfg["wl_15m"] = []
        cfg["wl_1h"] = []
        cfg["wl_4h"] = []
        cfg["wl_1d"] = []
        save_config(cfg)
        bot.send_message(chat_id, "🧹 واچ‌لیست‌ها صفر شدند.")
        return

    if text == MAIN_PAGE_1:
        bot.send_message(chat_id, "نماد را وارد کنید (مثلاً BTCUSDT):")
        STATE[chat_id] = "await_single_symbol"
        return

    if text == MAIN_PAGE_1_WL:
        bot.send_message(chat_id, "واچ‌لیست مورد نظر را انتخاب کنید:", reply_markup=build_watchlist_menu())
        STATE[chat_id] = "watchlists_menu"
        return

    if STATE.get(chat_id) == "watchlists_menu":
        cfg = load_config()
        key_map = {
            WL_15M: ("wl_15m", "watchlist_enabled_15m", "15m"),
            WL_1H:  ("wl_1h",  "watchlist_enabled_1h",  "1h"),
            WL_4H:  ("wl_4h",  "watchlist_enabled_4h",  "4h"),
            WL_1D:  ("wl_1d",  "watchlist_enabled_1d",  "1d"),
        }
        if text == WL_BACK:
            send_main_menu(chat_id, page=1)
            STATE[chat_id] = None
            return
        if text in key_map:
            sym_key, flag_key, tf = key_map[text]
            syms = cfg[sym_key]
            enabled = cfg[flag_key]
            txt = f"👁 واچ‌لیست {tf}:\n\n"
            txt += (", ".join(syms) if syms else "خالی") + "\n\n"
            txt += f"🔔 آلارم: {'روشن' if enabled else 'خاموش'}\n\n"
            txt += "➕ افزودن نماد: ارسال نماد (مثلاً BTCUSDT)\n"
            txt += "➖ حذف نماد: ارسال -BTCUSDT\n"
            txt += "🔔 روشن/خاموش: ارسال «روشن» یا «خاموش»\n"
            bot.send_message(chat_id, txt, reply_markup=build_watchlist_menu())
            STATE[chat_id] = ("edit_watchlist", sym_key, flag_key)
            return

    if isinstance(state, tuple) and state[0] == "edit_watchlist":
        sym_key, flag_key = state[1], state[2]
        cfg = load_config()
        t_raw = text.strip()
        t = t_raw.upper()

        if t_raw in ALL_MENU_TEXTS:
            if t_raw == WL_BACK:
                send_main_menu(chat_id, page=1)
                STATE[chat_id] = None
            return

        if t_raw == "روشن":
            cfg[flag_key] = True
            save_config(cfg)
            bot.send_message(chat_id, "🔔 آلارم روشن شد.")
            return

        if t_raw == "خاموش":
            cfg[flag_key] = False
            save_config(cfg)
            bot.send_message(chat_id, "🔕 آلارم خاموش شد.")
            return

        syms = cfg[sym_key]

        if t.startswith("-"):
            sym = t[1:]
            if not SYMBOL_PATTERN.match(sym):
                bot.send_message(chat_id, "⚠ فرمت نماد برای حذف صحیح نیست. مثال: -BTCUSDT")
                return
            if sym in syms:
                syms.remove(sym)
                cfg[sym_key] = syms
                save_config(cfg)
                bot.send_message(chat_id, f"❌ {sym} از واچ‌لیست حذف شد.")
            else:
                bot.send_message(chat_id, f"⚠ {sym} در واچ‌لیست وجود ندارد.")
            return

        if not SYMBOL_PATTERN.match(t):
            bot.send_message(chat_id, "⚠ فرمت نماد صحیح نیست. مثال: BTCUSDT\nفقط حروف و عدد + USDT مجاز است.")
            return

        sym = t
        if sym not in syms:
            syms.append(sym)
            cfg[sym_key] = syms
            save_config(cfg)
            bot.send_message(chat_id, f"✅ {sym} به واچ‌لیست اضافه شد.")
        else:
            bot.send_message(chat_id, f"ℹ {sym} قبلاً در واچ‌لیست وجود دارد.")
        return

    if state == "await_single_symbol":
        symbol = text.strip().upper()
        if not SYMBOL_PATTERN.match(symbol):
            bot.send_message(chat_id, "⚠ فرمت نماد صحیح نیست. مثال: BTCUSDT")
            return
        STATE[chat_id] = ("single_symbol_tf", symbol)
        bot.send_message(chat_id, "⏱ تایم‌فریم را انتخاب کنید:", reply_markup=build_tf_menu())
        return

    if isinstance(state, tuple) and state[0] == "single_symbol_tf":
        symbol = state[1]
        if text == TF_BACK:
            send_main_menu(chat_id, page=1)
            STATE[chat_id] = None
            return
        tf_map = {
            TF_15M: "15m",
            TF_1H:  "1h",
            TF_4H:  "4h",
            TF_1D:  "1d"
        }
        if text in tf_map:
            interval = tf_map[text]
            process_single_symbol(chat_id, symbol, interval)
            send_main_menu(chat_id, page=1)
            STATE[chat_id] = None
            return

    if text == MAIN_PAGE_1_START_ALL:
        bot.send_message(chat_id, "⏳ شروع چرخه‌های کامل (15m + 1h + 4h + 1d)...")
        run_all_cycles(chat_id)
        STATE[chat_id] = None
        return

    if text == MAIN_PAGE_1_RUN_15M:
        bot.send_message(chat_id, "⚡ اجرای فوری سیکل 15m...")
        run_cycle_15m(chat_id)
        STATE[chat_id] = None
        return

    if text == MAIN_PAGE_1_RUN_1H:
        bot.send_message(chat_id, "⚡ اجرای فوری سیکل 1h...")
        run_cycle_1h(chat_id)
        STATE[chat_id] = None
        return

    if text == MAIN_PAGE_1_RUN_4H:
        bot.send_message(chat_id, "⚡ اجرای فوری سیکل 4h...")
        run_cycle_4h(chat_id)
        STATE[chat_id] = None
        return

    if text == MAIN_PAGE_1_RUN_1D:
        bot.send_message(chat_id, "⚡ اجرای فوری سیکل 1d...")
        run_cycle_1d(chat_id)
        STATE[chat_id] = None
        return

    if text == MAIN_PAGE_1_LOOPS:
        cfg = load_config()
        txt = "⏱ وضعیت لوپ‌های زمانی:\n\n"
        txt += f"چت سیکل: {'ثبت شده' if cfg.get('chat_id_cycle') else 'ثبت نشده'}\n"
        txt += "15m: فعال (هر ۱۵ دقیقه)\n"
        txt += "1h: فعال (هر ساعت دقیقه ۳۰)\n"
        txt += "4h: فعال (۴،۸،۱۲،۱۶،۲۰،۰:۳۰)\n"
        txt += "1d: فعال (۲۳:۳۰)\n"
        bot.send_message(chat_id, txt)
        return

    if text == MAIN_PAGE_2_ALARMS:
        cfg = load_config()
        txt = "🔔 تنظیم آلارم‌ها (config.json):\n\n"
        txt += f"alarm_wma_direction = {cfg['alarm_wma_direction']}\n"
        txt += f"alarm_cross_sma20   = {cfg['alarm_cross_sma20']}\n"
        txt += f"alarm_cross_sma100  = {cfg['alarm_cross_sma100']}\n"
        txt += f"alarm_cross_sma200  = {cfg['alarm_cross_sma200']}\n"
        txt += f"alarm_sma20_direction  = {cfg['alarm_sma20_direction']}\n"
        txt += f"alarm_sma100_direction = {cfg['alarm_sma100_direction']}\n"
        txt += f"alarm_sma200_direction = {cfg['alarm_sma200_direction']}\n"
        bot.send_message(chat_id, txt)
        return

    if text == MAIN_PAGE_2_ADV:
        cfg = load_config()
        txt = "⚙ تنظیمات پیشرفته:\n\n"
        txt += f"max_bars = {cfg['max_bars']}\n"
        txt += f"lookback_15m_days = {cfg['lookback_15m_days']}\n"
        txt += f"lookback_1h_days  = {cfg['lookback_1h_days']}\n"
        txt += f"lookback_4h_days  = {cfg['lookback_4h_days']}\n"
        txt += f"lookback_1d_days  = {cfg['lookback_1d_days']}\n"
        bot.send_message(chat_id, txt)
        return

    if text == MAIN_PAGE_2_LAST:
        if not LAST_ALARMS:
            bot.send_message(chat_id, "هیچ آلارمی ثبت نشده است.")
        else:
            txt = "📑 آخرین آلارم‌ها:\n\n"
            for item in LAST_ALARMS[-20:]:
                txt += f"{item['time']} – {item['symbol']} ({item['interval']}):\n"
                for a in item["alarms"]:
                    txt += f"  • {a}\n"
                txt += "\n"
            bot.send_message(chat_id, txt)
        return

    if text == MAIN_PAGE_2_PDF:
        cfg = load_config()
        txt = "📄 وضعیت PDF:\n\n"
        txt += f"make_pdf = {cfg.get('make_pdf', True)}\n"
        bot.send_message(chat_id, txt)
        return

    if text == MAIN_PAGE_2_CFG:
        cfg = load_config()
        txt = "📦 وضعیت کانفیگ:\n\n"
        txt += f"menu_version = {cfg.get('menu_version', 1)}\n"
        txt += f"initial_symbols = {len(cfg.get('initial_symbols', []))} نماد\n"
        txt += f"chat_id_cycle = {cfg.get('chat_id_cycle')}\n"
        bot.send_message(chat_id, txt)
        return

    if text == MAIN_PAGE_3_HELP:
        txt = "❓ راهنما:\n\n"
        txt += "صفحه ۱: نمودار+آلارم تک‌نماد، لیست ارزها، واچ‌لیست‌ها، شروع چرخه‌ها، اجرای فوری ۱۵/۱/۴/۱ روزه، وضعیت لوپ‌ها\n"
        txt += "صفحه ۲: صفر کردن واچ‌لیست‌ها، تنظیم آلارم‌ها، تنظیمات پیشرفته، آخرین آلارم‌ها، وضعیت PDF، وضعیت کانفیگ\n"
        txt += "صفحه ۳: راهنما، ریست، تست نمودار BTCUSDT، تست آلارم‌ها\n"
        bot.send_message(chat_id, txt)
        return

    if text == MAIN_PAGE_3_TEST_CHART:
        process_single_symbol(chat_id, "BTCUSDT", "1h")
        return

    if text == MAIN_PAGE_3_TEST_ALARMS:
        cfg = load_config()
        ts = now_utc().strftime("%Y%m%d_%H%M%S")
        png = f"test_BTCUSDT_1h_{ts}.png"
        html = f"test_BTCUSDT_1h_{ts}.html"
        try:
            info = create_plotly_chart("BTCUSDT", "1h", cfg["lookback_1h_days"], cfg["max_bars"], png, html)
            alarms = detect_alarms(cfg, info)
            txt = "🧪 تست آلارم‌ها برای BTCUSDT – 1h:\n\n"
            if alarms:
                txt += "\n".join(f"• {a}" for a in alarms)
            else:
                txt += "در این لحظه آلارمی فعال نشد."
            bot.send_message(chat_id, txt)
        except Exception as e:
            bot.send_message(chat_id, f"❌ خطا در تست آلارم‌ها:\n{e}")
        return

# =========================
# اجرای نهایی
# =========================

if __name__ == "__main__":

    try:
        if ADMIN_CHAT:
            bot.send_message(ADMIN_CHAT, "✅ ربات Modu Bazler – Single Bot v10 راه‌اندازی شد.")
    except Exception:
        pass

    threading.Thread(target=loop_15m, daemon=True).start()
    threading.Thread(target=loop_1h, daemon=True).start()
    threading.Thread(target=loop_4h, daemon=True).start()
    threading.Thread(target=loop_1d, daemon=True).start()

    bot.infinity_polling()