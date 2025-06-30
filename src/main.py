from typing import List, Dict, Optional
from .core import search_organizations as _search_organizations


def search_organizations(
    organization_names: List[str],
    okved_filters: Optional[List[str]] = None,
    use_cache: bool = True,
    region: str = "Тюменская область"
) -> List[Dict]:
   
    return _search_organizations(
        organization_names=organization_names,
        okved_filters=okved_filters,
        use_cache=use_cache,
        region=region
    )