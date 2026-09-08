# -*- coding: utf-8 -*-
# Modu Bazler v7 – main.py

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


# ===== paths & config =====

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
PDF_DIR    = os.path.join(DATA_DIR, "pdf")
CFG_PATH   = os.path.join(DATA_DIR, "config.json")

for d in [DATA_DIR, CHARTS_DIR, PDF_DIR]:
    os.makedirs(d, exist_ok=True)

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


# ===== bots =====

TOKEN_1H  = "PUT-YOUR-TOKEN-HERE"
TOKEN_4H  = "PUT-YOUR-TOKEN-HERE"
TOKEN_1D  = "PUT-YOUR-TOKEN-HERE"
TOKEN_15M = "PUT-YOUR-TOKEN-HERE"

bot_1h  = telebot.TeleBot(TOKEN_1H,  parse_mode="HTML")
bot_4h  = telebot.TeleBot(TOKEN_4H,  parse_mode="HTML")
bot_1d  = telebot.TeleBot(TOKEN_1D,  parse_mode="HTML")
bot_15m = telebot.TeleBot(TOKEN_15M, parse_mode="HTML")


# ===== main menu =====

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


# ===== symbols management =====

def send_symbol_menu(chat_id, group):
    cfg = load_config()
    symbols = cfg.get(f"symbols_{group}", [])
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(f"افزودن نماد به {group}", f"حذف نماد از {group}")
    kb.row("بازگشت به منوی اصلی")
    text = f"نمادهای فعال در {group}:\n" + "\n".join(symbols) if symbols else "هیچ نمادی ثبت نشده است."
    bot_1h.send_message(chat_id, text, reply_markup=kb)

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1h")
def manage_1h(m): send_symbol_menu(m.chat.id, "1h")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 4h")
def manage_4h(m): send_symbol_menu(m.chat.id, "4h")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 1d")
def manage_1d(m): send_symbol_menu(m.chat.id, "1d")

@bot_1h.message_handler(func=lambda m: m.text == "مدیریت نمادهای 15m")
def manage_15m(m): send_symbol_menu(m.chat.id, "15m")

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

@bot_1h.message_handler(func=lambda m: m.text == "بازگشت به منوی اصلی")
def back_to_main(m): send_main_menu(m.chat.id)


# ===== data + indicators + alarms =====

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

def calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sma20"]  = df["close"].rolling(20).mean()
    df["sma100"] = df["close"].rolling(100).mean()
    df["sma200"] = df["close"].rolling(200).mean()
    df["wma20"] = df["close"].rolling(20).apply(
        lambda x: np.average(x, weights=np.arange(1, 21)), raw=True
    )
    df["wma_dir"] = df["wma20"].diff()
    df["cross_sma20"]  = df["close"] - df["sma20"]
    df["cross_sma100"] = df["close"] - df["sma100"]
    df["cross_sma200"] = df["close"] - df["sma200"]
    return df

def check_alarms(df: pd.DataFrame, cfg: dict):
    alarms = []
    last = df.iloc[-1]
    if cfg.get("alarm_wma_direction", True):
        if last["wma_dir"] > 0: alarms.append("WMA20 صعودی")
        elif last["wma_dir"] < 0: alarms.append("WMA20 نزولی")
    if cfg.get("alarm_cross_sma20", True):
        alarms.append("قیمت بالای SMA20" if last["cross_sma20"] > 0 else "قیمت زیر SMA20")
    if cfg.get("alarm_cross_sma100", True):
        alarms.append("قیمت بالای SMA100" if last["cross_sma100"] > 0 else "قیمت زیر SMA100")
    if cfg.get("alarm_cross_sma200", True):
        alarms.append("قیمت بالای SMA200" if last["cross_sma200"] > 0 else "قیمت زیر SMA200")
    if cfg.get("alarm_sma20_direction", True):
        alarms.append("SMA20 صعودی" if df["sma20"].diff().iloc[-1] > 0 else "SMA20 نزولی")
    if cfg.get("alarm_sma100_direction", True):
        alarms.append("SMA100 صعودی" if df["sma100"].diff().iloc[-1] > 0 else "SMA100 نزولی")
    if cfg.get("alarm_sma200_direction", True):
        alarms.append("SMA200 صعودی" if df["sma200"].diff().iloc[-1] > 0 else "SMA200 نزولی")
    return alarms

LAST_ALARMS = {"1h": [], "4h": [], "1d": [], "15m": []}

def now_utc_str(): return dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def record_alarm(group: str, symbol: str, interval: str, alarms: list):
    LAST_ALARMS[group].append({
        "symbol": symbol,
        "interval": interval,
        "alarms": alarms,
        "time": now_utc_str()
    })

