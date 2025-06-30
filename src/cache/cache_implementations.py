import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

from ..interfaces import CacheStrategy
from ..models import Organization

logger = logging.getLogger(__name__)


class FileCacheStrategy(CacheStrategy):
    """File-based cache implementation"""
    
    def __init__(self, cache_dir: str = "cache", cache_days: int = 7):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_days = cache_days
    
    def _get_cache_path(self, key: str) -> Path:
        """Generate safe cache file path from key"""
        safe_filename = "".join(c for c in key if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return self.cache_dir / f"{safe_filename}.json"
    
    def get(self, key: str) -> Optional[Organization]:
        """Retrieve organization from cache if valid"""
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check cache validity
            cache_time = datetime.fromisoformat(data['cached_at'])
            if (datetime.now() - cache_time).days >= self.cache_days:
                return None
            
            return Organization(**data['organization'])
        except Exception as e:
            logger.error(f"Error reading cache for {key}: {str(e)}")
            return None
    
    def set(self, key: str, organization: Organization) -> None:
        """Store organization in cache"""
        cache_path = self._get_cache_path(key)
        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'query': key,
                'organization': json.loads(organization.json())  # Use Pydantic's JSON serialization
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache for {key}: {str(e)}")
    
    def is_valid(self, key: str) -> bool:
        """Check if cache entry exists and is still valid"""
        return self.get(key) is not None


class NoCacheStrategy(CacheStrategy):
    """No-op cache implementation for when caching is disabled"""
    
    def get(self, key: str) -> Optional[Organization]:
        return None
    
    def set(self, key: str, organization: Organization) -> None:
        pass
    
    def is_valid(self, key: str) -> bool:
        return False