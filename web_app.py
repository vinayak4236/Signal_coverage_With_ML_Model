#!/usr/bin/env python3
"""
Enhanced Web Interface for Signal Coverage Prediction

This web application allows users to:
1. Enter a city name
2. View city-level signal strength coverage
3. Zoom in to see area-level signal strength details
4. Interact with multi-resolution predictions
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MarkerCluster
from branca.colormap import LinearColormap
from flask import Flask, render_template, request, jsonify, send_from_directory

from signal_model import (
    load_csv_dataset,
    generate_multi_resolution_grid,
    get_resolution_recommendations,
    SignalStrengthModel,
)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'signal_coverage_web_app_2024'

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "sample_measurements.csv"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Create directories
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# Global model (loaded once at startup)
signal_model = None

def _quality_label_and_color(metric: str, value: float) -> tuple[str, str]:
    """Return (label, hex_color) for a value under the given metric using thresholds.
    Colors: Excellent=#2ecc71, Good=#f1c40f, Fair=#e67e22, Poor=#e74c3c
    """
    # Default thresholds for download speed (primary metric)
    if value >= 50:
        return 'Excellent', '#2ecc71'
    if value >= 20:
        return 'Good', '#f1c40f'
    if value >= 5:
        return 'Fair', '#e67e22'
    return 'Poor', '#e74c3c'

class CityGeocoder:
    """Handle city name to coordinates conversion using multiple services."""
    
    def __init__(self):
        self.cache = {}
    
    def geocode_city(self, city_name: str) -> Dict:
        """Convert city name to coordinates using multiple geocoding services with India-specific enhancements."""
        # Enhanced city name processing for India
        city_name = self._process_city_name(city_name)
        
        # Check cache first
        if city_name in self.cache:
            return self.cache[city_name]
        
        # Try multiple geocoding services with India-specific priority
        services = [
            self._geocode_nominatim_india,
            self._geocode_google_fallback,  # Hardcoded India cities first
            self._geocode_nominatim,        # General Nominatim fallback
            self._geocode_opencage           # Future OpenCage implementation
        ]
        
        for service in services:
            try:
                result = service(city_name)
                if result:
                    self.cache[city_name] = result
                    return result
            except Exception as e:
                print(f"Geocoding service {service.__name__} failed: {e}")
                continue
        
        # Enhanced error message with India-specific suggestions
        india_suggestions = self._get_india_city_suggestions(city_name)
        error_msg = f"Could not find coordinates for city: {city_name}"
        if india_suggestions:
            error_msg += f"\nDid you mean: {', '.join(india_suggestions[:3])}?"
        
        raise ValueError(error_msg)
    
    def _process_city_name(self, city_name: str) -> str:
        """Process city name with India-specific enhancements."""
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
    
    def _get_india_city_suggestions(self, partial_name: str) -> List[str]:
        """Get India city suggestions for typos or similar names."""
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
        
        # Exact match first
        for city in india_cities:
            if partial_lower in city.lower():
                suggestions.append(city)
        
        # Sort by similarity
        suggestions.sort(key=lambda x: len(x))
        return suggestions[:5]  # Return top 5 suggestions
    
    def _geocode_nominatim_india(self, city_name: str) -> Optional[Dict]:
        """Enhanced Nominatim geocoding with India-specific optimizations."""
        # Try India-specific search first
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
                        if any(term in result.get('type', '').lower() 
                               for term in ['city', 'town', 'municipality', 'district']):
                            return {
                                'name': city_name,
                                'lat': float(result['lat']),
                                'lon': float(result['lon']),
                                'display_name': result['display_name'],
                                'service': 'nominatim_india'
                            }
                    
                    # If no perfect match, use first result
                    result = data[0]
                    return {
                        'name': city_name,
                        'lat': float(result['lat']),
                        'lon': float(result['lon']),
                        'display_name': result['display_name'],
                        'service': 'nominatim_india'
                    }
        except Exception as e:
            print(f"India-specific Nominatim failed: {e}")
        
        return None
    
    def _geocode_nominatim(self, city_name: str) -> Optional[Dict]:
        """Use OpenStreetMap Nominatim service (free)."""
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': city_name,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                result = data[0]
                return {
                    'name': city_name,
                    'lat': float(result['lat']),
                    'lon': float(result['lon']),
                    'display_name': result['display_name'],
                    'service': 'nominatim'
                }
        return None
    
    def _geocode_opencage(self, city_name: str) -> Optional[Dict]:
        """Use OpenCage service (requires API key)."""
        # This would require an API key - placeholder for future implementation
        return None
    
    def _geocode_google_fallback(self, city_name: str) -> Optional[Dict]:
        """Fallback to hardcoded major cities (comprehensive India coverage)."""
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
            return {
                'name': city_name,
                'lat': city_data['lat'],
                'lon': city_data['lon'],
                'display_name': city_data['display_name'],
                'service': 'hardcoded'
            }
        return None

class SignalCoveragePredictor:
    """Handle signal strength prediction for cities and areas."""
    
    def __init__(self, models: Dict[str, SignalStrengthModel]):
        self.models = models  # Dictionary of models by metric name
        self.geocoder = CityGeocoder()
    
    def predict_city_coverage(self, city_name: str, resolution_level: str = "city", metric: str = 'signal_strength') -> Dict:
        """Predict signal coverage for an entire city."""
        print(f"Predicting coverage for city: {city_name}")
        
        # Get city coordinates
        city_info = self.geocoder.geocode_city(city_name)
        lat, lon = city_info['lat'], city_info['lon']
        
        # Determine appropriate radius based on city size
        radius_m = self._get_city_radius(city_name)
        
        # Generate prediction grid
        grid = generate_multi_resolution_grid(
            center_lat=lat,
            center_lon=lon,
            radius_m=radius_m,
            resolution_level=resolution_level
        )
        
        # Generate predictions for all three metrics
        all_stats = {}
        all_predictions = {}
        
        for metric_name in ['download_mbps', 'upload_mbps', 'latency_ms']:
            # Use the appropriate model for this metric
            if metric_name not in self.models:
                raise ValueError(f"No model available for metric: {metric_name}")
            
            model = self.models[metric_name]
            predictions = model.predict(grid)
            all_predictions[metric_name] = predictions
            
            # Calculate statistics for this metric
            all_stats[metric_name] = self._calculate_coverage_stats(predictions, metric_name)
        
        # Use download_mbps as the primary metric for the grid signal
        grid['signal'] = all_predictions['download_mbps']
        
        return {
            'city_info': city_info,
            'grid': grid,
            'predictions': all_predictions['download_mbps'],  # Primary metric for display
            'stats': all_stats,  # All metrics stats
            'radius_m': radius_m,
            'resolution_level': resolution_level,
            'total_points': len(grid),
            'metric': 'download_mbps'  # Default to download speed
        }
    
    def predict_area_coverage(self, lat: float, lon: float, radius_m: float = 1000, 
                            resolution_level: str = "fine", metric: str = 'signal_strength') -> Dict:
        """Predict signal coverage for a specific area (for zoom functionality)."""
        print(f"Predicting area coverage: ({lat}, {lon}), radius: {radius_m}m")
        
        # Generate high-resolution grid for detailed area analysis
        grid = generate_multi_resolution_grid(
            center_lat=lat,
            center_lon=lon,
            radius_m=radius_m,
            resolution_level=resolution_level
        )
        
        # Generate predictions for all three metrics
        all_stats = {}
        all_predictions = {}
        
        for metric_name in ['download_mbps', 'upload_mbps', 'latency_ms']:
            # Use the appropriate model for this metric
            if metric_name not in self.models:
                raise ValueError(f"No model available for metric: {metric_name}")
            
            model = self.models[metric_name]
            predictions = model.predict(grid)
            all_predictions[metric_name] = predictions
            
            # Calculate statistics for this metric
            all_stats[metric_name] = self._calculate_coverage_stats(predictions, metric_name)
        
        # Use download_mbps as the primary metric for the grid signal
        grid['signal'] = all_predictions['download_mbps']
        
        return {
            'center': {'lat': lat, 'lon': lon},
            'grid': grid,
            'predictions': all_predictions['download_mbps'],  # Primary metric for display
            'stats': all_stats,  # All metrics stats
            'radius_m': radius_m,
            'resolution_level': resolution_level,
            'total_points': len(grid),
            'metric': 'download_mbps'  # Default to download speed
        }
    
    def _get_city_radius(self, city_name: str) -> int:
        """Determine appropriate radius based on city size and population."""
        # Comprehensive city radius mapping for India and international cities
        city_radius_map = {
            # **INDIA - TIER 1 METRO CITIES** (Largest radius for major metros)
            'Mumbai': 20000, 'Delhi': 20000, 'New Delhi': 20000,
            'Bengaluru': 18000, 'Bangalore': 18000,
            'Kolkata': 18000, 'Chennai': 18000, 'Madras': 18000,
            'Hyderabad': 18000,
            
            # **INDIA - TIER 2 CITIES** (Medium radius for large cities)
            'Pune': 15000, 'Poona': 15000,
            'Ahmedabad': 15000, 'Surat': 15000,
            'Jaipur': 15000, 'Lucknow': 15000, 'Kanpur': 15000,
            'Nagpur': 15000, 'Indore': 15000, 'Bhopal': 15000,
            'Visakhapatnam': 15000, 'Vadodara': 15000, 'Baroda': 15000,
            'Coimbatore': 15000, 'Patna': 15000, 'Bhubaneswar': 15000,
            'Ludhiana': 15000, 'Agra': 15000, 'Madurai': 15000,
            'Jamshedpur': 15000, 'Vijayawada': 15000, 'Nashik': 15000,
            'Rajkot': 15000, 'Raipur': 15000, 'Varanasi': 15000,
            'Kochi': 15000, 'Cochin': 15000, 'Thiruvananthapuram': 15000, 'Trivandrum': 15000,
            
            # **INDIA - STATE CAPITALS & UNION TERRITORIES**
            'Guwahati': 12000, 'Chandigarh': 12000, 'Dehradun': 12000,
            'Shimla': 12000, 'Gangtok': 12000, 'Itanagar': 12000,
            'Dispur': 12000, 'Imphal': 12000, 'Aizawl': 12000,
            'Kohima': 12000, 'Agartala': 12000, 'Shillong': 12000,
            'Port Blair': 12000, 'Puducherry': 12000, 'Pondicherry': 12000,
            'Daman': 12000, 'Diu': 12000, 'Silvassa': 12000,
            'Srinagar': 12000, 'Jammu': 12000, 'Leh': 12000, 'Kargil': 12000,
            
            # **INTERNATIONAL CITIES**
            'New York': 15000, 'Los Angeles': 20000, 'Chicago': 12000,
            'London': 15000, 'Paris': 10000, 'Tokyo': 15000,
            'Sydney': 10000,
            
            # **ADDITIONAL LARGE INTERNATIONAL CITIES**
            'San Francisco': 15000, 'Houston': 15000, 'Phoenix': 12000,
            'Philadelphia': 10000, 'San Antonio': 10000, 'San Diego': 10000,
            'Dallas': 10000, 'Toronto': 10000
        }
        
        return city_radius_map.get(city_name, 8000)  # Default 8km radius for smaller cities
    
    def _calculate_coverage_stats(self, predictions: np.ndarray, metric: str) -> Dict:
        """Calculate comprehensive coverage statistics per metric."""
        v = predictions
        # Hardcoded thresholds for download speed (download_mbps)
        def excellent_threshold(values):
            return values >= 50
        def good_threshold(values):
            return (values >= 25) & (values < 50)
        def fair_threshold(values):
            return (values >= 10) & (values < 25)
        def poor_threshold(values):
            return values < 10
        
        return {
            'mean_value': float(np.mean(predictions)),
            'std_value': float(np.std(predictions)),
            'min_value': float(np.min(predictions)),
            'max_value': float(np.max(predictions)),
            'coverage_percentage': {
                'excellent': float(np.sum(excellent_threshold(v)) / len(v) * 100),
                'good': float(np.sum(good_threshold(v)) / len(v) * 100),
                'fair': float(np.sum(fair_threshold(v)) / len(v) * 100),
                'poor': float(np.sum(poor_threshold(v)) / len(v) * 100),
            },
            'value_distribution': {
                'q25': float(np.percentile(predictions, 25)),
                'q50': float(np.percentile(predictions, 50)),
                'q75': float(np.percentile(predictions, 75))
            }
        }

def create_city_map(city_data: Dict) -> str:
    """Creates a Folium map for a city's signal coverage."""
    city_info = city_data['city_info']
    df = pd.DataFrame(city_data['grid'])
    stats = city_data['stats']
    metric = city_data.get('metric', 'download_mbps')

    # Check if 'df' is empty
    if df.empty:
        # Create a map centered on the city, but with a message
        fmap = folium.Map(location=[city_info['lat'], city_info['lon']], zoom_start=12)
        folium.Marker(
            location=[city_info['lat'], city_info['lon']],
            popup=f"<b>{city_info['name']}</b><br>No data available.",
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(fmap)
        return fmap._repr_html_()

    # Determine the signal strength for the heatmap
    df['strength'] = city_data['predictions']
    
    # Create the map
    fmap = folium.Map(location=[city_info['lat'], city_info['lon']], zoom_start=12)

    # Add heatmap layer
    HeatMap(
        data=df[['latitude', 'longitude', 'strength']].values,
        radius=15,
        blur=20,
        max_zoom=18,
        gradient={0.2: 'blue', 0.4: 'green', 0.6: 'yellow', 1: 'red'}
    ).add_to(fmap)

    # Add a marker for the city center
    folium.Marker(
        location=[city_info['lat'], city_info['lon']],
        popup=f"<b>{city_info['name']}</b><br>{city_info['display_name']}",
        icon=folium.Icon(color="red", icon="star", prefix="fa"),
    ).add_to(fmap)
    
    # Add coverage statistics panel
    # Get stats for all three metrics
    download_stats = stats.get('download_mbps', {})
    upload_stats = stats.get('upload_mbps', {})
    latency_stats = stats.get('latency_ms', {})
    
    # Download speed stats
    dl_mean = download_stats.get('mean_value', 0)
    dl_coverage = download_stats.get('coverage_percentage', {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0})
    
    # Upload speed stats
    ul_mean = upload_stats.get('mean_value', 0)
    ul_coverage = upload_stats.get('coverage_percentage', {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0})
    
    # Latency stats
    lat_mean = latency_stats.get('mean_value', 0)
    lat_coverage = latency_stats.get('coverage_percentage', {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0})
    
    stats_html = f"""
    <div style='position: fixed; top: 10px; right: 10px; z-index: 1000; background-color: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);'>
      <h4 style='margin-top: 0; margin-bottom: 10px; font-size: 16px;'>{city_info['name']} Signal Quality</h4>
      <div style='font-size: 12px;'>
        <p style='margin: 2px 0;'><b>Download:</b> {dl_mean:.1f} Mbps</p>
        <p style='margin: 2px 0;'><b>Upload:</b> {ul_mean:.1f} Mbps</p>
        <p style='margin: 2px 0;'><b>Latency:</b> {lat_mean:.1f} ms</p>
        <hr style='margin: 5px 0;'>
        <p style='margin: 2px 0;'><b>Points:</b> {city_data['total_points']:,}</p>
        <p style='margin: 2px 0;'><b>Resolution:</b> {city_data['resolution_level'].upper()}</p>
        <p style='margin: 2px 0;'><b>Radius:</b> {city_data['radius_m']:,}m</p>
      </div>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(stats_html))

    # Add quality legend (category colors)
    legend_html = f"""
    <div style='position: fixed; bottom: 20px; right: 20px; z-index: 9999; background: white; padding: 10px 12px; border: 1px solid #ccc; border-radius: 8px;'>
      <div style='font-weight:600; margin-bottom:6px;'>Quality Legend</div>
      <div style='display:flex; align-items:center; gap:6px; margin:4px 0;'>
        <span style='display:inline-block;width:12px;height:12px;background:#2ecc71;border:1px solid #333;'></span>
        <span>Excellent</span>
      </div>
      <div style='display:flex; align-items:center; gap:6px; margin:4px 0;'>
        <span style='display:inline-block;width:12px;height:12px;background:#f1c40f;border:1px solid #333;'></span>
        <span>Good</span>
      </div>
      <div style='display:flex; align-items:center; gap:6px; margin:4px 0;'>
        <span style='display:inline-block;width:12px;height:12px;background:#e67e22;border:1px solid #333;'></span>
        <span>Fair</span>
      </div>
      <div style='display:flex; align-items:center; gap:6px; margin:4px 0;'>
        <span style='display:inline-block;width:12px;height:12px;background:#e74c3c;border:1px solid #333;'></span>
        <span>Poor</span>
      </div>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control
    folium.LayerControl().add_to(fmap)
    
    return fmap._repr_html_()

def create_area_map(area_data: Dict) -> str:
    """Create a detailed map for area-level signal coverage."""
    center = area_data['center']
    grid = area_data['grid']
    predictions = area_data['predictions']
    stats = area_data['stats']
    metric = area_data.get('metric', 'download_mbps')
    
    # Create base map
    fmap = folium.Map(
        location=[center['lat'], center['lon']],
        zoom_start=15,
        tiles='OpenStreetMap'
    )
    
    # Color map for download speed
    cmap = LinearColormap(
        colors=["#d73027", "#fc8d59", "#fee08b", "#91cf60", "#1a9850"],
        vmin=0, vmax=100,
        caption="Download Speed (Mbps)"
    )
    
    # Add detailed markers
    for _, row in grid.iterrows():
        signal = row['signal']
        # Compute quality according to thresholds with color
        quality, qcolor = _quality_label_and_color(metric, signal)
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=4,
            color=qcolor,
            weight=1,
            fill=True,
            fill_color=cmap(signal),
            fill_opacity=0.8,
            popup=f"<div style='display:flex;align-items:center;gap:6px;'>"
                  f"<span style='display:inline-block;width:10px;height:10px;background:{qcolor};border:1px solid #333;'></span>"
                  f"<span><b>{quality}</b></span></div>"
                  f"Download Speed: {signal:.1f} Mbps<br>Location: ({row['latitude']:.5f}, {row['longitude']:.5f})"
        ).add_to(fmap)
    
    # Add center marker
    folium.Marker(
        location=[center['lat'], center['lon']],
        popup="Area Center",
        icon=folium.Icon(color="black", icon="crosshairs", prefix="fa"),
    ).add_to(fmap)
    
    # Add area boundary
    folium.Circle(
        location=[center['lat'], center['lon']],
        radius=area_data['radius_m'],
        color="blue",
        weight=2,
        fill=False,
        name=f"{area_data['radius_m']}m radius"
    ).add_to(fmap)
    
    # Add area statistics panel
    # Get stats for all three metrics
    download_stats = stats.get('download_mbps', {})
    upload_stats = stats.get('upload_mbps', {})
    latency_stats = stats.get('latency_ms', {})
    
    # Download speed stats
    dl_mean = download_stats.get('mean_value', 0)
    dl_min = download_stats.get('min_value', 0)
    dl_max = download_stats.get('max_value', 0)
    dl_coverage = download_stats.get('coverage_percentage', {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0})
    
    # Upload speed stats
    ul_mean = upload_stats.get('mean_value', 0)
    ul_min = upload_stats.get('min_value', 0)
    ul_max = upload_stats.get('max_value', 0)
    ul_coverage = upload_stats.get('coverage_percentage', {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0})
    
    # Latency stats
    lat_mean = latency_stats.get('mean_value', 0)
    lat_min = latency_stats.get('min_value', 0)
    lat_max = latency_stats.get('max_value', 0)
    lat_coverage = latency_stats.get('coverage_percentage', {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0})
    
    stats_html = f"""
    <div style='position: fixed; top: 20px; right: 20px; z-index: 9999; background: white; padding: 15px; border: 2px solid #28a745; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.2); min-width: 280px; max-height: 400px; overflow-y: auto;'>
      <h4 style='margin: 0 0 10px 0; color: #28a745;'>Area Coverage Details</h4>
      
      <!-- Download Speed Section -->
      <div style='margin-bottom: 15px; padding: 8px; background: #f8f9fa; border-radius: 4px;'>
        <h5 style='margin: 0 0 8px 0; color: #495057; font-size: 14px;'>📥 Download Speed</h5>
        <p style='margin: 3px 0; font-size: 12px;'><b>Mean:</b> {dl_mean:.1f} Mbps</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Range:</b> {dl_min:.1f} to {dl_max:.1f} Mbps</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Excellent (≥50 Mbps):</b> {dl_coverage['excellent']:.1f}%</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Good (20-50 Mbps):</b> {dl_coverage['good']:.1f}%</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Fair (5-20 Mbps):</b> {dl_coverage['fair']:.1f}%</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Poor (<5 Mbps):</b> {dl_coverage['poor']:.1f}%</p>
      </div>
      
      <!-- Upload Speed Section -->
      <div style='margin-bottom: 15px; padding: 8px; background: #f8f9fa; border-radius: 4px;'>
        <h5 style='margin: 0 0 8px 0; color: #495057; font-size: 14px;'>📤 Upload Speed</h5>
        <p style='margin: 3px 0; font-size: 12px;'><b>Mean:</b> {ul_mean:.1f} Mbps</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Range:</b> {ul_min:.1f} to {ul_max:.1f} Mbps</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Excellent (≥25 Mbps):</b> {ul_coverage['excellent']:.1f}%</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Good (10-25 Mbps):</b> {ul_coverage['good']:.1f}%</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Fair (2-10 Mbps):</b> {ul_coverage['fair']:.1f}%</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Poor (<2 Mbps):</b> {ul_coverage['poor']:.1f}%</p>
      </div>
      
      <!-- Latency Section -->
      <div style='margin-bottom: 15px; padding: 8px; background: #f8f9fa; border-radius: 4px;'>
        <h5 style='margin: 0 0 8px 0; color: #495057; font-size: 14px;'>⚡ Latency</h5>
        <p style='margin: 3px 0; font-size: 12px;'><b>Mean:</b> {lat_mean:.1f} ms</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Range:</b> {lat_min:.1f} to {lat_max:.1f} ms</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Excellent (≤20 ms):</b> {lat_coverage['excellent']:.1f}%</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Good (20-50 ms):</b> {lat_coverage['good']:.1f}%</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Fair (50-100 ms):</b> {lat_coverage['fair']:.1f}%</p>
        <p style='margin: 3px 0; font-size: 12px;'><b>Poor (>100 ms):</b> {lat_coverage['poor']:.1f}%</p>
      </div>
      
      <hr style='margin: 10px 0;'>
      <p style='margin: 5px 0; font-size: 11px; color: #666;'>
        <b>Points:</b> {area_data['total_points']:,}<br>
        <b>Resolution:</b> {area_data['resolution_level'].upper()}<br>
        <b>Radius:</b> {area_data['radius_m']:,}m
      </p>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(stats_html))

    # Add quality legend (category colors)
    legend_html = f"""
    <div style='position: fixed; bottom: 20px; right: 20px; z-index: 9999; background: white; padding: 10px 12px; border: 1px solid #ccc; border-radius: 8px;'>
      <div style='font-weight:600; margin-bottom:6px;'>Quality Legend</div>
      <div style='display:flex; align-items:center; gap:6px; margin:4px 0;'>
        <span style='display:inline-block;width:12px;height:12px;background:#2ecc71;border:1px solid #333;'></span>
        <span>Excellent</span>
      </div>
      <div style='display:flex; align-items:center; gap:6px; margin:4px 0;'>
        <span style='display:inline-block;width:12px;height:12px;background:#f1c40f;border:1px solid #333;'></span>
        <span>Good</span>
      </div>
      <div style='display:flex; align-items:center; gap:6px; margin:4px 0;'>
        <span style='display:inline-block;width:12px;height:12px;background:#e67e22;border:1px solid #333;'></span>
        <span>Fair</span>
      </div>
      <div style='display:flex; align-items:center; gap:6px; margin:4px 0;'>
        <span style='display:inline-block;width:12px;height:12px;background:#e74c3c;border:1px solid #333;'></span>
        <span>Poor</span>
      </div>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(legend_html))
    
    # Add legend
    cmap.add_to(fmap)
    
    # Add layer control
    folium.LayerControl().add_to(fmap)
    
    return fmap._repr_html_()

