# -*- coding: utf-8 -*-
# Modu Bazler – upgraded main.py

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
    "alarm_cross_sma20": False,
    "alarm_cross_sma100": False,
    "alarm_cross_sma200": False,
    "alarm_sma20_direction": False,
    "alarm_sma100_direction": False,
    "alarm_sma200_direction": False,
    "make_pdf": False,
    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,
    # واچ‌لیست‌های جدا برای هر ربات
    "watchlist_1h": [],
    "watchlist_4h": [],
    "watchlist_1d": [],
    "watchlist_15m": [],
    # چت مقصد آلارم‌ها (مثلاً ربات گزارش)
    "alarm_target_chat_1h": None,
    "alarm_target_chat_4h": None,
    "alarm_target_chat_1d": None,
    "alarm_target_chat_15m": None
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
    except:
        return None

bot_1h  = create_bot(TOKEN_1H)
bot_4h  = create_bot(TOKEN_4H)
bot_1d  = create_bot(TOKEN_1D)
bot_15m = create_bot(TOKEN_15M)

# =========================
# متن راهنما
# =========================

HELP_TEXT = """Modu Bazler – نسخه ارتقا یافته

دستورات:
/start        شروع و ثبت چت اصلی
/refresh      ریست منو و وضعیت
/start_cycle  شروع چرخه همه تایم‌فریم‌ها
/start_cycle_4h  شروع چرخه 4h
/start_cycle_1d  شروع چرخه 1d
/start_cycle_15m شروع چرخه 15m

دکمه‌ها:
- تست نمودار تک‌نماد
- اجرای فوری همین تایم‌فریم
- واچ‌لیست‌ها (افزودن/حذف نماد)
- ریست منو و وضعیت
- برگشت به منوی اصلی
- وضعیت لوپ‌ها و آلارم‌ها
"""

# =========================
# منوها و دکمه‌ها
# =========================

def send_main_menu(bot, chat_id, tf_label: str):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # ردیف ۱: تست نماد و اجرای فوری
    kb.row("تست نمودار BTCUSDT 📈", "اجرای فوری همین تایم‌فریم ⚡")
    # ردیف ۲: واچ‌لیست و وضعیت لوپ‌ها
    kb.row("👁️ واچ‌لیست‌ها", "⏱️ وضعیت لوپ‌ها")
    # ردیف ۳: راهنما و ریست منو و وضعیت
    kb.row("راهنما ❓", "ریست منو و وضعیت 🔄")
    # ردیف ۴: شروع چرخه خودکار و برگشت
    kb.row("شروع سیکل خودکار 🔄", "بازگشت به منوی اصلی ⬅️")
    bot.send_message(chat_id, f"منوی اصلی – {tf_label}", reply_markup=kb)

def refresh_menu(bot, chat_id, tf_label: str):
    send_main_menu(bot, chat_id, tf_label)

# =========================
# ابزار صرافی‌ها و داده‌ها
# =========================

def _binance_interval(i: str) -> str:
    return {"1h": "1h", "4h": "4h", "1d": "1d", "15m": "15m"}[i]

def _kucoin_interval(i: str) -> str:
    return {"1h": "1hour", "4h": "4hour", "1d": "1day", "15m": "15min"}[i]

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
    except:
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
    except:
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

def create_plotly_chart(symbol: str, interval: str,
                        lookback_days: int, max_bars: int,
                        png_name: str, html_name: str) -> dict:

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
    fig.add_hline(y=70, line=dict(color="red", dash="dash"),  row=2, col=1)
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
        "symbol": symbol,
        "interval": interval,
        "png_path": png_path,
        "html_path": html_path,
    }

# =========================
# آلارم‌ها و واچ‌لیست
# =========================

