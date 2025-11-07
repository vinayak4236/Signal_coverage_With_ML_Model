from typing import Tuple, Optional
import numpy as np
import pandas as pd
import folium
from folium.plugins import HeatMap


def _color_for_dbm(v: float) -> str:
    """Map dBm to hex color.
    - Green: strong (>= -70)
    - Orange: medium (-85 to -70)
    - Red: weak (< -85)
    """
    if v >= -70:
        return "#2ecc71"  # green
    elif v >= -85:
        return "#f39c12"  # orange
    else:
        return "#e74c3c"  # red


def build_signal_map(
    points_df: pd.DataFrame,
    predictions: pd.Series | np.ndarray,
    center: Optional[Tuple[float, float]] = None,
    zoom_start: int = 14,
    show_heatmap: bool = False,
) -> folium.Map:
    """Create a Folium map with color-coded predicted points.

    points_df: DataFrame with columns [latitude, longitude]
    predictions: array aligned with points_df
    center: center of the map; if None, use centroid of points
    show_heatmap: add optional heatmap layer for quick overview
    """
    if center is None:
        center = (float(points_df["latitude"].mean()), float(points_df["longitude"].mean()))

    m = folium.Map(location=center, zoom_start=zoom_start, control_scale=True, tiles="OpenStreetMap")

    # Add predicted points as circle markers
    for lat, lon, val in zip(points_df["latitude"].to_numpy(), points_df["longitude"].to_numpy(), np.asarray(predictions)):
        folium.CircleMarker(
            location=(float(lat), float(lon)),
            radius=4,
            weight=0.5,
            color="#333333",
            fill=True,
            fill_opacity=0.8,
            fill_color=_color_for_dbm(float(val)),
            popup=f"Signal: {float(val):.1f} dBm\n({float(lat):.5f}, {float(lon):.5f})",
        ).add_to(m)

    # Optional heatmap to visually smooth areas (not used for metrics)
    if show_heatmap:
        weights = (np.clip(predictions, -120, -50) + 120) / 70.0  # map -120..-50 -> 0..1
        heat_data = [
            [float(lat), float(lon), float(w)] for lat, lon, w in zip(points_df["latitude"], points_df["longitude"], weights)
        ]
        HeatMap(heat_data, radius=15, blur=20, min_opacity=0.3).add_to(m)

    # Add a simple legend
    legend_html = """
    <div style='position: fixed; bottom: 20px; left: 20px; z-index: 9999; background: white; padding: 10px; border: 1px solid #ccc; border-radius: 6px;'>
      <b>Signal Strength (dBm)</b><br>
      <span style='display:inline-block;width:12px;height:12px;background:#2ecc71;border:1px solid #333;'></span> ≥ -70 (Strong)<br>
      <span style='display:inline-block;width:12px;height:12px;background:#f39c12;border:1px solid #333;'></span> -85 to -70 (Medium)<br>
      <span style='display:inline-block;width:12px;height:12px;background:#e74c3c;border:1px solid #333;'></span> < -85 (Weak)
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m