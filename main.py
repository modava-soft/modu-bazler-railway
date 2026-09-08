# -*- coding: utf-8 -*-
# Modu Bazler v7 – نسخه کامل بازنویسی‌شده
# بخش ۱: ایمپورت‌ها + کانفیگ + ساخت ربات‌ها + منوی اصلی

import os
import io
import json
import time
import base64
import threading
import datetime as dt

import numpy as np
import pandas as pd
from PIL import Image
from fpdf import FPDF

import requests
import telebot
from telebot import types
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# =========================
# مسیرها
# =========================

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")
CFG_PATH   = os.path.join(DATA_DIR, "config.json")

for d in [DATA_DIR, CHARTS_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)


# =========================
# کانفیگ
# =========================

DEFAULT_CFG = {
    "symbols_1h": [],
    "symbols_4h": [],
    "symbols_1d": [],
    "symbols_15m": [],

    "chat_id_1h": None,
    "chat_id_4h": None,
    "chat_id_1d": None,
    "chat_id_15m": None,

    "alarm_wma_direction": True,
    "alarm_cross_sma20": True,
    "alarm_cross_sma100": True,
    "alarm_cross_sma200": True,
    "alarm_sma20_direction": True,
    "alarm_sma100_direction": True,
    "alarm_sma200_direction": True,

    "report_steps": True,
    "max_bars": 300
}


def load_config():
    if not os.path.exists(CFG_PATH):
        save_config(DEFAULT_CFG)
        return DEFAULT_CFG
    try:
        with open(CFG_PATH, "r") as f:
            return json.load(f)
    except:
        return DEFAULT_CFG


def save_config(cfg):
    with open(CFG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)


def reset_config():
    save_config(DEFAULT_CFG)
    return DEFAULT_CFG


# =========================
# ساخت ربات‌ها
# =========================

TOKEN_1H  = "PUT-YOUR-TOKEN-HERE"
TOKEN_4H  = "PUT-YOUR-TOKEN-HERE"
TOKEN_1D  = "PUT-YOUR-TOKEN-HERE"
TOKEN_15M = "PUT-YOUR-TOKEN-HERE"

bot_1h  = telebot.TeleBot(TOKEN_1H,  parse_mode="HTML")
bot_4h  = telebot.TeleBot(TOKEN_4H,  parse_mode="HTML")
bot_1d  = telebot.TeleBot(TOKEN_1D,  parse_mode="HTML")
bot_15m = telebot.TeleBot(TOKEN_15M, parse_mode="HTML")


# =========================
# منوی اصلی
# =========================

def send_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("مدیریت نمادهای 1h", "مدیریت نمادهای 4h")
    kb.row("مدیریت نمادهای 1d", "مدیریت نمادهای 15m")
    kb.row("تنظیم آلارم‌ها", "گزارش آلارم‌ها")
    kb.row("اجرای چرخه‌ها")
    kb.row("ریست برنامه")
    bot_1h.send_message(chat_id, "منوی اصلی:", reply_markup=kb)


@bot_1h.message_handler(commands=["start"])
def start_cmd(m):
    cfg = load_config()
    cfg["chat_id_1h"] = m.chat.id
    save_config(cfg)
    send_main_menu(m.chat.id)


# =========================
# مدیریت نمادها
# =========================

def send_symbol_menu(chat_id, group):
    cfg = load_config()
    symbols = cfg.get(f"symbols_{group}", [])

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(f"افزودن نماد به {group}", f"حذف نماد از {group}")
    kb.row("بازگشت به منوی اصلی")

    text = f"نمادهای فعال در {group}:\n" + "\n".join(symbols) if symbols else "هیچ نمادی ثبت نشده است."
    bot_1h.send_message(chat_id, text, reply_markup=kb)


@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1h")
def manage_1h(m):
    send_symbol_menu(m.chat.id, "1h")


@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 4h")
def manage_4h(m):
    send_symbol_menu(m.chat.id, "4h")


@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1d")
def manage_1d(m):
    send_symbol_menu(m.chat.id, "1d")


@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 15m")
def manage_15m(m):
    send_symbol_menu(m.chat.id, "15m")


# =========================
# افزودن نماد
# =========================

@bot_1h.message_handler(func=lambda m: m.text.startswith("افزودن نماد به"))
def add_symbol(m):
    group = m.text.split("به")[1].strip()
    msg = bot_1h.send_message(m.chat.id, f"نماد موردنظر برای افزودن به {group} را وارد کنید:")
    bot_1h.register_next_step_handler(msg, lambda ms: add_symbol_final(ms, group))