def report_step(bot, chat_id, text: str, cfg: dict):
    if cfg.get("report_steps", True):
        try: bot.send_message(chat_id, f"🔹 {text}")
        except: pass


# ===== charts + combined pages + PDF =====

def make_single_chart_png(symbol: str, interval: str, df: pd.DataFrame, quality: str = "B") -> str:
    if quality == "A":
        width, height, scale = 2000, 1500, 3
    elif quality == "B":
        width, height, scale = 1800, 1400, 2
    else:
        width, height, scale = 1500, 1200, 2

    fig = make_subplots(rows=1, cols=1, specs=[[{"type": "xy"}]])
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price"
    ), row=1, col=1)

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

def make_combined_page_png(image_paths: list, page_number: int, quality: str = "B") -> str:
    if quality == "A":
        width, height, scale = 2000, 1500, 3
    elif quality == "B":
        width, height, scale = 1800, 1400, 2
    else:
        width, height, scale = 1500, 1200, 2

    ROWS, COLS = 3, 4
    fig = make_subplots(
        rows=ROWS, cols=COLS,
        specs=[[{"type": "domain"} for _ in range(COLS)] for _ in range(ROWS)],
        horizontal_spacing=0.01, vertical_spacing=0.01
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
                    fig.add_trace(go.Image(source=f"data:image/png;base64,{encoded}"), row=r, col=c)
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

def build_pdf_12_per_page(interval: str, single_pngs: list) -> str:
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

def build_all_charts_and_pdf(interval: str, symbol_df_map: dict, quality: str = "B", bot=None, chat_id=None, cfg=None):
    def report(msg):
        if cfg and cfg.get("report_steps", True) and bot and chat_id:
            try: bot.send_message(chat_id, f"🔹 {msg}")
            except: pass
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


# ===== cycles + scheduler =====

def run_cycle(group: str, bot, interval: str, cfg: dict):
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

    for sym in symbols:
        report_step(bot, chat_id, f"دریافت دیتا برای {sym}", cfg)
        df = get_klines(sym, interval, cfg["max_bars"])
        if df is None:
            report_step(bot, chat_id, f"❌ خطا در دریافت دیتا {sym}", cfg)
            continue
        df = calc_indicators(df)
        alarms = check_alarms(df, cfg)
        if alarms:
            record_alarm(group, sym, interval, alarms)
        symbol_df_map[sym] = df

    if not symbol_df_map:
        report_step(bot, chat_id, "هیچ دیتایی برای ساخت نمودار وجود ندارد.", cfg)
        return

    report_step(bot, chat_id, "ساخت نمودارها و PDF…", cfg)
    pdf_path = build_all_charts_and_pdf(interval, symbol_df_map, "B", bot, chat_id, cfg)

    if pdf_path:
        try:
            with open(pdf_path, "rb") as f:
                bot.send_document(chat_id, f, caption=f"PDF تجمیعی {interval}")
            report_step(bot, chat_id, "PDF ارسال شد.", cfg)
        except Exception as e:
            print("خطا در ارسال PDF:", e)

    report_step(bot, chat_id, f"پایان چرخه {group}", cfg)

@bot_1h.message_handler(func=lambda m: m.text == "اجرای چرخه‌ها")
def run_all_cycles(m):
    cfg = load_config()
    if bot_1h:  run_cycle("1h",  bot_1h,  "1h",  cfg)
    if bot_4h:  run_cycle("4h",  bot_4h,  "4h",  cfg)
    if bot_1d:  run_cycle("1d",  bot_1d,  "1d",  cfg)
    if bot_15m: run_cycle("15m", bot_15m, "15m", cfg)

def scheduler_loop():
    while True:
        now = dt.datetime.utcnow()
        minute = now.minute
        hour = now.hour
        cfg = load_config()

        if minute == 22:
            run_cycle("1h", bot_1h, "1h", cfg)
        if minute == 7 and hour in [2, 6, 10, 14, 18, 22]:
            run_cycle("4h", bot_4h, "4h", cfg)
        if hour == 1 and minute == 5:
            run_cycle("1d", bot_1d, "1d", cfg)
        if minute % 15 == 0:
            run_cycle("15m", bot_15m, "15m", cfg)

        time.sleep(30)

def start_bots():
    threading.Thread(target=scheduler_loop, daemon=True).start()
    threading.Thread(target=bot_1h.infinity_polling,  daemon=True).start()
    threading.Thread(target=bot_4h.infinity_polling,  daemon=True).start()
    threading.Thread(target=bot_1d.infinity_polling,  daemon=True).start()
    threading.Thread(target=bot_15m.infinity_polling, daemon=True).start()
    while True:
        time.sleep(1)


if __name__ == "__main__":
    print("Modu Bazler v7 started.")
    start_bots()