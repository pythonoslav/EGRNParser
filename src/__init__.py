"""
EGRN Parser Library

A Python library for searching Russian organizations information.

Usage:
    from src.main import search_organizations
    
    results = search_organizations(['ООО "Компания"'], okved_filters=['86.23'])
"""

from .main import search_organizations

# Main entry point function
__all__ = ['search_organizations']

# Version info
__version__ = '1.0.0'
__author__ = 'EGRN Parser'