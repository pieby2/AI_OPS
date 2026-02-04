"""
News Tool - Integrates with NewsAPI for news article search
"""
import os
import requests
import time
from typing import Dict, Any, List, Optional
from .base import BaseTool


class NewsTool(BaseTool):
    """Tool for fetching news articles using NewsAPI"""
    
    def __init__(self):
        self.api_key = os.getenv("NEWS_API_KEY")
        if not self.api_key:
            raise ValueError("NEWS_API_KEY not found in environment variables")
        
        self.base_url = "https://newsapi.org/v2"
        self.max_retries = 3
    
    @property
    def name(self) -> str:
        return "search_news"
    
    @property
    def description(self) -> str:
        return "Search for news articles on any topic. Returns headlines, sources, descriptions, and URLs."
    
    @property
    def parameters(self) -> Dict[str, str]:
        return {
            "query": "Search query for news articles (e.g., 'artificial intelligence', 'climate change')",
            "category": "Optional category: business, entertainment, health, science, sports, technology",
            "limit": "Maximum number of articles to return (default: 5, max: 10)"
        }
    
    def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """
        Search for news articles
        
        Args:
            query: Search query string
            category: Optional news category
            limit: Max results to return
            
        Returns:
            dict: Search results with article information
        """
        query = kwargs.get("query", "")
        category = kwargs.get("category", None)
        limit = min(int(kwargs.get("limit", 5)), 10)
        
        if not query:
            return {
                "success": False,
                "error": "Query parameter is required"
            }
        
        # Make API request with retry logic
        for attempt in range(self.max_retries):
            try:
                # Use 'everything' endpoint for search, 'top-headlines' for category
                if category:
                    url = f"{self.base_url}/top-headlines"
                    params = {
                        "q": query,
                        "category": category,
                        "apiKey": self.api_key,
                        "pageSize": limit,
                        "language": "en"
                    }
                else:
                    url = f"{self.base_url}/everything"
                    params = {
                        "q": query,
                        "apiKey": self.api_key,
                        "pageSize": limit,
                        "sortBy": "relevancy",
                        "language": "en"
                    }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == "ok":
                        articles = self._format_articles(data.get("articles", []))
                        
                        return {
                            "success": True,
                            "data": {
                                "total_results": data.get("totalResults", 0),
                                "articles": articles[:limit]
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("message", "Unknown NewsAPI error")
                        }
                        
                elif response.status_code == 401:
                    return {
                        "success": False,
                        "error": "Invalid NewsAPI key"
                    }
                elif response.status_code == 429:
                    return {
                        "success": False,
                        "error": "NewsAPI rate limit exceeded. Please try again later."
                    }
                else:
                    if attempt < self.max_retries - 1:
                        time.sleep(1 * (attempt + 1))  # Exponential backoff
                        continue
                    return {
                        "success": False,
                        "error": f"NewsAPI error: {response.status_code}"
                    }
                    
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
                return {
                    "success": False,
                    "error": "NewsAPI request timeout"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"NewsAPI error: {str(e)}"
                }
        
        return {
            "success": False,
            "error": "Max retries exceeded"
        }
    
    def _format_articles(self, articles: List[Dict]) -> List[Dict[str, Any]]:
        """Format article data for output"""
        formatted = []
        for article in articles:
            source = article.get("source", {})
            formatted.append({
                "title": article.get("title"),
                "source": source.get("name"),
                "description": article.get("description"),
                "url": article.get("url"),
                "published_at": article.get("publishedAt"),
                "author": article.get("author")
            })
        return formatted
