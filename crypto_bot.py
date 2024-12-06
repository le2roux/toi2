
from binance.client import Client
from binance.enums import *
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import time
import math


# Binance API Keys
API_KEY = "WjIxSj1ZPjptcUVNbnsZTUKlGLo8Lj6YkrvCUz8D2NZH93Yd8IUNtvHPDFOFUZ1Q"
API_SECRET = "rWHYwxyISKFJMnsPFbaFIVrnobZFDxFj9QQyoIiZYKmZwAakub6tuP7rhqpgwzko"

# Telegram Bot Token
TELEGRAM_TOKEN = '8177261485:AAGpp3sJc7TMioXuB963CmGlrS7-znP1pQo'


# Initialize Binance Client
client = Client(API_KEY, API_SECRET)

# Utility Functions
def round_quantity(quantity, step_size):
    """Round quantity to the nearest valid increment."""
    precision = int(round(-math.log(step_size, 10), 0))
    return round(quantity, precision)

async def place_buy_order(symbol, usdt_amount):
    """Place a market buy order."""
    try:
        # Get price and calculate quantity
        ticker = client.get_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])
        quantity = usdt_amount / price

        # Get minimum quantity step size for the symbol
        info = client.get_symbol_info(symbol)
        step_size = float(next(filter(lambda f: f['filterType'] == 'LOT_SIZE', info['filters']))['stepSize'])
        quantity = round_quantity(quantity, step_size)

        # Place buy order
        order = client.create_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        return quantity, price, order
    except Exception as e:
        return None, None, str(e)

async def place_sell_order(symbol, quantity, target_price):
    """Place a market sell order."""
    try:
        order = client.create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_LIMIT,
            quantity=quantity,
            price=f"{target_price:.2f}",
            timeInForce=TIME_IN_FORCE_GTC
        )
        return order
    except Exception as e:
        return str(e)

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the bot starts."""
    await update.message.reply_text("Welcome to the Auto Trading Bot! Use /trade <symbol> to start trading.")

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle trading requests."""
    if len(context.args) != 1:
        await update.message.reply_text("Please provide a valid coin symbol (e.g., /trade BTCUSDT).")
        return

    symbol = context.args[0].upper()
    usdt_amount = 200
    profit_percent = 1.2

    # Place buy order
    await update.message.reply_text(f"Placing a buy order for {symbol} with {usdt_amount} USDT...")
    quantity, buy_price, result = await place_buy_order(symbol, usdt_amount)
    
    if not quantity:
        await update.message.reply_text(f"Error placing buy order: {result}")
        return

    await update.message.reply_text(f"Bought {quantity} {symbol} at {buy_price} USDT.")

    # Calculate target sell price
    target_price = buy_price * (1 + profit_percent / 100)
    target_price = round(target_price, 2)  # Round target price to 2 decimal places

    # Monitor price and place sell order
    await update.message.reply_text(f"Monitoring price to sell at {target_price} USDT...")
    while True:
        ticker = client.get_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])

        if current_price >= target_price:
            sell_result = await place_sell_order(symbol, quantity, target_price)
            if isinstance(sell_result, str):
                await update.message.reply_text(f"Error placing sell order: {sell_result}")
            else:
                await update.message.reply_text(f"Sold {quantity} {symbol} at {target_price} USDT!")
            break
        else:
            time.sleep(5)

# Main Function
def main():
    """Start the Telegram bot."""
    # Initialize the application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("trade", trade))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
