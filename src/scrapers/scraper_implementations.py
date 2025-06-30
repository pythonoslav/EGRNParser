import requests
from bs4 import BeautifulSoup
import time
from typing import Optional, Dict
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential
import re
from datetime import datetime
import logging

from ..interfaces import OrganizationScraper, OrganizationDataTransformer
from ..models import Organization

logger = logging.getLogger(__name__)


class BaseHttpScraper(OrganizationScraper):
    
    def __init__(self):
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
    def _make_request(self, url: str, params: Optional[Dict] = None) -> requests.Response:
        response = self.session.get(
            url,
            params=params,
            headers=self._get_headers(),
            timeout=10
        )
        response.raise_for_status()
        return response


class RusprofileDataTransformer(OrganizationDataTransformer):
    
    def transform(self, soup: BeautifulSoup) -> Optional[Organization]:
        try:
            org_data = {}
            
            # Extract organization name
            title = soup.find('h1', class_='company-name')
            if title:
                org_data['name'] = title.text.strip()
            
            # Extract requisites (INN, OGRN, KPP)
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
            
            # Extract OKVED
            okved_section = soup.find('span', {'id': 'okved2_main'})
            if okved_section:
                okved_code = okved_section.find('span', class_='okved-code')
                if okved_code:
                    org_data['okved'] = okved_code.text.strip()
            
            # Extract address
            address_elem = soup.find('address')
            if address_elem:
                org_data['address'] = address_elem.text.strip()
            
            # Extract director
            director_section = soup.find('div', class_='company-row', text=re.compile('Руководитель'))
            if director_section:
                director_link = director_section.find_next('a')
                if director_link:
                    org_data['director'] = director_link.text.strip()
            
            # Extract status
            status_elem = soup.find('div', class_='company-status')
            if status_elem:
                org_data['status'] = status_elem.text.strip()
            
            return Organization(**org_data) if org_data else None
            
        except Exception as e:
            logger.error(f"Error transforming Rusprofile data: {str(e)}")
            return None


class RusprofileScraperImpl(BaseHttpScraper):
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.rusprofile.ru"
        self.search_url = f"{self.base_url}/search"
        self.transformer = RusprofileDataTransformer()
    
    def get_scraper_name(self) -> str:
        return "RusprofileScraper"
    
    def search_organization(self, name: str, region: str = "Тюменская область") -> Optional[Organization]:
        try:
            params = {
                'query': name,
                'type': 'ul',  # Search for legal entities
                'region': '72'  # Tyumen region code
            }
            
            response = self._make_request(self.search_url, params)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find search results
            search_results = soup.find_all('div', class_='company-item')
            
            for result in search_results:
                # Check region
                if region.lower() not in result.text.lower():
                    continue
                
                # Try to parse directly from search results
                org = self._parse_search_result(result)
                if org:
                    return org
                
                # Fallback to company page
                link = result.find('a')
                if link and link.get('href'):
                    company_url = self.base_url + link.get('href', '')
                    return self._parse_company_page(company_url)
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching {name} on Rusprofile: {str(e)}")
            return None
    
    def _parse_company_page(self, url: str) -> Optional[Organization]:
        try:
            time.sleep(1)  # Rate limiting
            response = self._make_request(url)
            soup = BeautifulSoup(response.text, 'lxml')
            return self.transformer.transform(soup)
        except Exception as e:
            logger.error(f"Error parsing company page {url}: {str(e)}")
            return None
    
    def _parse_search_result(self, company_item) -> Optional[Organization]:
        try:
            org_data = {}
            
            # Extract name
            title_elem = company_item.find('div', class_='company-item__title')
            if title_elem and title_elem.find('a'):
                org_data['name'] = title_elem.get_text(strip=True)
            
            # Extract INN, OGRN, registration date
            info_sections = company_item.find_all('div', class_='company-item-info')
            for section in info_sections:
                dls = section.find_all('dl')
                for dl in dls:
                    dt = dl.find('dt')
                    dd = dl.find('dd')
                    if dt and dd:
                        label = dt.text.strip()
                        value = dd.text.strip()
                        
                        if label == 'ИНН':
                            org_data['inn'] = value
                        elif label == 'ОГРН':
                            org_data['ogrn'] = value
                        elif label == 'Дата регистрации':
                            # Convert to datetime
                            try:
                                from datetime import datetime
                                # Parse Russian date format
                                months = {
                                    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
                                    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                                    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
                                }
                                parts = value.split()
                                if len(parts) >= 3:
                                    day = int(parts[0])
                                    month = months.get(parts[1], 1)
                                    year = int(parts[2].rstrip('г.'))
                                    org_data['registration_date'] = datetime(year, month, day)
                            except:
                                pass
                        elif label == 'Основной вид деятельности':
                            # Extract OKVED code
                            if ' ' in value:
                                org_data['okved'] = value.split()[0]
                            else:
                                org_data['okved'] = value
                        elif label == 'Директор' or label == 'Генеральный директор':
                            org_data['director'] = value
                        elif label == 'Уставный капитал':
                            org_data['capital'] = value
            
            # Extract address
            address_elem = company_item.find('address', class_='company-item__text')
            if address_elem:
                org_data['address'] = address_elem.text.strip()
            
            # Set status as active (since we filter for active companies)
            org_data['status'] = 'Действующая'
            
            return Organization(**org_data) if org_data else None
            
        except Exception as e:
            logger.error(f"Error parsing search result: {str(e)}")
            return None