def add_symbol_final(m, group):
    sym = m.text.upper().replace(" ", "")
    cfg = load_config()

    if sym not in cfg[f"symbols_{group}"]:
        cfg[f"symbols_{group}"].append(sym)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"نماد {sym} به {group} اضافه شد.")
    else:
        bot_1h.send_message(m.chat.id, f"نماد {sym} قبلاً در {group} وجود دارد.")

    send_symbol_menu(m.chat.id, group)


# =========================
# حذف نماد
# =========================

@bot_1h.message_handler(func=lambda m: m.text.startswith("حذف نماد از"))
def remove_symbol(m):
    group = m.text.split("از")[1].strip()
    msg = bot_1h.send_message(m.chat.id, f"نمادی که باید از {group} حذف شود را وارد کنید:")
    bot_1h.register_next_step_handler(msg, lambda ms: remove_symbol_final(ms, group))


def remove_symbol_final(m, group):
    sym = m.text.upper().replace(" ", "")
    cfg = load_config()

    if sym in cfg[f"symbols_{group}"]:
        cfg[f"symbols_{group}"].remove(sym)
        save_config(cfg)
        bot_1h.send_message(m.chat.id, f"نماد {sym} از {group} حذف شد.")
    else:
        bot_1h.send_message(m.chat.id, f"نماد {sym} در {group} وجود ندارد.")

    send_symbol_menu(m.chat.id, group)


# =========================
# بازگشت به منوی اصلی
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
def back_to_main(m):
    send_main_menu(m.chat.id)

# =========================
# دریافت دیتا از بایننس
# =========================

def get_klines(symbol: str, interval: str, limit: int = 300):
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

        df["open"]   = df["open"].astype(float)
        df["high"]   = df["high"].astype(float)
        df["low"]    = df["low"].astype(float)
        df["close"]  = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)

        df.index = pd.to_datetime(df["open_time"], unit="ms")

        return df

    except Exception as e:
        print("خطا در دریافت دیتا:", e)
        return None


# =========================
# اندیکاتورها (نسخه کامل)
# =========================

def calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["sma20"]  = df["close"].rolling(20).mean()
    df["sma100"] = df["close"].rolling(100).mean()
    df["sma200"] = df["close"].rolling(200).mean()

    df["wma20"] = df["close"].rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, 21)),
        raw=True
    )

    df["wma_dir"] = df["wma20"].diff()

    df["cross_sma20"]  = df["close"] - df["sma20"]
    df["cross_sma100"] = df["close"] - df["sma100"]
    df["cross_sma200"] = df["close"] - df["sma200"]

    return df


# =========================
# سیستم آلارم‌ها
# =========================

def check_alarms(df: pd.DataFrame, cfg: dict):
    alarms = []
    last = df.iloc[-1]

    # جهت WMA20
    if cfg.get("alarm_wma_direction", True):
        if last["wma_dir"] > 0:
            alarms.append("WMA20 صعودی")
        elif last["wma_dir"] < 0:
            alarms.append("WMA20 نزولی")

    # کراس SMA20
    if cfg.get("alarm_cross_sma20", True):
        if last["cross_sma20"] > 0:
            alarms.append("قیمت بالای SMA20")
        else:
            alarms.append("قیمت زیر SMA20")

    # کراس SMA100
    if cfg.get("alarm_cross_sma100", True):
        if last["cross_sma100"] > 0:
            alarms.append("قیمت بالای SMA100")
        else:
            alarms.append("قیمت زیر SMA100")

    # کراس SMA200
    if cfg.get("alarm_cross_sma200", True):
        if last["cross_sma200"] > 0:
            alarms.append("قیمت بالای SMA200")
        else:
            alarms.append("قیمت زیر SMA200")

    # جهت SMA20
    if cfg.get("alarm_sma20_direction", True):
        if df["sma20"].diff().iloc[-1] > 0:
            alarms.append("SMA20 صعودی")
        else:
            alarms.append("SMA20 نزولی")

    # جهت SMA100
    if cfg.get("alarm_sma100_direction", True):
        if df["sma100"].diff().iloc[-1] > 0:
            alarms.append("SMA100 صعودی")
        else:
            alarms.append("SMA100 نزولی")

    # جهت SMA200
    if cfg.get("alarm_sma200_direction", True):
        if df["sma200"].diff().iloc[-1] > 0:
            alarms.append("SMA200 صعودی")
        else:
            alarms.append("SMA200 نزولی")

    return alarms


# =========================
# ثبت آلارم‌ها
# =========================

LAST_ALARMS = {
    "1h": [],
    "4h": [],
    "1d": [],
    "15m": []
}

def now_utc_str():
    return dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def record_alarm(group: str, symbol: str, interval: str, alarms: list):
    LAST_ALARMS[group].append({
        "symbol": symbol,
        "interval": interval,
        "alarms": alarms,
        "time": now_utc_str()
    })


# =========================
# گزارش مرحله‌به‌مرحله
# =========================

