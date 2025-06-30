import requests
from bs4 import BeautifulSoup
import json
import time
from typing import Optional, Dict, List
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential
from models import Organization
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RusprofileScraper:
    """Скрапер для получения данных с rusprofile.ru"""
    
    def __init__(self):
        self.base_url = "https://www.rusprofile.ru"
        self.search_url = f"{self.base_url}/search"
        self.ua = UserAgent()
        self.session = requests.Session()
        
    def _get_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_organization(self, name: str, region: str = "Тюменская область") -> Optional[Organization]:
        """Поиск организации по названию"""
        try:
            params = {
                'query': name,
                'type': '0',
                'region': '72'  # Код Тюменской области
            }
            
            response = self.session.get(
                self.search_url,
                params=params,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Ищем первый результат
            search_results = soup.find_all('div', class_='company-item')
            
            for result in search_results:
                # Проверяем регион
                if region.lower() not in result.text.lower():
                    continue
                    
                # Получаем ссылку на компанию
                link = result.find('a', class_='company-item__title')
                if link:
                    company_url = self.base_url + link.get('href', '')
                    return self._parse_company_page(company_url)
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при поиске {name}: {str(e)}")
            return None
    
    def _parse_company_page(self, url: str) -> Optional[Organization]:
        """Парсинг страницы компании"""
        try:
            time.sleep(1)  # Задержка между запросами
            
            response = self.session.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            org_data = {}
            
            # Название
            title = soup.find('h1', class_='company-name')
            if title:
                org_data['name'] = title.text.strip()
            
            # ИНН, ОГРН, КПП
            requisites = soup.find('div', id='requisites')
            if requisites:
                inn = requisites.find('span', {'id': 'clip_inn'})
                if inn:
                    org_data['inn'] = inn.text.strip()
                
                ogrn = requisites.find('span', {'id': 'clip_ogrn'})
                if ogrn:
                    org_data['ogrn'] = ogrn.text.strip()
                
                kpp_elem = requisites.find(text=re.compile('КПП'))
                if kpp_elem:
                    kpp_value = kpp_elem.find_next('span')
                    if kpp_value:
                        org_data['kpp'] = kpp_value.text.strip()
            
            # ОКВЭД
            okved_section = soup.find('span', {'id': 'okved2_main'})
            if okved_section:
                okved_code = okved_section.find('span', class_='okved-code')
                if okved_code:
                    org_data['okved'] = okved_code.text.strip()
            
            # Адрес
            address_elem = soup.find('address')
            if address_elem:
                org_data['address'] = address_elem.text.strip()
            
            # Руководитель
            director_section = soup.find('div', class_='company-row', text=re.compile('Руководитель'))
            if director_section:
                director_link = director_section.find_next('a')
                if director_link:
                    org_data['director'] = director_link.text.strip()
            
            # Статус
            status_elem = soup.find('div', class_='company-status')
            if status_elem:
                org_data['status'] = status_elem.text.strip()
            
            return Organization(**org_data)
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы компании {url}: {str(e)}")
            return None


class ListOrgScraper:
    """Скрапер для list-org.com"""
    
    def __init__(self):
        self.base_url = "https://www.list-org.com"
        self.ua = UserAgent()
        self.session = requests.Session()
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_organization(self, name: str, region: str = "Тюменская область") -> Optional[Organization]:
        """Поиск организации по названию"""
        try:
            search_url = f"{self.base_url}/search"
            params = {
                'val': name,
                'type': 'all'
            }
            
            response = self.session.get(
                search_url,
                params=params,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Ищем результаты
            results = soup.find_all('p', class_='org_list')
            
            for result in results:
                # Проверяем регион
                if region.lower() not in result.text.lower():
                    continue
                
                link = result.find('a')
                if link:
                    company_url = self.base_url + link.get('href', '')
                    return self._parse_company_page(company_url)
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при поиске в list-org {name}: {str(e)}")
            return None
    
    def _parse_company_page(self, url: str) -> Optional[Organization]:
        """Парсинг страницы компании"""
        try:
            time.sleep(1)
            
            response = self.session.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            org_data = {}
            
            # Название
            title = soup.find('h1')
            if title:
                org_data['name'] = title.text.strip()
            
            # Таблица с данными
            info_table = soup.find('table', class_='table')
            if info_table:
                rows = info_table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        label = cells[0].text.strip().lower()
                        value = cells[1].text.strip()
                        
                        if 'инн' in label:
                            org_data['inn'] = value
                        elif 'огрн' in label:
                            org_data['ogrn'] = value
                        elif 'кпп' in label:
                            org_data['kpp'] = value
                        elif 'адрес' in label:
                            org_data['address'] = value
                        elif 'телефон' in label:
                            org_data['phone'] = value
                        elif 'оквэд' in label and 'okved' not in org_data:
                            org_data['okved'] = value.split()[0] if value else None
            
            return Organization(**org_data) if org_data else None
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге list-org страницы {url}: {str(e)}")
            return None


class ZachemINNScraper:
    """Скрапер для zachestnyibiznes.ru"""
    
    def __init__(self):
        self.base_url = "https://zachestnyibiznes.ru"
        self.ua = UserAgent()
        self.session = requests.Session()
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': self.ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'X-Requested-With': 'XMLHttpRequest'
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_organization(self, name: str, region: str = "Тюменская область") -> Optional[Organization]:
        """Поиск организации по названию"""
        try:
            search_url = f"{self.base_url}/search"
            params = {
                'query': name,
                'page': 1
            }
            
            response = self.session.get(
                search_url,
                params=params,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json() if response.text else {}
            
            if 'data' in data and isinstance(data['data'], list):
                for item in data['data']:
                    # Проверяем регион
                    if 'address' in item and region.lower() in item.get('address', '').lower():
                        return self._parse_company_data(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при поиске в zachestnyibiznes {name}: {str(e)}")
            return None
    
    def _parse_company_data(self, data: Dict) -> Optional[Organization]:
        """Парсинг данных компании из JSON"""
        try:
            org_data = {
                'name': data.get('name', ''),
                'inn': data.get('inn', ''),
                'ogrn': data.get('ogrn', ''),
                'kpp': data.get('kpp', ''),
                'address': data.get('address', ''),
                'status': data.get('status', ''),
                'okved': data.get('okved_code', ''),
                'director': data.get('director', '')
            }
            
            # Дата регистрации
            if 'registration_date' in data:
                try:
                    org_data['registration_date'] = datetime.fromisoformat(data['registration_date'])
                except:
                    pass
            
            return Organization(**org_data)
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге данных zachestnyibiznes: {str(e)}")
            return None