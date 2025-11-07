"""
Visualization utilities for signal coverage mapping.
"""

import folium
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from folium.plugins import HeatMap
from folium import plugins
import branca.colormap as cm


def _quality_label_and_color(signal_strength: float, metric: str = 'download_mbps') -> Tuple[str, str]:
    """
    Determine quality label and color based on signal strength and metric.
    
    Args:
        signal_strength: The signal strength value
        metric: The metric type ('download_mbps', 'upload_mbps', 'latency_ms')
        
    Returns:
        Tuple of (label, color)
    """
    if metric == 'download_mbps':
        if signal_strength >= 50:
            return 'Excellent', 'green'
        elif signal_strength >= 25:
            return 'Good', 'orange'
        elif signal_strength >= 10:
            return 'Fair', 'yellow'
        else:
            return 'Poor', 'red'
            
    elif metric == 'upload_mbps':
        if signal_strength >= 25:
            return 'Excellent', 'green'
        elif signal_strength >= 10:
            return 'Good', 'orange'
        elif signal_strength >= 5:
            return 'Fair', 'yellow'
        else:
            return 'Poor', 'red'
            
    elif metric == 'latency_ms':
        if signal_strength <= 20:
            return 'Excellent', 'green'
        elif signal_strength <= 50:
            return 'Good', 'orange'
        elif signal_strength <= 100:
            return 'Fair', 'yellow'
        else:
            return 'Poor', 'red'
    
    # Default fallback
    if signal_strength >= 75:
        return 'Excellent', 'green'
    elif signal_strength >= 50:
        return 'Good', 'orange'
    elif signal_strength >= 25:
        return 'Fair', 'yellow'
    else:
        return 'Poor', 'red'