def detect_alarms(symbol: str, interval: str, df: pd.DataFrame, cfg: dict) -> list:
    alarms = []
    if df.empty or len(df) < 3:
        return alarms

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if cfg.get("alarm_wma_direction", True):
        if prev["WMA20_slope"] <= 0 and last["WMA20_slope"] > 0:
            alarms.append("تغییر جهت WMA20 به صعودی")
        if prev["WMA20_slope"] >= 0 and last["WMA20_slope"] < 0:
            alarms.append("تغییر جهت WMA20 به نزولی")

    if cfg.get("alarm_cross_sma20", False):
        if prev["WMA20"] < prev["SMA20"] and last["WMA20"] > last["SMA20"]:
            alarms.append("برخورد WMA20 به بالای SMA20")
        if prev["WMA20"] > prev["SMA20"] and last["WMA20"] < last["SMA20"]:
            alarms.append("برخورد WMA20 به زیر SMA20")

    return alarms

def add_to_watchlist(cfg: dict, key: str, symbol: str) -> bool:
    wl = cfg.get(key, [])
    symbol = symbol.upper().strip()
    if not symbol.endswith("USDT"):
        return False
    if symbol in wl:
        return False
    wl.append(symbol)
    cfg[key] = wl
    save_config(cfg)
    return True

def remove_from_watchlist(cfg: dict, key: str, symbol: str) -> bool:
    wl = cfg.get(key, [])
    symbol = symbol.upper().strip()
    if symbol not in wl:
        return False
    wl.remove(symbol)
    cfg[key] = wl
    save_config(cfg)
    return True

# =========================
# اجرای چرخه‌ها
# =========================

def run_cycle(interval_name: str,
              bot,
              chat_id: int,
              symbols: list,
              tf: str,
              lookback_days: int,
              max_bars: int,
              watchlist_key: str,
              alarm_target_chat: int):

    if not chat_id:
        return

    start_time = now_utc_str()
    bot.send_message(chat_id, f"لوپ {tf}: شروع سیکل خودکار.\nزمان شروع: {start_time}\nتعداد نمادها: {len(symbols)}")

    cfg = load_config()
    wl = cfg.get(watchlist_key, [])

    for idx, sym in enumerate(symbols, start=1):
        bot.send_message(chat_id, f"در حال بررسی 🔍 {sym} ({idx}/{len(symbols)}) در سیکل {tf}...")
        df_raw = fetch_ohlc(sym, tf, lookback_days, max_bars)
        if df_raw.empty:
            continue
        df = df_raw[["o","h","l","c","v"]]
        df = compute_indicators(df)

        # اگر در واچ‌لیست است، آلارم‌ها را چک کن
        if sym in wl:
            alarms = detect_alarms(sym, tf, df, cfg)
            if alarms:
                LAST_ALARMS.append({
                    "symbol": sym,
                    "interval": tf,
                    "alarms": alarms,
                    "time": now_utc_str()
                })
                msg = f"آلارم‌ها برای {sym} ({tf}):\n" + "\n".join(f"- {a}" for a in alarms)
                # ارسال به چت مقصد (ربات دیگر یا همین ربات)
                if alarm_target_chat:
                    try:
                        bot.send_message(alarm_target_chat, msg)
                    except:
                        pass
                # ارسال خلاصه در چت فعلی
                bot.send_message(chat_id, msg)

    bot.send_message(chat_id, f"سیکل {tf} به پایان رسید. زمان پایان: {now_utc_str()}")

# =========================
# هندلرهای /start و منوها
# =========================

