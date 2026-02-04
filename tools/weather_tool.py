"""
Weather Tool - Integrates with Open-Meteo API
"""
import requests
import requests_cache
import pandas as pd
from retry_requests import retry
import openmeteo_requests
from typing import Dict, Any, Optional, Tuple
from .base import BaseTool


class WeatherTool(BaseTool):
    """Tool for fetching weather data using Open-Meteo"""
    
    def __init__(self):
        # Setup the Open-Meteo API client with cache and retry on error
        # Using a local cache directory
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=retry_session)
        
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"
    
    @property
    def name(self) -> str:
        return "get_weather"
    
    @property
    def description(self) -> str:
        return "Get weather forecast for a city using Open-Meteo API (includes hourly data)"
    
    @property
    def parameters(self) -> Dict[str, str]:
        return {
            "city": "City name (e.g., 'London', 'New York')",
            "units": "temperature unit: 'metric' (default) or 'imperial'"
        }
    
    def _get_coordinates(self, city: str) -> Optional[Tuple[float, float, str, str]]:
        """Geocode city name to coordinates"""
        try:
            params = {
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json"
            }
            response = requests.get(self.geocoding_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("results"):
                return None
                
            result = data["results"][0]
            return (
                result["latitude"], 
                result["longitude"], 
                result["name"], 
                result.get("country", "Unknown")
            )
        except Exception:
            return None

    def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        city = kwargs.get("city", "")
        # Map units: metric (Celsius) is default. imperial for Fahrenheit
        units = kwargs.get("units", "metric")
        
        if not city:
            return {"success": False, "error": "City parameter is required"}
            
        # 1. Geocoding
        coords = self._get_coordinates(city)
        if not coords:
            return {"success": False, "error": f"City '{city}' not found"}
            
        lat, lon, name, country = coords
        
        try:
            # 2. Fetch Weather using Open-Meteo
            # Based on user provided snippet
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": [
                    "temperature_2m", 
                    "relative_humidity_2m", 
                    "dew_point_2m", 
                    "precipitation_probability", 
                    "apparent_temperature", 
                    "precipitation", 
                    "rain", 
                    "showers", 
                    "snow_depth"
                ]
            }
            
            if units == "imperial":
                params["temperature_unit"] = "fahrenheit"
                params["wind_speed_unit"] = "mph"
                params["precipitation_unit"] = "inch"

            responses = self.openmeteo.weather_api(self.weather_url, params=params)
            response = responses[0]
            
            # Process hourly data
            hourly = response.Hourly()
            
            # Helper to get numpy array
            def get_var(index):
                return hourly.Variables(index).ValuesAsNumpy()
            
            hourly_data = {
                "date": pd.date_range(
                    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left"
                ).astype(str).tolist(), # Convert to string for JSON serialization
                "temperature_2m": get_var(0).tolist(),
                "relative_humidity_2m": get_var(1).tolist(),
                "dew_point_2m": get_var(2).tolist(),
                "precipitation_probability": get_var(3).tolist(),
                "apparent_temperature": get_var(4).tolist(),
                "precipitation": get_var(5).tolist(),
                "rain": get_var(6).tolist(),
                "showers": get_var(7).tolist(),
                "snow_depth": get_var(8).tolist()
            }
            
            # Create a summary of current conditions (first hour) for backward compatibility/simplicity
            current_summary = {
                "city": name,
                "country": country,
                "latitude": lat,
                "longitude": lon,
                "elevation": response.Elevation(),
                "timezone_offset": response.UtcOffsetSeconds(),
                "current_temp": round(hourly_data["temperature_2m"][0], 1),
                "current_apparent_temp": round(hourly_data["apparent_temperature"][0], 1),
                "current_humidity": int(hourly_data["relative_humidity_2m"][0]),
                "precip_prob": int(hourly_data["precipitation_probability"][0]),
                "units": units
            }

            return {
                "success": True,
                "data": {
                    "summary": current_summary,
                    "hourly_forecast": hourly_data
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Open-Meteo API error: {str(e)}"
            }
