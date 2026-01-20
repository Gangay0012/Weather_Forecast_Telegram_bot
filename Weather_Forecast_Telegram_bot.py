import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ==========================================================
# API KEYS
# ==========================================================
TELEGRAM_TOKEN = "8524080997:AAE3Bj3MTJ2GKvWjlJO0Mb-S6LwLpM22l0c"
WEATHERBIT_KEY = "52f55430d57d474881c455348151f401"
TOMORROW_KEY = "IPAEGNhmJ5S2GsScmY9hkwohFm8ChdTP"

# ==========================================================
# OPEN-METEO ECMWF
# ==========================================================
def open_meteo_ecmwf(lat, lon, days):
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&daily=temperature_2m_max"
            "&forecast_model=ecmwf"
            "&timezone=auto"
        )
        r = requests.get(url, timeout=10).json()
        temps = r.get("daily", {}).get("temperature_2m_max", [None]*days)
        dates = r.get("daily", {}).get("time", [None]*days)
        return temps[:days], dates[:days]
    except:
        return [None]*days, ["N/A"]*days

# ==========================================================
# ALTRE API
# ==========================================================
def weatherbit_forecast(lat, lon, days):
    try:
        url = (
            "https://api.weatherbit.io/v2.0/forecast/daily"
            f"?lat={lat}&lon={lon}&days={days}&key={WEATHERBIT_KEY}"
        )
        r = requests.get(url, timeout=10).json()
        return (
            [d["max_temp"] for d in r.get("data", [])[:days]],
            [d["datetime"] for d in r.get("data", [])[:days]]
        )
    except:
        return [None]*days, ["N/A"]*days

def tomorrow_forecast(lat, lon, days):
    try:
        url = (
            "https://api.tomorrow.io/v4/timelines"
            f"?location={lat},{lon}"
            "&fields=temperatureMax"
            "&timesteps=1d&units=metric"
            f"&apikey={TOMORROW_KEY}"
        )
        r = requests.get(url, timeout=10).json()
        intervals = r.get("data", {}).get("timelines", [])[0].get("intervals", [])[:days]
        temps = [i["values"]["temperatureMax"] for i in intervals]
        dates = [i["startTime"][:10] for i in intervals]
        return temps, dates
    except:
        return [None]*days, ["N/A"]*days

def geocode_city(city):
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        r = requests.get(url, timeout=10).json()
        if r.get("results"):
            res = r["results"][0]
            return res["latitude"], res["longitude"]
    except:
        pass
    return None, None

def make_bar(temp, width=14):
    if temp is None:
        return "N/A"
    temp = max(-5, min(40, temp))
    filled = int((temp + 5) / 45 * width)
    return "█" * max(1, filled)

# ==========================================================
# TELEGRAM COMMAND
# ==========================================================
async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso:\n/forecast <città> <giorni (1–10)> [soglia °C]"
        )
        return

    # ---------------- PARSING INPUT ----------------
    city = " ".join(context.args[:-1])
    days = None
    threshold = None

    try:
        if len(context.args) >= 3:
            threshold_str = context.args[-1].replace(",", ".")
            threshold = float(threshold_str)
            days = int(context.args[-2])
            city = " ".join(context.args[:-2])
        else:
            days = int(context.args[-1])
    except ValueError:
        await update.message.reply_text(
            "Errore nel parsing dei parametri.\n"
            "Formato corretto: /forecast <città> <numero giorni (1–10)> [soglia °C]\n"
            "Esempio: /forecast london 3 10.5"
        )
        return

    if days < 1 or days > 10:
        await update.message.reply_text("Il numero di giorni deve essere tra 1 e 10.")
        return

    lat, lon = geocode_city(city)
    if lat is None:
        await update.message.reply_text(f"Città non trovata: {city}")
        return

    # ---------------- MODELLI ----------------
    ecmwf_t, dates = open_meteo_ecmwf(lat, lon, days)
    wb_t, _ = weatherbit_forecast(lat, lon, days)
    tm_t, _ = tomorrow_forecast(lat, lon, days)

    msg = f"🌡️ **Temperature massime – {city}**\n\n"

    spread_max = 1.5  # spread massimo accettabile

    for i in range(days):
        temps = {
            "ECMWF": ecmwf_t[i],
            "Weat": wb_t[i],
            "Tomo": tm_t[i]
        }

        valid = [v for v in temps.values() if v is not None]
        if not valid:
            continue

        lo = min(valid)
        hi = max(valid)
        spread = hi - lo

        msg += f"📅 {dates[i]}\n"
        for name, val in temps.items():
            msg += f"{name:4} {val}°C {make_bar(val)}\n"

        msg += f"➡️ Range: **{lo:.1f} – {hi:.1f}°C** | Spread: **{spread:.2f}°C**\n"

        if threshold is not None:
            above = len([v for v in valid if v > threshold])
            prob = above / len(valid) * 100
            decision = "✅ BET" if prob >= 70 and spread <= spread_max else "❌ NO BET"
            msg += f"   Prob > {threshold}°C: {prob:.0f}% → {decision}\n\n"
        else:
            msg += "\n"

    await update.message.reply_text(msg)

# ==========================================================
# AVVIO BOT
# ==========================================================
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("forecast", forecast_command))

print("🤖 Bot Telegram avviato – STEP 3 ottimizzato con 3 fonti")
app.run_polling()
