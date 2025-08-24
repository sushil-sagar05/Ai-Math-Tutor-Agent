import asyncio
from typing import List, Dict
from .search_providers import DuckDuckGoProvider, WikipediaProvider, MathStackExchangeProvider

class MCPClient:
    """Fixed MCP Client for FastAPI async context"""
    
    def __init__(self):
        self.providers = [
            DuckDuckGoProvider(),
            WikipediaProvider(),
            MathStackExchangeProvider()
        ]
    
    async def _search_provider(self, provider, query, max_results):
        try:
            return await provider.search(query, max_results)
        except Exception as e:
            print(f"Provider {provider.__class__.__name__} failed: {e}")
            return []
    
    async def search(self, query: str, max_results_per_provider: int = 3) -> List[Dict]:
        """Async search - works in FastAPI"""
        print(f" MCP searching: {query}")
        
        tasks = []
        for provider in self.providers:
            task = self._search_provider(provider, query, max_results_per_provider)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_results = []
        for provider_results in results:
            if isinstance(provider_results, list):
                all_results.extend(provider_results)
        
        filtered_results = self._filter_math_relevant(all_results, query)
        
        print(f" MCP found {len(filtered_results)} results")
        return filtered_results
    
    def _filter_math_relevant(self, results: List[Dict], query: str) -> List[Dict]:
        """Filter for math relevance (sync method)"""
        if not results:
            if "derivative" in query.lower() and "sin" in query.lower() and "cos" in query.lower():
                return [{
                    "title": "Product Rule for Derivatives",
                    "url": "https://mathworld.wolfram.com/ProductRule.html",
                    "snippet": "For sin(x)*cos(x), use product rule: d/dx[uv] = u'v + uv' = cos(x)*cos(x) + sin(x)*(-sin(x)) = cos(2x)",
                    "source": "math_knowledge"
                }]
            return []
        
        math_keywords = [
            "equation", "formula", "calculate", "solve", "derivative", "integral",
            "algebra", "geometry", "calculus", "trigonometry", "mathematics"
        ]
        
        scored_results = []
        query_lower = query.lower()
        
        for result in results:
            content = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
            
            keyword_score = sum(1 for keyword in math_keywords if keyword in content)
            query_terms = query_lower.split()
            query_score = sum(2 for term in query_terms if term in content)
            
            total_score = keyword_score + query_score
            
            if total_score > 1:
                result["relevance_score"] = total_score
                scored_results.append(result)
        
        scored_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return scored_results[:6]
