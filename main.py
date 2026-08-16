# -*- coding: utf-8 -*-
# Modu Bazler – main.py (نسخه یکپارچه با ۴ ربات و واچ‌لیست‌ها)

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
    "hourly_interval":   "1h",
    "fourh_interval":    "4h",
    "daily_interval":    "1d",
    "fifteenm_interval": "15m",
    "hourly_lookback_days":   5,
    "fourh_lookback_days":    15,
    "daily_lookback_days":    180,
    "fifteenm_lookback_days": 3,
    "max_bars": 300,
    "alarm_wma_direction": True,
    "alarm_cross_sma20":   False,
    "alarm_cross_sma100":  False,
    "alarm_cross_sma200":  False,
    "alarm_sma20_direction":   False,
    "alarm_sma100_direction":  False,
    "alarm_sma200_direction":  False,
    "make_pdf": False,
    "chat_id_1h":   None,
    "chat_id_4h":   None,
    "chat_id_1d":   None,
    "chat_id_15m":  None,
    # واچ‌لیست‌ها
    "watchlist_15m": [],
    "watchlist_1h":  [],
    "watchlist_4h":  [],
    "watchlist_1d":  []
}

LAST_ALARMS = []

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_config() -> dict:
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

TOKEN_1H  = (os.getenv("TOKEN_1H")  or "").strip()
TOKEN_4H  = (os.getenv("TOKEN_4H")  or "").strip()
TOKEN_1D  = (os.getenv("TOKEN_1D")  or "").strip()
TOKEN_15M = (os.getenv("TOKEN_15M") or "").strip()
ADMIN_CHAT = (os.getenv("ADMIN_CHAT_ID") or "").strip()

def create_bot(token: str):
    if not token or not isinstance(token, str):
        return None
    if any(ch.isspace() for ch in token):
        return None
    try:
        return telebot.TeleBot(token, parse_mode="HTML")
    except Exception:
        return None

bot_1h   = create_bot(TOKEN_1H)
bot_4h   = create_bot(TOKEN_4H)
bot_1d   = create_bot(TOKEN_1D)
bot_15m  = create_bot(TOKEN_15M)

# =========================
# متن راهنما
# =========================

HELP_TEXT = """Modu Bazler – گزارش‌گر نمودار و آلارم

دستورات اصلی:
/start        – فعال‌سازی ربات و ثبت چت اصلی
/refresh      – ریست منو و وضعیت
/start_cycle_1h   – شروع لوپ خودکار 1h
/start_cycle_4h   – شروع لوپ خودکار 4h
/start_cycle_1d   – شروع لوپ خودکار 1d
/start_cycle_15m  – شروع لوپ خودکار 15m

از منوی اصلی می‌توانید:
- تست نمودار تک‌نماد
- اجرای فوری همین تایم‌فریم
- مشاهده واچ‌لیست‌ها
- وضعیت لوپ‌ها
- گزارش آلارم‌ها
"""

# =========================
# منوی اصلی
# =========================

def send_main_menu(bot, chat_id, timeframe_label: str):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("راهنما ❓", "ریست منو و وضعیت 🔄")
    kb.row("تست نمودار BTCUSDT 📈", "تست آلارم‌ها ✏️")
    kb.row("👁️ واچ‌لیست‌ها", "⏱️ وضعیت لوپ‌ها")
    kb.row("⚡ اجرای فوری همین تایم‌فریم", "➡️ صفحه ۲")
    bot.send_message(chat_id, f"منوی اصلی – {timeframe_label}", reply_markup=kb)

def refresh_menu(bot, chat_id, timeframe_label: str):
    send_main_menu(bot, chat_id, timeframe_label)

# =========================
# نگاشت بازه‌ها
# =========================

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str) -> str:
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

# =========================
# دریافت داده و اندیکاتورها
# =========================

