"""
Signal Coverage Prediction Models

This module contains machine learning models for predicting signal coverage
across different metrics (download speed, upload speed, latency).
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from typing import Dict, List, Optional, Tuple
import joblib
from pathlib import Path


class ModelResult:
    """Container for model training results."""
    
    def __init__(self, model, X_test, y_test, y_pred, feature_names):
        self.model = model
        self.X_test = X_test
        self.y_test = y_test
        self.y_pred = y_pred
        self.feature_names = feature_names
        self.mae = mean_absolute_error(y_test, y_pred)
        self.r2 = r2_score(y_test, y_pred)
        self.rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))


class SignalStrengthModel:
    """
    Machine learning model for predicting signal strength metrics.
    
    Supports multiple metrics:
    - download_mbps: Download speed in Mbps
    - upload_mbps: Upload speed in Mbps  
    - latency_ms: Latency in milliseconds
    """
    
    def __init__(self, model_type: str = "rf", target_column: str = "download_mbps"):
        """
        Initialize the signal strength model.
        
        Args:
            model_type: Type of model to use ("rf" for RandomForest)
            target_column: Target variable to predict
        """
        self.model_type = model_type
        self.target_column = target_column
        self.model = None
        self.feature_names = None
        self.is_fitted = False
        
        # Model configurations
        self.model_configs = {
            "rf": {
                "class": RandomForestRegressor,
                "params": {
                    "n_estimators": 100,
                    "max_depth": 15,
                    "min_samples_split": 5,
                    "min_samples_leaf": 2,
                    "random_state": 42,
                    "n_jobs": -1
                }
            }
        }
    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare feature matrix from input data.
        
        Args:
            df: Input dataframe with raw data
            
        Returns:
            Feature matrix for model training/prediction
        """
        # Feature engineering
        features_df = df.copy()
        
        # Location-based features
        if 'latitude' in features_df.columns and 'longitude' in features_df.columns:
            # Distance from city center (if available)
            if 'city_center_lat' in features_df.columns and 'city_center_lon' in features_df.columns:
                features_df['distance_from_center'] = np.sqrt(
                    (features_df['latitude'] - features_df['city_center_lat'])**2 +
                    (features_df['longitude'] - features_df['city_center_lon'])**2
                )
            
            # Grid-based features
            features_df['lat_grid'] = np.round(features_df['latitude'], 3)
            features_df['lon_grid'] = np.round(features_df['longitude'], 3)
        
        # Time-based features (if timestamp available)
        if 'timestamp' in features_df.columns:
            features_df['timestamp'] = pd.to_datetime(features_df['timestamp'])
            features_df['hour'] = features_df['timestamp'].dt.hour
            features_df['day_of_week'] = features_df['timestamp'].dt.dayofweek
            features_df['is_weekend'] = features_df['day_of_week'].isin([5, 6]).astype(int)
        
        # Signal quality indicators
        if 'rsrp' in features_df.columns:
            features_df['rsrp_dbm'] = features_df['rsrp']
        
        if 'rsrq' in features_df.columns:
            features_df['rsrq_db'] = features_df['rsrq']
        
        # Population density proxy (if available)
        if 'population_density' in features_df.columns:
            features_df['pop_density_log'] = np.log1p(features_df['population_density'])
        
        # Building density (if available)
        if 'building_density' in features_df.columns:
            features_df['building_density_scaled'] = features_df['building_density'] / 100.0
        
        # Select relevant features
        feature_columns = [
            col for col in features_df.columns
            if col not in [self.target_column, 'timestamp', 'city_center_lat', 'city_center_lon']
            and not col.startswith(('lat_grid', 'lon_grid'))  # Exclude grid features from final selection
        ]
        
        # Add grid features back
        if 'lat_grid' in features_df.columns:
            feature_columns.extend(['lat_grid', 'lon_grid'])
        
        return features_df[feature_columns]
    
    def fit(self, df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> ModelResult:
        """
        Train the signal strength model.
        
        Args:
            df: Training data
            test_size: Proportion of data to use for testing
            random_state: Random seed for reproducibility
            
        Returns:
            ModelResult object with training metrics
        """
        if self.target_column not in df.columns:
            raise ValueError(f"Target column '{self.target_column}' not found in data")
        
        # Prepare features
        X = self._prepare_features(df)
        y = df[self.target_column]
        
        # Store feature names
        self.feature_names = X.columns.tolist()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        # Initialize and train model
        model_class = self.model_configs[self.model_type]["class"]
        model_params = self.model_configs[self.model_type]["params"]
        
        self.model = model_class(**model_params)
        self.model.fit(X_train, y_train)
        
        # Make predictions on test set
        y_pred = self.model.predict(X_test)
        
        # Store results
        result = ModelResult(self.model, X_test, y_test, y_pred, self.feature_names)
        self.is_fitted = True
        
        print(f"Model trained for {self.target_column}:")
        print(f"  R² Score: {result.r2:.3f}")
        print(f"  MAE: {result.mae:.3f}")
        print(f"  RMSE: {result.rmse:.3f}")
        
        return result
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions on new data.
        
        Args:
            X: Input data for prediction
            
        Returns:
            Predicted values
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before making predictions")
        
        # Prepare features
        X_processed = self._prepare_features(X)
        
        # Ensure all required features are present
        missing_features = set(self.feature_names) - set(X_processed.columns)
        if missing_features:
            # Fill missing features with zeros or appropriate defaults
            for feature in missing_features:
                X_processed[feature] = 0.0
        
        # Reorder columns to match training data
        X_processed = X_processed[self.feature_names]
        
        return self.model.predict(X_processed)
    
    def save_model(self, filepath: str):
        """Save the trained model to disk."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before saving")
        
        model_data = {
            'model_type': self.model_type,
            'target_column': self.target_column,
            'model': self.model,
            'feature_names': self.feature_names,
            'is_fitted': self.is_fitted
        }
        
        joblib.dump(model_data, filepath)
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load a trained model from disk."""
        model_data = joblib.load(filepath)
        
        self.model_type = model_data['model_type']
        self.target_column = model_data['target_column']
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        self.is_fitted = model_data['is_fitted']
        
        print(f"Model loaded from {filepath}")
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance for tree-based models."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before getting feature importance")
        
        if hasattr(self.model, 'feature_importances_'):
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            return importance_df
        else:
            raise ValueError("Model does not support feature importance")