def report_step(bot, chat_id, text: str, cfg: dict):
    if cfg.get("report_steps", True):
        try:
            bot.send_message(chat_id, f"🔹 {text}")
        except:
            pass

# =========================
# نمودار تک‌نماد (استایل نسخه قبل)
# =========================

def make_single_chart_png(symbol: str, interval: str, df: pd.DataFrame, quality: str = "B") -> str:
    """
    ساخت نمودار تک‌نماد با استایل کندل + SMA20/100/200 + WMA20
    خروجی: مسیر فایل PNG
    """

    if quality == "A":
        width, height, scale = 2000, 1500, 3
    elif quality == "B":
        width, height, scale = 1800, 1400, 2
    else:
        width, height, scale = 1500, 1200, 2

    fig = make_subplots(
        rows=1,
        cols=1,
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
        x=df.index, y=df["sma20"], name="SMA20",
        line=dict(color="orange", width=2)
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["sma100"], name="SMA100",
        line=dict(color="blue", width=2)
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["sma200"], name="SMA200",
        line=dict(color="purple", width=2)
    ), row=1, col=1)

    # WMA20
    fig.add_trace(go.Scatter(
        x=df.index, y=df["wma20"], name="WMA20",
        line=dict(color="green", width=2)
    ), row=1, col=1)

    fig.update_layout(
        title=f"{symbol} – {interval}",
        template="plotly_dark",
        width=width,
        height=height,
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=True
    )

    out_path = os.path.join(CHARTS_DIR, f"{symbol}_{interval}.png")
    fig.write_image(out_path, scale=scale)

    return out_path


# =========================
# ساخت صفحهٔ تجمیعی ۱۲تایی (PNG)
# =========================

def make_combined_page_png(image_paths: list, page_number: int, quality: str = "B") -> str:
    """
    از لیست مسیر PNGها، یک صفحه تجمیعی ۱۲تایی می‌سازد.
    """

    if quality == "A":
        width, height, scale = 2000, 1500, 3
    elif quality == "B":
        width, height, scale = 1800, 1400, 2
    else:
        width, height, scale = 1500, 1200, 2

    ROWS, COLS = 3, 4

    fig = make_subplots(
        rows=ROWS,
        cols=COLS,
        specs=[[{"type": "domain"} for _ in range(COLS)] for _ in range(ROWS)],
        horizontal_spacing=0.01,
        vertical_spacing=0.01
    )

    idx = 0
    for r in range(1, ROWS + 1):
        for c in range(1, COLS + 1):
            if idx < len(image_paths):
                img_path = image_paths[idx]
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


# =========================
# ساخت PDF که هر صفحه ۱۲ نمودار دارد
# =========================