# ---- 1h ----
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

    @bot_1h.message_handler(commands=["start_cycle"])
    def start_cycle_all_from_1h(m):
        cfg = load_config()
        # شروع چرخه‌ها در ترد جدا
        threading.Thread(
            target=run_cycle,
            args=("1h", bot_1h, cfg.get("chat_id_1h"),
                  cfg.get("hourly_symbols", []),
                  cfg.get("hourly_interval", "1h"),
                  cfg.get("hourly_lookback_days", 5),
                  cfg.get("max_bars", 300),
                  "watchlist_1h",
                  cfg.get("alarm_target_chat_1h"))
        ).start()

    # دکمه‌ها
    @bot_1h.message_handler(func=lambda m: m.text == "راهنما ❓")
    def help_menu_1h(m):
        bot_1h.send_message(m.chat.id, HELP_TEXT)

    @bot_1h.message_handler(func=lambda m: m.text == "ریست منو و وضعیت 🔄")
    def reset_menu_1h(m):
        cfg = load_config()
        # ریست نمادها و واچ‌لیست و چت
        cfg["hourly_symbols"]   = DEFAULT_CONFIG["hourly_symbols"]
        cfg["watchlist_1h"]     = []
        cfg["chat_id_1h"]       = m.chat.id
        save_config(cfg)
        bot_1h.send_message(m.chat.id, "منو و وضعیت 1h ریست شد.")
        refresh_menu(bot_1h, m.chat.id, "1h")

    @bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی ⬅️")
    def back_to_main_1h(m):
        refresh_menu(bot_1h, m.chat.id, "1h")

    @bot_1h.message_handler(func=lambda m: m.text == "تست نمودار BTCUSDT 📈")
    def test_chart_1h(m):
        cfg = load_config()
        bot_1h.send_message(m.chat.id, "در حال آماده‌سازی نمودار 1h ...BTCUSDT 🧮\nزمان تقریبی: حدود ۵ تا ۱۰ ثانیه")
        info = create_plotly_chart(
            "BTCUSDT",
            cfg.get("hourly_interval", "1h"),
            cfg.get("hourly_lookback_days", 5),
            cfg.get("max_bars", 300),
            "BTCUSDT_1h.png",
            "BTCUSDT_1h.html"
        )
        with open(info["png_path"], "rb") as f:
            bot_1h.send_photo(m.chat.id, f, caption="نمودار تست BTCUSDT – 1h")

    @bot_1h.message_handler(func=lambda m: m.text == "اجرای فوری همین تایم‌فریم ⚡")
    def manual_run_1h(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("1h", bot_1h, m.chat.id,
                  cfg.get("hourly_symbols", []),
                  cfg.get("hourly_interval", "1h"),
                  cfg.get("hourly_lookback_days", 5),
                  cfg.get("max_bars", 300),
                  "watchlist_1h",
                  cfg.get("alarm_target_chat_1h"))
        ).start()

    @bot_1h.message_handler(func=lambda m: m.text == "👁️ واچ‌لیست‌ها")
    def watchlist_menu_1h(m):
        cfg = load_config()
        wl = cfg.get("watchlist_1h", [])
        txt = "واچ‌لیست 1h:\n" + ("\n".join(f"- {s}" for s in wl) if wl else "خالی است.")
        txt += "\n\nبرای افزودن نماد، نام آن را مثل «BCHUSDT» ارسال کن.\nبرای حذف، قبل از نماد علامت منفی بگذار: «-BCHUSDT»."
        bot_1h.send_message(m.chat.id, txt)

    @bot_1h.message_handler(func=lambda m: m.text == "⏱️ وضعیت لوپ‌ها")
    def loops_status_1h(m):
        bot_1h.send_message(m.chat.id, "لوپ 1h فعال است (در صورت اجرای دستی یا زمان‌بندی خارجی).")

    @bot_1h.message_handler(func=lambda m: m.text == "شروع سیکل خودکار 🔄")
    def start_cycle_btn_1h(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("1h", bot_1h, m.chat.id,
                  cfg.get("hourly_symbols", []),
                  cfg.get("hourly_interval", "1h"),
                  cfg.get("hourly_lookback_days", 5),
                  cfg.get("max_bars", 300),
                  "watchlist_1h",
                  cfg.get("alarm_target_chat_1h"))
        ).start()

    # افزودن/حذف نماد به واچ‌لیست با متن آزاد
    @bot_1h.message_handler(func=lambda m: True, content_types=["text"])
    def watchlist_edit_1h(m):
        text = m.text.strip().upper()
        cfg = load_config()
        if text.startswith("-") and text.endswith("USDT"):
            sym = text[1:]
            if remove_from_watchlist(cfg, "watchlist_1h", sym):
                bot_1h.send_message(m.chat.id, f"{sym} از واچ‌لیست 1h حذف شد.")
            else:
                bot_1h.send_message(m.chat.id, f"{sym} در واچ‌لیست نبود.")
        elif text.endswith("USDT"):
            if add_to_watchlist(cfg, "watchlist_1h", text):
                bot_1h.send_message(m.chat.id, f"{text} به واچ‌لیست 1h اضافه شد.")
            else:
                bot_1h.send_message(m.chat.id, f"امکان افزودن {text} نیست یا قبلاً اضافه شده.")
        else:
            # سایر متن‌ها را نادیده بگیر یا پیام راهنما بده
            pass

