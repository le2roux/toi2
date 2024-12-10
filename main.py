import asyncio
from binance.client import Client
from telegram import Bot
import talib
import numpy as np

# Binance API keys
API_KEY = "WjIxSj1ZPjptcUVNbnsZTUKlGLo8Lj6YkrvCUz8D2NZH93Yd8IUNtvHPDFOFUZ1Q"
API_SECRET = "rWHYwxyISKFJMnsPFbaFIVrnobZFDxFj9QQyoIiZYKmZwAakub6tuP7rhqpgwzko"

# Telegram Bot token and chat ID
TELEGRAM_TOKEN = '7262381054:AAEZDAt4rbz5ZdD8QTaQckz6iEV64X-ykmw'
TELEGRAM_CHAT_ID = '1042306196'

# Initialize Binance client and Telegram bot
client = Client(API_KEY, API_SECRET)
bot = Bot(token=TELEGRAM_TOKEN)

# Trading configuration
EXCLUDE_COINS = ["BTCUSDT", "ETHUSDT"]  # Coins to exclude from monitoring

async def send_telegram_message(message):
    """Send a message via Telegram."""
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

def fetch_candlestick_data(symbol, interval, limit=50):
    """Fetch historical candlestick data."""
    candles = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    closes = np.array([float(c[4]) for c in candles], dtype=np.float64)
    return closes

def check_conditions(symbol):
    """Check if MA5 crosses MA10 from bottom to top."""
    closes = fetch_candlestick_data(symbol, interval="3m")

    if len(closes) < 10:  # Ensure there are enough data points
        return False

    # Calculate moving averages
    ma5 = talib.SMA(closes, timeperiod=5)
    ma10 = talib.SMA(closes, timeperiod=10)

    # Check if MA5 crosses MA10 from bottom to top
    if ma5[-1] > ma10[-1] and ma5[-2] <= ma10[-2]:
        return True

    return False

def get_active_pairs():
    """Fetch active USDT pairs."""
    exchange_info = client.get_exchange_info()
    active_pairs = []
    for symbol_info in exchange_info["symbols"]:
        if (
            symbol_info["status"] == "TRADING"
            and symbol_info["symbol"].endswith("USDT")
            and symbol_info["symbol"] not in EXCLUDE_COINS
        ):
            active_pairs.append(symbol_info["symbol"])
    return active_pairs

async def main():
    """Main monitoring loop."""
    while True:
        try:
            # Fetch all active USDT pairs
            active_pairs = get_active_pairs()

            for symbol in active_pairs:
                if check_conditions(symbol):
                    await send_telegram_message(
                        f"🔔 CONDITION MET\nSymbol: {symbol}\n"
                        "MA5 crossed MA10 from bottom to top on the 3-minute timeframe."
                    )
                await asyncio.sleep(1)  # Avoid hitting API limits
        except Exception as e:
            await send_telegram_message(f"⚠️ An error occurred: {str(e)}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
