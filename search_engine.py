import asyncio
import aiohttp
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime
import os
from pathlib import Path

from models import Organization, SearchRequest, SearchResult
from scrapers import RusprofileScraper, ListOrgScraper, ZachemINNScraper
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrganizationSearchEngine:
    """Основной движок поиска организаций"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.scrapers = [
            RusprofileScraper(),
            ListOrgScraper(),
            ZachemINNScraper()
        ]
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def _get_cache_path(self, query: str) -> Path:
        """Получить путь к кэш-файлу для запроса"""
        safe_filename = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return self.cache_dir / f"{safe_filename}.json"
    
    def _load_from_cache(self, query: str) -> Optional[Organization]:
        """Загрузить данные из кэша"""
        cache_path = self._get_cache_path(query)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Проверяем актуальность кэша (7 дней)
                    cache_time = datetime.fromisoformat(data['cached_at'])
                    if (datetime.now() - cache_time).days < 7:
                        return Organization(**data['organization'])
            except Exception as e:
                logger.error(f"Ошибка чтения кэша для {query}: {str(e)}")
        return None
    
    def _save_to_cache(self, query: str, organization: Organization):
        """Сохранить данные в кэш"""
        cache_path = self._get_cache_path(query)
        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'query': query,
                'organization': organization.dict()
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения кэша для {query}: {str(e)}")
    
    def search_single_organization(self, name: str, region: str = "Тюменская область") -> Optional[Organization]:
        """Поиск одной организации"""
        # Проверяем кэш
        cached = self._load_from_cache(name)
        if cached:
            logger.info(f"Найдено в кэше: {name}")
            return cached
        
        # Ищем через скраперы
        for scraper in self.scrapers:
            try:
                logger.info(f"Поиск {name} через {scraper.__class__.__name__}")
                result = scraper.search_organization(name, region)
                if result:
                    # Сохраняем в кэш
                    self._save_to_cache(name, result)
                    return result
            except Exception as e:
                logger.error(f"Ошибка в {scraper.__class__.__name__}: {str(e)}")
                continue
        
        return None
    
    def filter_by_okved(self, organization: Organization, okved_filters: List[str]) -> bool:
        """Фильтрация по ОКВЭД"""
        if not okved_filters:
            return True
        
        if not organization.okved:
            return False
        
        # Проверяем основной ОКВЭД
        for okved_filter in okved_filters:
            if organization.okved.startswith(okved_filter):
                return True
            
            # Проверяем дополнительные ОКВЭД
            for add_okved in organization.okved_additional:
                if add_okved.startswith(okved_filter):
                    return True
        
        return False
    
    async def search_organizations_async(self, request: SearchRequest) -> List[SearchResult]:
        """Асинхронный поиск организаций"""
        results = []
        
        loop = asyncio.get_event_loop()
        
        # Создаем задачи для поиска
        tasks = []
        for org_name in request.organization_names:
            task = loop.run_in_executor(
                self.executor,
                self.search_single_organization,
                org_name,
                request.region
            )
            tasks.append((org_name, task))
        
        # Ждем результаты
        for org_name, task in tasks:
            try:
                organization = await task
                
                if organization:
                    # Применяем фильтр по ОКВЭД
                    if self.filter_by_okved(organization, request.okved_filter or []):
                        results.append(SearchResult(
                            query=org_name,
                            found=True,
                            organization=organization
                        ))
                    else:
                        results.append(SearchResult(
                            query=org_name,
                            found=False,
                            error="Организация найдена, но не соответствует фильтру ОКВЭД"
                        ))
                else:
                    results.append(SearchResult(
                        query=org_name,
                        found=False,
                        error="Организация не найдена"
                    ))
            except Exception as e:
                results.append(SearchResult(
                    query=org_name,
                    found=False,
                    error=f"Ошибка поиска: {str(e)}"
                ))
        
        return results
    
    def search_organizations(self, request: SearchRequest) -> List[SearchResult]:
        """Синхронный поиск организаций"""
        return asyncio.run(self.search_organizations_async(request))
    
    def export_to_excel(self, results: List[SearchResult], filename: str = "organizations.xlsx"):
        """Экспорт результатов в Excel"""
        import pandas as pd
        
        data = []
        for result in results:
            if result.found and result.organization:
                org = result.organization
                data.append({
                    'Поисковый запрос': result.query,
                    'Название': org.name,
                    'ИНН': org.inn,
                    'ОГРН': org.ogrn,
                    'КПП': org.kpp,
                    'ОКВЭД': org.okved,
                    'Адрес': org.address,
                    'Телефон': org.phone,
                    'Email': org.email,
                    'Руководитель': org.director,
                    'Статус': org.status,
                    'Дата регистрации': org.registration_date.strftime('%d.%m.%Y') if org.registration_date else None
                })
            else:
                data.append({
                    'Поисковый запрос': result.query,
                    'Название': 'Не найдено',
                    'Ошибка': result.error
                })
        
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine='openpyxl')
        logger.info(f"Результаты экспортированы в {filename}")
    
    def export_to_json(self, results: List[SearchResult], filename: str = "organizations.json"):
        """Экспорт результатов в JSON"""
        data = [result.dict() for result in results]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Результаты экспортированы в {filename}")