# ---- 4h ----
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

    @bot_4h.message_handler(commands=["start_cycle_4h"])
    def start_cycle_4h_cmd(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("4h", bot_4h, cfg.get("chat_id_4h"),
                  cfg.get("fourh_symbols", []),
                  cfg.get("fourh_interval", "4h"),
                  cfg.get("fourh_lookback_days", 15),
                  cfg.get("max_bars", 300),
                  "watchlist_4h",
                  cfg.get("alarm_target_chat_4h"))
        ).start()

    @bot_4h.message_handler(func=lambda m: m.text == "ریست منو و وضعیت 🔄")
    def reset_menu_4h(m):
        cfg = load_config()
        cfg["fourh_symbols"]   = DEFAULT_CONFIG["fourh_symbols"]
        cfg["watchlist_4h"]    = []
        cfg["chat_id_4h"]      = m.chat.id
        save_config(cfg)
        bot_4h.send_message(m.chat.id, "منو و وضعیت 4h ریست شد.")
        refresh_menu(bot_4h, m.chat.id, "4h")

    @bot_4h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی ⬅️")
    def back_to_main_4h(m):
        refresh_menu(bot_4h, m.chat.id, "4h")

    @bot_4h.message_handler(func=lambda m: m.text == "تست نمودار BTCUSDT 📈")
    def test_chart_4h(m):
        cfg = load_config()
        bot_4h.send_message(m.chat.id, "در حال آماده‌سازی نمودار 4h ...BTCUSDT 🧮\nزمان تقریبی: حدود ۵ تا ۱۰ ثانیه")
        info = create_plotly_chart(
            "BTCUSDT",
            cfg.get("fourh_interval", "4h"),
            cfg.get("fourh_lookback_days", 15),
            cfg.get("max_bars", 300),
            "BTCUSDT_4h.png",
            "BTCUSDT_4h.html"
        )
        with open(info["png_path"], "rb") as f:
            bot_4h.send_photo(m.chat.id, f, caption="نمودار تست BTCUSDT – 4h")

    @bot_4h.message_handler(func=lambda m: m.text == "اجرای فوری همین تایم‌فریم ⚡")
    def manual_run_4h(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("4h", bot_4h, m.chat.id,
                  cfg.get("fourh_symbols", []),
                  cfg.get("fourh_interval", "4h"),
                  cfg.get("fourh_lookback_days", 15),
                  cfg.get("max_bars", 300),
                  "watchlist_4h",
                  cfg.get("alarm_target_chat_4h"))
        ).start()

    @bot_4h.message_handler(func=lambda m: m.text == "👁️ واچ‌لیست‌ها")
    def watchlist_menu_4h(m):
        cfg = load_config()
        wl = cfg.get("watchlist_4h", [])
        txt = "واچ‌لیست 4h:\n" + ("\n".join(f"- {s}" for s in wl) if wl else "خالی است.")
        txt += "\n\nبرای افزودن نماد، نام آن را مثل «BCHUSDT» ارسال کن.\nبرای حذف، قبل از نماد علامت منفی بگذار: «-BCHUSDT»."
        bot_4h.send_message(m.chat.id, txt)

    @bot_4h.message_handler(func=lambda m: m.text == "⏱️ وضعیت لوپ‌ها")
    def loops_status_4h(m):
        bot_4h.send_message(m.chat.id, "لوپ 4h فعال است (در صورت اجرای دستی یا زمان‌بندی خارجی).")

    @bot_4h.message_handler(func=lambda m: m.text == "شروع سیکل خودکار 🔄")
    def start_cycle_btn_4h(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("4h", bot_4h, m.chat.id,
                  cfg.get("fourh_symbols", []),
                  cfg.get("fourh_interval", "4h"),
                  cfg.get("fourh_lookback_days", 15),
                  cfg.get("max_bars", 300),
                  "watchlist_4h",
                  cfg.get("alarm_target_chat_4h"))
        ).start()

    @bot_4h.message_handler(func=lambda m: True, content_types=["text"])
    def watchlist_edit_4h(m):
        text = m.text.strip().upper()
        cfg = load_config()
        if text.startswith("-") and text.endswith("USDT"):
            sym = text[1:]
            if remove_from_watchlist(cfg, "watchlist_4h", sym):
                bot_4h.send_message(m.chat.id, f"{sym} از واچ‌لیست 4h حذف شد.")
            else:
                bot_4h.send_message(m.chat.id, f"{sym} در واچ‌لیست نبود.")
        elif text.endswith("USDT"):
            if add_to_watchlist(cfg, "watchlist_4h", text):
                bot_4h.send_message(m.chat.id, f"{text} به واچ‌لیست 4h اضافه شد.")
            else:
                bot_4h.send_message(m.chat.id, f"امکان افزودن {text} نیست یا قبلاً اضافه شده.")
        else:
            pass

