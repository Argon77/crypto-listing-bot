import time
import logging
import os
import requests
from config import FETCH_INTERVAL_SECONDS
from exchanges.binance import BinanceExchange
from exchanges.bybit import BybitExchange
from exchanges.okx import OKXExchange
from exchanges.bitget import BitgetExchange

# Telegram bot settings
TELEGRAM_BOT_TOKEN = '7587990879:AAEg0oIpa2ILPF-uAhEfMAsRP7YK0GntNgc'
CHAT_ID = '1004156477'

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("listings.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
OUTPUT_FILE = "output/listings.txt"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            logger.info("Message sent successfully to Telegram")
        else:
            logger.error(f"Failed to send message to Telegram: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")

def format_listing(exchange_name, listing):
    symbol = listing.get("symbol", "UNKNOWN")
    date = listing.get("date", "unknown time")
    # date may be datetime; convert to isoformat
    if hasattr(date, 'isoformat'):
        date = date.isoformat()
    return f"{exchange_name} : {symbol} ({date})"

def fetch_and_display():
    exchanges = [
        BinanceExchange(),
        BybitExchange(),
        OKXExchange(),
        BitgetExchange(),
    ]

    output_lines = []
    no_update = []

    # Send message indicating the start of the listing check
    send_telegram_message("Начинаю проверку новых листингов...")

    for exchange in exchanges:
        name = exchange.__class__.__name__.replace("Exchange", "")
        try:
            logger.info(f"Fetching data from {name}")
            upcoming = exchange.get_upcoming_listings()
        except Exception as e:
            logger.error(f"{name}: unexpected error {e}")
            upcoming = []

        if upcoming:
            for lst in upcoming:
                line = format_listing(name, lst)
                print(line)
                output_lines.append(line)
                send_telegram_message(line)  # Send message to Telegram
        else:
            no_update.append(name)

    # Append no-update messages at the end
    for name in no_update:
        msg = f"{name} -> На данный момент нет новых листингов"
        print(msg)
        output_lines.append(msg)

    # Write to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in output_lines:
            f.write(line + "\n")


if __name__ == "__main__":
    logger.info("Starting crypto listings fetcher.")
    try:
        while True:
            logger.info("Starting fetch cycle.")
            fetch_and_display()
            logger.info(f"Sleeping for {FETCH_INTERVAL_SECONDS} seconds...\n")
            time.sleep(FETCH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Fetcher stopped by user.")