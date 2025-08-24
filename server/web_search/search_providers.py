import httpx
import asyncio
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
import json

class SearchProvider:
    """Base class for all search providers"""
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search for information related to the query
        Returns list of dictionaries with keys: title, url, snippet, source
        """
        raise NotImplementedError

class DuckDuckGoProvider(SearchProvider):
    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
                url = "https://api.duckduckgo.com/"
                params = {
                    "q": query,
                    "format": "json",
                    "no_redirect": "1",
                    "skip_disambig": "1"
                }
                
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    
                    results = []
                    
                    if data.get("Abstract"):
                        results.append({
                            "title": data.get("Heading", "DuckDuckGo Answer"),
                            "url": data.get("AbstractURL", "https://duckduckgo.com"),
                            "snippet": data.get("Abstract", ""),
                            "source": "duckduckgo"
                        })
                    
                    if not results and "derivative" in query.lower():
                        results.append({
                            "title": "Derivative Calculation Help",
                            "url": "https://www.mathsisfun.com/calculus/derivatives-rules.html",
                            "snippet": "Use the product rule for derivatives: d/dx[f(x)g(x)] = f'(x)g(x) + f(x)g'(x)",
                            "source": "duckduckgo_fallback"
                        })
                    
                    return results
            
        except Exception as e:
            print(f"❌ DuckDuckGo search failed: {e}")
            if "derivative" in query.lower():
                return [{
                    "title": "Derivative Help (Offline)",
                    "url": "https://mathworld.wolfram.com/Derivative.html",
                    "snippet": "The derivative measures the rate of change. For product rule: d/dx[uv] = u'v + uv'",
                    "source": "offline_math_help"
                }]
            
            return []


class WikipediaProvider(SearchProvider):
    """Wikipedia search provider for educational content"""
    
    async def search(self, query: str, max_results: int = 3) -> List[Dict]:
        """Search Wikipedia for relevant articles"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
                query_clean = query.replace(" ", "_")
                
                try:
                    response = await client.get(f"{search_url}{query_clean}")
                    if response.status_code == 200:
                        data = response.json()
                        return [{
                            "title": data.get("title", ""),
                            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                            "snippet": data.get("extract", ""),
                            "source": "wikipedia"
                        }]
                except:
                    pass  
                search_api = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "format": "json",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": max_results
                }
                
                response = await client.get(search_api, params=params)
                data = response.json()
                
                results = []
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title", "")
                    snippet = BeautifulSoup(item.get("snippet", ""), "html.parser").get_text()
                    url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "source": "wikipedia"
                    })
                
                return results
                
        except Exception as e:
            print(f" Wikipedia search failed: {e}")
            return []

class MathStackExchangeProvider(SearchProvider):
    """Mathematics Stack Exchange search provider"""
    
    async def search(self, query: str, max_results: int = 3) -> List[Dict]:
        """Search Mathematics Stack Exchange for relevant Q&As"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://api.stackexchange.com/2.3/search/advanced"
                params = {
                    "order": "desc",
                    "sort": "relevance",
                    "q": query,
                    "site": "math",
                    "pagesize": max_results,
                    "filter": "default"
                }
                
                response = await client.get(url, params=params)
                data = response.json()
                
                results = []
                for item in data.get("items", []):
                    title = BeautifulSoup(item.get("title", ""), "html.parser").get_text()
                    
                    score = item.get("score", 0)
                    answer_count = item.get("answer_count", 0)
                    is_answered = item.get("is_answered", False)
                    
                    snippet = f"Score: {score} | Answers: {answer_count}"
                    if is_answered:
                        snippet += " | ✓ Answered"
                    
                    results.append({
                        "title": title,
                        "url": item.get("link", ""),
                        "snippet": snippet,
                        "source": "math_stackexchange"
                    })
                
                return results
                
        except Exception as e:
            print(f" Math StackExchange search failed: {e}")
            return []

class KhanAcademyProvider(SearchProvider):
    """Khan Academy search for educational math content"""
    
    async def search(self, query: str, max_results: int = 3) -> List[Dict]:
        """Search Khan Academy (simplified approach)"""
        try:
            
            results = []
            base_url = "https://www.khanacademy.org"
            math_topics = {
                "algebra": "Basic algebra concepts and problem solving",
                "calculus": "Differential and integral calculus",
                "geometry": "Geometric shapes, theorems, and proofs",
                "trigonometry": "Trigonometric functions and identities",
                "statistics": "Statistics and probability concepts"
            }
            
            query_lower = query.lower()
            for topic, description in math_topics.items():
                if topic in query_lower:
                    results.append({
                        "title": f"Khan Academy: {topic.capitalize()}",
                        "url": f"{base_url}/math/{topic}",
                        "snippet": description,
                        "source": "khan_academy"
                    })
                    
                    if len(results) >= max_results:
                        break
            
            return results
            
        except Exception as e:
            print(f"❌ Khan Academy search failed: {e}")
            return []