# Initialize global predictor
def initialize_model():
    """Initialize the signal prediction models for all metrics."""
    global signal_models
    print("Initializing signal prediction models...")
    
    # Load training data
    df = load_csv_dataset(str(DATA_PATH))
    print(f"Loaded {len(df)} training samples")
    
    # Train separate models for each metric
    signal_models = {}
    
    for metric in ['download_mbps', 'upload_mbps', 'latency_ms']:
        print(f"Training model for {metric}...")
        model = SignalStrengthModel(model_type="rf", target_column=metric)
        result = model.fit(df)
        signal_models[metric] = model
        print(f"  {metric} model trained - R²={result.r2:.2f}, MAE={result.mae:.2f}")
    
    return SignalCoveragePredictor(signal_models)

# Initialize predictor
predictor = initialize_model()

@app.route('/')
def index():
    """Main page with city input form."""
    return render_template('index.html')

@app.route('/predict_city', methods=['POST'])
def predict_city():
    """Predict signal coverage for a city."""
    try:
        data = request.get_json()
        city_name = data.get('city_name', '').strip()
        resolution_level = data.get('resolution_level', 'medium')
        metric = data.get('metric', 'download_mbps')
        
        app.logger.info(f"Received predict_city request for city: {city_name}, resolution: {resolution_level}, metric: {metric}")

        if not city_name:
            return jsonify({'error': 'City name is required'}), 400
        
        # Predict city coverage
        app.logger.info("Calling predictor.predict_city_coverage")
        city_data = predictor.predict_city_coverage(city_name, resolution_level, metric)
        app.logger.info("Finished predictor.predict_city_coverage")
        
        # Create map and save as HTML file for front-end to load dynamically
        app.logger.info("Calling create_city_map")
        map_html = create_city_map(city_data)
        map_path = STATIC_DIR / f"{city_name.lower().replace(' ', '_')}_map.html"
        with open(map_path, "w", encoding="utf-8") as f:
            f.write(map_html)
        app.logger.info(f"Map saved to: {map_path}")
        
        return jsonify({
            'success': True,
            'city_info': city_data['city_info'],
            'stats': city_data['stats'],
            'map_url': f"/static/{city_name.lower().replace(' ', '_')}_map.html",
            'total_points': city_data['total_points'],
            'metric': city_data.get('metric', metric)
        })
        
    except Exception as e:
        app.logger.error(f"An error occurred in predict_city: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/predict_area', methods=['POST'])
def predict_area():
    """Predict signal coverage for a specific area (zoom functionality)."""
    try:
        data = request.get_json()
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        radius_m = int(data.get('radius_m', 1000))
        resolution_level = data.get('resolution_level', 'fine')
        metric = data.get('metric', 'download_mbps')
        
        # Predict area coverage
        area_data = predictor.predict_area_coverage(lat, lon, radius_m, resolution_level, metric)
        
        # Create detailed map and save as HTML file
        map_html = create_area_map(area_data)
        map_path = STATIC_DIR / f"area_{lat}_{lon}.html"
        with open(map_path, "w", encoding="utf-8") as f:
            f.write(map_html)
        
        return jsonify({
            'success': True,
            'map_url': f"/static/area_{lat}_{lon}.html",
            'stats': area_data['stats'],
            'radius_m': area_data['radius_m'],
            'resolution_level': area_data['resolution_level'],
            'total_points': area_data['total_points']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_resolution_options')
def get_resolution_options():
    """Get available resolution options."""
    radius_m = int(request.args.get('radius_m', 2000))
    recommendations = get_resolution_recommendations(radius_m)
    
    return jsonify({
        'recommendations': recommendations,
        'default': 'medium'
    })

@app.route('/api/map/<city>')
def api_map_city(city):
    """API endpoint for map data - returns GeoJSON for the city."""
    try:
        # Convert city name to proper format
        city_name = city.strip().lower()
        
        # Construct GeoJSON file path
        geojson_file = BASE_DIR / "data" / f"{city_name.lower().replace(' ', '_')}_areas.geojson"
        
        # Check if GeoJSON file exists
        if not geojson_file.exists():
            app.logger.warning(f"GeoJSON file not found: {geojson_file}")
            # Fallback: generate sample GeoJSON data for demonstration
            app.logger.info(f"Generating sample GeoJSON data for {city_name}")
            
            # Get city coordinates
            city_info = predictor.geocoder.geocode_city(city_name)
            lat, lon = city_info['lat'], city_info['lon']
            
            geojson_data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "area_name": "Central Business District",
                            "signal_strength": 85.5,
                            "avg_download": 45.2,
                            "avg_upload": 12.8,
                            "latency": 18.5,
                            "samples": 234
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [lon - 0.01, lat - 0.01],
                                [lon + 0.01, lat - 0.01],
                                [lon + 0.01, lat + 0.01],
                                [lon - 0.01, lat + 0.01],
                                [lon - 0.01, lat - 0.01]
                            ]]
                        }
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "area_name": "Residential Area North",
                            "signal_strength": 72.3,
                            "avg_download": 32.1,
                            "avg_upload": 8.9,
                            "latency": 25.2,
                            "samples": 156
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [lon - 0.02, lat + 0.01],
                                [lon, lat + 0.01],
                                [lon, lat + 0.02],
                                [lon - 0.02, lat + 0.02],
                                [lon - 0.02, lat + 0.01]
                            ]]
                        }
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "area_name": "Industrial Zone",
                            "signal_strength": 45.8,
                            "avg_download": 15.7,
                            "avg_upload": 4.2,
                            "latency": 45.8,
                            "samples": 89
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [lon - 0.02, lat - 0.02],
                                [lon, lat - 0.02],
                                [lon, lat - 0.01],
                                [lon - 0.02, lat - 0.01],
                                [lon - 0.02, lat - 0.02]
                            ]]
                        }
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "area_name": "Suburban Area",
                            "signal_strength": 91.2,
                            "avg_download": 52.8,
                            "avg_upload": 15.3,
                            "latency": 12.4,
                            "samples": 312
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [lon + 0.01, lat - 0.01],
                                [lon + 0.02, lat - 0.01],
                                [lon + 0.02, lat + 0.01],
                                [lon + 0.01, lat + 0.01],
                                [lon + 0.01, lat - 0.01]
                            ]]
                        }
                    }
                ]
            }
            return jsonify(geojson_data)
        
        # Read and return the GeoJSON data
        with open(geojson_file, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        app.logger.info(f"Successfully loaded GeoJSON data for {city} from {geojson_file}")
        return jsonify(geojson_data)
        
    except Exception as e:
        app.logger.error(f"Error in api_map_city: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/signal-grid/<city>')
def api_signal_grid(city):
    """API endpoint for dense signal grid data - returns GeoJSON with ML predictions."""
    try:
        # Convert city name to proper format
        city_name = city.strip().lower()
        
        # Construct signal grid file path
        signal_grid_file = BASE_DIR / "data" / f"{city_name.lower().replace(' ', '_')}_signal_grid.geojson"
        
        # Check if signal grid file exists
        if not signal_grid_file.exists():
            app.logger.warning(f"Signal grid file not found: {signal_grid_file}")
            # Return empty feature collection
            return jsonify({
                "type": "FeatureCollection",
                "features": [],
                "message": "Signal grid data not available for this city"
            })
        
        # Read and return the signal grid data
        with open(signal_grid_file, 'r', encoding='utf-8') as f:
            signal_grid_data = json.load(f)
        
        app.logger.info(f"Successfully loaded signal grid data for {city} from {signal_grid_file}")
        return jsonify(signal_grid_data)
        
    except Exception as e:
        app.logger.error(f"Error loading signal grid data for {city}: {e}")
        return jsonify({
            "type": "FeatureCollection", 
            "features": [],
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Set up logging
    import logging
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler('web_app.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    print("Starting Signal Coverage Web Application...")
    print("=" * 50)
    print("Features:")
    print("- City name input with geocoding")
    print("- City-level signal coverage prediction")
    print("- Interactive zoom to area-level details")
    print("- Multi-resolution support")
    print("- Real-time statistics")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)