def create_city_map(city_data: Dict) -> str:
    """
    Create a comprehensive city-level signal coverage map.
    
    Args:
        city_data: Dictionary containing city prediction data
        
    Returns:
        HTML string of the map
    """
    city_info = city_data['city_info']
    grid = city_data['grid']
    predictions = city_data['predictions']
    stats = city_data['stats']
    radius_m = city_data['radius_m']
    metric = city_data['metric']
    
    # Create base map centered on city
    m = folium.Map(
        location=[city_info['lat'], city_info['lon']],
        zoom_start=11,
        tiles='OpenStreetMap'
    )
    
    # Add different tile layers
    folium.TileLayer('cartodbpositron').add_to(m)
    folium.TileLayer('cartodbdark_matter').add_to(m)
    folium.TileLayer('Stamen Terrain').add_to(m)
    folium.TileLayer('Stamen Toner').add_to(m)
    
    # Create heatmap data
    heatmap_data = []
    for idx, row in grid.iterrows():
        heatmap_data.append([
            row['lat'],
            row['lon'],
            float(predictions.iloc[idx])
        ])
    
    # Create colormap based on metric
    if metric == 'download_mbps':
        colormap = cm.LinearColormap(
            colors=['red', 'yellow', 'orange', 'green'],
            index=[0, 10, 25, 50],
            vmin=0, vmax=100
        )
        colormap.caption = 'Download Speed (Mbps)'
        
    elif metric == 'upload_mbps':
        colormap = cm.LinearColormap(
            colors=['red', 'yellow', 'orange', 'green'],
            index=[0, 5, 10, 25],
            vmin=0, vmax=50
        )
        colormap.caption = 'Upload Speed (Mbps)'
        
    elif metric == 'latency_ms':
        colormap = cm.LinearColormap(
            colors=['green', 'yellow', 'orange', 'red'],
            index=[10, 20, 50, 100],
            vmin=10, vmax=200
        )
        colormap.caption = 'Latency (ms)'
    else:
        colormap = cm.LinearColormap(
            colors=['red', 'yellow', 'orange', 'green'],
            index=[0, 25, 50, 75],
            vmin=0, vmax=100
        )
        colormap.caption = 'Signal Strength'
    
    # Add heatmap layer
    HeatMap(
        heatmap_data,
        min_opacity=0.3,
        max_opacity=0.8,
        radius=15,
        blur=10,
        gradient={
            0.0: 'blue',
            0.2: 'cyan',
            0.4: 'lime',
            0.6: 'yellow',
            0.8: 'orange',
            1.0: 'red'
        }
    ).add_to(m)
    
    # Add city center marker
    folium.Marker(
        location=[city_info['lat'], city_info['lon']],
        popup=f"<b>{city_info['name']}</b><br>Signal Coverage Analysis",
        tooltip=f"{city_info['name']} City Center",
        icon=folium.Icon(color='blue', icon='star')
    ).add_to(m)
    
    # Add coverage circle
    folium.Circle(
        location=[city_info['lat'], city_info['lon']],
        radius=radius_m,
        popup=f"Analysis Area: {radius_m/1000:.1f}km radius",
        color='blue',
        fillColor='lightblue',
        fillOpacity=0.1,
        weight=2
    ).add_to(m)
    
    # Create comprehensive statistics panel
    stats_html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 12px; width: 300px;">
        <h4>Signal Coverage Analysis - {city_info['name']}</h4>
        <hr>
        <p><b>Metric:</b> {metric.replace('_', ' ').title()}</p>
        <p><b>Total Points:</b> {city_data['total_points']:,}</p>
        <p><b>Resolution:</b> {city_data['resolution_level'].title()}</p>
        <hr>
        <h5>Overall Statistics</h5>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td><b>Mean:</b></td>
                <td>{stats[metric]['mean_value']:.1f}</td>
            </tr>
            <tr>
                <td><b>Range:</b></td>
                <td>{stats[metric]['min_value']:.1f} - {stats[metric]['max_value']:.1f}</td>
            </tr>
            <tr>
                <td><b>Std Dev:</b></td>
                <td>{stats[metric]['std_value']:.1f}</td>
            </tr>
        </table>
        <hr>
        <h5>Coverage Quality Distribution</h5>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="color: green;">● Excellent:</td>
                <td>{stats[metric]['coverage_percentage']['excellent']:.1f}%</td>
            </tr>
            <tr>
                <td style="color: orange;">● Good:</td>
                <td>{stats[metric]['coverage_percentage']['good']:.1f}%</td>
            </tr>
            <tr>
                <td style="color: #FFD700;">● Fair:</td>
                <td>{stats[metric]['coverage_percentage']['fair']:.1f}%</td>
            </tr>
            <tr>
                <td style="color: red;">● Poor:</td>
                <td>{stats[metric]['coverage_percentage']['poor']:.1f}%</td>
            </tr>
        </table>
        <hr>
        <h5>Value Distribution</h5>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td><b>25th Percentile:</b></td>
                <td>{stats[metric]['value_distribution']['q25']:.1f}</td>
            </tr>
            <tr>
                <td><b>Median:</b></td>
                <td>{stats[metric]['value_distribution']['q50']:.1f}</td>
            </tr>
            <tr>
                <td><b>75th Percentile:</b></td>
                <td>{stats[metric]['value_distribution']['q75']:.1f}</td>
            </tr>
        </table>
    </div>
    """
    
    # Add statistics panel to map
    folium.map.Marker(
        location=[city_info['lat'] + 0.05, city_info['lon'] + 0.05],
        popup=folium.Popup(stats_html, max_width=350),
        icon=folium.DivIcon(html="<div style='font-size: 12px; font-weight: bold; color: blue;'>📊 Stats</div>")
    ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Add colormap
    colormap.add_to(m)
    
    # Add custom JavaScript for interactive features
    m.get_root().html.add_child(folium.Element("""
    <script>
        function updateLegend(metric) {
            // Update legend based on selected metric
            console.log('Updating legend for metric:', metric);
        }
    </script>
    """))
    
    return m._repr_html_()


def create_area_map(area_data: Dict) -> str:
    """
    Create a detailed area-level signal coverage map for zoom functionality.
    
    Args:
        area_data: Dictionary containing area prediction data
        
    Returns:
        HTML string of the map
    """
    center = area_data['center']
    grid = area_data['grid']
    predictions = area_data['predictions']
    stats = area_data['stats']
    radius_m = area_data['radius_m']
    metric = area_data['metric']
    
    # Create base map centered on area
    m = folium.Map(
        location=[center['lat'], center['lon']],
        zoom_start=14,
        tiles='OpenStreetMap'
    )
    
    # Add different tile layers
    folium.TileLayer('cartodbpositron').add_to(m)
    folium.TileLayer('cartodbdark_matter').add_to(m)
    folium.TileLayer('Stamen Terrain').add_to(m)
    
    # Create detailed markers for each grid point
    for idx, row in grid.iterrows():
        value = float(predictions.iloc[idx])
        label, color = _quality_label_and_color(value, metric)
        
        # Create popup with detailed information
        popup_html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 12px;">
            <h4>Signal Measurement</h4>
            <p><b>Location:</b> {row['lat']:.6f}, {row['lon']:.6f}</p>
            <p><b>{metric.replace('_', ' ').title()}:</b> {value:.1f}</p>
            <p><b>Quality:</b> <span style="color: {color};">{label}</span></p>
            <p><b>Distance from center:</b> {row['distance_from_center_m']:.0f}m</p>
        </div>
        """
        
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=8,
            popup=folium.Popup(popup_html, max_width=300),
            color=color,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(m)
    
    # Add center marker
    folium.Marker(
        location=[center['lat'], center['lon']],
        popup="<b>Area Center</b>",
        tooltip="Analysis Center",
        icon=folium.Icon(color='red', icon='crosshairs')
    ).add_to(m)
    
    # Add coverage circle
    folium.Circle(
        location=[center['lat'], center['lon']],
        radius=radius_m,
        popup=f"Analysis Area: {radius_m}m radius",
        color='red',
        fillColor='lightcoral',
        fillOpacity=0.1,
        weight=2
    ).add_to(m)
    
    # Create detailed statistics panel
    stats_html = f"""
    <div style="font-family: Arial, sans-serif; font-size: 12px; width: 300px;">
        <h4>Area Coverage Analysis</h4>
        <hr>
        <p><b>Center:</b> {center['lat']:.6f}, {center['lon']:.6f}</p>
        <p><b>Radius:</b> {radius_m}m</p>
        <p><b>Metric:</b> {metric.replace('_', ' ').title()}</p>
        <p><b>Total Points:</b> {area_data['total_points']:,}</p>
        <p><b>Resolution:</b> {area_data['resolution_level'].title()}</p>
        <hr>
        <h5>Overall Statistics</h5>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td><b>Mean:</b></td>
                <td>{stats[metric]['mean_value']:.1f}</td>
            </tr>
            <tr>
                <td><b>Range:</b></td>
                <td>{stats[metric]['min_value']:.1f} - {stats[metric]['max_value']:.1f}</td>
            </tr>
            <tr>
                <td><b>Std Dev:</b></td>
                <td>{stats[metric]['std_value']:.1f}</td>
            </tr>
        </table>
        <hr>
        <h5>Coverage Quality Distribution</h5>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="color: green;">● Excellent:</td>
                <td>{stats[metric]['coverage_percentage']['excellent']:.1f}%</td>
            </tr>
            <tr>
                <td style="color: orange;">● Good:</td>
                <td>{stats[metric]['coverage_percentage']['good']:.1f}%</td>
            </tr>
            <tr>
                <td style="color: #FFD700;">● Fair:</td>
                <td>{stats[metric]['coverage_percentage']['fair']:.1f}%</td>
            </tr>
            <tr>
                <td style="color: red;">● Poor:</td>
                <td>{stats[metric]['coverage_percentage']['poor']:.1f}%</td>
            </tr>
        </table>
        <hr>
        <h5>Value Distribution</h5>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td><b>25th Percentile:</b></td>
                <td>{stats[metric]['value_distribution']['q25']:.1f}</td>
            </tr>
            <tr>
                <td><b>Median:</b></td>
                <td>{stats[metric]['value_distribution']['q50']:.1f}</td>
            </tr>
            <tr>
                <td><b>75th Percentile:</b></td>
                <td>{stats[metric]['value_distribution']['q75']:.1f}</td>
            </tr>
        </table>
    </div>
    """
    
    # Add statistics panel to map
    folium.map.Marker(
        location=[center['lat'] + 0.001, center['lon'] + 0.001],
        popup=folium.Popup(stats_html, max_width=350),
        icon=folium.DivIcon(html="<div style='font-size: 12px; font-weight: bold; color: red;'>📊 Stats</div>")
    ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m._repr_html_()