def fetch_ohlc(symbol: str, interval: str, lookback_days: int, max_bars: int) -> pd.DataFrame:
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
    except Exception:
        pass

    # KuCoin
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
    gain  = np.where(delta > 0, delta, 0.0)
    loss  = np.where(delta < 0, -delta, 0.0)
    roll_gain  = pd.Series(gain, index=df.index).rolling(14).mean()
    roll_loss  = pd.Series(loss, index=df.index).rolling(14).mean()
    rs = roll_gain / (roll_loss + 1e-9)
    df["RSI14"] = 100 - (100 / (1 + rs))

    ema12 = df["c"].ewm(span=12, adjust=False).mean()
    ema26 = df["c"].ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"]   = df["MACD"] - df["MACD_signal"]

    return df

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

    # Price
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

    # SMA
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"],  mode="lines", name="SMA20",  line=dict(color="blue")),   row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA100"], mode="lines", name="SMA100", line=dict(color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], mode="lines", name="SMA200", line=dict(color="purple")), row=1, col=1)

    # WMA20 با رنگ شیب
    wma   = df["WMA20"]
    slope = df["WMA20_slope"]
    wma_up   = wma.where(slope >= 0)
    wma_down = wma.where(slope < 0)

    fig.add_trace(
        go.Scatter(
            x=df.index, y=wma_up,
            mode="lines", name="WMA20 Up",
            line=dict(color="green", width=2, dash="dot")
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=wma_down,
            mode="lines", name="WMA20 Down",
            line=dict(color="red", width=2, dash="dot")
        ),
        row=1, col=1
    )

    # RSI
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["RSI14"],
            mode="lines", name="RSI14",
            line=dict(color="brown")
        ),
        row=2, col=1
    )
    fig.add_hline(y=70, line=dict(color="red",   dash="dash"), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="green", dash="dash"), row=2, col=1)

    # MACD
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["MACD"],
            mode="lines", name="MACD",
            line=dict(color="black")
        ),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["MACD_signal"],
            mode="lines", name="Signal",
            line=dict(color="magenta")
        ),
        row=3, col=1
    )
    fig.add_trace(
        go.Bar(
            x=df.index, y=df["MACD_hist"],
            name="Hist", marker_color="gray"
        ),
        row=3, col=1
    )

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
        "symbol":   symbol,
        "interval": interval,
        "png_path": png_path,
        "html_path": html_path
    }

# =========================
# واچ‌لیست‌ها
# =========================

def add_to_watchlist(cfg: dict, tf_key: str, symbol: str) -> bool:
    wl = cfg.get(tf_key, [])
    symbol = symbol.upper().strip()
    if symbol not in wl:
        wl.append(symbol)
        cfg[tf_key] = wl
        save_config(cfg)
        return True
    return False

def format_watchlist(cfg: dict, tf_key: str, label: str) -> str:
    wl = cfg.get(tf_key, [])
    if not wl:
        return f"واچ‌لیست {label} خالی است."
    return f"واچ‌لیست {label}:\n" + "\n".join(f"- {s}" for s in wl)

# =========================
# اجرای سیکل‌ها
# =========================

cycle_flags = {
    "1h":   False,
    "4h":   False,
    "1d":   False,
    "15m":  False
}

def run_cycle_once(
    interval_name: str,
    bot,
    chat_id: int,
    symbols: list,
    api_interval: str,
    lookback_days: int,
    max_bars: int
):
    if not bot or not chat_id or not symbols:
        return

    start_time = time.time()
    total = len(symbols)
    approx_sec = max(10, total * 6)  # تخمین ساده

    bot.send_message(
        chat_id,
        f"شروع سیکل {interval_name} 🔄\n"
        f"زمان شروع: 🕰 {dt.datetime.now().strftime('%H:%M:%S %d-%m-%Y')}\n"
        f"زمان تقریبی پردازش: ⏳ حدود {approx_sec} ثانیه\n"
        f"تعداد نمادها: 📅 {total}"
    )

    for idx, sym in enumerate(symbols, start=1):
        bot.send_message(
            chat_id,
            f"در حال بررسی 🔍 {sym} ({idx}/{total}) در سیکل {interval_name}..."
        )

        try:
            res = create_plotly_chart(
                symbol=sym,
                interval=api_interval,
                lookback_days=lookback_days,
                max_bars=max_bars,
                png_name=f"{sym}_{interval_name}.png",
                html_name=f"{sym}_{interval_name}.html"
            )
            bot.send_photo(
                chat_id,
                open(res["png_path"], "rb"),
                caption=f"{sym} – {interval_name}"
            )
        except Exception as e:
            bot.send_message(
                chat_id,
                f"خطا در پردازش {sym} در سیکل {interval_name}: {e}"
            )

        if idx % 10 == 0 or idx == total:
            bot.send_message(
                chat_id,
                f"✅ بررسی {idx} از {total} نماد در سیکل {interval_name} انجام شد."
            )

    duration = int(time.time() - start_time)
    bot.send_message(
        chat_id,
        f"پایان سیکل {interval_name} ✅\n"
        f"مدت زمان پردازش: ⏱ {duration} ثانیه"
    )

