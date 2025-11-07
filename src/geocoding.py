"""
Geocoding Utilities for Signal Coverage Application

This module provides city name to coordinate conversion using multiple
geocoding services with India-specific enhancements.
"""

import requests
import time
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class CityCoordinates:
    """Data class for city coordinates."""
    name: str
    lat: float
    lon: float
    display_name: str
    service: str


class CityGeocoder:
    """
    Handle city name to coordinates conversion using multiple geocoding services.
    
    Features:
    - Multiple geocoding service support (Nominatim, Google, etc.)
    - India-specific city name processing
    - Comprehensive fallback system
    - Caching for improved performance
    """
    
    def __init__(self, cache_enabled: bool = True):
        """
        Initialize the geocoder.
        
        Args:
            cache_enabled: Whether to enable result caching
        """
        self.cache_enabled = cache_enabled
        self.cache = {}
        self.request_delay = 1.0  # Seconds between requests to respect rate limits
        self.last_request_time = 0
    
    def geocode_city(self, city_name: str) -> CityCoordinates:
        """
        Convert city name to coordinates using multiple geocoding services.
        
        Args:
            city_name: Name of the city
            
        Returns:
            CityCoordinates object with location data
            
        Raises:
            ValueError: If city cannot be found
        """
        # Check cache first
        if self.cache_enabled and city_name in self.cache:
            return self.cache[city_name]
        
        # Process city name with India-specific enhancements
        processed_name = self._process_city_name(city_name)
        
        # Define geocoding services in order of preference
        services = [
            self._geocode_nominatim_india,
            self._geocode_nominatim,
            self._geocode_google_fallback,
        ]
        
        # Try each service
        for service in services:
            try:
                # Rate limiting
                self._respect_rate_limit()
                
                result = service(processed_name)
                if result:
                    # Cache the result
                    if self.cache_enabled:
                        self.cache[city_name] = result
                    return result
                    
            except Exception as e:
                print(f"Geocoding service {service.__name__} failed: {e}")
                continue
        
        # If all services fail, provide helpful error message
        suggestions = self._get_india_city_suggestions(city_name)
        error_msg = f"Could not find coordinates for city: {city_name}"
        if suggestions:
            error_msg += f"\nDid you mean: {', '.join(suggestions[:3])}?"
        
        raise ValueError(error_msg)
    
    def _process_city_name(self, city_name: str) -> str:
        """
        Process city name with India-specific enhancements.
        
        Args:
            city_name: Raw city name
            
        Returns:
            Processed city name
        """
        city_name = city_name.strip()
        
        # Handle common India city name variations
        india_variations = {
            'bengaluru': 'Bengaluru',
            'bangalore': 'Bengaluru',
            'chennai': 'Chennai',
            'madras': 'Chennai',
            'mumbai': 'Mumbai',
            'bombay': 'Mumbai',
            'kolkata': 'Kolkata',
            'calcutta': 'Kolkata',
            'poona': 'Pune',
            'baroda': 'Vadodara',
            'cochin': 'Kochi',
            'trivandrum': 'Thiruvananthapuram',
            'quilon': 'Kollam',
            'pondicherry': 'Puducherry',
            'new delhi': 'New Delhi',
            'gurgaon': 'Gurugram',
            'prayagraj': 'Allahabad'
        }
        
        lower_city = city_name.lower()
        if lower_city in india_variations:
            return india_variations[lower_city]
        
        return city_name.title()
    
    def _respect_rate_limit(self):
        """Respect rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def _geocode_nominatim_india(self, city_name: str) -> Optional[CityCoordinates]:
        """
        Enhanced Nominatim geocoding with India-specific optimizations.
        
        Args:
            city_name: City name to geocode
            
        Returns:
            CityCoordinates if found, None otherwise
        """
        url = "https://nominatim.openstreetmap.org/search"
        
        # First try with India context
        india_params = {
            'q': f"{city_name}, India",
            'format': 'json',
            'limit': 3,
            'addressdetails': 1,
            'countrycodes': 'IN',
            'viewbox': '68.0,37.0,97.0,6.0',  # India bounding box
            'bounded': 1
        }
        
        try:
            response = requests.get(url, params=india_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Find the best match (prefer cities/towns)
                    for result in data:
                        result_type = result.get('type', '').lower()
                        if any(term in result_type for term in ['city', 'town', 'municipality', 'district']):
                            return CityCoordinates(
                                name=city_name,
                                lat=float(result['lat']),
                                lon=float(result['lon']),
                                display_name=result['display_name'],
                                service='nominatim_india'
                            )
                    
                    # If no perfect match, use first result
                    result = data[0]
                    return CityCoordinates(
                        name=city_name,
                        lat=float(result['lat']),
                        lon=float(result['lon']),
                        display_name=result['display_name'],
                        service='nominatim_india'
                    )
        except Exception as e:
            print(f"India-specific Nominatim failed: {e}")
        
        return None
    
    def _geocode_nominatim(self, city_name: str) -> Optional[CityCoordinates]:
        """
        Use OpenStreetMap Nominatim service (free).
        
        Args:
            city_name: City name to geocode
            
        Returns:
            CityCoordinates if found, None otherwise
        """
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': city_name,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data:
                    result = data[0]
                    return CityCoordinates(
                        name=city_name,
                        lat=float(result['lat']),
                        lon=float(result['lon']),
                        display_name=result['display_name'],
                        service='nominatim'
                    )
        except Exception as e:
            print(f"Nominatim geocoding failed: {e}")
        
        return None
    
    def _geocode_google_fallback(self, city_name: str) -> Optional[CityCoordinates]:
        """
        Fallback to hardcoded major cities (comprehensive coverage).
        
        Args:
            city_name: City name to geocode
            
        Returns:
            CityCoordinates if found in hardcoded list, None otherwise
        """
        major_cities = {
            # International Cities
            'San Francisco': {'lat': 37.7749, 'lon': -122.4194, 'display_name': 'San Francisco, CA, USA'},
            'New York': {'lat': 40.7128, 'lon': -74.0060, 'display_name': 'New York, NY, USA'},
            'Los Angeles': {'lat': 34.0522, 'lon': -118.2437, 'display_name': 'Los Angeles, CA, USA'},
            'Chicago': {'lat': 41.8781, 'lon': -87.6298, 'display_name': 'Chicago, IL, USA'},
            'London': {'lat': 51.5074, 'lon': -0.1278, 'display_name': 'London, UK'},
            'Paris': {'lat': 48.8566, 'lon': 2.3522, 'display_name': 'Paris, France'},
            'Tokyo': {'lat': 35.6762, 'lon': 139.6503, 'display_name': 'Tokyo, Japan'},
            'Sydney': {'lat': -33.8688, 'lon': 151.2093, 'display_name': 'Sydney, Australia'},
            
            # **COMPREHENSIVE INDIA COVERAGE**
            # Tier 1 Cities (Metro Cities)
            'Mumbai': {'lat': 19.0760, 'lon': 72.8777, 'display_name': 'Mumbai, Maharashtra, India'},
            'Delhi': {'lat': 28.6139, 'lon': 77.2090, 'display_name': 'Delhi, India'},
            'New Delhi': {'lat': 28.6139, 'lon': 77.2090, 'display_name': 'New Delhi, Delhi, India'},
            'Bengaluru': {'lat': 12.9716, 'lon': 77.5946, 'display_name': 'Bengaluru, Karnataka, India'},
            'Bangalore': {'lat': 12.9716, 'lon': 77.5946, 'display_name': 'Bangalore (Bengaluru), Karnataka, India'},
            'Kolkata': {'lat': 22.5726, 'lon': 88.3639, 'display_name': 'Kolkata, West Bengal, India'},
            'Chennai': {'lat': 13.0827, 'lon': 80.2707, 'display_name': 'Chennai, Tamil Nadu, India'},
            'Madras': {'lat': 13.0827, 'lon': 80.2707, 'display_name': 'Chennai (Madras), Tamil Nadu, India'},
            'Hyderabad': {'lat': 17.3850, 'lon': 78.4867, 'display_name': 'Hyderabad, Telangana, India'},
            'Pune': {'lat': 18.5204, 'lon': 73.8567, 'display_name': 'Pune, Maharashtra, India'},
            'Poona': {'lat': 18.5204, 'lon': 73.8567, 'display_name': 'Pune (Poona), Maharashtra, India'},
            'Ahmedabad': {'lat': 23.0225, 'lon': 72.5714, 'display_name': 'Ahmedabad, Gujarat, India'},
            'Surat': {'lat': 21.1702, 'lon': 72.8311, 'display_name': 'Surat, Gujarat, India'},
            
            # Tier 2 Cities
            'Jaipur': {'lat': 26.9124, 'lon': 75.7873, 'display_name': 'Jaipur, Rajasthan, India'},
            'Lucknow': {'lat': 26.8467, 'lon': 80.9462, 'display_name': 'Lucknow, Uttar Pradesh, India'},
            'Kanpur': {'lat': 26.4499, 'lon': 80.3319, 'display_name': 'Kanpur, Uttar Pradesh, India'},
            'Nagpur': {'lat': 21.1458, 'lon': 79.0882, 'display_name': 'Nagpur, Maharashtra, India'},
            'Indore': {'lat': 22.7196, 'lon': 75.8577, 'display_name': 'Indore, Madhya Pradesh, India'},
            'Bhopal': {'lat': 23.2599, 'lon': 77.4126, 'display_name': 'Bhopal, Madhya Pradesh, India'},
            'Visakhapatnam': {'lat': 17.6868, 'lon': 83.2185, 'display_name': 'Visakhapatnam, Andhra Pradesh, India'},
            'Vadodara': {'lat': 22.3072, 'lon': 73.1812, 'display_name': 'Vadodara, Gujarat, India'},
            'Baroda': {'lat': 22.3072, 'lon': 73.1812, 'display_name': 'Vadodara (Baroda), Gujarat, India'},
            'Coimbatore': {'lat': 11.0168, 'lon': 76.9558, 'display_name': 'Coimbatore, Tamil Nadu, India'},
            'Patna': {'lat': 25.5941, 'lon': 85.1376, 'display_name': 'Patna, Bihar, India'},
            'Bhubaneswar': {'lat': 20.2961, 'lon': 85.8245, 'display_name': 'Bhubaneswar, Odisha, India'},
            'Ludhiana': {'lat': 30.9010, 'lon': 75.8573, 'display_name': 'Ludhiana, Punjab, India'},
            'Agra': {'lat': 27.1767, 'lon': 78.0081, 'display_name': 'Agra, Uttar Pradesh, India'},
            'Madurai': {'lat': 9.9252, 'lon': 78.1198, 'display_name': 'Madurai, Tamil Nadu, India'},
            'Jamshedpur': {'lat': 22.8046, 'lon': 86.2029, 'display_name': 'Jamshedpur, Jharkhand, India'},
            'Vijayawada': {'lat': 16.5062, 'lon': 80.6480, 'display_name': 'Vijayawada, Andhra Pradesh, India'},
            'Nashik': {'lat': 20.0051, 'lon': 73.7857, 'display_name': 'Nashik, Maharashtra, India'},
            'Rajkot': {'lat': 22.3039, 'lon': 70.8022, 'display_name': 'Rajkot, Gujarat, India'},
            'Raipur': {'lat': 21.2514, 'lon': 81.6296, 'display_name': 'Raipur, Chhattisgarh, India'},
            'Varanasi': {'lat': 25.3176, 'lon': 82.9739, 'display_name': 'Varanasi, Uttar Pradesh, India'},
            'Kollam': {'lat': 8.8932, 'lon': 76.6141, 'display_name': 'Kollam, Kerala, India'},
            'Quilon': {'lat': 8.8932, 'lon': 76.6141, 'display_name': 'Kollam (Quilon), Kerala, India'},
            'Kochi': {'lat': 9.9312, 'lon': 76.2673, 'display_name': 'Kochi, Kerala, India'},
            'Cochin': {'lat': 9.9312, 'lon': 76.2673, 'display_name': 'Kochi (Cochin), Kerala, India'},
            'Thiruvananthapuram': {'lat': 8.5241, 'lon': 76.9366, 'display_name': 'Thiruvananthapuram, Kerala, India'},
            'Trivandrum': {'lat': 8.5241, 'lon': 76.9366, 'display_name': 'Thiruvananthapuram (Trivandrum), Kerala, India'},
            
            # Tier 3 Cities
            'Guwahati': {'lat': 26.1445, 'lon': 91.7362, 'display_name': 'Guwahati, Assam, India'},
            'Chandigarh': {'lat': 30.7333, 'lon': 76.7794, 'display_name': 'Chandigarh, India'},
            'Dehradun': {'lat': 30.3165, 'lon': 78.0322, 'display_name': 'Dehradun, Uttarakhand, India'},
            'Shimla': {'lat': 31.1048, 'lon': 77.1734, 'display_name': 'Shimla, Himachal Pradesh, India'},
            'Gangtok': {'lat': 27.3389, 'lon': 88.6065, 'display_name': 'Gangtok, Sikkim, India'},
            'Itanagar': {'lat': 27.0844, 'lon': 93.6053, 'display_name': 'Itanagar, Arunachal Pradesh, India'},
            'Dispur': {'lat': 26.1445, 'lon': 91.7362, 'display_name': 'Dispur, Assam, India'},
            'Imphal': {'lat': 24.8170, 'lon': 93.9368, 'display_name': 'Imphal, Manipur, India'},
            'Aizawl': {'lat': 23.7271, 'lon': 92.7176, 'display_name': 'Aizawl, Mizoram, India'},
            'Kohima': {'lat': 25.6747, 'lon': 94.1107, 'display_name': 'Kohima, Nagaland, India'},
            'Agartala': {'lat': 23.8315, 'lon': 91.2868, 'display_name': 'Agartala, Tripura, India'},
            'Shillong': {'lat': 25.5788, 'lon': 91.8933, 'display_name': 'Shillong, Meghalaya, India'},
            'Port Blair': {'lat': 11.6234, 'lon': 92.7265, 'display_name': 'Port Blair, Andaman and Nicobar Islands, India'},
            
            # Union Territories
            'Puducherry': {'lat': 11.9416, 'lon': 79.8083, 'display_name': 'Puducherry, India'},
            'Pondicherry': {'lat': 11.9416, 'lon': 79.8083, 'display_name': 'Puducherry (Pondicherry), India'},
            'Daman': {'lat': 20.3974, 'lon': 72.8328, 'display_name': 'Daman, Daman and Diu, India'},
            'Diu': {'lat': 20.7140, 'lon': 70.9880, 'display_name': 'Diu, Daman and Diu, India'},
            'Silvassa': {'lat': 20.2755, 'lon': 73.0088, 'display_name': 'Silvassa, Dadra and Nagar Haveli, India'},
            'Srinagar': {'lat': 34.0837, 'lon': 74.7973, 'display_name': 'Srinagar, Jammu and Kashmir, India'},
            'Jammu': {'lat': 32.7266, 'lon': 74.8570, 'display_name': 'Jammu, Jammu and Kashmir, India'},
            'Leh': {'lat': 34.1526, 'lon': 77.5771, 'display_name': 'Leh, Ladakh, India'},
            'Kargil': {'lat': 34.5531, 'lon': 76.1252, 'display_name': 'Kargil, Ladakh, India'},
        }
        
        if city_name in major_cities:
            city_data = major_cities[city_name]
            return CityCoordinates(
                name=city_name,
                lat=city_data['lat'],
                lon=city_data['lon'],
                display_name=city_data['display_name'],
                service='hardcoded'
            )
        
        return None
    
    def _get_india_city_suggestions(self, partial_name: str) -> List[str]:
        """
        Get India city suggestions for typos or similar names.
        
        Args:
            partial_name: Partial city name
            
        Returns:
            List of suggested city names
        """
        india_cities = [
            'Mumbai', 'Delhi', 'Bengaluru', 'Kolkata', 'Chennai', 'Hyderabad',
            'Pune', 'Ahmedabad', 'Jaipur', 'Surat', 'Lucknow', 'Kanpur',
            'Nagpur', 'Indore', 'Bhopal', 'Patna', 'Vadodara', 'Ludhiana',
            'Agra', 'Nashik', 'Faridabad', 'Meerut', 'Rajkot', 'Varanasi',
            'Srinagar', 'Aurangabad', 'Amritsar', 'Allahabad', 'Howrah',
            'Ranchi', 'Coimbatore', 'Jodhpur', 'Madurai', 'Raipur', 'Kota',
            'Guwahati', 'Chandigarh', 'Thiruvananthapuram', 'Vijayawada',
            'Visakhapatnam', 'Bhubaneswar', 'Noida', 'Ghaziabad', 'Gurugram'
        ]
        
        partial_lower = partial_name.lower()
        suggestions = []
        
        # Find matches
        for city in india_cities:
            if partial_lower in city.lower():
                suggestions.append(city)
        
        # Sort by similarity (shorter names first)
        suggestions.sort(key=lambda x: len(x))
        return suggestions[:5]  # Return top 5 suggestions


# Convenience function
def geocode_city(city_name: str) -> CityCoordinates:
    """
    Convenience function to geocode a city name.
    
    Args:
        city_name: Name of the city
        
    Returns:
        CityCoordinates object
    """
    geocoder = CityGeocoder()
    return geocoder.geocode_city(city_name)