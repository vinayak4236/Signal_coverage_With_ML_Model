import math
from typing import Tuple, Optional
import numpy as np
import pandas as pd


EARTH_RADIUS_M = 6371000.0  # meters


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in meters.
    Uses haversine formula for accuracy with small/medium distances.
    """
    rlat1, rlon1, rlat2, rlon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = np.sin(dlat / 2) ** 2 + np.cos(rlat1) * np.cos(rlat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return float(EARTH_RADIUS_M * c)


def meters_to_deg(lat_ref: float, dx_m: float, dy_m: float) -> Tuple[float, float]:
    """Approximate meter-to-degree conversion relative to a reference latitude.
    - dx_m: east-west meters -> delta longitude degrees
    - dy_m: north-south meters -> delta latitude degrees
    Note: accurate for small distances (< ~10km) near lat_ref.
    """
    # 1 deg latitude ~ 111,320 m
    dlat = dy_m / 111320.0
    # 1 deg longitude ~ 111,320 * cos(lat)
    dlon = dx_m / (111320.0 * math.cos(math.radians(lat_ref)) or 1e-9)
    return dlon, dlat


def deg_to_meters(lat_ref: float, dlon: float, dlat: float) -> Tuple[float, float]:
    """Inverse of meters_to_deg for small deltas.
    Returns (dx_m, dy_m).
    """
    dy_m = dlat * 111320.0
    dx_m = dlon * (111320.0 * math.cos(math.radians(lat_ref)) or 1e-9)
    return dx_m, dy_m


def load_csv_dataset(path: str) -> pd.DataFrame:
    """Load dataset with columns [latitude, longitude, download_mbps, upload_mbps, latency_ms].
    - Ensures proper dtypes and drops rows with missing values.
    - Clips values to reasonable ranges for each metric.
    """
    df = pd.read_csv(path)
    needed = {"latitude", "longitude", "download_mbps", "upload_mbps", "latency_ms"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")
    df = df.copy()
    df = df.dropna(subset=["latitude", "longitude", "download_mbps", "upload_mbps", "latency_ms"])  # basic cleaning
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["download_mbps"] = pd.to_numeric(df["download_mbps"], errors="coerce")
    df["upload_mbps"] = pd.to_numeric(df["upload_mbps"], errors="coerce")
    df["latency_ms"] = pd.to_numeric(df["latency_ms"], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    # Clip extreme outliers
    df["download_mbps"] = df["download_mbps"].clip(lower=0, upper=1000)
    df["upload_mbps"] = df["upload_mbps"].clip(lower=0, upper=500)
    df["latency_ms"] = df["latency_ms"].clip(lower=1, upper=500)
    return df


def dataset_centroid(df: pd.DataFrame) -> Tuple[float, float]:
    """Return centroid (lat, lon) of the dataset as a simple mean.
    For small areas, mean is acceptable; for large areas, consider geodesic centroid.
    """
    return float(df["latitude"].mean()), float(df["longitude"].mean())


def generate_prediction_grid(
    center_lat: float,
    center_lon: float,
    radius_m: float = 2000.0,
    spacing_m: float = 50.0,
    clip_to_bbox: Optional[Tuple[float, float, float, float]] = None,
) -> pd.DataFrame:
    """Generate a grid of coordinates around a center using meter spacing.
    - radius_m: radial extent from center
    - spacing_m: grid spacing (approx meters)
    - clip_to_bbox: optional (min_lat, min_lon, max_lat, max_lon)
    Returns DataFrame with [latitude, longitude].
    """
    # Determine step in degrees at center latitude
    dlon_step_deg, dlat_step_deg = meters_to_deg(center_lat, spacing_m, spacing_m)

    # Compute extents in degrees
    dlon_radius_deg, dlat_radius_deg = meters_to_deg(center_lat, radius_m, radius_m)

    lats = np.arange(center_lat - dlat_radius_deg, center_lat + dlat_radius_deg + 1e-12, dlat_step_deg)
    lons = np.arange(center_lon - dlon_radius_deg, center_lon + dlon_radius_deg + 1e-12, dlon_step_deg)

    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")

    # Optionally clip to circular radius (more natural) and bbox
    flat_lat = lat_grid.ravel()
    flat_lon = lon_grid.ravel()

    # Keep only points within radius_m (circle)
    within = np.array([
        haversine_distance_m(center_lat, center_lon, la, lo) <= radius_m for la, lo in zip(flat_lat, flat_lon)
    ])

    if clip_to_bbox is not None:
        min_lat, min_lon, max_lat, max_lon = clip_to_bbox
        within_bbox = (flat_lat >= min_lat) & (flat_lat <= max_lat) & (flat_lon >= min_lon) & (flat_lon <= max_lon)
        within = within & within_bbox

    coords = pd.DataFrame({
        "latitude": flat_lat[within],
        "longitude": flat_lon[within],
    }).reset_index(drop=True)

    return coords


def generate_multi_resolution_grid(
    center_lat: float,
    center_lon: float,
    radius_m: float = 2000.0,
    resolution_level: str = "medium",
    clip_to_bbox: Optional[Tuple[float, float, float, float]] = None,
) -> pd.DataFrame:
    """Generate a prediction grid with configurable resolution levels.
    
    Args:
        center_lat: Center latitude
        center_lon: Center longitude  
        radius_m: Radial extent from center in meters
        resolution_level: Resolution preset ("coarse", "medium", "fine", "ultra")
        clip_to_bbox: Optional bounding box clipping
        
    Returns:
        DataFrame with [latitude, longitude] and resolution metadata
    """
    # Dynamic spacing based on radius to optimize performance for large areas
    if radius_m > 10000:  # Large cities
        base_spacing = 200 if resolution_level == "medium" else 100
    elif radius_m > 5000:  # Medium cities
        base_spacing = 100 if resolution_level == "medium" else 50
    else:  # Small cities/areas
        base_spacing = 50 if resolution_level == "medium" else 25
    
    resolution_configs = {
        "city": {
            "spacing_m": max(500, base_spacing * 2),
            "description": f"City-level overview - {max(500, base_spacing * 2)}m spacing",
            "estimated_points": int((radius_m * 2 / max(500, base_spacing * 2)) ** 2 * 0.8)
        },
        "coarse": {
            "spacing_m": max(200, base_spacing),
            "description": f"Fast overview - {max(200, base_spacing)}m spacing",
            "estimated_points": int((radius_m * 2 / max(200, base_spacing)) ** 2 * 0.8)  # ~80% of square area
        },
        "medium": {
            "spacing_m": base_spacing,
            "description": f"Balanced detail - {base_spacing}m spacing", 
            "estimated_points": int((radius_m * 2 / base_spacing) ** 2 * 0.8)
        },
        "fine": {
            "spacing_m": max(25, base_spacing // 2),
            "description": f"High detail - {max(25, base_spacing // 2)}m spacing",
            "estimated_points": int((radius_m * 2 / max(25, base_spacing // 2)) ** 2 * 0.8)
        },
        "ultra": {
            "spacing_m": max(10, base_spacing // 4),
            "description": f"Maximum detail - {max(10, base_spacing // 4)}m spacing",
            "estimated_points": int((radius_m * 2 / max(10, base_spacing // 4)) ** 2 * 0.8)
        }
    }
    
    if resolution_level not in resolution_configs:
        raise ValueError(f"Invalid resolution_level: {resolution_level}. "
                       f"Choose from: {list(resolution_configs.keys())}")
    
    config = resolution_configs[resolution_level]
    spacing_m = config["spacing_m"]
    
    print(f"Generating {resolution_level} resolution grid:")
    print(f"  - {config['description']}")
    print(f"  - Estimated points: ~{config['estimated_points']:,}")
    print(f"  - Radius: {radius_m}m, Spacing: {spacing_m}m")
    
    # Generate the grid using existing function
    grid = generate_prediction_grid(
        center_lat=center_lat,
        center_lon=center_lon,
        radius_m=radius_m,
        spacing_m=spacing_m,
        clip_to_bbox=clip_to_bbox
    )
    
    # Apply hard limit on points for performance
    max_points = 20000  # Hard limit for performance
    if len(grid) > max_points:
        print(f"  - Warning: Generated {len(grid):,} points exceeds limit of {max_points:,}")
        print(f"  - Sampling {max_points:,} points for performance")
        # Sample points evenly
        sample_indices = np.linspace(0, len(grid)-1, max_points, dtype=int)
        grid = grid.iloc[sample_indices].reset_index(drop=True)
    
    # Add resolution metadata
    grid.attrs = {
        "resolution_level": resolution_level,
        "spacing_m": spacing_m,
        "radius_m": radius_m,
        "center_lat": center_lat,
        "center_lon": center_lon,
        "total_points": len(grid),
        "description": config["description"]
    }
    
    print(f"  - Actual points generated: {len(grid):,}")
    
    return grid


def get_resolution_recommendations(radius_m: float) -> dict:
    """Get resolution recommendations based on area size.
    
    Args:
        radius_m: Radius of the prediction area in meters
        
    Returns:
        Dictionary with resolution recommendations and performance estimates
    """
    recommendations = {
        "coarse": {
            "spacing_m": 100,
            "suitable_for": "Large areas (>5km), quick overviews, initial planning",
            "performance": "Fast",
            "detail_level": "Low"
        },
        "medium": {
            "spacing_m": 50,
            "suitable_for": "Standard analysis, neighborhood coverage",
            "performance": "Balanced",
            "detail_level": "Medium"
        },
        "fine": {
            "spacing_m": 25,
            "suitable_for": "Detailed analysis, site-specific planning",
            "performance": "Slower",
            "detail_level": "High"
        },
        "ultra": {
            "spacing_m": 10,
            "suitable_for": "Precise analysis, small areas (<1km), research",
            "performance": "Slowest",
            "detail_level": "Maximum"
        }
    }
    
    # Adjust recommendations based on area size
    if radius_m > 5000:
        recommendations["ultra"]["suitable_for"] += " (Not recommended for large areas)"
        recommendations["fine"]["suitable_for"] += " (Consider for large areas)"
    elif radius_m < 1000:
        recommendations["coarse"]["suitable_for"] += " (May be too coarse for small areas)"
    
    return recommendations