def cycle_loop(interval_name: str, sleep_sec: int):
    cycle_flags[interval_name] = True
    while cycle_flags[interval_name]:
        cfg = load_config()
        if interval_name == "1h":
            bot = bot_1h
            chat_id = cfg.get("chat_id_1h")
            symbols = cfg.get("hourly_symbols", [])
            api_interval = cfg.get("hourly_interval", "1h")
            lookback_days = cfg.get("hourly_lookback_days", 5)
        elif interval_name == "4h":
            bot = bot_4h
            chat_id = cfg.get("chat_id_4h")
            symbols = cfg.get("fourh_symbols", [])
            api_interval = cfg.get("fourh_interval", "4h")
            lookback_days = cfg.get("fourh_lookback_days", 15)
        elif interval_name == "1d":
            bot = bot_1d
            chat_id = cfg.get("chat_id_1d")
            symbols = cfg.get("daily_symbols", [])
            api_interval = cfg.get("daily_interval", "1d")
            lookback_days = cfg.get("daily_lookback_days", 180)
        else:  # "15m"
            bot = bot_15m
            chat_id = cfg.get("chat_id_15m")
            symbols = cfg.get("fifteenm_symbols", [])
            api_interval = cfg.get("fifteenm_interval", "15m")
            lookback_days = cfg.get("fifteenm_lookback_days", 3)

        max_bars = cfg.get("max_bars", 300)

        if bot and chat_id:
            run_cycle_once(interval_name, bot, chat_id, symbols, api_interval, lookback_days, max_bars)

        time.sleep(sleep_sec)

def start_cycle_thread(interval_name: str, sleep_sec: int, bot, chat_id):
    if not bot or not chat_id:
        return
    if cycle_flags.get(interval_name, False):
        bot.send_message(chat_id, f"لوپ {interval_name} از قبل فعال است.")
        return
    t = threading.Thread(target=cycle_loop, args=(interval_name, sleep_sec), daemon=True)
    t.start()
    bot.send_message(chat_id, f"لوپ {interval_name}: شروع سیکل خودکار.")

# =========================
# هندلرهای /start و منوها
# =========================

if bot_1h:
    @bot_1h.message_handler(commands=["start"])
    def start_1h(m):
        cfg = load_config()
        cfg["chat_id_1h"] = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, HELP_TEXT)
        refresh_menu(bot_1h, m.chat.id, "1h")

    @bot_1h.message_handler(commands=["refresh"])
    def refresh_1h_cmd(m):
        refresh_menu(bot_1h, m.chat.id, "1h")

if bot_4h:
    @bot_4h.message_handler(commands=["start"])
    def start_4h(m):
        cfg = load_config()
        cfg["chat_id_4h"] = m.chat.id
        save_config(cfg)
        bot_4h.send_message(m.chat.id, "ربات 4h فعال شد و این چت بعنوان چت اصلی سیکل 4h ثبت شد.")
        refresh_menu(bot_4h, m.chat.id, "4h")

    @bot_4h.message_handler(commands=["refresh"])
    def refresh_4h_cmd(m):
        refresh_menu(bot_4h, m.chat.id, "4h")

if bot_1d:
    @bot_1d.message_handler(commands=["start"])
    def start_1d(m):
        cfg = load_config()
        cfg["chat_id_1d"] = m.chat.id
        save_config(cfg)
        bot_1d.send_message(m.chat.id, "ربات 1d فعال شد و این چت بعنوان چت اصلی سیکل 1d ثبت شد.")
        refresh_menu(bot_1d, m.chat.id, "1d")

    @bot_1d.message_handler(commands=["refresh"])
    def refresh_1d_cmd(m):
        refresh_menu(bot_1d, m.chat.id, "1d")

