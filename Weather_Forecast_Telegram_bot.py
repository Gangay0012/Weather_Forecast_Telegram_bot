import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- CONFIGURAZIONE API ----------------
VISUALCROSSING_KEY = "MDD4NPYGYTHY92TQNNZPDJFJH"
WEATHERBIT_KEY = "52f55430d57d474881c455348151f401"
TOMORROW_KEY = "IPAEGNhmJ5S2GsScmY9hkwohFm8ChdTP"
TELEGRAM_TOKEN = "8524080997:AAE3Bj3MTJ2GKvWjlJO0Mb-S6LwLpM22l0c"

# ---------------- FUNZIONI API ----------------
def open_meteo_forecast(lat, lon, days):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&timezone=auto"
    r = requests.get(url).json()
    return r["daily"]["temperature_2m_max"], r["daily"]["time"]

def visualcrossing_forecast(city_name, days):
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city_name}?unitGroup=metric&key={VISUALCROSSING_KEY}&elements=datetime,tempmax&include=days&contentType=json"
    r = requests.get(url).json()
    temps = []
    dates = []
    for day in r.get("days", [])[:days]:
        temps.append(day.get("tempmax"))
        dates.append(day.get("datetime"))
    while len(temps) < days:
        temps.append(None)
        dates.append("N/A")
    return temps, dates

def weatherbit_forecast(lat, lon, days):
    url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={lat}&lon={lon}&days={days}&key={WEATHERBIT_KEY}"
    r = requests.get(url).json()
    temps = [day["max_temp"] for day in r["data"]]
    dates = [day["datetime"] for day in r["data"]]
    return temps, dates

def tomorrow_forecast(lat, lon):
    url = f"https://api.tomorrow.io/v4/timelines?location={lat},{lon}&fields=temperatureMax&timesteps=1d&units=metric&apikey={TOMORROW_KEY}"
    r = requests.get(url).json()
    intervals = r["data"]["timelines"][0]["intervals"]
    temps = [day["values"]["temperatureMax"] for day in intervals]
    dates = [day["startTime"][:10] for day in intervals]
    return temps, dates

def geocode_city(city_name):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1"
    r = requests.get(url).json()
    if "results" in r and len(r["results"]) > 0:
        return r["results"][0]["latitude"], r["results"][0]["longitude"]
    else:
        return None, None

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

        om_temp, om_dates = open_meteo_forecast(lat, lon, days)
        vc_temp, vc_dates = visualcrossing_forecast(city_name, days)
        wb_temp, wb_dates = weatherbit_forecast(lat, lon, days)
        tm_temp, tm_dates = tomorrow_forecast(lat, lon)

        message = f"🌤️ Previsioni temperatura massima per {city_name} (prossimi {days} giorni):\n\n"

        for i in range(days):
            temps = [om_temp[i], vc_temp[i], wb_temp[i], tm_temp[i]]
            valid_temps = list(filter(None, temps))
            avg = sum(valid_temps)/len(valid_temps) if valid_temps else None
            min_temp = min(valid_temps) if valid_temps else None
            max_temp = max(valid_temps) if valid_temps else None

            message += f"📅 {om_dates[i]}:\n"
            message += f"  🌐 Open-Meteo: {om_temp[i]}°C\n"
            message += f"  🌐 Visual Crossing: {vc_temp[i]}°C\n"
            message += f"  🌐 Weatherbit: {wb_temp[i]}°C\n"
            message += f"  🌐 Tomorrow.io: {tm_temp[i]}°C\n"
            message += f"  ➤ Media: {avg:.1f}°C, Range: {min_temp}-{max_temp}°C\n\n"

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"Errore: {str(e)}")

# ---------------- SETUP BOT ----------------
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("forecast", forecast_command))

print("Bot avviato...")
app.run_polling()
