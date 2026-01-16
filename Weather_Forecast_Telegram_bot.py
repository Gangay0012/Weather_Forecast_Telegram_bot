import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- API KEYS (default per test locale) ----------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8524080997:AAE3Bj3MTJ2GKvWjlJO0Mb-S6LwLpM22l0c")
VISUALCROSSING_KEY = os.environ.get("VISUALCROSSING_KEY", "MDD4NPYGYTHY92TQNNZPDJFJH")
WEATHERBIT_KEY = os.environ.get("WEATHERBIT_KEY", "52f55430d57d474881c455348151f401")
TOMORROW_KEY = os.environ.get("TOMORROW_KEY", "IPAEGNhmJ5S2GsScmY9hkwohFm8ChdTP")

# ---------------- FUNZIONI API ----------------
def open_meteo_forecast(lat, lon, days):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
        r = requests.get(url, timeout=10).json()
        temps = r.get("daily", {}).get("temperature_2m_max", [None]*days)
        dates = r.get("daily", {}).get("time", [None]*days)
        return temps[:days], dates[:days]
    except:
        return [None]*days, ["N/A"]*days

def visualcrossing_forecast(city_name, days):
    try:
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city_name}?unitGroup=metric&key={VISUALCROSSING_KEY}&elements=datetime,tempmax&include=days&contentType=json"
        r = requests.get(url, timeout=10).json()
        temps = [day.get("tempmax") for day in r.get("days", [])[:days]]
        dates = [day.get("datetime") for day in r.get("days", [])[:days]]
        while len(temps) < days:
            temps.append(None)
            dates.append("N/A")
        return temps, dates
    except:
        return [None]*days, ["N/A"]*days

def weatherbit_forecast(lat, lon, days):
    try:
        url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={lat}&lon={lon}&days={days}&key={WEATHERBIT_KEY}"
        r = requests.get(url, timeout=10).json()
        temps = [day["max_temp"] for day in r.get("data", [])[:days]]
        dates = [day["datetime"] for day in r.get("data", [])[:days]]
        while len(temps) < days:
            temps.append(None)
            dates.append("N/A")
        return temps, dates
    except:
        return [None]*days, ["N/A"]*days

def tomorrow_forecast(lat, lon, days):
    try:
        url = f"https://api.tomorrow.io/v4/timelines?location={lat},{lon}&fields=temperatureMax&timesteps=1d&units=metric&apikey={TOMORROW_KEY}"
        r = requests.get(url, timeout=10).json()
        intervals = r.get("data", {}).get("timelines", [])[0].get("intervals", [])[:days]
        temps = [day["values"]["temperatureMax"] for day in intervals]
        dates = [day["startTime"][:10] for day in intervals]
        while len(temps) < days:
            temps.append(None)
            dates.append("N/A")
        return temps, dates
    except:
        return [None]*days, ["N/A"]*days

def geocode_city(city_name):
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1"
        r = requests.get(url, timeout=10).json()
        if "results" in r and len(r["results"]) > 0:
            return r["results"][0]["latitude"], r["results"][0]["longitude"]
        return None, None
    except:
        return None, None

# ---------------- FUNZIONE PER IL GRAFICO ORIZZONTALE ----------------
def make_bar(temp, min_val=0, max_val=40, width=20):
    if temp is None:
        return "N/A"
    scaled = int((temp - min_val) / (max_val - min_val) * width)
    return "█" * max(1, scaled)

# ---------------- FUNZIONE DI RISPOSTA ----------------
async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text("Formato corretto: /forecast <nome città> <numero giorni (max 10)>")
            return

        city_name = " ".join(context.args[:-1])
        days = int(context.args[-1])
        if days < 1 or days > 10:
            await update.message.reply_text("Il numero di giorni deve essere tra 1 e 10.")
            return

        lat, lon = geocode_city(city_name)
        if lat is None:
            await update.message.reply_text(f"Non ho trovato la città: {city_name}")
            return

        # chiamate API
        om_temp, om_dates = open_meteo_forecast(lat, lon, days)
        vc_temp, vc_dates = visualcrossing_forecast(city_name, days)
        wb_temp, wb_dates = weatherbit_forecast(lat, lon, days)
        tm_temp, tm_dates = tomorrow_forecast(lat, lon, days)

        message = f"🌤️ Previsioni temperature massime per {city_name} (prossimi {days} giorni):\n\n"

        for i in range(days):
            temps = [om_temp[i], vc_temp[i], wb_temp[i], tm_temp[i]]
            valid_temps = [t for t in temps if t is not None]
            avg = sum(valid_temps)/len(valid_temps) if valid_temps else None
            min_temp = min(valid_temps) if valid_temps else None
            max_temp = max(valid_temps) if valid_temps else None

            message += f"📅 {om_dates[i]}\n"
            message += f"  Open-Meteo      : {om_temp[i]}°C\n  {make_bar(om_temp[i])}\n"
            message += f"  Visual Crossing : {vc_temp[i]}°C\n  {make_bar(vc_temp[i])}\n"
            message += f"  Weatherbit      : {wb_temp[i]}°C\n  {make_bar(wb_temp[i])}\n"
            message += f"  Tomorrow.io     : {tm_temp[i]}°C\n  {make_bar(tm_temp[i])}\n"
            if avg is not None:
                message += f"  ➤ Media: {avg:.1f}°C, Range: {min_temp}-{max_temp}°C\n\n"
            else:
                message += "\n"

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"Errore: {str(e)}")

# ---------------- SETUP BOT ----------------
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("forecast", forecast_command))

print("Bot avviato...")
app.run_polling()