if bot_15m:
    @bot_15m.message_handler(commands=["start"])
    def start_15m(m):
        cfg = load_config()
        cfg["chat_id_15m"] = m.chat.id
        save_config(cfg)
        bot_15m.send_message(m.chat.id, "ربات 15m فعال شد و این چت بعنوان چت اصلی سیکل 15m ثبت شد.")
        refresh_menu(bot_15m, m.chat.id, "15m")

    @bot_15m.message_handler(commands=["refresh"])
    def refresh_15m_cmd(m):
        refresh_menu(bot_15m, m.chat.id, "15m")

# =========================
# منوی دکمه‌ها – 1h
# =========================

if bot_1h:
    @bot_1h.message_handler(func=lambda m: m.text == "راهنما ❓")
    def help_menu_1h(m):
        bot_1h.send_message(m.chat.id, HELP_TEXT)

    @bot_1h.message_handler(func=lambda m: m.text == "ریست منو و وضعیت 🔄")
    def refresh_btn_1h(m):
        refresh_menu(bot_1h, m.chat.id, "1h")

    @bot_1h.message_handler(func=lambda m: m.text == "تست نمودار BTCUSDT 📈")
    def test_chart_1h(m):
        cfg = load_config()
        bot_1h.send_message(m.chat.id, "در حال آماده‌سازی نمودار 1h ...BTCUSDT 🧮\nزمان تقریبی: حدود ۵ تا ۱۰ ثانیه")
        res = create_plotly_chart(
            symbol="BTCUSDT",
            interval=cfg.get("hourly_interval", "1h"),
            lookback_days=cfg.get("hourly_lookback_days", 5),
            max_bars=cfg.get("max_bars", 300),
            png_name="BTCUSDT_1h_test.png",
            html_name="BTCUSDT_1h_test.html"
        )
        bot_1h.send_photo(m.chat.id, open(res["png_path"], "rb"), caption="تست نمودار BTCUSDT – 1h")

    @bot_1h.message_handler(func=lambda m: m.text == "تست آلارم‌ها ✏️")
    def test_alarms_1h(m):
        bot_1h.send_message(m.chat.id, "تست آلارم‌ها هنوز به‌صورت ساده فعال است.")

    @bot_1h.message_handler(func=lambda m: m.text == "👁️ واچ‌لیست‌ها")
    def watchlists_1h(m):
        cfg = load_config()
        txt = format_watchlist(cfg, "watchlist_1h", "1h")
        bot_1h.send_message(m.chat.id, txt)

    @bot_1h.message_handler(func=lambda m: m.text == "⚡ اجرای فوری همین تایم‌فریم")
    def manual_run_1h(m):
        cfg = load_config()
        run_cycle_once(
            "1h",
            bot_1h,
            cfg.get("chat_id_1h", m.chat.id),
            cfg.get("hourly_symbols", []),
            cfg.get("hourly_interval", "1h"),
            cfg.get("hourly_lookback_days", 5),
            cfg.get("max_bars", 300)
        )

    @bot_1h.message_handler(func=lambda m: m.text.startswith("واچ‌لیست"))
    def add_watchlist_1h(m):
        cfg = load_config()
        parts = m.text.split()
        if len(parts) == 2 and parts[0].lower() == "bchusdt":
            # نمونه از عکس؛ در عمل می‌توانید هر نماد را بگیرید
            pass

    @bot_1h.message_handler(func=lambda m: True)
    def add_symbol_to_watchlist_1h(m):
        # کاربر نماد می‌فرستد، به واچ‌لیست 1h اضافه می‌شود
        cfg = load_config()
        if add_to_watchlist(cfg, "watchlist_1h", m.text):
            bot_1h.send_message(m.chat.id, f"✅ {m.text.upper()} به واچ‌لیست 1h اضافه شد.")
        else:
            bot_1h.send_message(m.chat.id, f"⚠️ {m.text.upper()} قبلاً در واچ‌لیست 1h بوده است.")

# =========================
# منوی دکمه‌ها – 4h
# =========================

