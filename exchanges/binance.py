from interfaces import ExchangeInterface
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BinanceExchange(ExchangeInterface):
    BASE_URL = "https://www.binance.com"
    ANNOUNCEMENTS_URL = f"{BASE_URL}/en/support/announcement/c-48"

    def get_upcoming_listings(self):
        logger.info("Fetching upcoming listings from Binance announcements...")
        listings = self._scrape_announcements()

        upcoming = []
        for item in listings:
            title = item["title"].lower()
            if "will list" in title or "will be listed" in title:
                content = self._fetch_announcement_content(item["url"])
                if content:
                    parsed = self._parse_listing_details(content)
                    if parsed:
                        upcoming.append(parsed)
        return upcoming

    def get_past_listings(self):
        return []

    def _scrape_announcements(self):
        try:
            response = requests.get(self.ANNOUNCEMENTS_URL, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch Binance announcements: {e}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        announcements = []

        for a in soup.select("a.css-1ej4hfo"):  # Класс может поменяться
            title = a.get_text(strip=True)
            href = a.get("href")
            if href and "/en/support/announcement/" in href:
                announcements.append({
                    "title": title,
                    "url": f"{self.BASE_URL}{href}",
                })

        return announcements

    def _fetch_announcement_content(self, url):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch announcement content from {url}: {e}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        content = soup.get_text(separator="\n")
        return content

    def _parse_listing_details(self, content):
        """
        Ищем дату начала торгов и символ.
        """
        # Пример строки: "Trading will open for XYZ/USDT trading pair at 2025-06-01 10:00 (UTC)"
        pair_match = re.search(r"trading will open for (\w+/\w+)", content, re.IGNORECASE)
        date_match = re.search(r"at\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", content)

        if not pair_match or not date_match:
            logger.warning("Couldn't parse trading pair or time.")
            return None

        pair_raw = pair_match.group(1).upper()
        date_str = date_match.group(1)
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            logger.warning(f"Invalid date format in Binance announcement: {date_str}")
            return None

        # Преобразуем формат пары: ABC/USDT → ABC-USDT
        formatted_symbol = pair_raw.replace("/", "-")

        return {
            "symbol": formatted_symbol,
            "date": dt.isoformat(),
        }