# ---- 1d ----
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

    @bot_1d.message_handler(commands=["start_cycle_1d"])
    def start_cycle_1d_cmd(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("1d", bot_1d, cfg.get("chat_id_1d"),
                  cfg.get("daily_symbols", []),
                  cfg.get("daily_interval", "1d"),
                  cfg.get("daily_lookback_days", 180),
                  cfg.get("max_bars", 300),
                  "watchlist_1d",
                  cfg.get("alarm_target_chat_1d"))
        ).start()

    @bot_1d.message_handler(func=lambda m: m.text == "ریست منو و وضعیت 🔄")
    def reset_menu_1d(m):
        cfg = load_config()
        cfg["daily_symbols"]   = DEFAULT_CONFIG["daily_symbols"]
        cfg["watchlist_1d"]    = []
        cfg["chat_id_1d"]      = m.chat.id
        save_config(cfg)
        bot_1d.send_message(m.chat.id, "منو و وضعیت 1d ریست شد.")
        refresh_menu(bot_1d, m.chat.id, "1d")

    @bot_1d.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی ⬅️")
    def back_to_main_1d(m):
        refresh_menu(bot_1d, m.chat.id, "1d")

    @bot_1d.message_handler(func=lambda m: m.text == "تست نمودار BTCUSDT 📈")
    def test_chart_1d(m):
        cfg = load_config()
        bot_1d.send_message(m.chat.id, "در حال آماده‌سازی نمودار 1d ...BTCUSDT 🧮\nزمان تقریبی: حدود ۵ تا ۱۰ ثانیه")
        info = create_plotly_chart(
            "BTCUSDT",
            cfg.get("daily_interval", "1d"),
            cfg.get("daily_lookback_days", 180),
            cfg.get("max_bars", 300),
            "BTCUSDT_1d.png",
            "BTCUSDT_1d.html"
        )
        with open(info["png_path"], "rb") as f:
            bot_1d.send_photo(m.chat.id, f, caption="نمودار تست BTCUSDT – 1d")

    @bot_1d.message_handler(func=lambda m: m.text == "اجرای فوری همین تایم‌فریم ⚡")
    def manual_run_1d(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("1d", bot_1d, m.chat.id,
                  cfg.get("daily_symbols", []),
                  cfg.get("daily_interval", "1d"),
                  cfg.get("daily_lookback_days", 180),
                  cfg.get("max_bars", 300),
                  "watchlist_1d",
                  cfg.get("alarm_target_chat_1d"))
        ).start()

    @bot_1d.message_handler(func=lambda m: m.text == "👁️ واچ‌لیست‌ها")
    def watchlist_menu_1d(m):
        cfg = load_config()
        wl = cfg.get("watchlist_1d", [])
        txt = "واچ‌لیست 1d:\n" + ("\n".join(f"- {s}" for s in wl) if wl else "خالی است.")
        txt += "\n\nبرای افزودن نماد، نام آن را مثل «BCHUSDT» ارسال کن.\nبرای حذف، قبل از نماد علامت منفی بگذار: «-BCHUSDT»."
        bot_1d.send_message(m.chat.id, txt)

    @bot_1d.message_handler(func=lambda m: m.text == "⏱️ وضعیت لوپ‌ها")
    def loops_status_1d(m):
        bot_1d.send_message(m.chat.id, "لوپ 1d فعال است (در صورت اجرای دستی یا زمان‌بندی خارجی).")

    @bot_1d.message_handler(func=lambda m: m.text == "شروع سیکل خودکار 🔄")
    def start_cycle_btn_1d(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("1d", bot_1d, m.chat.id,
                  cfg.get("daily_symbols", []),
                  cfg.get("daily_interval", "1d"),
                  cfg.get("daily_lookback_days", 180),
                  cfg.get("max_bars", 300),
                  "watchlist_1d",
                  cfg.get("alarm_target_chat_1d"))
        ).start()

    @bot_1d.message_handler(func=lambda m: True, content_types=["text"])
    def watchlist_edit_1d(m):
        text = m.text.strip().upper()
        cfg = load_config()
        if text.startswith("-") and text.endswith("USDT"):
            sym = text[1:]
            if remove_from_watchlist(cfg, "watchlist_1d", sym):
                bot_1d.send_message(m.chat.id, f"{sym} از واچ‌لیست 1d حذف شد.")
            else:
                bot_1d.send_message(m.chat.id, f"{sym} در واچ‌لیست نبود.")
        elif text.endswith("USDT"):
            if add_to_watchlist(cfg, "watchlist_1d", text):
                bot_1d.send_message(m.chat.id, f"{text} به واچ‌لیست 1d اضافه شد.")
            else:
                bot_1d.send_message(m.chat.id, f"امکان افزودن {text} نیست یا قبلاً اضافه شده.")
        else:
            pass

