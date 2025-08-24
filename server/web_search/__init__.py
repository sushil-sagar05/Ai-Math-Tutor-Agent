# Web search package initialization
"""
Web search module for mathematical problem solving
Provides multi-provider search capabilities
"""

from .search_providers import (
    SearchProvider,
    DuckDuckGoProvider,
    WikipediaProvider,
    MathStackExchangeProvider
)
from .mcp_client import MCPClient

__all__ = [
    'SearchProvider',
    'DuckDuckGoProvider', 
    'WikipediaProvider',
    'MathStackExchangeProvider',
    'MCPClient'
]
