#!/usr/bin/env python3
import argparse
import json
from typing import List
from pathlib import Path

from models import SearchRequest
from search_engine import OrganizationSearchEngine
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Поиск юридических лиц в Тюменской области по названию и ОКВЭД'
    )
    
    parser.add_argument(
        'organizations',
        nargs='*',
        help='Названия организаций для поиска (через пробел)'
    )
    
    parser.add_argument(
        '-f', '--file',
        help='Файл со списком организаций (одна на строку)'
    )
    
    parser.add_argument(
        '-o', '--okved',
        nargs='*',
        help='Фильтр по ОКВЭД (можно указать несколько)'
    )
    
    parser.add_argument(
        '-r', '--region',
        default='Тюменская область',
        help='Регион поиска (по умолчанию: Тюменская область)'
    )
    
    parser.add_argument(
        '--export-excel',
        help='Экспортировать результаты в Excel файл'
    )
    
    parser.add_argument(
        '--export-json',
        help='Экспортировать результаты в JSON файл'
    )
    
    parser.add_argument(
        '--cache-dir',
        default='cache',
        help='Директория для кэша (по умолчанию: cache)'
    )
    
    args = parser.parse_args()
    
    # Собираем список организаций
    organizations = []
    
    if args.organizations:
        organizations.extend(args.organizations)
    
    if args.file:
        file_path = Path(args.file)
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                organizations.extend([line.strip() for line in f if line.strip()])
        else:
            logger.error(f"Файл {args.file} не найден")
            return
    
    if not organizations:
        logger.error("Не указаны организации для поиска")
        parser.print_help()
        return
    
    # Создаем запрос
    request = SearchRequest(
        organization_names=organizations,
        okved_filter=args.okved,
        region=args.region
    )
    
    # Создаем движок поиска
    engine = OrganizationSearchEngine(cache_dir=args.cache_dir)
    
    logger.info(f"Начинаем поиск {len(organizations)} организаций...")
    
    # Выполняем поиск
    results = engine.search_organizations(request)
    
    # Выводим результаты
    found_count = 0
    for result in results:
        print(f"\n{'='*60}")
        print(f"Поиск: {result.query}")
        
        if result.found and result.organization:
            found_count += 1
            org = result.organization
            print(f"✓ Найдено: {org.name}")
            print(f"  ИНН: {org.inn or 'не указан'}")
            print(f"  ОГРН: {org.ogrn or 'не указан'}")
            print(f"  КПП: {org.kpp or 'не указан'}")
            print(f"  ОКВЭД: {org.okved or 'не указан'}")
            print(f"  Адрес: {org.address or 'не указан'}")
            if org.phone:
                print(f"  Телефон: {org.phone}")
            if org.email:
                print(f"  Email: {org.email}")
            if org.director:
                print(f"  Руководитель: {org.director}")
            if org.status:
                print(f"  Статус: {org.status}")
        else:
            print(f"✗ Не найдено")
            if result.error:
                print(f"  Ошибка: {result.error}")
    
    print(f"\n{'='*60}")
    print(f"Итого найдено: {found_count} из {len(organizations)}")
    
    # Экспорт результатов
    if args.export_excel:
        engine.export_to_excel(results, args.export_excel)
    
    if args.export_json:
        engine.export_to_json(results, args.export_json)


if __name__ == '__main__':
    main()