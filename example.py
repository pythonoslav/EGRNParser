from src.main import search_organizations

# С оквэдами
results = search_organizations(
    organization_names=['ООО "Доктор Зуб"'],
    okved_filters=['86.23', '86.22', '86.21', '86.90', '32.50', '47.74.1', '47.74.2']
)

# Display results
for result in results:
    print(f"\nOrganization: {result['name']}")
    print(f"  INN: {result['inn']}")
    print(f"  OGRN: {result['ogrn']}")
    print(f"  OKVED: {result['okved']}")
    print(f"  Status: {result['status']}")
    print(f"  Registration Date: {result['reg_date']}")
    print(f"  Phone: {result['phone_number']}")
