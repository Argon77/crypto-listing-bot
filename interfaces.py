from abc import ABC, abstractmethod
from typing import List, Dict

class ExchangeInterface(ABC):
    @abstractmethod
    def get_upcoming_listings(self) -> List[Dict]:
        """Return upcoming listings from the exchange."""
        pass

    @abstractmethod
    def get_past_listings(self) -> List[Dict]:
        """Return past listings from the exchange."""
        pass
