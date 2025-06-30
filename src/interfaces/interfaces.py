from abc import ABC, abstractmethod
from typing import Optional, Dict, Protocol
from ..models import Organization


class HttpClient(Protocol):
    def get(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None, timeout: int = 10) -> any:
        ...


class HtmlParser(Protocol):
    def parse(self, html: str) -> any:
        ...


class OrganizationScraper(ABC):
    
    @abstractmethod
    def search_organization(self, name: str, region: str = "Тюменская область") -> Optional[Organization]:
        pass
    
    @abstractmethod
    def get_scraper_name(self) -> str:
        pass


class OrganizationDataTransformer(ABC):
    
    @abstractmethod
    def transform(self, raw_data: Dict) -> Optional[Organization]:
        pass


class CacheStrategy(ABC):
    
    @abstractmethod
    def get(self, key: str) -> Optional[Organization]:
        pass
    
    @abstractmethod
    def set(self, key: str, organization: Organization) -> None:
        pass
    
    @abstractmethod
    def is_valid(self, key: str) -> bool:
        pass