from interfaces import ExchangeInterface
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class OKXExchange(ExchangeInterface):
    ANNOUNCEMENTS_URL = "https://www.okx.com/en-us/help/section/announcements-new-listings"
    MAX_RETRIES = 3

    def get_upcoming_listings(self):
        logger.info("Fetching upcoming listings from OKX...")
        listings = self._scrape_announcements()

        upcoming = []
        for item in listings:
            title = item["title"].lower()
            if "will list" in title or "new listing" in title:
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
                resp = requests.get(self.ANNOUNCEMENTS_URL, timeout=10)
                resp.raise_for_status()
                break
            except requests.exceptions.ReadTimeout:
                logger.warning(f"OKX timeout, retry {attempt}/{self.MAX_RETRIES}")
            except Exception as e:
                logger.error(f"OKX fetch error: {e}")
                return []
        else:
            logger.error("OKX announcements unavailable after retries")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        announcements = []
        for a in soup.select(".announcement-list-item a"):
            title = a.get_text(strip=True)
            href = a.get("href")
            if href:
                url = href if href.startswith("http") else f"https://www.okx.com{href}"
                announcements.append({"title": title, "url": url})
        logger.info(f"Found {len(announcements)} total OKX announcements")
        return announcements

    def _fetch_announcement_content(self, url):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch OKX announcement content from {url}: {e}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        return soup.get_text(separator="\n")

    def _parse_listing_details(self, content):
        match = re.search(r"will list (\w+)/(\w+) at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC", content, re.IGNORECASE)
        if not match:
            logger.warning("Could not parse listing details in OKX announcement.")
            return None

        coin, quote, date_str = match.group(1).upper(), match.group(2).upper(), match.group(3)
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Invalid date format in OKX announcement: {date_str}")
            return None

        return {"symbol": f"{coin}-{quote}", "date": dt}
