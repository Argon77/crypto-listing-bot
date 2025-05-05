from interfaces import ExchangeInterface
import requests
from requests.exceptions import ReadTimeout
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class BybitExchange(ExchangeInterface):
    ANNOUNCEMENTS_URL = "https://announcements.bybit.com/en-US/"
    MAX_RETRIES = 3
    HEADERS = {"User-Agent": "Mozilla/5.0"}

    def get_upcoming_listings(self):
        logger.info("Fetching upcoming listings from Bybit...")
        listings = self._scrape_announcements()

        upcoming = []
        for item in listings:
            title = item["title"].lower()
            if "will list" in title or "new spot listing" in title:
                content = self._fetch_announcement_content(item["url"])
                if content:
                    parsed = self._parse_listing_details(content)
                    if parsed and parsed["date"] > datetime.now(timezone.utc):
                        upcoming.append(parsed)
        return upcoming

    def get_past_listings(self):
        return []

    def _scrape_announcements(self):
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = requests.get(self.ANNOUNCEMENTS_URL, timeout=10, headers=self.HEADERS)
                resp.raise_for_status()
                break
            except ReadTimeout:
                logger.warning(f"Bybit timeout, retry {attempt}/{self.MAX_RETRIES}")
            except Exception as e:
                logger.error(f"Bybit fetch error: {e}")
                return []
        else:
            logger.error("Bybit announcements unavailable after retries")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        announcements = []
        for a in soup.select(".announcement-item a[href*='/en-US/']"):
            title = a.get_text(strip=True)
            href = a.get('href')
            if href:
                url = href if href.startswith('http') else f"https://announcements.bybit.com{href}"
                announcements.append({"title": title, "url": url})
        logger.info(f"Found {len(announcements)} total Bybit announcements")
        return announcements

    def _fetch_announcement_content(self, url):
        try:
            resp = requests.get(url, timeout=10, headers=self.HEADERS)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch Bybit announcement content from {url}: {e}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        return soup.get_text(separator="\n")

    def _parse_listing_details(self, content):
        pair_match = re.search(r"trading for (\w+)/(\w+)", content, re.IGNORECASE)
        date_match = re.search(r"will start on ([A-Za-z]+ \d{1,2}, \d{4}) at (\d{2}:\d{2}) UTC", content)

        if not pair_match or not date_match:
            logger.warning("Could not parse pair or date in Bybit announcement.")
            return None

        coin, quote = pair_match.group(1).upper(), pair_match.group(2).upper()
        formatted_symbol = f"{coin}-{quote}"

        date_str = f"{date_match.group(1)} {date_match.group(2)}"
        try:
            dt = datetime.strptime(date_str, "%B %d, %Y %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Invalid date format in Bybit announcement: {date_str}")
            return None

        return {"symbol": formatted_symbol, "date": dt}