def build_pdf_12_per_page(interval: str, single_pngs: list) -> str:
    """
    از لیست PNGهای تک‌نماد، PDF می‌سازد که هر صفحه ۱۲ نمودار دارد.
    """

    pdf_path = os.path.join(PDF_DIR, f"combined_{interval}.pdf")
    pdf = FPDF(unit="pt", format="A4")

    pages = []
    for i in range(0, len(single_pngs), 12):
        chunk = single_pngs[i:i+12]
        page_num = (i // 12) + 1
        page_img = make_combined_page_png(chunk, page_num, "B")
        pages.append(page_img)

    for page_img in pages:
        pdf.add_page()
        pdf.image(page_img, x=10, y=10, w=575)

    pdf.output(pdf_path)

    return pdf_path


# =========================
# فلو کامل ساخت نمودار + PDF
# =========================

def build_all_charts_and_pdf(interval: str, symbol_df_map: dict, quality: str = "B", bot=None, chat_id=None, cfg=None):
    """
    ساخت:
    - نمودار تک‌نماد
    - صفحات ۱۲تایی
    - PDF نهایی
    - گزارش مرحله‌به‌مرحله
    """

    def report(msg):
        if cfg and cfg.get("report_steps", True) and bot and chat_id:
            try:
                bot.send_message(chat_id, f"🔹 {msg}")
            except:
                pass
        else:
            print(msg)

    report("شروع ساخت نمودارهای تک‌نماد…")

    single_pngs = []
    for sym, df in symbol_df_map.items():
        report(f"ساخت نمودار {sym}")
        df2 = calc_indicators(df)
        png_path = make_single_chart_png(sym, interval, df2, quality)
        single_pngs.append(png_path)

    if not single_pngs:
        report("هیچ نموداری ساخته نشد.")
        return None

    report("ساخت صفحات ۱۲تایی…")
    pdf_path = build_pdf_12_per_page(interval, single_pngs)

    report("PDF آماده شد.")
    return pdf_path


# =========================
# اجرای یک چرخه کامل
# =========================

def run_cycle(group: str, bot, interval: str, cfg: dict):
    """
    اجرای کامل چرخه:
    - دریافت دیتا
    - ساخت نمودار تک‌نماد
    - ساخت صفحات ۱۲تایی
    - ساخت PDF
    - ارسال PDF
    - گزارش مرحله‌به‌مرحله
    """

    chat_id = cfg.get(f"chat_id_{group}")
    if not chat_id:
        print(f"chat_id برای {group} تنظیم نشده.")
        return

    symbols = cfg.get(f"symbols_{group}", [])
    if not symbols:
        report_step(bot, chat_id, f"هیچ نمادی برای {group} ثبت نشده.", cfg)
        return

    report_step(bot, chat_id, f"شروع چرخه {group}", cfg)

    symbol_df_map = {}

    # دریافت دیتا برای هر نماد
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

        symbol_df_map[sym] = df

    if not symbol_df_map:
        report_step(bot, chat_id, "هیچ دیتایی برای ساخت نمودار وجود ندارد.", cfg)
        return

    # ساخت نمودار + PDF
    report_step(bot, chat_id, "ساخت نمودارها و PDF…", cfg)
    pdf_path = build_all_charts_and_pdf(
        interval=interval,
        symbol_df_map=symbol_df_map,
        quality="B",
        bot=bot,
        chat_id=chat_id,
        cfg=cfg
    )

    if pdf_path:
        try:
            with open(pdf_path, "rb") as f:
                bot.send_document(chat_id, f, caption=f"PDF تجمیعی {interval}")
            report_step(bot, chat_id, "PDF ارسال شد.", cfg)
        except Exception as e:
            print("خطا در ارسال PDF:", e)

    report_step(bot, chat_id, f"پایان چرخه {group}", cfg)


# =========================
# اجرای چرخه‌ها از منوی اصلی
# =========================

@bot_1h.message_handler(func=lambda m: m.text == "اجرای چرخه‌ها")
def run_all_cycles(m):
    cfg = load_config()

 {sym}", cfg)

        df = get_klines(sym, interval, cfg["max_bars"])
        if df is None:
            report_step(bot, chat_id, f"❌ خطا در دریافت دیتا {sym}", cfg)
            continue

        df = calc_indicators(df)

        # بررسی آلارم‌ها
        alarms = check_alarms(df, cfg)
        if alarms:
            record_alarm(group, sym, interval, alarms)

        symbol_df_map[sym] = df

    if not symbol_df_map:
        report_step(bot, chat_id, "هیچ دیتایی برای ساخت نمودار وجود ندارد.", cfg)
        return

    # ساخت نمودار + PDF
    report_step(bot, chat_id, "ساخت نمودارها و PDF…", cfg)
    pdf_path = build_all_charts_and_pdf(
        interval=interval,
        symbol_df_map=symbol_df_map,
        quality="B",
        bot=bot,
        chat_id=chat_id,
        cfg=cfg
    )

    if pdf_path:
        try:
            with open(pdf_path, "rb") as f:
                bot.send_document(chat_id, f, caption=f"PDF تجمیعی {interval}")
            report_step(bot, chat_id, "PDF ارسال شد.", cfg)
        except Exception as e:
            print("خطا در ارسال PDF:", e)

    report_step(bot, chat_id, f"پایان چرخه {group}", cfg)


# =========================
# اجرای چرخه‌ها از منوی اصلی
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
# زمان‌بندی خودکار
# =========================

def scheduler_loop():
    while True:
        now = dt.datetime.utcnow()
        minute = now.minute
        hour = now.hour

        cfg = load_config()

        # 1h → هر ساعت دقیقه 22
        if minute == 22:
            run_cycle("1h", bot_1h, "1h", cfg)

        # 4h → ساعت‌های 2، 6، 10، 14، 18، 22 دقیقه 7
        if minute == 7 and hour in [2, 6, 10, 14, 18, 22]:
            run_cycle("4h", bot_4h, "4h", cfg)

        # 1d → هر روز ساعت 1:05
        if hour == 1 and minute == 5:
            run_cycle("1d", bot_1d, "1d", cfg)

        # 15m → هر ۱۵ دقیقه
        if minute % 15 == 0:
            run_cycle("15m", bot_15m, "15m", cfg)

        time.sleep(30)


# =========================
# اجرای ربات‌ها + زمان‌بندی
# =========================

def start_bots():
    # زمان‌بندی در یک Thread جدا
    threading.Thread(target=scheduler_loop, daemon=True).start()

    # اجرای ربات‌ها
    threading.Thread(target=bot_1h.infinity_polling, daemon=True).start()
    threading.Thread(target=bot_4h.infinity_polling, daemon=True).start()
    threading.Thread(target=bot_1d.infinity_polling, daemon=True).start()
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