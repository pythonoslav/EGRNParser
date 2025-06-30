from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from .models import Organization


class SimpleOrganization(BaseModel):
    name: str = Field(..., description="Organization name")
    inn: Optional[str] = Field(None, description="INN (Tax ID)")
    ogrn: Optional[str] = Field(None, description="OGRN (Primary Registration Number)")
    okved: Optional[str] = Field(None, description="OKVED (Economic Activity Code)")
    status: Optional[str] = Field(None, description="Organization status")
    reg_date: Optional[str] = Field(None, description="Registration date in DD.MM.YYYY format")
    phone_number: Optional[str] = Field(None, description="Phone number")
    
    @classmethod
    def from_organization(cls, org: 'Organization') -> 'SimpleOrganization':
        reg_date = None
        if org.registration_date:
            reg_date = org.registration_date.strftime('%d.%m.%Y')
        
        return cls(
            name=org.name,
            inn=org.inn,
            ogrn=org.ogrn,
            okved=org.okved,
            status=org.status,
            reg_date=reg_date,
            phone_number=org.phone
        )
    
    def dict(self, **kwargs) -> Dict:
        return {
            'name': self.name,
            'inn': self.inn,
            'ogrn': self.ogrn,
            'okved': self.okved,
            'status': self.status,
            'reg_date': self.reg_date,
            'phone_number': self.phone_number
        }