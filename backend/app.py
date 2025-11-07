from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from pathlib import Path
import random

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create data directory if it doesn't exist
data_dir = Path(__file__).parent / "data"
data_dir.mkdir(exist_ok=True)

# Mock data generator for demonstration
def generate_mock_geojson(city_name):
    """Generate mock GeoJSON data for a city"""
    areas = [
        {"name": "Downtown", "lat": 12.9716, "lng": 77.5946},
        {"name": "North Zone", "lat": 13.1, "lng": 77.6},
        {"name": "South Zone", "lat": 12.85, "lng": 77.58},
        {"name": "East Zone", "lat": 12.98, "lng": 77.7},
        {"name": "West Zone", "lat": 12.95, "lng": 77.5},
        {"name": "Central Zone", "lat": 12.97, "lng": 77.6},
        {"name": "Airport Area", "lat": 13.2, "lng": 77.7},
        {"name": "Tech Park", "lat": 12.9, "lng": 77.65}
    ]

    features = []
    for area in areas:
        # Generate realistic signal data with some variation
        base_signal = 70 + (random.random() * 20)  # 70-90%
        base_download = 25 + (random.random() * 20)  # 25-45 Mbps
        base_upload = 8 + (random.random() * 12)     # 8-20 Mbps
        base_latency = 30 + (random.random() * 40)   # 30-70 ms

        # Add some variation for different areas
        if "Airport" in area["name"]:
            base_signal -= 15
            base_download -= 10
            base_latency += 20
        elif "Tech Park" in area["name"]:
            base_signal += 5
            base_download += 15
            base_latency -= 10

        # Create polygon with some random offset
        offset = 0.03 + (random.random() * 0.02)
        
        feature = {
            "type": "Feature",
            "properties": {
                "name": area["name"],
                "signal_strength": max(0, min(100, round(base_signal, 1))),
                "avg_download": max(0, round(base_download, 1)),
                "avg_upload": max(0, round(base_upload, 1)),
                "latency": max(0, round(base_latency, 1))
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [area["lng"] - offset, area["lat"] - offset],
                    [area["lng"] + offset, area["lat"] - offset],
                    [area["lng"] + offset, area["lat"] + offset],
                    [area["lng"] - offset, area["lat"] + offset],
                    [area["lng"] - offset, area["lat"] - offset]
                ]]
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }

@app.route('/api/cities')
def get_cities():
    """Get list of available cities"""
    cities = ['Bangalore', 'Delhi', 'Mumbai', 'Chennai', 'Hyderabad', 'Pune', 'Kolkata']
    return jsonify(cities)

@app.route('/api/map/<city>')
def get_map_data(city):
    """Get GeoJSON map data for a specific city"""
    try:
        # For now, generate mock data
        # In a real implementation, this would load from actual GeoJSON files
        geo_data = generate_mock_geojson(city)
        return jsonify(geo_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Signal Coverage API is running"})

if __name__ == '__main__':
    print("Starting Signal Coverage API...")
    print("Available endpoints:")
    print("  GET /api/cities - List available cities")
    print("  GET /api/map/<city> - Get map data for a city")
    print("  GET /api/health - Health check")
    
    app.run(debug=True, port=5001)  # Using port 5001 to avoid conflict with existing Flask app