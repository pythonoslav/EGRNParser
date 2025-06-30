import asyncio
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

from ..interfaces import OrganizationScraper, CacheStrategy
from ..scrapers import (
    RusprofileScraperImpl,
    ListOrgScraperImpl,
    ZachemINNScraperImpl
)
from ..cache import FileCacheStrategy, NoCacheStrategy
from ..models import Organization, SimpleOrganization

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrganizationSearchService:
    """Service for searching organizations following SOLID principles"""
    
    def __init__(
        self,
        scrapers: Optional[List[OrganizationScraper]] = None,
        cache_strategy: Optional[CacheStrategy] = None,
        max_workers: int = 3,
        okved_filters: Optional[List[str]] = None
    ):
        self.scrapers = scrapers or [
            RusprofileScraperImpl(),
            ListOrgScraperImpl(),
            ZachemINNScraperImpl()
        ]
        self.cache = cache_strategy or FileCacheStrategy()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.okved_filters = okved_filters
    
    def _matches_okved_filter(self, organization: Organization) -> bool:
        """Check if organization matches OKVED filters"""
        if not self.okved_filters:
            return True
        
        if not organization.okved:
            return False
        
        # Check main OKVED
        for okved_filter in self.okved_filters:
            if organization.okved.startswith(okved_filter):
                return True
        
        # Check additional OKVEDs if available
        if hasattr(organization, 'okved_additional'):
            for add_okved in organization.okved_additional:
                for okved_filter in self.okved_filters:
                    if add_okved.startswith(okved_filter):
                        return True
        
        return False
    
    def search_single(self, name: str, region: str = "Тюменская область") -> Optional[Organization]:
        """Search for a single organization"""
        # Check cache first
        cached = self.cache.get(name)
        if cached:
            logger.info(f"Found in cache: {name}")
            # Apply OKVED filter even for cached results
            if self._matches_okved_filter(cached):
                return cached
            else:
                logger.info(f"Cached result for {name} doesn't match OKVED filter")
                return None
        
        # Try each scraper
        for scraper in self.scrapers:
            try:
                logger.info(f"Searching {name} using {scraper.get_scraper_name()}")
                result = scraper.search_organization(name, region)
                if result:
                    # Apply OKVED filter
                    if self._matches_okved_filter(result):
                        # Save to cache
                        self.cache.set(name, result)
                        return result
                    else:
                        logger.info(f"Found {name} but doesn't match OKVED filter")
            except Exception as e:
                logger.error(f"Error in {scraper.get_scraper_name()}: {str(e)}")
                continue
        
        return None
    
    async def search_multiple_async(self, names: List[str], region: str = "Тюменская область") -> List[Optional[Organization]]:
        """Search for multiple organizations asynchronously"""
        loop = asyncio.get_event_loop()
        
        # Create tasks for parallel search
        tasks = [
            loop.run_in_executor(self.executor, self.search_single, name, region)
            for name in names
        ]
        
        # Wait for all results
        results = await asyncio.gather(*tasks)
        return results
    
    def search_multiple(self, names: List[str], region: str = "Тюменская область") -> List[Optional[Organization]]:
        """Search for multiple organizations synchronously"""
        return asyncio.run(self.search_multiple_async(names, region))


def search_organizations(
    organization_names: List[str],
    okved_filters: Optional[List[str]] = None,
    use_cache: bool = True,
    region: str = "Тюменская область"
) -> List[Dict]:
    
    # Initialize service with appropriate cache strategy and OKVED filters
    cache_strategy = FileCacheStrategy() if use_cache else NoCacheStrategy()
    service = OrganizationSearchService(
        cache_strategy=cache_strategy,
        okved_filters=okved_filters
    )
    
    # Search for organizations
    organizations = service.search_multiple(organization_names, region)
    
    # Convert to simplified format
    results = []
    for name, org in zip(organization_names, organizations):
        if org:
            # Convert to simplified model and then to dict
            simple_org = SimpleOrganization.from_organization(org)
            results.append(simple_org.dict())
        else:
            # Return empty result with just the name
            results.append({
                'name': name,
                'inn': None,
                'ogrn': None,
                'okved': None,
                'status': None,
                'reg_date': None,
                'phone_number': None
            })
    
    return results


# Convenience function for single organization search
def search_organization(name: str, use_cache: bool = True, region: str = "Тюменская область") -> Dict:
    results = search_organizations([name], use_cache, region)
    return results[0] if results else None