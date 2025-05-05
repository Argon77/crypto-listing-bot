# exchanges/bitget.py
from interfaces import ExchangeInterface
import requests
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class BitgetExchange(ExchangeInterface):
    ANNOUNCEMENTS_URL = "https://api.bitget.com/api/v2/spot/public/symbols"  # Используем правильный URL
    MAX_RETRIES = 3

    def get_upcoming_listings(self):
        logger.info("Fetching upcoming listings from Bitget...")
        listings = self._fetch_listings()

        upcoming = []
        for item in listings:
            # Предполагаем, что мы ищем только активные торговые пары
            if item.get("status") == "TRADING":
                # Формируем торговую пару
                formatted_symbol = f"{item['baseAsset']}-{item['quoteAsset']}"
                upcoming.append({
                    "symbol": formatted_symbol,
                    "date": datetime.now(timezone.utc)  # Поставим текущее время как временную метку
                })
        return upcoming

    def get_past_listings(self):
        return []  # В данный момент мы не отслеживаем прошедшие листинги

    def _fetch_listings(self):
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = requests.get(self.ANNOUNCEMENTS_URL, timeout=10)
                resp.raise_for_status()
                return resp.json().get("data", [])
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch Bitget listings: {e}")
                if attempt == self.MAX_RETRIES:
                    return []
                logger.warning(f"Retrying {attempt}/{self.MAX_RETRIES}...")
