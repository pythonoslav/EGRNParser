#!/usr/bin/env python3
"""
Пример использования библиотеки поиска организаций
"""

from models import SearchRequest
from search_engine import OrganizationSearchEngine


def example_simple_search():
    """Простой поиск одной организации"""
    print("=== Простой поиск ===")
    
    engine = OrganizationSearchEngine()
    
    # Поиск одной организации
    result = engine.search_single_organization("Газпром нефть")
    
    if result:
        print(f"Найдено: {result.name}")
        print(f"ИНН: {result.inn}")
        print(f"ОГРН: {result.ogrn}")
        print(f"Адрес: {result.address}")
    else:
        print("Организация не найдена")


def example_batch_search():
    """Пакетный поиск нескольких организаций"""
    print("\n=== Пакетный поиск ===")
    
    engine = OrganizationSearchEngine()
    
    # Список организаций для поиска
    organizations = [
        "Сибур",
        "Тюменьэнерго",
        "Тюменский нефтяной научный центр"
    ]
    
    # Создаем запрос
    request = SearchRequest(
        organization_names=organizations,
        region="Тюменская область"
    )
    
    # Выполняем поиск
    results = engine.search_organizations(request)
    
    # Выводим результаты
    for result in results:
        if result.found and result.organization:
            org = result.organization
            print(f"\n{result.query}: ✓ Найдено")
            print(f"  Название: {org.name}")
            print(f"  ИНН: {org.inn}")
            print(f"  ОКВЭД: {org.okved}")
        else:
            print(f"\n{result.query}: ✗ Не найдено")


def example_search_with_okved_filter():
    """Поиск с фильтрацией по ОКВЭД"""
    print("\n=== Поиск с фильтром ОКВЭД ===")
    
    engine = OrganizationSearchEngine()
    
    # Поиск строительных компаний (ОКВЭД 41-43)
    organizations = [
        "СибирьСтрой",
        "ТюменьДорСтрой",
        "Газпром",
        "Строительная компания Тюмень"
    ]
    
    request = SearchRequest(
        organization_names=organizations,
        okved_filter=["41", "42", "43"],  # Строительство
        region="Тюменская область"
    )
    
    results = engine.search_organizations(request)
    
    print("Фильтр: только строительные компании (ОКВЭД 41-43)")
    for result in results:
        if result.found and result.organization:
            org = result.organization
            print(f"\n✓ {org.name}")
            print(f"  ОКВЭД: {org.okved}")
        else:
            print(f"\n✗ {result.query}: {result.error}")


def example_export_results():
    """Экспорт результатов в файлы"""
    print("\n=== Экспорт результатов ===")
    
    engine = OrganizationSearchEngine()
    
    organizations = [
        "Роснефть",
        "Лукойл Западная Сибирь",
        "Новатэк"
    ]
    
    request = SearchRequest(
        organization_names=organizations,
        region="Тюменская область"
    )
    
    results = engine.search_organizations(request)
    
    # Экспорт в Excel
    engine.export_to_excel(results, "oil_companies.xlsx")
    print("Результаты экспортированы в oil_companies.xlsx")
    
    # Экспорт в JSON
    engine.export_to_json(results, "oil_companies.json")
    print("Результаты экспортированы в oil_companies.json")


def example_programmatic_usage():
    """Программное использование результатов"""
    print("\n=== Программное использование ===")
    
    engine = OrganizationSearchEngine()
    
    # Поиск организации
    org = engine.search_single_organization("Тюменский государственный университет")
    
    if org:
        # Используем данные в программе
        data = {
            "name": org.name,
            "inn": org.inn,
            "contacts": {
                "address": org.address,
                "phone": org.phone,
                "email": org.email
            },
            "legal": {
                "ogrn": org.ogrn,
                "kpp": org.kpp,
                "okved": org.okved
            }
        }
        
        print(f"Данные для API:")
        import json
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    # Запускаем примеры
    example_simple_search()
    example_batch_search()
    example_search_with_okved_filter()
    example_export_results()
    example_programmatic_usage()