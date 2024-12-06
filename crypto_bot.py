import telebot
from binance.client import Client
from binance.exceptions import BinanceAPIException
import json
import math

# Configuration file path
CONFIG_FILE = "config.json"

# Default configuration template
default_config = {
    "binance_api_key": "WjIxSj1ZPjptcUVNbnsZTUKlGLo8Lj6YkrvCUz8D2NZH93Yd8IUNtvHPDFOFUZ1Q",
    "binance_api_secret": "rWHYwxyISKFJMnsPFbaFIVrnobZFDxFj9QQyoIiZYKmZwAakub6tuP7rhqpgwzko",
    "telegram_token": "8177261485:AAGpp3sJc7TMioXuB963CmGlrS7-znP1pQo",
    "chat_id": "1042306196",
    "budget": 0.0,
    "max_transactions": 0
}

# Initialize or read configuration
def init_config():
    try:
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(CONFIG_FILE, "w") as file:
            json.dump(default_config, file)
        config = default_config
    return config

# Update configuration
def update_config(key, value):
    config = init_config()
    config[key] = value
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)

# Load configuration
config = init_config()
bot = telebot.TeleBot(config["telegram_token"])
binance_client = Client(config["binance_api_key"], config["binance_api_secret"])

# Start Command
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("Set Budget"),
        telebot.types.KeyboardButton("Buy Coin"),
        telebot.types.KeyboardButton("Sell Coin"),
        telebot.types.KeyboardButton("Check Balance")
    )
    bot.send_message(
        message.chat.id,
        "Welcome to the Binance Telegram Bot! Choose an option:",
        reply_markup=markup
    )

# Set Budget
@bot.message_handler(func=lambda message: message.text == "Set Budget")
def set_budget(message):
    bot.send_message(message.chat.id, "Enter the budget in USDT:")
    bot.register_next_step_handler(message, process_budget)

def process_budget(message):
    try:
        budget = float(message.text)
        update_config("budget", budget)
        bot.send_message(message.chat.id, f"Budget set to {budget} USDT.\nNow, enter the max number of transactions:")
        bot.register_next_step_handler(message, process_transactions)
    except ValueError:
        bot.send_message(message.chat.id, "Invalid budget. Please enter a number.")

def process_transactions(message):
    try:
        max_transactions = int(message.text)
        update_config("max_transactions", max_transactions)
        bot.send_message(message.chat.id, f"Max transactions set to {max_transactions}.")
    except ValueError:
        bot.send_message(message.chat.id, "Invalid number. Please enter an integer.")

# Buy Coin
@bot.message_handler(func=lambda message: message.text == "Buy Coin")
def buy_coin(message):
    """Prompt the user to enter the coin symbol for buying."""
    bot.send_message(message.chat.id, "Enter the coin symbol (e.g., ADAUSDT):")
    bot.register_next_step_handler(message, execute_buy_order)

def get_valid_quantity(symbol, amount_in_usdt):
    """Fetch the valid quantity based on LOT_SIZE filter and price."""
    try:
        # Get the symbol's trading information
        exchange_info = binance_client.get_symbol_info(symbol)
        
        # Extract the LOT_SIZE filter for the symbol
        lot_size_filter = next(filter(lambda x: x['filterType'] == 'LOT_SIZE', exchange_info['filters']))
        step_size = float(lot_size_filter['stepSize'])  # Get the allowed step size for quantity
        
        # Get the current price of the coin
        price = float(binance_client.get_symbol_ticker(symbol=symbol)['price'])
        
        # Calculate the quantity based on the budget
        quantity = amount_in_usdt / price

        # Adjust quantity to match the step size
        quantity = math.floor(quantity / step_size) * step_size

        return round(quantity, int(-math.log10(step_size)))
    except Exception as e:
        print(f"Error getting valid quantity: {e}")
        return None

def execute_buy_order(message):
    """Execute a market buy order."""
    coin = message.text.strip().upper()

    try:
        # Load the budget from the config file
        budget = init_config()["budget"]
        
        if budget <= 0:
            bot.send_message(message.chat.id, "Error: Budget not set. Please set a budget first.")
            return

        # Get the valid quantity for the order
        quantity = get_valid_quantity(coin, budget)
        
        if quantity is None or quantity <= 0:
            bot.send_message(message.chat.id, "Error: Unable to determine a valid quantity.")
            return

        # Place the buy order
        order = binance_client.order_market_buy(symbol=coin, quantity=quantity)
        price = float(binance_client.get_symbol_ticker(symbol=coin)['price'])
        
        # Send the confirmation message
        bot.send_message(message.chat.id, f"Buy order placed for {coin}.\nPrice: {price}, Quantity: {quantity}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error placing buy order: {str(e)}")

# Sell Coin
@bot.message_handler(func=lambda message: message.text == "Sell Coin")
def sell_coin(message):
    bot.send_message(message.chat.id, "Enter the coin symbol (e.g., ADAUSDT):")
    bot.register_next_step_handler(message, execute_sell_order)

def execute_sell_order(message):
    coin = message.text.strip().upper()
    profit_margin = 1.013  # 1.30% profit margin
    try:
        trades = binance_client.get_my_trades(symbol=coin)
        if not trades:
            bot.send_message(message.chat.id, f"No recent trades found for {coin}.")
            return

        buy_price = float(trades[-1]["price"])
        quantity = float(trades[-1]["qty"])
        sell_price = round(buy_price * profit_margin, 5)

        binance_client.order_limit_sell(symbol=coin, quantity=quantity, price=sell_price)
        bot.send_message(
            message.chat.id, f"Sell order placed for {quantity} {coin} at {sell_price} USDT."
        )
    except BinanceAPIException as e:
        bot.send_message(message.chat.id, f"Binance error: {str(e)}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {str(e)}")

# Check Spot Balance
@bot.message_handler(func=lambda message: message.text == "Check Balance")
def check_balance(message):
    try:
        balances = binance_client.get_account()["balances"]
        response = "Spot Wallet Balances:\n"
        for asset in balances:
            free = float(asset["free"])
            if free > 1:  # Show balances greater than 1 USDT
                response += f"{asset['asset']}: {free}\n"
        bot.send_message(message.chat.id, response)
    except BinanceAPIException as e:
        bot.send_message(message.chat.id, f"Binance error: {str(e)}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {str(e)}")

# Run Bot
bot.polling()