# ---- 15m ----
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

    @bot_15m.message_handler(commands=["start_cycle_15m"])
    def start_cycle_15m_cmd(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("15m", bot_15m, cfg.get("chat_id_15m"),
                  cfg.get("fifteenm_symbols", []),
                  cfg.get("fifteenm_interval", "15m"),
                  cfg.get("fifteenm_lookback_days", 3),
                  cfg.get("max_bars", 300),
                  "watchlist_15m",
                  cfg.get("alarm_target_chat_15m"))
        ).start()

    @bot_15m.message_handler(func=lambda m: m.text == "ریست منو و وضعیت 🔄")
    def reset_menu_15m(m):
        cfg = load_config()
        cfg["fifteenm_symbols"] = DEFAULT_CONFIG["fifteenm_symbols"]
        cfg["watchlist_15m"]    = []
        cfg["chat_id_15m"]      = m.chat.id
        save_config(cfg)
        bot_15m.send_message(m.chat.id, "منو و وضعیت 15m ریست شد.")
        refresh_menu(bot_15m, m.chat.id, "15m")

    @bot_15m.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی ⬅️")
    def back_to_main_15m(m):
        refresh_menu(bot_15m, m.chat.id, "15m")

    @bot_15m.message_handler(func=lambda m: m.text == "تست نمودار BTCUSDT 📈")
    def test_chart_15m(m):
        cfg = load_config()
        bot_15m.send_message(m.chat.id, "در حال آماده‌سازی نمودار 15m ...BTCUSDT 🧮\nزمان تقریبی: حدود ۵ تا ۱۰ ثانیه")
        info = create_plotly_chart(
            "BTCUSDT",
            cfg.get("fifteenm_interval", "15m"),
            cfg.get("fifteenm_lookback_days", 3),
            cfg.get("max_bars", 300),
            "BTCUSDT_15m.png",
            "BTCUSDT_15m.html"
        )
        with open(info["png_path"], "rb") as f:
            bot_15m.send_photo(m.chat.id, f, caption="نمودار تست BTCUSDT – 15m")

    @bot_15m.message_handler(func=lambda m: m.text == "اجرای فوری همین تایم‌فریم ⚡")
    def manual_run_15m(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("15m", bot_15m, m.chat.id,
                  cfg.get("fifteenm_symbols", []),
                  cfg.get("fifteenm_interval", "15m"),
                  cfg.get("fifteenm_lookback_days", 3),
                  cfg.get("max_bars", 300),
                  "watchlist_15m",
                  cfg.get("alarm_target_chat_15m"))
        ).start()

    @bot_15m.message_handler(func=lambda m: m.text == "👁️ واچ‌لیست‌ها")
    def watchlist_menu_15m(m):
        cfg = load_config()
        wl = cfg.get("watchlist_15m", [])
        txt = "واچ‌لیست 15m:\n" + ("\n".join(f"- {s}" for s in wl) if wl else "خالی است.")
        txt += "\n\nبرای افزودن نماد، نام آن را مثل «BCHUSDT» ارسال کن.\nبرای حذف، قبل از نماد علامت منفی بگذار: «-BCHUSDT»."
        bot_15m.send_message(m.chat.id, txt)

    @bot_15m.message_handler(func=lambda m: m.text == "⏱️ وضعیت لوپ‌ها")
    def loops_status_15m(m):
        bot_15m.send_message(m.chat.id, "لوپ 15m فعال است (در صورت اجرای دستی یا زمان‌بندی خارجی).")

    @bot_15m.message_handler(func=lambda m: m.text == "شروع سیکل خودکار 🔄")
    def start_cycle_btn_15m(m):
        cfg = load_config()
        threading.Thread(
            target=run_cycle,
            args=("15m", bot_15m, m.chat.id,
                  cfg.get("fifteenm_symbols", []),
                  cfg.get("fifteenm_interval", "15m"),
                  cfg.get("fifteenm_lookback_days", 3),
                  cfg.get("max_bars", 300),
                  "watchlist_15m",
                  cfg.get("alarm_target_chat_15m"))
        ).start()

    @bot_15m.message_handler(func=lambda m: True, content_types=["text"])
    def watchlist_edit_15m(m):
        text = m.text.strip().upper()
        cfg = load_config()
        if text.startswith("-") and text.endswith("USDT"):
            sym = text[1:]
            if remove_from_watchlist(cfg, "watchlist_15m", sym):
                bot_15m.send_message(m.chat.id, f"{sym} از واچ‌لیست 15m حذف شد.")
            else:
                bot_15m.send_message(m.chat.id, f"{sym} در واچ‌لیست نبود.")
        elif text.endswith("USDT"):
            if add_to_watchlist(cfg, "watchlist_15m", text):
                bot_15m.send_message(m.chat.id, f"{text} به واچ‌لیست 15m اضافه شد.")
            else:
                bot_15m.send_message(m.chat.id, f"امکان افزودن {text} نیست یا قبلاً اضافه شده.")
        else:
            pass

# =========================
# اجرای ربات‌ها
# =========================

def run_all_bots():
    threads = []
    if bot_1h:
        threads.append(threading.Thread(target=bot_1h.infinity_polling))
    if bot_4h:
        threads.append(threading.Thread(target=bot_4h.infinity_polling))
    if bot_1d:
        threads.append(threading.Thread(target=bot_1d.infinity_polling))
    if bot_15m:
        threads.append(threading.Thread(target=bot_15m.infinity_polling))

    for t in threads:
        t.daemon = True
        t.start()

    # نگه داشتن برنامه
    while True:
        time.sleep(1)

if __name__ == "__main__":
    run_all_bots()