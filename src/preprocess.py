
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, Point
import os
import json

def create_mock_boundaries(city_name):
    """Creates a GeoDataFrame with mock administrative boundaries for a city."""
    if city_name.lower() == 'bengaluru':
        # Create a few sample wards in Bengaluru
        wards = {
            'area_name': ['Indiranagar', 'Koramangala', 'Jayanagar', 'Rajajinagar', 'Kengeri'],
            'geometry': [
                Polygon([(77.63, 12.97), (77.64, 12.97), (77.64, 12.98), (77.63, 12.98), (77.63, 12.97)]),
                Polygon([(77.62, 12.93), (77.63, 12.93), (77.63, 12.94), (77.62, 12.94), (77.62, 12.93)]),
                Polygon([(77.58, 12.92), (77.59, 12.92), (77.59, 12.93), (77.58, 12.93), (77.58, 12.92)]),
                Polygon([(77.55, 12.99), (77.56, 12.99), (77.56, 13.00), (77.55, 13.00), (77.55, 12.99)]),
                Polygon([(77.48, 12.92), (77.49, 12.92), (77.49, 12.93), (77.48, 12.93), (77.48, 12.92)])
            ]
        }
        gdf = gpd.GeoDataFrame(wards, crs="EPSG:4326")
        gdf['city_name'] = city_name
        return gdf
    else:
        return gpd.GeoDataFrame()

def generate_mock_predictions(boundaries_gdf, num_points=1000):
    """Generates mock prediction data within the given boundaries."""
    points = []
    min_x, min_y, max_x, max_y = boundaries_gdf.total_bounds
    
    while len(points) < num_points:
        random_point = Point(np.random.uniform(min_x, max_x), np.random.uniform(min_y, max_y))
        if boundaries_gdf.geometry.contains(random_point).any():
            points.append(random_point)
            
    predictions_gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")
    predictions_gdf['signal_strength'] = np.random.uniform(0, 100, num_points)
    predictions_gdf['avg_download'] = np.random.uniform(10, 100, num_points)
    predictions_gdf['avg_upload'] = np.random.uniform(5, 50, num_points)
    predictions_gdf['latency'] = np.random.uniform(10, 100, num_points)
    predictions_gdf['timestamp'] = pd.to_datetime('now')
    return predictions_gdf

def aggregate_data_to_areas(predictions_gdf, boundaries_gdf):
    """Aggregates prediction data to administrative areas."""
    # Spatial join to associate points with areas
    joined_gdf = gpd.sjoin(predictions_gdf, boundaries_gdf, how="inner", predicate='within')
    
    # Group by area and calculate statistics
    area_stats = joined_gdf.groupby('area_name').agg(
        signal_strength=('signal_strength', 'mean'),
        avg_download=('avg_download', 'mean'),
        avg_upload=('avg_upload', 'mean'),
        latency=('latency', 'mean'),
        samples=('signal_strength', 'count')
    ).reset_index()
    
    # Merge stats back with boundaries
    aggregated_gdf = boundaries_gdf.merge(area_stats, on='area_name')
    
    # Add timestamp
    aggregated_gdf['timestamp'] = pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S')
    
    return aggregated_gdf

if __name__ == "__main__":
    CITY = "Bengaluru"
    OUTPUT_DIR = "outputs"
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # 1. Create mock boundaries
    boundaries = create_mock_boundaries(CITY)
    
    # 2. Generate mock predictions
    predictions = generate_mock_predictions(boundaries, num_points=5000)
    
    # 3. Aggregate data
    area_level_data = aggregate_data_to_areas(predictions, boundaries)
    
    # 4. Save to GeoJSON
    output_path = os.path.join(OUTPUT_DIR, "predictions_city_level.geojson")
    area_level_data.to_file(output_path, driver='GeoJSON')
    
    print(f"Successfully generated and saved city-level predictions to {output_path}")
    print("\n--- Sample Data ---")
    print(area_level_data.head())

    # 5. Calculate and save summary metrics
    summary_metrics = {
        "city_name": CITY,
        "avg_signal_strength": float(area_level_data['signal_strength'].mean()),
        "avg_download_speed": float(area_level_data['avg_download'].mean()),
        "avg_upload_speed": float(area_level_data['avg_upload'].mean()),
        "avg_latency": float(area_level_data['latency'].mean()),
        "timestamp": pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S')
    }
    summary_output_path = os.path.join(OUTPUT_DIR, "metrics_summary.json")
    with open(summary_output_path, 'w') as f:
        json.dump(summary_metrics, f, indent=4)
        
    print(f"\nSuccessfully generated and saved summary metrics to {summary_output_path}")
    print("\n--- Summary Metrics ---")
    print(summary_metrics)