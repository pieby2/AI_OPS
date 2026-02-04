"""
GitHub Tool - Integrates with GitHub API for repository operations
"""
import os
import requests
import time
from typing import Dict, Any, List
from .base import BaseTool


class GitHubTool(BaseTool):
    """Tool for interacting with GitHub API"""
    
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GITHUB_TOKEN not found in environment variables")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.max_retries = 3
    
    @property
    def name(self) -> str:
        return "github_search"
    
    @property
    def description(self) -> str:
        return "Search GitHub repositories by query, get repository details including stars, description, and language"
    
    @property
    def parameters(self) -> Dict[str, str]:
        return {
            "query": "Search query for repositories (e.g., 'python web framework', 'machine learning')",
            "sort": "Sort by 'stars', 'forks', or 'updated' (default: 'stars')",
            "limit": "Maximum number of results to return (default: 5)"
        }
    
    def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """
        Search GitHub repositories
        
        Args:
            query: Search query string
            sort: Sort criteria (stars, forks, updated)
            limit: Max results to return
            
        Returns:
            dict: Search results with repository information
        """
        query = kwargs.get("query", "")
        sort = kwargs.get("sort", "stars")
        limit = int(kwargs.get("limit", 5))
        
        if not query:
            return {
                "success": False,
                "error": "Query parameter is required"
            }
        
        # Make API request with retry logic
        for attempt in range(self.max_retries):
            try:
                url = f"{self.base_url}/search/repositories"
                params = {
                    "q": query,
                    "sort": sort,
                    "order": "desc",
                    "per_page": limit
                }
                
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    repositories = self._format_repositories(data.get("items", []))
                    
                    return {
                        "success": True,
                        "data": {
                            "total_count": data.get("total_count", 0),
                            "repositories": repositories[:limit]
                        }
                    }
                elif response.status_code == 403:
                    # Rate limit exceeded
                    return {
                        "success": False,
                        "error": "GitHub API rate limit exceeded. Please try again later."
                    }
                elif response.status_code == 422:
                    return {
                        "success": False,
                        "error": f"Invalid query: {query}"
                    }
                else:
                    if attempt < self.max_retries - 1:
                        time.sleep(1 * (attempt + 1))  # Exponential backoff
                        continue
                    return {
                        "success": False,
                        "error": f"GitHub API error: {response.status_code}"
                    }
                    
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
                return {
                    "success": False,
                    "error": "GitHub API request timeout"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"GitHub API error: {str(e)}"
                }
        
        return {
            "success": False,
            "error": "Max retries exceeded"
        }
    
    def _format_repositories(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """Format repository data for output"""
        formatted = []
        for repo in items:
            formatted.append({
                "name": repo.get("name"),
                "full_name": repo.get("full_name"),
                "description": repo.get("description"),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language"),
                "url": repo.get("html_url"),
                "topics": repo.get("topics", [])
            })
        return formatted
