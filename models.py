from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Organization(BaseModel):
    name: str = Field(..., description="Название организации")
    inn: Optional[str] = Field(None, description="ИНН")
    ogrn: Optional[str] = Field(None, description="ОГРН")
    kpp: Optional[str] = Field(None, description="КПП")
    okved: Optional[str] = Field(None, description="Основной ОКВЭД")
    okved_additional: List[str] = Field(default_factory=list, description="Дополнительные ОКВЭД")
    address: Optional[str] = Field(None, description="Юридический адрес")
    phone: Optional[str] = Field(None, description="Телефон")
    email: Optional[str] = Field(None, description="Email")
    director: Optional[str] = Field(None, description="Руководитель")
    registration_date: Optional[datetime] = Field(None, description="Дата регистрации")
    status: Optional[str] = Field(None, description="Статус организации")
    region: str = Field(default="Тюменская область", description="Регион")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SearchRequest(BaseModel):
    organization_names: List[str] = Field(..., description="Список названий организаций для поиска")
    okved_filter: Optional[List[str]] = Field(None, description="Фильтр по ОКВЭД")
    region: str = Field(default="Тюменская область", description="Регион поиска")


class SearchResult(BaseModel):
    query: str = Field(..., description="Поисковый запрос")
    found: bool = Field(..., description="Найдена ли организация")
    organization: Optional[Organization] = Field(None, description="Данные организации")
    error: Optional[str] = Field(None, description="Ошибка при поиске")