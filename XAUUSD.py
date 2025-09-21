import os 
import requests
from datetime import datetime, timezone
from dateutil import parser
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import pytz

# Load .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

# Timezones
IST = pytz.timezone('Asia/Kolkata')

def get_xauusd(interval="5min", outputsize=12):
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={interval}&outputsize={outputsize}&apikey={API_KEY}"
    response = requests.get(url).json()
    if "values" not in response:
        return None, response.get("message", "Unknown error")
    data = response["values"]
    data.reverse()
    return data, None

# /xau command
async def xau_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for h in range(1, 6):
        keyboard.append([InlineKeyboardButton(f"5-min {h}H", callback_data=f"5min_{h}h")])
    tf_15 = [1, 2, 3, 4, 5, 6, 9, 12, 18, 21]
    for h in tf_15:
        keyboard.append([InlineKeyboardButton(f"15-min {h}H", callback_data=f"15min_{h}h")])
    for h in range(6, 61, 6):
        keyboard.append([InlineKeyboardButton(f"1H {h}H", callback_data=f"1h_{h}h")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📊 Select XAU/USD timeframe:", reply_markup=reply_markup)

# Format message
def format_msg(data, tf, interval, tz="UTC"):
    msg = f"📊 XAU/USD (Gold vs USD) OHLCV Data ({tf} - {interval}) - {tz}\n\n"
    for candle in data:
        utc_dt = parser.parse(candle['datetime'])
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)

        if tz == "IST":
            dt = utc_dt.astimezone(IST)
        else:
            dt = utc_dt

        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        msg += f"🕒 {dt_str}\nO: {candle['open']} | H: {candle['high']} | L: {candle['low']} | C: {candle['close']} | V: {candle.get('volume','N/A')}\n\n"
    return msg

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data_str = query.data

    # अगर conversion बटन है
    if data_str.startswith("convert_"):
        _, tz, interval, tf = data_str.split("_")
        data, error = get_xauusd(interval=interval, outputsize=context.user_data.get("outputsize"))
        if error:
            await query.edit_message_text(f"❌ Error fetching data: {error}")
            return

        msg = format_msg(data, tf, interval, tz)
        keyboard = [
            [InlineKeyboardButton("📌 Show in UTC", callback_data=f"convert_UTC_{interval}_{tf}")],
            [InlineKeyboardButton("📌 Show in IST", callback_data=f"convert_IST_{interval}_{tf}")]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # अगर timeframe select किया गया है
    interval, tf = data_str.split("_")

    # Map interval → candles count
    candles_map = {}
    if interval == "5min":
        candles_map = {"1h": 12, "2h": 24, "3h": 36, "4h": 48, "5h": 60}
    elif interval == "15min":
        candles_map = {
            "1h": 4, "2h": 8, "3h": 12, "4h": 16, "5h": 20, "6h": 24,
            "9h": 36, "12h": 48, "18h": 72, "21h": 84
        }
    elif interval == "1h":
        candles_map = {f"{h}h": h for h in range(6, 61, 6)}

    outputsize = candles_map.get(tf)
    if not outputsize:
        await query.edit_message_text("❌ Invalid timeframe.")
        return

    # Save outputsize for later reuse
    context.user_data["outputsize"] = outputsize

    data, error = get_xauusd(interval=interval, outputsize=outputsize)
    if error:
        await query.edit_message_text(f"❌ Error fetching data: {error}")
        return

    msg = format_msg(data, tf, interval, "UTC")
    keyboard = [
        [InlineKeyboardButton("📌 Show in UTC", callback_data=f"convert_UTC_{interval}_{tf}")],
        [InlineKeyboardButton("📌 Show in IST", callback_data=f"convert_IST_{interval}_{tf}")]
    ]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# Main function
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("xau", xau_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ Bot is running... use /xau in Telegram")
    app.run_polling()

if __name__ == "__main__":
    main()