if bot_4h:
    @bot_4h.message_handler(func=lambda m: m.text == "راهنما ❓")
    def help_menu_4h(m):
        bot_4h.send_message(m.chat.id, HELP_TEXT)

    @bot_4h.message_handler(func=lambda m: m.text == "ریست منو و وضعیت 🔄")
    def refresh_btn_4h(m):
        refresh_menu(bot_4h, m.chat.id, "4h")

    @bot_4h.message_handler(func=lambda m: m.text == "تست نمودار BTCUSDT 📈")
    def test_chart_4h(m):
        cfg = load_config()
        bot_4h.send_message(m.chat.id, "در حال آماده‌سازی نمودار 4h ...BTCUSDT 🧮\nزمان تقریبی: حدود ۵ تا ۱۰ ثانیه")
        res = create_plotly_chart(
            symbol="BTCUSDT",
            interval=cfg.get("fourh_interval", "4h"),
            lookback_days=cfg.get("fourh_lookback_days", 15),
            max_bars=cfg.get("max_bars", 300),
            png_name="BTCUSDT_4h_test.png",
            html_name="BTCUSDT_4h_test.html"
        )
        bot_4h.send_photo(m.chat.id, open(res["png_path"], "rb"), caption="تست نمودار BTCUSDT – 4h")

    @bot_4h.message_handler(func=lambda m: m.text == "👁️ واچ‌لیست‌ها")
    def watchlists_4h(m):
        cfg = load_config()
        txt = format_watchlist(cfg, "watchlist_4h", "4h")
        bot_4h.send_message(m.chat.id, txt)

    @bot_4h.message_handler(func=lambda m: m.text == "⚡ اجرای فوری همین تایم‌فریم")
    def manual_run_4h(m):
        cfg = load_config()
        run_cycle_once(
            "4h",
            bot_4h,
            cfg.get("chat_id_4h", m.chat.id),
            cfg.get("fourh_symbols", []),
            cfg.get("fourh_interval", "4h"),
            cfg.get("fourh_lookback_days", 15),
            cfg.get("max_bars", 300)
        )

# =========================
# منوی دکمه‌ها – 1d
# =========================

if bot_1d:
    @bot_1d.message_handler(func=lambda m: m.text == "راهنما ❓")
    def help_menu_1d(m):
        bot_1d.send_message(m.chat.id, HELP_TEXT)

    @bot_1d.message_handler(func=lambda m: m.text == "ریست منو و وضعیت 🔄")
    def refresh_btn_1d(m):
        refresh_menu(bot_1d, m.chat.id, "1d")

    @bot_1d.message_handler(func=lambda m: m.text == "تست نمودار BTCUSDT 📈")
    def test_chart_1d(m):
        cfg = load_config()
        bot_1d.send_message(m.chat.id, "در حال آماده‌سازی نمودار 1d ...BTCUSDT 🧮\nزمان تقریبی: حدود ۵ تا ۱۰ ثانیه")
        res = create_plotly_chart(
            symbol="BTCUSDT",
            interval=cfg.get("daily_interval", "1d"),
            lookback_days=cfg.get("daily_lookback_days", 180),
            max_bars=cfg.get("max_bars", 300),
            png_name="BTCUSDT_1d_test.png",
            html_name="BTCUSDT_1d_test.html"
        )
        bot_1d.send_photo(m.chat.id, open(res["png_path"], "rb"), caption="تست نمودار BTCUSDT – 1d")

    @bot_1d.message_handler(func=lambda m: m.text == "👁️ واچ‌لیست‌ها")
    def watchlists_1d(m):
        cfg = load_config()
        txt = format_watchlist(cfg, "watchlist_1d", "1d")
        bot_1d.send_message(m.chat.id, txt)

    @bot_1d.message_handler(func=lambda m: m.text == "⚡ اجرای فوری همین تایم‌فریم")
    def manual_run_1d(m):
        cfg = load_config()
        run_cycle_once(
            "1d",
            bot_1d,
            cfg.get("chat_id_1d", m.chat.id),
            cfg.get("daily_symbols", []),
            cfg.get("daily_interval", "1d"),
            cfg.get("daily_lookback_days", 180),
            cfg.get("max_bars", 300)
        )

# =========================
# منوی دکمه‌ها – 15m
# =========================

