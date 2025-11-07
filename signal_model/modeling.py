from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error


ModelType = Literal["rf", "gpr"]


def _to_xy(df: pd.DataFrame, target_column: str) -> Tuple[np.ndarray, np.ndarray]:
    X = df[["latitude", "longitude"]].to_numpy(dtype=float)
    y = df[target_column].to_numpy(dtype=float)
    return X, y


@dataclass
class TrainResult:
    model_type: ModelType
    r2: Optional[float]
    mae: Optional[float]
    n_train: int


class SignalStrengthModel:
    """Wraps a regression model to predict a target metric from lat/lon.

    model_type: 'rf' (RandomForestRegressor) or 'gpr' (GaussianProcessRegressor)
    target_column: which column to learn (e.g. 'signal_strength', 'download_mbps')
    The model can be updated with new points via update_model.
    """

    def __init__(
        self,
        model_type: ModelType = "rf",
        random_state: int = 42,
        n_estimators: int = 300,
        gpr_length_scale: float = 0.01,
        gpr_alpha: float = 1.0,
        target_column: str = "signal_strength",
    ) -> None:
        self.model_type = model_type
        self.random_state = random_state
        self.n_estimators = n_estimators
        self.gpr_length_scale = gpr_length_scale
        self.gpr_alpha = gpr_alpha
        self.target_column = target_column
        self._model = None
        self._data = None  # cached training dataframe

    def _build_model(self):
        if self.model_type == "rf":
            return RandomForestRegressor(
                n_estimators=self.n_estimators,
                random_state=self.random_state,
                n_jobs=-1,
                min_samples_leaf=2,
                max_depth=None,
            )
        elif self.model_type == "gpr":
            # Kernel: Constant * RBF + WhiteKernel (noise)
            # Note: lat/lon are in degrees; length_scale ~0.01 deg ~ 1.1 km near equator.
            kernel = ConstantKernel(1.0, (1e-2, 1e3)) * RBF(length_scale=self.gpr_length_scale, length_scale_bounds=(1e-4, 1e1)) + WhiteKernel(noise_level=self.gpr_alpha)
            return GaussianProcessRegressor(kernel=kernel, alpha=0.0, normalize_y=True, random_state=self.random_state)
        else:
            raise ValueError("Unknown model_type: {self.model_type}")

    def fit(self, df: pd.DataFrame, holdout: bool = True) -> TrainResult:
        """Fit the model on df. Optionally compute simple holdout metrics for quick validation."""
        if df.empty:
            raise ValueError("Training data is empty")
        self._data = df.copy()
        if self.target_column not in df.columns:
            raise ValueError(f"Training data missing target column '{self.target_column}'")
        X, y = _to_xy(df, self.target_column)

        if holdout and len(df) >= 10:
            X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=self.random_state)
        else:
            X_tr, y_tr = X, y
            X_te = y_te = None

        self._model = self._build_model()
        self._model.fit(X_tr, y_tr)

        r2 = mae = None
        if X_te is not None:
            y_pred = self._model.predict(X_te)
            r2 = float(r2_score(y_te, y_pred))
            mae = float(mean_absolute_error(y_te, y_pred))

        return TrainResult(model_type=self.model_type, r2=r2, mae=mae, n_train=len(X_tr))

    def predict(self, coords: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model is not trained. Call fit() first.")
        X = coords[["latitude", "longitude"]].to_numpy(dtype=float)
        return self._model.predict(X)

    def update_model(self, new_data: pd.DataFrame) -> TrainResult:
        """Append new measurements and retrain the model.
        new_data must contain columns [latitude, longitude, <target_column>].
        """
        if self._data is None:
            # If model not trained yet, treat as initial fit
            return self.fit(new_data, holdout=False)
        updated = pd.concat([self._data, new_data], ignore_index=True)
        return self.fit(updated, holdout=False)

    @property
    def training_data(self) -> Optional[pd.DataFrame]:
        return None if self._data is None else self._data.copy()

    def set_target(self, target_column: str) -> None:
        """Change the target metric for future fits/predictions (requires refit)."""
        self.target_column = target_column