class ListOrgDataTransformer(OrganizationDataTransformer):
    
    def transform(self, soup: BeautifulSoup) -> Optional[Organization]:
        try:
            org_data = {}
            
            # Extract title
            title = soup.find('h1')
            if title:
                org_data['name'] = title.text.strip()
            
            # Extract data from table
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
            logger.error(f"Error transforming List-org data: {str(e)}")
            return None


class ListOrgScraperImpl(BaseHttpScraper):
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.list-org.com"
        self.transformer = ListOrgDataTransformer()
    
    def get_scraper_name(self) -> str:
        return "ListOrgScraper"
    
    def search_organization(self, name: str, region: str = "Тюменская область") -> Optional[Organization]:
        try:
            search_url = f"{self.base_url}/search"
            params = {
                'val': name,
                'type': 'all'
            }
            
            response = self._make_request(search_url, params)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find results
            results = soup.find_all('p', class_='org_list')
            
            for result in results:
                # Check region
                if region.lower() not in result.text.lower():
                    continue
                
                link = result.find('a')
                if link:
                    company_url = self.base_url + link.get('href', '')
                    return self._parse_company_page(company_url)
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching {name} on List-org: {str(e)}")
            return None
    
    def _parse_company_page(self, url: str) -> Optional[Organization]:
        try:
            time.sleep(1)  # Rate limiting
            response = self._make_request(url)
            soup = BeautifulSoup(response.text, 'lxml')
            return self.transformer.transform(soup)
        except Exception as e:
            logger.error(f"Error parsing company page {url}: {str(e)}")
            return None


class ZachemINNDataTransformer(OrganizationDataTransformer):
    
    def transform(self, data: Dict) -> Optional[Organization]:
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
            
            # Parse registration date
            if 'registration_date' in data:
                try:
                    org_data['registration_date'] = datetime.fromisoformat(data['registration_date'])
                except:
                    pass
            
            return Organization(**org_data)
            
        except Exception as e:
            logger.error(f"Error transforming ZachemINN data: {str(e)}")
            return None


class ZachemINNScraperImpl(BaseHttpScraper):
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://zachestnyibiznes.ru"
        self.transformer = ZachemINNDataTransformer()
    
    def get_scraper_name(self) -> str:
        return "ZachemINNScraper"
    
    def _get_headers(self) -> Dict[str, str]:
        headers = super()._get_headers()
        headers.update({
            'Accept': 'application/json, text/plain, */*',
            'X-Requested-With': 'XMLHttpRequest'
        })
        return headers
    
    def search_organization(self, name: str, region: str = "Тюменская область") -> Optional[Organization]:
        try:
            search_url = f"{self.base_url}/search"
            params = {
                'query': name,
                'page': 1
            }
            
            response = self._make_request(search_url, params)
            data = response.json() if response.text else {}
            
            if 'data' in data and isinstance(data['data'], list):
                for item in data['data']:
                    # Check region
                    if 'address' in item and region.lower() in item.get('address', '').lower():
                        return self.transformer.transform(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching {name} on ZachemINN: {str(e)}")
            return None