if bot_15m:
    @bot_15m.message_handler(func=lambda m: m.text == "راهنما ❓")
    def help_menu_15m(m):
        bot_15m.send_message(m.chat.id, HELP_TEXT)

    @bot_15m.message_handler(func=lambda m: m.text == "ریست منو و وضعیت 🔄")
    def refresh_btn_15m(m):
        refresh_menu(bot_15m, m.chat.id, "15m")

    @bot_15m.message_handler(func=lambda m: m.text == "تست نمودار BTCUSDT 📈")
    def test_chart_15m(m):
        cfg = load_config()
        bot_15m.send_message(m.chat.id, "در حال آماده‌سازی نمودار 15m ...BTCUSDT 🧮\nزمان تقریبی: حدود ۵ تا ۱۰ ثانیه")
        res = create_plotly_chart(
            symbol="BTCUSDT",
            interval=cfg.get("fifteenm_interval", "15m"),
            lookback_days=cfg.get("fifteenm_lookback_days", 3),
            max_bars=cfg.get("max_bars", 300),
            png_name="BTCUSDT_15m_test.png",
            html_name="BTCUSDT_15m_test.html"
        )
        bot_15m.send_photo(m.chat.id, open(res["png_path"], "rb"), caption="تست نمودار BTCUSDT – 15m")

    @bot_15m.message_handler(func=lambda m: m.text == "👁️ واچ‌لیست‌ها")
    def watchlists_15m(m):
        cfg = load_config()
        txt = format_watchlist(cfg, "watchlist_15m", "15m")
        bot_15m.send_message(m.chat.id, txt)

    @bot_15m.message_handler(func=lambda m: m.text == "⚡ اجرای فوری همین تایم‌فریم")
    def manual_run_15m(m):
        cfg = load_config()
        run_cycle_once(
            "15m",
            bot_15m,
            cfg.get("chat_id_15m", m.chat.id),
            cfg.get("fifteenm_symbols", []),
            cfg.get("fifteenm_interval", "15m"),
            cfg.get("fifteenm_lookback_days", 3),
            cfg.get("max_bars", 300)
        )

    @bot_15m.message_handler(func=lambda m: True)
    def add_symbol_to_watchlist_15m(m):
        cfg = load_config()
        if add_to_watchlist(cfg, "watchlist_15m", m.text):
            bot_15m.send_message(m.chat.id, f"✅ {m.text.upper()} به واچ‌لیست 15m اضافه شد.")
        else:
            bot_15m.send_message(m.chat.id, f"⚠️ {m.text.upper()} قبلاً در واچ‌لیست 15m بوده است.")

# =========================
# دستورات شروع لوپ‌ها
# =========================

if bot_1h:
    @bot_1h.message_handler(commands=["start_cycle_1h"])
    def start_cycle_1h_cmd(m):
        cfg = load_config()
        chat_id = cfg.get("chat_id_1h", m.chat.id)
        start_cycle_thread("1h", 60 * 60, bot_1h, chat_id)

if bot_4h:
    @bot_4h.message_handler(commands=["start_cycle_4h"])
    def start_cycle_4h_cmd(m):
        cfg = load_config()
        chat_id = cfg.get("chat_id_4h", m.chat.id)
        start_cycle_thread("4h", 4 * 60 * 60, bot_4h, chat_id)

if bot_1d:
    @bot_1d.message_handler(commands=["start_cycle_1d"])
    def start_cycle_1d_cmd(m):
        cfg = load_config()
        chat_id = cfg.get("chat_id_1d", m.chat.id)
        start_cycle_thread("1d", 24 * 60 * 60, bot_1d, chat_id)

if bot_15m:
    @bot_15m.message_handler(commands=["start_cycle_15m"])
    def start_cycle_15m_cmd(m):
        cfg = load_config()
        chat_id = cfg.get("chat_id_15m", m.chat.id)
        start_cycle_thread("15m", 15 * 60, bot_15m, chat_id)

# =========================
# اجرای polling هر ربات
# =========================

def start_polling(bot):
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception:
        pass

threads = []
for b in [bot_1h, bot_4h, bot_1d, bot_15m]:
    if b:
        t = threading.Thread(target=start_polling, args=(b,), daemon=True)
        t.start()
        threads.append(t)

# نگه داشتن برنامه
while True:
    time.sleep(5)