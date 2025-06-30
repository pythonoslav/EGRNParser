from src.main import search_organizations

# С оквэдами
results = search_organizations(
    organization_names=['ООО "Доктор Зуб"'],
    okved_filters=['86.23', '86.22', '86.21', '86.90', '32.50', '47.74.1', '47.74.2']
)

# Display results
for result in results:
    print(f"\nQuery: {result['query']}")
    org = result['organization']
    if org['inn']:
        print(f"Organization: {org['name']}")
        print(f"  INN: {org['inn']}")
        print(f"  OGRN: {org['ogrn']}")
        print(f"  KPP: {org['kpp']}")
        print(f"  OKVED: {org['okved']}")
        print(f"  OKVED Additional: {org['okved_additional']}")
        print(f"  Address: {org['address']}")
        print(f"  Phone: {org['phone']}")
        print(f"  Email: {org['email']}")
        print(f"  Director: {org['director']}")
        print(f"  Registration Date: {org['registration_date']}")
        print(f"  Status: {org['status']}")
        print(f"  Region: {org['region']}")
    else:
        print("  Organization not found")