def load_csv_dataset(filepath: str) -> pd.DataFrame:
    """
    Load signal coverage dataset from CSV file.
    
    Expected columns:
    - latitude, longitude: Geographic coordinates
    - download_mbps: Download speed in Mbps
    - upload_mbps: Upload speed in Mbps
    - latency_ms: Latency in milliseconds
    - Optional: rsrp, rsrq, timestamp, population_density, etc.
    """
    if not Path(filepath).exists():
        raise FileNotFoundError(f"Dataset file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    
    # Validate required columns
    required_columns = ['latitude', 'longitude', 'download_mbps', 'upload_mbps', 'latency_ms']
    missing_columns = set(required_columns) - set(df.columns)
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Basic data cleaning
    df = df.dropna(subset=required_columns)
    
    # Remove outliers (basic filtering)
    df = df[
        (df['download_mbps'] >= 0) & (df['download_mbps'] <= 1000) &
        (df['upload_mbps'] >= 0) & (df['upload_mbps'] <= 500) &
        (df['latency_ms'] >= 0) & (df['latency_ms'] <= 1000)
    ]
    
    print(f"Loaded dataset with {len(df)} samples")
    return df


def generate_multi_resolution_grid(center_lat: float, center_lon: float, 
                                 radius_m: int, resolution_level: str = "medium") -> pd.DataFrame:
    """
    Generate a grid of prediction points around a center location.
    
    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        radius_m: Radius in meters
        resolution_level: Resolution level ("coarse", "medium", "fine", "ultra_fine")
        
    Returns:
        DataFrame with grid points
    """
    # Resolution settings (meters between points)
    resolution_settings = {
        "coarse": 1000,      # 1km spacing
        "medium": 500,       # 500m spacing
        "fine": 200,         # 200m spacing
        "ultra_fine": 100    # 100m spacing
    }
    
    if resolution_level not in resolution_settings:
        raise ValueError(f"Invalid resolution level: {resolution_level}")
    
    spacing_m = resolution_settings[resolution_level]
    
    # Convert radius to degrees (approximate)
    radius_deg = radius_m / 111000  # 1 degree ≈ 111km
    
    # Generate grid
    n_points = int(radius_m / spacing_m) * 2 + 1
    lat_min = center_lat - radius_deg
    lat_max = center_lat + radius_deg
    lon_min = center_lon - radius_deg
    lon_max = center_lon + radius_deg
    
    lat_points = np.linspace(lat_min, lat_max, n_points)
    lon_points = np.linspace(lon_min, lon_max, n_points)
    
    # Create grid
    grid_points = []
    for lat in lat_points:
        for lon in lon_points:
            # Calculate distance from center
            dist_m = np.sqrt((lat - center_lat)**2 + (lon - center_lon)**2) * 111000
            
            if dist_m <= radius_m:
                grid_points.append({
                    'latitude': lat,
                    'longitude': lon,
                    'distance_from_center_m': dist_m
                })
    
    df = pd.DataFrame(grid_points)
    
    # Add some basic features for prediction
    df['city_center_lat'] = center_lat
    df['city_center_lon'] = center_lon
    
    print(f"Generated {len(df)} grid points with {resolution_level} resolution")
    return df


def get_resolution_recommendations(radius_m: int) -> Dict[str, str]:
    """
    Get resolution recommendations based on area radius.
    
    Args:
        radius_m: Radius in meters
        
    Returns:
        Dictionary with resolution recommendations and descriptions
    """
    if radius_m <= 1000:
        return {
            "coarse": "1km spacing - Fast, low detail",
            "medium": "500m spacing - Balanced (recommended)",
            "fine": "200m spacing - Detailed, slower",
            "ultra_fine": "100m spacing - Very detailed, slow"
        }
    elif radius_m <= 5000:
        return {
            "coarse": "1km spacing - Fast overview",
            "medium": "500m spacing - Good balance (recommended)",
            "fine": "200m spacing - Detailed analysis",
            "ultra_fine": "100m spacing - Very detailed, may be slow"
        }
    elif radius_m <= 15000:
        return {
            "coarse": "1km spacing - Recommended for large areas",
            "medium": "500m spacing - Detailed for medium areas",
            "fine": "200m spacing - Very detailed, slower",
            "ultra_fine": "100m spacing - Ultra detailed, very slow"
        }
    else:
        return {
            "coarse": "1km spacing - Only option for very large areas",
            "medium": "500m spacing - May be slow for very large areas",
            "fine": "200m spacing - Not recommended for very large areas",
            "ultra_fine": "100m spacing - Not recommended for very large areas"
        }